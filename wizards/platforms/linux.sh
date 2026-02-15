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
      echo "Usage: linux.sh [--venv-path PATH] [--package-name NAME]"
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

ensure_docker() {
  if command_exists docker; then
    log_step "Docker already installed."
    return
  fi

  log_step "Installing Docker..."
  if command_exists apt-get; then
    run_install "apt-get update && apt-get install -y docker.io"
  elif command_exists dnf; then
    run_install "dnf install -y docker"
  elif command_exists yum; then
    run_install "yum install -y docker"
  elif command_exists pacman; then
    run_install "pacman -Sy --noconfirm docker"
  elif command_exists zypper; then
    run_install "zypper --non-interactive install docker"
  else
    echo "No supported package manager found to install Docker."
    exit 1
  fi

  if command_exists systemctl; then
    run_install "systemctl enable --now docker" || true
  fi
}

ensure_nvidia_container_toolkit() {
  if ! command_exists nvidia-smi; then
    log_step "No NVIDIA GPU detected (nvidia-smi missing). Skipping NVIDIA Docker setup."
    return
  fi

  if command_exists nvidia-ctk; then
    log_step "NVIDIA Container Toolkit already installed."
  else
    log_step "Installing NVIDIA Container Toolkit..."
    if command_exists apt-get; then
      run_install "apt-get update && apt-get install -y nvidia-container-toolkit"
    elif command_exists dnf; then
      run_install "dnf install -y nvidia-container-toolkit"
    elif command_exists yum; then
      run_install "yum install -y nvidia-container-toolkit"
    else
      echo "Automatic NVIDIA Container Toolkit install is not configured for this distro."
      echo "Install manually: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html"
      return
    fi
  fi

  if command_exists nvidia-ctk; then
    run_install "nvidia-ctk runtime configure --runtime=docker" || true
    if command_exists systemctl; then
      run_install "systemctl restart docker" || true
    fi
    log_step "NVIDIA Docker runtime configured. Validate with:"
    echo "docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi"
  fi
}

ensure_git() {
  if command_exists git; then
    log_step "Git already installed."
    return
  fi

  log_step "Installing Git..."
  if command_exists apt-get; then
    run_install "apt-get update && apt-get install -y git"
  elif command_exists dnf; then
    run_install "dnf install -y git"
  elif command_exists yum; then
    run_install "yum install -y git"
  elif command_exists pacman; then
    run_install "pacman -Sy --noconfirm git"
  elif command_exists zypper; then
    run_install "zypper --non-interactive install git"
  else
    echo "No supported package manager found to install Git."
    exit 1
  fi
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
  log_step "Installing Python..."
  if command_exists apt-get; then
    run_install "apt-get update && apt-get install -y python3 python3-venv python3-pip"
  elif command_exists dnf; then
    run_install "dnf install -y python3 python3-pip"
  elif command_exists yum; then
    run_install "yum install -y python3 python3-pip"
  elif command_exists pacman; then
    run_install "pacman -Sy --noconfirm python python-pip"
  elif command_exists zypper; then
    run_install "zypper --non-interactive install python3 python3-pip"
  else
    echo "No supported package manager found to install Python."
    exit 1
  fi

  if command_exists python3; then
    PYTHON_CMD="python3"
  elif command_exists python; then
    PYTHON_CMD="python"
  else
    echo "Python installation finished but the command was not found."
    exit 1
  fi
}

log_step "Starting TheBundle setup on Linux..."
confirm_stage "Install Docker Engine"
ensure_docker
confirm_stage "Configure NVIDIA GPU support for Docker"
ensure_nvidia_container_toolkit
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
