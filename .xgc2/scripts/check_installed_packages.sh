#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/noetic/setup.bash
set -u

dpkg -s ros-noetic-xgc2-h1-description >/dev/null
package_path="$(rospack find h1_description)"
test "${package_path}" = /opt/ros/noetic/share/h1_description
test -f "${package_path}/meshes/pelvis.STL"
test -f "${package_path}/meshes/left_hip_yaw_link.STL"
test -f "${package_path}/urdf/h1_visual.urdf"
test -f "${package_path}/ASSET_SHA256SUMS"

(
  cd "${package_path}"
  sha256sum --check ASSET_SHA256SUMS
)

python3 - "${package_path}/urdf/h1_visual.urdf" <<'PY'
import sys
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
assert root.attrib["name"] == "h1"
assert len(root.findall("link")) == 22
assert len(root.findall("joint")) == 21
for tag in ("collision", "inertial", "transmission", "gazebo", "plugin"):
    assert not root.findall(f".//{tag}"), tag
PY

echo "Installed package check passed."
