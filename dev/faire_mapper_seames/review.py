"""Apply a person's review decisions (confirm, delete, change the term, or add a second term) (reviewer_decisions.tsv) to a crosswalk from propose mapping.
A term or add decision for a column with no row adds a row for it.

Usage: python review.py CROSSWALK.sssom.tsv DECISIONS.tsv OUT.sssom.tsv
"""
import sys

import pandas as pd

cw_path, dec_path, out = sys.argv[1:4]
lines = open(cw_path, encoding='utf-8').read().splitlines()
head = [ln for ln in lines if ln.startswith('#')]
body = [ln for ln in lines if not ln.startswith('#')]
cols = body[0].split('\t')
rows = [dict(zip(cols, ln.split('\t'))) for ln in body[1:]]
dec = pd.read_csv(dec_path, sep='\t', comment='#', dtype=str).fillna('')
done = set()
kept = []
for r in rows:
    d = dec[dec.column == r['subject_label']]
    if d.empty:
        kept.append(r)
        continue
    action = d.action.iloc[0]
    done.add(r['subject_label'])
    if action == 'delete':
        continue
    if action == 'confirm':
        r['predicate_id'] = 'skos:exactMatch'
        r['comment'] = 'confirmed by reviewer'
    elif action.startswith('add:'):
        # keep this row and add a second row matching the same column to another term
        extra = dict(r)
        extra['object_label'] = action[4:]
        extra['object_id'] = 'FAIRe:' + action[4:]
        extra['predicate_id'] = 'skos:exactMatch'
        extra['comment'] = 'added by reviewer'
        kept.append(r)
        kept.append(extra)
        continue
    elif action.startswith('term:'):
        r['object_label'] = action[5:]
        r['object_id'] = 'FAIRe:' + action[5:]
        r['predicate_id'] = 'skos:exactMatch'
        r['comment'] = 'changed by reviewer'
    kept.append(r)
# A column with no row (no match) gets one for term: and add: decisions, as a person adds a row
# in a spreadsheet; other decisions on such columns are reported.
for d in dec.to_dict('records'):
    if d['column'] in done:
        continue
    action = d['action']
    if action.startswith(('term:', 'add:')):
        term = action.split(':', 1)[1]
        kept.append({'subject_id': 'local:' + ''.join(c if c.isalnum() or c in '_.-' else '_' for c in d['column']),
                     'subject_label': d['column'], 'predicate_id': 'skos:exactMatch', 'object_id': 'FAIRe:' + term,
                     'object_label': term, 'mapping_justification': 'semapv:ManualMappingCuration',
                     'confidence': '', 'comment': 'added by reviewer', 'combine_order': '', 'value_part': ''})
        done.add(d['column'])
missing = set(dec.column) - done
if missing:
    print('not in the crosswalk: ' + ', '.join(sorted(missing)), file=sys.stderr)
with open(out, 'w', encoding='utf-8') as f:
    f.write('\n'.join(head) + '\n' + '\t'.join(cols) + '\n')
    for r in kept:
        f.write('\t'.join(r.get(c, '') for c in cols) + '\n')
print(f'{len(rows)} rows; {len(rows) - len(kept)} deleted; {len(done)} decisions applied')
