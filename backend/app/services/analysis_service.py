import sys
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.config import JOBS_DIR, OUTPUTS_DIR
from app.models import Job, JobLog
from app.services.git_service import GitService
from app.services.redaction_service import redact_secrets
from app.services.providers import get_provider
from app.services.providers.provider_limits import is_local_provider_name
from app.utils.file_filters import is_important_file
from app.services.summary_service import SummaryMapService
from app.services.reduce_service import ReduceService
from app.services.incremental_generator import IncrementalSpecGenerator

logger = logging.getLogger(__name__)

LOCAL_DIRECT_MODE_MIN_OUTPUT_TOKENS = 6000
LOCAL_DIRECT_MODE_MIN_CHUNK_SIZE = 50000
DEFAULT_QUALITY_STRATEGY = "hierarchical"

class AnalysisService:
    def __init__(self, db: Session, job_id: str):
        self.db = db
        self.job_id = job_id
        
    def log(self, message: str, level: str = "INFO"):
        """Logs a message to Python logging and inserts it into the SQLite database."""
        logger.info(f"[{self.job_id}] {level}: {message}")
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            log_entry = JobLog(job_id=self.job_id, level=level, message=message)
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to commit log to database: {e}")
        finally:
            db.close()

    def update_job(self, progress: int, current_step: str, status: str = "running", error: str = None, output_path: str = None):
        """Updates the job progress and status in the database."""
        if status not in ["cancelled", "failed", "completed"]:
            self.check_cancelled()
            
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == self.job_id).first()
            if job:
                job.progress = progress
                job.current_step = current_step
                job.status = status
                if error:
                    job.error_message = error
                if output_path:
                    job.output_path = output_path
                if status in ["completed", "failed", "cancelled"]:
                    job.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception as e:
            if "cancelled by the user" in str(e):
                raise e
            logger.error(f"Failed to update job status: {e}")
        finally:
            db.close()

    def log_stage(self, stage: str, message: str, level: str = "INFO", **details):
        detail_text = ""
        if details:
            parts = [f"{key}={value}" for key, value in details.items()]
            detail_text = " | " + ", ".join(parts)
        self.log(f"[{stage}] {message}{detail_text}", level)

    def check_cancelled(self):
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == self.job_id).first()
            if job and job.status == "cancelled":
                raise Exception("Job was cancelled by the user")
        finally:
            db.close()

    def get_available_output_path(self, base_name: str) -> Path:
        """Return a stable output path without job IDs, adding a numeric suffix only on collision."""
        candidate = OUTPUTS_DIR / base_name
        if not candidate.exists():
            return candidate

        stem = Path(base_name).stem
        suffix = Path(base_name).suffix
        counter = 2
        while True:
            candidate = OUTPUTS_DIR / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def run_analysis(self, repo_url: str, github_token: str = None, provider_override: str = None, model_override: str = None):
        """Executes the full repository analysis pipeline."""
        workspace_path = None
        repo_path = None
        try:
            self.check_cancelled()
            self.update_job(0, "Validating parameters", "running")
            self.log(f"Starting analysis for repository: {repo_url}")
            
            # Fetch settings
            from app.models import Setting
            settings = self.db.query(Setting).first()
            if not settings:
                raise Exception("System settings not found. Please configure settings first.")

            # Load provider
            provider_name = provider_override or settings.provider
            model_name = model_override or settings.model
            
            # Resolve api key for the chosen provider
            api_key = ""
            if settings.api_keys_json:
                import json
                try:
                    api_keys = json.loads(settings.api_keys_json or "{}")
                    api_key = api_keys.get(provider_name, "")
                except Exception:
                    pass
            if not api_key and provider_name == settings.provider:
                api_key = settings.api_key
                
            # If provider is overridden and different from active setting, do not use settings.base_url (which belongs to the active provider)
            if provider_name == settings.provider:
                base_url = settings.base_url
            else:
                base_url = ""
            
            # Handle github token override
            token = github_token or settings.github_token
            
            self.log(f"Using LLM Provider: {provider_name} (Model: {model_name})")

            # Setup workspace
            workspace_path = JOBS_DIR / self.job_id
            workspace_path.mkdir(parents=True, exist_ok=True)
            
            # Update job model
            job = self.db.query(Job).filter(Job.id == self.job_id).first()
            if job:
                job.workspace_path = str(workspace_path)
                job.started_at = datetime.now(timezone.utc)
                self.db.commit()

            # Step 1: Clone Repository
            self.check_cancelled()
            self.update_job(10, "Cloning repository")
            self.log_stage("clone", "Cloning repository into temporary workspace...")
            repo_path = GitService.clone_repository(repo_url, workspace_path, token)
            repo_name = repo_path.name
            self.log_stage("clone", "Repository cloned successfully.", repo_name=repo_name, workspace=str(repo_path))

            # Locate Extractor Scripts dynamically by walking up parents
            extractor_dir = None
            current = Path(__file__).resolve().parent
            for _ in range(10):
                candidate = current / "universal-repo-rebuild-blueprint-extractor"
                if candidate.exists() and candidate.is_dir():
                    extractor_dir = candidate
                    break
                candidate_nested = current / "repo-blueprint-studio" / "universal-repo-rebuild-blueprint-extractor"
                if candidate_nested.exists() and candidate_nested.is_dir():
                    extractor_dir = candidate_nested
                    break
                if current.parent == current:
                    break
                current = current.parent

            if not extractor_dir:
                raise Exception("universal-repo-rebuild-blueprint-extractor directory not found in workspace hierarchy")

            skill_dir = extractor_dir / "skills" / "repo-spec-extractor"
            inventory_script = skill_dir / "scripts" / "repo_inventory.py"
            template_file = skill_dir / "templates" / "REPO_SPECIFICATION_TEMPLATE.md"
            
            if not inventory_script.exists():
                raise Exception(f"Inventory script not found at {inventory_script}")
            if not template_file.exists():
                raise Exception(f"Template file not found at {template_file}")

            # Step 2: Run Inventory Script
            self.check_cancelled()
            self.update_job(18, "Generating repository inventory")
            self.log_stage("inventory", "Running repo_inventory.py...", script=str(inventory_script))
            docs_dir = repo_path / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)
            inventory_json_path = docs_dir / "inventory" / f"{repo_name}_inventory.json"
            inventory_json_path.parent.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                sys.executable, 
                str(inventory_script), 
                "--repo-path", str(repo_path), 
                "--output", str(inventory_json_path),
                "--max-files", "20000"
            ]
            
            res = subprocess.run(cmd, text=True, capture_output=True, timeout=90.0)
            if res.returncode != 0:
                raise Exception(f"Inventory generation failed: {res.stderr}")
                
            self.log_stage("inventory", "Inventory written.", output=str(inventory_json_path))
            
            # Step 3: Parse Inventory & Load Core Metadata
            self.check_cancelled()
            self.update_job(28, "Analyzing repository file structure")
            with open(inventory_json_path, "r", encoding="utf-8") as f:
                inventory_data = json.load(f)
                
            summary = inventory_data.get("summary", {})
            manifests = summary.get("manifest_files", [])
            files_list = inventory_data.get("files", [])
            
            self.log_stage(
                "inventory",
                "Repository inventory parsed.",
                file_count=summary.get("file_count_included", 0),
                manifest_count=len(manifests),
            )
            self.log_stage("inventory", "Detected manifests.", manifests=", ".join(manifests) or "none")

            # Optional fast path for explicit mock/direct local testing only.
            if provider_name.lower() == "mock" and getattr(settings, "analysis_strategy", DEFAULT_QUALITY_STRATEGY) == "direct":
                self.check_cancelled()
                self.update_job(60, "Generating blueprint via Mock Provider")
                self.log("Using Mock Provider to create rebuild blueprint...")
                provider = get_provider("mock")
                blueprint_content = provider.generate(
                    prompt=f"Repository: {repo_name}\nURL: {repo_url}",
                    system_prompt=""
                )

                
                # Save output
                output_md_name = f"{repo_name}_REBUILD_BLUEPRINT.md"
                repo_output_path = docs_dir / output_md_name
                repo_output_path.write_text(blueprint_content, encoding="utf-8")
                
                # Copy to data/outputs
                local_output_path = self.get_available_output_path(output_md_name)
                shutil.copy(str(repo_output_path), str(local_output_path))
                
                self.update_job(100, "Analysis complete", "completed", output_path=str(local_output_path))
                self.log(f"Rebuild blueprint saved successfully to {local_output_path}")
                return

            # Real LLM Pipeline
            provider = get_provider(provider_name, api_key, base_url, model_name)
            
            # Resolve model limits dynamically
            limits = provider.get_model_limits(model_name)
            resolved_max_output_tokens = limits["max_output_tokens"]
            resolved_chunk_size = limits["chunk_size"]
            limit_source = limits.get("source", "fallback")
            limit_notes = limits.get("notes", "")
            
            # If no override was requested, prefer using settings value unless it's default/unconfigured
            if not model_override and not provider_override:
                if settings.max_output_tokens:
                    resolved_max_output_tokens = settings.max_output_tokens
                if settings.chunk_size:
                    resolved_chunk_size = settings.chunk_size

            self.log(
                f"Model limits resolved: context window / chunk size = {resolved_chunk_size} chars, "
                f"max output = {resolved_max_output_tokens} tokens (source: {limit_source})"
            )
            if limit_notes:
                self.log(f"Model limits note: {limit_notes}", "DEBUG")
            
            # Branch based on Strategy
            strategy = getattr(settings, "analysis_strategy", DEFAULT_QUALITY_STRATEGY)
            effective_strategy = DEFAULT_QUALITY_STRATEGY
            if strategy != DEFAULT_QUALITY_STRATEGY:
                self.log_stage(
                    "strategy",
                    "Quality-first pipeline overrides the selected strategy to preserve consistent output quality across models.",
                    "WARNING",
                    requested=strategy,
                    effective=effective_strategy,
                )
            else:
                self.log_stage("strategy", "Quality-first staged analysis enabled.", effective=effective_strategy)

            if effective_strategy == "hierarchical":
                self.log("Hierarchical Map-Reduce Strategy enabled.", "INFO")
                
                # Step 4: Map Phase - summarize files in parallel
                self.update_job(34, "Preparing evidence extraction")
                map_service = SummaryMapService(
                    provider=provider,
                    workspace_path=workspace_path,
                    log_fn=self.log,
                    progress_fn=self.update_job
                )
                
                allowed_files = []
                skipped_for_size = 0
                skipped_for_type = 0
                for f in files_list:
                    # Max file size limit
                    if f["size_bytes"] > settings.max_file_size_kb * 1024:
                        skipped_for_size += 1
                        continue
                    ext = Path(f["path"]).suffix.lower()
                    if ext in [".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".tar", ".gz", ".mp3", ".mp4", ".woff", ".woff2", ".ttf"]:
                        skipped_for_type += 1
                        continue
                    allowed_files.append(f)
                    
                self.log_stage(
                    "evidence",
                    "Prepared candidate files for summarization.",
                    candidates=len(allowed_files),
                    skipped_for_size=skipped_for_size,
                    skipped_for_type=skipped_for_type,
                    map_batch_size=getattr(settings, "map_batch_size", 5),
                )
                self.update_job(38, f"Summarizing {len(allowed_files)} candidate files")
                summaries = map_service.map_codebase(
                    files_list=allowed_files,
                    repo_path=repo_path,
                    batch_size=getattr(settings, "map_batch_size", 5)
                )
                
                # Step 5: Reduce Phase - synthesize components
                self.check_cancelled()
                self.update_job(55, "Synthesizing architectural components")
                reduce_service = ReduceService(
                    provider=provider,
                    workspace_path=workspace_path,
                    log_fn=self.log,
                    progress_fn=self.update_job
                )
                component_specs = reduce_service.reduce_summaries(summaries)
                self.log_stage(
                    "synthesis",
                    "Component synthesis complete.",
                    components=len(component_specs),
                    summary_records=len(summaries),
                )
                
                # Step 6: Load manifests content for global context
                manifests_context_list = []
                manifest_paths = []
                for f_entry in allowed_files:
                    f_path_str = f_entry["path"]
                    f_path = repo_path / f_path_str
                    if f_path_str.endswith(("package.json", "cargo.toml", "pyproject.toml", "requirements.txt", "go.mod", "schema.prisma")):
                        try:
                            content = f_path.read_text(encoding="utf-8", errors="ignore")
                            manifests_context_list.append(f"File: {f_path_str}\n```\n{content}\n```")
                            manifest_paths.append(f_path_str)
                        except Exception:
                            pass
                manifests_content = "\n\n".join(manifests_context_list)
                self.log_stage(
                    "evidence",
                    "Collected manifest/config evidence for final generation.",
                    manifest_files=len(manifest_paths),
                    manifest_chars=len(manifests_content),
                )
                
                # Step 7: Incremental generation of final blueprint
                self.check_cancelled()
                self.update_job(64, "Generating rebuild blueprint sections")
                generator = IncrementalSpecGenerator(
                    provider=provider,
                    workspace_path=workspace_path,
                    log_fn=self.log,
                    progress_fn=self.update_job
                )
                file_tree_list = [f["path"] for f in allowed_files]
                blueprint_content = generator.generate_blueprint(
                    repo_url=repo_url,
                    repo_name=repo_name,
                    file_tree=file_tree_list,
                    manifests_content=manifests_content,
                    component_specs=component_specs
                )
                self.log_stage(
                    "assembly",
                    "Blueprint generation completed.",
                    output_chars=len(blueprint_content),
                    section_chunks="4 validated chunks",
                )
                
                # Prepend metadata card
                now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                metadata_header = (
                    f"> **Analysis Metadata**\n"
                    f"> - **Repository URL**: {repo_url}\n"
                    f"> - **Generated At**: {now_str}\n"
                    f"> - **LLM Provider**: `{provider_name}`\n"
                    f"> - **Model Used**: `{model_name}`\n"
                    f"> - **Analysis Strategy**: `Hierarchical (Map-Reduce)`\n\n"
                    f"---\n\n"
                )
                blueprint_content = metadata_header + blueprint_content
                
            else:
                self.log("Direct Strategy enabled.", "INFO")
                if (
                    is_local_provider_name(provider_name)
                    and (
                        resolved_max_output_tokens < LOCAL_DIRECT_MODE_MIN_OUTPUT_TOKENS
                        or resolved_chunk_size < LOCAL_DIRECT_MODE_MIN_CHUNK_SIZE
                    )
                ):
                    self.log(
                        "Local model capacity looks tight for direct generation. "
                        "Consider switching to Hierarchical Map-Reduce mode for larger repositories or longer blueprints.",
                        "WARNING",
                    )
                # Step 4: Extract configuration and readme data
                self.update_job(50, "Extracting configurations and Readmes")
                code_context = []
                
                # Add file tree
                file_tree = [f["path"] for f in files_list]
                tree_text = f"### Repository Directory Tree:\n" + "\n".join(file_tree[:300])
                if len(file_tree) > 300:
                    tree_text += f"\n... and {len(file_tree) - 300} more files."
                code_context.append(tree_text)
                
                current_context_len = len(tree_text)
    
                # Load important manifests & readme
                for f_entry in files_list:
                    f_path_str = f_entry["path"]
                    f_path = repo_path / f_path_str
                    
                    # Filter by file size
                    if f_entry["size_bytes"] > settings.max_file_size_kb * 1024:
                        continue
                        
                    if is_important_file(f_path, f_path_str):
                        try:
                            content = f_path.read_text(encoding="utf-8", errors="ignore")
                            # Redact secrets
                            redacted = redact_secrets(content)
                            file_context = f"### File: {f_path_str}\n```\n{redacted}\n```"
                            
                            # Enforce context chunk size limit (chars)
                            if current_context_len + len(file_context) + 2 > resolved_chunk_size:
                                self.log(f"Context chunk size limit ({resolved_chunk_size} chars) reached. Skipping remaining files.", "WARNING")
                                break
                                
                            code_context.append(file_context)
                            current_context_len += len(file_context) + 2
                            self.log(f"Included config context from: {f_path_str}")
                        except Exception as ex:
                            self.log(f"Failed to read important file {f_path_str}: {ex}", "WARNING")
    
                context_str = "\n\n".join(code_context)
                
                # Map Phase: LLM generation of segments
                self.update_job(70, "Drafting repository specification")
                self.log("Running primary LLM analysis...")
                
                # System prompt based on SKILL.md
                system_prompt = (
                    "You are an expert reverse-engineer and product architect. "
                    "Your task is to analyze the provided repository context (directory tree, manifest files, and configurations) "
                    "and generate a highly detailed, clean-room rebuild blueprint. "
                    "Strict clean-room rule: do not copy original source code or secret credentials. "
                    "Analyze and describe functional rules, API signatures, database layouts, and user journeys so "
                    "another coding agent can implement it from scratch."
                )
                
                prompt = (
                    f"Repository Name: {repo_name}\n"
                    f"Repository URL: {repo_url}\n\n"
                    f"Below is the repository inventory and configurations:\n\n"
                    f"{context_str}\n\n"
                    f"Based on the repository context above, write a detailed rebuild specification. "
                    f"Return a clean markdown document matching the standard 25 sections requested:\n"
                    f"1. Executive Summary\n"
                    f"2. Product Purpose and Scope\n"
                    f"3. Repository Evidence Summary\n"
                    f"4. Technology Stack\n"
                    f"5. Architecture Overview\n"
                    f"6. Low-Level Design\n"
                    f"7. Functional Requirements\n"
                    f"8. User Roles and Permissions\n"
                    f"9. User Journeys and Workflows\n"
                    f"10. UI/UX Specification\n"
                    f"11. API Specification\n"
                    f"12. Data Model and Database Design\n"
                    f"13. Business Rules and Validation Logic\n"
                    f"14. Integrations and External Services\n"
                    f"15. Security Specification\n"
                    f"16. Performance and Scalability Specification\n"
                    f"17. Reliability and Error Handling\n"
                    f"18. Configuration and Environment Variables\n"
                    f"19. File Storage and Generated Assets\n"
                    f"20. Testing Strategy\n"
                    f"21. Deployment and Operations\n"
                    f"22. Rebuild Implementation Plan\n"
                    f"23. Acceptance Criteria\n"
                    f"24. Risks, Gaps, Unknowns, and Assumptions\n"
                    f"25. Clean-Room Notes\n\n"
                    f"For each section, explain what was found, what can be inferred, and what the rebuild instructions should be. "
                    f"If any details (like a database schema or UI screen) are not explicit in the configuration files, make "
                    f"evidence-based inferences and mark them clearly as assumptions or recommendations."
                )
    
                blueprint_content = provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=settings.temperature,
                    max_tokens=resolved_max_output_tokens
                )
                
                # Prepend metadata card to the output
                now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                metadata_header = (
                    f"> **Analysis Metadata**\n"
                    f"> - **Repository URL**: {repo_url}\n"
                    f"> - **Generated At**: {now_str}\n"
                    f"> - **LLM Provider**: `{provider_name}`\n"
                    f"> - **Model Used**: `{model_name}`\n"
                    f"> - **Analysis Strategy**: `Direct (Single Prompt)`\n\n"
                    f"---\n\n"
                )
                blueprint_content = metadata_header + blueprint_content
            
            # Step 8: Save Outputs
            self.update_job(95, "Saving rebuild blueprint")
            output_md_name = f"{repo_name}_REBUILD_BLUEPRINT.md"
            repo_output_path = docs_dir / output_md_name
            repo_output_path.write_text(blueprint_content, encoding="utf-8")
            
            # Copy to local outputs folder
            local_output_path = self.get_available_output_path(output_md_name)
            shutil.copy(str(repo_output_path), str(local_output_path))
            
            # Copy inventory JSON to local outputs folder
            if 'inventory_json_path' in locals() and inventory_json_path.exists():
                local_inventory_path = OUTPUTS_DIR / f"{self.job_id}_inventory.json"
                shutil.copy(str(inventory_json_path), str(local_inventory_path))
            
            # Clean up cloned repo if configured
            if not settings.keep_cloned_repos:
                self.log_stage("cleanup", "Cleaning up cloned repository workspace...")
                shutil.rmtree(repo_path)
                
            self.update_job(100, "Analysis complete", "completed", output_path=str(local_output_path))
            self.log_stage("complete", "Rebuild blueprint saved successfully.", output=str(local_output_path))

        except Exception as e:
            err_msg = str(e)
            is_cancelled = "cancelled by the user" in err_msg
            
            if is_cancelled:
                self.log("Analysis aborted: Job was cancelled by the user", "WARNING")
                self.update_job(100, "Job cancelled by user", "cancelled")
            else:
                if "429" in err_msg or "rate limit" in err_msg.lower() or "rate-limit" in err_msg.lower():
                    err_msg = f"Rate Limit Exceeded (429): {err_msg}. Recommendation: Switch to a different provider/model in Settings, or add your own API key to bypass shared limits."
                elif "model_not_found" in err_msg or "does not exist or you do not have access to it" in err_msg or ("404" in err_msg and "OpenRouter" in err_msg):
                    err_msg = f"Model Not Found / Access Denied (404): {err_msg}. Recommendation: Verify your API key is correctly configured in Settings and has sufficient credits/funds. Alternatively, select a free model (e.g. ending in ':free' like 'meta-llama/llama-3-8b-instruct:free')."
                self.log(f"Analysis failed: {err_msg}", "ERROR")
                self.update_job(100, "Failed", "failed", error=err_msg)
                
            # Clean up workspace folder if cloning failed or job was cancelled
            if workspace_path and workspace_path.exists() and not settings.keep_cloned_repos:
                try:
                    shutil.rmtree(workspace_path)
                except Exception:
                    pass
            if is_cancelled:
                return
