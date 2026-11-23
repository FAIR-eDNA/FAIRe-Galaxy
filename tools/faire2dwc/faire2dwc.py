"""FAIRe to Darwin Core: presence and absence records from a FAIRe workbook, as a Darwin Core archive
for a GBIF or OBIS IPT.

The archive holds an occurrence core, the DNA derived data extension (GBIF, issued 2024-07-11), the
dataset's EML and meta.xml, as the guide "Publishing DNA-derived data through biodiversity data
platforms" sets out for targeted detection (qPCR, ddPCR) and for metabarcoding taxa reported as
present.

Two kinds of workbook:
  targeted       one record per sample and assay: present when detected_notDetected is 1, absent
                 when 0. ampData, when filled, gives the number of technical replicates that
                 amplified, the mean Cq and the mean copy number.
  metabarcoding  one record per sample and sequence (taxaFinal and otuFinal) with reads or a 1:
                 taxa found in a sample are present; no absences are written, and read counts
                 are not published (FAIRe2MDT and edna2obis are the tools for read counts).

Controls (samp_category other than sample) are left out. FAIRe's missing-value terms ("missing:
...", "not applicable ...") are written as empty cells, as Darwin Core asks.

Usage: faire2dwc.py WORKBOOK --archive OUT.zip --report REPORT.md [options]; see --help.
"""

import argparse
import datetime as dt
import math
import re
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree, indent, SubElement

import pandas as pd

__version__ = '0.2.0'
HERE = Path(__file__).resolve().parent
TERMS = HERE / 'faire2dwc_terms.tsv'

LICENCES = {
    'CC0-1.0': ('http://creativecommons.org/publicdomain/zero/1.0/legalcode',
                'Public Domain (CC0 1.0)'),
    'CC-BY-4.0': ('http://creativecommons.org/licenses/by/4.0/legalcode',
                  'Creative Commons Attribution (CC-BY 4.0)'),
    'CC-BY-NC-4.0': ('http://creativecommons.org/licenses/by-nc/4.0/legalcode',
                     'Creative Commons Attribution Non Commercial (CC-BY-NC 4.0)'),
}
# INSDC country names (as geo_loc_name starts) and ISO 3166-1 codes, for the countries most eDNA
# data come from; --country_code covers the rest.
COUNTRY_CODES = {
    'australia': 'AU', 'new zealand': 'NZ', 'usa': 'US', 'united states': 'US', 'canada': 'CA',
    'united kingdom': 'GB', 'ireland': 'IE', 'france': 'FR', 'germany': 'DE', 'netherlands': 'NL',
    'belgium': 'BE', 'denmark': 'DK', 'norway': 'NO', 'sweden': 'SE', 'finland': 'FI', 'iceland': 'IS',
    'spain': 'ES', 'portugal': 'PT', 'italy': 'IT', 'switzerland': 'CH', 'austria': 'AT', 'poland': 'PL',
    'greece': 'GR', 'japan': 'JP', 'china': 'CN', 'south korea': 'KR', 'taiwan': 'TW', 'india': 'IN',
    'indonesia': 'ID', 'malaysia': 'MY', 'singapore': 'SG', 'philippines': 'PH', 'thailand': 'TH',
    'viet nam': 'VN', 'papua new guinea': 'PG', 'fiji': 'FJ', 'new caledonia': 'NC', 'south africa': 'ZA',
    'kenya': 'KE', 'brazil': 'BR', 'argentina': 'AR', 'chile': 'CL', 'peru': 'PE', 'colombia': 'CO',
    'mexico': 'MX', 'antarctica': 'AQ',
}
# Labels for the counts in the report (one, several)
COUNT_LABELS = {
    'present': ('present', 'present'), 'absent': ('absent', 'absent'),
    'not written': ('sample not written (detection missing or not applicable)',
                    'samples not written (detection missing or not applicable)'),
    'from ampData': ('detection taken from ampData', 'detections taken from ampData'),
    'detections with no taxon name': ('detection with no taxon name', 'detections with no taxon name'),
    'control columns': ('control column', 'control columns'),
    'columns not in sampleMetadata': ('column not in sampleMetadata', 'columns not in sampleMetadata'),
}
MISSING_RE = re.compile(r'^\s*(missing|not applicable|not collected|not provided|restricted access)\b', re.I)
NO_CQ = {'undetermined', 'no ct', 'no cq', 'n/a', 'na', 'nan', 'none', '-', ''}


class StopError(Exception):
    pass


# ---------------------------------------------------------------- reading the workbook

def blank(v):
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    return str(v).strip() == ''


def clean(v):
    """A cell as Darwin Core text: empty for FAIRe's missing-value terms, dates as ISO 8601,
    whole numbers without '.0'."""
    if blank(v):
        return ''
    if isinstance(v, (dt.datetime, pd.Timestamp)):
        ts = pd.Timestamp(v)
        return ts.date().isoformat() if ts == ts.normalize() else ts.isoformat()
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    s = re.sub(r'[\t\r\n]+', ' ', str(v)).strip()
    if MISSING_RE.match(s):
        return ''
    # FAIRe writes a value outside a controlled vocabulary as 'other: <value>'; Darwin Core takes the value
    return re.sub(r'^other:\s*', '', s, flags=re.I)


