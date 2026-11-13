#!/usr/bin/env bash
# The FAIRe tools on the CSIRO SEA-MES eDNA data (Deagle et al. 2025; see README.md).
# Usage: run.sh OUTDIR        (needs python with pandas, openpyxl and pyyaml; set RSCRIPT for FAIRe2MDT;
#                              files 4, 7 and 8 of the record downloaded into data/, see README.md)
#        DATA=demo/seames run.sh OUTDIR   runs it on the demonstration set (make_demo.py)
#   1. propose mapping on both sample tables as published (NCBI BioSample sheets with comment lines)
#   2. prepare_table.py: what a person following the guide adds to the 10 L table (the control type)
#   3. propose mapping on that table, then review.py applies the reviewer's decisions
#   4. find primers on the methods text from the NESP report
#   5. apply mapping: the FAIRe workbook for Fish16S, with the 16S fish ASV table (file 4) as otuRaw
#      and taxaRaw, and ENA's run report as the library table. otuFinal and taxaFinal come from the
#      authors' ASV-level table of curated names (data/private, unpublished, kept out of the
#      repository; README.md) when it is there, and from the curated fish taxa (file 5) when not.
#      Each library also holds COI amplicons, which the authors did not use, so COI is left out
#   6. FAIRe-fier checks the workbook
#   7. FAIRe2MDT (if RSCRIPT is set), FAIRe2QIIME, FAIRe2NCBI BioSample and SRA, FAIRe2ENA samples
#      and runs; compare.py checks the NCBI tables against what the authors submitted
#   8. 18S end to end: make_2L_table.py turns the sample details below the 18S counts into a sample
#      table, with a row for each control library in the run report (not in the 18S table);
#      find primers on the consolidated methods; then propose mapping, review, apply mapping (the 18S ASV table, whose columns are fastq
#      file names, and ENA's run report as the library table), FAIRe-fier, FAIRe2MDT, FAIRe2QIIME,
#      FAIRe2NCBI BioSample and SRA, and FAIRe2ENA samples and runs; compare.py checks the SRA table
#      against the authors' SRA sheet for 18S (file 3)
#   9. Wilderlab's 12-assay panel (file 8, gzipped): rename_WL_repeats.py names its second CN065
#      and CN066 columns CN165 and CN166, as the authors confirmed; make_WL_table.py puts the 150
#      samples it holds (10 L, 2 L and deep-tow) into one sample table; propose mapping, review, apply mapping with
#      the table split by its target column, FAIRe-fier, FAIRe2MDT for each assay and FAIRe2QIIME.
#      BioSample and ENA sample tables are not made: the samples are registered already, and five
#      2 L samples have no details in the record (README.md)
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo="$here/../.."
tools="$repo/tools/faire_mapper"
ck="$tools/checklist/FAIRe_checklist_v1.0.2.xlsx"
tpl="$tools/checklist/FAIRe_checklist_v1.0.2_FULLtemplate.xlsx"
out=$(mkdir -p "${1:?usage: run.sh OUTDIR}" && cd "$1" && pwd)
d=$(cd "${DATA:-$here/data}" && pwd)
# Files 4, 7 and 8 of the record are not stored in the repository (each over 1 MB; README.md)
for f in 4_SEA-MES_16S_ASV_level_output_with_seq.csv 7_SEA-MES_2025_EUK_18S_for_DAT.csv.gz \
         8_WL_Full_SEA_MES_samples.csv.gz; do
    [ -e "$d/$f" ] || { echo "Missing $d/$f: download it from the SEA-MES data record (README.md)," \
        "or run on the demonstration set: DATA=demo/seames run.sh OUTDIR" >&2; exit 1; }
done
report="$d/filereport_read_run_PRJNA1263580.tsv"
mkdir -p "$out/mapper" "$out/faire" "$out/convert/qiime/out" "$out/convert/ncbi_biosample" "$out/convert/ncbi_sra" \
    "$out/convert/ena_samples" "$out/convert/ena_runs"

echo "== 1. propose mapping on the published tables"
python "$tools/faire_mapper.py" map "$d/1_SEA-MES_M_samples_metadata_10L.xlsx" --sample_types Water \
    --checklist "$ck" --assay_type metabarcoding -o "$out/mapper/M_published"
python "$tools/faire_mapper.py" map "$d/2_SEA-MES_CN_samples_metadata_OCD.xlsx" --sample_types Water \
    --checklist "$ck" --assay_type metabarcoding -o "$out/mapper/CN_published"

echo "== 2-3. the 10 L table with the control type, mapped and reviewed"
python "$here/prepare_table.py" "$d/1_SEA-MES_M_samples_metadata_10L.xlsx" "$out/mapper/M_prepared.csv"
python "$tools/faire_mapper.py" map "$out/mapper/M_prepared.csv" --sample_types Water --checklist "$ck" \
    --assay_type metabarcoding -o "$out/mapper/M_prepared"
