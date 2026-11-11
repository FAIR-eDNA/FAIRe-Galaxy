"""Build benchmark tables with known answers from the GOMECC-4 FAIRe example and independent headers."""
import json
import random
import re

import pandas as pd

import sys
# Usage: build_benchmark.py [HEADERS_JSON] [PREFIX] [GOMECC4_XLSX]
# GOMECC4_XLSX: raw-v3/FAIRe_generic_example_dataset/noaa-aoml-gomecc4.xlsx from aomlomics/edna2obis (MIT)
HFILE = sys.argv[1] if len(sys.argv) > 1 else 'bespoke_headers.json'
PREFIX = sys.argv[2] if len(sys.argv) > 2 else 'bench'
X = sys.argv[3] if len(sys.argv) > 3 else 'noaa-aoml-gomecc4.xlsx'
H = json.load(open(HFILE))
random.seed(1)

sm = pd.read_excel(X, sheet_name='sampleMetadata', skiprows=2)
er = pd.read_excel(X, sheet_name='experimentRunMetadata', skiprows=2)
pm = pd.read_excel(X, sheet_name='projectMetadata')

controls = sm[sm.samp_category != 'sample'].head(8)
samples = sm[sm.samp_category == 'sample'].head(52)
rows = pd.concat([samples, controls]).reset_index(drop=True)
er16 = er[er.assay_name == 'ssu16sv4v5-emp'].drop_duplicates('samp_name').set_index('samp_name')


def pm_value(term):
    r = pm[pm.term_name == term]
    if r.empty:
        return None
    v = r['assay1'].iloc[0]
    return v if pd.notna(v) else r['project_level'].iloc[0]


def term_values(term):
    if term in rows.columns:
        return rows[term].tolist()
    if term in er16.columns:
        return [er16[term].get(s) for s in rows.samp_name]
    v = pm_value(term)
    if v is None and term == 'instrument':
        v = 'Illumina MiSeq'
    return [v] * len(rows)


def distractor_values(h, n):
    hl = h.lower()
    if 'y/n' in hl or hl.endswith('?') or 'archived' in hl or 'printed' in hl:
        return [random.choice(['Y', 'N']) for _ in range(n)]
    if any(w in hl for w in ('initials', 'checked by', 'entered by', 'who ', 'holder')):
        return [random.choice(['JS', 'KL', 'MB', 'TW']) for _ in range(n)]
    if any(w in hl for w in ('number', 'no.', '#', 'page')):
        return [random.randint(1, 40) for _ in range(n)]
    if 'photo' in hl:
        return [f'IMG_{random.randint(1000, 9999)}' for _ in range(n)]
    if 'notes' in hl or 'comments' in hl:
        return [random.choice(['calm', 'windy, light rain', 'swell 1 m', '', 'check depth']) for _ in range(n)]
    if 'cost code' in hl:
        return ['R-08234-01'] * n
    if 'colour' in hl:
        return [random.choice(['red', 'blue', 'green']) for _ in range(n)]
    if 'spare' in hl:
        return [None] * n
    return [random.choice(['RV Walton', 'Hilux 2', 'Bay 3', 'Ute A']) for _ in range(n)]


def messy(term, vals):
    if term == 'eventDate':
        out = []
        for v in vals:
            m = re.match(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})', str(v))
            out.append(f'{m.group(3)}/{m.group(2)}/{m.group(1)} {m.group(4)}:{m.group(5)}' if m else v)
        return out
    if term.startswith('env_'):
        return [re.sub(r'\s*\[[^\]]*\]\s*$', '', str(v)) if pd.notna(v) else v for v in vals]
    return vals


def build(style, value_style='as_is', headers='named'):
    data, gold = {}, []
    for i, h in enumerate(H['headers']):
        term = h['term']
        vals = term_values(term)
        if value_style == 'messy':
            vals = messy(term, vals)
        name = h[style] if headers == 'named' else f'col_{i + 1}'
        data[name] = vals
        gold.append({'column': name, 'term': term})
    for j, d in enumerate(H['distractors']):
        name = d if headers == 'named' else f'col_{len(H["headers"]) + j + 1}'
        data[name] = distractor_values(d, len(rows))
        gold.append({'column': name, 'term': ''})
    # shuffle column order so position carries no signal
    order = list(data)
    random.shuffle(order)
    return pd.DataFrame({k: data[k] for k in order}), pd.DataFrame(gold)


STYLES = {'tidy': ('tidy',), 'terse': ('terse',), 'messy_headers': ('messy',),
          'messy_values': ('messy', 'messy'), 'no_headers': ('tidy', 'as_is', 'none')}
if 'lab_a' in H['headers'][0]:
    STYLES = {'lab_a': ('lab_a',), 'lab_b': ('lab_b',), 'lab_c': ('lab_c',), 'lab_c_messy_values': ('lab_c', 'messy')}
for label, args in STYLES.items():
    df, gold = build(*args)
    df.to_csv(f'data/{PREFIX}_{label}.csv', index=False)
    gold.to_csv(f'data/{PREFIX}_{label}.gold.tsv', sep='\t', index=False)
    print(label, df.shape, 'empty columns:', [c for c in df.columns if df[c].isna().all()])
