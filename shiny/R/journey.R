# The journey through the app: seven stages, each with a status, and the next step to take, worked out
# from what the app already knows (its files, mapping, review, project values, workbook and checks). The
# next-step card, the journey bar, the FAIRe mapper's step list and the boxes of e. all show this one
# result, so they cannot disagree. journey_status() takes plain facts and returns plain values, so it can
# be tested without the app (tests/test_journey.R).

JOURNEY <- data.frame(
  id = c("files", "map", "review", "project", "build", "check", "convert"),
  label = c("Prepare files", "Map sample information", "Review matches", "Complete methods and project information",
            "Add DNA results and build the workbook", "Check the workbook", "Export or convert"),
  short = c("Prepare files", "Map samples", "Review matches", "Methods and project", "DNA results and workbook",
            "Check", "Export or convert"),
  # the tool or FAIRe name, shown second
  term = c("Identify your files", "FAIRe mapper: propose mapping", "The review sheet", "projectMetadata",
           "sampleMetadata, otuFinal and experimentRunMetadata, or ampData", "FAIRe-fier",
           "NCBI, ENA, GBIF, OBIS or QIIME 2"),
  stringsAsFactors = FALSE)

# The five states, each with an icon and a word, so none relies on colour alone. "skip" is a stage the
# person's way through does not need (stages 1 to 5 when they bring a FAIRe workbook of their own).
STATUS_WORD <- c(done = "Done", todo = "To do", optional = "Optional", stale = "Out of date", blocked = "Waiting",
                 skip = "Not needed")
STATUS_ICON <- c(done = "circle-check", todo = "circle-exclamation", optional = "circle-dot", stale = "rotate",
                 blocked = "lock", skip = "minus")

plural <- function(n, one, many = paste0(one, "s")) paste(n, if (n == 1) one else many)

# A list of names, shortened after four
name_list <- function(x, n = 4) {
  if (length(x) <= n) return(paste(x, collapse = ", "))
  paste0(paste(x[seq_len(n)], collapse = ", "), " and ", length(x) - n, " more")
}

