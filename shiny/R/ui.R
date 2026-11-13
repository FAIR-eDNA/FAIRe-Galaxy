# The pages of the app. Each tool's form follows its Galaxy wrapper, with the same choices.

SAMPLE_TYPES <- c("Water" = "Water", "Soil" = "Soil", "Sediment" = "Sediment", "Air" = "Air",
                  "Host-associated" = "HostAssociated", "Microbial mat or biofilm" = "MicrobialMatBiofilm",
                  "Symbiont-associated" = "SymbiontAssociated")
REQ_LEVELS <- c("Highly recommended" = "HR", "Recommended" = "R", "Optional" = "O")
ORGANISMS <- c("marine metagenome", "seawater metagenome", "freshwater metagenome", "aquatic metagenome",
               "estuary metagenome", "marine sediment metagenome", "freshwater sediment metagenome",
               "soil metagenome", "metagenome")
ENA_INSTRUMENTS <- c("Illumina MiSeq", "Illumina iSeq 100", "Illumina MiniSeq", "NextSeq 500", "NextSeq 550",
                     "NextSeq 1000", "NextSeq 2000", "Illumina NovaSeq 6000", "Illumina NovaSeq X",
                     "Illumina HiSeq 2500", "Illumina HiSeq 4000")
SRA_INSTRUMENTS <- c("Taken from the workbook" = "from_workbook", "Illumina MiSeq", "Illumina MiniSeq",
                     "Illumina iSeq 100", "NextSeq 500", "NextSeq 550", "NextSeq 1000", "NextSeq 2000",
                     "Illumina NovaSeq 6000", "Illumina NovaSeq X", "Illumina NovaSeq X Plus",
                     "Illumina HiSeq 2500", "Illumina HiSeq 4000", "MinION", "GridION", "PromethION",
                     "Sequel II", "Sequel IIe", "Revio", "Ion Torrent S5", "Element AVITI", "DNBSEQ-G400")

stat_tile <- function(value, label, kind = "") div(class = paste("stat", kind), div(class = "stat-value", value),
                                                  div(class = "stat-label", label))
help_text <- function(...) tags$p(class = "help-text", ...)
step_intro <- function(...) div(class = "step-intro", ...)
run_button <- function(id, label) actionButton(id, label, class = "btn-primary run-btn", icon = icon("play"))

# Short explanations of the words the app uses, shown when the pointer rests on (or keyboard focus
# reaches) the small question mark beside a label.
GLOSSARY <- c(
  sample_table = paste("Your table of sample details: one row per sample, with columns such as the sample name, date,",
                       "place, depth and volume. The mapper proposes a FAIRe term for each of its columns."),
  data_dictionary = paste("A file that says what each column of your sample table holds, such as 'Days frozen: number",
                          "of days the water was frozen before filtering'. It can be a table (column name, description,",
                          "units) or a ReadMe with one line per column. It helps the mapper with unclear column names.",
                          "Leave it as None if you don't have one."),
  header_row = "The row of your table that holds the column names. Use it when a title or notes sit above them.",
  assay_type = paste("Metabarcoding: sequencing a marker gene (12S, 16S, 18S, COI ...) to see which taxa are present.",
                     "Targeted: a qPCR or ddPCR test for one species."),
  sample_types = "What was sampled (water, sediment, soil ...). It decides which FAIRe terms apply.",
  other_terms = paste("MIxS (Genomic Standards Consortium) and Darwin Core (TDWG) are the standards FAIRe builds on.",
                      "When FAIRe has no term for a column, the FAIRe guidelines ask for one of theirs before a name of",
                      "your own."),
  input_term = "One column heading of your sample table.",
  mappers_call = paste("Accept: the mapper is sure of the match. Review: a person should decide. No match: no FAIRe term",
                       "fits, so the column is kept under its own name (a user-defined field) unless you choose one."),
  decision = paste("Accept uses the proposed term. Reject keeps the column as your own term. Change uses the",
                   "replacement you pick."),
  methods = paste("The methods section of your paper, report or protocol, as text or a PDF. Find primers looks in it",
                  "for primer names, citations and sequences. A PDF of scanned pages has no text to read."),
  primer_table = paste("The published primers that the names, citations and sequences in your methods are checked against,",
                       "so that primer names are written as in the literature and typos in sequences are caught. The one",
                       "that comes with the tools holds about 550 pairs: most from Takahashi et al. (2023, Science of the",
                       "Total Environment), plus Wilderlab's assays, the 18S V4 pairs and broad bacteria and archaea 16S",
                       "pairs. Your own table needs primer names and sequences."),
  own_primer_table = paste("Your own table of primers, for primers not in the reference table: a TSV made by FAIRe mapper:",
                           "build primer table in Galaxy, or one with the same columns (pcr_primer_name_forward,",
                           "pcr_primer_forward, pcr_primer_name_reverse, pcr_primer_reverse and so on)."),
  primer_assay = paste("The name of the assay this primer pair was used for, such as Fish16S or Euk18S: the same name",
                       "you give its OTU table in e. Write the workbook. Leave it empty if the project has one assay."),
  project_values = paste("FAIRe terms with one value for the whole project, or for each assay: the primers, target gene,",
                         "extraction kit, sequencing platform, reference database and so on. They go in projectMetadata."),
  assay = paste("A name for one PCR assay, such as Fish16S or Euk18S. It links the project values, OTU tables and",
                "libraries of that assay."),
  otu_table = paste("Read counts: one row per sequence (OTU or ASV) or taxon, one column per sample, or the other way",
                    "round. Taxonomy can be in the same table."),
  taxonomy_table = "A table of each sequence's taxonomy (kingdom to species, or a lineage), when it is separate from the read counts.",
  sequences = paste("A FASTA file of the sequences: a header line starting with > before each sequence. Needed when",
                    "the OTU table names its sequences (ASV_1 ...) but does not hold them, as LCA outputs do."),
  stage = paste("Final: the reads you report, after your curation. Raw: the reads as they came from the pipeline,",
                "before curation. FAIRe keeps each in its own pair of sheets."),
  run_id = "A name for the sequencing run these reads came from, such as AGRF_2024-12.",
  library_table = paste("A table of sequencing libraries: library names, sequence file names and checksums, such as ENA's",
                        "or NCBI's run report, or your sequencing facility's run sheet."),
  crosswalk = paste("The record of which column of your table goes to which FAIRe term. The review sheet is the version",
                    "to fill in; the SSSOM table is the same record in a standard format for term mappings."),
  review_sheet = paste("An Excel workbook with one row per column of your sample table, with the proposed term and the",
                       "mapper's call. You choose Accept, Reject or Change for each row."),
  utc_offset = paste("How far local time is ahead of (+) or behind (-) UTC where the samples were taken, such as +10:00",
                     "for Australian Eastern Standard Time. Used to give times of collection in local time."),
  curated_column = "A column of the OTU table that holds your curated names, if they differ from the lineage's.",
  lineage = "The column of the lineage to use when the table has more than one (from SILVA and PR2, say).",
  layout = "How the read counts are laid out: samples as columns, samples as rows, or one row per sample and sequence.",
  file_kind = paste("What the file seems to be, from its layout, column names and values. If it is wrong, choose the",
                    "right kind: the app then offers the file in the right places.")
)

