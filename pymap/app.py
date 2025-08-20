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


def create_app(data_dir: Path, flask_config_data: dict[str, Any]) -> Flask:
    """Application factory function"""

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
    create_routes(app)

    return app


# ------------------------------------------------------------------------------------------


def main(data_dir: Path, config_file: str, config_dir: str = "config") -> None:
    """Main function to run the application"""
    json_data = _load_json_config(data_dir / config_dir / config_file)

    app = create_app(data_dir, json_data.get("flask_init", {}))

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
    main(input_dir, "flask_config.json")


# ==========================================================================================
# ==========================================================================================
# eof
