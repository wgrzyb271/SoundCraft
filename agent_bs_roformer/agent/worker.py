import argparse

from .model import load_model
from .audio import load_audio, save_stems
from .inference import separate_audio
from .validation import validate_output


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--repo", required=True)


    args = parser.parse_args()

    model, device, config = load_model(
        config_path=args.config,
        checkpoint_path=args.checkpoint,
        repo_path=args.repo,
    )

    sample_rate = config["audio"]["sample_rate"]
    chunck_size = config["audio"]["chunk_size"]

    audio = load_audio(
        args.input,
        sample_rate=sample_rate
    )

    separated = separate_audio(
        audio=audio,
        model=model,
        device=device,
        chunk_size=chunck_size,
        sample_rate=sample_rate,
        overlap=0.5,
    )

    save_stems(
        separated=separated,
        output_dir=args.output,
        sample_rate=sample_rate,
    )

    validate_output(args.output)


if __name__ == "__main__":
    main()