# facts: a list with
#   n_files, n_unidentified (files not yet identified, FAIRe workbooks aside), identified, demo,
#   faire_workbooks (FAIRe workbooks among Your files), template_href (a blank template made, or ""),
#   mapped, map_failed, n_columns, review ("unsaved", "unreviewed" or ""), review_saved, n_open (columns
#   for review with no decision), n_pv, missing (mandatory project terms still to give), project_id,
#   assay_type, n_dna, written, stale, workbook (the workbook in use, or ""), checked (NULL, or a list with
#   valid and errors), check_current (that check was of the workbook in use, after it was written),
#   converted (the conversions written)
journey_status <- function(f) {
  g <- function(k, d) if (is.null(f[[k]])) d else f[[k]]
  n_files <- g("n_files", 0); n_unid <- g("n_unidentified", 0); mapped <- isTRUE(f$mapped)
  n_pv <- g("n_pv", 0); missing <- g("missing", character()); pid <- g("project_id", "")
  targeted <- identical(f$assay_type, "targeted"); written <- isTRUE(f$written); stale <- isTRUE(f$stale)
  wbs <- g("faire_workbooks", character()); checked <- f$checked; current <- isTRUE(f$check_current)
  converted <- g("converted", character())
  started <- mapped || isTRUE(f$identified) || n_pv > 0 || n_unid > 0 || isTRUE(f$demo) || written
  path <- if (started) "mapper" else if (length(wbs) || nzchar(g("workbook", ""))) "workbook"
          else if (nzchar(g("template_href", ""))) "template" else if (n_files == 0) "empty" else "mapper"

  st <- JOURNEY
  st$status <- "todo"; st$detail <- ""; st$done_text <- ""
  set <- function(id, status, detail = "", done_text = "") {
    k <- match(id, st$id)
    st$status[k] <<- status; st$detail[k] <<- detail; st$done_text[k] <<- done_text
  }
  passes <- current && isTRUE(checked$valid)
  if (path %in% c("mapper", "empty")) {
    # 1. files
    if (n_files == 0) set("files", "todo", "No files yet")
    # identifying is a help, not a gate: once the table is mapped, files not yet identified are optional
    else if (n_unid > 0 && mapped) set("files", "optional", paste(plural(n_unid, "file"), "not identified (optional)"))
    else if (n_unid > 0) set("files", "todo", paste(plural(n_unid, "file"), "not identified yet"))
    else set("files", "done", paste(plural(n_files, "file"), "identified"), paste(plural(n_files, "file"), "identified"))
    # 2. map
    if (mapped) set("map", "done", paste("Mapping proposed for", plural(g("n_columns", 0), "column")), "Mapping proposed")
    else if (isTRUE(f$map_failed)) set("map", "todo", "The mapping stopped: see why in b")
    else if (n_files == 0) set("map", "blocked", "Waits for your files (step 1)")
    else set("map", "todo", "Your sample table is not mapped yet")
    # 3. review
    n_open <- g("n_open", 0)
    if (!mapped) set("review", "blocked", "Waits for a mapping (step 2)")
    else if (identical(f$review, "unsaved")) set("review", "todo", "Changes not saved yet")
    else if (!isTRUE(f$review_saved))
      set("review", "todo", if (n_open) paste(plural(n_open, "column"), "need your decision") else "Check the matches and save")
    else set("review", "done", if (n_open) paste0("Saved; ", plural(n_open, "column"), " left undecided") else "Review saved",
             "Review saved")
    # 4. project information. Before a mapping, the mandatory terms still missing are not known yet.
    if (n_pv == 0) set("project", "todo", "No method or project values yet")
    else if (!nzchar(pid) && !length(missing)) set("project", "todo", "No project ID yet")
    else if (length(missing)) set("project", "todo", paste(plural(length(missing), "mandatory term"), "still missing"))
    else set("project", "done", paste(plural(n_pv, "value"), "given"), "Project information complete")
    # 5. DNA results and the workbook
    dna <- if (targeted) "qPCR or ddPCR results" else "OTU or ASV tables"
    if (stale) set("build", "stale", "The review or project values changed after it was built")
    else if (written) set("build", "done", "Workbook built", "Workbook built")
    else if (!mapped) set("build", "blocked", "Waits for a mapping (step 2)")
    else if (!nzchar(pid)) set("build", "blocked", "Needs a project ID (step 4)")
    else if (g("n_dna", 0) == 0) set("build", "todo", paste("No", dna, "chosen yet"))
    else set("build", "todo", "Ready to build")
  } else {
    why <- if (path == "template") "You are filling in a blank template" else "You have a FAIRe workbook"
    for (id in JOURNEY$id[1:5]) set(id, "skip", why)
  }
  # 6. check
  has_wb <- nzchar(g("workbook", "")) || length(wbs)
  if (path == "template" && !length(wbs)) set("check", "blocked", "Waits for your filled-in template")
  else if (!has_wb) set("check", "blocked", "Waits for a workbook (step 5)")
  else if (stale && path == "mapper") set("check", "blocked", "Rebuild the workbook first (step 5)")
  else if (passes) set("check", "done", "The workbook passes", "The workbook passes FAIRe-fier")
  else if (current && !is.null(checked)) set("check", "todo", paste(plural(g2(checked$errors), "error"), "to fix"))
  else set("check", "todo", "Not checked yet")
  # 7. convert: optional, and only worth doing once the workbook passes
  if (length(converted)) set("convert", "done", paste("Written for", name_list(converted)), paste("Written for", name_list(converted)))
  else if (passes) set("convert", "optional", "If you are publishing or analysing the data")
  else set("convert", "blocked", "Waits for a workbook that passes (step 6)")

  list(path = path, stages = st, next_step = next_step(path, st, f))
}
g2 <- function(x) if (is.null(x) || is.na(x)) 0 else x

# The one action the card offers: go to a stage (or another page), open the file chooser, or download.
go_action <- function(label, target) list(type = "go", label = label, target = target)

