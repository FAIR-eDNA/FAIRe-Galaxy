#!/bin/bash
# Reproduce faire2ncbi_biosample.xml / faire2ncbi_sra.xml for the metabarcoding workbooks.
# usage: run_ncbi.sh MODE TAG [extra args...]   (MODE biosample|sra; TAG names the job folder)
W=${EXAMPLES_RUN:?set EXAMPLES_RUN to a working folder that holds a copy of tools/}
E=${FAIRE_EXAMPLES:?set FAIRE_EXAMPLES to docs/examples in a copy of FAIR-eDNA.github.io}/metabarcoding
PY=${PYTHON:-python -I -W ignore}
T=$W/tools/faire2ncbi
mode=$1; tag=$2; shift 2
while read -r wb organism; do
    name=$(basename "$wb" .xlsx)
    job=$W/jobs/faire2ncbi_${mode}_$tag/$name
    rm -rf "$job"; mkdir -p "$job"; cd "$job" || exit 1
    ln -s "$E/$wb" input.xlsx
    if [ "$mode" = biosample ]; then
        out=biosample_table.tsv
        set -o pipefail
        timeout 300 $PY "$T/faire2ncbi_galaxy.py" biosample --input_file input.xlsx --organism "$organism" \
            --sample_title default --extra_columns all --output $out --config_out config.yaml "$@" \
            < /dev/null 2> stderr.txt | tee log.txt > /dev/null
    else
        out=sra_table.tsv
        set -o pipefail
        timeout 300 $PY "$T/faire2ncbi_galaxy.py" sra --input_file input.xlsx --organism "$organism" \
            --output $out --config_out config.yaml "$@" < /dev/null 2> stderr.txt | tee log.txt > /dev/null
    fi
    rc=$?
    rows=$( [ -f $out ] && echo $(( $(wc -l < $out) )) || echo none)
    echo "$name exit=$rc lines=$rows :: $(grep -m1 -v '^\s*$' stderr.txt | cut -c1-200)"
done <<EOF
CPR_2015.xlsx marine metagenome
NECR534_GCN_metabarcoding.xlsx freshwater metagenome
verte_quadeloupe.xlsx marine metagenome
IOT-eDNA/IOT-eDNA.xlsx marine metagenome
noaa-aoml-gomecc4/noaa-aoml-gomecc4.xlsx marine metagenome
EOF
