# What a FAIRe workbook holds, for the Convert page, and whether each conversion can run on it.
#
# workbook_facts() reads the workbook once: its assays, runs, sheets and filled fields. The page offers
# these in its fields. convert_readiness() says from them, and from the choices on the form, whether a
# conversion has what it needs: 'ready', 'needs' (with each missing thing and how to add it) or
# 'not_suited' (the conversion is for another kind of study). tests/conversions.R runs every
# conversion on the demonstration workbooks and checks that a conversion said to be ready runs.

empty_facts <- function() list(assays = character(), runs = character(), libs = character(), sheets = character(),
                               run_pairs = NULL, n_libs = 0, n_no_run = 0, sample_fields = character(),
                               run_fields = character(), pm = NULL, smd = NULL, erm = NULL, taxa = list(),
                               assay_type = "", path = NULL)

# projectMetadata as a table of term_name and the value columns (project_level, then one per assay)
read_project_table <- function(path) {
  pm <- tryCatch(as.data.frame(readxl::read_excel(path, "projectMetadata", col_names = FALSE, col_types = "text",
                                                  .name_repair = "minimal")), error = function(e) NULL)
  if (is.null(pm) || !nrow(pm)) return(NULL)
  pm[is.na(pm)] <- ""
  tc <- which(apply(pm, 2, function(x) any(x == "term_name")))[1]
  if (is.na(tc) || tc >= ncol(pm)) return(NULL)
  hr <- which(pm[[tc]] == "term_name")[1]
  out <- pm[-seq_len(hr), c(tc, (tc + 1):ncol(pm)), drop = FALSE]
  names(out) <- c("term", make.unique(ifelse(nzchar(unlist(pm[hr, (tc + 1):ncol(pm)])),
                                             unlist(pm[hr, (tc + 1):ncol(pm)]), "col")))
  out[nzchar(out$term), , drop = FALSE]
}

# A projectMetadata value for an assay: its own column's value, or else project_level's
project_value <- function(facts, term, assay = NULL) {
  pm <- facts$pm
  if (is.null(pm) || !term %in% pm$term) return("")
  row <- pm[which(pm$term == term)[1], -1, drop = FALSE]
  vals <- setNames(trimws(as.character(unlist(row))), names(row))
  if (!is.null(assay) && "assay_name" %in% pm$term) {
    an <- pm[which(pm$term == "assay_name")[1], -1, drop = FALSE]
    an <- setNames(trimws(as.character(unlist(an))), names(an))
    col <- setdiff(names(an)[an == assay], "project_level")
    if (length(col) && nzchar(vals[[col[1]]])) return(vals[[col[1]]])
  }
  if ("project_level" %in% names(vals)) vals[["project_level"]] else ""
}

