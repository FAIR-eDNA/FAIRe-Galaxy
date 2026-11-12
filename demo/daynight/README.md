# Day-night demonstration set

A small copy of the files of the day-night eDNA study of West et al. (2024), for demonstrating and
testing the FAIRe tools. It has the authors' files, with the same names and layouts, but only the
150 sequences of each assay with the most reads. It is 0.25 MB, against about 30 MB for the files
it is cut from (and 13 GB of reads), and the whole trial (`dev/faire_mapper_daynight/run.sh`) runs
on it in under half a minute.

**This is not data for ecological analysis.** Numbers of taxa, totals and proportions differ from
the full data. Use the published data for any analysis.

## Source and licence

West K, Jones T, Denis-Roy L, Johnson O, Clausius E, Edgar G, Deagle B (2024). Continual eDNA
detectability amidst diel reef species fluctuations on diver transects. v1. CSIRO Data Collection,
[doi:10.25919/pzsq-kv47](https://doi.org/10.25919/pzsq-kv47). Licensed under
[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).

**These files are under CC BY-NC 4.0, not under the MIT licence of this repository's code.** They
may be shared and adapted for non-commercial purposes, with credit to the authors as above.

`methods.txt` holds sections 2.1 to 2.3 of the paper: West KM, Jones TR, Denis-Roy L, Johnson OJ,
Clausius E, Edgar G, Deagle B (2024). Continual day-night eDNA detectability amidst diel reef
species fluctuations on diver transects. *Environmental DNA* 6: e70018,
[doi:10.1002/edn3.70018](https://doi.org/10.1002/edn3.70018), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

**Changes made** (as both licences ask): the two LCA outputs keep every sample column but only the
150 sequences of each assay with the most reads, and the two FASTA files only those sequences;
`methods.txt` is the paper's text from the PDF, without the publisher's download notes. The sample
sheet and the fastq ReadMe are as published. `dev/faire_mapper_daynight/make_demo.py` makes the
set from the full files, so the cut can be checked and repeated.

## Files

| File | What it holds |
|---|---|
| `Day_night_Tasmania_sample_data.xlsx` | The sample sheet as published: 126 rows (120 samples and 6 filtration controls), with the time of collection in its own column and notes in three columns |
| `Day_night_16S_LCA_output.txt`, `Day_night_COI_LCA_output.txt` | eDNAFlow's LCA output for each assay: domain to species, the OTU column, then reads per sample (122 and 117 samples) |
| `Day_night_16S_ASV.fasta`, `Day_night_COI_ASV.fasta` | The sequences of those ASVs |
| `eDNA_fastq_READ_ME.txt` | The ReadMe of the reads on the Data Access Portal: how the fastq files are named |
| `methods.txt` | The paper's methods, for *find primers* and the project values |
