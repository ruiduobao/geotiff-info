---
description: 'Zero-dependency Python tool for reading GeoTIFF file metadata.

  Parses TIFF IFD manually using only Python standard library.

  Supports CRS, resolution, bands, corner coordinates, and batch scanning.

  '
name: geotiff-info
---

# GeoTIFF Metadata Viewer

A zero-dependency Python tool for reading GeoTIFF file metadata without opening GIS software. Parses TIFF IFD (Image File Directory) manually using only Python standard library.

## Features

- **CRS Information**: EPSG code, CRS name, WKT
- **Resolution**: Pixel scale (X/Y resolution)
- **Image Dimensions**: Width, height, band count
- **Data Types**: Bits per sample, sample format (integer/float)
- **NoData Value**: GDAL nodata tag
- **Band Statistics**: Min, max, mean, std per band (when available)
- **File Information**: File size, BigTIFF detection
- **Corner Coordinates**: UL, UR, LL, LR in geographic/projected coordinates
- **Affine Transform**: 6-parameter affine transformation matrix
- **GeoTIFF Keys**: All GeoKey directory entries
- **Output Formats**: Text table or JSON
- **Batch Processing**: Scan entire directories for GeoTIFF files

## Installation

No installation required! This tool uses only Python standard library.

```bash
# Just run the script directly
python geotiff-info.py <input_file>
```

## Usage

### Single File

```bash
# Text output
python geotiff-info.py image.tif

# JSON output
python geotiff-info.py image.tif --json
```

### Batch Directory Scan

```bash
# Scan directory for all GeoTIFF files
python geotiff-info.py /path/to/directory --batch

# Export all metadata to JSON
python geotiff-info.py /path/to/directory --batch --json > metadata.json
```

### Example Output

```
============================================================
GeoTIFF Metadata: dem.tif
============================================================

                    FILE INFORMATION                    
------------------------------------------------------------
  File Size:          12.45 MB
  BigTIFF:            No

                   IMAGE DIMENSIONS                     
------------------------------------------------------------
  Width:              1024 pixels
  Height:             1024 pixels
  Bands:              1

                       DATA TYPE                         
------------------------------------------------------------
  Bits per Sample:    32
  Sample Format:      floating point
  Compression:        LZW
  Photometric:        MinIsBlack
  Planar Config:      Chunky

                    NODATA VALUE                        
------------------------------------------------------------
  NoData:             -9999

              COORDINATE REFERENCE SYSTEM               
------------------------------------------------------------
  EPSG Code:          4326
  CRS Name:           WGS 84

                   PIXEL RESOLUTION                     
------------------------------------------------------------
  Scale X:            0.000277777777778
  Scale Y:            0.000277777777778

                  AFFINE TRANSFORM                      
------------------------------------------------------------
  [      0.000278,       0.000000,     115.000000]
  [      0.000000,      -0.000278,      40.000000]
  [          0.0,           0.0,           1.0]

                  CORNER COORDINATES                    
------------------------------------------------------------
  Upper Left         (    115.000000,      40.000000)
  Upper Right        (    115.285714,      40.000000)
  Lower Left         (    115.000000,      39.714286)
  Lower Right        (    115.285714,      39.714286)

============================================================
```

## Supported GeoTIFF Tags

| Tag ID | Name | Description |
|--------|------|-------------|
| 256 | ImageWidth | Image width in pixels |
| 257 | ImageLength | Image height in pixels |
| 258 | BitsPerSample | Bits per sample |
| 259 | Compression | Compression method |
| 262 | PhotometricInterpretation | Color space |
| 277 | SamplesPerPixel | Number of bands |
| 284 | PlanarConfiguration | Chunky or planar |
| 339 | SampleFormat | Integer/float format |
| 33550 | ModelPixelScaleTag | Pixel scale (x, y, z) |
| 33922 | ModelTiepointTag | Tiepoint (i, j, k, x, y, z) |
| 34735 | GeoKeyDirectoryTag | GeoTIFF key directory |
| 34736 | GeoDoubleParamsTag | Double precision parameters |
| 34737 | GeoAsciiParamsTag | ASCII parameters |
| 42113 | GDAL_NODATA | NoData value |

## Supported Formats

- Classic TIFF (magic number 42)
- BigTIFF (magic number 43)
- Little-endian and big-endian byte order
- All standard TIFF data types (BYTE, SHORT, LONG, FLOAT, DOUBLE, etc.)

## Limitations

- Band statistics (min/max/mean/std) are placeholders for large files
- Does not read actual pixel data (metadata only)
- Limited CRS WKT support (relies on GeoKeys)
- No support for GeoTIFF 1.1 new model (yet)

## License

MIT-0 (No Attribution)

## Author

OpenCode AI Assistant

---

## 中文说明

零依赖的 GeoTIFF 元数据读取工具。仅使用 Python 标准库，手动解析 TIFF IFD。

### 特性

- **CRS 信息**：EPSG 编码、CRS 名称、WKT
- **分辨率**：X/Y 方向像元大小
- **图像尺寸**：宽度、高度、波段数
- **数据类型**：位深度、采样格式（整型/浮点）
- **NoData**：GDAL nodata 标签
- **角点坐标**：左上、右上、左下、右下
- **仿射变换**：6 参数仿射变换矩阵
- **批量处理**：扫描整个目录的 GeoTIFF 文件
- **输出格式**：文本表格或 JSON

### 使用方法

```bash
# 单文件
python geotiff-info.py image.tif
python geotiff-info.py image.tif --json

# 批量扫描目录
python geotiff-info.py /path/to/directory --batch
python geotiff-info.py /path/to/directory --batch --json > metadata.json
```

无需安装任何依赖，直接运行即可。
