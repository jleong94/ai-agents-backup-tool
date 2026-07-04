#!/usr/bin/env bash
# macOS Finder double-click launcher.
# Delegates to run.sh in the same folder (which finds/installs Python, then
# runs the tool). Kept as a thin wrapper so run.sh stays the single source.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec bash "$DIR/run.sh" "$@"