next_step <- function(path, st, f) {
  s <- function(id) st$status[st$id == id]
  d <- function(id) st$detail[st$id == id]
  out <- function(stage, title, attention, why, action, more = list(), state = "todo") {
    k <- match(stage, st$id)
    before <- if (!is.na(k) && k > 1) rev(st$done_text[seq_len(k - 1)][st$status[seq_len(k - 1)] == "done"]) else character()
    list(stage = stage, num = if (is.na(k)) NA else k, title = title, attention = attention, why = why, action = action,
         more = more, state = state, done = if (length(before)) before[1] else "")
  }
  targeted <- identical(f$assay_type, "targeted")
  if (path == "empty")
    return(out("files", "Add your files to start", "No files yet.",
               "The tools read your sample table, methods and DNA results as they are, in your own formats.",
               list(type = "upload", label = "Add files"),
               list(go_action("Try the demonstration data", "start"), go_action("Make a blank template instead", "faireator"))))
  if (path == "template" && s("check") == "blocked")
    return(out("check", "Fill in your template", "FAIRe-ator has made a blank template for you.",
               "Fill it in with Excel or another spreadsheet program, add it to Your files, then check it.",
               list(type = "link", label = "Download the template", href = f$template_href),
               list(list(type = "upload", label = "Add the filled-in template"))))
  first <- st$id[st$status %in% c("todo", "stale")][1]
  if (!is.na(first)) {
    return(switch(first,
      files = out("files", "Identify your files", paste0(d("files"), "."),
                  "The app then says what each file is and offers it in the step it belongs to.",
                  go_action("Go to a. Prepare your files", "files")),
      map = if (isTRUE(f$map_failed)) out("map", "The mapping stopped", "The result in b says why and what to do.",
                                          "The mapping proposes a FAIRe term for each column of your sample table.",
                                          go_action("Go to b. Map sample information", "map"))
            else out("map", "Map your sample information", "Your sample table is not mapped yet.",
                     "The mapper proposes a FAIRe term for each column of your sample table.",
                     go_action("Go to b. Map sample information", "map")),
      review = if (s("review") == "todo" && identical(f$review, "unsaved"))
                 out("review", "Save your review", "You have changed decisions that are not saved yet.",
                     "The workbook is built from the saved review.", go_action("Go to c. Review the matches", "review"))
               else out("review", "Review the uncertain matches",
                        if (g2(f$n_open)) paste0(plural(f$n_open, "column"), " need", if (f$n_open == 1) "s" else "",
                                                 " your decision.")
                        else "No column needs a decision, but check the matches and save the review.",
                        "Your decisions set which FAIRe term each column of your table goes to.",
                        go_action("Go to c. Review the matches", "review")),
      project = if (g2(f$n_pv) == 0)
                  out("project", "Find the primers and method details", "No method or project values yet.",
                      "Most of the project information comes from your methods: the primers, kits, PCR and sequencing.",
                      go_action("Go to d. Methods and project information", "project"))
                else if (length(f$missing))
                  out("project", "Complete the mandatory project information",
                      paste0(plural(length(f$missing), "mandatory term"), " still missing: ", name_list(f$missing), "."),
                      "FAIRe needs every mandatory term, and repositories refuse a dataset without them.",
                      go_action("Give them in d. Methods and project information", "missing"))
                else out("project", "Give a project ID", "The project has no project_id yet.",
                         "It names the workbook and is part of every record's identifier.",
                         go_action("Give it in d. Methods and project information", "missing")),
      build = if (s("build") == "stale")
                out("build", "Rebuild the workbook", "The review or project values changed after the workbook was built.",
                    "The workbook in use does not have your latest changes yet.",
                    go_action("Go to e. DNA results and the workbook", "build"), state = "stale")
              else if (g2(f$n_dna) == 0)
                out("build", if (targeted) "Add your qPCR or ddPCR results" else "Add your DNA results",
                    paste0(if (targeted) "No qPCR or ddPCR results" else "No OTU or ASV table", " chosen yet."),
                    "The workbook joins your DNA results to the sample and project information.",
                    go_action("Go to e. DNA results and the workbook", "build"))
              else out("build", "Build the FAIRe workbook", "Everything it needs is ready: check the tables chosen in step 2, then build it.",
                       "It joins your sample, project and DNA information into one FAIRe workbook.",
                       go_action("Go to e. DNA results and the workbook", "build")),
      check = if (isTRUE(f$check_current) && !is.null(f$checked) && !isTRUE(f$checked$valid))
                out("check", "Fix the errors and check again",
                    paste0("FAIRe-fier found ", plural(g2(f$checked$errors), "error"), "."),
                    "GBIF, OBIS, NCBI and ENA accept a dataset only once it passes.",
                    go_action("See the errors on the Check page", "check"))
              else out("check", "Check the workbook",
                       if (path == "mapper") "The workbook has not been checked since it was built."
                       else "Your FAIRe workbook has not been checked yet.",
                       "FAIRe-fier finds missing mandatory fields and values in the wrong format.",
                       go_action("Go to the Check page", "check"))))
  }
  if (s("convert") == "optional")
    return(out("convert", "Convert it, if you need to", "Your workbook passes FAIRe-fier.",
               paste("Converting is optional: choose a destination only if you are publishing or analysing the data",
                     "(NCBI or ENA for sequences, GBIF or OBIS for occurrences, QIIME 2 for analysis)."),
               go_action("Go to the Convert page", "convert"), list(go_action("Download your files", "outputs")), state = "optional"))
  out("convert", "Download what you want to keep", paste0(d("convert"), "."),
      "Everything is deleted when you close the app, so download your files from Outputs.",
      go_action("Go to Outputs", "outputs"), state = "done")
}

