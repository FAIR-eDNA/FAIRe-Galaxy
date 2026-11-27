# Unit tests for the journey (R/journey.R): the next step and the stages' statuses for each situation the
# app can be in. Run from the shiny folder: Rscript tests/test_journey.R
suppressPackageStartupMessages(library(shiny))
source("R/journey.R")

failures <- 0
check <- function(what, got, want) {
  ok <- identical(got, want)
  cat(if (ok) "PASS" else "FAIL", what, if (!ok) paste0("(got '", paste(got, collapse = ", "), "', wanted '",
                                                       paste(want, collapse = ", "), "')"), "\n")
  if (!ok) failures <<- failures + 1
}
status <- function(j) setNames(j$stages$status, j$stages$id)

# A mapper journey, one stage further at each step
base <- list(n_files = 5, n_unidentified = 0, identified = TRUE, mapped = TRUE, n_columns = 20, review = "",
             review_saved = TRUE, n_open = 0, n_pv = 12, missing = character(), project_id = "P1",
             assay_type = "metabarcoding", n_dna = 1, written = TRUE, stale = FALSE, workbook = "/w/P1.xlsx",
             checked = list(valid = TRUE, errors = 0), check_current = TRUE, converted = character())
with <- function(...) modifyList(base, list(...))

# 1. No files and no workbook
j <- journey_status(list(n_files = 0))
check("1 empty: next step", j$next_step$title, "Add your files to start")
check("1 empty: the action opens the file chooser", j$next_step$action$type, "upload")
check("1 empty: offers the demonstration and a template", vapply(j$next_step$more, `[[`, "", "target"), c("start", "faireator"))
check("1 empty: later stages wait", unname(status(j)[c("map", "review", "build")]), c("blocked", "blocked", "blocked"))

# 2. Files present but not identified
j <- journey_status(list(n_files = 3, n_unidentified = 3))
check("2 not identified: next step", j$next_step$title, "Identify your files")
check("2 not identified: says how many", j$next_step$attention, "3 files not identified yet.")
check("2 not identified: files to do", unname(status(j)["files"]), "todo")

# Identifying is optional once the table is mapped: the next step moves on
j <- journey_status(list(n_files = 3, n_unidentified = 3, mapped = TRUE, n_columns = 10, review = "unreviewed",
                         n_open = 2))
check("2 mapped without identifying: files optional", unname(status(j)["files"]), "optional")
check("2 mapped without identifying: next step is the review", j$next_step$title, "Review the uncertain matches")

# 3. Identified, no mapping
j <- journey_status(list(n_files = 3, identified = TRUE))
check("3 no mapping: next step", j$next_step$title, "Map your sample information")
check("3 no mapping: just done", j$next_step$done, "3 files identified")

# 4. Mapping with rows to review
j <- journey_status(with(review_saved = FALSE, review = "unreviewed", n_open = 7, n_pv = 0, written = FALSE,
                         workbook = "", checked = NULL, check_current = FALSE))
check("4 to review: next step", j$next_step$title, "Review the uncertain matches")
check("4 to review: states the number", j$next_step$attention, "7 columns need your decision.")
check("4 to review: target", j$next_step$action$target, "review")

# 5. Review changed but not saved (even after an earlier save)
j <- journey_status(with(review = "unsaved", written = FALSE, workbook = "", checked = NULL, check_current = FALSE))
check("5 unsaved: next step", j$next_step$title, "Save your review")
check("5 unsaved: review to do", unname(status(j)["review"]), "todo")

# 6. Review saved, no project or method values
j <- journey_status(with(n_pv = 0, project_id = "", written = FALSE, workbook = "", checked = NULL, check_current = FALSE))
check("6 no values: next step", j$next_step$title, "Find the primers and method details")
check("6 no values: just done", j$next_step$done, "Review saved")

# 7. Mandatory project values missing
j <- journey_status(with(missing = c("recordedBy", "project_contact", "project_id"), project_id = "", written = FALSE,
                         workbook = "", checked = NULL, check_current = FALSE))
check("7 missing: next step", j$next_step$title, "Complete the mandatory project information")
check("7 missing: states the number", grepl("^3 mandatory terms still missing", j$next_step$attention), TRUE)
check("7 missing: goes to the missing terms", j$next_step$action$target, "missing")
check("7 missing: building waits for a project ID", unname(status(j)["build"]), "blocked")

