# FAIRe dataset skill for AI assistants

A third way to make a FAIRe dataset, alongside the Galaxy tools and the Shiny app. The researcher
talks with an AI assistant, which runs the same FAIRe tools in its own workspace, explains what they
find, asks the questions only the researcher can answer, and records each decision. At the end the
researcher gets the FAIRe workbook, checked by FAIRe-fier, and a README that says where every value
came from.

The package follows the open Agent Skills format (a folder with a `SKILL.md`), which Claude, ChatGPT,
Microsoft 365 Copilot and most coding assistants can load. One package serves all of them.

## What is in it

```
faire-dataset/
  SKILL.md                  the instructions the assistant follows, step by step
  references/
    data_care.md            the notice on data sensitivity given before any file is shared
    faire_rules.md          FAIRe conventions: missing values, local time, controls, runs, confused terms
    faire_terms.md          the mandatory and highly recommended FAIRe terms (made from the checklist)
    commands.md             every command of faire_session.py
    advisor_mode.md         how to help when the assistant cannot run code
  scripts/
    faire_session.py        runs the tools one step at a time and keeps the session's decisions
    tools/                  copies of the FAIRe mapper and FAIRe-fier from tools/, with their licences
```

The assistant never writes the workbook itself. `faire_session.py` runs FAIRe mapper (identify,
propose mapping, find method details, find primers, apply mapping) and FAIRe-fier, and keeps the
researcher's decisions in the same review sheets the Galaxy tools and the Shiny app use. A session
can therefore be finished in the Shiny app or Galaxy, and a review made there can be brought back.

## How a session goes

1. The assistant says what it will do and gives the data notice: files go to the AI provider, so the
   researcher checks for unpublished data, sensitive species locations, biosecurity detections,
   Indigenous data and personal details, and their organisation's rules. They can share everything,
   or only the column headings, a few rows and the methods, and build the workbook offline.
2. A few scoping questions: assay type, sample types, assay names, project ID, country, time zone.
3. The files are identified. A study with no sample table gets one made from its OTU table.
4. The sample table is mapped. Problems such as repeated sample names or unmarked controls are fixed
   in a copy. The columns that need a decision are taken one at a time, with the question that tells
   commonly confused terms apart.
5. The methods are read for values for the whole study and for primers; the researcher confirms the
   reliable values as a list and the others one at a time.
6. The mandatory terms still empty are asked about in plain words. Highly recommended terms that the
   methods answer are offered as one optional checklist.
7. The workbook is built with the OTU tables or qPCR results, and checked with FAIRe-fier.
8. The researcher gets a zip of the workbook, review sheets, logs and a README of provenance.

If the assistant cannot run code, it follows `references/advisor_mode.md`: the researcher runs the
tools in the Shiny app or Galaxy, and the assistant helps with each decision.

## Building the package

```
python skill/build_skill.py            # writes skill/dist/faire-dataset.zip and skill/dist/faire-dataset-plugin.zip
```

The build copies the current tools from `tools/faire_mapper` and `tools/fairefier`, makes
`references/faire_terms.md` from the checklist, and records the commit in
`scripts/tools/SOURCE_COMMIT`. Rebuild after any change to the tools, so the package and the Galaxy
tools stay the same. The zip is about 0.6 MB.

## Setting it up

So far the skill has been tested only in Claude, on paid plans. Whether you can add it to an
assistant depends on your subscription and on your organisation's settings for that assistant.
Trials so far:

| Assistant | Status |
|---|---|
| Claude (Max) | Works: added as a plugin, and run on the khapra beetle data |
| ChatGPT (free plan) | Could not be added: the free plan does not allow skills |
| Microsoft 365 Copilot | Not yet added: organisations can turn off skills or agent building |

### Claude (claude.ai, desktop and mobile apps)

1. Check that code execution is on: *Settings > Capabilities > Code execution and file creation*
   (Free, Pro and Max plans), or ask the organisation owner (Team and Enterprise plans).
