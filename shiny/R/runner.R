# Finding the tools, Python and R, and running a tool in its own folder.
#
# The app calls the same scripts, with the same arguments, as the Galaxy wrappers in ../tools.
# Each run gets its own folder inside the session folder, so every output can be traced to the
# run that wrote it.

is_windows <- function() .Platform$OS.type == "windows"

app_dir <- function() normalizePath(getOption("faire.app_dir", getwd()), mustWork = FALSE)

tools_dir <- function() {
  d <- Sys.getenv("FAIRE_TOOLS_DIR", "")
  if (!nzchar(d)) d <- file.path(app_dir(), "..", "tools")
  normalizePath(d, mustWork = FALSE)
}

tool_path <- function(...) file.path(tools_dir(), ...)

# Python: FAIRE_PYTHON if set, then the virtual environment setup.R makes, then python3 or python.
find_python <- function() {
  p <- Sys.getenv("FAIRE_PYTHON", "")
  # Not normalizePath(): a virtual environment's python is a link, and resolving it would leave the
  # environment and its packages behind.
  if (nzchar(p) && file.exists(p)) return(p)
  venv <- if (is_windows()) file.path(app_dir(), ".venv", "Scripts", "python.exe")
          else file.path(app_dir(), ".venv", "bin", "python")
  if (file.exists(venv)) return(venv)
  for (cand in c("python3", "python")) {
    w <- Sys.which(cand)
    if (nzchar(w)) return(unname(w))
  }
  ""
}

find_rscript <- function() {
  exe <- if (is_windows()) "Rscript.exe" else "Rscript"
  p <- file.path(R.home("bin"), exe)
  if (file.exists(p)) p else unname(Sys.which("Rscript"))
}

# Check that Python and each tool's packages are there; returns a data frame for the start page.
check_setup <- function() {
  py <- find_python()
  rows <- list()
  add <- function(item, ok, detail) rows[[length(rows) + 1]] <<- data.frame(item = item, ok = ok, detail = detail)
  add("FAIRe tools folder", dir.exists(tools_dir()) && file.exists(tool_path("faire_mapper", "faire_mapper.py")),
      tools_dir())
  if (!nzchar(py)) {
    add("Python", FALSE, "not found: run setup.R, or set FAIRE_PYTHON to a Python 3.10 or later")
  } else {
    v <- tryCatch(processx::run(py, c("-c", "import sys; print(sys.version.split()[0])"),
                                error_on_status = FALSE)$stdout, error = function(e) "")
    add("Python", nzchar(trimws(v)), paste(py, trimws(v)))
    mods <- c(core = "pandas, openpyxl, pypdf", "FAIRe-fier" = "pydantic, jinja2", "FAIRe2NCBI" = "yaml",
              edna2obis = "pyworms, pygbif, multiprocess, requests, rich, pyfiglet")
    for (nm in names(mods)) {
      code <- sprintf("import %s", mods[[nm]])
      r <- tryCatch(processx::run(py, c("-c", code), error_on_status = FALSE), error = function(e) list(status = 1))
      label <- if (nm == "core") "Python packages for all tools" else paste("Python packages for", nm)
      add(label, r$status == 0, if (r$status == 0) mods[[nm]] else paste("missing one of:", mods[[nm]]))
    }
  }
  rpk <- c("readxl", "openxlsx", "dplyr", "tibble", "RColorBrewer", "here")
  have <- vapply(rpk, requireNamespace, logical(1), quietly = TRUE)
  add("R packages for FAIRe-ator and FAIRe2MDT", all(have),
      if (all(have)) paste(rpk, collapse = ", ") else paste("missing:", paste(rpk[!have], collapse = ", ")))
  do.call(rbind, rows)
}

new_run_dir <- function(session_dir, tool) {
  runs <- file.path(session_dir, "runs")
  dir.create(runs, showWarnings = FALSE, recursive = TRUE)
  n <- length(list.dirs(runs, recursive = FALSE)) + 1
  d <- file.path(runs, sprintf("%02d_%s", n, tool))
  dir.create(d, recursive = TRUE)
  normalizePath(d)
}

quote_arg <- function(a) if (grepl("[[:space:]'\"]", a) || !nzchar(a)) shQuote(a) else a

# Run a command in wd. Returns status, the combined output and the command line (for the log).
run_cmd <- function(cmd, args, wd, env = character(), timeout = 1800) {
  args <- as.character(args)
  envs <- c("current", PYTHONUTF8 = "1", PYTHONIOENCODING = "utf-8", env)
  res <- tryCatch(
    processx::run(cmd, args, wd = wd, error_on_status = FALSE, stderr_to_stdout = TRUE,
                  env = envs, timeout = timeout, encoding = "UTF-8"),
    error = function(e) list(status = 127, stdout = conditionMessage(e), timeout = FALSE))
  out <- res$stdout %||% ""
  if (isTRUE(res$timeout)) out <- paste0(out, "\nStopped: the tool ran for longer than ", timeout, " seconds.")
  # strip colour codes some upstream scripts print
  out <- gsub("\033\\[[0-9;]*m", "", out)
  line <- paste(c(basename(cmd), vapply(args, quote_arg, character(1))), collapse = " ")
  list(status = res$status, output = out, cmdline = line)
}

run_python <- function(script, args, wd, env = character(), timeout = 1800) {
  py <- find_python()
  if (!nzchar(py)) return(list(status = 127, output = "Python was not found. Run setup.R first.", cmdline = ""))
  run_cmd(py, c(script, args), wd, env, timeout)
}

run_rscript <- function(script, args, wd, timeout = 1800) {
  run_cmd(find_rscript(), c("--vanilla", script, args), wd, timeout = timeout)
}

`%||%` <- function(a, b) if (is.null(a) || length(a) == 0) b else a

# A finished run: what it wrote, plus the command lines and output for the log.
run_result <- function(tool, label, dir, steps, outputs = list(), notes = character()) {
  status <- max(vapply(steps, function(s) as.numeric(s$status), numeric(1)))
  log <- paste(vapply(steps, function(s) paste0("$ ", s$cmdline, "\n", s$output), character(1)), collapse = "\n")
  writeLines(log, file.path(dir, "run_log.txt"), useBytes = TRUE)
  outputs <- outputs[vapply(outputs, function(p) !is.null(p) && file.exists(p), logical(1))]
  list(tool = tool, label = label, dir = dir, ok = status == 0, status = status, log = log,
       outputs = outputs, notes = notes, time = format(Sys.time(), "%H:%M:%S"))
}
