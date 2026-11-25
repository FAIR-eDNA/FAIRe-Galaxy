#!/usr/bin/env bash
# Builds the workbooks of the four demonstration sets with their pipelines, then runs the sense check
# on each. Usage: bash dev/faire_sense_check/run_demos.sh OUTDIR
#   day/night: dev/faire_mapper_daynight/run.sh on demo/daynight (150 ASVs of each assay)
#   SEA-MES:   dev/faire_mapper_seames/run.sh (files 4, 7 and 8 of the record in its data/ folder)
#   khapra:    dev/faire_mapper_khapra/run.sh (qPCR)
#   eelgrass:  dev/faire_mapper_eelgrass/run_asvs.sh (the authors' per-ASV files, downloaded)
set -euo pipefail
out=${1:?usage: run_demos.sh OUTDIR}
here=$(cd "$(dirname "$0")" && pwd)
repo="$here/../.."
mkdir -p "$out"
DATA="$repo/demo/daynight" PYTHON="${PYTHON:-python3} -W ignore" bash "$repo/dev/faire_mapper_daynight/run.sh" "$out/daynight" > "$out/daynight.log" 2>&1
bash "$repo/dev/faire_mapper_seames/run.sh" "$out/seames" > "$out/seames.log" 2>&1 || true   # later steps may stop
bash "$repo/dev/faire_mapper_khapra/run.sh" "$out/khapra" > "$out/khapra.log" 2>&1
bash "$repo/dev/faire_mapper_eelgrass/run_asvs.sh" "$out/eelgrass" > "$out/eelgrass.log" 2>&1
for w in daynight seames khapra eelgrass; do
    "${PYTHON:-python3}" "$here/faire_sense_check.py" "$out/$w/faire/$w.xlsx" -o "$out/${w}_sense_check.html" \
        --flags "$out/${w}_flags.tsv"
done