python "$here/review.py" "$out/mapper/M_prepared/crosswalk.sssom.tsv" "$here/reviewer_decisions.tsv" \
    "$out/mapper/M_reviewed.sssom.tsv"

echo "== 4. find primers"
python "$tools/faire_primers.py" text "$d/methods.txt" -o "$out/mapper/primer_candidates.tsv"

echo "== 5. apply mapping"
curated="$d/private/SEA_MES_Fish16S_ASV_Feb_27_2025_editColRename.csv"
if [ -f "$curated" ]; then
  final=(--otu "$curated" --otu_curated_column New_Name)
  echo "16S final tables from the authors' ASV-level curated names (private)"
else
  final=(--otu "$d/5_SEA_MES_Fish16S_Tax_Feb_27_2025.csv" --otu_curated_column '')
  echo "16S final tables from the curated fish taxa (file 5); the ASV-level curated names are not here"
fi
python "$tools/faire_mapper_apply.py" "$out/mapper/M_prepared.csv" --crosswalk "$out/mapper/M_reviewed.sssom.tsv" \
    --checklist "$ck" --template "$tpl" --assay_type metabarcoding --sample_types Water --project_id SEA-MES_eDNA \
    --assay_name Fish16S --country Australia --project_values "$here/project_values.tsv" \
    --otu "$d/4_SEA-MES_16S_ASV_level_output_with_seq.csv" --otu_assay Fish16S --otu_run AGRF_2024-12 --otu_stage raw \
    --otu_curated_column '' \
    "${final[@]}" --otu_assay Fish16S --otu_run AGRF_2024-12 --otu_stage final \
    --library "$report" --library_filter 16SFish --library_assay Fish16S \
    -o "$out/faire/seames.xlsx" --log "$out/faire/seames.log"

echo "== 6. FAIRe-fier"
python "$repo/tools/fairefier/fairefier_cli.py" "$out/faire/seames.xlsx" -o "$out/faire/fairefier" \
    --checklist_dir "$repo/tools/fairefier/checklist" || true

echo "== 7. conversions and submission tables"
if [ -n "${RSCRIPT:-}" ]; then
  m="$repo/tools/faire2mdt"
  (cd "$out/faire" && "$RSCRIPT" --vanilla "$m/faire2mdt_galaxy.R" --upstream "$m/FAIRe2MDT.R" \
      --target_genes "$m/mdt_target_gene.tsv" --workbook seames.xlsx --assay Fish16S --seq_run AGRF_2024-12 \
      --otu seames.xlsx --otu_format xlsx --otu_sheet otuFinal --taxa seames.xlsx --taxa_format xlsx \
      --taxa_sheet taxaFinal --output seames_Fish16S_MDT.xlsx --log seames_Fish16S_MDT.log)
fi
(cd "$out/convert/qiime" && python "$repo/tools/faire2qiime/normalise_faire.py" "$out/faire/seames.xlsx" normalised.xlsx \
    --check_column samp_name > log.txt && python "$repo/tools/faire2qiime/faire2qiime.py" --path_faire normalised.xlsx \
    --sample_name_column samp_name --absolute_path_sequences /not/used --output_directory out >> log.txt 2>&1)
# The samples are registered already: accessions.py makes NCBI's accession table and a stand-in ENA
# receipt from the run report, to link the runs to them.
python "$here/accessions.py" "$report" "$out/convert/biosample_accessions.tsv" "$out/convert/ena_receipt.xml" 16SFish
# FAIRe2NCBI writes its working files in the current folder. --duplicates_column: the 10 L samples
# come in pairs with the same attributes (README.md).
(cd "$out/convert/ncbi_biosample" && python "$repo/tools/faire2ncbi/faire2ncbi_galaxy.py" biosample \
    --input_file "$out/faire/seames.xlsx" --organism "marine metagenome" --bioproject PRJNA1263580 \
    --mandatory_fill "not applicable" --duplicates_column replicate \
    --output biosample.tsv --config_out config.yaml < /dev/null > log.txt)
(cd "$out/convert/ncbi_sra" && python "$repo/tools/faire2ncbi/faire2ncbi_galaxy.py" sra \
    --input_file "$out/faire/seames.xlsx" --instrument_model "NextSeq 2000" \
    --accessions "$out/convert/biosample_accessions.tsv" --output sra.tsv --config_out config.yaml < /dev/null > log.txt)
