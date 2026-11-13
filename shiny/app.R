# FAIRe tools: a Shiny app that brings together the FAIRe eDNA metadata tools (FAIRe-ator, the
# FAIRe mapper, FAIRe-fier, FAIRe2NCBI, FAIRe2ENA, FAIRe2MDT, edna2obis and FAIRe2QIIME).
#
# The app runs the same scripts, with the same arguments, as the Galaxy wrappers in ../tools, so
# it and the Galaxy eDNA Lab give the same results. Start it with run_app.R (see README.md).

suppressPackageStartupMessages({
  library(shiny)
  library(bslib)
  library(DT)
})

if (is.null(getOption("faire.app_dir"))) options(faire.app_dir = normalizePath("."))
for (f in c("runner.R", "tools.R", "helpers.R", "ui.R"))
  source(file.path(getOption("faire.app_dir"), "R", f), local = FALSE)

options(shiny.maxRequestSize = 500 * 1024^2, DT.fillContainer = FALSE)

APP_VERSION <- "0.3.0"
DEMO_DIR <- file.path(getOption("faire.app_dir"), "demo")

theme <- bs_theme(version = 5, primary = "#1f6f78", secondary = "#5b6770", success = "#3c8d5a",
                  "font-size-base" = "0.95rem", base_font = font_collection("Segoe UI", "Helvetica Neue", "Arial", "sans-serif"))

ui <- page_navbar(
  id = "main",
  fillable = FALSE,
  title = tags$span(icon("dna"), "FAIRe tools"),
  window_title = "FAIRe tools",
  theme = theme,
  header = tags$head(tags$link(rel = "stylesheet", href = "styles.css")),
  sidebar = sidebar(
    width = 300, open = "desktop",
    tags$h6("Workbook in use"),
    uiOutput("current_workbook"),
    tags$hr(),
    tags$h6("Your files"),
    fileInput("upload", NULL, multiple = TRUE, buttonLabel = "Add files", placeholder = "sample tables, OTU tables, ..."),
    uiOutput("file_list")
  ),
  start_page(),
  nav_menu(
    "1. Make a workbook", icon = icon("table"),
    faireator_panel(),
    mapper_panel()
  ),
  check_page(),
  convert_page(),
  outputs_page(),
  nav_spacer(),
  nav_item(tags$span(class = "version", paste("version", APP_VERSION)))
)

