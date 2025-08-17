from pathlib import Path

from flask import Flask
from map import BASEMAP_OPTIONS, Config, TemplateManager, create_routes

# ==========================================================================================
# ==========================================================================================

# File:    app.py
# Date:    August 14, 2025
# Author:  Jonathan A. Webb
# Purpose: This file integrates all map application functions and classes into a single
#          application
# ==========================================================================================
# ==========================================================================================


def create_app(data_dir: Path) -> Flask:
    """Application factory function"""

    template_path = data_dir / "templates"
    static_path = data_dir / "assets"

    print(f"DEBUG: Flask template_folder: {template_path.resolve()}")  # Add this
    print(f"DEBUG: Flask static_folder: {static_path.resolve()}")  # Add this

    app = Flask(__name__, template_folder=template_path, static_folder=static_path)
    app.config.from_object(Config)

    # Create templates
    template_manager = TemplateManager(data_dir)
    template_manager.create_templates()

    # Register routes
    create_routes(app)

    return app


# ------------------------------------------------------------------------------------------


def main(data_dir: Path) -> None:
    """Main function to run the application"""
    app = create_app(data_dir)

    print("Starting Folium Web Application...")
    print(f"Open your browser and navigate to: http://{Config.HOST}:{Config.PORT}")
    print("Available basemaps:", list(BASEMAP_OPTIONS.keys()))

    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)


# ==========================================================================================
# ==========================================================================================


if __name__ == "__main__":
    # Import here to avoid circular imports
    input_dir = Path("../data/")
    main(input_dir)


# ==========================================================================================
# ==========================================================================================
# eof
