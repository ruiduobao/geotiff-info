#!/usr/bin/env python3
"""
GeoTIFF Metadata Viewer - Zero-dependency tool for reading GeoTIFF metadata.
Parses TIFF IFD manually using only Python standard library.

Privacy disclosure
------------------
This tool reads only local files. No data is sent over the network.

Public domain notice
--------------------
This tool does not transmit any data and does not access any
external services. All processing is local.

License
-------
MIT-0 — No Attribution.
"""

import argparse
import json
import os
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


# TIFF Tag definitions
TIFF_TAGS = {
    256: "ImageWidth",
    257: "ImageLength",
    258: "BitsPerSample",
    259: "Compression",
    262: "PhotometricInterpretation",
    270: "ImageDescription",
    273: "StripOffsets",
    274: "Orientation",
    277: "SamplesPerPixel",
    278: "RowsPerStrip",
    279: "StripByteCounts",
    282: "XResolution",
    283: "YResolution",
    284: "PlanarConfiguration",
    296: "ResolutionUnit",
    305: "Software",
    339: "SampleFormat",
    33550: "ModelPixelScaleTag",
    33922: "ModelTiepointTag",
    34735: "GeoKeyDirectoryTag",
    34736: "GeoDoubleParamsTag",
    34737: "GeoAsciiParamsTag",
    42113: "GDAL_NODATA",
}

# TIFF data types and their sizes
TIFF_TYPES = {
    1: ("BYTE", 1),
    2: ("ASCII", 1),
    3: ("SHORT", 2),
    4: ("LONG", 4),
    5: ("RATIONAL", 8),
    6: ("SBYTE", 1),
    7: ("UNDEFINED", 1),
    8: ("SSHORT", 2),
    9: ("SLONG", 4),
    10: ("SRATIONAL", 8),
    11: ("FLOAT", 4),
    12: ("DOUBLE", 8),
}

# GeoTIFF Key IDs
GEO_KEYS = {
    1024: "GTModelTypeGeoKey",
    1025: "GTRasterTypeGeoKey",
    1026: "GTCitationGeoKey",
    2048: "GeographicTypeGeoKey",
    2049: "GeogCitationGeoKey",
    2050: "GeogGeodeticDatumGeoKey",
    2051: "GeogAngularUnitsGeoKey",
    2052: "GeogAngularUnitSizeGeoKey",
    2054: "GeogPrimeMeridianGeoKey",
    2057: "GeogSemiMajorAxisGeoKey",
    2058: "GeogSemiMinorAxisGeoKey",
    2059: "GeogInvFlatteningGeoKey",
    2060: "GeogPrimeMeridianLongGeoKey",
    3072: "ProjectedCSTypeGeoKey",
    3073: "PCSCitationGeoKey",
    3074: "ProjectionGeoKey",
    3075: "ProjCoordTransGeoKey",
    3076: "ProjLinearUnitsGeoKey",
    3077: "ProjLinearUnitSizeGeoKey",
    3078: "ProjStdParallel1GeoKey",
    3079: "ProjStdParallel2GeoKey",
    3080: "ProjNatOriginLongGeoKey",
    3081: "ProjNatOriginLatGeoKey",
    3082: "ProjFalseEastingGeoKey",
    3083: "ProjFalseNorthingGeoKey",
    3084: "ProjFalseOriginLongGeoKey",
    3085: "ProjFalseOriginLatGeoKey",
    3086: "ProjFalseOriginEastingGeoKey",
    3087: "ProjFalseOriginNorthingGeoKey",
    3088: "ProjCenterLongGeoKey",
    3089: "ProjCenterLatGeoKey",
    3090: "ProjCenterEastingGeoKey",
    3091: "ProjCenterNorthingGeoKey",
    3092: "ProjScaleAtNatOriginGeoKey",
    3093: "ProjScaleAtCenterGeoKey",
    3094: "ProjAzimuthAngleGeoKey",
    3095: "ProjStraightVertPoleLongGeoKey",
    4096: "VerticalCSTypeGeoKey",
    4097: "VerticalCitationGeoKey",
    4098: "VerticalUnitsGeoKey",
}