def number(v):
    if blank(v):
        return None
    try:
        x = float(str(v).strip())
    except ValueError:
        return None
    return None if math.isnan(x) else x


def fmt(x, places=2):
    if x is None:
        return ''
    s = f'{x:.{places}f}'.rstrip('0').rstrip('.')
    return s


def read_sheet(path, name, key):
    """A FAIRe sheet as a DataFrame of text, with the header row (the first row holding `key`, below
    any rows of requirement levels and sections) as the column names."""
    raw = pd.read_excel(path, sheet_name=name, header=None, dtype=object)
    for i in range(min(len(raw), 10)):
        cells = [str(x).strip() for x in raw.iloc[i].tolist()]
        if key in cells:
            df = raw.iloc[i + 1:].copy()
            df.columns = [c if c and c != 'nan' else f'_col{j}' for j, c in enumerate(cells)]
            df = df.loc[:, ~pd.Index(df.columns).duplicated()]
            return df.dropna(how='all').reset_index(drop=True)
    raise StopError(f"the {name} sheet has no '{key}' column in its first 10 rows")


def read_project(path, sheets):
    """projectMetadata: values for the whole project, and each assay's values (its own column first,
    then project_level). Reads the FAIRe-ator layout (assay1, assay2 ... named by the assay_name row),
    the FAIRe-NOAA layout (columns headed by the assay names) and a single assay in project_level."""
    if 'projectMetadata' not in sheets:
        raise StopError('the workbook has no projectMetadata sheet')
    pm = read_sheet(path, 'projectMetadata', 'term_name')
    if 'project_level' not in pm.columns:
        raise StopError("projectMetadata has no project_level column")
    cols = list(pm.columns)
    assay_cols = [c for c in cols[cols.index('project_level') + 1:] if not c.startswith('_col')]
    rows = {str(r['term_name']).strip(): r for _, r in pm.iterrows() if not blank(r['term_name'])}
    project = {t: r['project_level'] for t, r in rows.items() if not blank(r['project_level'])}
    assays = {}
    names_row = rows.get('assay_name')
    for c in assay_cols:
        name = c
        if names_row is not None and not blank(names_row[c]) and re.fullmatch(r'assay\d+', c):
            name = str(names_row[c]).strip()
        elif re.fullmatch(r'assay\d+', c):
            continue   # an empty FAIRe-ator assay column
        assays[name] = {t: r[c] for t, r in rows.items() if not blank(r[c])}
    if not assays:
        name = clean(project.get('assay_name'))
        if not name:
            raise StopError('projectMetadata names no assay (assay_name)')
        for one in [x.strip() for x in name.split('|') if x.strip()]:
            assays[one] = {}
    for a in assays:
        assays[a] = {**project, **assays[a], 'assay_name': a}
    return project, assays


def sheets_named(sheets, base):
    return [s for s in sheets if s == base or s.startswith(base + '_')]


# ---------------------------------------------------------------- records

def country_of(geo, code_given, notes):
    country = geo.split(':', 1)[0].strip() if geo else ''
    locality = geo.split(':', 1)[1].strip(' ,') if ':' in geo else ''
    code = code_given or COUNTRY_CODES.get(country.lower(), '')
    if country and not code and ('country', country) not in notes:
        notes.add(('country', country))
    if country.lower().endswith('ocean') or country.lower().endswith('sea'):
        return '', '', geo.strip()
    return country, code, locality


def taxon_table(path):
    """The optional taxon table: one row per name as the workbook gives it (name), with the Darwin
    Core values to publish for it."""
    if not path:
        return {}
    with open(path, encoding='utf-8-sig') as f:
        first = f.readline()
    sep = '\t' if '\t' in first else ','
    df = pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False, encoding='utf-8-sig')
    if 'name' not in df.columns:
        raise StopError("the taxon table needs a column called 'name' (the name as the workbook gives it)")
    return {str(r['name']).strip(): {k: str(v).strip() for k, v in r.items() if k != 'name' and str(v).strip()}
            for _, r in df.iterrows()}


def taxon_values(name, row, table):
    """Darwin Core taxon values for one name: the taxon table's, else the workbook's (taxaFinal)."""
    out = {}
    if row is not None:
        for t in ('kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'taxonRank',
                  'verbatimIdentification', 'identificationRemarks'):
            out[t] = clean(row.get(t))
        tid, db = clean(row.get('taxonID')), clean(row.get('taxonID_db')).lower()
        if tid.startswith(('urn:lsid:', 'http')):
            out['scientificNameID'] = tid
        elif tid.isdigit() and 'worms' in db:
            out['scientificNameID'] = f'urn:lsid:marinespecies.org:taxname:{tid}'
    out['scientificName'] = name
    out.update(table.get(name, {}))
    return out


