#!/usr/bin/env python3
"""Guard h1_description visual URDF structure and mesh references."""

from __future__ import annotations

import hashlib
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
URDF = PACKAGE / "urdf" / "h1_visual.urdf"
MESHES = PACKAGE / "meshes"
HASHES = PACKAGE / "ASSET_SHA256SUMS"


class VisualAssetsTest(unittest.TestCase):
    def test_robot_name_and_mesh_package_uris(self) -> None:
        root = ET.parse(URDF).getroot()
        self.assertEqual(root.attrib.get("name"), "h1")
        meshes = root.findall(".//mesh")
        self.assertGreater(len(meshes), 3)
        for mesh in meshes:
            filename = mesh.attrib["filename"]
            self.assertTrue(
                filename.startswith("package://h1_description/meshes/"),
                msg=filename,
            )
            leaf = filename.rsplit("/", 1)[-1]
            self.assertTrue((MESHES / leaf).is_file(), msg=f"missing mesh {leaf}")

    def test_link_and_joint_counts(self) -> None:
        root = ET.parse(URDF).getroot()
        self.assertEqual(len(root.findall("link")), 22)
        self.assertEqual(len(root.findall("joint")), 21)

    def test_visual_only_boundary(self) -> None:
        root = ET.parse(URDF).getroot()
        self.assertGreater(len(root.findall(".//visual")), 0)
        for tag in ("collision", "inertial", "transmission", "gazebo", "plugin"):
            self.assertEqual(root.findall(f".//{tag}"), [], msg=tag)
        self.assertTrue({"link", "joint"}.issubset({child.tag for child in root}))

    def test_required_mesh_files_exist(self) -> None:
        for name in (
            "pelvis.STL",
            "left_hip_yaw_link.STL",
            "left_hip_roll_link.STL",
            "left_hip_pitch_link.STL",
            "left_knee_link.STL",
            "left_ankle_link.STL",
        ):
            self.assertTrue((MESHES / name).is_file(), msg=name)

    def test_asset_hash_manifest(self) -> None:
        declared = {}
        for line in HASHES.read_text(encoding="utf-8").splitlines():
            digest, relative = line.split(maxsplit=1)
            declared[relative] = digest
        expected_paths = {
            str(path.relative_to(PACKAGE))
            for path in MESHES.iterdir()
            if path.is_file()
        }
        expected_paths.add(str(URDF.relative_to(PACKAGE)))
        self.assertEqual(set(declared), expected_paths)
        for relative, expected in declared.items():
            actual = hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, msg=relative)


if __name__ == "__main__":
    unittest.main()