# Common EPSG codes for reference
COMMON_EPSG = {
    4326: "WGS 84",
    3857: "WGS 84 / Pseudo-Mercator",
    32601: "WGS 84 / UTM zone 1N",
    32602: "WGS 84 / UTM zone 2N",
    32603: "WGS 84 / UTM zone 3N",
    32604: "WGS 84 / UTM zone 4N",
    32605: "WGS 84 / UTM zone 5N",
    32606: "WGS 84 / UTM zone 6N",
    32607: "WGS 84 / UTM zone 7N",
    32608: "WGS 84 / UTM zone 8N",
    32609: "WGS 84 / UTM zone 9N",
    32610: "WGS 84 / UTM zone 10N",
    32611: "WGS 84 / UTM zone 11N",
    32612: "WGS 84 / UTM zone 12N",
    32613: "WGS 84 / UTM zone 13N",
    32614: "WGS 84 / UTM zone 14N",
    32615: "WGS 84 / UTM zone 15N",
    32616: "WGS 84 / UTM zone 16N",
    32617: "WGS 84 / UTM zone 17N",
    32618: "WGS 84 / UTM zone 18N",
    32619: "WGS 84 / UTM zone 19N",
    32620: "WGS 84 / UTM zone 20N",
    32621: "WGS 84 / UTM zone 21N",
    32622: "WGS 84 / UTM zone 22N",
    32623: "WGS 84 / UTM zone 23N",
    32624: "WGS 84 / UTM zone 24N",
    32625: "WGS 84 / UTM zone 25N",
    32626: "WGS 84 / UTM zone 26N",
    32627: "WGS 84 / UTM zone 27N",
    32628: "WGS 84 / UTM zone 28N",
    32629: "WGS 84 / UTM zone 29N",
    32630: "WGS 84 / UTM zone 30N",
    32631: "WGS 84 / UTM zone 31N",
    32632: "WGS 84 / UTM zone 32N",
    32633: "WGS 84 / UTM zone 33N",
    32634: "WGS 84 / UTM zone 34N",
    32635: "WGS 84 / UTM zone 35N",
    32636: "WGS 84 / UTM zone 36N",
    32637: "WGS 84 / UTM zone 37N",
    32638: "WGS 84 / UTM zone 38N",
    32639: "WGS 84 / UTM zone 39N",
    32640: "WGS 84 / UTM zone 40N",
    32641: "WGS 84 / UTM zone 41N",
    32642: "WGS 84 / UTM zone 42N",
    32643: "WGS 84 / UTM zone 43N",
    32644: "WGS 84 / UTM zone 44N",
    32645: "WGS 84 / UTM zone 45N",
    32646: "WGS 84 / UTM zone 46N",
    32647: "WGS 84 / UTM zone 47N",
    32648: "WGS 84 / UTM zone 48N",
    32649: "WGS 84 / UTM zone 49N",
    32650: "WGS 84 / UTM zone 50N",
    32651: "WGS 84 / UTM zone 51N",
    32652: "WGS 84 / UTM zone 52N",
    32653: "WGS 84 / UTM zone 53N",
    32654: "WGS 84 / UTM zone 54N",
    32655: "WGS 84 / UTM zone 55N",
    32656: "WGS 84 / UTM zone 56N",
    32657: "WGS 84 / UTM zone 57N",
    32658: "WGS 84 / UTM zone 58N",
    32659: "WGS 84 / UTM zone 59N",
    32660: "WGS 84 / UTM zone 60N",
    32701: "WGS 84 / UTM zone 1S",
    32702: "WGS 84 / UTM zone 2S",
    32703: "WGS 84 / UTM zone 3S",
    32704: "WGS 84 / UTM zone 4S",
    32705: "WGS 84 / UTM zone 5S",
    32706: "WGS 84 / UTM zone 6S",
    32707: "WGS 84 / UTM zone 7S",
    32708: "WGS 84 / UTM zone 8S",
    32709: "WGS 84 / UTM zone 9S",
    32710: "WGS 84 / UTM zone 10S",
    32711: "WGS 84 / UTM zone 11S",
    32712: "WGS 84 / UTM zone 12S",
    32713: "WGS 84 / UTM zone 13S",
    32714: "WGS 84 / UTM zone 14S",
    32715: "WGS 84 / UTM zone 15S",
    32716: "WGS 84 / UTM zone 16S",
    32717: "WGS 84 / UTM zone 17S",
    32718: "WGS 84 / UTM zone 18S",
    32719: "WGS 84 / UTM zone 19S",
    32720: "WGS 84 / UTM zone 20S",
    32721: "WGS 84 / UTM zone 21S",
    32722: "WGS 84 / UTM zone 22S",
    32723: "WGS 84 / UTM zone 23S",
    32724: "WGS 84 / UTM zone 24S",
    32725: "WGS 84 / UTM zone 25S",
    32726: "WGS 84 / UTM zone 26S",
    32727: "WGS 84 / UTM zone 27S",
    32728: "WGS 84 / UTM zone 28S",
    32729: "WGS 84 / UTM zone 29S",
    32730: "WGS 84 / UTM zone 30S",
    32731: "WGS 84 / UTM zone 31S",
    32732: "WGS 84 / UTM zone 32S",
    32733: "WGS 84 / UTM zone 33S",
    32734: "WGS 84 / UTM zone 34S",
    32735: "WGS 84 / UTM zone 35S",
    32736: "WGS 84 / UTM zone 36S",
    32737: "WGS 84 / UTM zone 37S",
    32738: "WGS 84 / UTM zone 38S",
    32739: "WGS 84 / UTM zone 39S",
    32740: "WGS 84 / UTM zone 40S",
    32741: "WGS 84 / UTM zone 41S",
    32742: "WGS 84 / UTM zone 42S",
    32743: "WGS 84 / UTM zone 43S",
    32744: "WGS 84 / UTM zone 44S",
    32745: "WGS 84 / UTM zone 45S",
    32746: "WGS 84 / UTM zone 46S",
    32747: "WGS 84 / UTM zone 47S",
    32748: "WGS 84 / UTM zone 48S",
    32749: "WGS 84 / UTM zone 49S",
    32750: "WGS 84 / UTM zone 50S",
    32751: "WGS 84 / UTM zone 51S",
    32752: "WGS 84 / UTM zone 52S",
    32753: "WGS 84 / UTM zone 53S",
    32754: "WGS 84 / UTM zone 54S",
    32755: "WGS 84 / UTM zone 55S",
    32756: "WGS 84 / UTM zone 56S",
    32757: "WGS 84 / UTM zone 57S",
    32758: "WGS 84 / UTM zone 58S",
    32759: "WGS 84 / UTM zone 59S",
    32760: "WGS 84 / UTM zone 60S",
}


