#!/usr/bin/env bash
# Run FAIRe mapper: find method details on the methods texts of the trial: run.sh OUTDIR [WEST_2024_TEXT]
#
# The five development texts are in this repository. The held-out text, the day-night paper of West et al.
# (2024, Environmental DNA 6: e70018), is not: give the path of its text (pdftotext, not -layout) to run it,
# and its values are compared with dev/faire_mapper_daynight/project_values.tsv by hand.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
tools="$repo/tools/faire_mapper"
out=${1:?give an output folder}
mkdir -p "$out"
declare -A text=(
  [seames]="$repo/dev/faire_mapper_seames/data/methods.txt"
  [kimberley]="$repo/dev/faire_mapper_australian_datasets/data/kimberley/methods.txt"
  [jackman]="$repo/dev/faire_mapper_real_datasets/data/jackman/methods.txt"
  [sacco]="$repo/dev/faire_mapper_real_datasets/data/sacco/methods.txt"
  [vanderheyde]="$repo/dev/faire_mapper_real_datasets/data/vanderheyde/methods.txt"
)
if [ -n "${2:-}" ]; then text[west2024]="$2"; fi
for n in "${!text[@]}"; do
  extra=()
  [ "$n" = west2024 ] && extra=(--assay_names 16S_Fish,COI_Leray)
  python "$tools/faire_method_details.py" "${text[$n]}" --checklist "$tools/checklist/FAIRe_checklist_v1.0.2.xlsx" \
      "${extra[@]}" -o "$out/$n.tsv" --review_sheet "$out/$n.review_sheet.xlsx" > "$out/$n.summary.txt"
  sed -n 2,3p "$out/$n.summary.txt" | sed "s/^/$n: /"
done
