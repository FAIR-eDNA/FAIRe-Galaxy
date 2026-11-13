# FAIRe tools: a Shiny app

This app brings together the FAIRe eDNA metadata tools in one place, so that a person can make,
check and convert a FAIRe workbook on their own computer, in a web browser. It is a companion to the
FAIRe tools in the Galaxy Australia eDNA Lab. Galaxy remains the place for full analyses, with many
more tools and a record of every step; the app suits someone who wants to format one dataset quickly,
or to try the tools before using them in Galaxy.

The app runs the same scripts as the Galaxy wrappers in `../tools`, with the same arguments, so the two
give the same results. Each tool's command line in `R/tools.R` follows the `<command>` block of its
Galaxy XML file. Run through the app, the SEA-MES demonstration gives a workbook identical, sheet for
sheet, to the one the same steps give from the command line (`dev/faire_mapper_seames/run.sh`), given
the same files.

This version is a demonstration that runs on one computer. It is written so that it can later be
hosted on a server (see *Hosting later*, below). It was first built in a private repository and moved
here, beside the tools it runs, on 13 November 2026 (version 0.2.0).

## What it covers

| Step | Tools |
|---|---|
| 1. Make a workbook | FAIRe-ator (a blank template); the FAIRe mapper (identify your files, profile and propose a mapping, review it, find primers, values for the whole project, write the workbook), with the optional language model step |
| 2. Check | FAIRe-fier |
| 3. Convert | FAIRe2NCBI (BioSample and SRA), FAIRe2ENA (samples, and experiments and runs), FAIRe2MDT, edna2obis (match taxa and build the Darwin Core archive) and FAIRe2QIIME |

The review screen is the review sheet that propose mapping writes, row for row: each column heading
of the sample table (an input term), with some of its values, the proposed term and its score, the
mapper's call and its reasoning. For each row the person chooses Accept, Reject or Change, and a
replacement term for Change, from a list with the best candidates for that column first. Saving writes
the decisions into a copy of the review sheet, which apply mapping reads, as it does in Galaxy. The
sheet can also be downloaded, filled in with Excel (sorted or filtered as the person likes) and added
back with the upload button: the decisions go on screen and are saved, matched to their columns by
input term. Either way, the mapper's conversions, such as reading Y and N as *negative control* and
*sample*, are kept for the matches a person accepts.

## Downloading and running it

The app needs R and Python on your computer, and a copy of this whole repository: the app is in the
`shiny` folder and runs the tools in the `tools` folder beside it, so keep the two folders together.
Setting it up takes about 15 minutes the first time, most of it downloading packages. After that, it
starts in a few seconds.

### 1. Install R and Python, if you don't have them

