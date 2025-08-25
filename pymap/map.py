from pathlib import Path
from typing import Optional, Union

import folium
from flask import Flask, Response, jsonify, render_template, request

from pymap.layers import BoundaryManager

# ==========================================================================================
# ==========================================================================================

# File:    map.py
# Date:    August 16, 2025
# Purpose: This file contains classes and functions that create the maps wich data
#          is overlaid on
# ==========================================================================================
# ==========================================================================================

# Sample markers data
SAMPLE_MARKERS = [
    {
        "lat": 39.8283,
        "lon": -98.5795,
        "popup": "Center of USA",
        "tooltip": "Click for more info",
    },
    {"lat": 40.7128, "lon": -74.0060, "popup": "New York City", "tooltip": "NYC"},
    {"lat": 34.0522, "lon": -118.2437, "popup": "Los Angeles", "tooltip": "LA"},
]


# ==========================================================================================
# ==========================================================================================


class MapService:
    """Service class for creating and managing Folium maps with predefined basemaps."""

    def __init__(
        self,
        basemap_options: dict[str, str],
        attributions: dict[str, str],
        default_config: dict[str, float],
        boundary_dir: Path,
    ) -> None:
        """
        Initialize the map service with predefined configuration.

        Attributes:
            basemap_options (Dict[str, str]): Mapping of basemap names to tile URLs.
            attributions (Dict[str, str]): Mapping of basemap names to attribution text.
            default_config (Dict[str, Any]): Default map configuration including
                'basemap', 'lat', 'lon', and 'zoom'.
        """
        self.basemap_options = basemap_options
        self.attributions = attributions
        self.default_config = default_config
        self.boundary_dir = boundary_dir

    # ------------------------------------------------------------------------------------------

    def validate_basemap(self, basemap: Optional[str]) -> str:
        """
        Validate that a basemap name exists in the available options.

        Args:
            basemap: Name of the basemap to validate.

        Returns:
            The validated basemap name if it exists, otherwise the default basemap.
        """
        if basemap not in self.basemap_options:
            return self.default_config["basemap"]
        return basemap

    # ------------------------------------------------------------------------------------------

    def create_base_map(self, lat: float, lon: float, zoom: int) -> folium.Map:
        """
        Create a new Folium base map.

        Args:
            lat: Latitude for the initial map center.
            lon: Longitude for the initial map center.
            zoom: Initial zoom level.

        Returns:
            A Folium Map object centered at the given coordinates.
        """
        return folium.Map(location=[lat, lon], zoom_start=zoom, tiles=None)

    # ------------------------------------------------------------------------------------------

    def add_basemap_layer(self, map_obj: folium.Map, basemap_name: str, is_default: bool = False) -> None:
        """
        Add a basemap layer to an existing Folium map.

        Args:
            map_obj: The Folium Map to add the basemap to.
            basemap_name: The name of the basemap to add.
            is_default: Whether this basemap should be the default visible layer.

        Raises:
            ValueError: If the basemap name is not valid.
        """
        if basemap_name not in self.basemap_options:
            raise ValueError(f"Invalid basemap: {basemap_name}")

        folium.TileLayer(
            tiles=self.basemap_options[basemap_name],
            attr=self.attributions[basemap_name],
            name=basemap_name,
            overlay=False,
            control=True,
            show=is_default,
        ).add_to(map_obj)

    # ------------------------------------------------------------------------------------------

    def add_all_basemap_layers(self, map_obj: folium.Map, selected_basemap: str) -> None:
        """
        Add all basemap layers to the map, ensuring the selected one is default.

        Args:
            map_obj: The Folium Map to add basemap layers to.
            selected_basemap: The basemap to set as default.
        """
        # Add selected basemap first (will be default)
        self.add_basemap_layer(map_obj, selected_basemap, is_default=True)

        # Add other basemap options
        for basemap_name in self.basemap_options:
            if basemap_name != selected_basemap:
                self.add_basemap_layer(map_obj, basemap_name)

    # ------------------------------------------------------------------------------------------

    def add_sample_markers(self, map_obj: folium.Map) -> None:
        """
        Add sample markers to the map.

        Args:
            map_obj: The Folium Map to which markers should be added.
        """
        for marker_data in SAMPLE_MARKERS:
            folium.Marker(
                [marker_data["lat"], marker_data["lon"]],
                popup=marker_data["popup"],
                tooltip=marker_data["tooltip"],
            ).add_to(map_obj)

    # ------------------------------------------------------------------------------------------

    def create_map(
        self,
        basemap: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        zoom: Optional[int] = None,
        include_markers: Optional[bool] = True,
    ) -> folium.Map:
        """
        Construct a complete Folium map with basemaps, controls, and markers.

        Args:
            basemap: The basemap to use. Defaults to the configured default basemap.
            lat: Latitude for the map center. Defaults to the configured default.
            lon: Longitude for the map center. Defaults to the configured default.
            zoom: Initial zoom level. Defaults to the configured default.
            include_markers: Whether to add sample markers.

        Returns:
            A fully constructed Folium Map with basemaps, controls, and optional markers.
        """
        # Use defaults if parameters not provided
        basemap = basemap or self.default_config["basemap"]
        lat = lat or self.default_config["lat"]
        lon = lon or self.default_config["lon"]
        zoom = zoom or self.default_config["zoom"]

        # Validate basemap
        basemap = self.validate_basemap(basemap)

        # Create base map
        map_obj = self.create_base_map(lat, lon, zoom)

        # Add basemap layers
        self.add_all_basemap_layers(map_obj, basemap)

        BoundaryManager(self.boundary_dir).add_boundaries(map_obj)
        # Add layer control
        folium.LayerControl().add_to(map_obj)

        # Add sample markers if requested
        if include_markers:
            self.add_sample_markers(map_obj)

        return map_obj

    # ------------------------------------------------------------------------------------------

    def get_available_basemaps(self) -> list[str]:
        """
        Get a list of available basemap names.

        Returns:
            A list of basemap option names.
        """
        return list(self.basemap_options.keys())


