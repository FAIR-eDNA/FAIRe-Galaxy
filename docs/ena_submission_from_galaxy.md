# Submitting FAIRe data to ENA from Galaxy

5 November 2026. FAIRe2ENA writes ENA XML, and the user then submits it with curl outside Galaxy,
after a round trip for the sample receipt. The IUC's **ENA Upload** tool could do the submission
inside Galaxy, with one new converter from the FAIRe workbook. Galaxy Australia has since said
that its users can store ENA Webin credentials in Galaxy (November 2026).

## The ENA Upload tool

From the IUC repository (galaxyproject/tools-iuc, `tools/ena_upload`, commit `bffd84c`,
4 November 2026):

- **What it is:** `ena_upload`, version 0.11.0, a wrapper of ena-upload-cli (usegalaxy-eu;
  Roos et al. 2021, doi:10.1093/bioinformatics/btab421). MIT licence. It submits studies, samples,
  experiments and runs, and uploads the read files from the Galaxy history.
- **Credentials:** it declares Galaxy credentials (`<credentials name="ena_credentials">` with two
  secrets, the Webin username and password, given to the job as environment variables). The
  password never goes in a job parameter or the history, which meets our rule. Its help still
  mentions the older user-preferences route.
- **Galaxy version:** the wrapper declares tool profile 25.1, so it needs Galaxy 25.1 or later,
  with the server's vault set up for credentials.
- **Metadata in:** four tables (study, sample, experiment, run) in the ena-upload-cli template
  ([ELIXIR-Belgium/ENA-metadata-templates](https://github.com/ELIXIR-Belgium/ENA-metadata-templates)),
  as tab-separated files or one Excel workbook with the sheets ENA_study, ENA_sample,
  ENA_experiment and ENA_run; or ISA-JSON; or typed into the form.
- **Columns** (from its test workbook `metadata_test_nonviral.xlsx`): ENA_study: alias, title,
  study_type, study_abstract. ENA_sample: alias, title, scientific_name, sample_description, then
  the checklist's fields (collection date, geographic location (country and/or sea) ...).
  ENA_experiment: alias, title, study_alias, sample_alias, design_description, library_name,
  library_strategy, library_source, library_selection, library_layout, insert_size,
  library_construction_protocol, platform, instrument_model. ENA_run: alias, experiment_alias,
  file_name, file_format.
- **Options:** a sample checklist from ENA's list (ERC000024, GSC MIxS water, among them); add or
  modify; a dry run (`--draft`); and submission to ENA's test server.

## What it would take for FAIRe

1. **A converter**, "FAIRe2ENA: ENA upload tables": the FAIRe workbook to the four sheets above, in
   one Excel file. The mapping is the one FAIRe2ENA already uses for its SAMPLE, EXPERIMENT and
   RUN XML (sample fields, ERC000024, AMPLICON / METAGENOMIC / PCR, the file names and checksums),
   plus a study sheet from projectMetadata. The read files come from a collection in the history.
2. **Galaxy Australia:** Galaxy 25.1 or later in the eDNA Lab, credentials set up, `ena_upload`
   installed, and jobs allowed to reach ENA's Webin service and upload area.
3. **A trial** with `--draft`, then on the ENA test server with a Webin account.

What it would save: no curl, no XML handled by the user, the reads uploaded from the history, and
no separate sample receipt step, as ena-upload-cli submits samples and runs together.

Still to check before building: how ena-upload-cli names uploaded files, and whether its sample
sheet takes every ERC000024 field FAIRe2ENA writes.