python "$here/compare.py" biosample "$out/convert/ncbi_biosample/biosample.tsv" "$d/1_SEA-MES_M_samples_metadata_10L.xlsx"
python "$here/compare.py" sra "$out/convert/ncbi_sra/sra.tsv" "$report"
(cd "$out/convert/ena_samples" && python "$repo/tools/faire2ena/faire2ena_galaxy.py" sample \
    --input_file "$out/faire/seames.xlsx" --center_name CSIRO --taxon_id 408172 --output_file samples.xml \
    --submission_file submission.xml > log.txt)
(cd "$out/convert/ena_runs" && python "$repo/tools/faire2ena/faire2ena_galaxy.py" run \
    --input_file "$out/faire/seames.xlsx" --receipt_file "$out/convert/ena_receipt.xml" \
    --study_accession PRJNA1263580 --center_name CSIRO --instrument_model "NextSeq 2000" \
    --experiment_output experiments.xml --run_output runs.xml --submission_file submission.xml > log.txt)

echo "== 8. 18S end to end"
s="$out/18S"
mkdir -p "$s/mapper" "$s/faire" "$s/convert/qiime/out" "$s/convert/ncbi_biosample" "$s/convert/ncbi_sra" \
    "$s/convert/ena_samples" "$s/convert/ena_runs"
python "$here/make_2L_table.py" "$d/7_SEA-MES_2025_EUK_18S_for_DAT.csv.gz" "$s/mapper/samples_18S.csv" "$report"
python "$tools/faire_primers.py" text "$d/methods_consolidated.txt" -o "$s/mapper/primer_candidates.tsv"
python "$tools/faire_mapper.py" map "$s/mapper/samples_18S.csv" --sample_types Water --checklist "$ck" \
    --assay_type metabarcoding -o "$s/mapper/samples_18S"
python "$here/review.py" "$s/mapper/samples_18S/crosswalk.sssom.tsv" "$here/reviewer_decisions_18S.tsv" \
    "$s/mapper/reviewed.sssom.tsv"
gunzip -c "$d/7_SEA-MES_2025_EUK_18S_for_DAT.csv.gz" > "$s/faire/18S.csv"
python "$tools/faire_mapper_apply.py" "$s/mapper/samples_18S.csv" --crosswalk "$s/mapper/reviewed.sssom.tsv" \
    --checklist "$ck" --template "$tpl" --assay_type metabarcoding --sample_types Water --project_id SEA-MES_eDNA \
    --assay_name Euk18S --country Australia --utc_offset +10:00 --project_values "$here/project_values_18S.tsv" \
    --otu "$s/faire/18S.csv" --otu_assay Euk18S --otu_run Ramaciotti_2025-02 \
    --library "$report" --library_filter _18s --library_assay Euk18S \
    -o "$s/faire/seames_18S.xlsx" --log "$s/faire/seames_18S.log"
python "$repo/tools/fairefier/fairefier_cli.py" "$s/faire/seames_18S.xlsx" -o "$s/faire/fairefier" \
    --checklist_dir "$repo/tools/fairefier/checklist" || true
if [ -n "${RSCRIPT:-}" ]; then
  m="$repo/tools/faire2mdt"
  (cd "$s/faire" && "$RSCRIPT" --vanilla "$m/faire2mdt_galaxy.R" --upstream "$m/FAIRe2MDT.R" \
      --target_genes "$m/mdt_target_gene.tsv" --workbook seames_18S.xlsx --assay Euk18S --seq_run Ramaciotti_2025-02 \
      --otu seames_18S.xlsx --otu_format xlsx --otu_sheet otuFinal --taxa seames_18S.xlsx --taxa_format xlsx \
      --taxa_sheet taxaFinal --output seames_18S_MDT.xlsx --log seames_18S_MDT.log)
fi
(cd "$s/convert/qiime" && python "$repo/tools/faire2qiime/normalise_faire.py" "$s/faire/seames_18S.xlsx" normalised.xlsx \
    --check_column samp_name > log.txt && python "$repo/tools/faire2qiime/faire2qiime.py" --path_faire normalised.xlsx \
    --sample_name_column samp_name --absolute_path_sequences /not/used --output_directory out >> log.txt 2>&1)
python "$here/accessions.py" "$report" "$s/convert/biosample_accessions.tsv" "$s/convert/ena_receipt.xml" _18s
# --duplicates_column: the 2 L samples also come in pairs (_a and _b) with the same attributes.
(cd "$s/convert/ncbi_biosample" && python "$repo/tools/faire2ncbi/faire2ncbi_galaxy.py" biosample \
    --input_file "$s/faire/seames_18S.xlsx" --organism "marine metagenome" --bioproject PRJNA1263580 \
    --mandatory_fill "not applicable" --duplicates_column Sample_ID \
    --output biosample.tsv --config_out config.yaml < /dev/null > log.txt)
