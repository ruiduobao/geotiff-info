"""Integration tests for GeoTIFF metadata viewer."""

import pytest
import os
import struct
import tempfile
import json
import sys

from conftest import (
    read_geotiff, format_text_table, format_json, scan_directory,
    create_test_geotiff
)


def test_full_workflow_text(tmp_path):
    """Test complete workflow with text output."""
    tif_file = tmp_path / "workflow.tif"
    create_test_geotiff(str(tif_file))
    
    info = read_geotiff(str(tif_file))
    table = format_text_table(info)
    
    assert "GeoTIFF Metadata" in table
    assert "EPSG Code" in table
    assert "4326" in table
    assert "PIXEL RESOLUTION" in table
    assert "AFFINE TRANSFORM" in table
    assert "CORNER COORDINATES" in table
    assert "Upper Left" in table
    assert "Upper Right" in table
    assert "Lower Left" in table
    assert "Lower Right" in table


def test_full_workflow_json(tmp_path):
    """Test complete workflow with JSON output."""
    tif_file = tmp_path / "workflow.tif"
    create_test_geotiff(str(tif_file))
    
    info = read_geotiff(str(tif_file))
    json_str = format_json(info)
    
    data = json.loads(json_str)
    
    assert data["is_geotiff"] == True
    assert data["crs"]["epsg"] == 4326
    assert data["crs"]["name"] == "WGS 84"
    assert len(data["pixel_scale"]) == 3
    assert len(data["tiepoint"]) == 6
    assert len(data["affine_transform"]) == 6
    assert "Upper Left" in data["corner_coords"]
    assert "GTModelTypeGeoKey" in data["geo_keys"]
    assert "GeographicTypeGeoKey" in data["geo_keys"]


def test_batch_scan_multiple_files(tmp_path):
    """Test scanning directory with multiple GeoTIFF files."""
    for i in range(5):
        tif_file = tmp_path / f"file_{i}.tif"
        create_test_geotiff(str(tif_file), width=10 * (i + 1), height=10 * (i + 1))
    
    results = scan_directory(str(tmp_path))
    
    assert len(results) == 5
    for info in results:
        assert info.is_geotiff == True
        assert info.width > 0
        assert info.height > 0


def test_batch_scan_mixed_files(tmp_path):
    """Test scanning directory with mixed file types."""
    # Create GeoTIFF files
    for i in range(3):
        tif_file = tmp_path / f"geo_{i}.tif"
        create_test_geotiff(str(tif_file))
    
    # Create non-TIFF files
    (tmp_path / "readme.txt").write_text("Not a TIFF")
    (tmp_path / "data.csv").write_text("a,b,c")
    
    results = scan_directory(str(tmp_path))
    
    assert len(results) == 3


def test_batch_scan_subdirectories(tmp_path):
    """Test that scan doesn't recurse into subdirectories."""
    # Create GeoTIFF in root
    tif_file = tmp_path / "root.tif"
    create_test_geotiff(str(tif_file))
    
    # Create subdirectory with GeoTIFF
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    sub_tif = subdir / "sub.tif"
    create_test_geotiff(str(sub_tif))
    
    results = scan_directory(str(tmp_path))
    
    # Should only find root file (non-recursive)
    assert len(results) == 1
    assert results[0].file_path == str(tif_file)


def test_different_epsg_codes(tmp_path):
    """Test reading files with different EPSG codes."""
    # Create file with UTM projection
    tif_file = tmp_path / "utm.tif"
    
    with open(tif_file, 'wb') as f:
        f.write(b'II')
        f.write(struct.pack('<H', 42))
        f.write(struct.pack('<I', 8))
        
        entries = [
            (256, 3, 1, 100),  # Width
            (257, 3, 1, 100),  # Height
            (258, 3, 1, 16),   # BitsPerSample
            (259, 3, 1, 1),    # Compression
            (262, 3, 1, 1),    # Photometric
            (277, 3, 1, 1),    # SamplesPerPixel
            (339, 3, 1, 1),    # SampleFormat
            (33550, 12, 3, 600),  # PixelScale
            (33922, 12, 6, 624),  # Tiepoint
            (34735, 3, 12, 672),  # GeoKeyDirectory
        ]
        
        f.write(struct.pack('<H', len(entries)))
        for tag, type_id, count, value in entries:
            f.write(struct.pack('<HH', tag, type_id))
            f.write(struct.pack('<I', count))
            f.write(struct.pack('<I', value))
        
        # PixelScale
        f.seek(600)
        f.write(struct.pack('<ddd', 30.0, 30.0, 0.0))
        
        # Tiepoint
        f.seek(624)
        f.write(struct.pack('<dddddd', 0.0, 0.0, 0.0, 500000.0, 4000000.0, 0.0))
        
        # GeoKeyDirectory with UTM Zone 32N (EPSG:32632)
        f.seek(672)
        geo_keys = [1, 1, 0, 2, 1024, 0, 1, 1, 3072, 0, 1, 32632]
        for val in geo_keys:
            f.write(struct.pack('<H', val))
    
    info = read_geotiff(str(tif_file))
    
    assert info.crs_epsg == 32632
    assert "UTM" in info.crs_name


