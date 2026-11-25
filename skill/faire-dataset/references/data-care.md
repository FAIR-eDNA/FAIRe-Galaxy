# Care with the data

SKILL.md Step 1 gives the notice itself, to be shown in full at the start of every session. This
file has the background to it, and what to do when the researcher chooses to share less.

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
