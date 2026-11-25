"""Make skill/faire-dataset/assets/envo-terms.tsv from a release of the Environment Ontology (ENVO).

    python skill/make_envo_terms.py path/to/envo.obo

envo.obo comes with each ENVO release (https://github.com/EnvironmentOntology/envo, or
http://purl.obolibrary.org/obo/envo.obo). ENVO is CC0. The table holds every current (not obsolete)
ENVO class: its identifier, label, branch, parents, synonyms and definition, so the skill's `envo`
command can search ENVO and `set` can check identifiers without internet access.
"""
import collections
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'faire-dataset' / 'assets' / 'envo-terms.tsv'
# The branches that matter for env_broad_scale (biomes), env_local_scale (systems and features) and
# env_medium (materials), in the order they are reported
BRANCHES = [('ENVO:00000428', 'biome'), ('ENVO:00010483', 'environmental material'),
            ('ENVO:01000254', 'environmental system'), ('ENVO:01000813', 'astronomical body part'),
            ('ENVO:01001813', 'construction')]
# Classes in none of these: material entities, or processes and qualities (not for the env_ terms)
OTHER = [('BFO:0000040', 'other material entity'), ('BFO:0000003', 'process, not for env_ terms'),
         ('PATO:0000001', 'quality, not for env_ terms')]


def clean(x):
    return re.sub(r'\s+', ' ', x.replace('\t', ' ')).strip()


def main(obo):
    text = Path(obo).read_text(encoding='utf-8')
    release = re.search(r'^data-version: (.+)$', text, re.M)
    terms = {}
    for block in text.split('\n\n'):
        if not block.startswith('[Term]'):
            continue
        d = collections.defaultdict(list)
        for ln in block.split('\n')[1:]:
            k, _, v = ln.partition(': ')
            d[k].append(v)
        terms[d['id'][0]] = d
    parents = {t: [p.split(' ')[0] for p in d.get('is_a', [])] for t, d in terms.items()}

    def ancestors(t):
        seen, todo = set(), [t]
        while todo:
            for p in parents.get(todo.pop(), []):
                if p not in seen:
                    seen.add(p)
                    todo.append(p)
        return seen

    rows = []
    for t, d in sorted(terms.items()):
        if not t.startswith('ENVO:') or 'true' in d.get('is_obsolete', []) or not d.get('name'):
            continue
        a = ancestors(t) | {t}
        branch = ('; '.join(name for root, name in BRANCHES if root in a)
                  or next((name for root, name in OTHER if root in a), 'other, not for env_ terms'))
        par = '; '.join(clean(terms[p]['name'][0]) for p in parents[t] if p in terms and terms[p].get('name'))
        syn = ' | '.join(dict.fromkeys(clean(re.match(r'"(.*?)"', s).group(1)) for s in d.get('synonym', [])
                                       if re.match(r'"(.*?)"', s)))
        df = d.get('def', [''])[0]
        m = re.match(r'"(.*)" \[', df)
        df = clean(m.group(1) if m else df.strip('"'))
        if len(df) > 260:
            df = df[:257].rsplit(' ', 1)[0] + ' ...'
        rows.append('\t'.join([t, clean(d['name'][0]), branch, par, syn, df]))
    head = (f'# ENVO {release.group(1) if release else "release unknown"}; CC0 1.0; '
            'https://github.com/EnvironmentOntology/envo. Made by skill/make_envo_terms.py.')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text('\n'.join([head, 'id\tlabel\tbranch\tparents\tsynonyms\tdefinition'] + rows) + '\n',
                   encoding='utf-8')
    print(f'{OUT}: {len(rows)} ENVO terms, {OUT.stat().st_size / 1e6:.1f} MB')


if __name__ == '__main__':
    main(sys.argv[1])
