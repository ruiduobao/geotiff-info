# GeoTIFF Metadata Viewer · GeoTIFF 元数据查看器

> 快速查看 **GeoTIFF** 文件的 CRS、分辨率、波段数、NoData、统计值。
> **零依赖**（仅使用 Python 标准库），无需打开 GIS 软件。
> MIT-0 开源。

[English](#quickstart) | 中文

## 为什么做这个

查看 GeoTIFF 元数据通常需要打开 QGIS/ArcGIS 或安装 GDAL/rasterio。
本工具纯 Python 实现，直接解析 TIFF 二进制格式，一条命令即可查看
所有关键信息，适合脚本集成和快速检查。

## Quickstart / 快速开始

```bash
# 零依赖，无需安装任何第三方库

# 查看单个文件元数据
python geotiff-info.py image.tif

# JSON 格式输出
python geotiff-info.py image.tif --json

# 批量扫描目录
python geotiff-info.py ./data/ --scan

# 扫描并输出 JSON
python geotiff-info.py ./data/ --scan --json
```

## 支持的格式 / Supported Formats

| 格式 | 说明 |
|---|---|
| **Classic TIFF** | 标准 TIFF 格式 |
| **BigTIFF** | 大文件 TIFF（>4GB） |
| **GeoTIFF** | 带地理参考的 TIFF |

## 输出信息 / Output Fields

| 字段 | 说明 |
|---|---|
| `CRS` | 坐标参考系统（EPSG 代码 + WKT） |
| `Resolution` | 像素大小（x, y） |
| `Bands` | 波段数量和数据类型 |
| `NoData` | 无效值 |
| `Size` | 影像尺寸（宽 × 高） |
| `Corners` | 四角坐标（UL, UR, LL, LR） |
| `Transform` | 仿射变换参数 |
| `Statistics` | 各波段最小/最大/均值/标准差 |
| `FileSize` | 文件大小 |

## 参数一览 / Parameters

| 参数 | 说明 | 必填 |
|---|---|---|
| `input` | 输入文件或目录路径 | ✅ |
| `--json` | JSON 格式输出 | ❌ |
| `--scan` | 扫描目录下所有 GeoTIFF | ❌ |

## License

MIT-0（详见 [LICENSE](./LICENSE)）。
零外部依赖，仅使用 Python 标准库（struct, json, os）。
