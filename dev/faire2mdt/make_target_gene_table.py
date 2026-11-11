"""Make tools/faire2mdt/mdt_target_gene.tsv: FAIRe target_gene values and the GBIF target_gene
vocabulary term that GBIF's Metabarcoding Data Toolkit (MDT) stores for each.

MDT matches a target_gene value to the GBIF vocabulary by term name, English label or alternative
label, ignoring case (util/targetGeneVocabulary.js, matchConcept). This script applies the same
rule to the FAIRe checklist's target_gene options, using MDT's bundled copy of the vocabulary
(enum/targetGeneFallback.js, captured 2026-10-01). FAIRe's names for five rRNA genes match no term;
for those the term is set here by gene and compartment.

Usage: python -I make_target_gene_table.py targetGeneFallback.js FAIRe_checklist.xlsx OUTPUT.tsv
"""
import csv
import json
import sys

import pandas as pd

ADDED = {  # FAIRe value -> GBIF term, where MDT's rule finds no match
    '12S rRNA (SSU mitochondria)': 'SSU_rRNA_12S_mitochondrial',
    '16S rRNA (LSU mitochondria)': 'LSU_rRNA_16S_mitochondrial',
    '23S rRNA (LSU prokaryote)': 'LSU_rRNA_23S_prokaryotic',
    '18S rRNA (SSU eukaryote)': 'SSU_rRNA_18S_eukaryotic',
    '28S rRNA (LSU eukaryote)': 'LSU_rRNA_28S_eukaryotic',
}
EXTRA = [  # FAIRe ITS with target_subfragment ITS1 or ITS2
    ('ITS', 'ITS1', 'ITS1'),
    ('ITS', 'ITS2', 'ITS2'),
]

src = open(sys.argv[1], encoding='utf-8').read()
concepts = json.loads(src[src.index('export default') + len('export default'):].strip().rstrip(';'))
by_name = {c['name']: c for c in concepts}
checklist = pd.read_excel(sys.argv[2], sheet_name='checklist', dtype=str)
options = checklist.loc[checklist.term_name == 'target_gene', 'controlled_vocabulary_options'].iloc[0]
faire = [v.strip() for v in options.split('|') if v.strip() and not v.strip().startswith('other')]


def mdt_match(value):
    n = value.strip().lower()
    for c in concepts:
        labels = [c['name'], c.get('label') or ''] + [str(x) for x in c.get('alternativeLabels') or []]
        if any(n == x.lower() for x in labels):
            return c['name']
    return None


rows = []
for v in faire:
    term = mdt_match(v)
    how = 'MDT matches it'
    if term is None:
        term, how = ADDED.get(v), 'set for this tool (MDT finds no match)'
    if term is None:
        sys.exit(f'no GBIF term for FAIRe value {v!r}')
    rows.append([v, '', term, by_name[term]['label'], how])
for v, sub, term in EXTRA:
    rows.append([v, sub, term, by_name[term]['label'], 'set for this tool (from target_subfragment)'])

with open(sys.argv[3], 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    w.writerow(['faire_target_gene', 'target_subfragment', 'gbif_target_gene', 'gbif_label', 'how'])
    w.writerows(rows)
print(f'{len(rows)} rows; {sum(r[4].startswith("set") for r in rows)} set for this tool')
