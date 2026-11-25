#!/usr/bin/env bash
# Makes the Shiny app's khapra beetle demonstration (shiny/demo/khapra) from the published files in
# demo/khapra: the sample table and qPCR results as a person following the guide prepares them, the
# Dryad README (data dictionary and methods), the notes from the paper, and the taxon table.
# Usage: bash dev/faire_mapper_khapra/make_app_demo.sh   (from anywhere; needs python with pandas)
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo="$here/../.."
d="$repo/demo/khapra"
out="$repo/shiny/demo/khapra"
mkdir -p "$out"
python "$here/prepare_table.py" "$d/Sample_metadata.csv" "$out/khapra_samples_prepared.csv"
python "$here/prepare_results.py" "$d/Amplification_data_khapra_05012022_dryad.csv" "$out/khapra_qpcr_prepared.csv"
cp "$d/Trujillo_Gonzalez_et_al_2022_README.txt" "$out/"
cp "$d/khapra_notes.md" "$out/"
cp "$here/taxa_khapra.tsv" "$out/khapra_taxa.tsv"
echo "written to $out"
