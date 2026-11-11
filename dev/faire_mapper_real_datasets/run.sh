#!/usr/bin/env bash
# Run the FAIRe mapper on four published Dryad eDNA datasets and score it against independent answer keys.
# Usage: run.sh OUTDIR        (needs python with pandas and openpyxl)
# Steps for each dataset:
#   1. faire_mapper.py map on the sample table (no model)
#   2. faire_mapper_adjudicate.py checks the stand-in model's answers to the review requests
#   3. faire_mapper.py map again with those answers
#   4. faire_mapper_methods.py checks the stand-in model's values from the methods text
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools="$here/../../tools/faire_mapper"
ck="$tools/checklist/FAIRe_checklist_v1.0.2.xlsx"
out=${1:?usage: run.sh OUTDIR}
mkdir -p "$out/mapper" "$out/with_model" "$out/methods"
declare -A table args methods
table[mathon]="$here/data/mathon/Metadata_eDNA_global_V6.csv";      args[mathon]="--sample_types Water"
table[sacco]="$here/data/sacco/mapping_file_Sacco_et_al.xlsx";      args[sacco]="--sample_types Water"
table[vanderheyde]="$here/data/vanderheyde/Barrow_18S_sample_data2.csv"; args[vanderheyde]="--sample_types Water,Sediment"
table[jackman]="$here/data/jackman/README-file.xlsx";               args[jackman]="--sheet DNA_Extractions --header_row 2 --sample_types Water"
methods[mathon]="$here/data/mathon/README.md"
methods[sacco]="$here/data/sacco/methods.txt $here/data/sacco/readme.txt"
methods[vanderheyde]="$here/data/vanderheyde/methods.txt"
methods[jackman]="$here/data/jackman/methods.txt $here/data/jackman/readme.txt"
for n in mathon sacco vanderheyde jackman; do
  echo "== $n"
  python "$tools/faire_mapper.py" map "${table[$n]}" ${args[$n]} --checklist "$ck" --assay_type metabarcoding -o "$out/mapper/$n"
  python "$tools/faire_mapper_adjudicate.py" "$out/mapper/$n/adjudication_requests.json" \
      --answers_from "$here/standin_answers/$n.adjudication.json" --answered_by "model:stand-in (Claude Sonnet)" \
      -o "$out/with_model/$n.responses.json" \
      --log "$out/with_model/$n.answers_log.tsv"
  python "$tools/faire_mapper.py" map "${table[$n]}" ${args[$n]} --checklist "$ck" --assay_type metabarcoding \
      --responses "$out/with_model/$n.responses.json" -o "$out/with_model/$n"
  python "$tools/faire_mapper_methods.py" ${methods[$n]} --checklist "$ck" --assay_type metabarcoding --sample_types "${args[$n]##*--sample_types }" \
      --report "$out/with_model/$n/mapping_report.tsv" --answers_from "$here/standin_answers/$n.methods.json" \
      -o "$out/methods/$n.values.tsv"
done
python "$here/score.py" "$here/gold" "$out/mapper" "$out/with_model"
