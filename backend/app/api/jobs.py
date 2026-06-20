import subprocess
import sys
import uuid
from datetime import datetime, timezone
from urllib.parse import unquote
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from typing import List

from app.database import get_db
from app.models import Job, JobLog, Setting
from app.schemas import JobArtifactContentResponse, JobArtifactResponse, JobCreate, JobResponse, JobLogResponse
from app.utils.url_validation import is_safe_github_url
from app.utils.repo_name import repo_name_from_url
from app.services.analysis_service import AnalysisService

router = APIRouter()


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _compute_duration_seconds(job: Job) -> int | None:
    started_at = _ensure_utc(job.started_at)
    if not started_at:
        return None

    end_time = _ensure_utc(job.completed_at) or datetime.now(timezone.utc)
    duration = end_time - started_at
    return max(0, int(duration.total_seconds()))


def _build_job_response(job: Job) -> JobResponse:
    response = JobResponse.model_validate(job)
    response.created_at = _ensure_utc(response.created_at)
    response.started_at = _ensure_utc(response.started_at)
    response.completed_at = _ensure_utc(response.completed_at)
    response.download_url = f"/api/jobs/{job.id}/download"
    response.duration_seconds = _compute_duration_seconds(job)
    return response

def run_analysis_task(
    job_id: str, 
    repo_url: str, 
    github_token: str = None, 
    provider_override: str = None, 
    model_override: str = None,
    source_job_id: str = None,
    resume_from_stage: str = None,
):
    """Background task executed by FastAPI to run the analysis."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        service = AnalysisService(db, job_id)
        service.run_analysis(
            repo_url,
            github_token,
            provider_override,
            model_override,
            source_job_id=source_job_id,
            resume_from_stage=resume_from_stage,
        )
    finally:
        db.close()

@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    url = payload.github_url.strip()
    if not is_safe_github_url(url):
        raise HTTPException(status_code=400, detail="Invalid or unsafe GitHub URL")

    source_job = None
    if payload.resume_from_stage:
        if not payload.source_job_id:
            raise HTTPException(status_code=400, detail="source_job_id is required when resume_from_stage is provided")
        source_job = db.query(Job).filter(Job.id == payload.source_job_id).first()
        if not source_job:
            raise HTTPException(status_code=404, detail="Source job not found")
        if payload.resume_from_stage != "analysis_state":
            raise HTTPException(status_code=400, detail="Unsupported resume stage")

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
        job_kind="analysis",
        repo_url=url,
        repo_name=repo_name,
        status="queued",
        progress=0,
        current_step=(
            "Queued to retry from Structured Analysis State"
            if payload.resume_from_stage == "analysis_state"
            else "Queued in background"
        ),
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
        model_override=payload.model_override,
        source_job_id=payload.source_job_id,
        resume_from_stage=payload.resume_from_stage,
    )

    return _build_job_response(new_job)

@router.get("/jobs", response_model=List[JobResponse])
def get_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).filter(Job.parent_job_id.is_(None)).order_by(Job.created_at.desc()).all()
    return [_build_job_response(job) for job in jobs]

@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return _build_job_response(job)

@router.get("/jobs/{job_id}/logs", response_model=List[JobLogResponse])
def get_job_logs(job_id: str, db: Session = Depends(get_db)):
    # Verify job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    logs = db.query(JobLog).filter(JobLog.job_id == job_id).order_by(JobLog.created_at.asc()).all()
    return logs

@router.get("/jobs/{job_id}/children", response_model=List[JobResponse])
def get_job_children(job_id: str, db: Session = Depends(get_db)):
    parent = db.query(Job).filter(Job.id == job_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Job not found")

    children = (
        db.query(Job)
        .filter(Job.parent_job_id == job_id)
        .order_by(Job.sort_index.asc(), Job.created_at.asc())
        .all()
    )
    return [_build_job_response(child) for child in children]

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


def build_artifact_label(relative_path: str) -> str:
    parts = Path(relative_path).parts
    if not parts:
        return relative_path
    if parts[0] == "evidence" and parts[-1] == "extraction_report.md":
        return "Evidence Extraction Report"
    if parts[0] == "sections" and len(parts) >= 2:
        return parts[-1].replace(".md", "").replace("_", " ").title()
    if parts[-1] == "analysis_state.md":
        return "Structured Analysis State"
    if parts[-1] == "analysis_state.json":
        return "Structured Analysis State JSON"
    if parts[-1] == "compiled_blueprint.md":
        return "Compiled Blueprint"
    return parts[-1]


def build_artifact_category(relative_path: str) -> str:
    parts = Path(relative_path).parts
    if not parts:
        return "artifact"
    if parts[0] == "evidence":
        return "evidence"
    if parts[0] == "sections":
        return "section"
    if parts[-1].startswith("analysis_state"):
        return "analysis"
    if parts[-1] == "compiled_blueprint.md":
        return "compiled"
    return "artifact"


def resolve_workspace_artifact(job: Job, relative_path: str) -> Path:
    if not job.workspace_path:
        raise HTTPException(status_code=404, detail="Job workspace path is not available")

    base_path = Path(job.workspace_path).resolve()
    candidate = (base_path / unquote(relative_path)).resolve()
    if base_path != candidate and base_path not in candidate.parents:
        raise HTTPException(status_code=403, detail="Forbidden artifact path access attempt")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return candidate


def resolve_repo_inventory_file(job: Job, relative_path: str) -> Path:
    if not job.workspace_path:
        raise HTTPException(status_code=404, detail="Job workspace path is not available")

    workspace_path = Path(job.workspace_path).resolve()
    normalized_relative_path = Path(unquote(relative_path))
    if normalized_relative_path.is_absolute():
        raise HTTPException(status_code=400, detail="File path must be relative to the analyzed repository")

    candidate_roots = [workspace_path]
    if job.repo_name:
        candidate_roots.append((workspace_path / job.repo_name).resolve())

    # Older jobs keep the cloned repository as a direct child of the workspace.
    for child in workspace_path.iterdir():
        if child.is_dir():
            candidate_roots.append(child.resolve())

    checked_roots = []
    for root in candidate_roots:
        if root in checked_roots or not root.exists() or not root.is_dir():
            continue
        checked_roots.append(root)
        candidate = (root / normalized_relative_path).resolve()
        if root != candidate and root not in candidate.parents:
            continue
        if candidate.exists() and candidate.is_file():
            return candidate

    raise HTTPException(status_code=404, detail="File not found")


def open_path_in_default_app(target_path: Path) -> None:
    if sys.platform == "darwin":
        command = ["open", str(target_path)]
    elif sys.platform.startswith("win"):
        command = ["cmd", "/c", "start", "", str(target_path)]
    else:
        command = ["xdg-open", str(target_path)]

    try:
        subprocess.run(command, check=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to open file in the default app: {exc}") from exc


@router.get("/jobs/{job_id}/artifacts", response_model=List[JobArtifactResponse])
def list_job_artifacts(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.workspace_path:
        return []

    workspace = Path(job.workspace_path)
    artifact_rel_paths = []
    for relative_path in [
        "evidence/extraction_report.md",
        "analysis/analysis_state.md",
        "analysis/analysis_state.json",
        "sections/01_foundation.md",
        "sections/02_functional_architecture.md",
        "sections/03_data_api_ui_security.md",
        "sections/04_ops_quality_delivery.md",
        "sections/compiled_blueprint.md",
    ]:
        artifact_path = workspace / relative_path
        if artifact_path.exists() and artifact_path.is_file():
            artifact_rel_paths.append(relative_path)

    return [
        JobArtifactResponse(
            path=relative_path,
            label=build_artifact_label(relative_path),
            category=build_artifact_category(relative_path),
        )
        for relative_path in artifact_rel_paths
    ]


@router.get("/jobs/{job_id}/artifacts/content", response_model=JobArtifactContentResponse)
def get_job_artifact_content(job_id: str, path: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    artifact_path = resolve_workspace_artifact(job, path)
    try:
        content = artifact_path.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read artifact content: {e}")

    relative_path = str(artifact_path.relative_to(Path(job.workspace_path)))
    return JobArtifactContentResponse(
        path=relative_path,
        label=build_artifact_label(relative_path),
        category=build_artifact_category(relative_path),
        content=content,
    )


@router.post("/jobs/{job_id}/open-file")
def open_job_file(job_id: str, path: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    target_file = resolve_repo_inventory_file(job, path)
    open_path_in_default_app(target_file)

    return {
        "message": "File opened in the default app",
        "path": str(target_file.relative_to(Path(job.workspace_path).resolve())),
    }