- **R**, version 4.1 or later, from [cloud.r-project.org](https://cloud.r-project.org). RStudio
  ([posit.co/download/rstudio-desktop](https://posit.co/download/rstudio-desktop/)) is optional but
  makes the next steps easier.
- **Python**, version 3.10 to 3.13, from [python.org/downloads](https://www.python.org/downloads/).
  Version 3.14 is too new for some of the tools' packages. On Windows, tick *Add python.exe to PATH*
  on the first screen of the installer. On a Mac, the installer from python.org is the simplest
  choice.

At CSIRO and other organisations, both may also be available from the software centre.

### 2. Download the repository

The app is in the public repository [FAIR-eDNA/FAIRe-Galaxy](https://github.com/FAIR-eDNA/FAIRe-Galaxy),
so no GitHub account is needed.

- **Without git:** open [the repository](https://github.com/FAIR-eDNA/FAIRe-Galaxy), press the green
  *Code* button, choose *Download ZIP*, and unzip the file somewhere convenient, such as your
  Documents folder. The folder it makes is called `FAIRe-Galaxy-main`.
- **With git:** `git clone https://github.com/FAIR-eDNA/FAIRe-Galaxy.git`

### 3. Set it up (once)

This installs the R packages the app uses, makes a separate Python environment for the tools (in a
folder called `.venv` inside `shiny`, so it does not change any other Python on your computer), and
installs the tools' Python packages into it, at the versions the Galaxy tools use. It ends with a
check that everything is in place.

- **In RStudio:** open `shiny/setup.R` from the folder you downloaded. Choose *Session > Set Working
  Directory > To Source File Location*, then press *Source* (top right of the script).
- **In a terminal** (Command Prompt or PowerShell on Windows, Terminal on a Mac): go to the `shiny`
  folder, for example `cd Documents/FAIRe-Galaxy-main/shiny`, and run
  `Rscript setup.R`. On Windows, if `Rscript` is not found, give its full path, such as
  `"C:\Program Files\R\R-4.5.1\bin\Rscript.exe" setup.R`.

If the check at the end shows *NO* against Python, setup.R could not find a suitable Python. Install
one as in step 1, or tell setup.R where it is by setting `FAIRE_PYTHON_BASE` to its full path, and
run setup.R again.

### 4. Start the app

- **In RStudio:** open `shiny/app.R` and press *Run App* (top right of the script). To have it open
  in your web browser, choose *Run External* from the small arrow beside *Run App*.
- **In a terminal:** in the `shiny` folder, run `Rscript run_app.R`. The app opens in your web
  browser. If it does not, go to http://127.0.0.1:7788.

The app runs only on your computer: nothing you add is sent anywhere, except the column details you
choose to send to a language model in the optional review step, and the taxon names edna2obis looks
up in WoRMS or GBIF. To stop the app, close the browser tab and press *Stop* in RStudio, or Ctrl+C in
the terminal. Everything it wrote in that session is deleted, so download what you want to keep from
the *Outputs* page first. To use it again later, repeat step 4 only.

### Getting a newer version

Download the repository again (step 2) and run setup.R again (step 3), which only installs what has
changed. With git, `git pull` in the repository folder does the same as downloading.

### Settings

Three settings can be given as environment variables: `FAIRE_TOOLS_DIR` to use a copy of the tools
somewhere other than `../tools`, `FAIRE_PYTHON` to use a Python other than the one in `.venv`, and
`FAIRE_PORT` for another port than 7788 (useful if something else on your computer uses it).

## Trying it with the demonstration data

The Start page has a button that loads a small cut of CSIRO's SEA-MES eDNA data record (Deagle et al.
2025; see `demo/README.md`). It fills in the forms with the values the trial used, but each tool still
has to be run by pressing its button, and the review is done by hand, as a person would do it. The
Start page lists the steps. edna2obis looks the names up in WoRMS or GBIF, so it needs internet
access, and its two steps were not run on the demonstration in testing; the Darwin Core build was
tested through the app's code on edna2obis's own test data, with its stand-in mapping table.

What you should see: the mapping accepts 11 of the table's 23 columns, sends 6 for review and finds
no term for 6. *Fill in the authors' answers* gives the decisions from the trial
(`dev/faire_mapper_seames/reviewer_decisions.tsv`). Once the review is saved, the workbook has 13
samples and 58 FAIRe terms, plus 9 columns kept as their own terms, with the 16S ASV table as otuRaw
and taxaRaw and the 48 curated fish taxa as otuFinal and taxaFinal. FAIRe-fier passes both sheets, with
a warning for each of the 9 columns kept as their own terms, which the checklist does not list.
FAIRe2NCBI writes 13 BioSamples and 13 SRA rows, and FAIRe2ENA 13 samples and 13 experiments and runs.
(Tested 13 November 2026, up to the workbook through the app and the conversions from the command
line with the app's settings. On 10 November, version 0.1.0 also ran FAIRe2MDT, which writes a
workbook for Fish16S, and FAIRe2QIIME, which writes a metadata file and a manifest.)

## How it works

- `app.R` holds the pages' behaviour; `R/ui.R` the pages themselves; `R/tools.R` one function for each
  Galaxy tool, building its command line; `R/runner.R` finds Python, R and the tools and runs a
  command; `R/helpers.R` reads the review sheet and the other files the tools exchange; and
  `python/fill_review_sheet.py` writes the decisions from the review screen into a copy of the review
  sheet, leaving the rest of it (the drop-downs, the shading and the other sheets) as it was.
- The files a person adds, and everything the tools write, go into a folder for the session in R's
  temporary folder. Each run has its own folder, with its inputs, outputs and a log of the exact
  command (`run_log.txt`), so any file can be traced to the run that wrote it. The *Outputs* page
  lists the runs and downloads the lot as a zip. The folder is deleted when the session ends.
- The workbook written by the mapper becomes the *workbook in use*, which the Check and Convert pages
  take by default. A workbook from the person's files can be chosen instead.
- The language model step is optional, as in Galaxy. The key is passed to the tool through its
  environment and is never written to a file, and the model's answers are only suggestions that a
  person confirms.

## Hosting later

The app is written to move to a server with little change. Shiny Server or Posit Connect can run the
folder as it is, with the tools beside it and the Python environment made by `setup.R`. Points to
settle then:

- **Uploaded data.** Each session's files are kept in their own folder, reached only through that
  session's random link, and deleted when the session ends. A hosted version should say this on the
  Start page, set a limit on upload size (500 MB now, in `app.R`), and clear old session folders if a
  session ends without notice.
- **Several people at once.** Tools run one after another within a session, and a long run holds that
  session until it finishes. Shiny Server runs each person in their own session, but heavy use would
  need more processes, or runs moved to a background queue.
- **The language model.** A hosted version would hold the key on the server (as Galaxy's
  `FAIRE_MAPPER_SERVER` does), with a limit on use, and no longer ask people for theirs.
- **Internet access.** edna2obis needs to reach WoRMS and GBIF from the server.

## Not yet in the app

- The mapper's model script for methods text (`faire_mapper_methods.py`) is not on the forms.
- edna2obis's custom eMoF template and EML from YAML files, and the less used advanced settings of
  the tools, are left out; the Galaxy tools have them.
- FAIReSheets (the Google Sheets template maker) is not included, as it works inside Google Sheets.

## Credits

The app was written by Oliver Berry (CSIRO), with Claude (Anthropic), to sit beside the FAIRe Galaxy
tools. The tools it runs belong to their own developers; each tool folder in `../tools` gives its
upstream repository and licence. The FAIRe checklist is described in Takahashi et al. (2025)
*Environmental DNA* 7: e70100.
