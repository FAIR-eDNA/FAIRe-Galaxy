# Galaxy driver for FAIRe2MDT.R (https://github.com/FAIR-eDNA/FAIRe2MDT).
# Wrapper code: MIT licence (see LICENSE). FAIRe2MDT.R is copied unchanged.
#
# FAIRe2MDT.R starts with a section the user edits (working directory, assay name, sequencing run
# and input files), followed by the conversion code from the line "# Run the below code". This
# driver replaces the user section: it reads the Galaxy inputs into the same five tables, checks
# them, then runs the conversion code unchanged and copies the workbook it writes to the output.
#
# Differences from running the script by hand:
# - Runs are selected by exact assay and sequencing run names (ignoring case), and by names that
#   differ only in punctuation or case if there is no exact match. Upstream uses grepl, which also
#   selects names that contain the given name (COILeray picks COILeray2, run1 picks run10).
# - Cells are read one by one, so Excel dates stay dates (2024-03-05, not 45356) and numbers keep
#   the digits shown in Excel (105.70852, not 105.70851999999999).
# - Problems that would stop the script part way, or give an empty sheet, are reported in plain
#   words before the conversion starts.
# - Control samples are left out, as GBIF does not want them (--controls keep keeps them).
#
# Usage: Rscript faire2mdt_galaxy.R --upstream FAIRe2MDT.R --workbook W.xlsx --assay A --seq_run R
#          --otu OTU --otu_format xlsx|tabular|csv --otu_sheet S --taxa TAXA --taxa_format F
#          --taxa_sheet S [--controls omit|keep] --output OUT.xlsx --log LOG.txt

suppressPackageStartupMessages({
  library(readxl)
  library(openxlsx)
  library(dplyr)
  library(tibble)
})

log_lines <- character(0)
say <- function(...) {
  line <- paste0(...)
  log_lines <<- c(log_lines, line)
  cat(line, "\n", sep = "")
}
write_log <- function() {
  if (!is.null(opt$log)) writeLines(log_lines, opt$log, useBytes = TRUE)
}
fail <- function(...) {
  line <- paste0("ERROR: ", ...)
  log_lines <<- c(log_lines, line)
  write_log()
  cat(line, "\n", sep = "", file = stderr())
  quit(save = "no", status = 1)
}
listing <- function(x, n = 10) {
  x <- unique(x)
  more <- if (length(x) > n) sprintf(" and %d more", length(x) - n) else ""
  paste0(paste(head(x, n), collapse = ", "), more)
}

# Arguments --------------------------------------------------------------------------------------
args <- commandArgs(trailingOnly = TRUE)
opt <- list()
if (length(args) %% 2 != 0) stop("arguments must come in --name value pairs")
for (i in seq(1, length(args), by = 2)) opt[[sub("^--", "", args[i])]] <- args[i + 1]
for (k in c("upstream", "workbook", "assay", "seq_run", "otu", "otu_format", "taxa", "taxa_format", "output")) {
  if (is.null(opt[[k]]) || !nzchar(opt[[k]])) fail("missing --", k)
}
assay_given <- trimws(opt$assay)
run_given <- trimws(opt$seq_run)
upstream <- readLines(opt$upstream, warn = FALSE, encoding = "UTF-8")
version <- sub(".*Script version: *", "", grep("Script version:", upstream, value = TRUE)[1])
say("FAIRe2MDT ", version, ": assay ", assay_given, ", sequencing run ", run_given, ".")

# Reading ----------------------------------------------------------------------------------------
cell_text <- function(v) {
  if (length(v) == 0 || all(is.na(v))) return(NA_character_)
  if (inherits(v, "POSIXct")) {
    if (format(v, "%Y-%m-%d", tz = "UTC") == "1899-12-31") return(format(v, "%H:%M:%S", tz = "UTC"))
    if (format(v, "%H:%M:%S", tz = "UTC") == "00:00:00") return(format(v, "%Y-%m-%d", tz = "UTC"))
    return(format(v, "%Y-%m-%dT%H:%M:%S", tz = "UTC"))
  }
  if (is.numeric(v)) return(format(v, digits = 15, scientific = FALSE, trim = TRUE))
  as.character(v)
}

