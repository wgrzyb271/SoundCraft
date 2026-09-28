#!/usr/bin/env bash
# Wybiera partycję CPU i wysyła worker SoundCraft do Slurma.

source /etc/profile
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SBATCH_SCRIPT="$PROJECT_ROOT/scripts/wcss_worker.sbatch"
ACCOUNT="${WCSS_SLURM_ACCOUNT:-hpc-danbor2008-1756464546}"
QOS="${WCSS_SLURM_QOS:-$ACCOUNT}"

mkdir -p /home/wojgrz4918/tmp/logs

if [[ -n "${WCSS_WORKER_PARTITION:-}" ]]; then
    PARTITION="$WCSS_WORKER_PARTITION"
else
    mapfile -t PARTITIONS < <(sinfo -h -o '%P' | tr -d '*' | sort -u)
    PARTITION=""
    for candidate in lem-cpu-short lem-cpu; do
        for available in "${PARTITIONS[@]}"; do
            if [[ "$candidate" == "$available" ]]; then
                PARTITION="$candidate"
                break 2
            fi
        done
    done
    if [[ -z "$PARTITION" ]]; then
        echo "Nie znaleziono partycji CPU lem-cpu-short ani lem-cpu." >&2
        echo "Dostępne partycje:" >&2
        printf '  %s\n' "${PARTITIONS[@]}" >&2
        echo "Ustaw właściwą ręcznie, np. WCSS_WORKER_PARTITION=PARTYCJA $0" >&2
        exit 2
    fi
fi

JOB_ID="$(sbatch --parsable \
    --account="$ACCOUNT" \
    --qos="$QOS" \
    --partition="$PARTITION" \
    "$SBATCH_SCRIPT")"

echo "SoundCraft worker submitted."
echo "Job ID: $JOB_ID"
echo "Partition: $PARTITION"
echo "Status: squeue -j $JOB_ID"
echo "Output: /home/wojgrz4918/tmp/logs/soundcraft-worker-$JOB_ID.out"
echo "Errors: /home/wojgrz4918/tmp/logs/soundcraft-worker-$JOB_ID.err"
