# One function per Galaxy tool. Each builds the same command line as the tool's XML wrapper
# (tools/<tool>/<tool>.xml) and runs it in a new folder in the session.

galaxy_ext <- function(path) {
  e <- tolower(tools::file_ext(path))
  if (e %in% c("xlsx", "xlsm", "xls")) return("xlsx")
  if (e == "csv") return("csv")
  if (e %in% c("tsv", "tab", "tabular")) return("tabular")
  if (e %in% c("json")) return("json")
  if (e %in% c("yaml", "yml")) return("yaml")
  "txt"
}

split_list <- function(x) {
  x <- trimws(unlist(strsplit(paste(x, collapse = ","), ",")))
  x[nzchar(x) & x != "None"]
}

blank <- function(x) is.null(x) || length(x) == 0 || all(!nzchar(trimws(as.character(x))))

checklist <- function(tool = "faire_mapper") tool_path(tool, "checklist", "FAIRe_checklist_v1.0.2.xlsx")

# ---------------------------------------------------------------- FAIRe-ator

run_faireator <- function(session_dir, project_id, assay_type, assay_name, sample_type, req_lev,
                          project_fields = "", sample_fields = "") {
  d <- new_run_dir(session_dir, "faireator")
  for (f in c("FAIRe_checklist_v1.0.2.xlsx", "FAIRe_checklist_v1.0.2_FULLtemplate.xlsx"))
    file.copy(tool_path("faireator", "checklist", f), d)
  rvec <- function(v) paste0("c(", paste0("'", gsub("'", "", v), "'", collapse = ", "), ")")
  # As the wrapper: upstream crashes when 'other' is combined with several targeted assays, and
  # listing all seven sample types gives the same fields.
  if ("other" %in% sample_type)
    sample_type <- c("Water", "Soil", "Sediment", "Air", "HostAssociated", "MicrobialMatBiofilm", "SymbiontAssociated")
  call <- c(
    sprintf("suppressPackageStartupMessages(source('%s'))", gsub("\\\\", "/", tool_path("faireator", "FAIReator.R"))),
    "suppressPackageStartupMessages(FAIReator(",
    sprintf("  req_lev = %s,", rvec(c("M", req_lev))),
    sprintf("  sample_type = %s,", rvec(sample_type)),
    sprintf("  assay_type = '%s',", assay_type),
    sprintf("  project_id = '%s',", gsub("'", "", project_id)),
    sprintf("  assay_name = %s", rvec(split_list(assay_name))),
    if (!blank(project_fields)) sprintf("  , projectMetadata_user = %s", rvec(split_list(project_fields))),
    if (!blank(sample_fields)) sprintf("  , sampleMetadata_user = %s", rvec(split_list(sample_fields))),
    "))")
  writeLines(call, file.path(d, "faireator_call.R"))
  s <- run_rscript("faireator_call.R", character(), d)
  made <- file.path(d, paste0("template_", project_id), paste0(project_id, ".xlsx"))
  out <- file.path(d, paste0(project_id, "_FAIRe_template.xlsx"))
  if (file.exists(made)) file.copy(made, out)
  run_result("faireator", "FAIRe-ator", d, list(s), list(template = out))
}

# ---------------------------------------------------------------- FAIRe mapper

run_identify <- function(session_dir, files) {
  d <- new_run_dir(session_dir, "identify")
  args <- c(tool_path("faire_mapper", "faire_mapper_identify.py"), "--checklist", checklist())
  for (nm in names(files)) args <- c(args, "--file", files[[nm]], "--name", nm, "--format", galaxy_ext(nm))
  args <- c(args, "-o", "identify_report.tsv")
  s <- run_python(args[1], args[-1], d)
  run_result("identify", "FAIRe mapper: identify your files", d, list(s),
             list(report = file.path(d, "identify_report.tsv")))
}

table_args <- function(table, sheet, header_row) {
  c(table, if (!blank(sheet)) c("--sheet", sheet), "--header_row", as.integer(header_row %||% 1))
}

run_profile <- function(session_dir, table, sheet = "", header_row = 1) {
  d <- new_run_dir(session_dir, "profile")
  s <- run_python(tool_path("faire_mapper", "faire_mapper.py"),
                  c("profile", table_args(table, sheet, header_row), "--output", "profile.tsv"), d)
  run_result("profile", "FAIRe mapper: profile columns", d, list(s), list(profile = file.path(d, "profile.tsv")))
}

