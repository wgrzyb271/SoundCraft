"""
Skrypt testowy SAM-Audio - optymalizacja RAM i poprawna obsługa API.
"""

import os
import stat
import sys

if "PDDIR" in os.environ:
    os.environ["HF_HOME"] = os.path.join(os.environ["PDDIR"], "wojgrz4918", "hf_cache")

import numpy as np
import torch
from dotenv import load_dotenv
from huggingface_hub import HfApi
from sam_audio import SAMAudio, SAMAudioProcessor
from sam_audio.model.base import BaseModel

# Patch na _from_pretrained
_orig = BaseModel._from_pretrained.__func__


@classmethod
def _patched(cls, *, proxies=None, resume_download=False, **kwargs):
    return _orig(cls, proxies=proxies, resume_download=resume_download, **kwargs)


BaseModel._from_pretrained = _patched

# Diagnostyka ImageBind
try:
    import imagebind  # noqa: F401

    print("✅ 'import imagebind' działa poprawnie.")
except Exception as e:
    print(f"\n⚠️  Błąd importu ImageBind: {e!r}\n")

print("NumPy Version:", np.__version__)

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

if os.path.exists(ENV_PATH):
    mode = stat.S_IMODE(os.stat(ENV_PATH).st_mode)
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        print(f"\n⚠️  Plik {ENV_PATH} ma zbyt otwarte uprawnienia ({oct(mode)}).")
        print(f"    Popraw: chmod 600 {ENV_PATH}")

load_dotenv(ENV_PATH)

hf_token = os.environ.get("HF_TOKEN")
if not hf_token:
    print(f"\n❌ Brak HF_TOKEN w {ENV_PATH}.")
    sys.exit(1)

try:
    user_info = HfApi(token=hf_token).whoami()
    print(f"\n✅ Success! Logged in as: {user_info['name']}")
    role = user_info.get("auth", {}).get("accessToken", {}).get("role", "unknown")
    print(f"🔑 Token permission level: {role}")
except Exception as e:
    print(f"\n❌ Authentication Error: {e}")
    sys.exit(1)

MODEL_ID = "facebook/sam-audio-small"

print(f"\nLoading {MODEL_ID}...")
processor = SAMAudioProcessor.from_pretrained(MODEL_ID)

dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16

model = SAMAudio.from_pretrained(
    MODEL_ID,
    torch_dtype=dtype,
    low_cpu_mem_usage=True
)

device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.eval().to(device, dtype=dtype)

print(f"✅ SAM-Audio successfully initialized on: {device.upper()} ({dtype})")


def cast_floats(obj, target_dtype, _seen=None):
    if _seen is None:
        _seen = set()

    if isinstance(obj, torch.Tensor):
        return obj.to(dtype=target_dtype) if obj.is_floating_point() else obj

    obj_id = id(obj)
    if obj_id in _seen:
        return obj
    _seen.add(obj_id)

    if hasattr(obj, "__dict__"):
        for k, v in vars(obj).items():
            try:
                setattr(obj, k, cast_floats(v, target_dtype, _seen))
            except AttributeError:
                pass
        return obj

    if isinstance(obj, dict):
        return {k: cast_floats(v, target_dtype, _seen) for k, v in obj.items()}
    if isinstance(obj, list):
        return [cast_floats(v, target_dtype, _seen) for v in obj]
    if isinstance(obj, tuple):
        return tuple(cast_floats(v, target_dtype, _seen) for v in obj)

    return obj


# Input audio 3D: (batch, channels, samples)
sample_rate = 16000
duration = 1.0
dummy_audio = torch.randn(1, 1, int(sample_rate * duration), dtype=dtype)
text_prompt = "speech"

inputs = processor(
    audios=dummy_audio,
    descriptions=[text_prompt]
)

if hasattr(inputs, "to"):
    inputs = inputs.to(device)

inputs = cast_floats(inputs, dtype)

with torch.no_grad():
    outputs = model.separate(inputs)

print("\n✅ Przetwarzanie zakończone sukcesem!")
print("Typ obiektu wyjściowego:", type(outputs))

public_fields = [f for f in dir(outputs) if not f.startswith("_")]
print("Dostępne pola obiektu wyjściowego:", public_fields)

for candidate in ("audio", "waveform", "separated_audio", "audios", "samples", "masks"):
    if hasattr(outputs, candidate):
        value = getattr(outputs, candidate)
        shape = getattr(value, "shape", None)
        print(f"  pole '{candidate}' -> typ {type(value)}", f"kształt {shape}" if shape is not None else "")
