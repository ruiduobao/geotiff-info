"""Pytest configuration for geotiff-info tests."""

import importlib.util
import sys
import os
import struct
import tempfile
from pathlib import Path

# Load geotiff-info.py as a module since it has a hyphen in the name
def load_geotiff_info():
    """Load geotiff-info.py as a module."""
    spec = importlib.util.spec_from_file_location(
        "geotiff_info",
        os.path.join(os.path.dirname(__file__), "..", "geotiff-info.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Import the module
geotiff_info = load_geotiff_info()

# Make functions available at module level
TIFFReader = geotiff_info.TIFFReader
GeoTIFFInfo = geotiff_info.GeoTIFFInfo
read_geotiff = geotiff_info.read_geotiff
format_file_size = geotiff_info.format_file_size
get_compression_name = geotiff_info.get_compression_name
get_photometric_name = geotiff_info.get_photometric_name
get_sample_format_name = geotiff_info.get_sample_format_name
parse_geo_keys = geotiff_info.parse_geo_keys
calculate_affine = geotiff_info.calculate_affine
calculate_corners = geotiff_info.calculate_corners
format_text_table = geotiff_info.format_text_table
format_json = geotiff_info.format_json
scan_directory = geotiff_info.scan_directory


def create_test_geotiff(filepath: str, width: int = 10, height: int = 10,
                        bits_per_sample: int = 16, sample_format: int = 1,
                        include_geo: bool = True, bigtiff: bool = False,
                        byte_order: str = '<', nodata: float = None,
                        compression: int = 1) -> None:
    """Create a minimal test GeoTIFF file."""
    bo = byte_order
    
    with open(filepath, 'wb') as f:
        # Write header
        if bo == '<':
            f.write(b'II')  # Little-endian
        else:
            f.write(b'MM')  # Big-endian
        
        # Magic number
        magic = 43 if bigtiff else 42
        f.write(struct.pack(f'{bo}H', magic))
        
        if bigtiff:
            # BigTIFF header: offset_size(2) + reserved(2) + IFD_offset(8)
            f.write(struct.pack(f'{bo}H', 8))  # Offset size
            f.write(struct.pack(f'{bo}H', 0))  # Reserved
            ifd_offset = 16
            f.write(struct.pack(f'{bo}Q', ifd_offset))  # IFD offset
        else:
            # Classic TIFF: IFD_offset(4)
            ifd_offset = 8
            f.write(struct.pack(f'{bo}I', ifd_offset))  # IFD offset
        
        # Calculate data block offsets
        # After header + IFD count + IFD entries + next_ifd pointer
        # Count the actual entries we'll have
        num_entries = 7  # base entries: 256, 257, 258, 259, 262, 277, 339
        if include_geo:
            num_entries += 3  # pixel_scale, tiepoint, geo_keys
            if nodata is not None:
                num_entries += 1
        
        if bigtiff:
            # header(16) + count(8) + entries(num*20) + next_ifd(8)
            data_start = 16 + 8 + num_entries * 20 + 8
        else:
            # header(8) + count(2) + entries(num*12) + next_ifd(4)
            data_start = 8 + 2 + num_entries * 12 + 4
        
        # Align to 8 bytes for doubles
        data_start = (data_start + 7) & ~7
        
        # Prepare data block
        pixel_scale_offset = data_start
        tiepoint_offset = pixel_scale_offset + 24  # 3 doubles = 24 bytes
        geo_key_offset = tiepoint_offset + 48  # 6 doubles = 48 bytes
        
        # GeoKey data: version=1, revision=1, minor=0, 2 keys
        # Key 1: GTModelTypeGeoKey(1024) = 2 (Geographic)
        # Key 2: GeographicTypeGeoKey(2048) = 4326 (WGS84)
        geo_key_data = [1, 1, 0, 2, 1024, 0, 1, 2, 2048, 0, 1, 4326]
        
        nodata_offset = geo_key_offset + len(geo_key_data) * 2  # 12 shorts = 24 bytes
        
        # Prepare IFD entries - tag, type, count, value
        entries = []
        
        # ImageWidth (tag 256) - SHORT
        entries.append((256, 3, 1, width))
        
        # ImageLength (tag 257) - SHORT
        entries.append((257, 3, 1, height))
        
        # BitsPerSample (tag 258) - SHORT
        entries.append((258, 3, 1, bits_per_sample))
        
        # Compression (tag 259) - SHORT
        entries.append((259, 3, 1, compression))
        
        # PhotometricInterpretation (tag 262) - SHORT
        entries.append((262, 3, 1, 1))  # MinIsBlack
        
        # SamplesPerPixel (tag 277) - SHORT
        entries.append((277, 3, 1, 1))
        
        # SampleFormat (tag 339) - SHORT
        entries.append((339, 3, 1, sample_format))
        
        if include_geo:
            # ModelPixelScaleTag (33550) - DOUBLE[3]
            entries.append((33550, 12, 3, pixel_scale_offset))
            
            # ModelTiepointTag (33922) - DOUBLE[6]
            entries.append((33922, 12, 6, tiepoint_offset))
            
            # GeoKeyDirectoryTag (34735) - SHORT[12]
            entries.append((34735, 3, len(geo_key_data), geo_key_offset))
            
            if nodata is not None:
                nodata_str = str(nodata)
                # For ASCII type, if string is <= 4 bytes, store in value field
                # Otherwise store at offset
                if len(nodata_str) + 1 <= 4:
                    # Store in value field (pack as 4 bytes)
                    nodata_bytes = (nodata_str + '\x00').encode('ascii').ljust(4, b'\x00')
                    nodata_value = struct.unpack(f'{bo}I', nodata_bytes)[0]
                    entries.append((42113, 2, len(nodata_str) + 1, nodata_value))
                else:
                    entries.append((42113, 2, len(nodata_str) + 1, nodata_offset))
        
        # Sort entries by tag number (required by TIFF spec)
        entries.sort(key=lambda x: x[0])
        
        # Write IFD
        if bigtiff:
            f.write(struct.pack(f'{bo}Q', len(entries)))
            for tag, type_id, count, value in entries:
                f.write(struct.pack(f'{bo}H', tag))
                f.write(struct.pack(f'{bo}H', type_id))
                f.write(struct.pack(f'{bo}Q', count))
                f.write(struct.pack(f'{bo}Q', value))
            f.write(struct.pack(f'{bo}Q', 0))  # Next IFD offset
        else:
            f.write(struct.pack(f'{bo}H', len(entries)))
            for tag, type_id, count, value in entries:
                f.write(struct.pack(f'{bo}H', tag))
                f.write(struct.pack(f'{bo}H', type_id))
                f.write(struct.pack(f'{bo}I', count))
                f.write(struct.pack(f'{bo}I', value))
            f.write(struct.pack(f'{bo}I', 0))  # Next IFD offset
        
        # Write data blocks
        if include_geo:
            # Write pixel scale (3 doubles)
            f.seek(pixel_scale_offset)
            f.write(struct.pack(f'{bo}ddd', 0.000277777777778, 0.000277777777778, 0.0))
            
            # Write tiepoint (6 doubles)
            f.seek(tiepoint_offset)
            f.write(struct.pack(f'{bo}dddddd', 0.0, 0.0, 0.0, 115.0, 40.0, 0.0))
            
            # Write GeoKey directory (12 shorts)
            f.seek(geo_key_offset)
            for val in geo_key_data:
                f.write(struct.pack(f'{bo}H', val))
            
            # Write nodata string (only if stored at offset)
            if nodata is not None:
                nodata_str = str(nodata)
                if len(nodata_str) + 1 > 4:
                    f.seek(nodata_offset)
                    f.write(nodata_str.encode('ascii') + b'\x00')
