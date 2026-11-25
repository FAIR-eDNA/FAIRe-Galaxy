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
#        pypdf, pydantic, numpy, jinja2 and pyyaml; PYTHON=... to use another Python)
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
# ENVO: the search finds dust first for env_medium, and set refuses an identifier that names another class
$S --work "$W" envo dust --term env_medium --limit 3 | sed -n 2p | grep -q "^ENVO:00002008  dust " \
    || { echo "FAIL day-night: envo search"; fail=1; }
if $S --work "$W" set env_medium "dust [ENVO:00002221]" > /dev/null 2>&1; then
    echo "FAIL day-night: set took a mismatched ENVO identifier"; fail=1
fi
$S --work "$W" set targetTaxonomicAssay Actinopterygii --assay 16S_Fish > /dev/null
$S --work "$W" set targetTaxonomicAssay Metazoa --assay COI_Leray > /dev/null
$S --work "$W" set neg_cont_0_1 1 > /dev/null
$S --work "$W" set pos_cont_0_1 0 > /dev/null
gaps=$($S --work "$W" gaps --recommended)   # the optional terms offered as one checklist
grep -q "samp_vol_we_dna_ext:" <<< "$gaps" || { echo "FAIL day-night: gaps --recommended misses samp_vol_we_dna_ext"; fail=1; }
! grep -q "probeReporter" <<< "$gaps" || { echo "FAIL day-night: gaps --recommended lists qPCR probe terms"; fail=1; }
$S --work "$W" set samp_vol_we_dna_ext 500 --source "methods: half of each 1 L filter was extracted" > /dev/null
$S --work "$W" set samp_vol_we_dna_ext_unit mL > /dev/null
$S --work "$W" build \
    --otu "$D/Day_night_16S_LCA_output.txt" assay=16S_Fish run=AGRF_NovaSeq6000_SP sequences="$D/Day_night_16S_ASV.fasta" \
    --otu "$D/Day_night_COI_LCA_output.txt" assay=COI_Leray run=AGRF_NovaSeq6000_SP sequences="$D/Day_night_COI_ASV.fasta" \
    --library "$D/fastq_file_names.txt" assay=16S_Fish filter=16S_Fish run=AGRF_NovaSeq6000_SP \
    --library "$D/fastq_file_names.txt" assay=COI_Leray filter=COI_Leray run=AGRF_NovaSeq6000_SP > /dev/null
$S --work "$W" check > /dev/null || true
# Conversions: the Darwin Core archive, ENA samples and QIIME 2 metadata are written; NCBI stops,
# as these replicate samples have identical BioSample attributes, and says so.
$S --work "$W" convert gbif --licence CC-BY-4.0 --given_name Katrina --surname West > /dev/null
$S --work "$W" convert ena --center_name "Example University" > /dev/null
$S --work "$W" convert qiime > /dev/null
if $S --work "$W" convert ncbi --mandatory_fill "not collected" > "$out/ncbi.txt"; then
    echo "FAIL day-night: NCBI should stop on identical BioSamples"; fail=1
elif ! grep -q "identical BioSample attributes" "$out/ncbi.txt"; then
    echo "FAIL day-night: NCBI stopped for another reason"; cat "$out/ncbi.txt"; fail=1
fi
for f in gbif/dwca.zip ena/samples.xml qiime/out/West2024_DayNight_16S_metadata.tsv; do
    [ -s "$W/convert/$f" ] || { echo "FAIL day-night: no convert/$f"; fail=1; }
done
$S --work "$W" summary > /dev/null
[ -s "$W/handover/convert/gbif/dwca.zip" ] || { echo "FAIL day-night: conversions not in the handover"; fail=1; }
check_pass "$W" day-night pass
"$py" - "$W"/build/*_FAIRe.xlsx <<'PY' || { echo "FAIL day-night: samp_vol_we_dna_ext not in the workbook"; fail=1; }
import sys, openpyxl
rows = list(openpyxl.load_workbook(sys.argv[1], read_only=True)['sampleMetadata'].iter_rows(values_only=True))
head = next(r for r in rows if r and r[0] == 'samp_name')
vals = {str(r[head.index('samp_vol_we_dna_ext')]) for r in rows[rows.index(head) + 1:] if r and r[0]}
sys.exit(0 if vals == {'500'} or vals == {'500.0'} else 1)
PY

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
# FAIRe-fier finds errors (terms left for the researcher), so convert stops unless asked for a draft
if $S --work "$W" convert gbif > /dev/null 2>&1; then echo "FAIL khapra: converted with errors"; fail=1; fi
for a in FURUIFranklin FURUIViiA7 OLSONFranklin OLSONViiA7; do
    $S --work "$W" set targetTaxonomicAssay "Trogoderma granarium" --assay $a > /dev/null
done
$S --work "$W" build --amp "$K/Amplification_data_khapra_05012022_dryad.csv" assay_column=assay_name > /dev/null
$S --work "$W" check > /dev/null || true
$S --work "$W" convert gbif --anyway --country_code AU > /dev/null
[ -s "$W/convert/gbif/dwca.zip" ] || { echo "FAIL khapra: no Darwin Core archive"; fail=1; }
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
