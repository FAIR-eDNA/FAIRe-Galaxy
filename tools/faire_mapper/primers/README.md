# Bundled primer table

`faire_primers.tsv` is the primer table used by **FAIRe mapper: find primers**,
**FAIRe mapper: build primer table** and `faire_mapper_methods.py`. One row per primer pair, with a
stable `primer_pair_id` made from the two sequences, and the `source` of every row.

The columns use FAIRe term names wherever FAIRe has a term (`assay_name`, `assay_type`,
`targetTaxonomicAssay`, `targetTaxonomicScope`, `target_gene`, `target_subfragment`, the six
`pcr_primer_*` terms, `ampliconSize`, `bibliographicCitation`), and `target_gene` uses the FAIRe
vocabulary, so values can be copied into a FAIRe workbook. The other columns describe the table:
`other_names` (aliases), `record_ids` (identifiers in the source registers), `notes` and `source`.

## Sources

| Source | Rows | Licence and permission |
|---|---|---|
| Takahashi M, Saccò M, Kestel JH, et al. 2023. Aquatic environmental DNA: a review of the macro-organismal biomonitoring revolution. *Science of the Total Environment* 873:162322. [doi:10.1016/j.scitotenv.2023.162322](https://doi.org/10.1016/j.scitotenv.2023.162322). Table S3 (species-specific primers) and Table S4 (metabarcoding primers) | 511 pairs (S3: 376, S4: 135, after merging rows with the same sequences) | CC BY-NC 4.0. Inclusion with the tool confirmed by Oliver Berry (CSIRO), 3 November 2026. |
| Metazoan primer register in FAIRe terms, compiled for this project from Tables S3 and S4 (3 November 2026, updated version): metazoan records and broad eukaryote assays, with the target taxon, normalised gene names, the citing study's DOI and a record identifier (for example TAK23-Q-0003) | 481 of the pairs above | As for Takahashi et al. 2023 |
| Curated supplement in the same register (records SUP-M-0001 to 0013): VertU universal vertebrate 12S, 16S and COI (Wang et al. 2023, [10.3389/fevo.2023.1164206](https://doi.org/10.3389/fevo.2023.1164206)); LoboF1/LoboR1 (Lobo et al. 2013, [10.1186/1472-6785-13-34](https://doi.org/10.1186/1472-6785-13-34)); fwh1 and fwh2 (Vamos et al. 2017, [10.3897/mbmg.1.14625](https://doi.org/10.3897/mbmg.1.14625)); two Wilderlab assays, CI and WV (Wilkinson et al. 2024, [10.7717/peerj.16963](https://doi.org/10.7717/peerj.16963)); three more pairs named as Wilderlab's (ZP and ZC, DG, YG) were removed on 7 November 2026, as their source could not be confirmed; two coral 28S assays (McCartin et al. 2024, [10.7717/peerj.18607](https://doi.org/10.7717/peerj.18607)) | 9 new pairs (12 before the three were removed) | CC BY 4.0 or open access, as listed in the register's *supplemental_sources* sheet; the Lobo et al. licence is still to be checked |
| Wilderlab assay details, 9 July 2026 ([`Wilderlab_assay_details_260709.xlsx`](https://s3.ap-southeast-2.amazonaws.com/wilderlab.resources/methods/Wilderlab_assay_details_260709.xlsx)), the table that Wilderlab's laboratory methods (Wilkinson 2026, version 2.3.0, [doi:10.5281/zenodo.21288920](https://doi.org/10.5281/zenodo.21288920), CC BY 4.0) refer to for each assay's primers and PCR conditions. Its 25 assays are in `dev/faire_primer_lookup/sources/wilderlab_assays.tsv`: 25 assays, with primer codes, original names, references and Wilderlab's PCR conditions | 25 pairs, 16 of them new; the other 9 match published pairs already in the table, which keep their published names with the Wilderlab codes as aliases | Published by Wilderlab NZ; the spreadsheet states no licence, so it is cited here and not copied. Inclusion with the tool confirmed by Oliver Berry, 3 November 2026 |
| `curation.tsv` (this folder): corrections, aliases and checks against the papers, applied last (3 to 5 November 2026) | 4 corrected pairs (V16S-U, CoralITS2, CoralITS2_acro, and the gene of Wilderlab UM), 2 removed pairs (COI elasmobranch rows entered in error), 3 added pairs (fwh2 with fwhR2n; the 18S V4 pairs below), laboratory names for 3 pairs (vert01, tele01, 1391f and EukBr), notes on 14 others | Ours |
| 18S V4 primers, added to `curation.tsv` on 4 November 2026: TAReuk454FWD1 and TAReukREV3 (Stoeck et al. 2010, *Molecular Ecology* 19 Suppl 1:21-31, [doi:10.1111/j.1365-294X.2009.04480.x](https://doi.org/10.1111/j.1365-294X.2009.04480.x); sequences checked against the pr2-primers table, Vaulot et al. 2021, Table S1), and the Australian Microbiome pair with the modified TAReukREV3 ([protocol meth_4.1.4](https://research.csiro.au/ambsm/4-omics-sequencing-procedures/4-1-library-preparation-incl-amplicon-generation-where-appropriate/meth_4-1-4-eukaryotic-18s-v4-rrna-gene-tareuk454fwd1-and-modified-tareukrev3-1-step)), used for the SEA-MES 2 L samples | 2 pairs | Sequences as published |
| Bacteria and archaea 16S primer register, compiled for this project (3 November 2026): the ten broad-range pairs recommended by Klindworth et al. 2013 (*Nucleic Acids Research* 41:e1, [PMC3592464](https://europepmc.org/articles/PMC3592464/)), the Earth Microbiome Project 16S primers ([protocols](https://earthmicrobiome.ucsd.edu/protocols-and-standards/16s/)) and three other common pairs ([Frontiers in Marine Science 2023, 10.3389/fmars.2023.1199116](https://doi.org/10.3389/fmars.2023.1199116)) | 16 pairs | Sequences and references as published |

Primer sequences are facts; the table records where each came from. Keep the CC BY-NC 4.0
attribution with any copy of the Takahashi et al. rows.

## Known gaps and problems

- The supplement was checked against the papers on 3 November 2026, and the results are in
  `curation.tsv` and each row's `notes`:
  - VertU (Wang et al. 2023 Table 1), fwh1 and fwh2 (Vamos et al. 2017), LoboF1/R1 (Lobo et al.
    2013 Figure 1, where LoboR1 is printed as the sense strand), wilderlab_CI (Wilkinson et al.
    2024 Table 1) and the two coral 28S pairs (McCartin et al. 2024 Table 1) match.
  - V16S-U-F was corrected to `ACGAGAAGACCCYRYGRARCTT` as in Wang et al. 2023; the register had
    one C fewer. The register row is replaced.
  - fwh2 is kept with the laboratory-tested fwhR2 and added with the corrected fwhR2n
    (`GTRATWGCHCCDGCTARWACWGG`), which Vamos et al. 2017 tested only in silico.
  - CoralITS2 and CoralITS2_acro (DiBattista et al. 2024 Table 1) were listed with target gene
    28S rRNA. Their primers sit in 5.8S and 28S rRNA, either side of ITS2, so the target gene is now
    ITS with target_subfragment ITS2. CoralTTS2 acro is renamed CoralITS2_acro, and the CoralITS2
    reverse primer is named SCLER28SRev, as in the paper.
  - Takahashi et al. 2023 Table S4 rows 119 and 120 paired FishF1 forward with FishF2 reverse, and
    Shark COI-MINIR forward with FishF2 reverse. West et al. 2021 Table 1 uses FishF1 and FishF2
    (forward) with Shark COI-MINIR (reverse), which are rows 121 and 122, so rows 119 and 120 are
    removed.
  - Wilderlab UM (bacterial 16S V5) took the mitochondrial 16S gene from the metazoan register,
    which the build applies after the Wilderlab list. Its gene is now *16S rRNA (SSU prokaryote)*,
    as in the Wilderlab list. The build also kept turning a FAIRe 16S value given in a source into
    the mitochondrial one; it now keeps FAIRe values as given.
  - The Wilderlab WV assay (Wilkinson et al. 2024 Table 1) uses the same primers as the W pair of
    Nester et al. 2020 already in the table, so WV and wilderlab_WV were added as its names.
  - wilderlab_ZP, ZC, DG and YG (from the metazoan register) were removed on 7 November 2026.
    The register attributes them to Wilkinson et al. 2024, but they are not there or in the
    Wilderlab assay list of 9 July 2026, and no other source for their sequences or targets was
    found. (The list's closest assay to ZP and ZC is HD, MiDeca of Komai et al. 2019, a shorter
    primer pair in the same region.) The removals are in `curation.tsv` and the build's problems
    report, with the sequences, so the pairs can be added back if Wilderlab confirms them.
- Wilderlab's PCR conditions (annealing temperature, cycles, replication) are in each row's
  `notes`, not in the FAIRe columns, because the same primers are used elsewhere under other
  conditions.
- One primer pair appears twice in opposite orientations: Wilderlab RV and the table's 12S-V5-b
  (TAGAACAGGCTCCTCTAG and TTAGATACCCCACTATGC, the Riaz et al. 2011 12S V5 primers, which Wilkinson
  et al. 2024 describe as a Riaz forward and a Kelly et al. 2014 reverse). Both rows are kept, and
  the build reports them.
- `targetTaxonomicAssay` is filled for the species-specific assays (from Table S3) and the
  bacteria and archaea pairs, but not yet for most metabarcoding assays; `targetTaxonomicScope`
  holds the published target group (for example "Fish"). 31 pairs have no gene recorded.
- 16S is written as mitochondrial (*16S rRNA (LSU mitochondria)*) for the Takahashi et al. rows and
  as prokaryote (*16S rRNA (SSU prokaryote)*) for the bacteria and archaea register. Check the few
  non-animal 16S and 23S rows (algae, sponges) when using them.
- Two rows of the published tables were left out because neither sequence is plain IUPAC code (two
  primers in one cell; adapters with `XXXXXXXX` index placeholders), and 13 pairs have only one
  usable sequence (modified bases such as `rU`, stray characters, or a sequence not given).
  `faire_primers.py build --report` lists them.
- Several names are used for different sequences (515F, 806R, 341F, 785R, Uni18SR, and
  "Forward" and "Reverse" for 14 species-specific pairs). Lookups show every candidate.
- The register's references for the Earth Microbiome Project primers give authors only (Parada,
  Apprill, Quince, Caporaso), so citations with years in methods text do not match them yet.
- Laboratory names are added in `other_names` as they are found: vert01 (12S-V5), tele01 (teleo),
  1391f and EukBr (F1391/EukB), from the FAIRe examples verte_quadeloupe and noaa-aoml-gomecc4
  (5 November 2026). Others will be missing.

## Updating the table

Users can add primers at any time in Galaxy with **FAIRe mapper: build primer table** and use their
table in **FAIRe mapper: find primers**; nothing needs to change on the server.

To update the bundled table:

1. Edit the source registers in `dev/faire_primer_lookup/sources/` (not shipped with the tool), or
   add rows to `curation.tsv`. A curation row that corrects a sequence names the old pair's
   `primer_pair_id` in its `replaces` column, and the old pair is removed. A row with `replaces` and
   no sequences removes a pair entered in error; the build lists every removal.
2. Rebuild from all sources with `dev/faire_primer_lookup/build_table.sh`, which also writes the
   problems found. Rows with the same two sequences are merged; later sources replace earlier
   values where they give one, so the curation file has the last word.

   To add a few rows without the sources, build on the current table instead:

   ```bash
   python faire_primers.py build new_rows.xlsx --base primers/faire_primers.tsv \
       -o primers/faire_primers.tsv --report problems.tsv
   ```
3. Check `problems.tsv`, run the tests, raise `@VERSION_SUFFIX@` in `macros.xml` (or the tool
   version for larger changes), and publish to the ToolShed. Galaxy Australia then updates the tool.

A longer-term option is to keep the master table in its own repository, maintained by its
authors, with this file rebuilt from it at each release.
