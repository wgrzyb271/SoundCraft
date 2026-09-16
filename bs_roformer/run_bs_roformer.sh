#!/bin/bash -l

#SBATCH --job-name=bs_roformer
#SBATCH --account=hpc-danbor2008-1756464546
#SBATCH --qos=hpc-danbor2008-1756464546
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:hopper:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=0
#SBATCH --partition=lem-gpu-short
#SBATCH --time=24:00:00
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err

source /etc/profile
set -euo pipefail

module load Python/3.10.4-GCCcore-11.3.0

cd "$HOME/bs_roformer"
source .venv/bin/activate

AUDIO_DIR="$HOME/bs_roformer/test_wav"
OUTPUT_DIR="$HOME/bs_roformer/output-dir"

mkdir -p "$OUTPUT_DIR"

echo "=== PATHS ==="
echo "AUDIO_DIR=$AUDIO_DIR"
echo "OUTPUT_DIR=$OUTPUT_DIR"

echo "=== HOST ==="
hostname

echo "=== PYTHON ==="
which python
python --version

echo "=== GPU ==="
nvidia-smi

echo "=== PYTORCH ==="
python - <<'PY'
import torch

print("torch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("CUDA version:", torch.version.cuda)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
PY

echo "=== CHECK WAV FILES ==="

WAV_COUNT=$(find "$AUDIO_DIR" -maxdepth 1 -type f -name '*.wav' | wc -l)

echo "WAV files: $WAV_COUNT"

if [ "$WAV_COUNT" -ne 5 ]; then
    echo "ERROR: Expected 5 WAV files, found $WAV_COUNT"
    exit 1
fi

du -sh "$AUDIO_DIR"

echo "=== START MODEL ==="

python -u run_bs_roformer.py

echo "=== FINISHED ==="