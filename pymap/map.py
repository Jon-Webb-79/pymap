from pathlib import Path

import folium
from flask import Flask, jsonify, render_template, request

# ==========================================================================================
# ==========================================================================================

# File:    map.py
# Date:    August 16, 2025
# Purpose: This file contains classes and functions that create the maps wich data
#          is overlaid on
# ==========================================================================================
# ==========================================================================================


class Config:
    """Application configuration"""

    DEBUG = True
    HOST = "localhost"
    PORT = 5000
    SECRET_KEY = "your-secret-key-here"


# ==========================================================================================
# ==========================================================================================

# Basemap configuration
BASEMAP_OPTIONS = {
    "Esri Satellite": (
        "https://server.arcgisonline.com/ArcGIS/rest/services/" "World_Imagery/MapServer/tile/{z}/{y}/{x}"
    ),
    "OpenStreetMap": ("https://tile.openstreetmap.org/{z}/{x}/{y}.png"),
    "OpenTopoMap": ("https://tile.opentopomap.org/{z}/{x}/{y}.png"),
}

# ==========================================================================================
# ==========================================================================================

# Attribution for each basemap
BASEMAP_ATTRIBUTIONS = {
    "Esri Satellite": (
        "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, "
        "Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
    ),
    "OpenStreetMap": (
        "&copy; <a href='https://www.openstreetmap.org/copyright'>" "OpenStreetMap</a> contributors"
    ),
    "OpenTopoMap": (
        "Map data: &copy; <a href='https://www.openstreetmap.org/copyright'>"
        "OpenStreetMap</a> contributors, <a href='http://viewfinderpanorama.org'>"
        "SRTM</a> | Map style: &copy; <a href='https://opentopomap.org'>OpenTopoMap</a> "
        "(<a href='https://creativecommons.org/licenses/by-sa/3.0/'>CC-BY-SA</a>)"
    ),
}


# ==========================================================================================
# ==========================================================================================

# Default map settings
DEFAULT_MAP_CONFIG = {
    "lat": 39.8283,
    "lon": -98.5795,
    "zoom": 4,
    "basemap": "OpenStreetMap",
}

# ------------------------------------------------------------------------------------------

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
    """Service class for creating and managing Folium maps"""

    def __init__(self):
        self.basemap_options = BASEMAP_OPTIONS
        self.attributions = BASEMAP_ATTRIBUTIONS
        self.default_config = DEFAULT_MAP_CONFIG

    # ------------------------------------------------------------------------------------------

    def validate_basemap(self, basemap):
        """Validate basemap selection"""
        if basemap not in self.basemap_options:
            return self.default_config["basemap"]
        return basemap

    # ------------------------------------------------------------------------------------------

    def create_base_map(self, lat, lon, zoom):
        """Create a base Folium map without tiles"""
        return folium.Map(location=[lat, lon], zoom_start=zoom, tiles=None)

    # ------------------------------------------------------------------------------------------

    def add_basemap_layer(self, map_obj, basemap_name, is_default=False):
        """Add a single basemap layer to the map"""
        if basemap_name not in self.basemap_options:
            raise ValueError(f"Invalid basemap: {basemap_name}")

        folium.TileLayer(
            tiles=self.basemap_options[basemap_name],
            attr=self.attributions[basemap_name],
            name=basemap_name,
            overlay=False,
            control=True,
        ).add_to(map_obj)

    # ------------------------------------------------------------------------------------------

    def add_all_basemap_layers(self, map_obj, selected_basemap):
        """Add all basemap layers to the map"""
        # Add selected basemap first (will be default)
        self.add_basemap_layer(map_obj, selected_basemap, is_default=True)

        # Add other basemap options
        for basemap_name in self.basemap_options:
            if basemap_name != selected_basemap:
                self.add_basemap_layer(map_obj, basemap_name)

    # ------------------------------------------------------------------------------------------

    def add_sample_markers(self, map_obj):
        """Add sample markers to the map"""
        for marker_data in SAMPLE_MARKERS:
            folium.Marker(
                [marker_data["lat"], marker_data["lon"]],
                popup=marker_data["popup"],
                tooltip=marker_data["tooltip"],
            ).add_to(map_obj)

    # ------------------------------------------------------------------------------------------

    def create_map(self, basemap=None, lat=None, lon=None, zoom=None, include_markers=True):
        """Create a complete Folium map with specified parameters"""
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

        # Add layer control
        folium.LayerControl().add_to(map_obj)

        # Add sample markers if requested
        if include_markers:
            self.add_sample_markers(map_obj)

        return map_obj

    # ------------------------------------------------------------------------------------------

    def get_available_basemaps(self):
        """Get list of available basemap names"""
        return list(self.basemap_options.keys())


# ==========================================================================================
# ==========================================================================================


def create_routes(app: Flask) -> None:
    """Create and register all routes with the Flask app"""

    map_service = MapService()

    @app.route("/")
    def index():
        """Main route that displays the map"""
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
    def get_basemaps():
        """API endpoint to get available basemaps"""
        return jsonify(
            {
                "basemaps": map_service.get_available_basemaps(),
                "default": map_service.default_config["basemap"],
            }
        )


# ==========================================================================================
# ==========================================================================================


class TemplateManager:
    """Manager for HTML templates and static assets"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.template_dir = data_dir / "templates"
        self.static_dir = data_dir / "assets"

    # ------------------------------------------------------------------------------------------

    def create_templates(self) -> str:
        """Create all template files and static assets"""
        self._ensure_template_dir()
        self._ensure_static_dirs()

        # Create index.html
        index_path = self.template_dir / "index.html"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(self._get_index_template())

        # Copy or ensure style.css exists
        css_path = self.static_dir / "style.css"
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
        """Create templates directory if it doesn't exist."""
        self.template_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------------------------------

    def _ensure_static_dirs(self) -> None:
        """Create static directories if they don't exist."""
        for dir_path in (
            self.static_dir,
            self.static_dir / "css",
            self.static_dir / "js",
        ):
            dir_path.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------------------------------

    def _get_index_template(self) -> str:
        """Get the main index.html template content"""
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
        <h1>Energy Infrastructure Map</h1>
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
        """Get default CSS content only if style.css doesn't exist"""
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
