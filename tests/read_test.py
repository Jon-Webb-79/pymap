import copy
import json
from pathlib import Path

from pymap.read_files import load_json_config

# ==========================================================================================
# ==========================================================================================
# File:    test.py
# Date:    August 16, 2025
# Author:  Jonathan A. Webb
# Purpose: This file contains unit tests for public functions in the read_files.py fiel

# ==========================================================================================
# ==========================================================================================


def write_json(path: Path, data: dict) -> None:
    """Helper to write a dictionary to a file as JSON with UTF-8 encoding."""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ------------------------------------------------------------------------------------------


def test_load_json_config_none_path_returns_defaults():
    """Verify that passing None as config_path returns the defaults unchanged."""
    defaults = {
        "flask": {
            "template_folder": "data/templates",
            "static_folder": "data/assets",
        },
        "flask_run": {"host": "127.0.0.1", "port": 5000, "debug": False},
    }

    result = load_json_config(None, defaults)

    # Nominal behavior: returns defaults as-is
    assert result is defaults
    assert result == defaults


# ------------------------------------------------------------------------------------------


def test_load_json_config_shallow_override_merges(tmp_path: Path):
    """Verify shallow merge: file overrides top-level keys and adds unknown keys."""
    defaults = {
        "flask": {
            "template_folder": "data/templates",
            "static_folder": "data/assets",
        },
        "flask_run": {"host": "127.0.0.1", "port": 5000, "debug": False},
    }
    defaults_snapshot = copy.deepcopy(defaults)

    # File overrides a top-level key and adds an unknown key
    cfg_file = tmp_path / "flask_config.json"
    file_cfg = {
        "flask_run": {"host": "0.0.0.0", "debug": True},
        "unknown_top": 123,
    }
    write_json(cfg_file, file_cfg)

    result = load_json_config(cfg_file, defaults)

    # Shallow overrides apply, unknown keys pass through
    assert result["flask_run"]["host"] == "0.0.0.0"
    assert result["flask_run"]["port"] == 5000
    assert result["flask_run"]["debug"] is True
    assert result["unknown_top"] == 123

    # Defaults are not mutated
    assert defaults == defaults_snapshot


# ------------------------------------------------------------------------------------------


def test_load_json_config_deep_override_merges(tmp_path: Path):
    """Verify deep merge: nested dict keys are merged and new keys added."""
    defaults = {
        "flask": {
            "template_folder": "data/templates",
            "static_folder": "data/assets",
            "nested": {"a": 1, "b": 2},
        },
        "flask_run": {"host": "127.0.0.1", "port": 5000, "debug": False},
    }
    defaults_snapshot = copy.deepcopy(defaults)

    # File overrides nested dict and adds a new nested key
    cfg_file = tmp_path / "flask_config.json"
    file_cfg = {
        "flask": {
            "static_folder": "data/static",
            "nested": {"b": 20, "c": 30},
        }
    }
    write_json(cfg_file, file_cfg)

    result = load_json_config(cfg_file, defaults)

    # Deep merge: existing nested keys preserved unless overridden
    assert result["flask"]["template_folder"] == "data/templates"
    assert result["flask"]["static_folder"] == "data/static"
    assert result["flask"]["nested"] == {"a": 1, "b": 20, "c": 30}

    # Unrelated sections preserved
    assert result["flask_run"] == {"host": "127.0.0.1", "port": 5000, "debug": False}

    # Defaults are not mutated
    assert defaults == defaults_snapshot


# ==========================================================================================
# ==========================================================================================
# eof
