# What each conversion needs

Ask for these before running `convert`, one question at a time, and never invent them. The options
are listed in full in `references/commands.md` (Converting).

- **gbif**: the licence (CC0-1.0, CC-BY-4.0 or CC-BY-NC-4.0), and the name, organisation and email
  of the dataset contact (`--licence`, `--given_name`, `--surname`, `--organisation`, `--email`,
  `--orcid`). Ask whether it is for GBIF, OBIS or both (`--publish_to`). For targeted assays,
  absence records are written unless they say otherwise (`--no_absences`). If kingdom or other
  ranks are empty, offer to make a small taxon table (name, scientificName, kingdom ...) with them
  and pass it with `--taxa`; OBIS needs WoRMS IDs in scientificNameID.
- **ncbi**: which metagenome the samples are (`--organism`, such as freshwater metagenome), and the
  BioProject accession if they have one.
- **ena**: the centre name of their ENA Webin account (`--center_name`), and the NCBI taxonomy ID
  of the metagenome (`--taxon_id`).
- **qiime**: the column that names the samples (`--sample_name_column`, default lib_id) and the
  folder of the fastq files (`--sequences_folder`), for the manifests.
