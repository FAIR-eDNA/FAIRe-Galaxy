"""The sample table for the 18S data, from the sample details below the counts of the 18S ASV table.

File 7 has 37 rows below its counts, one for each sample detail (Sample ID, Voyage, Depth (m),
Latitude ...), with one column for each sample. This writes them the usual way round: one row per
sample, one column per detail, with the lab's own names. It covers every sample in the 18S table:
the 190 2 L samples (S001 ...) and the 12 10 L samples sequenced for 18S (M097 ...). Details empty
for every sample are left out.

It then adds the columns a person would add for the details that differ between the two kinds of
sample. The ReadMe says sample names start with S for 2 L samples, collected on 0.22 µm filters,
and M for 10 L samples, collected on 0.45 µm filters. The methods (methods_consolidated.txt,
sections 2 and 4) give the filter, its processing and the extraction for each; the 2 L extraction
protocol, Australian Microbiome meth_3.1.9, is given as the link to its SOP. The 12 10 L samples
are taken to have the 10 L extraction (section 2.2), as they come from the same extracts as the 16S
data. The membrane of the Sterivex GP filters is not stated, so Filter material is empty for them.

Given the run report, it also adds a row for each control library sequenced with the 18S samples,
as a person following the guide would: the controls have reads at the archive but are not in the
18S table. Each 18S run (BOD14795 and BOD14856) had a no-template control (NTC), a mock community
(ATCC1010) and a soil sample. The SRA sheet titles all three "Pos. control"; a no-template control
is a PCR negative (O. Berry, 13 November 2026). Each row is named after its library, without _18s
(NTC-7C-1608411-BOD14795), and has only a Sample ID that says what it is and which run it was on
(no-template control, run BOD14795), so that its BioSample differs from the other run's, a Sample
type, a Negative control type and a Positive control type; the field samples have Sample type
"sample". Nothing else is changed.

Usage: python make_2L_table.py 7_SEA-MES_2025_EUK_18S_for_DAT.csv.gz OUT.csv [RUN_REPORT.tsv]
"""
import csv
import gzip
import sys

# The controls in the run report, by the start of their library name: sample type, negative control
# type, positive control type.
CONTROLS = {'NTC-': ('no-template control', 'negative control', 'PCR negative', ''),
            'ATCC1010-': ('mock community ATCC1010', 'positive control', '', 'PCR positive: mock community (ATCC1010)'),
            'Soil-': ('soil', 'positive control', '', 'PCR positive: soil')}

src, out = sys.argv[1], sys.argv[2]
report = sys.argv[3] if len(sys.argv) > 3 else None
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
          'https://research.csiro.au/ambsm/3-omics-sample-extraction-purification-and-quantification-procedures/'
          '3-1-dna-extraction-purification-procedures/meth_3-1-9-qiagen-dneasy-powerwater-sterivex-kit-modified-'
          'imos-nrs-acmon-and-voyages-csiro-hobart-genetics-laboratories',
          'DNeasy PowerWater filter columns (QIAGEN)'),
    'M': ('10 L', '0.45', '47 mm mixed cellulose ester membrane (MerckMillipore)', 'cellulose ester',
          'Held at 4 °C and filtered within 12 hours through 47 mm, 0.45 µm mixed cellulose ester membranes '
          'with a peristaltic pump; filters stored at -80 °C.',
          'West et al. (2024), with modifications', 'DNeasy Blood and Tissue Kit (QIAGEN)'),
}
controls = []
if report:
    with open(report, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            lib = r['library_name'].strip()
            kind = next((v for k, v in CONTROLS.items() if lib.startswith(k)), None)
            if kind and lib.lower().endswith('_18s'):
                controls.append((lib[:-4], kind))
controls.sort()
kinds = ['Sample type', 'Negative control type', 'Positive control type']
with open(out, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow([names[j] for j in keep] + added + (kinds if controls else []))
    for s in samples:
        w.writerow([s[j].strip() for j in keep] + list(by_prefix.get(s[name].strip()[:1], ('',) * len(added)))
                   + (['sample', '', ''] if controls else []))
    for lib, (what, *kind) in controls:
        label = f"{what}, run {lib.rsplit('-', 1)[-1]}"
        w.writerow([lib if names[j] == 'Sample No.' else label if names[j] == 'Sample ID' else '' for j in keep]
                   + [''] * len(added) + kind)
left_out = [names[j] for j in range(len(names)) if j not in keep]
print(f'{len(samples)} samples and {len(keep)} details from rows {start + 1} to {len(rows)} of the 18S table'
      + (f"; empty for every sample: {', '.join(left_out)}" if left_out else '')
      + (f"; {len(controls)} controls from the run report: {', '.join(c for c, _ in controls)}" if controls else ''))
