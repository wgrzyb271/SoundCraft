#!/bin/bash -l

#SBATCH --job-name=convert_wav
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

module load FFmpeg/7.1.2-GCCcore-14.3.0

set -euo pipefail

PD_BASE="$HOME/bs_roformer"
INPUT="$PD_BASE/test"
OUTPUT="$PD_BASE/test_wav"

mkdir -p "$OUTPUT"

echo "=== INPUT ==="
find "$INPUT" -maxdepth 1 -type f -name '*.mp4' | wc -l

for f in "$INPUT"/*.mp4; do
    name=$(basename "$f" .mp4)
    wav="$OUTPUT/${name}.wav"

    if [ -s "$wav" ]; then
        echo "SKIP: $name"
        continue
    fi

    echo "Converting: $name"

    ffmpeg \
        -hide_banner \
        -loglevel error \
        -y \
        -i "$f" \
        -vn \
        -ac 2 \
        -ar 44100 \
        "$wav"
done

echo "=== OUTPUT ==="
find "$OUTPUT" -maxdepth 1 -type f -name '*.wav' | wc -l
du -sh "$OUTPUT"