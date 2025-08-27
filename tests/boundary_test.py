import json
import logging
from pathlib import Path

import folium
import pytest
from folium.features import GeoJson, GeoJsonPopup, GeoJsonTooltip

from pymap.layers import BoundaryManager

# ==========================================================================================
# ==========================================================================================
# File:    boundary_test.py
# Date:    August 26, 2025
# Author:  Jonathan A. Webb
# Purpose: This file contains unit tests for the BoundaryManager class in the layers.py
#          file
# ==========================================================================================
# ==========================================================================================
# Test support code


def _write_geojson(path: Path, name: str = "Test") -> None:
    """Write a minimal valid GeoJSON FeatureCollection (single triangle)."""
    fc = {
        "type": "FeatureCollection",
        "name": name,
        "features": [
            {
                "type": "Feature",
                "properties": {"name": name},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-100.0, 40.0], [-99.5, 40.0], [-99.75, 40.5], [-100.0, 40.0]]],
                },
            }
        ],
    }
    path.write_text(json.dumps(fc), encoding="utf-8")


# ------------------------------------------------------------------------------------------


def _basic_fc(with_props: dict | None = None) -> dict:
    """A minimal FeatureCollection with a single polygon and optional properties."""
    return {
        "type": "FeatureCollection",
        "name": "FC",
        "features": [
            {
                "type": "Feature",
                "properties": (with_props or {"name": "feat"}),
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-100.0, 40.0], [-99.5, 40.0], [-99.75, 40.5], [-100.0, 40.0]]],
                },
            }
        ],
    }


# ------------------------------------------------------------------------------------------


def _feature_groups_on(map_obj: folium.Map):
    """Return FeatureGroup children in insertion order."""
    # Folium keeps children in map_obj._children (ordered); filter FeatureGroup instances
    return [child for child in map_obj._children.values() if isinstance(child, folium.map.FeatureGroup)]


# ------------------------------------------------------------------------------------------


def _geojson_children_of(group: folium.map.FeatureGroup):
    """Return GeoJson children of a FeatureGroup."""
    return [ch for ch in group._children.values() if isinstance(ch, GeoJson)]


# ------------------------------------------------------------------------------------------


def _tooltip_of(geojson_layer: GeoJson):
    """Return the GeoJsonTooltip child if present, else None."""
    for ch in geojson_layer._children.values():
        if isinstance(ch, GeoJsonTooltip):
            return ch
    return None


#
# ------------------------------------------------------------------------------------------


def _popup_of(geojson_layer: GeoJson):
    """Return the GeoJsonPopup child if present, else None."""
    for ch in geojson_layer._children.values():
        if isinstance(ch, GeoJsonPopup):
            return ch
    return None


# ------------------------------------------------------------------------------------------


def _group_show(group: folium.map.FeatureGroup):
    """Return the 'show' option for the FeatureGroup if available (bool or None)."""
    # Folium exposes 'show' as an attribute in many versions; fall back to options if present.
    if hasattr(group, "show"):
        return getattr(group, "show")
    if hasattr(group, "options"):
        return group.options.get("show")
    return None


# ==========================================================================================
# ==========================================================================================


