"""What a person following the guide adds to the khapra beetle sample table (Sample_metadata.csv)
before mapping it, from the README and the paper (Trujillo-Gonzalez et al. 2022):

  * Category: sample, negative control or positive control, from 'sample type' (field controls are
    field negatives; the Kambah dust with a live larva and the specimens' genomic DNA are the study's
    positive controls);
  * Negative control type and Positive control type;
  * State, so geo_loc_name reads 'Australia: Australian Capital Territory, Tuggeranong';
  * Latitude, Longitude and coordinateUncertaintyInMeters for the samples: the centre of the place the
    authors name (the Tuggeranong district, the suburb of Fyshwick), as the stores' locations are
    withheld; with an uncertainty that covers the district or suburb;
  * env_broad_scale, env_local_scale and env_medium (ENVO, release 2026-10-23).

The published table is not changed. Usage: python prepare_table.py Sample_metadata.csv OUT.csv
"""

import sys

import pandas as pd

# Centres of the places named, from their Wikipedia articles (Tuggeranong district 35.4244 S
# 149.0888 E; Fyshwick 35.329 S 149.174 E), and uncertainties covering them
PLACES = {'Tuggeranong': (-35.4244, 149.0888, 10000), 'Fyshwick': (-35.329, 149.174, 3000)}
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
for col, i in (('Latitude', 0), ('Longitude', 1), ('coordinateUncertaintyInMeters', 2)):
    df[col] = [str(PLACES[loc][i]) if s and loc in PLACES else '' for s, loc in zip(samples, df['Location'])]
df['env_broad_scale'] = ['urban biome [ENVO:01000249]' if s else '' for s in samples]
df['env_local_scale'] = ['shop [ENVO:00002221]' if s else '' for s in samples]
df['env_medium'] = [('air [ENVO:00002005]' if k == 'Airborne sample' else 'dust [ENVO:00002008]') if s else ''
                    for s, k in zip(samples, kind)]
missing = df.loc[samples & df['Latitude'].eq(''), 'Location'].unique()
if len(missing):
    sys.exit(f'samples from places with no coordinates: {list(missing)}')
df.to_csv(out, index=False)
print(f"{len(df)} rows: {samples.sum()} samples, {(~samples).sum()} controls -> {out}")