# ==========================================================================================
# ==========================================================================================


def create_routes(
    app: Flask,
    map_options: dict[str, str],
    attributes: dict[str, str],
    map_config: dict[str, float],
    boundary_dir: Path,
) -> None:
    """
    Register application routes on the provided Flask app.

    This function attaches two routes:

      - ``"/"``: The index page. Renders an interactive Folium map into an HTML
        template. Accepts an optional ``basemap`` query parameter to choose the
        initial basemap.

      - ``"/api/basemaps"``: A JSON API endpoint that returns the list of
        available basemaps and the default basemap.

    Args:
        app: The Flask application instance to which routes will be registered.

    Returns:
        None. Routes are registered on the given app in place.
    """
    map_service = MapService(map_options, attributes, map_config, boundary_dir)

    @app.route("/")
    def index() -> Union[str, Response]:
        """
        Render the index page with an embedded Folium map.

        Query Parameters:
            basemap (str, optional): The name of the basemap to use. If not
                provided or invalid, the service's default basemap is used.

        Returns:
            Rendered HTML page (str or Response) with:
              - ``map_html``: HTML representation of the Folium map
              - ``available_basemaps``: List of basemaps for UI controls
        """
        # Get basemap from query parameter (optional, for URL-based control)
        selected_basemap = request.args.get("basemap", map_service.default_config["basemap"])

        # Validate basemap selection
        selected_basemap = map_service.validate_basemap(selected_basemap)

        # Create the map
        map_obj = map_service.create_map(basemap=selected_basemap)

        # Get map HTML
        map_html = map_obj._repr_html_()

        return render_template(
            "index.html",
            map_html=map_html,
            available_basemaps=map_service.get_available_basemaps(),
        )

    @app.route("/api/basemaps")
    def get_basemaps() -> Response:
        """
        JSON API endpoint returning available basemaps.

        Returns:
            JSON response with keys:
              - ``basemaps`` (List[str]): All supported basemap names
              - ``default`` (str): The configured default basemap
        """
        return jsonify(
            {
                "basemaps": map_service.get_available_basemaps(),
                "default": map_service.default_config["basemap"],
            }
        )


# ==========================================================================================
# ==========================================================================================


