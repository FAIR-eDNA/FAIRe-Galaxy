#!/usr/bin/env bash
# The FAIRe tools on the day-night eDNA study (West et al. 2024; see README.md).
# Usage: DATA=demo/daynight run.sh OUTDIR   on the demonstration set (make_demo.py), or
#        DATA=DIR run.sh OUTDIR              on the study's files (needs pdftotext; README.md)
#   (needs python with pandas and openpyxl). DIR holds the files as the authors provide them:
#   Day_night_Tasmania_sample_data.xlsx, Day_night_16S_LCA_output.txt, Day_night_COI_LCA_output.txt,
#   Day_night_16S_ASV.fasta, Day_night_COI_ASV.fasta, and the paper as West_2024.pdf (Environmental
#   DNA 6: e70018, CC BY), or its methods as methods.txt.
#   1. propose mapping on the sample sheet as published
#   2. prepare_table.py: what a person adds before mapping (9B for the second 8B, a sample type and
#      control type column, a row for the extraction blank in the 16S table)
#   3. propose mapping on that sheet, then review.py applies the reviewer's decisions
#   4. find primers on the paper's methods
#   5. apply mapping: both LCA outputs as otuFinal and taxaFinal, with their FASTA files, the times
#      joined to the dates at +11:00, and the values from the paper (project_values.tsv)
#   6. FAIRe-fier, then FAIRe2ENA samples, FAIRe2NCBI BioSample and FAIRe2QIIME
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo="$here/../.."
tools="$repo/tools/faire_mapper"
ck="$tools/checklist/FAIRe_checklist_v1.0.2.xlsx"
tpl="$tools/checklist/FAIRe_checklist_v1.0.2_FULLtemplate.xlsx"
out=$(mkdir -p "${1:?usage: DATA=DIR run.sh OUTDIR}" && cd "$1" && pwd)
d=$(cd "${DATA:?set DATA to the folder that holds the study files (README.md)}" && pwd)
for f in Day_night_Tasmania_sample_data.xlsx Day_night_16S_LCA_output.txt Day_night_COI_LCA_output.txt \
         Day_night_16S_ASV.fasta Day_night_COI_ASV.fasta; do
    [ -e "$d/$f" ] || { echo "Missing $d/$f (README.md)" >&2; exit 1; }
done
[ -e "$d/methods.txt" ] || [ -e "$d/West_2024.pdf" ] || { echo "Missing $d/methods.txt or West_2024.pdf" >&2; exit 1; }
py="${PYTHON:-python -I -W ignore}"
mkdir -p "$out/mapper" "$out/faire" "$out/convert/ena_samples" "$out/convert/ncbi_biosample" "$out/convert/qiime/out"

echo "== 1. propose mapping on the sample sheet as published"
$py "$tools/faire_mapper.py" map "$d/Day_night_Tasmania_sample_data.xlsx" --sample_types Water --checklist "$ck" \
    --assay_type metabarcoding -o "$out/mapper/published"

echo "== 2-3. the prepared sheet, mapped and reviewed"
$py "$here/prepare_table.py" "$d/Day_night_Tasmania_sample_data.xlsx" "$out/mapper/samples_prepared.xlsx"
$py "$tools/faire_mapper.py" map "$out/mapper/samples_prepared.xlsx" --sample_types Water --checklist "$ck" \
    --assay_type metabarcoding -o "$out/mapper/prepared"
$py "$repo/dev/faire_mapper_seames/review.py" "$out/mapper/prepared/crosswalk.sssom.tsv" \
    "$here/reviewer_decisions.tsv" "$out/mapper/reviewed.sssom.tsv"

echo "== 4. find primers"
if [ -e "$d/methods.txt" ]; then cp "$d/methods.txt" "$out/mapper/methods.txt"
else pdftotext "$d/West_2024.pdf" "$out/mapper/methods.txt"; fi
$py "$tools/faire_primers.py" text "$out/mapper/methods.txt" -o "$out/mapper/primer_candidates.tsv"

echo "== 5. apply mapping"
$py "$tools/faire_mapper_apply.py" "$out/mapper/samples_prepared.xlsx" --crosswalk "$out/mapper/reviewed.sssom.tsv" \
    --checklist "$ck" --template "$tpl" --assay_type metabarcoding --sample_types Water \
    --project_id West2024_DayNight --assay_name 16S_Fish,COI_Leray --country Australia --utc_offset +11:00 \
    --project_values "$here/project_values.tsv" --drop_unmapped \
    --otu "$d/Day_night_16S_LCA_output.txt" --otu_assay 16S_Fish --otu_run AGRF_NovaSeq6000_SP \
    --otu_sequences "$d/Day_night_16S_ASV.fasta" \
    --otu "$d/Day_night_COI_LCA_output.txt" --otu_assay COI_Leray --otu_run AGRF_NovaSeq6000_SP \
    --otu_sequences "$d/Day_night_COI_ASV.fasta" \
    -o "$out/faire/daynight.xlsx" --log "$out/faire/daynight.log"

echo "== 6. FAIRe-fier and conversions"
$py "$repo/tools/fairefier/fairefier_cli.py" "$out/faire/daynight.xlsx" -o "$out/faire/fairefier" \
    --checklist_dir "$repo/tools/fairefier/checklist" || true
(cd "$out/convert/ena_samples" && $py "$repo/tools/faire2ena/faire2ena_galaxy.py" sample \
    --input_file "$out/faire/daynight.xlsx" --center_name CSIRO --output_file samples.xml \
    --submission_file submission.xml > log.txt)
# NCBI stops here: the ten replicates of each site and time have the same attributes (README.md).
(cd "$out/convert/ncbi_biosample" && $py "$repo/tools/faire2ncbi/faire2ncbi_galaxy.py" biosample \
    --input_file "$out/faire/daynight.xlsx" --organism "marine metagenome" --bioproject PRJNA000000 \
    --mandatory_fill "not applicable" --output biosample.tsv --config_out config.yaml < /dev/null > log.txt 2>&1) || true
(cd "$out/convert/qiime" && $py "$repo/tools/faire2qiime/normalise_faire.py" "$out/faire/daynight.xlsx" normalised.xlsx \
    > log.txt && $py "$repo/tools/faire2qiime/faire2qiime.py" --path_faire normalised.xlsx \
    --sample_name_column samp_name --absolute_path_sequences /not/used --output_directory out >> log.txt 2>&1)
echo "done: $out"
