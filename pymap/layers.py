import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

import folium
import geopandas as gpd
from folium.features import GeoJsonPopup, GeoJsonTooltip

# ==========================================================================================
# ==========================================================================================

# File:    layers.py
# Date:    August 24, 2025
# Author:  Jonathan A. Webb
# Purpose: This file contains data necessary to add data layers to a Folium map
# ==========================================================================================
# ==========================================================================================


@dataclass
class BoundaryMeta:
    """
    Metadata definition for a single boundary overlay layer.

    This dataclass stores display and behavior options for a boundary file
    (GeoJSON or GPKG) so that the map rendering logic can apply styles,
    tooltips, and popups consistently.

    Attributes:
        title: Human-readable name for the boundary layer, shown in the map's layer control.
        visible_default: Whether the boundary should be visible (enabled) when the map first loads.
        tooltip_fields: List of property keys to display in a tooltip when hovering over features.
                        If None or empty, no tooltip is shown.
        tooltip_aliases: Optional list of labels corresponding to tooltip_fields; used as display names.
                         If None, the raw field names are used.
        popup_fields: List of property keys to display in a popup when clicking a feature.
                      If None or empty, no popup is shown.
        style: Optional dictionary of style parameters for the boundary geometry.
               Keys typically include Leaflet/Folium style options like:
                   "color" (stroke color),
                   "weight" (stroke width),
                   "fill" (boolean),
                   "fillColor",
                   "fillOpacity", etc.
    """

    title: str
    visible_default: bool = True
    tooltip_fields: Optional[list[str]] = None
    tooltip_aliases: Optional[list[str]] = None
    popup_fields: Optional[list[str]] = None
    style: Optional[dict] = None


# ==========================================================================================
# ==========================================================================================