# Each kind of file identify reports, and where it goes in this app.
KIND_PLACE <- c(
  "sample table" = "b. Propose a mapping: Sample table",
  "OTU or ASV table" = "e. Write the workbook: OTU or ASV table",
  "taxonomy table" = "e. Write the workbook: Taxonomy table (under More for this table)",
  "library table" = "e. Write the workbook: Library table",
  "crosswalk" = "c. Review: Add a review sheet you filled in, or Use a crosswalk you edited yourself",
  "data dictionary" = "b. Propose a mapping: Data dictionary",
  "project values" = "d. Values for the whole project: Or load a table of values",
  "primer table" = "d. Find primers: My own primer table",
  "sequences (FASTA)" = "e. Write the workbook: Sequences of this table (under More for this table)",
  "text" = "d. Find primers: Your methods (text or PDF)",
  "not recognised" = "Check the file: its column names may be below a title (set the header row) or on another sheet.")

# A label with a question mark beside it that explains the term on hover or focus.
term_label <- function(label, key) {
  tags$span(label, " ", bslib::tooltip(
    tags$span(class = "term-help", tabindex = "0", `aria-label` = paste("What is", label), icon("circle-question")),
    GLOSSARY[[key]], placement = "right"))
}

workbook_picker <- function(id) uiOutput(paste0(id, "_ui"))

