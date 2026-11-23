#!/usr/bin/env bash
# Makes the Shiny app's eelgrass demonstration (shiny/demo/eelgrass) from the published files in
# demo/eelgrass: the sample table a person following the guide makes, the species table, the Dryad
# README (data dictionary and methods), the project values and the taxon table.
# Usage: bash dev/faire_mapper_eelgrass/make_app_demo.sh   (from anywhere; needs python with pandas)
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo="$here/../.."
d="$repo/demo/eelgrass"
out="$repo/shiny/demo/eelgrass"
mkdir -p "$out"
python "$here/prepare_table.py" "$d/Final_ASVTable_withTaxonomy_Filtered.csv" "$d/Site_coordinates.csv" \
    "$out/eelgrass_samples_prepared.csv"
python "$here/make_taxa.py" "$d/Final_ASVTable_withTaxonomy_Filtered.csv" "$out/eelgrass_taxa.tsv"
cp "$d/Final_ASVTable_withTaxonomy_Filtered.csv" "$d/Dryad_README.md" "$out/"
cp "$here/project_values.tsv" "$out/eelgrass_project_values.tsv"
chmod 644 "$out"/*
echo "written to $out"
