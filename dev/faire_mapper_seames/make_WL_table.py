"""The sample table for the Wilderlab panel (file 8), as a person following the guide would make it.

Usage: python make_WL_table.py M_prepared.csv CN_SHEET.xlsx samples_18S.csv WILDERLAB.csv OUT.csv

Wilderlab sequenced 150 extracts from three sample sets: 10 L samples (file 1, here the prepared
copy with the control type), deep-tow samples (file 2) and 2 L samples (the table made from the
sample details below the 18S counts). Their sheets have different columns, so the rows of each set
go into one table in the 10 L sheet's form (MIxS names, as submitted to NCBI):

- 10 L rows as they are;
- deep-tow rows from file 2, with Voyage IN2024_V03 (the deep-tow study was on the second
  voyage); CN167, the "Clean Dry Lab Control", is a field negative from the deep-tow sampler,
  probably the water used to rinse the filtration equipment (B. Deagle, 6 November 2026);
- 2 L rows from the 18S sample table: the date and UTC time as ISO 8601, latitude and longitude as
  MIxS lat_lon, geo_loc_name as "Australia: <Locality>" (as in the 18S trial), the volume in mL,
  the pore size, temperature, salinity and the three ENVO terms of the 10 L sheet;
- 2 L samples with no details in the record (not in the 18S table) with their name and voyage only;
- MQ1, a Milli-Q control not in any sheet: a field negative, 5 L of Milli-Q water filtered on the
  ship alongside the CTD samples (B. Deagle, 6 November 2026).
Give it the Wilderlab table with its repeated columns renamed (rename_WL_repeats.py): CN165 and
CN166 are then deep-tow rows too.

A column *Sample set* says which set each row comes from.
"""
import re
import sys

import pandas as pd

OUT_COLS = ['*sample_name', 'sample_title', 'Sample set', 'Voyage', 'Location', '*collection_date', '*depth',
            '*lat_lon', '*geo_loc_name', '*env_broad_scale', '*env_local_scale', '*env_medium', 'temp', 'salinity',
            'samp_vol_we_dna_ext', 'size_frac_low', 'Control_Neg', 'Negative control type']


def ncbi_sheet(path):
    raw = pd.read_excel(path, header=None, dtype=str)
    h = raw.index[raw[0].astype(str).str.contains('sample_name')][0]
    t = raw.iloc[h + 1:].copy()
    t.columns = [str(c) for c in raw.iloc[h]]
    return t.dropna(how='all').fillna('')


def lat_lon(lat, lon):
    try:
        a, b = float(lat), float(lon)
    except ValueError:
        return ''
    return f"{lat.lstrip('-')} {'S' if a < 0 else 'N'} {lon.lstrip('-')} {'W' if b < 0 else 'E'}"


def iso_date(d, t):
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', d.strip())
    if not m:
        return d
    day = f'{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}'
    hm = re.match(r'^(\d{1,2}):(\d{2})$', t.strip())
    return f'{day}T{int(hm.group(1)):02d}:{hm.group(2)}Z' if hm else day


def main(m_csv, cn_xlsx, s_csv, wl_csv, out_csv):
    wanted = [c for c in pd.read_csv(wl_csv, nrows=0).columns[7:]]
    wanted = list(dict.fromkeys(re.sub(r'\.\d+$', '', c) for c in wanted))   # CN065.1 is a repeat of CN065
    m = pd.read_csv(m_csv, dtype=str, keep_default_na=False)
    cn = ncbi_sheet(cn_xlsx)
    s = pd.read_csv(s_csv, dtype=str, keep_default_na=False)
    envo = {c: m[c].iloc[0] for c in ('*env_broad_scale', '*env_local_scale', '*env_medium')}
    by = {'M': m.set_index('*sample_name'), 'CN': cn.set_index('*sample_name'), 'S': s.set_index('Sample No.')}
    rows, missing = [], []
    for name in wanted:
        r = {c: '' for c in OUT_COLS}
        r['*sample_name'] = name
        if name in by['M'].index:
            src = by['M'].loc[name]
            r.update({c: src[c] for c in OUT_COLS if c in src.index})
            r['Sample set'] = '10 L'
        elif name in by['CN'].index:
            src = by['CN'].loc[name]
            r.update({c: src[c] for c in OUT_COLS if c in src.index})
            control = 'control' in src['sample_title'].lower()
            r.update({'Sample set': 'deep-tow', 'Voyage': 'IN2024_V03', 'Control_Neg': 'Y' if control else 'N',
                      'Negative control type': 'field negative' if control else ''})
        elif name in by['S'].index:
            src = by['S'].loc[name]
            vol = re.match(r'^\s*([\d.]+)\s*L\s*$', src['Volume filtered'])
            r.update({'sample_title': src['Sample ID'], 'Sample set': '2 L', 'Voyage': src['Voyage'],
                      'Location': src['Location'],
                      '*collection_date': iso_date(src['Collection Date'], src['Collection Time (UTC)']),
                      '*depth': src['Depth (m)'], '*lat_lon': lat_lon(src['Latitude'], src['Longitude']),
                      '*geo_loc_name': f"Australia: {src['Locality']}" if src['Locality'] else '',
                      'temp': src['Temperature'], 'salinity': src['Salinity'],
                      'samp_vol_we_dna_ext': str(int(float(vol.group(1)) * 1000)) if vol else '',
                      'size_frac_low': src['Filter pore size (µm)'], 'Control_Neg': 'N', **envo})
        elif name.startswith('S'):
            r.update({'Sample set': '2 L', 'Voyage': 'IN2023_V05', 'Control_Neg': 'N'})
            missing.append(name)
        elif name == 'MQ1':
            r.update({'sample_title': 'Field filtration control: 5 L of Milli-Q water filtered on the ship '
                                      'alongside the CTD samples', 'Sample set': '10 L', 'Voyage': 'IN2023_V05',
                      'samp_vol_we_dna_ext': '5000', 'Control_Neg': 'Y', 'Negative control type': 'field negative'})
        else:
            sys.exit(f'{name}: not in any sample sheet')
        rows.append(r)
    out = pd.DataFrame(rows, columns=OUT_COLS)
    out.to_csv(out_csv, index=False)
    sets = out['Sample set'].value_counts().to_dict()
    print(f"{len(out)} samples ({', '.join(f'{v} {k}' for k, v in sets.items())}); "
          f"{(out.Control_Neg == 'Y').sum()} negative controls; no details in the record for "
          f"{len(missing)} 2 L samples: {', '.join(missing)}")


if __name__ == '__main__':
    if len(sys.argv) != 6:
        sys.exit(__doc__)
    main(*sys.argv[1:])
