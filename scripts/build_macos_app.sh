#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

usage() {
  cat <<'EOF'
Usage: ./scripts/build_macos_app.sh [--skip-install] [--target-arch <arm64|x86_64|universal2>] [--python <path>]

Examples:
  ./scripts/build_macos_app.sh
  ./scripts/build_macos_app.sh --target-arch x86_64
  ./scripts/build_macos_app.sh --target-arch universal2 --skip-install
EOF
}

SKIP_INSTALL=false
TARGET_ARCH=""
PYTHON_BIN="${PYTHON:-python}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-install)
      SKIP_INSTALL=true
      shift
      ;;
    --target-arch)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --target-arch" >&2
        usage
        exit 1
      fi
      TARGET_ARCH="$2"
      shift 2
      ;;
    --target-arch=*)
      TARGET_ARCH="${1#*=}"
      shift
      ;;
    --python)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --python" >&2
        usage
        exit 1
      fi
      PYTHON_BIN="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -n "$TARGET_ARCH" ]]; then
  case "$TARGET_ARCH" in
    arm64|x86_64|universal2)
      ;;
    *)
      echo "Unsupported target arch: $TARGET_ARCH" >&2
      usage
      exit 1
      ;;
  esac
fi

HOST_ARCH="$(uname -m)"
PYTHON_ARCH="$("$PYTHON_BIN" -c 'import platform; print(platform.machine())')"
PYTHON_PATH="$("$PYTHON_BIN" -c 'import sys; print(sys.executable)')"

echo "Host arch: $HOST_ARCH"
echo "Python arch: $PYTHON_ARCH"
echo "Python executable: $PYTHON_PATH"

if [[ -n "$TARGET_ARCH" ]]; then
  echo "Requested PyInstaller target arch: $TARGET_ARCH"
fi

if [[ "$HOST_ARCH" == "arm64" && "$TARGET_ARCH" == "x86_64" ]]; then
  echo "Warning: building x86_64 on Apple Silicon requires an x86_64 Python environment (for example via Rosetta)." >&2
fi

if [[ "$TARGET_ARCH" == "universal2" ]]; then
  echo "Warning: universal2 builds require universal2-compatible Python and dependency wheels." >&2
fi

if [[ "$SKIP_INSTALL" != true ]]; then
  "$PYTHON_BIN" -m pip install -r requirements.txt
  "$PYTHON_BIN" -m pip install -r requirements-build.txt
fi

if [[ ! -f assets/aica_icon.icns ]]; then
  "$PYTHON_BIN" - <<'PY'
from PIL import Image

image = Image.open("assets/aica_icon.png")
image.save(
    "assets/aica_icon.icns",
    sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)],
)
PY
fi

PYINSTALLER_ARGS=(--noconfirm --clean)
if [[ -n "$TARGET_ARCH" ]]; then
  PYINSTALLER_ARGS+=(--target-arch "$TARGET_ARCH")
fi

"$PYTHON_BIN" -m PyInstaller "${PYINSTALLER_ARGS[@]}" aica_macos.spec

echo
echo "Build complete: dist/AICA.app"
