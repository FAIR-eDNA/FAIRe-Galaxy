#!/usr/bin/env bash
# The Nova Scotia eelgrass demonstration with a sequence behind each identification: the published
# Dryad files (demo/eelgrass) plus the authors' per-ASV files from their GitHub repository
# (fetch_github.sh). See demo/eelgrass/README.md.
# Usage: run_asvs.sh OUTDIR [GITHUB_DIR]     (GITHUB_DIR: the downloaded files; fetched if not given)
#   1. fetch_github.sh, then prepare_asvs.py: the ASVs behind the published species, with their
#      sequences, one table and one FASTA file for each year; prepare_table.py: the sample table, now
#      with the controls and the 2019 dates; make_taxa.py: the taxon table
#   2. propose mapping, and the reviewer's decision
#   3. apply mapping: each year's ASV table as otuFinal and taxaFinal, with its sequences, as its own
#      sequencing batch (COI_2019, COI_2023)
#   4. FAIRe-fier
#   5. FAIRe to Darwin Core: one presence record per sample and ASV, with the ASV's sequence
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo="$here/../.."
tools="$repo/tools/faire_mapper"
ck="$tools/checklist/FAIRe_checklist_v1.0.2.xlsx"
tpl="$tools/checklist/FAIRe_checklist_v1.0.2_FULLtemplate.xlsx"
d="$repo/demo/eelgrass"
out=$(mkdir -p "${1:?usage: run_asvs.sh OUTDIR [GITHUB_DIR]}" && cd "$1" && pwd)
gh=${2:-$out/github}
mkdir -p "$out/mapper" "$out/faire" "$out/dwc"
[ -f "$gh/Trask_RDPv5.tsv" ] || bash "$here/fetch_github.sh" "$gh"

echo "== 1. the ASV tables, the sample table and the taxon table"
python -I "$here/prepare_asvs.py" "$gh" "$d/Final_ASVTable_withTaxonomy_Filtered.csv" "$out/mapper"
python -I "$here/prepare_table.py" "$d/Final_ASVTable_withTaxonomy_Filtered.csv" "$d/Site_coordinates.csv" \
    "$out/mapper/samples.csv" "$out/mapper/eelgrass_2019_asvs.csv" "$out/mapper/eelgrass_2023_asvs.csv" \
    "$gh/MAR_2019eDNASiteData.csv"
python -I "$here/make_taxa.py" "$out/mapper/eelgrass_2019_asvs.csv" "$out/mapper/eelgrass_2023_asvs.csv" \
    "$out/mapper/taxa.tsv"

echo "== 2. propose mapping and review"
python "$tools/faire_mapper.py" map "$out/mapper/samples.csv" --checklist "$ck" --assay_type metabarcoding \
    --sample_types Water --dictionary "$d/Dryad_README.md" -o "$out/mapper/samples"
python "$repo/dev/faire_mapper_seames/review.py" "$out/mapper/samples/crosswalk.sssom.tsv" \
    "$here/reviewer_decisions.tsv" "$out/mapper/reviewed.sssom.tsv"

echo "== 3. apply mapping"
otu=()
for y in 2019 2023; do
    otu+=(--otu "$out/mapper/eelgrass_${y}_asvs.csv" --otu_name "eelgrass_${y}_asvs.csv"
          --otu_sequences "$out/mapper/eelgrass_${y}_asvs.fasta" --otu_sequences_name "eelgrass_${y}_asvs.fasta"
          --otu_assay LerayCOI --otu_run "COI_$y" --otu_stage final)
done
python "$tools/faire_mapper_apply.py" "$out/mapper/samples.csv" --crosswalk "$out/mapper/reviewed.sssom.tsv" \
    --checklist "$ck" --template "$tpl" --assay_type metabarcoding --sample_types Water \
    --project_id NS_eelgrass_eDNA --assay_name LerayCOI --project_values "$here/project_values_asvs.tsv" \
    "${otu[@]}" --table_name eelgrass_samples.csv -o "$out/faire/eelgrass.xlsx" --log "$out/faire/eelgrass.log"

echo "== 4. FAIRe-fier"
python "$repo/tools/fairefier/fairefier_cli.py" "$out/faire/eelgrass.xlsx" -o "$out/faire/fairefier" \
    --checklist_dir "$repo/tools/fairefier/checklist" || true

echo "== 5. FAIRe to Darwin Core"
abstract="Detections of 134 invertebrate species by COI eDNA metabarcoding (Leray et al. 2013 primers) in 50 \
samples from eelgrass (Zostera marina) meadows at 17 sites across Nova Scotia, Canada: ten mainland sites sampled \
between July and September 2019, and seven sites (six in Cape Breton, one on the south shore) sampled between June \
and October 2023, with three replicates at each site (two at Rose Bay). One record per sample and ASV, with the \
ASV's sequence: the ASVs the COI RDP classifier v5.0.0 assigned to a species with a probability above 0.90, for \
the species in the published table (Trask et al., Dryad doi:10.5061/dryad.gqnk98t0c; per-ASV files from the \
authors' GitHub repository, dfo-mar-mpas/coastal-invertebrate-metabarcoding). Coordinates are those of each site; \
2019 records have the date of the site visit, 2023 records the period of sampling. Raw reads: NCBI BioProject \
PRJNA1145319. Prepared with the FAIRe tools as a demonstration."
python "$repo/tools/faire2dwc/faire2dwc.py" "$out/faire/eelgrass.xlsx" --taxa "$out/mapper/taxa.tsv" \
    --title "Invertebrate eDNA in eelgrass meadows across Nova Scotia, 2019 and 2023, with sequences (demonstration)" \
    --abstract "$abstract" --keywords "eelgrass,Zostera marina,COI,invertebrates,Nova Scotia" \
    --given_name Nick --surname Jeffery --organisation "Fisheries and Oceans Canada" \
    --email Nick.Jeffery@dfo-mpo.gc.ca \
    --archive "$out/dwc/eelgrass_dwca.zip" --occurrence "$out/dwc/occurrence.txt" --dna "$out/dwc/dna_derived_data.txt" \
    --eml "$out/dwc/eml.xml" --report "$out/dwc/report.md"
echo "done: $out"
