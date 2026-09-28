import os
import soundfile as sf
from collections.abc import Callable

from .config import STORAGE_ROOT, SAFETY_LIMITER_THRESHOLD_DB, SAFETY_LIMITER_RELEASE_MS
from .effects import build_pedalboard, make_limiter
from .agent import decide_effects


def process_stem(
    input_path: str,
    user_prompt: str,
    mixed_output_path: str,
    stem_name: str,
    *,
    chosen_effects: dict | None = None,
    effects_decider: Callable[[str, str], dict] | None = None,
) -> dict:
    audio, sr = sf.read(input_path, always_2d=True)
    audio = audio.T  # pedalboard oczekuje (channels, samples)

    chosen = chosen_effects
    if chosen is None:
        chosen = (effects_decider or decide_effects)(user_prompt, stem_name)
    board = build_pedalboard(chosen)
    processed = board(audio, sr)

    if "limiter" not in chosen:
        safety = make_limiter(SAFETY_LIMITER_THRESHOLD_DB, SAFETY_LIMITER_RELEASE_MS)
        processed = safety(processed, sr)

    os.makedirs(os.path.dirname(mixed_output_path), exist_ok=True)
    sf.write(mixed_output_path, processed.T, sr)

    return {"mixed_output_path": mixed_output_path, "effects_used": chosen}


def process_job(manifest: dict, user_prompt: str) -> dict:
    job_id = manifest["job_id"]
    results = {}
    for stem_name, in_path in manifest["stems"].items():
        out_path = f"{STORAGE_ROOT}/{job_id}/mixed_{stem_name}.wav"        
        results[stem_name] = process_stem(in_path, user_prompt, out_path, stem_name)
    return results