workbook_facts <- function(wb) {
  if (is.null(wb) || !file.exists(wb)) return(empty_facts())
  sheets <- xlsx_sheets(wb)
  pm <- if ("projectMetadata" %in% sheets) read_project_table(wb) else NULL
  facts <- list(pm = pm)
  # a targeted project lists its assays in project_level as 'A | B'
  assays <- unique(trimws(unlist(strsplit(project_value(facts, "assay_name"), "|", fixed = TRUE))))
  erm <- if ("experimentRunMetadata" %in% sheets) read_faire_sheet(wb, "experimentRunMetadata") else NULL
  smd <- if ("sampleMetadata" %in% sheets) read_faire_sheet(wb, "sampleMetadata") else NULL
  col <- function(d, x) if (!is.null(d) && x %in% names(d)) trimws(d[[x]]) else rep("", if (is.null(d)) 0 else nrow(d))
  # rows with something in them: the sheets keep empty template rows
  if (!is.null(erm)) erm <- erm[nzchar(col(erm, "samp_name")) | nzchar(col(erm, "lib_id")), , drop = FALSE]
  if (!is.null(smd)) smd <- smd[nzchar(col(smd, "samp_name")), , drop = FALSE]
  # each sampleMetadata field's section (row 2): 'User defined' marks your own terms
  sections <- tryCatch({
    top <- as.data.frame(readxl::read_excel(wb, "sampleMetadata", col_names = FALSE, col_types = "text", n_max = 3,
                                            .name_repair = "minimal"))
    top[is.na(top)] <- ""
    setNames(as.character(unlist(top[2, ])), make.unique(as.character(unlist(top[3, ]))))
  }, error = function(e) character())
  runs <- unique(col(erm, "seq_run_id")[nzchar(col(erm, "seq_run_id"))])
  libs <- unique(col(erm, "lib_id")[nzchar(col(erm, "lib_id"))])
  # The libraries (rows of experimentRunMetadata) as assay and run, so a converter that picks them by
  # both (FAIRe2MDT) offers only the runs of the assay chosen, and the page can say when there are none
  run_pairs <- data.frame(assay = col(erm, "assay_name"), run = col(erm, "seq_run_id"), stringsAsFactors = FALSE)
  # the taxonomy sheets' filled columns, for the converters that name taxa from them
  taxa <- list()
  for (s in grep("^taxaFinal", sheets, value = TRUE)) {
    tx <- read_faire_sheet(wb, s)
    if (!is.null(tx)) taxa[[s]] <- names(tx)[vapply(tx, function(v) any(nzchar(trimws(v))), logical(1))]
  }
  type <- tolower(project_value(facts, "assay_type"))
  if (!nzchar(type)) type <- if (is.null(erm) && any(grepl("^(ampData|stdData)", sheets))) "targeted" else "metabarcoding"
  list(assays = assays[nzchar(assays)], runs = runs, libs = libs, sheets = sheets,
       run_pairs = run_pairs, n_libs = nrow(run_pairs), n_no_run = sum(!nzchar(run_pairs$run)),
       sample_fields = if (is.null(smd)) character() else names(smd),
       run_fields = if (is.null(erm)) character() else names(erm),
       pm = pm, smd = smd, erm = erm, taxa = taxa, assay_type = type, sections = sections, path = wb)
}

# ------------------------------------------------------------------------------ instruments

# NCBI's instrument_model values, as faire2ncbi_galaxy.py lists them (NCBI_INSTRUMENTS)
ncbi_instruments <- local({
  cache <- NULL
  function() {
    if (is.null(cache)) {
      src <- tryCatch(readLines(tool_path("faire2ncbi", "faire2ncbi_galaxy.py"), warn = FALSE), error = function(e) character())
      a <- grep("^NCBI_INSTRUMENTS = \\{", src)[1]
      b <- if (is.na(a)) NA else a + which(src[(a + 1):length(src)] == "}")[1]
      block <- if (is.na(b)) "" else paste(src[a:b], collapse = "\n")
      # every quoted string, left to right, less the platform keys (those followed by a colon)
      m <- gregexpr("'[^']*'", block)[[1]]
      strs <- regmatches(block, list(m))[[1]]
      after <- substring(block, m + attr(m, "match.length"), m + attr(m, "match.length"))
      cache <<- gsub("'", "", strs[after != ":"])
    }
    cache
  }
})

# The name a list uses for an instrument value, as faire2ncbi_galaxy.py's clean_instrument does:
# 'Illumina MiSeq [OBI_0002003]' and 'Illumina NextSeq 2000' -> 'NextSeq 2000'. "" when it has none.
instrument_in <- function(value, names) {
  v <- sub("\\s*\\[[A-Za-z]+[_:][0-9]+\\]\\s*$", "", trimws(value %||% ""))
  if (!nzchar(v)) return("")
  prefix <- "^(Illumina|Oxford Nanopore( Technologies)?|ONT|PacBio|Pacific Biosciences|MGI|Thermo Fisher)\\s+"
  for (cand in c(v, sub(prefix, "", v, ignore.case = TRUE), paste("Illumina", v))) {
    hit <- names[tolower(names) == tolower(cand)]
    if (length(hit)) return(hit[1])
  }
  ""
}

# The instrument values the workbook gives: experimentRunMetadata's instrument column, or projectMetadata's
workbook_instruments <- function(facts) {
  v <- if (!is.null(facts$erm) && "instrument" %in% names(facts$erm)) trimws(facts$erm$instrument) else character()
  v <- v[nzchar(v)]
  if (!length(v)) v <- unique(c(project_value(facts, "instrument"),
                                vapply(facts$assays, function(a) project_value(facts, "instrument", a), "")))
  unique(v[nzchar(v)])
}

