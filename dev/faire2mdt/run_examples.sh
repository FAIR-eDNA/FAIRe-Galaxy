#!/usr/bin/env bash
# Run the Galaxy driver and upstream-by-hand on the FAIRe metabarcoding example workbooks
# (FAIR-eDNA.github.io/docs/examples/metabarcoding), for every assay and run that has an otuFinal
# and taxaFinal table. The examples have no stated licence, so they are not stored here.
#
# Usage: run_examples.sh EXAMPLES_DIR OUT_DIR RSCRIPT
set -u
EX=$1; OUT=$2; RSCRIPT=$3
HERE=$(cd "$(dirname "$0")" && pwd)
TOOL=$HERE/../../tools/faire2mdt
mkdir -p "$OUT"

# name | workbook | assay | run | otu file | otu sheet | taxa file | taxa sheet
cat > "$OUT/cases.txt" <<EOF
IOT_COI_2021|IOT-eDNA/IOT-eDNA.xlsx|COILeray|Library_2021|IOT-eDNA/otuFinal_IOT-eDNA_COILeray_Library_2021.xlsx|otuFinal|IOT-eDNA/taxaFinal_IOT-eDNA_COILeray_Library_2021.xlsx|taxaFinal
IOT_COI_2022|IOT-eDNA/IOT-eDNA.xlsx|COILeray|Library_2022|IOT-eDNA/otuFinal_IOT-eDNA_COILeray_Library_2022.xlsx|otuFinal|IOT-eDNA/taxaFinal_IOT-eDNA_COILeray_Library_2022.xlsx|taxaFinal
IOT_16S_2021|IOT-eDNA/IOT-eDNA.xlsx|16SFish|Library_2021|IOT-eDNA/otuFinal_IOT-eDNA_16SFish_Library_2021.xlsx|otuFinal|IOT-eDNA/taxaFinal_IOT-eDNA_16SFish_Library_2021.xlsx|taxaFinal
IOT_16S_2022|IOT-eDNA/IOT-eDNA.xlsx|16SFish|Library_2022|IOT-eDNA/otuFinal_IOT-eDNA_16SFish_Library_2022.xlsx|otuFinal|IOT-eDNA/taxaFinal_IOT-eDNA_16SFish_Library_2022.xlsx|taxaFinal
CPR_2015|CPR_2015.xlsx|LerayCOI|seq_run_1|CPR_2015.xlsx|otuFinal|CPR_2015.xlsx|taxaFinal
NECR534|NECR534_GCN_metabarcoding.xlsx|12S-V5|Run1|NECR534_GCN_metabarcoding.xlsx|otuFinal|NECR534_GCN_metabarcoding.xlsx|taxaFinal
verte_cetac|verte_quadeloupe.xlsx|cetac|cetac|verte_quadeloupe.xlsx|otuFinal_cetac_cetac|verte_quadeloupe.xlsx|taxaFinal_cetac_cetac
verte_mamm01|verte_quadeloupe.xlsx|mamm01|mamm|verte_quadeloupe.xlsx|otuFinal_mamm01_mamm|verte_quadeloupe.xlsx|taxaFinal_mamm01_mamm
verte_tele01|verte_quadeloupe.xlsx|tele01|teleo|verte_quadeloupe.xlsx|otuFinal_tele01_teleo|verte_quadeloupe.xlsx|taxaFinal_tele01_teleo
verte_vert01_2021|verte_quadeloupe.xlsx|vert01|vert_2021|verte_quadeloupe.xlsx|otuFinal_vert01_vert_2021|verte_quadeloupe.xlsx|taxaFinal_vert01_vert_2021
verte_vert01_2022|verte_quadeloupe.xlsx|vert01|vert_2022|verte_quadeloupe.xlsx|otuFinal_vert01_vert_2022|verte_quadeloupe.xlsx|taxaFinal_vert01_vert_2022
EOF

while IFS='|' read -r name wb assay run otu osheet taxa tsheet; do
  d=$OUT/$name; mkdir -p "$d/galaxy" "$d/by_hand"
  (cd "$d/galaxy" && "$RSCRIPT" --vanilla "$TOOL/faire2mdt_galaxy.R" --upstream "$TOOL/FAIRe2MDT.R" --target_genes "$TOOL/mdt_target_gene.tsv" \
     --workbook "$EX/$wb" --assay "$assay" --seq_run "$run" --otu "$EX/$otu" --otu_format xlsx \
     --otu_sheet "$osheet" --taxa "$EX/$taxa" --taxa_format xlsx --taxa_sheet "$tsheet" \
     --output "$d/galaxy/mdt.xlsx" --log "$d/galaxy/log.txt" > /dev/null 2> "$d/galaxy/stderr.txt")
  echo "$name galaxy exit $?"
  (cd "$d/by_hand" && "$RSCRIPT" --vanilla "$HERE/run_by_hand.R" "$TOOL/FAIRe2MDT.R" "$EX/$wb" "$assay" "$run" \
     "$EX/$otu" "$osheet" "$EX/$taxa" "$tsheet" "$d/by_hand" > /dev/null 2> "$d/by_hand/stderr.txt")
  echo "$name by_hand exit $?"
done < "$OUT/cases.txt"
