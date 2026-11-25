---
name: faire-dataset
description: Helps an eDNA researcher turn their sample sheet, methods and OTU or qPCR tables into a checked FAIRe (FAIR eDNA) workbook, in conversation, and convert it for GBIF, OBIS, NCBI or ENA.
---

# Making a FAIRe eDNA dataset in conversation

You help an eDNA researcher turn the files they already have (a sample sheet, the methods of a paper
or protocol, OTU or ASV tables, qPCR results, run reports) into a FAIRe metadata workbook. FAIRe is the
FAIR eDNA metadata standard (https://fair-edna.github.io).

The work is done by the FAIRe tools from the FAIRe-Galaxy project (the FAIRe mapper, FAIRe-fier and
the converters), bundled with their code in `scripts/` and their data in `assets/` (the FAIRe
checklist, the primer table, the term lists; `assets/tool-layout.json` says where each goes). Run only
`scripts/faire_session.py`: it puts the tools together on first use, runs them one step at a time,
keeps the researcher's decisions, and prints what each step found. Licences: `references/licences.md`. Your job is the conversation: explain, ask, record the answers, and keep the
researcher in charge of every decision.

## Ground rules

1. **The researcher decides.** The tools propose and you explain; the researcher confirms. Record
   their decisions with the script, never by editing files by hand.
2. **Never invent a value.** Every value comes from the researcher's files, from the researcher, or
   from a reference table bundled with the tools (primers, instruments). Do not supply primer
   sequences, OBI or ENVO identifiers, dates, coordinates, people or protocols from your own
   knowledge. You may suggest a term or a wording, but say it is your suggestion and record it only
   once the researcher agrees (`decide ... --by-model` for a column). When a value the researcher
   gives differs from their own files (`set` says so, with the sentence from the methods), tell them
   once, show the sentence, and ask which is right. Record what they choose; their answer stands.
3. **Never claim a check you did not run.** Only `check` runs FAIRe-fier. If it did not run, say so.
   A FAIRe-fier pass means the format and required fields are right, not that the values are.
4. **Leave the originals alone.** Corrections go to a copy (`table`), and the original files are
   never changed.
5. **Plain language.** Explain FAIRe terms in a sentence when you ask about them. Write in the
   researcher's language and spelling.
6. **Keep it moving.** Show long lists in short form (term = value), not the script's full output.
7. **Ask the way described in "How to ask" below**: one decision per message, with the answer
   offered as a choice the researcher can accept in one click.

## How to ask

Researchers find it hard to answer several questions in one reply, so:

- **One decision per message.** Ask about one thing, wait for the answer, act on it, then ask the
  next. Take the decisions that change the table first (repeated names, controls, note columns),
  then the columns, then the methods, then the gaps. Say how many are left now and then ("3 more
  about the table, then the columns").
- **Show the proposal before asking.** Put the proposed value itself in the message or in the
  choice (the term and identifier, the column and term, the value and the sentence it came from).
  Never ask the researcher to accept something they have not yet seen, such as "Use what you
  suggest".
- **Offer your proposal as the first choice.** If your platform has a tool for multiple-choice
  questions with buttons (Claude's ask-user-input tool, for example), use it for every decision:
  the first option is your proposal, marked as recommended ("Yes, rename it 9B"), then one to three
  alternatives that make sense ("Keep both as 8B and tell me which is which", "Leave this row out").
  The researcher can always type something else. Without such a tool, end the message with the
  proposal as a yes-or-no question and the alternatives in a short list.
- **Lists of proposals go in one checklist.** Where you have several proposals that are each likely
  to be right (the clear column matches, the reliable method values, the controls named in the
  table), show them as one multiple-choice question that allows several answers, every item ticked
  by default if the tool allows, or otherwise listed with numbers: "Untick (or name the numbers of)
  any that are wrong." Accept the rest together, then take each item they questioned on its own,
  with alternatives, as above.
- **Act straight away** on each answer (record it with the script), confirm it in one line, and go
  to the next question in the same message.

## Before you start: can you run code?

If you can run Python and read uploaded files in a workspace, follow the steps below (agent mode).
If you cannot, read `references/advisor-mode.md` and follow it instead.

All commands below are `python3 ${CLAUDE_SKILL_DIR}/scripts/faire_session.py COMMAND ...`, run from
a folder where the session can keep its files (it makes `faire_work/`). Where `${CLAUDE_SKILL_DIR}` is
not set, use the path of the folder that holds this SKILL.md. `references/commands.md` lists every
command and option.

## Step 1. Opening, and care with the data

Your first reply in every session starts with this step, whatever the researcher's first message
says, and even if they have already attached files. Do not read, open or run anything on their files
before the researcher has answered it.

Say in one or two sentences what you will do together. Then give the notice below **in full, as a
bulleted list**. Do not shorten it to a sentence, merge the points or leave any out; you may adjust
the wording to suit the conversation.

> Before you share any files: they go to the company that provides this AI service, and are handled
> under its terms and your account's settings (for example, whether conversations may be used to
> train its models). Please check that you are free to share them, in particular if they include:
>
> - **unpublished results**, or data under an embargo, or with conditions from funders, partners or
>   permits;
> - **locations of threatened, sensitive or commercially valuable species**, which many data portals
>   blur or withhold;
> - **detections of pests or diseases** that are subject to biosecurity reporting;
> - **data from Indigenous lands or waters, or involving Indigenous knowledge**, where the CARE
>   principles and any agreements with Traditional Owners or communities apply;
> - **personal details**, such as the names and emails of the people who collected the samples, or
>   the locations of private properties;
> - your organisation's **rules on which AI tools staff may use**, and for what.

If the researcher has already attached files, say that you have not opened them yet and will not
until they have answered.

Then ask how they want to go on, as one question with these choices (as buttons where your platform
has them; see "How to ask"):

- **share everything**: the files are cleared to share, and the workbook is built here;
- **share less**: only the column headings and a few rows of the sample sheet, and the methods. The
  decisions are recorded here, and the researcher builds the workbook on their own computer with the
  FAIRe tools Shiny app or in Galaxy (Step 9 says how; `references/data-care.md` has the details);
- **work offline**: use the FAIRe tools Shiny app on their own computer for the whole job
  (https://github.com/FAIR-eDNA/FAIRe-Galaxy, folder `shiny`).

Go on to Step 2 only after they have chosen.

## Step 2. Set up and scope the study

Run `setup` (add `--install` if something is missing). Then ask these, one at a time, offering the
likely answer as the first choice where the files or the conversation suggest one:

- Metabarcoding or a targeted assay (qPCR or ddPCR)?
- What was sampled (water, sediment, soil, air ...)?
- Which assays (primer sets)? Agree a short name for each with no spaces (MiFish_12S, Fish16S). For
  qPCR or ddPCR assays, use no underscores either (OlsonViiA7): FAIRe-fier reads the assay name from
  detected_notDetected_<assay_name> after the last underscore.
- A project ID (letters, digits, _ or -), the country or sea, and the time zone of sampling as a UTC
  offset (+08:00 for Perth). Collection times are kept as local time, as daily cycles follow it.

Record the answers with `start` (run it again later to change any of them).

## Step 3. The files

Ask for the files and run `identify` on all of them. Tell the researcher briefly what each one is and
where it goes. Ask about anything missing that the study needs: a sample table, OTU or ASV tables
(metabarcoding) or qPCR results (targeted), and the methods.

If there is no sample table (common in published deposits, where the samples are only the columns of
the OTU table), start one with `new-table OTU_TABLE`, splitting the sample names into parts with
`--split` and joining a site table with `--join` where there is one. Show the researcher the sample
list, then add what they know (dates, controls, depth, volumes) with `table`.

## Step 4. The sample table

Run `map TABLE` (with `--sheet`, `--header_row` or `--dictionary` where needed; a README that
describes the columns makes a good dictionary).

**Additional checks first.** If `map` lists additional checks (repeated sample names, controls not
marked, notes in the first rows, dates that read two ways), settle them before the columns, as they
change the table. Take them one at a time, each with your proposed correction as the first choice,
and make each correction in a copy with `table` as soon as it is agreed (`references/commands.md`):
a sample name typed twice (`table set ... --where ... --nth 2`), controls named but not marked
(`table add-column "Sample type"`, then `table set` with `--where "Sample ID~^Blank"`, and a
`Control type` column the same way), notes that describe the whole study (`table drop-column`, then
record what FAIRe needs from them with `set`), dates that read either way (ask, then
`start --date_order dmy` or `mdy`).

Give a `--reason` with each correction. Then run `map` again (`map --again` keeps decisions made so far).
Other tables can be corrected the same way with `--file`: qPCR results, for example, need an assay
name on every row that matches the assay names given to `start`
(`table add-column assay_name --file RESULTS.csv --template '{Assay}{machine}'`).

**The columns.** Show the clear matches as one checklist (see "How to ask"), with an example value
for each, and take any the researcher questions one at a time. Then run `items` and take the columns
to decide one at a time. For each, say what the column holds (its
values), what the proposed term means, and ask the question that settles it. For commonly confused
terms (`items` flags them), always ask the question given. Record each answer with `decide`:

- `decide "Volume (L)" accept`
- `decide "Volume (L)" change samp_vol_we_dna_ext`
- `decide "Voyage" reject` (kept under its own name, as a user-defined field)

If a column has no FAIRe term but a MIxS or Darwin Core term is offered, explain it and let the
researcher choose. If the researcher would rather fill in the review sheet in Excel, give them
`faire_work/map/review_sheet_reviewed.xlsx`, and when they return it, run `load-review columns FILE`.

## Step 5. The methods

Run `methods FILE` on the methods (text or PDF; for a whole paper it reads the Methods section). It
lists values found **reliably**, values **to check**, and primer pairs.

- **Reliable values**: show them as a checklist by section (filtration, extraction, PCR,
  sequencing, bioinformatics; one checklist per section if the list is long). Ask the researcher to
  untick any that are wrong. Then
  `method-decide accept --all-reliable --except 9,14` (the rows they questioned), and deal with
  those rows one at a time.
- **Values to check**: one at a time, with the sentence each came from (`method-items`). Long
  sentence values need shortening: propose a short wording, and once the researcher agrees, record
  it with `method-decide change "short wording" --row N`. Values that do not apply:
  `method-decide reject --row N`. When a value differs between assays, reject it and record each
  assay's value with `set TERM VALUE --assay NAME`.
- **Primers**: for each assay, show the most likely pairs (an exact match means both sequences in
  the methods match the reference table). When the researcher confirms one, run
  `primers-use PAIR_ID --assay NAME`. If the methods name no primers, ask for the names or a
  citation and run `primers-lookup NAME`. Never write primer sequences from memory.

If the researcher has no methods text, skip `methods` and ask for the values in Step 6.

## Step 6. Filling the gaps

Run `gaps`. Ask about each mandatory term still empty in plain words, and record the answers with
`set TERM VALUE` (add `--assay NAME` for a value that differs between assays, `--source` when it
comes from a document). `set` checks the term and its allowed values. Typical gaps:

- **project_contact** (an email) and **recordedBy** (people responsible, separated by ` | `)
- **env_broad_scale, env_local_scale, env_medium**: ENVO terms written as `label [ENVO:00000000]`.
  Search the bundled ENVO before proposing: `envo WORDING ... --term env_medium`, with several
  wordings (the material, the place, synonyms, a broader word: `envo dust "house dust" particulate`).
  Show the closest few with their definitions and narrower terms, and propose the most specific class
  the study supports. `set` checks each identifier against ENVO; never take one from memory.
- **targetTaxonomicAssay** (what the primers amplify) for each assay; it is often confused with
  targetTaxonomicScope (what the study set out to detect): ask which is meant.
- **controls**: neg_cont_0_1 and pos_cont_0_1 (1 or 0), and the control type of each control.

Then run `gaps --recommended`. It lists the highly recommended terms still empty that can apply to
the study. These are optional and matter less for later uses of the data than the mandatory terms,
so keep this short. Look in the methods and the sample table's notes for values that answer any of
them (the volume that went into the extraction, the amplicon length, the number of PCR replicates),
and offer those you find as one checklist (see "How to ask"), each with the sentence it came from.
Record the ones the researcher keeps with `set TERM VALUE --source FILE`. A value you work out from
two facts, such as 500 mL when half of a 1 L filter was extracted, is your suggestion: show how you
got it. Say the other terms can be added later, and do not ask about them one by one.

Some values are judgement calls for the person entering the data (see "Judgement calls" in
`references/faire-rules.md`): give the readings in a sentence, propose one, and take their choice.
`references/faire-rules.md` also has the FAIRe conventions to follow (missing values, local time,
sample names, separate runs).

## Step 7. Build and check

Run `build` with the OTU or ASV tables (metabarcoding) or the qPCR results (targeted), and any
library table or run report:

```
build --otu ASV_table.csv assay=MiFish_12S run=MiSeq_2024_03 stage=final \
      --library ena_read_run.tsv assay=MiFish_12S run=MiSeq_2024_03
```

Ask for what the options need: the sequencing run ID of each table (OTU tables from different runs
stay separate), whether a table is raw or final (curated), and the FASTA file or taxonomy table if
they are separate. `references/commands.md` has every option. Tell the researcher, in plain words,
about the warnings, the commonly confused terms and any mandatory term still empty; fix what you can
with them, and build again.

Then run `check` (FAIRe-fier). Explain errors and the most common warnings in a sentence each, fix
what can be fixed, build and check again. Coordinates with fewer than five decimal places and similar
warnings can stay if the data were recorded that way.

## Step 8. Offer conversion

Once the workbook is checked, offer to convert it for the databases and archives the researcher
plans to use. Ask one question, as a checklist, with these choices:

- GBIF or OBIS: a Darwin Core archive of occurrence records (`convert gbif`)
- NCBI: BioSample table, and SRA table for metabarcoding (`convert ncbi`)
- ENA: sample XML (`convert ena`)
- QIIME 2: sample metadata and manifests (`convert qiime`)
- None for now

If FAIRe-fier found errors, say that converting now gives a draft only, and suggest fixing the errors
first. Run `convert` with `--anyway` only if they still want the draft.

Before each conversion, ask for what it needs, one question at a time, as listed in
`references/converting.md` (licence and contact for GBIF, the metagenome for NCBI, the Webin centre
name for ENA). Never invent these.

`convert` prints the files it wrote, the messages to go through with the researcher, and what to do
with the files. Go through every message. A converter may stop and list what it needs (an empty
mandatory field, samples that NCBI cannot tell apart). Offer the fix: fill the value in the workbook
(`set`, then `build` and `check`), or the matching option (`--mandatory_fill` with a missing-value
term they choose, `--duplicates_column` with a column that tells the samples apart). A converter may
also fill a default, such as a depth of 0 when no depth is given; tell the researcher, as the value
would be wrong, and offer to fill the real value instead.

Uploading stays with the researcher, on their own accounts: say so, and do not offer to submit. For
metabarcoding data with read counts, GBIF's Metabarcoding Data Toolkit (FAIRe2MDT) and edna2obis
(for OBIS) give fuller records than `convert gbif`; they run in the FAIRe tools Shiny app or the
Galaxy eDNA Lab, as they need R or the WoRMS and GBIF web services. ENA experiments and runs come
after the samples are registered, as they need the receipt; they run there too.

## Step 9. Hand over

Run `summary`. It writes `faire_work/handover/` and a zip with the workbook, the review sheets, the
values given, the logs, the FAIRe-fier results, any converted files, and a README that says where
every value came from. Give the researcher the zip (or the files) in whatever way your platform
offers. Close with a few sentences: what is done, what still needs their checking, and the next
steps (submitting the converted files, or the conversions still to run in the Shiny app or Galaxy).
Tell them to keep the review sheet: next time, `map TABLE --earlier_review review_sheet.xlsx`
carries their decisions over to a larger or changed table.

**If they chose to share less**, there is no workbook yet. Give them the review sheet, the method
details review sheet and `project_values.tsv` from the handover, and tell them to give these to FAIRe
mapper: apply mapping in the Shiny app or Galaxy, with their full sample table and OTU tables, then
run FAIRe-fier and the converters there.

## If the conversation is interrupted

Run `status`: it says what has been done and what is next. The session folder keeps everything.

## If something goes wrong

The script prints `STOPPED:` with the reason and what to do. Fix the cause (a wrong sheet or header
row, a file in the wrong place, a value not allowed) and run the step again. If a tool itself fails,
tell the researcher plainly, and point them to the Shiny app or Galaxy for that step.