sheet_to_use <- function(path, wanted, what) {
  sheets <- excel_sheets(path)
  if (wanted %in% sheets) return(wanted)
  if (length(sheets) == 1) {
    say("Note: ", what, " has no sheet called '", wanted, "', so its only sheet ('", sheets, "') was used.")
    return(sheets)
  }
  fail(what, " has no sheet called '", wanted, "'. Its sheets are: ", paste(sheets, collapse = ", "), ".")
}

# A sheet as text, without a header row (as upstream reads it with col_names = FALSE)
read_sheet_text <- function(path, sheet, n_max = Inf) {
  raw <- suppressMessages(read_xlsx(path, sheet = sheet, col_names = FALSE, col_types = "list",
                                     n_max = n_max, .name_repair = "minimal"))
  cols <- lapply(raw, function(col) vapply(col, cell_text, character(1), USE.NAMES = FALSE))
  names(cols) <- paste0("...", seq_along(cols))
  as_tibble(cols)
}

read_delim_text <- function(path, format, header, nrows = -1) {
  sep <- if (format == "csv") "," else "\t"
  utils::read.table(path, sep = sep, header = header, nrows = nrows, quote = "\"", comment.char = "",
                    colClasses = "character", na.strings = c("", "NA"), check.names = FALSE,
                    fill = TRUE, fileEncoding = "UTF-8-BOM", stringsAsFactors = FALSE)
}

header_row <- function(tbl, first, what) {
  h <- which(trimws(tbl[[1]]) == first)
  if (length(h) == 0) fail(what, " has no row starting with '", first, "' (the row of column names).")
  h[1]
}

# Metadata workbook
wb_sheets <- excel_sheets(opt$workbook)
needed <- c("projectMetadata", "sampleMetadata", "experimentRunMetadata")
missing_sheets <- setdiff(needed, wb_sheets)
if (length(missing_sheets) > 0) {
  fail("the FAIRe workbook has no sheet called ", paste(missing_sheets, collapse = ", "),
       ". Its sheets are: ", paste(wb_sheets, collapse = ", "), ".")
}

Project <- read_sheet_text(opt$workbook, "projectMetadata")
proj_names <- as.character(unlist(Project[1, ]))
proj_names[is.na(proj_names)] <- ""
Project <- Project[-1, ]
names(Project) <- vctrs::vec_as_names(proj_names, repair = "unique", quiet = TRUE)
for (k in c("term_name", "project_level")) {
  if (!k %in% names(Project)) fail("the first row of projectMetadata has no '", k, "' column.")
}

Samples <- read_sheet_text(opt$workbook, "sampleMetadata")
expRun <- read_sheet_text(opt$workbook, "experimentRunMetadata")
s_h <- header_row(Samples, "samp_name", "sampleMetadata")
e_h <- header_row(expRun, "samp_name", "experimentRunMetadata")
e_cols <- trimws(as.character(unlist(expRun[e_h, ])))
for (k in c("assay_name", "seq_run_id")) {
  if (!k %in% e_cols) fail("experimentRunMetadata has no '", k, "' column.")
}

