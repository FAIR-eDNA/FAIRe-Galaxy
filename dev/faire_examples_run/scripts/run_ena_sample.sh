#!/bin/bash
# Reproduce faire2ena_sample.xml (centre CSIRO, dates converted, taxon from the form) for the metabarcoding workbooks.
W=${EXAMPLES_RUN:?set EXAMPLES_RUN to a working folder that holds a copy of tools/}
E=${FAIRE_EXAMPLES:?set FAIRE_EXAMPLES to docs/examples in a copy of FAIR-eDNA.github.io}/metabarcoding
PY=${PYTHON:-python -I -W ignore}
T=$W/tools/faire2ena
while read -r wb taxon; do
    name=$(basename "$wb" .xlsx)
    job=$W/jobs/faire2ena_sample/$name
    rm -rf "$job"; mkdir -p "$job"; cd "$job" || exit 1
    ln -s "$E/$wb" input.xlsx
    set -o pipefail
    $PY "$T/faire2ena_galaxy.py" sample --input_file input.xlsx --center_name CSIRO --taxon_id "$taxon" \
        --output_file samples.xml --submission_file submission.xml 2> stderr.txt | tee log.txt > /dev/null
    echo "$name exit=$?"
done <<EOF
CPR_2015.xlsx 408172
NECR534_GCN_metabarcoding.xlsx 449393
verte_quadeloupe.xlsx 408172
IOT-eDNA/IOT-eDNA.xlsx 408172
noaa-aoml-gomecc4/noaa-aoml-gomecc4.xlsx 408172
EOF
