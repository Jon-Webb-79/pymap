import json
from pathlib import Path
from typing import Any, Optional

from flask import Flask
from map import TemplateManager, create_routes

# ==========================================================================================
# ==========================================================================================

# File:    app.py
# Date:    August 14, 2025
# Author:  Jonathan A. Webb
# Purpose: This file integrates all map application functions and classes into a single
#          application
# ==========================================================================================
# ==========================================================================================
# Global Data


DEFAULTS: dict[str, Any] = {
    "flask_init": {
        "import_name": "__name__",
        "static_url_path": None,
        "static_folder": "static",
        "static_host": None,
        "host_matching": False,
        "subdomain_matching": False,
        "template_folder": "templates",
        "instance_path": None,
        "instance_relative_config": False,
        "root_path": None,
    },
    "flask_run": {
        "host": "127.0.0.1",
        "port": 5000,
        "debug": False,
        "load_dotenv": True,
        "use_reloader": None,
        "use_debugger": None,
        "use_evalex": True,
        "extra_files": [],
        "exclude_patterns": [],
        "reloader_type": "auto",
        "threaded": False,
        "processes": 1,
        "request_handler": None,
        "static_files": None,
        "passthrough_errors": False,
        "ssl_context": None,
        "certfile": None,
        "keyfile": None,
    },
}

# ==========================================================================================
# ==========================================================================================
# Support functions


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


def _load_json_config(config_path: Optional[Path]) -> dict[str, Any]:
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
        return DEFAULTS
    if not config_path.exists():
        print(f"WARNING: config file {config_path} not found. Using defaults.")
        return DEFAULTS
    with config_path.open("r", encoding="utf-8") as f:
        user_cfg = json.load(f)
    return _deep_update(DEFAULTS, user_cfg)


# ------------------------------------------------------------------------------------------


def _split_run_args(run_cfg: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
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


class MapConfigError(Exception):
    """Custom exception for invalid map configuration."""

    pass


# ------------------------------------------------------------------------------------------


def _load_map_config(config_path: Path) -> dict:
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


# ------------------------------------------------------------------------------------------


def create_app(
    data_dir: Path,
    flask_config_data: dict[str, Any],
    basemap_options: dict[str, str],
    attributes: dict[str, str],
    map_config: dict[str, float],
) -> Flask:
    """
    Application factory that builds and configures a Flask app instance.

    This function prepares a Flask application with:
      - Template and static folder paths resolved relative to ``data_dir``.
      - A :class:`TemplateManager` initialized and instructed to create any
        required template scaffolding.
      - Application routes registered via :func:`create_routes`.

    Args:
        data_dir: Base data directory for the application. Template and static
            directories are resolved relative to this path.
        flask_config_data: A mapping of keyword arguments to pass to the
            :class:`flask.Flask` constructor (typically the ``"flask_init"``
            section of the JSON config). Must contain ``"template_folder"`` and
            ``"static_folder"`` keys with relative paths.

    Returns:
        A fully constructed :class:`flask.Flask` application instance ready
        to be run or further configured.

    Side Effects:
        - Prints debug messages with the resolved template and static folder paths.
        - Creates template files via :class:`TemplateManager`.
        - Registers routes globally.

    Raises:
        KeyError: If required keys (e.g., ``"template_folder"`` or
            ``"static_folder"``) are missing in ``flask_config_data``.

    Examples:
        >>> app = create_app(Path("../data"), {"import_name": "__main__",
        ...     "template_folder": "templates", "static_folder": "assets"})
        >>> isinstance(app, Flask)
        True
    """
    flask_config_data["template_folder"] = data_dir / flask_config_data["template_folder"]
    flask_config_data["static_folder"] = data_dir / flask_config_data["static_folder"]

    print(f"DEBUG: Flask template_folder: {flask_config_data['template_folder'].resolve()}")
    print(f"DEBUG: Flask static_folder: {flask_config_data['static_folder'].resolve()}")

    app = Flask(**flask_config_data)

    # Create templates
    template_manager = TemplateManager(
        data_dir, flask_config_data["template_folder"], flask_config_data["static_folder"]
    )
    template_manager.create_templates()

    # Register routes
    create_routes(
        app,
        basemap_options,
        attributes,
        map_config,
    )

    return app


# ------------------------------------------------------------------------------------------


def main(data_dir: Path, config_file: str, basemap_file: str, config_dir: str = "config") -> None:
    """
    Entry point for running the Flask application.

    This function loads configuration from a JSON file, constructs the app
    via :func:`create_app`, and launches it using runtime parameters from the
    ``"flask_run"`` section of the config.

    Args:
        data_dir: Path to the application's data directory (the parent of
            ``config_dir``, ``templates``, and ``assets``).
        config_file: Name of the JSON configuration file to load (e.g.,
            ``"flask_config.json"``).
        basemap_file: Name of the JSON file containing basemap information to be loaded
        config_dir: Subdirectory of ``data_dir`` where config files are stored.
            Defaults to ``"config"``.

    Side Effects:
        - Prints startup messages, including host/port and available basemaps.
        - Calls :func:`flask.Flask.run`, which blocks until the server exits.

    Raises:
        json.JSONDecodeError: If the configuration file exists but contains
            invalid JSON.
        OSError: If the configuration file exists but cannot be opened/read.

    Notes:
        - ``_load_json_config`` merges the loaded file with defaults, so
          ``run_cfg["host"]`` and ``run_cfg["port"]`` are always defined.
        - This function does not return; it starts the WSGI dev server.

    Examples:
        >>> # From a script entry point
        >>> if __name__ == "__main__":
        ...     main(Path("../data"), "flask_config.json")
    """
    config_data = _load_json_config(data_dir / config_dir / config_file)
    basemap_data = _load_map_config(data_dir / config_dir / basemap_file)
    app = create_app(
        data_dir,
        config_data.get("flask_init", {}),
        basemap_data.get("basemap_options", {}),
        basemap_data.get("basemap_attributions", {}),
        basemap_data.get("default_map_config", {}),
    )

    run_cfg = config_data.get("flask_run", {})
    print("Starting Folium Web Application...")
    print(f'Open your browser and navigate to: http://{run_cfg["host"]}:{run_cfg["port"]}')
    print("Available basemaps:", list(basemap_data.get("basemap_options", {}).keys()))

    base_args, extra_args = _split_run_args(run_cfg)
    app.run(**base_args, **extra_args)


# ==========================================================================================
# ==========================================================================================


if __name__ == "__main__":
    # Import here to avoid circular imports
    input_dir = Path("../data/")
    main(input_dir, "flask_config.json", "basemaps.json")


# ==========================================================================================
# ==========================================================================================
# eof
