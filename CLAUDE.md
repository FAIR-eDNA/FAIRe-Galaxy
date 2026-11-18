# Working on FAIRe-Galaxy

This file sets out the house style and working conventions for this repository. It is written for
Claude Code and for anyone else contributing. The repository brings the eDNA community's FAIRe tools
into Galaxy for the Galaxy Australia eDNA Lab, adds the FAIRe mapper (new code that turns a lab's own
tables into a FAIRe workbook), and has a Shiny app (`shiny/`) that runs the same tools on a person's
own computer.

Read `README.md` first, then the README of the folder you are working in. Each tool folder's README
records its status, what the wrapper adds, upstream issues, test results and the steps left before
deployment. `tools/faire_mapper/README.md` and `shiny/README.md` are the fullest.

## House style

Everything written in this repository follows one style: READMEs, tool help, the app's text, guides,
commit messages and pull request descriptions.

- Australian spelling (organise, licence as a noun, colour, behaviour, analyse).
- No em dashes. Use a comma, a colon, brackets or a new sentence.
- Active voice and plain English.
- Full, natural sentences, in the voice of a typical Australian scientist. Avoid the terse, clipped
  style of a language model, and avoid business or start-up language.
- Concise. Say a thing once. Do not restate a point as a contrast ("X rather than Y", "not A but
  B") unless the contrast is the point.
- Plain descriptive words in place of punchy abstractions; no rhetorical flourishes, challenge
  adverbs ("honestly") or adversarial framing.
- Gentle framing of critique: "is not ideal because" in place of "is fragile because".
- Help text instructs. It says what to do and what will happen, and leaves design reasons to the
  READMEs.
- Keep the same words for the same things across the tools, the guides and the app.

## How the repository is put together

- Each folder under `tools/` is its own ToolShed repository, with its own `.shed.yml`, `LICENSE`,
  macros and test data. Files shared between folders are copied into each one.
- The guide at the end of every tool's help is `dev/faire_guide/faire_guide.xml`. Edit it there and
  run `python dev/faire_guide/sync.py` to copy it into every folder (`--check` lists stale copies).
  `docs/faire_tools_guide.md` is the same text in Markdown; keep it in step.
- The FAIRe mapper's inputs guide exists twice: `docs/faire_mapper_inputs.md` and `HELP_INPUTS` in
  `tools/faire_mapper/macros.xml`. Change both together.
- Upstream scripts are copied in unchanged, with their licence in `LICENSE.upstream`. Work around
  upstream problems in the Galaxy driver scripts, and record each problem in the folder README for
  reporting upstream. The FAIRe2MDT and edna2obis drivers replace named upstream functions at run
  time; when the upstream pin changes, check those functions still exist and behave as assumed.
- The Shiny app builds the same command lines as the Galaxy tools (`shiny/R/tools.R`). When a tool's
  parameters change, change the app's form and `tools.R` as well.
- The mapper's review sheet (`tools/faire_mapper/faire_mapper_review.py`) and the app's review screen
  must agree. The review sheet's layout came from the FAIRe team's review; change it with their
  agreement.
- `dev/` holds trials, benchmarks and comparisons that are not published to the ToolShed. `demo/`
  holds two small demonstration datasets.

## Principles for what the tools do

- Read and write the FAIRe layout that FAIRe-ator produces (assay columns `assay1`, `assay2`, or
  `project_level`).
- Automate only what FAIRe defines, common pipeline outputs, and patterns seen in two or more
  datasets. Send everything else to a person for review.
- A language model is always optional. Every tool works without one, and a model's answers are only
  suggestions until a person confirms them.
- Commonly confused FAIRe terms always go to review (`tools/faire_mapper/commonly_confused_terms.tsv`).
- Ask about ambiguous dates (day first or month first); never guess. Keep local times.
- Report anything a tool leaves out, with a count. Stop only on scientific ambiguity or obvious
  corruption, and leave harmless formatting alone.
- No tool submits anything to an archive or takes credentials.
- The decisions behind these, with dates, are in the README's *Decisions* section and the folder
  READMEs. Raise a change to them with the maintainers before acting on it.

## Making a change

1. Work on a branch and open a pull request into `main`. Merge with a squash merge once the
   maintainer agrees.
2. Before changing what a tool writes, add a test that fails, then make the change.
3. Update the folder README in the same pull request: status, what changed, the test summary line,
   and the steps left. Update the root README's tool table if a status or test count changes.
4. Bump versions when behaviour changes:
   - FAIRe mapper: `@TOOL_VERSION@` in `tools/faire_mapper/macros.xml` and `__version__` in
     `faire_mapper.py`, `faire_method_details.py` and `faire_primers.py`.
   - Wrapped tools: `@TOOL_VERSION@` follows the upstream pin (a release, or the date of the pinned
     commit); `@VERSION_SUFFIX@` counts wrapper changes and returns to 0 when the pin changes.
   - Shiny app: `APP_VERSION` in `shiny/app.R`, with a note in `shiny/README.md`.
5. Commit with your GitHub no-reply address, never a personal email address.

## Testing

- `planemo lint` and `planemo test` on each tool folder, one folder at a time (given only `tools/`,
  planemo does not look inside the folders). Galaxy will not run as root, so run planemo as an
  ordinary user. The first run downloads Galaxy and builds conda environments.
- Continuous integration (`.github/workflows/pr.yaml`, the IUC's planemo-ci) tests the changed
  folders on Galaxy release_26.1 with internet access. Until each `.shed.yml` has a real `owner`,
  "Lint tool-list" and "Check workflow success" fail on every run; the "Test tools" jobs, flake8 and
  the file-size check must pass.
- Run flake8 from the `tools/` folder so it picks up the repository's `.flake8`.
- Keep each folder's test data small (well under 1 MB in total).
- For the app, run it from the `shiny` folder
  (`Rscript -e 'shiny::runApp(".", port = 7788, launch.browser = FALSE)'`) and try the change in a
  browser; Playwright with headless Chromium works for scripted checks.
- After changing how the mapper matches columns, rerun `dev/faire_mapper_benchmark/`.
- After changing FAIRe-fier's wrapper, rerun `dev/fairefier_equivalence/`.

## Known pitfalls

- Galaxy dataset paths end in `.dat`. Recognise files by their content, and give pandas and openpyxl
  an explicit engine.
- Galaxy job scripts set `PYTHONWARNINGS=ignore`. A tool that reports problems through Python's
  warnings module must undo it.
- In planemo assertions, a real tab inside an XML attribute is read as a space; write `\t` in
  `has_line_matching` expressions.
- Workbooks written by openpyxl have no `xl/sharedStrings.xml`; assert on `xl/worksheets/sheet1.xml`.
- Read spreadsheet cells as text (`dtype=str`, `keep_default_na=False`) so IDs such as `001` keep
  their zeros and NA-like text is not emptied. Keep text that starts with `=` as text when writing
  Excel.
- FAIRe-ator's workbooks cannot be fully opened by openpyxl; `normalise_faire.py` reads them.
- In the Shiny UI, htmltools puts a space between child tags; use the `inline()` helper in
  `shiny/R/ui.R` or `HTML(paste0(...))` before punctuation. Use `DTOutput(..., fill = FALSE)` so
  tables do not overlap what follows. In Playwright, set selectize inputs with
  `document.getElementById(id).selectize.setValue(...)`.
- FAIRe-fier's pinned pydantic (2.7.0) does not build on Python 3.13; use Python 3.12.
- Compare FAIRe-fier outputs with `PYTHONHASHSEED=0`, as set order affects the order of messages.

## Data that must not be committed

- Unpublished data. `dev/faire_mapper_seames/data/private/` and `demo/seames/private/` are in
  `.gitignore` for the SEA-MES authors' unpublished table; nothing built from it may be committed.
- Large files. The four largest SEA-MES files are downloaded from the data record.
- Papers, their text, and the FAIRe example workbooks (tables built from them are rebuilt by
  script).
- Credentials, account numbers (such as ENA Webin accounts), API keys and personal email addresses.
- When offering `demo/daynight` or the primer table, say that they are CC BY-NC 4.0 (the primer
  table's rows from Takahashi et al. 2023).
