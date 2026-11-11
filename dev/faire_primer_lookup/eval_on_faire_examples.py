"""Check faire_primers.py lookups against FAIRe workbooks that give both primer names and sequences.
Usage: eval_on_faire_examples.py PRIMER_TSV WORKBOOK [WORKBOOK ...]
For each assay, looks up the primer names, the assay name and the primer reference, and reports
whether the true sequence pair is among the candidates and how many candidate pairs there are."""
import sys
from pathlib import Path

import pandas as pd

tools = Path(__file__).resolve().parent.parent.parent / 'tools' / 'faire_mapper'
sys.path.insert(0, str(tools))
import faire_primers as fp  # noqa: E402

TERMS = ['assay_name', 'target_gene', 'pcr_primer_forward', 'pcr_primer_reverse', 'pcr_primer_name_forward',
         'pcr_primer_name_reverse', 'pcr_primer_reference_forward']


def assays(path):
    pm = pd.read_excel(path, sheet_name='projectMetadata', header=None, dtype=str)
    hdr = next(i for i in range(len(pm)) if 'term_name' in pm.iloc[i].astype(str).tolist())
    cols = pm.iloc[hdr].astype(str).tolist()
    body = pm.iloc[hdr + 1:]
    tcol = cols.index('term_name')
    vals = {str(r[tcol]): r for _, r in body.iterrows()}
    acols = [i for i, c in enumerate(cols) if c.startswith('assay') or c not in ('nan', 'term_name', 'section',
             'requirement_level_code', 'project_level')]
    lv = cols.index('project_level')
    out = []
    for i in (acols or [lv]):
        a = {t: (str(vals[t].iloc[i]).strip() if t in vals and str(vals[t].iloc[i]) != 'nan' else '') for t in TERMS}
        for t in TERMS:   # fall back to project_level when the assay column is empty
            if not a[t] and t in vals and str(vals[t].iloc[lv]) != 'nan' and '|' not in str(vals[t].iloc[lv]):
                a[t] = str(vals[t].iloc[lv]).strip()
        if a['assay_name']:
            out.append(a)
    return out


def main():
    t = fp.load(sys.argv[1])
    rows = []
    for path in sys.argv[2:]:
        for a in assays(path):
            truth = (fp.clean_seq(a['pcr_primer_forward']), fp.clean_seq(a['pcr_primer_reverse']))
            in_table = any((r.pcr_primer_forward, r.pcr_primer_reverse) == truth for r in t.itertuples())
            fwd_in_table = any(r.pcr_primer_forward == truth[0] for r in t.itertuples())
            for how, q in (('primer name', a['pcr_primer_name_forward']), ('assay name', a['assay_name']),
                           ('reference', a['pcr_primer_reference_forward'])):
                if not q:
                    continue
                cands = fp.lookup(t, q, a['target_gene'] or None)
                prs = fp.pairs(cands)
                rows.append({'workbook': Path(path).stem, 'assay': a['assay_name'], 'query_type': how,
                             'query': q[:40], 'pair_in_table': in_table, 'fwd_in_table': fwd_in_table,
                             'candidate_pairs': len(prs), 'true_pair_found': truth in prs,
                             'true_fwd_found': any(p[0] == truth[0] for p in prs),
                             'compatible_pair_found': any(fp.compatible(p[0], truth[0]) and fp.compatible(p[1], truth[1])
                                                          for p in prs),
                             'swapped_pair_found': (truth[1], truth[0]) in prs,
                             'matched_by': cands[0]['matched_by'] if cands else ''})
    d = pd.DataFrame(rows)
    pd.set_option('display.width', 250)
    print(d.to_string(index=False))
    d.to_csv(Path(__file__).resolve().parent / 'eval_on_faire_examples.tsv', sep='\t', index=False)
    return d


if __name__ == '__main__':
    main()