def test_pixel_scale_variations(tmp_path):
    """Test reading different pixel scale values."""
    scales = [
        (0.000277777777778, 0.000277777777778, 0.0),  # ~30m at equator
        (1.0, 1.0, 0.0),  # 1 meter
        (0.5, 0.5, 0.0),  # 50 cm
        (30.0, 30.0, 0.0),  # 30 meters
    ]
    
    for i, scale in enumerate(scales):
        tif_file = tmp_path / f"scale_{i}.tif"
        
        with open(tif_file, 'wb') as f:
            f.write(b'II')
            f.write(struct.pack('<H', 42))
            f.write(struct.pack('<I', 8))
            
            entries = [
                (256, 3, 1, 10),
                (257, 3, 1, 10),
                (258, 3, 1, 16),
                (259, 3, 1, 1),
                (262, 3, 1, 1),
                (277, 3, 1, 1),
                (339, 3, 1, 1),
                (33550, 12, 3, 200),
                (33922, 12, 6, 224),
                (34735, 3, 12, 272),
            ]
            
            f.write(struct.pack('<H', len(entries)))
            for tag, type_id, count, value in entries:
                f.write(struct.pack('<HH', tag, type_id))
                f.write(struct.pack('<I', count))
                f.write(struct.pack('<I', value))
            
            f.seek(200)
            f.write(struct.pack('<ddd', *scale))
            
            f.seek(224)
            f.write(struct.pack('<dddddd', 0.0, 0.0, 0.0, 100.0, 200.0, 0.0))
            
            f.seek(272)
            geo_keys = [1, 1, 0, 2, 1024, 0, 1, 2, 2048, 0, 1, 4326]
            for val in geo_keys:
                f.write(struct.pack('<H', val))
        
        info = read_geotiff(str(tif_file))
        
        assert info.pixel_scale[0] == pytest.approx(scale[0], rel=1e-10)
        assert info.pixel_scale[1] == pytest.approx(scale[1], rel=1e-10)


def test_nodata_variations(tmp_path):
    """Test reading different NoData values."""
    nodata_values = [-9999.0, -3.4028234663852886e+38, 0.0, 255.0]
    
    for i, nodata in enumerate(nodata_values):
        tif_file = tmp_path / f"nodata_{i}.tif"
        create_test_geotiff(str(tif_file), nodata=nodata)
        
        info = read_geotiff(str(tif_file))
        
        # NoData is stored as string
        assert info.nodata is not None


def test_bits_per_sample_combinations(tmp_path):
    """Test different bits per sample combinations."""
    bits = [8, 16, 32]
    
    for b in bits:
        tif_file = tmp_path / f"bits_{b}.tif"
        create_test_geotiff(str(tif_file), bits_per_sample=b)
        
        info = read_geotiff(str(tif_file))
        
        assert b in info.bits_per_sample


def test_sample_format_combinations(tmp_path):
    """Test different sample format combinations."""
    formats = [
        (1, "unsigned integer"),
        (2, "signed integer"),
        (3, "floating point"),
    ]
    
    for fmt_code, fmt_name in formats:
        tif_file = tmp_path / f"format_{fmt_code}.tif"
        create_test_geotiff(str(tif_file), sample_format=fmt_code)
        
        info = read_geotiff(str(tif_file))
        
        assert fmt_name in info.sample_format


def test_compression_combinations(tmp_path):
    """Test different compression types."""
    compressions = [
        (1, "None"),
        (5, "LZW"),
        (8, "Deflate"),
    ]
    
    for comp_code, comp_name in compressions:
        tif_file = tmp_path / f"comp_{comp_code}.tif"
        create_test_geotiff(str(tif_file), compression=comp_code)
        
        info = read_geotiff(str(tif_file))
        
        assert info.compression == comp_name


