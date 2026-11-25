# Licences of the bundled tools and data

The tool folders at the top of the skill (`faire_mapper/`, `fairefier/`, `faire2dwc/`, `faire2ncbi/`,
`faire2ena/`, `faire2qiime/`) are copies of the FAIRe tools from the FAIRe-Galaxy project,
https://github.com/FAIR-eDNA/FAIRe-Galaxy, at the commit named in `references/source_commit.txt`. They
are bundled unchanged so the skill works without downloading anything, except that each `LICENSE`
file is renamed `LICENSE.txt` (and `LICENSE.upstream` to `LICENSE_upstream.txt`), as some assistants
accept only files with known endings.

| What | Licence |
|---|---|
| `faire_mapper/*.py` (FAIRe mapper, by Oliver Berry, CSIRO, with Claude) | MIT (`faire_mapper/LICENSE.txt`) |
| `faire_mapper/checklist/` (FAIRe checklist v1.0.2 and full template, FAIR-eDNA) | CC BY 4.0 (`faire_mapper/checklist/LICENSE.txt`) |
| `faire_mapper/mixs_dwc_terms.tsv` (MIxS v7.0.1 and Darwin Core terms) | MIxS CC0; Darwin Core CC BY 4.0 (named at the top of the file) |
| `faire_mapper/primers/faire_primers.tsv` | Most rows from Takahashi et al. 2023, *Science of the Total Environment* 873:162322, under CC BY-NC 4.0; other sources and their terms in `faire_mapper/primers/README.md`. Keep this attribution with any copy |
| `faire_mapper/method_details/` (vocabulary and reliability tables) | MIT, as the mapper |
| `fairefier/fairefier_cli.py`, `create_validator.py`, `config_data.py` (FAIRe-fier, by Suk Yee Yong, CSIRO) | BSD 3-Clause (`fairefier/LICENSE_upstream.txt`) |
| `fairefier/checklist/` | CC BY 4.0 (`fairefier/checklist/LICENSE.txt`) |
| `faire2ncbi/scripts/`, `faire2ncbi/docs/` (FAIRe2NCBI, NOAA 'Omics, https://github.com/aomlomics/FAIRe2NCBI) | CC0 1.0 (`faire2ncbi/LICENSE_upstream.txt`) |
| `faire2ena/faire2ena_sample.py`, `faire2ena_run.py` (FAIRe2ENA, Minderoo OceanOmics Centre at UWA, https://github.com/FAIR-eDNA/FAIRe2ENA) | MIT (`faire2ena/LICENSE_upstream.txt`) |
| `faire2qiime/faire2qiime.py` (faire2qiime, NOAA 'Omics, https://github.com/aomlomics/faire2qiime) | CC0 1.0 (`faire2qiime/LICENSE_upstream.txt`) |
| `faire2dwc/` (FAIRe to Darwin Core), and the drivers `faire2ncbi_galaxy.py`, `faire2ena_galaxy.py`, `faire2qiime_by_assay.py`, `faire2qiime_run.py` and `normalise_faire.py` | MIT (`LICENSE.txt` in each folder) |

`../faire_session.py` and the skill's instructions (`SKILL.md`, `references/`) are MIT, as the
FAIRe-Galaxy project.

To update the tools, run `skill/build_skill.py` in a newer copy of the FAIRe-Galaxy repository: it
copies the same files and writes `references/source_commit.txt`.
