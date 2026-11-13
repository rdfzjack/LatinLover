#!/bin/sh
# Copies the data tables into the Godot project so that an export carries them (export_presets.cfg includes data/*).
# Run from anywhere before exporting. The copy is not committed (game/silentstar/data/ is in .gitignore).
set -e
root="$(cd "$(dirname "$0")/.." && pwd)"
dst="$root/game/silentstar/data"
rm -rf "$dst"
mkdir -p "$dst/locale"
cp -r "$root/data/new" "$dst/new"
cp "$root/data/locale/text.csv" "$root/data/locale/ui.csv" "$dst/locale/"
echo "copied data/new and data/locale into $dst"
