# Reading and writing the files the tools exchange, and small display helpers.

read_tsv <- function(path, ...) {
  if (is.null(path) || !file.exists(path) || file.size(path) == 0) return(NULL)
  tryCatch(utils::read.delim(path, sep = "\t", quote = "", comment.char = "", check.names = FALSE,
                             colClasses = "character", na.strings = character(), encoding = "UTF-8", ...),
           error = function(e) NULL)
}

# Always UTF-8, whatever the computer's own character set: write.table's fileEncoding goes through the
# native encoding, which turns ° and µ into <U+00B0> and <U+00B5> where that is not UTF-8.
write_tsv <- function(df, path) {
  cols <- lapply(df, function(x) { x <- as.character(x); x[is.na(x)] <- ""; enc2utf8(x) })
  lines <- c(paste(enc2utf8(names(df)), collapse = "\t"),
             if (nrow(df)) do.call(paste, c(unname(cols), sep = "\t")))
  con <- file(path, open = "wb")
  on.exit(close(con))
  writeLines(lines, con, useBytes = TRUE)
}

# The FAIRe terms, from the checklist the tools bundle: name, sheet, requirement level, description.
checklist_terms <- local({
  cache <- NULL
  function() {
    if (is.null(cache)) {
      d <- readxl::read_excel(checklist(), sheet = "checklist")
      cache <<- data.frame(term = d$term_name, sheet = d$data_type, level = d$requirement_level_code,
                           description = d$description, example = d$example, stringsAsFactors = FALSE)
    }
    cache
  }
})

# ---------------------------------------------------------------- the review sheet

# The review sheet propose mapping writes (tools/faire_mapper/faire_mapper_review.py). The app's review
# screen shows its Review sheet and saves the decisions into a copy of it, so a sheet filled in on screen
# and one filled in with Excel go to apply mapping in the same way.
REVIEW_COLS <- c(input = "Input term", proposed = "Proposed FAIRe term", score = "Score", call = "Mapper's call",
                 reasoning = "Mapper's reasoning", decision = "Reviewer's decision",
                 replacement = "Replacement FAIRe term", kept_as = "If rejected, kept as")
DECISIONS <- c("Accept", "Reject", "Change")

# rows: one per input term, with the REVIEW_COLS fields. choices: for each input term, its replacement
# list from the hidden Choices sheet, split where the sheet leaves a blank line: the best candidates
# (a MIxS or Darwin Core term first, when the mapper found one) and then every other term.
read_review_sheet <- function(path) {
  sheets <- readxl::excel_sheets(path)
  if (!"Review" %in% sheets) stop("this file has no Review sheet, so it is not a review sheet from propose mapping")
  r <- as.data.frame(readxl::read_excel(path, sheet = "Review", col_types = "text"), check.names = FALSE)
  need <- REVIEW_COLS[c("input", "decision", "replacement")]
  if (!all(need %in% names(r)))
    stop("the review sheet needs the columns ", paste(need, collapse = ", "))
  for (h in setdiff(REVIEW_COLS, names(r))) r[[h]] <- ""
  r <- r[, unname(REVIEW_COLS), drop = FALSE]
  names(r) <- names(REVIEW_COLS)
  r[is.na(r)] <- ""
  r$input <- trimws(r$input)
  r <- r[nzchar(r$input), , drop = FALSE]
  d <- tolower(trimws(r$decision))
  r$decision <- ifelse(d %in% tolower(DECISIONS), DECISIONS[match(d, tolower(DECISIONS))], "")
  r$replacement <- trimws(r$replacement)
  choices <- list()
  if ("Choices" %in% sheets) {
    ch <- suppressMessages(readxl::read_excel(path, sheet = "Choices", col_names = FALSE, col_types = "text"))
    for (j in seq_along(ch)) {
      v <- as.character(ch[[j]])
      v[is.na(v)] <- ""
      if (!nzchar(v[1])) next
      items <- v[-1]
      while (length(items) && !nzchar(items[length(items)])) items <- items[-length(items)]
      gap <- which(!nzchar(items))[1]
      best <- if (is.na(gap)) items else items[seq_len(gap - 1)]
      rest <- if (is.na(gap)) character() else items[-seq_len(gap)]
      choices[[trimws(v[1])]] <- list(best = best, rest = setdiff(rest[nzchar(rest)], best))
    }
  }
  list(rows = r, choices = choices)
}

