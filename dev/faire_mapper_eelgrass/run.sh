#!/usr/bin/env bash
# The FAIRe tools on the Nova Scotia eelgrass COI metabarcoding data (Trask et al., Dryad
# doi:10.5061/dryad.gqnk98t0c; see demo/eelgrass/README.md), from the published files to a Darwin Core
# archive of presence records for GBIF.
# Usage: run.sh OUTDIR        (needs python with pandas and openpyxl)
#   1. prepare_table.py: the sample table a person following the guide makes from the ASV table's
#      columns and the site coordinates (the study published none); make_taxa.py: the taxon table
#   2. propose mapping, with the Dryad README as its data dictionary; review.py applies the reviewer's
#      decisions
#   3. apply mapping: the workbook, with the species table as otuFinal and taxaFinal
#   4. FAIRe-fier checks the workbook
#   5. FAIRe to Darwin Core: the archive for GBIF
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo="$here/../.."
tools="$repo/tools/faire_mapper"
ck="$tools/checklist/FAIRe_checklist_v1.0.2.xlsx"
tpl="$tools/checklist/FAIRe_checklist_v1.0.2_FULLtemplate.xlsx"
d="$repo/demo/eelgrass"
out=$(mkdir -p "${1:?usage: run.sh OUTDIR}" && cd "$1" && pwd)
mkdir -p "$out/mapper" "$out/faire" "$out/dwc"

echo "== 1. the sample table and the taxon table"
python "$here/prepare_table.py" "$d/Final_ASVTable_withTaxonomy_Filtered.csv" "$d/Site_coordinates.csv" \
    "$out/mapper/samples.csv"
python "$here/make_taxa.py" "$d/Final_ASVTable_withTaxonomy_Filtered.csv" "$out/mapper/taxa.tsv"

echo "== 2. propose mapping and review"
python "$tools/faire_mapper.py" map "$out/mapper/samples.csv" --checklist "$ck" --assay_type metabarcoding \
    --sample_types Water --dictionary "$d/Dryad_README.md" -o "$out/mapper/samples"
python "$repo/dev/faire_mapper_seames/review.py" "$out/mapper/samples/crosswalk.sssom.tsv" \
    "$here/reviewer_decisions.tsv" "$out/mapper/reviewed.sssom.tsv"

echo "== 3. apply mapping"
python "$tools/faire_mapper_apply.py" "$out/mapper/samples.csv" --crosswalk "$out/mapper/reviewed.sssom.tsv" \
    --checklist "$ck" --template "$tpl" --assay_type metabarcoding --sample_types Water \
    --project_id NS_eelgrass_eDNA --assay_name LerayCOI --project_values "$here/project_values.tsv" \
    --otu "$d/Final_ASVTable_withTaxonomy_Filtered.csv" --otu_name Final_ASVTable_withTaxonomy_Filtered.csv \
    --otu_assay LerayCOI --otu_stage final --table_name eelgrass_samples.csv \
    -o "$out/faire/eelgrass.xlsx" --log "$out/faire/eelgrass.log"

echo "== 4. FAIRe-fier"
python "$repo/tools/fairefier/fairefier_cli.py" "$out/faire/eelgrass.xlsx" -o "$out/faire/fairefier" \
    --checklist_dir "$repo/tools/fairefier/checklist" || true

echo "== 5. FAIRe to Darwin Core"
abstract="Detections of 138 invertebrate species by COI eDNA metabarcoding (Leray et al. 2013 primers) in 50 \
samples from eelgrass (Zostera marina) meadows at 17 sites across Nova Scotia, Canada: ten mainland sites sampled \
between July and September 2019, and seven sites (six in Cape Breton, one on the south shore) sampled between June \
and October 2023, with three replicates at each site (two at Rose Bay). ASVs were assigned to species by the COI RDP \
classifier v5.0.0 with a probability of at least 0.95, and the reads summed per species (Trask et al., Dryad \
doi:10.5061/dryad.gqnk98t0c). The records are presence only, and carry no DNA sequence, as the published files do not \
link sequences to species. Coordinates are those of each site, and dates the period in which it was sampled. Raw \
reads: NCBI BioProject PRJNA1145319. Prepared with the FAIRe tools as a demonstration."
python "$repo/tools/faire2dwc/faire2dwc.py" "$out/faire/eelgrass.xlsx" --taxa "$out/mapper/taxa.tsv" \
    --title "Invertebrate eDNA in eelgrass meadows across Nova Scotia, 2019 and 2023 (demonstration)" \
    --abstract "$abstract" --keywords "eelgrass,Zostera marina,COI,invertebrates,Nova Scotia" \
    --given_name Nick --surname Jeffery --organisation "Fisheries and Oceans Canada" \
    --email Nick.Jeffery@dfo-mpo.gc.ca \
    --archive "$out/dwc/eelgrass_dwca.zip" --occurrence "$out/dwc/occurrence.txt" --dna "$out/dwc/dna_derived_data.txt" \
    --eml "$out/dwc/eml.xml" --report "$out/dwc/report.md"
echo "done: $out"