# ---------------------------------------------------------------- what the person sees

# A status as an icon and a word, never colour alone
status_tag <- function(status, word = STATUS_WORD[[status]]) {
  tags$span(class = paste("st-tag", paste0("st-", status)), icon(STATUS_ICON[[status]], `aria-hidden` = "true"), word)
}

# Sends a navigation request to the server: to a stage (files to convert) or another page
go_js <- function(target) sprintf("Shiny.setInputValue('journey_go', '%s', {priority: 'event'})", target)

# The seven stages across the top of every page, each a button that goes to its page
journey_bar_ui <- function(j) {
  st <- j$stages
  tags$nav(
    class = "journey", `aria-label` = "Your progress",
    tags$ol(lapply(seq_len(nrow(st)), function(i) {
      cur <- identical(st$id[i], j$next_step$stage)
      tags$li(
        class = paste("j-step", paste0("st-", st$status[i]), if (cur) "j-current"),
        tags$button(
          type = "button", class = "j-link", onclick = go_js(st$id[i]), `aria-current` = if (cur) "step",
          title = paste0(st$label[i], " (", st$term[i], ")", if (nzchar(st$detail[i])) paste0(": ", st$detail[i])),
          `aria-label` = paste0("Step ", i, ", ", st$label[i], ": ", STATUS_WORD[[st$status[i]]],
                                if (nzchar(st$detail[i])) paste0(". ", st$detail[i]), if (cur) ". The next step." else ""),
          tags$span(class = "j-top", tags$span(class = "j-num", i), tags$span(class = "j-label", st$short[i])),
          tags$span(class = "j-foot", status_tag(st$status[i]), if (cur) tags$span(class = "j-next", "Next"))))
    })))
}

# The next step: what was just done, what needs attention and why, and one action
next_step_ui <- function(j, where) {
  n <- j$next_step
  action <- function(a, primary = TRUE) {
    cls <- if (primary) "btn btn-primary btn-sm ns-go" else "btn btn-link btn-sm ns-more"
    switch(a$type,
      go = tags$button(type = "button", class = cls, onclick = go_js(a$target), if (primary) icon("arrow-right"), a$label),
      upload = tags$button(type = "button", class = cls, onclick = "document.getElementById('upload').click()",
                           icon("upload"), a$label),
      link = tags$a(class = cls, href = a$href, download = NA, icon("download"), a$label))
  }
  div(class = paste("next-step-card", paste0("st-", n$state)), role = "region",
      `aria-label` = "Next step", id = paste0("next-step-", where),
      div(class = "ns-head", icon("compass"), " Next step",
          if (!is.na(n$num)) tags$span(class = "ns-num", sprintf("step %d of 7", n$num))),
      if (nzchar(n$done)) div(class = "ns-done", status_tag("done", "Done:"), n$done),
      div(class = "ns-title", n$title),
      div(class = "ns-attention", n$attention),
      div(class = "ns-why", n$why),
      action(n$action),
      if (length(n$more)) div(class = "ns-alt", lapply(n$more, action, primary = FALSE)))
}
