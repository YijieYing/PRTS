#!/bin/bash
# Build the two tiny apps the Shortcuts automations open (action 「打开 App」).
set -eu
cd "$(dirname "$0")"; out=~/Applications; mkdir -p "$out"
for pair in "start:开始" "stop:结束"; do
  app="$out/PRTS 勿扰${pair#*:}.app"; rm -rf "$app"
  osacompile -o "$app" "dnd-${pair%%:*}.applescript"
  /usr/libexec/PlistBuddy -c 'Add :LSUIElement bool true' "$app/Contents/Info.plist"   # no Dock icon
  /usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string com.prts.dnd-${pair%%:*}" "$app/Contents/Info.plist" 2>/dev/null ||
    /usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier com.prts.dnd-${pair%%:*}" "$app/Contents/Info.plist"
  codesign --force --sign - "$app"
done