start_page <- function() {
  nav_panel(
    "Start", icon = icon("house"),
    layout_columns(
      col_widths = c(7, 5),
      card(
        card_header("The FAIRe tools"),
        tags$p("This app brings together the tools for making environmental DNA (eDNA) data FAIR: Findable,",
               "Accessible, Interoperable and Reusable. It runs the same scripts as the FAIRe tools in the",
               "Galaxy Australia eDNA Lab, on your own computer, so you can try them on your data before",
               "you submit anything."),
        tags$p("Each tool does one step of the job. You make a metadata workbook in the FAIRe format, check",
               "it, and then convert it for the place where your data are going: a sequence archive (NCBI",
               "or ENA), a biodiversity database (GBIF or OBIS), or an analysis in QIIME 2."),
        tags$h5("Where to start"),
        tags$ul(
          tags$li(HTML("<b>If you have no metadata yet</b>, or are planning a study, start with <b>FAIRe-ator</b> under",
                       "<em>1. Make a workbook</em>. It makes a blank template for you to fill in.")),
          tags$li(HTML("<b>If you have a sample table in your own format</b>, start with the <b>FAIRe mapper</b> under",
                       "<em>1. Make a workbook</em>. It builds the workbook from your table, your OTU and taxonomy",
                       "tables and your methods text.")),
          tags$li(HTML("<b>If you already have a FAIRe workbook</b>, add it to your files and go to <em>2. Check</em>."))),
        tags$h5("The steps"),
        div(class = "flow",
            div(class = "flow-step", tags$b("1. Make a workbook"), tags$span("FAIRe-ator or the FAIRe mapper")),
            div(class = "flow-arrow", icon("arrow-right")),
            div(class = "flow-step", tags$b("2. Check"), tags$span("FAIRe-fier")),
            div(class = "flow-arrow", icon("arrow-right")),
            div(class = "flow-step", tags$b("3. Convert"),
                tags$span("NCBI, ENA, GBIF, OBIS, QIIME 2"))),
        help_text("The files you add stay on this computer. Each tool run gets its own folder, listed under",
                  tags$em("Outputs"), ", and everything is deleted when you close the app.")
      ),
      card(
        card_header("Try it with the demonstration data"),
        tags$p("The demonstration set is a small cut of CSIRO's SEA-MES eDNA data record (Deagle et al.",
               "2025): 13 water samples from the RV Investigator, a 16S fish ASV table, the authors' curated",
               "fish taxa, ENA's run report and the methods text. It is for trying the tools, not for",
               "ecological analysis."),
        actionButton("load_demo", "Load the demonstration data", icon = icon("flask"), class = "btn-success"),
        help_text("Loading the demonstration fills in the forms with the values the trial used. You still",
                  "press each tool's button yourself, in order, and you do the review of the mapping."),
        uiOutput("demo_status"),
        tags$hr(),
        tags$h6("Set-up check"),
        uiOutput("setup_table"),
        help_text("If something is missing, close the app, run setup.R and start it again.")
      )
    )
  )
}

faireator_panel <- function() {
  nav_panel(
    "FAIRe-ator: a blank template",
    layout_columns(
      col_widths = c(5, 7),
      card(
        card_header("Make a blank FAIRe template"),
        step_intro("FAIRe-ator makes an Excel template for your study, with the fields that suit your assay",
                   "type and sample types. You fill it in outside the app, then add it to your files and check",
                   "it with FAIRe-fier."),
        textInput("fa_project_id", "Project ID", placeholder = "for example SEA-MES_eDNA"),
        help_text("A short identifier with no spaces. It is used in file names."),
        radioButtons("fa_assay_type", "Assay type",
                     c("Metabarcoding" = "metabarcoding", "Targeted (qPCR or ddPCR detection of particular taxa)" = "targeted")),
        textInput("fa_assay_name", "Assay name(s)", placeholder = "for example MiFish, 16SFish"),
        help_text("Short names with no spaces, separated by commas. Each assay gets its own column in projectMetadata."),
        checkboxGroupInput("fa_sample_type", "Sample type(s)", c(SAMPLE_TYPES, "All sample types" = "other"),
                           selected = "Water", inline = TRUE),
        checkboxGroupInput("fa_req_lev", "Fields to include as well as the mandatory ones", REQ_LEVELS,
                           selected = REQ_LEVELS, inline = TRUE),
        textInput("fa_project_fields", "Extra projectMetadata fields (optional)", placeholder = "for example funder"),
        textInput("fa_sample_fields", "Extra sampleMetadata fields (optional)", placeholder = "for example plot_id, burn_age"),
        run_button("run_faireator", "Make the template")
      ),
      card(card_header("Result"), uiOutput("faireator_result"))
    )
  )
}

