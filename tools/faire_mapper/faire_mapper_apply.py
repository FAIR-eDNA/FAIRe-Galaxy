"""faire_mapper_apply: write a FAIRe workbook from a table and its crosswalk.

Reads the user's table and the crosswalk written by `faire_mapper.py map` (SSSOM TSV, after review),
and writes a workbook in the layout FAIRe-ator makes: README, projectMetadata, sampleMetadata and the
sheets for the assay type, with the drop-down values. Each mapped column is written to its FAIRe
term, with these conversions:

  * dates to ISO 8601 (stops when day-first and month-first readings both fit, unless told which);
  * durations to ISO 8601 (2 days, or 316 under a "Days frozen" header, become P2D and P316D);
  * a number and its unit in one cell ("1 L") split into the term and its unit term, or the number
    kept, and converted where the term has a fixed unit (mm to µm);
  * several columns combined into one value (geo_loc_name: "Country: region, locality");
  * yes/no to 1/0, allowed values to the checklist's spelling, INSDC country names;
  * a column with one value for a project-level term written once to projectMetadata.

Columns with no skos:exactMatch row in the crosswalk are kept as user-defined fields. Library tables
(run reports from ENA or the SRA, or a lab's run sheet) fill experimentRunMetadata. A log lists every
change, every value that could not be converted, and the mandatory terms still empty.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import math
import re
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, str(Path(__file__).resolve().parent))
import faire_mapper as fm  # noqa: E402
import faire_mapper_kinds as fk  # noqa: E402
import faire_mapper_library as fl  # noqa: E402
import faire_mapper_otu as fo  # noqa: E402

__version__ = fm.__version__
CHECKLIST_NAME = 'FAIRe_checklist_v1.0.2.xlsx'
# The checklist defines checkls_ver as a number (example 1.2) and FAIRe-fier rejects anything else,
# so write the major version, as the FAIRe example workbooks do. The README sheet names the exact file.
CHECKLIST_NUMBER = 1
SECTIONS_OUT = {'metabarcoding': ('Targeted assay detection',),
                'targeted': ('Library preparation sequencing', 'Bioinformatics', 'OTU/ASV')}
OTHER_SHEETS = {'metabarcoding': ('experimentRunMetadata', 'taxaRaw', 'taxaFinal'),
                'targeted': ('stdData', 'eLowQuantData', 'ampData')}
LEVEL_FILL = {'M': 'F4CCCC', 'HR': 'FCE5CD', 'R': 'FFF2CC', 'O': 'D9EAD3'}


class StopError(Exception):
    """A problem the user has to settle before the workbook can be written."""


class Log:
    def __init__(self):
        self.sections = {'Inputs': [], 'Columns written': [], 'Project values': [], 'Commonly confused terms': [],
                         'Library tables': [],
                         'OTU and taxonomy tables': [], 'Left out': [], 'Warnings': [],
                         'Mandatory terms with no value': []}

    def add(self, section, line):
        self.sections[section].append(line)

    def write(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f'FAIRe mapper: apply mapping {__version__}\n')
            for name, lines in self.sections.items():
                f.write(f'\n## {name}\n\n')
                f.write('\n'.join(f'- {x}' for x in lines) + '\n' if lines else '- none\n')


# ------------------------------------------------------------------ reading the crosswalk

def read_crosswalk(path):
    """The crosswalk as written by propose mapping, or after editing in a spreadsheet: tab- or
    comma-separated text, or Excel. Metadata lines (starting with #) are skipped."""
    raw = Path(path).read_bytes()
    if raw[:4] == b'PK\x03\x04':
        cw = pd.read_excel(path, dtype=str, header=None).fillna('')
        cw = cw[[not str(v).strip().startswith('#') for v in cw.iloc[:, 0]]]
        cw.columns = [str(c).strip() for c in cw.iloc[0]]
        cw = cw.iloc[1:].reset_index(drop=True)
    else:
        text = raw.decode('utf-8-sig', errors='replace')
        lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip('"').startswith('#')]
        header = lines[0] if lines else ''
        sep = '\t' if '\t' in header else (';' if header.count(';') > header.count(',') else ',')
        cw = pd.read_csv(io.StringIO('\n'.join(lines)), sep=sep, dtype=str, keep_default_na=False)
    cw.columns = [str(c).strip() for c in cw.columns]
    need = {'subject_label', 'predicate_id', 'object_label'}
    if not need <= set(cw.columns):
        raise StopError(f"the crosswalk needs the columns {', '.join(sorted(need))}; found {', '.join(cw.columns)}")
    for c in ('combine_order', 'value_part', 'comment'):
        if c not in cw.columns:
            cw[c] = ''
    return cw


def choose_rows(cw, table_columns, by_name, include_review, log):
    """The crosswalk rows to apply, as dicts with column, term, part (int) and value_part."""
    stripped = {str(c).strip(): c for c in table_columns}
    applied, held = [], []
    for r in cw.to_dict('records'):
        label, term = r['subject_label'], r['object_label'].strip()
        if term.startswith('FAIRe:'):
            term = term[6:]
        column = label if label in table_columns else stripped.get(label.strip())
        if column is None:
            log.add('Warnings', f"crosswalk column '{label}' is not in the table; row skipped")
            continue
        if term not in by_name:
            log.add('Warnings', f"'{label}': {term} is not a FAIRe term for this assay and sample type; row skipped")
            continue
        pred = r['predicate_id'].strip()
        part = int(float(r['combine_order'])) if str(r['combine_order']).strip() else 0
        row = {'column': column, 'term': term, 'part': part, 'value_part': r['value_part'].strip().lower(),
               'predicate': pred}
        if pred == 'skos:exactMatch' or (include_review and pred == 'skos:closeMatch'):
            applied.append(row)
        else:
            held.append(row)
            log.add('Left out', f"'{column}' to {term}: {pred} (for review); confirm it as skos:exactMatch to apply it"
                    if pred == 'skos:closeMatch' else f"'{column}' to {term}: {pred} is not applied")
    # A combined value is written only when all its parts are applied.
    for term in {r['term'] for r in held if r['part']}:
        dropped = [r for r in applied if r['term'] == term and r['part']]
        if dropped:
            applied = [r for r in applied if r not in dropped]
            names = ', '.join(f"'{r['column']}'" for r in dropped)
            log.add('Warnings', f'{term} not written: some of its parts are for review. Confirm all parts, or delete '
                                f'the rows you do not want, to write it (also left out: {names})')
    # One column per term, except for combined values and the unit half of a split cell.
    seen, out = {}, []
    for r in applied:
        key = (r['term'], r['part']) if r['part'] else r['term']
        if key in seen:
            log.add('Warnings', f"{r['term']} is mapped from '{seen[key]}' and '{r['column']}'; "
                                f"'{seen[key]}' is used")
            continue
        seen[key] = r['column']
        out.append(r)
    return out


# ------------------------------------------------------------------ value conversion

DMY = ['%d/%m/%Y', '%d/%m/%y', '%d-%m-%Y', '%d-%m-%y', '%d.%m.%Y', '%d.%m.%y']
MDY = ['%m/%d/%Y', '%m/%d/%y', '%m-%d-%Y', '%m-%d-%y', '%m.%d.%Y', '%m.%d.%y']
ONE_READING = ['%Y-%m-%d', '%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
               '%Y/%m/%d', '%Y%m%d', '%d %b %Y', '%d-%b-%Y', '%d-%b-%y', '%d %b %y', '%d %B %Y', '%d-%B-%Y',
               '%b %d %Y', '%B %d %Y', '%b %d, %Y', '%B %d, %Y', '%d/%b/%Y']
PARTIAL_ISO = re.compile(r'^\d{4}(-\d{2})?$')


def _parse(s, fmts):
    for f in fmts:
        try:
            d = dt.datetime.strptime(s, f)
        except ValueError:
            continue
        if 1900 <= d.year <= 2100:
            return d, f
    return None, None


def _iso(d, fmt):
    if fmt and ('%H' in fmt or (d.hour or d.minute or d.second)):
        return d.strftime('%Y-%m-%dT%H:%M:%S' if (fmt and '%S' in fmt) or d.second else '%Y-%m-%dT%H:%M')
    return d.strftime('%Y-%m-%d')


def convert_dates(column, values, date_order, profile):
    """Values to ISO 8601. Returns (new values, notes, problems)."""
    notes, problems = [], []
    texts = [str(v).strip() for v in values if not _blank(v) and not fm.is_missing(v)
             and not isinstance(v, (dt.datetime, dt.date, pd.Timestamp))]
    # Day-first or month-first: settled by any value that only one reading fits.
    dmy_only = [s for s in texts if _parse(s, DMY)[0] and not _parse(s, MDY)[0]]
    mdy_only = [s for s in texts if _parse(s, MDY)[0] and not _parse(s, DMY)[0]]
    either = [s for s in texts if _parse(s, DMY)[0] and _parse(s, MDY)[0] and _parse(s, DMY)[0] != _parse(s, MDY)[0]]
    if dmy_only and mdy_only:
        raise StopError(f"'{column}' has dates that only fit day first ({dmy_only[0]}) and others that only fit "
                        f"month first ({mdy_only[0]}). Correct the table, then run again.")
    order = 'dmy' if dmy_only else ('mdy' if mdy_only else date_order)
    if either and order == 'stop':
        raise StopError(f"'{column}': dates such as {either[0]} can be read day first or month first, and no value "
                        f"settles it. Set 'Dates such as 06/09/2017' on the form to day first or month first.")
    if either and not (dmy_only or mdy_only):
        notes.append(f"read {'day' if order == 'dmy' else 'month'} first, as set on the form")
    elif dmy_only or mdy_only:
        notes.append(f"read {'day' if order == 'dmy' else 'month'} first, as {(dmy_only or mdy_only)[0]} shows")
    two_digit = False
    serial = profile.serial_date_frac >= 0.9 and profile.numeric_frac >= 0.9
    out, timed = [], []
    for v in values:
        if _blank(v) or fm.is_missing(v):
            out.append(v)
            continue
        if isinstance(v, (dt.datetime, pd.Timestamp)):
            out.append(_iso(pd.Timestamp(v).to_pydatetime(), None))
            continue
        if isinstance(v, dt.date):
            out.append(v.isoformat())
            continue
        s = str(v).strip()
        if fm.ISO_OFFSET_RE.match(s) or PARTIAL_ISO.match(s):
            out.append(s)
            continue
        if serial and re.match(r'^\d+(\.0+)?$', s):
            d = dt.datetime(1899, 12, 30) + dt.timedelta(days=float(s))
            out.append(_iso(d, None))
            continue
        d, f = _parse(s, ONE_READING + (DMY if order == 'dmy' else MDY if order == 'mdy' else []))
        if d is None:
            d, f = _parse(s, DMY if not mdy_only else MDY)   # one reading only (13/06/2019)
        if d is None:
            problems.append(s)
            out.append(s)
            continue
        two_digit = two_digit or '%y' in f
        if '%H' in f:
            timed.append((len(out), d))
        out.append(_iso(d, f))
    if timed and all(not (d.hour or d.minute or d.second) for _, d in timed):
        # Every time is midnight: dates saved with a time, as Excel and pandas write them.
        for i, d in timed:
            out[i] = d.strftime('%Y-%m-%d')
        notes.append('the time 00:00:00 on every date left out')
    if serial:
        notes.append('Excel serial numbers read as dates (days since 1899-12-30)')
    if two_digit:
        notes.append('two-digit years read as 1969 to 2068')
    return out, notes, problems


