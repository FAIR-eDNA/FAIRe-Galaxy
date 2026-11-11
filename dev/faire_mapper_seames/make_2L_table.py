"""The sample table for the 18S data, from the sample details below the counts of the 18S ASV table.

File 7 has 37 rows below its counts, one for each sample detail (Sample ID, Voyage, Depth (m),
Latitude ...), with one column for each sample. This writes them the usual way round: one row per
sample, one column per detail, with the lab's own names. It covers every sample in the 18S table:
the 190 2 L samples (S001 ...) and the 12 10 L samples sequenced for 18S (M097 ...). Details empty
for every sample are left out.

It then adds the columns a person would add for the details that differ between the two kinds of
sample. The ReadMe says sample names start with S for 2 L samples, collected on 0.22 µm filters,
and M for 10 L samples, collected on 0.45 µm filters. The methods (methods_consolidated.txt,
sections 2 and 4) give the filter, its processing and the extraction for each. The 12 10 L samples
are taken to have the 10 L extraction (section 2.2), as they come from the same extracts as the 16S
data. The membrane of the Sterivex GP filters is not stated, so Filter material is empty for them.
Nothing else is changed.

Usage: python make_2L_table.py 7_SEA-MES_2025_EUK_18S_for_DAT.csv.gz OUT.csv
"""
import csv
import gzip
import sys

src, out = sys.argv[1], sys.argv[2]
with gzip.open(src, 'rt', encoding='utf-8-sig', newline='') as f:
    rows = list(csv.reader(f))
header = rows[0]
end = header.index('Total reads')          # the sample columns run from the second column to here
start = next(i for i in range(len(rows) - 1, 0, -1) if rows[i] and rows[i][0] == 'Sample')
details = [r for r in rows[start:] if r and r[0].strip()]
names = [r[0].strip() for r in details]
samples = list(zip(*[r[1:end] for r in details]))
keep = [j for j in range(len(names)) if any(s[j].strip() for s in samples)]
name = names.index('Sample No.')
added = ['Volume filtered', 'Filter pore size (µm)', 'Filter name', 'Filter material', 'Sample processing',
         'Extraction protocol', 'Extraction kit']
by_prefix = {   # from the ReadMe and the methods
    'S': ('2 L', '0.22', 'Sterivex GP', '',
          'Held at 4 °C and filtered within 12 hours onto 0.22 µm Sterivex GP filters with a Masterflex L/S '
          'console pump; filters stored at -80 °C.',
          'Australian Microbiome protocol meth_3.1.9', 'DNeasy PowerWater filter columns (QIAGEN)'),
    'M': ('10 L', '0.45', '47 mm mixed cellulose ester membrane (MerckMillipore)', 'cellulose ester',
          'Held at 4 °C and filtered within 12 hours through 47 mm, 0.45 µm mixed cellulose ester membranes '
          'with a peristaltic pump; filters stored at -80 °C.',
          'West et al. (2024), with modifications', 'DNeasy Blood and Tissue Kit (QIAGEN)'),
}
with open(out, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow([names[j] for j in keep] + added)
    for s in samples:
        w.writerow([s[j].strip() for j in keep] + list(by_prefix.get(s[name].strip()[:1], ('',) * len(added))))
left_out = [names[j] for j in range(len(names)) if j not in keep]
print(f'{len(samples)} samples and {len(keep)} details from rows {start + 1} to {len(rows)} of the 18S table'
      + (f"; empty for every sample: {', '.join(left_out)}" if left_out else ''))