# Write decisions (a data frame with input, decision and replacement) into a copy of a review sheet.
write_review_decisions <- function(sheet, decisions, out, wd) {
  tsv <- file.path(wd, "decisions.tsv")
  write_tsv(decisions[, c("input", "decision", "replacement")], tsv)
  run_python(file.path(app_dir(), "python", "fill_review_sheet.py"), c(sheet, tsv, out), wd)
}

# ---------------------------------------------------------------- files the person adds

# Uploaded .gz files are unpacked, as Galaxy does on upload.
add_to_library <- function(lib_dir, name, src) {
  dir.create(lib_dir, showWarnings = FALSE, recursive = TRUE)
  if (grepl("\\.gz$", name, ignore.case = TRUE)) {
    name <- sub("\\.gz$", "", name, ignore.case = TRUE)
    dest <- file.path(lib_dir, name)
    inp <- gzfile(src, "rb"); outp <- file(dest, "wb")
    repeat { b <- readBin(inp, "raw", 1e6); if (!length(b)) break; writeBin(b, outp) }
    close(inp); close(outp)
  } else {
    dest <- file.path(lib_dir, name)
    file.copy(src, dest, overwrite = TRUE)
  }
  setNames(normalizePath(dest), name)
}

xlsx_sheets <- function(path) tryCatch(readxl::excel_sheets(path), error = function(e) character())

# A table for display: TSV or CSV as text, or one sheet of a workbook as it is laid out.
preview_table <- function(path, sheet = NULL, n = 200) {
  ext <- galaxy_ext(path)
  out <- tryCatch({
    if (ext == "xlsx") {
      sh <- sheet %||% xlsx_sheets(path)[1]
      d <- readxl::read_excel(path, sheet = sh, col_names = FALSE, col_types = "text", n_max = n,
                              .name_repair = "minimal")
      d <- as.data.frame(d)
      names(d) <- paste0("col", seq_along(d))
      d[is.na(d)] <- ""
      d
    } else if (ext == "csv") {
      utils::read.csv(path, colClasses = "character", check.names = FALSE, nrows = n, encoding = "UTF-8")
    } else if (ext %in% c("tabular")) {
      utils::read.delim(path, colClasses = "character", check.names = FALSE, nrows = n, quote = "",
                        comment.char = "", encoding = "UTF-8")
    } else NULL
  }, error = function(e) NULL)
  out
}

# A FAIRe workbook sheet as a table: requirement and section rows above the field names on row 3.
read_faire_sheet <- function(path, sheet) {
  d <- tryCatch(readxl::read_excel(path, sheet = sheet, col_names = FALSE, col_types = "text",
                                   .name_repair = "minimal"), error = function(e) NULL)
  if (is.null(d) || nrow(d) < 3) return(NULL)
  d <- as.data.frame(d)
  d[is.na(d)] <- ""
  if (sheet == "projectMetadata") return(d)
  hdr <- as.character(unlist(d[3, ]))
  body <- d[-(1:3), , drop = FALSE]
  names(body) <- make.unique(ifelse(nzchar(hdr), hdr, paste0("col", seq_along(hdr))))
  body
}

fmt_bytes <- function(b) {
  if (is.na(b)) return("")
  if (b < 1024) return(paste(b, "B"))
  if (b < 1024^2) return(sprintf("%.0f KB", b / 1024))
  sprintf("%.1f MB", b / 1024^2)
}

short_log <- function(log, n = 40) {
  l <- strsplit(log, "\n", fixed = TRUE)[[1]]
  l <- l[!grepl("^\\$ |UserWarning: Data Validation|^\\s*warn\\(msg\\)$", l)]
  paste(utils::tail(l, n), collapse = "\n")
}
