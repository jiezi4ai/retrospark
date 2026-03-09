import json
from pathlib import Path
import pytest

from retrospark import config

@pytest.fixture
def mock_config_paths(tmp_path, mocker):
    """Mock the configuration paths to use a temporary directory."""
    config_dir = tmp_path / ".retrospark"
    config_file = config_dir / "config.json"
    brain_dir = config_dir / "brain"
    
    mocker.patch("retrospark.config.CONFIG_DIR", config_dir)
    mocker.patch("retrospark.config.CONFIG_FILE", config_file)
    mocker.patch("retrospark.config.DEFAULT_BRAIN_DIR", brain_dir)
    return config_dir, config_file, brain_dir

def test_load_empty_config(mock_config_paths):
    _, config_file, _ = mock_config_paths
    assert not config_file.exists()
    
    conf = config.load_config()
    assert conf == {}

def test_save_and_load_config(mock_config_paths):
    _, config_file, _ = mock_config_paths
    test_conf = {"brain_dir": "/tmp/test_brain", "remote_url": "git@github.com:test/repo.git"}
    
    config.save_config(test_conf)
    assert config_file.exists()
    
    loaded = config.load_config()
    assert loaded == test_conf

def test_get_brain_dir_default(mock_config_paths):
    _, _, expected_brain_dir = mock_config_paths
    
    brain_dir = config.get_brain_dir()
    assert brain_dir == expected_brain_dir

def test_get_brain_dir_custom(mock_config_paths):
    custom_dir = "/tmp/my_custom_brain"
    config.save_config({"brain_dir": custom_dir})
    
    brain_dir = config.get_brain_dir()
    assert brain_dir == Path(custom_dir)
