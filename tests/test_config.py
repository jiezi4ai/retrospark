import json
from pathlib import Path
import pytest

from retrospark import config

@pytest.fixture
def mock_config_paths(tmp_path, mocker):
    """Mock the configuration paths to use a temporary directory."""
    project_root = tmp_path
    config_file = project_root / "config.yaml"
    interaction_dir = project_root / ".retrospark" / "interaction"
    
    mocker.patch("retrospark.config.PROJECT_ROOT", project_root)
    mocker.patch("retrospark.config.ROOT_CONFIG_FILE", config_file)
    mocker.patch("retrospark.config.DEFAULT_INTERACTION_DIR", interaction_dir)
    return project_root, config_file, interaction_dir

def test_load_empty_config(mock_config_paths):
    _, config_file, _ = mock_config_paths
    assert not config_file.exists()
    
    conf = config.load_config()
    assert conf == {}

def test_save_and_load_config(mock_config_paths):
    _, config_file, _ = mock_config_paths
    test_conf = {
        "github_repo": {"remote_url": "https://github.com/test/repo.git"}
    }
    
    config.save_config(test_conf)
    assert config_file.exists()
    
    loaded = config.load_config()
    assert loaded == test_conf

def test_get_interaction_dir_default(mock_config_paths):
    _, _, expected_dir = mock_config_paths
    
    interaction_dir = config.get_interaction_dir()
    assert interaction_dir == expected_dir