# ------------------------------------------------------------------------------ readiness

CONVERTERS <- list(
  ncbi_biosample = list(label = "NCBI: BioSample", tab = "NCBI", sequences = TRUE),
  ncbi_sra = list(label = "NCBI: SRA", tab = "NCBI", sequences = TRUE),
  ena_sample = list(label = "ENA: samples", tab = "ENA", sequences = TRUE),
  ena_run = list(label = "ENA: experiments and runs", tab = "ENA", sequences = TRUE),
  mdt = list(label = "GBIF (MDT)", tab = "GBIF (MDT)", sequences = TRUE),
  eo_build = list(label = "OBIS and GBIF (Darwin Core)", tab = "OBIS and GBIF (Darwin Core)", sequences = TRUE),
  dwc = list(label = "GBIF and OBIS (presence and absence)", tab = "GBIF and OBIS (presence and absence)", sequences = FALSE),
  qiime = list(label = "QIIME 2", tab = "QIIME 2", sequences = TRUE)
)

NOT_SUITED <- list(
  ncbi_biosample = "NCBI holds the samples behind sequence reads, and a targeted (qPCR or ddPCR) study has none.",
  ncbi_sra = "the SRA holds sequence reads, and a targeted (qPCR or ddPCR) study has none.",
  ena_sample = "ENA holds the samples behind sequence reads, and a targeted (qPCR or ddPCR) study has none.",
  ena_run = "ENA holds sequence reads, and a targeted (qPCR or ddPCR) study has none.",
  mdt = "GBIF's MDT takes metabarcoding read counts, and a targeted study has detections instead.",
  eo_build = "edna2obis builds records from metabarcoding tables (OTUs and their taxa).",
  qiime = "QIIME 2 analyses sequence reads, and a targeted (qPCR or ddPCR) study has none."
)

# One thing a conversion needs: what is missing, and how to add it. 'form' items are choices on the
# tool's form; the others are in the workbook. 'key' lets the page add a button (run_id).
need <- function(what, fix, form = FALSE, key = "", short = "") list(what = what, fix = fix, form = form, key = key, short = short)

shown <- function(x, n = 5) paste0(paste(head(x, n), collapse = ", "), if (length(x) > n) ", ..." else "")
is_empty <- function(v) if (is.null(v)) TRUE else !nzchar(trimws(as.character(v)))
field_of <- function(d, f) if (!is.null(d) && f %in% names(d)) d[[f]] else rep("", if (is.null(d)) 0 else nrow(d))
sheet_for <- function(facts, base, assay) {
  s <- c(paste0(base, "_", assay), base)
  s[s %in% facts$sheets][1] %||% NA_character_
}

