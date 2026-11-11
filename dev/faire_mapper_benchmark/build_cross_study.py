"""Build benchmark tables from other FAIRe example workbooks, with the held-out lab headers.

The original benchmark took all its values from one marine study (GOMECC-4). This applies the same
held-out header sets (heldout_headers.json, written before any of these workbooks were seen) to the
values of other FAIRe examples, so the values come from different studies, habitats and labs.

Usage: build_cross_study.py OUTDIR WORKBOOK [WORKBOOK ...]
Writes OUTDIR/<workbook>_<lab>.csv and .gold.tsv. A term is used only when the workbook has at
least one real value for it (FAIRe missing-value notes do not count).
"""
import json
import random
import sys
from pathlib import Path

import pandas as pd

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent.parent / 'tools' / 'faire_mapper'))
import faire_mapper as fm  # noqa: E402

H = json.load(open(here / 'heldout_headers.json'))
LABS = ('lab_a', 'lab_b', 'lab_c')


def sheet(path, name):
    raw = pd.read_excel(path, sheet_name=name, header=None, dtype=object)
    hdr = next(i for i in range(min(10, len(raw))) if 'samp_name' in raw.iloc[i].astype(str).tolist())
    df = pd.read_excel(path, sheet_name=name, skiprows=hdr, dtype=object)
    return df.dropna(how='all')


def project(path):
    pm = pd.read_excel(path, sheet_name='projectMetadata', dtype=object)
    cols = [c for c in pm.columns if str(c).startswith('assay')]
    first = cols[0] if cols else 'project_level'
    out = {}
    for _, r in pm.iterrows():
        v = r.get(first)
        if pd.isna(v) or v is None:
            v = r.get('project_level')
        if pd.notna(v) and '|' not in str(v):
            out[str(r['term_name'])] = v
    return out, (out.get('assay_name') or '')


def build(path, n_rows=60, seed=1):
    random.seed(seed)
    sm = sheet(path, 'sampleMetadata')
    try:
        er = sheet(path, 'experimentRunMetadata')
    except (StopIteration, ValueError):
        er = pd.DataFrame()
    pm, assay = project(path)
    if 'samp_category' in sm:
        ctl = sm[sm.samp_category.astype(str) != 'sample'].head(8)
        rows = pd.concat([sm[sm.samp_category.astype(str) == 'sample'].head(n_rows - len(ctl)), ctl])
    else:
        rows = sm.head(n_rows)
    rows = rows.reset_index(drop=True)
    if len(er) and 'samp_name' in er:
        if assay and 'assay_name' in er:
            er = er[er.assay_name.astype(str) == assay]
        er = er.drop_duplicates('samp_name').set_index('samp_name')

    def values(term):
        if term in rows.columns:
            return rows[term].tolist()
        if len(er) and term in er.columns:
            return [er[term].get(s) for s in rows.samp_name]
        if term in pm:
            return [pm[term]] * len(rows)
        return None

    tables = {}
    for lab in LABS:
        data, gold = {}, []
        for h in H['headers']:
            vals = values(h['term'])
            if vals is None or not any(v is not None and not (isinstance(v, float) and pd.isna(v))
                                       and not fm.is_missing(v) for v in vals):
                continue
            data[h[lab]] = vals
            gold.append({'column': h[lab], 'term': h['term']})
        for d in H['distractors']:
            data[d] = [random.choice(['RV Walton', 'Hilux 2', 'Bay 3', 'Ute A', 'calm', '']) for _ in range(len(rows))]
            gold.append({'column': d, 'term': ''})
        order = list(data)
        random.shuffle(order)
        tables[lab] = (pd.DataFrame({k: data[k] for k in order}), pd.DataFrame(gold))
    return tables


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for p in sys.argv[2:]:
        for lab, (df, gold) in build(p).items():
            stem = f'{Path(p).stem}_{lab}'
            df.to_csv(out / f'{stem}.csv', index=False)
            gold.to_csv(out / f'{stem}.gold.tsv', sep='\t', index=False)
            print(f'{stem}: {len(df)} rows, {int((gold.term != "").sum())} columns with a term, '
                  f'{int((gold.term == "").sum())} distractors')


if __name__ == '__main__':
    main()
