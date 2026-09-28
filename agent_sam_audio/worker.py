"""GPU worker for text-prompted separation with facebook/sam-audio-base."""
from __future__ import annotations

import argparse
from pathlib import Path

import torch
import torchaudio
from sam_audio import SAMAudio, SAMAudioProcessor


def separate(input_path: Path, prompt: str, output_path: Path, model_id: str) -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("SAM Audio requires a CUDA GPU on WCSS")
    device = torch.device("cuda")
    model = SAMAudio.from_pretrained(model_id).eval().to(device)
    processor = SAMAudioProcessor.from_pretrained(model_id)
    batch = processor(audios=[str(input_path)], descriptions=[prompt]).to(device)
    with torch.inference_mode():
        result = model.separate(batch, predict_spans=False, reranking_candidates=1)

    target = result.target.detach().cpu()
    if target.ndim == 3 and target.shape[0] == 1:
        target = target[0]
    if target.ndim == 1:
        target = target.unsqueeze(0)
    if target.ndim != 2:
        raise RuntimeError(f"Unexpected SAM Audio target shape: {tuple(target.shape)}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torchaudio.save(str(output_path), target, processor.audio_sampling_rate)


def main() -> None:
    parser = argparse.ArgumentParser(description="SAM Audio Base worker")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="facebook/sam-audio-base")
    args = parser.parse_args()
    prompt = args.prompt_file.read_text(encoding="utf-8").strip()
    if not prompt:
        raise ValueError("SAM Audio prompt cannot be empty")
    separate(args.input, prompt, args.output, args.model)


if __name__ == "__main__":
    main()
