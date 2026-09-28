#!/bin/bash -l

#SBATCH --job-name=check_wcss
#SBATCH --account=hpc-danbor2008-1756464546
#SBATCH --qos=hpc-danbor2008-1756464546
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:hopper:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --partition=lem-gpu-short
#SBATCH --time=00:10:00
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err

source /etc/profile
set -euo pipefail

module load Python/3.10.4-GCCcore-11.3.0

VENV_DIR="$TMPDIR/venv"

cleanup() {
    rm -rf "$VENV_DIR"
}

trap cleanup EXIT

python -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo
echo "=== VENV ==="
which python
python --version

echo
echo "=== INSTALL TEST AUDIO DEPENDENCIES ==="
python -m pip install --no-cache-dir \
    "torch==2.4.1" \
    "torchaudio==2.4.1" \
    "numpy" \
    "scipy" \
    "soundfile" \
    "librosa" \
    "einops"\
    "beartype"\
    "packaging"\
    "rotary-embedding-torch"\
    "PyYAML" 

echo
echo "=== BS-ROFORMER IMPORT TEST ==="

PYTHONPATH="/home/wojgrz4918/bs_roformer/Music-Source-Separation-Training:${PYTHONPATH:-}" \
python - <<'PY'

from models.bs_roformer.bs_roformer import BSRoformer

print("BSRoformer import: OK")
print("Class:", BSRoformer)

PY

echo
echo "=== BS-ROFORMER MODEL INIT TEST ==="

PYTHONPATH="/home/wojgrz4918/bs_roformer/Music-Source-Separation-Training:${PYTHONPATH:-}" \
python - <<'PY'

from pathlib import Path
import os

import librosa
import numpy as np
import torch
import yaml

from models.bs_roformer.bs_roformer import BSRoformer

REPO_PATH = Path(
    "/home/wojgrz4918/bs_roformer/Music-Source-Separation-Training"
)

CONFIG_PATH = Path("/home/wojgrz4918/bs_roformer/model_files/config_bs_roformer_384_8_2_485100.yaml")

print("Config:", CONFIG_PATH)
print("Config exists:", CONFIG_PATH.exists())

with open(CONFIG_PATH, "r") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

print("YAML loaded: OK")

model_config = config["model"]
SAMPLE_RATE = config["audio"]["sample_rate"]
CHUNK_SIZE = config["audio"]["chunk_size"]

print("Creating BSRoformer...")
model = BSRoformer(**model_config)

print("BSRoformer initialization: OK")
print("Parameters:", sum(p.numel() for p in model.parameters()))

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("Device:", device)

model = model.to(device)

print("Model moved to device: OK")

model.eval()

print("Model eval mode: OK")
print("=== MODEL INIT TEST PASSED ===")
PY

echo
echo "=== BS-ROFORMER CHECKPOINT LOAD TEST ==="

PYTHONPATH="/home/wojgrz4918/bs_roformer/Music-Source-Separation-Training:${PYTHONPATH:-}" \
python -u - <<'PY'

from pathlib import Path
import os

import librosa
import numpy as np
import torch
import yaml


from models.bs_roformer.bs_roformer import BSRoformer


REPO_PATH = Path(
    "/home/wojgrz4918/bs_roformer/Music-Source-Separation-Training"
)

CONFIG_PATH = Path(
    "/home/wojgrz4918/bs_roformer/model_files/"
    "config_bs_roformer_384_8_2_485100.yaml"
)

CHECKPOINT_PATH = Path(
    "/home/wojgrz4918/bs_roformer/model_files/"
    "model_bs_roformer_ep_17_sdr_9.6568.ckpt"
)


print("1. Config:", CONFIG_PATH, flush=True)
print("2. Config exists:", CONFIG_PATH.exists(), flush=True)

print("3. Checkpoint:", CHECKPOINT_PATH, flush=True)
print(
    "4. Checkpoint exists:",
    CHECKPOINT_PATH.exists(),
    flush=True,
)

print(
    "5. Checkpoint size:",
    f"{CHECKPOINT_PATH.stat().st_size / (1024**3):.2f} GiB",
    flush=True,
)

with open(CONFIG_PATH, "r") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

print("6. YAML loaded: OK", flush=True)

