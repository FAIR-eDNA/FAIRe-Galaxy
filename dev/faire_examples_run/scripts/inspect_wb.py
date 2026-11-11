"""Inspect FAIRe example workbooks (read-only)."""
import sys
import pandas as pd

for path in sys.argv[1:]:
    print('=' * 100)
    print(path)
    xl = pd.ExcelFile(path)
    print('sheets:', xl.sheet_names)
    pm = pd.read_excel(path, sheet_name='projectMetadata', header=None)
    print('projectMetadata header row:', list(pm.iloc[0]))
    hdr = [str(v) for v in pm.iloc[0]]
    tcol = hdr.index('term_name') if 'term_name' in hdr else None
    if tcol is not None:
        for term in ('project_id', 'checkls_ver', 'assay_type', 'assay_name', 'pcr_0_1', 'target_gene',
                     'target_subfragment', 'platform', 'instrument', 'mod_date', 'informationWithheld'):
            rows = pm[pm[tcol].astype(str).str.strip() == term]
            if len(rows):
                vals = list(rows.iloc[0, tcol + 1:])
                print(f'  {term}: {vals!r}')
            else:
                print(f'  {term}: <absent>')
    for sh in ('sampleMetadata', 'experimentRunMetadata'):
        if sh not in xl.sheet_names:
            print(f'{sh}: <absent>')
            continue
        df = pd.read_excel(path, sheet_name=sh, header=None)
        print(f'{sh}: shape {df.shape}; row1[:4]={list(df.iloc[0,:4])}; row3[:6]={list(df.iloc[2,:6])}')
        d = pd.read_excel(path, sheet_name=sh, skiprows=2)
        print(f'  data rows {len(d)}; nonblank samp_name: {d["samp_name"].notna().sum() if "samp_name" in d else "NA"}')
        for c in ('samp_category', 'assay_name', 'seq_run_id'):
            if c in d:
                print(f'  {c} counts: {d[c].value_counts(dropna=False).to_dict()}')
        for c in ('eventDate', 'date_ext'):
            if c in d:
                vals = d[c].dropna()
                types = vals.map(lambda v: type(v).__name__).value_counts().to_dict()
                print(f'  {c} types {types}; sample: {list(vals.astype(str).unique()[:4])}')
        for c in ('lib_id', 'filename', 'filename2', 'checksum_filename', 'checksum_filename2', 'associatedSequences'):
            if c in d:
                print(f'  {c}: nonblank {d[c].notna().sum()} unique {d[c].nunique()} eg {list(d[c].dropna().astype(str).unique()[:2])}')
