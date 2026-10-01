# h1_description

Reusable **visual** ROS description assets for **Unitree H1** (`h1`).

Package layout follows `b2arx_description`: meshes + visual URDF only. No
controllers, Gazebo plugins, or hardcoded machine USB/serial topology.

This is a productized vendor snapshot. It is not an accepted XGC low-polygon
visual default.

| Item | Value |
|------|--------|
| ROS package | `h1_description` |
| Visual URDF | `urdf/h1_visual.urdf` |
| Robot name | `h1` |
| Canonical source | h1.urdf |
| Debian package | `ros-noetic-xgc2-h1-description` |

Meshes and kinematics remain Unitree's (BSD-3-Clause). Mesh paths use
`package://h1_description/meshes/...`.

## Build

```bash
source /opt/ros/noetic/setup.bash
catkin_make_isolated --pkg h1_description
```

## Install

```
sudo apt update
sudo apt install ros-noetic-xgc2-h1-description
```

## Use

```text
$(rospack find h1_description)/urdf/h1_visual.urdf
```

Joint states and TF still come from drivers; this package only supplies
description assets.
