#!/bin/bash -l
#SBATCH --job-name=gowno
#SBATCH --account=hpc-danbor2008-1756464546
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:hopper:1,storage:lustre:500G
#SBATCH --cpus-per-task=4
#SBATCH --mem=0
#SBATCH --partition=lem-gpu-short
#SBATCH --time=4:00:00
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --extra=FORCE_RM_TMPDIR

source /etc/profile

module load Python/3.12.3-GCCcore-13.3.0

ROOT_DIR="/home/wojgrz4918"
cd "$ROOT_DIR"

CACHE_ROOT="$TMPDIR"
export PIP_CACHE_DIR="$CACHE_ROOT/pip-cache"
export UV_CACHE_DIR="$CACHE_ROOT/uv-cache"
export XDG_CACHE_HOME="$CACHE_ROOT/xdg-cache"
export PYTHONPYCACHEPREFIX="$CACHE_ROOT/python-cache"
export NUMBA_CACHE_DIR="$CACHE_ROOT/numba-cache"
export MPLCONFIGDIR="$CACHE_ROOT/mpl"
export TORCH_HOME="$CACHE_ROOT/torch"
export HF_HOME="$CACHE_ROOT/hf"
export HF_HUB_CACHE="$CACHE_ROOT/hf/hub"
export TRANSFORMERS_CACHE="$CACHE_ROOT/hf/transformers"
export TRITON_CACHE_DIR="$CACHE_ROOT/triton"
export WANDB_DIR="$CACHE_ROOT/wandb"
export WANDB_CACHE_DIR="$CACHE_ROOT/wandb-cache"
mkdir -p "$PIP_CACHE_DIR" "$UV_CACHE_DIR" "$XDG_CACHE_HOME" "$PYTHONPYCACHEPREFIX" \
         "$NUMBA_CACHE_DIR" "$MPLCONFIGDIR" "$TORCH_HOME" "$HF_HOME/hub" \
         "$HF_HOME/transformers" "$TRITON_CACHE_DIR" "$WANDB_DIR" "$WANDB_CACHE_DIR"

export HYDRA_FULL_ERROR=1
export PYTHONPATH="$ROOT_DIR/src:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1
export TOKENIZERS_PARALLELISM=false
export WANDB_START_METHOD=thread

python3 -m venv $TMPDIR/.venv
source $TMPDIR/.venv/bin/activate
pip install -r requirements.txt
