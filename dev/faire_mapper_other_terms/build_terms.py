"""Build tools/faire_mapper/mixs_dwc_terms.tsv: the MIxS and Darwin Core terms that the FAIRe checklist
does not have, for propose mapping to suggest for columns with no FAIRe term.

Usage:
    python -I build_terms.py MIXS_YAML DWC_TERM_VERSIONS_CSV FAIRE_CHECKLIST_XLSX OUT_TSV MIXS_VERSION DWC_COMMIT

MIXS_YAML is src/mixs/schema/mixs.yaml from a MIxS release (https://github.com/GenomicsStandardsConsortium/mixs),
DWC_TERM_VERSIONS_CSV is vocabulary/term_versions.csv from https://github.com/tdwg/dwc. Only the YAML and CSV are
read; nothing from either repository is run.

What is kept:
- MIxS: the slots used by a MIxS checklist or extension (environmental package), not deprecated.
- Darwin Core: the recommended Simple Darwin Core terms in the dwc namespace, from the record-level, Event,
  Location and MaterialEntity groups. The Occurrence, Organism, Identification, Taxon and GeologicalContext
  groups describe specimens and observations, not samples, and are left out.
- Left out of both: terms the FAIRe checklist has, by name or by IRI (FAIRe's URI column), and MIxS lat_lon and
  depth, which FAIRe splits into decimalLatitude and decimalLongitude, and minimumDepthInMeters and
  maximumDepthInMeters.
"""
import csv
import re
import sys

import pandas as pd
import yaml

FAIRE_SPLITS = {'lat_lon', 'depth'}
DWC_GROUPS = {'': 'record-level', 'Event': 'Event', 'http://purl.org/dc/terms/Location': 'Location',
              'MaterialEntity': 'MaterialEntity', 'MaterialSample': 'MaterialSample'}
DWC_NUMBER = re.compile(r'(InMeters|InGrams|Value|Count|Year|DayOfYear)$|^(year|month|day)$')


def one_line(text):
    return re.sub(r'\s+', ' ', str(text or '')).strip()


def mixs_terms(path, faire_names, faire_iris):
    d = yaml.safe_load(open(path, encoding='utf-8'))
    classes, slots = d['classes'], d['slots']
    where = {}
    for name, c in classes.items():
        kind = c.get('is_a')
        if kind not in ('Extension', 'Checklist'):
            continue
        label = c.get('title') or name
        for s in list(c.get('slots') or []) + list((c.get('slot_usage') or {}).keys()):
            where.setdefault(s, {'Extension': [], 'Checklist': []})[kind].append(label)
    out = []
    for name in sorted(where):
        s = slots.get(name)
        if not s or s.get('deprecated') or name in faire_names or name in FAIRE_SPLITS:
            continue
        uri = s.get('slot_uri') or ''
        number = uri.split(':')[-1] if uri.startswith('MIXS:') else ''
        if number and number in faire_iris:
            continue
        pattern = (s.get('structured_pattern') or {}).get('syntax', '')
        kind = 'number' if ('scientific_float' in pattern and pattern.startswith('^{scientific_float}')) \
            or s.get('range') in ('float', 'integer', 'double') else 'text'
        ext = sorted(set(where[name]['Extension']))
        scope = ('extensions: ' + ', '.join(ext)) if ext else 'checklists: ' + ', '.join(sorted(set(where[name]['Checklist'])))
        examples = s.get('examples') or []
        out.append({'source': 'MIxS', 'term': name, 'id': uri, 'iri': f'https://w3id.org/mixs/{number}' if number else '',
                    'label': one_line(s.get('title') or name), 'definition': one_line(s.get('description')),
                    'unit': one_line((s.get('annotations') or {}).get('Preferred_unit', '')), 'kind': kind,
                    'scope': scope, 'example': one_line(examples[0].get('value', '') if examples else '')})
    return out


def dwc_terms(path, faire_names, faire_iris):
    tv = pd.read_csv(path, dtype=str, keep_default_na=False)
    tv = tv[(tv.status == 'recommended') & (tv['flags'] == 'simple')
            & tv.term_iri.str.startswith('http://rs.tdwg.org/dwc/terms/')
            & tv.rdf_type.str.endswith('#Property')]
    out = []
    for r in tv.sort_values('term_localName').to_dict('records'):
        group = r['organized_in'].replace('http://rs.tdwg.org/dwc/terms/', '')
        name = r['term_localName']
        if group not in DWC_GROUPS or name in faire_names or r['term_iri'] in faire_iris:
            continue
        example = re.findall(r'`([^`]+)`', r['examples'])
        out.append({'source': 'Darwin Core', 'term': name, 'id': f'dwc:{name}', 'iri': r['term_iri'],
                    'label': one_line(r['label']), 'definition': one_line(r['definition']), 'unit': '',
                    'kind': 'number' if DWC_NUMBER.search(name) else 'text', 'scope': DWC_GROUPS[group],
                    'example': example[0] if example else ''})
    return out


def main(mixs_yaml, dwc_csv, checklist, out, mixs_version, dwc_commit):
    ck = pd.read_excel(checklist, sheet_name='checklist', dtype=str).fillna('')
    faire_names = set(ck.term_name.str.strip())
    iris = set()
    for u in ck.URI:
        for part in str(u).split('|'):
            part = part.strip()
            if part:
                iris.add(part)
                m = re.search(r'mixs/(\d{7})', part)
                if m:
                    iris.add(m.group(1))
                m = re.search(r'#dwc_(\w+)$', part)
                if m:
                    iris.add(f'http://rs.tdwg.org/dwc/terms/{m.group(1)}')
    rows = mixs_terms(mixs_yaml, faire_names, iris) + dwc_terms(dwc_csv, faire_names, iris)
    cols = ['source', 'term', 'id', 'iri', 'label', 'definition', 'unit', 'kind', 'scope', 'example']
    n_mixs = sum(r['source'] == 'MIxS' for r in rows)
    with open(out, 'w', encoding='utf-8', newline='') as f:
        f.write(f'# MIxS and Darwin Core terms that the FAIRe checklist ({checklist.rsplit("/", 1)[-1]}) does not have,\n'
                f'# for FAIRe mapper to suggest for columns with no FAIRe term. {n_mixs} MIxS terms, {len(rows) - n_mixs} '
                f'Darwin Core terms.\n'
                f'# MIxS {mixs_version}, Genomic Standards Consortium, '
                f'https://github.com/GenomicsStandardsConsortium/mixs, CC0 1.0.\n'
                f'# Darwin Core, TDWG Darwin Core Maintenance Group, https://github.com/tdwg/dwc (commit {dwc_commit}),\n'
                f'# CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Terms and definitions are as published;\n'
                f'# the selection and the kind and scope columns are FAIRe mapper\'s.\n'
                f'# Built by dev/faire_mapper_other_terms/build_terms.py.\n')
        w = csv.DictWriter(f, fieldnames=cols, delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    print(f'{n_mixs} MIxS and {len(rows) - n_mixs} Darwin Core terms: {out}')


if __name__ == '__main__':
    main(*sys.argv[1:7])
