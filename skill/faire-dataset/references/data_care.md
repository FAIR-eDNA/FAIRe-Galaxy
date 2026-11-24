# Care with the data

Give this notice at the start of every session, before any file is uploaded or read. Put it in your
own words, keep every point, and keep it short. Then ask the researcher to confirm before going on.

## The notice

The files you share in this conversation go to the company that provides this AI service, and are
handled under its terms and your account's settings (for example, whether conversations may be used
to train its models). Before you share anything, please check that you are free to, in particular
if the data include:

- **unpublished results**, or data under an embargo, or with conditions from funders, partners or
  permits;
- **locations of threatened, sensitive or commercially valuable species**, which many data portals
  blur or withhold;
- **detections of pests or diseases** that are subject to biosecurity reporting;
- **data from Indigenous lands or waters, or involving Indigenous knowledge**, where the CARE
  principles for Indigenous data governance and any agreements with Traditional Owners or
  communities apply;
- **personal details**, such as the names and emails of the people who collected the samples, or the
  locations of private properties;
- your organisation's **rules on which AI tools staff may use**, and for what.

If you are unsure, there are two other ways to go on:

- **share less**: give only the column headings and a few rows of your sample sheet, and the
  methods. We record the decisions here, and you build the workbook on your own computer with the
  FAIRe tools Shiny app, or in Galaxy;
- **work offline**: use the FAIRe tools Shiny app on your own computer for the whole job
  (https://github.com/FAIR-eDNA/FAIRe-Galaxy, folder `shiny`).

## When the researcher chooses to share less

- Ask for a copy of the sample sheet with the column headings and 10 to 20 typical rows, including
  a control or two. More rows help the mapper judge each column; real values matter less than their
  form, so coordinates can be rounded or replaced with made-up values of the same form.
- Corrections you make with `table` change only the copy here. Tell the researcher each correction
  so they can make it in their own file too (the handover README lists them under the session log).
- Skip `build` and `check`. At the end, hand over the review sheet, the method details review sheet
  and `project_values.tsv` for FAIRe mapper: apply mapping in the Shiny app or Galaxy.

## Data that should be generalised in the published record

If the researcher needs to publish less precise data than they hold (coarser coordinates for a
threatened species, say), FAIRe has project terms to say so: **dataGeneralizations** (what was made
less precise, and how) and **informationWithheld** (what exists but is not shared). Record what they
tell you with `set`, and make the change itself in a copy of the table with `table`, with a reason.
Do not decide on generalisation for them.