def test_dimensions_variations(tmp_path):
    """Test different image dimensions."""
    dimensions = [
        (1, 1),      # Minimum
        (100, 100),  # Small
        (1000, 1000),  # Medium
    ]
    
    for width, height in dimensions:
        tif_file = tmp_path / f"dim_{width}x{height}.tif"
        create_test_geotiff(str(tif_file), width=width, height=height)
        
        info = read_geotiff(str(tif_file))
        
        assert info.width == width
        assert info.height == height


def test_json_roundtrip(tmp_path):
    """Test that JSON output can be parsed back."""
    tif_file = tmp_path / "roundtrip.tif"
    create_test_geotiff(str(tif_file))
    
    info = read_geotiff(str(tif_file))
    json_str = format_json(info)
    
    # Parse back
    data = json.loads(json_str)
    
    # Verify structure
    assert "file" in data
    assert "width" in data
    assert "height" in data
    assert "is_geotiff" in data
    assert "crs" in data
    assert "pixel_scale" in data
    assert "affine_transform" in data
    assert "corner_coords" in data
    assert "geo_keys" in data


def test_text_table_contains_all_sections(tmp_path):
    """Test that text table contains all expected sections."""
    tif_file = tmp_path / "sections.tif"
    create_test_geotiff(str(tif_file))
    
    info = read_geotiff(str(tif_file))
    table = format_text_table(info)
    
    sections = [
        "FILE INFORMATION",
        "IMAGE DIMENSIONS",
        "DATA TYPE",
        "COORDINATE REFERENCE SYSTEM",
        "PIXEL RESOLUTION",
        "AFFINE TRANSFORM",
        "CORNER COORDINATES",
    ]
    
    for section in sections:
        assert section in table


def test_scan_empty_directory(tmp_path):
    """Test scanning empty directory."""
    results = scan_directory(str(tmp_path))
    assert results == []


def test_scan_with_tiff_extensions(tmp_path):
    """Test scanning with different TIFF extensions."""
    extensions = ['.tif', '.tiff', '.TIF', '.TIFF']
    
    for ext in extensions:
        tif_file = tmp_path / f"file{ext}"
        create_test_geotiff(str(tif_file))
    
    results = scan_directory(str(tmp_path))
    # On Windows, .tif and .TIF are the same, .tiff and .TIFF are the same
    # So we get 2 unique files
    assert len(results) == 2


def test_file_size_accuracy(tmp_path):
    """Test that file size is reported accurately."""
    tif_file = tmp_path / "size.tif"
    create_test_geotiff(str(tif_file))
    
    expected_size = os.path.getsize(str(tif_file))
    info = read_geotiff(str(tif_file))
    
    assert info.file_size == expected_size


def test_bigtiff_detection(tmp_path):
    """Test BigTIFF detection."""
    tif_file = tmp_path / "big.tif"
    create_test_geotiff(str(tif_file), bigtiff=True)
    
    info = read_geotiff(str(tif_file))
    
    assert info.is_bigtiff == True


def test_classic_tiff_detection(tmp_path):
    """Test classic TIFF detection."""
    tif_file = tmp_path / "classic.tif"
    create_test_geotiff(str(tif_file), bigtiff=False)
    
    info = read_geotiff(str(tif_file))
    
    assert info.is_bigtiff == False


def test_geo_key_parsing_completeness(tmp_path):
    """Test that all GeoKeys are parsed."""
    tif_file = tmp_path / "geokeys.tif"
    create_test_geotiff(str(tif_file))
    
    info = read_geotiff(str(tif_file))
    
    assert "GTModelTypeGeoKey" in info.geo_keys
    assert "GeographicTypeGeoKey" in info.geo_keys
    assert info.geo_keys["GTModelTypeGeoKey"] == 2  # Geographic
    assert info.geo_keys["GeographicTypeGeoKey"] == 4326  # WGS 84


def test_affine_transform_calculation(tmp_path):
    """Test affine transform calculation accuracy."""
    tif_file = tmp_path / "affine.tif"
    create_test_geotiff(str(tif_file))
    
    info = read_geotiff(str(tif_file))
    
    # Verify affine transform components
    sx, sy = info.pixel_scale[0], info.pixel_scale[1]
    tx, ty = info.tiepoint[3], info.tiepoint[4]
    
    assert info.affine_transform[0] == sx  # a
    assert info.affine_transform[1] == 0.0  # b
    assert info.affine_transform[2] == tx  # c
    assert info.affine_transform[3] == 0.0  # d
    assert info.affine_transform[4] == -sy  # e
    assert info.affine_transform[5] == ty  # f