def _blank(v):
    return v is None or (isinstance(v, float) and math.isnan(v)) or (isinstance(v, str) and not v.strip())


def _number(s):
    s = str(s).strip().replace(',', '') if not isinstance(s, (int, float)) else s
    try:
        x = float(s)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(x):
        return None
    return int(x) if x.is_integer() and not (isinstance(s, str) and '.' in s) else x


def convert_number(values, t, part, header_unit):
    """Numbers, or the number or unit of 'number unit' cells. Returns (values, notes, problems)."""
    want = fm.fixed_unit(t)
    notes, problems, out, units_seen = [], [], [], set()
    for v in values:
        if _blank(v) or fm.is_missing(v):
            out.append(v)
            continue
        n = _number(v)
        if n is not None and part != 'unit':
            out.append(n)
            continue
        q = fm.parse_quantity(v)
        if q is None:
            problems.append(str(v))
            out.append(v)
            continue
        num, unit = q
        units_seen.add(unit)
        if part == 'unit':
            out.append(unit)
            continue
        x = _number(num)
        if want and unit != want:
            factor = fm.UNIT_FACTORS.get((unit, want))
            if factor is None:
                problems.append(f'{v} (the term is in {want})')
                out.append(v)
                continue
            x = x * factor
            x = int(x) if float(x).is_integer() else round(x, 10)
        out.append(x)
    if units_seen:
        if part == 'unit':
            notes.append(f"unit taken from each cell ({', '.join(sorted(units_seen))})")
        else:
            notes.append(f"number taken from each cell ({', '.join(sorted(units_seen))}"
                         + (f', converted to {want})' if want and units_seen != {want} else ')'))
    return out, notes, problems


def convert_duration(values, header_unit):
    notes, problems, out = [], [], []
    for v in values:
        if _blank(v) or fm.is_missing(v):
            out.append(v)
            continue
        s = str(v).strip()
        if fm.ISO_DUR_RE.match(s):
            out.append(s.upper())
            continue
        n = _number(s)
        if n is not None and header_unit in fm.ISO_DURATION_UNITS:
            out.append(fm.iso_duration(n, header_unit))
            continue
        q = fm.parse_quantity(s)
        iso = fm.iso_duration(*q) if q else None
        if iso:
            out.append(iso)
        else:
            problems.append(s)
            out.append(s)
    if any(not _blank(v) and _number(v) is not None for v in values) and header_unit:
        word = {'d': 'days', 'h': 'hours', 'min': 'minutes', 'wk': 'weeks', 'mo': 'months', 'yr': 'years'}
        notes.append(f'numbers read as {word.get(header_unit, header_unit)} (from the header) and written as ISO 8601 '
                     f'durations')
    return out, notes, problems


BOOL_TRUE, BOOL_FALSE = {'1', 'yes', 'y', 'true', 't', '1.0'}, {'0', 'no', 'n', 'false', 'f', '0.0'}


DEPTH_RANGE = re.compile(r'^\s*(\d+(\.\d+)?)\s*(?:-|–|to)\s*(\d+(\.\d+)?)\s*m?\s*$')


CONTROL_CATEGORIES = {'negative control', 'positive control', 'pcr standard'}
CONTROL_NA = 'not applicable: control sample'


def control_rows(sample_out, n):
    """Which samples are controls: samp_category negative control, positive control or PCR standard,
    or a neg_cont_type or pos_cont_type given."""
    def given(v):
        return not (_blank(v) or fm.is_missing(v))
    cats = sample_out.get('samp_category') or [''] * n
    neg = sample_out.get('neg_cont_type') or [''] * n
    pos = sample_out.get('pos_cont_type') or [''] * n
    return [str(cats[i]).strip().lower() in CONTROL_CATEGORIES or given(neg[i]) or given(pos[i]) for i in range(n)]


# A UTC offset as ISO 8601 writes it (+11:00, -04:00 or Z).
UTC_OFFSET_RE = re.compile(r'^(Z|[+-](0\d|1[0-4]):[0-5]\d)$')
TIME_24_RE = re.compile(r'^([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?$')
TIME_AMPM_RE = re.compile(r'^(1[0-2]|0?[1-9])(?::([0-5]\d))?(?::([0-5]\d))?\s*([ap])\.?\s*m\.?$', re.I)
# FAIRe's description of a term that takes a range of numbers (ampliconSize: "A range can be entered
# separated by a hyphen").
NUMBER_RANGE = re.compile(r'^\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*$')


def time_of_day(v):
    """(hour, minute, second) of a time of day: an Excel time cell, or text such as 10:00, 22:30:00,
    4 pm or 4:30 pm. None for anything else."""
    if isinstance(v, dt.time):
        return v.hour, v.minute, v.second
    if _blank(v) or fm.is_missing(v):
        return None
    s = str(v).strip()
    m = TIME_24_RE.match(s)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
    m = TIME_AMPM_RE.match(s)
    if m:
        h = int(m.group(1)) % 12 + (12 if m.group(4).lower() == 'p' else 0)
        return h, int(m.group(2) or 0), int(m.group(3) or 0)
    return None