run_map <- function(session_dir, table, sheet = "", header_row = 1, assay_type = "metabarcoding",
                    sample_types = character(), responses = NULL, dictionary = NULL, dictionary_sheet = "",
                    shortlist = 5, shortlist_close = 10, other_terms = TRUE, table_name = basename(table),
                    label = "FAIRe mapper: propose mapping") {
  d <- new_run_dir(session_dir, if (is.null(responses)) "propose_mapping" else "reviewed_mapping")
  args <- c("map", table_args(table, sheet, header_row), "--checklist", checklist(),
            if (assay_type != "any") c("--assay_type", assay_type),
            if (length(sample_types)) c("--sample_types", paste(sample_types, collapse = ",")),
            if (!is.null(responses)) c("--responses", responses),
            if (!is.null(dictionary)) c("--dictionary", dictionary,
                                        if (!blank(dictionary_sheet)) c("--dictionary_sheet", dictionary_sheet)),
            "--shortlist", shortlist, "--shortlist_close", shortlist_close,
            if (!other_terms) "--no_other_terms", "--table_name", table_name, "--outdir", "out")
  s <- run_python(tool_path("faire_mapper", "faire_mapper.py"), args, d)
  o <- function(f) file.path(d, "out", f)
  run_result("map", label, d, list(s),
             list(report = o("mapping_report.tsv"), crosswalk = o("crosswalk.sssom.tsv"),
                  missing = o("missing_mandatory.tsv"), requests = o("adjudication_requests.json"),
                  summary = o("summary.json"), checks = o("review_list.tsv"), review_sheet = o("review_sheet.xlsx"),
                  responses = responses))
}

# The model step. The key goes to the tool through the environment only, as in Galaxy, and is
# never written to disk.
run_model <- function(session_dir, requests, api = "anthropic", model = "", api_url = "", key = "",
                      preview = FALSE) {
  d <- new_run_dir(session_dir, "model")
  env <- character()
  if (nzchar(key)) env[[if (api == "openai") "OPENAI_API_KEY" else "ANTHROPIC_API_KEY"]] <- key
  # --model with no name takes the script's default model
  args <- c(requests, "-o", "answers.json", "--log", "answer_log.tsv",
            "--model", if (nzchar(model)) model, "--api", api,
            if (nzchar(api_url)) c("--api_url", api_url),
            if (preview) "--dry_run")
  s <- run_python(tool_path("faire_mapper", "faire_mapper_adjudicate.py"), args, d, env = env)
  run_result("model", "FAIRe mapper: ask a language model", d, list(s),
             list(answers = file.path(d, "answers.json"), log = file.path(d, "answer_log.tsv")))
}

run_primers <- function(session_dir, mode = "text", texts = character(), names_text = "", gene = "",
                        source = "bundled", own = NULL) {
  d <- new_run_dir(session_dir, "find_primers")
  if (mode == "text") {
    args <- c("text", texts)
  } else {
    writeLines(names_text, file.path(d, "queries.txt"))
    args <- c("lookup", "--queries_file", "queries.txt", if (!blank(gene)) c("--gene", gene))
  }
  if (source != "bundled" && !is.null(own)) {
    args <- c(args, "--primers", own, "--primers_label", gsub("[^A-Za-z0-9._ ()-]", "_", basename(own)))
    if (source == "own") args <- c(args, "--no_bundled")
  }
  args <- c(args, "--output", "primer_candidates.tsv")
  s <- run_python(tool_path("faire_mapper", "faire_primers.py"), args, d)
  run_result("primers", "FAIRe mapper: find primers", d, list(s),
             list(candidates = file.path(d, "primer_candidates.tsv")))
}

# FAIRe mapper: find method details. texts are the methods files, labels the names the person knows them by.
run_method_details <- function(session_dir, texts, labels = basename(texts), assay_names = "") {
  d <- new_run_dir(session_dir, "method_details")
  args <- c(texts, as.vector(rbind("--label", gsub("[^A-Za-z0-9._ ()-]", "_", labels))),
            "--checklist", checklist(), "--assay_type", "metabarcoding",
            if (!blank(assay_names)) c("--assay_names", assay_names),
            "--output", "method_details.tsv", "--review_sheet", "method_details_review_sheet.xlsx")
  s <- run_python(tool_path("faire_mapper", "faire_method_details.py"), args, d)
  run_result("method_details", "FAIRe mapper: find method details", d, list(s),
             list(proposals = file.path(d, "method_details.tsv"),
                  review_sheet = file.path(d, "method_details_review_sheet.xlsx")))
}

