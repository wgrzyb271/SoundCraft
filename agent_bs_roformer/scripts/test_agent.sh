#!/bin/bash -l

#SBATCH --job-name=bs_agent_test
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

python -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip

python -m pip install --no-cache-dir \
    -r "$PROJECT_ROOT/requirements-agent.txt"

python tests/test_slurm_job.py