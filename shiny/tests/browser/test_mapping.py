"""A mapping table like edna2obis: match taxa writes, for a FAIRe workbook's taxaFinal sheet, made
without the internet lookup: most names matched as they are given, and one of each kind of change
(a synonym, a species matched at its genus, a namesake with two candidates, a name not found and
another spelling). The IDs are made up. Used by journeys.py through FAIRE_TEST_MAPPING.

    python3 test_mapping.py WORKBOOK OUT.tsv [ASSAY]
"""
import csv
import sys

import openpyxl

RANKS = ['kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'scientificName']
COLS = ['verbatimIdentification', 'assay_name', 'cleanedTaxonomy', 'selected_match', 'ambiguous', 'replaced_unaccepted',
        'unaccepted_match', 'ranks_matched', 'ranks_provided', 'assignment_score', 'environment', 'scientificName',
        'taxonRank', 'scientificNameID', 'higherClassification', 'kingdom', 'phylum', 'class', 'order', 'family', 'genus',
        'match_type_debug', 'nameAccordingTo']


def taxa_names(workbook):
    """The names edna2obis looks up: verbatimIdentification, or the ranks joined with ';'."""
    ws = openpyxl.load_workbook(workbook, read_only=True)['taxaFinal']
    rows = list(ws.iter_rows(values_only=True))
    head = [str(h) if h is not None else '' for h in rows[2]]
    out = []
    for r in rows[3:]:
        rec = {h: ('' if v is None else str(v).strip()) for h, v in zip(head, r)}
        if not rec.get('seq_id'):
            continue
        name = rec.get('verbatimIdentification') or ';'.join(rec[k] for k in RANKS if rec.get(k))
        if name and name not in [n for n, _ in out]:
            out.append((name, rec))
    return out


def make_mapping(workbook, out, assay='LerayCOI'):
    names = taxa_names(workbook)
    rows, n = [], [0]

    def add(v, rec, sci, rank, sel='True', **extra):
        n[0] += 1
        parts = v.split(';')
        row = {c: '' for c in COLS}
        row.update({'verbatimIdentification': v, 'assay_name': assay, 'cleanedTaxonomy': ';'.join(p.replace('_', ' ') for p in parts),
                    'selected_match': sel, 'ambiguous': 'False', 'replaced_unaccepted': 'False', 'unaccepted_match': 'False',
                    'scientificName': sci, 'taxonRank': rank, 'scientificNameID': f'urn:lsid:marinespecies.org:taxname:9{n[0]:05d}',
                    'kingdom': 'Animalia', 'phylum': rec.get('phylum', ''), 'class': rec.get('class', ''), 'genus': rec.get('genus', ''),
                    'match_type_debug': f'Success_Batch_{sci}', 'nameAccordingTo': 'WoRMS'})
        row.update(extra)
        rows.append(row)

    changed = {}
    species = [(v, r) for v, r in names if r.get('taxonRank', '').lower() == 'species' and r.get('genus')]
    # one of each kind, on the first species names
    for kind, (v, r) in zip(['synonym', 'higher', 'namesake', 'missing', 'spelling'], species):
        changed[v] = kind
        lowest = v.split(';')[-1]
        if kind == 'synonym':
            add(v, r, r['genus'] + ' acceptus', 'Species', ambiguous='True', replaced_unaccepted='True',
                match_type_debug=f'Success_Batch_{lowest}')
            add(v, r, lowest, 'Species', sel='False', ambiguous='True', unaccepted_match='True')
        elif kind == 'higher':
            add(v, r, r['genus'], 'Genus', match_type_debug=f"Success_Batch_{r['genus']}")
        elif kind == 'namesake':
            add(v, r, lowest, 'Species', ambiguous='True', kingdom='Plantae', phylum='Tracheophyta', **{'class': 'Magnoliopsida'})
            add(v, r, lowest, 'Species', sel='False', ambiguous='True')
        elif kind == 'missing':
            add(v, r, 'incertae sedis', '', match_type_debug='Failed_All_Stages_NoMatch', kingdom='', phylum='', genus='',
                scientificNameID='urn:lsid:marinespecies.org:taxname:12', **{'class': ''})
        else:
            add(v, r, lowest + 'a', 'Species')
    for v, r in names:
        if v not in changed:
            add(v, r, v.split(';')[-1].replace('_', ' '), r.get('taxonRank', '').capitalize() or 'Species')
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLS, delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    return changed, len(names)


if __name__ == '__main__':
    print(make_mapping(*sys.argv[1:]))