def amp_summary(path, sheets, notes):
    """(samp_name, assay_name) -> replicates, amplified, mean Cq of those that amplified, mean copies
    and their unit, from the ampData sheets."""
    out = {}
    for s in sheets_named(sheets, 'ampData'):
        df = read_sheet(path, s, 'samp_name')
        default_assay = s[len('ampData_'):] if s.startswith('ampData_') else ''
        for _, r in df.iterrows():
            samp = clean(r.get('samp_name'))
            if not samp:
                continue
            assay = clean(r.get('assay_name')) or default_assay
            cq_text = '' if blank(r.get('quantificationCycle')) else str(r.get('quantificationCycle')).strip()
            cq = number(cq_text)
            if cq is not None and cq <= 0:
                notes.add(('cq_zero', f'{samp} ({assay})'))
                cq = None
            elif cq is None and cq_text.lower() not in NO_CQ and not MISSING_RE.match(cq_text):
                notes.add(('cq_text', cq_text))
            d = out.setdefault((samp, assay), {'n': 0, 'amp': 0, 'cq': [], 'copies': [], 'unit': ''})
            d['n'] += 1
            if cq is not None:
                d['amp'] += 1
                d['cq'].append(cq)
            copies = number(r.get('estimatedNumberOfCopies'))
            if copies is not None:
                d['copies'].append(copies)
                d['unit'] = d['unit'] or clean(r.get('estimatedNumberOfCopies_unit'))
    return out


def detection_column(sm, assay, n_assays):
    for c in (f'detected_notDetected_{assay}', 'detected_notDetected' if n_assays == 1 else None):
        if c and c in sm.columns:
            return c
    return None


def otu_tables(path, sheets, assays):
    """(assay, run, otuFinal frame indexed by seq_id, taxaFinal rows by seq_id) for each otuFinal sheet:
    otuFinal, otuFinal_<assay>, or otuFinal_<assay>_<run> for an assay sequenced in several runs."""
    out = []
    finals = sheets_named(sheets, 'otuFinal')
    for s in finals:
        suffix = s[len('otuFinal_'):] if s != 'otuFinal' else ''
        assay, run = suffix, ''
        if not suffix and len(assays) == 1:
            assay = next(iter(assays))
        elif suffix not in assays:
            match = sorted((a for a in assays if suffix.startswith(f'{a}_')), key=len, reverse=True)
            if match:
                assay, run = match[0], suffix[len(match[0]) + 1:]
        if assay not in assays:
            continue
        otu = read_sheet(path, s, 'seq_id').set_index('seq_id')
        tname = 'taxaFinal' + (f'_{suffix}' if suffix else '')
        if tname not in sheets:
            raise StopError(f'{s} has no taxonomy sheet ({tname})')
        taxa = read_sheet(path, tname, 'seq_id')
        out.append((assay, run, otu, {clean(r['seq_id']): r for _, r in taxa.iterrows() if clean(r['seq_id'])}))
    return out


def lowest_name(row):
    name = clean(row.get('scientificName'))
    if name:
        return name
    for t in ('genus', 'family', 'order', 'class', 'phylum', 'kingdom'):
        if clean(row.get(t)):
            return clean(row.get(t))
    return ''


# ---------------------------------------------------------------- main conversion