# The values kept in a review sheet from find method details: Accept gives the proposed value, Change or a
# value of the person's own gives theirs, and Reject or no decision leaves the row out.
read_method_review <- function(path) {
  r <- as.data.frame(readxl::read_excel(path, sheet = "Method details", col_types = "text"), check.names = FALSE)
  r[is.na(r)] <- ""
  dec <- tolower(trimws(r[["Reviewer's decision"]]))
  yours <- trimws(r[["Your value"]])
  value <- ifelse(dec == "accept", r[["Proposed value"]],
                  ifelse(dec != "reject" & nzchar(yours), yours, ""))
  keep <- nzchar(trimws(value)) & dec != "reject"
  data.frame(term = r[["FAIRe term"]][keep], value = value[keep],
             assay = if ("Assay" %in% names(r)) r[["Assay"]][keep] else rep("", sum(keep)), stringsAsFactors = FALSE)
}

# otu_tables and library_tables are lists of lists, one per table, with the wrapper's fields.
run_apply <- function(session_dir, table, sheet, header_row, crosswalk, assay_type, sample_types, project_id,
                      assay_name = "", country = "", utc_offset = "", date_order = "stop", include_review = FALSE,
                      project_values = NULL, req_lev = c("HR", "R", "O"), drop_unmapped = FALSE,
                      otu_tables = list(), library_tables = list(), table_name = basename(table)) {
  d <- new_run_dir(session_dir, "apply_mapping")
  ck <- tool_path("faire_mapper", "checklist")
  args <- c(table_args(table, sheet, header_row), "--crosswalk", crosswalk,
            "--checklist", file.path(ck, "FAIRe_checklist_v1.0.2.xlsx"),
            "--template", file.path(ck, "FAIRe_checklist_v1.0.2_FULLtemplate.xlsx"),
            "--assay_type", assay_type,
            if (length(sample_types)) c("--sample_types", paste(sample_types, collapse = ",")),
            "--project_id", project_id,
            if (!blank(assay_name)) c("--assay_name", assay_name),
            if (!blank(country)) c("--country", country),
            if (!blank(utc_offset)) paste0("--utc_offset=", trimws(utc_offset)),
            "--date_order", date_order,
            if (include_review) "--include_review",
            if (!is.null(project_values)) c("--project_values", project_values),
            "--req_lev", paste(c("M", req_lev), collapse = ","),
            if (drop_unmapped) "--drop_unmapped")
  for (o in otu_tables) {
    args <- c(args, "--otu", o$path, "--otu_name", o$name, "--otu_sheet", o$sheet %||% "",
              "--otu_assay", o$assay %||% "", "--otu_run", o$run %||% "",
              "--otu_assay_column", o$assay_column %||% "", "--otu_curated_column", o$curated_column %||% "",
              "--otu_lineage", o$lineage %||% "", "--otu_stage", o$stage %||% "final",
              "--otu_layout", o$layout %||% "detect",
              "--otu_sequences", o$sequences %||% "",
              "--otu_sequences_name", if (is.null(o$sequences)) "" else basename(o$sequences),
              "--taxa", o$taxa %||% "", "--taxa_sheet", if (is.null(o$taxa)) "" else (o$taxa_sheet %||% ""))
  }
  for (l in library_tables) {
    args <- c(args, "--library", l$path, "--library_name", l$name, "--library_sheet", l$sheet %||% "",
              "--library_assay", l$assay %||% "", "--library_filter", l$filter %||% "",
              "--library_run", l$run %||% "")
  }
  args <- c(args, "--table_name", table_name, "--crosswalk_name", basename(crosswalk),
            "--output", "faire.xlsx", "--log", "apply_mapping_log.txt")
  s <- run_python(tool_path("faire_mapper", "faire_mapper_apply.py"), args, d)
  wb <- file.path(d, paste0(project_id, "_FAIRe.xlsx"))
  if (file.exists(file.path(d, "faire.xlsx"))) file.copy(file.path(d, "faire.xlsx"), wb)
  run_result("apply", "FAIRe mapper: apply mapping", d, list(s),
             list(workbook = wb, log = file.path(d, "apply_mapping_log.txt")))
}

# ---------------------------------------------------------------- FAIRe-fier

