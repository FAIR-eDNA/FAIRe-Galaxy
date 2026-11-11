#!/usr/bin/env bash
# Score the mapper before and after applying answers to its review requests.
# Usage: run_with_answers.sh CHECKLIST_XLSX ANSWERS_DIR OUTDIR TABLE [TABLE ...]
#   ANSWERS_DIR holds <TABLE>.json answer lists, from a model or a person.
# Needs python with pandas and openpyxl.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools="$here/../../tools/faire_mapper"
checklist=$1; answers=$2; out=$3; shift 3
mkdir -p "$out"
printf "table\trequests\tanswers_used\ttop1_before\ttop1_after\taccepted_correct_before\taccepted_correct_after\tconfirmed\n" > "$out/results.tsv"
for name in "$@"; do
  data="$here/data/$name.csv"; gold="$here/data/$name.gold.tsv"
  python "$tools/faire_mapper.py" map "$data" --checklist "$checklist" --assay_type metabarcoding \
      --sample_types Water --gold "$gold" -o "$out/$name/before" > /dev/null
  python "$tools/faire_mapper_adjudicate.py" "$out/$name/before/adjudication_requests.json" \
      --answers_from "$answers/$name.json" --answered_by "model:stand-in" -o "$out/$name/responses.json" --log "$out/$name/answers_log.tsv" > /dev/null
  python "$tools/faire_mapper.py" map "$data" --checklist "$checklist" --assay_type metabarcoding \
      --sample_types Water --gold "$gold" --responses "$out/$name/responses.json" -o "$out/$name/after" > /dev/null
  python - "$out/$name" "$name" >> "$out/results.tsv" <<'PY'
import json, sys
d, name = sys.argv[1], sys.argv[2]
b = json.load(open(f'{d}/before/summary.json'))
a = json.load(open(f'{d}/after/summary.json'))
n_req = len(json.load(open(f'{d}/before/adjudication_requests.json')))
n_used = len(json.load(open(f'{d}/responses.json')))
print('\t'.join(map(str, [name, n_req, n_used, b['evaluation']['top1_accuracy'], a['evaluation']['top1_accuracy'],
                          b['evaluation']['accepted_correct'], a['evaluation']['accepted_correct'], a['confirmed'] + a.get('model', 0)])))
PY
done
cat "$out/results.tsv"