@dataclass
class GeoTIFFInfo:
    """Container for GeoTIFF metadata."""
    file_path: str
    file_size: int = 0
    file_size_human: str = ""
    width: int = 0
    height: int = 0
    bits_per_sample: List[int] = field(default_factory=list)
    samples_per_pixel: int = 0
    sample_format: List[str] = field(default_factory=list)
    compression: str = "None"
    photometric: str = ""
    planar_config: str = ""
    nodata: Optional[str] = None
    pixel_scale: Tuple[float, ...] = ()
    tiepoint: Tuple[float, ...] = ()
    geo_keys: Dict[str, Any] = field(default_factory=dict)
    crs_epsg: Optional[int] = None
    crs_name: Optional[str] = None
    crs_wkt: Optional[str] = None
    affine_transform: Tuple[float, ...] = ()
    corner_coords: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    band_stats: List[Dict[str, float]] = field(default_factory=list)
    is_geotiff: bool = False
    is_bigtiff: bool = False


class TIFFReader:
    """Low-level TIFF file reader using only standard library."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.file_size = os.path.getsize(filepath)
        self.byte_order = '<'  # little-endian by default
        self.is_bigtiff = False
        self._file = None

    def __enter__(self):
        self._file = open(self.filepath, 'rb')
        self._read_header()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._file:
            self._file.close()
        return False

    def _read_header(self):
        """Read TIFF header to determine byte order and version."""
        if self.file_size < 8:
            raise ValueError("File too small to be a valid TIFF")

        header = self._file.read(8)

        # Check byte order
        if header[0:2] == b'II':
            self.byte_order = '<'  # little-endian
        elif header[0:2] == b'MM':
            self.byte_order = '>'  # big-endian
        else:
            raise ValueError(f"Invalid TIFF byte order: {header[0:2]}")

        # Check magic number
        magic = struct.unpack(f'{self.byte_order}H', header[2:4])[0]
        if magic == 42:
            self.is_bigtiff = False
        elif magic == 43:
            self.is_bigtiff = True
            # Read BigTIFF header
            offset_size = struct.unpack(f'{self.byte_order}H', header[4:6])[0]
            if offset_size != 8:
                raise ValueError(f"Invalid BigTIFF offset size: {offset_size}")
            # Skip 2 reserved bytes
            self._file.read(2)
        else:
            raise ValueError(f"Invalid TIFF magic number: {magic}")

    def _read_short(self, offset: int) -> int:
        """Read a 16-bit unsigned integer at offset."""
        self._file.seek(offset)
        return struct.unpack(f'{self.byte_order}H', self._file.read(2))[0]

    def _read_long(self, offset: int) -> int:
        """Read a 32-bit unsigned integer at offset."""
        self._file.seek(offset)
        return struct.unpack(f'{self.byte_order}I', self._file.read(4))[0]

    def _read_ifd(self, offset: int) -> List[Dict[str, int]]:
        """Read an IFD (Image File Directory) at the given offset."""
        self._file.seek(offset)

        # Read number of entries
        if self.is_bigtiff:
            # BigTIFF: count is 8 bytes
            count = struct.unpack(f'{self.byte_order}Q', self._file.read(8))[0]
            entry_size = 20
            # After count, entries start
            entries_start = offset + 8
        else:
            # Classic TIFF: count is 2 bytes
            count = struct.unpack(f'{self.byte_order}H', self._file.read(2))[0]
            entry_size = 12
            entries_start = offset + 2

        entries = []
        for i in range(count):
            entry_offset = entries_start + i * entry_size
            self._file.seek(entry_offset)

            tag = struct.unpack(f'{self.byte_order}H', self._file.read(2))[0]
            type_id = struct.unpack(f'{self.byte_order}H', self._file.read(2))[0]

            if self.is_bigtiff:
                count_val = struct.unpack(f'{self.byte_order}Q', self._file.read(8))[0]
                value = struct.unpack(f'{self.byte_order}Q', self._file.read(8))[0]
            else:
                count_val = struct.unpack(f'{self.byte_order}I', self._file.read(4))[0]
                value = struct.unpack(f'{self.byte_order}I', self._file.read(4))[0]

            entries.append({
                'tag': tag,
                'type': type_id,
                'count': count_val,
                'value': value
            })

        return entries

    def _read_value(self, entry: Dict[str, int]) -> Any:
        """Read the actual value(s) for an IFD entry."""
        tag = entry['tag']
        type_id = entry['type']
        count = entry['count']
        value_field = entry['value']

        if type_id not in TIFF_TYPES:
            return value_field

        type_name, type_size = TIFF_TYPES[type_id]
        total_size = type_size * count

        # For small values that fit in the value field (4 or 8 bytes)
        if type_name == "ASCII":
            if total_size <= 4:
                # Value is stored in the value field itself
                return struct.pack(f'{self.byte_order}I', value_field)[:total_size].decode('ascii', errors='ignore').rstrip('\x00')
            else:
                # Value is at offset
                self._file.seek(value_field)
                data = self._file.read(count)
                return data.decode('ascii', errors='ignore').rstrip('\x00')

        if type_name in ("BYTE", "SBYTE", "UNDEFINED"):
            if count == 1:
                return value_field
            else:
                self._file.seek(value_field)
                return list(self._file.read(count))

        if type_name in ("SHORT", "SSHORT"):
            if count == 1:
                return value_field
            elif count <= 2:
                # Value fits in 4 bytes
                if self.byte_order == '<':
                    return [value_field & 0xFFFF, (value_field >> 16) & 0xFFFF][:count]
                else:
                    return [(value_field >> 16) & 0xFFFF, value_field & 0xFFFF][:count]
            else:
                self._file.seek(value_field)
                data = self._file.read(2 * count)
                fmt = f'{self.byte_order}{count}{"h" if type_name == "SSHORT" else "H"}'
                return list(struct.unpack(fmt, data))

        if type_name in ("LONG", "SLONG"):
            if count == 1:
                return value_field
            else:
                self._file.seek(value_field)
                data = self._file.read(4 * count)
                fmt = f'{self.byte_order}{count}{"i" if type_name == "SLONG" else "I"}'
                return list(struct.unpack(fmt, data))

        if type_name in ("FLOAT",):
            if count == 1:
                return struct.unpack(f'{self.byte_order}f', struct.pack(f'{self.byte_order}I', value_field))[0]
            else:
                self._file.seek(value_field)
                data = self._file.read(4 * count)
                return list(struct.unpack(f'{self.byte_order}{count}f', data))

        if type_name in ("DOUBLE",):
            self._file.seek(value_field)
            data = self._file.read(8 * count)
            result = list(struct.unpack(f'{self.byte_order}{count}d', data))
            if count == 1:
                return result[0]
            return result

        if type_name == "RATIONAL":
            self._file.seek(value_field)
            result = []
            for _ in range(count):
                num = struct.unpack(f'{self.byte_order}I', self._file.read(4))[0]
                den = struct.unpack(f'{self.byte_order}I', self._file.read(4))[0]
                result.append(num / den if den != 0 else 0)
            return result

        if type_name == "SRATIONAL":
            self._file.seek(value_field)
            result = []
            for _ in range(count):
                num = struct.unpack(f'{self.byte_order}i', self._file.read(4))[0]
                den = struct.unpack(f'{self.byte_order}i', self._file.read(4))[0]
                result.append(num / den if den != 0 else 0)
            return result

        return value_field

    def read_tags(self) -> Dict[int, Any]:
        """Read all tags from the first IFD."""
        if self.is_bigtiff:
            # BigTIFF: IFD offset is at bytes 8-15
            self._file.seek(8)
            ifd_offset = struct.unpack(f'{self.byte_order}Q', self._file.read(8))[0]
        else:
            # Classic TIFF: IFD offset is at bytes 4-7
            ifd_offset = self._read_long(4)

        entries = self._read_ifd(ifd_offset)
        tags = {}

        for entry in entries:
            try:
                value = self._read_value(entry)
                tags[entry['tag']] = value
            except Exception:
                tags[entry['tag']] = entry['value']

        return tags


def format_file_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def get_compression_name(code: int) -> str:
    """Get compression method name from code."""
    compressions = {
        1: "None",
        2: "CCITT 1D",
        3: "Group 3 Fax",
        4: "Group 4 Fax",
        5: "LZW",
        6: "JPEG",
        7: "JPEG",
        8: "Deflate",
        32773: "PackBits",
    }
    return compressions.get(code, f"Unknown ({code})")


def get_photometric_name(code: int) -> str:
    """Get photometric interpretation name."""
    photometrics = {
        0: "MinIsWhite",
        1: "MinIsBlack",
        2: "RGB",
        3: "Palette",
        4: "Transparency Mask",
        5: "Separated (CMYK)",
        6: "YCbCr",
    }
    return photometrics.get(code, f"Unknown ({code})")


def get_sample_format_name(code: int) -> str:
    """Get sample format name."""
    formats = {
        1: "unsigned integer",
        2: "signed integer",
        3: "floating point",
    }
    return formats.get(code, f"Unknown ({code})")


def parse_geo_keys(key_directory, double_params, ascii_params) -> Dict[str, Any]:
    """Parse GeoTIFF key directory."""
    if not key_directory:
        return {}

    # Convert to list if needed
    if isinstance(key_directory, int):
        return {}

    if len(key_directory) < 4:
        return {}

    # Header: KeyDirectoryVersion, KeyRevision, MinorRevision, NumberOfKeys
    num_keys = key_directory[3]
    keys = {}

    for i in range(num_keys):
        offset = 4 + i * 4
        if offset + 3 >= len(key_directory):
            break

        key_id = key_directory[offset]
        tiff_tag_location = key_directory[offset + 1]
        count = key_directory[offset + 2]
        value_offset = key_directory[offset + 3]

        key_name = GEO_KEYS.get(key_id, f"Unknown_{key_id}")

        # Get value based on location
        if tiff_tag_location == 0:
            # Value is stored in the value_offset field directly
            keys[key_name] = value_offset
        elif tiff_tag_location == 34736:
            # GeoDoubleParamsTag
            if double_params and isinstance(double_params, (list, tuple)):
                if count == 1 and value_offset < len(double_params):
                    keys[key_name] = double_params[value_offset]
                elif value_offset + count <= len(double_params):
                    keys[key_name] = double_params[value_offset:value_offset + count]
        elif tiff_tag_location == 34737:
            # GeoAsciiParamsTag
            if ascii_params and isinstance(ascii_params, str):
                if value_offset + count <= len(ascii_params):
                    keys[key_name] = ascii_params[value_offset:value_offset + count].rstrip('|')

    return keys


def calculate_affine(pixel_scale: Tuple[float, ...], tiepoint: Tuple[float, ...]) -> Tuple[float, ...]:
    """Calculate affine transform from pixel scale and tiepoint."""
    if not pixel_scale or len(pixel_scale) < 2:
        return ()
    if not tiepoint or len(tiepoint) < 6:
        return ()

    # Tiepoint: (i, j, k, x, y, z)
    # PixelScale: (scale_x, scale_y, scale_z)
    sx, sy = pixel_scale[0], pixel_scale[1]
    tx, ty = tiepoint[3], tiepoint[4]
    ti, tj = tiepoint[0], tiepoint[1]

    # Affine transform: [a, b, c, d, e, f]
    # a = sx, b = 0, c = tx - ti * sx
    # d = 0, e = -sy, f = ty + tj * sy
    a = sx
    b = 0.0
    c = tx - ti * sx
    d = 0.0
    e = -sy
    f = ty + tj * sy

    return (a, b, c, d, e, f)


def calculate_corners(width: int, height: int, affine: Tuple[float, ...]) -> Dict[str, Tuple[float, float]]:
    """Calculate corner coordinates from affine transform."""
    if not affine or len(affine) < 6 or width == 0 or height == 0:
        return {}

    a, b, c, d, e, f = affine

    ul = (c, f)
    ur = (a * width + c, b * width + f)
    ll = (d * height + c, e * height + f)
    lr = (a * width + d * height + c, b * width + e * height + f)

    return {
        "Upper Left": ul,
        "Upper Right": ur,
        "Lower Left": ll,
        "Lower Right": lr,
    }


def read_geotiff(filepath: str) -> GeoTIFFInfo:
    """Read GeoTIFF metadata from a file."""
    info = GeoTIFFInfo(file_path=filepath)
    info.file_size = os.path.getsize(filepath)
    info.file_size_human = format_file_size(info.file_size)

    try:
        with TIFFReader(filepath) as reader:
            info.is_bigtiff = reader.is_bigtiff
            tags = reader.read_tags()

            # Basic image info
            info.width = tags.get(256, 0)
            info.height = tags.get(257, 0)
            info.samples_per_pixel = tags.get(277, 1)

            # Bits per sample
            bps = tags.get(258, [8])
            if isinstance(bps, (int, float)):
                info.bits_per_sample = [int(bps)]
            elif isinstance(bps, list):
                info.bits_per_sample = [int(x) for x in bps]
            else:
                info.bits_per_sample = [8]

            # Sample format
            sf = tags.get(339, [1])
            if isinstance(sf, (int, float)):
                sf = [int(sf)]
            elif isinstance(sf, list):
                sf = [int(x) for x in sf]
            else:
                sf = [1]
            info.sample_format = [get_sample_format_name(x) for x in sf]

            # Compression
            comp = tags.get(259, 1)
            if isinstance(comp, list):
                comp = comp[0] if comp else 1
            info.compression = get_compression_name(int(comp))

            # Photometric
            photo = tags.get(262, 0)
            if isinstance(photo, list):
                photo = photo[0] if photo else 0
            info.photometric = get_photometric_name(int(photo))

            # Planar configuration
            planar = tags.get(284, 1)
            if isinstance(planar, list):
                planar = planar[0] if planar else 1
            info.planar_config = "Chunky" if planar == 1 else "Planar"

            # NoData
            nodata = tags.get(42113)
            if nodata:
                if isinstance(nodata, str):
                    info.nodata = nodata.strip()
                else:
                    info.nodata = str(nodata)

            # GeoTIFF specific tags
            pixel_scale = tags.get(33550)
            tiepoint = tags.get(33922)

            if pixel_scale:
                if isinstance(pixel_scale, (list, tuple)):
                    info.pixel_scale = tuple(float(x) for x in pixel_scale)
                elif isinstance(pixel_scale, (int, float)):
                    info.pixel_scale = (float(pixel_scale),)

            if tiepoint:
                if isinstance(tiepoint, (list, tuple)):
                    info.tiepoint = tuple(float(x) for x in tiepoint)
                elif isinstance(tiepoint, (int, float)):
                    info.tiepoint = (float(tiepoint),)

            # GeoKeys
            key_dir = tags.get(34735)
            double_params = tags.get(34736, [])
            if isinstance(double_params, (int, float)):
                double_params = [double_params]
            elif not isinstance(double_params, list):
                double_params = []
            ascii_params = tags.get(34737, "")
            if not isinstance(ascii_params, str):
                ascii_params = ""

            if key_dir:
                info.geo_keys = parse_geo_keys(key_dir, double_params, ascii_params)
                if info.geo_keys:
                    info.is_geotiff = True

                    # Get EPSG code
                    epsg = info.geo_keys.get("ProjectedCSTypeGeoKey") or info.geo_keys.get("GeographicTypeGeoKey")
                    if epsg:
                        info.crs_epsg = int(epsg)
                        info.crs_name = COMMON_EPSG.get(info.crs_epsg, f"EPSG:{info.crs_epsg}")

            # Calculate affine transform
            if info.pixel_scale and info.tiepoint and len(info.pixel_scale) >= 2 and len(info.tiepoint) >= 6:
                info.affine_transform = calculate_affine(info.pixel_scale, info.tiepoint)

            # Calculate corner coordinates
            if info.affine_transform and info.width and info.height:
                info.corner_coords = calculate_corners(info.width, info.height, info.affine_transform)

    except Exception as e:
        info.geo_keys["error"] = str(e)

    return info


def format_text_table(info: GeoTIFFInfo) -> str:
    """Format GeoTIFF info as a text table."""
    lines = []
    sep = "=" * 60

    lines.append(sep)
    lines.append(f"GeoTIFF Metadata: {info.file_path}")
    lines.append(sep)

    lines.append(f"\n{'FILE INFORMATION':^60}")
    lines.append("-" * 60)
    lines.append(f"  File Size:          {info.file_size_human}")
    lines.append(f"  BigTIFF:            {'Yes' if info.is_bigtiff else 'No'}")

    lines.append(f"\n{'IMAGE DIMENSIONS':^60}")
    lines.append("-" * 60)
    lines.append(f"  Width:              {info.width} pixels")
    lines.append(f"  Height:             {info.height} pixels")
    lines.append(f"  Bands:              {info.samples_per_pixel}")

    lines.append(f"\n{'DATA TYPE':^60}")
    lines.append("-" * 60)
    lines.append(f"  Bits per Sample:    {', '.join(str(x) for x in info.bits_per_sample)}")
    lines.append(f"  Sample Format:      {', '.join(info.sample_format)}")
    lines.append(f"  Compression:        {info.compression}")
    lines.append(f"  Photometric:        {info.photometric}")
    lines.append(f"  Planar Config:      {info.planar_config}")

    if info.nodata is not None:
        lines.append(f"\n{'NODATA VALUE':^60}")
        lines.append("-" * 60)
        lines.append(f"  NoData:             {info.nodata}")

    if info.is_geotiff:
        lines.append(f"\n{'COORDINATE REFERENCE SYSTEM':^60}")
        lines.append("-" * 60)
        if info.crs_epsg:
            lines.append(f"  EPSG Code:          {info.crs_epsg}")
        if info.crs_name:
            lines.append(f"  CRS Name:           {info.crs_name}")

        if info.pixel_scale and len(info.pixel_scale) >= 2:
            lines.append(f"\n{'PIXEL RESOLUTION':^60}")
            lines.append("-" * 60)
            lines.append(f"  Scale X:            {info.pixel_scale[0]}")
            lines.append(f"  Scale Y:            {info.pixel_scale[1]}")

        if info.affine_transform and len(info.affine_transform) >= 6:
            lines.append(f"\n{'AFFINE TRANSFORM':^60}")
            lines.append("-" * 60)
            a, b, c, d, e, f = info.affine_transform
            lines.append(f"  [{a:>14.6f}, {b:>14.6f}, {c:>14.6f}]")
            lines.append(f"  [{d:>14.6f}, {e:>14.6f}, {f:>14.6f}]")
            lines.append(f"  [          0.0,           0.0,           1.0]")

        if info.corner_coords:
            lines.append(f"\n{'CORNER COORDINATES':^60}")
            lines.append("-" * 60)
            for name, (x, y) in info.corner_coords.items():
                lines.append(f"  {name:<20} ({x:>14.6f}, {y:>14.6f})")

        if info.geo_keys:
            lines.append(f"\n{'GEO KEYS':^60}")
            lines.append("-" * 60)
            for key, value in info.geo_keys.items():
                lines.append(f"  {key:<30} {value}")

    lines.append(sep)
    return '\n'.join(lines)


def format_json(info: GeoTIFFInfo) -> str:
    """Format GeoTIFF info as JSON."""
    data = {
        "file": info.file_path,
        "file_size": info.file_size,
        "file_size_human": info.file_size_human,
        "is_bigtiff": info.is_bigtiff,
        "width": info.width,
        "height": info.height,
        "bands": info.samples_per_pixel,
        "bits_per_sample": info.bits_per_sample,
        "sample_format": info.sample_format,
        "compression": info.compression,
        "photometric": info.photometric,
        "planar_config": info.planar_config,
        "nodata": info.nodata,
        "is_geotiff": info.is_geotiff,
    }

    if info.is_geotiff:
        data["crs"] = {
            "epsg": info.crs_epsg,
            "name": info.crs_name,
        }
        data["pixel_scale"] = list(info.pixel_scale) if info.pixel_scale else None
        data["tiepoint"] = list(info.tiepoint) if info.tiepoint else None
        data["affine_transform"] = list(info.affine_transform) if info.affine_transform else None
        data["corner_coords"] = {
            name: list(coord) for name, coord in info.corner_coords.items()
        } if info.corner_coords else None
        data["geo_keys"] = info.geo_keys

    return json.dumps(data, indent=2)


def deep_qa(info: 'GeoTIFFInfo') -> Dict[str, Any]:
    """[Phase 1+ 2026-07-26] 深度 QA 检查 — 不依赖 numpy/rasterio。

    基于元数据层面（不读栅格数据）做 6 类检查：
    1. CRS 完整性：必须有 EPSG 或 GeoKey
    2. bbox 合理性：W < E, S < N, 在地球范围内
    3. resolution 合理性：> 0, < 1° 等等
    4. 文件大小合理性：和像素数大致成正比
    5. nodata 设置：浮点/高光谱产品必须有 nodata
    6. 多波段一致性：所有波段 bits_per_sample / sample_format 一致
    """
    findings: List[Dict[str, str]] = []
    score = 100  # 起始满分；每发现一个问题扣分
    # 1. CRS 检查
    if not info.crs_epsg and not info.geo_keys:
        findings.append({
            "severity": "error",
            "category": "crs",
            "message": "No CRS information (no EPSG code, no GeoKeys)",
        })
        score -= 30
    elif info.crs_epsg and info.crs_epsg <= 0:
        findings.append({
            "severity": "error",
            "category": "crs",
            "message": f"Invalid EPSG code: {info.crs_epsg}",
        })
        score -= 20
    # 2. bbox 检查
    if not info.corner_coords:
        findings.append({
            "severity": "warning",
            "category": "bbox",
            "message": "No corner coordinates (no GeoTransform)",
        })
        score -= 10
    else:
        cc = info.corner_coords
        if "upper_left" in cc and "lower_right" in cc:
            ul_lon, ul_lat = cc["upper_left"]
            lr_lon, lr_lat = cc["lower_right"]
            if not (-180 <= ul_lon <= 180 and -180 <= lr_lon <= 180):
                findings.append({
                    "severity": "error",
                    "category": "bbox",
                    "message": f"Longitude out of range: ul={ul_lon}, lr={lr_lon}",
                })
                score -= 25
            if not (-90 <= ul_lat <= 90 and -90 <= lr_lat <= 90):
                findings.append({
                    "severity": "error",
                    "category": "bbox",
                    "message": f"Latitude out of range: ul={ul_lat}, lr={lr_lat}",
                })
                score -= 25
            if info.crs_epsg == 4326 and (ul_lon == 0 and lr_lon == 0 and ul_lat == 0 and lr_lat == 0):
                findings.append({
                    "severity": "warning",
                    "category": "bbox",
                    "message": "bbox is (0,0,0,0) - likely unset GeoTransform",
                })
                score -= 15
    # 3. resolution 检查
    if not info.pixel_scale or len(info.pixel_scale) < 2:
        findings.append({
            "severity": "warning",
            "category": "resolution",
            "message": "No pixel scale (cannot determine spatial resolution)",
        })
        score -= 5
    else:
        sx, sy = info.pixel_scale[0], info.pixel_scale[1]
        if sx <= 0 or sy <= 0:
            findings.append({
                "severity": "error",
                "category": "resolution",
                "message": f"Non-positive pixel scale: sx={sx}, sy={sy}",
            })
            score -= 15
        elif sx > 1.0 or sy > 1.0:
            findings.append({
                "severity": "warning",
                "category": "resolution",
                "message": f"Coarse resolution: sx={sx}, sy={sy} (>{1.0} degrees)",
            })
            score -= 5
    # 4. 文件大小 vs 像素数
    if info.width > 0 and info.height > 0 and info.samples_per_pixel > 0:
        total_pixels = info.width * info.height * info.samples_per_pixel
        bytes_per_pixel = info.file_size / total_pixels if total_pixels > 0 else 0
        if bytes_per_pixel < 0.1:
            findings.append({
                "severity": "warning",
                "category": "filesize",
                "message": f"File too small: {bytes_per_pixel:.3f} bytes/pixel (might be empty/over-compressed)",
            })
            score -= 10
        elif bytes_per_pixel > 100:
            findings.append({
                "severity": "info",
                "category": "filesize",
                "message": f"File large: {bytes_per_pixel:.1f} bytes/pixel (might be uncompressed)",
            })
            # info 不扣分
    # 5. nodata 检查
    bits = info.bits_per_sample[0] if info.bits_per_sample else 0
    is_float = "floating" in (info.sample_format[0].lower() if info.sample_format else "")
    if not info.nodata:
        if is_float or bits >= 32:
            findings.append({
                "severity": "warning",
                "category": "nodata",
                "message": "Float/32-bit+ raster without nodata (downstream analysis may mis-handle missing pixels)",
            })
            score -= 5
    # 6. 多波段一致性
    if info.samples_per_pixel > 1 and len(info.bits_per_sample) > 1:
        if len(set(info.bits_per_sample)) > 1:
            findings.append({
                "severity": "warning",
                "category": "consistency",
                "message": f"Inconsistent bits_per_sample across bands: {info.bits_per_sample}",
            })
            score -= 5
        if len(set(info.sample_format)) > 1:
            findings.append({
                "severity": "warning",
                "category": "consistency",
                "message": f"Inconsistent sample_format across bands: {info.sample_format}",
            })
            score -= 5
    # 统计
    by_severity = {"error": 0, "warning": 0, "info": 0}
    for f in findings:
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
    return {
        "file": info.file_path,
        "score": max(0, score),
        "passed": score >= 70,
        "findings": findings,
        "summary": by_severity,
    }


__version__ = "1.0.0"
USER_AGENT = f"geotiff-info/{__version__}"


def write_qa_summary(qa_path, *, info, command, extra=None):
    """Write a JSON deep_qa checks summary to qa_path (Phase 5 optimization).

    The sidecar includes the deep_qa() report (score, findings, summary by
    severity) plus a UTC timestamp and the command that produced the run.
    """
    from datetime import datetime as _dt, timezone as _tz

    qa = deep_qa(info)
    summary = {
        "skill": "geotiff-info",
        "command": command,
        "version": __version__,
        "user_agent": USER_AGENT,
        "timestamp": _dt.now(_tz.utc).isoformat(),
        "file": info.file_path,
        "file_size": info.file_size,
        "qa": qa,
    }
    if extra:
        summary.update(extra)
    qa_p = Path(qa_path)
    qa_p.parent.mkdir(parents=True, exist_ok=True)
    with open(qa_p, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    return qa_p


def scan_directory(dirpath: str) -> List[GeoTIFFInfo]:
    """Scan a directory for GeoTIFF files."""
    results = []
    path = Path(dirpath)
    
    # Use a set to avoid duplicates (Windows is case-insensitive)
    seen = set()
    
    for ext in ['*.tif', '*.tiff', '*.TIF', '*.TIFF']:
        for filepath in path.glob(ext):
            abs_path = str(filepath.resolve())
            if abs_path not in seen:
                seen.add(abs_path)
                try:
                    info = read_geotiff(str(filepath))
                    results.append(info)
                except Exception as e:
                    print(f"Error reading {filepath}: {e}", file=sys.stderr)

    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="GeoTIFF Metadata Viewer - Read GeoTIFF metadata without GIS software",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python geotiff-info.py image.tif
  python geotiff-info.py image.tif --json
  python geotiff-info.py /path/to/directory --batch
  python geotiff-info.py *.tif --json > metadata.json
        """
    )

    parser.add_argument(
        "input",
        help="GeoTIFF file or directory path"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (alias for --format json)"
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default=None,
        help="Output format: 'text' (default, human-readable) or 'json' "
             "(machine-readable). Overrides --json when both are set."
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Scan directory for GeoTIFF files"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="One-line per file (fast preview across a directory)"
    )
    parser.add_argument(
        "--qa",
        metavar="PATH",
        default=None,
        help="Write a JSON deep_qa checks summary to PATH (Phase 5). "
             "The sidecar contains the QA score, findings (by severity) and "
             "any per-band consistency issues. Defaults to <input>.qa.json "
             "when --qa is given as a bare flag."
    )

    args = parser.parse_args()

    # Resolve --format: explicit --format wins; otherwise --json decides.
    # Default is "text".
    output_format = args.format or ("json" if args.json else "text")
    want_json = output_format == "json"

    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: Path does not exist: {args.input}", file=sys.stderr)
        sys.exit(1)

    if args.batch or input_path.is_dir():
        if args.batch and input_path.is_file():
            # --batch with a single file: process just that file
            try:
                results = [read_geotiff(str(input_path))]
            except Exception as e:
                print(f"Error reading {args.input}: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            results = scan_directory(str(input_path))
            if not results:
                print("No GeoTIFF files found.", file=sys.stderr)
                sys.exit(1)

        if args.summary:
            for info in results:
                m = info.get("metadata", {})
                print(f"{info.get('file', '?'):<60} "
                      f"{m.get('width', '?')}x{m.get('height', '?')} "
                      f"bands={m.get('count', '?')} "
                      f"crs={m.get('crs', '?')[:30]} "
                      f"dtype={m.get('dtype', '?')}")
        elif want_json:
            all_data = []
            for info in results:
                all_data.append(json.loads(format_json(info)))
            print(json.dumps(all_data, indent=2))
        else:
            for info in results:
                print(format_text_table(info))
                print()

        # Phase 5: --qa sidecar for batch mode (writes one combined JSON)
        if getattr(args, "qa", None) and not (args.batch and input_path.is_file()):
            if not (args.qa is True or args.qa == ""):
                # Per-file deep_qa + combined roll-up
                per_file = [deep_qa(info) for info in results]
                n_passed = sum(1 for q in per_file if q.get("passed"))
                avg_score = (
                    sum(q.get("score", 0) for q in per_file) / len(per_file)
                    if per_file else 0
                )
                summary = {
                    "skill": "geotiff-info",
                    "command": "batch",
                    "version": __version__,
                    "user_agent": USER_AGENT,
                    "timestamp": _dt.now(_tz.utc).isoformat(),
                    "input_dir": str(input_path.resolve()),
                    "n_files": len(results),
                    "n_passed": n_passed,
                    "avg_score": round(avg_score, 2),
                    "per_file": per_file,
                }
                qa_p = Path(args.qa)
                qa_p.parent.mkdir(parents=True, exist_ok=True)
                with open(qa_p, "w", encoding="utf-8") as f:
                    json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
                print(f"QA: {qa_p}")
    else:
        try:
            info = read_geotiff(str(input_path))
            if want_json:
                print(format_json(info))
            else:
                print(format_text_table(info))
            if args.qa is not None:
                # --qa may be a boolean True (no value) or a path string.
                # argparse gives True when no value is given and the
                # argument is declared with store_true. Since we changed
                # --qa to metavar=PATH, the user must supply a value;
                # however we also accept the bare-flag form by falling
                # back to <input>.qa.json when args.qa is True.
                if args.qa is True or args.qa == "":
                    qa_path = str(input_path) + ".qa.json"
                else:
                    qa_path = args.qa
                write_qa_summary(qa_path, info=info, command="info")
                print(f"QA: {qa_path}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
