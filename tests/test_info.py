"""Tests for GeoTIFF metadata reading."""

import pytest
import os
import tempfile

from conftest import (
    read_geotiff, format_text_table, format_json, create_test_geotiff
)


def test_read_basic_tiff(tmp_path):
    """Test reading a basic TIFF file."""
    tif_file = tmp_path / "basic.tif"
    create_test_geotiff(str(tif_file), include_geo=False)
    
    info = read_geotiff(str(tif_file))
    
    assert info.file_path == str(tif_file)
    assert info.width == 10
    assert info.height == 10
    assert info.samples_per_pixel == 1
    assert info.is_geotiff == False
    assert info.is_bigtiff == False


def test_read_geotiff(tmp_path):
    """Test reading a GeoTIFF file."""
    tif_file = tmp_path / "geo.tif"
    create_test_geotiff(str(tif_file), include_geo=True)
    
    info = read_geotiff(str(tif_file))
    
    assert info.is_geotiff == True
    assert info.crs_epsg == 4326
    assert info.crs_name == "WGS 84"
    assert len(info.pixel_scale) > 0
    assert len(info.tiepoint) > 0
    assert len(info.affine_transform) > 0
    assert len(info.corner_coords) > 0


def test_read_bigtiff(tmp_path):
    """Test reading a BigTIFF file."""
    tif_file = tmp_path / "big.tif"
    create_test_geotiff(str(tif_file), include_geo=True, bigtiff=True)
    
    info = read_geotiff(str(tif_file))
    
    assert info.is_bigtiff == True
    assert info.is_geotiff == True
    assert info.crs_epsg == 4326


def test_read_nodata(tmp_path):
    """Test reading NoData value."""
    tif_file = tmp_path / "nodata.tif"
    create_test_geotiff(str(tif_file), nodata=-9999.0)
    
    info = read_geotiff(str(tif_file))
    
    assert info.nodata == "-9999.0"


def test_read_bits_per_sample_8(tmp_path):
    """Test reading 8-bit data."""
    tif_file = tmp_path / "8bit.tif"
    create_test_geotiff(str(tif_file), bits_per_sample=8)
    
    info = read_geotiff(str(tif_file))
    
    assert 8 in info.bits_per_sample


def test_read_bits_per_sample_16(tmp_path):
    """Test reading 16-bit data."""
    tif_file = tmp_path / "16bit.tif"
    create_test_geotiff(str(tif_file), bits_per_sample=16)
    
    info = read_geotiff(str(tif_file))
    
    assert 16 in info.bits_per_sample


def test_read_bits_per_sample_32(tmp_path):
    """Test reading 32-bit data."""
    tif_file = tmp_path / "32bit.tif"
    create_test_geotiff(str(tif_file), bits_per_sample=32, sample_format=3)
    
    info = read_geotiff(str(tif_file))
    
    assert 32 in info.bits_per_sample
    assert "floating point" in info.sample_format


def test_read_sample_format_uint(tmp_path):
    """Test reading unsigned integer format."""
    tif_file = tmp_path / "uint.tif"
    create_test_geotiff(str(tif_file), sample_format=1)
    
    info = read_geotiff(str(tif_file))
    
    assert "unsigned integer" in info.sample_format


def test_read_sample_format_int(tmp_path):
    """Test reading signed integer format."""
    tif_file = tmp_path / "int.tif"
    create_test_geotiff(str(tif_file), sample_format=2)
    
    info = read_geotiff(str(tif_file))
    
    assert "signed integer" in info.sample_format


def test_read_sample_format_float(tmp_path):
    """Test reading floating point format."""
    tif_file = tmp_path / "float.tif"
    create_test_geotiff(str(tif_file), sample_format=3)
    
    info = read_geotiff(str(tif_file))
    
    assert "floating point" in info.sample_format


def test_read_pixel_scale(tmp_path):
    """Test reading pixel scale."""
    tif_file = tmp_path / "scale.tif"
    create_test_geotiff(str(tif_file))
    
    info = read_geotiff(str(tif_file))
    
    assert len(info.pixel_scale) >= 2
    assert info.pixel_scale[0] > 0
    assert info.pixel_scale[1] > 0


def test_read_tiepoint(tmp_path):
    """Test reading tiepoint."""
    tif_file = tmp_path / "tiepoint.tif"
    create_test_geotiff(str(tif_file))
    
    info = read_geotiff(str(tif_file))
    
    assert len(info.tiepoint) >= 6
    assert info.tiepoint[3] == 115.0  # x
    assert info.tiepoint[4] == 40.0   # y


