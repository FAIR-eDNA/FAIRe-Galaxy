"""Score mapping reports against the independent answer keys (term plus also_acceptable).
Usage: score.py GOLD_DIR RUN_DIR [RUN_DIR ...]   (each RUN_DIR holds <name>/mapping_report.tsv)
Writes <name>/scored.tsv in each run and scores.tsv next to the first run.

Outcomes per column: correct (the key's term), acceptable (in also_acceptable), part of a term (the key
leaves the column empty but notes it builds that term, e.g. site and country for geo_loc_name), wrong,
missed (the key has a term, the mapper none), right to leave (neither has a term)."""
import re
import sys
from pathlib import Path

import pandas as pd

NAMES = ['mathon', 'sacco', 'vanderheyde', 'jackman']


def load_gold(path, term_names):
    g = pd.read_csv(path, sep='\t', dtype=str, keep_default_na=False)
    out = {}
    for r in g.to_dict('records'):
        also = {t.strip() for t in r.get('also_acceptable', '').split(';') if t.strip()}
        part = set()
        if not r['term']:
            part = {w for w in re.findall(r'[A-Za-z_0-9]+', r.get('note', '')) if w in term_names}
        out[r['column']] = (r['term'], also, part)
    return out


def score(rep, gold):
    rows = []
    for r in rep.to_dict('records'):
        col, term, route = r['column'], r['proposed_term'], r['route']
        short = [s.split(' (')[0].strip() for s in r.get('shortlist', '').split(';') if s.strip()]
        best, also, part = gold.get(col, ('', set(), set()))
        if best:
            if term == best:
                out = 'correct'
            elif term and term in also:
                out = 'acceptable'
            elif term:
                out = 'wrong'
            else:
                out = 'missed'
        else:
            out = 'right to leave' if not term else ('part of a term' if term in part else 'wrong')
        in_short = bool(best) and (best in short or bool(also & set(short)))
        rows.append({'column': col, 'route': route, 'proposed': term, 'gold': best, 'outcome': out,
                     'gold_in_shortlist': in_short})
    d = pd.DataFrame(rows)
    has = d[d.gold != '']
    acc = d[d.route.isin(['accept', 'confirmed', 'model'])]
    ok = {'correct', 'acceptable', 'part of a term'}
    return d, {
        'columns': len(d), 'with_term': len(has),
        'top1_correct': int((has.outcome == 'correct').sum()),
        'top1_ok': int(has.outcome.isin(ok).sum()),
        'in_shortlist': int(has.gold_in_shortlist.sum()),
        'accepted': len(acc), 'accepted_ok': int(acc.outcome.isin(ok).sum()),
        'no_term': int((d.gold == '').sum()), 'no_term_left': int((d.outcome == 'right to leave').sum()),
        'wrong': int((d.outcome == 'wrong').sum()), 'missed': int((d.outcome == 'missed').sum()),
    }


def main():
    gold_dir = Path(sys.argv[1])
    tools = Path(__file__).resolve().parent.parent.parent / 'tools' / 'faire_mapper'
    sys.path.insert(0, str(tools))
    import faire_mapper as fm
    names = {t.name for t in fm.load_checklist(tools / 'checklist' / 'FAIRe_checklist_v1.0.2.xlsx')}
    allrows = []
    for run in sys.argv[2:]:
        for n in NAMES:
            p = Path(run) / n / 'mapping_report.tsv'
            if not p.exists():
                allrows.append({'run': Path(run).name, 'table': n, 'note': 'no report (failed)'})
                continue
            rep = pd.read_csv(p, sep='\t', dtype=str, keep_default_na=False)
            d, s = score(rep, load_gold(gold_dir / f'{n}.gold.tsv', names))
            d.to_csv(Path(run) / n / 'scored.tsv', sep='\t', index=False)
            allrows.append({'run': Path(run).name, 'table': n, **s})
    out = pd.DataFrame(allrows)
    print(out.to_string(index=False))
    out.to_csv(Path(sys.argv[2]).parent / 'scores.tsv', sep='\t', index=False)


if __name__ == '__main__':
    main()
