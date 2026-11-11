#!/usr/bin/env bash
# Check that tools/fairefier/fairefier_cli.py gives the same outputs as the FAIRe-fier Shiny app.
# Usage: check.sh PATH_TO_FAIRe-fier_CLONE WORKBOOK [CHECKLIST_VERSION]
# Needs python with pandas, openpyxl, pydantic (FAIRe-fier's pinned versions) and jinja2.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tool="$here/../../tools/fairefier"
upstream=$1; workbook=$(realpath "$2"); version=${3:-v1.0.2}
work=$(mktemp -d)
cp "$tool"/checklist/FAIRe_checklist_*.xlsx "$work"/
cd "$work"
export PYTHONHASHSEED=0   # upstream orders some warnings by set iteration
python "$here/run_shiny_reference.py" "$upstream" "$workbook" "$version" ref > /dev/null
PYTHONWARNINGS=ignore python "$tool/fairefier_cli.py" "$workbook" --checklist_version "$version" \
    --checklist_dir "$tool/checklist" -o cli > /dev/null
diff <(cat ref/message.txt) <(python -c "import json;print(json.load(open('cli/fairefier_summary.json'))['message'],end='')") \
    && echo "validation message identical"
python "$here/compare_outputs.py" ref cli
