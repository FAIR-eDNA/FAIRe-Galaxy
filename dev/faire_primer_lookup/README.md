# Primer lookup: names and citations to sequences

`tools/faire_mapper/faire_primers.py` fills a gap found in the Dryad trial
(`dev/faire_mapper_real_datasets`): methods sections name or cite their primers ("the MiFish primer
set", "universal eukaryote 18S assay (Pochon et al., 2013)") but rarely give the sequences, which
FAIRe requires in `pcr_primer_forward` and `pcr_primer_reverse`.

The script builds a primer table from published compilations, then finds candidate primer pairs for
a name, a citation, or a whole methods text. `faire_mapper_methods.py --primers TABLE` adds the
candidates to its output, always for review, with the table row as the source.

## Primer sources

The tools now ship a primer table, `tools/faire_mapper/primers/faire_primers.tsv`, built from
Tables S3 and S4 of Takahashi et al. 2023 (CC BY-NC 4.0; inclusion confirmed), a metazoan register that puts those tables in
FAIRe terms, a bacteria and archaea 16S primer register, both compiled for this project, and the
Wilderlab assay list. `build_table.sh` rebuilds it from the files in `sources/`. The Wilderlab
assays are in `sources/wilderlab_assays.tsv`, in the table's columns. Wilderlab publishes the
original spreadsheet ([`Wilderlab_assay_details_260709.xlsx`](https://s3.ap-southeast-2.amazonaws.com/wilderlab.resources/methods/Wilderlab_assay_details_260709.xlsx), linked from its laboratory
methods, [doi:10.5281/zenodo.21288920](https://doi.org/10.5281/zenodo.21288920)); it is not copied here, and `convert_wilderlab.py` converts it or a newer one. The
table's columns are FAIRe term names. Its sources, gaps and update steps are in
`tools/faire_mapper/primers/README.md`. Users can add their own primers in Galaxy with
**FAIRe mapper: build primer table**.

## Results

**FAIRe examples** (`eval_on_faire_examples.py`, the nine example workbooks on the FAIR-eDNA site,
which give both names and sequences). With the Takahashi et al. tables alone, the table held the
pair for 6 of 18 assays; with the bacteria and archaea register added, 7. Looking up the primer
name, assay name or reference found the right pair for 5 of these 7 (LerayCOI, COILeray, 12S-V5,
TCCB and the NOAA 16S 515F-Y/926R pair), with 1 to 6 candidate pairs each, and for mamm01 a pair
that differs from the workbook by one degenerate base. It missed vert01 (a laboratory's own assay
name) and the 18S V9 pair (named 1391f in the workbook and F1391 in the table). The other 11
assays are not in the table (mostly new species-specific assays).

**Dryad methods texts** (`faire_primers.py text`): candidates for all four datasets.

| Dataset | Text says | Candidates |
|---|---|---|
| jackman | "the MiFish primer set" | MiFish-U and two MiFish-E pairs (Miya et al. 2015) |
| vanderheyde | "universal eukaryote 18S assay (Pochon et al., 2013)" | 18S Universal 18S_1F/18S_400R |
| mathon | `teleo` in the file names (no methods text) | teleo (Valentini et al. 2016) |
| sacco | "Bact16S_515F and Bact16S_806R" | with the bacteria and archaea register: four 16S pairs, led by the original and updated 515F/806R pairs (both primer names match) |

A citation counts only when the same sentence names the primers' gene, so "used to detect
stygofauna (West et al., 2020)" is not taken as a primer reference. Plain words that are primer
names in the table ("Forward", "Reverse") are ignored.

## Next steps

1. (Done 3 November 2026: inclusion of the Takahashi et al. and Wilderlab primers confirmed.)
2. Add laboratory aliases (vert01 for 12S-V5, tele01 for teleo, 1391f for F1391), each with its
   source, and years for the register's references so that citations match.
3. Let the FAIRe community maintain the table, as FAIRe-ator maintains the checklist, so every tool
   reads the same primer names.

`test_primers.py` checks the matching rules on a small table written for the test.
