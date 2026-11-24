# Licences of the bundled tools and data

The tools in this folder are copies of the FAIRe tools from the FAIRe-Galaxy project,
https://github.com/FAIR-eDNA/FAIRe-Galaxy, at the commit named in `SOURCE_COMMIT`. They are bundled
unchanged so the skill works without downloading anything.

| What | Licence |
|---|---|
| `faire_mapper/*.py` (FAIRe mapper, by Oliver Berry, CSIRO, with Claude) | MIT (`faire_mapper/LICENSE`) |
| `faire_mapper/checklist/` (FAIRe checklist v1.0.2 and full template, FAIR-eDNA) | CC BY 4.0 (`faire_mapper/checklist/LICENSE`) |
| `faire_mapper/mixs_dwc_terms.tsv` (MIxS v7.0.1 and Darwin Core terms) | MIxS CC0; Darwin Core CC BY 4.0 (named at the top of the file) |
| `faire_mapper/primers/faire_primers.tsv` | Most rows from Takahashi et al. 2023, *Science of the Total Environment* 873:162322, under CC BY-NC 4.0; other sources and their terms in `faire_mapper/primers/README.md`. Keep this attribution with any copy |
| `faire_mapper/method_details/` (vocabulary and reliability tables) | MIT, as the mapper |
| `fairefier/fairefier_cli.py`, `create_validator.py`, `config_data.py` (FAIRe-fier, by Suk Yee Yong, CSIRO) | BSD 3-Clause (`fairefier/LICENSE.upstream`) |
| `fairefier/checklist/` | CC BY 4.0 (`fairefier/checklist/LICENSE`) |

`../faire_session.py` and the skill's instructions (`SKILL.md`, `references/`) are MIT, as the
FAIRe-Galaxy project.

To update the tools, run `skill/build_skill.py` in a newer copy of the FAIRe-Galaxy repository: it
copies the same files and writes `SOURCE_COMMIT`.
