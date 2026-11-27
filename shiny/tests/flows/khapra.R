source("tests/flows/common.R")
testServer(app, {
  set <- function(id, value) do.call(session$setInputs, setNames(list(value), id))
  session$setInputs(demo_choice = "khapra", load_demo = 1)
  cat("demo:", rv$demo, "| files:", paste(names(rv$files), collapse = ", "), "| pv:", nrow(rv$pv), "\n")
  session$setInputs(run_identify = 1)
  print(rv$identify[, c("file", "kind")])
  session$setInputs(map_table = "khapra_samples_prepared.csv", map_dictionary = "Trujillo_Gonzalez_et_al_2022_README.txt",
                    map_assay_type = "targeted", map_sample_types = "Air", map_header_row = 1, run_map = 1)
  r <- review()$rows
  ans <- DEMOS$khapra$decisions
  for (i in seq_len(nrow(r))) { k <- match(r$input[i], ans$input); if (!is.na(k)) { set(dec_id(i), ans$decision[k]); set(rep_id(i), ans$replacement[k]) } }
  session$setInputs(save_review = 1)
  next_is(journey_now(), "Find the primers and method details")
  cat("mandatory project terms still to give:", paste(missing_terms(rv), collapse = ", "), "\n")
  session$setInputs(pr_texts = DEMOS$khapra$methods, pr_mode = "text", pr_source = "bundled", run_primers = 1)
  p <- rv$primers; cat("primer pairs found:", nrow(p), "| likely:", paste(likely_of(p), collapse = ", "), "\n")
  a <- list(); a[[pr_id("use", 1)]] <- TRUE; a[[pr_id("name", 1)]] <- "Olson_ViiA7"; a$pr_add <- 11
  do.call(session$setInputs, a); cat("pv rows after an underscore in a qPCR assay name:", nrow(rv$pv), "\n")
  cat("default name for a targeted pair:", default_assay(data.frame(assay_name = "Some_Pair", target_gene = NA)), "\n")
  a <- list(); a[[pr_id("use", 1)]] <- TRUE; a[[pr_id("name", 1)]] <- "Olson ViiA7"; a$pr_add <- 1
  do.call(session$setInputs, a); cat("pv rows after a name with a space:", nrow(rv$pv), "\n")
  a <- list(); a[[pr_id("use", 1)]] <- TRUE; a[[pr_id("name", 1)]] <- "OlsonViiA7, OlsonFranklin"
  a[[pr_id("use", 2)]] <- TRUE; a[[pr_id("name", 2)]] <- "OlsonViiA7"; a$pr_add <- 2
  do.call(session$setInputs, a); cat("pv rows after a name given twice:", nrow(rv$pv), "\n")
  a <- list(); a[[pr_id("name", 2)]] <- "FuruiViiA7, FuruiFranklin"; a$pr_add <- 3
  do.call(session$setInputs, a); cat("pv assays:", paste(unique(rv$pv$assay), collapse = ", "), "\n")
  session$setInputs(md_assay_type = "targeted", run_details = 1)
  d <- rv$details
  for (i in seq_len(nrow(d))) cat(sprintf("  %2d %-9s %-28s %s\n", i, d$confidence[i], d$term[i], substr(d$value[i], 1, 60)))
  pick <- function(term, value_start, assay = "") {
    i <- which(d$term == term & startsWith(d$value, value_start))[1]
    set(paste0("md_assay_", i), assay); i
  }
  keep <- c(pick("pcr_0_1", "1"),
            pick("commercial_mm", "TaqMan", "OlsonViiA7, FuruiViiA7"),
            pick("pcr_cond", "initial denaturation:95_10;denaturation:95_0.333;annealing:50", "OlsonViiA7"),
            pick("pcr_cond", "initial denaturation:95_10;denaturation:95_0.333;annealing:60", "FuruiViiA7"),
            pick("pcr_cond", "initial denaturation:95_2;denaturation:95_0.167;annealing:50", "OlsonFranklin"),
            pick("pcr_cond", "initial denaturation:95_2;denaturation:95_0.333;annealing:60", "FuruiFranklin"),
            pick("annealingTemp", "50", "OlsonViiA7, OlsonFranklin"), pick("annealingTemp", "60", "FuruiViiA7, FuruiFranklin"),
            pick("pcr_cycles", "50", "OlsonViiA7, OlsonFranklin"), pick("pcr_cycles", "45", "FuruiViiA7, FuruiFranklin"),
            pick("amplificationReactionVolume", "20"), pick("pcr_dna_vol", "5"),
            pick("thermocycler", "Applied Biosystems, ViiA7", "OlsonViiA7, FuruiViiA7"))
  session$setInputs(md_kept = keep, md_add = 1)
  session$setInputs(md_add_confirm = 1)
  cat("after details:", nrow(rv$pv), "values; still to give:", paste(missing_terms(rv), collapse = ", "), "\n")
  typed <- list(c("targetTaxonomicAssay", "Trogoderma granarium", ""), c("amp_vis_method", "qPCR", ""),
                c("detection_criteria", "A replicate was positive when its amplification curve crossed a common fluorescence threshold, set in each qPCR run from the positive controls", ""),
                c("pcr_assay_lod", "100", "OlsonViiA7, OlsonFranklin"), c("pcr_assay_lod", "10", "FuruiViiA7, FuruiFranklin"),
                c("pcr_assay_lod_unit", "copies/\u00b5L", ""), c("pcr_assay_loq", "missing: not provided", ""),
                c("pcr_assay_loq_unit", "missing: not provided", ""), c("thresholdQuantificationCycle", "missing: not provided", ""),
                c("project_contact", "Alejandro Trujillo-Gonzalez (alejandro.Trujillogonzalez@canberra.edu.au)", ""),
                c("recordedBy", "missing: not provided", ""),
                c("license", "http://creativecommons.org/publicdomain/zero/1.0/legalcode", ""),
                c("informationWithheld", "The locations of the stores sampled, withheld by the authors as sensitive and potentially identifying; only the suburb is given", ""))
  for (tv in typed) session$setInputs(pv_term = tv[1], pv_value = tv[2], pv_assay = tv[3], pv_add = 1)
  cat("project values:\n"); show_pv(rv$pv)
  cat("still to give:", paste(missing_terms(rv), collapse = ", "), "\n")
  bv <- rv$block_version
  session$setInputs(pv_term = "project_id", pv_value = "khapra_eDNA", pv_assay = "", pv_add = 99)
  # a targeted assay asks for qPCR or ddPCR results, not OTU tables
  set(paste0("amp", bv, "_1_file"), "")
  build <- journey_now()$stages$detail[journey_now()$stages$id == "build"]
  expect(identical(build, "No qPCR or ddPCR results chosen yet"), paste("with no results chosen, step 5 asks for qPCR or ddPCR results:", build))
  set(paste0("amp", bv, "_1_file"), "khapra_qpcr_prepared.csv")
  set(paste0("amp", bv, "_1_assay_column"), "assay_name")
  set(paste0("amp", bv, "_1_sheet"), "")
  next_is(journey_now(), "Build the FAIRe workbook")
  session$setInputs(ap_utc_offset = "", ap_date_order = "dmy", ap_include_review = FALSE,
                    ap_req_lev = c("HR", "R", "O"), ap_drop_unmapped = FALSE, run_apply = 1)
  res <- rv$res$apply
  next_is(journey_now(), "Check the workbook")
  cat("apply ok:", res$ok, "\n"); cat(grep("^WARNING|^INFO: wrote", strsplit(res$log, "\n")[[1]], value = TRUE), sep = "\n")
  session$setInputs(ck_wb = "__current__", ck_version = "auto", run_fairefier = 1)
  fr <- rv$res$fairefier
  cat(tail(strsplit(fr$log, "\n")[[1]], 12), sep = "\n"); iss <- read_tsv(file.path(dirname(fr$outputs[[1]]), "out", "fairefier_issues.tsv")); if (is.null(iss)) iss <- read_tsv(list.files(dirname(dirname(fr$outputs[[1]])), "fairefier_issues.tsv", recursive = TRUE, full.names = TRUE)[1]); print(head(iss, 20))
  w <- DEMOS$khapra$dwc
  session$setInputs(cv_wb = "__current__", dw_assays = NULL, dw_taxa = "khapra_taxa.tsv", dw_target = "gbif",
                    dw_country_code = "", dw_absences = TRUE, dw_title = w$title, dw_abstract = w$abstract, dw_keywords = w$keywords,
                    dw_given = w$given, dw_surname = w$surname, dw_org = w$org, dw_email = w$email, dw_orcid = "", dw_licence = "workbook", run_dwc = 1)
  d <- rv$res$dwc
  cat("dwc ok:", d$ok, "\n"); rep <- readLines(d$outputs$report); cat(rep[grepl("^- ", rep)], sep = "\n")
  expect(res$ok, "khapra: the workbook is written")
  expect(!is.null(rv$res$fairefier) && file.exists(rv$res$fairefier$outputs$summary %||% ""), "khapra: FAIRe-fier ran")
  expect(isTRUE(rv$res$dwc$ok), "khapra: the Darwin Core archive is written")
  save_outputs("khapra", res, rv$res$fairefier, rv$res$dwc)
})
finish()