run_fairefier <- function(session_dir, workbook, checklist_version = "auto", strict = FALSE) {
  d <- new_run_dir(session_dir, "fairefier")
  file.copy(workbook, file.path(d, "input.xlsx"))
  dir.create(file.path(d, "out"))
  s <- run_python(tool_path("fairefier", "fairefier_cli.py"),
                  c("input.xlsx", "--outdir", "out", "--checklist_dir", tool_path("fairefier", "checklist"),
                    "--checklist_version", checklist_version, if (strict) "--strict"), d)
  o <- function(f) file.path(d, "out", f)
  run_result("fairefier", "FAIRe-fier", d, list(s),
             list(summary = o("fairefier_summary.json"), issues = o("fairefier_issues.tsv"),
                  warn_error = o("fairefier_warn_error.xlsx"), metadata = o("fairefier_metadata.xlsx")))
}

# ---------------------------------------------------------------- sequence archives

link_input <- function(d, workbook) {
  file.copy(workbook, file.path(d, "input.xlsx"), overwrite = TRUE)
  "input.xlsx"
}

run_ncbi_biosample <- function(session_dir, workbook, organism, bioproject = "", mandatory_fill = "stop",
                               associated = "all", duplicates_column = "", convert_dates = TRUE,
                               mixs_units = TRUE, sample_title = "default", title_columns = "",
                               extra_columns = "all", exclude_columns = "") {
  d <- new_run_dir(session_dir, "ncbi_biosample")
  args <- c("biosample", "--input_file", link_input(d, workbook),
            if (!blank(bioproject)) c("--bioproject", bioproject),
            "--organism", organism, "--mandatory_fill", mandatory_fill, "--associated", associated,
            if (!blank(duplicates_column)) c("--duplicates_column", duplicates_column),
            if (!convert_dates) "--no_date_conversion", if (!mixs_units) "--no_mixs_units",
            "--sample_title", sample_title, if (sample_title == "custom") c("--title_columns", title_columns),
            "--extra_columns", extra_columns, if (extra_columns == "except") c("--exclude_columns", exclude_columns),
            "--output", "biosample.tsv", "--config_out", "config.yaml")
  s <- run_python(tool_path("faire2ncbi", "faire2ncbi_galaxy.py"), args, d)
  run_result("ncbi_biosample", "FAIRe2NCBI: BioSample", d, list(s),
             list(biosample_table = file.path(d, "biosample.tsv"), config = file.path(d, "config.yaml")))
}

run_ncbi_sra <- function(session_dir, workbook, runs_by = "all", runs_values = "", associated = "all",
                         instrument_model = "from_workbook", accessions = NULL, organism = "marine metagenome") {
  d <- new_run_dir(session_dir, "ncbi_sra")
  args <- c("sra", "--input_file", link_input(d, workbook), "--runs_by", runs_by,
            if (runs_by != "all") c("--runs_values", runs_values), "--associated", associated,
            if (instrument_model != "from_workbook") c("--instrument_model", instrument_model),
            if (!is.null(accessions)) c("--accessions", accessions),
            "--organism", organism, "--output", "sra.tsv", "--config_out", "config.yaml")
  s <- run_python(tool_path("faire2ncbi", "faire2ncbi_galaxy.py"), args, d)
  run_result("ncbi_sra", "FAIRe2NCBI: SRA", d, list(s),
             list(sra_table = file.path(d, "sra.tsv"), config = file.path(d, "config.yaml")))
}

run_ena_sample <- function(session_dir, workbook, center_name, taxon_id, convert_dates = TRUE) {
  d <- new_run_dir(session_dir, "ena_samples")
  args <- c("sample", "--input_file", link_input(d, workbook), "--center_name", center_name,
            "--taxon_id", taxon_id, if (!convert_dates) "--no_date_conversion",
            "--output_file", "samples.xml", "--submission_file", "submission.xml")
  s <- run_python(tool_path("faire2ena", "faire2ena_galaxy.py"), args, d)
  run_result("ena_sample", "FAIRe2ENA: samples", d, list(s),
             list(samples_xml = file.path(d, "samples.xml"), submission_xml = file.path(d, "submission.xml")))
}

