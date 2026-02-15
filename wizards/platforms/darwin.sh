#!/usr/bin/env sh
set -eu

VENV_PATH=".venv"
PACKAGE_NAME="thebundle[all]"
PYTHON_CMD=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --venv-path)
      VENV_PATH="$2"
      shift 2
      ;;
    --package-name)
      PACKAGE_NAME="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: darwin.sh [--venv-path PATH] [--package-name NAME]"
      exit 1
      ;;
  esac
done

log_step() {
  echo "[wizard] $1"
}

confirm_stage() {
  stage="$1"
  printf "[wizard] Stage: %s. Continue? [y/N]: " "$stage"
  read -r reply
  case "$reply" in
    y|Y|yes|YES)
      return 0
      ;;
    *)
      echo "[wizard] Aborted at stage: $stage"
      exit 1
      ;;
  esac
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

run_install() {
  if [ "$(id -u)" -eq 0 ]; then
    sh -c "$1"
  elif command_exists sudo; then
    sudo sh -c "$1"
  else
    sh -c "$1"
  fi
}

ensure_docker_desktop() {
  if [ -d "/Applications/Docker.app" ] || command_exists docker; then
    log_step "Docker Desktop already installed."
    return
  fi

  log_step "Installing Docker Desktop with Homebrew..."
  run_install "brew install --cask docker"
}

ensure_gpu_note() {
  if command_exists nvidia-smi; then
    log_step "NVIDIA GPU detected, but NVIDIA Docker runtime is generally not supported on macOS."
  fi
  log_step "macOS Docker uses Docker Desktop virtualization. GPU passthrough for NVIDIA containers is not supported."
  log_step "After launch, validate Docker with: docker run --rm hello-world"
}

ensure_brew() {
  if command_exists brew; then
    return
  fi
  echo "Homebrew is required on macOS. Install it first: https://brew.sh/"
  exit 1
}

ensure_git() {
  if command_exists git; then
    log_step "Git already installed."
    return
  fi
  log_step "Installing Git with Homebrew..."
  run_install "brew install git"
}

ensure_python() {
  if command_exists python3; then
    PYTHON_CMD="python3"
    return
  fi
  if command_exists python; then
    PYTHON_CMD="python"
    return
  fi

  confirm_stage "Install Python"
  log_step "Installing Python with Homebrew..."
  run_install "brew install python"
  if command_exists python3; then
    PYTHON_CMD="python3"
  elif command_exists python; then
    PYTHON_CMD="python"
  else
    echo "Python installation finished but the command was not found."
    exit 1
  fi
}

log_step "Starting TheBundle setup on macOS..."
confirm_stage "Check Homebrew"
ensure_brew
confirm_stage "Install Docker Desktop"
ensure_docker_desktop
confirm_stage "Review GPU support notes for Docker on macOS"
ensure_gpu_note
confirm_stage "Install Git"
ensure_git
ensure_python

if [ -d "$VENV_PATH" ]; then
  log_step "Virtual environment already exists at '$VENV_PATH'. Reusing it."
else
  confirm_stage "Create virtual environment at $VENV_PATH"
  log_step "Creating virtual environment at '$VENV_PATH'..."
  "$PYTHON_CMD" -m venv "$VENV_PATH"
fi

VENV_PY="$VENV_PATH/bin/python"
if [ ! -x "$VENV_PY" ]; then
  echo "Could not find venv python executable at '$VENV_PY'."
  exit 1
fi

confirm_stage "Upgrade pip/setuptools/wheel"
log_step "Upgrading pip/setuptools/wheel..."
"$VENV_PY" -m pip install --upgrade pip setuptools wheel

confirm_stage "Install package $PACKAGE_NAME"
log_step "Installing package '$PACKAGE_NAME'..."
"$VENV_PY" -m pip install "$PACKAGE_NAME"

log_step "Setup completed."
echo "Activate with: source $VENV_PATH/bin/activate"
echo "Then run: python -m pip show thebundle"
