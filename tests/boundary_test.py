import json
from pathlib import Path

import folium
import pytest

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


def _feature_groups_on(map_obj: folium.Map):
    """Return FeatureGroup children in insertion order."""
    # Folium keeps children in map_obj._children (ordered); filter FeatureGroup instances
    return [child for child in map_obj._children.values() if isinstance(child, folium.map.FeatureGroup)]


# ==========================================================================================
# ==========================================================================================


def test_directory_missing_adds_no_layers_and_prints(tmp_path: Path, capsys: pytest.CaptureFixture):
    """boundary_dir does not exist → no layers added; debug lines printed; no exceptions."""
    missing_dir = tmp_path / "boundary"  # do not create it
    m = folium.Map(location=[0, 0], zoom_start=2)

    mgr = BoundaryManager(missing_dir)
    mgr.add_boundaries(m)

    out = capsys.readouterr().out
    assert f"[DEBUG] Searching {missing_dir}" in out
    assert "Boundary directory does not exist" in out

    groups = _feature_groups_on(m)
    assert groups == []


# ------------------------------------------------------------------------------------------


def test_directory_exists_but_empty_adds_no_layers_and_prints(tmp_path: Path, capsys: pytest.CaptureFixture):
    """Empty directory → no layers; debug prints include 'Found 0 boundary files'."""
    boundary_dir = tmp_path / "boundary"
    boundary_dir.mkdir(parents=True, exist_ok=True)
    m = folium.Map(location=[0, 0], zoom_start=2)

    mgr = BoundaryManager(boundary_dir)
    mgr.add_boundaries(m)

    out = capsys.readouterr().out
    assert f"[DEBUG] Searching {boundary_dir}" in out
    assert "[DEBUG] Found 0 boundary files" in out

    groups = _feature_groups_on(m)
    assert groups == []


# ------------------------------------------------------------------------------------------


def test_unsupported_extensions_only_ignored(tmp_path: Path, capsys: pytest.CaptureFixture):
    """Only unsupported files present (e.g., .txt) → zero layers, no errors."""
    boundary_dir = tmp_path / "boundary"
    boundary_dir.mkdir(parents=True, exist_ok=True)
    (boundary_dir / "notes.txt").write_text("hello", encoding="utf-8")

    m = folium.Map(location=[0, 0], zoom_start=2)
    BoundaryManager(boundary_dir).add_boundaries(m)

    out = capsys.readouterr().out
    assert "[DEBUG] Found 0 boundary files" in out

    groups = _feature_groups_on(m)
    assert groups == []


# ------------------------------------------------------------------------------------------


def test_unsupported_extensions_are_ignored_when_mixed_with_valid(
    tmp_path: Path, capsys: pytest.CaptureFixture
):
    """Unsupported files are ignored; supported ones are processed."""
    boundary_dir = tmp_path / "boundary"
    boundary_dir.mkdir(parents=True, exist_ok=True)
    (boundary_dir / "README.txt").write_text("ignore me", encoding="utf-8")
    _write_geojson(boundary_dir / "a_layer.geojson", name="A")

    m = folium.Map(location=[0, 0], zoom_start=2)
    BoundaryManager(boundary_dir).add_boundaries(m)

    out = capsys.readouterr().out
    # Should report exactly 1 supported file
    assert "[DEBUG] Found 1 boundary files: ['a_layer.geojson']" in out

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
# eof
