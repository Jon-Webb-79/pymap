import json
from pathlib import Path
from typing import Any, Optional

from flask import Flask
from map import BASEMAP_OPTIONS, TemplateManager, create_routes

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
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_update(out[k], v)
        else:
            out[k] = v
    return out


# ------------------------------------------------------------------------------------------

# def _coerce_path(maybe_path: Optional[str], data_dir: Path) -> Optional[Path]:
#     if maybe_path is None:
#         return None
#     p = Path(maybe_path)
#     return p if p.is_absolute() else (data_dir / p)
#
# # ------------------------------------------------------------------------------------------
#
# def _resolve_import_name(value: Optional[str], module_dunder_name: str) -> str:
#     # If JSON has "__name__", replace with the caller's __name__
#     # This keeps your app import-safe and script-safe.
#     if not value or value == "__name__":
#         return module_dunder_name
#     return value

# ------------------------------------------------------------------------------------------


def _load_json_config(config_path: Optional[Path]) -> dict[str, Any]:
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
    """Return (flask_run_known, werkzeug_extra) with None removed."""
    # Keys that Flask.run knows directly
    flask_keys = {"host", "port", "debug", "load_dotenv"}
    base = {k: v for k, v in run_cfg.items() if k in flask_keys and v is not None}
    extra = {k: v for k, v in run_cfg.items() if k not in flask_keys and v is not None}
    return base, extra


# ------------------------------------------------------------------------------------------


def create_app(data_dir: Path, template_dir: str, static_dir: str) -> Flask:
    """Application factory function"""

    template_path = data_dir / template_dir
    static_path = data_dir / static_dir

    print(f"DEBUG: Flask template_folder: {template_path.resolve()}")  # Add this
    print(f"DEBUG: Flask static_folder: {static_path.resolve()}")  # Add this

    app = Flask(__name__, template_folder=template_path, static_folder=static_path)
    # app.config.from_object(Config)

    # Create templates
    template_manager = TemplateManager(data_dir, template_dir, static_dir)
    template_manager.create_templates()

    # Register routes
    create_routes(app)

    return app


# ------------------------------------------------------------------------------------------


def main(data_dir: Path) -> None:
    """Main function to run the application"""
    app = create_app(data_dir, "templates", "assets")

    json_data = _load_json_config(data_dir / "config" / "flask_config.json")
    run_cfg = json_data.get("flask_run", {})
    print("Starting Folium Web Application...")
    print(f'Open your browser and navigate to: http://{run_cfg["host"]}:{run_cfg["port"]}')
    print("Available basemaps:", list(BASEMAP_OPTIONS.keys()))

    base_args, extra_args = _split_run_args(run_cfg)
    app.run(**base_args, **extra_args)


# ==========================================================================================
# ==========================================================================================


if __name__ == "__main__":
    # Import here to avoid circular imports
    input_dir = Path("../data/")
    main(input_dir)


# ==========================================================================================
# ==========================================================================================
# eof
