#!/bin/bash

set -euo pipefail

if [ -f /tmp/amd.tgz ]; then
    echo "Extracting archive..."
    cd /opt
    tar xfz /tmp/amd.tgz
    rm /tmp/amd.tgz
    echo "Done extracting."
fi

mkdir -p /opt/content/{models,custom_nodes,input,output,user,cache}
mkdir -p /opt/content/models/{checkpoints,clip,clip_vision,configs,controlnet,diffusers,diffusion_models,embeddings,gligen,hypernetworks,loras,photomaker,style_models,text_encoders,unet,upscale_models,vae,vae_approx}

if [ "${INSTALL_CUSTOM_NODES:-1}" = "1" ] && [ -x /opt/bootstrap/install_nodes_once.sh ]; then
    /bin/bash /opt/bootstrap/install_nodes_once.sh || true
fi

if [ -z "$(ls -A /opt/content/models/configs/ 2>/dev/null)" ]; then
    cp -r /opt/ComfyUI/models/configs/* /opt/content/models/configs/
fi

STARTUP_ARGS=("--listen" "${LISTEN_ADDR:-0.0.0.0}" "--enable-cors-header" "${CORS_HEADER:-*}" "--max-upload-size"
    "${MAX_UPLOAD_MB:-100}" "--base-directory" "/opt/content" "--temp-directory" "/tmp/comfyui" "--disable-auto-launch")

if [ -f /etc/ssl/private/key.pem ] && [ -f /etc/ssl/private/cert.pem ]; then
    STARTUP_ARGS+=("--tls-keyfile" "/etc/ssl/private/key.pem"
        "--tls-certfile" "/etc/ssl/private/cert.pem")
fi

if [ "${GPU_ONLY:-false}" == "true" ]; then
    STARTUP_ARGS+=(--gpu-only)
elif [ "${CPU_ONLY:-false}" == "true" ]; then
    STARTUP_ARGS+=("--cpu")
fi

# Normalize Windows CRLF env values (e.g. VRAM=high\r) before parsing.
VRAM_VALUE="$(printf '%s' "${VRAM:-auto}" | tr -d '\r')"
if [ "${VRAM_VALUE}" != "auto" ]; then
    if [ "${VRAM_VALUE}" == "high" ]; then
        STARTUP_ARGS+=(--highvram)
    elif [ "${VRAM_VALUE}" == "normal" ]; then
        STARTUP_ARGS+=(--normalvram)
    elif [ "${VRAM_VALUE}" == "low" ]; then
        STARTUP_ARGS+=(--lowvram)
    elif [ "${VRAM_VALUE}" == "no" ]; then
        STARTUP_ARGS+=(--novram)
    else
        echo "Ignoring VRAM environment variable expected 'auto', 'high', 'normal', 'low' or 'no' got '${VRAM_VALUE}'"
    fi
fi

if [ "${SPLIT_CROSS_ATTENTION:-false}" == "true" ]; then
    STARTUP_ARGS+=("--use-split-cross-attention")
fi

echo "Activating Virtual Environment..."
. /opt/ComfyUI.venv/bin/activate

echo "Starting ComfyUI with these options:"
printf '  %q\n' "${STARTUP_ARGS[@]}"
echo "----------"
python3 /opt/ComfyUI/main.py "${STARTUP_ARGS[@]}"
