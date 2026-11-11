"""Compare the trial's submission sheets with what the authors submitted.

  biosample: our BioSample sheet against the authors' (file 1), field by field. With MIxS units on,
             FAIRe2NCBI adds units to numbers ("14.1" becomes "14.1 degree Celsius"); a field that
             differs only by that, or by an empty cell filled with a missing-value term, is counted
             as the same value with a unit added.
  sra:       our SRA sheet against ENA's run report: library_ID and library_name, the BioSample,
             and the two file names.

  sra_sheet: our SRA sheet against the SRA sheet the authors submitted (file 3, for 18S), field by
             field, for the libraries in both (library_ID compared without regard to case).

Usage: python compare.py biosample OURS.tsv AUTHORS.xlsx
       python compare.py sra OURS.tsv FILEREPORT.tsv
       python compare.py sra_sheet OURS.tsv AUTHORS_SRA.xlsx
"""
import re
import sys

import pandas as pd


MISSING = ('not applicable', 'missing', 'not collected', 'not provided')


def text(v):
    s = '' if v is None or (isinstance(v, float) and v != v) else str(v).strip()
    return '' if s == 'nan' else s


def biosample(ours_path, authors_path):
    ours = pd.read_csv(ours_path, sep='\t', dtype=str, keep_default_na=False, skiprows=11).set_index('*sample_name')
    theirs = pd.read_excel(authors_path, header=11, dtype=object).set_index('*sample_name')
    shared = [c for c in theirs.columns if c in ours.columns]
    same, unit, differ, notes = [], [], {}, []
    for c in shared:
        a = [text(v).replace(' 00:00:00', '') for v in theirs[c]]
        b = [text(v) for v in ours.loc[theirs.index, c]]
        if a == b:
            same.append(c)
        elif all(x == y or (x and re.fullmatch(re.escape(x) + r' [^\d].*', y)) or (not x and y in MISSING)
                 for x, y in zip(a, b)):
            unit.append(c)
            filled = sum(not x and y in MISSING for x, y in zip(a, b))
            if filled:
                notes.append(f'{c}: empty for {filled} samples in the authors\' sheet, {b[a.index("")]!r} in ours')
        else:
            bad = [(x, y) for x, y in zip(a, b) if x != y]
            differ[c] = (len(bad), bad[0])
    print(f'BioSample: {len(theirs)} samples, {len(shared)} fields in both sheets: {len(same)} identical, '
          f'{len(unit)} the same values with a unit added ({", ".join(unit)}), {len(differ)} different')
    for c, (n, ex) in differ.items():
        print(f'  {c}: {n} samples differ, e.g. {ex[0]!r} and {ex[1]!r}')
    for n in notes:
        print(f'  {n}')


def sra(ours_path, report_path):
    ours = pd.read_csv(ours_path, sep='\t', dtype=str, keep_default_na=False)
    rep = pd.read_csv(report_path, sep='\t', dtype=str, keep_default_na=False).set_index('library_name')
    rows = ours[ours.library_ID.isin(rep.index)]
    checks = {'BioSample': 0, 'filename': 0, 'filename2': 0, 'instrument_model': 0}
    for _, r in rows.iterrows():
        e = rep.loc[r.library_ID]
        files = [f.split('/')[-1] for f in e.fastq_ftp.split(';')]
        checks['BioSample'] += r.biosample_accession == e.sample_accession
        checks['filename'] += r.filename in files and r.filename.endswith('_1.fastq.gz')
        checks['filename2'] += r.filename2 in files and r.filename2.endswith('_2.fastq.gz')
        checks['instrument_model'] += r.instrument_model == e.instrument_model
    print(f'SRA: {len(ours)} rows, {len(rows)} with a library_ID that is a library_name in the run report; '
          + ', '.join(f'{k} matches for {v}' for k, v in checks.items()))


def sra_sheet(ours_path, authors_path):
    ours = pd.read_csv(ours_path, sep='\t', dtype=str, keep_default_na=False)
    theirs = pd.read_excel(authors_path, sheet_name='SRA_data', dtype=object)
    theirs.index = [text(v).lower() for v in theirs.library_ID]
    rows = ours[ours.library_ID.str.lower().isin(theirs.index)]
    fields = [c for c in ('title', 'library_strategy', 'library_source', 'library_selection', 'library_layout',
                          'platform', 'instrument_model', 'design_description', 'filetype', 'filename', 'filename2')
              if c in ours.columns and c in theirs.columns]
    print(f'SRA sheet: {len(ours)} rows, {len(rows)} with a library_ID in the authors\' sheet '
          f'({len(theirs)} libraries)')
    for c in fields:
        pairs = [(text(theirs.at[r.library_ID.lower(), c]), text(r[c])) for _, r in rows.iterrows()]
        same = sum(a.lower() == b.lower() for a, b in pairs)
        diff = next(((a, b) for a, b in pairs if a.lower() != b.lower()), None)
        print(f'  {c}: the same for {same}' + (f', e.g. {diff[0]!r} and {diff[1]!r}' if diff else ''))


if __name__ == '__main__':
    {'biosample': biosample, 'sra': sra, 'sra_sheet': sra_sheet}[sys.argv[1]](*sys.argv[2:4])
