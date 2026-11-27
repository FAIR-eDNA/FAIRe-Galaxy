# Shared set-up for the demonstration flows. Run each flow from the shiny folder:
#   Rscript tests/flows/eelgrass.R
# FAIRE_PYTHON chooses the Python (python3 by default); FAIRE_TEST_OUT the folder the flows copy their
# workbook, FAIRe-fier summary and Darwin Core report to (a temporary folder by default), so that two
# versions of the app can be compared with tests/compare_outputs.py.
if (!nzchar(Sys.getenv("FAIRE_PYTHON"))) Sys.setenv(FAIRE_PYTHON = "python3")
suppressPackageStartupMessages(library(shiny))
app <- source("app.R")$value
out_dir <- Sys.getenv("FAIRE_TEST_OUT", file.path(tempdir(), "faire_flows"))
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
failures <- character()
expect <- function(ok, what) {
  ok <- isTRUE(ok)
  cat(if (ok) "PASS" else "FAIL", what, "\n")
  if (!ok) failures <<- c(failures, what)
}
finish <- function() {
  if (length(failures)) { cat(length(failures), "failed\n"); quit(status = 1) }
  cat("All checks passed\n")
}
# Copies of what each flow wrote, named after the demonstration
save_outputs <- function(name, apply, fairefier, dwc) {
  cp <- function(p, to) if (!is.null(p) && length(p) && file.exists(p)) file.copy(p, file.path(out_dir, to), overwrite = TRUE)
  cp(apply$outputs$workbook, paste0(name, "_workbook.xlsx"))
  cp(fairefier$outputs$summary, paste0(name, "_fairefier_summary.json"))
  cp(fairefier$outputs$issues, paste0(name, "_fairefier_issues.tsv"))
  cp(dwc$outputs$report, paste0(name, "_dwc_report.md"))
  cat("outputs copied to", out_dir, "\n")
}
# The journey's next step (R/journey.R) is the one wanted
next_is <- function(j, want) {
  got <- j$next_step$title
  expect(identical(got, want), paste0("next step: ", want, if (!identical(got, want)) paste0(" (got: ", got, ")") else ""))
}
show_pv <- function(pv) { for (i in seq_len(nrow(pv))) cat(sprintf("  %-28s %-14s %s\n", pv$term[i], pv$assay[i], substr(pv$value[i], 1, 70))) }
missing_terms <- function(rv) {
  m <- read_tsv(rv$map$outputs$missing)
  setdiff(m$term[m$sheet == "projectMetadata"], c(rv$pv$term, "project_id", "assay_name", "assay_type", "checkls_ver"))
}
