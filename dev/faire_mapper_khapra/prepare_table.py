"""What a person following the guide adds to the khapra beetle sample table (Sample_metadata.csv)
before mapping it, from the README and the paper (Trujillo-Gonzalez et al. 2022):

  * Category: sample, negative control or positive control, from 'sample type' (field controls are
    field negatives; the Kambah dust with a live larva and the specimens' genomic DNA are the study's
    positive controls);
  * Negative control type and Positive control type;
  * State, so geo_loc_name reads 'Australia: Australian Capital Territory, Tuggeranong';
  * Latitude and Longitude for the samples: 'missing: restricted access', as the authors withheld
    the stores' locations. Only the district or suburb they name (Tuggeranong, Fyshwick) is given,
    in geo_loc_name;
  * env_broad_scale, env_local_scale and env_medium (ENVO, release 2026-10-23).

The published table is not changed. Usage: python prepare_table.py Sample_metadata.csv OUT.csv
"""

import sys

import pandas as pd

WITHHELD = 'missing: restricted access'
CATEGORY = {'Dust sample': 'sample', 'Airborne sample': 'sample', 'Infested box inside freezer': 'sample',
            'Field control': 'negative control', 'eDNA Positive control': 'positive control',
            'Specimen': 'positive control'}
POSITIVE = {'eDNA Positive control': 'dust with a live T. granarium larva, from a car boot (Kambah biosecurity '
                                     'response), extracted 15 times',
            'Specimen': 'genomic DNA from T. granarium larvae and adults (tissue)'}

src, out = sys.argv[1:3]
df = pd.read_csv(src, dtype=str, keep_default_na=False)
kind = df['sample type'].str.strip()
unknown = sorted(set(kind) - set(CATEGORY))
if unknown:
    sys.exit(f'unknown sample types: {unknown}')
df['Category'] = kind.map(CATEGORY)
df['Negative control type'] = ['field negative' if k == 'Field control' else '' for k in kind]
df['Positive control type'] = [POSITIVE.get(k, '') for k in kind]
df['State'] = ['Australian Capital Territory' if loc != 'CSIRO Collection' else '' for loc in df['Location']]
samples = df['Category'].eq('sample')
for col in ('Latitude', 'Longitude'):
    df[col] = [WITHHELD if s else '' for s in samples]
df['env_broad_scale'] = ['urban biome [ENVO:01000249]' if s else '' for s in samples]
df['env_local_scale'] = ['shop [ENVO:00002221]' if s else '' for s in samples]
df['env_medium'] = [('air [ENVO:00002005]' if k == 'Airborne sample' else 'dust [ENVO:00002008]') if s else ''
                    for s, k in zip(samples, kind)]
df.to_csv(out, index=False)
print(f"{len(df)} rows: {samples.sum()} samples, {(~samples).sum()} controls -> {out}")
