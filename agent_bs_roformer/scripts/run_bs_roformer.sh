#!/bin/bash -l

#SBATCH --job-name=bs_roformer
#SBATCH --account=hpc-danbor2008-1756464546
#SBATCH --qos=hpc-danbor2008-1756464546
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:hopper:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --partition=lem-gpu-short
#SBATCH --time=00:30:00
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err

source /etc/profile
set -euo pipefail

module load Python/3.10.4-GCCcore-11.3.0
PROJECT_ROOT="/home/wojgrz4918/agent_bs_roformer"
ORCHESTRATOR_ROOT="/home/wojgrz4918/llm_agent"
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT:$ORCHESTRATOR_ROOT:${PYTHONPATH:-}"

VENV_DIR="$TMPDIR/venv"

cleanup() {
    rm -rf "$VENV_DIR"
}

trap cleanup EXIT

echo "=== BS-Roformer agent ==="
echo "Host: $(hostname)"
echo "Job ID: ${SLURM_JOB_ID:-unknown}"
echo "TMPDIR: $TMPDIR"

python -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip

python -m pip install --no-cache-dir \
    -r /home/wojgrz4918/agent_bs_roformer/requirements-agent.txt

echo "=== Python ==="
python --version

echo "=== PyTorch ==="
python - <<'PY'
import torch

print("torch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
PY


echo "=== Running AgentTask integration test ==="

python tests/run_agent_task.py

echo "=== AgentTask integration test completed ==="
