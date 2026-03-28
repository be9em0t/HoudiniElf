#!/bin/zsh

# APP="/Applications/Houdini/Houdini21.0.631/Applications/Houdini FX 21.0.631.app/Contents/MacOS/houdinifx"
APP="/Applications/Houdini/Houdini21.0.631/Houdini FX 21.0.631.app/Contents/MacOS/houdinifx"

exec "$APP" -foreground "$@"