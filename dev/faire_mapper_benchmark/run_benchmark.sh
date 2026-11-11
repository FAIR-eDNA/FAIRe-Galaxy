#!/usr/bin/env bash
# Score tools/faire_mapper on the benchmark tables. Needs python with pandas and openpyxl.
# Usage: run_benchmark.sh CHECKLIST_XLSX [OUTDIR]
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mapper="$here/../../tools/faire_mapper/faire_mapper.py"
checklist=$1; out=${2:-benchmark_results}
mkdir -p "$out"
printf "table\ttop1\tshortlist\tdistractors_unmatched\taccepted\taccepted_correct\n" > "$out/results.tsv"
for gold in "$here"/data/*.gold.tsv; do
  name=$(basename "$gold" .gold.tsv)
  python "$mapper" map "$here/data/$name.csv" --checklist "$checklist" --assay_type metabarcoding \
      --sample_types Water --gold "$gold" -o "$out/$name" > /dev/null
  python - "$out/$name/summary.json" "$name" >> "$out/results.tsv" <<'PY'
import json, sys
e = json.load(open(sys.argv[1]))['evaluation']
print('\t'.join(map(str, [sys.argv[2], e['top1_accuracy'], e['shortlist_recall'], e['distractors_left_unmatched'], e['accepted'], e['accepted_correct']])))
PY
done
cat "$out/results.tsv"