class BoundaryManager:
    """
    Loads boundary overlays from data/boundary and adds them to a Folium map.

    Supported formats:
      - .geojson / .json : parsed directly
      - .gpkg            : requires GeoPandas (optional dependency)

    Metadata resolution order (first found wins):
      1) Embedded under top-level "pymap" in GeoJSON
      2) Sidecar file: <basename>.meta.json
      3) Defaults (title=file stem, visible_default=True)
    """

    def __init__(self, boundary_dir: Path, logger=None) -> None:
        """
        Initialize a BoundaryManager for handling overlay boundary files.

        Args:
            boundary_dir: Path to the directory where boundary files (GeoJSON/JSON/GPKG) are stored.
            logger: a log file object
        """
        self.boundary_dir = boundary_dir
        self.logger = logger or logging.getLogger("pymap.boundary")

    # ------------------------------------------------------------------------------------------

    def add_boundaries(self, m: folium.Map) -> None:
        """
        Discover boundary files and add them as overlay layers to a Folium map.

        Scans the boundary directory for supported files (.geojson, .json, .gpkg),
        reads geometry and metadata, builds tooltips and popups, and adds each file as a
        FeatureGroup layer to the given map.

        Args:
            m: A Folium Map instance to which the boundary layers will be added.

        Side Effects:
            - Prints debug information about files and metadata.
            - Adds FeatureGroups and GeoJson layers directly to the map.
            - Logs warnings for any files that could not be processed.
        """

        self.logger.debug(f"Searching {self.boundary_dir} for files")
        for path in self._iter_boundary_files():
            try:
                stem = path.stem
                if path.suffix.lower() in (".geojson", ".json"):
                    gj = self._read_geojson(path)
                    embedded = self._extract_embedded_meta(gj)  # dict or None
                    sidecar = self._load_sidecar_meta(stem)  # dict or None
                    meta_raw = embedded if embedded is not None else sidecar
                elif path.suffix.lower() == ".gpkg":
                    gj = self._read_gpkg_as_geojson(path)
                    meta_raw = self._load_sidecar_meta(stem)
                else:
                    # Skip unsupported extensions
                    continue

                meta = self._normalize_meta(meta_raw, fallback_title=stem)
                self.logger.debug(
                    "Metadata for %s: title=%s, tooltip_fields=%s, popup_fields=%s",
                    path.name,
                    meta.title,
                    meta.tooltip_fields,
                    meta.popup_fields,
                )

                group = folium.FeatureGroup(
                    name=meta.title, overlay=True, control=True, show=meta.visible_default
                )

                tooltip = None
                if meta.tooltip_fields:
                    tooltip = GeoJsonTooltip(
                        fields=meta.tooltip_fields,
                        aliases=meta.tooltip_aliases or [],
                        sticky=True,
                    )

                popup = None
                if meta.popup_fields:
                    popup = GeoJsonPopup(
                        fields=meta.popup_fields,
                        aliases=meta.popup_fields,  # or meta.tooltip_aliases if different labels desired
                        labels=True,
                        max_width=300,
                        localize=True,
                    )

                style_fn = self._build_style_function(meta.style)

                folium.GeoJson(
                    data=gj,
                    name=meta.title,
                    style_function=style_fn,
                    tooltip=tooltip,
                    popup=popup,
                    overlay=True,
                    control=True,
                    show=meta.visible_default,
                    highlight_function=lambda f: {"weight": 3},
                ).add_to(group)

                group.add_to(m)

            except Exception as e:
                # Log and skip problematic file
                self.logger.warning(f"Skipping {path.name} due to error: {e}")

    # ==========================================================================================

    def _load_sidecar_meta(self, stem: str) -> Optional[dict]:
        """
        Load metadata from a sidecar JSON file if it exists.

        Looks for a file named `<stem>.meta.json` in the boundary directory.

        Args:
            stem: Base filename (without extension) of the boundary file.

        Returns:
            Parsed metadata dictionary if the sidecar exists, otherwise None.
        """
        meta_path = self.boundary_dir / f"{stem}.meta.json"
        if meta_path.exists():
            with open(meta_path, encoding="utf-8") as f:
                return json.load(f)
        return None

    # ------------------------------------------------------------------------------------------

    def _extract_embedded_meta(self, geojson_obj: dict) -> Optional[dict]:
        """
        Extract embedded metadata from a GeoJSON object.

        Checks for a top-level "pymap" key in the GeoJSON structure.

        Args:
            geojson_obj: Parsed GeoJSON dictionary.

        Returns:
            The embedded metadata dictionary if present and valid, otherwise None.
        """
        # supports your proposed "pymap" block at the GeoJSON top level
        meta = geojson_obj.get("pymap")
        return meta if isinstance(meta, dict) else None

    # ------------------------------------------------------------------------------------------

    def _normalize_meta(self, meta_raw: Optional[dict], fallback_title: str) -> BoundaryMeta:
        """
        Normalize raw metadata to a BoundaryMeta dataclass.

        Uses provided metadata if available; otherwise fills with defaults.

        Args:
            meta_raw: Raw metadata dictionary from embedded or sidecar source, or None.
            fallback_title: Title to use if metadata does not specify one.

        Returns:
            A BoundaryMeta instance with normalized values.
        """
        meta_raw = meta_raw or {}
        return BoundaryMeta(
            title=meta_raw.get("title", fallback_title),
            visible_default=bool(meta_raw.get("visible_default", True)),
            tooltip_fields=meta_raw.get("tooltip", {}).get("fields"),
            tooltip_aliases=meta_raw.get("tooltip", {}).get("aliases"),
            popup_fields=meta_raw.get("popup", {}).get("fields"),
            style=meta_raw.get("style"),
        )

    # ------------------------------------------------------------------------------------------

    def _iter_boundary_files(self) -> Iterable[Path]:
        """
        Yield supported boundary files from the boundary directory.

        Scans the directory for files with extensions .geojson, .json, or .gpkg.

        Returns:
            A sorted list of Paths for supported files. Empty if directory does not exist.
        """
        if not self.boundary_dir.exists():
            self.logger.debug(f"Boundary directory does not exist: {self.boundary_dir}")
            return []
        exts = (".geojson", ".json", ".gpkg")
        files = []
        for p in self.boundary_dir.iterdir():
            if p.suffix.lower() not in exts:
                continue
            # skip sidecar metadata files like "<stem>.meta.json"
            if p.name.endswith(".meta.json"):
                continue
            files.append(p)
        files = sorted(files)
        self.logger.debug(f"Found {len(files)} boundary files: {[f.name for f in files]}")
        return files

    # ------------------------------------------------------------------------------------------

    def _read_geojson(self, path: Path) -> dict:
        """
        Read a GeoJSON file from disk.

        Args:
            path: Path to the .geojson or .json file.

        Returns:
            Parsed GeoJSON as a Python dictionary.
        """
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    # ------------------------------------------------------------------------------------------

    def _read_gpkg_as_geojson(self, path: Path) -> dict:
        """
        Read a GeoPackage (GPKG) file and convert it to GeoJSON format.

        Requires GeoPandas to be installed. Converts CRS to EPSG:4326 if needed.

        Args:
            path: Path to the .gpkg file.

        Returns:
            Parsed GeoJSON dictionary of the first layer.

        Raises:
            RuntimeError: If GeoPandas is not installed.
        """
        if gpd is None:
            raise RuntimeError(
                f"GeoPackage support requires GeoPandas. Install geopandas to read: {path.name}"
            )
        # Load first layer by default; users can specify layer in future metadata if needed
        gdf = gpd.read_file(path)
        # Ensure WGS84 lon/lat for Leaflet
        try:
            if gdf.crs and gdf.crs.to_epsg() != 4326:
                gdf = gdf.to_crs(4326)
        except Exception:
            # if CRS undefined, assume already lon/lat
            pass
        return json.loads(gdf.to_json())

    # ------------------------------------------------------------------------------------------

    def _build_style_function(self, style: Optional[dict]):
        """
        Build a Folium style function based on a provided style dictionary.

        Args:
            style: Optional style dictionary with Leaflet/Folium style keys such as
                   'color', 'weight', 'fill', 'fillColor', 'fillOpacity', 'dashArray'.

        Returns:
            A callable function that Folium can use to style GeoJson features.
        """
        style = style or {}

        def style_fn(_feature):
            return {
                "color": style.get("color", "#444"),
                "weight": style.get("weight", 1.0),
                "fill": bool(style.get("fill", False)),
                "fillColor": style.get("fillColor", style.get("color", "#444")),
                "fillOpacity": style.get("fillOpacity", 0.2),
                "dashArray": style.get("dashArray", "3"),
            }

        return style_fn

    # ------------------------------------------------------------------------------------------

    def _build_tooltip(self, meta: BoundaryMeta):
        """
        Build a Folium GeoJsonTooltip from metadata.

        Args:
            meta: BoundaryMeta instance containing tooltip field information.

        Returns:
            A Folium GeoJsonTooltip if tooltip_fields exist, otherwise None.
        """
        if not meta.tooltip_fields:
            return None
        return folium.features.GeoJsonTooltip(
            fields=meta.tooltip_fields, aliases=meta.tooltip_aliases or [], sticky=True
        )

    # ------------------------------------------------------------------------------------------

    def _build_popup(self, meta: BoundaryMeta):
        """
        Build a Folium popup function from metadata.

        Args:
            meta: BoundaryMeta instance containing popup field information.

        Returns:
            A function that creates a Folium Popup for each feature if popup_fields exist,
            otherwise None.
        """
        if not meta.popup_fields:
            return None

        # Simple key:value popup; for richer HTML, you could format a template string
        def popup_html(props: dict[str, Any]) -> str:
            rows = []
            for k in meta.popup_fields or []:
                if k in props:
                    rows.append(
                        f"<tr><th style='text-align:left;padding-right:8px'>{k}</th><td>{props[k]}</td></tr>"
                    )
            return f"<table>{''.join(rows)}</table>" if rows else ""

        return lambda feature: folium.Popup(popup_html(feature.get("properties", {})), max_width=300)


# ==========================================================================================
# ==========================================================================================
# eof
