# Set up the FAIRe tools app on this computer. Run it once, from this folder:
#
#   Rscript setup.R          (or source("setup.R") in RStudio, with this folder as the working directory)
#
# It installs the R packages the app and the R tools need, makes a Python virtual environment in
# .venv beside this file, and installs the Python packages in requirements.txt into it. Python 3.10
# to 3.13 must be installed already (python.org, or your organisation's software centre).

app_dir <- normalizePath(".")
if (!file.exists(file.path(app_dir, "app.R"))) stop("Run setup.R from the folder that holds app.R.")

cat("== R packages\n")
pkgs <- c("shiny", "bslib", "DT", "readxl", "openxlsx", "jsonlite", "processx", "zip",
          "dplyr", "tibble", "RColorBrewer", "here")
missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) {
  cat("Installing:", paste(missing, collapse = ", "), "\n")
  install.packages(missing, repos = "https://cloud.r-project.org")
} else cat("All there.\n")

cat("\n== Python\n")
windows <- .Platform$OS.type == "windows"
py_version <- function(cmd, args = character()) {
  out <- tryCatch(system2(cmd, c(args, "-c", shQuote("import sys; print('%d.%d' % sys.version_info[:2])")),
                          stdout = TRUE, stderr = FALSE), error = function(e) character(), warning = function(w) character())
  if (length(out)) out[1] else ""
}
base <- Sys.getenv("FAIRE_PYTHON_BASE", "")
cands <- if (nzchar(base)) {
  list(list(base))
} else if (windows) {
  list(list("py", "-3.13"), list("py", "-3.12"), list("py", "-3.11"), list("py", "-3"), list("python"))
} else {
  list(list("python3.13"), list("python3.12"), list("python3.11"), list("python3"), list("python"))
}
python <- NULL
for (c in cands) {
  if (!nzchar(Sys.which(c[[1]]))) next
  v <- py_version(c[[1]], unlist(c[-1]))
  if (!nzchar(v)) next
  parts <- as.integer(strsplit(v, ".", fixed = TRUE)[[1]])
  if (parts[1] == 3 && parts[2] >= 10 && parts[2] <= 13) { python <- c; cat("Using Python", v, "(", paste(unlist(c), collapse = " "), ")\n"); break }
  cat("Skipping Python", v, "from", c[[1]], "(the tools need 3.10 to 3.13)\n")
}
if (is.null(python)) stop("No Python 3.10 to 3.13 found. Install one, or set FAIRE_PYTHON_BASE to its path, and run setup.R again.")

venv <- file.path(app_dir, ".venv")
venv_python <- if (windows) file.path(venv, "Scripts", "python.exe") else file.path(venv, "bin", "python")
if (!file.exists(venv_python)) {
  cat("Making the virtual environment in", venv, "\n")
  status <- system2(python[[1]], c(unlist(python[-1]), "-m", "venv", shQuote(venv)))
  if (status != 0 || !file.exists(venv_python)) stop("Could not make the virtual environment.")
}
cat("Installing the Python packages (this takes a few minutes the first time)\n")
status <- system2(venv_python, c("-m", "pip", "install", "--upgrade", "pip", "--quiet"))
status <- system2(venv_python, c("-m", "pip", "install", "-r", shQuote(file.path(app_dir, "requirements.txt"))))
if (status != 0) stop("pip could not install the packages; see the messages above.")

cat("\n== Check\n")
options(faire.app_dir = app_dir)
source(file.path(app_dir, "R", "runner.R"))
s <- check_setup()
print(data.frame(ok = ifelse(s$ok, "yes", "NO"), item = s$item, detail = s$detail), right = FALSE, row.names = FALSE)
if (all(s$ok)) {
  cat("\nAll set. Start the app with: Rscript run_app.R\n")
} else {
  cat("\nSomething is missing (NO above). The app still starts, but the tools that need it will stop with a message.\n")
}