def convert(args):
    path = args.workbook
    sheets = pd.ExcelFile(path).sheet_names
    notes = set()
    log = []
    project, assays = read_project(path, sheets)
    assay_type = clean(project.get('assay_type')).lower() or ('targeted' if sheets_named(sheets, 'ampData') else
                                                              'metabarcoding')
    if args.assays:
        wanted = [a.strip() for a in args.assays.split(',') if a.strip()]
        unknown = [a for a in wanted if a not in assays]
        if unknown:
            raise StopError(f"assay {', '.join(unknown)} is not in projectMetadata (assays: {', '.join(assays)})")
        assays = {a: assays[a] for a in wanted}
    project_id = clean(project.get('project_id')) or Path(path).stem
    sm = read_sheet(path, 'sampleMetadata', 'samp_name')
    sm = sm[sm['samp_name'].map(lambda v: not blank(v))]
    terms = pd.read_csv(TERMS, sep='\t', comment='#', dtype=str, keep_default_na=False)
    table = taxon_table(args.taxa)

    cats = sm['samp_category'].map(clean).str.lower() if 'samp_category' in sm.columns else pd.Series(['sample'] * len(sm))
    is_sample = cats.eq('sample') | cats.eq('')
    controls = sm[~is_sample.values]
    samples = sm[is_sample.values]
    log.append(f'{len(sm)} rows in sampleMetadata: {len(samples)} samples, {len(controls)} '
               f'control{"s" if len(controls) != 1 else ""} left out'
               + (f" ({', '.join(f'{v} {k}' for k, v in controls['samp_category'].map(clean).value_counts().items())})"
                  if len(controls) else ''))
    if cats.eq('').any():
        log.append(f'{int(cats.eq("").sum())} rows have no samp_category; they are taken as samples')

    def sample_value(r, term):
        return clean(r.get(term)) if term in r.index else ''

    def sample_fields(r, file):
        out = {}
        for t in terms[(terms.file == file) & (terms.source == 'sample')].itertuples():
            v = sample_value(r, t.faire_term)
            if v and t.unit and not t.unit.startswith('['):
                u = sample_value(r, t.unit)
                v = f'{v} {u}' if u else v
            out[t.dwc_term] = v
        return out

    def project_fields(values, file):
        out = {}
        for t in terms[(terms.file == file) & (terms.source == 'project')].itertuples():
            v = clean(values.get(t.faire_term))
            if v and t.unit and not t.unit.startswith('['):
                u = clean(values.get(t.unit))
                v = f'{v} {u}' if u else v
            out[t.dwc_term] = v
        return out

    def common(r, values):
        occ = sample_fields(r, 'occurrence')
        occ.update({k: v for k, v in project_fields(values, 'occurrence').items() if v})
        geo = sample_value(r, 'geo_loc_name')
        occ['country'], occ['countryCode'], occ['locality'] = country_of(geo, args.country_code, notes)
        if occ.get('decimalLatitude') and occ.get('decimalLongitude'):
            occ['geodeticDatum'] = 'WGS84'
        samp = sample_value(r, 'samp_name')
        occ['eventID'] = f'{project_id}_{samp}'
        occ['materialSampleID'] = sample_value(r, 'materialSampleID') or samp
        occ['basisOfRecord'] = 'MaterialSample'
        dna = sample_fields(r, 'dna')
        dna.update({k: v for k, v in project_fields(values, 'dna').items() if v})
        refs = [clean(values.get('pcr_primer_reference_forward')), clean(values.get('pcr_primer_reference_reverse'))]
        refs = list(dict.fromkeys(x for x in refs if x))
        dna['pcr_primer_reference'] = ' | '.join(refs)
        if dna.get('annealingTemp'):
            dna['annealingTempUnit'] = 'Degrees Celsius'
        if dna.get('amplificationReactionVolume'):
            dna['amplificationReactionVolumeUnit'] = 'µl'
        neg = clean(values.get('neg_cont_0_1'))
        dna['contaminationAssessment'] = {'1': 'true', '0': 'false'}.get(neg, '')
        return occ, dna

    occurrences, dna_rows = [], []
    counts = {}
    if assay_type == 'targeted':
        amp = amp_summary(path, sheets, notes) if sheets_named(sheets, 'ampData') else {}
        for assay, values in assays.items():
            target = clean(values.get('targetTaxonomicAssay'))
            if not target:
                raise StopError(f'targetTaxonomicAssay is empty for {assay}: it names the taxon each record is about')
            col = detection_column(sm, assay, len(assays))
            c = counts.setdefault(assay, {'present': 0, 'absent': 0, 'not written': 0, 'from ampData': 0})
            for _, r in samples.iterrows():
                samp = clean(r['samp_name'])
                a = amp.get((samp, assay))
                cell = r.get(col) if col else None
                det = clean(cell)
                if blank(cell) and a is not None:
                    # No detection given: at least one replicate that amplified counts as detected.
                    # A missing-value term ("missing: not provided") is left as the workbook says.
                    det = '1' if a['amp'] else '0'
                    c['from ampData'] += 1
                if det not in ('0', '1'):
                    c['not written'] += 1
                    continue
                if det == '0' and not args.absences:
                    c['not written'] += 1
                    continue
                occ, dna = common(r, values)
                status = 'present' if det == '1' else 'absent'
                c[status] += 1
                occ['occurrenceID'] = f'{project_id}_{samp}_{assay}'
                occ['occurrenceStatus'] = status
                occ.update(taxon_values(target, None, table))
                remark = f'{"Detected" if det == "1" else "Not detected"} by the {assay} assay'
                if a is not None:
                    remark += (f'; target DNA amplified in {a["amp"]} of {a["n"]} technical replicate'
                               f'{"s" if a["n"] != 1 else ""}')
                    if a['cq']:
                        dna['quantificationCycle'] = fmt(sum(a['cq']) / len(a['cq']))
                        remark += f' (mean Cq {dna["quantificationCycle"]})'
                    if a['copies']:
                        mean = sum(a['copies']) / len(a['copies'])
                        dna['estimatedNumberOfCopies'] = fmt(mean, 4)
                        occ['organismQuantity'] = fmt(mean, 4)
                        occ['organismQuantityType'] = (f'DNA copies ({a["unit"]})' if a['unit'] else 'DNA copies')
                criteria = clean(values.get('detection_criteria'))
                if criteria:
                    remark += f'. Detection criteria: {criteria}'
                occ['occurrenceRemarks'] = remark
                dna['occurrenceID'] = occ['occurrenceID']
                occurrences.append(occ)
                dna_rows.append(dna)
    else:
        tables = otu_tables(path, sheets, assays)
        if not tables:
            raise StopError('a metabarcoding workbook needs otuFinal and taxaFinal sheets (one pair per assay)')
        runs = {}
        if 'experimentRunMetadata' in sheets:
            erm = read_sheet(path, 'experimentRunMetadata', 'samp_name')
            for _, r in erm.iterrows():
                if clean(r.get('lib_id')):
                    runs[(clean(r.get('lib_id')))] = clean(r['samp_name'])
        by_name = {clean(r['samp_name']): r for _, r in samples.iterrows()}
        control_names = {clean(x) for x in controls['samp_name']}
        several = {a for a, *_ in tables if sum(1 for x, *_ in tables if x == a) > 1}
        for assay, run, otu, taxa in tables:
            values = assays[assay]
            c = counts.setdefault(assay, {'present': 0, 'detections with no taxon name': 0, 'control columns': 0,
                                          'columns not in sampleMetadata': 0})
            for col in otu.columns:
                if str(col).startswith('_col'):
                    continue
                samp = str(col) if str(col) in by_name or str(col) in control_names else runs.get(str(col), '')
                if samp in control_names:
                    c['control columns'] += 1
                    continue
                if samp not in by_name:
                    c['columns not in sampleMetadata'] += 1
                    continue
                r = by_name[samp]
                for seq_id, v in otu[col].items():
                    reads = number(v)
                    if not reads or reads <= 0:
                        continue
                    row = taxa.get(clean(seq_id))
                    name = lowest_name(row) if row is not None else ''
                    if not name:
                        c['detections with no taxon name'] += 1
                        continue
                    occ, dna = common(r, values)
                    part = f'{assay}_{run}' if assay in several and run else assay
                    occ['occurrenceID'] = f'{project_id}_{samp}_{part}_{clean(seq_id)}'
                    occ['occurrenceStatus'] = 'present'
                    occ.update(taxon_values(name, row, table))
                    seq = clean(row.get('dna_sequence')) if row is not None else ''
                    if clean(seq_id).replace('_', ' ').lower() == name.lower():   # reads summed per taxon
                        occ['occurrenceRemarks'] = f'Detected by the {assay} assay'
                    elif seq:
                        occ['occurrenceRemarks'] = f'Detected by the {assay} assay (sequence {clean(seq_id)})'
                    else:
                        occ['occurrenceRemarks'] = f'Detected by the {assay} assay (as {clean(seq_id)} in otuFinal)'
                    if seq and re.fullmatch(r'[ACGTUNRYSWKMBDHV]+', seq.upper()):
                        dna['DNA_sequence'] = seq
                    dna['occurrenceID'] = occ['occurrenceID']
                    occurrences.append(occ)
                    dna_rows.append(dna)
                    c['present'] += 1
    if not occurrences:
        raise StopError('no records to write: check samp_category, the detections and the assays chosen')
    return {'project': project, 'project_id': project_id, 'assays': assays, 'assay_type': assay_type,
            'occurrences': occurrences, 'dna': dna_rows, 'counts': counts, 'log': log, 'notes': notes,
            'terms': terms, 'samples': len(samples)}


