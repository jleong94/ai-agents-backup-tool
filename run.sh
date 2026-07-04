#!/usr/bin/env bash
# ==========================================================================
#  AI Agents Backup & Transfer Tool - Linux / macOS launcher
#
#  Finds Python 3 and, if it is missing, installs it automatically using the
#  system package manager (Homebrew on macOS; apt/dnf/yum/pacman/zypper/apk on
#  Linux), then runs backup_transfer_tool.py. Arguments are passed through:
#      ./run.sh                    ->  interactive menu
#      ./run.sh backup ~/Backups   ->  run a command directly
#      ./run.sh list  ~/Backups
# ==========================================================================
set -u

# Resolve this script's own directory, so the tool is found from any CWD.
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Print the name of a working Python 3 interpreter, or return non-zero.
find_python() {
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1; then
      if "$c" -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' >/dev/null 2>&1; then
        printf '%s\n' "$c"
        return 0
      fi
    fi
  done
  return 1
}

install_python() {
  os="$(uname -s)"
  echo "Python 3 was not found. Attempting to install it..."
  if [ "$os" = "Darwin" ]; then
    if command -v brew >/dev/null 2>&1; then
      brew install python
    else
      echo "Homebrew is not installed, so Python cannot be installed automatically."
      echo "Install Homebrew from https://brew.sh and re-run, or install Python 3"
      echo "from https://www.python.org/downloads/"
      return 1
    fi
  else
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update && sudo apt-get install -y python3
    elif command -v dnf >/dev/null 2>&1; then
      sudo dnf install -y python3
    elif command -v yum >/dev/null 2>&1; then
      sudo yum install -y python3
    elif command -v pacman >/dev/null 2>&1; then
      sudo pacman -S --noconfirm python
    elif command -v zypper >/dev/null 2>&1; then
      sudo zypper install -y python3
    elif command -v apk >/dev/null 2>&1; then
      sudo apk add python3
    else
      echo "No supported package manager was found."
      echo "Please install Python 3 manually: https://www.python.org/downloads/"
      return 1
    fi
  fi
  return 0
}

PY="$(find_python || true)"

if [ -z "${PY:-}" ]; then
  install_python || exit 1
  PY="$(find_python || true)"
  if [ -z "${PY:-}" ]; then
    echo "Python 3 still not found after installation. Please install it manually."
    exit 1
  fi
fi

# The tool needs Python 3.8+ (it uses shutil.copytree(dirs_exist_ok=...)).
if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'; then
  echo "Python 3.8+ is required. Found: $("$PY" --version 2>&1)"
  echo "Please upgrade Python: https://www.python.org/downloads/"
  exit 1
fi

echo "Using Python: $PY"
exec "$PY" "$DIR/backup_transfer_tool.py" "$@"
