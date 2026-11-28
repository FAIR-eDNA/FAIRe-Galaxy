# Runs every conversion on the FAIRe workbooks that the demonstration flows write, with the Convert
# page's starting settings (and the demonstration's own files, such as ENA's sample receipt), and says
# which ran and why any stopped. It also checks the app's readiness verdict for each against the result:
# a conversion said to be ready should run.
#
#   FAIRE_PYTHON=python3 FAIRE_TEST_OUT=/tmp/flows Rscript tests/conversions.R [eelgrass seames khapra]
#
# FAIRE_TEST_OUT is the folder the flows (tests/flows/*.R) wrote <name>_workbook.xlsx to. edna2obis's
# name matching needs internet access, so its build step is given a mapping table made from the
# workbook's own taxaFinal sheet; the match step is run only when FAIRE_TEST_NETWORK=1.

options(faire.app_dir = normalizePath("."))
suppressMessages({
  library(shiny)
  for (f in list.files("R", pattern = "\\.R$", full.names = TRUE)) source(f)
})
out <- Sys.getenv("FAIRE_TEST_OUT", "/tmp/flows")
names_given <- commandArgs(trailingOnly = TRUE)
which <- if (length(names_given)) names_given else c("seames", "eelgrass", "khapra")
sd <- tempfile("conversions_"); dir.create(sd)

failures <- 0
report <- function(name, conv, res, ready) {
  ok <- isTRUE(res$ok)
  log <- res$log %||% paste(vapply(res$steps %||% list(), function(s) s$output %||% "", ""), collapse = "\n")
  why <- if (ok) "" else {
    e <- explain_error(log)
    if (!nzchar(e)) e <- paste(tail(grep("ERROR|Error|error", strsplit(log, "\n")[[1]], value = TRUE), 2), collapse = " / ")
    e
  }
  verdict <- if (is.null(ready)) "" else ready$status
  # a conversion said to be ready should run, and one that needs something should stop; one not suited
  # to the study is not run on the page, whatever it does here
  agree <- is.null(ready) || ready$status == "not_suited" || (ok == (ready$status == "ready"))
  if (!agree) failures <<- failures + 1
  cat(sprintf("%-9s %-34s %-6s %-10s %s%s\n", name, conv, if (ok) "ran" else "STOPPED", verdict,
              if (agree) "" else "MISMATCH ", substr(gsub("\\s+", " ", why), 1, 220)))
}

# A WoRMS mapping table from the workbook's taxaFinal sheet, standing in for edna2obis: match taxa
mapping_from_taxa <- function(wb, assay, path) {
  tx <- read_faire_sheet(wb, "taxaFinal")
  tx <- tx[nzchar(tx$seq_id), , drop = FALSE]
  # the names edna2obis looks up: verbatimIdentification, or else the ranks joined with ';'
  ranks <- intersect(c("kingdom", "phylum", "class", "order", "family", "genus", "scientificName"), names(tx))
  joined <- apply(tx[ranks], 1, function(r) paste(r[nzchar(trimws(r))], collapse = ";"))
  tx$verbatimIdentification <- ifelse(nzchar(trimws(tx$verbatimIdentification)), tx$verbatimIdentification, joined)
  v <- unique(tx$verbatimIdentification[nzchar(tx$verbatimIdentification)])
  sci <- tx$scientificName[match(v, tx$verbatimIdentification)]
  rank <- tx$taxonRank[match(v, tx$verbatimIdentification)]
  sci[!nzchar(sci)] <- "Biota"; rank[!nzchar(rank)] <- "kingdom"
  m <- data.frame(verbatimIdentification = v, assay_name = assay, selected_match = "True", ambiguous = "False",
                  scientificName = sci, taxonRank = rank,
                  scientificNameID = paste0("urn:lsid:marinespecies.org:taxname:", seq_along(v)),
                  kingdom = "Animalia", nameAccordingTo = "WoRMS", stringsAsFactors = FALSE)
  utils::write.table(m, path, sep = "\t", quote = FALSE, row.names = FALSE)
  path
}
sheet_tsv <- function(wb, sheet, path) {
  x <- as.data.frame(readxl::read_excel(wb, sheet, col_names = FALSE, col_types = "text", .name_repair = "minimal"))
  x[is.na(x)] <- ""
  utils::write.table(x, path, sep = "\t", quote = FALSE, row.names = FALSE, col.names = FALSE, fileEncoding = "UTF-8")
  path
}

