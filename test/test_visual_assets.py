#!/usr/bin/env python3
"""Guard h1_description visual URDF structure and mesh references."""

from __future__ import annotations

import hashlib
import json
import struct
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
PACKAGE_NAME = ET.parse(PACKAGE / "package.xml").getroot().findtext("name")
URDF = PACKAGE / "urdf" / "h1_visual.urdf"
MESHES = PACKAGE / "meshes"
HASHES = PACKAGE / "ASSET_SHA256SUMS"

# BEGIN LOD PACKAGING CONTRACT HELPERS
COLLADA = {"c": "http://www.collada.org/2005/11/COLLADASchema"}
LOD_TIERS = {"high": "lod10k", "medium": "lod_medium", "low": "lod1500"}


def _asset_paths(package: Path) -> set[str]:
    paths = {str(p.relative_to(package)) for p in (package / "meshes").rglob("*") if p.is_file()}
    paths.update(str(p.relative_to(package)) for p in (package / "urdf").rglob("*visual*.urdf") if p.is_file())
    paths.add("modeling/visual_variants.json")
    return paths


def _canonical_without_visual_uri(root: ET.Element) -> tuple:
    for mesh in root.findall("link/visual/geometry/mesh"):
        mesh.set("filename", "VISUAL_URI")
    def canonical(node):
        return (node.tag, tuple(sorted(node.attrib.items())), (node.text or "").strip(),
                tuple(canonical(child) for child in node))
    return canonical(root)


def _resolve_mesh(uri: str) -> Path:
    prefix = "package://" + PACKAGE_NAME + "/"
    if not uri.startswith(prefix):
        raise ValueError("Unexpected package URI: " + uri)
    path = (PACKAGE / uri[len(prefix):]).resolve()
    if not _within_package(path) or not path.is_file():
        raise ValueError("Missing or escaping package resource: " + uri)
    return path


def _within_package(path: Path) -> bool:
    try:
        path.relative_to(PACKAGE.resolve())
        return True
    except ValueError:
        return False


def _lod_variants(manifest: dict) -> dict:
    variants = manifest["variants"]
    if isinstance(variants, list):
        entries = {entry["tier"]: entry for entry in variants}
        if len(entries) != len(variants):
            raise ValueError("Repeated LOD variant")
    else:
        entries = variants
    return {tier: entry for tier, entry in entries.items() if tier.startswith("lod")}


def _empty_decorative_declaration(tier: str, entry: dict, asset: Path) -> None:
    report_relative = entry.get("geometry_report", entry.get("report", "modeling/geometry_report_" + tier + ".json"))
    report_path = (PACKAGE / report_relative).resolve()
    if not _within_package(report_path) or not report_path.is_file():
        raise ValueError("Empty decorative mesh needs its geometry report: " + str(asset))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    declarations = report.get("intentionally_empty_visual_meshes", {})
    if not isinstance(declarations, dict):
        raise ValueError("Empty visual declarations must be keyed by package-relative mesh path")
    relative = str(asset.relative_to(PACKAGE.resolve()))
    declaration = declarations.get(relative, {})
    if (not isinstance(declaration, dict) or declaration.get("role") != "decorative_logo" or
            not isinstance(declaration.get("reason"), str) or not declaration["reason"].strip()):
        raise ValueError("Undeclared empty decorative mesh: " + relative)


def _mesh_triangles(path: Path) -> int:
    if path.suffix.lower() == ".stl":
        data = path.read_bytes()
        if len(data) >= 84:
            count = struct.unpack_from("<I", data, 80)[0]
            if len(data) == 84 + 50 * count:
                return count
        return sum(line.lstrip().lower().startswith("facet normal") for line in data.decode("ascii").splitlines())
    if path.suffix.lower() != ".dae":
        raise ValueError("Unsupported exported LOD format: " + str(path))
    root = ET.parse(path).getroot()
    geometry_counts = {}
    for geometry in root.findall("c:library_geometries/c:geometry", COLLADA):
        mesh = geometry.find("c:mesh", COLLADA)
        if mesh is None or any(mesh.find("c:" + kind, COLLADA) is not None
                               for kind in ("polylist", "polygons", "trifans", "tristrips")):
            raise ValueError("LOD geometry must export explicit triangles: " + str(path))
        count = 0
        for triangles in mesh.findall("c:triangles", COLLADA):
            stride = 1 + max(int(i.get("offset", "0")) for i in triangles.findall("c:input", COLLADA))
            indices = triangles.findtext("c:p", namespaces=COLLADA).split()
            declared = int(triangles.get("count"))
            if len(indices) != declared * 3 * stride:
                raise ValueError("Triangle stream/count mismatch: " + str(path))
            count += declared
        geometry_counts[geometry.get("id")] = count
    nodes = {node.get("id"): node for node in root.findall(".//c:node", COLLADA) if node.get("id")}
    def node_count(node, active=()):
        key = node.get("id")
        if key and key in active:
            raise ValueError("Cyclic Collada instance_node: " + str(path))
        active = active + ((key,) if key else ())
        if node.find("c:instance_controller", COLLADA) is not None:
            raise ValueError("Unexpected animated LOD controller: " + str(path))
        count = sum(geometry_counts[instance.get("url")[1:]]
                    for instance in node.findall("c:instance_geometry", COLLADA))
        count += sum(node_count(child, active) for child in node.findall("c:node", COLLADA))
        count += sum(node_count(nodes[instance.get("url")[1:]], active)
                     for instance in node.findall("c:instance_node", COLLADA))
        return count
    scenes = {scene.get("id"): scene for scene in root.findall("c:library_visual_scenes/c:visual_scene", COLLADA)}
    selected = root.findall("c:scene/c:instance_visual_scene", COLLADA)
    if not selected:
        raise ValueError("Missing active Collada visual scene: " + str(path))
    return sum(node_count(scenes[instance.get("url")[1:]]) for instance in selected)