# ---------------------------------------------------------------- writing

def columns_used(rows, terms, file):
    """The terms of this file with a value in any row, in the order of the terms table (the ID first)."""
    order = list(terms[terms.file == file].dwc_term)
    used = {k for r in rows for k, v in r.items() if v}
    return [t for t in order if t in used or t == 'occurrenceID']


def write_tsv(rows, cols, out):
    # Values have no tabs or line breaks (clean() turns them into spaces), so the table needs no quoting,
    # as meta.xml says (fieldsEnclosedBy is empty).
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\t'.join(cols) + '\n')
        for r in rows:
            f.write('\t'.join(re.sub(r'[\t\r\n]+', ' ', str(r.get(c, ''))) for c in cols) + '\n')


def write_xml(root, out):
    """Indented XML that keeps mixed content (the licence sentence and its link) as written."""
    indent(root, space='  ')
    ElementTree(root).write(out, encoding='utf-8', xml_declaration=True)


def meta_xml(occ_cols, dna_cols, terms, out):
    uri = {(r.file, r.dwc_term): r.uri for r in terms.itertuples()}
    archive = Element('archive', {'xmlns': 'http://rs.tdwg.org/dwc/text/', 'metadata': 'eml.xml'})
    for tag, file, cols, row_type, name in (
            ('core', 'occurrence', occ_cols, 'http://rs.tdwg.org/dwc/terms/Occurrence', 'occurrence.txt'),
            ('extension', 'dna', dna_cols, 'http://rs.gbif.org/terms/1.0/DNADerivedData', 'dna_derived_data.txt')):
        if not cols:
            continue
        e = SubElement(archive, tag, {'encoding': 'UTF-8', 'fieldsTerminatedBy': '\\t', 'linesTerminatedBy': '\\n',
                                      'fieldsEnclosedBy': '', 'ignoreHeaderLines': '1', 'rowType': row_type})
        SubElement(SubElement(e, 'files'), 'location').text = name
        SubElement(e, 'id' if tag == 'core' else 'coreid', {'index': str(cols.index('occurrenceID'))})
        for i, c in enumerate(cols):
            if tag == 'extension' and c == 'occurrenceID':
                continue
            SubElement(e, 'field', {'index': str(i), 'term': uri[(file, c)]})
    write_xml(archive, out)


