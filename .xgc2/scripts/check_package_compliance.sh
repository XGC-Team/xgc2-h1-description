#!/usr/bin/env bash
set -euo pipefail

grep -q '^id: xgc2-h1-description$' .xgc2/product.yml
version="$(awk '/^version:/ {print $2; exit}' .xgc2/product.yml)"
focal_version="$(awk '/^  apt_versions:/ {inside=1; next} inside && /^    focal:/ {print $2; exit}' .xgc2/product.yml)"
test -n "${version}"
dpkg --validate-version "${version}"
if [[ "${focal_version}" != "${version}" ]]; then
  echo "focal APT version must match the product version" >&2
  exit 1
fi
grep -q '^kind: ros1-apt$' .xgc2/product.yml
grep -q '^  distro: noetic$' .xgc2/product.yml
grep -q '^  distribution: focal$' .xgc2/product.yml
grep -q 'ros-noetic-xgc2-h1-description' .xgc2/product.yml
grep -q '<name>h1_description</name>' package.xml
grep -q '<buildtool_depend>catkin</buildtool_depend>' package.xml
grep -q '^project(h1_description)$' CMakeLists.txt
test -f urdf/h1_visual.urdf
test -f meshes/pelvis.STL
test -f meshes/left_hip_yaw_link.STL
test -f ASSET_SHA256SUMS
grep -q 'robot name="h1"' urdf/h1_visual.urdf
grep -q 'package://h1_description/meshes/' urdf/h1_visual.urdf
grep -q 'left_hip_yaw_joint' urdf/h1_visual.urdf

sha256sum --check ASSET_SHA256SUMS
python3 -m unittest discover -s test -v

if git ls-files | grep -E '^(launch|rviz|config|src|include)/'; then
  echo "non-visual payload is tracked" >&2
  exit 1
fi
if grep -ERi '<(collision|inertial|transmission|gazebo)|<plugin|ros_control|ros2_control|gazebo_ros' urdf package.xml CMakeLists.txt; then
  echo "non-visual URDF or runtime integration found" >&2
  exit 1
fi
if grep -E 'filename="meshes/' urdf/h1_visual.urdf; then
  echo "relative mesh paths remain" >&2
  exit 1
fi
if grep -ERi 'enP2p1s0|2207:0019|slcan1|192\.168\.123' urdf package.xml CMakeLists.txt README.md; then
  echo "hardcoded machine topology found" >&2
  exit 1
fi

echo "Package compliance checks passed."