for (name in which) {
  wb <- file.path(out, paste0(name, "_workbook.xlsx"))
  if (!file.exists(wb)) { cat(name, ": no workbook at", wb, "\n"); failures <- failures + 1; next }
  demo <- DEMOS[[name]]
  dfile <- function(f) if (!is.null(f) && nzchar(f)) file.path(DEMO_ROOT, demo$dir, f) else NULL
  facts <- workbook_facts(wb)
  ready <- function(id, settings = list()) convert_readiness(facts, id, settings)
  cat("\n==", name, ":", paste(facts$assays, collapse = ", "), "\n")
  assay <- facts$assays[1] %||% ""
  run <- facts$run_pairs$run[nzchar(facts$run_pairs$run) & facts$run_pairs$assay == assay][1] %||% ""

  report(name, "NCBI BioSample", run_ncbi_biosample(sd, wb, ORGANISMS[1]), ready("ncbi_biosample"))
  report(name, "NCBI SRA (by sample name)", run_ncbi_sra(sd, wb), ready("ncbi_sra"))
  if (!is.null(dfile(demo$accessions)))
    report(name, "NCBI SRA (by accession)", run_ncbi_sra(sd, wb, accessions = dfile(demo$accessions)), NULL)
  report(name, "ENA samples", run_ena_sample(sd, wb, "TESTCENTRE", "408172"), ready("ena_sample", list(center = "TESTCENTRE")))
  if (!is.null(dfile(demo$receipt)))
    report(name, "ENA experiments and runs", run_ena_run(sd, wb, dfile(demo$receipt), "PRJEB00000", "TESTCENTRE",
                                                         "NextSeq 2000"),
           ready("ena_run", list(receipt = dfile(demo$receipt), study = "PRJEB00000", center = "TESTCENTRE",
                                 instrument = "NextSeq 2000")))
  report(name, "GBIF (MDT)", if (nzchar(run)) run_mdt(sd, wb, assay, run) else list(ok = FALSE, steps = list(list(output =
    "ERROR: no rows in experimentRunMetadata have assay_name 'x' and seq_run_id ''. The workbook has: x / NA (1 rows)."))),
    ready("mdt"))
  if ("taxaFinal" %in% facts$sheets) {
    d <- file.path(sd, paste0(name, "_eo")); dir.create(d, showWarnings = FALSE)
    an <- lapply(facts$assays, function(a) list(assay = a, run = run %||% a,
                                               taxonomy = sheet_tsv(wb, "taxaFinal", file.path(d, "taxa.tsv")),
                                               abundance = sheet_tsv(wb, "otuFinal", file.path(d, "otu.tsv"))))
    if (Sys.getenv("FAIRE_TEST_NETWORK") == "1")
      report(name, "edna2obis: match taxa", run_edna2obis_match(sd, an), NULL)
    report(name, "edna2obis: Darwin Core", run_edna2obis_build(sd, wb, an, mapping_from_taxa(wb, assay, file.path(d, "map.tsv"))),
           ready("eo_build", list(mapping = "made from taxaFinal")))
  } else report(name, "edna2obis: Darwin Core", list(ok = FALSE, steps = list(list(output = "ERROR: no taxaFinal sheet"))),
                ready("eo_build"))
  report(name, "Darwin Core presence (GBIF)", run_faire2dwc(sd, wb), ready("dwc"))
  report(name, "QIIME 2 (with manifests)", run_qiime(sd, wb), ready("qiime"))
  report(name, "QIIME 2 (metadata only)", run_qiime(sd, wb, write_manifests = FALSE), NULL)
}
# ---------------------------------------------------------------- variants
# The same conversions where the workbook, or the form, gives what was missing: each should then be
# ready, and run. A variant workbook is a copy with cells of one sheet filled (field names on row 3).
fill_cells <- function(from, to, sheet, values) {
  w <- openxlsx::loadWorkbook(from)
  hdr <- as.character(unlist(openxlsx::read.xlsx(w, sheet, rows = 3, colNames = FALSE, skipEmptyCols = FALSE)))
  for (f in names(values)) {
    j <- match(f, hdr)
    if (is.na(j)) stop("no ", f, " in ", sheet)
    openxlsx::writeData(w, sheet, data.frame(values[[f]]), startCol = j, startRow = 4, colNames = FALSE)
  }
  openxlsx::saveWorkbook(w, to, overwrite = TRUE)
  to
}
if (all(c("seames", "eelgrass") %in% which)) {
  cat("\n== variants\n")
  # eelgrass, with a run ID and read files (as a library table in step e would give)
  ew <- file.path(out, "eelgrass_workbook.xlsx")
  libs <- read_faire_sheet(ew, "experimentRunMetadata")$lib_id
  libs <- libs[nzchar(libs)]
  md5 <- function(x) vapply(x, function(v) paste(rev(strsplit(sprintf("%032s", gsub("[^0-9a-f]", "", tolower(paste0(
    unlist(lapply(utf8ToInt(v), function(i) sprintf("%02x", i))), collapse = "")))), "")[[1]]), collapse = ""), "")
  ev <- fill_cells(ew, file.path(sd, "eelgrass_with_runs.xlsx"), "experimentRunMetadata",
                   list(seq_run_id = rep("run1", length(libs)), filename = paste0(libs, "_R1.fastq.gz"),
                        filename2 = paste0(libs, "_R2.fastq.gz"), checksum_filename = gsub(" ", "0", md5(paste0(libs, "1"))),
                        checksum_filename2 = gsub(" ", "0", md5(paste0(libs, "2")))))
  f2 <- workbook_facts(ev)
  report("eelgrass+", "GBIF (MDT), with a run ID", run_mdt(sd, ev, "LerayCOI", "run1"), convert_readiness(f2, "mdt"))
  report("eelgrass+", "NCBI SRA, with read files", run_ncbi_sra(sd, ev), convert_readiness(f2, "ncbi_sra"))
  report("eelgrass+", "NCBI BioSample, 'not collected'", run_ncbi_biosample(sd, ev, ORGANISMS[1], mandatory_fill = "not collected"),
         convert_readiness(f2, "ncbi_biosample", list(mandatory_fill = "not collected")))
  report("eelgrass+", "NCBI BioSample, filled, Replicate", run_ncbi_biosample(sd, ev, ORGANISMS[1], mandatory_fill = "not collected",
                                                                            duplicates_column = "Replicate"),
         convert_readiness(f2, "ncbi_biosample", list(mandatory_fill = "not collected", duplicates_column = "Replicate")))
  report("eelgrass+", "QIIME 2 (with manifests)", run_qiime(sd, ev), convert_readiness(f2, "qiime"))
  report("eelgrass+", "QIIME 2 (run ID suffix)", run_qiime(sd, ev, use_suffix = TRUE),
         convert_readiness(f2, "qiime", list(suffix = TRUE)))

  # SEA-MES, with other choices on the forms
  sw <- file.path(out, "seames_workbook.xlsx"); f3 <- workbook_facts(sw)
  report("seames", "NCBI BioSample, 'not applicable'", run_ncbi_biosample(sd, sw, ORGANISMS[1], mandatory_fill = "not applicable"),
         convert_readiness(f3, "ncbi_biosample", list(mandatory_fill = "not applicable")))
  report("seames", "NCBI BioSample, filled, replicate", run_ncbi_biosample(sd, sw, ORGANISMS[1], mandatory_fill = "not applicable",
                                                                        duplicates_column = "replicate"),
         convert_readiness(f3, "ncbi_biosample", list(mandatory_fill = "not applicable", duplicates_column = "replicate")))
  report("seames", "NCBI SRA, runs by assay", run_ncbi_sra(sd, sw, runs_by = "assay", runs_values = "Fish16S"),
         convert_readiness(f3, "ncbi_sra", list(runs_by = "assay", runs_values = "Fish16S")))
  report("seames", "NCBI SRA, only runs not submitted", run_ncbi_sra(sd, sw, associated = "blank_only"),
         convert_readiness(f3, "ncbi_sra", list(associated = "blank_only")))
  report("seames", "ENA runs, one assay", run_ena_run(sd, sw, file.path(DEMO_ROOT, "seames", "ena_sample_receipt.xml"),
                                                    "PRJEB00000", "TESTCENTRE", "NextSeq 2000", assay_name = "Fish16S"),
         convert_readiness(f3, "ena_run", list(receipt = "r", study = "s", center = "c", assay = "Fish16S", instrument = "NextSeq 2000")))
  report("seames", "GBIF (MDT), keeping controls", run_mdt(sd, sw, "Fish16S", f3$runs[1], controls = "keep"), convert_readiness(f3, "mdt"))
  d <- file.path(sd, "seames_eo2"); dir.create(d, showWarnings = FALSE)
  an <- list(list(assay = "Fish16S", run = f3$runs[1], taxonomy = sheet_tsv(sw, "taxaFinal", file.path(d, "t.tsv")),
                  abundance = sheet_tsv(sw, "otuFinal", file.path(d, "o.tsv"))))
  mp <- mapping_from_taxa(sw, "Fish16S", file.path(d, "map.tsv"))
  report("seames", "edna2obis, event core, no eMoF", run_edna2obis_build(sd, sw, an, mp, core_type = "event", emof = "none"),
         convert_readiness(f3, "eo_build", list(mapping = mp)))
  report("seames", "Darwin Core presence, GBIF and OBIS", run_faire2dwc(sd, sw, target = "both", country_code = "AU"),
         convert_readiness(f3, "dwc"))

  # SEA-MES with its dates written as text (7/12/24): edna2obis stops to ask, then runs day first
  dates <- read_faire_sheet(sw, "sampleMetadata")$eventDate
  dates <- dates[nzchar(dates)]
  as_text <- format(as.Date(substr(dates, 1, 10)), "%d/%m/%y")
  tw <- fill_cells(sw, file.path(sd, "seames_text_dates.xlsx"), "sampleMetadata", list(eventDate = as_text))
  f4 <- workbook_facts(tw)
  report("seames~", "edna2obis, text dates, stop", run_edna2obis_build(sd, tw, an, mp), convert_readiness(f4, "eo_build", list(mapping = mp)))
  report("seames~", "edna2obis, text dates, day first", run_edna2obis_build(sd, tw, an, mp, text_dates = "dmy"),
         convert_readiness(f4, "eo_build", list(mapping = mp, text_dates = "dmy")))
}