model_config = config["model"]
SAMPLE_RATE = config["audio"]["sample_rate"]
CHUNK_SIZE = config["audio"]["chunk_size"]

print("7. Creating BSRoformer...", flush=True)

model = BSRoformer(**model_config)

print("8. BSRoformer initialization: OK", flush=True)

print("9. Loading checkpoint to CPU...", flush=True)

checkpoint = torch.load(
    CHECKPOINT_PATH,
    map_location="cpu",
)

print(
    "10. Checkpoint loaded:",
    type(checkpoint),
    flush=True,
)

if isinstance(checkpoint, dict):
    print(
        "11. Checkpoint keys:",
        list(checkpoint.keys()),
        flush=True,
    )

    if "state_dict" in checkpoint:
        state_dict = checkpoint["state_dict"]
        print(
            "12. Using checkpoint['state_dict']",
            flush=True,
        )
    else:
        state_dict = checkpoint
        print(
            "12. Using checkpoint directly as state_dict",
            flush=True,
        )
else:
    state_dict = checkpoint

print(
    "13. State dict entries:",
    len(state_dict),
    flush=True,
)

print("14. Loading state dict into model...", flush=True)

missing_keys, unexpected_keys = model.load_state_dict(
    state_dict,
    strict=False,
)

print(
    "15. load_state_dict: OK",
    flush=True,
)

print(
    "16. Missing keys:",
    len(missing_keys),
    flush=True,
)

print(
    "17. Unexpected keys:",
    len(unexpected_keys),
    flush=True,
)

if missing_keys:
    print("Missing key examples:", missing_keys[:10], flush=True)

if unexpected_keys:
    print(
        "Unexpected key examples:",
        unexpected_keys[:10],
        flush=True,
    )

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print(
    "18. Moving model to device:",
    device,
    flush=True,
)

model = model.to(device)

print(
    "19. Model moved to device: OK",
    flush=True,
)

model.eval()

print(
    "20. Model eval mode: OK",
    flush=True,
)

del checkpoint
del state_dict

if torch.cuda.is_available():
    torch.cuda.empty_cache()

print(
    "=== CHECKPOINT LOAD TEST PASSED ===",
    flush=True,
)
# ============================================================
# FORWARD TEST
# ============================================================

AUDIO_PATH = (
    "/home/wojgrz4918/backend_files/"
    "2f1c9f47-fba1-4ad7-a314-10a3751aed8f/"
    "input/audio_folder/audio.wav"
)

print("=== BS-ROFORMER FORWARD TEST ===")

print("1. Audio:", AUDIO_PATH)

if not os.path.exists(AUDIO_PATH):
    raise FileNotFoundError(
        f"Audio file does not exist: {AUDIO_PATH}"
    )

# ------------------------------------------------------------
# Load audio
# ------------------------------------------------------------

print("2. Loading audio...")

audio, sr = librosa.load(
    AUDIO_PATH,
    sr=SAMPLE_RATE,
    mono=False,
)

audio = np.asarray(
    audio,
    dtype=np.float32,
)

if audio.ndim == 1:
    audio = np.stack(
        [audio, audio],
        axis=0,
    )

if audio.shape[0] > 2:
    audio = audio[:2]

print("3. Audio shape:", audio.shape)
print("4. Sample rate:", sr)
print(
    "5. Duration:",
    f"{audio.shape[-1] / sr:.2f} s",
)
print("6. Audio dtype:", audio.dtype)
print(
    "7. Audio finite:",
    bool(np.isfinite(audio).all()),
)

if audio.shape[0] != 2:
    raise RuntimeError(
        f"Expected stereo audio, got shape {audio.shape}"
    )

# ------------------------------------------------------------
# Prepare one model chunk
# ------------------------------------------------------------

audio = torch.from_numpy(audio)

chunk = audio[:, :CHUNK_SIZE]

if chunk.shape[-1] < CHUNK_SIZE:
    chunk = torch.nn.functional.pad(
        chunk,
        (0, CHUNK_SIZE - chunk.shape[-1]),
    )

print("8. Chunk shape:", chunk.shape)
print(
    "9. Chunk duration:",
    f"{chunk.shape[-1] / SAMPLE_RATE:.2f} s",
)

# ------------------------------------------------------------
# Move to GPU
# ------------------------------------------------------------

chunk = chunk.unsqueeze(0).to(device)