mapper_panel <- function() {
  nav_panel(
    "FAIRe mapper: from your own tables",
    navset_pill_list(
      id = "mapper_steps", widths = c(2, 10), well = FALSE,
      nav_panel(
        "a. Your files",
        card(
          card_header("Say what each file is"),
          step_intro("Add every file you have for the dataset to ", tags$em("Your files"), " (on the left):",
                     " the sample table, OTU or ASV tables, taxonomy tables, sequences (FASTA), run reports, and",
                     " your methods or ReadMe (text or PDF). This step looks at each one and says what it seems to",
                     " be and which step it goes to. If it gets one wrong, choose the right kind in the table."),
          help_text("A sample table is the spreadsheet you keep for your samples, with one row per sample or filter",
                    "and columns such as site, date, coordinates, depth, volume filtered and which samples are",
                    "controls. Reads per ASV or taxon, and taxon assignments, go in separately as OTU and",
                    "taxonomy tables, even if you keep them in the same spreadsheet."),
          run_button("run_identify", "Identify my files"),
          uiOutput("identify_result")
        )
      ),
      nav_panel(
        "b. Propose a mapping",
        layout_columns(
          col_widths = c(4, 8),
          card(
            card_header("Your sample table"),
            uiOutput("map_table_ui"),
            uiOutput("map_sheet_ui"),
            numericInput("map_header_row", term_label("Row holding the column headers", "header_row"), 1, min = 1, max = 50),
            help_text("Change this when the sheet has a title or notes above the headers. Comment lines",
                      "starting with # (as in NCBI and ENA submission sheets) are skipped without it."),
            radioButtons("map_assay_type", term_label("Assay type", "assay_type"), c("Metabarcoding" = "metabarcoding",
                                                           "Targeted" = "targeted", "Either" = "any"), inline = TRUE),
            checkboxGroupInput("map_sample_types", term_label("Sample types", "sample_types"), SAMPLE_TYPES, selected = "Water", inline = TRUE),
            uiOutput("map_dictionary_ui"),
            checkboxInput("map_other_terms", term_label("Suggest MIxS or Darwin Core terms for columns with no FAIRe term", "other_terms"), TRUE),
            help_text("The FAIRe guidelines ask for a MIxS or Darwin Core term, where one exists, before a name of",
                      "your own. These suggestions are always for review."),
            run_button("run_map", "Propose a mapping")
          ),
          card(card_header("Proposed mapping"), uiOutput("map_result"))
        )
      ),
      nav_panel(
        "c. Review the mapping",
        card(
          card_header("Review the mapping"),
          step_intro("This is the review sheet propose mapping writes, row for row. Each row is one column heading",
                     "(an input term) of your sample table, with the term the mapper proposes, its score (0 to 1),",
                     "the mapper's call and why. The mapper's accepted matches have Accept already. For each row,",
                     "choose Accept to use the proposed term, Reject to keep the column as your own term, or Change",
                     "and pick a replacement: the best candidates for the column come first. A MIxS or Darwin Core",
                     "term is used by accepting it, or by choosing it as the replacement. Rows for review are",
                     "shaded; a row for review with no decision is kept as your own term."),
          uiOutput("review_toolbar"),
          uiOutput("review_saved"),
          uiOutput("review_table")
        ),
        accordion(
          open = FALSE,
          accordion_panel(
            "Ask a language model about the columns for review (optional)", icon = icon("robot"),
            help_text("A model can suggest a term for each column for review. It only chooses from the candidates",
                      "the mapper offers, and its answers are only suggestions: you still choose and save. Every",
                      "step of the mapper works without one."),
            help_text("The column headers, a few example values from each column for review and the candidate terms",
                      "are sent to the service you choose. Use ", tags$em("Preview"), " to see exactly what would be sent."),
            layout_columns(
              col_widths = c(3, 3, 6),
              selectInput("model_api", "Service", c("Anthropic (Claude)" = "anthropic",
                                                    "OpenAI-compatible service" = "openai")),
              textInput("model_name", "Model (optional)", placeholder = "the tool's default"),
              textInput("model_url", "Address of the service (optional)", placeholder = "the provider's public address")),
            passwordInput("model_key", "API key", placeholder = "kept in memory for this run only"),
            help_text("The key goes to the tool through its environment, as in Galaxy, and is never written to a file.",
                      "If you started the app with ANTHROPIC_API_KEY or OPENAI_API_KEY set, leave this empty."),
            div(class = "btn-row",
                actionButton("run_model_preview", "Preview what would be sent", icon = icon("eye")),
                actionButton("run_model", "Ask the model", icon = icon("paper-plane"), class = "btn-primary")),
            uiOutput("model_result")
          ),
          accordion_panel(
            "Use a crosswalk you edited yourself (SSSOM)", icon = icon("file-pen"),
            help_text("If you work with the crosswalk (an SSSOM table) instead of the review sheet, you can edit it in",
                      "a spreadsheet and add it to your files. Set predicate_id to skos:exactMatch to confirm a row,",
                      "change object_label and object_id (FAIRe:term) to change its term, and delete a row to leave a",
                      "column unmatched."),
            uiOutput("own_crosswalk_ui"),
            actionButton("use_own_crosswalk", "Use this crosswalk", icon = icon("check"))
          )
        )
      ),
      nav_panel(
        "d. Primers and project values",
        layout_columns(
          col_widths = c(5, 7),
          card(
            card_header("Your methods and the primers"),
            step_intro("Your methods (text or PDF) are where the values for the whole project come from. The app",
                       "reads them for primers: it looks for primer names, citations and sequences, and checks them",
                       "against a reference table of published primers. The other values, such as PCR conditions,",
                       "extraction kit, sequencing platform, reference databases and protocols, come from you: open",
                       "your methods beside the table on the right and add them there."),
            radioButtons("pr_mode", "Look for primers in", c("My methods" = "text", "Names or citations I type" = "names"),
                         inline = TRUE),
            conditionalPanel("input.pr_mode == 'text'", uiOutput("pr_texts_ui")),
            uiOutput("pr_texts_open"),
            conditionalPanel("input.pr_mode == 'names'",
                             textAreaInput("pr_names", "Names or citations, one per line", rows = 4,
                                           placeholder = "MiFish-U\nLeray et al. 2013"),
                             textInput("pr_gene", "Only primers for this gene (optional)", placeholder = "for example 12S")),
            radioButtons("pr_source", term_label("Reference table of primers to check against", "primer_table"),
                         c("The reference table that comes with the tools" = "bundled",
                           "The reference table and my own" = "both",
                           "My own table only" = "own")),
            help_text("Checking against a reference table keeps primer names the same as in the literature and",
                      "catches typos in sequences. The one that comes with the tools holds about 550 published primer",
                      "pairs, most from Takahashi et al. (2023) and Wilderlab's assays. Add your own table if your",
                      "primers are not in it."),
            conditionalPanel("input.pr_source != 'bundled'", uiOutput("pr_own_ui")),
            run_button("run_primers", "Find primers"),
            uiOutput("primers_result")
          ),
          card(
            card_header(term_label("Values for the whole project", "project_values")),
            step_intro("Some FAIRe fields hold one value for the whole project or for each assay: the primers, the",
                       "extraction kit, the sequencing platform, the reference database and so on. Most come from",
                       "your methods. List them here and they are written to projectMetadata. Leave the assay empty",
                       "for a value that applies to every assay."),
            uiOutput("pv_missing"),
            DTOutput("pv_table"),
            div(class = "btn-row",
                actionButton("pv_delete", "Delete the selected rows", icon = icon("trash")),
                downloadButton("pv_download", "Download as a table")),
            tags$h6("Add a value"),
            radioButtons("pv_section", "Offer the FAIRe terms for",
                         c("PCR and primers" = "PCR", "Library preparation and sequencing" = "Library preparation sequencing",
                           "Bioinformatics" = "Bioinformatics", "The project" = "Project", "Data management" = "Data management",
                           "Targeted assays (qPCR, ddPCR)" = "Targeted assay detection", "All" = "all"),
                         inline = TRUE),
            layout_columns(
              col_widths = c(4, 5, 3),
              selectizeInput("pv_term", "FAIRe term", choices = NULL, options = list(placeholder = "type to search")),
              textInput("pv_value", "Value"),
              textInput("pv_assay", "Assay (optional)")),
            actionButton("pv_add", "Add", icon = icon("plus")),
            tags$h6("Or load a table of values"),
            help_text("A table with the columns term, value and (optionally) assay, from your files."),
            uiOutput("pv_file_ui"),
            actionButton("pv_load", "Load these values", icon = icon("file-import"))
          )
        )
      ),
      nav_panel(
        "e. Write the workbook",
        layout_columns(
          col_widths = c(5, 7),
          div(
            card(
              card_header("Project"),
              uiOutput("apply_inputs_summary"),
              textInput("ap_project_id", "Project ID", placeholder = "for example SEA-MES_eDNA"),
              textInput("ap_assay_name", "Assay name(s)", placeholder = "for example Fish16S"),
              help_text("Separated by commas. Leave empty when an OTU table names its assays in a column."),
              textInput("ap_country", "Country or sea for geo_loc_name (optional)", placeholder = "for example Australia"),
              textInput("ap_utc_offset", term_label("UTC offset of the times of collection (optional)", "utc_offset"), placeholder = "for example +10:00"),
              help_text("When the table gives the time of collection in its own column, the time is joined to its",
                        "date in eventDate, in local time. Give the offset of local time from UTC, such as +10:00",
                        "for Australian Eastern Standard Time; times the column name says are UTC are converted to",
                        "local time with it."),
              selectInput("ap_date_order", "Dates such as 06/09/2017",
                          c("Stop and ask me" = "stop", "Day first (as in Australia)" = "dmy", "Month first" = "mdy")),
              checkboxGroupInput("ap_req_lev", "Fields to include as well as the mandatory ones", REQ_LEVELS,
                                 selected = REQ_LEVELS, inline = TRUE),
              checkboxInput("ap_include_review", "Also write the matches still for review (rows with no decision)", FALSE),
              checkboxInput("ap_drop_unmapped", "Leave out columns not matched to a FAIRe term", FALSE)
            ),
            card(
              card_header("OTU or ASV tables"),
              help_text("One block for each table. A taxonomy table is only needed when the taxonomy is not in the",
                        "OTU table itself. Write a table as final (otuFinal and taxaFinal) if these are the reads you",
                        "report, after filtering and curation, or as raw for the reads before."),
              uiOutput("otu_blocks"),
              div(class = "btn-row",
                  actionButton("otu_add", "Add an OTU table", icon = icon("plus"), class = "btn-sm"),
                  actionButton("otu_remove", "Remove the last", icon = icon("minus"), class = "btn-sm"))
            ),
            card(
              card_header("Library tables"),
              help_text("A library table or run report gives each library's name, read files and checksums (for",
                        "example ENA's run report). Each row should be one amplicon of one sample."),
              uiOutput("lib_blocks"),
              div(class = "btn-row",
                  actionButton("lib_add", "Add a library table", icon = icon("plus"), class = "btn-sm"),
                  actionButton("lib_remove", "Remove the last", icon = icon("minus"), class = "btn-sm"))
            ),
            run_button("run_apply", "Write the FAIRe workbook")
          ),
          card(card_header("The workbook"), uiOutput("apply_result"), wb_preview_ui("apply_preview"))
        )
      )
    )
  )
}