# OTU table: one row per sequence, one column per sample, the sequence IDs in seq_id. A table whose
# top-left cell is empty (as R and many other programs write it) is read with seq_id as that column.
otu_header <- function(top) {
  h <- which(trimws(top[[1]]) == "seq_id")
  if (length(h) > 0) return(list(skip = h[1] - 1, blank = FALSE))
  if (nrow(top) > 0 && is.na(top[[1]][1])) return(list(skip = 0, blank = TRUE))
  fail("the OTU table has no row starting with 'seq_id' (the row of column names).")
}
if (opt$otu_format == "xlsx") {
  otu_sheet <- sheet_to_use(opt$otu, opt$otu_sheet, "the OTU table")
  oh <- otu_header(read_sheet_text(opt$otu, otu_sheet, n_max = 50))
  otu <- suppressMessages(read_xlsx(opt$otu, sheet = otu_sheet, skip = oh$skip, col_names = TRUE))
} else {
  oh <- otu_header(read_delim_text(opt$otu, opt$otu_format, header = FALSE, nrows = 50))
  otu <- utils::read.table(opt$otu, sep = if (opt$otu_format == "csv") "," else "\t", header = TRUE,
                           skip = oh$skip, quote = "\"", comment.char = "", na.strings = c("", "NA"),
                           check.names = FALSE, fileEncoding = "UTF-8-BOM", stringsAsFactors = FALSE)
  otu <- as_tibble(otu, .name_repair = "minimal")
}
if (oh$blank) {
  names(otu)[1] <- "seq_id"
  say("Note: the OTU table's top-left cell is empty, so its first column was taken as seq_id.")
}
names(otu)[1] <- trimws(names(otu)[1])
if (!"seq_id" %in% names(otu)) fail("the OTU table has no seq_id column.")
otu <- otu[!is.na(otu$seq_id) & nzchar(trimws(otu$seq_id)), ]
dup_seq <- otu$seq_id[duplicated(otu$seq_id)]
if (length(dup_seq) > 0) fail("these seq_id values appear more than once in the OTU table: ", listing(dup_seq), ".")
empty_cols <- setdiff(names(otu)[vapply(otu, function(x) all(is.na(x)), logical(1))], "seq_id")
not_numeric <- setdiff(names(otu)[!vapply(otu, is.numeric, logical(1))], c("seq_id", empty_cols))
if (length(empty_cols) > 0) say("Warning: these OTU table columns are empty: ", listing(empty_cols), ".")
if (length(not_numeric) > 0) {
  say("Warning: these OTU table columns hold text, not read counts: ", listing(not_numeric), ".")
}
# MDT reads each OTU table row without its empty cells, so the counts after an empty cell move to
# the wrong samples (seen on MDT's test site, 3 November 2026). Empty count cells are written as 0.
count_cols <- setdiff(names(otu), c("seq_id", not_numeric))
empty_cells <- sum(vapply(otu[count_cols], function(x) sum(is.na(x)), numeric(1)))
if (empty_cells > 0) {
  for (k in count_cols) otu[[k]][is.na(otu[[k]])] <- 0
  say("Note: the OTU table had ", empty_cells, " empty ", if (empty_cells == 1) "cell" else "cells",
      ", written as 0. MDT moves counts to the wrong samples when a row has empty cells.")
}
blank_names <- which(!nzchar(names(otu)) | grepl("^\\.\\.\\.[0-9]+$", names(otu)))
if (length(blank_names) > 0) say("Warning: the OTU table has ", length(blank_names), " column(s) with no sample name.")

# Taxonomy table: read as text, with its header rows (as upstream reads it with col_names = FALSE)
if (opt$taxa_format == "xlsx") {
  taxa <- read_sheet_text(opt$taxa, sheet_to_use(opt$taxa, opt$taxa_sheet, "the taxonomy table"))
} else {
  taxa <- read_delim_text(opt$taxa, opt$taxa_format, header = FALSE)
  names(taxa) <- paste0("...", seq_along(taxa))
  taxa <- as_tibble(taxa)
}
t_h <- header_row(taxa, "seq_id", "the taxonomy table")
# FAIRe's taxaFinal lists every ASV of the final taxa, and otuFinal sums each taxon's reads under
# its most abundant ASV, so taxaFinal can hold ASVs that otuFinal has no row for. MDT wants one
# taxonomy row for each OTU table row, so those are left out.
t_ids <- trimws(as.character(taxa[[1]]))
t_data <- seq_len(nrow(taxa)) > t_h & !is.na(t_ids) & nzchar(t_ids)
in_otu <- t_ids %in% trimws(as.character(otu$seq_id))
if (any(t_data & in_otu) && any(t_data & !in_otu)) {
  n_out <- sum(t_data & !in_otu)
  say("Note: ", n_out, if (n_out == 1) " row" else " rows", " of the taxonomy table left out, as the OTU table has no row ",
      "for ", if (n_out == 1) "its sequence" else "their sequences", " (", listing(t_ids[t_data & !in_otu]), "). In FAIRe's ",
      "final tables these are the ASVs whose reads otuFinal sums under another ASV of the same taxon; MDT wants one ",
      "taxonomy row for each OTU table row.")
  taxa <- taxa[!(t_data & !in_otu), ]
}

