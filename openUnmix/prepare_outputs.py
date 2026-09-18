from pathlib import Path
import stempeg
import soundfile as sf


BASE_DIR = Path(__file__).resolve().parent

INPUT_DIR = BASE_DIR / "dataset"
OUTPUT_DIR = BASE_DIR / "preprocessed_dataset"

TARGET_SR = 44100

STEMS = {
    1: "drums",
    2: "bass",
    3: "other",
    4: "vocals",
}

def main():
    files = sorted(INPUT_DIR.glob("*.stem.mp4"))

    print(f"Znaleziono {len(files)} plików .stem.mp4")

    if len(files) != 50:
        print("UWAGA: oczekiwano dokładnie 50 utworów.")

    for track_number, stem_file in enumerate(files, start=1):
        track_name = f"track_{track_number:03d}"
        track_dir = OUTPUT_DIR / track_name
        track_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n[{track_name}] {stem_file.name}")

        # Wczytanie wszystkich 5 stemów
        stems, samplerate = stempeg.read_stems(
            str(stem_file),
            sample_rate=TARGET_SR
        )

        print(f"  sample rate: {samplerate}")
        print(f"  shape: {stems.shape}")

        # stems ma postać:
        # [5, channels, samples]
        for stem_index, stem_name in STEMS.items():
            audio = stems[stem_index]

            output_file = track_dir / f"{stem_name}.wav"

            sf.write(
                output_file,
                audio,
                samplerate,
                subtype="PCM_16"
            )

            print(f"  -> {output_file}")


if __name__ == "__main__":
    main()
