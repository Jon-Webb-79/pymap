import builtins
import copy
import json
from pathlib import Path

import pytest

from pymap.read_files import load_json_config, split_run_args

# ==========================================================================================
# ==========================================================================================
# File:    test.py
# Date:    August 16, 2025
# Author:  Jonathan A. Webb
# Purpose: This file contains unit tests for public functions in the read_files.py fiel

# ==========================================================================================
# ==========================================================================================
# Nominal test cases for load_json_config


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


# ------------------------------------------------------------------------------------------


def base_defaults():
    """Shared defaults used across tests."""
    return {
        "flask": {
            "template_folder": "data/templates",
            "static_folder": "data/assets",
            "nested": {"a": 1, "b": 2},
        },
        "flask_run": {"host": "127.0.0.1", "port": 5000, "debug": False},
    }


# ------------------------------------------------------------------------------------------


def test_invalid_json_raises_jsondecodeerror(tmp_path: Path):
    """Malformed JSON → json.JSONDecodeError is raised."""
    defaults = base_defaults()
    cfg = tmp_path / "flask_config.json"
    cfg.write_text("{ invalid json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_json_config(cfg, defaults)


# ------------------------------------------------------------------------------------------


def test_unreadable_file_raises_oserror(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Unreadable file (simulated) → OSError propagates."""
    defaults = base_defaults()
    cfg = tmp_path / "flask_config.json"
    write_json(cfg, {"flask_run": {"port": 7000}})

    # Monkeypatch Path.open to raise for this path
    def boom(self, *args, **kwargs):
        if self == cfg:
            raise OSError("Permission denied")
        return builtins.open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", boom, raising=True)

    with pytest.raises(OSError):
        load_json_config(cfg, defaults)


# ------------------------------------------------------------------------------------------


def test_defaults_immutability_on_success(tmp_path: Path):
    """Defaults remain unchanged (deep) after successful load+merge."""
    defaults = base_defaults()
    snapshot = copy.deepcopy(defaults)

    cfg = tmp_path / "flask_config.json"
    write_json(cfg, {"flask": {"nested": {"b": 99, "c": 3}}})

    result = load_json_config(cfg, defaults)

    # Result reflects merge…
    assert result["flask"]["nested"] == {"a": 1, "b": 99, "c": 3}
    # …but original defaults are intact
    assert defaults == snapshot
    # And not the same nested object (optional but nice to assert no in-place mutation)
    assert defaults["flask"]["nested"] is not result["flask"]["nested"]


# ------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "override_value",
    [False, 0, "", [], {}],
    ids=["false", "zero", "empty_str", "empty_list", "empty_dict"],
)
def test_override_falsy_values_replace_defaults(tmp_path: Path, override_value):
    """Falsy config values replace defaults (not dropped due to falsiness)."""
    defaults = base_defaults()
    cfg = tmp_path / "flask_config.json"

    # Override various places: a top-level run flag and a nested value
    file_cfg = {
        "flask_run": {"debug": override_value},
        "flask": {"nested": {"b": override_value}},
    }
    write_json(cfg, file_cfg)

    result = load_json_config(cfg, defaults)

    assert result["flask_run"]["debug"] == override_value
    assert result["flask"]["nested"]["b"] == override_value


# ------------------------------------------------------------------------------------------


def test_empty_override_object_returns_defaults(tmp_path: Path):
    """Empty object {} in file → result equals defaults (unchanged)."""
    defaults = base_defaults()
    snapshot = copy.deepcopy(defaults)

    cfg = tmp_path / "flask_config.json"
    write_json(cfg, {})

    result = load_json_config(cfg, defaults)
    assert result == defaults
    assert defaults == snapshot


# ------------------------------------------------------------------------------------------


def test_unknown_keys_pass_through(tmp_path: Path):
    """Unknown keys present in file are preserved in result."""
    defaults = base_defaults()
    cfg = tmp_path / "flask_config.json"
    file_cfg = {"new_section": {"x": 1}, "flask_run": {"host": "0.0.0.0"}}
    write_json(cfg, file_cfg)

    result = load_json_config(cfg, defaults)

    assert result["new_section"] == {"x": 1}
    assert result["flask_run"]["host"] == "0.0.0.0"
    # Defaults still present
    assert "template_folder" in result["flask"]


# ------------------------------------------------------------------------------------------


def test_unicode_handling_in_keys_and_values(tmp_path: Path):
    """Non-ASCII keys/values load and merge correctly with UTF-8."""
    defaults = base_defaults()
    cfg = tmp_path / "flask_config.json"

    file_cfg = {
        "flask": {
            "nested": {"b": "naïve café", "Δ": "delta"},
        },
        "flask_run": {"host": "127.0.0.1"},
        "секция": {"ключ": "значение"},  # Cyrillic
    }
    write_json(cfg, file_cfg)

    result = load_json_config(cfg, defaults)

    # Unicode preserved
    assert result["flask"]["nested"]["b"] == "naïve café"
    assert result["flask"]["nested"]["Δ"] == "delta"
    assert result["секция"]["ключ"] == "значение"


# ==========================================================================================
# ==========================================================================================
# Test split_run_args


def test_partitioning_known_vs_unknown_keys():
    """Known keys go to base; all others to extra."""
    run_cfg = {
        "host": "0.0.0.0",
        "port": 8000,
        "debug": True,
        "load_dotenv": False,
        "use_reloader": True,  # unknown → extra
        "threaded": False,  # unknown → extra
        "anything": "goes",  # unknown → extra
    }

    base, extra = split_run_args(run_cfg)

    assert base == {
        "host": "0.0.0.0",
        "port": 8000,
        "debug": True,
        "load_dotenv": False,
    }
    assert extra == {
        "use_reloader": True,
        "threaded": False,
        "anything": "goes",
    }


# ------------------------------------------------------------------------------------------


def test_drop_none_values():
    """Keys with value None appear in neither base nor extra."""
    run_cfg = {
        "host": None,
        "port": None,
        "debug": None,
        "load_dotenv": None,
        "use_reloader": None,
        "threaded": None,
    }

    base, extra = split_run_args(run_cfg)

    assert base == {}
    assert extra == {}


# ------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key,value",
    [
        ("port", 0),  # falsy int retained
        ("debug", False),  # falsy bool retained
        ("host", ""),  # empty string retained
    ],
    ids=["zero_port", "false_debug", "empty_host"],
)
def test_keep_falsy_but_valid_values(key, value):
    """Falsy-but-valid values (0, False, '') are retained, not dropped."""
    run_cfg = {
        key: value,
        "use_reloader": False,  # ensure extra path also keeps falsy
    }

    base, extra = split_run_args(run_cfg)

    if key in {"host", "port", "debug", "load_dotenv"}:
        assert key in base and base[key] == value
    else:
        assert key in extra and extra[key] == value

    assert "use_reloader" in extra and extra["use_reloader"] is False


# ------------------------------------------------------------------------------------------


def test_empty_input_returns_empty_base_and_extra():
    """Empty input dict → both base and extra are empty."""
    base, extra = split_run_args({})

    assert base == {}
    assert extra == {}


# ------------------------------------------------------------------------------------------


def test_input_immutability():
    """Input mapping is not mutated by split_run_args."""
    run_cfg = {
        "host": "127.0.0.1",
        "port": 5000,
        "debug": False,
        "use_reloader": True,
        "unknown": 123,
    }
    snapshot = copy.deepcopy(run_cfg)

    _base, _extra = split_run_args(run_cfg)

    assert run_cfg == snapshot


# ------------------------------------------------------------------------------------------


def test_base_whitelist_enforced():
    """Base contains only {host, port, debug, load_dotenv}; others must be in extra."""
    run_cfg = {
        "host": "0.0.0.0",
        "port": 8080,
        "debug": True,
        "load_dotenv": True,
        "use_reloader": True,  # should NOT leak into base
        "threaded": True,  # should NOT leak into base
    }

    base, extra = split_run_args(run_cfg)

    # Strict base whitelist
    assert set(base.keys()) <= {"host", "port", "debug", "load_dotenv"}
    assert "use_reloader" not in base and "threaded" not in base

    # Unknowns present in extra
    assert extra.get("use_reloader") is True
    assert extra.get("threaded") is True


# ------------------------------------------------------------------------------------------


def test_many_unknown_keys_route_to_extra():
    """Multiple arbitrary unknown keys route to extra intact (types preserved)."""
    run_cfg = {
        "debug": True,
        "alpha": [1, 2, 3],
        "beta": {"x": 1},
        "gamma": ("a", "b"),
        "delta": 0.0,
        "epsilon": None,  # should be dropped entirely
    }

    base, extra = split_run_args(run_cfg)

    assert base == {"debug": True}
    assert "epsilon" not in extra
    assert extra["alpha"] == [1, 2, 3]
    assert extra["beta"] == {"x": 1}
    assert extra["gamma"] == ("a", "b")
    assert extra["delta"] == 0.0


# ==========================================================================================
# ==========================================================================================
# eof
