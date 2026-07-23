"""Tests for CLI interface and utility functions."""

import pytest
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from conftest import (
    format_file_size, get_compression_name, get_photometric_name,
    get_sample_format_name, parse_geo_keys, calculate_affine,
    calculate_corners, format_text_table, format_json, scan_directory,
    GeoTIFFInfo, create_test_geotiff
)


def test_format_file_size_bytes():
    """Test file size formatting for bytes."""
    assert format_file_size(100) == "100.00 B"
    assert format_file_size(0) == "0.00 B"
    assert format_file_size(1023) == "1023.00 B"


def test_format_file_size_kilobytes():
    """Test file size formatting for kilobytes."""
    assert format_file_size(1024) == "1.00 KB"
    assert format_file_size(1536) == "1.50 KB"


def test_format_file_size_megabytes():
    """Test file size formatting for megabytes."""
    assert format_file_size(1048576) == "1.00 MB"
    assert format_file_size(10485760) == "10.00 MB"


def test_format_file_size_gigabytes():
    """Test file size formatting for gigabytes."""
    assert format_file_size(1073741824) == "1.00 GB"


def test_get_compression_name():
    """Test compression name lookup."""
    assert get_compression_name(1) == "None"
    assert get_compression_name(5) == "LZW"
    assert get_compression_name(8) == "Deflate"
    assert get_compression_name(32773) == "PackBits"
    assert "Unknown" in get_compression_name(999)


def test_get_photometric_name():
    """Test photometric interpretation name lookup."""
    assert get_photometric_name(0) == "MinIsWhite"
    assert get_photometric_name(1) == "MinIsBlack"
    assert get_photometric_name(2) == "RGB"
    assert get_photometric_name(3) == "Palette"
    assert "Unknown" in get_photometric_name(999)


def test_get_sample_format_name():
    """Test sample format name lookup."""
    assert get_sample_format_name(1) == "unsigned integer"
    assert get_sample_format_name(2) == "signed integer"
    assert get_sample_format_name(3) == "floating point"
    assert "Unknown" in get_sample_format_name(999)


def test_calculate_affine():
    """Test affine transform calculation."""
    pixel_scale = (0.5, 0.5, 0.0)
    tiepoint = (0.0, 0.0, 0.0, 100.0, 200.0, 0.0)
    
    result = calculate_affine(pixel_scale, tiepoint)
    
    assert len(result) == 6
    assert result[0] == 0.5  # a = sx
    assert result[1] == 0.0  # b = 0
    assert result[2] == 100.0  # c = tx
    assert result[3] == 0.0  # d = 0
    assert result[4] == -0.5  # e = -sy
    assert result[5] == 200.0  # f = ty


def test_calculate_affine_with_offset():
    """Test affine transform with tiepoint offset."""
    pixel_scale = (1.0, 1.0, 0.0)
    tiepoint = (5.0, 3.0, 0.0, 100.0, 200.0, 0.0)
    
    result = calculate_affine(pixel_scale, tiepoint)
    
    assert result[0] == 1.0  # a = sx
    assert result[2] == 95.0  # c = tx - ti * sx = 100 - 5 * 1
    assert result[4] == -1.0  # e = -sy
    assert result[5] == 203.0  # f = ty + tj * sy = 200 + 3 * 1


def test_calculate_affine_empty():
    """Test affine transform with empty inputs."""
    assert calculate_affine((), (0, 0, 0, 0, 0, 0)) == ()
    assert calculate_affine((1, 1), ()) == ()
    assert calculate_affine((), ()) == ()


def test_calculate_corners():
    """Test corner coordinate calculation."""
    affine = (1.0, 0.0, 100.0, 0.0, -1.0, 200.0)
    
    corners = calculate_corners(10, 10, affine)
    
    assert len(corners) == 4
    assert corners["Upper Left"] == (100.0, 200.0)
    assert corners["Upper Right"] == (110.0, 200.0)
    assert corners["Lower Left"] == (100.0, 190.0)
    assert corners["Lower Right"] == (110.0, 190.0)


def test_calculate_corners_empty():
    """Test corner calculation with empty affine."""
    assert calculate_corners(10, 10, ()) == {}
    assert calculate_corners(0, 0, (1, 0, 0, 0, -1, 0)) == {}
    assert calculate_corners(10, 10, (1, 0)) == {}


def test_parse_geo_keys():
    """Test GeoKey parsing."""
    # GeoKey directory: version, revision, minor, num_keys, then keys
    key_directory = [1, 1, 0, 2, 1024, 0, 1, 2, 2048, 0, 1, 4326]
    double_params = []
    ascii_params = ""
    
    result = parse_geo_keys(key_directory, double_params, ascii_params)
    
    assert "GTModelTypeGeoKey" in result
    assert result["GTModelTypeGeoKey"] == 2
    assert "GeographicTypeGeoKey" in result
    assert result["GeographicTypeGeoKey"] == 4326


def test_parse_geo_keys_empty():
    """Test GeoKey parsing with empty input."""
    assert parse_geo_keys([], [], "") == {}
    assert parse_geo_keys([1, 1, 0, 0], [], "") == {}


def test_parse_geo_keys_with_doubles():
    """Test GeoKey parsing with double parameters."""
    key_directory = [1, 1, 0, 1, 2057, 34736, 1, 0]
    double_params = [6378137.0]
    ascii_params = ""
    
    result = parse_geo_keys(key_directory, double_params, ascii_params)
    
    assert "GeogSemiMajorAxisGeoKey" in result
    assert result["GeogSemiMajorAxisGeoKey"] == 6378137.0


def test_format_text_table():
    """Test text table formatting."""
    info = GeoTIFFInfo(
        file_path="test.tif",
        file_size=1024,
        file_size_human="1.00 KB",
        width=100,
        height=100,
        bits_per_sample=[16],
        samples_per_pixel=1,
        sample_format=["unsigned integer"],
        compression="None",
        photometric="MinIsBlack",
        planar_config="Chunky",
    )
    
    result = format_text_table(info)
    
    assert "test.tif" in result
    assert "100 pixels" in result
    assert "1.00 KB" in result
    assert "unsigned integer" in result


def test_format_json():
    """Test JSON formatting."""
    info = GeoTIFFInfo(
        file_path="test.tif",
        file_size=1024,
        file_size_human="1.00 KB",
        width=100,
        height=100,
        bits_per_sample=[16],
        samples_per_pixel=1,
        sample_format=["unsigned integer"],
        compression="None",
        photometric="MinIsBlack",
        planar_config="Chunky",
    )
    
    result = format_json(info)
    
    import json
    data = json.loads(result)
    
    assert data["file"] == "test.tif"
    assert data["width"] == 100
    assert data["height"] == 100


def test_scan_directory_empty(tmp_path):
    """Test scanning empty directory."""
    result = scan_directory(str(tmp_path))
    assert result == []


def test_scan_directory_with_tiff(tmp_path):
    """Test scanning directory with TIFF files."""
    tif_file = tmp_path / "test.tif"
    create_test_geotiff(str(tif_file), include_geo=False)
    
    result = scan_directory(str(tmp_path))
    assert len(result) == 1
    assert result[0].file_path == str(tif_file)
