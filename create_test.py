"""Create a minimal valid GeoTIFF for testing."""
import struct, os

def create_geotiff(filepath, width=10, height=10):
    nodata = -9999.0
    E = '<'  # little-endian
    
    # Pixel data as float32
    pixel_bytes = bytearray()
    for row in range(height):
        for col in range(width):
            val = 100.0 + row * 10.0 + col
            pixel_bytes.extend(struct.pack(E + 'f', val))
    raw_pixel_data = bytes(pixel_bytes)
    
    nodata_str = str(nodata)
    
    # GeoKey directory for EPSG:4326
    # Header(4 shorts) + 3 keys(4 shorts each) = 16 shorts = 32 bytes
    geo_keys = struct.pack(E + 'HHHH', 1, 1, 1, 3)
    geo_keys += struct.pack(E + 'HHHH', 1024, 0, 1, 2)      # ModelType=Geographic
    geo_keys += struct.pack(E + 'HHHH', 2048, 0, 1, 4326)    # EPSG=4326
    geo_keys += struct.pack(E + 'HHHH', 2049, 34737, 6, 0)   # Citation in GeoAscii
    geo_ascii = b'WGS 84|'
    
    num_tags = 19
    
    ifd_size = 2 + num_tags * 12 + 4  # count + entries + next_ifd
    data_offset = 8 + ifd_size
    
    # Extra section: XRes(8) YRes(8) PixelScale(24) Tiepoint(48) NoData GeoKeys GeoAscii
    xres_off = data_offset
    yres_off = data_offset + 8
    ps_off = data_offset + 16
    tp_off = data_offset + 40
    nd_off = data_offset + 88
    gk_off = nd_off + len(nodata_str) + 1
    ga_off = gk_off + len(geo_keys)
    strip_offset = ga_off + len(geo_ascii)
    
    # Build extra data
    extra = bytearray()
    extra.extend(struct.pack(E + 'II', 1, 1))       # XRes
    extra.extend(struct.pack(E + 'II', 1, 1))       # YRes
    extra.extend(struct.pack(E + 'ddd', 0.001, 0.001, 0.0))
    extra.extend(struct.pack(E + 'dddddd', 0,0,0, 116.0, 40.0, 0.0))
    extra.extend(nodata_str.encode('ascii') + b'\x00')
    extra.extend(geo_keys)
    extra.extend(geo_ascii)
    
    assert data_offset + len(extra) == strip_offset
    
    # Header
    header = b'II' + struct.pack(E + 'HI', 42, 8)
    
    # IFD
    ifd = struct.pack(E + 'H', num_tags)
    def entry(tag, typ, count, val):
        return struct.pack(E + 'HHI', tag, typ, count) + struct.pack(E + 'I', val)
    
    ifd += entry(256, 4, 1, width)
    ifd += entry(257, 4, 1, height)
    ifd += entry(258, 3, 1, 32)
    ifd += entry(259, 3, 1, 1)
    ifd += entry(262, 3, 1, 1)
    ifd += entry(273, 4, 1, strip_offset)
    ifd += entry(277, 3, 1, 1)
    ifd += entry(278, 4, 1, height)
    ifd += entry(279, 4, 1, len(raw_pixel_data))
    ifd += entry(282, 5, 1, xres_off)
    ifd += entry(283, 5, 1, yres_off)
    ifd += entry(284, 3, 1, 1)
    ifd += entry(296, 3, 1, 1)
    ifd += entry(339, 3, 1, 3)
    ifd += entry(33550, 12, 3, ps_off)
    ifd += entry(33922, 12, 6, tp_off)
    ifd += entry(42113, 2, len(nodata_str), nd_off)
    ifd += entry(34735, 3, len(geo_keys)//2, gk_off)
    ifd += entry(34737, 2, len(geo_ascii)-1, ga_off)
    ifd += struct.pack(E + 'I', 0)  # next IFD
    
    assert len(header) == 8
    assert 8 + len(ifd) == data_offset
    
    with open(filepath, 'wb') as f:
        f.write(header)
        f.write(ifd)
        f.write(extra)
        f.write(raw_pixel_data)
    
    size = os.path.getsize(filepath)
    print('Created %s: %d bytes' % (filepath, size))

create_geotiff('test_dem.tif')
