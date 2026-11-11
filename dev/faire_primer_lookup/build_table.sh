#!/usr/bin/env bash
# Rebuild the bundled primer table, tools/faire_mapper/primers/faire_primers.tsv, from its sources.
# Usage: build_table.sh [WILDERLAB_XLSX]   (needs python with pandas and openpyxl)
# Later inputs win where they give a value for the same primer pair, so the order matters:
#   1   the Wilderlab assay list, sources/wilderlab_assays.tsv (25 assays, as in the bundled table).
#       First, so that published names and references win for primers Wilderlab also uses; the
#       Wilderlab codes are kept as other names. Wilderlab's spreadsheet is not copied here; it is
#       published at https://s3.ap-southeast-2.amazonaws.com/wilderlab.resources/methods/Wilderlab_assay_details_260709.xlsx
#       Given it or a newer one, convert_wilderlab.py rewrites the TSV first:
#       build_table.sh path/to/Wilderlab_assay_details.xlsx
#   2-3 Takahashi et al. 2023 Tables S4 and S3 (as published)
#   4   the metazoan register in FAIRe terms (adds target taxa, record IDs and the curated supplement)
#   5   the bacteria and archaea 16S register
#   6   primers/curation.tsv: corrections, aliases and checks against the papers, applied last
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools="$here/../../tools/faire_mapper"
if [ $# -gt 0 ]; then
    python "$here/convert_wilderlab.py" "$1" "$here/sources/wilderlab_assays.tsv"
fi
python "$tools/faire_primers.py" build \
    "$here/sources/wilderlab_assays.tsv" \
    "$here/sources/takahashi2023_tableS4.xlsx" \
    "$here/sources/takahashi2023_tableS3.xlsx" \
    "$here/sources/metazoan_primers_FAIRe_aligned.xlsx" \
    "$here/sources/bacteria_archaea_primers.xlsx" \
    "$tools/primers/curation.tsv" \
    -o "$tools/primers/faire_primers.tsv" --report "$here/build_problems.tsv"
