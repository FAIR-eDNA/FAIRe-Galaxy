source("tests/flows/common.R")
testServer(app, {
  set <- function(id, value) do.call(session$setInputs, setNames(list(value), id))
  session$setInputs(demo_choice = "eelgrass", load_demo = 1)
  cat("demo:", rv$demo, "| files:", paste(names(rv$files), collapse = ", "), "| pv:", nrow(rv$pv), "\n")
  session$setInputs(run_identify = 1)
  session$setInputs(map_table = "eelgrass_samples_prepared.csv", map_dictionary = "Dryad_README.md", map_assay_type = "metabarcoding",
                    map_sample_types = "Water", map_header_row = 1, run_map = 1)
  r <- review()$rows
  ans <- DEMOS$eelgrass$decisions
  for (i in seq_len(nrow(r))) { k <- match(r$input[i], ans$input); if (!is.na(k)) { set(dec_id(i), ans$decision[k]); set(rep_id(i), ans$replacement[k]) } }
  session$setInputs(save_review = 1)
  cat("mandatory project terms still to give:", paste(missing_terms(rv), collapse = ", "), "\n")
  # d. find primers in the README and the notes
  session$setInputs(pr_texts = DEMOS$eelgrass$methods, pr_mode = "text", pr_source = "bundled", run_primers = 1)
  p <- rv$primers; cat("primer pairs found:", nrow(p), "| first:", likely_of(p)[1], "| default name:", default_assay(p[1, , drop = FALSE]), "\n")
  a <- list(); a[[pr_id("use", 2)]] <- TRUE; a[[pr_id("name", 2)]] <- "Hidden"; a$pr_add <- 1
  do.call(session$setInputs, a); cat("pv rows after ticking only a hidden pair:", nrow(rv$pv), "\n")
  a <- list(); a[[pr_id("use", 2)]] <- FALSE; a[[pr_id("use", 1)]] <- TRUE; a[[pr_id("name", 1)]] <- "LerayCOI"; a$pr_add <- 2
  do.call(session$setInputs, a); cat("pv assays:", paste(unique(rv$pv$assay), collapse = ", "), "\n")
  # the reference table's target taxon for this pair is wrong for this study: change it, as the steps say
  k <- which(rv$pv$term == "targetTaxonomicAssay")
  session$setInputs(pv_table_cell_edit = list(row = k, col = 1, value = "Metazoa"))
  # other method details: tick the reliable ones, correct sequencing_location
  session$setInputs(md_assay_type = "metabarcoding", run_details = 1)
  d <- rv$details
  rel <- which(d$confidence == "reliable")
  cat("details:", nrow(d), "found,", length(rel), "reliable:", paste(d$term[rel], collapse = ", "), "\n")
  sl <- which(d$term == "sequencing_location")
  set(paste0("md_val_", sl), "Pacific Biological Station, Fisheries and Oceans Canada, Nanaimo (samples from 2019) | The Centre for Applied Genomics, Toronto (samples from 2023)")
  session$setInputs(md_kept = rel, md_add = 1)
  cat("mandatory project terms still to give:", paste(missing_terms(rv), collapse = ", "), "\n")
  # values typed by hand
  cat("missing-terms form lists:", paste(pv_left(), collapse = ", "), "\n")
  session$setInputs(mt_value_pcr_0_1 = "1", mt_value_project_id = "NS.eelgrass", mt_add = 1)
  cat("after a project_id with a space, still missing:", paste(pv_left(), collapse = ", "), "\n")
  session$setInputs(mt_value_project_id = "NS_eelgrass_eDNA", mt_value_project_contact = "Nick Jeffery (Nick.Jeffery@dfo-mpo.gc.ca)",
                    mt_value_recordedBy = "missing: not provided", mt_add = 2)
  cat("after the form, still missing:", paste(pv_left(), collapse = ", "), "\n")
  session$setInputs(pv_term = "license", pv_value = "http://creativecommons.org/publicdomain/zero/1.0/legalcode", pv_assay = "", pv_add = 1)
  cat("project values:\n"); show_pv(rv$pv)
  cat("mandatory project terms still to give:", paste(missing_terms(rv), collapse = ", "), "\n")
  bv <- rv$block_version
  for (kind in c("otu", "lib")) for (i in seq_along(DEMOS$eelgrass[[kind]])) {
    b <- DEMOS$eelgrass[[kind]][[i]]
    for (f in names(b)) set(paste0(kind, bv, "_", i, "_", f), b[[f]])
  }
  session$setInputs(ap_utc_offset = "",
                    ap_date_order = "stop", ap_include_review = FALSE, ap_req_lev = c("HR", "R", "O"),
                    ap_drop_unmapped = FALSE, run_apply = 1)
  res <- rv$res$apply
  cat("apply ok:", res$ok, "\n")
  cat(grep("^WARNING|^INFO: wrote", strsplit(res$log, "\n")[[1]], value = TRUE), sep = "\n")
  session$setInputs(ck_wb = "__current__", ck_version = "auto", run_fairefier = 1)
  cat(grep("Success|Error", strsplit(rv$res$fairefier$log, "\n")[[1]], value = TRUE), sep = "\n")
  w <- DEMOS$eelgrass$dwc
  session$setInputs(cv_wb = "__current__", dw_assays = NULL, dw_taxa = "eelgrass_taxa.tsv", dw_target = "gbif", dw_country_code = "",
                    dw_absences = TRUE, dw_title = w$title, dw_abstract = w$abstract, dw_keywords = w$keywords, dw_given = w$given,
                    dw_surname = w$surname, dw_org = w$org, dw_email = w$email, dw_orcid = "", dw_licence = "workbook", run_dwc = 1)
  d <- rv$res$dwc
  cat("dwc ok:", d$ok, "\n"); rep <- readLines(d$outputs$report); cat(rep[grepl("^- ", rep)], sep = "\n")
  expect(res$ok, "eelgrass: the workbook is written")
  expect(!is.null(rv$res$fairefier) && file.exists(rv$res$fairefier$outputs$summary %||% ""), "eelgrass: FAIRe-fier ran")
  expect(isTRUE(rv$res$dwc$ok), "eelgrass: the Darwin Core archive is written")
  save_outputs("eelgrass", res, rv$res$fairefier, rv$res$dwc)
})
finish()
