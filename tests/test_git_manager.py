import pytest
from pathlib import Path
import subprocess
from retrospark.vcs import git_manager

def test_init_repo_success(tmp_path):
    repo_dir = tmp_path / "brain"
    
    # Init new repo
    success = git_manager.init_repo(repo_dir)
    assert success is True
    assert (repo_dir / ".git").exists()
    
    # Init again should be a no-op but return True
    success2 = git_manager.init_repo(repo_dir)
    assert success2 is True

def test_sync_repo_no_repo(tmp_path):
    repo_dir = tmp_path / "not_a_repo"
    
    res = git_manager.sync_repo(repo_dir)
    assert res["status"] == "error"
    assert "Not a git repository" in res["message"]

def test_sync_repo_no_changes(tmp_path):
    repo_dir = tmp_path / "test_repo"
    git_manager.init_repo(repo_dir)
    
    # Empty repo, no commits yet, sync shouldn't crash
    res = git_manager.sync_repo(repo_dir)
    assert res["status"] == "success"
    assert "No new changes" in res["message"]

def test_sync_repo_with_changes(tmp_path, mocker):
    repo_dir = tmp_path / "test_repo"
    git_manager.init_repo(repo_dir)
    
    # Add a file
    test_file = repo_dir / "test.md"
    test_file.write_text("Hello World!")
    
    # Mock push to always return True (we don't want to actually push in tests)
    mocker.patch("retrospark.vcs.git_manager._push", return_value=True)
    
    res = git_manager.sync_repo(repo_dir)
    assert res["status"] == "success"
    assert "Committed and pushed successfully" in res["message"]
    
    # Verify the commit exists
    log = subprocess.run(["git", "log", "-1", "--oneline"], cwd=str(repo_dir), capture_output=True, text=True)
    assert "Auto-sync" in log.stdout
