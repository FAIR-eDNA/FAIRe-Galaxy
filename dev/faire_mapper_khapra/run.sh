#!/usr/bin/env bash
# The FAIRe tools on the khapra beetle qPCR data (Trujillo-Gonzalez et al. 2022; see demo/khapra/README.md),
# from the published files to a Darwin Core archive for GBIF.
# Usage: run.sh OUTDIR        (needs python with pandas and openpyxl)
#   1. prepare_table.py and prepare_results.py: what a person following the guide adds to the published
#      tables (the control categories, places and ENVO terms; an assay name for each assay and machine)
#   2. propose mapping on the sample table, with the README as its data dictionary; review.py applies the
#      reviewer's decisions
#   3. find method details in the README's methods (for comparison with project_values.tsv)
#   4. apply mapping: the targeted-assay workbook, with the qPCR results as ampData and detected_notDetected
#      worked out from them, and the values for the whole project and each assay
#   5. FAIRe-fier checks the workbook
#   6. FAIRe to Darwin Core: the archive for GBIF, with the taxon table for the higher taxonomy
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo="$here/../.."
tools="$repo/tools/faire_mapper"
ck="$tools/checklist/FAIRe_checklist_v1.0.2.xlsx"
tpl="$tools/checklist/FAIRe_checklist_v1.0.2_FULLtemplate.xlsx"
d="$repo/demo/khapra"
out=$(mkdir -p "${1:?usage: run.sh OUTDIR}" && cd "$1" && pwd)
mkdir -p "$out/mapper" "$out/faire" "$out/dwc"
assays=OlsonViiA7,OlsonFranklin,FuruiViiA7,FuruiFranklin

echo "== 1. the tables, as a person following the guide prepares them"
python "$here/prepare_table.py" "$d/Sample_metadata.csv" "$out/mapper/samples.csv"
python "$here/prepare_results.py" "$d/Amplification_data_khapra_05012022_dryad.csv" "$out/mapper/results.csv"

echo "== 2. propose mapping and review"
python "$tools/faire_mapper.py" map "$out/mapper/samples.csv" --checklist "$ck" --assay_type targeted \
    --sample_types Air,other --dictionary "$d/Trujillo_Gonzalez_et_al_2022_README.txt" -o "$out/mapper/samples"
python "$repo/dev/faire_mapper_seames/review.py" "$out/mapper/samples/crosswalk.sssom.tsv" \
    "$here/reviewer_decisions.tsv" "$out/mapper/reviewed.sssom.tsv"

echo "== 3. find method details"
python "$tools/faire_method_details.py" "$d/Trujillo_Gonzalez_et_al_2022_README.txt" --whole_text --checklist "$ck" \
    --assay_type targeted --assay_names Olson,Furui -o "$out/mapper/method_details.tsv" \
    --review_sheet "$out/mapper/method_details.xlsx"

echo "== 4. apply mapping"
python "$tools/faire_mapper_apply.py" "$out/mapper/samples.csv" --crosswalk "$out/mapper/reviewed.sssom.tsv" \
    --checklist "$ck" --template "$tpl" --assay_type targeted --sample_types Air,other --project_id khapra_eDNA \
    --assay_name "$assays" --country Australia --date_order dmy --project_values "$here/project_values.tsv" \
    --amp "$out/mapper/results.csv" --amp_assay_column assay_name \
    --amp_name Amplification_data_khapra_05012022_dryad.csv --table_name Sample_metadata.csv \
    -o "$out/faire/khapra.xlsx" --log "$out/faire/khapra.log"

echo "== 5. FAIRe-fier"
python "$repo/tools/fairefier/fairefier_cli.py" "$out/faire/khapra.xlsx" -o "$out/faire/fairefier" \
    --checklist_dir "$repo/tools/fairefier/checklist" || true

echo "== 6. FAIRe to Darwin Core"
abstract="Detections of khapra beetle (Trogoderma granarium) DNA in dust and air vacuumed from two retail \
stores in Canberra during Australian biosecurity responses between August and November 2020 (Trujillo-Gonzalez et al. \
2022, Frontiers in Insect Science 2: 795379). Each sample was tested with two TaqMan qPCR assays (Olson et al. 2014; \
Furui et al. 2019) on a benchtop (ViiA 7) and a portable (Franklin) thermocycler, in technical replicates. A record \
is present when at least one replicate amplified. Field negative controls also amplified, and the Fyshwick samples \
were collected with a vacuum cleaner used in an earlier khapra beetle response, so some detections may come from \
contamination. The authors withheld the store locations; coordinates are the centre of the district or suburb. \
Prepared with the FAIRe tools as a demonstration."
python "$repo/tools/faire2dwc/faire2dwc.py" "$out/faire/khapra.xlsx" --taxa "$here/taxa_khapra.tsv" \
    --title "Khapra beetle environmental DNA in dust from Australian biosecurity responses (demonstration)" \
    --abstract "$abstract" --keywords "biosecurity,qPCR,Trogoderma granarium,khapra beetle" \
    --given_name Alejandro --surname "Trujillo-González" --organisation "University of Canberra" \
    --email alejandro.trujillogonzalez@canberra.edu.au \
    --archive "$out/dwc/khapra_dwca.zip" --occurrence "$out/dwc/occurrence.txt" --dna "$out/dwc/dna_derived_data.txt" \
    --eml "$out/dwc/eml.xml" --report "$out/dwc/report.md"
echo "done: $out"