2. Add the skill in one of two ways, depending on what your account shows:
   - **Plugins** in the left-hand menu, then *Add > Upload plugin*, and upload
     `faire-dataset-plugin.zip` (the skill packaged as a plugin);
   - or *Customize > Skills*, then **+**, *Create skill > Upload a skill*, and upload
     `faire-dataset.zip`.
3. In a new chat, ask for it, for example: *"Help me make a FAIRe dataset from my eDNA data."*

Claude limits a skill's description to 200 characters; this one has 179.

### ChatGPT

In *Skills*, choose *Create > Upload from your computer* and upload the zip. Skills need a paid
plan; in business and enterprise workspaces an administrator may also need to allow skills and skill
uploads. ChatGPT runs the scripts in its own Python workspace. Not yet tried.

### Microsoft 365 Copilot

Skills are added to a declarative agent, made in Agent Builder:

1. Create an agent (for example *FAIRe dataset assistant*), with short instructions such as *"Help
   eDNA researchers make FAIRe datasets with the faire-dataset skill."*
2. Turn on the *Code interpreter* capability.
3. Add the skill: upload `faire-dataset.zip`.

This needs a Microsoft 365 Copilot licence, and an organisation can turn off skills or agent
building; ask your IT team if the options above are missing. Once it can be added, the first thing to
check is whether the agent's code interpreter runs the skill's scripts. If it does not, the assistant
falls back to advisor mode, which still works.

### Coding assistants (Claude Code, Codex, GitHub Copilot in VS Code, Gemini CLI)

Copy the `faire-dataset` folder from `skill/dist/` into the assistant's skills folder (for example
`.claude/skills/`, `.github/skills/` or `.agents/skills/` in a project). These run the scripts on the
researcher's own computer, so the data stay there unless the assistant's model provider sees them in
the conversation.

### Any other chat

Attach `SKILL.md`, `references/advisor_mode.md`, `references/data_care.md` and
`references/faire_rules.md`, and start with: *"Follow SKILL.md to help me make a FAIRe dataset. You
cannot run code, so use advisor mode."*

## Testing

`skill/test_skill.sh` builds the package, unpacks it in a clean folder and runs three demonstration
sets through every step, with the researcher's answers written into the script:

- **day-night** (`demo/daynight`): metabarcoding with two assays; the sample sheet needs a sample
  name corrected, controls marked, an extraction blank added and three note columns left out; the
  methods give the values for the whole study and both primer pairs; LCA outputs with FASTA files and
  a list of fastq files. The workbook passes FAIRe-fier.
- **khapra beetle** (`demo/khapra`): a targeted qPCR study; the authors' sample types are kept and a
  FAIRe sample category added; the results get an assay name on each row.
- **eelgrass** (`demo/eelgrass`): no sample table, so one is made from the OTU table's columns and
  the site coordinates.

```
bash skill/test_skill.sh OUTDIR          # PYTHON=... to use another Python
```

All three pass with Python 3.10 and 3.13, pandas 2.2.3 and 3.0. This tests the machinery. How well
a given assistant follows SKILL.md in conversation still needs trying with real researchers and
their data, in each of Claude, ChatGPT and Copilot.

## Limits

- Assistants vary, and so does the same assistant from one model version to the next. The rules in
  SKILL.md (no invented values, every decision recorded, no check claimed that was not run) are the
  safeguards, and the handover README lets a reviewer see what was decided and by whom.
- Chat workspaces usually cannot reach the internet. ENVO identifiers then come from the researcher,
  or from the assistant's own web search if it has one; the tools cannot look them up.
- Chat tools limit the size of uploads. Very large OTU tables are better handled in the Shiny app or
  Galaxy.
- If a workspace lacks pandas, openpyxl and numpy and cannot install them, the tools cannot run
  there; `setup` says so, and the assistant uses advisor mode.

## Licences

`SKILL.md`, `references/` and `faire_session.py` are MIT, as the rest of this repository. The bundled
tools and data keep their own licences, listed in `scripts/tools/LICENSES.md`: the FAIRe checklist is
CC BY 4.0, FAIRe-fier is BSD 3-Clause, and most rows of the primer table come from Takahashi et al.
2023 under CC BY-NC 4.0.
