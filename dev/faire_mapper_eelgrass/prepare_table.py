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

The published tables are not changed.
Usage: python prepare_table.py Final_ASVTable_withTaxonomy_Filtered.csv Site_coordinates.csv OUT.csv
"""

import re
import sys

import pandas as pd

YEAR_2019 = {'CAB', 'CON', 'FAI', 'FRK', 'MOS', 'PLS', 'RSE', 'TAE', 'TAW', 'WRK'}
DATES = {2019: '2019-07/2019-09', 2023: '2023-06/2023-10'}
SITE_CODE = {'WRK02': 'WRK'}

asv, coords, out = sys.argv[1:4]
table = pd.read_csv(asv, nrows=0)
sites = pd.read_csv(coords, encoding='utf-8-sig').set_index('Code')
rows = []
for col in table.columns:
    m = re.fullmatch(r'([A-Z]+\d*)-(\d+)', col)
    if not m:
        continue     # Phylum, Class, Species, Probability
    code = SITE_CODE.get(m.group(1), m.group(1))
    if code not in sites.index:
        sys.exit(f'no coordinates for site {code} (column {col})')
    site = sites.loc[code]
    year = 2019 if code in YEAR_2019 else 2023
    rows.append({'Sample ID': col, 'Site code': code, 'Site': site['Site'], 'Replicate': int(m.group(2)),
                 'Latitude': site['Latitude'], 'Longitude': site['Longitude'], 'Date': DATES[year],
                 'Country': 'Canada', 'Province': 'Nova Scotia', 'Category': 'sample',
                 'env_broad_scale': 'marine biome [ENVO:00000447]',
                 'env_local_scale': 'sea grass bed [ENVO:01000059]',
                 'env_medium': 'coastal sea water [ENVO:00002150]'})
df = pd.DataFrame(rows)
df.to_csv(out, index=False)
print(f'{len(df)} samples from {df["Site code"].nunique()} sites: '
      f'{(df["Date"] == DATES[2019]).sum()} in 2019, {(df["Date"] == DATES[2023]).sum()} in 2023 -> {out}')
