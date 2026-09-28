#!/bin/bash -l
# Lekki worker kolejki SoundCraft. Partycja, konto i QOS są przekazywane
# przez scripts/submit_wcss_worker.sh, aby nie utrwalać lokalnej konfiguracji
# klastra w tym pliku.
#SBATCH --job-name=soundcraft-worker
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=2-23:00:00
#SBATCH --output=/home/wojgrz4918/tmp/logs/soundcraft-worker-%j.out
#SBATCH --error=/home/wojgrz4918/tmp/logs/soundcraft-worker-%j.err

source /etc/profile
set -euo pipefail

module load Python/3.11.5-GCCcore-13.2.0

PROJECT_ROOT=/home/wojgrz4918/SoundCraft
WORK_ROOT=/home/wojgrz4918/tmp
WORKER_PYTHON="$WORK_ROOT/venvs/orchestrator/bin/python"
WORKER_CONFIG="$PROJECT_ROOT/llm_agent/config.local.yaml"

export TMPDIR="$WORK_ROOT"
export PIP_CACHE_DIR="$WORK_ROOT/cache/pip"
export XDG_CACHE_HOME="$WORK_ROOT/cache/xdg"
export TORCH_HOME="$WORK_ROOT/cache/torch"
export HF_HOME="$WORK_ROOT/cache/huggingface"
export HF_HUB_CACHE="$HF_HOME/hub"
export TRANSFORMERS_CACHE="$HF_HOME/transformers"
export NUMBA_CACHE_DIR="$WORK_ROOT/cache/numba"
export MPLCONFIGDIR="$WORK_ROOT/cache/matplotlib"
export TRITON_CACHE_DIR="$WORK_ROOT/cache/triton"
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

test -x "$WORKER_PYTHON"
test -f "$WORKER_CONFIG"
mkdir -p /home/wojgrz4918/backend_files

cd "$PROJECT_ROOT"
exec "$WORKER_PYTHON" -m llm_agent.orchestrator.wcss_worker \
    --config "$WORKER_CONFIG" \
    --poll 3
