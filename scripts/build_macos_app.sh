#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SKIP_INSTALL="${1:-}"

if [[ "$SKIP_INSTALL" != "--skip-install" ]]; then
  python -m pip install -r requirements.txt
  python -m pip install -r requirements-build.txt
fi

if [[ ! -f assets/aica_icon.icns ]]; then
  python - <<'PY'
from PIL import Image

image = Image.open("assets/aica_icon.png")
image.save(
    "assets/aica_icon.icns",
    sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)],
)
PY
fi

python -m PyInstaller --noconfirm --clean aica_macos.spec

echo
echo "Build complete: dist/AICA.app"
