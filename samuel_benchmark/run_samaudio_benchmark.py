#!/usr/bin/env python3
import sys
import argparse
import os
import stat
import gc
from pathlib import Path

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

if "PDDIR" in os.environ:
    os.environ.setdefault(
        "HF_HOME", os.path.join(os.environ["PDDIR"], "wojgrz4918", "hf_cache")
    )

from benchmark_common import STEMS, TARGET_SR, list_track_dirs, load_wav, save_wav, timer, write_inference_times

PROMPTS = {
    "vocals": "vocals",
    "drums": "drums",
    "bass": "bass",
    "other": "other instruments",
}

_OUTPUT_FIELD_CANDIDATES = ("target", "audio", "waveform", "separated_audio", "audios", "samples", "masks")


def _extract_separated_audio(outputs):
    for field in _OUTPUT_FIELD_CANDIDATES:
        if hasattr(outputs, field):
            value = getattr(outputs, field)
            if value is not None:
                return value
    if isinstance(outputs, (tuple, list)) and len(outputs) > 0:
        return outputs[0]
    available = [f for f in dir(outputs) if not f.startswith("_")]
    raise AttributeError(
        f"Nie znaleziono znanego pola audio w wyniku typu {type(outputs)}. "
        f"Dostępne pola: {available}."
    )


def _to_tensor(value, debug_label=""):
    import torch

    while isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError(f"[{debug_label}] Otrzymano pustą listę/krotkę zamiast tensora audio.")
        value = value[0]

    if not torch.is_tensor(value):
        raise TypeError(f"[{debug_label}] Oczekiwano torch.Tensor po rozpakowaniu, otrzymano {type(value)}: {value!r}")

    return value


def load_hf_token() -> str:
    from dotenv import load_dotenv

    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        mode = stat.S_IMODE(env_path.stat().st_mode)
        if mode & (stat.S_IRWXG | stat.S_IRWXO):
            print(f"⚠️ {env_path} ma zbyt otwarte uprawnienia ({oct(mode)}). Popraw: chmod 600 {env_path}")
    load_dotenv(env_path)

    token = os.environ.get("HF_TOKEN")
    if not token:
        sys.exit(f"Brak HF_TOKEN w {env_path}. Utwórz .env z HF_TOKEN=... i chmod 600 .env")
    return token


