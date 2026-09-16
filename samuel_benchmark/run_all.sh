#!/usr/bin/env bash
#
# run_all.sh — odpala cały pipeline SAM-Audio-small (README "Kolejność
# uruchomienia") jedną komendą. Domyślnie NIE WYMAGA ŻADNYCH FLAG —
# skrypt sam wykrywa katalogi:
#
#   1. reference-dir (./musdb18_test_wav) — jeśli już istnieje i ma w
#      środku katalogi utworów, KROK prepare_reference.py jest pomijany.
#   2. jeśli reference-dir nie istnieje — skrypt szuka surowego MUSDB18
#      w typowych lokalizacjach (patrz CANDIDATE_MUSDB_ROOTS niżej) albo
#      w zmiennej środowiskowej MUSDB_ROOT.
#   3. selected-tracks (5 utworów do package_results.py) — jeśli nie
#      podasz ich ręcznie, skrypt bierze pierwsze 5 katalogów z
#      reference-dir w kolejności alfabetycznej. To jest DETERMINISTYCZNE
#      (ta sama kolejność u każdego, kto ma ten sam, współdzielony
#      reference-dir), ale to NIE zastępuje ustalenia listy z zespołem
#      wg pkt 5.0 protokołu — traktuj to jako sensowny domyślny wybór,
#      nie jako oficjalną decyzję za zespół. Jeśli zespół ustalił inną
#      piątkę, podaj ją przez --selected-tracks.
#
# UŻYCIE (najprostsze — wszystko automatycznie):
#   ./run_all.sh
#
# UŻYCIE (z ręcznym nadpisaniem czegokolwiek):
#   ./run_all.sh --musdb-root /sciezka/do/musdb18 \
#                --selected-tracks TRACK_A TRACK_B TRACK_C TRACK_D TRACK_E \
#                --limit 5
#
# Wymaga: requirements.txt, prepare_reference.py, run_samaudio_benchmark.py,
#         package_results.py, evaluator.py, benchmark_common.py — wszystkie
#         w tym samym katalogu co ten skrypt.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Typowe miejsca, gdzie może leżeć surowy (niepoprocesowany) MUSDB18,
# jeśli reference-dir jeszcze nie istnieje. Kolejność = priorytet.
CANDIDATE_MUSDB_ROOTS=(
    "${MUSDB_ROOT:-}"
    "./musdb18"
    "../musdb18"
    "$HOME/musdb18"
    "$HOME/datasets/musdb18"
    "/data/musdb18"
    "/mnt/data/musdb18"
)

MUSDB_ROOT_ARG=""
SELECTED_TRACKS=()
SKIP_INSTALL=0
LIMIT_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --musdb-root)
            MUSDB_ROOT_ARG="$2"; shift 2 ;;
        --selected-tracks)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                SELECTED_TRACKS+=("$1"); shift
            done ;;
        --skip-install)
            SKIP_INSTALL=1; shift ;;
        --limit)
            LIMIT_ARGS=(--limit "$2"); shift 2 ;;
        *)
            echo "Nieznany argument: $1" >&2; exit 1 ;;
    esac
done

REFERENCE_DIR="./musdb18_test_wav"
OUTPUTS_DIR="./samaudio_outputs"
INFERENCE_TIMES="./samaudio_inference_times.json"
RESULTS_CSV="./samaudio_results.csv"
SUMMARY_CSV="./samaudio_summary.csv"
DEST="./SamAudio"

# --- Krok 0: zależności -----------------------------------------------
if [[ "$SKIP_INSTALL" -eq 0 ]]; then
    echo "==> [0/4] Instalacja zależności"
    pip install -r requirements.txt --break-system-packages
else
    echo "==> [0/4] Pominięto instalację zależności (--skip-install)"
fi

# --- Krok 1: reference-dir (auto-wykrywanie) ----------------------------
reference_dir_ready() {
    [[ -d "$REFERENCE_DIR" ]] && [[ -n "$(find "$REFERENCE_DIR" -mindepth 1 -maxdepth 1 -type d -print -quit)" ]]
}

