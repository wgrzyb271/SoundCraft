#!/bin/bash -l

#SBATCH --job-name=demucs_agent
#SBATCH --account=hpc-danbor2008-1756464546
#SBATCH --qos=hpc-danbor2008-1756464546
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:hopper:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=0
#SBATCH --partition=lem-gpu-short
#SBATCH --time=24:00:00
#SBATCH --output=demucs_agent-%j.out
#SBATCH --error=demucs_agent-%j.err

set -euo pipefail

# ============================================================
# PROJECT
# ============================================================

PROJECT_DIR="/home/wojgrz4918/finger/projekt"
VENV_DIR="$PROJECT_DIR/venv"
AGENT_SCRIPT="$PROJECT_DIR/agent.py"

# ============================================================
# PYTHON MODULE
# ============================================================

module load Python/3.11.5-GCCcore-13.2.0

# ============================================================
# PROJECT DIRECTORY
# ============================================================

cd "$PROJECT_DIR"

# ============================================================
# VIRTUAL ENVIRONMENT
# ============================================================

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "$PROJECT_DIR/requirements.txt"
export PYTHONPATH="$HOME/llm_agent:$PYTHONPATH"
# ============================================================
# FFMPEG ENVIRONMENT
# ============================================================

export PATH="$HOME/samuel_benchmark/ffmpeg_env/bin:$PATH"
export LD_LIBRARY_PATH="$HOME/samuel_benchmark/ffmpeg_env/lib:${LD_LIBRARY_PATH:-}"

# ============================================================
# HEADER
# ============================================================

echo "======================================"
echo "        DEMUCS AGENT"
echo "======================================"

echo
echo "=== HOST ==="
hostname

echo
echo "=== PROJECT ==="
echo "PROJECT_DIR=$PROJECT_DIR"
echo "VENV_DIR=$VENV_DIR"
echo "AGENT_SCRIPT=$AGENT_SCRIPT"

echo
echo "=== PYTHON ==="
which python
python --version

echo
echo "=== PYTHON EXECUTABLE ==="
python -c "import sys; print(sys.executable)"

echo
echo "=== GPU ==="
nvidia-smi

echo
echo "=== PYTORCH ==="

python - <<'PY'
import torch

print("torch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("CUDA version:", torch.version.cuda)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
    print("GPU count:", torch.cuda.device_count())
PY

# ============================================================
# CHECK AGENT SCRIPT
# ============================================================

echo
echo "=== CHECK AGENT ==="

if [ ! -f "$AGENT_SCRIPT" ]; then
    echo "ERROR: Missing agent script:"
    echo "$AGENT_SCRIPT"
    exit 1
fi

echo "Agent script found:"
echo "$AGENT_SCRIPT"

# ============================================================
# START AGENT
# ============================================================

echo
echo "=== START AGENT ==="

python -u "$AGENT_SCRIPT"

# ============================================================
# FINISHED
# ============================================================

echo
echo "======================================"
echo "        DEMUCS AGENT FINISHED"
echo "======================================"
