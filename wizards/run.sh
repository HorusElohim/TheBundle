#!/usr/bin/env sh
set -eu

RAW_BASE_URL="https://raw.githubusercontent.com/HorusElohim/TheBundle/main/wizards"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
TMP_DIR="${TMPDIR:-/tmp}"
OS_NAME="$(uname -s 2>/dev/null || echo unknown)"

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

run_sh_script() {
  script_name="$1"
  shift

  local_path="$SCRIPT_DIR/platforms/$script_name"
  if [ -f "$local_path" ]; then
    sh "$local_path" "$@"
    return
  fi

  tmp_script="$TMP_DIR/thebundle-$script_name"
  if command_exists curl; then
    curl -fsSL "$RAW_BASE_URL/platforms/$script_name" -o "$tmp_script"
  elif command_exists wget; then
    wget -qO "$tmp_script" "$RAW_BASE_URL/platforms/$script_name"
  else
    echo "Neither curl nor wget is available."
    exit 1
  fi
  sh "$tmp_script" "$@"
}

run_ps1_script() {
  script_name="$1"
  shift

  if command_exists powershell; then
    ps_cmd="powershell"
  elif command_exists pwsh; then
    ps_cmd="pwsh"
  else
    echo "PowerShell is required to run Windows setup."
    exit 1
  fi

  local_path="$SCRIPT_DIR/platforms/$script_name"
  if [ -f "$local_path" ]; then
    "$ps_cmd" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "$local_path" "$@"
    return
  fi

  tmp_script="$TMP_DIR/thebundle-$script_name"
  if command_exists curl; then
    curl -fsSL "$RAW_BASE_URL/platforms/$script_name" -o "$tmp_script"
  elif command_exists wget; then
    wget -qO "$tmp_script" "$RAW_BASE_URL/platforms/$script_name"
  else
    echo "Neither curl nor wget is available."
    exit 1
  fi
  "$ps_cmd" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "$tmp_script" "$@"
}

case "$OS_NAME" in
  Linux)
    run_sh_script "linux.sh" "$@"
    ;;
  Darwin)
    run_sh_script "darwin.sh" "$@"
    ;;
  CYGWIN*|MINGW*|MSYS*|Windows_NT)
    run_ps1_script "windows.ps1" "$@"
    ;;
  *)
    echo "Unsupported platform: $OS_NAME"
    exit 1
    ;;
esac