check_page <- function() {
  nav_panel(
    "2. Check", icon = icon("clipboard-check"),
    layout_columns(
      col_widths = c(4, 8),
      card(
        card_header("Check the workbook with FAIRe-fier"),
        step_intro("FAIRe-fier lists missing mandatory fields and values in the wrong format, and suggests",
                   "corrections. If it finds problems it returns a workbook with a list of the errors and",
                   "warnings and a copy of each problem sheet, with those cells highlighted: red for errors and",
                   "yellow for warnings. Correct the workbook, add it to your files and check it again until it passes."),
        workbook_picker("ck_wb"),
        selectInput("ck_version", "FAIRe checklist version", c("Read it from the workbook" = "auto", "v1.0.2", "v1.0")),
        run_button("run_fairefier", "Check the workbook")
      ),
      card(card_header("Result"), uiOutput("fairefier_result"))
    )
  )
}

convert_page <- function() {
  nav_panel(
    "3. Convert", icon = icon("right-left"),
    card(
      class = "convert-top",
      layout_columns(
        col_widths = c(5, 7),
        workbook_picker("cv_wb"),
        help_text("Each tool writes the files for one destination, and you then upload them yourself. NCBI and",
                  "ENA take the sample and run tables, GBIF takes data through its Metabarcoding Data Toolkit",
                  "(MDT) or an IPT, OBIS through an IPT, and QIIME 2 takes the metadata and manifests."))
    ),
    navset_card_tab(
      nav_panel(
        "NCBI",
        layout_columns(
          col_widths = c(6, 6),
          div(
            tags$h5("FAIRe2NCBI: BioSample"),
            help_text("Writes the BioSample table for the NCBI Submission Portal. You need an NCBI account to upload it."),
            selectInput("nb_organism", "Organism for samples with none in the workbook", c(ORGANISMS, "Other" = "other")),
            conditionalPanel("input.nb_organism == 'other'", textInput("nb_organism_other", "Organism name")),
            textInput("nb_bioproject", "BioProject accession (optional)", placeholder = "PRJNA..."),
            selectInput("nb_mandatory_fill", "Empty mandatory fields",
                        c("Stop and list them" = "stop", "Fill with 'not collected'" = "not collected",
                          "Fill with 'not provided'" = "not provided", "Fill with 'not applicable'" = "not applicable",
                          "Fill with 'missing'" = "missing", "Fill with 'missing: control sample'" = "missing: control sample")),
            selectInput("nb_associated", "Samples to include",
                        c("All samples" = "all", "Only samples not yet submitted" = "blank_only")),
            textInput("nb_duplicates", "Field that tells apart samples with identical attributes (optional)"),
            help_text("NCBI refuses samples whose attributes are all the same. Name a field, such as a replicate",
                      "label, that differs between them."),
            accordion(open = FALSE, accordion_panel(
              "More options",
              checkboxInput("nb_convert_dates", "Convert eventDate values for NCBI", TRUE),
              checkboxInput("nb_mixs_units", "Add MIxS preferred units", TRUE),
              selectInput("nb_title", "sample_title", c("geo_loc_name, organism and sample_name" = "default",
                                                        "Join other BioSample columns" = "custom", "Leave empty" = "none")),
              conditionalPanel("input.nb_title == 'custom'", textInput("nb_title_columns", "BioSample columns to join")),
              selectInput("nb_extra", "Other sampleMetadata fields", c("Add all" = "all", "Add all except some" = "except",
                                                                       "Add none" = "none")),
              conditionalPanel("input.nb_extra == 'except'", textInput("nb_exclude", "Fields to leave out")))),
            run_button("run_ncbi_biosample", "Write the BioSample table"),
            uiOutput("ncbi_biosample_result")
          ),
          div(
            tags$h5("FAIRe2NCBI: SRA"),
            help_text("Writes the SRA table. It needs experimentRunMetadata filled in, with samp_name, assay_name,",
                      "lib_id and the fastq file names. In the Submission Portal, upload the fastq files after the table."),
            selectInput("ns_runs_by", "Runs to include", c("All" = "all", "By assay" = "assay",
                                                           "By sequencing run" = "seq_run", "By library" = "lib_id")),
            conditionalPanel("input.ns_runs_by != 'all'", textInput("ns_runs_values", "Values, separated by commas")),
            selectInput("ns_associated", "Runs already submitted", c("Include them" = "all", "Only runs not yet submitted" = "blank_only")),
            selectInput("ns_instrument", "Sequencing instrument", SRA_INSTRUMENTS),
            radioButtons("ns_link", "Link runs to their BioSamples by",
                         c("Sample name (submitted together)" = "sample_name", "BioSample accessions" = "accessions"), inline = TRUE),
            conditionalPanel("input.ns_link == 'accessions'", uiOutput("ns_accessions_ui")),
            run_button("run_ncbi_sra", "Write the SRA table"),
            uiOutput("ncbi_sra_result")
          )
        )
      ),
      nav_panel(
        "ENA",
        layout_columns(
          col_widths = c(6, 6),
          div(
            tags$h5("FAIRe2ENA: samples"),
            help_text("Writes the sample XML for ENA. You submit it to ENA's Webin service yourself, and ENA returns",
                      "a receipt with the sample accessions."),
            textInput("es_center", "Centre name, as registered with your Webin account", placeholder = "for example CSIRO"),
            selectInput("es_taxon", "Sample taxon", c("marine metagenome (408172)" = "408172",
                                                      "freshwater metagenome (449393)" = "449393",
                                                      "aquatic metagenome (1169740)" = "1169740", "Other" = "other")),
            conditionalPanel("input.es_taxon == 'other'", textInput("es_taxon_id", "NCBI taxon ID")),
            checkboxInput("es_convert_dates", "Convert eventDate values to a form ENA accepts", TRUE),
            run_button("run_ena_sample", "Write the sample XML"),
            uiOutput("ena_sample_result")
          ),
          div(
            tags$h5("FAIRe2ENA: experiments and runs"),
            help_text("Writes the experiment and run XML. It needs the receipt from the samples step, the study",
                      "accession and the MD5 checksum of each fastq file. Upload the fastq files to your Webin",
                      "upload area first."),
            uiOutput("er_receipt_ui"),
            textInput("er_study", "ENA study accession", placeholder = "PRJEB..."),
            textInput("er_center", "Centre name"),
            selectInput("er_instrument", "Sequencing instrument", ENA_INSTRUMENTS, selected = "Illumina MiSeq"),
            radioButtons("er_assay", "Assays to include", c("All" = "all", "One" = "one"), inline = TRUE),
            conditionalPanel("input.er_assay == 'one'",
                             textInput("er_assay_name", "assay_name"),
                             checkboxInput("er_assay_suffix", "Add the assay name to experiment and run aliases", TRUE)),
            textInput("er_seq_runs", "Sequencing runs to include (optional)"),
            textInput("er_ftp", "FTP sub-folder of the read files (optional)"),
            run_button("run_ena_run", "Write the experiment and run XML"),
            uiOutput("ena_run_result")
          )
        )
      ),
      nav_panel(
        "GBIF (MDT)",
        layout_columns(
          col_widths = c(5, 7),
          div(
            tags$h5("FAIRe2MDT"),
            help_text("Writes a workbook for GBIF's Metabarcoding Data Toolkit (MDT), which turns it into Darwin",
                      "Core for GBIF. Run it once for each assay and sequencing run."),
            uiOutput("mdt_assay_ui"),
            uiOutput("mdt_tables_ui"),
            selectInput("mdt_controls", "Control samples", c("Leave them out, as GBIF asks" = "omit", "Keep them" = "keep")),
            run_button("run_mdt", "Write the MDT workbook")
          ),
          div(uiOutput("mdt_result"))
        )
      ),
      nav_panel(
        "OBIS and GBIF (Darwin Core)",
        layout_columns(
          col_widths = c(5, 7),
          div(
            tags$h5("edna2obis"),
            help_text("Writes a Darwin Core archive for an IPT (Integrated Publishing Toolkit), which suits OBIS and",
                      "GBIF. First it matches the names in your taxonomy tables to WoRMS or GBIF, which needs",
                      "internet access. You can check the matches, then build the archive."),
            uiOutput("eo_tables_ui"),
            selectInput("eo_api", "Look up names in", c("WoRMS (World Register of Marine Species), for OBIS" = "WoRMS",
                                                        "GBIF Backbone Taxonomy, for GBIF" = "GBIF")),
            checkboxInput("eo_worms_all", "Include non-marine taxa (WoRMS)", FALSE),
            run_button("run_eo_match", "1. Match taxa"),
            tags$hr(),
            radioButtons("eo_taxa_source", "Taxonomy for the Darwin Core tables",
                         c("The mapping table from step 1" = "mapping", "Look the names up again" = "api"), inline = TRUE),
            conditionalPanel("input.eo_taxa_source == 'mapping'", uiOutput("eo_mapping_ui")),
            selectInput("eo_core", "Archive layout", c("Occurrence core" = "occurrence", "Event core" = "event")),
            selectInput("eo_emof", "Extended Measurement Or Fact (eMoF) extension",
                        c("The standard eMoF fields" = "default", "Leave the eMoF out" = "none")),
            help_text("The eMoF joins runs by lib_id, so leave it out if a lib_id is used by more than one run."),
            selectInput("eo_text_dates", "Text dates such as 7/6/19", c("Stop and ask me" = "stop", "Day first" = "dmy",
                                                                        "Month first" = "mdy")),
            textInput("eo_location", "sampleMetadata fields that make up locationID", "line_id, station_id"),
            checkboxInput("eo_eml", "Write the dataset metadata (eml.xml) now", FALSE),
            conditionalPanel("input.eo_eml",
                             textInput("eo_title", "Dataset title (optional: project_name is used otherwise)"),
                             textAreaInput("eo_abstract", "Abstract", rows = 3),
                             layout_columns(textInput("eo_given", "Given name"), textInput("eo_surname", "Surname")),
                             layout_columns(textInput("eo_org", "Organisation"), textInput("eo_email", "Email")),
                             selectInput("eo_licence", "Licence", c("CC0", "CC-BY", "CC-BY-NC"), selected = "CC-BY")),
            run_button("run_eo_build", "2. Build the Darwin Core archive")
          ),
          div(uiOutput("eo_match_result"), uiOutput("eo_build_result"))
        )
      ),
      nav_panel(
        "QIIME 2",
        layout_columns(
          col_widths = c(5, 7),
          div(
            tags$h5("FAIRe2QIIME"),
            help_text("Writes QIIME 2 sample metadata and, if you want them, manifest files for importing the reads.",
                      "It needs target_gene for each assay in projectMetadata."),
            selectInput("qi_sample_col", "Column to use as the QIIME 2 sample ID", c("lib_id", "samp_name")),
            radioButtons("qi_manifests", "Write manifest files?", c("Yes" = "yes", "No, metadata only" = "no"), inline = TRUE),
            conditionalPanel("input.qi_manifests == 'yes'",
                             textInput("qi_folder", "Folder that holds the sequencing run folders", "/path/to/sequences"),
                             help_text("On the computer where QIIME 2 runs. The manifests give each fastq file's full path.")),
            radioButtons("qi_suffix", "Make repeated sample IDs unique?", c("No" = "no", "Yes" = "yes"), inline = TRUE),
            conditionalPanel("input.qi_suffix == 'yes'",
                             textInput("qi_suffix_col", "Column to take the suffix from", "seq_run_id"),
                             selectInput("qi_suffix_dir", "Take characters from the", c("start (left)" = "left", "end (right)" = "right")),
                             numericInput("qi_suffix_n", "Number of characters", 20, min = 1),
                             textInput("qi_suffix_delim", "Text to put before the suffix", "_")),
            run_button("run_qiime", "Write the QIIME 2 files")
          ),
          div(uiOutput("qiime_result"))
        )
      )
    )
  )
}

