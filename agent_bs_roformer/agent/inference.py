import torch

@torch.inference_mode()
def separate_audio(audio:torch.Tensor,model,device: torch.device,chunk_size:int,sample_rate:int,overlap=0.5) -> torch.Tensor:

    model.eval()
    audio = audio.float()

    if audio.ndim != 2:
        raise ValueError(f"Expected audio [channels, samples], got {audio.shape}")

    channels, total_samples = audio.shape

    if channels != 2:
        raise ValueError(f"BS-Roformer config expects stereo audio, got {channels} channels")

    step = int(chunk_size * (1.0 - overlap))

    if not 0.0 <= overlap < 1.0:
        raise ValueError(
            "overlap must satisfy 0.0 <= overlap < 1.0"
        )

    output = torch.zeros(4,2,total_samples,dtype=torch.float32)

    weight = torch.zeros(total_samples, dtype=torch.float32)
    window = torch.hann_window(chunk_size,dtype=torch.float32)
    positions = list(range(0, max(total_samples - chunk_size, 0) + 1, step))

    if not positions or positions[-1] + chunk_size < total_samples:
        positions.append(max(total_samples - chunk_size, 0))

    for i, start in enumerate(positions):

        end = min(start + chunk_size, total_samples)

        chunk_len = end - start
        chunk = audio[:, start:end]

        if chunk_len < chunk_size:
            chunk = torch.nn.functional.pad(chunk,(0, chunk_size - chunk_len))

        chunk = chunk.unsqueeze(0).to(device)

        print(
            f"Chunk {i+1}/{len(positions)} "
            f"[{start / sample_rate:.1f}s - {end / sample_rate:.1f}s]"
        )

        with torch.autocast(device_type="cuda", dtype=torch.float16):
            prediction = model(chunk)

        prediction = prediction[0].float().cpu()
        prediction = prediction[:, :, :chunk_len]

        w = window[:chunk_len]
        output[:, :, start:end] += prediction * w
        weight[start:end] += w

        del chunk, prediction

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    weight = weight.clamp_min(1e-8)

    output /= weight[None, None, :]

    return output