# ---------------------------------------------------------------- choices among the matched names
# The names the matching changed (R/taxa_review.R), and a person's choice among them, reach the archive:
# eelgrass with a mapping table whose Amphichaeta sannio is a plant namesake, chosen back to the annelid
if ("eelgrass" %in% which) {
  cat("\n== choices among matched names\n")
  ew <- file.path(out, "eelgrass_workbook.xlsx")
  mp <- file.path(sd, "eel_test_mapping.tsv")
  system2(Sys.getenv("FAIRE_PYTHON", "python3"), c("tests/browser/test_mapping.py", ew, mp), stdout = FALSE)
  map <- read_tsv(mp)
  ch <- taxa_changes(map)
  nm <- ch$changes[[which(vapply(ch$changes, `[[`, "", "kind") == "disagrees")]]
  edited <- write_mapping(apply_taxa_choices(map, setNames(list(as.character(nm$candidates[2])), nm$key)), file.path(sd, "eel_chosen.tsv"))
  d <- file.path(sd, "eel_eo3"); dir.create(d, showWarnings = FALSE)
  an <- list(list(assay = "LerayCOI", run = "LerayCOI", taxonomy = sheet_tsv(ew, "taxaFinal", file.path(d, "t.tsv")),
                  abundance = sheet_tsv(ew, "otuFinal", file.path(d, "o.tsv"))))
  kingdom_of <- function(res) {
    occ <- utils::read.csv(res$outputs$occurrence, colClasses = "character", check.names = FALSE)
    unique(occ$kingdom[occ$scientificName == "Amphichaeta sannio"])
  }
  r1 <- run_edna2obis_build(sd, ew, an, mp)
  r2 <- run_edna2obis_build(sd, ew, an, edited)
  k1 <- if (isTRUE(r1$ok)) kingdom_of(r1) else "(stopped)"
  k2 <- if (isTRUE(r2$ok)) kingdom_of(r2) else "(stopped)"
  ok <- identical(k1, "Plantae") && identical(k2, "Animalia")
  cat(sprintf("%-9s %-34s %s  (as matched: %s; with the choice: %s)\n", "eelgrass", "edna2obis uses a choice",
              if (ok) "ok" else "FAILED", paste(k1, collapse = ","), paste(k2, collapse = ",")))
  if (!ok) failures <- failures + 1
  # and no match: the species matched at its genus, Alitta, recorded as incertae sedis instead
  hi <- ch$changes[[which(vapply(ch$changes, `[[`, "", "kind") == "higher")]]
  none <- write_mapping(apply_taxa_choices(map, setNames(list("none"), hi$key)), file.path(sd, "eel_none.tsv"))
  r3 <- run_edna2obis_build(sd, ew, an, none)
  occ <- if (isTRUE(r3$ok)) utils::read.csv(r3$outputs$occurrence, colClasses = "character", check.names = FALSE) else NULL
  got <- if (is.null(occ)) "(stopped)" else unique(occ$scientificName[occ$verbatimIdentification == hi$verbatim])
  ok <- identical(got, "incertae sedis")
  cat(sprintf("%-9s %-34s %s  (%s: %s)\n", "eelgrass", "edna2obis uses 'no match'", if (ok) "ok" else "FAILED",
              hi$lowest, paste(got, collapse = ",")))
  if (!ok) failures <- failures + 1
}

cat(if (failures) sprintf("\n%d readiness verdict(s) did not match the result\n", failures) else "\nAll verdicts matched\n")
quit(status = if (failures) 1 else 0)
