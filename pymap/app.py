from pathlib import Path
from typing import Any

from flask import Flask

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
    create_routes(app, basemap_options, attributes, map_config, boundary_dir)

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
