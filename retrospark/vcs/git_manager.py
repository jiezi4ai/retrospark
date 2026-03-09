import subprocess
from pathlib import Path

def init_repo(repo_dir: Path, remote_url: str = None) -> bool:
    """Initialize a git repository in the given directory."""
    if not repo_dir.exists():
        repo_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if already a git repo
    if (repo_dir / ".git").exists():
        if remote_url:
            _set_remote(repo_dir, remote_url)
        return True

    try:
        subprocess.run(["git", "init"], cwd=str(repo_dir), check=True, capture_output=True)
        if remote_url:
            _set_remote(repo_dir, remote_url)
        return True
    except subprocess.CalledProcessError:
        return False


def _set_remote(repo_dir: Path, remote_url: str) -> bool:
    """Set or update the origin remote URL."""
    try:
        # Check existing remote
        result = subprocess.run(["git", "remote"], cwd=str(repo_dir), check=True, capture_output=True, text=True)
        if "origin" in result.stdout:
            subprocess.run(["git", "remote", "set-url", "origin", remote_url], cwd=str(repo_dir), check=True)
        else:
            subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=str(repo_dir), check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def sync_repo(repo_dir: Path, commit_msg: str = "Auto-sync") -> dict:
    """Add all files, commit, and push."""
    if not (repo_dir / ".git").exists():
        return {"status": "error", "message": "Not a git repository."}

    try:
        # Add all
        subprocess.run(["git", "add", "."], cwd=str(repo_dir), check=True, capture_output=True)
        
        # Check if there are changes to commit
        status_res = subprocess.run(["git", "status", "--porcelain"], cwd=str(repo_dir), check=True, capture_output=True, text=True)
        if not status_res.stdout.strip():
            # Try to push anyway (might have unpushed commits)
            _push(repo_dir)
            return {"status": "success", "message": "No new changes to commit. Push attempted."}

        # Commit
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(repo_dir), check=True, capture_output=True)
        
        # Push
        pushed = _push(repo_dir)
        if pushed:
            return {"status": "success", "message": "Committed and pushed successfully."}
        else:
            return {"status": "warning", "message": "Committed locally, but push failed (check your remote/ssh keys)."}
            
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": f"Git operation failed: {e.stderr if e.stderr else str(e)}"}


def _push(repo_dir: Path) -> bool:
    try:
        # Find current branch
        branch_res = subprocess.run(["git", "branch", "--show-current"], cwd=str(repo_dir), check=True, capture_output=True, text=True)
        branch = branch_res.stdout.strip() or "main"
        
        subprocess.run(["git", "push", "-u", "origin", branch], cwd=str(repo_dir), check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False