run_ena_run <- function(session_dir, workbook, receipt, study_accession, center_name, instrument_model,
                        assay_name = "", add_assay_suffix = TRUE, seq_runs = "", ftp_subdir = "") {
  d <- new_run_dir(session_dir, "ena_runs")
  args <- c("run", "--input_file", link_input(d, workbook), "--receipt_file", receipt,
            "--study_accession", study_accession, "--center_name", center_name,
            "--instrument_model", instrument_model,
            if (!blank(assay_name)) c("--assay_name", assay_name, if (add_assay_suffix) "--add_assay_suffix"),
            if (!blank(seq_runs)) c("--seq_run_id", seq_runs),
            if (!blank(ftp_subdir)) c("--ftp_subdir", ftp_subdir),
            "--experiment_output", "experiments.xml", "--run_output", "runs.xml",
            "--submission_file", "submission.xml")
  s <- run_python(tool_path("faire2ena", "faire2ena_galaxy.py"), args, d)
  run_result("ena_run", "FAIRe2ENA: experiments and runs", d, list(s),
             list(experiments_xml = file.path(d, "experiments.xml"), runs_xml = file.path(d, "runs.xml"),
                  submission_xml = file.path(d, "submission.xml")))
}

# ---------------------------------------------------------------- analysis and biodiversity databases

run_qiime <- function(session_dir, workbook, sample_name_column = "lib_id", write_manifests = TRUE,
                      sequences_folder = "/path/to/sequences", use_suffix = FALSE, column_suffix = "seq_run_id",
                      direction_suffix = "left", num_chars_suffix = 20, delimiter_suffix = "_") {
  d <- new_run_dir(session_dir, "faire2qiime")
  link_input(d, workbook)
  s1 <- run_python(tool_path("faire2qiime", "normalise_faire.py"),
                   c("input.xlsx", "normalised.xlsx", "--check_column", sample_name_column,
                     if (use_suffix) c("--check_column", column_suffix),
                     if (write_manifests) c("--check_filled", "filename")), d)
  steps <- list(s1)
  if (s1$status == 0) {
    dir.create(file.path(d, "out"))
    s2 <- run_python(tool_path("faire2qiime", "faire2qiime_by_assay.py"),
                     c(tool_path("faire2qiime", "faire2qiime.py"), "normalised.xlsx", "out", "--",
                       "--sample_name_column", sample_name_column,
                       "--absolute_path_sequences", if (write_manifests) sequences_folder else "/not/used",
                       if (use_suffix) c("--column_suffix", column_suffix, "--direction_suffix", direction_suffix,
                                         "--num_chars_suffix", num_chars_suffix,
                                         "--delimiter_suffix", delimiter_suffix)), d)
    keep <- strsplit(s2$output, "\n")[[1]]
    keep <- keep[!grepl("pyfiglet", keep) & !grepl("^=*$", keep) & !grepl("^ *$", keep)]
    s2$output <- paste(keep, collapse = "\n")
    gen <- regmatches(s2$output, gregexpr("Generated [a-z]* file .*", s2$output))[[1]]
    if (any(duplicated(gen))) {
      s2$status <- 1
      s2$output <- paste0(s2$output, "\nERROR: two or more assays share the same target_gene and target_subfragment, ",
                          "so FAIRe2QIIME wrote these files more than once. Give each assay its own ",
                          "target_subfragment in projectMetadata.")
    }
    steps <- c(steps, list(s2))
  }
  files <- list.files(file.path(d, "out"), recursive = TRUE, full.names = TRUE)
  if (!write_manifests) files <- files[!grepl("manifest", basename(files), ignore.case = TRUE)]
  outs <- setNames(as.list(files), basename(files))
  run_result("qiime", "FAIRe2QIIME", d, steps, outs)
}

run_mdt <- function(session_dir, workbook, assay, seq_run, otu = workbook, otu_sheet = "otuFinal",
                    taxa = workbook, taxa_sheet = "taxaFinal", controls = "omit") {
  d <- new_run_dir(session_dir, "faire2mdt")
  out <- file.path(d, sprintf("MDT_%s_%s.xlsx", assay, seq_run))
  args <- c("--upstream", tool_path("faire2mdt", "FAIRe2MDT.R"),
            "--target_genes", tool_path("faire2mdt", "mdt_target_gene.tsv"),
            "--workbook", workbook, "--assay", assay, "--seq_run", seq_run,
            "--otu", otu, "--otu_format", galaxy_ext(otu), "--otu_sheet", otu_sheet,
            "--taxa", taxa, "--taxa_format", galaxy_ext(taxa), "--taxa_sheet", taxa_sheet,
            "--controls", controls, "--output", out, "--log", "faire2mdt_log.txt")
  s <- run_rscript(tool_path("faire2mdt", "faire2mdt_galaxy.R"), args, d)
  if (file.exists(file.path(d, "faire2mdt_log.txt")))
    s$output <- paste(s$output, paste(readLines(file.path(d, "faire2mdt_log.txt"), warn = FALSE), collapse = "\n"),
                      sep = "\n")
  run_result("mdt", "FAIRe2MDT", d, list(s), list(mdt_workbook = out))
}