print("10. Model device:", next(model.parameters()).device)
print("11. Input shape:", chunk.shape)
print("12. Input device:", chunk.device)

if torch.cuda.is_available():
    torch.cuda.reset_peak_memory_stats()

# ------------------------------------------------------------
# Forward pass
# ------------------------------------------------------------

print("13. Running model forward...")

with torch.inference_mode():
    with torch.autocast(
        device_type="cuda",
        dtype=torch.float16,
    ):
        prediction = model(chunk)

print("14. Forward: OK")
print("15. Prediction type:", type(prediction))

# ------------------------------------------------------------
# Inspect prediction
# ------------------------------------------------------------

if isinstance(prediction, (tuple, list)):

    print(
        "16. Number of outputs:",
        len(prediction),
    )

    for i, item in enumerate(prediction):

        if torch.is_tensor(item):

            print(
                f"    output[{i}]: "
                f"shape={tuple(item.shape)}, "
                f"dtype={item.dtype}, "
                f"device={item.device}"
            )

            print(
                f"    output[{i}] finite:",
                bool(torch.isfinite(item).all()),
            )

        else:
            print(
                f"    output[{i}]:",
                type(item),
            )

else:

    print(
        "16. Prediction shape:",
        tuple(prediction.shape),
    )

    print(
        "17. Prediction dtype:",
        prediction.dtype,
    )

    print(
        "18. Prediction device:",
        prediction.device,
    )

    print(
        "19. Prediction finite:",
        bool(torch.isfinite(prediction).all()),
    )

# ------------------------------------------------------------
# GPU memory
# ------------------------------------------------------------

if torch.cuda.is_available():

    peak_memory = (
        torch.cuda.max_memory_allocated()
        / 1024**3
    )

    print(
        f"20. Peak GPU memory: "
        f"{peak_memory:.2f} GiB"
    )

# ------------------------------------------------------------
# Cleanup
# ------------------------------------------------------------

del chunk
del prediction

if torch.cuda.is_available():
    torch.cuda.empty_cache()

print()
print("=== FORWARD TEST PASSED ===")
PY


echo
echo "=== PIP / VENV ==="
python -m pip --version
python -m venv --help | head -20

echo
echo "=== PIP INDEX ==="
python -m pip config list || true

echo
echo "=== PYTORCH AVAILABILITY ==="
python -m pip index versions torch 2>&1 | head -30 || true

echo "=== PYTHON ==="
which python
python --version

echo "========================================"
echo "WCSS ENVIRONMENT CHECK"
echo "========================================"

echo
echo "=== HOST ==="
hostname

echo
echo "=== TMPDIR ==="
echo "TMPDIR=${TMPDIR:-<not set>}"
df -h "${TMPDIR:-/tmp}" || true

echo
echo "=== MODULES ==="
module list 2>&1 || true

echo
echo "=== AVAILABLE PYTHON MODULES ==="
module avail Python 2>&1 || true

echo
echo "=== AVAILABLE PYTORCH MODULES ==="
module avail PyTorch 2>&1 || true

echo
echo "=== AVAILABLE CUDA MODULES ==="
module avail CUDA 2>&1 || true

echo
echo "=== PYTHON WITHOUT ADDITIONAL MODULES ==="
which python || true
python --version || true

echo
echo "=== GPU ==="
nvidia-smi || true

echo
echo "=== PYTHON TEST ==="
python - <<'PY'
import sys

print("Python executable:", sys.executable)
print("Python version:", sys.version)

try:
    import torch

    print("torch:", torch.__version__)
    print("torch path:", torch.__file__)
    print("torch CUDA version:", torch.version.cuda)
    print("CUDA available:", torch.cuda.is_available())

    if torch.cuda.is_available():
        print("GPU:", torch.cuda.get_device_name(0))

except Exception as e:
    print("torch import failed:", repr(e))

for package in [
    "torchaudio",
    "numpy",
    "scipy",
    "soundfile",
    "librosa",
    "einops",
    "omegaconf",
    "transformers",
    "demucs",
    "accelerate",
]:
    try:
        module = __import__(package)
        version = getattr(module, "__version__", "unknown")
        print(f"{package}: {version}")
    except Exception as e:
        print(f"{package}: NOT AVAILABLE ({e})")
PY

echo
echo "=== DONE ==="