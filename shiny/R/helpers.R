# Reading and writing the files the tools exchange, and small display helpers.

read_tsv <- function(path, ...) {
  if (is.null(path) || !file.exists(path) || file.size(path) == 0) return(NULL)
  tryCatch(utils::read.delim(path, sep = "\t", quote = "", comment.char = "", check.names = FALSE,
                             colClasses = "character", na.strings = character(), encoding = "UTF-8", ...),
           error = function(e) NULL)
}

# The assays typed in one box, separated by commas ("OlsonViiA7, OlsonFranklin"); "" (every assay) when
# none is given. A value for several assays becomes one row of the project values for each.
split_assays <- function(x) {
  x <- as.character(x); x[is.na(x)] <- ""
  a <- trimws(strsplit(paste(x, collapse = ","), ",", fixed = TRUE)[[1]])
  a <- unique(a[nzchar(a)])
  if (length(a)) a else ""
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
      cache <<- data.frame(term = d$term_name, sheet = d$data_type, section = d$section,
                           level = d$requirement_level_code, description = d$description, example = d$example,
                           stringsAsFactors = FALSE)
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
                 replacement = "Replacement FAIRe term", kept_as = "If rejected, kept as",
                 earlier = "Earlier review")
DECISIONS <- c("Accept", "Reject", "Change")

# rows: one per input term, with the REVIEW_COLS fields. choices: for each input term, its replacement
# list from the hidden Choices sheet, split where the sheet leaves a blank line: the best candidates
# (a MIxS or Darwin Core term first, when the mapper found one) and then every other term.
# CSV for opening in Excel: UTF-8 with a byte order mark (so Excel shows ° and µ), every value quoted.
write_csv <- function(df, path) {
  q <- function(x) { x <- as.character(x); x[is.na(x)] <- ""; paste0('"', gsub('"', '""', enc2utf8(x), fixed = TRUE), '"') }
  lines <- c(paste(q(names(df)), collapse = ","),
             if (nrow(df)) do.call(paste, c(unname(lapply(df, q)), sep = ",")))
  con <- file(path, open = "wb")
  on.exit(close(con))
  writeBin(as.raw(c(0xef, 0xbb, 0xbf)), con)
  writeLines(lines, con, useBytes = TRUE)
}
read_csv <- function(path) {
  tryCatch(utils::read.csv(path, colClasses = "character", check.names = FALSE, na.strings = character(),
                           fileEncoding = "UTF-8-BOM"),
           error = function(e) NULL)
}
# A CSV copy of a tool's TSV output, written beside it, for opening in Excel. NULL for other files, and for
# TSV files that start with # lines (such as the SSSOM crosswalk's metadata block), which stay TSV only.
csv_copy <- function(path) {
  if (!grepl("\\.tsv$", path, ignore.case = TRUE) || !file.exists(path)) return(NULL)
  first <- tryCatch(readLines(path, n = 1, warn = FALSE), error = function(e) "")
  if (!length(first) || startsWith(first, "#")) return(NULL)
  out <- sub("\\.tsv$", ".csv", path, ignore.case = TRUE)
  if (!file.exists(out) || file.mtime(out) < file.mtime(path)) {
    d <- read_tsv(path)
    if (is.null(d)) return(NULL)
    write_csv(d, out)
  }
  out
}

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
  if (!"chosen_by" %in% names(decisions)) decisions$chosen_by <- ""
  write_tsv(decisions[, c("input", "decision", "replacement", "chosen_by")], tsv)
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

# ---------------------------------------------------------------- previewing a file

# What a file is, judged by its first bytes (Galaxy and people name files in all sorts of ways): a PDF,
# a workbook, a FASTA file, a table with tabs or commas between its columns, or plain text.
sniff_file <- function(path) {
  b <- tryCatch(readBin(path, "raw", 4096), error = function(e) raw())
  if (length(b) >= 5 && rawToChar(b[1:5]) == "%PDF-") return("pdf")
  if (length(b) >= 4 && identical(b[1:4], as.raw(c(0x50, 0x4b, 0x03, 0x04)))) return("workbook")
  lines <- preview_lines(path, 30)
  lines <- lines[nzchar(trimws(lines))]
  if (!length(lines)) return("text")
  if (startsWith(trimws(lines[1]), ">")) return("fasta")
  same_count <- function(ch) {
    n <- lengths(regmatches(lines, gregexpr(ch, lines, fixed = TRUE)))
    n[1] > 0 && mean(n == n[1]) >= 0.8
  }
  e <- galaxy_ext(path)
  if (e == "tabular" || same_count("\t")) return("tab")
  if (e == "csv" || (length(lines) > 2 && same_count(","))) return("csv")
  "text"
}

preview_lines <- function(path, n) {
  con <- file(path, open = "r", encoding = "UTF-8")
  on.exit(close(con))
  tryCatch(suppressWarnings(readLines(con, n = n, warn = FALSE)), error = function(e) character())
}

