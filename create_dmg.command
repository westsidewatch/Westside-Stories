#!/bin/bash
set -e
cd "$(dirname "$0")"

APP="dist/Westside Stories.app"
DMG="Westside-Stories-1.1.dmg"
STAGE=".dmg-stage"

if [ ! -d "$APP" ]; then
  echo "找不到 $APP"
  echo "請先執行 build_app.command 完成 App 打包。"
  exit 1
fi

rm -rf "$STAGE" "$DMG"
mkdir "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

hdiutil create \
  -volname "Westside Stories 1.1" \
  -srcfolder "$STAGE" \
  -ov \
  -format UDZO \
  "$DMG"

rm -rf "$STAGE"

echo
echo "完成：$(pwd)/$DMG"
