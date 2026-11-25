# FAIRe sense check (prototype)

A one-page summary of a FAIRe workbook, to look over before the data go to a repository. It draws
the data in a few small pictures and lists the things that look wrong, so that a large mistake
shows at a glance: samples plotted on land, a date in the future, reads in a negative control, a
Cq value above the number of cycles run. It does not replace the review of the workbook or
FAIRe-fier, which checks each value against the checklist.

```
python dev/faire_sense_check/faire_sense_check.py WORKBOOK.xlsx -o sense_check.html --flags flags.tsv
```

It needs pandas, numpy and openpyxl, as the other tools do. The page is a single HTML file with no
web requests, so it opens offline and can be attached or archived. It follows the reader's light or
dark setting.

**Finding the samples behind a mark.** Hovering over a mark shows what it is: a dot on the map lists
its samples with their rows in sampleMetadata; a column of reads gives the sample, its reads, its
row in sampleMetadata and its column in the OTU table; a qPCR column lists its reactions; a taxon
bar lists the taxa with the most reads. Clicking a mark opens the table under the chart and
highlights its rows, so the samples can be found in the workbook. Row numbers and column letters
are those of the workbook's sheets. This uses one small script in the page; where scripts are
removed, as Galaxy may do, the browser's own tooltips show the same text, more slowly.

## What it shows

| Panel | What it shows | Flags it raises |
|---|---|---|
| What to look at | The flags, most serious first | |
| Where the samples were taken | Map of the positions, samples and controls (for qPCR, detected and not detected), with a small locator map for small areas | Coordinates missing, out of range, at 0, 0 or apparently swapped; samples described as marine that plot more than 10 km inland, or land and freshwater samples more than 10 km out to sea (problem past 25 km) |
| When the samples were taken | Samples per day, month or year | Dates in the future or before 1970; samples with no date; samples dated by a period |
| Samples and controls | Samples, positions and controls by type, samples per position | No controls; no negative controls; a few positions with one sample where most have more |
| Measured values | Each numeric FAIRe term of the sample sheet, lowest, median and highest, with a strip of the samples | Values that cannot be right (negative depth, volume of zero) or are unusual (temperature above 45 °C, salinity above 45) |
| Links between the sheets | Sample names across sampleMetadata, the OTU tables, experimentRunMetadata and ampData | Columns or libraries for samples not in the sample sheet; samples with no reads; libraries with no reads column or no reads file names |
| Reads per sample | One column per sample, then the controls, with the median | Samples with no reads, or under a tenth of the median |
| Controls with reads | Each control with reads, its type and its main taxa | Controls with reads, and taxa found in controls but in no sample |
| What was detected | Reads by class (or phylum), and the share of reads named at each rank | Under half of the reads in the assay's target group (targetTaxonomicAssay); reads of people or domestic animals |
| qPCR | Cq values per cycle for samples, negative and positive controls, with the number of cycles run | Cq above the cycles run; negative controls that amplified; positive controls that did not |
| What GBIF or OBIS would receive | Records, records with a sequence, taxon names, control columns left out | |
| How complete | Terms with a value, by sheet and requirement level | |

Three levels: **Problem** (cannot be right), **Check** (worth a look; may be fine) and **Note**.
The thresholds are in the script, near the top or in the panel that uses them.

The coastline is Natural Earth's 1:50 million land (public domain), cut to 0.01 degrees and gzipped
to 258 KB (`data/ne_50m_land.json.gz`, made by `make_coastline.py`). At that scale bays, estuaries
and small islands are rough, so the map shows positions near the coast as they are and flags only
those more than 10 km on the wrong side.

## The four demonstration sets

`run_demos.sh OUTDIR` builds the workbooks with their pipelines and runs the sense check on each.
What it found (25 November 2026):

| Set | Problems | Checks | What stood out |
|---|---|---|---|
| Day/night (`demo/daynight`, 150 ASVs per assay) | 0 | 3 | COI: 28% of reads in the target group (Metazoa); 20,000 reads of *Homo sapiens*; three samples with no COI reads in the cut-down set. The PCR blank has a library but no reads column |
| SEA-MES (Fish16S) | 0 | 2 | All 7 field negatives in the curated table have fish reads, up to 146,000 (mostly one taxon each); one sample with no reads; 12 libraries with no reads column in the curated table |
| Khapra beetle (qPCR) | 2 | 5 | Cq values above the cycles run in both ViiA 7 assays; negative controls amplified in all four assays; positive controls 1582 and 1589 not detected by OlsonViiA7 |
| Eelgrass (with sequences) | 0 | 2 | The North River field control (NOR-C) has 84 reads of *Polydora cornuta*; one 2019 sample with no reads; no reads file names |

The day/night workbook made with the AI assistant skill from the full published files gives the
same picture, and adds a note that its 239 libraries have no reads file names.

The sense check also showed that the SEA-MES pipeline's project values still put the −80 °C storage
of the filters in samp_store_temp; they are corrected here, as they were for the Shiny app's copy.

`test_sense_check.py` makes small workbooks with one of each problem, a qPCR one and a clean one,
and checks the flags.

## In Galaxy, the Shiny app and the skill

The script is meant to be shared by all three, as the other tools are:

- **Galaxy:** a tool with the page as an HTML dataset and the flags as a tabular one. Galaxy cleans
  HTML outputs unless an administrator allows the tool, which removes the page's styles; the charts
  are plain SVG, so they still show, and the tool can be added to the allow list.
- **Shiny app:** a step after FAIRe-fier that shows the same page.
- **AI assistant skill:** the page in the handover zip, with the assistant going through the flags
  table one item at a time.

## Not yet done

- Checking the country in geo_loc_name against the coordinates (needs country outlines).
- Flagging records of threatened species or biosecurity detections at exact coordinates (needs the
  lists, which vary by country and state).
- Checking names against GBIF or WoRMS, and marine or freshwater taxa against the environment.
- A finer coastline, if the 1:50 million one gives false flags in practice.