if reference_dir_ready; then
    echo "==> [1/4] Znaleziono gotowy reference-dir: $REFERENCE_DIR (pomijam prepare_reference.py)"
else
    echo "==> [1/4] Brak gotowego $REFERENCE_DIR — szukam surowego MUSDB18..."

    FOUND_ROOT=""
    if [[ -n "$MUSDB_ROOT_ARG" ]]; then
        FOUND_ROOT="$MUSDB_ROOT_ARG"
    else
        for candidate in "${CANDIDATE_MUSDB_ROOTS[@]}"; do
            [[ -z "$candidate" ]] && continue
            if [[ -d "$candidate" ]]; then
                FOUND_ROOT="$candidate"
                echo "    znaleziono: $candidate"
                break
            fi
        done
    fi

    if [[ -z "$FOUND_ROOT" ]]; then
        echo "Błąd: nie znalazłem ani gotowego $REFERENCE_DIR, ani surowego MUSDB18" >&2
        echo "      w żadnej z typowych lokalizacji ani w \$MUSDB_ROOT." >&2
        echo "      Podaj ręcznie: ./run_all.sh --musdb-root /sciezka/do/musdb18" >&2
        exit 1
    fi

    python prepare_reference.py \
        --musdb-root "$FOUND_ROOT" \
        --reference-dir "$REFERENCE_DIR" \
        "${LIMIT_ARGS[@]}"
fi

# --- Krok 1b: selected-tracks (auto-wykrywanie) -------------------------
if [[ "${#SELECTED_TRACKS[@]}" -eq 0 ]]; then
    mapfile -t SELECTED_TRACKS < <(
        find "$REFERENCE_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | LC_ALL=C sort | head -n 5
    )
    echo "==> Nie podano --selected-tracks — automatycznie wybrano pierwsze 5 (alfabetycznie):"
    printf '    - %s\n' "${SELECTED_TRACKS[@]}"
    echo "    (jeśli zespół ustalił inną piątkę wg pkt 5.0 protokołu, odpal ponownie z --selected-tracks)"
fi
if [[ "${#SELECTED_TRACKS[@]}" -ne 5 ]]; then
    echo "Błąd: w $REFERENCE_DIR jest mniej niż 5 katalogów utworów — nie mam czego wybrać automatycznie." >&2
    exit 1
fi

# --- Krok 2: benchmark ---------------------------------------------------
echo "==> [2/4] Benchmark SAM-Audio-small"
python run_samaudio_benchmark.py \
    --reference-dir "$REFERENCE_DIR" \
    --outputs-dir "$OUTPUTS_DIR" \
    --inference-times-output "$INFERENCE_TIMES" \
    "${LIMIT_ARGS[@]}"

# --- Krok 3: metryki ------------------------------------------------------
echo "==> [3/4] Liczenie metryk (evaluator.py)"
python evaluator.py \
    --model-name SamAudio \
    --outputs-dir "$OUTPUTS_DIR" \
    --reference-dir "$REFERENCE_DIR" \
    --inference-times "$INFERENCE_TIMES" \
    --output "$RESULTS_CSV" \
    --summary-output "$SUMMARY_CSV"

# --- Krok 4: finalna struktura ---------------------------------------------
echo "==> [4/4] Składanie finalnej struktury do repo"
python package_results.py \
    --model-name SamAudio \
    --outputs-dir "$OUTPUTS_DIR" \
    --results-csv "$RESULTS_CSV" \
    --selected-tracks "${SELECTED_TRACKS[@]}" \
    --dest "$DEST"

echo ""
echo "✅ Gotowe. Struktura do repo: $DEST/"
echo "   Wybrane utwory (selected-tracks): ${SELECTED_TRACKS[*]}"
echo "   Nie zapomnij ręcznie uzupełnić $DEST/README.md (pola TODO)."
