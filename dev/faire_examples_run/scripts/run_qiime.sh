#!/bin/bash
# Reproduce faire2qiime.xml with form defaults (sample ID lib_id, manifests on, no suffix).
W=${EXAMPLES_RUN:?set EXAMPLES_RUN to a working folder that holds a copy of tools/}
E=${FAIRE_EXAMPLES:?set FAIRE_EXAMPLES to docs/examples in a copy of FAIR-eDNA.github.io}/metabarcoding
PY=${PYTHON:-python -I -W ignore}
T=$W/tools/faire2qiime
col=${1:-lib_id}
for wb in CPR_2015.xlsx NECR534_GCN_metabarcoding.xlsx verte_quadeloupe.xlsx IOT-eDNA/IOT-eDNA.xlsx noaa-aoml-gomecc4/noaa-aoml-gomecc4.xlsx; do
    name=$(basename "$wb" .xlsx)
    job=$W/jobs/faire2qiime_$col/$name
    rm -rf "$job"; mkdir -p "$job"; cd "$job" || exit 1
    ln -s "$E/$wb" input.xlsx
    (
    set -o pipefail
    $PY "$T/normalise_faire.py" input.xlsx normalised.xlsx --check_column "$col" > log.txt 2> stderr.txt &&
    mkdir out &&
    $PY "$T/faire2qiime.py" --path_faire normalised.xlsx --sample_name_column "$col" \
        --absolute_path_sequences /path/to/sequences --output_directory out 2>> stderr.txt \
        | sed 's/\x1b\[[0-9;]*m//g' | grep -v -e 'pyfiglet' -e '^=*$' -e '^ *$' >> log.txt
    )
    rc=$?
    echo "$name exit=$rc metadata=$(ls out/*_metadata.tsv 2>/dev/null | wc -l) manifests=$(ls out/*_manifest.tsv 2>/dev/null | wc -l) :: $(grep -v '^\s*$' stderr.txt | tail -1 | cut -c1-200)"
done
