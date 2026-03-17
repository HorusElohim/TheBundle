#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${COMFY_BASE_DIR:-/opt/content}"
CN_DIR="${BASE_DIR}/custom_nodes"
MODELS_DIR="${BASE_DIR}/models"
MARKER_FILE="${CN_DIR}/.thebundle_custom_nodes_initialized"
PYTHON_BIN="${PYTHON_BIN:-/opt/ComfyUI.venv/bin/python}"
PIP_BIN="${PIP_BIN:-/opt/ComfyUI.venv/bin/pip}"

UPDATE_REPOS="${CUSTOM_NODES_UPDATE:-0}"
INSTALL_DEPS="${CUSTOM_NODES_INSTALL_DEPS:-1}"

mkdir -p "${CN_DIR}" "${MODELS_DIR}"

clone_or_update() {
  local name="$1"
  local repo="$2"
  local target="${CN_DIR}/${name}"

  if [ ! -d "${target}/.git" ]; then
    git clone --depth 1 "${repo}" "${target}"
    return 0
  fi

  if [ "${UPDATE_REPOS}" = "1" ]; then
    git -C "${target}" pull --ff-only || true
    return 0
  fi

  return 1
}

install_node_deps() {
  [ "${INSTALL_DEPS}" = "1" ] || return 0

  find "${CN_DIR}" -maxdepth 2 -name requirements.txt -print0 | while IFS= read -r -d '' req; do
    "${PIP_BIN}" install --no-cache-dir -r "${req}" || true
  done

  find "${CN_DIR}" -maxdepth 2 -name install.py -print0 | while IFS= read -r -d '' installer; do
    "${PYTHON_BIN}" "${installer}" || true
  done
}

mkdir -p \
  "${MODELS_DIR}/checkpoints" \
  "${MODELS_DIR}/diffusion_models" \
  "${MODELS_DIR}/text_encoders" \
  "${MODELS_DIR}/clip_vision" \
  "${MODELS_DIR}/vae" \
  "${MODELS_DIR}/CogVideo" \
  "${MODELS_DIR}/loras" \
  "${MODELS_DIR}/latent_upscale_models" \
  "${MODELS_DIR}/animatediff_models" \
  "${MODELS_DIR}/animatediff_motion_lora" \
  "${MODELS_DIR}/upscale_models"

changed=0

clone_or_update "comfyui-manager" "https://github.com/ltdrdata/ComfyUI-Manager.git" && changed=1 || true
clone_or_update "ComfyUI-VideoHelperSuite" "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git" && changed=1 || true
clone_or_update "ComfyUI-AnimateDiff-Evolved" "https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git" && changed=1 || true
clone_or_update "ComfyUI-CogVideoXWrapper" "https://github.com/kijai/ComfyUI-CogVideoXWrapper.git" && changed=1 || true
clone_or_update "ComfyUI-LTXVideo" "https://github.com/Lightricks/ComfyUI-LTXVideo.git" && changed=1 || true
clone_or_update "ComfyUI-WanVideoWrapper" "https://github.com/kijai/ComfyUI-WanVideoWrapper.git" && changed=1 || true

if [ ! -f "${MARKER_FILE}" ] || [ "${changed}" = "1" ] || [ "${UPDATE_REPOS}" = "1" ]; then
  install_node_deps
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${MARKER_FILE}"
fi