# The first rows of a table as they are in the file, with no row taken as the column names, so the
# person can see where the column names are.
preview_raw_table <- function(path, kind, sheet = NULL, n = 15, max_cols = 30) {
  d <- tryCatch({
    if (kind == "workbook") {
      # A range keeps empty rows at the top, so the row numbers are those Excel shows.
      as.data.frame(readxl::read_excel(path, sheet = sheet, range = readxl::cell_rows(c(1, n)), col_names = FALSE,
                                       col_types = "text", .name_repair = "minimal"))
    } else {
      # As many columns as the widest of the rows shown, so a short row of notes above the column names
      # does not set the width.
      lines <- preview_lines(path, n)
      sep <- if (kind == "tab") "\t" else ","
      quote <- if (kind == "tab") "" else "\""
      w <- max(utils::count.fields(textConnection(lines), sep = sep, quote = quote, blank.lines.skip = FALSE),
               na.rm = TRUE)
      utils::read.table(text = lines, sep = sep, header = FALSE, fill = TRUE, quote = quote, comment.char = "",
                        colClasses = "character", blank.lines.skip = FALSE, col.names = paste0("V", seq_len(w)))
    }
  }, error = function(e) NULL)
  if (is.null(d) || !nrow(d)) return(NULL)
  d[is.na(d)] <- ""
  list(rows = d[, seq_len(min(ncol(d), max_cols)), drop = FALSE], more_cols = max(0, ncol(d) - max_cols))
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

# A plain first line for the commonest ways a tool stops, from its log: what went wrong and what to do.
# The tool's own message stays in the log. Our own scripts' "ERROR:" lines are plain already, so when no
# pattern fits, the first of them is used.
ERROR_HELP <- list(
  c("Excel file format cannot be determined|BadZipFile|not a zip file|File is not a zip file",
    "The file is not an Excel workbook (.xlsx), or it is damaged. Open it in Excel, save it as an Excel workbook (.xlsx) and add it again."),
  c("Worksheet named .* not found|Worksheet .* does not exist|No sheet named|sheet .* not found",
    "The workbook does not have a sheet the tool needs, such as projectMetadata or sampleMetadata. Check that it is a FAIRe workbook, or choose the right sheet."),
  c("UnicodeDecodeError|codec can't decode",
    "The file's text is not in UTF-8. Save it again as UTF-8 text (in Excel: CSV UTF-8) and add it again."),
  c("EmptyDataError|No columns to parse",
    "The file is empty, or has no rows the tool can read."),
  c("ParserError|Error tokenizing data",
    "The table could not be read: a row has more or fewer fields than the header. Look for stray commas or tabs in that row."),
  c("ModuleNotFoundError|No module named",
    "A Python package the tool needs is not installed. Close the app, run setup.R again and restart it."),
  c("there is no package called",
    "An R package the tool needs is not installed. Close the app, run setup.R again and restart it."),
  c("ConnectionError|Max retries exceeded|NameResolutionError|timed out|Temporary failure in name resolution",
    "The tool could not reach a web service it needs (such as WoRMS or GBIF). Check the internet connection and try again."),
  c("PermissionError|Permission denied",
    "The tool could not write its files. Close any file from this session that is open in Excel, then try again."),
  c("KeyError: '([^']+)'",
    "A column the tool needs, \\1, is missing from the file. Check the column names.")
)
explain_error <- function(log) {
  log <- log %||% ""
  for (h in ERROR_HELP) {
    m <- regmatches(log, regexec(h[1], log, perl = TRUE))[[1]]
    if (length(m)) return(if (length(m) > 1) sub("\\1", m[2], h[2], fixed = TRUE) else h[2])
  }
  e <- grep("^ERROR:", strsplit(log, "\n")[[1]], value = TRUE)
  if (!length(e)) return("")
  e <- sub("^ERROR:\\s*", "", e[1])
  paste0(toupper(substr(e, 1, 1)), substring(e, 2))
}

# Whether GitHub has a newer version of the app than this copy, checked once each time the app starts,
# however it is started; nothing is said when GitHub cannot be reached. Only for a copy that the
# one-line start (start.R) installed: it records the commit it installed in .faire_app_version, in the
# folder above the app. A copy the person downloaded or cloned themselves is left to them to update.
latest_app_commit <- function(timeout = 5) {
  old <- options(timeout = timeout)
  on.exit(options(old), add = TRUE)
  tryCatch({
    con <- url("https://github.com/FAIR-eDNA/FAIRe-Galaxy.git/info/refs?service=git-upload-pack", "rb")
    on.exit(close(con), add = TRUE)
    bytes <- readBin(con, "raw", 5e6)
    bytes[bytes == as.raw(0)] <- as.raw(32)
    text <- rawToChar(bytes)
    hit <- regmatches(text, regexpr("[0-9a-f]{40} refs/heads/main", text))
    if (length(hit)) substr(hit, 1, 40) else NA_character_
  }, error = function(e) NA_character_, warning = function(w) NA_character_)
}

newer_app_available <- local({
  found <- NULL
  function() {
    if (!is.null(found)) return(found)
    home <- dirname(normalizePath(getOption("faire.app_dir", "."), winslash = "/", mustWork = FALSE))
    marker <- file.path(home, ".faire_app_version")
    installed <- if (file.exists(marker)) readLines(marker, warn = FALSE)[1] else NA_character_
    latest <- if (is.na(installed) || installed == "unknown") NA_character_ else latest_app_commit()
    found <<- !is.na(installed) && !is.na(latest) && !identical(installed, latest)
    found
  }
})