def licence_of(text):
    """The GBIF licence a projectMetadata license value names (a URL or a name such as CC BY 4.0), or ''."""
    t = re.sub(r'^https?://|/legalcode$|/$', '', text.strip().lower())
    t = re.sub(r'[\s_]+', '-', t)
    if not t:
        return ''
    if 'zero' in t or t.startswith('cc0'):
        return 'CC0-1.0'
    if 'by-nc/4.0' in t or t.startswith('cc-by-nc-4'):
        return 'CC-BY-NC-4.0'
    if 'licenses/by/4.0' in t or t in ('cc-by-4.0', 'cc-by'):
        return 'CC-BY-4.0'
    return ''


def contact_of(project):
    """Name and email from project_contact ('Name (email)', 'Name, email' or 'Name | email')."""
    text = clean(project.get('project_contact'))
    m = re.search(r'[\w.+-]+@[\w-]+(\.[\w-]+)+', text)
    email = m.group(0) if m else ''
    name = re.sub(r'\s+', ' ', text.replace(email, '') if email else text)
    name = re.sub(r'(mailto:|[()<>\[\]|,;:])', ' ', name).strip()
    name = re.sub(r'\s+', ' ', name)
    return name, email


def eml_xml(args, res, out):
    occ = res['occurrences']
    project = res['project']
    title = args.title or clean(project.get('project_name')) or res['project_id']
    licence = args.licence
    if not licence:
        licence = licence_of(clean(project.get('license')))
    ns = {'xmlns:eml': 'https://eml.ecoinformatics.org/eml-2.2.0', 'xmlns:dc': 'http://purl.org/dc/terms/',
          'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
          'xsi:schemaLocation': 'https://eml.ecoinformatics.org/eml-2.2.0 '
                                'https://rs.gbif.org/schema/eml-gbif-profile/1.3/eml.xsd',
          'packageId': str(uuid.uuid5(uuid.NAMESPACE_URL, f'faire2dwc:{res["project_id"]}')),
          'system': 'http://gbif.org', 'scope': 'system', 'xml:lang': 'en'}
    root = Element('eml:eml', ns)
    ds = SubElement(root, 'dataset')
    SubElement(ds, 'title', {'xml:lang': 'en'}).text = title

    given, surname, email = args.given_name, args.surname, args.email
    organisation = args.organisation
    if not (given or surname or organisation):
        name, contact_email = contact_of(project)
        if name:
            given, _, surname = name.rpartition(' ')
        email = email or contact_email
        organisation = clean(project.get('institution'))
        if name or contact_email:
            res['contact'] = (given, surname, email, organisation)

    def party(tag):
        p = SubElement(ds, tag)
        if given or surname:
            ind = SubElement(p, 'individualName')
            if given:
                SubElement(ind, 'givenName').text = given
            SubElement(ind, 'surName').text = surname or given
        if organisation or not (given or surname):
            SubElement(p, 'organizationName').text = organisation or 'not given'
        if email:
            SubElement(p, 'electronicMailAddress').text = email
        if args.orcid:
            SubElement(p, 'userId', {'directory': 'https://orcid.org/'}).text = args.orcid.split('orcid.org/')[-1]
    party('creator')
    party('metadataProvider')
    SubElement(ds, 'pubDate').text = dt.date.today().isoformat()
    SubElement(ds, 'language').text = 'eng'
    abstract = args.abstract or (f'Environmental DNA detections from the FAIRe workbook of project '
                                 f'{res["project_id"]} ({res["assay_type"]} assays: {", ".join(res["assays"])}).')
    SubElement(SubElement(ds, 'abstract'), 'para').text = abstract
    ks = SubElement(ds, 'keywordSet')
    for k in ['environmental DNA', 'eDNA', res['assay_type']] + [x.strip() for x in (args.keywords or '').split(',')
                                                                 if x.strip()]:
        SubElement(ks, 'keyword').text = k
    SubElement(ks, 'keywordThesaurus').text = 'N/A'
    if licence:
        url, label = LICENCES[licence]
        para = SubElement(SubElement(ds, 'intellectualRights'), 'para')
        para.text = 'This work is licensed under a '
        ul = SubElement(para, 'ulink', {'url': url})
        SubElement(ul, 'citetitle').text = f'{label} License'
        ul.tail = '.'
    cov = SubElement(ds, 'coverage')
    lats = [number(o.get('decimalLatitude')) for o in occ]
    lons = [number(o.get('decimalLongitude')) for o in occ]
    lats, lons = [x for x in lats if x is not None], [x for x in lons if x is not None]
    if lats and lons:
        g = SubElement(cov, 'geographicCoverage')
        places = sorted({o.get('locality') or o.get('country') for o in occ if o.get('locality') or o.get('country')})
        SubElement(g, 'geographicDescription').text = '; '.join(places) or 'See the records'
        b = SubElement(g, 'boundingCoordinates')
        for tag, v in (('westBoundingCoordinate', min(lons)), ('eastBoundingCoordinate', max(lons)),
                       ('northBoundingCoordinate', max(lats)), ('southBoundingCoordinate', min(lats))):
            SubElement(b, tag).text = fmt(v, 6)
    dates = sorted(d[:10] for d in (o.get('eventDate', '') for o in occ) if re.match(r'\d{4}-\d{2}-\d{2}', d))
    if dates:
        r = SubElement(SubElement(cov, 'temporalCoverage'), 'rangeOfDates')
        SubElement(SubElement(r, 'beginDate'), 'calendarDate').text = dates[0]
        SubElement(SubElement(r, 'endDate'), 'calendarDate').text = dates[-1]
    names = sorted({(o.get('scientificName'), o.get('taxonRank', '')) for o in occ if o.get('scientificName')})
    if names:
        tc = SubElement(cov, 'taxonomicCoverage')
        for name, rank in names[:200]:
            t = SubElement(tc, 'taxonomicClassification')
            if rank:
                SubElement(t, 'taxonRankName').text = rank
            SubElement(t, 'taxonRankValue').text = name
    party('contact')
    methods = SubElement(ds, 'methods')
    steps = []
    for assay, values in res['assays'].items():
        bits = [f'Assay {assay}']
        for label, term in (('target', 'targetTaxonomicAssay'), ('gene', 'target_gene'),
                            ('detection', 'amp_vis_method'), ('detection criteria', 'detection_criteria')):
            if clean(values.get(term)):
                bits.append(f'{label}: {clean(values.get(term))}')
        steps.append('; '.join(bits) + '.')
    steps.append('Converted from a FAIRe workbook (https://fair-edna.github.io/) with FAIRe to Darwin Core '
                 f'{__version__}; controls are not published.')
    for s in steps:
        SubElement(SubElement(SubElement(methods, 'methodStep'), 'description'), 'para').text = s
    sampling = SubElement(methods, 'sampling')
    extent = SubElement(SubElement(sampling, 'studyExtent'), 'description')
    SubElement(extent, 'para').text = f'{res["samples"]} samples; {len(occ)} records.'
    SubElement(SubElement(sampling, 'samplingDescription'), 'para').text = (
        clean(project.get('samp_collect_method')) or 'Environmental DNA samples; see the records.')
    write_xml(root, out)
    return licence