convert_readiness <- function(facts, id, settings = list()) {
  st <- function(name, default) { v <- settings[[name]]; if (is.null(v) || (length(v) == 1 && is.na(v))) default else v }
  needs <- list(); cautions <- character()
  add <- function(...) needs[[length(needs) + 1]] <<- need(...)
  done <- function() list(id = id, status = if (length(needs)) "needs" else "ready", needs = needs, cautions = cautions)
  if (is.null(facts$path)) return(list(id = id, status = "no_workbook", needs = list(), cautions = character()))
  if (facts$assay_type == "targeted" && isTRUE(CONVERTERS[[id]]$sequences))
    return(list(id = id, status = "not_suited", why = NOT_SUITED[[id]], needs = list(), cautions = character()))
  smd <- facts$smd; erm <- facts$erm
  samples <- field_of(smd, "samp_name")
  no_erm <- function() add(short = "an experimentRunMetadata sheet", "No experimentRunMetadata sheet, which lists each sequencing library.",
                           "Build the workbook with the FAIRe mapper (Make a workbook), which adds it, or add the sheet from a FAIRe template.")
  missing_in <- function(field, rows = rep(TRUE, length(samples))) samples[rows & is_empty(field_of(smd, field))]

  if (id == "ncbi_biosample") {
    if (is.null(erm)) no_erm()
    rows <- rep(TRUE, length(samples))
    if (st("associated", "all") == "blank_only" && "biosample_accession" %in% names(smd))
      rows <- is_empty(smd$biosample_accession)
    mand <- list(`*collection_date` = "eventDate", `*depth` = "maximumDepthInMeters", `*env_broad_scale` = "env_broad_scale",
                 `*env_local_scale` = "env_local_scale", `*env_medium` = "env_medium", `*geo_loc_name` = "geo_loc_name",
                 `*lat_lon` = c("decimalLatitude", "decimalLongitude"))
    gaps <- character()
    for (f in names(mand)) {
      empty <- unique(unlist(lapply(mand[[f]], missing_in, rows = rows)))
      if (length(empty)) gaps <- c(gaps, sprintf("%s (%s) for %s: %s", sub("^\\*", "", f), paste(mand[[f]], collapse = " and "),
                                                 plural(length(empty), "sample"), shown(empty)))
    }
    if (length(gaps)) {
      fill <- st("mandatory_fill", "stop")
      if (fill == "stop")
        add(short = "values for empty mandatory fields", paste0("Mandatory BioSample fields are empty: ", paste(gaps, collapse = "; "), "."),
            paste("Fill them in sampleMetadata, or choose a missing-value term under Empty mandatory fields below,",
                  "such as 'not applicable' for a field that does not apply to a control."), form = FALSE)
      else cautions <- c(cautions, sprintf("Empty mandatory fields will be filled with '%s': %s.", fill, paste(gaps, collapse = "; ")))
    }
    # NCBI refuses samples whose attributes are all the same apart from their names. FAIRe2NCBI compares
    # the BioSample fields it maps from the checklist, so your own terms do not tell samples apart unless
    # one is named on the form.
    if (length(samples) > 1) {
      fields <- names(smd)[!names(smd) %in% c("samp_name", "sample_title", "description") &
                             facts$sections[names(smd)] %in% setdiff(unique(facts$sections), c("User defined", NA))]
      dup <- st("duplicates_column", "")
      groups_by <- function(cols) {
        key <- do.call(paste, c(lapply(cols, function(f) trimws(smd[[f]])), sep = "\r"))[rows]
        g <- split(samples[rows], key)
        g[lengths(g) > 1]
      }
      g <- groups_by(c(fields, if (nzchar(dup) && dup %in% names(smd)) dup))
      if (length(g)) {
        # fields that would tell every group apart
        apart <- names(smd)[vapply(names(smd), function(f) {
          v <- trimws(smd[[f]])[rows]; names(v) <- samples[rows]
          !f %in% c("samp_name", "sample_title", "description") && all(vapply(g, function(x) !any(duplicated(v[x])) && all(nzchar(v[x])), logical(1)))
        }, logical(1))]
        add(short = "a field that tells samples apart", sprintf("%s identical BioSample attributes apart from their names, and NCBI will not register them: %s.",
                    if (length(g) == 1) "Two or more samples have" else paste(length(g), "groups of samples have"),
                    paste0(paste(head(vapply(g, paste, "", collapse = " and "), 3), collapse = "; "), if (length(g) > 3) "; ..." else "")),
            paste0("Choose a field that tells them apart under 'Field that tells apart samples with identical attributes' below",
                   if (length(apart)) paste0(", such as ", shown(apart, 3)) else
                     ", or add one (such as a replicate number) to sampleMetadata", "."),
            form = length(apart) > 0)
      }
    }
    return(done())
  }

  if (id == "ncbi_sra") {
    if (is.null(erm)) { no_erm(); return(done()) }
    rows <- rep(TRUE, nrow(erm))
    by <- st("runs_by", "all"); vals <- st("runs_values", character())
    if (by != "all" && length(vals)) rows <- trimws(field_of(erm, c(assay = "assay_name", seq_run = "seq_run_id", lib_id = "lib_id")[[by]])) %in% vals
    if (st("associated", "all") == "blank_only") rows <- rows & is_empty(field_of(erm, "associatedSequences"))
    libs <- ifelse(is_empty(field_of(erm, "lib_id")), field_of(erm, "samp_name"), field_of(erm, "lib_id"))[rows]
    if (!length(libs)) {
      add(short = "runs to submit", if (st("associated", "all") == "blank_only" && any(!is_empty(field_of(erm, "associatedSequences"))))
            "No runs to submit: every run chosen already has an accession number (associatedSequences)."
          else "No runs of experimentRunMetadata match the runs chosen.",
          "Choose other runs under Runs to include, or include runs already submitted.", form = TRUE)
      return(done())
    }
    nofile <- libs[is_empty(field_of(erm, "filename")[rows])]
    if (length(nofile))
      add(short = "read file names", sprintf("%s of %s have no read file name (filename in experimentRunMetadata): %s.", length(nofile),
                  plural(length(libs), "library", "libraries"), shown(nofile)),
          paste("In Make a workbook, e, add a library table (a run report from ENA or the SRA, or a sheet naming each",
                "library's read files) and build the workbook again, or fill filename (and filename2 for paired reads)",
                "in experimentRunMetadata."), key = "filenames")
    files <- unlist(lapply(c("filename", "filename2"), function(f) field_of(erm, f)[rows]))
    files <- files[!is_empty(files)]
    if (any(duplicated(files)))
      add(short = "unique read file names", paste0("These read file names appear more than once: ", shown(unique(files[duplicated(files)])), "."),
          "Give each library its own read files in experimentRunMetadata.")
    if (st("instrument", "from_workbook") == "from_workbook") {
      inst <- workbook_instruments(facts)
      if (!length(inst))
        add(short = "the instrument", "The workbook gives no sequencing instrument.", "Choose it under Sequencing instrument below.", form = TRUE)
      else {
        bad <- inst[!nzchar(vapply(inst, instrument_in, "", names = ncbi_instruments()))]
        if (length(bad))
          add(short = "the instrument", sprintf("The workbook's instrument %s is not one of NCBI's names (it may not give the model).",
                      paste0("'", bad, "'", collapse = ", ")),
              "Choose the instrument under Sequencing instrument below.", form = TRUE)
      }
    }
    if (st("link", "sample_name") == "accessions" && blank(st("accessions", "")))
      add(short = "the accession table", "No BioSample accession table chosen.", "Choose the table NCBI returned for your BioSamples, from Your files.", form = TRUE)
    if (length(libs) && all(!is_empty(field_of(erm, "associatedSequences")[rows])))
      cautions <- c(cautions, "Every run has an accession number (associatedSequences), so the reads are in an archive already.")
    return(done())
  }

  if (id == "ena_sample") {
    if (blank(st("center", ""))) add(short = "a centre name", "No centre name.", "Give the centre name your Webin account is registered with, below.", form = TRUE)
    mand <- list(eventDate = "collection date", decimalLatitude = "latitude", decimalLongitude = "longitude",
                 geo_loc_name = "country or sea", env_broad_scale = "broad-scale environmental context",
                 env_medium = "environmental medium")
    gaps <- character()
    for (f in names(mand)) {
      empty <- missing_in(f)
      if (length(empty)) gaps <- c(gaps, sprintf("%s (%s) for %s: %s", f, mand[[f]], plural(length(empty), "sample"), shown(empty)))
    }
    if (length(gaps))
      add(short = "values for empty mandatory fields", paste0("Mandatory ENA fields are empty: ", paste(gaps, collapse = "; "), "."), "Fill them in sampleMetadata.")
    nodepth <- samples[is_empty(field_of(smd, "minimumDepthInMeters")) & is_empty(field_of(smd, "maximumDepthInMeters"))]
    if (length(nodepth))
      cautions <- c(cautions, sprintf(paste("%s no depth, so FAIRe2ENA writes 0 m, its default for surface samples.",
                                            "If that is wrong, fill minimumDepthInMeters or maximumDepthInMeters in sampleMetadata."),
                                      if (length(nodepth) == length(samples)) "No sample has" else paste(plural(length(nodepth), "sample"), "have")))
    nolocal <- missing_in("env_local_scale")
    if (length(nolocal))
      cautions <- c(cautions, sprintf("%s no env_local_scale, so FAIRe2ENA writes 'marine pelagic zone'. If that is wrong, fill it in sampleMetadata.",
                                      paste(plural(length(nolocal), "sample"), "have")))
    return(done())
  }

  if (id == "ena_run") {
    if (is.null(erm)) { no_erm(); return(done()) }
    if (blank(st("receipt", "")))
      add(short = "ENA's sample receipt", "No ENA sample receipt.", paste("Submit the sample XML (written above) to ENA first, and add the receipt ENA",
                                          "returns to Your files; then choose it below."), form = TRUE)
    if (blank(st("study", ""))) add(short = "a study accession", "No ENA study accession.", "Give the study (project) accession, PRJEB..., below.", form = TRUE)
    if (blank(st("center", ""))) add(short = "a centre name", "No centre name.", "Give the centre name your Webin account is registered with, below.", form = TRUE)
    rows <- rep(TRUE, nrow(erm))
    a <- st("assay", ""); if (nzchar(a)) rows <- trimws(field_of(erm, "assay_name")) == a
    r <- st("seq_runs", character()); if (length(r)) rows <- rows & trimws(field_of(erm, "seq_run_id")) %in% r
    if (!any(rows)) {
      add(short = "runs to submit", "No runs of experimentRunMetadata match the assay and sequencing runs chosen.",
          "Choose another assay or other runs below.", form = TRUE)
      return(done())
    }
    libs <- ifelse(is_empty(field_of(erm, "lib_id")), field_of(erm, "samp_name"), field_of(erm, "lib_id"))
    layout <- vapply(trimws(field_of(erm, "assay_name")), function(x) tolower(project_value(facts, "lib_layout", x)), "")
    paired <- !grepl("single", layout)
    gap <- function(f, which) {
      empty <- libs[rows & which & is_empty(field_of(erm, f))]
      bad <- libs[rows & which & !is_empty(field_of(erm, f)) & !grepl("^[0-9a-fA-F]{32}$", trimws(field_of(erm, f)))]
      list(empty = empty, bad = if (grepl("^checksum", f)) bad else character())
    }
    probs <- character()
    for (f in c("filename", "checksum_filename")) { g <- gap(f, TRUE); if (length(g$empty)) probs <- c(probs, sprintf("%s is empty for %s", f, plural(length(g$empty), "library", "libraries")))
                                                   if (length(g$bad)) probs <- c(probs, sprintf("%s is not an MD5 checksum for %s", f, plural(length(g$bad), "library", "libraries"))) }
    for (f in c("filename2", "checksum_filename2")) { g <- gap(f, paired); if (length(g$empty)) probs <- c(probs, sprintf("%s is empty for %s with paired reads", f, plural(length(g$empty), "library", "libraries")))
                                                      if (length(g$bad)) probs <- c(probs, sprintf("%s is not an MD5 checksum for %s", f, plural(length(g$bad), "library", "libraries"))) }
    if (length(probs))
      add(short = "read files and checksums", paste0("ENA needs each run's read files and their MD5 checksums: ", paste(probs, collapse = "; "), "."),
          paste("Add a library table in Make a workbook, e (ENA's or the SRA's run report gives file names and MD5",
                "checksums) and build the workbook again, or fill them in experimentRunMetadata. For single-end reads,",
                "set lib_layout to 'single end' in projectMetadata."), key = "filenames")
    inst <- workbook_instruments(facts)
    chosen <- st("instrument", "")
    known <- vapply(inst, instrument_in, "", names = ENA_INSTRUMENTS)
    if (length(inst) && nzchar(chosen) && any(nzchar(known)) && !chosen %in% known)
      cautions <- c(cautions, sprintf("The workbook gives the instrument as %s, but %s is chosen below.", shown(inst), chosen))
    return(done())
  }

  if (id == "mdt") {
    if (is.null(erm)) { no_erm(); return(done()) }
    a <- st("assay", facts$assays[1] %||% "")
    p <- facts$run_pairs
    runs <- unique(p$run[nzchar(p$run) & (p$assay == a | !nzchar(p$assay))])
    if (!length(runs))
      add(short = "a run ID", sprintf("No sequencing run ID (seq_run_id) for %s: FAIRe2MDT finds the libraries by assay and run.", if (nzchar(a)) a else "the assay"),
          "Give the run ID in Make a workbook, e (the Sequencing run ID of the OTU table) and build the workbook again, or fill seq_run_id in experimentRunMetadata.",
          key = "run_id")
    if (!isTRUE(st("tables_chosen", NA)) && (is.na(sheet_for(facts, "otuFinal", a)) || is.na(sheet_for(facts, "taxaFinal", a))))
      add(short = "OTU and taxonomy tables", "No OTU and taxonomy tables (otuFinal and taxaFinal sheets).",
          "Add your OTU table in Make a workbook, e, and build the workbook again, or choose the tables from Your files below.")
    tg <- project_value(facts, "target_gene", a)
    known <- tryCatch(utils::read.delim(tool_path("faire2mdt", "mdt_target_gene.tsv"), colClasses = "character")$faire_target_gene,
                      error = function(e) character())
    if (!nzchar(tg)) cautions <- c(cautions, "projectMetadata gives no target_gene: choose the marker in MDT's mapping step.")
    else if (length(known) && !tolower(tg) %in% tolower(known))
      cautions <- c(cautions, sprintf("target_gene '%s' is not one MDT knows: check the marker in MDT's mapping step.", tg))
    return(done())
  }

  if (id == "eo_build") {
    if (!length(facts$assays)) add(short = "an assay name", "projectMetadata names no assay (assay_name).", "Fill assay_name in projectMetadata.")
    chosen <- st("tables_chosen", NA)
    for (a in facts$assays) {
      tx <- sheet_for(facts, "taxaFinal", a); otu <- sheet_for(facts, "otuFinal", a)
      if (!isTRUE(chosen) && (is.na(tx) || is.na(otu)))
        add(short = "taxonomy and abundance tables", sprintf("No taxonomy and abundance tables for %s (taxaFinal and otuFinal sheets).", a),
            "Add your OTU and taxonomy tables in Make a workbook, e, and build the workbook again, or choose them from Your files below.")
      else if (!is.na(tx)) {
        filled <- facts$taxa[[tx]] %||% character()
        if (!any(c("verbatimIdentification", "kingdom", "phylum", "class", "order", "family", "genus", "scientificName") %in% filled))
          add(short = "named taxa", sprintf("The %s sheet names no taxa (no verbatimIdentification, scientificName or rank columns filled).", tx),
              "Add the taxonomy table in Make a workbook, e, and build the workbook again.")
      }
    }
    if (st("taxa_source", "mapping") == "mapping" && blank(st("mapping", "")))
      add(short = "matched names", "No mapping table of matched names.", paste("Run 1. Match taxa (it needs internet access), check the matches, then build;",
                                                       "or choose a mapping table made earlier."), form = TRUE)
    dates <- trimws(field_of(smd, "eventDate")); dates <- dates[nzchar(dates)]
    text <- dates[!grepl("^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?([T ][0-9:.]+(Z|[+-][0-9:]+)?)?(/.*)?$", dates)]
    if (length(text) && st("text_dates", "stop") == "stop")
      add(short = "a date order", sprintf("eventDate has %s that are not in ISO 8601 form, such as %s.", plural(length(text), "value"), shown(unique(text), 2)),
          "Choose day first or month first under Text dates below, or write the dates as YYYY-MM-DD in sampleMetadata.", form = TRUE)
    nocoord <- samples[is_empty(field_of(smd, "decimalLatitude")) | is_empty(field_of(smd, "decimalLongitude"))]
    if (length(nocoord))
      cautions <- c(cautions, sprintf("%s no coordinates (decimalLatitude and decimalLongitude): OBIS needs them for each record.",
                                      paste(plural(length(nocoord), "sample"), "have")))
    return(done())
  }

  if (id == "dwc") {
    assays <- st("assays", character()); if (!length(assays)) assays <- facts$assays
    if (!length(facts$assays)) add(short = "an assay name", "projectMetadata names no assay (assay_name).", "Fill assay_name in projectMetadata.")
    for (a in assays) {
      if (facts$assay_type == "targeted") {
        det <- c(paste0("detected_notDetected_", a), if (length(facts$assays) == 1) "detected_notDetected")
        has_det <- any(vapply(det, function(f) any(!is_empty(field_of(smd, f))), logical(1)))
        if (!has_det && !any(grepl("^ampData", facts$sheets)))
          add(short = "detections", sprintf("No detections for %s (detected_notDetected_%s in sampleMetadata, or an ampData sheet).", a, a),
              "Add your qPCR or ddPCR results in Make a workbook, e, and build the workbook again.")
        if (!nzchar(project_value(facts, "targetTaxonomicAssay", a)))
          add(short = "a target taxon", sprintf("targetTaxonomicAssay is empty for %s: it names the taxon each record is about.", a),
              "Fill it in projectMetadata (in Make a workbook, d, or in the workbook).")
      } else if (is.na(sheet_for(facts, "otuFinal", a)) || is.na(sheet_for(facts, "taxaFinal", a)))
        add(short = "OTU and taxonomy tables", sprintf("No otuFinal and taxaFinal sheets for %s.", a),
            "Add your OTU and taxonomy tables in Make a workbook, e, and build the workbook again.")
    }
    return(done())
  }

  if (id == "qiime") {
    if (is.null(erm)) { no_erm(); return(done()) }
    col <- st("sample_col", "lib_id")
    empty <- which(is_empty(field_of(erm, col)))
    if (length(empty))
      add(short = "sample IDs", sprintf("%s of %s rows of experimentRunMetadata have no %s, the QIIME 2 sample ID chosen below.", length(empty), nrow(erm), col),
          sprintf("Choose %s as the sample ID below, or fill %s.", setdiff(c("lib_id", "samp_name"), col), col), form = TRUE)
    if (isTRUE(st("manifests", TRUE))) {
      nofile <- which(is_empty(field_of(erm, "filename")))
      if (length(nofile))
        add(short = "read file names, or metadata only", sprintf("%s of %s libraries have no read file name (filename), which the manifest files list.", length(nofile), nrow(erm)),
            paste("Choose 'No, metadata only' below, or add a library table in Make a workbook, e (a run report, or a sheet",
                  "naming each library's read files) and build the workbook again."), key = "filenames")
    }
    if (length(facts$assays) > 1) {
      key <- vapply(facts$assays, function(a) paste(project_value(facts, "target_gene", a), project_value(facts, "target_subfragment", a)), "")
      if (any(duplicated(key)))
        add(short = "a target_subfragment for each assay", sprintf("Assays %s share a target_gene and target_subfragment, so their QIIME 2 files would have the same names.",
                    shown(facts$assays[key %in% key[duplicated(key)]])),
            "Give each assay its own target_subfragment in projectMetadata.")
    }
    if (isTRUE(st("suffix", FALSE))) {
      sc <- st("suffix_col", "seq_run_id")
      if (any(is_empty(field_of(erm, sc))))
        add(short = "a suffix column", sprintf("Some rows of experimentRunMetadata have no %s, the column the suffix is taken from.", sc),
            sprintf("Fill %s, or choose another column below.", sc), form = TRUE)
    }
    return(done())
  }
  done()
}

# A short phrase for the readiness of a conversion: 'Ready', 'Needs: ...' or 'Not for this study'
readiness_phrase <- function(r) {
  switch(r$status,
         ready = if (length(r$cautions)) "Ready, with a note" else "Ready",
         needs = {
           short <- function(form) unique(vapply(Filter(function(n) n$form == form, r$needs), `[[`, "", "short"))
           and <- function(x) if (length(x) > 1) paste(paste(head(x, -1), collapse = ", "), "and", tail(x, 1)) else x
           wb <- short(FALSE); fm <- short(TRUE)
           paste0("Needs ", paste(c(if (length(wb)) and(wb), if (length(fm)) paste(and(fm), "(on its form)")), collapse = "; "))
         },
         not_suited = "Not for a targeted study",
         no_workbook = "Choose a workbook",
         "")
}
