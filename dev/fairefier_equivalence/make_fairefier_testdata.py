"""Make FAIRe-fier test workbooks from a mandatory-only FAIRe-ator template (made-up data)."""
import sys
import pandas as pd

TEMPLATE, OUTDIR = sys.argv[1], sys.argv[2]
sheets = pd.read_excel(TEMPLATE, sheet_name=None, header=None)

pm_values = {
    'checkls_ver': 1.0,
    'recordedBy': 'A. Researcher',
    'project_contact': 'a.researcher@example.org',
    'pcr_0_1': 1,
    'targetTaxonomicAssay': 'Actinopterygii',
    'pcr_primer_forward': 'GTCGGTAAAACTCGTGCCAGC',
    'pcr_primer_reverse': 'CATAGTGGGGTATCTAATCCCAGTTTG',
}
samples = [
    dict(samp_name='RI01_1', samp_category='sample', decimalLongitude=115.51234, decimalLatitude=-32.00612,
         geo_loc_name='Australia: Western Australia, Rottnest Island', eventDate='2026-03-14T09:30+08:00',
         env_broad_scale='marine biome [ENVO:00000447]', env_local_scale='neritic epipelagic zone [ENVO:01000042]',
         env_medium='sea water [ENVO:00002149]', assay_name='MiFish'),
    dict(samp_name='RI01_2', samp_category='sample', decimalLongitude=115.51234, decimalLatitude=-32.00612,
         geo_loc_name='Australia: Western Australia, Rottnest Island', eventDate='2026-03-14T09:45+08:00',
         env_broad_scale='marine biome [ENVO:00000447]', env_local_scale='neritic epipelagic zone [ENVO:01000042]',
         env_medium='sea water [ENVO:00002149]', assay_name='MiFish'),
    dict(samp_name='NC_1', samp_category='negative control', neg_cont_type='field negative',
         geo_loc_name='Australia: Western Australia, Rottnest Island', eventDate='2026-03-14T10:00+08:00', assay_name='MiFish'),
]


def build(path, pm_override=None, sample_override=None):
    out = {k: v.copy() for k, v in sheets.items()}
    pm = out['projectMetadata']
    for term, value in {**pm_values, **(pm_override or {})}.items():
        pm.loc[pm[2] == term, 3] = value
    sm = out['sampleMetadata']
    fields = list(sm.iloc[2])
    rows = []
    for s in samples:
        s = {**s, **(sample_override or {}).get(s['samp_name'], {})}
        rows.append([s.get(f) for f in fields])
    out['sampleMetadata'] = pd.concat([sm.iloc[:3], pd.DataFrame(rows, columns=sm.columns)], ignore_index=True)
    with pd.ExcelWriter(path, engine='openpyxl') as w:
        for name, df in out.items():
            df.to_excel(w, sheet_name=name, header=False, index=False)
    print('wrote', path)


build(f'{OUTDIR}/faire_valid.xlsx')
build(f'{OUTDIR}/faire_invalid.xlsx',
      pm_override={'pcr_0_1': 'yes', 'checkls_ver': 'FAIRe_checklist_v1.0.2.xlsx'},
      sample_override={'RI01_1': {'samp_category': 'smaple', 'eventDate': '14/03/2026'},
                       'RI01_2': {'env_medium': 'sea water', 'decimalLatitude': -32.006}})
