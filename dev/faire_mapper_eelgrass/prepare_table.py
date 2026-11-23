"""Builds the sample table for the Nova Scotia eelgrass study (Trask et al., Dryad
doi:10.5061/dryad.gqnk98t0c) from its two published tables, as a person following the mapper's guide
would. The study published no sample table: its samples are the columns of the ASV table (CAB-1,
CAB-2 ...), and its sites are in Site_coordinates.csv. One row per sample:

  * Sample ID, Site code, Site, Replicate, from the column name (site code, then the replicate);
    WRK02 in the ASV table is Wreck Cove (WRK) in the coordinates, revisited in 2019;
  * Latitude and Longitude of the site (WGS84, as the Dryad README says), so every replicate of a
    site has the site's coordinates;
  * Date, as the interval the Dryad page gives: July to September 2019 for the ten mainland sites,
    June to October 2023 for the six Cape Breton sites and Chebogue. No sample has its own date;
  * Country and Province;
  * Category: all are samples (the published table has no controls);
  * env_broad_scale, env_local_scale and env_medium (ENVO, release 2026-10-23): marine biome, sea
    grass bed and coastal sea water. The 2019 samples were water samples (He et al. 2022); the
    Dryad files do not say for 2023, and the same is assumed.

With the authors' per-ASV tables (prepare_asvs.py, from their GitHub repository), the table also
has a row for each control, and each 2019 sample has its site's date from MAR_2019eDNASiteData.csv:

  * controls: Category 'negative control', with no coordinates (a field control has its site's name,
    country and province). Their codes are read as field
    negatives (2019 FC and the 2023 site controls, C) and extraction negatives (2019 ENEG and the
    2023 Extraction-C); the 2019 lab control (CON-LC) gets 'missing: not provided'. These readings
    are ours, to confirm with the authors. A field control takes its site's date;
  * the 2023 samples keep the period of sampling, as the files give no date for them.

The published tables are not changed.
Usage: python prepare_table.py Final_ASVTable_withTaxonomy_Filtered.csv Site_coordinates.csv OUT.csv
       python prepare_table.py ... OUT.csv eelgrass_2019_asvs.csv eelgrass_2023_asvs.csv MAR_2019eDNASiteData.csv
"""

import datetime as dt
import re
import sys

import pandas as pd

YEAR_2019 = {'CAB', 'CON', 'FAI', 'FRK', 'MOS', 'PLS', 'RSE', 'TAE', 'TAW', 'WRK'}
DATES = {2019: '2019-07/2019-09', 2023: '2023-06/2023-10'}
SITE_CODE = {'WRK02': 'WRK'}
CONTROL_TYPE = {'FC': 'field negative', 'C': 'field negative', 'ENEG': 'extraction negative',
                'EXT': 'extraction negative', 'LC': 'missing: not provided'}
ENV = {'env_broad_scale': 'marine biome [ENVO:00000447]',
       'env_local_scale': 'sea grass bed [ENVO:01000059]',
       'env_medium': 'coastal sea water [ENVO:00002150]'}

asv, coords, out = sys.argv[1:4]
extra = sys.argv[4:7]
sites = pd.read_csv(coords, encoding='utf-8-sig').set_index('Code')
columns = list(pd.read_csv(asv, nrows=0).columns)
dates_2019 = {}
if extra:
    columns = [c for t in extra[:2] for c in pd.read_csv(t, nrows=0).columns]
    site_data = pd.read_csv(extra[2], encoding='latin-1')
    dates_2019 = {r.ID: dt.datetime.strptime(r.date, '%d-%b-%y').date().isoformat() for r in site_data.itertuples()}
rows = []
for col in columns:
    m = re.fullmatch(r'([A-Z]+\d*)-(\d+|FC|LC|C|\d{3})', col)
    if not m:
        continue     # ASV, Phylum, Class, Species, Probability
    code, rep = m.group(1), m.group(2)
    if code in ('ENEG', 'EXT'):
        rows.append({'Sample ID': col, 'Category': 'negative control', 'Negative control type': CONTROL_TYPE[code],
                     'Date': 'not applicable: control sample'})
        continue
    site_code = SITE_CODE.get(code, code)
    if site_code not in sites.index:
        sys.exit(f'no coordinates for site {site_code} (column {col})')
    site = sites.loc[site_code]
    year = 2019 if site_code in YEAR_2019 else 2023
    date = dates_2019.get(code, DATES[year]) if year == 2019 else DATES[year]
    if not rep.isdigit():
        rows.append({'Sample ID': col, 'Site code': site_code, 'Site': site['Site'], 'Date': date,
                     'Country': 'Canada', 'Province': 'Nova Scotia', 'Category': 'negative control',
                     'Negative control type': CONTROL_TYPE[rep]})
        continue
    rows.append({'Sample ID': col, 'Site code': site_code, 'Site': site['Site'], 'Replicate': int(rep),
                 'Latitude': site['Latitude'], 'Longitude': site['Longitude'], 'Date': date,
                 'Country': 'Canada', 'Province': 'Nova Scotia', 'Category': 'sample', **ENV})
df = pd.DataFrame(rows)
order = ['Sample ID', 'Site code', 'Site', 'Replicate', 'Latitude', 'Longitude', 'Date', 'Country', 'Province',
         'Category', 'Negative control type'] + list(ENV)
df = df[[c for c in order if c in df.columns]]
df.to_csv(out, index=False)
samples = df[df['Category'] == 'sample']
print(f'{len(samples)} samples from {samples["Site code"].nunique()} sites and {len(df) - len(samples)} controls '
      f'-> {out}')
