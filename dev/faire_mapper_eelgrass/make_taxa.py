"""The taxon table for FAIRe to Darwin Core, from the eelgrass study's species table
(Final_ASVTable_withTaxonomy_Filtered.csv): each species with its phylum and class as the authors give
them, and kingdom Animalia, as all 138 are metazoan invertebrates (the Dryad abstract). Names are as
the workbook gives them: with a space for the underscore, and to the genus for a name such as
'Clitellio sp. BOLD:AAG8543' or 'Boonea cf. bisuturalis' (as apply mapping names them).
Usage: python make_taxa.py TABLE [TABLE ...] OUT.tsv   (the species table, or the per-ASV tables)
"""

import re
import sys

import pandas as pd

UNNAMED = re.compile(r'^(\S+)\s+(sp|spp|sp\d+|cf|aff|nr)\.?\s*\d*(\s.*)?$', re.I)

*srcs, out = sys.argv[1:]
d = pd.concat([pd.read_csv(x, usecols=['Phylum', 'Class', 'Species'], dtype=str) for x in srcs])
names = d['Species'].str.strip().str.replace('_', ' ', regex=False).str.replace(r'\s+', ' ', regex=True)
genus_only = names.str.match(UNNAMED)
names = names.where(~genus_only, names.str.split(' ').str[0])
t = pd.DataFrame({'name': names, 'scientificName': names, 'taxonRank': ['genus' if g else 'species' for g in genus_only],
                  'kingdom': 'Animalia', 'phylum': d['Phylum'].str.strip(), 'class': d['Class'].str.strip(),
                  'genus': names.str.split(' ').str[0]}).drop_duplicates('name')
t.to_csv(out, sep='\t', index=False)
print(f'{len(t)} names, {t["phylum"].nunique()} phyla -> {out}')