def main():
    parser = argparse.ArgumentParser(description="Benchmark SAM-Audio na MUSDB18 test set.")
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--outputs-dir", type=Path, required=True)
    parser.add_argument("--inference-times-output", type=Path, required=True)
    parser.add_argument("--model-id", default="facebook/sam-audio-small")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    hf_token = load_hf_token()

    import numpy as np
    import torch
    from sam_audio import SAMAudio, SAMAudioProcessor
    from sam_audio.model.base import BaseModel

    _orig_base_fp = BaseModel._from_pretrained.__func__

    @classmethod
    def _patched_base_fp(cls, *, proxies=None, resume_download=False, **kwargs):
        return _orig_base_fp(cls, proxies=proxies, resume_download=resume_download, **kwargs)

    BaseModel._from_pretrained = _patched_base_fp

    track_dirs = list_track_dirs(args.reference_dir)
    track_dirs = [d for d in track_dirs if (d / "mixture.wav").exists()]
    if args.limit:
        track_dirs = track_dirs[: args.limit]
    if not track_dirs:
        sys.exit(f"Nie znaleziono żadnego mixture.wav w {args.reference_dir}")

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # bf16 dla WAG modelu (mniejsze zużycie pamięci przy ładowaniu i
    # przechowywaniu parametrów). NIE rzutujemy jednak wejść (inputs)
    # ręcznie przez _cast_floats — to powodowało realny bug:
    # _cast_floats rzutowało KAŻDY tensor zmiennoprzecinkowy w obiekcie
    # inputs, w tym prawdopodobnie wewnętrzną długość/maskę audio
    # przechowywaną przez processor jako float. bf16 ma tylko ~8 bitów
    # mantysy, więc dla długości ~9.3M próbek błąd zaokrąglenia sięgał
    # dziesiątek tysięcy próbek — zaobserwowano dokładnie to:
    # unbatch() próbował przyciąć do 9306112 zamiast poprawnych 9258240
    # (różnica 47872 ~ błąd zaokrąglenia bf16 dla liczby tej wielkości).
    # Zamiast tego używamy torch.autocast wokół właściwego wywołania
    # modelu — PyTorch sam dobiera precyzję per operacja w trakcie
    # forward(), nie dotykając wartości przechowywanych w obiekcie
    # inputs (np. długości audio używanej później do indeksowania).
    dtype = torch.bfloat16 if device == "cuda" and torch.cuda.is_bf16_supported() else torch.float32

    print(f"Ładowanie {args.model_id} na {device.upper()} ({dtype})...")
    processor = SAMAudioProcessor.from_pretrained(args.model_id)
    model = SAMAudio.from_pretrained(
        args.model_id,
        torch_dtype=dtype,
        low_cpu_mem_usage=True,
    )
    model = model.eval().to(device, dtype=dtype)

    inference_times = {}

    for i, track_dir in enumerate(track_dirs, 1):
        track = track_dir.name
        mixture, sr = load_wav(track_dir / "mixture.wav")
        mixture_t = torch.from_numpy(mixture.T).float().unsqueeze(0)

        out_dir = args.outputs_dir / track
        total_elapsed = 0.0

        for stem in STEMS:
            prompt = PROMPTS[stem]
            with timer() as t:
                inputs = processor(
                    audios=mixture_t,
                    descriptions=[prompt],
                )
                if hasattr(inputs, "to"):
                    inputs = inputs.to(device)
                with torch.no_grad():
                    if device == "cuda":
                        with torch.autocast(device_type="cuda", dtype=dtype):
                            outputs = model.separate(inputs)
                    else:
                        outputs = model.separate(inputs)
            elapsed = t()
            total_elapsed += elapsed

            separated = _extract_separated_audio(outputs)
            separated = _to_tensor(separated, debug_label=f"{track}/{stem}")

            separated_np = separated.detach().cpu().float().numpy()
            if separated_np.ndim == 1:
                separated_np = separated_np[:, None]
            else:
                if separated_np.ndim == 3:
                    separated_np = np.squeeze(separated_np, axis=0)
                if separated_np.shape[0] < separated_np.shape[-1]:
                    separated_np = separated_np.T

            # SAM-Audio zwraca audio MONO (1 kanał), ale referencje MUSDB18
            # są STEREO (2 kanały) — museval.bss_eval wymaga zgodnej liczby
            # kanałów między estimate a reference. Duplikujemy pojedynczy
            # kanał modelu na L i R. To jest jawne założenie upraszczające
            # (nie jest to prawdziwa separacja stereo) — jeśli w przyszłości
            # potrzebna będzie ocena jakości stereo-obrazu, ta linia jest
            # miejscem do zmiany.
            if separated_np.ndim == 2 and separated_np.shape[1] == 1:
                separated_np = np.repeat(separated_np, 2, axis=1)
            save_wav(out_dir / f"{stem}.wav", separated_np.astype("float32"), TARGET_SR)
            print(f"  [{i}/{len(track_dirs)}] {track}/{stem} (prompt='{prompt}'): {elapsed:.2f}s")

            del inputs, outputs, separated, separated_np
            if device == "cuda":
                torch.cuda.empty_cache()
            gc.collect()

        inference_times[track] = total_elapsed
        del mixture, mixture_t
        if device == "cuda":
            torch.cuda.empty_cache()
        gc.collect()

    write_inference_times(inference_times, args.inference_times_output)
    print(f"\n✅ Gotowe. Output: {args.outputs_dir}")
    print(f"   Czasy inferencji: {args.inference_times_output}")


if __name__ == "__main__":
    main()