# Choosing the assay and run ---------------------------------------------------------------------
norm <- function(x) gsub("[^a-z0-9]", "", tolower(trimws(x)))
match_name <- function(values, wanted) {
  v <- trimws(values)
  hit <- !is.na(v) & tolower(v) == tolower(wanted)
  if (any(hit)) return(list(hit = hit, loose = FALSE))
  list(hit = !is.na(v) & nzchar(norm(wanted)) & norm(v) == norm(wanted), loose = TRUE)
}


data_rows <- e_h + which(!is.na(expRun[[1]][-seq_len(e_h)]))
runs <- expRun[data_rows, ]
names(runs) <- vctrs::vec_as_names(e_cols, repair = "unique", quiet = TRUE)
a_m <- match_name(runs$assay_name, assay_given)
r_m <- match_name(runs$seq_run_id, run_given)
chosen <- a_m$hit & r_m$hit
if (!any(chosen)) {
  pairs <- runs %>% count(assay_name, seq_run_id)
  fail("no rows in experimentRunMetadata have assay_name '", assay_given, "' and seq_run_id '",
       run_given, "'. The workbook has: ",
       paste(sprintf("%s / %s (%d %s)", pairs$assay_name, pairs$seq_run_id, pairs$n, ifelse(pairs$n == 1, "row", "rows")), collapse = "; "), ".")
}
if (a_m$loose) {
  say("Note: no assay_name in experimentRunMetadata is exactly '", assay_given, "', so '",
      listing(runs$assay_name[chosen]), "' was used, which differs only in punctuation or case.")
}
if (r_m$loose) {
  say("Note: no seq_run_id in experimentRunMetadata is exactly '", run_given, "', so '",
      listing(runs$seq_run_id[chosen]), "' was used, which differs only in punctuation or case.")
}
by_hand <- tryCatch(base::grepl(assay_given, runs$assay_name, ignore.case = TRUE) &
                      base::grepl(run_given, runs$seq_run_id, ignore.case = TRUE),
                    error = function(e) rep(FALSE, nrow(runs)))
extra <- runs[by_hand & !chosen, ]
if (nrow(extra) > 0) {
  say("Note: FAIRe2MDT.R run by hand with these names would also take ", nrow(extra),
      " rows of other assays or runs (", listing(unique(paste(extra$assay_name, "/", extra$seq_run_id))),
      "); they are left out here.")
}
dup_samp <- runs$samp_name[chosen][duplicated(runs$samp_name[chosen])]
if (length(dup_samp) > 0) {
  fail("these samples have more than one row in experimentRunMetadata for this assay and run: ",
       listing(dup_samp), ". MDT needs one row per sample (one OTU table column per sample).")
}
no_sample_row <- setdiff(runs$samp_name[chosen], Samples[[1]][-seq_len(s_h)])
if (length(no_sample_row) > 0) {
  say("Warning: these samples are in experimentRunMetadata but not in sampleMetadata, so they are left out: ",
      listing(no_sample_row), ".")
}

# Control samples --------------------------------------------------------------------------------
# A control is a sample whose samp_category is negative control, positive control or PCR standard,
# or that has a neg_cont_type or pos_cont_type. GBIF does not want controls, so they are left out
# by default, with the sequences that only they have reads of (the FAIRe authors, 6 November 2026).
# Kept, a control's "missing: not collected" is written as "not applicable: control sample".
s_cols <- trimws(as.character(unlist(Samples[s_h, ])))
s_rows <- seq_len(nrow(Samples)) > s_h
s_col <- function(name) {
  k <- which(s_cols == name)
  if (length(k) == 0) return(rep(NA_character_, nrow(Samples)))
  trimws(Samples[[k[1]]])
}
given <- function(v) {
  !is.na(v) & nzchar(v) & !grepl("^(not applicable|missing|not collected|not provided|restricted access)", tolower(v))
}
is_ctrl <- s_rows & (tolower(s_col("samp_category")) %in% c("negative control", "positive control", "pcr standard") |
                       given(s_col("neg_cont_type")) | given(s_col("pos_cont_type")))