# edna2obis reads its settings from the JSON file Galaxy writes for the form; the app writes the
# same file. Datasets are given as {"source_path": ..., "ext": ...}.
dataset <- function(path) if (is.null(path)) NULL else list(source_path = normalizePath(path), ext = galaxy_ext(path))

run_edna2obis_match <- function(session_dir, analyses, api = "WoRMS", worms_all = FALSE, mapping_format = "tabular") {
  d <- new_run_dir(session_dir, "edna2obis_match")
  form <- list(
    analyses = lapply(analyses, function(a) list(assay_name = a$assay, taxonomy = dataset(a$taxonomy),
                                                 skip_species = isTRUE(a$skip_species))),
    api = if (api == "WoRMS") list(api_select = "WoRMS", worms_return_all_matches = worms_all,
                                   worms_advanced = list(worms_min_ranks_matched = 1, n_proc = 4))
          else list(api_select = "GBIF", gbif_advanced = list(gbif_match_limit = 3, n_proc = 4)),
    mapping_format = mapping_format)
  jsonlite::write_json(form, file.path(d, "form.json"), auto_unbox = TRUE, null = "null", pretty = TRUE)
  ext <- if (mapping_format == "xlsx") "xlsx" else "tsv"
  s <- run_python(tool_path("edna2obis", "edna2obis_galaxy.py"),
                  c("match", "--form", "form.json", "--mapping_out", paste0("taxa_mapping.", ext)), d)
  run_result("edna2obis_match", "edna2obis: match taxa", d, list(s),
             list(mapping = file.path(d, paste0("taxa_mapping.", ext))))
}

run_edna2obis_build <- function(session_dir, workbook, analyses, mapping = NULL, api = "WoRMS",
                                text_dates = "stop", na_text = "not_provided", control_column = "samp_category",
                                control_values = "negative control, positive control, PCR standard",
                                location_fields = "line_id, station_id", core_type = "occurrence",
                                emof = "default", eml = list(select = "none")) {
  d <- new_run_dir(session_dir, "edna2obis_build")
  taxa <- if (!is.null(mapping)) list(source = "mapping", mapping_file = dataset(mapping))
          else list(source = "api", api = if (api == "WoRMS") list(api_select = "WoRMS", worms_return_all_matches = FALSE,
                                                                   worms_advanced = list(worms_min_ranks_matched = 1, n_proc = 4))
                                       else list(api_select = "GBIF", gbif_advanced = list(gbif_match_limit = 3, n_proc = 4)))
  eml_form <- if (eml$select == "form") c(list(eml_select = "form"), eml[setdiff(names(eml), "select")])
              else list(eml_select = "none")
  form <- list(
    input_file = dataset(workbook), text_dates = text_dates, na_text = na_text,
    analyses = lapply(analyses, function(a) list(assay_name = a$assay, run_name = a$run %||% "",
                                                 taxonomy = dataset(a$taxonomy), abundance = dataset(a$abundance),
                                                 skip_species = isTRUE(a$skip_species))),
    taxa = taxa,
    samples = list(control_column = control_column, control_values = control_values, location_fields = location_fields),
    core_type = core_type, emof = list(emof_select = emof), eml = eml_form)
  jsonlite::write_json(form, file.path(d, "form.json"), auto_unbox = TRUE, null = "null", pretty = TRUE)
  s <- run_python(tool_path("edna2obis", "edna2obis_galaxy.py"), c("build", "--form", "form.json", "--outputs", "outputs"), d)
  o <- function(f) file.path(d, "outputs", f)
  run_result("edna2obis_build", "edna2obis: build Darwin Core tables", d, list(s),
             list(archive = o("dwca.zip"), occurrence = o("occurrence_core.csv"),
                  dna_derived = o("dna_derived_extension.csv"), emof = o("emof.csv"), event_core = o("event_core.csv"),
                  eml = o("eml.xml"), taxa_mapping = o("taxa_mapping.tsv"), report = o("report.html"),
                  config = o("config.yaml")))
}
