#!/bin/bash -l

#SBATCH --job-name=extract_reference
#SBATCH --account=hpc-danbor2008-1756464546
#SBATCH --qos=hpc-danbor2008-1756464546
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --partition=lem-cpu-short
#SBATCH --time=02:00:00
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err

source /etc/profile
module purge
module load FFmpeg/7.1.2-GCCcore-14.3.0

set -euo pipefail

PD_BASE=/lustre/pd03/hpc-danbor2008-1756464546/bs_roformer
INPUT_DIR="$PD_BASE/test"
REFERENCE_DIR="$PD_BASE/reference-dir"

mkdir -p "$REFERENCE_DIR"

echo "=== FFMPEG ==="
which ffmpeg
ffmpeg -version | head -1

echo "=== EXTRACT REFERENCES ==="

index=1

for input_file in "$INPUT_DIR"/*.mp4; do
    track_name=$(printf "track_%03d" "$index")
    track_dir="$REFERENCE_DIR/$track_name"

    mkdir -p "$track_dir"

    echo "=== $track_name : $(basename "$input_file") ==="

    ffmpeg -hide_banner -loglevel error -y \
        -i "$input_file" \
        -map 0:1 -ar 44100 -ac 2 \
        "$track_dir/drums.wav"

    ffmpeg -hide_banner -loglevel error -y \
        -i "$input_file" \
        -map 0:2 -ar 44100 -ac 2 \
        "$track_dir/bass.wav"

    ffmpeg -hide_banner -loglevel error -y \
        -i "$input_file" \
        -map 0:3 -ar 44100 -ac 2 \
        "$track_dir/other.wav"

    ffmpeg -hide_banner -loglevel error -y \
        -i "$input_file" \
        -map 0:4 -ar 44100 -ac 2 \
        "$track_dir/vocals.wav"

    index=$((index + 1))
done

echo "=== FINISHED ==="

TRACK_COUNT=$(find "$REFERENCE_DIR" -maxdepth 1 -type d -name 'track_*' | wc -l)
WAV_COUNT=$(find "$REFERENCE_DIR" -type f -name '*.wav' | wc -l)

echo "Tracks: $TRACK_COUNT"
echo "WAV files: $WAV_COUNT"

if [ "$TRACK_COUNT" -ne 50 ]; then
    echo "ERROR: Expected 50 tracks, found $TRACK_COUNT"
    exit 1
fi

if [ "$WAV_COUNT" -ne 200 ]; then
    echo "ERROR: Expected 200 WAV files, found $WAV_COUNT"
    exit 1
fi

du -sh "$REFERENCE_DIR"