controls <- trimws(Samples[[1]][is_ctrl])
run_ctrl <- chosen & trimws(runs$samp_name) %in% controls
if (!identical(opt$controls, "keep") && any(run_ctrl)) {
  if (all(!chosen | run_ctrl)) fail("every sample of this assay and run is a control, and controls are left out.")
  left <- trimws(runs$samp_name[run_ctrl])
  say("Note: ", length(left), if (length(left) == 1) " control sample" else " control samples", " left out (",
      listing(left), "), as GBIF does not want controls. Choose to keep controls to include them.")
  chosen <- chosen & !run_ctrl
  ctrl_cols <- intersect(names(otu), left)
  if (length(ctrl_cols) > 0) {
    counts <- setdiff(names(otu)[vapply(otu, is.numeric, logical(1))], "seq_id")
    had <- rowSums(otu[counts], na.rm = TRUE) > 0
    otu <- otu[, setdiff(names(otu), ctrl_cols)]
    counts <- setdiff(counts, ctrl_cols)
    only_ctrl <- had & rowSums(otu[counts], na.rm = TRUE) == 0
    if (any(only_ctrl)) {
      gone <- trimws(as.character(otu$seq_id[only_ctrl]))
      say("Note: ", length(gone), if (length(gone) == 1) " sequence" else " sequences",
          " with reads only in the controls left out of the OTU and taxonomy tables (", listing(gone), ").")
      otu <- otu[!only_ctrl, ]
      t_ids2 <- trimws(as.character(taxa[[1]]))
      taxa <- taxa[!(seq_len(nrow(taxa)) > t_h & t_ids2 %in% gone), ]
    }
  }
} else if (any(run_ctrl)) {
  n_conv <- 0
  ctrl_rows <- which(is_ctrl & trimws(Samples[[1]]) %in% trimws(runs$samp_name[run_ctrl]))
  for (k in seq_along(Samples)[-1]) {
    v <- Samples[[k]][ctrl_rows]
    hit <- !is.na(v) & tolower(gsub("\\s+", " ", trimws(v))) == "missing: not collected"
    if (any(hit)) {
      Samples[[k]][ctrl_rows[hit]] <- "not applicable: control sample"
      n_conv <- n_conv + sum(hit)
    }
  }
  if (n_conv > 0) {
    say("Note: 'missing: not collected' written as 'not applicable: control sample' in ", n_conv,
        if (n_conv == 1) " cell" else " cells", " of the controls, FAIRe's term for controls.")
  }
}

# Keep the rows above the column names and the chosen runs. Upstream then selects runs with grepl;
# with the runs already chosen, its grepl is set to keep every row.
expRun <- expRun[c(seq_len(e_h), data_rows[chosen]), ]

# With assay columns in projectMetadata, upstream finds the assay's column from the assay_name row
assay <- assay_given
pl <- which(names(Project) == "project_level")
if (pl < which(names(Project) == "term_name")) fail("in projectMetadata, project_level must come after term_name.")
assay_cols <- names(Project)[seq_along(Project) > pl]
if (length(assay_cols) > 0) {
  a_row <- which(Project$term_name == "assay_name")
  if (length(a_row) == 0) fail("projectMetadata has assay columns but no assay_name row.")
  proj_assays <- as.character(unlist(Project[a_row[1], assay_cols]))
  pm <- match_name(proj_assays, assay_given)
  if (!any(pm$hit)) {
    fail("the assay_name row of projectMetadata has no assay '", assay_given, "'. It has: ",
         listing(proj_assays[!is.na(proj_assays)]), ".")
  }
  if (sum(pm$hit) > 1) fail("assay '", assay_given, "' is in more than one column of projectMetadata.")
  assay <- proj_assays[pm$hit]
  if (pm$loose) say("Note: projectMetadata spells the assay '", assay, "'; the Study sheet uses that spelling.")
}
p_id <- Project$project_level[which(Project$term_name == "project_id")]
if (length(p_id) == 0 || is.na(p_id[1])) say("Warning: projectMetadata has no project_id.")