def checks(args, res, licence):
    """What GBIF and OBIS need that the records lack."""
    occ = res['occurrences']
    out = []

    def missing(term):
        return sum(1 for o in occ if not o.get(term))
    for term, who in (('eventDate', 'GBIF and OBIS (required)'), ('scientificName', 'GBIF and OBIS (required)'),
                      ('countryCode', 'GBIF (required when known)'),
                      ('decimalLatitude', 'GBIF (highly recommended), OBIS (required)'),
                      ('kingdom', 'GBIF (highly recommended)')):
        k = missing(term)
        if k:
            out.append(f'{term} is empty in {k} of {len(occ)} records: needed by {who}')
    if args.target in ('obis', 'both'):
        k = missing('scientificNameID')
        if k:
            out.append(f'scientificNameID is empty in {k} of {len(occ)} records: OBIS needs a WoRMS LSID for '
                       f'each name (give it in the taxon table)')
    if not licence:
        out.append('no licence: GBIF needs CC0 1.0, CC BY 4.0 or CC BY-NC 4.0 (set it on the form, or license '
                   'in projectMetadata)')
    if not (args.given_name or args.surname or args.organisation or res.get('contact')):
        out.append('no creator or contact: the EML uses the institution from projectMetadata; give a name and '
                   'email before publishing')
    if res['assay_type'] == 'targeted' and any(not d.get('pcr_primer_forward') for d in res['dna']):
        out.append('pcr_primer_forward is empty for some records (highly recommended for qPCR and ddPCR)')
    return out


