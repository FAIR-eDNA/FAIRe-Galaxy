# Start the FAIRe tools app and open it in your web browser.
#
#   Rscript run_app.R        (or source("run_app.R") in RStudio, with this folder as the working directory)
#
# The app finds the FAIRe tools in ../tools (the tools folder of the FAIRe-Galaxy repository). Set
# FAIRE_TOOLS_DIR to use a copy somewhere else, and FAIRE_PYTHON to use a Python other than the one
# setup.R made in .venv.

app_dir <- normalizePath(".")
if (!file.exists(file.path(app_dir, "app.R"))) stop("Run run_app.R from the folder that holds app.R.")
options(faire.app_dir = app_dir)
port <- as.integer(Sys.getenv("FAIRE_PORT", "7788"))
shiny::runApp(app_dir, port = port, launch.browser = interactive() || Sys.getenv("FAIRE_NO_BROWSER") == "",
              host = "127.0.0.1")