def test_read_affine_transform(tmp_path):
    """Test affine transform calculation."""
    tif_file = tmp_path / "affine.tif"
    create_test_geotiff(str(tif_file))
    
    info = read_geotiff(str(tif_file))
    
    assert len(info.affine_transform) == 6
    assert info.affine_transform[0] > 0  # sx
    assert info.affine_transform[4] < 0  # -sy


def test_read_corner_coordinates(tmp_path):
    """Test corner coordinate calculation."""
    tif_file = tmp_path / "corners.tif"
    create_test_geotiff(str(tif_file))
    
    info = read_geotiff(str(tif_file))
    
    assert "Upper Left" in info.corner_coords
    assert "Upper Right" in info.corner_coords
    assert "Lower Left" in info.corner_coords
    assert "Lower Right" in info.corner_coords
    
    ul = info.corner_coords["Upper Left"]
    assert ul[0] == 115.0
    assert ul[1] == 40.0


def test_read_geo_keys(tmp_path):
    """Test reading GeoKeys."""
    tif_file = tmp_path / "geokeys.tif"
    create_test_geotiff(str(tif_file))
    
    info = read_geotiff(str(tif_file))
    
    assert "GTModelTypeGeoKey" in info.geo_keys
    assert "GeographicTypeGeoKey" in info.geo_keys


def test_read_file_size(tmp_path):
    """Test reading file size."""
    tif_file = tmp_path / "size.tif"
    create_test_geotiff(str(tif_file))
    
    info = read_geotiff(str(tif_file))
    
    assert info.file_size > 0
    assert info.file_size_human != ""


def test_read_little_endian(tmp_path):
    """Test reading little-endian TIFF."""
    tif_file = tmp_path / "le.tif"
    create_test_geotiff(str(tif_file), byte_order='<')
    
    info = read_geotiff(str(tif_file))
    
    assert info.width == 10
    assert info.crs_epsg == 4326


def test_read_big_endian(tmp_path):
    """Test reading big-endian TIFF."""
    tif_file = tmp_path / "be.tif"
    create_test_geotiff(str(tif_file), byte_order='>')
    
    info = read_geotiff(str(tif_file))
    
    assert info.width == 10


def test_read_compression_lzw(tmp_path):
    """Test reading LZW compression."""
    tif_file = tmp_path / "lzw.tif"
    create_test_geotiff(str(tif_file), compression=5)
    
    info = read_geotiff(str(tif_file))
    
    assert info.compression == "LZW"


def test_read_compression_none(tmp_path):
    """Test reading no compression."""
    tif_file = tmp_path / "none.tif"
    create_test_geotiff(str(tif_file), compression=1)
    
    info = read_geotiff(str(tif_file))
    
    assert info.compression == "None"


def test_read_photometric_minisblack(tmp_path):
    """Test reading MinIsBlack photometric."""
    tif_file = tmp_path / "minblack.tif"
    create_test_geotiff(str(tif_file))
    
    info = read_geotiff(str(tif_file))
    
    assert info.photometric == "MinIsBlack"


def test_format_text_table_geotiff(tmp_path):
    """Test text table output for GeoTIFF."""
    tif_file = tmp_path / "table.tif"
    create_test_geotiff(str(tif_file))
    
    info = read_geotiff(str(tif_file))
    table = format_text_table(info)
    
    assert "GeoTIFF Metadata" in table
    assert "EPSG Code" in table
    assert "4326" in table
    assert "CORNER COORDINATES" in table


def test_format_json_geotiff(tmp_path):
    """Test JSON output for GeoTIFF."""
    import json
    
    tif_file = tmp_path / "json.tif"
    create_test_geotiff(str(tif_file))
    
    info = read_geotiff(str(tif_file))
    json_str = format_json(info)
    
    data = json.loads(json_str)
    assert data["is_geotiff"] == True
    assert data["crs"]["epsg"] == 4326
    assert data["affine_transform"] is not None
    assert data["corner_coords"] is not None


def test_read_large_dimensions(tmp_path):
    """Test reading file with larger dimensions."""
    tif_file = tmp_path / "large.tif"
    create_test_geotiff(str(tif_file), width=1000, height=1000)
    
    info = read_geotiff(str(tif_file))
    
    assert info.width == 1000
    assert info.height == 1000


def test_read_nonexistent_file():
    """Test reading nonexistent file."""
    with pytest.raises(Exception):
        read_geotiff("nonexistent.tif")


def test_read_invalid_file(tmp_path):
    """Test reading invalid file."""
    invalid_file = tmp_path / "invalid.tif"
    invalid_file.write_text("This is not a TIFF file")
    
    # The reader catches errors and stores them in geo_keys
    info = read_geotiff(str(invalid_file))
    assert "error" in info.geo_keys