def report(args, res, licence, problems, out):
    lines = [f'# FAIRe to Darwin Core {__version__}', '',
             f'Workbook: {args.workbook_name or Path(args.workbook).name}  ',
             f'Project: {res["project_id"]} ({res["assay_type"]})  ',
             f'Licence: {licence or "not given"}', '', '## Records', '']
    lines += [f'- {x}' for x in res['log']]
    for assay, c in res['counts'].items():
        parts = [f'{v} {COUNT_LABELS[k][v != 1]}' for k, v in c.items() if v or k == 'present']
        lines.append(f'- {assay}: ' + ', '.join(parts))
    lines.append(f'- {len(res["occurrences"])} occurrence records and {len(res["dna"])} DNA derived data rows')
    lines += ['', '## What GBIF and OBIS will want', '']
    lines += [f'- {p}' for p in problems] or ['- Nothing missing from the checks this tool makes.']
    notes = res['notes']
    extra = []
    for kind, v in sorted(notes):
        if kind == 'country':
            extra.append(f"countryCode: no code known for '{v}'; give it with the country code option")
        elif kind == 'cq_zero':
            extra.append(f'a Cq of 0 (read as no amplification) in {v}')
        elif kind == 'cq_text':
            extra.append(f"quantificationCycle '{v}' is not a number; read as no amplification")
    if res.get('contact'):
        given, surname, email, organisation = res['contact']
        if surname:
            extra.insert(0, f'creator and contact from project_contact: given name {given or "(none)"}, surname '
                            f'{surname}{", " + email if email else ""}. Check the name is split correctly, and '
                            'add the other authors in the IPT')
        elif organisation:
            extra.insert(0, f'creator and contact: {organisation}, with the email in project_contact ({email}). '
                            'Give the person\'s name on the form, or add it and the other authors in the IPT')
        else:
            extra.insert(0, f'creator and contact: only the email in project_contact ({email}), as projectMetadata '
                            'has no institution. Give the name and organisation on the form, or add them in the IPT')
    if extra:
        lines += ['', '## Notes', ''] + [f'- {x}' for x in extra]
    occ_cols = columns_used(res['occurrences'], res['terms'], 'occurrence')
    dna_cols = columns_used(res['dna'], res['terms'], 'dna')
    lines += ['', '## Columns written', '', f'occurrence.txt: {", ".join(occ_cols)}', '',
              f'dna_derived_data.txt: {", ".join(dna_cols)}', '',
              'Before publishing: check the records in the IPT, which validates the archive, and confirm the '
              'dataset metadata (EML).']
    Path(out).write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('workbook', help='FAIRe workbook (xlsx)')
    ap.add_argument('--version', action='version', version=__version__)
    ap.add_argument('--workbook_name', help='name of the workbook for the report')
    ap.add_argument('--assays', help='assays to publish, comma-separated (default all)')
    ap.add_argument('--absences', action=argparse.BooleanOptionalAction, default=True,
                    help='targeted assays: write absent records for samples where the target was not detected')
    ap.add_argument('--taxa', help='taxon table (CSV or TSV): name, then any of scientificName, '
                                   'scientificNameID, taxonRank, kingdom, phylum, class, order, family, genus')
    ap.add_argument('--country_code', default='', help='ISO 3166-1 two-letter code, when geo_loc_name is not enough')
    ap.add_argument('--target', choices=['gbif', 'obis', 'both'], default='gbif',
                    help='which checks to report: GBIF, OBIS or both')
    ap.add_argument('--title', default='')
    ap.add_argument('--abstract', default='')
    ap.add_argument('--keywords', default='')
    ap.add_argument('--licence', choices=sorted(LICENCES), default=None)
    ap.add_argument('--given_name', default='')
    ap.add_argument('--surname', default='')
    ap.add_argument('--organisation', default='')
    ap.add_argument('--email', default='')
    ap.add_argument('--orcid', default='')
    ap.add_argument('--archive', required=True, help='Darwin Core archive to write (zip)')
    ap.add_argument('--occurrence', help='also write the occurrence table here')
    ap.add_argument('--dna', help='also write the DNA derived data table here')
    ap.add_argument('--eml', help='also write eml.xml here')
    ap.add_argument('--report', required=True, help='report (markdown)')
    args = ap.parse_args(argv)
    args.country_code = args.country_code.strip().upper()
    if args.country_code and not re.fullmatch(r'[A-Z]{2}', args.country_code):
        print(f"ERROR: the country code '{args.country_code}' is not two letters (ISO 3166-1)", file=sys.stderr)
        return 2
    try:
        res = convert(args)
    except StopError as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 2
    tmp = tempfile.TemporaryDirectory()
    work = Path(tmp.name)
    occ_cols = columns_used(res['occurrences'], res['terms'], 'occurrence')
    dna_cols = columns_used(res['dna'], res['terms'], 'dna')
    write_tsv(res['occurrences'], occ_cols, work / 'occurrence.txt')
    write_tsv(res['dna'], dna_cols, work / 'dna_derived_data.txt')
    licence = eml_xml(args, res, work / 'eml.xml')
    meta_xml(occ_cols, dna_cols, res['terms'], work / 'meta.xml')
    with zipfile.ZipFile(args.archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in ('meta.xml', 'eml.xml', 'occurrence.txt', 'dna_derived_data.txt'):
            z.write(work / name, name)
    for opt, name in ((args.occurrence, 'occurrence.txt'), (args.dna, 'dna_derived_data.txt'),
                      (args.eml, 'eml.xml')):
        if opt:
            Path(opt).write_bytes((work / name).read_bytes())
    tmp.cleanup()
    problems = checks(args, res, licence)
    report(args, res, licence, problems, args.report)
    print(f'{len(res["occurrences"])} records written to {args.archive}'
          + (f'; {len(problems)} thing{"s" if len(problems) != 1 else ""} to check before publishing (see the '
             f'report)' if problems else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
