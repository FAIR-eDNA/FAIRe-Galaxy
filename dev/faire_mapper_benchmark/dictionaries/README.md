# Data dictionaries for two benchmark tables

`bench_terse.dictionary.csv` and `heldout_lab_b.dictionary.csv` describe every column of the
benchmark tables `data/bench_terse.csv` and `data/heldout_lab_b.csv`, as a lab member might write
them for a Dryad deposit. They were written on 4 November 2026 by a stand-in (Claude Sonnet, run as a
separate agent) that saw only each table's headers and first six rows, was told to use ordinary
words rather than metadata standard terms, and did not see the answer keys or the mapper.

Run, from the top of the repository:

```bash
python tools/faire_mapper/faire_mapper.py map dev/faire_mapper_benchmark/data/bench_terse.csv \
    --checklist tools/faire_mapper/checklist/FAIRe_checklist_v1.0.2.xlsx --assay_type metabarcoding \
    --sample_types Water --gold dev/faire_mapper_benchmark/data/bench_terse.gold.tsv \
    --dictionary dev/faire_mapper_benchmark/dictionaries/bench_terse.dictionary.csv -o OUTDIR
```

Results (first choice right, of 70 columns with a FAIRe term): terse headers 81% without the
dictionary and 91% with it; the held-out university lab table 90% and 94%. See
`tools/faire_mapper/README.md`, "With a data dictionary".
