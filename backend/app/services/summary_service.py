import json
import logging
from time import monotonic
from pathlib import Path
from typing import List, Dict, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx

from app.services.prompt_builders import (
    SUMMARY_SYSTEM_PROMPT,
    build_file_summary_prompt,
)

logger = logging.getLogger(__name__)

MAP_PROGRESS_START = 35
MAP_PROGRESS_END = 73

def should_preserve_raw(path_str: str) -> bool:
    """
    Decides whether a file should be preserved in its raw form rather than summarized.
    Crucial for schemas, router configs, database models, and manifests.
    """
    path_lower = path_str.lower()
    
    # Manifest / Configuration patterns
    if path_lower.endswith((
        "package.json", "cargo.toml", "pyproject.toml", 
        "requirements.txt", "go.mod", "dockerfile", 
        "docker-compose.yml", "schema.prisma"
    )):
        return True
        
    # Schema & DB Model patterns
    if "schema" in path_lower or "models" in path_lower:
        if path_lower.endswith((".py", ".ts", ".js", ".go", ".rs", ".sql", ".graphql")):
            return True
            
    # Router / Routing / Route patterns
    if "route" in path_lower or "router" in path_lower or "endpoints" in path_lower:
        if path_lower.endswith((".py", ".ts", ".js", ".go", ".rs", ".java", ".cs")):
            return True
            
    return False

class SummaryMapService:
    def __init__(
        self, 
        provider, 
        workspace_path: Path, 
        log_fn: Callable[[str, str], None], 
        progress_fn: Callable[[int, str], None]
    ):
        self.provider = provider
        self.workspace_path = workspace_path
        self.log = log_fn
        self.progress = progress_fn
        self.summaries_dir = workspace_path / "summaries"
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        self._last_progress_emit_at = 0.0
        self._last_progress_value = -1
        self._last_progress_message = ""

    def _emit_progress(self, progress_value: int, message: str, *, force: bool = False):
        now = monotonic()
        if not force:
            if (
                progress_value == self._last_progress_value
                and message == self._last_progress_message
                and (now - self._last_progress_emit_at) < 1.5
            ):
                return
            if (
                progress_value == self._last_progress_value
                and (now - self._last_progress_emit_at) < 1.5
            ):
                return
        self.progress(progress_value, message)
        self._last_progress_emit_at = now
        self._last_progress_value = progress_value
        self._last_progress_message = message

    def summarize_file(self, file_path: str, repo_path: Path) -> Dict:
        """
        Summarizes a single file. If it's a critical configuration or schema,
        preserves the raw code. Otherwise, calls the LLM to get a structured summary.
        """
        full_path = repo_path / file_path
        
        # Guard if file doesn't exist
        if not full_path.exists() or not full_path.is_file():
            return {"path": file_path, "type": "empty", "content": "File not found"}

        # Read content
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return {"path": file_path, "type": "empty", "content": f"Failed to read: {str(e)}"}

        if not content.strip():
            return {"path": file_path, "type": "empty", "content": "Empty file"}

        # Case A: Preserve raw schemas/routers/manifests
        if should_preserve_raw(file_path):
            summary_data = {
                "path": file_path,
                "type": "raw",
                "content": content
            }
            self._save_summary(file_path, summary_data)
            return summary_data

        # Case B: LLM Summarization
        system_prompt = SUMMARY_SYSTEM_PROMPT
        prompt = build_file_summary_prompt(file_path, content)

        try:
            resp = self.provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=500
            )
            # Try parsing response as JSON
            try:
                # Clean markdown wrapper if LLM returned it
                cleaned_resp = resp.strip()
                if cleaned_resp.startswith("```"):
                    cleaned_resp = cleaned_resp.split("\n", 1)[1]
                if cleaned_resp.endswith("```"):
                    cleaned_resp = cleaned_resp.rsplit("\n", 1)[0]
                if cleaned_resp.startswith("json"):
                    cleaned_resp = cleaned_resp.split("json", 1)[1]
                
                parsed_json = json.loads(cleaned_resp.strip())
                summary_data = {
                    "path": file_path,
                    "type": "summary",
                    "responsibilities": parsed_json.get("responsibilities", []),
                    "exports": parsed_json.get("exports", []),
                    "dependencies": parsed_json.get("dependencies", []),
                    "evidence": parsed_json.get("evidence", [])
                }
            except Exception:
                # Fallback to plain text if JSON parse failed
                summary_data = {
                    "path": file_path,
                    "type": "text",
                    "content": resp.strip()
                }
        except Exception as e:
            self.log(f"LLM Summarization failed for {file_path}: {str(e)}", "WARNING")
            summary_data = {
                "path": file_path,
                "type": "error",
                "content": f"Summarization failed: {str(e)}"
            }

        self._save_summary(file_path, summary_data)
        return summary_data

    def _save_summary(self, rel_path: str, data: Dict):
        """Saves a summary dict in a path-preserving way inside summaries_dir."""
        target_file = self.summaries_dir / f"{rel_path}.json"
        target_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            target_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save summary for {rel_path}: {str(e)}")

    def map_codebase(self, files_list: List[Dict], repo_path: Path, batch_size: int = 5) -> List[Dict]:
        """
        Coordinates the mapping phase, executing requests in parallel.
        """
        self.log(f"Starting Map Phase for {len(files_list)} files with parallel batch size = {batch_size}...", "INFO")
        
        results = []
        completed = 0
        total = len(files_list)

        if total == 0:
            self._emit_progress(MAP_PROGRESS_END, "No candidate files required summarization", force=True)
            return results
        
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = {
                executor.submit(self.summarize_file, file_info["path"], repo_path): file_info["path"]
                for file_info in files_list
            }
            
            for future in as_completed(futures):
                path = futures[future]
                try:
                    res = future.result()
                    results.append(res)
                except Exception as e:
                    self.log(f"Unhandled mapping thread error on {path}: {str(e)}", "ERROR")
                    results.append({"path": path, "type": "error", "content": str(e)})
                    
                completed += 1
                pct = int(
                    MAP_PROGRESS_START
                    + (completed / total) * (MAP_PROGRESS_END - MAP_PROGRESS_START)
                )
                progress_message = f"Summarizing files ({completed}/{total}) - {path}"
                self._emit_progress(pct, progress_message, force=(completed == total))

                if completed <= 3 or completed % max(1, total // 20) == 0 or completed == total:
                    self.log(
                        f"[map] Summarized {completed}/{total} files ({int(completed / total * 100)}% of map phase). "
                        f"Latest: {path}",
                        "INFO",
                    )
                    
        return results