def read_fasta(path):
    """{sequence ID (the first word of each header): sequence} from a FASTA file."""
    seqs, name, parts = {}, None, []
    with open(path, encoding='utf-8-sig', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line.startswith('>'):
                if name is not None:
                    seqs[name] = ''.join(parts).upper()
                name, parts = fo.norm_id(line[1:].split()[0]) if line[1:].split() else '', []
            elif line and name is not None:
                parts.append(line)
    if name is not None:
        seqs[name] = ''.join(parts).upper()
    if not seqs:
        raise StopError(f'{Path(path).name}: no sequences found; a FASTA file has a line starting with > before '
                        f'each sequence')
    return seqs


def convert_value(v, t, notes_seen):
    """Allowed values, booleans and the like, one value at a time. Returns (value, problem or None)."""
    if _blank(v) or fm.is_missing(v):
        return v, None
    s = str(v).strip()
    k = t.kind
    if k == 'boolean':
        if s.lower() in BOOL_TRUE:
            return 1, None
        if s.lower() in BOOL_FALSE:
            return 0, None
        return s, s
    if k in ('vocab', 'number_or_vocab') and t.vocab:
        if k == 'number_or_vocab' and _number(s) is not None:
            return _number(s), None
        if ' | ' in s:   # several values, as FAIRe lists them
            done = [convert_value(x, t, notes_seen) for x in s.split(' | ')]
            bad = [p for _, p in done if p is not None]
            return ' | '.join(str(x) for x, _ in done), (s if bad else None)
        for o in t.vocab:
            if s.lower() == o.lower():
                return o, None
        if s.lower().startswith('other:'):
            return s, None
        return s, s
    if k in ('latitude', 'longitude', 'number', 'integer'):
        n = _number(s)
        if n is None and 'range can be entered' in (t.description or '').lower() and NUMBER_RANGE.match(s):
            m = NUMBER_RANGE.match(s)
            return f'{m.group(1)}-{m.group(2)}', None
        return (n, None) if n is not None else (s, s)
    if k == 'termlabel' and not fm.TERMLABEL_RE.match(s):
        return s, s
    return (v if isinstance(v, (int, float)) else s), None


def geo_value(parts, country):
    """'Country: region, locality' from the parts in order."""
    parts = [str(p).strip() for p in parts if not _blank(p) and not fm.is_missing(p)]
    if not parts:
        return None, None
    first = fm.insdc_country(parts[0])
    if first:
        rest = parts[1:]
    elif ':' in parts[0] and fm.insdc_country(parts[0].split(':', 1)[0]):
        return ', '.join(parts), None   # already "Country: region"
    elif country:
        first, rest = country, parts
    else:
        return ', '.join(parts), 'no country or sea name'
    return (f"{first}: {', '.join(rest)}" if rest else first), None


# ------------------------------------------------------------------ the workbook

def load_template(path):
    return pd.read_excel(path, sheet_name=None, header=None, dtype=object)


def filter_columns(sheet, assay_type, req_lev, sample_types, checklist):
    """A sample-style template sheet (3 header rows) with FAIRe-ator's choice of columns."""
    df = sheet.copy()
    df.columns = list(df.iloc[2])
    keep = []
    spec = {r['term_name']: str(r.get('sample_type_specificity') or '') for r in checklist}
    for i, name in enumerate(df.columns):
        level, section = str(df.iloc[0, i]), str(df.iloc[1, i])
        if i == 0:
            keep.append(name)
            continue
        if section in SECTIONS_OUT.get(assay_type, ()):
            continue
        if level not in req_lev:
            continue
        s = spec.get(name, '')
        if sample_types and s and s != 'nan' and s != 'ALL' and not any(st.lower() in s.lower() for st in sample_types):
            continue
        keep.append(name)
    return df[keep]


def build_workbook(args, df, rows, terms, by_name, log):
    tpl = load_template(args.template)
    checklist = pd.read_excel(args.checklist, sheet_name='checklist', dtype=object).to_dict('records')
    req_lev = ['M'] + [x for x in args.req_lev.split(',') if x and x != 'M']
    sample_types = [s.strip() for s in args.sample_types.split(',')] if args.sample_types else None
    assays = [a.strip() for a in args.assay_name.split(',') if a.strip()] if args.assay_name else []
    profiles = {c: fm.profile_column(c, df[c]) for c in df.columns}
    offset = (getattr(args, 'utc_offset', '') or '').strip()
    if offset and not UTC_OFFSET_RE.match(offset):
        raise StopError(f"the UTC offset '{offset}' is not in the form +11:00, -04:00 or Z")

    # ---- sampleMetadata columns
    sm = filter_columns(tpl['sampleMetadata'], args.assay_type, req_lev, sample_types, checklist)
    if args.assay_type == 'targeted' and len(assays) > 1 and 'detected_notDetected' in sm.columns:
        # One detected_notDetected column per assay, as FAIRe-ator makes them.
        cols = {}
        for c in sm.columns:
            if c == 'detected_notDetected':
                for a in assays:
                    cols[f'detected_notDetected_{a}'] = [sm[c].iloc[0], sm[c].iloc[1], f'detected_notDetected_{a}']
            else:
                cols[c] = list(sm[c])
        sm = pd.DataFrame(cols)
    sample_terms = list(sm.columns)
    other = {name: filter_columns(tpl[name], args.assay_type, req_lev, None, checklist)
             for name in OTHER_SHEETS[args.assay_type]}
    run_terms = list(other['experimentRunMetadata'].columns) if 'experimentRunMetadata' in other else []

    # ---- projectMetadata rows
    pm = tpl['projectMetadata'].copy()
    pm.columns = list(pm.iloc[0])
    pm = pm.iloc[1:].reset_index(drop=True)
    pm = pm[~pm['section'].isin(SECTIONS_OUT.get(args.assay_type, ()))]
    pm = pm[pm['requirement_level_code'].isin(req_lev)].reset_index(drop=True)
    project_terms = list(pm['term_name'])
    project = {'project_id': args.project_id, 'assay_type': args.assay_type, 'checkls_ver': CHECKLIST_NUMBER}
    if len(assays) == 1:
        project['assay_name'] = assays[0]
    by_assay = {a: {} for a in assays}   # values for one assay, in its projectMetadata column

    n = len(df)
    formats, controls = {}, {}
    sample_out = {t: [None] * n for t in sample_terms}
    run_out = {}
    written = set()

    def put(term, values, column_desc):
        """Write a converted column to the right sheet."""
        t = by_name[term]
        if term in sample_out:
            sample_out[term] = values
            written.add(term)
            return 'sampleMetadata'
        if term in project_terms and t.level == 'project':
            vals = list(dict.fromkeys(str(v) for v in values if not _blank(v)))
            if not vals:
                return None
            if len(vals) > 1:
                log.add('Warnings', f"{column_desc}: {term} holds one value per project, but the column has "
                                    f"{len(vals)}; written joined with ' | '")
            project[term] = ' | '.join(vals) if len(vals) > 1 else _maybe_number(values, vals[0])
            written.add(term)
            return 'projectMetadata'
        if term in run_terms:
            run_out[term] = values
            written.add(term)
            return 'experimentRunMetadata'
        log.add('Warnings', f"{column_desc}: {term} is not in the sheets made for this assay type and these "
                            f"requirement levels; not written")
        return None

    # ---- mapped columns
    by_term = {}
    for r in rows:
        by_term.setdefault(r['term'], []).append(r)
    for term, group in by_term.items():
        t = by_name[term]
        if any(r['part'] for r in group) and len(group) > 1 or (group[0]['part'] and t.kind == 'geoloc'):
            group = sorted(group, key=lambda r: r['part'])
            cols = [r['column'] for r in group]
            values, missing_country = [], 0
            for i in range(n):
                v, problem = geo_value([df[c].iloc[i] for c in cols], args.country) if t.kind == 'geoloc' else \
                    (' | '.join(str(df[c].iloc[i]) for c in cols if not _blank(df[c].iloc[i])) or None, None)
                values.append(v)
                missing_country += bool(problem)
            desc = ' + '.join(f"'{c}'" for c in cols)
            sheet = put(term, values, desc)
            if sheet:
                ex = next((v for v in values if v), '')
                log.add('Columns written', f"{desc} to {term} ({sheet}), combined in this order, e.g. '{ex}'")
            if missing_country:
                log.add('Warnings', f'{term}: {missing_country} rows have no country or sea name first; set the '
                                    f'country on the form, or add a country column')
            continue
        for r in group:
            col = r['column']
            p = profiles[col]
            raw = list(df[col])
            texts = raw   # the text each value came from, for the cell format
            notes, problems = [], []
            vp = r['value_part']
            if term in fm.DEPTH_TERMS:
                # A depth range (250-350) gives the minimum to one term and the maximum to the other.
                end = 0 if term == 'minimumDepthInMeters' else 1
                ranges = [bool(not _blank(v) and DEPTH_RANGE.match(str(v))) for v in raw]
                if any(ranges):
                    raw = [DEPTH_RANGE.match(str(v)).group(1 + 2 * end) if rg else v for v, rg in zip(raw, ranges)]
                    texts = raw
                    notes.append(f"{sum(ranges)} ranges written as their {'minimum' if end == 0 else 'maximum'}"
                                 f" ({next(str(v) for v, rg in zip(df[col], ranges) if rg)})")
            if vp in ('latitude', 'longitude'):
                texts = []
                for v in raw:
                    ll = None if _blank(v) or fm.is_missing(v) else fm.parse_lat_lon(v)
                    if ll is None and not (_blank(v) or fm.is_missing(v)) and _number(v) is None:
                        problems.append(str(v))
                    texts.append(v if ll is None else ll[0 if vp == 'latitude' else 1])
                values = [_number(x) if isinstance(x, str) and _number(x) is not None else x for x in texts]
                notes.append(f'the {vp} part of each cell' + (', south as negative' if vp == 'latitude'
                                                              else ', west as negative'))
            elif vp.endswith(' control if yes'):
                kind = vp[:-len(' if yes')]
                values = []
                for v in raw:
                    s = '' if _blank(v) else str(v).strip().lower()
                    if s in BOOL_TRUE:
                        values.append(kind)
                    elif s in BOOL_FALSE:
                        values.append('sample')
                    else:
                        values.append(v)
                        if s and not fm.is_missing(v):
                            problems.append(str(v))
                controls[kind] = controls.get(kind, 0) + values.count(kind)
                notes.append(f'yes written as {kind} ({values.count(kind)} rows), no as sample')
            elif t.kind == 'date':
                values, notes, problems = convert_dates(col, raw, args.date_order, p)
            elif t.kind == 'duration':
                values, notes, problems = convert_duration(raw, p.header_time_unit)
            elif r['value_part'] in ('number', 'unit') or (t.kind in ('number', 'integer', 'number_or_vocab')
                                                           and p.quantity_frac > 0):
                values, notes, problems = convert_number(raw, t, r['value_part'], p.header_time_unit)
                if r['value_part'] == 'unit' or t.kind == 'vocab':
                    values = [convert_value(v, t, None)[0] for v in values]
            elif t.kind == 'geoloc':
                values, problem_rows = [], 0
                for v in raw:
                    gv, problem = geo_value([v], args.country)
                    values.append(gv)
                    problem_rows += bool(problem)
                if problem_rows:
                    log.add('Warnings', f"'{col}' to {term}: {problem_rows} rows have no country or sea name first; "
                                        f"set the country on the form, or add a country column")
            else:
                values = []
                for v in raw:
                    nv, problem = convert_value(v, t, None)
                    values.append(nv)
                    if problem is not None:
                        problems.append(problem)
            sheet = put(term, values, f"'{col}'")
            if not sheet:
                continue
            if t.kind in ('latitude', 'longitude', 'number', 'integer', 'number_or_vocab'):
                # Excel numbers drop trailing zeros (-13.99230 is -13.9923); show them with the cell format.
                dps = [len(str(a).strip().split('.')[1]) if isinstance(a, str) and isinstance(b, float)
                       and re.match(r'^-?\d+\.\d+$', str(a).strip()) else None for a, b in zip(texts, values)]
                if any(dps):
                    formats[term] = dps
                    zero = next((str(a).strip() for a, d in zip(texts, dps) if d and str(a).strip().endswith('0')), None)
                    if zero:
                        notes.append(f'trailing zeros ({zero}) are shown by the cell format but dropped from the '
                                     f'stored number, so FAIRe-fier may count fewer decimal places')
            changed = [(a, b) for a, b in zip(raw, values) if not _blank(a) and str(a).strip() != str(b)
                       and not (isinstance(b, (int, float)) and _number(a) == b)]
            ex = f", e.g. '{changed[0][0]}' as '{changed[0][1]}'" if changed else ''
            part = {'number': ' (the number)', 'unit': ' (the unit)', 'latitude': ' (the latitude)',
                    'longitude': ' (the longitude)'}.get(vp, '')
            log.add('Columns written', f"'{col}' to {term}{part} ({sheet})" + (f": {'; '.join(notes)}" if notes else '')
                    + ex)
            if problems:
                uniq = list(dict.fromkeys(problems))
                why = {'termlabel': 'are not in "label [ENVO:id]" form, as FAIRe needs; kept as they are',
                       'vocab': 'are not allowed values; kept as they are',
                       'boolean': 'are not 0 or 1 (or yes or no); kept as they are'}.get(
                    t.kind, 'could not be converted and are kept as they are')
                log.add('Warnings', f"'{col}' to {term}: {len(problems)} values {why}, e.g. "
                        + ', '.join(f"'{x}'" for x in uniq[:3]))

    # ---- times of day in a column of their own (verbatimEventTime), joined to the dates in eventDate,
    # as FAIRe's eventDate is "the date and time of sampling" (2008-01-23T19:23-06:00)
    if 'verbatimEventTime' in written and 'eventDate' in sample_out:
        times, dates = sample_out['verbatimEventTime'], sample_out['eventDate']
        tcol = next((r['column'] for r in rows if r['term'] == 'verbatimEventTime'), 'the time column')
        says_utc = bool(re.search(r'\b(UTC|GMT)\b', str(tcol), re.I))
        # Daily cycles follow local time, so eventDate keeps it: times in UTC are converted to local time
        # when the sites' offset is given (the dates then taken as UTC dates, as in a UTC log)
        to_local = says_utc and offset not in ('', 'Z')
        join_offset = offset or ('Z' if says_utc else '')
        shift = dt.timedelta(0)
        if to_local:   # +10:00 or -04:30 (checked against UTC_OFFSET_RE above)
            hours, minutes = offset[1:].split(':')
            shift = (-1 if offset.startswith('-') else 1) * dt.timedelta(hours=int(hours), minutes=int(minutes))
        # Excel time cells come as 10:00:00: written as 10:00, FAIRe's example form
        sample_out['verbatimEventTime'] = [fm.time_text(v) if isinstance(v, dt.time) or TIME_24_RE.match(str(v).strip())
                                           else v for v in times]
        joined, example = 0, None
        for i in range(n):
            hms, d = time_of_day(times[i]), str(dates[i]).strip()
            if hms is None or _blank(dates[i]) or not re.match(r'^\d{4}-\d{2}-\d{2}$', d):
                continue
            when = dt.datetime.fromisoformat(d) + dt.timedelta(hours=hms[0], minutes=hms[1], seconds=hms[2]) + shift
            stamp = when.strftime('%Y-%m-%dT%H:%M' + (':%S' if when.second else '')) + join_offset
            example = example or (d, fm.time_text(times[i]), stamp)
            dates[i] = stamp
            joined += 1
        if joined:
            eg = f"in {joined} rows (e.g. '{example[0]}' at '{example[1]}' as '{example[2]}')"
            if to_local:
                log.add('Columns written', f"eventDate: the times in '{tcol}' (verbatimEventTime), which the column "
                                           f"name says are UTC, joined to the dates and converted from UTC to local "
                                           f"time at {offset}, {eg}")
            elif says_utc and not offset:
                log.add('Columns written', f"eventDate: the times in '{tcol}' (verbatimEventTime) joined to the dates "
                                           f"in UTC (Z), as the column name says, {eg}")
                log.add('Warnings', 'eventDate: the times are in UTC. Give the UTC offset of the sampling sites on '
                                    'the form to write them as local times, which daily cycles follow')
            else:
                log.add('Columns written', f"eventDate: the times in '{tcol}' (verbatimEventTime) joined to the dates"
                        + (f', with the UTC offset {join_offset}' if join_offset else '') + f', {eg}')
            if not join_offset:
                log.add('Warnings', 'eventDate: the times have no UTC offset, so they are kept as local times; give '
                                    'the offset on the form (for example +11:00 for Australian Eastern Daylight '
                                    'Time) so eventDate also gives the time zone')

    # ---- values for the whole project or for every sample (e.g. from the methods text)
    if args.project_values:
        pv = fm.read_table(args.project_values).astype(object).where(lambda x: x.notna(), '')
        pv.columns = [str(c).strip().lower() for c in pv.columns]
        pv = pv.map(lambda v: str(v) if v != '' else '')
        held_values, for_samples_only, from_values = {}, [], {}
        ctrl = control_rows(sample_out, n)
        if not {'term', 'value'} <= set(pv.columns):
            raise StopError('the project values file needs the columns term and value')
        for r in pv.to_dict('records'):
            term, value = r['term'].strip(), r['value'].strip()
            status = r.get('status', '').strip().lower()
            assay = (r.get('assay') or r.get('assay_name') or '').strip()
            if not term or not value:
                continue
            if status and status not in ('supported', 'confirmed'):
                held_values.setdefault(status, {}).setdefault(term, 0)
                held_values[status][term] += 1
                continue
            if assay and len(assays) > 1:
                # A value for one assay goes to that assay's column of projectMetadata.
                if assay not in by_assay:
                    log.add('Warnings', f"project value {term} for assay '{assay}': not one of the assay names "
                                        f"({', '.join(assays)}); skipped")
                    continue
                if term not in by_name or term not in project_terms or by_name[term].level != 'project':
                    log.add('Warnings', f"project value {term} for assay '{assay}': values for one assay go to "
                                        f"projectMetadata, and {term} is not a projectMetadata term; skipped")
                    continue
                v, problem = convert_value(value, by_name[term], None)
                by_assay[assay][term] = v
                written.add(term)
                from_values.setdefault(term, str(v))
                log.add('Project values', f'{term} = {str(v)[:80]} (projectMetadata, assay {assay})'
                        + (' (not an allowed value)' if problem else ''))
                continue
            if assay and assays and assay not in assays:
                log.add('Warnings', f"project value {term} for assay '{assay}': not the assay name "
                                    f"({', '.join(assays)}); skipped")
                continue
            if term not in by_name:
                log.add('Warnings', f'project value {term}: not a FAIRe term for this assay and sample type; skipped')
                continue
            if term in written:
                log.add('Left out', f'project value {term} = {value[:60]}: a column of the table gives this term')
                continue
            t = by_name[term]
            v, problem = convert_value(value, t, None)
            if term in project_terms and t.level == 'project':
                project[term] = v
            elif term in sample_out:
                cond = str(t.condition).lower()
                if any(ctrl) and 'unless' in cond and 'negative control' in cond:
                    # FAIRe asks samples, not controls, for this term (env_broad_scale, say)
                    sample_out[term] = [CONTROL_NA if c else v for c in ctrl]
                    for_samples_only.append(term)
                else:
                    sample_out[term] = [v] * n
            elif term in run_terms:
                run_out[term] = [v] * n
            else:
                log.add('Warnings', f'project value {term}: not in the sheets made; skipped')
                continue
            written.add(term)
            from_values.setdefault(term, str(v))
            where = 'projectMetadata' if term in project and project[term] == v else 'every sample'
            log.add('Project values', f'{term} = {str(v)[:80]} ({where})' + (' (not an allowed value)' if problem else ''))
        # Terms that people often confuse, given here with no review: the same check as the crosswalk's
        confused = fm.load_confused(args.confused_terms)
        sides = {}
        for term in from_values:
            if term in confused[0]:
                sides.setdefault(confused[0][term][1], []).append(term)
        for given in sides.values():
            note = fm.confused_note(given, confused)
            if note:
                log.add('Commonly confused terms', ', '.join(f'{t} = {from_values[t][:60]}' for t in given)
                        + f' (from the values for the whole project): {note}')
        if for_samples_only:
            log.add('Project values', f"{', '.join(for_samples_only)}: written as '{CONTROL_NA}' for the "
                    f"{sum(ctrl)} controls, as FAIRe asks only the samples for them")
        for status, counts in held_values.items():
            log.add('Left out', f'project values with status {status}, not applied: '
                    + ', '.join(f'{t} ({k})' if k > 1 else t for t, k in counts.items()))

    # ---- controls marked yes or no in a column
    for kind, k in controls.items():
        flag, typ = ('neg_cont_0_1', 'neg_cont_type') if kind.startswith('negative') else ('pos_cont_0_1', 'pos_cont_type')
        if k and flag in project_terms and flag not in written:
            project[flag] = 1
            written.add(flag)
            log.add('Project values', f'{flag} = 1 (projectMetadata): {k} samples are {kind}s')
        if k and typ in sample_out and typ not in written:
            log.add('Warnings', f'{typ}: fill the type of each of the {k} {kind}s (for example field negative or '
                                f'extraction negative); FAIRe needs it when samp_category is {kind}')

    # ---- controls: FAIRe's term for a value a control cannot have is "not applicable: control sample",
    # so a control's "missing: not collected" is written as that (the FAIRe authors, 6 November 2026)
    ctrl = control_rows(sample_out, n)
    if any(ctrl):
        changed, terms_changed = 0, []
        for term, values in sample_out.items():
            for i, v in enumerate(values):
                if ctrl[i] and re.sub(r'\s+', ' ', str(v)).strip().lower() == 'missing: not collected':
                    values[i] = 'not applicable: control sample'
                    changed += 1
                    if term not in terms_changed:
                        terms_changed.append(term)
        if changed:
            log.add('Columns written',
                    f"'missing: not collected' written as 'not applicable: control sample' in {changed} cells of "
                    f"{sum(ctrl)} control {'sample' if sum(ctrl) == 1 else 'samples'} ({', '.join(terms_changed[:6])}"
                    f"{' ...' if len(terms_changed) > 6 else ''}), FAIRe's term for controls")

    # ---- assay names in sampleMetadata, as FAIRe-ator pre-fills them
    if 'assay_name' in sample_out and 'assay_name' not in written and assays:
        sample_out['assay_name'] = [' | '.join(assays)] * n
        log.add('Project values', f"assay_name = {' | '.join(assays)} (every sample)")
    if run_out and 'samp_name' in sample_out:
        run_out['samp_name'] = sample_out['samp_name']
        if 'assay_name' not in run_out and len(assays) == 1:
            run_out['assay_name'] = [assays[0]] * n
        elif 'assay_name' not in run_out:
            log.add('Warnings', 'experimentRunMetadata: fill assay_name for each library (several assays were named)')

    # ---- user-defined fields
    mapped_cols = {r['column'] for r in rows}
    user_fields, empty_cols = [], []
    if not args.drop_unmapped:
        names = set(sample_terms) | set(by_name)
        for c in df.columns:
            if c in mapped_cols:
                continue
            if all(_blank(v) for v in df[c]):
                empty_cols.append(str(c))
                continue
            name = re.sub(r'[^A-Za-z0-9_-]+', '_', str(c).strip()).strip('_') or 'column'
            if name in names:
                name = f'user_{name}'
            base, k = name, 2
            while name in names:
                name, k = f'{base}_{k}', k + 1
            names.add(name)
            user_fields.append((c, name))
        if user_fields:
            log.add('Columns written', 'kept as user-defined fields in sampleMetadata: '
                    + ', '.join(f"'{c}' as {nm}" if c != nm else nm for c, nm in user_fields))
        if empty_cols:
            log.add('Left out', f'{len(empty_cols)} empty columns not matched to a FAIRe term: '
                    + ', '.join(empty_cols[:8]) + (' ...' if len(empty_cols) > 8 else ''))

    # ---- library tables: one experimentRunMetadata row per library and assay
    run_rows, lib_map = [], {}
    if args.library and 'experimentRunMetadata' in other:
        run_rows, info = read_library_tables(args, sample_out, assays, log)
        if run_out:
            # Values from the sample table's run columns fill what the library table does not give.
            index = {fo.norm_id(s): i for i, s in enumerate(sample_out['samp_name']) if not _blank(s)}
            filled = set()
            for r in run_rows:
                i = index.get(r['samp_name'])
                for term, values in run_out.items():
                    if i is not None and _blank(r.get(term)) and not _blank(values[i]) and term != 'samp_name':
                        r[term] = values[i]
                        filled.add(term)
            log.add('Library tables', 'the library tables replace the run columns of the sample table'
                    + (f"; from those: {', '.join(sorted(filled))}" if filled else ''))
            run_out = {}
        for r in run_rows:
            if r.get('lib_id'):
                lib_map[r['lib_id']] = r['samp_name']
            for f in ('filename', 'filename2'):
                if r.get(f):
                    lib_map[fl.file_stem(r[f])] = r['samp_name']
        library_project_values(info, project, project_terms, written, by_name, log)
    elif args.library:
        log.add('Warnings', 'library tables are for metabarcoding (experimentRunMetadata); not used')

    # ---- OTU and taxonomy tables
    otu_tables = read_otu_tables(args, sample_out, run_out, other, assays, log, terms, list(df.columns), lib_map) \
        if args.otu else []
    if otu_tables and run_rows:
        libs = {(r['samp_name'], r['assay_name'] or '') for r in run_rows}
        for t in otu_tables:
            none = [s for s in t['samples'] if (s, t['assay'] or '') not in libs and (s, '') not in libs]
            if none:
                log.add('Warnings', f"{t['label']}: {len(none)} samples have no library in the library tables, e.g. "
                                    + ', '.join(none[:3]))
    if otu_tables and not run_out and not run_rows and 'experimentRunMetadata' in other:
        # One library per sample and assay, as the OTU tables show; lib_id is the lab's to give.
        seen = set()
        for t in otu_tables:
            for samp in t['samples']:
                key = (samp, t['assay'], t['run'])
                if key not in seen:   # a raw and a final table of one assay are the same libraries
                    seen.add(key)
                    run_rows.append({'samp_name': samp, 'assay_name': t['assay'] or None,
                                     'seq_run_id': t['run'] or None})
        log.add('OTU and taxonomy tables', f'experimentRunMetadata: {len(run_rows)} rows made from the OTU tables '
                                           f'(samp_name, assay_name' + (', seq_run_id' if any(t['run'] for t in otu_tables)
                                                                        else '') + ')')
    # FAIRe's library is one amplicon of a sample, so each row gets its own lib_id (after the OTU
    # tables are read, as their columns may be named by the libraries' own names).
    if run_rows:
        amplicon_lib_ids(run_rows, log, 'Library tables' if args.library else 'OTU and taxonomy tables')
    elif run_out and 'samp_name' in run_out:
        view = [{t: v[i] for t, v in run_out.items()} for i in range(n)]
        amplicon_lib_ids(view, log, 'Columns written')
        run_out['lib_id'] = [r.get('lib_id') for r in view]
    for t in otu_tables:
        if any(fo.PR2_REMARK in str(r.get('identificationRemarks') or '') for r in t['taxa'].values()):
            db = by_assay.get(t['assay'], {}).get('otu_db') or project.get('otu_db')
            if 'pr2' not in str(db or '').lower():
                log.add('Warnings', f"{t['label']}: classified with PR2; name PR2 and its version in otu_db "
                                    f"(projectMetadata), e.g. PR2 v5.0.0")

    # ---- controls: their empty mandatory cells (a term FAIRe asks of every row, such as eventDate or
    # geo_loc_name) are given "not applicable: control sample", FAIRe's term for them
    ctrl = control_rows(sample_out, n)
    if any(ctrl):
        filled, cells, ctrl_rows = [], 0, set()
        for term in sample_terms:
            cond = str(by_name[term].condition) if term in by_name else ''
            if str(sm[term].iloc[0]) != 'M' or (cond and cond != 'nan') or term == 'assay_name':
                continue
            for i in range(n):
                if ctrl[i] and _blank(sample_out[term][i]):
                    sample_out[term][i] = CONTROL_NA
                    cells += 1
                    ctrl_rows.add(i)
                    if term not in filled:
                        filled.append(term)
        if cells:
            k = len(ctrl_rows)
            log.add('Columns written', f"'{CONTROL_NA}' written in the {cells} empty mandatory cells of {k} "
                    f"control{'s' if k > 1 else ''} ({', '.join(sorted(filled, key=str.lower))})")

    # ---- checks
    if 'samp_name' not in written:
        raise StopError('no column is mapped to samp_name, which FAIRe needs to identify each sample')
    names = [str(x) for x in sample_out['samp_name'] if not _blank(x)]
    dups = sorted({x for x in names if names.count(x) > 1})
    if dups:
        log.add('Warnings', f"samp_name repeats ({len(dups)} names, e.g. '{dups[0]}'); FAIRe needs a unique name per "
                            f"sample")
    if len(assays) > 1:
        log.add('Warnings', 'several assays: values from the table and the methods are in project_level; give '
                            'any that differ between assays an assay column in the project values file, or move '
                            'them to the assay columns')

    def when(term):
        cond = by_name[term].condition if term in by_name else ''
        if not cond or str(cond) == 'nan':
            return ''
        return f'; {cond[0].lower()}{cond[1:]}' if cond.lower().startswith('mandatory') else \
            f'; mandatory {cond[0].lower()}{cond[1:]}'
    for r in pm.to_dict('records'):
        term = r['term_name']
        if term == 'assay_name' and len(assays) > 1:
            continue   # in the assay columns
        if r['requirement_level_code'] == 'M' and _blank(project.get(term)):
            missing = [x for x in assays if _blank(by_assay.get(x, {}).get(term))] if len(assays) > 1 else assays
            if len(assays) > 1 and not missing:
                continue   # given for every assay
            log.add('Mandatory terms with no value', f'{term} (projectMetadata{when(term)})'
                    + (f": no value for {', '.join(missing)}" if len(assays) > 1 and len(missing) < len(assays) else ''))
    cats = [str(c).strip().lower() for c in (sample_out.get('samp_category') or [''] * n)]
    for term in sample_terms:
        lvl = str(sm[term].iloc[0])
        if lvl != 'M':
            continue
        vals = sample_out[term]
        # Only the rows the condition applies to: neg_cont_type is needed for the negative controls only,
        # and env_broad_scale for the samples only.
        cond = str(by_name[term].condition).strip().lower() if term in by_name else ''
        needed = list(range(n))
        if cond.startswith('if samp_category = '):
            needed = [i for i in range(n) if cats[i] == cond.split('=', 1)[1].strip()]
            if not needed:
                continue
        elif 'unless' in cond and 'samp_category' in cond:
            needed = [i for i in range(n) if not ctrl[i]]
        empty = sum(_blank(vals[i]) for i in needed)
        if empty == len(needed) == n:
            log.add('Mandatory terms with no value', f'{term} (sampleMetadata{when(term)})')
        elif empty:
            log.add('Mandatory terms with no value', f'{term} (sampleMetadata{when(term)}): empty in {empty} of '
                    f'{len(needed)} rows' + (' it applies to' if len(needed) < n else ''))
    if 'experimentRunMetadata' in other and not run_out and not run_rows:
        log.add('Mandatory terms with no value', 'experimentRunMetadata has no rows: no column of the table is a '
                                                 'library or run term (lib_id, seq_run_id, filename ...)')
    elif run_rows:
        for term in ('lib_id', 'seq_run_id', 'assay_name'):
            empty = sum(_blank(r.get(term)) for r in run_rows)
            if empty:
                log.add('Mandatory terms with no value', f'{term} (experimentRunMetadata)'
                        + (f': empty in {empty} of {len(run_rows)} rows' if empty < len(run_rows) else ''))
    log.add('Project values', f'checkls_ver is written as the number {CHECKLIST_NUMBER}, as the checklist defines it; the README '
            f'sheet names the exact checklist ({CHECKLIST_NAME})')

    # ---- write
    wb = Workbook()
    ws = wb.active
    ws.title = 'README'
    stamp = dt.datetime.now().astimezone().isoformat(timespec='seconds')
    readme = ['The templates were generated using the FAIR eDNA checklist version of;', CHECKLIST_NAME, '',
              'Date/Time generated;', stamp, '',
              f'Filled by FAIRe mapper: apply mapping {__version__}, from;',
              f'table = {args.table_name or Path(args.table).name}',
              f'crosswalk = {args.crosswalk_name or Path(args.crosswalk).name}', '',
              'The templates were generated based on the below arguments;',
              f'project_id = {args.project_id}', f"assay_name = {' | '.join(assays)}",
              f'assay_type = {args.assay_type}', f"req_lev = {' | '.join(req_lev)}",
              f"sample_type = {' | '.join(sample_types) if sample_types else 'all'}", '',
              'Requirement levels;', 'M = Mandatory', 'HR = Highly recommended', 'R = Recommended', 'O = Optional']
    for line in readme:
        ws.append([line])
    bold = Font(bold=True)

    # projectMetadata
    ws = wb.create_sheet('projectMetadata')
    header = ['requirement_level_code', 'section', 'term_name', 'project_level']
    if len(assays) > 1:
        header += [f'assay{i}' for i in range(1, len(assays) + 1)]
    ws.append(header)
    for r in pm.to_dict('records'):
        row = [r['requirement_level_code'], r['section'], r['term_name'], _cell(project.get(r['term_name']))]
        if len(assays) > 1:
            row += [a if r['term_name'] == 'assay_name' else _cell(by_assay[a].get(r['term_name'])) for a in assays]
        ws.append(row)
        ws.cell(ws.max_row, 1).fill = PatternFill('solid', fgColor=LEVEL_FILL.get(r['requirement_level_code'], 'FFFFFF'))
    for c in ws[1]:
        c.font = bold
    ws.freeze_panes = 'D2'

    # sampleMetadata
    ws = wb.create_sheet('sampleMetadata')
    levels = [sm[t].iloc[0] for t in sample_terms] + ['O'] * len(user_fields)
    sections = [sm[t].iloc[1] for t in sample_terms] + ['User defined'] * len(user_fields)
    ws.append(levels)
    ws.append(sections)
    ws.append(sample_terms + [nm for _, nm in user_fields])
    for i in range(n):
        ws.append([_cell(sample_out[t][i]) for t in sample_terms] + [_cell(df[c].iloc[i]) for c, _ in user_fields])
        for j, t in enumerate(sample_terms, 1):
            dp = formats.get(t, [None] * n)[i]
            if dp:
                ws.cell(ws.max_row, j).number_format = '0.' + '0' * dp
    _style_sample_sheet(ws, levels, bold)

    by_stage = {st: [t for t in otu_tables if t['stage'] == st] for st in ('Raw', 'Final')}
    in_place = {st: len(ts) == 1 and not ts[0]['suffix'] for st, ts in by_stage.items()}
    for name, sheet in other.items():
        st = name[4:] if name in ('taxaRaw', 'taxaFinal') else None
        if st and by_stage[st] and not in_place[st]:
            continue   # one taxonomy sheet per assay instead, below
        ws = wb.create_sheet(name)
        cols = list(sheet.columns)
        lv = [sheet[c].iloc[0] for c in cols]
        ws.append(lv)
        ws.append([sheet[c].iloc[1] for c in cols])
        ws.append(cols)
        if name == 'experimentRunMetadata' and run_rows:
            for r in run_rows:
                ws.append([_cell(r.get(c)) for c in cols])
        if name == 'experimentRunMetadata' and run_out:
            for i in range(n):
                ws.append([_cell(run_out.get(c, [None] * n)[i]) for c in cols])
            unknown = [t for t in run_out if t not in cols]
            for t in unknown:
                log.add('Warnings', f'{t}: not a column of experimentRunMetadata; not written')
        if st and in_place[st]:
            for r in by_stage[st][0]['taxa'].values():
                ws.append([_cell(r.get(c)) for c in cols])
        _style_sample_sheet(ws, lv, bold)
        if st and in_place[st]:
            _write_otu_sheet(wb, f'otu{st}', by_stage[st][0]['counts'], bold)
    for st, tables in by_stage.items():
        if not tables or in_place[st]:
            continue
        sheet = other[f'taxa{st}']
        cols = list(sheet.columns)
        lv = [sheet[c].iloc[0] for c in cols]
        for t in tables:
            ws = wb.create_sheet(_sheet_name(f'taxa{st}', t['suffix']))
            ws.append(lv)
            ws.append([sheet[c].iloc[1] for c in cols])
            ws.append(cols)
            for r in t['taxa'].values():
                ws.append([_cell(r.get(c)) for c in cols])
            _style_sample_sheet(ws, lv, bold)
            _write_otu_sheet(wb, _sheet_name(f'otu{st}', t['suffix']), t['counts'], bold)

    dd = tpl['Drop-down values']
    ws = wb.create_sheet('Drop-down values')
    for row in dd.itertuples(index=False):
        ws.append([_cell(x) for x in row])
    for c in ws[1]:
        c.font = bold
    k = add_dropdowns(wb, dd)
    if k:
        log.add('Inputs', f'drop-down lists added to {k} columns and rows, from the Drop-down values sheet, as '
                          f'FAIRe-ator adds them')
    wb.save(args.output)
    return {'samples': n, 'terms': len(written), 'user_fields': len(user_fields)}


def amplicon_lib_id(base, assay, run, shared=False):
    """M097_16SFish_LerayCOI, Fish16S, AGRF_2024-12 -> M097_16SFish_LerayCOI_Fish16S_AGRF_2024-12:
    the library name, then the assay and the sequencing run, unless it already ends with them. A name
    that ends with the assay (1A_16S_Fish, as the day-night study names its files) gets the run only,
    unless the library holds several amplicons (shared), when each lib_id names its assay."""
    tail = '_'.join(str(x).strip() for x in (assay, run) if not _blank(x))
    base = str(base).strip()
    if not tail or base == tail or base.endswith('_' + tail):
        return base
    a = '' if _blank(assay) else str(assay).strip()
    if a and base.endswith('_' + a) and not _blank(run) and not shared:
        return f'{base}_{str(run).strip()}'
    return f'{base}_{tail}'


def amplicon_lib_ids(rows, log, section):
    """Sets each row's lib_id to one amplicon of one sample in one run, as FAIRe defines a library
    ('an amplicon of a sample with unique MIDs'): the library name (samp_name when there is none),
    assay_name and seq_run_id. A library that holds several amplicons, or was sequenced in several
    runs, gets a lib_id for each, and its rows keep the same files."""
    from_samp, shared, example, todo = 0, {}, None, []
    for r in rows:
        base = r.get('lib_id')
        if _blank(base):
            if _blank(r.get('samp_name')):
                continue
            base, from_samp = r['samp_name'], from_samp + 1
        key = None
        if not _blank(r.get('filename')):
            key = (str(base).strip(), str(r.get('samp_name')), str(r['filename']), str(r.get('filename2') or ''))
            shared.setdefault(key, []).append(str(r.get('assay_name') or ''))
        todo.append((r, base, key))
    for r, base, key in todo:
        r['lib_id'] = amplicon_lib_id(base, r.get('assay_name'), r.get('seq_run_id'),
                                      shared=key is not None and len(set(shared[key])) > 1)
        example = example or r['lib_id']
    if not example:
        return
    several = {k: v for k, v in shared.items() if len(set(v)) > 1}
    msg = (f"lib_id is the library name, assay_name and seq_run_id (e.g. {example}), as FAIRe takes a library "
           f"to be one amplicon of a sample")
    if several:
        lib, assays = next(iter(several.items()))
        names = list(dict.fromkeys(assays))
        msg += (f"; {len(several)} {'library holds' if len(several) == 1 else 'libraries hold'} several amplicons "
                f"in the same files (e.g. {lib[0]}: {', '.join(names[:-1])} and {names[-1]}), so each amplicon has "
                f"its own lib_id")
    if from_samp:
        msg += (f"; samp_name stands in for the library name in {from_samp} "
                f"{'row' if from_samp == 1 else 'rows'} (give a library table for the lab's names)")
    log.add(section, msg)


def looks_like(path, sheet, expected, samples=(), terms=(), frame=None):
    """A sentence saying what a file looks like, when that is not what its field expects ('' when it
    is, or when nothing can be said)."""
    try:
        df = frame if frame is not None else fo.read_table_any(path, sheet or None)
        kind, why = fk.describe(df, samples, {frozenset(a) for t in terms if 'sampleMetadata' in t.sheets
                                              for a in t.aliases}, {t.name for t in terms})
    except (SystemExit, Exception):
        return ''
    return fk.hint(kind, why, expected)


def with_hint(msg, hint):
    """An error message with the hint after it, as a sentence of its own."""
    msg = str(msg).rstrip()
    return msg + ('' if not hint or msg.endswith('.') else '.') + hint


def check_raw_final(tables, say):
    """A final table has fewer sequences and reads than the raw one of its assay, after filtering and
    curation: more of either suggests the two were set the wrong way round."""
    def source(label):
        return label[:-len(' (raw)')] if label.endswith(' (raw)') else \
            label[:-len(' (final)')] if label.endswith(' (final)') else label
    for f in [t for t in tables if t['stage'] == 'Final']:
        for r in [t for t in tables if t['stage'] == 'Raw' and t['assay'] == f['assay']]:
            if source(f['label']) == source(r['label']):
                continue   # both from one table with curated names
            fr, rr = f['counts'].shape[0], r['counts'].shape[0]
            fs, rs = int(f['counts'].values.sum()), int(r['counts'].values.sum())
            if fr > rr or fs > rs:
                say(f"WARNING '{f['label']}' is written as final but has more "
                    + ('sequences or taxa' if fr > rr else 'reads') + f" than '{r['label']}', written as raw "
                    f"({fr} against {rr} rows; {fs:,} against {rs:,} reads). A final table usually has fewer of "
                    f"both, after filtering and curation: if the two are the wrong way round, swap 'Write this "
                    f"table as' for them")


def read_library_tables(args, sample_out, assays, log):
    """Rows of experimentRunMetadata from each library table, and what they say about the project."""
    samples = [fo.norm_id(x) for x in sample_out['samp_name'] if fo.norm_id(x)]
    k = len(args.library)
    pad = lambda xs, n=k: (list(xs or []) + [''] * n)[:n]  # noqa: E731
    sheets, which, filters, runs, names = (pad(args.library_sheet), pad(args.library_assay), pad(args.library_filter),
                                           pad(args.library_run), pad(args.library_name))
    # The run ID given for an OTU table is used for the libraries of the same assay.
    n_otu = len(args.otu or [])
    otu_runs = {}
    for a, r in zip(pad(args.otu_assay, n_otu), pad(args.otu_run, n_otu)):
        a = a.strip() or (assays[0] if len(assays) == 1 else '')
        if r.strip():
            otu_runs.setdefault(a, r.strip())
    rows, info = [], {'instruments': {}, 'platforms': set(), 'layouts': set(), 'md5': False}
    for i, path in enumerate(args.library):
        label = names[i] or Path(path).name
        these = [a.strip() for a in which[i].split(',') if a.strip()] or (assays if len(assays) == 1 else [])
        bad = [a for a in these if assays and a not in assays]
        if bad:
            raise StopError(f"library table '{label}' is for assay '{bad[0]}', which is not among the assay names "
                            f"({', '.join(assays)})")
        if not these and len(assays) > 1:
            log.add('Warnings', f"{label}: assay_name left empty; give the assays of the library table")
        try:
            got, inf = fl.read_library(path, sheets[i] or None, samples, label,
                                       lambda m: log.add('Library tables', m), these, filters[i].strip(), runs[i].strip())
        except fl.LibraryError as e:
            raise StopError(with_hint(e, looks_like(path, sheets[i], 'library', samples)))
        from_otu = 0
        for r in got:
            if _blank(r.get('seq_run_id')) and otu_runs.get(r['assay_name'] or ''):
                r['seq_run_id'] = otu_runs[r['assay_name'] or '']
                from_otu += 1
        if from_otu:
            log.add('Library tables', f'{label}: seq_run_id for {from_otu} rows from the run ID of the OTU table '
                                      f'of the same assay')
        rows += got
        for name, x in inf['instruments'].items():
            info['instruments'][name] = info['instruments'].get(name, 0) + x
        info['platforms'] |= inf['platforms']
        info['layouts'] |= inf['layouts']
        info['md5'] = info['md5'] or inf['md5']
    return rows, info


def library_project_values(info, project, project_terms, written, by_name, log):
    """Project-level terms the library tables settle: platform, lib_layout and checksum_method;
    the instrument is reported for checking, as FAIRe wants it with its OBI ID."""
    def put(term, value, why):
        if term in project_terms and term not in written and term in by_name:
            v, problem = convert_value(value, by_name[term], None)
            if problem is None:
                project[term] = v
                written.add(term)
                log.add('Project values', f'{term} = {v} (projectMetadata), {why}')
    if len(info['platforms']) == 1:
        put('platform', next(iter(info['platforms'])), 'from the library tables')
    layout = {'paired': 'paired end', 'single': 'single end'}
    if len(info['layouts']) == 1 and next(iter(info['layouts'])) in layout:
        put('lib_layout', layout[next(iter(info['layouts']))], 'from the library tables')
    if info['md5']:
        put('checksum_method', 'MD5', 'as the checksums in the library tables are MD5')
    if info['instruments']:
        names = ', '.join(f'{m} ({k} libraries)' for m, k in info['instruments'].items())
        given = str(project.get('instrument') or '')
        if not given:
            log.add('Warnings', f'instrument (projectMetadata) is empty; the library tables name {names}. FAIRe '
                                f'asks for the name with its OBI ID, such as Illumina HiSeq 1500 [OBI_0003386]')
        elif not all(m.lower() in given.lower() for m in info['instruments']):
            log.add('Warnings', f"instrument is '{given}', but the library tables name {names}")


def read_otu_tables(args, sample_out, run_out, other, assays, log, terms, table_columns, lib_map=None):
    """Read each OTU table (and its taxonomy table) for the workbook."""
    own = {re.sub(r'[^a-z0-9]', '', str(c).lower()) for c in table_columns}
    term_names = {frozenset(a) for t in terms for a in t.aliases}

    def is_detail(header):
        # A header that is a column of the sample table, or exactly a FAIRe term's name or common name
        # (Site depth), is a sample detail. Exact words only: a genus such as Pelates is not "plate".
        if re.sub(r'[^a-z0-9]', '', header.lower()) in own:
            return True
        toks = fm.tokens_of(header)
        return bool(toks) and frozenset(toks) in term_names
    if args.assay_type != 'metabarcoding':
        raise StopError('OTU and taxonomy tables are for metabarcoding; set the assay type to metabarcoding')
    samples = [fo.norm_id(x) for x in sample_out['samp_name']]
    lib_to_samp = {fo.norm_id(k): v for k, v in (lib_map or {}).items() if fo.norm_id(k)}
    if run_out.get('lib_id'):
        lib_to_samp.update({fo.norm_id(lib): s for lib, s in zip(run_out['lib_id'], samples) if fo.norm_id(lib)})
    k = len(args.otu)
    pad = lambda xs: (list(xs or []) + [''] * k)[:k]  # noqa: E731
    sheets, taxa, taxa_sheets, which, names, runs = (pad(args.otu_sheet), pad(args.taxa), pad(args.taxa_sheet),
                                                     pad(args.otu_assay), pad(args.otu_name), pad(args.otu_run))
    lineages = pad(args.otu_lineage)
    layouts = pad(getattr(args, 'otu_layout', None))
    fastas, fasta_names = pad(getattr(args, 'otu_sequences', None)), pad(getattr(args, 'otu_sequences_name', None))
    given = list(args.otu_stage or [])
    stages = [('Raw' if (given[0] if len(given) == 1 else (pad(given)[i] or 'final')) == 'raw' else 'Final')
              for i in range(k)] if given else ['Final'] * k
    curated = pad(args.otu_curated_column)
    # A table with a column of curated names gives both raw and final tables, unless it is given as
    # final and another table of the same assay is the raw one (an ASV table before curation, with
    # the off-target ASVs a curated table leaves out): then it gives the final tables only.
    assay_of = [which[i].strip() or (assays[0] if len(assays) == 1 else '') for i in range(k)]
    raw_of = [next((names[j] or Path(args.otu[j]).name for j in range(k)
                    if j != i and not curated[j].strip() and stages[j] == 'Raw' and assay_of[j] == assay_of[i]), None)
              if curated[i].strip() and stages[i] == 'Final' else None for i in range(k)]
    in_stage = {'Raw': 0, 'Final': 0}
    for i in range(k):
        for st in (('Final',) if raw_of[i] else ('Raw', 'Final') if curated[i].strip() else (stages[i],)):
            in_stage[st] += 1
    out, suffixes = [], []
    say = lambda m: log.add('OTU and taxonomy tables', m)  # noqa: E731
    for i, path in enumerate(args.otu):
        label = names[i] or Path(path).name
        assay = which[i].strip()
        if assay and assays and assay not in assays:
            raise StopError(f"OTU table '{label}' is for assay '{assay}', which is not among the assay names "
                            f"({', '.join(assays)})")
        if not assay and len(assays) == 1:
            assay = assays[0]

        def emit(stage, counts, rows, compare, lab, orientation):
            suffix = assay if (in_stage[stage] > 1 or len(assays) > 1) else ''
            if in_stage[stage] > 1 and not assay:
                suffix = str(i + 1)
            if (stage, suffix) in suffixes:
                raise StopError(f"two {stage.lower()} OTU tables are for assay '{assay}'; give each a different "
                                f"assay name, or set one to raw and the other to final")
            suffixes.append((stage, suffix))
            sheet_names = (f'otu{stage}', f'taxa{stage}') if not suffix else \
                (_sheet_name(f'otu{stage}', suffix), _sheet_name(f'taxa{stage}', suffix))
            say(f"{lab}: written as {sheet_names[0]} and {sheet_names[1]}" + (f' (assay {assay})' if assay else ''))
            out.append({'counts': counts, 'taxa': rows, 'suffix': suffix, 'assay': assay, 'run': runs[i].strip(),
                        'label': lab, 'samples': [c for c in counts.columns if c in set(samples)], 'stage': stage,
                        'compare': compare, 'orientation': orientation})
        try:
            frame = (getattr(args, 'otu_frames', None) or [None] * k)[i]
            cc = curated[i].strip()
            if cc:
                frame = fo.read_table_any(path, sheets[i]) if frame is None else frame
                match = [c for c in frame.columns if str(c).strip().lower() == cc.lower()]
                if not match:
                    raise StopError(f"OTU table '{label}' has no column '{cc}' of curated names (columns: "
                                    + ', '.join(str(c) for c in frame.columns[:10]) + ' ...)')
                cc = match[0]
            counts, ann, seqs, orientation = fo.read_otu(path, sheets[i], samples, lib_to_samp, say, label,
                                                         is_detail, frame=frame, layout=layouts[i].strip() or 'detect')
            if fastas[i].strip():
                fasta = read_fasta(fastas[i])
                fname = fasta_names[i] or Path(fastas[i]).name
                found = [x for x in counts.index if x in fasta]
                for x in found:
                    seqs.setdefault(x, fasta[x])
                absent = [x for x in counts.index if x not in fasta]
                say(f'{label}: dna_sequence from {fname} for {len(found)} of {len(counts.index)} sequences'
                    + (f"; {len(absent)} IDs are not in it (e.g. {', '.join(absent[:3])})" if absent else ''))
            if counts.shape[0] == 0 or counts.shape[1] == 0:
                raise StopError(f"OTU table '{label}': no read counts were found ({orientation}, "
                                f"{counts.shape[0]} sequences or taxa, {counts.shape[1]} samples)."
                                + looks_like(path, sheets[i], 'otu', samples, terms, frame))
            if orientation == 'samples as rows':   # the layout most easily misread
                h = looks_like(path, sheets[i], 'otu', samples, terms, frame)
                if h:
                    say(f'{label}: WARNING' + h)
            taxa_df = fo.read_table_any(taxa[i], taxa_sheets[i]) if taxa[i] else None
            if taxa_df is not None:
                h = looks_like(taxa[i], taxa_sheets[i], 'taxonomy', samples, terms, taxa_df)
                if h:
                    say(f"{label}: WARNING about its taxonomy table:" + h)
            if not cc:
                stage = stages[i]
                rows = fo.taxa_rows(list(counts.index), ann, taxa_df, seqs, orientation,
                                    list(other[f'taxa{stage}'].columns), say, label, lineages[i].strip() or None,
                                    report_missing=False)
                emit(stage, counts, rows, fo.all_counts(counts, ann), label, orientation)
                continue
            if orientation != 'samples as columns' or ann is None or cc not in ann.columns:
                raise StopError(f"OTU table '{label}': a column of curated names needs one row per ASV, with the "
                                f"samples as columns")
            raw_ann = ann.drop(columns=[cc])
            if raw_of[i]:
                say(f"{label}: curated names, written as the final tables only: the raw tables are {raw_of[i]}")
                fin = fo.curated_final(counts, ann, cc, seqs, orientation, list(other['taxaFinal'].columns), say,
                                       label, fo.all_counts(counts, raw_ann))
                emit('Final', fin['counts'], fin['taxa'], fin['compare'], label, orientation)
                continue
            rows = fo.taxa_rows(list(counts.index), raw_ann, taxa_df, seqs, orientation,
                                list(other['taxaRaw'].columns), say, f'{label} (raw)', lineages[i].strip() or None,
                                report_missing=False)
            emit('Raw', counts, rows, fo.all_counts(counts, raw_ann), f'{label} (raw)', orientation)
            fin = fo.curated_final(counts, ann, cc, seqs, orientation, list(other['taxaFinal'].columns), say,
                                   f'{label} (final)', fo.all_counts(counts, raw_ann))
            emit('Final', fin['counts'], fin['taxa'], fin['compare'], f'{label} (final)', orientation)
        except fo.OtuError as e:
            raise StopError(with_hint(e, looks_like(path, sheets[i], 'otu', samples, terms, frame)))
    check_raw_final(out, say)
    fill_sequences(out, say)
    for t in out:   # after the filling, so a curated table's rows are counted with their sequences
        missing = sum(not r.get('dna_sequence') for r in t['taxa'].values())
        if missing:
            say(f"{t['label']}: WARNING dna_sequence (mandatory in FAIRe) is empty for {missing} of {len(t['taxa'])} rows"
                + ('; the table has reads summed per taxon, without sequences'
                   if t['orientation'] == 'samples as rows' else ''))
    return out


def fill_sequences(tables, say):
    """dna_sequence for the rows of a table that has none (a curated table, say) from another table
    of the same assay with the same seq_id. FAIRe's final tables name each taxon's row after its most
    abundant ASV and sum the reads of all its ASVs, so a row takes the sequence of the ASV it is
    named after. A row with more reads than that ASV in some samples, and none fewer, holds several
    ASVs; identificationRemarks says so, and the log asks for the other ASVs, which taxaFinal should
    list one per row. A row with fewer reads only is the same ASV with reads removed (as in screening
    for contamination)."""
    for t in tables:
        missing = [s for s, r in t['taxa'].items() if not r.get('dna_sequence')]
        if not missing:
            continue
        for src in tables:
            if src is t or src['assay'] != t['assay'] or not missing:
                continue
            have = {s: r['dna_sequence'] for s, r in src['taxa'].items() if r.get('dna_sequence')}
            common = [c for c in t['compare'].columns if c in set(src['compare'].columns)]
            copied, merged, mixed = [], [], []
            for s in missing:
                if s not in have:
                    continue
                if common:
                    mine = pd.to_numeric(t['compare'].loc[s, common], errors='coerce').fillna(0)
                    theirs = pd.to_numeric(src['compare'].loc[s, common], errors='coerce').fillna(0)
                    more, fewer = bool((mine > theirs).any()), bool((mine < theirs).any())
                else:
                    more = fewer = False
                r = t['taxa'][s]
                r['dna_sequence'] = have[s]
                copied.append(s)
                if more and not fewer:
                    merged.append(s)
                    note = (f"more reads than {s} in {src['label']}, so the reads of several ASVs are summed in "
                            f"this row; dna_sequence is that of {s}, the ASV the row is named after")
                elif more:
                    mixed.append(s)
                    note = (f"reads differ both ways from {s} in {src['label']}; dna_sequence is that of {s}, "
                            f"the ASV the row is named after")
                else:
                    continue
                r['identificationRemarks'] = '; '.join(x for x in (r.get('identificationRemarks'), note) if x)
            if copied:
                rows_ = lambda n: f"{n} row" + ('' if n == 1 else 's')  # noqa: E731
                msg = (f"{t['label']}: dna_sequence taken from {src['label']} for {rows_(len(copied))}: the sequence "
                       f"of the ASV each row is named after")
                if merged:
                    msg += (f"; {rows_(len(merged))} {'holds' if len(merged) == 1 else 'hold'} the reads of several "
                            f"ASVs (more reads than that ASV, e.g. {', '.join(merged[:3])})")
                if mixed:
                    msg += f"; {rows_(len(mixed))} with reads that differ both ways (e.g. {', '.join(mixed[:3])})"
                say(msg)
                if merged:
                    say(f"{t['label']}: WARNING FAIRe's taxaFinal lists every ASV, one per row, and this table has one "
                        f"row per taxon, so the other ASVs of {rows_(len(merged))} are not listed. To list them, give "
                        f"the ASV table with a column of each ASV's curated name (Column of curated names)")
            missing = [s for s in missing if not t['taxa'][s].get('dna_sequence')]


def add_dropdowns(wb, dd):
    """List validations as FAIRe-ator writes them: each controlled-vocabulary column (or
    projectMetadata row) offers the values in its row of the Drop-down values sheet. Other values
    are still accepted, as FAIRe allows 'other: ...'. Returns the number of lists added."""
    ranges = {}
    for i, r in enumerate(dd.itertuples(index=False), 1):
        try:
            k = int(float(r[3]))
        except (TypeError, ValueError):
            continue   # the header row, or a term without options
        if k >= 1 and not _blank(r[0]):
            ranges[str(r[0]).strip()] = f"'Drop-down values'!$E${i}:${get_column_letter(4 + k)}${i}"

    def lists(ws, ref, cells):
        dv = DataValidation(type='list', formula1=ref, allow_blank=True, showErrorMessage=False,
                            showInputMessage=True)
        dv.add(cells)
        ws.add_data_validation(dv)
    n = 0
    for name in ('sampleMetadata', 'experimentRunMetadata'):
        if name not in wb.sheetnames:
            continue
        ws = wb[name]
        last = max(ws.max_row, 103)   # FAIRe-ator's templates cover 100 rows
        for j, c in enumerate(ws[3], 1):
            if c.value in ranges:
                col = get_column_letter(j)
                lists(ws, ranges[c.value], f'{col}4:{col}{last}')
                n += 1
    if 'projectMetadata' in wb.sheetnames:
        ws = wb['projectMetadata']
        end = get_column_letter(ws.max_column)
        for row in ws.iter_rows(min_row=2, max_col=3):
            if row[2].value in ranges:
                lists(ws, ranges[row[2].value], f'D{row[0].row}:{end}{row[0].row}')
                n += 1
    return n


def _sheet_name(base, suffix):
    """Excel allows 31 characters and no []:*?/\\ in sheet names."""
    name = f'{base}_{suffix}' if suffix else base
    return re.sub(r'[\[\]:*?/\\]', '_', name)[:31]


def _write_otu_sheet(wb, name, counts, bold):
    ws = wb.create_sheet(name)
    ws.append(['seq_id'] + [str(c) for c in counts.columns])
    for seq_id, row in counts.iterrows():
        ws.append([seq_id] + [_cell(v) for v in row.tolist()])
    for c in ws[1]:
        c.font = bold
    ws.freeze_panes = 'B2'


def _maybe_number(values, s):
    for v in values:
        if not _blank(v) and str(v) == s:
            return v
    return s


def _cell(v):
    if _blank(v):
        return None
    if isinstance(v, (pd.Timestamp, dt.datetime)):
        return pd.Timestamp(v).isoformat()
    if hasattr(v, 'item') and not isinstance(v, str):
        try:
            return v.item()
        except (AttributeError, ValueError):
            pass
    return v


def _style_sample_sheet(ws, levels, bold):
    for i, lvl in enumerate(levels, 1):
        ws.cell(1, i).fill = PatternFill('solid', fgColor=LEVEL_FILL.get(str(lvl), 'FFFFFF'))
        ws.cell(3, i).font = bold
    ws.freeze_panes = 'B4'


# ------------------------------------------------------------------ main

def split_by_assay_column(args, log):
    """An OTU table that holds several assays, with a column naming each row's assay (Wilderlab's
    target), becomes one table per assay: the OTU arguments are repeated for each, with the rows of
    that assay. If no assay names were given, they are the column's values, in order."""
    args.otu_frames = [None] * len(args.otu or [])
    cols = list(args.otu_assay_column or [])
    if not args.otu or not any(c.strip() for c in cols):
        return
    k = len(args.otu)
    pad = lambda xs: (list(xs or []) + [''] * k)[:k]  # noqa: E731
    names = ('otu_sheet', 'otu_name', 'otu_assay', 'otu_run', 'taxa', 'taxa_sheet', 'otu_lineage', 'otu_curated_column',
             'otu_layout')
    lists = {n: pad(getattr(args, n)) for n in names}
    stages = list(args.otu_stage or [])
    per_table_stage = len(stages) > 1
    stages = pad(stages) if per_table_stage else stages
    given = [a.strip() for a in args.assay_name.split(',') if a.strip()] if args.assay_name else []
    new = {n: [] for n in lists}
    new_otu, new_frames, new_stages, found = [], [], [], []
    for i, path in enumerate(args.otu):
        col = pad(cols)[i].strip()
        label = lists['otu_name'][i] or Path(path).name
        if not col:
            new_otu.append(path)
            new_frames.append(None)
            new_stages += [stages[i]] if per_table_stage else []
            for n in lists:
                new[n].append(lists[n][i])
            continue
        if lists['otu_assay'][i].strip():
            raise StopError(f"OTU table '{label}': give either its assay or the column that holds each row's assay, "
                            f"not both")
        df = fo.read_table_any(path, lists['otu_sheet'][i] or None)
        match = [c for c in df.columns if str(c).strip().lower() == col.lower()]
        if not match:
            raise StopError(f"OTU table '{label}' has no column '{col}' for the assay (columns: "
                            + ', '.join(str(c) for c in df.columns[:8]) + ' ...)')
        headers = {str(c) for c in df.columns}
        repeats = [c for c in df.columns if re.match(r'^(.+)\.\d+$', str(c)) and str(c).rsplit('.', 1)[0] in headers]
        if repeats:
            names = sorted({str(c).rsplit('.', 1)[0] for c in repeats})
            log.add('OTU and taxonomy tables', f"{label}: WARNING {len(names)} column names appear more than once "
                    f"({', '.join(names[:5])}); the first of each is used and the others left out, as the table "
                    f"does not say which samples they are")
            df = df.drop(columns=repeats)
        values = df[match[0]].map(lambda v: '' if fo._blank(v) else str(v).strip())
        assays = list(dict.fromkeys(v for v in values if v))
        empty = int((values == '').sum())
        bad = [a for a in assays if not re.match(r'^[A-Za-z0-9_.-]+$', a)]
        if bad:
            raise StopError(f"OTU table '{label}': assay names can hold only letters, digits, _, . and -: "
                            + ', '.join(bad[:5]))
        unknown = [a for a in assays if given and a not in given]
        if unknown:
            raise StopError(f"OTU table '{label}' has assays that are not among the assay names "
                            f"({', '.join(given)}): {', '.join(unknown)}")
        log.add('OTU and taxonomy tables', f"{label}: the column '{match[0]}' gives each row's assay; "
                f"{len(assays)} assays ({', '.join(assays)}), each written as its own table"
                + (f"; {empty} rows with no assay left out" if empty else ''))
        for a in assays:
            new_otu.append(path)
            new_frames.append(df[values == a].drop(columns=[match[0]]).reset_index(drop=True))
            new_stages += [stages[i]] if per_table_stage else []
            for n in lists:
                new[n].append(lists[n][i])
            new['otu_name'][-1] = f'{label} ({a})'
            new['otu_assay'][-1] = a
            found += [a] if a not in found else []
    args.otu, args.otu_frames = new_otu, new_frames
    for n in lists:
        setattr(args, n, new[n])
    if per_table_stage:
        args.otu_stage = new_stages
    if not given:
        args.assay_name = ','.join(found)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='faire_mapper_apply', description=__doc__.splitlines()[0])
    ap.add_argument('--version', action='version', version=__version__)
    ap.add_argument('table', help='CSV, TSV or Excel table, as given to faire_mapper.py map')
    ap.add_argument('--sheet', help='Excel sheet name (default: first sheet)')
    ap.add_argument('--header_row', type=int, default=1, help='row number of the column headers (default 1)')
    ap.add_argument('--crosswalk', required=True, help='crosswalk (SSSOM TSV) from faire_mapper.py map, after review')
    ap.add_argument('--checklist', required=True, help='FAIRe checklist workbook')
    ap.add_argument('--template', required=True, help='FAIRe full template workbook (FAIRe_checklist_v*_FULLtemplate.xlsx)')
    ap.add_argument('--assay_type', choices=['metabarcoding', 'targeted'], default='metabarcoding')
    ap.add_argument('--sample_types', help='comma-separated sample types (Water, Soil, ...); default all')
    ap.add_argument('--project_id', default='', help='project identifier (letters, digits, _ or -)')
    ap.add_argument('--assay_name', default='', help='assay name(s), comma-separated')
    ap.add_argument('--req_lev', default='M,HR,R,O', help='requirement levels to include (M is always included)')
    ap.add_argument('--country', default='', help='country or sea name to put first in geo_loc_name when the table has none')
    ap.add_argument('--date_order', choices=['stop', 'dmy', 'mdy'], default='stop',
                    help='how to read dates such as 06/09/2017 when no value settles it (default: stop)')
    ap.add_argument('--include_review', action='store_true', help='also apply skos:closeMatch rows (for review)')
    ap.add_argument('--confused_terms', default=str(fm.CONFUSED_TERMS),
                    help='table of FAIRe terms people often confuse; a value for one of them in the project values '
                         'gets a note in the log (default: commonly_confused_terms.tsv beside faire_mapper.py)')
    ap.add_argument('--project_values', help='table (CSV, TSV or Excel) with term and value (and status): values for the whole project, '
                                             'e.g. from faire_mapper_methods.py; rows with status other than '
                                             'supported or confirmed are left out')
    ap.add_argument('--drop_unmapped', action='store_true', help='leave out columns with no skos:exactMatch row in the crosswalk')
    ap.add_argument('--otu', action='append', help='OTU or ASV table (reads per sequence or taxon and sample); repeat '
                                                   'for each assay')
    ap.add_argument('--otu_sequences', action='append', help='FASTA file of the sequences of each OTU table, '
                    'keyed by its sequence IDs (empty for none)')
    ap.add_argument('--otu_sequences_name', action='append', help='name of each FASTA file for the log')
    ap.add_argument('--utc_offset', default='', help='UTC offset of the times of collection (+11:00, -04:00 or Z), '
                    'added when a column of times is joined to the dates in eventDate')
    ap.add_argument('--otu_sheet', action='append', help='Excel sheet of each OTU table (empty for the first sheet)')
    ap.add_argument('--otu_name', action='append', help='name of each OTU table for the log')
    ap.add_argument('--otu_assay', action='append', help='assay of each OTU table (one of --assay_name)')
    ap.add_argument('--otu_curated_column', action='append',
                    help="column of an ASV table holding each ASV's curated name: the table gives otuRaw and "
                         "taxaRaw with every ASV, taxaFinal with one row per ASV that has a curated name, and "
                         "otuFinal with the reads of each name summed under its most abundant ASV")
    ap.add_argument('--otu_assay_column', action='append',
                    help="column of an OTU table that gives each row's assay, for a table that holds several "
                         "(such as Wilderlab's target): one table is written per assay, and the assay names, "
                         "if not given, are the column's values")
    ap.add_argument('--otu_run', action='append', help='sequencing run ID (seq_run_id) of each OTU table, written to '
                                                       'experimentRunMetadata when the table has no run columns')
    ap.add_argument('--taxa', action='append', help='taxonomy table for each OTU table (empty for none)')
    ap.add_argument('--otu_lineage', action='append', help='lineage column to take the taxonomy from, when an OTU '
                                                           'or taxonomy table has several (PR2 tax, Silva 138.1 tax); '
                                                           'default the first')
    ap.add_argument('--taxa_sheet', action='append', help='Excel sheet of each taxonomy table')
    ap.add_argument('--library', action='append', help='library table: a run report from ENA or the SRA, or a run '
                                                       'sheet, with library names, sample names, file names and '
                                                       'checksums; repeat for each')
    ap.add_argument('--library_sheet', action='append', help='Excel sheet of each library table (empty: the first '
                                                             'sheet that names libraries or files)')
    ap.add_argument('--library_name', action='append', help='name of each library table for the log')
    ap.add_argument('--library_assay', action='append', help='assay(s) of each library table, comma-separated: one '
                                                             'row per library and assay')
    ap.add_argument('--library_filter', action='append', help='keep only the libraries whose name holds this text')
    ap.add_argument('--library_run', action='append', help='sequencing run ID (seq_run_id) of each library table, '
                                                           'when it has none')
    ap.add_argument('--otu_layout', action='append', choices=['detect', 'columns', 'rows', 'long', ''],
                    help='layout of each OTU table: detect (the default), columns (samples as columns), rows '
                         '(samples as rows) or long (one row per sample and sequence)')
    ap.add_argument('--otu_stage', action='append', choices=['final', 'raw'],
                    help='for each OTU table: final, written as otuFinal and taxaFinal (the default), or raw, '
                         'written as otuRaw and taxaRaw; one value applies to every table')
    ap.add_argument('--table_name', help='name of the table to record in the README (default: file name)')
    ap.add_argument('--crosswalk_name', help='name of the crosswalk to record in the README (default: file name)')
    ap.add_argument('-o', '--output', required=True, help='FAIRe workbook (.xlsx)')
    ap.add_argument('--log', required=True, help='log (text)')
    args = ap.parse_args(argv)
    log = Log()
    try:
        if args.project_id and not re.match(r'^[A-Za-z0-9_-]+$', args.project_id):
            raise StopError('the project ID can only hold letters, digits, _ and -')
        if args.country and not fm.insdc_country(args.country):
            raise StopError(f"'{args.country}' is not an INSDC country or sea name (for example Australia, "
                            f"Indian Ocean, Coral Sea Islands)")
        args.country = fm.insdc_country(args.country) if args.country else ''
        df = fm.read_table(args.table, args.sheet, args.header_row)
        sample_types = [s.strip() for s in args.sample_types.split(',')] if args.sample_types else None
        terms = fm.load_checklist(args.checklist, assay_type=args.assay_type, sample_types=sample_types)
        by_name = {t.name: t for t in terms}
        cw = read_crosswalk(args.crosswalk)
        log.add('Inputs', f"table: {args.table_name or Path(args.table).name}, {len(df)} rows and "
                          f"{len(df.columns)} columns" + ''.join(f'; {x}' for x in df.attrs.get('read_notes', [])))
        log.add('Inputs', f"crosswalk: {args.crosswalk_name or Path(args.crosswalk).name}, {len(cw)} rows; applied: "
                          f"skos:exactMatch{' and skos:closeMatch' if args.include_review else ''}")
        named = bool(args.assay_name)
        split_by_assay_column(args, log)
        log.add('Inputs', f"assay type {args.assay_type}; sample types {args.sample_types or 'all'}; project ID "
                          f"{args.project_id or '(none)'}; assays {args.assay_name or '(none)'}"
                          + (' (from the assay column of the OTU table)' if args.assay_name and not named else ''))
        rows = choose_rows(cw, list(df.columns), by_name, args.include_review, log)
        counts = build_workbook(args, df, rows, terms, by_name, log)
    except StopError as e:
        log.add('Warnings', f'STOPPED: {e}')
        log.write(args.log)
        print(f'ERROR: {e}', file=sys.stderr)
        return 1
    log.write(args.log)
    print(f"INFO: wrote {counts['samples']} samples and {counts['terms']} FAIRe terms, plus {counts['user_fields']} "
          f"user-defined fields; see the log for conversions and the mandatory terms still empty")
    return 0


if __name__ == '__main__':
    sys.exit(main())
