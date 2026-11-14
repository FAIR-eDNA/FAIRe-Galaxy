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
here, beside the tools it runs, on 13 November 2026 (version 0.2.0). Version 0.3.0 has the changes
from the FAIRe team's first trial of it, and version 0.4.0 those from the second (14 November 2026).

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

A few things that help along the way:

- **Your files** (on the left) lists every file you add, with what *a. Your files* found it to be.
  The eye beside a file shows what is in it: the first rows of a table as they are in the file, with
  their row numbers (so you can see which row holds the column names), the first rows of each sheet
  of a workbook, the first lines of a FASTA file, or the text of a methods file or PDF as the tools
  read it. The cross removes a file; *Remove all files* starts again.
- **a. Your files** says what each file seems to be and where it goes in the app. It recognises
  FASTA files and PDFs by their content, whatever they are called. If it gets one wrong, choose the
  right kind in its table: the app then offers the file in the right places. *Look inside* shows the
  file, to help you decide.
- **Methods** can be text or a PDF. *d. Primers and project values* reads them for primers, and
  lists the mandatory project terms still to give; the other values for the whole study, such as
  PCR conditions and the sequencing platform, come from you, with the methods open beside you. A PDF
  of scanned pages has no text to read: save it as text first.
- **Primers** are checked against a reference table of about 550 published primer pairs, most from
  Takahashi et al. (2023) and Wilderlab's assays. This keeps primer names as they are in the
  literature and catches typos in sequences. If your primers are not in it, add your own table.
  The step says how to choose the pair you used for each assay, and which assay name to give it.
- **Other method details**: under the primers, *Find method details* reads the same methods for the
  filters, extraction kit, PCR conditions, sequencing kit, software, settings and reference databases,
  and lists each value it finds with the sentence it came from. Tick the ones to keep (correcting any
  that are nearly right) and add them to the values for the whole project. Its review sheet, which also
  lists the method terms not found, can be downloaded, filled in with Excel and loaded back on the right.
- **Adding a value** offers the FAIRe terms for one part of the checklist at a time, PCR and primers
  first, then library preparation and sequencing, bioinformatics and so on, or all of them.
- **A question mark** beside a label explains the term (*data dictionary*, *assay*, *raw* and
  *final* and so on) when the pointer rests on it, or when you move to it with the Tab key.
- **Optional fields**, such as the data dictionary, can be set back to *None* after choosing a file.

## Downloading and running it

The app needs R and Python on your computer, and a copy of this whole repository: the app is in the
`shiny` folder and runs the tools in the `tools` folder beside it, so keep the two folders together.
Setting it up takes about 15 minutes the first time, most of it downloading packages. After that, it
starts in a few seconds.

The steps below are written for Windows, with the differences for a Mac in brackets.

### Where to type the commands

Some steps ask you to type a command. You can do this without leaving RStudio:

- **RStudio's Terminal tab**, next to the Console tab at the bottom left (if it isn't there, choose
  *Tools > Terminal > New Terminal*). Type the commands as they are written here.
- **The R console**, by wrapping a command in `system()`, for example `system("py --list")`.

Windows' own PowerShell or Command Prompt (search for them in the Start menu), or Terminal on a Mac,
work the same way. Lines that start `Sys.setenv(` are R, and go in the R console.

### 1. Check for R and Python, and install what's missing

