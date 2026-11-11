#!/bin/bash
# Reproduce the Galaxy fairefier.xml command for each example workbook (defaults: checklist auto, not strict).
W=${EXAMPLES_RUN:?set EXAMPLES_RUN to a working folder that holds a copy of tools/}
E=${FAIRE_EXAMPLES:?set FAIRE_EXAMPLES to docs/examples in a copy of FAIR-eDNA.github.io}
PY=${PYTHON:-python -I -W ignore}
T=$W/tools/fairefier
for wb in metabarcoding/CPR_2015.xlsx metabarcoding/NECR534_GCN_metabarcoding.xlsx metabarcoding/verte_quadeloupe.xlsx \
          metabarcoding/IOT-eDNA/IOT-eDNA.xlsx metabarcoding/noaa-aoml-gomecc4/noaa-aoml-gomecc4.xlsx \
          targeted_assay/AEP_Fish_sedDNA.xlsx targeted_assay/EirwiniBurdekin.xlsx \
          targeted_assay/NECR534_GCN_single-species.xlsx targeted_assay/Rockfish_targeted_qPCR.xlsx; do
    name=$(basename "$wb" .xlsx)
    job=$W/jobs/fairefier/$name
    rm -rf "$job"; mkdir -p "$job"; cd "$job" || exit 1
    ln -s "$E/$wb" input.xlsx && mkdir out && \
    set -o pipefail; $PY "$T/fairefier_cli.py" input.xlsx --outdir out --checklist_dir "$T/checklist" --checklist_version auto \
        2> stderr.txt | tee log.txt > /dev/null
    echo "$name exit=$?"
done
