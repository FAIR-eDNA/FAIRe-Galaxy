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
for (f in c("runner.R", "tools.R", "helpers.R", "demos.R", "ui.R"))
  source(file.path(getOption("faire.app_dir"), "R", f), local = FALSE)

options(shiny.maxRequestSize = 500 * 1024^2, DT.fillContainer = FALSE)

APP_VERSION <- "0.8.1"

# Colours from the logo: petrol, teal, navy, red, orange and yellow (darkened where white text sits
# on them, to keep it readable).
theme <- bs_theme(version = 5, primary = "#186c78", secondary = "#5b6770", success = "#1d7f74",
                  danger = "#c81e36", warning = "#f0cc3c", info = "#0c2a6c",
                  "font-size-base" = "0.95rem", base_font = font_collection("Segoe UI", "Helvetica Neue", "Arial", "sans-serif"))

ui <- page_navbar(
  id = "main",
  lang = "en",
  fillable = FALSE,
  title = tags$span(class = "brand", tags$img(src = "logo.png", alt = "", class = "brand-logo"), "FAIRe tools"),
  window_title = "FAIRe tools",
  theme = theme,
  header = tags$head(tags$link(rel = "icon", type = "image/png", href = "favicon.png"),
                     tags$link(rel = "stylesheet", href = "styles.css"), tags$script(src = "app.js")),
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
                       crosswalk_from = "", review_version = 0, review_saved = NULL, review_saved_d = NULL, changed = NULL, written = NULL,
                       model = NULL, model_used = character(),
                       primers = NULL, details = NULL,
                       pv = data.frame(term = character(), value = character(), assay = character()),
                       md_prov = data.frame(term = character(), assay = character(), value = character(),
                                            proposed = character(), tier = character()),
                       otu_n = 1, lib_n = 1, amp_n = 0, block_version = 0, demo = "", eo_mapping = NULL)

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

  # Messages in three kinds, each with its own icon and word. An error stays until it is closed and, when
  # it is about a field, is repeated under that field, which is scrolled into view (app.js). Warnings and
  # information close themselves.
  notify_error <- function(msg, field = NULL) {
    showNotification(tagList(icon("circle-xmark"), tags$b("Error: "), msg), type = "error", duration = NULL)
    if (!is.null(field)) session$sendCustomMessage("field_error", list(id = field, msg = msg))
    invisible(NULL)
  }
  notify_warning <- function(msg, duration = 10)
    showNotification(tagList(icon("triangle-exclamation"), tags$b("Warning: "), msg), type = "warning", duration = duration)
  notify_info <- function(msg, duration = 6)
    showNotification(tagList(icon("circle-info"), msg), type = "message", duration = duration)

  # Run a tool with a progress message; record and return its result.
  with_run <- function(message, expr) {
    res <- withProgress(message = message, value = 0.3, expr)
    record(res)
    if (!res$ok) notify_error(paste(res$label, "stopped. The result says why and what to do."))
    res
  }

  set_workbook <- function(path, from) {
    rv$workbook <- path
    rv$workbook_from <- from
  }

  # The result of a run: whether it worked, its files, and the tool's own messages.
  result_ui <- function(res, extra = NULL, show_files = TRUE) {
    if (is.null(res)) return(NULL)
    # the tool's warnings are shown, not left among its messages
    warn <- sub("^WARNING:\\s*", "", grep("^WARNING:", strsplit(res$log %||% "", "\n")[[1]], value = TRUE))
    status <- if (res$ok) {
      div(class = "res-ok", icon("circle-check"),
          paste0(res$label, " finished at ", res$time,
                 if (length(warn)) sprintf(", with %d %s (below)", length(warn), if (length(warn) == 1) "warning" else "warnings"), "."))
    } else {
      why <- explain_error(res$log)
      div(class = "res-fail", icon("circle-xmark"), tags$b("Error: "),
          paste0(res$label, " stopped at ", res$time, "."),
          if (nzchar(why)) tags$div(class = "res-why", why),
          tags$div(class = "res-why", HTML("The tool's own message is under <em>The tool's messages</em>, below.")))
    }
    files <- NULL
    if (show_files && length(res$outputs)) {
      files <- tags$ul(class = "file-out", lapply(names(res$outputs), function(nm) {
        p <- res$outputs[[nm]]
        csv <- csv_copy(p)
        tags$li(icon("file"), file_link(p), tags$span(class = "size", fmt_bytes(file.size(p))),
                if (!is.null(csv)) tags$span(class = "csv-copy", "(", file_link(csv, "as CSV, for Excel"), ")"))
      }))
    }
    warn_ui <- if (length(warn)) div(class = "res-warn", icon("triangle-exclamation"),
                                     tags$b(if (length(warn) == 1) "Warning:" else "Warnings:"),
                                     tags$ul(lapply(head(warn, 8), tags$li)),
                                     if (length(warn) > 8) sprintf("And %d more among the tool's messages.", length(warn) - 8))
    tagList(status, warn_ui, extra, files,
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
    by_kind <- if (is.null(kinds)) rep(FALSE, length(n)) else vapply(n, function(f) any(kind_of(f) %in% kinds), logical(1))
    n[by_name | by_kind]
  }
  # What a file was found to be: one kind per sheet of a workbook.
  kind_of <- function(name) {
    idf <- rv$identify
    if (is.null(idf)) return("")
    k <- unique(idf$kind[idf$file == name])
    if (length(k)) k else ""
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
      tags$td(if (s$ok[i]) icon("circle-check", class = "text-success", role = "img", `aria-label` = "ready")
              else icon("circle-xmark", class = "text-danger", role = "img", `aria-label` = "missing")),
      tags$td(s$item[i]), tags$td(tags$small(s$detail[i]))))))
  })

  has_work <- reactive(length(rv$files) > 0 || length(rv$runs) > 0 || nrow(rv$pv) > 0)
  observe(session$sendCustomMessage("has_work", has_work()))
  observeEvent(input$start_faireator, nav_select("main", "FAIRe-ator: a blank template"))
  observeEvent(input$start_mapper, {
    nav_select("main", "FAIRe mapper: from your own tables"); nav_select("mapper_steps", "a. Your files")
  })
  observeEvent(input$start_check, nav_select("main", "2. Check"))
  # A newer version on GitHub: said on the Start page, with how to get it
  output$update_notice <- renderUI({
    if (!newer_app_available()) return(NULL)
    div(class = "res-warn", icon("circle-up"), tags$b(" A newer version of this app is available."),
        " To update it, download what you want to keep from Outputs, close the app (press Esc in the R",
        "console, or Stop in RStudio), and run the start line again:",
        tags$pre(class = "mb-0 mt-1", tags$code(
          'source("https://raw.githubusercontent.com/FAIR-eDNA/FAIRe-Galaxy/main/shiny/start.R")')))
  })
  observeEvent(input$load_demo, {
    id <- input$demo_choice %||% names(DEMOS)[1]
    if (!has_work()) return(load_demo(id))
    showModal(modalDialog(
      title = "Load the demonstration data?",
      tags$p("It adds the demonstration's files to Your files (replacing any with the same names), clears the",
             "values for the whole project, and fills in the forms with the demonstration's settings. Files from",
             "another demonstration stay in Your files: Remove all files first to start clean."),
      footer = tagList(modalButton("Cancel"), actionButton("load_demo_ok", "Load it", class = "btn-primary"))))
  })
  observeEvent(input$load_demo_ok, { removeModal(); load_demo(input$demo_choice %||% names(DEMOS)[1]) })
  load_demo <- function(id) {
    demo <- DEMOS[[id]]
    for (f in list.files(file.path(DEMO_ROOT, demo$dir), full.names = TRUE)) {
      if (basename(f) == "README.md") next
      rv$files <- c(rv$files[names(rv$files) != basename(f)], add_to_library(file.path(sd, "files"), basename(f), f))
    }
    rv$demo <- id
    # The values for the whole project start empty: the person finds them in the demonstration's files
    # with find primers and find method details, and types the rest, as with their own data.
    rv$pv <- rv$pv[0, , drop = FALSE]
    rv$md_prov <- rv$md_prov[0, , drop = FALSE]
    rv$otu_n <- length(demo$otu); rv$lib_n <- length(demo$lib); rv$amp_n <- length(demo$amp)
    rv$block_version <- rv$block_version + 1
    updateCheckboxGroupInput(session, "map_sample_types", selected = demo$sample_types)
    updateRadioButtons(session, "map_assay_type", selected = demo$assay_type)
    updateTextInput(session, "fa_project_id", value = demo$project_id)
    updateTextInput(session, "fa_assay_name", value = demo$assay_name)
    updateTextInput(session, "ap_project_id", value = demo$project_id)
    updateTextInput(session, "ap_assay_name", value = demo$assay_name)
    updateTextInput(session, "ap_country", value = demo$country)
    updateSelectInput(session, "ap_date_order", selected = demo$date_order)
    if (length(demo$dwc)) {
      w <- demo$dwc
      updateTextInput(session, "dw_title", value = w$title); updateTextAreaInput(session, "dw_abstract", value = w$abstract)
      updateTextInput(session, "dw_keywords", value = w$keywords)
      updateTextInput(session, "dw_given", value = w$given); updateTextInput(session, "dw_surname", value = w$surname)
      updateTextInput(session, "dw_org", value = w$org); updateTextInput(session, "dw_email", value = w$email)
      updateSelectInput(session, "dw_licence", selected = w$licence)
    }
    if (id == "seames") seames_forms()
    rv$changed <- Sys.time()
    notify_info("The demonstration files are in Your files. Start with 1. Make a workbook, FAIRe mapper.", duration = 6)
  }
  # The conversion forms for the SEA-MES demonstration, which has reads in the SRA
  seames_forms <- function() {
    updateTextInput(session, "nb_bioproject", value = "PRJNA1263580")
    updateSelectInput(session, "nb_mandatory_fill", selected = "not applicable")
    updateSelectizeInput(session, "nb_duplicates", choices = "replicate", selected = "replicate")
    updateSelectInput(session, "ns_instrument", selected = "NextSeq 2000")
    updateRadioButtons(session, "ns_link", selected = "accessions")
    updateTextInput(session, "es_center", value = "CSIRO")
    updateTextInput(session, "er_center", value = "CSIRO")
    updateTextInput(session, "er_study", value = "PRJNA1263580")
    updateSelectInput(session, "er_instrument", selected = "NextSeq 2000")
    updateRadioButtons(session, "eo_taxa_source", selected = "mapping")
  }

  output$demo_status <- renderUI({
    if (!nzchar(rv$demo)) return(NULL)
    div(class = "demo-steps",
        tags$p(tags$b(paste0("Demonstration loaded: ", DEMOS[[rv$demo]]$title, ".")), " To follow it through:"),
        DEMOS[[rv$demo]]$steps())
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
        k1 <- if (length(k) > 1) sprintf("%d kinds of sheet", length(k)) else k
        ic <- if (grepl("xlsx$", n, ignore.case = TRUE)) "file-excel" else if (grepl("pdf$", n, ignore.case = TRUE)) "file-pdf"
              else if ("sequences (FASTA)" %in% k || grepl("\\.(fa|fasta|fna|fas)$", n, ignore.case = TRUE)) "dna"
              else if (grepl("txt$|md$", n, ignore.case = TRUE)) "file-lines" else "file-csv"
        tags$li(title = n, icon(ic),
                tags$span(class = "fname", n,
                          if (nzchar(k1[1])) tags$span(class = "kind", title = paste(k, collapse = ", "), k1)),
                preview_button(n),
                tags$button(type = "button", class = "rm-file", title = paste("Remove", n), `aria-label` = paste("Remove", n),
                            onclick = sprintf("Shiny.setInputValue('remove_file', %s, {priority: 'event'})",
                                              jsonlite::toJSON(n, auto_unbox = TRUE)),
                            icon("xmark")))
      })),
      actionLink("clear_files", "Remove all files", icon = icon("xmark")))
  })
  observeEvent(input$clear_files, {
    showModal(modalDialog(
      title = sprintf("Remove all %d files?", length(rv$files)),
      tags$p("They are removed from Your files. Results already written keep their own copies."),
      footer = tagList(modalButton("Cancel"), actionButton("clear_files_ok", "Remove them", class = "btn-danger"))))
  })
  observeEvent(input$clear_files_ok, { removeModal(); rv$files <- character(); rv$identify <- NULL })
  # One file at a time. The run folders keep their copies, so results already written are not affected.
  observeEvent(input$remove_file, {
    n <- input$remove_file
    if (!n %in% names(rv$files)) return()
    rv$files <- rv$files[names(rv$files) != n]
    if (!is.null(rv$identify)) {
      rv$identify <- rv$identify[rv$identify$file != n, , drop = FALSE]
      if (!nrow(rv$identify)) rv$identify <- NULL
    }
    notify_info(paste("Removed", n), duration = 3)
  })

  # ------------------------------------------------------------ a look inside a file
  preview_button <- function(n, label = NULL) {
    tags$button(type = "button", class = if (is.null(label)) "look-file" else "look-file with-label",
                title = paste("Look inside", n), `aria-label` = paste("Look inside", n),
                onclick = sprintf("Shiny.setInputValue('preview_file', %s, {priority: 'event'})",
                                  jsonlite::toJSON(n, auto_unbox = TRUE)),
                icon("eye"), label)
  }
  col_letters <- function(j) vapply(j, function(i) {
    s <- ""
    while (i > 0) { r <- (i - 1) %% 26; s <- paste0(LETTERS[r + 1], s); i <- (i - 1) %/% 26 }
    s
  }, character(1))
  raw_table_ui <- function(t, letters = FALSE) {
    if (is.null(t)) return(help_text("The app could not read this as a table."))
    d <- t$rows
    cut <- function(x) if (nchar(x) > 40) paste0(substr(x, 1, 39), "\u2026") else x
    tagList(
      div(class = "table-responsive preview-raw", tabindex = "0", `aria-label` = "The file's first rows",
          tags$table(class = "table table-sm table-bordered",
                     tags$thead(tags$tr(tags$th("Row"), lapply(seq_along(d), function(j)
                       tags$th(if (letters) col_letters(j) else j)))),
                     tags$tbody(lapply(seq_len(nrow(d)), function(i)
                       tags$tr(tags$th(i), lapply(d[i, ], function(x) tags$td(title = if (nchar(x) > 40) x, cut(x)))))))),
      if (t$more_cols) help_text(sprintf("And %d more columns.", t$more_cols)))
  }
  preview_body <- function(n, p) {
    kind <- sniff_file(p)
    table_note <- help_text("The first rows as they are in the file. Check which row holds the column names: if it",
                            "is not row 1, give its number as the row holding the column headers when you map the table.")
    switch(kind,
      pdf = {
        wd <- file.path(sd, "preview")
        dir.create(wd, showWarnings = FALSE)
        out <- file.path(wd, "pdf.json")
        run_python(file.path(app_dir(), "python", "pdf_preview.py"), c(tool_path("faire_mapper"), p, out), wd, timeout = 120)
        j <- if (file.exists(out)) jsonlite::fromJSON(out) else list(error = "the PDF could not be read")
        tagList(
          tags$p(tags$a(href = file_href(p), target = "_blank", icon("file-pdf"), "Open the PDF"),
                 if (!is.null(j$pages)) sprintf(" (%d pages)", j$pages)),
          if (!is.null(j$error)) div(class = "res-fail", icon("circle-xmark"), tags$b("Error: "), j$error)
          else if (!nzchar(trimws(j$text))) div(class = "res-warn", icon("triangle-exclamation"), tags$b("Warning: "),
                                                "This PDF has no text to read: its pages are",
                                                "pictures (a scan). Save it as text first, or type the primer names.")
          else tagList(help_text(paste0("Its text as the tools read it", if (isTRUE(j$cut)) " (the first part)", ".")),
                       tags$pre(class = "preview-text", tabindex = "0", j$text)))
      },
      workbook = {
        sh <- xlsx_sheets(p)
        if (!length(sh)) return(help_text("The app could not read this workbook."))
        shown <- head(sh, 10)
        tagList(
          help_text(sprintf("A workbook with %d sheet%s.", length(sh), if (length(sh) > 1) "s" else ""),
                    "The first rows of each sheet as they are in the file. Check which row holds the column names:",
                    "if it is not row 1 (FAIRe workbooks have them in row 3), give its number as the row holding the",
                    "column headers when you map the table."),
          do.call(bslib::navset_tab, lapply(shown, function(x)
            bslib::nav_panel(x, raw_table_ui(preview_raw_table(p, "workbook", sheet = x), letters = TRUE)))),
          if (length(sh) > length(shown)) help_text(sprintf("And %d more sheets.", length(sh) - length(shown))))
      },
      fasta = {
        l <- preview_lines(p, 12)
        l <- ifelse(nchar(l) > 100, paste0(substr(l, 1, 99), "\u2026"), l)
        tagList(help_text("A FASTA file of sequences: each starts with a line beginning with >. Its first lines:"),
                tags$pre(class = "preview-text", tabindex = "0", paste(l, collapse = "\n")))
      },
      tab = , csv = tagList(
        help_text(if (kind == "tab") "A table with tabs between its columns." else "A table with commas between its columns."),
        table_note, raw_table_ui(preview_raw_table(p, kind))),
      {
        l <- preview_lines(p, 120)
        txt <- paste(l, collapse = "\n")
        cut <- nchar(txt) > 6000
        tagList(help_text("Text. Its first", if (cut || length(l) == 120) "part" else "lines", "as they are in the file:"),
                tags$pre(class = "preview-text", tabindex = "0", if (cut) paste0(substr(txt, 1, 6000), "\u2026") else txt))
      })
  }
  observeEvent(input$preview_file, {
    n <- input$preview_file
    p <- fpath(n)
    if (is.null(p)) return()
    idf <- rv$identify
    said <- if (!is.null(idf) && n %in% idf$file) {
      i <- which(idf$file == n)
      tags$p(class = "preview-kind", tags$b("Identify your files says: "),
             paste(unique(idf$kind[i]), collapse = ", "), if (nzchar(idf$why[i[1]])) paste0(" (", idf$why[i[1]], ")"))
    }
    body <- withProgress(message = "Opening the file", value = 0.5, preview_body(n, p))
    showModal(modalDialog(
      title = tagList(icon("eye"), " ", n), size = "xl", easyClose = TRUE, footer = modalButton("Close"),
      tags$p(class = "preview-kind", fmt_bytes(file.size(p))), said, body))
  })

  # The workbook the mapper wrote is out of date once the review or the project values change after it.
  observeEvent(rv$pv, rv$changed <- Sys.time(), ignoreInit = TRUE)
  wb_stale <- reactive(identical(rv$workbook_from, "written by the FAIRe mapper") && !is.null(rv$written) &&
                         !is.null(rv$changed) && rv$changed > rv$written)
  stale_note <- function(link_id) {
    div(class = "res-warn stale-note", icon("triangle-exclamation"),
        tags$b("Warning: "), "out of date. It was written before your latest changes to the review or the project values. ",
        actionLink(link_id, "Write it again"))
  }
  goto_write <- function() {
    nav_select("main", "FAIRe mapper: from your own tables")
    nav_select("mapper_steps", "e. Write the workbook")
  }
  output$current_workbook <- renderUI({
    if (is.null(rv$workbook)) return(help_text("None yet. Write one with the FAIRe mapper, or choose one of your files on the Check page."))
    tagList(div(class = "wb-card", icon("file-excel"), file_link(rv$workbook), tags$br(), tags$small(rv$workbook_from)),
            if (wb_stale()) stale_note("goto_write_sidebar"))
  })
  observeEvent(input$goto_write_sidebar, goto_write())

  # Checks made as you type: a note under the field, gone once the value is fine.
  field_check <- function(id, msg) session$sendCustomMessage("field_check", list(id = id, msg = msg))
  for (pid_field in c("ap_project_id", "fa_project_id")) local({
    id <- pid_field
    observeEvent(input[[id]], {
      v <- trimws(input[[id]] %||% "")
      field_check(id, if (nzchar(v) && !grepl("^[A-Za-z0-9_-]+$", v))
        "Use letters, digits, hyphens and underscores only (no spaces)." else "")
    }, ignoreInit = TRUE)
  })
  observeEvent(input$ap_utc_offset, {
    v <- trimws(input$ap_utc_offset %||% "")
    field_check("ap_utc_offset", if (nzchar(v) && !grepl("^(Z|[+-](0[0-9]|1[0-4]):[0-5][0-9])$", v))
      "Give it as +10:00, -04:00 or Z (hours and minutes, with the sign)." else "")
  }, ignoreInit = TRUE)
  observe({
    used <- trimws(strsplit(input$ap_assay_name %||% "", ",")[[1]])
    odd <- setdiff(used[nzchar(used)], pv_assays())
    field_check("ap_assay_name", if (length(pv_assays()) && length(odd))
      sprintf("Not among the assays named in d: %s. The assays there: %s.", paste(odd, collapse = ", "),
              paste(pv_assays(), collapse = ", ")) else "")
  })

  # The status of each mapper step, shown beside its name in the step list (app.js puts it there).
  observe({
    st <- list(
      a = if (!is.null(rv$identify)) "done" else "",
      b = if (!is.null(rv$map)) "done" else "",
      c = if (is.null(rv$map)) "" else switch(review_status(), unsaved = "not saved",
                                              unreviewed = "", if (!is.null(rv$review_saved)) "done" else ""),
      d = if (nrow(rv$pv)) "done" else "",
      e = if (wb_stale()) "redo" else if (!is.null(rv$written) && identical(rv$workbook_from, "written by the FAIRe mapper")) "done" else "")
    session$sendCustomMessage("step_status", st)
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
    output[[paste0(id, "_stale")]] <- renderUI(if (wb_stale() && identical(input[[id]], "__current__"))
      stale_note(paste0("goto_write_", id)))
    observeEvent(input[[paste0("goto_write_", id)]], goto_write())
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
      return(notify_error("Give a project ID with no spaces or special characters.", "fa_project_id"))
    if (blank(input$fa_assay_name)) return(notify_error("Give at least one assay name.", "fa_assay_name"))
    if (!length(input$fa_sample_type)) return(notify_error("Choose at least one sample type.", "fa_sample_type"))
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
    if (!length(rv$files)) return(notify_error("Add your files first."))
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
        tags$td(tags$b(d$file[i]), if (!is.na(d$sheet[i] %||% NA) && nzchar(d$sheet[i])) tags$div(class = "examples", paste("sheet", d$sheet[i])),
                tags$div(preview_button(d$file[i], "Look inside"))),
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
                "file in the right places. Look inside a file to see its first rows or its text."),
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
  # The sample table: once a. Your files has run, only the files it found to be sample tables are
  # offered, with a note saying where the choice came from.
  output$map_table_ui <- renderUI({
    idf <- rv$identify
    found <- if (is.null(idf)) character() else intersect(unique(idf$file[idf$kind == "sample table"]), names(rv$files))
    ch <- if (length(found)) found else file_names("\\.(csv|tsv|txt|tab|xlsx)$", kinds = "sample table")
    demo_table <- if (nzchar(rv$demo)) DEMOS[[rv$demo]]$sample_table else ""
    default <- if (demo_table %in% ch) demo_table else guess_file("sample table")
    note <- if (length(found) == 1) {
      help_text("This is the file ", tags$em("a. Your files"), " identified as your sample table. If that is wrong,",
                "change its kind there.")
    } else if (length(found) > 1) {
      help_text(tags$em("a. Your files"), " found ", length(found), " files that look like sample tables. The mapping",
                "is for one table: choose the one that holds your sample details. If they are parts of one",
                "table, combine them into one file first.")
    } else {
      help_text("Choose the file that holds your sample details. Running ", tags$em("a. Your files"),
                " first finds it for you.")
    }
    tagList(selectInput("map_table", term_label("Sample table", "sample_table"), c("Choose a file" = "", ch),
                        selected = keep_or("map_table", default)),
            note)
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
    demo_dict <- if (nzchar(rv$demo)) DEMOS[[rv$demo]]$dictionary else ""
    selectInput("map_dictionary", term_label("Data dictionary (optional)", "data_dictionary"), c("None" = "", ch),
                selected = keep_or("map_dictionary", if (demo_dict %in% ch) demo_dict else ""), selectize = FALSE)
  })

  # An earlier review sheet (or crosswalk) of this table, to carry its decisions over. None by default: it
  # is used only when chosen. a. Your files finds review sheets and crosswalks (kind "crosswalk").
  output$map_earlier_ui <- renderUI({
    idf <- rv$identify
    found <- if (is.null(idf)) character() else intersect(unique(idf$file[idf$kind == "crosswalk"]), names(rv$files))
    # before a. Your files has run, any workbook or tab-separated file; after, only those it found
    ch <- if (!is.null(idf)) found else file_names("\\.(xlsx|tsv)$")
    tagList(
      selectInput("map_earlier", term_label("Earlier review (optional)", "earlier_review"), c("None" = "", ch),
                  selected = keep_or("map_earlier", ""), selectize = FALSE),
      help_text(if (length(found)) tagList(tags$em("a. Your files"),
                                           sprintf("found %d %s.", length(found),
                                                   if (length(found) == 1) "review sheet or crosswalk" else "review sheets or crosswalks")),
                "If you mapped this table before and kept the review sheet, choose it here. Your decisions are",
                "carried over, so you review only the new columns and any whose proposed term has changed."))
  })

  # Running the mapping again replaces the review, so it asks first when there is one, and offers to keep
  # the decisions for columns that are still there (an Accept only when the mapper still proposes the same term).
  observeEvent(input$run_map, {
    if (is.null(fpath(input$map_table))) return(notify_error("Choose your sample table.", "map_table"))
    if (!is.null(rv$map) && (!is.null(rv$review_saved_d) || review_status() == "unsaved")) {
      d <- review_state(); base <- review_defaults()
      n <- sum(paste(d$decision, d$replacement) != paste(base$decision, base$replacement))
      showModal(modalDialog(
        title = "Run the mapping again?",
        tags$p(sprintf(paste("You have reviewed this mapping (%d %s from the mapper's proposals). Running it again",
                             "replaces the proposals. You can keep your decisions for the columns that are still in the",
                             "table, or start the review afresh."), n, if (n == 1) "decision differs" else "decisions differ")),
        footer = tagList(modalButton("Cancel"), actionButton("map_fresh", "Start the review afresh"),
                         actionButton("map_keep", "Run it again, keeping my decisions", class = "btn-primary"))))
    } else do_map(FALSE)
  })
  observeEvent(input$map_keep, { removeModal(); do_map(TRUE) })
  observeEvent(input$map_fresh, { removeModal(); do_map(FALSE) })

  do_map <- function(keep) {
    tab <- fpath(input$map_table)
    if (is.null(tab)) return(notify_error("Choose your sample table.", "map_table"))
    # The decisions to carry over: this session's review (saved as a review sheet first, with any changes
    # on screen), or a review sheet chosen at "Mapping this table again?"
    earlier <- NULL; earlier_name <- ""
    if (keep && !is.null(rv$map)) {
      dir <- new_run_dir(sd, "review")
      out <- file.path(dir, "review_in_this_session.xlsx")
      write_review_decisions(rv$map$outputs$review_sheet, mark_model(review_state()), out, dir)
      if (file.exists(out)) { earlier <- out; earlier_name <- "your review in this session" }
    } else if (!is.null(fpath(input$map_earlier))) {
      earlier <- fpath(input$map_earlier); earlier_name <- input$map_earlier
    }
    sheet <- if (galaxy_ext(tab) == "xlsx") input$map_sheet %||% "" else ""
    args <- list(table = tab, table_name = input$map_table, sheet = sheet, header_row = input$map_header_row %||% 1,
                 assay_type = input$map_assay_type,
                 # Other means every sample type's fields, which the tools take as no sample types given
                 sample_types = if ("other" %in% input$map_sample_types) character() else input$map_sample_types %||% character(),
                 dictionary = fpath(input$map_dictionary))
    withProgress(message = "Proposing a mapping", value = 0.3, {
      prof <- record(run_profile(sd, tab, sheet, args$header_row))
      res <- record(run_map(sd, tab, sheet, args$header_row, args$assay_type, args$sample_types,
                            dictionary = args$dictionary, other_terms = isTRUE(input$map_other_terms),
                            table_name = args$table_name, earlier_review = earlier, earlier_review_name = earlier_name))
    })
    rv$res$map <- res
    rv$profile <- if (prof$ok) read_tsv(prof$outputs$profile) else NULL
    if (res$ok) {
      rv$map <- res; rv$map_args <- args
      rv$crosswalk <- res$outputs$review_sheet; rv$crosswalk_from <- "proposed, not yet reviewed"
      rv$review_version <- rv$review_version + 1; rv$review_saved <- NULL; rv$review_saved_d <- NULL
      rv$model <- NULL; rv$model_used <- character()
      rv$changed <- Sys.time()
      if (!is.null(earlier)) {
        # The tool filled in the decisions it carried over; saving them makes them the review in use
        e <- jsonlite::fromJSON(res$outputs$summary)$earlier_review
        save_review(review_state(), paste("carried over from", earlier_name))
        listed <- function(x) paste(unlist(x), collapse = ", ")
        kept <- sprintf("%d %s carried over from %s and saved.", e$carried,
                        if (e$carried == 1) "decision" else "decisions", earlier_name)
        todo <- unlist(e$to_review)
        msg <- c(kept,
                 if (!e$carried && length(unlist(e$new)) == nrow(review()$rows))
                   sprintf("None of the columns of this table is in %s: is it the review of another table?", earlier_name),
                 if (length(todo)) sprintf("%d %s to review in c. Review the mapping: %s.", length(todo),
                                           if (length(todo) == 1) "column" else "columns", listed(todo))
                 else "Nothing new needs reviewing.",
                 if (length(unlist(e$not_in_table)))
                   sprintf("In the earlier review but not in this table: %s.", listed(e$not_in_table)))
        if (length(todo) || !e$carried) notify_warning(paste(msg, collapse = " "), duration = NULL)
        else notify_info(paste(msg, collapse = " "), duration = 10)
      }
    }
  }

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
      if (length(s$ambiguous_dates)) div(
        class = "res-warn date-order", icon("triangle-exclamation"), tags$b("Warning: "),
        sprintf("dates such as %s in %s can be read day first or month first, and no value settles it. Which is it?",
                s$ambiguous_dates$example[1], paste(unique(s$ambiguous_dates$column), collapse = ", ")),
        radioButtons("map_date_order", NULL, inline = TRUE, selected = isolate(input$ap_date_order) %||% "stop",
                     c("Day first (dd/mm/yyyy)" = "dmy", "Month first (mm/dd/yyyy)" = "mdy", "Not sure yet" = "stop")),
        tags$small("This sets the date order in e. Write the workbook.")),
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
  observeEvent(input$map_date_order, updateSelectInput(session, "ap_date_order", selected = input$map_date_order))
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
    # From an earlier review: carried (its decision is filled in), check (accepted before, but the proposed
    # term has changed), new, or none
    e <- s$rows$earlier
    s$rows$earlier_kind <- ifelse(startsWith(e, "carried over"), "carried", ifelse(startsWith(e, "check again"), "check",
                                  ifelse(nzchar(e), "new", "")))
    s
  })

  dec_id <- function(i) paste0("rvd", rv$review_version, "_", i)
  rep_id <- function(i) paste0("rvr", rv$review_version, "_", i)

  # A row's starting decision: the sheet's own (with any carried over from an earlier review filled in).
  init_choice <- function(r, i, field) r[[field]][i]
  # The decisions as they stand on screen (the starting ones until a person changes them).
  review_state <- function() {
    r <- review()$rows
    n <- seq_len(nrow(r))
    data.frame(input = r$input,
               decision = vapply(n, function(i) input[[dec_id(i)]] %||% init_choice(r, i, "decision"), character(1)),
               replacement = vapply(n, function(i) input[[rep_id(i)]] %||% init_choice(r, i, "replacement"), character(1)),
               stringsAsFactors = FALSE)
  }
  review_defaults <- function() {
    r <- review()$rows
    data.frame(input = r$input, decision = r$decision, replacement = r$replacement, stringsAsFactors = FALSE)
  }
  same_decisions <- function(a, b) identical(paste(a$input, a$decision, a$replacement), paste(b$input, b$decision, b$replacement))
  # "unsaved": decisions on screen that are not saved; "unreviewed": nothing changed or saved yet; "" otherwise
  review_status <- function() {
    if (is.null(rv$map)) return("")
    cur <- review_state()
    if (!is.null(rv$review_saved_d)) return(if (same_decisions(cur, rv$review_saved_d)) "" else "unsaved")
    if (!identical(rv$crosswalk_from, "proposed, not yet reviewed")) return("")
    if (same_decisions(cur, review_defaults())) "unreviewed" else "unsaved"
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
          if (any(r$earlier_kind == "carried"))
            tags$span(class = "badge text-bg-info", sum(r$earlier_kind == "carried"), "carried over from your earlier review"),
          if (any(r$earlier_kind == "check" | (r$earlier_kind == "new" & r$kind == "review")))
            tags$span(class = "badge text-bg-warning", sum(r$earlier_kind == "check" | (r$earlier_kind == "new" & r$kind == "review")),
                      "new or changed to review"),
          tags$label(class = "toggle", tags$input(type = "checkbox", checked = NA,
                                                  onchange = "document.getElementById('review-grid').classList.toggle('hide-accepted', !this.checked)"),
                     " Show the mapper's accepted matches"),
          if (any(r$earlier_kind == "carried"))
            tags$label(class = "toggle", tags$input(type = "checkbox", checked = NA,
                                                    onchange = "document.getElementById('review-grid').classList.toggle('hide-carried', !this.checked)"),
                       " Show the decisions carried over"),
          if (nzchar(rv$demo) && identical(rv$map_args$table_name, DEMOS[[rv$demo]]$sample_table))
            actionButton("demo_answers", "Fill in the authors' answers", icon = icon("flask"), class = "btn-sm"),
          actionButton("save_review", "Save the review", icon = icon("floppy-disk"), class = "btn-primary btn-sm")),
      help_text(paste0("The decisions in use: ", rv$crosswalk_from, ".")),
      div(class = "review-excel",
          tags$h6("Or do the review in Excel"),
          help_text("If you would rather do the review in Excel, download the review sheet, fill in the decisions",
                    "(sorting or filtering the rows is fine, but keep every row), then add it back here when you",
                    "have finished. Its decisions then show in the rows below, and are saved."),
          div(class = "review-files",
              downloadButton("review_download", "Download the review sheet", class = "btn-sm"),
              fileInput("review_upload", NULL, accept = ".xlsx", buttonLabel = "Add the review sheet you filled in",
                        placeholder = "Excel (.xlsx)", width = "440px"))))
  })

  # The mapper's call in each row, coloured as in the counts above the review
  call_badge <- c(review = "text-bg-warning", "no-match" = "text-bg-secondary", accept = "text-bg-success")
  output$review_table <- renderUI({
    s <- review()
    r <- s$rows
    model <- rv$model
    show <- order(r$earlier_kind == "carried", r$earlier_kind != "check",
                  match(r$kind, c("review", "no-match", "accept")), seq_len(nrow(r)))
    rows <- lapply(show, function(i) {
      x <- r[i, ]
      has_term <- nzchar(x$proposed)
      dec_choices <- c("No decision" = "", if (has_term) c("Accept" = "Accept"), "Reject" = "Reject", "Change" = "Change")
      dsel <- isolate(input[[dec_id(i)]]) %||% init_choice(r, i, "decision")
      rsel <- isolate(input[[rep_id(i)]]) %||% init_choice(r, i, "replacement")
      lists <- s$choices[[x$input]] %||% list(best = character(), rest = character())
      other <- setdiff(rsel, c("", lists$best, lists$rest))
      opt <- function(v) lapply(v, function(t) tags$option(value = t, selected = if (identical(t, rsel)) NA, t))
      rep_select <- tags$select(
        id = rep_id(i), class = "form-select form-select-sm", `aria-label` = paste("Replacement FAIRe term for", x$input),
        # choosing a replacement sets the decision to Change
        onchange = sprintf("if (this.value) { var d = document.getElementById('%s'); d.value = 'Change'; $(d).trigger('change'); }", dec_id(i)),
        tags$option(value = "", selected = if (!nzchar(rsel)) NA, "No replacement"),
        if (length(other)) opt(other),
        if (length(lists$best)) tags$optgroup(label = "Best candidates for this column", opt(lists$best)),
        if (length(lists$rest)) tags$optgroup(label = "Every other term", opt(lists$rest)))
      m <- if (!is.null(model)) model[model$column == x$input, , drop = FALSE] else NULL
      tags$div(
        class = paste("rv-row", paste0("call-", x$kind), if (nzchar(x$earlier_kind)) paste0("earlier-", x$earlier_kind)),
        div(class = "rv-col", tags$b(x$input), tags$div(class = "examples", x$examples)),
        div(class = "rv-proposed", if (has_term) x$proposed else tags$span(class = "muted", "none"),
            if (nzchar(x$score)) tags$small(class = "score", paste0(" ", x$score))),
        div(class = "rv-status", tags$span(class = paste("badge", if (x$kind %in% names(call_badge)) call_badge[[x$kind]] else "text-bg-secondary"), x$call),
            if (nzchar(x$earlier_kind)) tags$span(
              class = paste("earlier", x$earlier_kind), title = x$earlier,
              switch(x$earlier_kind, carried = "carried over", check = "check again",
                     new = if (startsWith(x$earlier, "no decision")) "no decision before" else "new"))),
        div(class = "rv-evidence", x$reasoning,
            if (!is.null(m) && nrow(m)) tags$div(class = "model-says", icon("robot"),
                                                  paste0(" Model suggests ", if (is.na(m$term[1]) || !nzchar(m$term[1])) "no term" else m$term[1],
                                                         if (nzchar(m$reason[1] %||% "")) paste0(": ", m$reason[1]) else ""),
                                                  " ", tags$a(href = "#", class = "use-model",
                                                              onclick = sprintf("Shiny.setInputValue('use_model_row', {i: %d, n: Math.random()}); return false;", i),
                                                              "Use this suggestion"))),
        div(class = "rv-choice",
            tagAppendAttributes(selectInput(dec_id(i), NULL, dec_choices, selected = dsel, selectize = FALSE, width = "100%"),
                                `aria-label` = paste("Reviewer's decision for", x$input), .cssSelector = "select"),
            tags$small(class = "kept-as", "If rejected, kept as ", x$kept_as)),
        div(class = "rv-replace", rep_select))
    })
    tagList(
      div(id = "review-grid",
        div(class = "rv-row rv-head", div(term_label("Input term", "input_term"), " and some values (grey text)"),
            div("Proposed FAIRe term and score"), div(term_label("Mapper's call", "mappers_call")), div("Mapper's reasoning"),
            div(term_label("Reviewer's decision", "decision")), div("Replacement FAIRe term")),
        rows),
      div(class = "review-foot",
          actionButton("save_review_bottom", "Save the review", icon = icon("floppy-disk"), class = "btn-primary"),
          help_text("Saves the decisions above. You can also save at the top of the review.")))
  })

  # Save decisions into a copy of the review sheet and use it for the workbook.
  # Decisions that still follow a model's suggestion, marked so the review sheet records them
  mark_model <- function(d) {
    d$chosen_by <- ""
    for (i in which(d$input %in% rv$model_used)) {
      got <- model_decision(match(d$input[i], review()$rows$input))
      if (!is.null(got) && identical(got$decision, d$decision[i]) && identical(got$replacement, d$replacement[i]))
        d$chosen_by[i] <- "model"
    }
    d
  }
  save_review <- function(d, from) {
    d <- mark_model(d)
    dir <- new_run_dir(sd, "review")
    stem <- sub("\\.[^.]*$", "", rv$map_args$table_name %||% "table")
    out <- file.path(dir, paste0(stem, "_review_sheet.xlsx"))
    s <- write_review_decisions(rv$map$outputs$review_sheet, d, out, dir)
    res <- record(run_result("review", "FAIRe mapper: review the mapping", dir, list(s), list(review_sheet = out)))
    if (!res$ok || !file.exists(out)) {
      notify_error("The review could not be saved. See the log of this step under Outputs.")
      return(invisible(NULL))
    }
    r <- review()$rows
    k <- r$kind[match(d$input, r$input)]
    rv$crosswalk <- out; rv$crosswalk_from <- from
    rv$review_saved_d <- d[, c("input", "decision", "replacement")]; rv$changed <- Sys.time()
    rv$review_saved <- list(accept = sum(d$decision == "Accept"), reject = sum(d$decision == "Reject"),
                            change = sum(d$decision == "Change"),
                            open = sum(d$decision == "" & k == "review", na.rm = TRUE),
                            bad = d$input[d$decision == "Change" & !nzchar(d$replacement)],
                            model = sum(d$chosen_by == "model"), time = format(Sys.time(), "%H:%M:%S"))
    invisible(out)
  }

  observeEvent(input$save_review, {
    req(rv$map)
    save_review(review_state(), "reviewed here")
  })
  observeEvent(input$save_review_bottom, {
    req(rv$map)
    if (!is.null(save_review(review_state(), "reviewed here")))
      notify_info(sprintf("Review saved at %s.", rv$review_saved$time), duration = 5)
  })

  output$review_download <- downloadHandler(
    filename = function() paste0(sub("\\.[^.]*$", "", rv$map_args$table_name %||% "table"), "_review_sheet.xlsx"),
    content = function(file) {
      dir <- new_run_dir(sd, "review_download")
      s <- write_review_decisions(rv$map$outputs$review_sheet, mark_model(review_state()), file.path(dir, "review_sheet.xlsx"), dir)
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
      return(notify_error(paste("That file could not be read:", conditionMessage(up))))
    d <- review_state()
    now <- review()$rows
    got <- up$rows[!duplicated(up$rows$input), , drop = FALSE]
    k <- match(d$input, got$input)
    # an Accept of a term the mapper no longer proposes (a sheet from an earlier mapping) is not taken
    stale <- !is.na(k) & got$decision[pmax(k, 1)] == "Accept" &
      nzchar(got$proposed[pmax(k, 1)]) & got$proposed[pmax(k, 1)] != now$proposed[match(d$input, now$input)]
    use <- !is.na(k) & !stale
    d$decision[use] <- got$decision[k[use]]
    d$replacement[use] <- got$replacement[k[use]]
    show_decisions(d)
    save_review(d, paste("from", f$name))
    gone <- d$input[is.na(k)]
    extra <- setdiff(got$input, d$input)
    notes <- c(
      if (length(gone)) sprintf("%s no row in the sheet, so %s unchanged: %s.",
                                if (length(gone) == 1) "1 column has" else paste(length(gone), "columns have"),
                                if (length(gone) == 1) "its decision is" else "their decisions are",
                                paste(gone, collapse = ", ")),
      if (any(stale)) sprintf("%s accepted a term the mapper no longer proposes, so %s: %s.",
                              if (sum(stale) == 1) "1 row of the sheet" else paste(sum(stale), "rows of the sheet"),
                              if (sum(stale) == 1) "it is left for you to decide" else "they are left for you to decide",
                              paste(d$input[stale], collapse = ", ")),
      if (length(extra)) sprintf("%s not %s of this table and %s left out: %s.",
                                 if (length(extra) == 1) "1 row is" else paste(length(extra), "rows are"),
                                 if (length(extra) == 1) "a column" else "columns",
                                 if (length(extra) == 1) "was" else "were", paste(extra, collapse = ", ")),
      if (any(duplicated(up$rows$input))) "Some input terms are in the sheet twice; their first rows were used.",
      if (length(gone) || length(extra) || any(stale))
        "If it is from an earlier mapping, choose it at b. Propose a mapping, under Mapping this table again?, instead.")
    msg <- paste(c(sprintf("The decisions in %s are on screen and saved.", f$name), notes), collapse = " ")
    if (length(notes)) notify_warning(msg, duration = 15) else notify_info(msg)
  })

  # The authors' answers for the demonstration's sample table (DEMOS in R/demos.R).
  observeEvent(input$demo_answers, {
    req(nzchar(rv$demo))
    ans <- DEMOS[[rv$demo]]$decisions
    d <- review_state()
    k <- match(d$input, ans$input)
    d$decision[!is.na(k)] <- ans$decision[k[!is.na(k)]]
    d$replacement[!is.na(k)] <- ans$replacement[k[!is.na(k)]]
    show_decisions(d)
    notify_info("Filled in. Look them over, then save the review.")
  })

  # A model's answer for a column for review: its term is the proposed one (Accept), another one (Change)
  # or none (Reject).
  # The decision a model's suggestion makes for row i: its term is the proposed one (Accept), another one
  # (Change) or none (Reject).
  model_decision <- function(i) {
    r <- review()$rows
    a <- rv$model[rv$model$column == r$input[i], , drop = FALSE]
    if (!nrow(a)) return(NULL)
    term <- if (is.na(a$term[1])) "" else a$term[1]
    proposed <- trimws(sub("\\s*\\(.*\\)\\s*$", "", r$proposed[i]))
    if (!nzchar(term)) return(list(decision = "Reject", replacement = ""))
    if (term == proposed || term == r$proposed[i]) return(list(decision = "Accept", replacement = ""))
    lists <- review()$choices[[r$input[i]]]
    all <- c(lists$best, lists$rest)
    hit <- all[trimws(sub("\\s*\\(.*\\)\\s*$", "", all)) == term]
    list(decision = "Change", replacement = if (length(hit)) hit[1] else term)
  }
  # A model's suggestion becomes a decision only row by row, when the person chooses it after checking it
  observeEvent(input$use_model_row, {
    req(rv$model)
    i <- as.integer(input$use_model_row$i)
    got <- model_decision(i); req(got)
    d <- review_state()
    d$decision[i] <- got$decision; d$replacement[i] <- got$replacement
    show_decisions(d[i, , drop = FALSE])
    rv$model_used <- union(rv$model_used, review()$rows$input[i])
  })

  output$review_saved <- renderUI({
    s <- rv$review_saved
    if (is.null(s)) return(NULL)
    div(class = "res-ok", icon("circle-check"),
        sprintf("Review saved at %s: %d accepted, %d rejected, %d changed.", s$time, s$accept, s$reject, s$change),
        if (isTRUE(s$model > 0)) sprintf(" %d of these follow%s the model's suggestions, which the review sheet records.",
                                        s$model, if (s$model == 1) "s" else ""),
        if (s$open) tags$span(sprintf(" %s for review %s no decision, so %s kept as %s own term%s, unless you tick 'Also write the matches still for review' in step e.",
                                      if (s$open == 1) "1 row" else paste(s$open, "rows"), if (s$open == 1) "has" else "have",
                                      if (s$open == 1) "it is" else "they are", if (s$open == 1) "its" else "their",
                                      if (s$open == 1) "" else "s")),
        if (length(s$bad)) tags$span(class = "text-danger", sprintf(" Change with no replacement term for %s: these are kept as their own terms.", paste(s$bad, collapse = ", "))),
        tags$br(), inline("Next, ", actionLink("goto_primers", "d. Methods and project values"), "."))
  })
  observeEvent(input$goto_primers, nav_select("mapper_steps", "d. Methods and project values"))

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
    tagList(result_ui(res), if (!is.null(rv$model)) help_text("The suggestions now show beside each row for review. Check",
                                                               "each against its column, then choose", tags$em("Use this suggestion"),
                                                               "on that row to make it your decision."))
  })

  output$own_crosswalk_ui <- renderUI({
    selectInput("own_crosswalk", "Crosswalk from your files", c("Choose a file" = "", file_names("\\.(tsv|csv|txt)$", kinds = "crosswalk")))
  })
  observeEvent(input$use_own_crosswalk, {
    p <- fpath(input$own_crosswalk)
    if (is.null(p)) return(notify_error("Choose the crosswalk from your files.", "own_crosswalk"))
    rv$crosswalk <- p; rv$crosswalk_from <- "your own crosswalk"
    notify_info("The workbook will be written with your crosswalk.")
  })

  # ------------------------------------------------------------ mapper d: methods and project values
  output$pr_texts_ui <- renderUI({
    ch <- file_names("\\.(txt|md|pdf)$", kinds = "text")
    sel <- isolate(input$pr_texts) %||% (if (nzchar(rv$demo)) intersect(DEMOS[[rv$demo]]$methods, ch) else ch[vapply(ch, function(f) identical(kind_of(f), "text"), logical(1))])
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
  output$pr_own_ui <- renderUI(selectInput("pr_own", term_label("My own primer table", "own_primer_table"),
                                           c("Choose a file" = "", file_names("\\.(tsv|tab|txt)$", kinds = "primer table"))))
  observeEvent(input$run_primers, {
    texts <- unname(unlist(lapply(input$pr_texts, fpath)))
    if (input$pr_mode == "text" && !length(texts)) return(notify_error("Choose your methods (text or PDF) at the top of this step.", "pr_texts"))
    if (input$pr_mode == "names" && blank(input$pr_names)) return(notify_error("Type at least one name."))
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
        div(class = "how-to",
            tags$b("Choose the primer pairs you used, one for each assay"),
            tags$ol(
              tags$li("Each row is a published primer pair that matches your methods (or the names you typed).",
                      "When both sequences in your methods match a pair in the reference table, it is an exact",
                      "match and comes first: usually these are the pairs you used, one for each assay.",
                      "Add the exact matches adds them all at once, each with its assay name; check them in the",
                      "table on the right, and delete any that were not used for these data (methods sometimes",
                      "give the sequences of primers from a pilot comparison, or of blocking primers)."),
              tags$li("Pairs found only from a primer name, for a gene whose sequences your methods already give,",
                      "are less likely (one name can belong to several published pairs), so they are hidden. Show",
                      "them if a pair you used is missing."),
              tags$li("Click the row of a pair you used, and check it against the paper it cites. Its assay name is",
                      "filled in below from the reference table; change it if you call the assay something else."),
              tags$li("Press Add this pair to the projectMetadata. The pair's names, sequences, gene, target taxon and",
                      "references go into the table on the right: check them there, and change any that do not fit",
                      "your study."),
              tags$li("Do the same for each of your other assays (say COI as well as 16S). The assay names you give",
                      "here are filled in for you in e. Write the workbook, so they stay the same."))),
        uiOutput("pr_exact_ui"),
        uiOutput("pr_show_all_ui"),
        DTOutput("primers_table"),
        uiOutput("pr_chosen"),
        layout_columns(col_widths = c(6, 6),
                       textInput("pr_assay", term_label("Assay this pair was used for", "primer_assay"),
                                 value = if (nzchar(rv$demo)) DEMOS[[rv$demo]]$primer_assay else "", placeholder = "for example Fish16S"),
                       div(class = "pt-4", actionButton("pr_add", "Add this pair to the projectMetadata", icon = icon("arrow-right"))))))
  })
  # Pairs from a methods text say how likely each is; the less likely ones are hidden unless asked for.
  less_likely <- function(d) {
    if (!"how_likely" %in% names(d)) return(rep(FALSE, nrow(d)))
    startsWith(ifelse(is.na(d$how_likely), "", as.character(d$how_likely)), "less likely")
  }
  primers_shown <- reactive({
    d <- rv$primers; req(d)
    if (isTRUE(input$pr_show_all)) d else d[!less_likely(d), , drop = FALSE]
  })
  output$pr_show_all_ui <- renderUI({
    n <- sum(less_likely(rv$primers %||% data.frame()))
    if (n) checkboxInput("pr_show_all", sprintf("Show the %d less likely %s", n, if (n == 1) "pair" else "pairs"),
                         isTRUE(isolate(input$pr_show_all)))
  })
  exact_rows <- function(d) {
    if (is.null(d) || !"how_likely" %in% names(d)) return(integer())
    which(startsWith(ifelse(is.na(d$how_likely), "", as.character(d$how_likely)), "exact match"))
  }
  output$pr_exact_ui <- renderUI({
    n <- length(exact_rows(rv$primers))
    if (n) actionButton("pr_add_exact", sprintf("Add the exact %s (%d) to the projectMetadata",
                                                if (n == 1) "match" else "matches", n),
                        icon = icon("check-double"), class = "btn-primary btn-sm mb-2")
  })
  # Puts a pair's values into the project values for an assay, replacing what that assay had.
  add_pair <- function(r, assay) {
    f <- intersect(primer_fields, names(r))
    f <- f[nzchar(trimws(ifelse(is.na(unlist(r[f])), "", unlist(r[f]))))]
    pv <- rv$pv
    pv <- pv[!(pv$term %in% f & pv$assay == assay), , drop = FALSE]
    rv$pv <- rbind(pv, data.frame(term = f, value = unname(unlist(r[f])), assay = assay))
    length(f)
  }
  observeEvent(input$pr_add_exact, {
    d <- rv$primers
    k <- exact_rows(d)
    if (!length(k)) return()
    names <- make.unique(vapply(k, function(i) default_assay(d[i, , drop = FALSE]), ""), sep = "_")
    for (j in seq_along(k)) add_pair(d[k[j], , drop = FALSE], names[j])
    notify_info(sprintf("%d %s added, for %s. Check them in the table on the right.", length(k),
                             if (length(k) == 1) "pair" else "pairs", paste(names, collapse = " and ")), duration = 8)
  })
  # The assay name for a chosen pair: the reference table's name for it, as a FAIRe assay_name
  # (letters, digits, dots, hyphens and underscores), or its gene when it has none.
  default_assay <- function(r) {
    a <- if ("assay_name" %in% names(r) && !is.na(r$assay_name)) trimws(r$assay_name) else ""
    if (!nzchar(a) && "target_gene" %in% names(r) && !is.na(r$target_gene)) a <- sub("\\s.*", "", r$target_gene)
    gsub("^_+|_+$", "", gsub("[^A-Za-z0-9_.-]+", "_", a))
  }
  observeEvent(input$primers_table_rows_selected, {
    i <- input$primers_table_rows_selected
    if (length(i)) updateTextInput(session, "pr_assay", value = default_assay(primers_shown()[i, , drop = FALSE]))
  })
  output$primers_table <- renderDT({
    d <- primers_shown()
    cols <- c(how_likely = "How likely", query = "Found from", matched_by = "Found by", assay_name = "Assay", target_gene = "Gene",
              pcr_primer_name_forward = "Forward primer", pcr_primer_forward = "Forward sequence",
              pcr_primer_name_reverse = "Reverse primer", pcr_primer_reverse = "Reverse sequence",
              pcr_primer_reference_forward = "Reference", notes = "Notes")
    keep <- intersect(names(cols), names(d))
    # "exact match" stands out in green, so the pairs the study most likely used are easy to see
    if ("how_likely" %in% keep) {
      h <- htmltools::htmlEscape(ifelse(is.na(d$how_likely), "", as.character(d$how_likely)))
      d$how_likely <- sub("^exact match:?\\s*", '<span class="likely-exact">exact match</span><br>', h)
    }
    datatable(d[, keep], rownames = FALSE, selection = "single", class = "compact stripe", colnames = unname(cols[keep]),
              escape = which(keep != "how_likely"), options = list(scrollX = TRUE, pageLength = 5, dom = "tip"))
  })
  output$pr_chosen <- renderUI({
    i <- input$primers_table_rows_selected
    if (!length(i)) return(help_text("No pair chosen yet: click a row of the table."))
    r <- primers_shown()[i, ]
    nm <- function(x) if (x %in% names(r) && !is.na(r[[x]])) r[[x]] else ""
    div(class = "res-ok", icon("circle-check"),
        sprintf(" Chosen: %s / %s (%s).", nm("pcr_primer_name_forward"), nm("pcr_primer_name_reverse"),
                if (nzchar(nm("target_gene"))) nm("target_gene") else "gene not given"))
  })
  observeEvent(input$pr_add, {
    i <- input$primers_table_rows_selected
    if (!length(i)) return(notify_error("Choose a primer pair in the table first."))
    r <- primers_shown()[i, ]
    assays <- split_assays(input$pr_assay)
    for (a in assays) n <- add_pair(r, a)
    notify_info(sprintf("%d values added for %s.", n,
                        if (all(nzchar(assays))) paste(assays, collapse = " and ") else "every assay"))
  })

  # The project terms of the chosen section of the checklist (PCR and primers first), or all of them
  # grouped by section.
  observe({
    t <- checklist_terms()
    t <- t[grepl("projectMetadata", t$sheet), , drop = FALSE]
    sec <- input$pv_section %||% "PCR"
    order <- c("PCR", "Library preparation sequencing", "Bioinformatics", "Project", "Data management",
               "Targeted assay detection", "Sample collection")
    if (sec != "all") t <- t[t$section == sec, , drop = FALSE]
    groups <- intersect(c(order, setdiff(unique(t$section), order)), unique(t$section))
    ch <- setNames(lapply(groups, function(g) { x <- t$term[t$section == g]; setNames(as.list(x), x) }), groups)
    updateSelectizeInput(session, "pv_term", choices = ch, selected = character(), server = FALSE)
  })
  output$pv_table <- renderDT({
    datatable(rv$pv, rownames = FALSE, editable = list(target = "cell"), class = "compact stripe",
              options = list(pageLength = 8, dom = "tip", autoWidth = FALSE,
                             columnDefs = list(list(width = "36%", targets = 0), list(width = "44%", targets = 1),
                                               list(width = "20%", targets = 2))),
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
    if (length(i)) {
      gone <- paste(rv$pv$term[i], rv$pv$assay[i])
      rv$md_prov <- rv$md_prov[!paste(rv$md_prov$term, rv$md_prov$assay) %in% gone, , drop = FALSE]
      rv$pv <- rv$pv[-i, , drop = FALSE]
    }
  })
  observeEvent(input$pv_add, {
    if (blank(input$pv_term) || blank(input$pv_value)) return(notify_error("Choose a term and give a value.", "pv_term"))
    rv$pv <- rbind(rv$pv, data.frame(term = input$pv_term, value = input$pv_value, assay = split_assays(input$pv_assay)))
    updateTextInput(session, "pv_value", value = "")
  })
  output$pv_file_ui <- renderUI(selectInput("pv_file", NULL, c("Choose a file" = "", file_names("\\.(tsv|tab|txt|csv|xlsx)$", kinds = "project values"))))
  observeEvent(input$pv_load, {
    p <- fpath(input$pv_file); req(p)
    if (galaxy_ext(p) == "xlsx") {
      if (!"Method details" %in% xlsx_sheets(p))
        return(notify_error("This workbook is not a review sheet from find method details."))
      d <- read_method_review(p)
    } else {
      d <- if (galaxy_ext(p) == "csv") read_csv(p) else read_tsv(p)
      if (is.null(d) || !all(c("term", "value") %in% names(d)))
        return(notify_error("The table needs columns named term and value."))
      if (!"assay" %in% names(d)) d$assay <- ""
    }
    add_values(d[, c("term", "value", "assay")])
  })
  # Values added to the project values; a term already there for the same assay keeps its value.
  add_values <- function(d) {
    d[] <- lapply(d, function(x) trimws(as.character(x)))
    d <- d[nzchar(d$term) & nzchar(d$value), , drop = FALSE]
    have <- paste(rv$pv$term, rv$pv$assay)
    dup <- paste(d$term, d$assay) %in% have
    rv$pv <- rbind(rv$pv, d[!dup, , drop = FALSE])
    notify_info(paste0(sum(!dup), " values added", if (any(dup)) paste0("; ", sum(dup), " left out, as their terms ",
                            "already have a value (delete it first to replace it)") else "", "."), duration = 6)
  }

  # ------------------------------------------------------------ mapper d: other method details
  observeEvent(input$run_details, {
    texts <- unname(unlist(lapply(input$pr_texts, fpath)))
    if (!length(texts)) return(notify_error("Choose your methods (text or PDF) at the top of this step.", "pr_texts"))
    assays <- unique(rv$pv$assay[nzchar(rv$pv$assay)])
    res <- with_run("Reading the methods", run_method_details(sd, texts, input$pr_texts, paste(assays, collapse = ","),
                                                              input$md_assay_type %||% "metabarcoding"))
    rv$res$details <- res
    rv$details <- if (res$ok) read_tsv(res$outputs$proposals) else NULL
  })
  # The assay type chosen for the mapping (b. Propose a mapping) is the default here too
  observeEvent(input$map_assay_type, {
    if (input$map_assay_type %in% c("metabarcoding", "targeted"))
      updateRadioButtons(session, "md_assay_type", selected = input$map_assay_type)
  }, ignoreInit = TRUE)
  output$details_result <- renderUI({
    res <- rv$res$details
    if (is.null(res)) return(NULL)
    d <- rv$details
    tbl <- NULL
    if (!is.null(d) && nrow(d)) {
      ck <- checklist_terms()
      tier <- if ("confidence" %in% names(d)) d$confidence else rep("check", nrow(d))
      item <- function(i) {
        desc <- ck$description[match(d$term[i], ck$term)]
        div(class = "md-item",
            div(class = "md-head",
                tags$input(type = "checkbox", id = paste0("md_keep_", i), class = "md-keep", `data-tier` = tier[i],
                           `aria-label` = paste("Keep", d$term[i])),
                tags$label(`for` = paste0("md_keep_", i), tags$b(d$term[i])),
                if ("level" %in% names(d) && nzchar(d$level[i]))
                  tags$span(class = paste("md-level", if (d$level[i] %in% c("Mandatory", "Highly recommended")) "md-level-high"),
                            d$level[i]),
                tags$span(class = "md-section", d$section[i]),
                if (!is.na(desc) && nzchar(desc)) bslib::tooltip(
                  tags$span(class = "term-help", tabindex = "0", role = "button", `aria-label` = paste("What is", d$term[i]),
                            icon("circle-question")), desc)),
            div(class = "md-fields",
                tagAppendAttributes(textAreaInput(paste0("md_val_", i), NULL, d$value[i], rows = if (nchar(d$value[i]) > 70) 3 else 1),
                                    `aria-label` = paste("Value for", d$term[i]), .cssSelector = "textarea"),
                tagAppendAttributes(textInput(paste0("md_assay_", i), NULL, d$assay[i], placeholder = "assay (all)"),
                                    `aria-label` = paste("Assay for", d$term[i]), .cssSelector = "input")),
            if ("tested" %in% names(d) && nzchar(d$tested[i])) div(class = "md-tested", "Record: ", d$tested[i]),
            if (nzchar(d$note[i])) div(class = "md-note", d$note[i]),
            tags$details(class = "md-evidence", tags$summary(substr(d$evidence[i], 1, 140),
                                                             if (nchar(d$evidence[i]) > 140) "…"),
                         if (nchar(d$evidence[i]) > 140) d$evidence[i]))
      }
      rel <- which(tier == "reliable")
      chk <- which(tier != "reliable")
      tbl <- tagList(
        help_text("Tick the values to keep, after checking each against its sentence (open a sentence to read all of",
                  "it). Correct a value in its box if it is nearly right. When a term has several values (two storage",
                  "temperatures, say), keep the one for your eDNA samples. Give the assay only for a value that",
                  "holds for some assays and not others; separate several with commas (Fish16S, MiFish)."),
        div(class = "md-list",
            if (length(rel)) tagList(div(class = "md-part md-part-reliable", paste0(
              "Found reliably (", length(rel), "): terms the tool has proposed reliably in published papers it was ",
              "tested on")), lapply(rel, item)),
            if (length(chk)) tagList(div(class = "md-part md-part-check", paste0(
              "Also found in the methods (", length(chk), "): check each against its sentence before you tick it. ",
              "These terms are less reliable, or a check found a problem")), lapply(chk, item))),
        div(class = "btn-row",
            actionButton("md_add", "Add the ticked values to the projectMetadata", icon = icon("arrow-right")),
            if (length(rel)) actionLink("md_all", "Tick all reliable values"), actionLink("md_none", "Untick all")),
        help_text("Or download the review sheet, fill it in with Excel and load it on the right; it also lists the",
                  "method terms not found, to fill in."))
    } else if (res$ok) {
      tbl <- help_text("No method details found in these files.")
    }
    tagList(result_ui(res), tbl)
  })
  observeEvent(input$md_all, session$sendCustomMessage("md_tick", "reliable"))
  observeEvent(input$md_none, session$sendCustomMessage("md_tick", FALSE))
  md_pending <- reactiveVal(NULL)
  md_add_now <- function(vals) {
    vals[] <- lapply(vals, function(x) trimws(as.character(x)))
    # one row for each assay of a value given for several
    vals <- do.call(rbind, lapply(seq_len(nrow(vals)), function(j) {
      a <- split_assays(vals$assay[j])
      v <- vals[rep(j, length(a)), , drop = FALSE]
      v$assay <- a
      v
    }))
    added <- !paste(vals$term, vals$assay) %in% paste(rv$pv$term, rv$pv$assay) & nzchar(vals$value)
    add_values(vals[, c("term", "value", "assay")])
    # where each value added came from, for the workbook's log: what the tool proposed and how reliable its term is
    prov <- vals[added, c("term", "assay", "value", "proposed", "tier"), drop = FALSE]
    keep <- !paste(rv$md_prov$term, rv$md_prov$assay) %in% paste(prov$term, prov$assay)
    rv$md_prov <- rbind(rv$md_prov[keep, , drop = FALSE], prov)
    session$sendCustomMessage("md_tick", FALSE)
  }
  observeEvent(input$md_add, {
    d <- rv$details; req(d)
    keep <- as.integer(input$md_kept %||% integer())
    keep <- keep[keep >= 1 & keep <= nrow(d)]
    if (!length(keep)) return(notify_error("Tick the values to keep first."))
    tier <- if ("confidence" %in% names(d)) d$confidence else rep("check", nrow(d))
    assay <- vapply(keep, function(i) trimws(input[[paste0("md_assay_", i)]] %||% ""), character(1))
    each <- unlist(lapply(seq_along(keep), function(j) paste(d$term[keep[j]], split_assays(assay[j]))))
    twice <- unique(sub(" .*", "", each[duplicated(each)]))
    if (length(twice))
      return(notify_error(paste0("More than one value is ticked for ", paste(twice, collapse = ", "),
                                     ". Keep one value per term (or give each its assay).")))
    vals <- data.frame(term = d$term[keep],
                       value = vapply(keep, function(i) input[[paste0("md_val_", i)]] %||% d$value[i], character(1)),
                       assay = vapply(keep, function(i) input[[paste0("md_assay_", i)]] %||% "", character(1)),
                       proposed = d$value[keep], tier = tier[keep], stringsAsFactors = FALSE)
    chk <- which(tier[keep] != "reliable")
    if (!length(chk)) return(md_add_now(vals))
    # Values to check: one look at them all, with their sentences, before they are added
    md_pending(vals)
    showModal(modalDialog(
      title = sprintf("%d of the ticked values %s to check", length(chk), if (length(chk) == 1) "is a value" else "are values"),
      help_text("These terms are less reliable, or a check found a problem with the value. Add them if you have",
                "compared each with its sentence; otherwise go back and check them."),
      tags$ul(class = "md-confirm", lapply(chk, function(j) {
        i <- keep[j]
        tags$li(tags$b(d$term[i]), " = ", vals$value[j],
                if (nzchar(d$note[i] %||% "")) tags$div(class = "md-note", d$note[i]),
                tags$div(class = "md-confirm-sentence", substr(d$evidence[i], 1, 300),
                         if (nchar(d$evidence[i]) > 300) "…"))
      })),
      footer = tagList(modalButton("Go back and check them"),
                       actionButton("md_add_confirm", "I have checked them: add them", class = "btn-primary")),
      size = "l", easyClose = TRUE))
  })
  observeEvent(input$md_add_confirm, {
    removeModal()
    vals <- md_pending(); req(vals)
    md_pending(NULL)
    md_add_now(vals)
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
  output$pv_download <- downloadHandler("project_values.csv", function(file) write_csv(rv$pv, file))

  # ------------------------------------------------------------ mapper e: write the workbook
  output$apply_inputs_summary <- renderUI({
    if (is.null(rv$map_args)) return(div(class = "res-info", icon("circle-info"), "Propose a mapping first (step b)."))
    help_text(tags$b("Sample table: "), rv$map_args$table_name, tags$br(), tags$b("Crosswalk: "),
              basename(rv$crosswalk %||% ""), paste0(" (", rv$crosswalk_from, ")"), tags$br(),
              tags$b("Project values: "), nrow(rv$pv), " (step d)")
  })

  observeEvent(input$otu_add, rv$otu_n <- rv$otu_n + 1)
  observeEvent(input$otu_remove, rv$otu_n <- max(0, rv$otu_n - 1))
  observeEvent(input$lib_add, rv$lib_n <- rv$lib_n + 1)
  observeEvent(input$lib_remove, rv$lib_n <- max(0, rv$lib_n - 1))
  observeEvent(input$amp_add, rv$amp_n <- rv$amp_n + 1)
  observeEvent(input$amp_remove, rv$amp_n <- max(0, rv$amp_n - 1))

  demo_block <- function(kind, i) {
    if (!nzchar(rv$demo)) return(list())
    blocks <- DEMOS[[rv$demo]][[kind]]
    if (i <= length(blocks)) blocks[[i]] else list()
  }
  bid <- function(kind, i, field) paste0(kind, rv$block_version, "_", i, "_", field)
  bval <- function(kind, i, field, default = "") {
    v <- isolate(input[[bid(kind, i, field)]])
    if (!is.null(v)) return(v)
    demo_block(kind, i)[[field]] %||% default
  }

  # The assay names given in d. Methods and project values, offered wherever e asks for an assay, so the
  # names stay the same and the project values link to the right OTU tables and libraries.
  pv_assays <- reactive({ a <- unique(trimws(rv$pv$assay)); a[!is.na(a) & nzchar(a)] })
  assay_input <- function(id, label, value) {
    ch <- unique(c(pv_assays(), if (nzchar(value)) value))
    selectizeInput(id, label, c("", ch), selected = value,
                   options = list(create = TRUE, placeholder = if (length(ch)) "choose or type" else "type a name"))
  }
  ap_assay_auto <- reactiveVal("")
  observe({
    a <- paste(pv_assays(), collapse = ", ")
    now <- trimws(isolate(input$ap_assay_name) %||% "")
    if (nzchar(a) && (!nzchar(now) || identical(now, ap_assay_auto()))) {
      updateTextInput(session, "ap_assay_name", value = a)
      ap_assay_auto(a)
    }
  })
  # The sheets of a file chosen in an OTU table block, for its Excel sheet drop-downs. The first choice
  # (empty) uses the first sheet, as the tools do when no sheet is given.
  sheet_choices <- function(file) {
    p <- fpath(file)
    sh <- if (!is.null(p) && galaxy_ext(p) == "xlsx") xlsx_sheets(p) else character()
    c(stats::setNames("", if (length(sh)) "First sheet" else "Not an Excel workbook"), sh)
  }
  # When a block's OTU table or taxonomy table changes, its sheet list follows: a sheet the new file
  # does not have goes back to the first sheet.
  observe({
    for (i in seq_len(rv$otu_n)) {
      for (pair in list(c("file", "sheet"), c("taxa", "taxa_sheet"))) {
        f <- input[[bid("otu", i, pair[1])]]
        if (is.null(f)) next
        id <- bid("otu", i, pair[2])
        ch <- sheet_choices(f)
        cur <- isolate(input[[id]]) %||% ""
        updateSelectInput(session, id, choices = ch, selected = if (cur %in% ch) cur else "")
      }
    }
  })

  output$otu_blocks <- renderUI({
    n <- rv$otu_n
    if (!n) return(help_text("No OTU tables. The workbook will hold the sample and project metadata only."))
    ch <- c("Choose a file" = "", file_names("\\.(csv|tsv|tab|txt|xlsx)$", kinds = "OTU or ASV table"))
    # A demonstration can add a sentence to the run ID's note, saying where its run ID came from
    run_note <- if (nzchar(rv$demo)) DEMOS[[rv$demo]]$run_note
    lapply(seq_len(n), function(i) {
      b <- function(field) bid("otu", i, field)
      div(class = "block",
          tags$h6(paste("OTU table", i)),
          selectInput(b("file"), term_label("OTU or ASV table", "otu_table"), ch, selected = bval("otu", i, "file")),
          layout_columns(
            col_widths = c(4, 4, 4),
            assay_input(b("assay"), term_label("Assay", "assay"),
                        bval("otu", i, "assay", if (length(pv_assays()) == 1) pv_assays() else "")),
            textInput(b("run"), term_label("Sequencing run ID", "run_id", run_note), bval("otu", i, "run")),
            selectInput(b("stage"), term_label("Write as", "stage"), c("final (otuFinal, taxaFinal)" = "final", "raw (otuRaw, taxaRaw)" = "raw"),
                        selected = bval("otu", i, "stage", "final"))),
          accordion(open = FALSE, accordion_panel(
            "More settings for this table (optional)",
            help_text(GLOSSARY[["more_for_table"]]),
            # plain drop-downs, so 'In the OTU table' can be chosen again after a file
            selectInput(b("taxa"), term_label("Taxonomy table (optional)", "taxonomy_table"),
                        c("In the OTU table" = "", file_names("\\.(csv|tsv|tab|txt|xlsx)$", kinds = "taxonomy table")),
                        selected = bval("otu", i, "taxa"), selectize = FALSE),
            selectInput(b("sequences"), term_label("Sequences of this table (FASTA, optional)", "sequences"),
                        # FASTA files by name, or a .txt file only when a. Your files found it holds sequences
                        c("In the OTU table" = "", file_names("\\.(fa|fasta|fna|fas)$", kinds = "sequences (FASTA)")),
                        selected = bval("otu", i, "sequences"), selectize = FALSE),
            help_text("Choose a taxonomy table if this OTU table does not hold the taxonomy itself. Choose a FASTA",
                      "file if the table names its sequences (ASV_1, ASV_2 and so on) without holding the DNA",
                      "sequences, as an LCA output does; the names in the FASTA file must match those in the table.",
                      "Both files must first be added in a. Your files."),
            help_text("If the OTU table or the taxonomy table is an Excel workbook with more than one sheet,",
                      "choose the sheet that holds it. The lists show the sheets of the files chosen above, and",
                      "the first sheet is used if you leave them as they are."),
            layout_columns(
              col_widths = c(6, 6),
              selectInput(b("sheet"), "Excel sheet (OTU table)",
                          sheet_choices(bval("otu", i, "file")), selected = bval("otu", i, "sheet"), selectize = FALSE),
              selectInput(b("taxa_sheet"), "Excel sheet (taxonomy table)",
                          sheet_choices(bval("otu", i, "taxa")), selected = bval("otu", i, "taxa_sheet"), selectize = FALSE)),
            selectInput(b("layout"), term_label("Layout", "layout"), c("Work it out" = "detect", "Samples as columns" = "columns",
                                                 "Samples as rows" = "rows", "Long (one row per sample and OTU)" = "long"),
                        selected = bval("otu", i, "layout", "detect")),
            help_text("The last three boxes name columns of the OTU table, and are needed only for some tables. If one",
                      "table holds the reads of several assays, give the column that says which assay each row",
                      "belongs to. If the table has a column giving each ASV's taxon name after your own checking",
                      "and curation (which can differ from the name the classifier assigned), give that column: the",
                      "app keeps every ASV in the raw tables, and builds the final tables from the ASVs that have a",
                      "curated name. If the table has more than one lineage column (from SILVA and PR2, say), give",
                      "the one to use."),
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
            textInput(b("assay"), "Assays of these libraries", bval("lib", i, "assay", paste(pv_assays(), collapse = ", "))),
            textInput(b("filter"), "Only libraries whose name holds", bval("lib", i, "filter")),
            textInput(b("run"), term_label("Sequencing run ID", "run_id"), bval("lib", i, "run"))),
          textInput(b("sheet"), "Excel sheet (optional)", bval("lib", i, "sheet")))
    })
  })

  at_of <- function(a) if (a$assay_type == "any") "metabarcoding" else a$assay_type
  output$amp_blocks <- renderUI({
    n <- rv$amp_n
    if (!n) return(help_text("No qPCR or ddPCR results. Add a table for a targeted assay."))
    ch <- c("Choose a file" = "", file_names("\\.(csv|tsv|tab|txt|xlsx)$"))
    lapply(seq_len(n), function(i) {
      b <- function(field) bid("amp", i, field)
      div(class = "block",
          tags$h6(paste("Results table", i)),
          selectInput(b("file"), term_label("qPCR or ddPCR results", "amp_table"), ch, selected = bval("amp", i, "file")),
          layout_columns(
            col_widths = c(6, 6),
            textInput(b("assay_column"), "Column that gives the assay (optional)", bval("amp", i, "assay_column"),
                      placeholder = "assay_name, Assay or Target"),
            textInput(b("sheet"), "Excel sheet (optional)", bval("amp", i, "sheet"))),
          help_text("Give the column only when it is not called assay_name, Assay or Target, or when the table has",
                    "several such columns. Its values must be the assay names above."))
    })
  })

  do_apply <- function() {
    a <- rv$map_args
    if (is.null(a)) return(notify_error("Propose a mapping first (step b)."))
    pid <- trimws(input$ap_project_id)
    if (!nzchar(pid)) return(notify_error("Give a project ID.", "ap_project_id"))
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
    amps <- list()
    for (i in seq_len(rv$amp_n)) {
      p <- fpath(g("amp", i, "file")); if (is.null(p)) next
      amps[[length(amps) + 1]] <- list(path = p, name = g("amp", i, "file"), sheet = g("amp", i, "sheet"),
                                       assay_column = g("amp", i, "assay_column"))
    }
    if (length(amps) && at_of(a) != "targeted")
      return(notify_error(paste("qPCR and ddPCR results are for targeted assays: choose Targeted as the assay type in",
                                "b. Propose a mapping and run it again, or remove the results tables.")))
    # The assay names used here should be the ones the project values were given for in d.
    used <- trimws(unlist(strsplit(c(input$ap_assay_name %||% "", vapply(otus, `[[`, "", "assay"),
                                     vapply(libs, `[[`, "", "assay")), ",")))
    odd <- setdiff(unique(used[nzchar(used)]), pv_assays())
    if (length(pv_assays()) && length(odd))
      return(notify_error(sprintf(paste(
        "The assay name%s %s %s not among the assays in d. Methods and project values (%s). Use the same names,",
        "so the project values go with the right OTU tables and libraries."),
        if (length(odd) == 1) "" else "s", paste(odd, collapse = ", "), if (length(odd) == 1) "is" else "are",
        paste(pv_assays(), collapse = ", ")), "ap_assay_name"))
    pv_path <- NULL
    if (nrow(rv$pv)) {
      pv_path <- file.path(sd, "project_values.tsv")
      pv <- rv$pv
      k <- match(paste(pv$term, pv$assay, trimws(pv$value)), paste(rv$md_prov$term, rv$md_prov$assay, rv$md_prov$value))
      pv$source <- ifelse(is.na(k), "", "find method details")
      pv$proposed <- ifelse(is.na(k), "", rv$md_prov$proposed[k])
      pv$tier <- ifelse(is.na(k), "", rv$md_prov$tier[k])
      write_tsv(pv, pv_path)
    }
    utc <- trimws(input$ap_utc_offset %||% "")
    if (nzchar(utc) && !grepl("^(Z|[+-](0[0-9]|1[0-4]):[0-5][0-9])$", utc))
      return(notify_error("Give the UTC offset as +10:00, -04:00 or Z, or leave it empty.", "ap_utc_offset"))
    at <- at_of(a)
    res <- with_run("Writing the FAIRe workbook", run_apply(
      sd, a$table, a$sheet, a$header_row, rv$crosswalk, at, a$sample_types, pid,
      assay_name = input$ap_assay_name, country = input$ap_country, utc_offset = utc, date_order = input$ap_date_order,
      include_review = input$ap_include_review, project_values = pv_path, req_lev = input$ap_req_lev,
      drop_unmapped = input$ap_drop_unmapped, otu_tables = otus, library_tables = libs, amp_tables = amps,
      table_name = a$table_name))
    if (!is.null(pv_path)) file.copy(pv_path, res$dir)
    rv$res$apply <- res
    if (res$ok && file.exists(res$outputs$workbook)) {
      set_workbook(res$outputs$workbook, "written by the FAIRe mapper")
      rv$written <- Sys.time()
    }
  }
  observeEvent(input$run_apply, apply_clicked())
  observeEvent(input$run_apply_bottom, apply_clicked())
  apply_clicked <- function() {
    st <- review_status()
    if (st == "unsaved") {
      showModal(modalDialog(
        title = "Your review has changes that are not saved",
        tags$p("The workbook is written from the saved review. Save your changes first, or write it without them."),
        footer = tagList(modalButton("Cancel"), actionButton("apply_without", "Write without these changes"),
                         actionButton("apply_save_first", "Save the review, then write", class = "btn-primary"))))
    } else if (st == "unreviewed") {
      n <- sum(review()$rows$kind == "review")
      showModal(modalDialog(
        title = "The mapping has not been reviewed",
        tags$p(sprintf(paste("Only the mapper's accepted matches will be written. The %d %s for review will be kept as",
                             "your own terms, so their values will not be under FAIRe terms."), n, if (n == 1) "row" else "rows")),
        footer = tagList(modalButton("Cancel"), actionButton("apply_without", "Write it anyway"),
                         actionButton("apply_goto_review", "Go to the review", class = "btn-primary"))))
    } else do_apply()
  }
  observeEvent(input$apply_save_first, { removeModal(); save_review(review_state(), "reviewed here"); do_apply() })
  observeEvent(input$apply_without, { removeModal(); do_apply() })
  observeEvent(input$apply_goto_review, { removeModal(); nav_select("mapper_steps", "c. Review the mapping") })
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
        tags$p(inline("This is now the workbook in use. Next, ", actionLink("goto_check", "check it with FAIRe-fier"), ".")),
        tags$details(tags$summary("What the mapper wrote, and what is still empty"), tags$pre(class = "log", apply_log()))))
  })
  observeEvent(input$goto_check, nav_select("main", "2. Check"))
  wb_preview_server("apply_preview", reactive(if (!is.null(rv$res$apply) && rv$res$apply$ok) rv$res$apply$outputs$workbook))

  # ------------------------------------------------------------ check
  observeEvent(input$run_fairefier, {
    wb <- picked_workbook("ck_wb")
    if (is.null(wb)) return(notify_error("Choose a workbook.", "ck_wb"))
    rv$res$fairefier <- with_run("Checking the workbook", run_fairefier(sd, wb, input$ck_version))
  })
  # Repositories refuse a dataset without every mandatory term: said on the Convert page, more strongly
  # when the last FAIRe-fier check in this session did not pass
  output$cv_mandatory_warning <- renderUI({
    res <- rv$res$fairefier
    s <- if (!is.null(res) && file.exists(res$outputs$summary %||% "")) jsonlite::fromJSON(res$outputs$summary) else NULL
    failed <- !is.null(s) && !isTRUE(s$valid)
    div(class = if (failed) "res-fail" else "res-warn", icon("triangle-exclamation"),
        tags$b("Before you convert: "),
        "GBIF, OBIS, NCBI and ENA accept a dataset only when every mandatory FAIRe term has a value, or a FAIRe",
        "missing-value term where it is truly unknown (such as 'missing: not collected' or 'not applicable').",
        if (failed) tags$b("The last FAIRe-fier check did not pass: fix its errors and the mandatory terms with no value,",
                           "then check again, or the files written here are likely to be refused.")
        else "Check the workbook with FAIRe-fier first (step 2), and fix its errors and any mandatory term with no value.")
  })
  output$fairefier_result <- renderUI({
    res <- rv$res$fairefier
    if (is.null(res)) return(help_text("FAIRe-fier's findings appear here."))
    s <- if (file.exists(res$outputs$summary %||% "")) jsonlite::fromJSON(res$outputs$summary) else NULL
    sheets <- if (!is.null(s)) intersect(c("projectMetadata", "sampleMetadata", "experimentRunMetadata"), names(s)) else character()
    tagList(
      if (!is.null(s)) tagList(
        div(class = if (isTRUE(s$valid)) "res-ok big" else "res-fail big",
            icon(if (isTRUE(s$valid)) "circle-check" else "circle-xmark"),
            if (isTRUE(s$valid)) "The workbook passes." else tagList(tags$b("Error: "), "the workbook does not pass yet.")),
        if (isTRUE(s$valid)) help_text("A pass means the format and the required fields are right, not that the values",
                                       "are: those rest on your review of the mapping and the method details.")
        else help_text("GBIF, OBIS, NCBI and ENA will not accept the dataset until it passes: every mandatory term needs",
                       "a value, or a FAIRe missing-value term (such as 'missing: not collected') where it is truly unknown."),
        div(class = "stats", lapply(sheets, function(sh) {
          x <- s[[sh]]
          stat_tile(if (isTRUE(x$valid)) "passes" else sprintf("%d errors", x$errors),
                    sprintf("%s, %d warnings", sh, x$warnings), if (isTRUE(x$valid)) "accepted" else "failed")
        })),
        if (!is.null(s$checklist_note)) help_text(s$checklist_note)),
      if (file.exists(res$outputs$issues %||% "")) tagList(
        tags$h6("Errors and warnings"),
        help_text("Errors must be fixed. Warnings are worth a look: an extra term, for example, may be a field you",
                  "meant to name differently. fairefier_highlighted.xlsx, below, is your workbook with each problem cell",
                  "filled yellow (warning) or red (error) and a note on the cell giving the message."),
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
    if (is.null(wb)) notify_error("Choose the workbook to convert, at the top of the page.", "cv_wb")
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
        # a targeted project lists its assays in project_level as 'A | B'
        if (!is.na(r)) assays <- unique(trimws(unlist(strsplit(na.omit(unlist(pm[r, (tc + 1):ncol(pm)])), "|", fixed = TRUE))))
      }
    }
    erm <- if ("experimentRunMetadata" %in% sheets) read_faire_sheet(wb, "experimentRunMetadata") else NULL
    runs <- if (!is.null(erm) && "seq_run_id" %in% names(erm)) unique(erm$seq_run_id[nzchar(erm$seq_run_id)]) else character()
    libs <- if (!is.null(erm) && "lib_id" %in% names(erm)) unique(erm$lib_id[nzchar(erm$lib_id)]) else character()
    smd <- if ("sampleMetadata" %in% sheets) read_faire_sheet(wb, "sampleMetadata") else NULL
    list(assays = assays[nzchar(assays)], runs = runs, libs = libs, sheets = sheets,
         sample_fields = if (is.null(smd)) character() else names(smd),
         run_fields = if (is.null(erm)) character() else names(erm))
  })
  # The Convert fields that name the workbook's fields, assays or runs offer them, and still take typing.
  offer <- function(id, choices) {
    cur <- isolate(input[[id]])
    updateSelectizeInput(session, id, choices = unique(c(cur, choices)), selected = cur)
  }
  observe({
    w <- wb_info()
    offer("nb_duplicates", w$sample_fields)
    offer("nb_exclude", w$sample_fields)
    offer("eo_location", w$sample_fields)
    offer("er_assay_name", w$assays)
    offer("dw_assays", w$assays)
    offer("er_seq_runs", w$runs)
    offer("qi_suffix_col", w$run_fields)
    offer("ns_runs_values", switch(input$ns_runs_by %||% "all", assay = w$assays, seq_run = w$runs, lib_id = w$libs,
                                   character()))
  })
  joined <- function(x) paste(x %||% character(), collapse = ", ")

  output$ns_accessions_ui <- renderUI({
    ch <- file_names("\\.(tsv|tab|txt|csv)$")
    selectInput("ns_accessions", "BioSample accession table (from NCBI)", c("Choose a file" = "", ch),
                selected = keep_or("ns_accessions", if (nzchar(rv$demo)) DEMOS[[rv$demo]]$accessions else ""))
  })
  output$er_receipt_ui <- renderUI({
    ch <- file_names("\\.xml$")
    selectInput("er_receipt", "ENA sample receipt", c("Choose a file" = "", ch),
                selected = keep_or("er_receipt", if (nzchar(rv$demo)) DEMOS[[rv$demo]]$receipt else ""))
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
      input$nb_convert_dates, input$nb_mixs_units, input$nb_title, input$nb_title_columns, input$nb_extra, joined(input$nb_exclude)))
  })
  observeEvent(input$run_ncbi_sra, {
    wb <- need_wb(); req(wb)
    acc <- if (input$ns_link == "accessions") fpath(input$ns_accessions) else NULL
    if (input$ns_link == "accessions" && is.null(acc)) return(notify_error("Choose the BioSample accession table.", "ns_accessions"))
    org <- if (input$nb_organism == "other") input$nb_organism_other else input$nb_organism
    rv$res$ncbi_sra <- with_run("Writing the SRA table", run_ncbi_sra(
      sd, wb, input$ns_runs_by, joined(input$ns_runs_values), input$ns_associated, input$ns_instrument, acc, org))
  })
  observeEvent(input$run_ena_sample, {
    wb <- need_wb(); req(wb)
    if (blank(input$es_center)) return(notify_error("Give your centre name.", "es_center"))
    taxon <- if (input$es_taxon == "other") input$es_taxon_id else input$es_taxon
    rv$res$ena_sample <- with_run("Writing the sample XML", run_ena_sample(sd, wb, trimws(input$es_center), taxon, input$es_convert_dates))
  })
  observeEvent(input$run_ena_run, {
    wb <- need_wb(); req(wb)
    rec <- fpath(input$er_receipt)
    if (is.null(rec)) return(notify_error("Choose ENA's sample receipt from your files.", "er_receipt"))
    if (blank(input$er_study) || blank(input$er_center)) return(notify_error("Give the study accession and centre name.", if (blank(input$er_study)) "er_study" else "er_center"))
    rv$res$ena_run <- with_run("Writing the experiment and run XML", run_ena_run(
      sd, wb, rec, trimws(input$er_study), trimws(input$er_center), input$er_instrument,
      if (input$er_assay == "one") input$er_assay_name %||% "" else "", input$er_assay_suffix, joined(input$er_seq_runs), input$er_ftp))
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
    if (blank(input$mdt_assay) || blank(input$mdt_run)) return(notify_error("Give the assay and sequencing run.", if (blank(input$mdt_assay)) "mdt_assay" else "mdt_run"))
    o <- source_of(input$mdt_otu, wb); t <- source_of(input$mdt_taxa, wb)
    if (is.null(o) || is.null(t)) return(notify_error("Choose the OTU and taxonomy tables.", if (is.null(o)) "mdt_otu" else "mdt_taxa"))
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
    if (!length(an)) return(notify_error("Choose a taxonomy table for at least one assay."))
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
    if (!length(an)) return(notify_error("Choose the taxonomy and abundance tables."))
    mapping <- NULL
    if (input$eo_taxa_source == "mapping") {
      mapping <- if (identical(input$eo_mapping, "__last__")) rv$eo_mapping else fpath(sub("^file:", "", input$eo_mapping %||% ""))
      if (is.null(mapping)) return(notify_error("Choose the mapping table, or match the taxa first."))
    }
    eml <- if (isTRUE(input$eo_eml)) list(select = "form", title = input$eo_title, abstract = input$eo_abstract,
                                          given_name = input$eo_given, surname = input$eo_surname,
                                          organisation = input$eo_org, email = input$eo_email, licence = input$eo_licence,
                                          keywords = "eDNA, metabarcoding")
           else list(select = "none")
    rv$res$eo_build <- with_run("Building the Darwin Core archive", run_edna2obis_build(
      sd, wb, an, mapping, input$eo_api, text_dates = input$eo_text_dates, location_fields = joined(input$eo_location),
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

  # FAIRe to Darwin Core: presence and absence records, with an optional taxon table from Your files.
  output$dw_taxa_ui <- renderUI({
    ch <- file_names("\\.(tsv|tab|csv|txt)$")
    demo_taxa <- if (nzchar(rv$demo)) DEMOS[[rv$demo]]$dwc$taxa %||% "" else ""
    tagList(selectInput("dw_taxa", term_label("Taxon table (optional)", "taxon_table"), c("None" = "", ch),
                        selected = keep_or("dw_taxa", if (demo_taxa %in% ch) demo_taxa else ""), selectize = FALSE))
  })
  observeEvent(input$run_dwc, {
    wb <- need_wb(); req(wb)
    cc <- trimws(input$dw_country_code %||% "")
    if (nzchar(cc) && !grepl("^[A-Za-z]{2}$", cc)) return(notify_error("Give a two-letter country code, such as AU.", "dw_country_code"))
    email <- trimws(input$dw_email %||% "")
    if (nzchar(email) && !grepl("^[^@[:space:]]+@[^@[:space:]]+$", email)) return(notify_error("Give an email address.", "dw_email"))
    orcid <- trimws(input$dw_orcid %||% "")
    if (nzchar(orcid) && !grepl("^(https://orcid.org/)?[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$", orcid))
      return(notify_error("Give an ORCID such as 0000-0002-1825-0097, or leave it empty.", "dw_orcid"))
    rv$res$dwc <- with_run("Writing the Darwin Core archive", run_faire2dwc(
      sd, wb, assays = joined(input$dw_assays), absences = isTRUE(input$dw_absences), taxa = fpath(input$dw_taxa %||% ""),
      country_code = cc, target = input$dw_target, title = input$dw_title, abstract = input$dw_abstract,
      keywords = input$dw_keywords, licence = input$dw_licence, given_name = input$dw_given, surname = input$dw_surname,
      organisation = input$dw_org, email = email, orcid = orcid))
  })
  output$dwc_result <- renderUI({
    res <- rv$res$dwc
    if (is.null(res)) return(help_text("The archive and its report appear here. Upload the archive (dwca.zip) to an IPT,",
                                       "which checks it again."))
    report <- res$outputs$report
    tagList(result_ui(res),
            if (res$ok && !is.null(report)) div(class = "dwc-report", markdown(paste(readLines(report, warn = FALSE), collapse = "\n"))))
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
                 tags$td(if (r$ok) tags$span(class = "badge text-bg-success", "finished") else tags$span(class = "badge text-bg-danger", "stopped")),
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
    rv$review_saved_d <- NULL; rv$changed <- NULL; rv$written <- NULL
    rv$model <- NULL; rv$model_used <- character(); rv$primers <- NULL; rv$demo <- ""; rv$eo_mapping <- NULL
    rv$pv <- data.frame(term = character(), value = character(), assay = character())
    rv$md_prov <- rv$md_prov[0, , drop = FALSE]
    rv$otu_n <- 1; rv$lib_n <- 1; rv$amp_n <- 0; rv$block_version <- rv$block_version + 1
  })
}

shinyApp(ui, server)