# target_gene: MDT takes it from the Study sheet only if it names a term of the GBIF target_gene
# vocabulary (by term, label or alternative label). FAIRe's names for five rRNA genes are not among
# them, so write the GBIF term for every FAIRe value. The table comes with the tool.
if (!is.null(opt$target_genes)) {
  genes <- utils::read.delim(opt$target_genes, colClasses = "character", na.strings = character(0))
  tg_row <- which(Project$term_name == "target_gene")
  sf_row <- which(Project$term_name == "target_subfragment")
  if (length(tg_row) > 0) {
    tg_row <- tg_row[1]
    # the cell that reaches the Study sheet: project_level, or this assay's column if that is empty
    col <- if (!is.na(Project$project_level[tg_row]) || length(assay_cols) == 0) "project_level" else assay_cols[pm$hit]
    value <- trimws(Project[[col]][tg_row])
    sub <- if (length(sf_row) > 0) trimws(Project[[col]][sf_row[1]]) else NA
    if (is.na(value) || !nzchar(value)) {
      say("Warning: projectMetadata has no target_gene for this assay; choose the marker in MDT's mapping step.")
    } else {
      hits <- genes[tolower(genes$faire_target_gene) == tolower(value), ]
      exact <- hits[!is.na(sub) & tolower(hits$target_subfragment) == tolower(sub), ]
      hit <- if (nrow(exact) > 0) exact[1, ] else hits[hits$target_subfragment == "", ][1, ]
      if (nrow(hits) > 0 && !is.na(hit$gbif_target_gene)) {
        if (hit$gbif_target_gene != value) {
          Project[[col]][tg_row] <- hit$gbif_target_gene
          say("Note: target_gene '", value, "' written as '", hit$gbif_target_gene, "', the GBIF term for ",
              hit$gbif_label, ", which MDT recognises.")
        }
      } else {
        say("Warning: target_gene '", value, "' is not a FAIRe target_gene value, so MDT may not recognise ",
            "it; check the marker in MDT's mapping step.")
      }
    }
  }
}

# Running the upstream conversion ----------------------------------------------------------------
start <- grep("^# Run the below code", upstream)
if (length(start) != 1) fail("could not find the line '# Run the below code' in ", basename(opt$upstream), ".")
code <- parse(text = upstream[start:length(upstream)], keep.source = FALSE)

env <- new.env(parent = globalenv())
env$Project <- Project
env$Samples <- Samples
env$expRun <- expRun
env$otu <- otu
env$taxa <- taxa
env$assay <- assay
env$seq_run <- run_given
env$grepl <- function(pattern, x, ...) rep(TRUE, length(x))

withCallingHandlers(
  for (e in code) eval(e, envir = env),
  error = function(e) fail("FAIRe2MDT stopped: ", conditionMessage(e))
)
if (is.null(env$output_filename) || !file.exists(env$output_filename)) fail("FAIRe2MDT did not write a workbook.")
if (!suppressWarnings(file.rename(env$output_filename, opt$output)) &&
    !file.copy(env$output_filename, opt$output, overwrite = TRUE)) {
  fail("could not copy the workbook to the output.")
}

# Checks on the result ---------------------------------------------------------------------------
samp_ids <- env$Samples_expRun$id
otu_ids <- names(env$otu)
taxa_ids <- env$taxa$id
otu_only <- setdiff(otu_ids, samp_ids)
meta_only <- setdiff(samp_ids, otu_ids)
if (length(otu_only) > 0) {
  say("Warning: these OTU table columns are not samples of this assay and run in the metadata: ",
      listing(otu_only), ".")
}
if (length(meta_only) > 0) say("Warning: these samples have no column in the OTU table: ", listing(meta_only), ".")
seq_otu_only <- setdiff(rownames(env$otu), taxa_ids)
seq_taxa_only <- setdiff(taxa_ids, rownames(env$otu))
if (length(seq_otu_only) > 0) {
  say("Warning: these sequences are in the OTU table but not in the taxonomy table: ", listing(seq_otu_only), ".")
}
if (length(seq_taxa_only) > 0) {
  say("Warning: these sequences are in the taxonomy table but not in the OTU table: ", listing(seq_taxa_only), ".")
}
dup_taxa <- taxa_ids[duplicated(taxa_ids)]
if (length(dup_taxa) > 0) say("Warning: these seq_id values appear more than once in the taxonomy table: ", listing(dup_taxa), ".")

say("Study sheet: ", nrow(env$Project), " terms.")
say("Samples sheet: ", nrow(env$Samples_expRun), " samples, ", ncol(env$Samples_expRun), " fields.")
say("Taxonomy sheet: ", nrow(env$taxa), " sequences, ", ncol(env$taxa), " fields.")
say("OTU_table sheet: ", nrow(env$otu), " sequences, ", ncol(env$otu), " samples.")
write_log()