def test_directory_missing_adds_no_layers_and_logs(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    """boundary_dir does not exist → no layers added; debug lines logged; no exceptions."""
    missing_dir = tmp_path / "boundary"  # do not create it
    m = folium.Map(location=[0, 0], zoom_start=2)

    # Capture DEBUG logs from just the boundary logger (regardless of global config)
    with caplog.at_level(logging.DEBUG, logger="pymap.boundary"):
        BoundaryManager(missing_dir).add_boundaries(m)

    # Assert no feature groups were added
    groups = _feature_groups_on(m)
    assert groups == []

    # Assert logs were emitted
    # Option 1: assert via structured records
    msgs = [rec.getMessage() for rec in caplog.records if rec.name == "pymap.boundary"]
    assert any("Searching" in msg and str(missing_dir) in msg for msg in msgs)
    assert any("Boundary directory does not exist" in msg for msg in msgs)


# ------------------------------------------------------------------------------------------


def test_directory_exists_but_empty_adds_no_layers_and_logs(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    """Empty directory → no layers; debug logs include 'Found 0 boundary files'."""
    boundary_dir = tmp_path / "boundary"
    boundary_dir.mkdir(parents=True, exist_ok=True)
    m = folium.Map(location=[0, 0], zoom_start=2)

    # Capture DEBUG for just the boundary logger so the test is independent of global config
    with caplog.at_level(logging.DEBUG, logger="pymap.boundary"):
        BoundaryManager(boundary_dir).add_boundaries(m)

    # No layers added
    groups = _feature_groups_on(m)
    assert groups == []

    # Assert on emitted log messages
    # Prefer structured assertions over raw text search
    msgs = [rec.getMessage() for rec in caplog.records if rec.name == "pymap.boundary"]
    assert any("Searching" in msg and str(boundary_dir) in msg for msg in msgs)
    assert any("Found 0 boundary files" in msg for msg in msgs)


# ------------------------------------------------------------------------------------------


def test_unsupported_extensions_only_ignored(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    """Only unsupported files present (e.g., .txt) → zero layers, no errors."""
    boundary_dir = tmp_path / "boundary"
    boundary_dir.mkdir(parents=True, exist_ok=True)
    (boundary_dir / "notes.txt").write_text("hello", encoding="utf-8")

    m = folium.Map(location=[0, 0], zoom_start=2)

    # Capture DEBUG for just the boundary logger (independent of global config)
    with caplog.at_level(logging.DEBUG, logger="pymap.boundary"):
        BoundaryManager(boundary_dir).add_boundaries(m)

    # No layers added
    groups = _feature_groups_on(m)
    assert groups == []

    # Assert debug message about finding zero boundary files
    msgs = [rec.getMessage() for rec in caplog.records if rec.name == "pymap.boundary"]
    assert any("Found 0 boundary files" in msg for msg in msgs)

    # Optional: ensure no warnings or errors were logged
    assert not any(rec.levelno >= logging.WARNING for rec in caplog.records)


# ------------------------------------------------------------------------------------------


def test_unsupported_extensions_are_ignored_when_mixed_with_valid(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    """Unsupported files are ignored; supported ones are processed."""
    boundary_dir = tmp_path / "boundary"
    boundary_dir.mkdir(parents=True, exist_ok=True)
    (boundary_dir / "README.txt").write_text("ignore me", encoding="utf-8")
    _write_geojson(boundary_dir / "a_layer.geojson", name="A")

    m = folium.Map(location=[0, 0], zoom_start=2)

    # Capture DEBUG logs for this module/logger regardless of global config
    with caplog.at_level(logging.DEBUG, logger="pymap.boundary"):
        BoundaryManager(boundary_dir).add_boundaries(m)

    # Assert one supported file was detected in logs
    msgs = [rec.getMessage() for rec in caplog.records if rec.name == "pymap.boundary"]
    assert any("Found 1 boundary files" in msg for msg in msgs)
    assert any("a_layer.geojson" in msg for msg in msgs)

    # No warnings or errors expected
    assert not any(rec.levelno >= logging.WARNING for rec in caplog.records)

    # Assert exactly one FeatureGroup was added
    groups = _feature_groups_on(m)
    assert len(groups) == 1

    # FeatureGroup.layer_name should reflect the title (defaults to stem)
    assert getattr(groups[0], "layer_name", None) in {"a_layer", "A", "a_layer.geojson"}


# ------------------------------------------------------------------------------------------


def test_deterministic_ordering_by_filename(tmp_path: Path, capsys: pytest.CaptureFixture):
    """Multiple files → FeatureGroups added in sorted filename order."""
    boundary_dir = tmp_path / "boundary"
    boundary_dir.mkdir(parents=True, exist_ok=True)

    # Create files out of order; sorted order should be a.geojson, b.geojson, c.geojson
    _write_geojson(boundary_dir / "c.geojson", name="C")
    _write_geojson(boundary_dir / "a.geojson", name="A")
    _write_geojson(boundary_dir / "b.geojson", name="B")

    m = folium.Map(location=[0, 0], zoom_start=2)
    BoundaryManager(boundary_dir).add_boundaries(m)

    groups = _feature_groups_on(m)
    # Extract display names (FeatureGroup.layer_name). Default title is stem (a, b, c)
    names = [getattr(g, "layer_name", None) for g in groups]

    # Accept either the stem ('a','b','c') or the embedded 'name' depending on your normalization.
    # Since your default title is the stem (when no 'pymap' block), expect 'a', 'b', 'c'.
    assert names[:3] == ["a", "b", "c"]


# ==========================================================================================
# ==========================================================================================


@pytest.mark.parametrize("ext", [".geojson", ".json"])
def test_geojson_and_json_add_one_group_and_one_geojson(tmp_path: Path, ext: str):
    """Minimal FeatureCollection adds exactly one FeatureGroup containing one GeoJson."""
    boundary_dir = tmp_path / "boundary"
    boundary_dir.mkdir(parents=True, exist_ok=True)

    _write_geojson(boundary_dir / f"simple{ext}", name="Simple")

    m = folium.Map(location=[0, 0], zoom_start=2)
    BoundaryManager(boundary_dir).add_boundaries(m)

    groups = _feature_groups_on(m)
    assert len(groups) == 1

    gj_children = _geojson_children_of(groups[0])
    assert len(gj_children) == 1


# ------------------------------------------------------------------------------------------


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("geopandas") is None,
    reason="GeoPandas not available; skipping GPKG write/read test",
)
def test_gpkg_adds_one_layer_when_geopandas_available(tmp_path: Path):
    """Small GPKG adds exactly one FeatureGroup with one GeoJson (reprojection harmless)."""
    import geopandas as gpd
    from shapely.geometry import Polygon

    boundary_dir = tmp_path / "boundary"
    boundary_dir.mkdir(parents=True, exist_ok=True)

    # Simple triangle polygon in a non-4326 CRS to exercise reprojection path
    poly = Polygon([(-1000000, 5000000), (-900000, 5000000), (-950000, 5100000)])
    gdf = gpd.GeoDataFrame({"name": ["GPKG"]}, geometry=[poly], crs="EPSG:3857")
    gpkg_path = boundary_dir / "one.gpkg"
    gdf.to_file(gpkg_path, driver="GPKG")

    m = folium.Map(location=[0, 0], zoom_start=2)
    BoundaryManager(boundary_dir).add_boundaries(m)

    groups = _feature_groups_on(m)
    assert len(groups) == 1
    assert len(_geojson_children_of(groups[0])) == 1


# ------------------------------------------------------------------------------------------


def test_gpkg_skipped_when_geopandas_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    """When gpd is None, .gpkg is skipped with a warning; no exception."""
    boundary_dir = tmp_path / "boundary"
    boundary_dir.mkdir(parents=True, exist_ok=True)
    (boundary_dir / "fake.gpkg").write_bytes(b"not-a-real-gpkg")

    # Patch where gpd is referenced
    import pymap.layers as layers_mod

    monkeypatch.setattr(layers_mod, "gpd", None, raising=False)

    m = folium.Map(location=[0, 0], zoom_start=2)

    with caplog.at_level(logging.WARNING, logger="pymap.boundary"):
        from pymap.layers import BoundaryManager

        BoundaryManager(boundary_dir).add_boundaries(m)

    # No layers added
    assert _feature_groups_on(m) == []

    # Warning logged about missing GeoPandas / skipping gpkg
    msgs = [r.getMessage() for r in caplog.records if r.name == "pymap.boundary"]
    assert any(
        "geopandas" in msg.lower() and ("gpkg" in msg.lower() or "geopackage" in msg.lower()) for msg in msgs
    )


# ==========================================================================================
# ==========================================================================================


def test_embedded_metadata_only_is_applied(tmp_path: Path, capsys):
    """GeoJSON with top-level 'pymap' drives title, visibility, tooltip/popup, and style."""
    boundary_dir = tmp_path / "boundary"
    boundary_dir.mkdir(parents=True, exist_ok=True)

    fc = _basic_fc({"name": "feat", "area": 1.23})
    fc["pymap"] = {
        "title": "Embedded Title",
        "visible_default": False,
        "tooltip": {"fields": ["name"], "aliases": ["Name"]},
        "popup": {"fields": ["area"]},
        "style": {"color": "#ff00ff", "weight": 3, "fill": True, "fillOpacity": 0.6},
    }
    (boundary_dir / "embedded.geojson").write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")

    m = folium.Map(location=[0, 0], zoom_start=2)
    BoundaryManager(boundary_dir).add_boundaries(m)
    out = capsys.readouterr().out
    print(out)

    groups = _feature_groups_on(m)
    assert len(groups) == 1
    group = groups[0]
    assert group.layer_name == "Embedded Title"
    assert _group_show(group) is False  # visible_default=False

    gj = _geojson_children_of(group)[0]
    # Tooltip
    tt = _tooltip_of(gj)
    assert tt is not None
    assert tt.fields == ["name"]
    assert tt.aliases == ["Name"]
    # Popup
    pp = _popup_of(gj)
    assert pp is not None
    assert pp.fields == ["area"]
    # Style
    style_fn = getattr(gj, "style_function", None)
    assert callable(style_fn)
    styled = style_fn({"properties": {}})  # feature arg is ignored by our style_fn
    assert styled["color"] == "#ff00ff"
    assert styled["weight"] == 3
    assert styled["fill"] is True
    assert styled["fillOpacity"] == 0.6


# ------------------------------------------------------------------------------------------


def test_sidecar_metadata_only_is_applied(tmp_path: Path):
    """No 'pymap' block, but sidecar '<stem>.meta.json' exists → sidecar settings applied."""
    boundary_dir = tmp_path / "boundary"
    boundary_dir.mkdir(parents=True, exist_ok=True)

    stem = "with_sidecar"
    _write_geojson(boundary_dir / f"{stem}.geojson", _basic_fc({"label": "L", "v": 7}))

    sidecar = {
        "title": "Sidecar Title",
        "visible_default": True,
        "tooltip": {"fields": ["label"], "aliases": ["Label"]},
        "popup": {"fields": ["v"]},
        "style": {"color": "#00aa00", "weight": 2, "fill": False},
    }
    (boundary_dir / f"{stem}.meta.json").write_text(json.dumps(sidecar, ensure_ascii=False), encoding="utf-8")

    m = folium.Map(location=[0, 0], zoom_start=2)
    BoundaryManager(boundary_dir).add_boundaries(m)

    group = _feature_groups_on(m)[0]
    assert group.layer_name == "Sidecar Title"
    assert _group_show(group) is True

    gj = _geojson_children_of(group)[0]
    tt = _tooltip_of(gj)
    assert tt is not None and tt.fields == ["label"] and tt.aliases == ["Label"]

    pp = _popup_of(gj)
    assert pp is not None and pp.fields == ["v"]

    styled = gj.style_function({})
    assert styled["color"] == "#00aa00"
    assert styled["weight"] == 2
    assert styled["fill"] is False


# ------------------------------------------------------------------------------------------


def test_embedded_metadata_precedes_sidecar(tmp_path: Path):
    """When both embedded and sidecar exist, embedded metadata wins on overlapping keys."""
    boundary_dir = tmp_path / "boundary"
    boundary_dir.mkdir(parents=True, exist_ok=True)

    stem = "both"
    fc = _basic_fc({"p": 42})
    fc["pymap"] = {
        "title": "Embedded Wins",
        "visible_default": False,
        "tooltip": {"fields": ["p"], "aliases": ["P-embed"]},
        "popup": {"fields": ["p"]},
        "style": {"color": "#111111", "weight": 4},
    }
    (boundary_dir / f"{stem}.geojson").write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")

    sidecar = {
        "title": "Sidecar Loses",
        "visible_default": True,
        "tooltip": {"fields": ["p"], "aliases": ["P-sidecar"]},
        "popup": {"fields": ["p"]},
        "style": {"color": "#eeeeee", "weight": 1},
    }
    (boundary_dir / f"{stem}.meta.json").write_text(json.dumps(sidecar, ensure_ascii=False), encoding="utf-8")

    m = folium.Map(location=[0, 0], zoom_start=2)
    BoundaryManager(boundary_dir).add_boundaries(m)

    group = _feature_groups_on(m)[0]
    assert group.layer_name == "Embedded Wins"
    assert _group_show(group) is False  # from embedded

    gj = _geojson_children_of(group)[0]
    tt = _tooltip_of(gj)
    assert tt is not None
    assert tt.aliases == ["P-embed"]  # embedded alias chosen

    styled = gj.style_function({})
    assert styled["color"] == "#111111"
    assert styled["weight"] == 4


# ------------------------------------------------------------------------------------------


def test_defaults_applied_when_no_metadata(tmp_path: Path):
    """No embedded or sidecar metadata → title=stem, visible_default=True, no tooltip/popup, default style."""
    boundary_dir = tmp_path / "boundary"
    boundary_dir.mkdir(parents=True, exist_ok=True)

    _write_geojson(boundary_dir / "plain.geojson", _basic_fc())

    m = folium.Map(location=[0, 0], zoom_start=2)
    BoundaryManager(boundary_dir).add_boundaries(m)

    group = _feature_groups_on(m)[0]
    # Default title is file stem
    assert group.layer_name == "plain"
    # Default visibility is True
    assert _group_show(group) is True

    gj = _geojson_children_of(group)[0]
    # No tooltip/popup added
    assert _tooltip_of(gj) is None
    assert _popup_of(gj) is None

    # Default style from _build_style_function
    styled = gj.style_function({})
    assert styled["color"] == "#444"
    assert styled["weight"] == 1.0
    assert styled["fill"] is False
    assert styled["fillOpacity"] == 0.2


# ==========================================================================================
# ==========================================================================================
# eof
