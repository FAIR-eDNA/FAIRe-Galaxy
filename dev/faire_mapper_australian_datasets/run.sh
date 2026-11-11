#!/usr/bin/env bash
# Run the FAIRe mapper on two Australian eDNA datasets and score it against independent answer keys.
# Usage: run.sh OUTDIR        (needs python with pandas and openpyxl)
# Steps for each dataset, as in dev/faire_mapper_real_datasets:
#   1. faire_mapper.py map on the sample table (no model)
#   2. faire_mapper_adjudicate.py checks the stand-in model's answers to the review requests
#   3. faire_mapper.py map again with those answers
#   4. faire_mapper_methods.py checks the stand-in model's values from the methods text
#   5. faire_primers.py text: candidate primer pairs from the methods text
#   6. faire_mapper_apply.py: a FAIRe workbook from the table, the crosswalk with the model's answers
#      (matches for review included), the values from the methods text and the country
#      and, for Kimberley, the read matrix as OTU and taxonomy tables
#   7. FAIRe-fier (tools/fairefier) checks the workbook
#   8. if RSCRIPT is set (an Rscript with readxl, openxlsx, dplyr and tibble), FAIRe2MDT converts the
#      Kimberley workbook for GBIF's Metabarcoding Data Toolkit
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools="$here/../../tools/faire_mapper"
ck="$tools/checklist/FAIRe_checklist_v1.0.2.xlsx"
out=${1:?usage: run.sh OUTDIR}
mkdir -p "$out/mapper" "$out/with_model" "$out/methods" "$out/primers" "$out/faire"
declare -A table methods project assays
project[dibattista]=lizard_island_2019; assays[dibattista]=Fish16S,CoralITS2,CoralITS2_acro
project[kimberley]=kimberley_2017_2018; assays[kimberley]=16SFish,COIElasmobranch,16SReptile
declare -A otu dict
otu[dibattista]=""
# The Dryad README describes every column of the DiBattista table: used as the data dictionary.
dict[dibattista]="--dictionary $here/data/dibattista/README.md"
dict[kimberley]=""
# The matrix sums reads per taxon over all three assays (bony fish from any assay); written under
# 16SFish for the trial, as FAIRe tables are per assay.
otu[kimberley]="--otu $here/data/kimberley/Actinopterygii_read_abundance_matrix.xlsx --otu_assay 16SFish --otu_run kimberley_2017_2018"
table[dibattista]="$here/data/dibattista/LI_sampling_metadata.csv"
table[kimberley]="$here/data/kimberley/site_metadata_TableS1.csv"
methods[dibattista]="$here/data/dibattista/methods.txt $here/data/dibattista/README.md"
methods[kimberley]="$here/data/kimberley/methods.txt"
if [ ! -f "$here/data/dibattista/methods.txt" ]; then
  echo "data/dibattista/methods.txt is missing: see README.md (the paper is not openly licensed, so its methods are not stored)" >&2
  exit 1
fi
for n in dibattista kimberley; do
  echo "== $n"
  python "$tools/faire_mapper.py" map "${table[$n]}" --sample_types Water --checklist "$ck" --assay_type metabarcoding \
      ${dict[$n]} -o "$out/mapper/$n"
  python "$tools/faire_mapper_adjudicate.py" "$out/mapper/$n/adjudication_requests.json" \
      --answers_from "$here/standin_answers/$n.adjudication.json" --answered_by "model:stand-in (Claude Sonnet)" \
      -o "$out/with_model/$n.responses.json" --log "$out/with_model/$n.answers_log.tsv"
  python "$tools/faire_mapper.py" map "${table[$n]}" --sample_types Water --checklist "$ck" --assay_type metabarcoding \
      ${dict[$n]} --responses "$out/with_model/$n.responses.json" -o "$out/with_model/$n"
  python "$tools/faire_mapper_methods.py" ${methods[$n]} --checklist "$ck" --assay_type metabarcoding --sample_types Water \
      --report "$out/with_model/$n/mapping_report.tsv" --answers_from "$here/standin_answers/$n.methods.json" \
      -o "$out/methods/$n.values.tsv"
  python "$tools/faire_primers.py" text $(echo ${methods[$n]} | cut -d' ' -f1) -o "$out/primers/$n.candidates.tsv"
  python "$tools/faire_mapper_apply.py" "${table[$n]}" --crosswalk "$out/with_model/$n/crosswalk.sssom.tsv" \
      --checklist "$ck" --template "$tools/checklist/FAIRe_checklist_v1.0.2_FULLtemplate.xlsx" --sample_types Water \
      --project_id "${project[$n]}" --assay_name "${assays[$n]}" --country Australia --include_review \
      --project_values "$out/methods/$n.values.tsv" ${otu[$n]} -o "$out/faire/$n.xlsx" --log "$out/faire/$n.log"
  python "$here/../../tools/fairefier/fairefier_cli.py" "$out/faire/$n.xlsx" -o "$out/faire/fairefier_$n" \
      --checklist_dir "$here/../../tools/fairefier/checklist"
done
if [ -n "${RSCRIPT:-}" ]; then
  m="$here/../../tools/faire2mdt"
  (cd "$out/faire" && "$RSCRIPT" --vanilla "$m/faire2mdt_galaxy.R" --upstream "$m/FAIRe2MDT.R" \
      --target_genes "$m/mdt_target_gene.tsv" --workbook kimberley.xlsx --assay 16SFish --seq_run kimberley_2017_2018 \
      --otu kimberley.xlsx --otu_format xlsx --otu_sheet otuFinal_16SFish --taxa kimberley.xlsx --taxa_format xlsx \
      --taxa_sheet taxaFinal_16SFish --output kimberley_MDT.xlsx --log kimberley_MDT.log)
fi
python "$here/score.py" "$here/gold" "$out/mapper" "$out/with_model"
