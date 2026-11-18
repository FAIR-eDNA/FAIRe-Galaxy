# Download, set up and start the FAIRe tools app in one step. In R or RStudio, run:
#
#   source("https://raw.githubusercontent.com/FAIR-eDNA/FAIRe-Galaxy/main/shiny/start.R")
#
# The first time, it downloads the FAIRe-Galaxy repository into a folder called FAIRe-Galaxy in your
# user folder (C:/Users/you/FAIRe-Galaxy on Windows, outside OneDrive; ~/FAIRe-Galaxy on a Mac), runs
# setup.R, and opens the app in your web browser.
# Setting up takes about 15 minutes, most of it downloading packages. After that, the same line checks
# for a newer version, downloads it if there is one, and starts the app in a few seconds.
#
# It needs R 4.1 or later and Python 3.10 to 3.13 (see shiny/README.md if you don't have Python).
# To use another folder, first run, for example,
#   Sys.setenv(FAIRE_HOME = "C:/Users/you/R_projects/FAIRe-Galaxy")
# The folder is replaced when a newer version arrives, so keep your own files somewhere else.

local({
  repo <- "FAIR-eDNA/FAIRe-Galaxy"
  branch <- "main"
  # On Windows, R's home is often a Documents folder that OneDrive syncs, which does not suit the
  # thousands of files in the app's Python environment, so the default is the user folder itself.
  user_dir <- if (.Platform$OS.type == "windows" && nzchar(Sys.getenv("USERPROFILE"))) {
    Sys.getenv("USERPROFILE")
  } else {
    path.expand("~")
  }
  home <- normalizePath(Sys.getenv("FAIRE_HOME", file.path(user_dir, "FAIRe-Galaxy")),
                        winslash = "/", mustWork = FALSE)
  marker <- file.path(home, ".faire_app_version")
  app <- file.path(home, "shiny")
  say <- function(...) cat(..., "\n", sep = "")

  if (getRversion() < "4.1.0") {
    stop("The FAIRe tools app needs R 4.1 or later. Install a newer R from https://cloud.r-project.org ",
         "and run this line again.", call. = FALSE)
  }

  # The commit at the tip of the branch, read from git's own list of branches on GitHub.
  latest_commit <- function() {
    tryCatch({
      con <- url(sprintf("https://github.com/%s.git/info/refs?service=git-upload-pack", repo), "rb")
      on.exit(close(con))
      bytes <- readBin(con, "raw", 5e6)
      bytes[bytes == as.raw(0)] <- as.raw(32)
      text <- rawToChar(bytes)
      hit <- regmatches(text, regexpr(sprintf("[0-9a-f]{40} refs/heads/%s", branch), text))
      if (length(hit)) substr(hit, 1, 40) else NA_character_
    }, error = function(e) NA_character_, warning = function(w) NA_character_)
  }

  # Download one commit of the repository and unpack it; returns the unpacked folder.
  download_repo <- function(commit) {
    ref <- if (is.na(commit)) branch else commit
    zipfile <- tempfile(fileext = ".zip")
    old <- options(timeout = max(600, getOption("timeout")))
    on.exit({ options(old); unlink(zipfile) }, add = TRUE)
    say("Downloading the FAIRe tools (about 4 MB) ...")
    utils::download.file(sprintf("https://github.com/%s/archive/%s.zip", repo, ref), zipfile,
                         mode = "wb", quiet = TRUE)
    unpacked <- tempfile("faire_download_")
    utils::unzip(zipfile, exdir = unpacked)
    top <- list.files(unpacked, full.names = TRUE)
    if (length(top) != 1 || !file.exists(file.path(top, "shiny", "app.R"))) {
      stop("The download does not look like the FAIRe-Galaxy repository. Try again later.", call. = FALSE)
    }
    top
  }

  # Replace the copy in `home` with the download, keeping the Python environment setup.R made in
  # shiny/.venv, so that a new version only installs what has changed.
  install_copy <- function(src, commit) {
    dir.create(home, recursive = TRUE, showWarnings = FALSE)
    for (p in list.files(home, all.files = TRUE, no.. = TRUE, full.names = TRUE)) {
      if (basename(p) == "shiny") {
        for (q in list.files(p, all.files = TRUE, no.. = TRUE, full.names = TRUE)) {
          if (basename(q) != ".venv") unlink(q, recursive = TRUE, force = TRUE)
        }
      } else {
        unlink(p, recursive = TRUE, force = TRUE)
      }
    }
    ok <- file.copy(list.files(src, all.files = TRUE, no.. = TRUE, full.names = TRUE), home,
                    recursive = TRUE, overwrite = TRUE)
    unlink(dirname(src), recursive = TRUE)
    if (!all(ok) || !file.exists(file.path(app, "app.R"))) {
      stop("Could not copy the FAIRe tools into ", home, ". If the app is open in another R session, ",
           "close it and run this line again.", call. = FALSE)
    }
    writeLines(if (is.na(commit)) "unknown" else commit, marker)
  }

  # Run one of the app's own scripts (setup.R or run_app.R) from the shiny folder.
  run_script <- function(file) {
    owd <- setwd(app)
    on.exit(setwd(owd))
    source(file, local = new.env())
  }

  ours <- file.exists(marker)
  own_copy <- !ours && file.exists(file.path(app, "app.R")) && dir.exists(file.path(home, "tools"))
  empty <- !dir.exists(home) || length(list.files(home, all.files = TRUE, no.. = TRUE)) == 0
  if (!ours && !own_copy && !empty) {
    stop(home, " already exists and is not a copy of the FAIRe tools. Choose another folder with ",
         "Sys.setenv(FAIRE_HOME = \"...\") and run this line again.", call. = FALSE)
  }

  fresh <- FALSE
  if (own_copy) {
    say("Using your own copy of FAIRe-Galaxy in ", home, ". To update it, download it again or use git pull.")
  } else {
    installed <- if (ours) readLines(marker, warn = FALSE)[1] else NA_character_
    latest <- latest_commit()
    if (empty) {
      say("Installing the FAIRe tools app in ", home)
      install_copy(download_repo(latest), latest)
      fresh <- TRUE
    } else if (is.na(latest)) {
      say("Could not check for a newer version (no internet connection?). Starting the copy you have.")
    } else if (!identical(installed, latest)) {
      say("A newer version of the FAIRe tools app is available. Updating the copy in ", home)
      install_copy(download_repo(latest), latest)
      fresh <- TRUE
    } else {
      say("The FAIRe tools app in ", home, " is up to date.")
    }
  }

  windows <- .Platform$OS.type == "windows"
  venv_python <- file.path(app, ".venv", if (windows) "Scripts/python.exe" else "bin/python")
  r_ready <- all(vapply(c("shiny", "bslib", "DT", "processx", "openxlsx", "readxl"),
                        requireNamespace, logical(1), quietly = TRUE))
  if (fresh || !file.exists(venv_python) || !r_ready || nzchar(Sys.getenv("FAIRE_SETUP"))) {
    say("\nSetting up the app (about 15 minutes the first time) ...\n")
    tryCatch(run_script("setup.R"), error = function(e) {
      stop(conditionMessage(e), "\n\nIf Python is missing, install Python 3.13 from https://www.python.org ",
           "(on Windows, tick 'Add python.exe to PATH' on the installer's first screen), restart R or RStudio, ",
           "and run this line again. shiny/README.md has more help.", call. = FALSE)
    })
  }

  say("\nStarting the FAIRe tools app. It opens in your web browser; to stop it, press Esc in the ",
      "R console (or Stop in RStudio).")
  run_script("run_app.R")
})
