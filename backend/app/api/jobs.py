import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from typing import List

from app.database import get_db
from app.models import Job, JobLog, Setting
from app.schemas import JobCreate, JobResponse, JobLogResponse
from app.utils.url_validation import is_safe_github_url
from app.utils.repo_name import repo_name_from_url
from app.services.analysis_service import AnalysisService

router = APIRouter()

def run_analysis_task(
    job_id: str, 
    repo_url: str, 
    github_token: str = None, 
    provider_override: str = None, 
    model_override: str = None
):
    """Background task executed by FastAPI to run the analysis."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        service = AnalysisService(db, job_id)
        service.run_analysis(repo_url, github_token, provider_override, model_override)
    finally:
        db.close()

@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    url = payload.github_url.strip()
    if not is_safe_github_url(url):
        raise HTTPException(status_code=400, detail="Invalid or unsafe GitHub URL")

    # Generate job details
    job_id = str(uuid.uuid4())
    repo_name = repo_name_from_url(url)
    
    # Resolve provider and model name from settings if not overridden
    setting = db.query(Setting).first()
    provider_name = payload.provider_override or (setting.provider if setting else "mock")
    model_name = payload.model_override or (setting.model if setting else "mock-model")
    
    # Save job record
    new_job = Job(
        id=job_id,
        repo_url=url,
        repo_name=repo_name,
        status="queued",
        progress=0,
        current_step="Queued in background",
        provider=provider_name,
        model=model_name
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Launch task in background
    background_tasks.add_task(
        run_analysis_task,
        job_id=job_id,
        repo_url=url,
        github_token=payload.github_token,
        provider_override=payload.provider_override,
        model_override=payload.model_override
    )

    response = JobResponse.model_validate(new_job)
    response.download_url = f"/api/jobs/{job_id}/download"
    return response

@router.get("/jobs", response_model=List[JobResponse])
def get_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    response_list = []
    for job in jobs:
        resp = JobResponse.model_validate(job)
        resp.download_url = f"/api/jobs/{job.id}/download"
        response_list.append(resp)
    return response_list

@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    resp = JobResponse.model_validate(job)
    resp.download_url = f"/api/jobs/{job_id}/download"
    return resp

@router.get("/jobs/{job_id}/logs", response_model=List[JobLogResponse])
def get_job_logs(job_id: str, db: Session = Depends(get_db)):
    # Verify job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    logs = db.query(JobLog).filter(JobLog.job_id == job_id).order_by(JobLog.created_at.asc()).all()
    return logs

@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.status not in ("queued", "running"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel job in state: {job.status}")
        
    # Mark job as cancelled
    job.status = "cancelled"
    job.current_step = "Job cancelled by user"
    
    # Log cancel event
    cancel_log = JobLog(job_id=job_id, level="WARNING", message="User requested job cancellation. Aborting steps...")
    db.add(cancel_log)
    db.commit()
    
    return {"message": "Job cancellation request sent"}

@router.get("/jobs/{job_id}/download")
def download_blueprint(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Rebuild blueprint is not ready yet")
        
    if not job.output_path or not Path(job.output_path).exists():
        raise HTTPException(status_code=404, detail="Generated blueprint file missing on local disk")
        
    # Security requirement: check that downloading path is indeed inside outputs folder
    output_file_path = Path(job.output_path).resolve()
    from app.config import OUTPUTS_DIR
    resolved_outputs = OUTPUTS_DIR.resolve()
    
    if resolved_outputs not in output_file_path.parents:
         raise HTTPException(status_code=403, detail="Forbidden file path download attempt")
         
    return FileResponse(
        path=str(output_file_path),
        filename=f"{job.repo_name}_REBUILD_BLUEPRINT.md",
        media_type="text/markdown"
    )

@router.get("/jobs/{job_id}/preview")
def preview_blueprint(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Blueprint is not generated yet")
        
    if not job.output_path or not Path(job.output_path).exists():
        raise HTTPException(status_code=404, detail="Generated blueprint file missing on disk")
        
    # Verify folder hierarchy
    output_file_path = Path(job.output_path).resolve()
    from app.config import OUTPUTS_DIR
    resolved_outputs = OUTPUTS_DIR.resolve()
    
    if resolved_outputs not in output_file_path.parents:
         raise HTTPException(status_code=403, detail="Forbidden file path preview attempt")
         
    try:
        content = output_file_path.read_text(encoding="utf-8")
        return {"repo_name": job.repo_name, "markdown": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read blueprint content: {e}")

@router.get("/jobs/{job_id}/inventory")
def get_job_inventory(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")
        
    from app.config import OUTPUTS_DIR, JOBS_DIR
    import json
    
    # Primary path: copied to outputs dir during job completion
    inventory_path = OUTPUTS_DIR / f"{job_id}_inventory.json"
    
    # Fallback: search inside the job workspace (for jobs completed before the copy step was added)
    if not inventory_path.exists() and job.workspace_path:
        workspace = Path(job.workspace_path)
        matches = list(workspace.rglob("*_inventory.json"))
        if matches:
            inventory_path = matches[0]
    
    if not inventory_path.exists():
        raise HTTPException(status_code=404, detail="Repository inventory file missing on disk")
        
    # Security check — only allow paths under OUTPUTS_DIR or JOBS_DIR
    resolved_inventory = inventory_path.resolve()
    resolved_outputs = OUTPUTS_DIR.resolve()
    resolved_jobs = JOBS_DIR.resolve()
    
    if resolved_outputs not in resolved_inventory.parents and resolved_jobs not in resolved_inventory.parents:
        raise HTTPException(status_code=403, detail="Forbidden file path retrieval attempt")
        
    try:
        content = resolved_inventory.read_text(encoding="utf-8")
        return json.loads(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read inventory content: {e}")
