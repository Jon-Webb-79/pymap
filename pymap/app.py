from __future__ import annotations

import logging
import logging.config
import os
import time
import uuid
from pathlib import Path
from typing import Any

from flask import Flask, g, request

from pymap.map import TemplateManager, create_routes
from pymap.read_files import load_json_config, load_map_config, split_run_args

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


def create_app(
    data_dir: Path,
    boundary_dir: Path,
    flask_config_data: dict[str, Any],
    basemap_options: dict[str, str],
    attributes: dict[str, str],
    map_config: dict[str, float],
    logging_cfg: dict[str, Any] | None = None,  # <-- NEW (optional)
) -> Flask:
    """
    Application factory that builds and configures a Flask app instance.
    """

    # 0) Configure logging first (optional, if not done in main.py)
    if logging_cfg:
        # Create logs/ directory if using file handlers (best-effort)
        for handler in logging_cfg.get("handlers", {}).values():
            filename = handler.get("filename")
            if filename:
                os.makedirs(Path(filename).parent, exist_ok=True)
        logging.config.dictConfig(logging_cfg)

    logger = logging.getLogger("pymap.app")

    # 1) Resolve template/static paths relative to data_dir
    flask_config_data = dict(flask_config_data)  # avoid mutating caller’s dict
    flask_config_data["template_folder"] = data_dir / flask_config_data["template_folder"]
    flask_config_data["static_folder"] = data_dir / flask_config_data["static_folder"]

    logger.debug("Flask template_folder: %s", Path(flask_config_data["template_folder"]).resolve())
    logger.debug("Flask static_folder: %s", Path(flask_config_data["static_folder"]).resolve())

    # 2) Build app
    app = Flask(**flask_config_data)

    # If running behind a trusted proxy that sets X-Forwarded-* headers, enable this:
    # app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    # 3) Per-request correlation + timing
    @app.before_request
    def _start_request_context():
        g.request_id = uuid.uuid4().hex[:12]
        g.start_ts = time.perf_counter()
        # If you add auth later, also set:
        # g.user_id = current_user.id if current_user.is_authenticated else "-"

    @app.after_request
    def _access_log(response):
        try:
            dur_ms = int((time.perf_counter() - getattr(g, "start_ts", 0)) * 1000)
            logging.getLogger("pymap.access").info(
                "%s %s %s %s %dms",
                request.method,
                request.path,
                response.status_code,
                request.user_agent.string,
                dur_ms,
            )
        except Exception:
            logging.getLogger("pymap").exception("failed to write access log")
        return response

    # 4) Create templates (with error handling)
    try:
        template_manager = TemplateManager(
            data_dir,
            flask_config_data["template_folder"],
            flask_config_data["static_folder"],
        )
        template_manager.create_templates()
        logger.info("Templates ensured at %s", flask_config_data["template_folder"])
    except Exception:
        logger.exception("Template creation failed")

    # 5) Register routes
    create_routes(app, basemap_options, attributes, map_config, boundary_dir)
    logger.info("Routes registered; app ready")

    return app


# ------------------------------------------------------------------------------------------


def main(
    data_dir: Path, config_file: str, basemap_file: str, config_dir: str = "config", boundary_dir="boundary"
) -> None:
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
    config_data = load_json_config(data_dir / config_dir / config_file, DEFAULTS)
    basemap_data = load_map_config(data_dir / config_dir / basemap_file)
    app = create_app(
        data_dir,
        data_dir / boundary_dir,
        config_data.get("flask_init", {}),
        basemap_data.get("basemap_options", {}),
        basemap_data.get("basemap_attributions", {}),
        basemap_data.get("default_map_config", {}),
        config_data.get("logging", {}),
    )

    run_cfg = config_data.get("flask_run", {})
    print("Starting Folium Web Application...")
    print(f'Open your browser and navigate to: http://{run_cfg["host"]}:{run_cfg["port"]}')
    print("Available basemaps:", list(basemap_data.get("basemap_options", {}).keys()))

    base_args, extra_args = split_run_args(run_cfg)
    app.run(**base_args, **extra_args)


# ==========================================================================================
# ==========================================================================================
# eof
