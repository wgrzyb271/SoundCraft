from pathlib import Path
import numpy as np 
import soundfile as sf
import torch 

STEMS = ["drums", "bass", "other", "vocals"]

def load_audio(path: str|Path, sample_rate:int) -> torch.Tensor:
    audio, sr = sf.read(str(path),dtype="float32",always_2d=True)

    if sr != sample_rate:
        raise ValueError( f"Expected sample rate {sample_rate}, got {sr} for {path}")

    audio = audio.T
    if audio.shape[0] == 1:
        audio = np.repeat(audio, 2, axis=0)
    if audio.shape[0] > 2:
        audio = audio[:2]

    return torch.from_numpy(audio)


def save_stems(separated:torch.Tensor, output_dir:str | Path, sample_rate:int)->None:
    output_dir = Path(output_dir)/"audio"
    output_dir.mkdir(parents=True,exist_ok=True)
    for i, stem_name in enumerate(STEMS):
        output_path = output_dir/f"{stem_name}.wav"
        sf.write(str(output_path),separated[i].cpu().numpy().T,sample_rate)
        print(f"Saved: {output_path}")