# ENA's run report names NextSeq 1000 for these runs; the ReadMe says MiSeq (README.md).
(cd "$s/convert/ncbi_sra" && python "$repo/tools/faire2ncbi/faire2ncbi_galaxy.py" sra \
    --input_file "$s/faire/seames_18S.xlsx" --instrument_model "NextSeq 1000" \
    --accessions "$s/convert/biosample_accessions.tsv" --output sra.tsv --config_out config.yaml < /dev/null > log.txt)
python "$here/compare.py" sra "$s/convert/ncbi_sra/sra.tsv" "$report"
python "$here/compare.py" sra_sheet "$s/convert/ncbi_sra/sra.tsv" "$d/3_SRA_metadata_SEAMES_18S.xlsx"
(cd "$s/convert/ena_samples" && python "$repo/tools/faire2ena/faire2ena_galaxy.py" sample \
    --input_file "$s/faire/seames_18S.xlsx" --center_name CSIRO --taxon_id 408172 --output_file samples.xml \
    --submission_file submission.xml > log.txt)
(cd "$s/convert/ena_runs" && python "$repo/tools/faire2ena/faire2ena_galaxy.py" run \
    --input_file "$s/faire/seames_18S.xlsx" --receipt_file "$s/convert/ena_receipt.xml" \
    --study_accession PRJNA1263580 --center_name CSIRO --instrument_model "NextSeq 1000" \
    --experiment_output experiments.xml --run_output runs.xml --submission_file submission.xml > log.txt)

echo "== 9. Wilderlab panel"
w="$out/WL"
mkdir -p "$w/mapper" "$w/faire" "$w/convert/qiime/out"
gunzip -c "$d/8_WL_Full_SEA_MES_samples.csv.gz" > "$w/faire/WL_published.csv"
python "$here/rename_WL_repeats.py" "$w/faire/WL_published.csv" "$w/faire/WL.csv"
python "$here/make_WL_table.py" "$out/mapper/M_prepared.csv" "$d/2_SEA-MES_CN_samples_metadata_OCD.xlsx" \
    "$s/mapper/samples_18S.csv" "$w/faire/WL.csv" "$w/mapper/samples_WL.csv"
python "$tools/faire_mapper.py" map "$w/mapper/samples_WL.csv" --sample_types Water --checklist "$ck" \
    --assay_type metabarcoding -o "$w/mapper/samples_WL"
python "$here/review.py" "$w/mapper/samples_WL/crosswalk.sssom.tsv" "$here/reviewer_decisions_WL.tsv" \
    "$w/mapper/reviewed.sssom.tsv"
# No assay names: they are the values of the target column (CI, WV, BE ...).
python "$tools/faire_mapper_apply.py" "$w/mapper/samples_WL.csv" --crosswalk "$w/mapper/reviewed.sssom.tsv" \
    --checklist "$ck" --template "$tpl" --assay_type metabarcoding --sample_types Water \
    --project_id SEA-MES_eDNA_Wilderlab --country Australia --project_values "$here/project_values_WL.tsv" \
    --otu "$w/faire/WL.csv" --otu_assay_column target --otu_name 8_WL_Full_SEA_MES_samples.csv \
    --otu_run Wilderlab_2024-12 -o "$w/faire/seames_WL.xlsx" --log "$w/faire/seames_WL.log"
python "$repo/tools/fairefier/fairefier_cli.py" "$w/faire/seames_WL.xlsx" -o "$w/faire/fairefier" \
    --checklist_dir "$repo/tools/fairefier/checklist" || true
if [ -n "${RSCRIPT:-}" ]; then
  m="$repo/tools/faire2mdt"
  for a in CI WV BE BU UM RV LG BX HD GD RJ XN; do
    (cd "$w/faire" && "$RSCRIPT" --vanilla "$m/faire2mdt_galaxy.R" --upstream "$m/FAIRe2MDT.R" \
        --target_genes "$m/mdt_target_gene.tsv" --workbook seames_WL.xlsx --assay $a --seq_run Wilderlab_2024-12 \
        --otu seames_WL.xlsx --otu_format xlsx --otu_sheet otuFinal_$a --taxa seames_WL.xlsx --taxa_format xlsx \
        --taxa_sheet taxaFinal_$a --output seames_WL_${a}_MDT.xlsx --log seames_WL_${a}_MDT.log)
  done
fi
(cd "$w/convert/qiime" && python "$repo/tools/faire2qiime/normalise_faire.py" "$w/faire/seames_WL.xlsx" normalised.xlsx \
    --check_column samp_name > log.txt && mkdir -p out && python "$repo/tools/faire2qiime/faire2qiime_by_assay.py" \
    "$repo/tools/faire2qiime/faire2qiime.py" normalised.xlsx out -- \
    --sample_name_column samp_name --absolute_path_sequences /not/used >> log.txt 2>&1)
echo "done: $out"
