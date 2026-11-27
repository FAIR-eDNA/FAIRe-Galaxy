source("tests/flows/common.R")
testServer(app, {
  set <- function(id, value) do.call(session$setInputs, setNames(list(value), id))
  session$setInputs(demo_choice = "seames", load_demo = 1)
  cat("demo:", rv$demo, "| files:", length(rv$files), "| pv:", nrow(rv$pv), "\n")
  session$setInputs(run_identify = 1)
  session$setInputs(map_table = "SEA-MES_10L_samples.csv", map_dictionary = "", map_assay_type = "metabarcoding",
                    map_sample_types = "Water", map_header_row = 1, run_map = 1)
  r <- review()$rows
  ans <- DEMOS$seames$decisions
  for (i in seq_len(nrow(r))) { k <- match(r$input[i], ans$input); if (!is.na(k)) { set(dec_id(i), ans$decision[k]); set(rep_id(i), ans$replacement[k]) } }
  session$setInputs(save_review = 1)
  cat("mandatory project terms still to give:", paste(missing_terms(rv), collapse = ", "), "\n")
  session$setInputs(pr_texts = DEMOS$seames$methods, pr_mode = "text", pr_source = "bundled", run_primers = 1)
  p <- rv$primers; print(data.frame(likely = likely_of(p), assay = vapply(seq_len(nrow(p)), function(i) default_assay(p[i, , drop = FALSE]), "")))
  k <- which(p$assay_name == "Fish16S")[1]; j <- which(likely_of(p) == "exact match" & p$assay_name != "Fish16S")[1]
  a <- list(); a[[pr_id("use", k)]] <- TRUE; a[[pr_id("name", k)]] <- "Fish16S"; a[[pr_id("use", j)]] <- FALSE; a$pr_add <- 1
  do.call(session$setInputs, a); cat("pv assays:", paste(unique(rv$pv$assay), collapse = ", "), "\n")
  k <- which(rv$pv$term == "ampliconSize")
  session$setInputs(pv_table_cell_edit = list(row = k, col = 1, value = "180-230"))
  session$setInputs(md_assay_type = "metabarcoding", run_details = 1)
  d <- rv$details
  rel <- which(d$confidence == "reliable")
  session$setInputs(md_kept = rel, md_add = 1)
  for (tv in list(c("targetTaxonomicAssay", "Fish (teleosts and elasmobranchs)"), c("recordedBy", "missing: not provided"),
                  c("project_contact", "Bruce Deagle"), c("institution", "CSIRO"),
                  c("license", "https://creativecommons.org/licenses/by/4.0/legalcode"), c("samp_vol_we_dna_ext_unit", "mL")))
    session$setInputs(pv_term = tv[1], pv_value = tv[2], pv_assay = "", pv_add = 1)
  cat("project values:\n"); show_pv(rv$pv)
  cat("still to give:", paste(missing_terms(rv), collapse = ", "), "\n")
  bv <- rv$block_version
  for (kind in c("otu", "lib")) for (i in seq_along(DEMOS$seames[[kind]])) {
    b <- DEMOS$seames[[kind]][[i]]
    for (f in names(b)) set(paste0(kind, bv, "_", i, "_", f), b[[f]])
  }
  session$setInputs(pv_term = "project_id", pv_value = "SEA-MES_eDNA", pv_assay = "", pv_add = 99)
  session$setInputs(ap_utc_offset = "",
                    ap_date_order = "stop", ap_include_review = FALSE, ap_req_lev = c("HR", "R", "O"),
                    ap_drop_unmapped = FALSE, run_apply = 1)
  res <- rv$res$apply
  cat("apply ok:", res$ok, "\n"); cat(grep("^WARNING|^INFO: wrote", strsplit(res$log, "\n")[[1]], value = TRUE), sep = "\n")
  session$setInputs(ck_wb = "__current__", ck_version = "auto", run_fairefier = 1)
  cat(grep("Success|Failed", strsplit(rv$res$fairefier$log, "\n")[[1]], value = TRUE), sep = "\n")
  iss <- read_tsv(list.files(dirname(dirname(rv$res$fairefier$outputs[[1]])), "fairefier_issues.tsv", recursive = TRUE, full.names = TRUE)[1])
  print(iss[iss$level == "error", c("worksheet", "record", "term", "input", "message")])
  session$setInputs(cv_wb = "__current__", dw_assays = NULL, dw_taxa = "", dw_target = "gbif", dw_country_code = "",
                    dw_absences = TRUE, dw_title = "", dw_abstract = "", dw_keywords = "", dw_given = "", dw_surname = "",
                    dw_org = "", dw_email = "", dw_orcid = "", dw_licence = "workbook", run_dwc = 1)
  d <- rv$res$dwc
  cat("dwc ok:", d$ok, "\n"); rep <- readLines(d$outputs$report); cat(rep[grepl("^- ", rep)], sep = "\n")
  expect(res$ok, "seames: the workbook is written")
  expect(!is.null(rv$res$fairefier) && file.exists(rv$res$fairefier$outputs$summary %||% ""), "seames: FAIRe-fier ran")
  expect(isTRUE(rv$res$dwc$ok), "seames: the Darwin Core archive is written")
  save_outputs("seames", res, rv$res$fairefier, rv$res$dwc)
})
finish()
