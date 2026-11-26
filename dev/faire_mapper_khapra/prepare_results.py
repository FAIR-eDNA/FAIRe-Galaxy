"""What a person following the guide adds to the khapra beetle qPCR results
(Amplification_data_khapra_05012022_dryad.csv) before apply mapping:

  * an assay_name column naming each assay and machine (OlsonViiA7, FuruiFranklin ...). FAIRe
    holds one set of PCR values per assay, and the cycling conditions and master mix differ between
    the laboratory machine (ViiA7) and the portable one (Franklin), so each pair is an assay of its
    own. The names have no underscore: FAIRe-fier takes the assay name to be the part of
    detected_notDetected_<assay_name> after the last underscore;
  * a pcr_plate_id column, 'missing: not provided', as FAIRe asks for the plate of each reaction and
    the published table does not give it.

The published table is not changed. Usage: python prepare_results.py RESULTS.csv OUT.csv
"""

import sys

import pandas as pd

src, out = sys.argv[1:3]
df = pd.read_csv(src, dtype=str, keep_default_na=False, encoding='utf-8-sig')
df['assay_name'] = df['Assay'].str.strip().str.capitalize() + df['machine'].str.strip()
df['pcr_plate_id'] = 'missing: not provided'
df.to_csv(out, index=False)
print(f"{len(df)} reactions; assays: {', '.join(f'{a} ({n})' for a, n in df['assay_name'].value_counts().items())}")
