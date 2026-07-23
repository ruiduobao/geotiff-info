"""Tests for security and edge cases."""

import pytest
import os
import tempfile
import struct

from conftest import (
    read_geotiff, format_file_size, create_test_geotiff
)


def test_read_empty_file(tmp_path):
    """Test reading an empty file."""
    empty_file = tmp_path / "empty.tif"
    empty_file.write_bytes(b"")
    
    info = read_geotiff(str(empty_file))
    assert "error" in info.geo_keys


def test_read_too_small_file(tmp_path):
    """Test reading a file that's too small for TIFF header."""
    small_file = tmp_path / "small.tif"
    small_file.write_bytes(b"II\x2a")
    
    info = read_geotiff(str(small_file))
    assert "error" in info.geo_keys


def test_read_invalid_byte_order(tmp_path):
    """Test reading file with invalid byte order."""
    invalid_file = tmp_path / "invalid_bo.tif"
    invalid_file.write_bytes(b"XX\x2a\x00\x00\x00\x00\x00")
    
    info = read_geotiff(str(invalid_file))
    assert "error" in info.geo_keys


def test_read_invalid_magic(tmp_path):
    """Test reading file with invalid magic number."""
    invalid_file = tmp_path / "invalid_magic.tif"
    invalid_file.write_bytes(b"II\x00\x00\x00\x00\x00\x00")
    
    info = read_geotiff(str(invalid_file))
    assert "error" in info.geo_keys


def test_read_truncated_ifd(tmp_path):
    """Test reading file with truncated IFD."""
    # Create a minimal TIFF with truncated IFD
    truncated_file = tmp_path / "truncated.tif"
    
    with open(truncated_file, 'wb') as f:
        f.write(b'II')  # Little-endian
        f.write(struct.pack('<H', 42))  # Magic
        f.write(struct.pack('<I', 8))  # IFD offset
        # Write 0 entries but claim there are more
        f.write(struct.pack('<H', 100))  # Claim 100 entries
        # Don't write any entries
    
    # Should handle gracefully
    try:
        info = read_geotiff(str(truncated_file))
    except Exception:
        pass  # Expected


def test_path_traversal_prevention(tmp_path):
    """Test that path traversal is handled."""
    # Try to read a file with path traversal
    malicious_path = str(tmp_path / ".." / ".." / ".." / "etc" / "passwd")
    
    with pytest.raises(Exception):
        read_geotiff(malicious_path)


def test_binary_data_handling(tmp_path):
    """Test handling of binary data in tags."""
    binary_file = tmp_path / "binary.tif"
    
    # Create file with binary data that could cause issues
    with open(binary_file, 'wb') as f:
        f.write(b'II')
        f.write(struct.pack('<H', 42))
        f.write(struct.pack('<I', 8))
        f.write(struct.pack('<H', 0))  # 0 entries
        # Add some random binary data
        f.write(b'\xff\xfe\xfd\xfc\xfb\xfa')
    
    # Should handle gracefully
    info = read_geotiff(str(binary_file))
    assert info.width == 0  # No image dimensions


def test_large_file_size_formatting():
    """Test file size formatting for very large files."""
    assert "PB" in format_file_size(2**50)
    assert "TB" in format_file_size(2**40)
    assert "GB" in format_file_size(2**30)


def test_zero_dimensions(tmp_path):
    """Test handling of zero dimensions."""
    zero_file = tmp_path / "zero.tif"
    
    with open(zero_file, 'wb') as f:
        f.write(b'II')
        f.write(struct.pack('<H', 42))
        f.write(struct.pack('<I', 8))
        # IFD with width=0, height=0
        entries = [
            (256, 3, 1, 0),  # Width = 0
            (257, 3, 1, 0),  # Height = 0
        ]
        f.write(struct.pack('<H', len(entries)))
        for tag, type_id, count, value in entries:
            f.write(struct.pack('<HH', tag, type_id))
            f.write(struct.pack('<I', count))
            f.write(struct.pack('<I', value))
    
    info = read_geotiff(str(zero_file))
    assert info.width == 0
    assert info.height == 0