- **R**, version 4.1 or later, from [cloud.r-project.org](https://cloud.r-project.org), and
  RStudio from [posit.co/download/rstudio-desktop](https://posit.co/download/rstudio-desktop/).
  RStudio is optional, but makes the next steps easier.
- **Python**, version 3.10 to 3.13. Version 3.14 is too new for some of the tools' packages. To see
  whether you have it, run:

  ```
  py --list
  ```

  It lists the versions installed. (On a Mac, run `python3 --version`.)

  If it says `'py' is not recognized`, check for Python under its usual name:

  ```
  python --version
  where.exe python
  ```

  If `python --version` gives 3.10 to 3.13, and `where.exe` gives a path that is not under
  `...\AppData\Local\Microsoft\WindowsApps\`, you have a suitable Python: go on to step 2. If it says
  *Python was not found; run without arguments to install from the Microsoft Store*, or the only
  path is under `WindowsApps`, there is no Python yet: that path is Windows' link to the Microsoft
  Store.

**Installing Python.** Go to [python.org/downloads/windows](https://www.python.org/downloads/windows/)
and download the *Windows installer (64-bit)* of the latest Python 3.13. Use python.org's installer:
the Microsoft Store's Python doesn't work well for the separate Python environment setup.R makes. On
the installer's first screen, tick **Add python.exe to PATH**, then choose
**Install Now**. It installs for your account only, so it shouldn't need administrator rights, and
it adds the `py` launcher. (On a Mac, use the macOS installer from
[python.org/downloads/macos](https://www.python.org/downloads/macos/).)

Then close and reopen your terminal and run `py --list` again: it should show 3.13. **Close and
reopen RStudio too**, as it only reads the list of programs on your computer when it starts.

At CSIRO and other organisations, R, RStudio and Python may also be in the Company Portal or software
centre, which is the place to look if an installer is blocked.

### 2. Download the repository and unpack it

The app is in the public repository [FAIR-eDNA/FAIRe-Galaxy](https://github.com/FAIR-eDNA/FAIRe-Galaxy),
so no GitHub account is needed.

- **Without git:** open [the repository](https://github.com/FAIR-eDNA/FAIRe-Galaxy), press the green
  *Code* button, choose *Download ZIP*, and unzip the file somewhere convenient, such as
  `Documents\R_projects`. The folder it makes is called `FAIRe-Galaxy-main`. You can rename it.
- **With git:** `git clone https://github.com/FAIR-eDNA/FAIRe-Galaxy.git`

Unpack the whole repository, not only the `shiny` folder. Afterwards, `shiny` and `tools` sit side
by side:

```
Documents\R_projects\FAIRe-Galaxy-main\
    shiny\      the app
    tools\      the FAIRe tools the app runs
    demo\  docs\  workflows\ ...
```

If you have an older copy of the app, such as one downloaded from the private repository it was first
built in, rename or delete that folder, and set up the new one as below. Its Python environment
belongs to the old folder.

### 3. Set it up (once)

- **In RStudio:** open `shiny/setup.R` from the folder you unpacked. Choose *Session > Set Working
  Directory > To Source File Location*, then press *Source* (top right of the script).
- **In a terminal:** go to the `shiny` folder, for example
  `cd Documents\R_projects\FAIRe-Galaxy-main\shiny`, and run `Rscript setup.R`. If `Rscript` is not
  found, give its full path, such as `"C:\Program Files\R\R-4.5.1\bin\Rscript.exe" setup.R`.

setup.R does four things:

1. installs the R packages the app uses;
2. finds a Python 3.10 to 3.13 (the `py` launcher first, then `python`);
3. makes a separate Python environment for the tools, in a folder called `.venv` inside `shiny`, so
   it doesn't change any other Python on your computer;
4. installs the tools' Python packages into it, at the versions the Galaxy tools use.

It ends with a check table. Every row should say *yes*.

**How the app uses Python.** There is nothing to set up in R for Python (no reticulate). The app runs
each tool as a separate program, as Galaxy does, using the Python in `shiny/.venv`. That is why
setup.R makes it, and why a new copy of the app needs setup.R run once.

### 4. Start the app

- **In RStudio:** open `shiny/app.R`. Choose *Run External* from the small arrow beside *Run App*,
  then press *Run App*. The app opens in your web browser.
- **In a terminal:** in the `shiny` folder, run `Rscript run_app.R`. The app opens in your web
  browser. If it does not, go to http://127.0.0.1:7788.

The app runs only on your computer: nothing you add is sent anywhere, except the column details you
choose to send to a language model in the optional review step, and the taxon names edna2obis looks
up in WoRMS or GBIF. To stop the app, close the browser tab and press *Stop* in RStudio, or Ctrl+C in
the terminal. Everything it wrote in that session is deleted, so download what you want to keep from
the *Outputs* page first. To use it again later, repeat step 4 only.

### If something goes wrong

- **The check says NO against Python.** setup.R found no Python 3.10 to 3.13. Install one (step 1),
  restart RStudio and run setup.R again. If Python is installed but still not found, tell setup.R
  where it is. Get its full path with

  ```
  py -3.13 -c "import sys; print(sys.executable)"
  ```

  then, in the R console, give that path with forward slashes, and run setup.R again:

  ```r
  Sys.setenv(FAIRE_PYTHON_BASE = "C:/Users/you/AppData/Local/Programs/Python/Python313/python.exe")
  ```

- **pip could not install the packages.** The messages above the check table say why. On a work
  network, a proxy can stop pip downloading packages; running setup.R from home, or off the VPN,
  usually gets round it.
- **A tool stops with a message that a package is missing.** Run setup.R again: it installs only
  what is missing.
- **Port 7788 is in use** (when starting with `Rscript run_app.R`). Start it on another port, for
  example `FAIRE_PORT=7790` before the command on a Mac, or `$env:FAIRE_PORT = "7790"` first in
  PowerShell. RStudio's *Run App* chooses a free port itself.

### Getting a newer version

Download the repository again (step 2) and run setup.R again (step 3), which only installs what has
changed. With git, `git pull` in the repository folder does the same as downloading.

### Settings

Three settings can be given as environment variables: `FAIRE_TOOLS_DIR` to use a copy of the tools
somewhere other than `../tools`, `FAIRE_PYTHON` to use a Python other than the one in `.venv`, and
`FAIRE_PORT` for another port than 7788 (useful if something else on your computer uses it).
`FAIRE_PYTHON_BASE` tells setup.R which Python to make `.venv` from.

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
