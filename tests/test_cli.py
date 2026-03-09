import json
from click.testing import CliRunner
import pytest
from retrospark.cli import main

@pytest.fixture
def runner():
    return CliRunner()

def test_cli_help(runner):
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "RetroSpark (retrospark)" in result.output
    assert "init" in result.output
    assert "sync" in result.output

def test_cli_init(runner, mocker, tmp_path):
    # Mock config paths and git_manager
    mocker.patch("retrospark.cli.get_interaction_dir", return_value=tmp_path / "brain")
    mocker.patch("retrospark.cli.init_repo", return_value=True)
    mocker.patch("retrospark.cli.load_config", return_value={})
    mocker.patch("retrospark.cli.save_config", return_value=True)

    result = runner.invoke(main, ["init", "--remote-url", "git@github.com:test.git"])
    assert result.exit_code == 0
    
    # Check if the output is valid JSON
    output_json = json.loads(result.output)
    assert output_json["status"] == "success"
    assert output_json["remote_url"].startswith("git@github.com:test.")
    assert "next_steps" in output_json

def test_cli_sync_kimi(runner, mocker, tmp_path):
    brain_dir = tmp_path / "brain"
    brain_dir.mkdir(parents=True)
    mocker.patch("retrospark.cli.get_interaction_dir", return_value=brain_dir)
    
    # Mock Parser
    mocker.patch("retrospark.cli.discover_projects", return_value=[{"dir_name": "proj1", "source": "kimi"}])
    mocker.patch("retrospark.cli.parse_project_sessions", return_value=[])
    
    # Mock Git Sync
    mocker.patch("retrospark.cli.sync_repo", return_value={"status": "success", "message": "Pushed"})
    
    result = runner.invoke(main, ["sync", "--source", "kimi", "--json"])
    assert result.exit_code == 0
    
    output_json = json.loads(result.output)
    assert output_json["status"] == "success"

def test_cli_sync_no_init(runner, mocker, tmp_path):
    # If the user hasn't run init, brain_dir won't exist
    mocker.patch("retrospark.cli.get_interaction_dir", return_value=tmp_path / "nonexistent")
    
    result = runner.invoke(main, ["sync", "--source", "claude", "--json"])
    assert result.exit_code == 0
    
    output_json = json.loads(result.output)
    assert output_json["status"] == "error"
    assert "interaction directory not initialized" in output_json["message"].lower()

def test_cli_sync_success(runner, mocker, tmp_path):
    brain_dir = tmp_path / "brain"
    brain_dir.mkdir(parents=True)
    mocker.patch("retrospark.cli.get_interaction_dir", return_value=brain_dir)
    
    # Mock Parser
    mock_sessions = [
        {"session_id": "1", "project": "proj1", "messages": [], "stats": {}}
    ]
    mocker.patch("retrospark.cli.discover_projects", return_value=[{"dir_name": "proj1", "source": "claude"}])
    mocker.patch("retrospark.cli.parse_project_sessions", return_value=mock_sessions)
    
    # Mock Git Sync
    mocker.patch("retrospark.cli.sync_repo", return_value={"status": "success", "message": "Pushed"})
    
    result = runner.invoke(main, ["sync", "--source", "claude", "--json"])
    assert result.exit_code == 0
    
    output_json = json.loads(result.output)
    assert output_json["status"] == "success"
    assert output_json["synced_sessions"] == 1
    assert output_json["git_status"]["status"] == "success"
