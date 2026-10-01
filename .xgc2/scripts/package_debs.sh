#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT=""
OUTPUT_DIR=""
ROS_DISTRO="jazzy"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PACKAGE="ros-jazzy-xgc2-h1-description"
ROS_PACKAGE="h1_description"

product_version() {
  awk -F': *' '/^version:[[:space:]]*/ {print $2; exit}' "${REPO_ROOT}/.xgc2/product.yml"
}

VERSION="${PACKAGE_VERSION:-$(product_version)}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-root)
      INSTALL_ROOT="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "${INSTALL_ROOT}" || -z "${OUTPUT_DIR}" ]]; then
  echo "--install-root and --output-dir are required" >&2
  exit 1
fi
if [[ -z "${VERSION}" ]]; then
  echo "package version is missing" >&2
  exit 1
fi

ARCH="$(dpkg --print-architecture)"
PREFIX="/opt/ros/${ROS_DISTRO}"
PREFIX_ROOT="${INSTALL_ROOT}${PREFIX}"
PKG_ROOT="$(mktemp -d)"

cleanup() {
  rm -rf "${PKG_ROOT}"
}
trap cleanup EXIT

mkdir -p "${OUTPUT_DIR}" "${PKG_ROOT}/DEBIAN" "${PKG_ROOT}/usr/share/doc/${PACKAGE}"
rm -f "${OUTPUT_DIR}"/${PACKAGE}_*.deb

if [[ ! -d "${PREFIX_ROOT}/share/${ROS_PACKAGE}" ]]; then
  echo "staged ROS package is missing: ${PREFIX_ROOT}/share/${ROS_PACKAGE}" >&2
  exit 1
fi

mkdir -p "${PKG_ROOT}${PREFIX}/share"
cp -a "${PREFIX_ROOT}/share/${ROS_PACKAGE}" "${PKG_ROOT}${PREFIX}/share/"

AMENT_RESOURCE_ROOT="${PREFIX_ROOT}/share/ament_index/resource_index"
PACKAGE_MARKER="${AMENT_RESOURCE_ROOT}/packages/${ROS_PACKAGE}"
if [[ ! -f "${PACKAGE_MARKER}" ]]; then
  echo "ament package marker is missing: ${PACKAGE_MARKER}" >&2
  exit 1
fi

while IFS= read -r -d '' resource; do
  relative="${resource#${INSTALL_ROOT}}"
  mkdir -p "${PKG_ROOT}$(dirname "${relative}")"
  cp -a "${resource}" "${PKG_ROOT}${relative}"
done < <(find "${AMENT_RESOURCE_ROOT}" -type f -name "${ROS_PACKAGE}" -print0)

cat >"${PKG_ROOT}/DEBIAN/control" <<EOF
Package: ${PACKAGE}
Version: ${VERSION}
Section: misc
Priority: optional
Architecture: ${ARCH}
Maintainer: XGC2 <apt@example.com>
Depends: ros-jazzy-urdf
Description: XGC2 Unitree B2 and ARX R5a visual description assets
EOF

printf '%s package\n' "${PACKAGE}" >"${PKG_ROOT}/usr/share/doc/${PACKAGE}/README"
find "${PKG_ROOT}" -type d -exec chmod 0755 {} +
find "${PKG_ROOT}" -type f -exec chmod 0644 {} +
chmod 0755 "${PKG_ROOT}/DEBIAN"

fakeroot dpkg-deb --build "${PKG_ROOT}" "${OUTPUT_DIR}/${PACKAGE}_${VERSION}_${ARCH}.deb" >/dev/null
find "${OUTPUT_DIR}" -maxdepth 1 -type f -name "${PACKAGE}_*.deb" -print | sort
