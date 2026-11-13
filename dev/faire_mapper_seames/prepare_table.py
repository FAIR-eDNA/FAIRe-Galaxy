"""What a person following the mapper's guide does to the 10 L sample table before mapping.

The guide asks for a column that says which rows are controls, and what kind. The BioSample sheet
says which (Control_Neg, Y or N) but not what kind, and the log of apply mapping asks for
neg_cont_type. This adds a column "Negative control type": field negative for the controls, which
the report describes as field filtration controls of Milli-Q water. Everything else is kept as it
is, including MIxS lat_lon and the yes/no control column, which the mapper now handles. Excel date
cells, which pandas reads as text such as 2023-06-30 00:00:00, are written as the date they hold
(2023-06-30): that text is not something the lab wrote, so apply mapping should not keep it in
verbatimEventDate.

Usage: python prepare_table.py SAMPLE_SHEET.xlsx OUT.csv
"""
import sys

import pandas as pd

src, out = sys.argv[1], sys.argv[2]
df = pd.read_excel(src, header=11, dtype=str)   # the header is on row 12, below NCBI's comment lines
flag = df['Control_Neg'].str.strip().str.upper()
df = df.replace(r'^(\d{4}-\d{2}-\d{2}) 00:00:00$', r'\1', regex=True)
df.insert(list(df.columns).index('Control_Neg') + 1, 'Negative control type', flag.map({'Y': 'field negative', 'N': ''}))
df.to_csv(out, index=False)
print(f"{len(df)} rows; Negative control type added for {int((flag == 'Y').sum())} controls")
