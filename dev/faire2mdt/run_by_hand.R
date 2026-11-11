# Run FAIRe2MDT.R as a user would by hand: the user section filled in with the given names and
# files (read exactly as upstream reads them), then the upstream code from "# Run the below code".
# Used to compare the Galaxy driver with upstream.
#
# Usage: Rscript run_by_hand.R FAIRe2MDT.R WORKBOOK ASSAY SEQ_RUN OTU.xlsx OTU_SHEET TAXA.xlsx TAXA_SHEET OUTDIR
suppressPackageStartupMessages({
  library(readxl); library(openxlsx); library(dplyr); library(tibble)
})
a <- commandArgs(trailingOnly = TRUE)
assay <- a[3]
seq_run <- a[4]
Project <- read_excel(a[2], sheet = "projectMetadata", col_names = TRUE)
Samples <- read_excel(a[2], sheet = "sampleMetadata", col_names = FALSE)
expRun <- read_excel(a[2], sheet = "experimentRunMetadata", col_names = FALSE)
otu <- read_excel(a[5], sheet = a[6], col_names = TRUE)
taxa <- read_excel(a[7], sheet = a[8], col_names = FALSE)
up <- readLines(a[1], warn = FALSE)
code <- parse(text = up[grep("^# Run the below code", up):length(up)], keep.source = FALSE)
setwd(a[9])
for (e in code) eval(e)
cat("wrote", output_filename, "\n")
