"""Diagnostic only: copy a workbook (values only) and fill empty filename/filename2 and the MD5
columns in experimentRunMetadata with invented values, so the ENA run step can be exercised."""
import hashlib
import sys

import pandas as pd

src, dst = sys.argv[1], sys.argv[2]
sheets = pd.read_excel(src, sheet_name=None, header=None)
erm = sheets['experimentRunMetadata']
fields = [str(v) for v in erm.iloc[2]]
col = {f: erm.columns[fields.index(f)] for f in ('lib_id', 'filename', 'filename2', 'checksum_filename', 'checksum_filename2', 'assay_name')}
filled = 0
for i in erm.index[3:]:
    lib = erm.at[i, col['lib_id']]
    if pd.isna(lib):
        continue
    tag = f"{lib}_{erm.at[i, col['assay_name']]}"
    for fcol, ccol, r in (('filename', 'checksum_filename', 'R1'), ('filename2', 'checksum_filename2', 'R2')):
        if pd.isna(erm.at[i, col[fcol]]):
            erm.at[i, col[fcol]] = f"{tag}_{r}.fastq.gz"
            filled += 1
        erm.at[i, col[ccol]] = hashlib.md5(str(erm.at[i, col[fcol]]).encode()).hexdigest()
with pd.ExcelWriter(dst, engine='openpyxl') as w:
    for name, df in sheets.items():
        df.to_excel(w, sheet_name=name, header=False, index=False)
print(f"filled {filled} file names; wrote {dst}")
