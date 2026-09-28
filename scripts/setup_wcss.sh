#!/usr/bin/env bash
# Odtwarza środowiska wykonawcze SoundCraft na WCSS. Domyślnie pomija SAM Audio.

source /etc/profile
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_HOME_DIR="${HOME:?HOME is not set}"
WORK_ROOT="${TMPDIR:-${USER_HOME_DIR}/tmp}"
WITH_SAM=0

# Nie pozwól, aby aktywny venv wybrał interpreter zamiast modułu EasyBuild.
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    PATH="${PATH#"${VIRTUAL_ENV}/bin:"}"
    unset VIRTUAL_ENV
fi

usage() {
    echo "Usage: $0 [--without-sam|--with-sam]"
}

for argument in "$@"; do
    case "$argument" in
        --without-sam) WITH_SAM=0 ;;
        --with-sam) WITH_SAM=1 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown argument: $argument" >&2; usage >&2; exit 2 ;;
    esac
done

case "$WORK_ROOT" in
    "$USER_HOME_DIR"/*) ;;
    *)
        echo "Refusing WORK_ROOT outside the home directory: $WORK_ROOT" >&2
        exit 2
        ;;
esac

VENV_ROOT="$WORK_ROOT/venvs"
CACHE_ROOT="$WORK_ROOT/cache"
export TMPDIR="$WORK_ROOT"
export PIP_CACHE_DIR="$CACHE_ROOT/pip"
export XDG_CACHE_HOME="$CACHE_ROOT/xdg"
export TORCH_HOME="$CACHE_ROOT/torch"
export HF_HOME="$CACHE_ROOT/huggingface"
export HF_HUB_CACHE="$HF_HOME/hub"
export TRANSFORMERS_CACHE="$HF_HOME/transformers"
export NUMBA_CACHE_DIR="$CACHE_ROOT/numba"
export MPLCONFIGDIR="$CACHE_ROOT/matplotlib"
export TRITON_CACHE_DIR="$CACHE_ROOT/triton"

mkdir -p \
    "$VENV_ROOT" "$PIP_CACHE_DIR" "$XDG_CACHE_HOME" "$TORCH_HOME" \
    "$HF_HUB_CACHE" "$TRANSFORMERS_CACHE" "$NUMBA_CACHE_DIR" \
    "$MPLCONFIGDIR" "$TRITON_CACHE_DIR" "$WORK_ROOT/logs" \
    "$USER_HOME_DIR/backend_files"
chmod 700 "$WORK_ROOT" "$USER_HOME_DIR/backend_files"

load_python() {
    local module_name="$1"
    module purge
    module load "$module_name"
    python --version
}

prepare_venv() {
    local venv_path="$1"
    if [[ ! -x "$venv_path/bin/python" ]]; then
        python -m venv "$venv_path"
    fi
    "$venv_path/bin/python" -m pip install --upgrade pip setuptools wheel
}

echo "== Orchestrator, mixAgent and PostProcessing =="
load_python "Python/3.11.5-GCCcore-13.2.0"
prepare_venv "$VENV_ROOT/orchestrator"
"$VENV_ROOT/orchestrator/bin/python" -m pip install -r "$PROJECT_ROOT/llm_agent/requirements.txt"
PYTHONPATH="$PROJECT_ROOT" "$VENV_ROOT/orchestrator/bin/python" - <<'PY'
from llm_agent.orchestrator.config import Settings
from mixAgent.server import process_stem
from PostProcessing.stitch_stems import stitch_stems

print("Orchestrator, mixAgent and PostProcessing imports: OK")
PY
"$VENV_ROOT/orchestrator/bin/python" -m pip check

echo "== BS-RoFormer =="
load_python "Python/3.10.4-GCCcore-11.3.0"
prepare_venv "$VENV_ROOT/bs-roformer"
"$VENV_ROOT/bs-roformer/bin/python" -m pip install \
    -r "$PROJECT_ROOT/agent_bs_roformer/requirements-agent.txt"
PYTHONPATH="$PROJECT_ROOT/agent_bs_roformer:$PROJECT_ROOT/llm_agent" \
    "$VENV_ROOT/bs-roformer/bin/python" - <<'PY'
import beartype
import einops
import librosa
import soundfile
import torch
import torchaudio
import yaml

from agent.agent import BSRoformerAgent

print("BS-RoFormer imports: OK")
print("torch:", torch.__version__)
print("torchaudio:", torchaudio.__version__)
PY
"$VENV_ROOT/bs-roformer/bin/python" -m pip check

BS_ASSET_ROOT="$USER_HOME_DIR/bs_roformer"
for asset in \
    "$BS_ASSET_ROOT/model_files/config_bs_roformer_384_8_2_485100.yaml" \
    "$BS_ASSET_ROOT/model_files/model_bs_roformer_ep_17_sdr_9.6568.ckpt" \
    "$BS_ASSET_ROOT/Music-Source-Separation-Training"
do
    if [[ ! -e "$asset" ]]; then
        echo "Missing BS-RoFormer asset: $asset" >&2
        exit 1
    fi
done

echo "== Demucs =="
load_python "Python/3.11.5-GCCcore-13.2.0"
prepare_venv "$VENV_ROOT/demucs"
"$VENV_ROOT/demucs/bin/python" -m pip install -r "$PROJECT_ROOT/demucs/requirements.txt"
PYTHONPATH="$PROJECT_ROOT/llm_agent" "$VENV_ROOT/demucs/bin/python" "$PROJECT_ROOT/demucs/agent.py" --help >/dev/null
PYTHONPATH="$PROJECT_ROOT/llm_agent" "$VENV_ROOT/demucs/bin/python" - <<'PY'
import torch
import torchaudio

from demucs.apply import apply_model
from demucs.pretrained import get_model

print("Demucs imports: OK")
print("torch:", torch.__version__)
print("torchaudio:", torchaudio.__version__)
PY
"$VENV_ROOT/demucs/bin/python" -m pip check

if [[ "$WITH_SAM" -eq 1 ]]; then
    echo "== SAM Audio Base (optional) =="
    SAM_SOURCE="$WORK_ROOT/src/sam-audio"
    mkdir -p "$WORK_ROOT/src" "$WORK_ROOT/tools"
    if [[ ! -d "$SAM_SOURCE/.git" ]]; then
        git clone https://github.com/facebookresearch/sam-audio.git "$SAM_SOURCE"
    fi

    load_python "Python/3.11.5-GCCcore-13.2.0"
    prepare_venv "$VENV_ROOT/sam-audio"
    "$VENV_ROOT/sam-audio/bin/python" -m pip install --upgrade --force-reinstall \
        torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 \
        --index-url https://download.pytorch.org/whl/cu124
    "$VENV_ROOT/sam-audio/bin/python" -m pip install -e "$SAM_SOURCE"
    "$VENV_ROOT/sam-audio/bin/python" -m pip install --force-reinstall --no-deps \
        torchcodec==0.2.1 --index-url https://download.pytorch.org/whl/cpu

    MICROMAMBA="$WORK_ROOT/tools/bin/micromamba"
    if [[ ! -x "$MICROMAMBA" ]]; then
        curl -L https://micro.mamba.pm/api/micromamba/linux-64/latest \
            -o "$WORK_ROOT/tools/micromamba.tar.bz2"
        tar -xjf "$WORK_ROOT/tools/micromamba.tar.bz2" -C "$WORK_ROOT/tools" bin/micromamba
        chmod 700 "$MICROMAMBA"
    fi
    export MAMBA_ROOT_PREFIX="$WORK_ROOT/micromamba"
    "$MICROMAMBA" create -y -p "$WORK_ROOT/ffmpeg-env" -c conda-forge "ffmpeg=6.1.*"
    export LD_LIBRARY_PATH="$WORK_ROOT/ffmpeg-env/lib:${LD_LIBRARY_PATH:-}"
    "$VENV_ROOT/sam-audio/bin/python" -c \
        "from sam_audio import SAMAudio, SAMAudioProcessor; print('SAM Audio imports: OK')"
else
    echo "== SAM Audio skipped (use --with-sam when ready) =="
fi

echo
echo "Setup completed. Environments:"
echo "  $VENV_ROOT/orchestrator"
echo "  $VENV_ROOT/bs-roformer"
echo "  $VENV_ROOT/demucs"
if [[ "$WITH_SAM" -eq 1 ]]; then
    echo "  $VENV_ROOT/sam-audio"
fi
echo "Run the worker with:"
echo "  $PROJECT_ROOT/scripts/submit_wcss_worker.sh"
