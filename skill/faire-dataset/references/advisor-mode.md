# Advisor mode: when you cannot run code

Use this when your chat can read files but cannot run Python. The researcher runs the FAIRe tools
themselves, in the FAIRe tools Shiny app on their own computer or in the Galaxy eDNA Lab, and you
help them make each decision. You never write the FAIRe workbook yourself, and you never say it has
been checked: only FAIRe-fier, run by the researcher, checks it.

The ground rules in SKILL.md apply unchanged, and so does the data notice in `data-care.md`.

## Where the researcher runs the tools

- **The FAIRe tools Shiny app** runs on their own computer. With R and Python installed, this line in
  R downloads it, sets it up and starts it:
  `source("https://raw.githubusercontent.com/FAIR-eDNA/FAIRe-Galaxy/main/shiny/start.R")`
- **Galaxy**: the FAIRe mapper tools in the Galaxy eDNA Lab, where Galaxy Australia offers them.

Both have the same steps: identify your files, propose mapping, find primers, find method details,
values for the whole project, apply mapping, FAIRe-fier.

## The steps

1. **Opening and data notice**, as in SKILL.md Step 1.
2. **Scope**, as in SKILL.md Step 2. Write the answers down for the researcher, as they enter them in
   the app: assay type, sample types, assay names, project ID, country or sea, UTC offset.
3. **Propose mapping.** Ask the researcher to run *propose mapping* on their sample table and share
   the review sheet it writes (or paste its Review sheet). Go through it with them:
   - the rows the mapper accepted: a short list, asking if any look wrong;
   - the rows to review, one at a time: what the column holds, what the proposed term means, the
     question for commonly confused terms (`faire-rules.md`), and the decision (Accept, Reject or
     Change with the replacement term). The researcher enters each decision in the sheet's
     *Reviewer's decision* and *Replacement FAIRe term* columns;
   - the *Additional checks to make* sheet: the corrections to make in their table, after which they
     run propose mapping again and give the earlier review sheet so their decisions carry over.
4. **Methods.** Ask them to run *find primers* and *find method details* on their methods and share
   the outputs. Go through the method details review sheet as in SKILL.md Step 5: the reliable values
   as a list, then the values to check one at a time with their sentences. They enter Accept, Reject
   or Change (with *Your value*) in the sheet. For primers, help them choose the pair the study used
   for each assay from the candidates.
5. **Values for the whole project.** For the mandatory terms still empty (apply mapping lists them,
   and so does *propose mapping*'s list of mandatory terms not covered), ask the researcher, as in
   SKILL.md Step 6. Collect the answers in a table they can load into the app's *Values for the whole
   project* (Load these values): tab-separated, with the columns `term`, `value` and `assay` (empty
   for the whole project). For example:

   ```
   term	value	assay
   project_contact	j.smith@example.org	
   recordedBy	Jo Smith | Sam Lee	
   env_broad_scale	freshwater river biome [ENVO:01000253]	
   pcr_primer_forward	GTCGGTAAAACTCGTGCCAGC	MiFish_12S
   ```

   Give it in a code block so it can be copied exactly, and say where each value came from (the
   researcher's answer, their methods, the primer reference table). Check each term and its allowed
   values against `faire-terms.md` or the checklist. Only the researcher's answers and their files
   are sources; take nothing from your own memory.
6. **Build and check.** The researcher runs *apply mapping* with the reviewed sheets, the values and
   their OTU or qPCR tables, then *FAIRe-fier*. Ask them to share the log and FAIRe-fier's report, and
   explain each error and the common warnings, and what to change.
7. **Convert.** Only once every mandatory term is filled and FAIRe-fier finds no errors (GBIF, OBIS,
   NCBI and ENA need them all), ask which databases or archives they plan to use, and point
   them to the matching converters in the Shiny app or Galaxy: FAIRe2MDT or FAIRe to Darwin Core for
   GBIF, edna2obis or FAIRe to Darwin Core for OBIS, FAIRe2NCBI, FAIRe2ENA, and FAIRe2QIIME. Explain
   the messages the converters give, as in SKILL.md Step 8. Uploading stays with the researcher.
8. **Close** with what is done, what they still need to check, and the next steps, as in SKILL.md
   Step 9.

## What to avoid

- Do not write a FAIRe workbook, a review sheet or OTU tables as text or as a file. They are made
  by the tools, which convert dates, units, coordinates and taxonomy in ways that are easy to get
  wrong by hand.
- Do not report FAIRe-fier results you have not seen.
- If the researcher cannot run the tools at all, you can still help them fill in a blank FAIRe
  template (from FAIRe-ator, or the FAIRe website) term by term, with the same rules about sources.
