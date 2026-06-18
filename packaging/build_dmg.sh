#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Vector Vario Analyzer"
VERSION="${VERSION:-0.03}"
VOL_NAME="${APP_NAME}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_PATH="${PROJECT_DIR}/src/dist/${APP_NAME}.app"
ASSET_DIR="${PROJECT_DIR}/packaging/dmg"
OUTPUT_DIR="${PROJECT_DIR}/dist"
STAGE_DIR="${PROJECT_DIR}/packaging/dmg/stage"
RW_DMG="${PROJECT_DIR}/packaging/dmg/${APP_NAME}-rw.dmg"
FINAL_DMG="${OUTPUT_DIR}/${APP_NAME}-${VERSION}.dmg"
DMG_ICON_SOURCE="${ASSET_DIR}/installer-icon-source.png"

if [[ ! -d "${APP_PATH}" ]]; then
  echo "Missing app bundle: ${APP_PATH}" >&2
  echo "Build it first with: cd src && python -m PyInstaller --noconfirm --clean VVA.spec" >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"
rm -rf "${STAGE_DIR}" "${RW_DMG}" "${FINAL_DMG}"
mkdir -p "${STAGE_DIR}/.background"

cp -R "${APP_PATH}" "${STAGE_DIR}/"
ln -s /Applications "${STAGE_DIR}/Applications"
cp "${ASSET_DIR}/background.png" "${STAGE_DIR}/.background/background.png"
cp "${ASSET_DIR}/VectorVarioInstaller.icns" "${STAGE_DIR}/.VolumeIcon.icns"
SetFile -c icnC "${STAGE_DIR}/.VolumeIcon.icns"
SetFile -a C "${STAGE_DIR}"

hdiutil create \
  -volname "${VOL_NAME}" \
  -srcfolder "${STAGE_DIR}" \
  -fs HFS+ \
  -fsargs "-c c=64,a=16,e=16" \
  -format UDRW \
  -size 520m \
  "${RW_DMG}"

MOUNT_DIR="$(hdiutil attach "${RW_DMG}" -readwrite -noverify -noautoopen | awk '/\/Volumes\// {print substr($0, index($0, "/Volumes/"))}' | tail -1)"
if [[ -z "${MOUNT_DIR}" ]]; then
  echo "Unable to find mounted DMG volume." >&2
  exit 1
fi

cp "${ASSET_DIR}/VectorVarioInstaller.icns" "${MOUNT_DIR}/.VolumeIcon.icns"
SetFile -c icnC "${MOUNT_DIR}/.VolumeIcon.icns"
SetFile -a C "${MOUNT_DIR}"

osascript <<APPLESCRIPT
set mountedPath to POSIX file "${MOUNT_DIR}" as alias
set backgroundPath to POSIX file "${MOUNT_DIR}/.background/background.png" as alias

tell application "Finder"
  set dmgFolder to folder mountedPath
  open dmgFolder
  delay 1
  set dmgWindow to container window of dmgFolder
  set current view of dmgWindow to icon view
  set toolbar visible of dmgWindow to false
  set statusbar visible of dmgWindow to false
  set the bounds of dmgWindow to {100, 100, 760, 500}
  set viewOptions to the icon view options of dmgWindow
  tell viewOptions
    set arrangement to not arranged
    set icon size to 104
    set background picture to backgroundPath
  end tell
  set position of item "${APP_NAME}.app" of dmgFolder to {148, 244}
  set position of item "Applications" of dmgFolder to {514, 244}
  update dmgFolder without registering applications
  delay 2
  close dmgWindow
end tell
APPLESCRIPT

test -f "${MOUNT_DIR}/.DS_Store"

cp "${ASSET_DIR}/VectorVarioInstaller.icns" "${MOUNT_DIR}/.VolumeIcon.icns"
SetFile -c icnC "${MOUNT_DIR}/.VolumeIcon.icns"
SetFile -a C "${MOUNT_DIR}"
test -f "${MOUNT_DIR}/.VolumeIcon.icns"

sync
hdiutil detach "${MOUNT_DIR}"
hdiutil convert "${RW_DMG}" -format UDZO -imagekey zlib-level=9 -o "${FINAL_DMG}"

if command -v sips >/dev/null && command -v DeRez >/dev/null && command -v Rez >/dev/null && command -v SetFile >/dev/null; then
  TMP_ICON="${OUTPUT_DIR}/.dmg-icon.png"
  TMP_RSRC="${OUTPUT_DIR}/.dmg-icon.rsrc"
  cp "${DMG_ICON_SOURCE}" "${TMP_ICON}"
  sips -i "${TMP_ICON}" >/dev/null
  DeRez -only icns "${TMP_ICON}" > "${TMP_RSRC}"
  Rez -append "${TMP_RSRC}" -o "${FINAL_DMG}"
  SetFile -a C "${FINAL_DMG}"
  rm -f "${TMP_ICON}" "${TMP_RSRC}"
else
  echo "Warning: macOS icon tools not available; DMG file icon was not customized." >&2
fi

hdiutil verify "${FINAL_DMG}"
rm -rf "${STAGE_DIR}" "${RW_DMG}"

echo "Created ${FINAL_DMG}"
