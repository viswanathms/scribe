#!/bin/bash
# Builds SCRIBE.app from SCRIBE.spec and packages it into a DMG for sharing.
# Ad-hoc signed only (no paid Apple Developer account) -- recipients will need
# to right-click -> Open the first time to get past Gatekeeper.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [ ! -d venv ]; then
  echo "No venv found. Run: python3 -m venv venv && venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

if ! venv/bin/python -c "import PyInstaller" 2>/dev/null; then
  echo "Installing PyInstaller..."
  venv/bin/pip install -q pyinstaller
fi

rm -rf build dist
venv/bin/pyinstaller --noconfirm SCRIBE.spec

echo "--- codesign check ---"
codesign -dv dist/SCRIBE.app

echo "--- packaging DMG ---"
STAGING="dist/dmg_staging"
rm -rf "$STAGING"
mkdir -p "$STAGING"
cp -R dist/SCRIBE.app "$STAGING/"
ln -s /Applications "$STAGING/Applications"
hdiutil create -volname "SCRIBE" -srcfolder "$STAGING" -ov -format UDZO dist/SCRIBE.dmg
rm -rf "$STAGING"

echo ""
echo "Done."
echo "  App: $PROJECT_DIR/dist/SCRIBE.app"
echo "  DMG: $PROJECT_DIR/dist/SCRIBE.dmg"
echo ""
echo "First launch on this or any other Mac: right-click SCRIBE.app -> Open"
echo "(ad-hoc signed, not notarized -- double-clicking straight away gets Gatekeeper-blocked)."