def test_corner_coordinates_calculation(tmp_path):
    """Test corner coordinate calculation accuracy."""
    tif_file = tmp_path / "corners.tif"
    create_test_geotiff(str(tif_file), width=100, height=100)

    info = read_geotiff(str(tif_file))

    a, b, c, d, e, f = info.affine_transform
    w, h = info.width, info.height

    # Upper Left
    assert info.corner_coords["Upper Left"] == (c, f)

    # Upper Right
    assert info.corner_coords["Upper Right"] == (a * w + c, b * w + f)

    # Lower Left
    assert info.corner_coords["Lower Left"] == (d * h + c, e * h + f)

    # Lower Right
    assert info.corner_coords["Lower Right"] == (a * w + d * h + c, b * w + e * h + f)


# ---------------------------------------------------------------------------
# Phase 6 — --format {text,json} flag
# ---------------------------------------------------------------------------

import subprocess


def _cli(*args, cwd=None):
    """Run geotiff-info.py and return (returncode, stdout, stderr)."""
    skill_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    script = os.path.join(skill_root, "geotiff-info.py")
    cmd = [sys.executable, script] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=cwd)


def test_help_lists_format_flag():
    """`--help` should advertise the --format {text,json} flag."""
    proc = _cli("--help")
    assert proc.returncode == 0
    assert "--format" in (proc.stdout + proc.stderr)
    # The choices should be visible
    combined = proc.stdout + proc.stderr
    assert "text" in combined
    assert "json" in combined


def test_default_format_is_text(tmp_path):
    """Without any flag, output should be the human-readable text table."""
    tif = tmp_path / "default.tif"
    create_test_geotiff(str(tif))
    proc = _cli(str(tif))
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    out = proc.stdout
    # text table contains section headers
    assert "GeoTIFF Metadata" in out
    assert "FILE INFORMATION" in out
    # and is NOT valid JSON top-level (no leading `{`)
    assert not out.lstrip().startswith("{")


def test_format_text_explicit(tmp_path):
    """`--format text` should match the default (human-readable)."""
    tif = tmp_path / "fmt_text.tif"
    create_test_geotiff(str(tif))
    proc = _cli(str(tif), "--format", "text")
    assert proc.returncode == 0
    out = proc.stdout
    assert "GeoTIFF Metadata" in out
    assert "FILE INFORMATION" in out
    assert not out.lstrip().startswith("{")


def test_format_json_explicit(tmp_path):
    """`--format json` should produce parseable JSON."""
    tif = tmp_path / "fmt_json.tif"
    create_test_geotiff(str(tif))
    proc = _cli(str(tif), "--format", "json")
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    out = proc.stdout
    data = json.loads(out)
    assert data["is_geotiff"] is True
    assert "width" in data and "height" in data
    # The human-readable header should NOT appear in JSON mode
    assert "FILE INFORMATION" not in out


def test_format_alias_json_flag_still_works(tmp_path):
    """`--json` (legacy flag) should still produce JSON output."""
    tif = tmp_path / "legacy_json.tif"
    create_test_geotiff(str(tif))
    proc = _cli(str(tif), "--json")
    assert proc.returncode == 0
    out = proc.stdout
    data = json.loads(out)
    assert data["is_geotiff"] is True


def test_format_overrides_legacy_json_flag(tmp_path):
    """`--json --format text` should output text (--format wins)."""
    tif = tmp_path / "over.tif"
    create_test_geotiff(str(tif))
    proc = _cli(str(tif), "--json", "--format", "text")
    assert proc.returncode == 0
    out = proc.stdout
    # text format, NOT JSON
    assert "FILE INFORMATION" in out
    assert not out.lstrip().startswith("{")


def test_format_rejects_invalid_choice(tmp_path):
    """`--format yaml` should be rejected by argparse."""
    tif = tmp_path / "bad_fmt.tif"
    create_test_geotiff(str(tif))
    proc = _cli(str(tif), "--format", "yaml")
    # argparse exits 2 on invalid choice
    assert proc.returncode != 0


def test_format_json_in_batch_mode(tmp_path):
    """`--batch --format json` on a directory should produce a JSON array."""
    tif = tmp_path / "batch_fmt.tif"
    create_test_geotiff(str(tif))
    proc = _cli(str(tmp_path), "--batch", "--format", "json")
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    data = json.loads(proc.stdout)
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["is_geotiff"] is True