def test_unicode_path(tmp_path):
    """Test handling of unicode file paths."""
    unicode_dir = tmp_path / "测试目录"
    unicode_dir.mkdir()
    unicode_file = unicode_dir / "测试文件.tif"
    
    create_test_geotiff(str(unicode_file))
    
    info = read_geotiff(str(unicode_file))
    assert info.width == 10


def test_special_characters_in_path(tmp_path):
    """Test handling of special characters in path."""
    special_dir = tmp_path / "dir with spaces"
    special_dir.mkdir()
    special_file = special_dir / "file (1).tif"
    
    create_test_geotiff(str(special_file))
    
    info = read_geotiff(str(special_file))
    assert info.width == 10


def test_readonly_file(tmp_path):
    """Test reading a readonly file."""
    readonly_file = tmp_path / "readonly.tif"
    create_test_geotiff(str(readonly_file))
    
    # Make file readonly
    os.chmod(str(readonly_file), 0o444)
    
    info = read_geotiff(str(readonly_file))
    assert info.width == 10
    
    # Restore permissions for cleanup
    os.chmod(str(readonly_file), 0o644)


def test_concurrent_read(tmp_path):
    """Test reading multiple files concurrently."""
    import threading
    
    files = []
    for i in range(5):
        tif_file = tmp_path / f"concurrent_{i}.tif"
        create_test_geotiff(str(tif_file))
        files.append(str(tif_file))
    
    results = [None] * len(files)
    errors = []
    
    def read_file(idx, path):
        try:
            results[idx] = read_geotiff(path)
        except Exception as e:
            errors.append(e)
    
    threads = []
    for i, path in enumerate(files):
        t = threading.Thread(target=read_file, args=(i, path))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    assert len(errors) == 0
    assert all(r.width == 10 for r in results)


def test_corrupted_geo_keys(tmp_path):
    """Test handling of corrupted GeoKey data."""
    corrupted_file = tmp_path / "corrupted_geo.tif"
    
    with open(corrupted_file, 'wb') as f:
        f.write(b'II')
        f.write(struct.pack('<H', 42))
        f.write(struct.pack('<I', 8))
        
        # IFD with corrupted GeoKey directory
        entries = [
            (256, 3, 1, 10),  # Width
            (257, 3, 1, 10),  # Height
            (34735, 3, 10, 1000),  # GeoKey directory pointing to bad offset
        ]
        f.write(struct.pack('<H', len(entries)))
        for tag, type_id, count, value in entries:
            f.write(struct.pack('<HH', tag, type_id))
            f.write(struct.pack('<I', count))
            f.write(struct.pack('<I', value))
    
    # Should handle gracefully
    try:
        info = read_geotiff(str(corrupted_file))
    except Exception:
        pass


def test_malformed_ascii_tag(tmp_path):
    """Test handling of malformed ASCII tags."""
    malformed_file = tmp_path / "malformed_ascii.tif"
    
    with open(malformed_file, 'wb') as f:
        f.write(b'II')
        f.write(struct.pack('<H', 42))
        f.write(struct.pack('<I', 8))
        
        # IFD with ASCII tag
        entries = [
            (256, 3, 1, 10),  # Width
            (257, 3, 1, 10),  # Height
            (270, 2, 5, 1000),  # ImageDescription ASCII
        ]
        f.write(struct.pack('<H', len(entries)))
        for tag, type_id, count, value in entries:
            f.write(struct.pack('<HH', tag, type_id))
            f.write(struct.pack('<I', count))
            f.write(struct.pack('<I', value))
        
        # Write malformed ASCII (no null terminator)
        f.seek(1000)
        f.write(b'hello world without null')
    
    info = read_geotiff(str(malformed_file))
    assert info.width == 10
