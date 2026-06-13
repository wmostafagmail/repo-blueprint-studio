import subprocess
import shutil
from pathlib import Path
from urllib.parse import urlparse
from backend.app.utils.url_validation import is_safe_github_url

class GitService:
    @staticmethod
    def clone_repository(
        repo_url: str, 
        workspace_dir: Path, 
        github_token: str = None,
        branch: str = None
    ) -> Path:
        """
        Clones a GitHub repository to the workspace directory.
        Injects github_token if provided for private repository access.
        """
        if not is_safe_github_url(repo_url):
            raise ValueError("Unsafe or invalid repository URL")
            
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine repository name
        from backend.app.utils.repo_name import repo_name_from_url
        repo_name = repo_name_from_url(repo_url)
        repo_path = workspace_dir / repo_name
        
        # Clean target if it exists
        if repo_path.exists():
            shutil.rmtree(repo_path)
            
        # Construct git clone command
        clone_url = repo_url
        if github_token:
            token = github_token.strip()
            parsed = urlparse(repo_url)
            # Inject token: https://<token>@github.com/org/repo
            clone_url = f"https://{token}@{parsed.netloc}{parsed.path}"
            
        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd += ["--branch", branch]
        cmd += [clone_url, str(repo_path)]
        
        try:
            # Run git clone synchronously, but capture stderr to parse/sanitize
            res = subprocess.run(
                cmd,
                text=True,
                capture_output=True,
                timeout=180.0
            )
            
            if res.returncode != 0:
                # Sanitize error message to hide token
                err_msg = res.stderr
                if github_token:
                    err_msg = err_msg.replace(github_token, "********")
                raise Exception(f"Git clone failed: {err_msg}")
                
            return repo_path.resolve()
        except subprocess.TimeoutExpired:
            raise Exception("Git clone timed out after 3 minutes")
        except Exception as e:
            err_msg = str(e)
            if github_token:
                err_msg = err_msg.replace(github_token, "********")
            raise Exception(err_msg)
