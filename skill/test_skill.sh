#!/usr/bin/env bash
# Tests the faire-dataset skill package end to end on three demonstration sets, as an assistant would
# run it in conversation (the researcher's answers are written in here).
#   1. day-night (demo/daynight): metabarcoding, two assays, an Excel sample sheet that needs
#      corrections, methods text, primers, LCA outputs with FASTA files and a list of fastq files
#   2. khapra beetle (demo/khapra): targeted qPCR, a CSV sample table with the authors' own sample
#      types, a README as data dictionary, and results that need an assay name on each row
#   3. eelgrass (demo/eelgrass): no sample table, so one is made from the OTU table's columns and
#      the site coordinates
# Each ends with FAIRe-fier and the handover. The test checks that each workbook is written and that
# FAIRe-fier ran; the day-night workbook must pass.
# Usage: bash skill/test_skill.sh [OUTDIR]      (builds the package first; needs pandas, openpyxl,
#        pypdf, pydantic, numpy and jinja2; PYTHON=... to use another Python)
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo="$here/.."
out=$(mkdir -p "${1:-$(mktemp -d)}" && cd "${1:-.}" && pwd)
py="${PYTHON:-python3}"
"$py" "$here/build_skill.py" "$out/dist" > /dev/null
pkg="$out/pkg"
rm -rf "$pkg" && mkdir -p "$pkg" && (cd "$pkg" && "$py" -c "import zipfile; zipfile.ZipFile('$out/dist/faire-dataset.zip').extractall()")
S="$py $pkg/faire-dataset/scripts/faire_session.py"
fail=0
check_pass() {  # session folder, label, whether FAIRe-fier must pass
    local w=$1 label=$2 must=$3
    [ -e "$w/handover/README.md" ] || { echo "FAIL $label: no handover"; fail=1; return; }
    ls "$w"/build/*_FAIRe.xlsx > /dev/null 2>&1 || { echo "FAIL $label: no workbook"; fail=1; return; }
    [ -e "$w/check/fairefier_summary.json" ] || { echo "FAIL $label: FAIRe-fier did not run"; fail=1; return; }
    if [ "$must" = pass ]; then
        "$py" -c "import json,sys; sys.exit(0 if json.load(open('$w/check/fairefier_summary.json'))['valid'] else 1)" \
            || { echo "FAIL $label: FAIRe-fier did not pass"; fail=1; return; }
    fi
    echo "ok   $label"
}

$S setup > /dev/null

echo "== 1. day-night"
D="$repo/demo/daynight"; W="$out/daynight"; rm -rf "$W"
$S --work "$W" start --assay_type metabarcoding --sample_types Water --assays 16S_Fish,COI_Leray \
    --project_id West2024_DayNight --country Australia --utc_offset +11:00 > /dev/null
$S --work "$W" identify "$D"/* > /dev/null
$S --work "$W" map "$D/Day_night_Tasmania_sample_data.xlsx" > /dev/null
$S --work "$W" table set "Sample ID" --value 9B --where "Sample ID=8B" --nth 2 --reason "typing slip" > /dev/null
$S --work "$W" table add-column "Sample type" --value sample > /dev/null
$S --work "$W" table set "Sample type" --value "negative control" --where "Sample ID~^Filtration control" > /dev/null
$S --work "$W" table add-column "Control type" > /dev/null
$S --work "$W" table set "Control type" --value "field negative" --where "Sample ID~^Filtration control" > /dev/null
$S --work "$W" table add-row --cells "Sample ID=Extbl19_4" "Sample type=negative control" "Control type=extraction negative" > /dev/null
for c in "Collected by" "Filtered by" "Information:"; do $S --work "$W" table drop-column "$c" --reason notes > /dev/null; done
$S --work "$W" map --again > /dev/null
$S --work "$W" methods "$D/methods.txt" > /dev/null
$S --work "$W" method-decide accept --all-reliable --except 9 > /dev/null
$S --work "$W" method-decide reject --row 9 > /dev/null
$S --work "$W" primers-use pp_1152ed015a --assay 16S_Fish > /dev/null
$S --work "$W" primers-use pp_2bd38e4e28 --assay COI_Leray > /dev/null
$S --work "$W" set annealingTemp 54 --assay 16S_Fish --source "methods Table 1" > /dev/null
$S --work "$W" set annealingTemp 46 --assay COI_Leray --source "methods Table 1" > /dev/null
$S --work "$W" set project_contact katrina.west@example.org > /dev/null
$S --work "$W" set recordedBy "Tyson Jones | Olivia Johnson | Ella Clausius" > /dev/null
$S --work "$W" set env_broad_scale "marine biome [ENVO:00000447]" > /dev/null
$S --work "$W" set env_local_scale "marine subtidal rocky reef [ENVO:01000150]" > /dev/null
$S --work "$W" set env_medium "ocean water [ENVO:00002149]" > /dev/null
$S --work "$W" set targetTaxonomicAssay Actinopterygii --assay 16S_Fish > /dev/null
$S --work "$W" set targetTaxonomicAssay Metazoa --assay COI_Leray > /dev/null
$S --work "$W" set neg_cont_0_1 1 > /dev/null
$S --work "$W" set pos_cont_0_1 0 > /dev/null
$S --work "$W" build \
    --otu "$D/Day_night_16S_LCA_output.txt" assay=16S_Fish run=AGRF_NovaSeq6000_SP sequences="$D/Day_night_16S_ASV.fasta" \
    --otu "$D/Day_night_COI_LCA_output.txt" assay=COI_Leray run=AGRF_NovaSeq6000_SP sequences="$D/Day_night_COI_ASV.fasta" \
    --library "$D/fastq_file_names.txt" assay=16S_Fish filter=16S_Fish run=AGRF_NovaSeq6000_SP \
    --library "$D/fastq_file_names.txt" assay=COI_Leray filter=COI_Leray run=AGRF_NovaSeq6000_SP > /dev/null
$S --work "$W" check > /dev/null || true
$S --work "$W" summary > /dev/null
check_pass "$W" day-night pass

echo "== 2. khapra beetle (qPCR)"
K="$repo/demo/khapra"; W="$out/khapra"; rm -rf "$W"
$S --work "$W" start --assay_type targeted --sample_types Air,Other --project_id khapra_eDNA --country Australia \
    --date_order dmy --assays FURUIFranklin,FURUIViiA7,OLSONFranklin,OLSONViiA7 > /dev/null
$S --work "$W" map "$K/Sample_metadata.csv" --dictionary "$K/Trujillo_Gonzalez_et_al_2022_README.txt" > /dev/null
$S --work "$W" table add-column Category --value sample > /dev/null
$S --work "$W" table set Category --value "negative control" --where "sample type=Field control" > /dev/null
$S --work "$W" table set Category --value "positive control" --where "sample type~^(eDNA Positive control|Specimen)$" > /dev/null
$S --work "$W" map --again > /dev/null
$S --work "$W" decide "sample type" reject > /dev/null
$S --work "$W" decide Category change samp_category > /dev/null
$S --work "$W" decide "Extraction technique" change nucl_acid_ext_kit > /dev/null
$S --work "$W" table add-column assay_name --file "$K/Amplification_data_khapra_05012022_dryad.csv" \
    --template "{Assay}{machine}" > /dev/null
$S --work "$W" set pcr_0_1 1 > /dev/null
$S --work "$W" set amp_vis_method qPCR > /dev/null
$S --work "$W" build --amp "$K/Amplification_data_khapra_05012022_dryad.csv" assay_column=assay_name > /dev/null
$S --work "$W" check > /dev/null || true
$S --work "$W" summary > /dev/null
check_pass "$W" khapra ran

echo "== 3. eelgrass (no sample table)"
E="$repo/demo/eelgrass"; W="$out/eelgrass"; rm -rf "$W"
$S --work "$W" start --assay_type metabarcoding --sample_types Water --assays COI_Leray --project_id Trask_eelgrass \
    --country Canada > /dev/null
$S --work "$W" new-table "$E/Final_ASVTable_withTaxonomy_Filtered.csv" \
    --split '(?P<Code>[A-Z]+[0-9]*)-(?P<Replicate>[0-9]+)' --join "$E/Site_coordinates.csv" --on 'Code=Code' > /dev/null
$S --work "$W" table set Site --value "Wreck Cove" --where "Code=WRK02" > /dev/null
$S --work "$W" table set Latitude --value 44.60293333 --where "Code=WRK02" > /dev/null
$S --work "$W" table set Longitude --value -63.51615 --where "Code=WRK02" > /dev/null
$S --work "$W" table rename-column Site --value "Site name" > /dev/null
$S --work "$W" table add-column Date --value "2019-07/2019-09" > /dev/null
$S --work "$W" table set Date --value "2023-06/2023-10" --where "Code~^(ASB|CHB|LIN|MIR|CHT|NOR|ESB)$" > /dev/null
$S --work "$W" table add-column "Sample type" --value sample > /dev/null
$S --work "$W" map --dictionary "$E/Dryad_README.md" > /dev/null
$S --work "$W" decide Code reject > /dev/null
$S --work "$W" decide Replicate reject > /dev/null
$S --work "$W" decide "Site name" change geo_loc_name > /dev/null
$S --work "$W" set pcr_0_1 1 > /dev/null
$S --work "$W" build --otu "$E/Final_ASVTable_withTaxonomy_Filtered.csv" run=run_unknown stage=final > /dev/null
$S --work "$W" check > /dev/null || true
$S --work "$W" summary > /dev/null
check_pass "$W" eelgrass ran

[ $fail = 0 ] && echo "All passed. Outputs in $out" || { echo "Some tests failed. Outputs in $out"; exit 1; }
