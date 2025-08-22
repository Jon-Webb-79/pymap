import json
from pathlib import Path
from typing import Any, Optional

# ==========================================================================================
# ==========================================================================================

# File:    read_files.py
# Date:    August 21, 2025
# Author:  Jonathan A. Webb
# Purpose: This file contains functions used to read files specific to the pymap application
# ==========================================================================================
# ==========================================================================================
# Read Flask Config File


def _deep_update(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively merge two dictionaries without mutating the inputs.

    For each key in ``override``:
      - If both ``base[key]`` and ``override[key]`` are dictionaries, merge them
        recursively.
      - Otherwise, ``override[key]`` replaces ``base[key]`` (or is added if missing).

    This is a *deep* version of ``{**base, **override}`` with recursive handling
    of nested mappings.

    Args:
        base: The original mapping to be used as the merge base.
        override: The mapping whose values take precedence over ``base``.

    Returns:
        A new dictionary containing the merged result. Neither ``base`` nor
        ``override`` are mutated.

    Notes:
        - Only nested ``dict`` values are merged recursively. Sequences (lists/tuples),
          sets, and other containers are *replaced*.
        - If ``override`` is falsy (e.g., ``None`` or ``{}``), a shallow copy of
          ``base`` is returned.

    Examples:
        >>> _deep_update({"a": 1, "b": {"x": 1}}, {"b": {"y": 2}, "c": 3})
        {'a': 1, 'b': {'x': 1, 'y': 2}, 'c': 3}

    Complexity:
        O(n) over the number of keys visited (including nested dicts).
    """
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_update(out[k], v)
        else:
            out[k] = v
    return out


# ------------------------------------------------------------------------------------------


def load_json_config(config_path: Optional[Path], defaults: dict[str, Any]) -> dict[str, Any]:
    """
    Load a JSON configuration file and merge it over module defaults.

    If ``config_path`` is ``None`` or does not exist, the module-level ``DEFAULTS``
    are returned. When a file exists and is valid JSON, its top-level keys are
    merged over ``DEFAULTS`` using :func:`_deep_update`.

    Args:
        config_path: Filesystem path to a JSON config file, or ``None`` to
            bypass file loading and return ``DEFAULTS``.

    Returns:
        A dictionary representing the effective configuration after merging the
        file contents (if any) over ``DEFAULTS``.

    Raises:
        json.JSONDecodeError: If ``config_path`` exists but contains invalid JSON.
        OSError: If the file exists but cannot be opened/read.

    Notes:
        - This function prints a WARNING and falls back to ``DEFAULTS`` when
          ``config_path`` is provided but the file is missing.
        - Keys present in the file that are not in ``DEFAULTS`` are kept and
          included in the resulting mapping (they will be passed through).

    Examples:
        >>> from pathlib import Path
        >>> cfg = _load_json_config(None)   # returns DEFAULTS
        >>> isinstance(cfg, dict)
        True
    """
    if not config_path:
        return defaults
    if not config_path.exists():
        print(f"WARNING: config file {config_path} not found. Using defaults.")
        return defaults
    with config_path.open("r", encoding="utf-8") as f:
        user_cfg = json.load(f)
    return _deep_update(defaults, user_cfg)


# ------------------------------------------------------------------------------------------


def split_run_args(run_cfg: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Partition Flask's ``app.run`` arguments from all other run options.

    The return value is a pair ``(base, extra)``:
      - ``base`` contains only the kwargs that ``Flask.run`` handles directly:
        ``{"host", "port", "debug", "load_dotenv"}``.
      - ``extra`` contains every *other* non-None key/value pair from ``run_cfg``.
        These are intended to be forwarded to Werkzeug's ``run_simple`` (or ignored
        by Flask if unsupported).

    Keys whose values are ``None`` are dropped from both outputs.

    Args:
        run_cfg: A mapping of runtime options (typically the ``"flask_run"`` section).

    Returns:
        A 2-tuple ``(base, extra)`` where:
          - ``base`` is safe to pass directly to ``app.run(**base)``.
          - ``extra`` is intended for forwarding as ``app.run(**extra)`` and may
            include Werkzeug-specific flags.

    Examples:
        >>> base, extra = _split_run_args({
        ...     "host": "0.0.0.0", "port": 8000, "debug": True,
        ...     "use_reloader": True, "threaded": False, "unknown": 123, "none_val": None
        ... })
        >>> base == {"host": "0.0.0.0", "port": 8000, "debug": True}
        True
        >>> "use_reloader" in extra and "threaded" in extra and "unknown" in extra
        True
        >>> "none_val" in base or "none_val" in extra
        False
    """
    # Keys that Flask.run knows directly
    flask_keys = {"host", "port", "debug", "load_dotenv"}
    base = {k: v for k, v in run_cfg.items() if k in flask_keys and v is not None}
    extra = {k: v for k, v in run_cfg.items() if k not in flask_keys and v is not None}
    return base, extra


# ==========================================================================================
# ==========================================================================================
# Rad Map Config File


class MapConfigError(Exception):
    """Custom exception for invalid map configuration."""

    pass


# ------------------------------------------------------------------------------------------


def load_map_config(config_path: Path) -> dict:
    """
    Load and validate the map configuration JSON file.

    Parameters
    ----------
    config_path : Path
        Path to the JSON configuration file.

    Returns
    -------
    dict
        The validated configuration dictionary.

    Raises
    ------
    MapConfigError
        If validation fails.
    """
    # Load JSON
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    basemap_options = config.get("basemap_options", {})
    basemap_attributions = config.get("basemap_attributions", {})
    default_config = config.get("default_map_config", {})

    # --- Validation rules ---
    # 1. Each basemap must have an attribution
    missing_attributions = [b for b in basemap_options if b not in basemap_attributions]
    if missing_attributions:
        raise MapConfigError(f"Missing attributions for basemaps: {missing_attributions}")

    # 2. Default basemap must exist in basemap_options
    default_basemap = default_config.get("basemap")
    if default_basemap not in basemap_options:
        raise MapConfigError(f"Default basemap '{default_basemap}' not found in basemap_options")

    return config


# ==========================================================================================
# ==========================================================================================
# eof