class TemplateManager:
    """
    Utility class for managing Jinja2 HTML templates and static files
    (CSS/JS) required by the Flask + Folium application.

    The class ensures template and static directories exist, provides
    default HTML/CSS content, and writes them to disk when needed.
    """

    def __init__(self, data_dir: Path, template_dir: Path, static_dir: Path) -> None:
        """
        Initialize the TemplateManager with paths to project directories.

        Args:
            data_dir: Base data directory for the application.
            template_dir: Directory where Jinja2 templates (e.g. ``index.html``) are stored.
            static_dir: Directory where static files (e.g. CSS, JS) are stored.
        """
        self.data_dir = data_dir
        self.template_dir = template_dir
        self.static_dir = static_dir

    # ------------------------------------------------------------------------------------------

    def create_templates(self) -> None:
        """
        Create required template and static files for the web application.

        - Ensures that the template and static directories exist.
        - Creates an ``index.html`` template file if not already present.
        - Ensures a default ``style.css`` exists in the static directory.

        Returns:
            None. Files are written to disk in the specified directories.
        """
        self._ensure_template_dir()
        self._ensure_static_dirs()

        # Create index.html
        index_path = self.template_dir / "index.html"
        if not index_path.exists():  # <-- don’t overwrite by default
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(self._get_index_template())

        # Copy or ensure style.css exists
        css_path = self.static_dir / "css" / "style.css"
        if not css_path.exists():
            # If style.css doesn't exist, create a basic one
            with open(css_path, "w", encoding="utf-8") as f:
                f.write(self._get_default_css_content())
            print(f"Default CSS file created: {css_path}")
        else:
            print(f"Using existing CSS file: {css_path}")

        print(f"Template created: {index_path}")

    # ==========================================================================================
    # PRIVATE-LIKE CONTENT

    def _ensure_template_dir(self) -> None:
        """
        Ensure the template directory exists.

        Creates the directory (and parents) if it does not exist.

        Returns:
            None
        """
        self.template_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------------------------------

    def _ensure_static_dirs(self) -> None:
        """
        Ensure static directories exist.

        Creates the ``static/``, ``static/css/``, and ``static/js/`` directories
        if they do not already exist.

        Returns:
            None
        """
        for dir_path in (
            self.static_dir,
            self.static_dir / "css",
            self.static_dir / "js",
        ):
            dir_path.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------------------------------

    def _get_index_template(self) -> str:
        """
        Return the default Jinja2 index.html template content.

        This template defines the HTML structure for embedding a Folium map
        into a Flask-rendered page.

        Returns:
            str: The HTML template as a string.
        """
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Interactive Folium Map</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <div class="container">
        <h1>Map Header Here</h1>
        <div class="map-container" id="map-container">
            {{ map_html|safe }}
        </div>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Folium Map Application Loaded');
            console.log('Available basemaps:', {{ available_basemaps|tojson }});
            console.log('Use the layer control in the top-right corner of the map to switch basemaps');
        });
    </script>
</body>
</html>"""

    # ------------------------------------------------------------------------------------------

    def _get_default_css_content(self):
        """
        Return default CSS content for styling the Folium map page.

        Provides responsive layout, container styles, and
        lightweight styling for basemap tags and instructions.

        Returns:
            str: CSS stylesheet content.
        """
        return """/* Basic styles - customize as needed */
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 0;
    background-color: #f5f5f5;
    height: 100vh;
    display: flex;
    flex-direction: column;
}

.container {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 20px;
}

.info-panel {
    background: white;
    padding: 15px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin-bottom: 20px;
    width: 66.67%;
    max-width: 800px;
}

.map-container {
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    overflow: hidden;
    width: 66.67%;
    height: 70vh;
}

h1 {
    color: #333;
    text-align: center;
    margin-bottom: 30px;
}

.info {
    color: #666;
    font-size: 14px;
    line-height: 1.6;
}

.basemap-list {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 10px;
}

.basemap-tag {
    background: #e9ecef;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    color: #495057;
}

.instruction {
    background: #d4edda;
    border: 1px solid #c3e6cb;
    color: #155724;
    padding: 12px;
    border-radius: 4px;
    margin-top: 15px;
}"""


# ==========================================================================================
# ==========================================================================================
# eof
