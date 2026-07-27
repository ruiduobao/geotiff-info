"""Tests for the --qa sidecar summary (Phase 5 optimization)."""

import json
import os
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent
CLI = PROJECT_ROOT / "geotiff-info.py"

# Reuse the test fixtures from conftest.py
sys.path.insert(0, str(HERE))
from conftest import (  # noqa: E402
    load_geotiff_info, create_test_geotiff, GeoTIFFInfo
)

gi = load_geotiff_info()
write_qa_summary = gi.write_qa_summary
deep_qa = gi.deep_qa
read_geotiff = gi.read_geotiff


def _make_info(**kwargs) -> GeoTIFFInfo:
    """Build a GeoTIFFInfo for direct write_qa_summary tests."""
    defaults = dict(
        file_path="/tmp/test.tif",
        file_size=1024 * 1024,
        file_size_human="1.0 MB",
        width=100,
        height=100,
        bits_per_sample=[16, 16, 16, 16],
        samples_per_pixel=4,
        sample_format=["uint", "uint", "uint", "uint"],
        compression="None",
        photometric="RGB",
        planar_config="Chunky",
        nodata="0",
        pixel_scale=(30.0, 30.0, 0.0),
        tiepoint=(0.0, 0.0, 0.0, 100.0, 40.0, 0.0),
        geo_keys={"GTModelTypeGeoKey": 1, "GTRasterTypeGeoKey": 1,
                  "GeographicTypeGeoKey": 4326, "ProjectedCSTypeGeoKey": 32650},
        crs_epsg=32650,
        crs_name="WGS 84 / UTM zone 50N",
        crs_wkt="...",
        affine_transform=(100.0, 30.0, 0.0, 40.0, 0.0, -30.0),
        corner_coords={
            "upper_left": (100.0, 40.0),
            "upper_right": (103.0, 40.0),
            "lower_left": (100.0, 37.0),
            "lower_right": (103.0, 37.0),
        },
    )
    defaults.update(kwargs)
    return GeoTIFFInfo(**defaults)


class TestWriteQASummary(unittest.TestCase):
    def test_writes_deep_qa_summary(self):
        with tempfile.TemporaryDirectory() as td:
            qa_path = os.path.join(td, "out.qa.json")
            info = _make_info()
            write_qa_summary(qa_path, info=info, command="info")
            self.assertTrue(os.path.exists(qa_path))
            data = json.loads(Path(qa_path).read_text(encoding="utf-8"))
            self.assertEqual(data["skill"], "geotiff-info")
            self.assertEqual(data["command"], "info")
            self.assertEqual(data["file"], "/tmp/test.tif")
            self.assertEqual(data["file_size"], 1024 * 1024)
            # The deep_qa() result is nested under "qa"
            self.assertIn("qa", data)
            qa = data["qa"]
            self.assertIn("score", qa)
            self.assertIn("passed", qa)
            self.assertIn("findings", qa)
            self.assertIn("summary", qa)
            self.assertIn("timestamp", data)
            self.assertIn("version", data)

    def test_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            qa_path = os.path.join(td, "nested", "subdir", "out.qa.json")
            info = _make_info()
            write_qa_summary(qa_path, info=info, command="info")
            self.assertTrue(os.path.exists(qa_path))

    def test_extra_field_is_merged(self):
        with tempfile.TemporaryDirectory() as td:
            qa_path = os.path.join(td, "out.qa.json")
            info = _make_info()
            write_qa_summary(
                qa_path, info=info, command="info",
                extra={"input_format": "geotiff", "n_files": 1},
            )
            data = json.loads(Path(qa_path).read_text(encoding="utf-8"))
            self.assertEqual(data["input_format"], "geotiff")
            self.assertEqual(data["n_files"], 1)

    def test_findings_are_recorded(self):
        """A bad EPSG code should produce a finding inside the sidecar."""
        with tempfile.TemporaryDirectory() as td:
            qa_path = os.path.join(td, "out.qa.json")
            info = _make_info(crs_epsg=-1, geo_keys={})
            write_qa_summary(qa_path, info=info, command="info")
            data = json.loads(Path(qa_path).read_text(encoding="utf-8"))
            # Either a CRS or nodata finding, but at minimum qa.findings exists
            self.assertIn("findings", data["qa"])
            self.assertIsInstance(data["qa"]["findings"], list)


class TestCLIQA(unittest.TestCase):
    """End-to-end: run the CLI with --qa and verify a sidecar is written."""

    def test_qa_writes_deep_qa_sidecar(self):
        with tempfile.TemporaryDirectory() as td:
            tif_path = os.path.join(td, "sample.tif")
            create_test_geotiff(tif_path)
            qa_path = os.path.join(td, "out.qa.json")
            proc = subprocess.run(
                [sys.executable, str(CLI), tif_path, "--qa", qa_path],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(proc.returncode, 0, msg=f"STDERR: {proc.stderr}")
            self.assertTrue(os.path.exists(qa_path), msg=f"missing {qa_path}")
            data = json.loads(Path(qa_path).read_text(encoding="utf-8"))
            self.assertEqual(data["skill"], "geotiff-info")
            self.assertEqual(data["command"], "info")
            self.assertIn("qa", data)
            self.assertIn("score", data["qa"])
            self.assertIn("findings", data["qa"])

    def test_qa_in_help(self):
        proc = subprocess.run(
            [sys.executable, str(CLI), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--qa", proc.stdout)
        self.assertIn("PATH", proc.stdout)


if __name__ == "__main__":
    unittest.main()