# 8. Sample and project information ready, no DNA results
j <- journey_status(with(n_dna = 0, written = FALSE, workbook = "", checked = NULL, check_current = FALSE))
check("8 no DNA results: next step", j$next_step$title, "Add your DNA results")
j <- journey_status(with(n_dna = 0, assay_type = "targeted", written = FALSE, workbook = "", checked = NULL, check_current = FALSE))
check("8 targeted: asks for qPCR or ddPCR results", j$next_step$title, "Add your qPCR or ddPCR results")

# 9. Ready to build
j <- journey_status(with(written = FALSE, workbook = "", checked = NULL, check_current = FALSE))
check("9 ready: next step", j$next_step$title, "Build the FAIRe workbook")
check("9 ready: check waits for a workbook", unname(status(j)["check"]), "blocked")

# 10. Workbook out of date
j <- journey_status(with(stale = TRUE, check_current = FALSE))
check("10 stale: next step", j$next_step$title, "Rebuild the workbook")
check("10 stale: build out of date", unname(status(j)["build"]), "stale")
check("10 stale: check waits for the rebuild", unname(status(j)["check"]), "blocked")

# 11. Written but not checked since
j <- journey_status(with(checked = NULL, check_current = FALSE))
check("11 not checked: next step", j$next_step$title, "Check the workbook")
check("11 not checked: just done", j$next_step$done, "Workbook built")
j <- journey_status(with(checked = list(valid = TRUE, errors = 0), check_current = FALSE))
check("11 checked before it was rebuilt: still to check", j$next_step$title, "Check the workbook")

# 12. FAIRe-fier failed
j <- journey_status(with(checked = list(valid = FALSE, errors = 4)))
check("12 failed: next step", j$next_step$title, "Fix the errors and check again")
check("12 failed: states the errors", j$next_step$attention, "FAIRe-fier found 4 errors.")
check("12 failed: convert waits", unname(status(j)["convert"]), "blocked")

# 13. Passed: converting is optional
j <- journey_status(base)
check("13 passed: next step", j$next_step$title, "Convert it, if you need to")
check("13 passed: convert optional", unname(status(j)["convert"]), "optional")
check("13 passed: every earlier stage done", unname(status(j)[1:6]), rep("done", 6))
j <- journey_status(with(converted = c("GBIF (Darwin Core)")))
check("13 converted: download", j$next_step$title, "Download what you want to keep")

# A FAIRe workbook of their own: stages 1 to 5 are not needed
j <- journey_status(list(n_files = 1, faire_workbooks = "mine.xlsx"))
check("own workbook: stages 1 to 5 not needed", unname(status(j)[1:5]), rep("skip", 5))
check("own workbook: next step", j$next_step$title, "Check the workbook")
j <- journey_status(list(n_files = 1, faire_workbooks = "mine.xlsx", checked = list(valid = TRUE, errors = 0),
                         check_current = TRUE))
check("own workbook passes: convert", j$next_step$title, "Convert it, if you need to")

# A blank template from FAIRe-ator
j <- journey_status(list(n_files = 0, template_href = "files/P1.xlsx"))
check("template: next step", j$next_step$title, "Fill in your template")
check("template: downloads it", j$next_step$action$type, "link")
j <- journey_status(list(n_files = 1, template_href = "files/P1.xlsx", faire_workbooks = "P1.xlsx"))
check("template filled in and added: check it", j$next_step$title, "Check the workbook")

# A mapping that stopped
j <- journey_status(list(n_files = 3, identified = TRUE, map_failed = TRUE))
check("mapping stopped: next step", j$next_step$title, "The mapping stopped")

# The same status everywhere: the bar's current stage is the card's stage
j <- journey_status(with(n_dna = 0, written = FALSE, workbook = "", checked = NULL, check_current = FALSE))
bar <- as.character(journey_bar_ui(j))
check("bar marks the card's stage as current", grepl('j-step st-todo j-current', bar, fixed = TRUE), TRUE)
check("bar gives each stage a word, not only a colour", all(vapply(STATUS_WORD[c("done", "todo")], grepl, logical(1), bar, fixed = TRUE)), TRUE)
card <- as.character(next_step_ui(j, "side"))
check("card has one primary action", lengths(regmatches(card, gregexpr("ns-go", card, fixed = TRUE))), 1L)

cat(if (failures) paste(failures, "failed") else "All passed", "\n")
if (failures) quit(status = 1)