# END LOD PACKAGING CONTRACT HELPERS


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
        expected_paths = _asset_paths(PACKAGE)
        self.assertEqual(set(declared), expected_paths)
        for relative, expected in declared.items():
            actual = hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, msg=relative)

    # BEGIN LOD PACKAGING CONTRACT TESTS
    def test_selected_lod_contract_and_resources(self) -> None:
        manifest = json.loads((PACKAGE / "modeling/visual_variants.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["lod_tiers"], LOD_TIERS)
        variants = _lod_variants(manifest)
        self.assertEqual(set(variants), set(LOD_TIERS.values()))
        self.assertEqual(len({entry["urdf"] for entry in variants.values()}), 3)
        for tier, entry in variants.items():
            with self.subTest(tier=tier):
                urdf = (PACKAGE / entry["urdf"]).resolve()
                self.assertTrue(_within_package(urdf) and urdf.is_file())
                self.assertEqual(urdf.name, URDF.stem + "_" + tier + ".urdf")
                root = ET.parse(urdf).getroot()
                self.assertGreater(len(root.findall("link/visual")), 0)
                for mesh in root.findall("link/visual/geometry/mesh"):
                    asset = _resolve_mesh(mesh.attrib["filename"])
                    if asset.suffix.lower() == ".dae":
                        dae = ET.parse(asset).getroot()
                        for image in dae.findall("c:library_images/c:image/c:init_from", COLLADA):
                            texture = (asset.parent / image.text).resolve()
                            self.assertTrue(_within_package(texture) and texture.is_file(), msg=str(texture))

    def test_lod_instance_triangle_counts_and_xml_contract(self) -> None:
        manifest = json.loads((PACKAGE / "modeling/visual_variants.json").read_text(encoding="utf-8"))
        canonical = _canonical_without_visual_uri(ET.parse(URDF).getroot())
        totals = {}
        for tier, entry in _lod_variants(manifest).items():
            with self.subTest(tier=tier):
                root = ET.parse(PACKAGE / entry["urdf"]).getroot()
                total, cache = 0, {}
                for link, visual in ((link, visual) for link in root.findall("link") for visual in link.findall("visual")):
                    geometry = visual.find("geometry")
                    mesh = geometry.find("mesh")
                    if mesh is not None:
                        asset = _resolve_mesh(mesh.attrib["filename"])
                        if asset not in cache:
                            cache[asset] = _mesh_triangles(asset)
                        if cache[asset] == 0:
                            self.assertEqual(link.get("name"), "logo_link", msg="Only the original decorative logo may be empty")
                            _empty_decorative_declaration(tier, entry, asset)
                        else:
                            self.assertGreater(cache[asset], 0, msg=str(asset))
                        total += cache[asset]
                    else:
                        self.assertEqual([child.tag for child in geometry], ["box"], msg="Unbudgeted primitive")
                        total += 12
                self.assertEqual(total, entry["vehicle_triangles"], msg=tier)
                # A tier's nominal target and filename do not impose a cap.
                # Only an explicit numeric manifest cap is binding.
                cap = entry.get("hard_vehicle_triangle_cap")
                if cap is not None:
                    self.assertIsInstance(cap, int)
                    self.assertLessEqual(total, cap, msg=tier)
                totals[tier] = total
                self.assertEqual(_canonical_without_visual_uri(root), canonical, msg=tier)
        self.assertGreater(totals[LOD_TIERS["high"]], totals[LOD_TIERS["medium"]])
        self.assertGreater(totals[LOD_TIERS["medium"]], totals[LOD_TIERS["low"]])
    # END LOD PACKAGING CONTRACT TESTS


if __name__ == "__main__":
    unittest.main()