outputs_page <- function() {
  nav_panel(
    "Outputs", icon = icon("folder-open"),
    card(
      card_header("Everything the tools wrote in this session"),
      help_text("Each run has its own folder with its inputs, outputs and a log of the exact command, so any file",
                "can be traced to the run that wrote it. The folder is deleted when you close the app, so download",
                "what you want to keep."),
      div(class = "btn-row",
          downloadButton("download_all", "Download everything (zip)"),
          actionButton("clear_session", "Start again", icon = icon("rotate-left"), class = "btn-outline-danger")),
      uiOutput("runs_list")
    )
  )
}

# A small module that shows a sheet of a workbook.
wb_preview_ui <- function(id) {
  ns <- NS(id)
  div(class = "wb-preview", uiOutput(ns("sheet_ui")), DTOutput(ns("table")))
}

wb_preview_server <- function(id, path, faire = TRUE) {
  moduleServer(id, function(input, output, session) {
    output$sheet_ui <- renderUI({
      p <- path()
      req(p, file.exists(p))
      sh <- xlsx_sheets(p)
      sh <- sh[!sh %in% c("Drop-down values", "README")]
      selectInput(session$ns("sheet"), "Look at a sheet", sh, selected = intersect(c("sampleMetadata", "Samples", sh), sh)[1])
    })
    output$table <- renderDT({
      p <- path(); req(p, input$sheet, input$sheet %in% xlsx_sheets(p))
      d <- if (faire) read_faire_sheet(p, input$sheet)
           else tryCatch(as.data.frame(readxl::read_excel(p, input$sheet, col_types = "text")), error = function(e) NULL)
      req(d)
      datatable(d, rownames = FALSE, options = list(scrollX = TRUE, pageLength = 10, dom = "tip"), class = "compact")
    })
  })
}