server <- function(input, output, session) {
  # ------------------------------------------------------------ the session's folder
  sd <- file.path(tempdir(), paste0("faire_", substr(session$token, 1, 12)))
  dir.create(sd, recursive = TRUE, showWarnings = FALSE)
  sd <- normalizePath(sd, winslash = "/")
  prefix <- paste0("files_", substr(session$token, 1, 16))
  addResourcePath(prefix, sd)
  session$onSessionEnded(function() {
    try(removeResourcePath(prefix), silent = TRUE)
    unlink(sd, recursive = TRUE)
  })

  rv <- reactiveValues(files = character(), workbook = NULL, workbook_from = "", res = list(), runs = list(),
                       identify = NULL, map = NULL, map_args = NULL, profile = NULL, crosswalk = NULL,
                       crosswalk_from = "", review_version = 0, review_saved = NULL, model = NULL,
                       primers = NULL, pv = data.frame(term = character(), value = character(), assay = character()),
                       otu_n = 1, lib_n = 1, block_version = 0, demo = FALSE, eo_mapping = NULL)

  # ------------------------------------------------------------ shared helpers
  file_href <- function(path) {
    p <- normalizePath(path, winslash = "/")
    rel <- substring(p, nchar(sd) + 2)
    paste0(prefix, "/", paste(vapply(strsplit(rel, "/")[[1]], utils::URLencode, character(1), reserved = TRUE),
                              collapse = "/"))
  }
  file_link <- function(path, label = basename(path)) tags$a(href = file_href(path), download = basename(path), label)

  record <- function(res) {
    rv$runs[[length(rv$runs) + 1]] <- res
    res
  }

  # Run a tool with a progress message; record and return its result.
  with_run <- function(message, expr) {
    res <- withProgress(message = message, value = 0.3, expr)
    record(res)
    if (!res$ok) showNotification(paste(res$label, "stopped with a message. See the result for why."),
                                  type = "warning", duration = 6)
    res
  }

  set_workbook <- function(path, from) {
    rv$workbook <- path
    rv$workbook_from <- from
  }

  # The result of a run: whether it worked, its files, and the tool's own messages.
  result_ui <- function(res, extra = NULL, show_files = TRUE) {
    if (is.null(res)) return(NULL)
    status <- if (res$ok) div(class = "res-ok", icon("circle-check"), paste(res$label, "finished at", res$time))
              else div(class = "res-fail", icon("triangle-exclamation"),
                       paste(res$label, "stopped at", res$time, "with the message below."))
    files <- NULL
    if (show_files && length(res$outputs)) {
      files <- tags$ul(class = "file-out", lapply(names(res$outputs), function(nm) {
        p <- res$outputs[[nm]]
        tags$li(icon("file"), file_link(p), tags$span(class = "size", fmt_bytes(file.size(p))))
      }))
    }
    tagList(status, extra, files,
            tags$details(open = if (!res$ok) NA else NULL, tags$summary("The tool's messages"),
                         tags$pre(class = "log", short_log(res$log, 60))))
  }

  table_dt <- function(df, page = 10, ...) {
    datatable(df, rownames = FALSE, class = "compact stripe",
              options = list(scrollX = TRUE, pageLength = page, dom = if (nrow(df) > page) "ftip" else "t", ...))
  }

  # Choices from the files the person added: those whose names end as the pattern says, and those
  # a. Your files found to be of one of the kinds (a FASTA file need not end in .fa, say).
  file_names <- function(pattern = NULL, kinds = NULL) {
    n <- names(rv$files)
    if (is.null(pattern) && is.null(kinds)) return(n)
    by_name <- if (is.null(pattern)) rep(FALSE, length(n)) else grepl(pattern, n, ignore.case = TRUE)
    by_kind <- if (is.null(kinds)) rep(FALSE, length(n)) else vapply(n, function(f) kind_of(f) %in% kinds, logical(1))
    n[by_name | by_kind]
  }
  kind_of <- function(name) {
    idf <- rv$identify
    if (is.null(idf)) return("")
    k <- idf$kind[idf$file == name]
    if (length(k)) k[1] else ""
  }
  guess_file <- function(kind) {
    idf <- rv$identify
    if (is.null(idf)) return("")
    f <- idf$file[idf$kind == kind]
    if (length(f)) f[1] else ""
  }
  fpath <- function(name) if (blank(name) || !name %in% names(rv$files)) NULL else unname(rv$files[[name]])
  keep_or <- function(id, default) {
    v <- isolate(input[[id]])
    if (is.null(v) || (length(v) == 1 && !nzchar(v))) default else v
  }

  # ------------------------------------------------------------ start page
  output$setup_table <- renderUI({
    s <- check_setup()
    tags$table(class = "table table-sm setup", tags$tbody(lapply(seq_len(nrow(s)), function(i) tags$tr(
      tags$td(if (s$ok[i]) icon("circle-check", class = "text-success") else icon("circle-xmark", class = "text-danger")),
      tags$td(s$item[i]), tags$td(tags$small(s$detail[i]))))))
  })

  observeEvent(input$load_demo, {
    for (f in list.files(DEMO_DIR, full.names = TRUE)) {
      if (basename(f) == "README.md") next
      rv$files <- c(rv$files[names(rv$files) != basename(f)], add_to_library(file.path(sd, "files"), basename(f), f))
    }
    rv$demo <- TRUE
    pv <- read_tsv(file.path(DEMO_DIR, "SEA-MES_project_values_Fish16S.tsv"))
    if (!is.null(pv)) rv$pv <- pv[, c("term", "value", "assay")]
    rv$otu_n <- 2; rv$lib_n <- 1; rv$block_version <- rv$block_version + 1
    updateCheckboxGroupInput(session, "map_sample_types", selected = "Water")
    updateRadioButtons(session, "map_assay_type", selected = "metabarcoding")
    updateTextInput(session, "fa_project_id", value = "SEA-MES_eDNA")
    updateTextInput(session, "fa_assay_name", value = "Fish16S")
    updateTextInput(session, "ap_project_id", value = "SEA-MES_eDNA")
    updateTextInput(session, "ap_assay_name", value = "Fish16S")
    updateTextInput(session, "ap_country", value = "Australia")
    updateTextInput(session, "nb_bioproject", value = "PRJNA1263580")
    updateSelectInput(session, "nb_mandatory_fill", selected = "not applicable")
    updateTextInput(session, "nb_duplicates", value = "replicate")
    updateSelectInput(session, "ns_instrument", selected = "NextSeq 2000")
    updateRadioButtons(session, "ns_link", selected = "accessions")
    updateTextInput(session, "es_center", value = "CSIRO")
    updateTextInput(session, "er_center", value = "CSIRO")
    updateTextInput(session, "er_study", value = "PRJNA1263580")
    updateSelectInput(session, "er_instrument", selected = "NextSeq 2000")
    updateRadioButtons(session, "eo_taxa_source", selected = "mapping")
    showNotification("The demonstration files are in Your files. Start with 1. Make a workbook, FAIRe mapper.",
                     type = "message", duration = 6)
  })

  output$demo_status <- renderUI({
    if (!rv$demo) return(NULL)
    div(class = "demo-steps",
        tags$p(tags$b("Demonstration loaded."), " To follow it through:"),
        tags$ol(
          tags$li(HTML("In <em>1. Make a workbook, FAIRe mapper</em>, run <em>a. Your files</em> and",
                       "<em>b. Propose a mapping</em> on SEA-MES_10L_samples.csv.")),
          tags$li(HTML("In <em>c. Review</em>, decide the six rows for review. The authors' answers: Accept",
                       "Control_Neg as samp_category (Y marks the field controls), *depth as the sampling depth and",
                       "samp_vol_we_dna_ext; Reject replicate, bioproject_accession and Location, which are kept as",
                       "their own terms. <em>Fill in the authors' answers</em> does this for you. Save the review.")),
          tags$li(HTML("In <em>d.</em>, find primers in methods.txt. The project values are filled in already.")),
          tags$li(HTML("In <em>e.</em>, write the workbook, then check it (2) and convert it (3).")),
          tags$li("FAIRe-fier passes both sheets, with a warning for each column kept as your own term (the",
                  "checklist does not list them). Every conversion runs on the workbook as it is.")))
  })

  # ------------------------------------------------------------ your files
  observeEvent(input$upload, {
    up <- input$upload
    for (i in seq_len(nrow(up))) {
      rv$files <- c(rv$files[names(rv$files) != sub("\\.gz$", "", up$name[i])],
                    add_to_library(file.path(sd, "files"), up$name[i], up$datapath[i]))
    }
  })

  output$file_list <- renderUI({
    if (!length(rv$files)) return(help_text("No files yet. Add yours, or load the demonstration data on the Start page."))
    tagList(
      tags$ul(class = "lib", lapply(names(rv$files), function(n) {
        k <- kind_of(n)
        ic <- if (grepl("xlsx$", n, ignore.case = TRUE)) "file-excel" else if (grepl("pdf$", n, ignore.case = TRUE)) "file-pdf"
              else if (k == "sequences (FASTA)" || grepl("\\.(fa|fasta|fna|fas)$", n, ignore.case = TRUE)) "dna"
              else if (grepl("txt$|md$", n, ignore.case = TRUE)) "file-lines" else "file-csv"
        tags$li(title = n, icon(ic), tags$span(class = "fname", n), if (nzchar(k)) tags$span(class = "kind", k),
                tags$button(type = "button", class = "rm-file", title = paste("Remove", n), `aria-label` = paste("Remove", n),
                            onclick = sprintf("Shiny.setInputValue('remove_file', %s, {priority: 'event'})",
                                              jsonlite::toJSON(n, auto_unbox = TRUE)),
                            icon("xmark")))
      })),
      actionLink("clear_files", "Remove all files", icon = icon("xmark")))
  })
  observeEvent(input$clear_files, { rv$files <- character(); rv$identify <- NULL })
  # One file at a time. The run folders keep their copies, so results already written are not affected.
  observeEvent(input$remove_file, {
    n <- input$remove_file
    if (!n %in% names(rv$files)) return()
    rv$files <- rv$files[names(rv$files) != n]
    if (!is.null(rv$identify)) {
      rv$identify <- rv$identify[rv$identify$file != n, , drop = FALSE]
      if (!nrow(rv$identify)) rv$identify <- NULL
    }
    showNotification(paste("Removed", n), type = "message", duration = 3)
  })

  output$current_workbook <- renderUI({
    if (is.null(rv$workbook)) return(help_text("None yet. Write one with the FAIRe mapper, or choose one of your files on the Check page."))
    div(class = "wb-card", icon("file-excel"), file_link(rv$workbook), tags$br(), tags$small(rv$workbook_from))
  })

  # Workbook pickers on the Check and Convert pages: the workbook in use, or one of your files.
  workbook_choices <- reactive({
    ch <- c()
    if (!is.null(rv$workbook)) ch <- c(ch, setNames("__current__", paste("Workbook in use:", basename(rv$workbook))))
    xl <- file_names("\\.xlsx$")
    if (length(xl)) ch <- c(ch, setNames(paste0("file:", xl), paste("Your files:", xl)))
    ch
  })
  for (pid in c("ck_wb", "cv_wb")) local({
    id <- pid
    output[[paste0(id, "_ui")]] <- renderUI({
      ch <- workbook_choices()
      if (!length(ch)) return(help_text("No workbook yet. Write one with the FAIRe mapper, or add a FAIRe workbook to your files."))
      cur <- isolate(input[[id]])
      selectInput(id, "Workbook", ch, selected = if (!is.null(cur) && cur %in% ch) cur else ch[1])
    })
  })
  picked_workbook <- function(id) {
    v <- input[[id]]
    if (is.null(v)) return(NULL)
    if (v == "__current__") return(rv$workbook)
    fpath(sub("^file:", "", v))
  }

  # ------------------------------------------------------------ FAIRe-ator
  observeEvent(input$run_faireator, {
    pid <- trimws(input$fa_project_id)
    if (!nzchar(pid) || grepl("[^A-Za-z0-9_.-]", pid))
      return(showNotification("Give a project ID with no spaces or special characters.", type = "error"))
    if (blank(input$fa_assay_name)) return(showNotification("Give at least one assay name.", type = "error"))
    if (!length(input$fa_sample_type)) return(showNotification("Choose at least one sample type.", type = "error"))
    rv$res$faireator <- with_run("Making the template", run_faireator(
      sd, pid, input$fa_assay_type, input$fa_assay_name, input$fa_sample_type, input$fa_req_lev,
      input$fa_project_fields, input$fa_sample_fields))
  })
  output$faireator_result <- renderUI({
    res <- rv$res$faireator
    if (is.null(res)) return(help_text("The template appears here."))
    result_ui(res, extra = if (res$ok) help_text(
      "Download the template and fill it in, in Excel or another spreadsheet program. The requirement levels are",
      "colour coded, and a Drop-down values sheet holds the allowed values. Then add it to your files and check it",
      "with FAIRe-fier."))
  })

  # ------------------------------------------------------------ mapper a: identify
  observeEvent(input$run_identify, {
    if (!length(rv$files)) return(showNotification("Add your files first.", type = "error"))
    res <- with_run("Looking at your files", run_identify(sd, as.list(rv$files)))
    rv$res$identify <- res
    if (res$ok) rv$identify <- read_tsv(res$outputs$report)
  })
  output$identify_result <- renderUI({
    res <- rv$res$identify
    if (is.null(res)) return(NULL)
    tagList(result_ui(res, show_files = FALSE), if (!is.null(rv$identify)) uiOutput("identify_table"))
  })
  # Each file, what it seems to be (which the person can correct) and where it goes in this app.
  output$identify_table <- renderUI({
    d <- rv$identify; req(d)
    rows <- lapply(seq_len(nrow(d)), function(i) {
      k <- d$kind[i]
      ch <- unique(c(names(KIND_PLACE), k))
      tags$tr(
        tags$td(tags$b(d$file[i]), if (!is.na(d$sheet[i] %||% NA) && nzchar(d$sheet[i])) tags$div(class = "examples", paste("sheet", d$sheet[i]))),
        tags$td(tags$select(class = "form-select form-select-sm kind-select",
                            `aria-label` = paste("What", d$file[i], "is"),
                            onchange = sprintf("Shiny.setInputValue('set_kind', {row: %d, kind: this.value}, {priority: 'event'})", i),
                            lapply(ch, function(x) tags$option(value = x, selected = if (identical(x, k)) NA, x))),
                if (isTRUE(d$set_by_you[i])) tags$div(class = "examples", "set by you")),
        tags$td(d$why[i]),
        tags$td(KIND_PLACE[[k]] %||% ""))
    })
    tagList(
      help_text("Check what each file seems to be. If one is wrong, choose the right kind: the app then offers the",
                "file in the right places."),
      div(class = "table-responsive",
          tags$table(class = "table table-sm identify",
                     tags$thead(tags$tr(tags$th("File"), tags$th(term_label("Kind", "file_kind")), tags$th("Why"),
                                        tags$th("Where it goes in this app"))),
                     tags$tbody(rows))))
  })
  observeEvent(input$set_kind, {
    s <- input$set_kind
    d <- rv$identify
    if (is.null(d) || s$row > nrow(d) || !s$kind %in% names(KIND_PLACE)) return()
    d$kind[s$row] <- s$kind
    if (!"set_by_you" %in% names(d)) d$set_by_you <- FALSE
    d$set_by_you[s$row] <- TRUE
    rv$identify <- d
  })

  # ------------------------------------------------------------ mapper b: propose
  output$map_table_ui <- renderUI({
    ch <- file_names("\\.(csv|tsv|txt|tab|xlsx)$", kinds = "sample table")
    default <- if (rv$demo && "SEA-MES_10L_samples.csv" %in% ch) "SEA-MES_10L_samples.csv" else guess_file("sample table")
    selectInput("map_table", term_label("Sample table", "sample_table"), c("Choose a file" = "", ch),
                selected = keep_or("map_table", default))
  })
  output$map_sheet_ui <- renderUI({
    p <- fpath(input$map_table)
    if (is.null(p) || galaxy_ext(p) != "xlsx") return(NULL)
    sh <- xlsx_sheets(p)
    selectInput("map_sheet", "Excel sheet", sh)
  })
  output$map_dictionary_ui <- renderUI({
    ch <- file_names()
    # a plain drop-down, so None can be chosen again after a file
    selectInput("map_dictionary", term_label("Data dictionary (optional)", "data_dictionary"), c("None" = "", ch),
                selected = keep_or("map_dictionary", ""), selectize = FALSE)
  })

  observeEvent(input$run_map, {
    tab <- fpath(input$map_table)
    if (is.null(tab)) return(showNotification("Choose your sample table.", type = "error"))
    sheet <- if (galaxy_ext(tab) == "xlsx") input$map_sheet %||% "" else ""
    args <- list(table = tab, table_name = input$map_table, sheet = sheet, header_row = input$map_header_row %||% 1,
                 assay_type = input$map_assay_type, sample_types = input$map_sample_types %||% character(),
                 dictionary = fpath(input$map_dictionary))
    withProgress(message = "Proposing a mapping", value = 0.3, {
      prof <- record(run_profile(sd, tab, sheet, args$header_row))
      res <- record(run_map(sd, tab, sheet, args$header_row, args$assay_type, args$sample_types,
                            dictionary = args$dictionary, other_terms = isTRUE(input$map_other_terms),
                            table_name = args$table_name))
    })
    rv$res$map <- res
    rv$profile <- if (prof$ok) read_tsv(prof$outputs$profile) else NULL
    if (res$ok) {
      rv$map <- res; rv$map_args <- args
      rv$crosswalk <- res$outputs$review_sheet; rv$crosswalk_from <- "proposed, not yet reviewed"
      rv$review_version <- rv$review_version + 1; rv$review_saved <- NULL; rv$model <- NULL
    } else showNotification("Propose mapping stopped with a message.", type = "warning")
  })

  map_summary <- reactive({
    req(rv$map)
    jsonlite::fromJSON(rv$map$outputs$summary)
  })
  output$map_result <- renderUI({
    res <- rv$res$map
    if (is.null(res)) return(help_text("The proposed match for each column appears here."))
    if (!res$ok) return(result_ui(res))
    s <- map_summary()
    tagList(
      div(class = "stats",
          stat_tile(s$accept, "accepted", "accepted"), stat_tile(s$review, "for review", "for-review"),
          stat_tile(s$no_match, "no match", "no-match"),
          stat_tile(s$missing_mandatory, "mandatory terms not covered", "missing")),
      if (length(s$read_notes)) help_text(tags$b("How the table was read: "), paste(s$read_notes, collapse = "; ")),
      tags$p("Next, go to ", actionLink("goto_review", "c. Review the mapping"), " to confirm or correct the matches."),
      navset_underline(
        nav_panel("Mapping report", DTOutput("map_report_table")),
        nav_panel("Additional checks to make", help_text(
          "Things only a person can settle before the workbook is written, such as a sample name used twice or",
          "controls named but not marked, with what to do about each."), DTOutput("map_checks_table")),
        nav_panel("Mandatory terms not covered", help_text(
          "These mandatory FAIRe terms are not in your table. Some come from the values for the whole project",
          "(step d), the OTU tables or the library tables (step e); the rest are questions to ask the data provider."),
          DTOutput("map_missing_table")),
        nav_panel("Column profiles", DTOutput("map_profile_table"))),
      result_ui(res))
  })
  observeEvent(input$goto_review, nav_select("mapper_steps", "c. Review the mapping"))
  output$map_report_table <- renderDT({
    d <- read_tsv(rv$map$outputs$report); req(d)
    table_dt(d[, intersect(c("column", "proposed_term", "route", "score", "evidence", "transform_hint", "shortlist"), names(d))])
  })
  output$map_checks_table <- renderDT({
    d <- read_tsv(rv$map$outputs$checks); req(d)
    table_dt(d)
  })
  output$map_missing_table <- renderDT({
    d <- read_tsv(rv$map$outputs$missing); req(d)
    table_dt(d[, intersect(c("term", "sheet", "condition", "description", "example"), names(d))])
  })
  output$map_profile_table <- renderDT({
    d <- rv$profile; req(d)
    table_dt(d[, intersect(c("column", "summary", "n_values", "n_unique", "examples", "min", "max", "date_format"), names(d))])
  })

  # ------------------------------------------------------------ mapper c: review
  # The screen is the review sheet propose mapping writes: the same rows, columns and choices. Saving
  # writes the decisions into a copy of that sheet, which apply mapping reads, so a sheet filled in here
  # and one filled in with Excel (and added back with the upload button) give the same workbook.
  review <- reactive({
    req(rv$map, rv$map$outputs$review_sheet)
    s <- read_review_sheet(rv$map$outputs$review_sheet)
    prof <- rv$profile
    s$rows$examples <- vapply(s$rows$input, function(col) {
      e <- if (is.null(prof)) character() else prof$examples[prof$column == col]
      if (length(e)) e[1] else ""
    }, character(1), USE.NAMES = FALSE)
    s$rows$kind <- ifelse(grepl("^review", s$rows$call), "review",
                          ifelse(s$rows$call == "no match", "no-match", "accept"))
    s
  })

  dec_id <- function(i) paste0("rvd", rv$review_version, "_", i)
  rep_id <- function(i) paste0("rvr", rv$review_version, "_", i)

  # The decisions as they stand on screen (the sheet's own values until a person changes them).
  review_state <- function() {
    r <- review()$rows
    n <- seq_len(nrow(r))
    data.frame(input = r$input,
               decision = vapply(n, function(i) input[[dec_id(i)]] %||% r$decision[i], character(1)),
               replacement = vapply(n, function(i) input[[rep_id(i)]] %||% r$replacement[i], character(1)),
               stringsAsFactors = FALSE)
  }

  # Put decisions on screen: a data frame with input, decision and replacement.
  show_decisions <- function(d) {
    r <- review()$rows
    for (i in seq_len(nrow(r))) {
      k <- match(r$input[i], d$input)
      if (is.na(k)) next
      updateSelectInput(session, dec_id(i), selected = d$decision[k])
      updateSelectInput(session, rep_id(i), selected = d$replacement[k])
    }
  }

  output$review_toolbar <- renderUI({
    if (is.null(rv$map)) return(help_text("Propose a mapping first (step b)."))
    r <- review()$rows
    tagList(
      div(class = "review-toolbar",
          tags$span(class = "badge text-bg-warning", sum(r$kind == "review"), "for review"),
          tags$span(class = "badge text-bg-secondary", sum(r$kind == "no-match"), "no match"),
          tags$span(class = "badge text-bg-success", sum(r$kind == "accept"), "accepted by the mapper"),
          tags$label(class = "toggle", tags$input(type = "checkbox", checked = NA,
                                                  onchange = "document.getElementById('review-grid').classList.toggle('hide-accepted', !this.checked)"),
                     " Show the mapper's accepted matches"),
          if (!is.null(rv$model)) actionButton("use_model", "Use the model's suggestions", icon = icon("robot"), class = "btn-sm"),
          if (rv$demo && identical(rv$map_args$table_name, "SEA-MES_10L_samples.csv"))
            actionButton("demo_answers", "Fill in the authors' answers", icon = icon("flask"), class = "btn-sm"),
          actionButton("save_review", "Save the review", icon = icon("floppy-disk"), class = "btn-primary btn-sm")),
      div(class = "review-files",
          downloadButton("review_download", "Download the review sheet", class = "btn-sm"),
          fileInput("review_upload", NULL, accept = ".xlsx", buttonLabel = "Add a review sheet you filled in",
                    placeholder = "Excel (.xlsx)", width = "440px")),
      help_text("The decisions in use: ", file_link(rv$crosswalk), paste0(" (", rv$crosswalk_from, ")."),
                "You can also download the sheet, fill it in with Excel (sorting or filtering the rows is fine,",
                "but keep every row) and add it back here."))
  })

  output$review_table <- renderUI({
    s <- review()
    r <- s$rows
    model <- rv$model
    show <- order(match(r$kind, c("review", "no-match", "accept")), seq_len(nrow(r)))
    rows <- lapply(show, function(i) {
      x <- r[i, ]
      has_term <- nzchar(x$proposed)
      dec_choices <- c("No decision" = "", if (has_term) c("Accept" = "Accept"), "Reject" = "Reject", "Change" = "Change")
      dsel <- isolate(input[[dec_id(i)]]) %||% x$decision
      rsel <- isolate(input[[rep_id(i)]]) %||% x$replacement
      lists <- s$choices[[x$input]] %||% list(best = character(), rest = character())
      other <- setdiff(rsel, c("", lists$best, lists$rest))
      opt <- function(v) lapply(v, function(t) tags$option(value = t, selected = if (identical(t, rsel)) NA, t))
      rep_select <- tags$select(
        id = rep_id(i), class = "form-select form-select-sm",
        # choosing a replacement sets the decision to Change
        onchange = sprintf("if (this.value) { var d = document.getElementById('%s'); d.value = 'Change'; $(d).trigger('change'); }", dec_id(i)),
        tags$option(value = "", selected = if (!nzchar(rsel)) NA, "No replacement"),
        if (length(other)) opt(other),
        if (length(lists$best)) tags$optgroup(label = "Best candidates for this column", opt(lists$best)),
        if (length(lists$rest)) tags$optgroup(label = "Every other term", opt(lists$rest)))
      m <- if (!is.null(model)) model[model$column == x$input, , drop = FALSE] else NULL
      tags$div(
        class = paste("rv-row", paste0("call-", x$kind)),
        div(class = "rv-col", tags$b(x$input), tags$div(class = "examples", x$examples)),
        div(class = "rv-proposed", if (has_term) x$proposed else tags$span(class = "muted", "none"),
            if (nzchar(x$score)) tags$small(class = "score", paste0(" ", x$score))),
        div(class = "rv-status", tags$span(class = paste("pill", x$kind), x$call)),
        div(class = "rv-evidence", x$reasoning,
            if (!is.null(m) && nrow(m)) tags$div(class = "model-says", icon("robot"),
                                                  paste0(" Model suggests ", if (is.na(m$term[1]) || !nzchar(m$term[1])) "no term" else m$term[1],
                                                         if (nzchar(m$reason[1] %||% "")) paste0(": ", m$reason[1]) else ""))),
        div(class = "rv-choice",
            selectInput(dec_id(i), NULL, dec_choices, selected = dsel, selectize = FALSE, width = "100%"),
            tags$small(class = "kept-as", "If rejected, kept as ", x$kept_as)),
        div(class = "rv-replace", rep_select))
    })
    div(id = "review-grid",
        div(class = "rv-row rv-head", div(term_label("Input term", "input_term"), " and some values"),
            div("Proposed FAIRe term and score"), div(term_label("Mapper's call", "mappers_call")), div("Mapper's reasoning"),
            div(term_label("Reviewer's decision", "decision")), div("Replacement FAIRe term")),
        rows)
  })

  # Save decisions into a copy of the review sheet and use it for the workbook.
  save_review <- function(d, from) {
    dir <- new_run_dir(sd, "review")
    stem <- sub("\\.[^.]*$", "", rv$map_args$table_name %||% "table")
    out <- file.path(dir, paste0(stem, "_review_sheet.xlsx"))
    s <- write_review_decisions(rv$map$outputs$review_sheet, d, out, dir)
    res <- record(run_result("review", "FAIRe mapper: review the mapping", dir, list(s), list(review_sheet = out)))
    if (!res$ok || !file.exists(out)) {
      showNotification("The review could not be saved. See the log of this step under Your session.", type = "error")
      return(invisible(NULL))
    }
    r <- review()$rows
    k <- r$kind[match(d$input, r$input)]
    rv$crosswalk <- out; rv$crosswalk_from <- from
    rv$review_saved <- list(accept = sum(d$decision == "Accept"), reject = sum(d$decision == "Reject"),
                            change = sum(d$decision == "Change"),
                            open = sum(d$decision == "" & k == "review", na.rm = TRUE),
                            bad = d$input[d$decision == "Change" & !nzchar(d$replacement)],
                            time = format(Sys.time(), "%H:%M:%S"))
    invisible(out)
  }

  observeEvent(input$save_review, {
    req(rv$map)
    save_review(review_state(), "reviewed here")
  })

  output$review_download <- downloadHandler(
    filename = function() paste0(sub("\\.[^.]*$", "", rv$map_args$table_name %||% "table"), "_review_sheet.xlsx"),
    content = function(file) {
      dir <- new_run_dir(sd, "review_download")
      s <- write_review_decisions(rv$map$outputs$review_sheet, review_state(), file.path(dir, "review_sheet.xlsx"), dir)
      file.copy(file.path(dir, "review_sheet.xlsx"), file, overwrite = TRUE)
    })

  # A review sheet filled in with Excel: its decisions go on screen and are saved, row by row by input
  # term, so the rows can be in any order. A column with no row is kept as its own term (Reject), as
  # apply mapping does with a row deleted from the sheet.
  observeEvent(input$review_upload, {
    f <- input$review_upload
    req(f, rv$map)
    up <- tryCatch(read_review_sheet(f$datapath), error = function(e) e)
    if (inherits(up, "error"))
      return(showNotification(paste("That file could not be read:", conditionMessage(up)), type = "error", duration = 10))
    d <- review_state()
    got <- up$rows[!duplicated(up$rows$input), , drop = FALSE]
    k <- match(d$input, got$input)
    d$decision[!is.na(k)] <- got$decision[k[!is.na(k)]]
    d$replacement[!is.na(k)] <- got$replacement[k[!is.na(k)]]
    d$decision[is.na(k)] <- "Reject"
    d$replacement[is.na(k)] <- ""
    show_decisions(d)
    save_review(d, paste("from", f$name))
    gone <- d$input[is.na(k)]
    extra <- setdiff(got$input, d$input)
    notes <- c(
      if (length(gone)) sprintf("%s no row in the sheet, so %s kept as %s own term%s: %s.",
                                if (length(gone) == 1) "1 column has" else paste(length(gone), "columns have"),
                                if (length(gone) == 1) "it is" else "they are",
                                if (length(gone) == 1) "its" else "their", if (length(gone) == 1) "" else "s",
                                paste(gone, collapse = ", ")),
      if (length(extra)) sprintf("%s not %s of this table and %s left out: %s.",
                                 if (length(extra) == 1) "1 row is" else paste(length(extra), "rows are"),
                                 if (length(extra) == 1) "a column" else "columns",
                                 if (length(extra) == 1) "was" else "were", paste(extra, collapse = ", ")),
      if (any(duplicated(up$rows$input))) "Some input terms are in the sheet twice; their first rows were used.")
    showNotification(paste(c(sprintf("The decisions in %s are on screen and saved.", f$name), notes), collapse = " "),
                     type = if (length(notes)) "warning" else "message", duration = if (length(notes)) 15 else 6)
  })

  # The authors' answers for the demonstration's 10 L table (dev/faire_mapper_seames/reviewer_decisions.tsv).
  DEMO_DECISIONS <- c(Control_Neg = "Accept", "*depth" = "Accept", samp_vol_we_dna_ext = "Accept",
                      sample_title = "Reject", replicate = "Reject", bioproject_accession = "Reject", Location = "Reject")
  observeEvent(input$demo_answers, {
    d <- review_state()
    k <- d$input %in% names(DEMO_DECISIONS)
    d$decision[k] <- DEMO_DECISIONS[d$input[k]]
    d$replacement[k] <- ""
    show_decisions(d)
    showNotification("Filled in. Look them over, then save the review.", type = "message")
  })

  # A model's answer for a column for review: its term is the proposed one (Accept), another one (Change)
  # or none (Reject).
  observeEvent(input$use_model, {
    m <- rv$model; req(m)
    r <- review()$rows
    d <- review_state()
    n <- 0
    for (i in seq_len(nrow(r))) {
      if (r$kind[i] != "review") next
      a <- m[m$column == r$input[i], , drop = FALSE]
      if (!nrow(a)) next
      term <- if (is.na(a$term[1])) "" else a$term[1]
      proposed <- trimws(sub("\\s*\\(.*\\)\\s*$", "", r$proposed[i]))
      if (!nzchar(term)) {
        d$decision[i] <- "Reject"; d$replacement[i] <- ""
      } else if (term == proposed || term == r$proposed[i]) {
        d$decision[i] <- "Accept"; d$replacement[i] <- ""
      } else {
        lists <- review()$choices[[r$input[i]]]
        all <- c(lists$best, lists$rest)
        hit <- all[trimws(sub("\\s*\\(.*\\)\\s*$", "", all)) == term]
        d$decision[i] <- "Change"; d$replacement[i] <- if (length(hit)) hit[1] else term
      }
      n <- n + 1
    }
    show_decisions(d)
    showNotification(sprintf("%d suggestions filled in. Check them, then save the review.", n), type = "message")
  })

  output$review_saved <- renderUI({
    s <- rv$review_saved
    if (is.null(s)) return(NULL)
    div(class = "res-ok", icon("circle-check"),
        sprintf("Review saved at %s: %d accepted, %d rejected, %d changed.", s$time, s$accept, s$reject, s$change),
        if (s$open) tags$span(sprintf(" %s for review %s no decision, so %s kept as %s own term%s, unless you tick 'Also write the matches still for review' in step e.",
                                      if (s$open == 1) "1 row" else paste(s$open, "rows"), if (s$open == 1) "has" else "have",
                                      if (s$open == 1) "it is" else "they are", if (s$open == 1) "its" else "their",
                                      if (s$open == 1) "" else "s")),
        if (length(s$bad)) tags$span(class = "text-danger", sprintf(" Change with no replacement term for %s: these are kept as their own terms.", paste(s$bad, collapse = ", "))),
        tags$br(), "Next, ", actionLink("goto_primers", "d. Primers and project values"), ".")
  })
  observeEvent(input$goto_primers, nav_select("mapper_steps", "d. Primers and project values"))

  run_model_step <- function(preview) {
    req(rv$map)
    res <- with_run(if (preview) "Preparing the requests" else "Asking the model",
                    run_model(sd, rv$map$outputs$requests, input$model_api, trimws(input$model_name),
                              trimws(input$model_url), input$model_key, preview))
    rv$res$model <- res
    if (res$ok && !preview && file.exists(res$outputs$answers)) {
      a <- tryCatch(jsonlite::fromJSON(res$outputs$answers, simplifyDataFrame = TRUE), error = function(e) NULL)
      if (is.data.frame(a) && nrow(a)) {
        if (!"reason" %in% names(a)) a$reason <- ""
        rv$model <- a[, c("column", "term", "reason")]
      }
    }
    updateTextInput(session, "model_key", value = "")
  }
  observeEvent(input$run_model_preview, run_model_step(TRUE))
  observeEvent(input$run_model, run_model_step(FALSE))
  output$model_result <- renderUI({
    res <- rv$res$model
    if (is.null(res)) return(NULL)
    tagList(result_ui(res), if (!is.null(rv$model)) help_text("The suggestions now show beside each row in the review. Press",
                                                               tags$em("Use the model's suggestions"), "to fill them in."))
  })

  output$own_crosswalk_ui <- renderUI({
    selectInput("own_crosswalk", "Crosswalk from your files", c("Choose a file" = "", file_names("\\.(tsv|csv|txt)$", kinds = "crosswalk")))
  })
  observeEvent(input$use_own_crosswalk, {
    p <- fpath(input$own_crosswalk)
    if (is.null(p)) return(showNotification("Choose the crosswalk from your files.", type = "error"))
    rv$crosswalk <- p; rv$crosswalk_from <- "your own crosswalk"
    showNotification("The workbook will be written with your crosswalk.", type = "message")
  })

  # ------------------------------------------------------------ mapper d: primers and project values
  output$pr_texts_ui <- renderUI({
    ch <- file_names("\\.(txt|md|pdf)$", kinds = "text")
    sel <- isolate(input$pr_texts) %||% (if (rv$demo) intersect("methods.txt", ch) else ch[vapply(ch, kind_of, "") == "text"])
    tagList(
      selectInput("pr_texts", term_label("Your methods (text or PDF)", "methods"), ch, selected = sel, multiple = TRUE),
      if (!length(ch)) help_text("Add your methods to Your files (left), as text or a PDF."))
  })
  # Links to the chosen methods, to open beside the project values
  output$pr_texts_open <- renderUI({
    f <- input$pr_texts
    if (!length(f)) return(NULL)
    help_text("Open:", lapply(f, function(n) tags$span(file_link(fpath(n)), " ")))
  })
  output$pr_own_ui <- renderUI(selectInput("pr_own", term_label("My primer table", "primer_table"),
                                           c("Choose a file" = "", file_names("\\.(tsv|tab|txt)$", kinds = "primer table"))))
  observeEvent(input$run_primers, {
    texts <- unname(unlist(lapply(input$pr_texts, fpath)))
    if (input$pr_mode == "text" && !length(texts)) return(showNotification("Choose the methods text.", type = "error"))
    if (input$pr_mode == "names" && blank(input$pr_names)) return(showNotification("Type at least one name.", type = "error"))
    res <- with_run("Looking for primers", run_primers(sd, input$pr_mode, texts, input$pr_names, input$pr_gene,
                                                      input$pr_source, fpath(input$pr_own)))
    rv$res$primers <- res
    rv$primers <- if (res$ok) read_tsv(res$outputs$candidates) else NULL
  })
  primer_fields <- c("targetTaxonomicAssay", "targetTaxonomicScope", "target_gene", "target_subfragment",
                     "pcr_primer_name_forward", "pcr_primer_forward", "pcr_primer_reference_forward",
                     "pcr_primer_name_reverse", "pcr_primer_reverse", "pcr_primer_reference_reverse",
                     "ampliconSize", "annealingTemp", "pcr_cycles")
  output$primers_result <- renderUI({
    res <- rv$res$primers
    if (is.null(res)) return(NULL)
    tagList(
      result_ui(res, show_files = TRUE),
      if (!is.null(rv$primers) && nrow(rv$primers)) tagList(
        help_text("Choose a primer pair, check it against the primary reference, and add its details to the",
                  "values for the whole project for one of your assays."),
        DTOutput("primers_table"),
        layout_columns(col_widths = c(6, 6),
                       textInput("pr_assay", "For assay", value = if (rv$demo) "Fish16S" else ""),
                       div(class = "pt-4", actionButton("pr_add", "Add to the project values", icon = icon("arrow-right"))))))
  })
  output$primers_table <- renderDT({
    d <- rv$primers; req(d)
    keep <- intersect(c("query", "assay_name", "target_gene", "pcr_primer_name_forward", "pcr_primer_forward",
                        "pcr_primer_name_reverse", "pcr_primer_reverse", "pcr_primer_reference_forward", "notes"), names(d))
    datatable(d[, keep], rownames = FALSE, selection = "single", class = "compact stripe",
              options = list(scrollX = TRUE, pageLength = 5, dom = "tip"))
  })
  observeEvent(input$pr_add, {
    i <- input$primers_table_rows_selected
    if (!length(i)) return(showNotification("Choose a primer pair in the table first.", type = "error"))
    r <- rv$primers[i, ]
    f <- intersect(primer_fields, names(r))
    f <- f[nzchar(trimws(unlist(r[f])))]
    assay <- trimws(input$pr_assay)
    pv <- rv$pv
    pv <- pv[!(pv$term %in% f & pv$assay == assay), , drop = FALSE]
    rv$pv <- rbind(pv, data.frame(term = f, value = unname(unlist(r[f])), assay = assay))
    showNotification(sprintf("%d values added for %s.", length(f), if (nzchar(assay)) assay else "every assay"), type = "message")
  })

  observe({
    t <- checklist_terms()
    pm <- t$term[t$sheet == "projectMetadata"]
    updateSelectizeInput(session, "pv_term", choices = c("", pm), server = TRUE)
  })
  output$pv_table <- renderDT({
    datatable(rv$pv, rownames = FALSE, editable = list(target = "cell"), class = "compact stripe",
              options = list(pageLength = 8, dom = "tip", scrollX = TRUE),
              colnames = c("FAIRe term", "Value", "Assay"))
  })
  observeEvent(input$pv_table_cell_edit, {
    e <- input$pv_table_cell_edit
    pv <- rv$pv
    pv[e$row, e$col + 1] <- as.character(e$value)
    rv$pv <- pv
  })
  observeEvent(input$pv_delete, {
    i <- input$pv_table_rows_selected
    if (length(i)) rv$pv <- rv$pv[-i, , drop = FALSE]
  })
  observeEvent(input$pv_add, {
    if (blank(input$pv_term) || blank(input$pv_value)) return(showNotification("Choose a term and give a value.", type = "error"))
    rv$pv <- rbind(rv$pv, data.frame(term = input$pv_term, value = input$pv_value, assay = trimws(input$pv_assay)))
    updateTextInput(session, "pv_value", value = "")
  })
  output$pv_file_ui <- renderUI(selectInput("pv_file", NULL, c("Choose a file" = "", file_names("\\.(tsv|tab|txt|csv)$", kinds = "project values"))))
  observeEvent(input$pv_load, {
    p <- fpath(input$pv_file); req(p)
    d <- if (galaxy_ext(p) == "csv") utils::read.csv(p, colClasses = "character", check.names = FALSE) else read_tsv(p)
    if (is.null(d) || !all(c("term", "value") %in% names(d)))
      return(showNotification("The table needs columns named term and value.", type = "error"))
    if (!"assay" %in% names(d)) d$assay <- ""
    rv$pv <- d[, c("term", "value", "assay")]
  })
  # The mandatory project terms no file covers yet (propose mapping's list), less those given here.
  output$pv_missing <- renderUI({
    m <- if (!is.null(rv$map)) read_tsv(rv$map$outputs$missing) else NULL
    if (is.null(m) || !nrow(m)) return(NULL)
    left <- setdiff(m$term[m$sheet == "projectMetadata"], c(rv$pv$term, "project_id", "assay_name", "assay_type",
                                                             "checkls_ver"))
    if (!length(left)) return(div(class = "res-ok", icon("circle-check"),
                                  "Every mandatory project term the mapping found missing has a value here."))
    div(class = "missing-terms",
        tags$b("Mandatory terms still to give"), " (from b. Propose a mapping):",
        tags$div(lapply(left, function(t) tags$span(class = "term-chip", title = m$description[m$term == t][1], t))))
  })
  output$pv_download <- downloadHandler("project_values.tsv", function(file) write_tsv(rv$pv, file))

  # ------------------------------------------------------------ mapper e: write the workbook
  output$apply_inputs_summary <- renderUI({
    if (is.null(rv$map_args)) return(div(class = "res-fail", icon("circle-info"), "Propose a mapping first (step b)."))
    help_text(tags$b("Sample table: "), rv$map_args$table_name, tags$br(), tags$b("Crosswalk: "),
              basename(rv$crosswalk %||% ""), paste0(" (", rv$crosswalk_from, ")"), tags$br(),
              tags$b("Project values: "), nrow(rv$pv), " (step d)")
  })

  observeEvent(input$otu_add, rv$otu_n <- rv$otu_n + 1)
  observeEvent(input$otu_remove, rv$otu_n <- max(0, rv$otu_n - 1))
  observeEvent(input$lib_add, rv$lib_n <- rv$lib_n + 1)
  observeEvent(input$lib_remove, rv$lib_n <- max(0, rv$lib_n - 1))

  demo_block <- function(kind, i) {
    if (!rv$demo) return(list())
    if (kind == "otu") {
      if (i == 1) return(list(file = "4_SEA-MES_16S_ASV_level_output_with_seq.csv", assay = "Fish16S", run = "AGRF_2024-12", stage = "raw"))
      if (i == 2) return(list(file = "5_SEA_MES_Fish16S_Tax_Feb_27_2025.csv", assay = "Fish16S", run = "AGRF_2024-12", stage = "final"))
    }
    if (kind == "lib" && i == 1) return(list(file = "filereport_read_run_PRJNA1263580.tsv", assay = "Fish16S", filter = "16SFish"))
    list()
  }
  bid <- function(kind, i, field) paste0(kind, rv$block_version, "_", i, "_", field)
  bval <- function(kind, i, field, default = "") {
    v <- isolate(input[[bid(kind, i, field)]])
    if (!is.null(v)) return(v)
    demo_block(kind, i)[[field]] %||% default
  }

  output$otu_blocks <- renderUI({
    n <- rv$otu_n
    if (!n) return(help_text("No OTU tables. The workbook will hold the sample and project metadata only."))
    ch <- c("Choose a file" = "", file_names("\\.(csv|tsv|tab|txt|xlsx)$", kinds = "OTU or ASV table"))
    lapply(seq_len(n), function(i) {
      b <- function(field) bid("otu", i, field)
      div(class = "block",
          tags$h6(paste("OTU table", i)),
          selectInput(b("file"), term_label("OTU or ASV table", "otu_table"), ch, selected = bval("otu", i, "file")),
          layout_columns(
            col_widths = c(4, 4, 4),
            textInput(b("assay"), term_label("Assay", "assay"), bval("otu", i, "assay")),
            textInput(b("run"), term_label("Sequencing run ID", "run_id"), bval("otu", i, "run")),
            selectInput(b("stage"), term_label("Write as", "stage"), c("final (otuFinal, taxaFinal)" = "final", "raw (otuRaw, taxaRaw)" = "raw"),
                        selected = bval("otu", i, "stage", "final"))),
          accordion(open = FALSE, accordion_panel(
            "More for this table",
            # plain drop-downs, so 'In the OTU table' can be chosen again after a file
            selectInput(b("taxa"), term_label("Taxonomy table (optional)", "taxonomy_table"),
                        c("In the OTU table" = "", file_names("\\.(csv|tsv|tab|txt|xlsx)$", kinds = "taxonomy table")),
                        selected = bval("otu", i, "taxa"), selectize = FALSE),
            selectInput(b("sequences"), term_label("Sequences of this table (FASTA, optional)", "sequences"),
                        c("In the OTU table" = "", file_names("\\.(fa|fasta|fna|fas|txt)$", kinds = "sequences (FASTA)")),
                        selected = bval("otu", i, "sequences"), selectize = FALSE),
            help_text("For a table that names its sequences (ASV_1, ASV_2 ...) but does not hold them, such as an",
                      "LCA output: a FASTA file whose headers are those names."),
            layout_columns(
              col_widths = c(6, 6),
              textInput(b("sheet"), "Excel sheet (OTU table)", bval("otu", i, "sheet")),
              textInput(b("taxa_sheet"), "Excel sheet (taxonomy table)", bval("otu", i, "taxa_sheet"))),
            selectInput(b("layout"), term_label("Layout", "layout"), c("Work it out" = "detect", "Samples as columns" = "columns",
                                                 "Samples as rows" = "rows", "Long (one row per sample and sequence)" = "long"),
                        selected = bval("otu", i, "layout", "detect")),
            layout_columns(
              col_widths = c(4, 4, 4),
              textInput(b("assay_column"), "Column that gives each row's assay", bval("otu", i, "assay_column")),
              textInput(b("curated_column"), term_label("Column of curated names", "curated_column"), bval("otu", i, "curated_column")),
              textInput(b("lineage"), term_label("Lineage column to use", "lineage"), bval("otu", i, "lineage"))))))
    })
  })

  output$lib_blocks <- renderUI({
    n <- rv$lib_n
    if (!n) return(help_text("No library tables."))
    ch <- c("Choose a file" = "", file_names("\\.(csv|tsv|tab|txt|xlsx)$", kinds = "library table"))
    lapply(seq_len(n), function(i) {
      b <- function(field) bid("lib", i, field)
      div(class = "block",
          tags$h6(paste("Library table", i)),
          selectInput(b("file"), term_label("Library table", "library_table"), ch, selected = bval("lib", i, "file")),
          layout_columns(
            col_widths = c(4, 4, 4),
            textInput(b("assay"), "Assays of these libraries", bval("lib", i, "assay")),
            textInput(b("filter"), "Only libraries whose name holds", bval("lib", i, "filter")),
            textInput(b("run"), "Sequencing run ID", bval("lib", i, "run"))),
          textInput(b("sheet"), "Excel sheet (optional)", bval("lib", i, "sheet")))
    })
  })

  observeEvent(input$run_apply, {
    a <- rv$map_args
    if (is.null(a)) return(showNotification("Propose a mapping first (step b).", type = "error"))
    pid <- trimws(input$ap_project_id)
    if (!nzchar(pid)) return(showNotification("Give a project ID.", type = "error"))
    g <- function(kind, i, field) { v <- input[[bid(kind, i, field)]]; if (is.null(v)) "" else trimws(v) }
    otus <- list()
    for (i in seq_len(rv$otu_n)) {
      p <- fpath(g("otu", i, "file")); if (is.null(p)) next
      otus[[length(otus) + 1]] <- list(path = p, name = g("otu", i, "file"), sheet = g("otu", i, "sheet"),
                                       assay = g("otu", i, "assay"), run = g("otu", i, "run"),
                                       stage = g("otu", i, "stage"), layout = g("otu", i, "layout") %||% "detect",
                                       assay_column = g("otu", i, "assay_column"), curated_column = g("otu", i, "curated_column"),
                                       lineage = g("otu", i, "lineage"), taxa = fpath(g("otu", i, "taxa")),
                                       taxa_sheet = g("otu", i, "taxa_sheet"), sequences = fpath(g("otu", i, "sequences")))
    }
    libs <- list()
    for (i in seq_len(rv$lib_n)) {
      p <- fpath(g("lib", i, "file")); if (is.null(p)) next
      libs[[length(libs) + 1]] <- list(path = p, name = g("lib", i, "file"), sheet = g("lib", i, "sheet"),
                                       assay = g("lib", i, "assay"), filter = g("lib", i, "filter"), run = g("lib", i, "run"))
    }
    pv_path <- NULL
    if (nrow(rv$pv)) {
      pv_path <- file.path(sd, "project_values.tsv")
      write_tsv(rv$pv, pv_path)
    }
    if (rv$crosswalk_from == "proposed, not yet reviewed")
      showNotification("The review has not been saved: only the mapper's accepted matches are written.", type = "warning")
    utc <- trimws(input$ap_utc_offset %||% "")
    if (nzchar(utc) && !grepl("^(Z|[+-](0[0-9]|1[0-4]):[0-5][0-9])$", utc))
      return(showNotification("Give the UTC offset as +10:00, -04:00 or Z, or leave it empty.", type = "error"))
    at <- if (a$assay_type == "any") "metabarcoding" else a$assay_type
    res <- with_run("Writing the FAIRe workbook", run_apply(
      sd, a$table, a$sheet, a$header_row, rv$crosswalk, at, a$sample_types, pid,
      assay_name = input$ap_assay_name, country = input$ap_country, utc_offset = utc, date_order = input$ap_date_order,
      include_review = input$ap_include_review, project_values = pv_path, req_lev = input$ap_req_lev,
      drop_unmapped = input$ap_drop_unmapped, otu_tables = otus, library_tables = libs, table_name = a$table_name))
    if (!is.null(pv_path)) file.copy(pv_path, res$dir)
    rv$res$apply <- res
    if (res$ok && file.exists(res$outputs$workbook)) set_workbook(res$outputs$workbook, "written by the FAIRe mapper")
  })
  apply_log <- reactive({
    res <- rv$res$apply
    if (is.null(res) || is.null(res$outputs$log)) return(NULL)
    paste(readLines(res$outputs$log, warn = FALSE, encoding = "UTF-8"), collapse = "\n")
  })
  output$apply_result <- renderUI({
    res <- rv$res$apply
    if (is.null(res)) return(help_text("The workbook appears here, with the mapper's notes on what it wrote."))
    tagList(
      result_ui(res),
      if (res$ok) tagList(
        tags$p("This is now the workbook in use. Next, ", actionLink("goto_check", "check it with FAIRe-fier"), "."),
        tags$details(tags$summary("What the mapper wrote, and what is still empty"), tags$pre(class = "log", apply_log()))))
  })
  observeEvent(input$goto_check, nav_select("main", "2. Check"))
  wb_preview_server("apply_preview", reactive(if (!is.null(rv$res$apply) && rv$res$apply$ok) rv$res$apply$outputs$workbook))

  # ------------------------------------------------------------ check
  observeEvent(input$run_fairefier, {
    wb <- picked_workbook("ck_wb")
    if (is.null(wb)) return(showNotification("Choose a workbook.", type = "error"))
    rv$res$fairefier <- with_run("Checking the workbook", run_fairefier(sd, wb, input$ck_version))
  })
  output$fairefier_result <- renderUI({
    res <- rv$res$fairefier
    if (is.null(res)) return(help_text("FAIRe-fier's findings appear here."))
    s <- if (file.exists(res$outputs$summary %||% "")) jsonlite::fromJSON(res$outputs$summary) else NULL
    sheets <- if (!is.null(s)) intersect(c("projectMetadata", "sampleMetadata", "experimentRunMetadata"), names(s)) else character()
    tagList(
      if (!is.null(s)) tagList(
        div(class = if (isTRUE(s$valid)) "res-ok big" else "res-fail big",
            icon(if (isTRUE(s$valid)) "circle-check" else "triangle-exclamation"),
            if (isTRUE(s$valid)) "The workbook passes." else "The workbook does not pass yet."),
        div(class = "stats", lapply(sheets, function(sh) {
          x <- s[[sh]]
          stat_tile(if (isTRUE(x$valid)) "passes" else sprintf("%d errors", x$errors),
                    sprintf("%s, %d warnings", sh, x$warnings), if (isTRUE(x$valid)) "accepted" else "failed")
        })),
        if (!is.null(s$checklist_note)) help_text(s$checklist_note)),
      if (file.exists(res$outputs$issues %||% "")) tagList(
        tags$h6("Errors and warnings"),
        help_text("Errors must be fixed. Warnings are worth a look: an extra term, for example, may be a field you",
                  "meant to name differently. The workbook below (fairefier_warn_error.xlsx) highlights the cells."),
        DTOutput("fairefier_issues")),
      result_ui(res))
  })
  output$fairefier_issues <- renderDT({
    d <- read_tsv(rv$res$fairefier$outputs$issues); req(d)
    d <- d[, intersect(c("worksheet", "level", "record", "term", "input", "message", "suggested"), names(d))]
    datatable(d, rownames = FALSE, class = "compact stripe",
              options = list(scrollX = TRUE, pageLength = 10, autoWidth = TRUE,
                             columnDefs = list(list(width = "320px", targets = which(names(d) == "message") - 1)))) |>
      formatStyle("level", target = "row", backgroundColor = styleEqual(c("error", "warning"), c("#fde2e1", "#fff4d6")))
  })

  # ------------------------------------------------------------ convert
  cv_wb <- reactive(picked_workbook("cv_wb"))
  need_wb <- function() {
    wb <- cv_wb()
    if (is.null(wb)) showNotification("Choose the workbook to convert, at the top of the page.", type = "error")
    wb
  }
  wb_info <- reactive({
    wb <- cv_wb()
    if (is.null(wb) || !file.exists(wb)) return(list(assays = character(), runs = character(), sheets = character()))
    sheets <- xlsx_sheets(wb)
    assays <- character()
    pm <- tryCatch(as.data.frame(readxl::read_excel(wb, "projectMetadata", col_names = FALSE, col_types = "text")),
                   error = function(e) NULL)
    if (!is.null(pm)) {
      tc <- which(apply(pm, 2, function(x) any(x == "term_name", na.rm = TRUE)))[1]
      if (!is.na(tc)) {
        r <- which(pm[[tc]] == "assay_name")[1]
        if (!is.na(r)) assays <- unique(na.omit(unlist(pm[r, (tc + 1):ncol(pm)])))
      }
    }
    erm <- if ("experimentRunMetadata" %in% sheets) read_faire_sheet(wb, "experimentRunMetadata") else NULL
    runs <- if (!is.null(erm) && "seq_run_id" %in% names(erm)) unique(erm$seq_run_id[nzchar(erm$seq_run_id)]) else character()
    list(assays = assays[nzchar(assays)], runs = runs, sheets = sheets)
  })

  output$ns_accessions_ui <- renderUI({
    ch <- file_names("\\.(tsv|tab|txt|csv)$")
    selectInput("ns_accessions", "BioSample accession table (from NCBI)", c("Choose a file" = "", ch),
                selected = keep_or("ns_accessions", if (rv$demo) "biosample_accessions.tsv" else ""))
  })
  output$er_receipt_ui <- renderUI({
    ch <- file_names("\\.xml$")
    selectInput("er_receipt", "ENA sample receipt", c("Choose a file" = "", ch),
                selected = keep_or("er_receipt", if (rv$demo) "ena_sample_receipt.xml" else ""))
  })

  table_result <- function(slot, table_key) {
    res <- rv$res[[slot]]
    if (is.null(res)) return(NULL)
    tagList(result_ui(res), if (res$ok && !is.null(res$outputs[[table_key]])) DTOutput(paste0(slot, "_table")))
  }
  for (spec in list(c("ncbi_biosample", "biosample_table"), c("ncbi_sra", "sra_table"))) local({
    slot <- spec[1]; key <- spec[2]
    output[[paste0(slot, "_result")]] <- renderUI(table_result(slot, key))
    output[[paste0(slot, "_table")]] <- renderDT({
      res <- rv$res[[slot]]; req(res, res$ok)
      lines <- readLines(res$outputs[[key]], warn = FALSE, encoding = "UTF-8")
      d <- tryCatch(utils::read.delim(text = lines[!startsWith(lines, "#")], colClasses = "character",
                                      check.names = FALSE, quote = ""), error = function(e) NULL)
      req(d); table_dt(d, page = 5)
    })
  })

  observeEvent(input$run_ncbi_biosample, {
    wb <- need_wb(); req(wb)
    org <- if (input$nb_organism == "other") input$nb_organism_other else input$nb_organism
    rv$res$ncbi_biosample <- with_run("Writing the BioSample table", run_ncbi_biosample(
      sd, wb, org, input$nb_bioproject, input$nb_mandatory_fill, input$nb_associated, input$nb_duplicates,
      input$nb_convert_dates, input$nb_mixs_units, input$nb_title, input$nb_title_columns, input$nb_extra, input$nb_exclude))
  })
  observeEvent(input$run_ncbi_sra, {
    wb <- need_wb(); req(wb)
    acc <- if (input$ns_link == "accessions") fpath(input$ns_accessions) else NULL
    if (input$ns_link == "accessions" && is.null(acc)) return(showNotification("Choose the BioSample accession table.", type = "error"))
    org <- if (input$nb_organism == "other") input$nb_organism_other else input$nb_organism
    rv$res$ncbi_sra <- with_run("Writing the SRA table", run_ncbi_sra(
      sd, wb, input$ns_runs_by, input$ns_runs_values, input$ns_associated, input$ns_instrument, acc, org))
  })
  observeEvent(input$run_ena_sample, {
    wb <- need_wb(); req(wb)
    if (blank(input$es_center)) return(showNotification("Give your centre name.", type = "error"))
    taxon <- if (input$es_taxon == "other") input$es_taxon_id else input$es_taxon
    rv$res$ena_sample <- with_run("Writing the sample XML", run_ena_sample(sd, wb, trimws(input$es_center), taxon, input$es_convert_dates))
  })
  observeEvent(input$run_ena_run, {
    wb <- need_wb(); req(wb)
    rec <- fpath(input$er_receipt)
    if (is.null(rec)) return(showNotification("Choose ENA's sample receipt from your files.", type = "error"))
    if (blank(input$er_study) || blank(input$er_center)) return(showNotification("Give the study accession and centre name.", type = "error"))
    rv$res$ena_run <- with_run("Writing the experiment and run XML", run_ena_run(
      sd, wb, rec, trimws(input$er_study), trimws(input$er_center), input$er_instrument,
      if (input$er_assay == "one") input$er_assay_name else "", input$er_assay_suffix, input$er_seq_runs, input$er_ftp))
  })
  output$ena_sample_result <- renderUI(result_ui(rv$res$ena_sample))
  output$ena_run_result <- renderUI(result_ui(rv$res$ena_run))

  # GBIF MDT: the OTU and taxonomy tables come from the workbook's sheets, or from your files.
  output$mdt_assay_ui <- renderUI({
    info <- wb_info()
    layout_columns(
      col_widths = c(6, 6),
      selectizeInput("mdt_assay", "Assay name", choices = info$assays, selected = info$assays[1], options = list(create = TRUE)),
      selectizeInput("mdt_run", "Sequencing run ID", choices = info$runs, selected = info$runs[1], options = list(create = TRUE)))
  })
  table_source_ui <- function(id, label, sheets, default_sheet) {
    ch <- c(setNames(paste0("sheet:", sheets), paste("Workbook sheet:", sheets)),
            setNames(paste0("file:", file_names("\\.(csv|tsv|tab|txt|xlsx)$")), paste("Your files:", file_names("\\.(csv|tsv|tab|txt|xlsx)$"))))
    sel <- keep_or(id, if (default_sheet %in% sheets) paste0("sheet:", default_sheet) else "")
    selectInput(id, label, c("Choose" = "", ch), selected = sel)
  }
  output$mdt_tables_ui <- renderUI({
    info <- wb_info()
    a <- input$mdt_assay %||% ""
    pick <- function(base) { s <- c(paste0(base, "_", a), base); s[s %in% info$sheets][1] %||% "" }
    tagList(table_source_ui("mdt_otu", "OTU table (otuFinal)", info$sheets, pick("otuFinal")),
            table_source_ui("mdt_taxa", "Taxonomy table (taxaFinal)", info$sheets, pick("taxaFinal")))
  })
  source_of <- function(v, wb) {
    if (blank(v)) return(NULL)
    if (startsWith(v, "sheet:")) return(list(path = wb, sheet = sub("^sheet:", "", v)))
    list(path = fpath(sub("^file:", "", v)), sheet = "")
  }
  observeEvent(input$run_mdt, {
    wb <- need_wb(); req(wb)
    if (blank(input$mdt_assay) || blank(input$mdt_run)) return(showNotification("Give the assay and sequencing run.", type = "error"))
    o <- source_of(input$mdt_otu, wb); t <- source_of(input$mdt_taxa, wb)
    if (is.null(o) || is.null(t)) return(showNotification("Choose the OTU and taxonomy tables.", type = "error"))
    sheet_or <- function(x, default) if (nzchar(x$sheet)) x$sheet else default
    rv$res$mdt <- with_run("Writing the MDT workbook", run_mdt(sd, wb, input$mdt_assay, input$mdt_run, o$path,
                                                              sheet_or(o, "otuFinal"), t$path, sheet_or(t, "taxaFinal"),
                                                              input$mdt_controls))
  })
  output$mdt_result <- renderUI({
    res <- rv$res$mdt
    if (is.null(res)) return(help_text("The MDT workbook appears here. Upload it to GBIF's MDT (mdt.gbif.org)."))
    tagList(result_ui(res), if (res$ok) wb_preview_ui("mdt_preview"))
  })
  wb_preview_server("mdt_preview", reactive(if (!is.null(rv$res$mdt) && rv$res$mdt$ok) rv$res$mdt$outputs$mdt_workbook),
                    faire = FALSE)

  # edna2obis: one taxonomy and abundance table for each assay, from the workbook's sheets.
  output$eo_tables_ui <- renderUI({
    info <- wb_info()
    if (!length(info$assays)) return(help_text("Choose a workbook with assays at the top of the page."))
    lapply(seq_along(info$assays), function(i) {
      a <- info$assays[i]
      pick <- function(base) { s <- c(paste0(base, "_", a), base); s[s %in% info$sheets][1] %||% "" }
      div(class = "block", tags$h6(paste("Assay", a)),
          table_source_ui(paste0("eo_tax_", i), "Taxonomy table", info$sheets, pick("taxaFinal")),
          table_source_ui(paste0("eo_abund_", i), "Abundance table", info$sheets, pick("otuFinal")),
          textInput(paste0("eo_run_", i), "Analysis run name", keep_or(paste0("eo_run_", i), info$runs[1] %||% a)),
          checkboxInput(paste0("eo_skip_", i), "Ignore species-level names for this assay", FALSE))
    })
  })
  # The upstream readers take a table with the field names in its first rows; a workbook sheet is
  # copied to its own file first.
  sheet_to_file <- function(src, d, name) {
    if (is.null(src)) return(NULL)
    if (!nzchar(src$sheet)) return(src$path)
    x <- as.data.frame(readxl::read_excel(src$path, src$sheet, col_names = FALSE, col_types = "text", .name_repair = "minimal"))
    x[is.na(x)] <- ""
    out <- file.path(d, paste0(name, "_", src$sheet, ".tsv"))
    utils::write.table(x, out, sep = "\t", quote = FALSE, row.names = FALSE, col.names = FALSE, fileEncoding = "UTF-8")
    out
  }
  eo_analyses <- function(wb, need_abundance) {
    info <- wb_info()
    d <- file.path(sd, "edna2obis_tables"); dir.create(d, showWarnings = FALSE)
    out <- list()
    for (i in seq_along(info$assays)) {
      tax <- sheet_to_file(source_of(input[[paste0("eo_tax_", i)]], wb), d, paste0(info$assays[i], "_taxonomy"))
      ab <- sheet_to_file(source_of(input[[paste0("eo_abund_", i)]], wb), d, paste0(info$assays[i], "_abundance"))
      if (is.null(tax) || (need_abundance && is.null(ab))) next
      out[[length(out) + 1]] <- list(assay = info$assays[i], run = input[[paste0("eo_run_", i)]] %||% "",
                                     taxonomy = tax, abundance = ab, skip_species = isTRUE(input[[paste0("eo_skip_", i)]]))
    }
    out
  }
  observeEvent(input$run_eo_match, {
    wb <- need_wb(); req(wb)
    an <- eo_analyses(wb, FALSE)
    if (!length(an)) return(showNotification("Choose a taxonomy table for at least one assay.", type = "error"))
    res <- with_run("Matching names (this needs internet access)", run_edna2obis_match(sd, an, input$eo_api, input$eo_worms_all))
    rv$res$eo_match <- res
    if (res$ok) rv$eo_mapping <- res$outputs$mapping
  })
  output$eo_mapping_ui <- renderUI({
    ch <- c(if (!is.null(rv$eo_mapping)) c("The table from step 1" = "__last__"),
            setNames(paste0("file:", file_names("\\.(tsv|tab|csv|xlsx)$")), paste("Your files:", file_names("\\.(tsv|tab|csv|xlsx)$"))))
    selectInput("eo_mapping", "Mapping table", c("Choose" = "", ch), selected = if (!is.null(rv$eo_mapping)) "__last__" else "")
  })
  observeEvent(input$run_eo_build, {
    wb <- need_wb(); req(wb)
    an <- eo_analyses(wb, TRUE)
    if (!length(an)) return(showNotification("Choose the taxonomy and abundance tables.", type = "error"))
    mapping <- NULL
    if (input$eo_taxa_source == "mapping") {
      mapping <- if (identical(input$eo_mapping, "__last__")) rv$eo_mapping else fpath(sub("^file:", "", input$eo_mapping %||% ""))
      if (is.null(mapping)) return(showNotification("Choose the mapping table, or match the taxa first.", type = "error"))
    }
    eml <- if (isTRUE(input$eo_eml)) list(select = "form", title = input$eo_title, abstract = input$eo_abstract,
                                          given_name = input$eo_given, surname = input$eo_surname,
                                          organisation = input$eo_org, email = input$eo_email, licence = input$eo_licence,
                                          keywords = "eDNA, metabarcoding")
           else list(select = "none")
    rv$res$eo_build <- with_run("Building the Darwin Core archive", run_edna2obis_build(
      sd, wb, an, mapping, input$eo_api, text_dates = input$eo_text_dates, location_fields = input$eo_location,
      core_type = input$eo_core, emof = input$eo_emof, eml = eml))
  })
  output$eo_match_result <- renderUI({
    res <- rv$res$eo_match
    if (is.null(res)) return(help_text("The matches appear here. Check them, especially for names that WoRMS or GBIF",
                                       "know in another sense, before you build the archive."))
    tagList(tags$h6("1. Match taxa"), result_ui(res), if (res$ok) DTOutput("eo_match_table"))
  })
  output$eo_match_table <- renderDT({
    res <- rv$res$eo_match; req(res, res$ok)
    d <- if (grepl("xlsx$", res$outputs$mapping)) as.data.frame(readxl::read_excel(res$outputs$mapping)) else read_tsv(res$outputs$mapping)
    req(d); table_dt(d, page = 8)
  })
  output$eo_build_result <- renderUI({
    res <- rv$res$eo_build
    if (is.null(res)) return(NULL)
    tagList(tags$h6("2. Darwin Core archive"), result_ui(res))
  })

  observeEvent(input$run_qiime, {
    wb <- need_wb(); req(wb)
    rv$res$qiime <- with_run("Writing the QIIME 2 files", run_qiime(
      sd, wb, input$qi_sample_col, input$qi_manifests == "yes", input$qi_folder, input$qi_suffix == "yes",
      input$qi_suffix_col, input$qi_suffix_dir, input$qi_suffix_n, input$qi_suffix_delim))
  })
  output$qiime_result <- renderUI({
    res <- rv$res$qiime
    if (is.null(res)) return(help_text("The metadata and manifest files appear here, one set for each target gene."))
    result_ui(res, extra = if (res$ok) help_text("Import with qiime tools import, using the manifest, and pass the",
                                                 "metadata file to QIIME 2's analysis steps."))
  })

  # ------------------------------------------------------------ outputs
  output$runs_list <- renderUI({
    if (!length(rv$runs)) return(help_text("Nothing yet."))
    rows <- rev(rv$runs)
    tags$table(class = "table table-sm runs",
               tags$thead(tags$tr(tags$th("Time"), tags$th("Tool"), tags$th("Result"), tags$th("Files"))),
               tags$tbody(lapply(rows, function(r) tags$tr(
                 tags$td(r$time), tags$td(r$label),
                 tags$td(if (r$ok) tags$span(class = "pill accepted", "finished") else tags$span(class = "pill for-review", "stopped")),
                 tags$td(lapply(c(r$outputs, list(log = file.path(r$dir, "run_log.txt"))), function(p)
                   tags$span(class = "out-link", file_link(p))))))))
  })
  output$download_all <- downloadHandler(
    filename = function() paste0("FAIRe_tools_", format(Sys.time(), "%Y%m%d_%H%M"), ".zip"),
    content = function(file) {
      old <- setwd(sd); on.exit(setwd(old))
      parts <- intersect(c("runs", "files", "project_values.tsv"), list.files("."))
      zip::zip(file, parts, recurse = TRUE)
    })
  observeEvent(input$clear_session, {
    showModal(modalDialog(
      "This removes your files and everything the tools wrote in this session.",
      title = "Start again?", easyClose = TRUE,
      footer = tagList(modalButton("Cancel"), actionButton("confirm_clear", "Start again", class = "btn-danger"))))
  })
  observeEvent(input$confirm_clear, {
    removeModal()
    unlink(file.path(sd, c("runs", "files", "edna2obis_tables", "project_values.tsv")), recursive = TRUE)
    rv$files <- character(); rv$workbook <- NULL; rv$res <- list(); rv$runs <- list(); rv$identify <- NULL
    rv$map <- NULL; rv$map_args <- NULL; rv$profile <- NULL; rv$crosswalk <- NULL; rv$review_saved <- NULL
    rv$model <- NULL; rv$primers <- NULL; rv$demo <- FALSE; rv$eo_mapping <- NULL
    rv$pv <- data.frame(term = character(), value = character(), assay = character())
    rv$otu_n <- 1; rv$lib_n <- 1; rv$block_version <- rv$block_version + 1
  })
}

shinyApp(ui, server)
