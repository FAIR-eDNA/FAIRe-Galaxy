"""faire_mapper: propose how the columns of a lab's own eDNA table map to FAIRe terms.

Two steps, each a command:

  profile  Describe every column: type, ranges, date formats, DNA sequences, ENVO-style
           labels, whether values are unique per row or constant across the table.
  map      Score every column against every term in the FAIRe checklist, assign each term
           to at most one column, and write a proposed crosswalk with the evidence for each
           match, plus the mandatory FAIRe terms no column covers (the questions to ask).

Matching uses three kinds of evidence, all read from the FAIRe checklist itself:
  * the header, compared with the term name and common names for it;
  * the values, compared with the term's type, format and allowed values;
  * the level: a column with one value for the whole table suits a project-level term.

No language model is needed. Columns routed to 'review' can be exported as model-agnostic
adjudication requests (--requests), and answers can be applied back (--responses), so a model
can be added later without changing the rest.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import io
import json
import math
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

__version__ = '0.7.2'

MISSING = {'', 'na', 'n/a', 'nan', 'none', 'null', '-', '--', '?', 'not applicable', 'missing',
           'not collected', 'not provided', 'unknown'}
# FAIRe and MIxS missing-value notes, e.g. "not applicable: control sample"
MISSING_PREFIXES = ('not applicable', 'missing', 'not collected', 'not provided', 'restricted access')


def is_missing(v):
    s = str(v).strip().lower()
    return s in MISSING or s.startswith(MISSING_PREFIXES)


# ------------------------------------------------------------------ text normalisation

# Abbreviations used in FAIRe term names and in lab headers, expanded to full words.
ABBREV = {
    'samp': ['sample'], 'smpl': ['sample'], 'spl': ['sample'], 'temp': ['temperature'], 'tmp': ['temperature'],
    'conc': ['concentration'], 'vol': ['volume'], 'ext': ['extraction'], 'extr': ['extraction'],
    'extn': ['extraction'], 'nucl': ['nucleic'], 'diss': ['dissolved'], 'inorg': ['inorganic'],
    'org': ['organic'], 'carb': ['carbon'], 'nitro': ['nitrogen'], 'frac': ['fraction'],
    'prep': ['preparation'], 'precip': ['precipitation'], 'store': ['storage'], 'stor': ['storage'],
    'stored': ['storage'],
    'collect': ['collection'], 'coll': ['collection'], 'mat': ['material'], 'env': ['environment'],
    'geo': ['geographic'], 'loc': ['location'], 'lib': ['library'], 'seq': ['sequencing'],
    'mid': ['index'], 'tot': ['total'], 'col': ['column'], 'num': ['number'], 'no': ['number'],
    'cont': ['control'], 'neg': ['negative'], 'pos': ['positive'], 'rel': ['related'],
    'lat': ['latitude'], 'lon': ['longitude'], 'lng': ['longitude'], 'long': ['longitude'],
    'fwd': ['forward'], 'rev': ['reverse'], 'f': ['forward'], 'r': ['reverse'],
    'max': ['maximum'], 'min': ['minimum'], 'sal': ['salinity'], 'chl': ['chlorophyll'],
    'chla': ['chlorophyll'], 'meth': ['method'], 'dur': ['duration'], 'sol': ['solution'],
    'id': ['identifier'], 'ids': ['identifier'], 'nm': ['name'], 'desc': ['description'],
    'proj': ['project'], 'dept': ['depth'], 'dpth': ['depth'], 'wt': ['weight'],
    'ox': ['oxygen'], 'oxy': ['oxygen'], 'o2': ['oxygen'], 'do': ['dissolved', 'oxygen'],
    'gps': ['coordinate'], 'coord': ['coordinate'], 'coords': ['coordinate'], 'cat': ['category'],
    'amt': ['amount'], 'qty': ['amount'], 'qnt': ['amount'], 'pcr': ['pcr'], 'dna': ['dna'],
    'mol': ['molecular'], 'nr': ['number'], 'yr': ['year'], 'dt': ['date'], 'tm': ['time'],
    'stn': ['station'], 'kit': ['kit'], 'filt': ['filter'], 'pore': ['pore'], 'rep': ['replicate'],
    'bio': ['biological'], 'plt': ['plate'], 'plat': ['platform'], 'inst': ['instrument'],
    'barcode': ['index'], 'tag': ['index'], 'idx': ['index'], 'i7': ['index', 'forward'],
    'i5': ['index', 'reverse'], 'r1': ['read', 'forward', 'file'], 'r2': ['read', 'reverse', 'file'],
    'fastq': ['file'], 'fq': ['file'], 'filename': ['file', 'name'], 'reads': ['read'],
    'sst': ['temperature'], 'ph': ['ph'], 'psu': ['salinity'], 'ppt': ['salinity'],
    'microns': ['micrometre'], 'um': ['micrometre'], 'micron': ['micrometre'],
}
STOPWORDS = {'the', 'of', 'a', 'an', 'in', 'at', 'for', 'used', 'was', 'were', 'and', 'or', 'to',
             'on', 'from', 'with', 'per', 'is', 'value', 'values', 'data', 'info', 'details'}
# Unit strings that appear in headers. Recorded as hints, then dropped from the tokens.
UNIT_TOKENS = {
    'ml': 'mL', 'l': 'L', 'ul': 'µL', 'mg': 'mg', 'g': 'g', 'kg': 'kg', 'm': 'm', 'cm': 'cm',
    'mm': 'mm', 'km': 'km', 'degc': 'degree Celsius', 'c': 'degree Celsius', 'celsius': 'degree Celsius',
    'psu': 'psu', 'ppt': 'ppt', 'umol': 'µmol', 'umolkg': 'µmol/kg', 'umoll': 'µmol/L',
    'mgl': 'mg/L', 'ugl': 'µg/L', 'mgm3': 'mg/m3', 'h': 'h', 'hr': 'h', 'hrs': 'h', 'min': 'min',
    'd': 'd', 'days': 'd', 'um': 'µm', 'micron': 'µm', 'microns': 'µm', 'ngul': 'ng/µL',
}
# Common names for FAIRe terms, from general knowledge of how fields are labelled.
# Used in addition to the term name itself. Keep these general: they describe the
# term, not any particular dataset.
SYNONYMS = {
    'samp_name': ['sample', 'sample identifier', 'sample name', 'sample code', 'sample number'],
    'samp_category': ['sample type', 'sample category', 'control type', 'sample or control'],
    'neg_cont_type': ['negative control type', 'blank type', 'control description'],
    'pos_cont_type': ['positive control type', 'mock community'],
    'materialSampleID': ['material sample', 'specimen identifier', 'parent sample', 'field sample identifier'],
    'decimalLatitude': ['latitude', 'decimal latitude', 'y coordinate', 'coordinate latitude'],
    'decimalLongitude': ['longitude', 'decimal longitude', 'x coordinate', 'coordinate longitude'],
    'geo_loc_name': ['location', 'location name', 'locality', 'site name', 'place', 'country region',
                     'country', 'country name', 'sampling location', 'site location', 'region', 'subregion',
                     'reef', 'island', 'state', 'province', 'territory'],
    'eventDate': ['date', 'collection date', 'sampling date', 'sample date', 'date time',
                  'event date', 'date collected', 'time sampled'],
    'verbatimEventTime': ['time', 'collection time', 'sampling time', 'sample time', 'time collected',
                          'time of collection', 'time of sampling', 'local time', 'event time', 'time of day'],
    'env_broad_scale': ['biome', 'broad habitat', 'broad environment'],
    'env_local_scale': ['habitat', 'local habitat', 'environmental feature', 'local environment'],
    'env_medium': ['environmental medium', 'sample material', 'medium', 'substrate', 'matrix'],
    'habitat_natural_artificial_0_1': ['artificial habitat', 'natural or artificial', 'aquarium'],
    'samp_collect_method': ['collection method', 'sampling method', 'sampling protocol'],
    'samp_collect_device': ['collection device', 'sampling device', 'sampler', 'sampling gear', 'niskin'],
    'samp_size': ['sample volume', 'volume', 'volume filtered', 'filtered volume', 'amount sampled',
                  'sample size', 'sample amount', 'water volume'],
    'samp_size_unit': ['sample volume unit', 'volume unit', 'sample size unit'],
    'samp_store_temp': ['storage temperature', 'stored at', 'freezer temperature'],
    'samp_store_sol': ['preservative', 'storage buffer', 'storage solution', 'preservation', 'fixative'],
    'samp_store_dur': ['storage duration', 'storage time', 'time stored', 'holding time', 'days frozen',
                       'days stored', 'time frozen', 'days in freezer'],
    'samp_store_loc': ['storage location', 'freezer', 'stored location'],
    'dna_store_loc': ['dna storage location', 'extract storage', 'dna freezer'],
    'samp_mat_process': ['sample processing', 'processing method', 'filtration method'],
    'size_frac_low': ['prefilter', 'pre filter', 'minimum pore size', 'size fraction lower', 'prefilter pore size'],
    'size_frac': ['pore size', 'filter pore size', 'size fraction', 'maximum pore size', 'filter size',
                  'mesh size', 'filter mesh size'],
    'filter_material': ['filter material', 'filter type', 'membrane', 'membrane type'],
    'filter_name': ['filter name', 'filter product', 'filter brand', 'filter model', 'filter catalogue'],
    'precip_chem_prep': ['precipitation chemical', 'precipitation reagent'],
    'precip_force_prep': ['centrifugation force', 'centrifuge speed', 'g force'],
    'precip_time_prep': ['centrifugation time', 'spin time', 'precipitation time'],
    'precip_temp_prep': ['centrifugation temperature', 'precipitation temperature'],
    'samp_vol_we_dna_ext': ['extraction volume', 'volume extracted', 'amount extracted', 'extraction input',
                            'extraction weight', 'mass extracted'],
    'samp_vol_we_dna_ext_unit': ['extraction volume unit', 'extraction unit'],
    'nucl_acid_ext_lysis': ['lysis', 'lysis method', 'lysis step', 'bead beating'],
    'nucl_acid_ext_sep': ['separation method', 'purification', 'column', 'magnetic beads'],
    'nucl_acid_ext': ['extraction method', 'extraction protocol', 'dna extraction', 'extraction'],
    'nucl_acid_ext_kit': ['extraction kit', 'kit', 'dna kit', 'extraction kit name'],
    'assay_name': ['assay', 'assay name', 'assay identifier'],
    'minimumDepthInMeters': ['depth', 'sample depth', 'sampling depth', 'minimum depth', 'water depth sampled',
                             'min depth', 'shallowest depth'],
    'maximumDepthInMeters': ['maximum depth', 'max depth', 'deepest depth'],
    'tot_depth_water_col': ['water depth', 'bottom depth', 'total depth', 'site depth', 'station depth',
                            'seafloor depth', 'depth to bottom'],
    'temp': ['temperature', 'water temperature', 'sea surface temperature'],
    'chlorophyll': ['chlorophyll', 'chlorophyll a', 'fluorescence'],
    'ph': ['ph', 'acidity'],
    'salinity': ['salinity', 'conductivity salinity'],
    'diss_inorg_carb': ['dissolved inorganic carbon', 'dic', 'total carbon dioxide', 'tco2'],
    'diss_oxygen': ['dissolved oxygen', 'oxygen', 'do'],
    'nitrate': ['nitrate', 'no3'],
    'nitrite': ['nitrite', 'no2'],
    'pcr_plate_id': ['pcr plate', 'plate', 'plate identifier', 'plate number'],
    'lib_id': ['library', 'library identifier', 'library name', 'library code'],
    'seq_run_id': ['run', 'run identifier', 'sequencing run', 'run name', 'flowcell', 'flow cell'],
    'mid_forward': ['forward index', 'index 1', 'i7 index', 'forward barcode', 'forward tag', 'barcode 1'],
    'mid_reverse': ['reverse index', 'index 2', 'i5 index', 'reverse barcode', 'reverse tag', 'barcode 2'],
    'filename': ['forward read file', 'read 1 file', 'r1 file', 'fastq file', 'forward fastq', 'file name'],
    'filename2': ['reverse read file', 'read 2 file', 'r2 file', 'reverse fastq'],
    'associatedSequences': ['accession', 'sra accession', 'ena accession', 'genbank accession', 'archive accession'],
    'input_read_count': ['read count', 'number of reads', 'raw reads', 'total reads', 'reads'],
    'target_gene': ['marker', 'gene', 'target gene', 'locus', 'barcode region', 'marker gene', 'amplicon'],
    'target_subfragment': ['region', 'variable region', 'subregion', 'hypervariable region'],
    'pcr_primer_forward': ['forward primer', 'forward primer sequence', 'primer forward', 'fwd primer'],
    'pcr_primer_reverse': ['reverse primer', 'reverse primer sequence', 'primer reverse', 'rev primer'],
    'pcr_primer_name_forward': ['forward primer name', 'forward primer identifier'],
    'pcr_primer_name_reverse': ['reverse primer name', 'reverse primer identifier'],
    'platform': ['sequencing platform', 'platform', 'sequencing technology'],
    'instrument': ['sequencer', 'instrument', 'sequencing instrument', 'sequencer model', 'machine'],
    'project_id': ['project', 'project code', 'project identifier', 'survey', 'expedition', 'cruise'],
    'project_name': ['project name', 'project title', 'study title'],
    'recordedBy': ['collector', 'collected by', 'sampler name', 'recorded by', 'person', 'people',
                   'filtered by', 'processed by', 'name of the person'],
    'biological_rep': ['replicate', 'replicate number', 'biological replicate'],
    'samp_store_date': ['storage date'],
}

_CAMEL = re.compile(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])')


def _plain(token):
    if len(token) > 4 and token.endswith('ies'):
        return token[:-3] + 'y'
    if len(token) > 3 and token.endswith('s') and not token.endswith('ss'):
        return token[:-1]
    return token


# Abbreviations still expanded in descriptions, which are written in full words: 'how long' is not a
# longitude, nor 'otherwise no' a number.
DESC_ABBREV = {'id', 'ids', 'temp', 'conc', 'vol', 'lat', 'lon', 'lng', 'gps', 'coord', 'coords', 'samp', 'smpl'}


def tokens_of(text, expand=True, units=None, keep_units=False):
    """Lower-case content tokens of a header or term name, with abbreviations expanded. Unit words
    after the first word are dropped (recorded in `units`), unless keep_units (for descriptions)."""
    text = str(text).replace('µ', 'u').replace('°', 'deg ').replace('μ', 'u')
    # Units in brackets, e.g. "Volume (mL)", are recorded as hints and removed.
    for inner in re.findall(r'[\(\[]([^\)\]]*)[\)\]]', text):
        key = re.sub(r'[^a-z0-9]', '', inner.lower())
        if units is not None and key in UNIT_TOKENS:
            units.append(UNIT_TOKENS[key])
    text = re.sub(r'[\(\[][^\)\]]*[\)\]]', ' ', text)
    # keep mixed-case words such as pH, eDNA and rRNA whole
    text = text.replace('_', ' ')
    text = re.sub(r'\b([a-z]{1,2})([A-Z]{1,4})\b', lambda m: m.group(0).lower(), text)
    text = _CAMEL.sub(' ', text)
    raw = re.findall(r'[a-z0-9]+', text.lower())
    # re-join tokens split from short alphanumerics such as 16s, co1, r1, i7
    joined = []
    for t in raw:
        if joined and t.isalpha() and len(t) <= 2 and joined[-1].isdigit() and len(joined[-1]) <= 3:
            joined[-1] = joined[-1] + t
        elif joined and t.isdigit() and len(t) <= 2 and joined[-1].isalpha() and len(joined[-1]) <= 2:
            joined[-1] = joined[-1] + t
        else:
            joined.append(t)
    out = []
    for i, t in enumerate(joined):
        if t in UNIT_TOKENS and i > 0 and t not in ABBREV and not keep_units:
            if units is not None:
                units.append(UNIT_TOKENS[t])
            continue
        if t in STOPWORDS:
            continue
        if expand and t in ABBREV and (not keep_units or t in DESC_ABBREV):
            out.extend(ABBREV[t])
        else:
            out.append(_plain(t))
    return out


# ------------------------------------------------------------------ checklist

@dataclass
class Term:
    name: str
    description: str
    sheets: tuple
    section: str
    requirement: str
    condition: str
    term_type: str
    unit: str
    fixed_format: str
    vocab: tuple
    example: str
    sample_types: str
    kind: str = 'text'
    level: str = 'sample'
    aliases: list = field(default_factory=list)   # list of token lists
    unit_term: str = ''   # the term that holds this term's unit, e.g. samp_size_unit for samp_size
    source: str = 'FAIRe'  # or MIxS or Darwin Core (mixs_dwc_terms.tsv)
    term_id: str = ''      # MIXS:0000505, dwc:verbatimDepth
    label: str = ''        # the standard's own label, e.g. 'total depth of water column'
    scope: str = ''        # where the standard uses it (MIxS extensions, Darwin Core group)

    @property
    def mandatory(self):
        return self.requirement.lower() == 'mandatory'


MAPPABLE_SHEETS = ('sampleMetadata', 'experimentRunMetadata', 'projectMetadata')


def _s(v):
    return '' if v is None or (isinstance(v, float) and math.isnan(v)) else str(v).strip()


def term_kind(name, term_type, fixed_format, vocab, example=''):
    """What the values of a term should look like. A fixed-format term with no format given takes its
    form from the example: date_ext has none, but its example is an ISO date."""
    tt, ff = term_type.lower(), fixed_format.lower()
    if tt == 'fixed format' and not ff and re.match(r'^\d{4}-\d{2}-\d{2}', example.strip()):
        ff = 'yyyy-mm-dd'
    if name == 'decimalLatitude':
        return 'latitude'
    if name == 'decimalLongitude':
        return 'longitude'
    if name in ('pcr_primer_forward', 'pcr_primer_reverse', 'probe_seq'):
        return 'primer'
    if name in ('mid_forward', 'mid_reverse'):
        return 'index_seq'
    if name in ('filename', 'filename2'):
        return 'filename'
    if name in ('samp_name', 'materialSampleID', 'lib_id', 'seq_samp_id'):
        return 'identifier'
    if tt == 'boolean':
        return 'boolean'
    if tt == 'integer':
        return 'integer'
    if tt == 'numeric':
        return 'number'
    if tt == 'numeric or controlled vocabulary':
        return 'number_or_vocab'
    if 'termlabel' in ff:
        return 'termlabel'
    if 'yyyy-mm-dd' in ff:
        return 'date'
    if 'pnynmn' in ff:
        return 'duration'
    if 'country or sea' in ff:
        return 'geoloc'
    if tt == 'controlled vocabulary':
        if vocab and all(v.startswith('http') for v in vocab):
            return 'termlabel'
        return 'vocab'
    return 'text'


def load_checklist(path, assay_type=None, sample_types=None, sheets=MAPPABLE_SHEETS):
    df = pd.read_excel(path, sheet_name='checklist')
    terms = []
    for r in df.to_dict('records'):
        name = _s(r.get('term_name'))
        if not name:
            continue
        tsheets = tuple(s.strip() for s in _s(r.get('data_type')).split('|') if s.strip())
        if not any(s in sheets for s in tsheets):
            continue
        section = _s(r.get('section'))
        if assay_type == 'metabarcoding' and section == 'Targeted assay detection':
            continue
        if assay_type == 'targeted' and section in ('Library preparation sequencing', 'Bioinformatics', 'OTU/ASV'):
            continue
        spec = _s(r.get('sample_type_specificity'))
        if sample_types and spec and spec != 'ALL' and 'other' not in [s.lower() for s in sample_types]:
            if not any(st.lower() in spec.lower() for st in sample_types):
                continue
        vocab = tuple(v.strip() for v in _s(r.get('controlled_vocabulary_options')).split('|')
                      if v.strip() and not v.strip().lower().startswith('other'))
        t = Term(name=name, description=_s(r.get('description')), sheets=tsheets, section=section,
                 requirement=_s(r.get('requirement_level')), condition=_s(r.get('requirement_level_condition')),
                 term_type=_s(r.get('term_type')), unit=_s(r.get('unit')), fixed_format=_s(r.get('fixed_format')),
                 vocab=vocab, example=_s(r.get('example')), sample_types=spec)
        t.kind = term_kind(name, t.term_type, t.fixed_format, vocab, t.example)
        t.level = 'sample' if any(s in ('sampleMetadata', 'experimentRunMetadata') for s in tsheets) else 'project'
        names = [name] + SYNONYMS.get(name, [])
        t.aliases = [tokens_of(n) for n in names]
        t.aliases = [a for a in t.aliases if a]
        terms.append(t)
    names = {t.name for t in terms}
    for t in terms:
        if f'{t.name}_unit' in names:
            t.unit_term = f'{t.name}_unit'
    return terms


OTHER_TERMS = Path(__file__).with_name('mixs_dwc_terms.tsv')


def load_other_terms(path=OTHER_TERMS, exclude=()):
    """MIxS and Darwin Core terms that FAIRe does not have (mixs_dwc_terms.tsv), as Terms, for columns with
    no FAIRe term: the FAIRe guidelines ask for a MIxS or Darwin Core term before a made-up name. Terms
    named in exclude (the FAIRe terms in use) are left out."""
    if not path or not Path(path).exists():
        return []
    lines = [ln for ln in Path(path).read_text(encoding='utf-8').splitlines() if ln and not ln.startswith('#')]
    table = pd.read_csv(io.StringIO('\n'.join(lines)), sep='\t', dtype=str, keep_default_na=False)
    exclude = set(exclude)
    out = []
    for r in table.to_dict('records'):
        name = r['term'].strip()
        if not name or name in exclude:
            continue
        t = Term(name=name, description=r['definition'], sheets=('sampleMetadata',), section='', requirement='',
                 condition='', term_type='', unit=r['unit'], fixed_format='', vocab=(), example=r['example'],
                 sample_types='', kind=r['kind'] or 'text', source=r['source'], term_id=r['id'],
                 label=r['label'], scope=r['scope'])
        t.aliases = [a for a in (tokens_of(name), tokens_of(r['label'])) if a]
        if len(t.aliases) == 2 and t.aliases[0] == t.aliases[1]:
            t.aliases = t.aliases[:1]
        out.append(t)
    return out


def fixed_unit(t):
    """The unit a term's values must be in, as FAIRe writes it ('µm', 'degree Celsius', 'm'), or ''."""
    u = t.unit.strip()
    if not u or u.lower().startswith(('select', 'same as', 'no unit')) or t.unit_term:
        return ''
    return UNIT_ALIASES.get(u.lower(), u)


# ------------------------------------------------------------------ column profiling

DNA_RE = re.compile(r'^[ACGTURYSWKMBDHVNI]+$', re.I)
TERMLABEL_RE = re.compile(r'^.+\[\s*[A-Za-z]+[:_]\s*\d+\s*\]$')
GEOLOC_RE = re.compile(r"^[A-Za-z][A-Za-z .'()-]+:\s*\S")
ISO_DUR_RE = re.compile(r'^P(?=\d)(\d+Y)?(\d+M)?(\d+W)?(\d+D)?(T(\d+H)?(\d+M)?(\d+S)?)?$', re.I)
HUMAN_DUR_RE = re.compile(r'^\d+(\.\d+)?\s*(d|day|days|h|hr|hrs|hour|hours|min|mins|minute|minutes|wk|week|weeks|month|months|yr|year|years)$', re.I)
FILE_RE = re.compile(r'\.(fastq|fq|fasta|fa|bam|sff)(\.gz|\.bz2)?$', re.I)
BOOL = {'0', '1', 'yes', 'no', 'y', 'n', 'true', 'false', 't', 'f', '0.0', '1.0'}
DATE_FORMATS = [
    ('%Y-%m-%d', 'yyyy-mm-dd'), ('%Y-%m-%dT%H:%M', 'ISO date-time'), ('%Y-%m-%dT%H:%M:%S', 'ISO date-time'),
    ('%Y-%m-%d %H:%M:%S', 'yyyy-mm-dd hh:mm:ss'), ('%Y-%m-%d %H:%M', 'yyyy-mm-dd hh:mm'),
    ('%Y/%m/%d', 'yyyy/mm/dd'), ('%d/%m/%Y', 'dd/mm/yyyy'), ('%d/%m/%y', 'dd/mm/yy'),
    ('%d-%m-%Y', 'dd-mm-yyyy'), ('%d.%m.%Y', 'dd.mm.yyyy'), ('%d.%m.%y', 'dd.mm.yy'), ('%Y%m%d', 'yyyymmdd'),
    ('%d %b %Y', 'dd Mon yyyy'), ('%d-%b-%Y', 'dd-Mon-yyyy'), ('%d-%b-%y', 'dd-Mon-yy'),
    ('%d %B %Y', 'dd Month yyyy'), ('%m/%d/%Y', 'mm/dd/yyyy'), ('%Y-%m', 'yyyy-mm'),
]
# A time of day: 10:00, 22:30:00, 4:00 pm, 10am (a column of its own, beside a column of dates).
TIME_OF_DAY_RE = re.compile(r'^(([01]?\d|2[0-3])(:[0-5]\d){1,2}(\s?[ap]\.?m\.?)?|(1[0-2]|0?[1-9])\s?[ap]\.?m\.?)$', re.I)
ISO_OFFSET_RE = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(Z|[+-]\d{2}:?\d{2})$')

# A number and its unit in one cell, e.g. "1 L", "0.2 micron", "-20 °C".
QUANTITY_RE = re.compile(r'^([-+]?\d+(?:\.\d+)?)\s*([^\d\s.,;:][^\d]*?)\.?$')
# Written units, lower case, to the spelling FAIRe uses.
UNIT_ALIASES = {
    'l': 'L', 'litre': 'L', 'liter': 'L', 'litres': 'L', 'liters': 'L', 'ltr': 'L',
    'ml': 'mL', 'millilitre': 'mL', 'milliliter': 'mL', 'millilitres': 'mL', 'milliliters': 'mL',
    'ul': 'µL', 'µl': 'µL', 'μl': 'µL', 'microlitre': 'µL', 'microliter': 'µL', 'microlitres': 'µL',
    'g': 'g', 'gram': 'g', 'grams': 'g', 'mg': 'mg', 'kg': 'kg', 'ug': 'µg', 'µg': 'µg',
    'um': 'µm', 'µm': 'µm', 'μm': 'µm', 'micron': 'µm', 'microns': 'µm', 'micrometre': 'µm',
    'micrometer': 'µm', 'micrometres': 'µm', 'micrometers': 'µm', 'mm': 'mm', 'cm': 'cm', 'm': 'm',
    'metre': 'm', 'meter': 'm', 'metres': 'm', 'meters': 'm', 'km': 'km', 'nm': 'nm',
    'cm2': 'cm2', 'm2': 'm2', 'cm3': 'cm3', 'm3': 'm3',
    'c': 'degree Celsius', '°c': 'degree Celsius', 'ºc': 'degree Celsius', 'degc': 'degree Celsius',
    'deg c': 'degree Celsius', 'degrees c': 'degree Celsius', 'degree celsius': 'degree Celsius',
    'degrees celsius': 'degree Celsius', 'celsius': 'degree Celsius',
    'd': 'd', 'day': 'd', 'days': 'd', 'h': 'h', 'hr': 'h', 'hrs': 'h', 'hour': 'h', 'hours': 'h',
    'min': 'min', 'mins': 'min', 'minute': 'min', 'minutes': 'min', 'wk': 'wk', 'wks': 'wk',
    'week': 'wk', 'weeks': 'wk', 'month': 'mo', 'months': 'mo', 'yr': 'yr', 'yrs': 'yr', 'year': 'yr',
    'years': 'yr', '%': '%', 'percent': '%', 'psu': 'psu', 'ppt': 'ppt',
}
# The same quantity in another unit: factor to the unit FAIRe asks for.
UNIT_FACTORS = {('mm', 'µm'): 1000, ('nm', 'µm'): 0.001, ('cm', 'm'): 0.01, ('km', 'm'): 1000, ('mm', 'm'): 0.001}
# Time units, as written in headers or cells, to ISO 8601 duration designators.
ISO_DURATION_UNITS = {'yr': ('Y', False), 'mo': ('M', False), 'wk': ('W', False), 'd': ('D', False),
                      'h': ('H', True), 'min': ('M', True)}
HEADER_TIME_UNIT_RE = re.compile(r'\b(days?|hours?|hrs?|weeks?|months?|years?|minutes?|mins?)\b', re.I)


# Latitude and longitude in one cell: MIxS lat_lon ("40.57773667 S 148.7301917 E") or a pair of
# decimal degrees ("-33.85, 151.21").
LATLON_MIXS_RE = re.compile(r'^\s*(-?\d{1,2}(?:\.\d+)?)\s*([NS])[\s,;]+(-?\d{1,3}(?:\.\d+)?)\s*([EW])\s*$', re.I)
LATLON_PAIR_RE = re.compile(r'^\s*([-+]?\d{1,2}\.\d+)\s*(?:[,;]\s*|\s+)([-+]?\d{1,3}\.\d+)\s*$')


def parse_lat_lon(v):
    """(latitude, longitude) as signed decimal text, keeping the digits given, or None."""
    s = str(v).strip()
    m = LATLON_MIXS_RE.match(s)
    if m:
        lat, ns, lon, ew = m.groups()
        # A minus sign as well as S or W ("-42.05 S") says the same twice; with N or E it contradicts.
        if (lat.startswith('-') and ns.upper() == 'N') or (lon.startswith('-') and ew.upper() == 'E'):
            return None
        lat, lon = lat.lstrip('-'), lon.lstrip('-')
        lat = ('-' if ns.upper() == 'S' and float(lat) else '') + lat
        lon = ('-' if ew.upper() == 'W' and float(lon) else '') + lon
    else:
        m = LATLON_PAIR_RE.match(s)
        if not m:
            return None
        lat, lon = (x.lstrip('+') for x in m.groups())
    if abs(float(lat)) > 90 or abs(float(lon)) > 180:
        return None
    return lat, lon


def parse_quantity(v):
    """'1 L' -> ('1', 'L'); None when the value is not a number followed by a known unit."""
    m = QUANTITY_RE.match(str(v).strip())
    if not m:
        return None
    unit = UNIT_ALIASES.get(re.sub(r'\s+', ' ', m.group(2).strip().lower()))
    return (m.group(1), unit) if unit else None


def iso_duration(number, unit):
    """(316, 'd') -> 'P316D'; (2.5, 'h') -> 'PT2.5H'; None for other units."""
    if unit not in ISO_DURATION_UNITS:
        return None
    letter, timepart = ISO_DURATION_UNITS[unit]
    x = float(number)
    n = str(int(x)) if x.is_integer() else f'{x:g}'
    return f"P{'T' if timepart else ''}{n}{letter}"


# INSDC geographic location names for the first part of geo_loc_name (the NCBI list, updated
# 30 October 2024: https://www.ncbi.nlm.nih.gov/genbank/collab/country/).
INSDC_COUNTRIES = tuple(
    "Afghanistan|Albania|Algeria|American Samoa|Andorra|Angola|Anguilla|Antarctica|Antigua and Barbuda|"
    "Arctic Ocean|Argentina|Armenia|Aruba|Ashmore and Cartier Islands|Atlantic Ocean|Australia|Austria|"
    "Azerbaijan|Bahamas|Bahrain|Baltic Sea|Baker Island|Bangladesh|Barbados|Bassas da India|Belarus|"
    "Belgium|Belize|Benin|Bermuda|Bhutan|Bolivia|Borneo|Bosnia and Herzegovina|Botswana|Bouvet Island|"
    "Brazil|British Virgin Islands|Brunei|Bulgaria|Burkina Faso|Burundi|Cambodia|Cameroon|Canada|"
    "Cape Verde|Cayman Islands|Central African Republic|Chad|Chile|China|Christmas Island|"
    "Clipperton Island|Cocos Islands|Colombia|Comoros|Cook Islands|Coral Sea Islands|Costa Rica|"
    "Cote d'Ivoire|Croatia|Cuba|Curacao|Cyprus|Czechia|Democratic Republic of the Congo|Denmark|"
    "Djibouti|Dominica|Dominican Republic|Ecuador|Egypt|El Salvador|Equatorial Guinea|Eritrea|Estonia|"
    "Eswatini|Ethiopia|Europa Island|Falkland Islands (Islas Malvinas)|Faroe Islands|Fiji|Finland|"
    "France|French Guiana|French Polynesia|French Southern and Antarctic Lands|Gabon|Gambia|Gaza Strip|"
    "Georgia|Germany|Ghana|Gibraltar|Glorioso Islands|Greece|Greenland|Grenada|Guadeloupe|Guam|"
    "Guatemala|Guernsey|Guinea|Guinea-Bissau|Guyana|Haiti|Heard Island and McDonald Islands|Honduras|"
    "Hong Kong|Howland Island|Hungary|Iceland|India|Indian Ocean|Indonesia|Iran|Iraq|Ireland|"
    "Isle of Man|Israel|Italy|Jamaica|Jan Mayen|Japan|Jarvis Island|Jersey|Johnston Atoll|Jordan|"
    "Juan de Nova Island|Kazakhstan|Kenya|Kerguelen Archipelago|Kingman Reef|Kiribati|Kosovo|Kuwait|"
    "Kyrgyzstan|Laos|Latvia|Lebanon|Lesotho|Liberia|Libya|Liechtenstein|Line Islands|Lithuania|"
    "Luxembourg|Macau|Madagascar|Malawi|Malaysia|Maldives|Mali|Malta|Marshall Islands|Martinique|"
    "Mauritania|Mauritius|Mayotte|Mediterranean Sea|Mexico|Micronesia, Federated States of|"
    "Midway Islands|Moldova|Monaco|Mongolia|Montenegro|Montserrat|Morocco|Mozambique|Myanmar|Namibia|"
    "Nauru|Navassa Island|Nepal|Netherlands|New Caledonia|New Zealand|Nicaragua|Niger|Nigeria|Niue|"
    "Norfolk Island|North Korea|North Macedonia|North Sea|Northern Mariana Islands|Norway|Oman|"
    "Pacific Ocean|Pakistan|Palau|Palmyra Atoll|Panama|Papua New Guinea|Paracel Islands|Paraguay|Peru|"
    "Philippines|Pitcairn Islands|Poland|Portugal|Puerto Rico|Qatar|Republic of the Congo|Reunion|"
    "Romania|Ross Sea|Russia|Rwanda|Saint Barthelemy|Saint Helena|Saint Kitts and Nevis|Saint Lucia|"
    "Saint Martin|Saint Pierre and Miquelon|Saint Vincent and the Grenadines|Samoa|San Marino|"
    "Sao Tome and Principe|Saudi Arabia|Senegal|Serbia|Seychelles|Sierra Leone|Singapore|Sint Maarten|"
    "Slovakia|Slovenia|Solomon Islands|Somalia|South Africa|South Georgia and the South Sandwich Islands|"
    "South Korea|South Sudan|Southern Ocean|Spain|Spratly Islands|Sri Lanka|State of Palestine|Sudan|"
    "Suriname|Svalbard|Sweden|Switzerland|Syria|Taiwan|Tajikistan|Tanzania|Tasman Sea|Thailand|"
    "Timor-Leste|Togo|Tokelau|Tonga|Trinidad and Tobago|Tromelin Island|Tunisia|Turkey|Turkmenistan|"
    "Turks and Caicos Islands|Tuvalu|Uganda|Ukraine|United Arab Emirates|United Kingdom|Uruguay|USA|"
    "Uzbekistan|Vanuatu|Venezuela|Viet Nam|Virgin Islands|Wake Island|Wallis and Futuna|West Bank|"
    "Western Sahara|Yemen|Zambia|Zimbabwe".split('|'))
# Other spellings and the list's historical names that have one current name.
COUNTRY_ALIASES = {
    'united states': 'USA', 'united states of america': 'USA', 'u.s.a.': 'USA', 'us': 'USA',
    'uk': 'United Kingdom', 'great britain': 'United Kingdom', 'vietnam': 'Viet Nam',
    'czech republic': 'Czechia', 'ivory coast': "Cote d'Ivoire", "côte d'ivoire": "Cote d'Ivoire",
    'burma': 'Myanmar', 'east timor': 'Timor-Leste', 'swaziland': 'Eswatini', 'macedonia': 'North Macedonia',
    'the former yugoslav republic of macedonia': 'North Macedonia', 'turkiye': 'Turkey', 'türkiye': 'Turkey',
    'micronesia': 'Micronesia, Federated States of', 'curaçao': 'Curacao', 'réunion': 'Reunion',
}
_COUNTRY_KEYS = {c.lower(): c for c in INSDC_COUNTRIES}


def insdc_country(v):
    """The INSDC name for a country or sea name, or None."""
    s = re.sub(r'\s+', ' ', str(v).strip()).lower()
    return _COUNTRY_KEYS.get(s) or COUNTRY_ALIASES.get(s)


def _date_format(v):
    if isinstance(v, (dt.datetime, dt.date, pd.Timestamp)):
        return 'Excel date'
    s = str(v).strip()
    if ISO_OFFSET_RE.match(s):
        return 'ISO date-time with offset'
    for fmt, label in DATE_FORMATS:
        try:
            d = dt.datetime.strptime(s, fmt)
            if 1900 <= d.year <= 2100:
                return label
        except ValueError:
            continue
    return None


@dataclass
class ColumnProfile:
    column: str
    n_rows: int
    n_values: int
    n_unique: int
    constant: bool
    unique_per_row: bool
    numeric_frac: float = 0.0
    integer_frac: float = 0.0
    min: float | None = None
    max: float | None = None
    decimals_median: float | None = None
    date_frac: float = 0.0
    date_format: str = ''
    serial_date_frac: float = 0.0
    dna_frac: float = 0.0
    dna_length_median: float | None = None
    termlabel_frac: float = 0.0
    geoloc_frac: float = 0.0
    boolean_frac: float = 0.0
    duration_frac: float = 0.0
    duration_human_frac: float = 0.0
    time_frac: float = 0.0
    filename_frac: float = 0.0
    read_pair: str = ''
    quantity_frac: float = 0.0
    quantity_units: list = field(default_factory=list)
    country_frac: float = 0.0
    latlon_frac: float = 0.0
    header_time_unit: str = ''
    missing_tokens: int = 0
    header_units: list = field(default_factory=list)
    examples: list = field(default_factory=list)
    distinct: list = field(default_factory=list)

    def summary(self):
        tags = []
        if self.constant:
            tags.append('constant')
        if self.unique_per_row:
            tags.append('unique per row')
        for name, frac in (('numeric', self.numeric_frac), ('date', self.date_frac), ('DNA', self.dna_frac),
                           ('ENVO-style label', self.termlabel_frac), ('place name', self.geoloc_frac),
                           ('country or sea name', self.country_frac),
                           ('boolean', self.boolean_frac), ('ISO duration', self.duration_frac),
                           ('duration', self.duration_human_frac), ('time of day', self.time_frac),
                           ('sequence file', self.filename_frac),
                           ('latitude and longitude in one cell', self.latlon_frac)):
            if frac >= 0.7:
                tags.append(name)
        if self.quantity_frac >= 0.7 and self.duration_human_frac < 0.7:
            tags.append('number and unit in each cell (' + ', '.join(self.quantity_units) + ')')
        if self.date_format:
            tags.append(f'date format {self.date_format}')
        if self.numeric_frac >= 0.7 and self.min is not None:
            tags.append(f'range {self.min:g} to {self.max:g}')
        if self.dna_length_median:
            tags.append(f'sequence length ~{self.dna_length_median:g}')
        if self.header_units:
            tags.append('unit in header: ' + ', '.join(self.header_units))
        if self.header_time_unit:
            tags.append(f'time unit in header: {self.header_time_unit}')
        return '; '.join(tags)


def profile_column(column, series):
    raw = [v for v in series.tolist() if not (v is None or (isinstance(v, float) and math.isnan(v)))]
    vals = [v for v in raw if not is_missing(v)]
    strs = [str(v).strip() for v in vals]
    n = len(strs)
    units = []
    tokens_of(column, units=units)
    p = ColumnProfile(column=str(column), n_rows=len(series), n_values=n, n_unique=len(set(strs)),
                      constant=(n >= 2 and len(set(strs)) == 1), unique_per_row=(n >= 3 and len(set(strs)) == n),
                      missing_tokens=len(raw) - n, header_units=sorted(set(units)),
                      examples=list(dict.fromkeys(strs))[:5], distinct=list(dict.fromkeys(strs))[:60])
    if not n:
        return p
    nums = []
    decimals = []
    for v, s in zip(vals, strs):
        if isinstance(v, bool):
            continue
        try:
            x = float(s.replace(',', '')) if not isinstance(v, (int, float)) else float(v)
        except ValueError:
            continue
        if math.isfinite(x):
            nums.append(x)
            decimals.append(len(s.split('.')[1]) if '.' in s else 0)
    p.numeric_frac = round(len(nums) / n, 3)
    if nums:
        p.integer_frac = round(sum(1 for x in nums if float(x).is_integer()) / len(nums), 3)
        p.min, p.max = min(nums), max(nums)
        p.decimals_median = float(pd.Series(decimals).median())
        # Excel stores dates as days since 1899-12-30; 32874 to 54789 covers 1990 to 2049.
        p.serial_date_frac = round(sum(1 for x in nums if 32874 <= x < 54789) / n, 3)
    fmts = [_date_format(v) for v in vals]
    dated = [f for f in fmts if f]
    # Plain numbers such as 20240315 or 2021 can parse as dates; only count them if most look like dates.
    if dated and p.numeric_frac < 0.5 or (dated and len(dated) / n >= 0.9 and all(f in ('yyyymmdd', 'Excel date') for f in dated)):
        p.date_frac = round(len(dated) / n, 3)
        p.date_format = pd.Series(dated).mode().iloc[0]
    dna = [s for s in strs if len(s) >= 6 and DNA_RE.match(s)]
    p.dna_frac = round(len(dna) / n, 3)
    if dna:
        p.dna_length_median = float(pd.Series([len(s) for s in dna]).median())
    p.termlabel_frac = round(sum(bool(TERMLABEL_RE.match(s)) for s in strs) / n, 3)
    p.geoloc_frac = round(sum(bool(GEOLOC_RE.match(s)) and not ISO_OFFSET_RE.match(s) and ':' in s[:40]
                              and not re.match(r'^\d', s) for s in strs) / n, 3)
    p.boolean_frac = round(sum(s.lower() in BOOL for s in strs) / n, 3)
    p.duration_frac = round(sum(bool(ISO_DUR_RE.match(s)) for s in strs) / n, 3)
    p.duration_human_frac = round(sum(bool(HUMAN_DUR_RE.match(s)) for s in strs) / n, 3)
    # Excel time cells (read as datetime.time) or text such as 10:00 or 4 pm
    p.time_frac = round(sum(isinstance(v, dt.time) or bool(TIME_OF_DAY_RE.match(s)) for v, s in zip(vals, strs)) / n, 3)
    files = [s for s in strs if FILE_RE.search(s)]
    p.filename_frac = round(len(files) / n, 3)
    if files:
        r1 = sum(bool(re.search(r'(_R?1[._]|_1\.f)', f)) for f in files)
        r2 = sum(bool(re.search(r'(_R?2[._]|_2\.f)', f)) for f in files)
        p.read_pair = 'forward' if r1 > r2 else ('reverse' if r2 > r1 else '')
    quantities = [q for q in (parse_quantity(s) for s in strs) if q]
    p.quantity_frac = round(len(quantities) / n, 3)
    p.quantity_units = list(dict.fromkeys(u for _, u in quantities))[:5]
    p.country_frac = round(sum(insdc_country(s) is not None for s in p.distinct) / len(p.distinct), 3)
    p.latlon_frac = round(sum(parse_lat_lon(s) is not None for s in strs) / n, 3)
    m = HEADER_TIME_UNIT_RE.search(str(column))
    if m:
        p.header_time_unit = UNIT_ALIASES[m.group(1).lower()]
    return p


def profile_table(df):
    return [profile_column(c, df[c]) for c in df.columns]


# ------------------------------------------------------------------ scoring

class NameScorer:
    """Weighted token overlap between a header and each term's names (IDF weights)."""

    def __init__(self, terms):
        self.terms = terms
        df = {}
        for t in terms:
            seen = set(tok for a in t.aliases for tok in a)
            for tok in seen:
                df[tok] = df.get(tok, 0) + 1
        n = len(terms)
        self.idf = {tok: math.log(1 + n / c) for tok, c in df.items()}
        self.max_w = max(self.idf.values()) if self.idf else 1.0
        self.default_w = self.max_w * 0.6
        self.vocab = set(self.idf)

    def w(self, tok):
        return self.idf.get(tok, self.default_w)

    @staticmethod
    def agent_pair(a, b, endings=('r', 'or'), plurals=True):
        """A word and its agent noun (sample and sampler, samples and samplers, sequence and
        sequencer, collect and collector), which name different things. -er is left out by
        default, as abbreviations end the same way (prefilt and prefilter)."""
        if plurals:
            a, b = (x[:-1] if len(x) > 4 and x.endswith('s') else x for x in (a, b))
        short, long_ = sorted((a, b), key=len)
        return long_ != short and long_ in tuple(short + e for e in endings)

    @classmethod
    def same(cls, a, b):
        if a == b:
            return True
        if cls.agent_pair(a, b):
            return False
        # same stem: a shared start of at least 5 letters covering most of the shorter word
        n = 0
        for x, y in zip(a, b):
            if x != y:
                break
            n += 1
        if n >= 5 and n >= 0.8 * min(len(a), len(b)):
            return True
        return len(a) >= 5 and len(b) >= 5 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.88

    def overlap(self, h, a):
        used, inter = set(), 0.0
        for x in h:
            for j, y in enumerate(a):
                if j not in used and self.same(x, y):
                    used.add(j)
                    inter += (self.w(x) + self.w(y)) / 2
                    break
        wh = sum(self.w(x) for x in h)
        wa = sum(self.w(y) for y in a)
        return 2 * inter / (wh + wa) if wh + wa else 0.0

    @classmethod
    def stem_same(cls, a, b):
        """Same word or the same stem (filtered, filtering), without the looser spelling match, and not
        a word and its agent noun (sample, sampler)."""
        if a == b:
            return True
        if cls.agent_pair(a, b, ('r', 'er', 'or'), plurals=False):
            return False
        n = 0
        for x, y in zip(a, b):
            if x != y:
                break
            n += 1
        return n >= 5 and n >= 0.8 * min(len(a), len(b))

    def contained(self, tokens, term, head=()):
        """Support from a column description. Strong (0.9): the term's name or a common name of two or
        more words appears in it ('days frozen' in 'number of days the sample was frozen'). Strong
        (0.85): a one-word name is the description's head ('person' in 'the person that filtered the
        sample'). Weak (0.5): a one-word name appears elsewhere. Common words such as 'sample' do not
        count."""
        best, why = 0.0, ''
        for i, a in enumerate(term.aliases):
            specific = len(a) >= 2 or self.w(a[0]) >= 0.75 * self.max_w
            if not specific or not all(any(self.stem_same(x, y) for x in tokens) for y in a):
                continue
            if len(a) >= 2:
                s = 0.9
            else:
                s = 0.85 if any(self.stem_same(x, a[0]) for x in head) else 0.5
            if s > best:
                best, why = s, ('term name' if i == 0 else 'common name') + f" '{' '.join(a)}'"
        return best, why

    def score(self, header_tokens, term):
        if not header_tokens:
            return 0.0, ''
        best, why = 0.0, ''
        for i, a in enumerate(term.aliases):
            s = 1.0 if header_tokens == a else self.overlap(header_tokens, a)
            # every word of the name appears in the header, with a few extra words
            specific = len(a) >= 2 or self.w(a[0]) >= 0.75 * self.max_w
            if s < 1.0 and specific and len(header_tokens) - len(a) <= 4 and all(any(self.same(x, y) for x in header_tokens) for y in a):
                s = max(s, 0.72 + 0.28 * s)
            if s > best:
                best, why = s, ('term name' if i == 0 else 'common name') + f" '{' '.join(a)}'"
        return best, why


def _vocab_match(distinct, vocab):
    """Fraction of distinct values that match an allowed value."""
    if not distinct or not vocab:
        return 0.0
    opts = [re.sub(r'[^a-z0-9]+', ' ', o.lower()).strip() for o in vocab]
    hits = 0
    for v in distinct[:40]:
        s = re.sub(r'[^a-z0-9]+', ' ', str(v).lower()).strip()
        if not s:
            continue
        if s in opts or any(len(s) >= 3 and (re.search(rf'\b{re.escape(s)}\b', o) or re.search(rf'\b{re.escape(o)}\b', s)) for o in opts if o):
            hits += 1
        elif difflib.get_close_matches(s, opts, n=1, cutoff=0.85):
            hits += 1
    return hits / min(len(distinct), 40)


# How specific a value fingerprint is: a matching latitude range says much more than "numeric".
SPECIFIC = {'latitude': 0.9, 'longitude': 0.9, 'primer': 0.9, 'index_seq': 0.8, 'filename': 0.9,
            'termlabel': 0.8, 'geoloc': 0.8, 'date': 0.7, 'duration': 0.6, 'boolean': 0.5,
            'identifier': 0.5, 'vocab': 0.9, 'number': 0.3, 'integer': 0.35, 'number_or_vocab': 0.4,
            'text': 0.2}


AMPLICON_REGION_RE = re.compile(r'^(V\d+(\s*[-–]\s*V?\d+)?|ITS\s?\d?|D\d+(\s*[-–]\s*D?\d+)?|[A-Z]{1,3}\d{1,3})$', re.I)


def value_fit(p: ColumnProfile, t: Term):
    """(fit 0..1, evidence text). fit 0 with evidence starting 'conflict' means the values rule the term out."""
    if p.n_values == 0:
        return 0.3, 'no values'
    if t.name == 'target_subfragment':
        # Amplicon regions (V4, V3-V4, ITS2, D1-D2), not place names that share the word "region".
        hits = sum(bool(AMPLICON_REGION_RE.match(str(v).strip())) for v in p.distinct)
        if hits >= 0.8 * len(p.distinct):
            return 1.0, 'amplicon region names (V4, ITS2 ...)'
        if p.numeric_frac < 0.5:
            return 0.0, 'conflict: values are not amplicon region names (V4, ITS2 ...)'
    k = t.kind
    num, dna = p.numeric_frac, p.dna_frac
    if k in ('latitude', 'longitude') and p.latlon_frac >= 0.8:
        ex = p.examples[0] if p.examples else ''
        return (1.0 if k == 'latitude' else 0.95), (f'latitude and longitude in each cell ({ex}): split into '
                                                    f'decimalLatitude and decimalLongitude')
    if k == 'latitude':
        if num >= 0.9 and -90 <= p.min and p.max <= 90 and (p.decimals_median or 0) >= 2:
            return 1.0, f'values are decimal degrees within latitude range ({p.min:g} to {p.max:g})'
        return (0.0, 'conflict: values are not latitudes') if p.n_values >= 2 else (0.2, '')
    if k == 'longitude':
        if num >= 0.9 and -180 <= p.min and p.max <= 180 and (p.decimals_median or 0) >= 2:
            fit = 1.0 if (abs(p.min) > 90 or abs(p.max) > 90) else 0.8
            return fit, f'values are decimal degrees within longitude range ({p.min:g} to {p.max:g})'
        return (0.0, 'conflict: values are not longitudes') if p.n_values >= 2 else (0.2, '')
    if k == 'primer':
        if dna >= 0.8 and 14 <= (p.dna_length_median or 0) <= 45:
            return 1.0, f'DNA sequences of primer length (~{p.dna_length_median:g} nt)'
        return 0.0, 'conflict: not primer sequences'
    if k == 'index_seq':
        if dna >= 0.8 and 5 <= (p.dna_length_median or 0) <= 14:
            return 1.0, f'short DNA sequences typical of index tags (~{p.dna_length_median:g} nt)'
        return 0.0, 'conflict: not index sequences'
    if k == 'filename':
        if p.filename_frac >= 0.8:
            pair_ok = (t.name == 'filename' and p.read_pair != 'reverse') or (t.name == 'filename2' and p.read_pair != 'forward')
            return (1.0, f'sequence file names ({p.read_pair or "read"} reads)') if pair_ok else (0.3, 'sequence files of the other read')
        return 0.0, 'conflict: not sequence file names'
    if t.name == 'verbatimEventTime' and p.time_frac >= 0.8:
        return 1.0, f"times of day ({', '.join(time_text(v) for v in p.distinct[:3])})"
    if p.time_frac >= 0.8 and k in ('duration', 'date', 'number', 'integer', 'number_or_vocab'):
        return 0.0, 'conflict: values are times of day'
    if dna >= 0.8:
        return 0.0, 'conflict: values are DNA sequences'
    if p.filename_frac >= 0.8:
        return 0.0, 'conflict: values are sequence file names'
    if k == 'termlabel':
        if p.termlabel_frac >= 0.7:
            return 1.0, 'values are in "label [ID]" form (e.g. ENVO terms)'
        if num >= 0.8 or p.date_frac >= 0.8:
            return 0.0, 'conflict: values are numbers or dates'
        return 0.45, 'text values (FAIRe needs "label [ENVO:id]" form)'
    if k == 'date':
        if p.date_frac >= 0.8:
            return 1.0, f'dates ({p.date_format})'
        if p.serial_date_frac >= 0.9:
            first = dt.date(1899, 12, 30) + dt.timedelta(days=int(p.min))
            return 0.7, f'numbers that may be Excel serial dates ({p.min:g} is {first.isoformat()})'
        return (0.0, 'conflict: values are not dates') if p.n_values >= 2 else (0.2, '')
    if k == 'duration':
        if p.duration_frac >= 0.8:
            return 1.0, 'ISO 8601 durations'
        if p.duration_human_frac >= 0.8:
            return 0.8, 'durations written in words (FAIRe needs ISO 8601, e.g. P2D)'
        if num >= 0.9 and p.header_time_unit in ISO_DURATION_UNITS:
            return 0.8, f'numbers with the time unit in the header ({p.header_time_unit}); FAIRe needs ISO 8601, e.g. P2D'
        return 0.15, ''
    if k == 'geoloc':
        if p.geoloc_frac >= 0.6:
            return 1.0, 'values look like "Country: region, locality"'
        if p.country_frac >= 0.9:
            return 1.0, 'country or sea names, the first part of "Country: region, locality"'
        if num >= 0.8 or p.date_frac >= 0.8:
            return 0.0, 'conflict: values are numbers or dates'
        return 0.4, 'text values'
    if k == 'boolean':
        if p.boolean_frac >= 0.9:
            return 1.0, 'yes/no or 0/1 values'
        return 0.1, ''
    if k == 'identifier':
        if p.date_frac >= 0.8 or (num >= 0.9 and p.integer_frac < 0.9):
            return 0.0, 'conflict: values are dates or measurements'
        if p.unique_per_row:
            return 1.0, 'a different value on every row'
        return 0.3, 'values repeat'
    if k in ('number', 'integer'):
        if p.date_frac >= 0.8:
            return 0.0, 'conflict: values are dates'
        if num >= 0.9:
            if k == 'integer' and p.integer_frac < 0.95:
                return 0.6, 'numbers, not all whole'
            return 1.0, f'numbers ({p.min:g} to {p.max:g})'
        if p.quantity_frac >= 0.8 and p.duration_human_frac < 0.8:
            return quantity_fit(p, t)
        if num >= 0.5:
            return 0.6, 'mostly numbers'
        return (0.0, 'conflict: values are not numbers') if p.n_values >= 3 else (0.2, '')
    if k == 'number_or_vocab':
        if num >= 0.9:
            return 1.0, 'numbers'
        if p.quantity_frac >= 0.9:
            return quantity_fit(p, t)
        m = _vocab_match(p.distinct, t.vocab)
        return (0.9, 'allowed values') if m >= 0.6 else (0.3, '')
    if k == 'vocab' and t.name.endswith('_unit') and p.quantity_frac >= 0.8:
        # "1 L" holds the unit, but mainly the amount: the amount's term fills this one too.
        return 0.4, 'values hold a number and its unit; the unit part fits'
    if k == 'vocab':
        m = _vocab_match(p.distinct, t.vocab)
        if m >= 0.8:
            return 1.0, f'values match the allowed values ({m:.0%} of distinct values)'
        if m >= 0.4:
            return 0.7, f'some values match the allowed values ({m:.0%})'
        if num >= 0.9 or p.date_frac >= 0.8:
            return 0.0, 'conflict: values are numbers or dates, which are not allowed values'
        return 0.25, 'values do not match the allowed values'
    # free text
    if num >= 0.9 or p.date_frac >= 0.8:
        return 0.25, 'numbers or dates in a text field'
    return 0.5, ''


def time_text(v):
    """A time of day as hh:mm (10:00:00 and an Excel time cell of 10:00 both as 10:00), or the text as
    written when it is in another form (4 pm)."""
    if isinstance(v, (dt.time, dt.datetime)):
        return v.strftime('%H:%M') + (v.strftime(':%S') if v.second else '')
    s = str(v).strip()
    m = re.match(r'^(\d{1,2}):(\d{2})(?::(\d{2}))?$', s)
    if m:
        return f'{int(m.group(1)):02d}:{m.group(2)}' + (f':{m.group(3)}' if m.group(3) and m.group(3) != '00' else '')
    return s


def quantity_fit(p, t):
    """Fit of 'number unit' values ("1 L", "0.2 micron") to a numeric term."""
    units = ', '.join(p.quantity_units)
    want = fixed_unit(t)
    if t.unit_term:
        return 0.9, f'a number and its unit in each cell ({units}): split into {t.name} and {t.unit_term}'
    if want:
        if all(u == want for u in p.quantity_units):
            return 0.9, f'a number and its unit in each cell ({units}, as the term needs)'
        if all((u, want) in UNIT_FACTORS for u in p.quantity_units):
            return 0.7, f'a number and its unit in each cell ({units}); convert to {want}'
        return 0.3, f'a number and its unit in each cell ({units}), but the term is in {want}'
    return 0.7, f'a number and its unit in each cell ({units})'


def level_factor(p, t):
    if p.constant and t.level == 'project':
        return 1.1, 'one value for the whole table, suits a project or assay-level term'
    if not p.constant and t.level == 'project' and p.n_unique > 3:
        return 0.8, 'varies between rows, but the term is project or assay level'
    return 1.0, ''


@dataclass
class Candidate:
    term: str
    score: float
    name_score: float
    value_score: float
    evidence: str
    name_why: str = ''      # the parts of the evidence, for the comment a reviewer reads
    value_why: str = ''
    level_why: str = ''
    from_desc: bool = False


HEAD_ENDS = re.compile(r"\s(?:that|which|who|whom|whose|where|when|of|for|used|from|in|at|on|to|by|with|based|"
                       r"was|were|is|are|as|per|during|after|before)\s|[,;:(]")


def description_head(text):
    """The words a description opens with, up to its first linking word: 'the person' in 'the person
    that filtered the sample', 'mesh size' in 'mesh size of the filter'."""
    head = HEAD_ENDS.split(' ' + str(text).strip().lower() + ' ', maxsplit=1)[0]
    return tokens_of(head, keep_units=True)[:4]


def score_column(p, terms, scorer, header_tokens, desc_tokens=None):
    """Candidates for one column. A description from a data dictionary counts like a header: a term
    it names gets that support, and when it names other terms but not the header's, the header
    match counts for less (Sample processing described as 'the person that filtered the sample')."""
    out = []
    support = {}
    if desc_tokens:
        tokens, head = desc_tokens
        support = {t.name: scorer.contained(tokens, t, head) for t in terms}
    points_elsewhere = any(s >= 0.8 for s, _ in support.values())
    for t in terms:
        ns, nwhy = scorer.score(header_tokens, t)
        ds, dwhy = support.get(t.name, (0.0, ''))
        if support and points_elsewhere and ds == 0 and ns >= 0.3:
            ns *= 0.7
            nwhy += ', but the description names other terms'
        from_desc = ds > ns
        if from_desc:
            ns, nwhy = ds, dwhy
        elif ds:
            nwhy += f'; the description has the {dwhy}'
        vf, vwhy = value_fit(p, t)
        lf, lwhy = level_factor(p, t)
        spec = SPECIFIC.get(t.kind, 0.3)
        value_part = vf * spec
        if ns >= 0.95:
            score = 0.75 + 0.25 * vf
        else:
            score = 0.62 * ns + 0.38 * value_part
        if vwhy.startswith('conflict'):
            # An exact header match is kept, but flagged; otherwise the values rule the term out.
            if ns >= 0.95:
                score *= 0.85
                vwhy = vwhy.replace('conflict:', 'check values:')
            else:
                score *= 0.25
        score *= lf
        if vf >= 1.0 and spec >= 0.7 and not vwhy.startswith(('conflict', 'check')):
            score = max(score, 0.42 + 0.1 * ns)
        if t.mandatory:
            score += 0.01
        score = max(0.0, min(1.0, score))
        name_bit = '' if ns < 0.3 else (f'description has the {nwhy} ({ns:.2f})' if from_desc
                                        else f'header matches {nwhy} ({ns:.2f})')
        bits = [b for b in (name_bit, vwhy, lwhy) if b]
        out.append(Candidate(t.name, round(score, 3), round(ns, 3), round(vf, 3), '; '.join(bits),
                             nwhy if ns >= 0.3 else '', vwhy, lwhy, from_desc))
    out.sort(key=lambda c: c.score, reverse=True)
    return out


# ------------------------------------------------------------------ mapping

ACCEPT, REVIEW = 0.65, 0.40
# The shortlist grows (to k_close) when its last candidate scores within CLOSE of the first, so no term
# clearly leads. On the tables with answer keys (November 2026), 5 candidates held the right term for
# 152 of 227 review columns and 10 for 166; this rule held it for 162, with 37 lists longer than 5.
CLOSE = 0.10
LATLON_TERMS = ('decimalLatitude', 'decimalLongitude')
DEPTH_TERMS = ('minimumDepthInMeters', 'maximumDepthInMeters')
# Words that say a depth column holds one end of a range.
DEPTH_END_RE = re.compile(r'\b(min|minimum|max|maximum|lower|upper|shallow\w*|deepest|start|end|from|to)\b', re.I)
# A yes/no column matched to one of these project-level terms marks the controls, sample by sample.
CONTROL_FLAGS = {'neg_cont_0_1': 'negative control', 'pos_cont_0_1': 'positive control'}
# Terms whose value may be built from several columns, in order. geo_loc_name is
# "Country: region, locality", often held in a country, a region and a locality column.
COMBINABLE = ('geo_loc_name',)
BROAD_PLACE_WORDS = {'country', 'state', 'province', 'territory', 'region', 'subregion', 'bioregion', 'reef',
                     'island', 'catchment', 'basin', 'park', 'ocean', 'sea', 'coast', 'district', 'county'}


@dataclass
class Proposal:
    column: str
    term: str
    sheet: str
    score: float
    route: str
    evidence: str
    hint: str
    candidates: list
    part: int = 0          # order of this column among the columns that build one value (COMBINABLE)
    unit_term: str = ''    # a unit term filled from the same cells ("1 L" fills samp_size and samp_size_unit)
    value_part: str = ''   # which part of each cell the term takes: number, latitude, or a conversion
    also: list = field(default_factory=list)   # other (term, value_part, note) filled from the same column
    comment: str = ''      # what a reviewer reads in the crosswalk (reader_comment)
    other: object = None   # for a column with no FAIRe term: a MIxS or Darwin Core Term, for review
    other_score: float = 0.0
    other_comment: str = ''
    fallback: object = None  # for a FAIRe match for review: a MIxS or Darwin Core term, offered in the review sheet

    def also_terms(self):
        return [a[0] for a in self.also]


def unit_hint(p, t, by_name):
    hints = []
    unit_term = by_name.get(f'{t.name}_unit')
    if p.header_units and unit_term and p.quantity_frac < 0.8:
        hints.append(f"set {unit_term.name} = {p.header_units[0]} (unit in header)")
    if t.kind == 'date' and p.date_format and p.date_format not in ('yyyy-mm-dd', 'ISO date-time', 'ISO date-time with offset'):
        hints.append(f"convert dates from {p.date_format} to ISO 8601 (yyyy-mm-dd)")
    elif t.kind == 'date' and not p.date_format and p.serial_date_frac >= 0.9:
        hints.append('convert Excel serial numbers to ISO 8601 dates (days since 1899-12-30)')
    if t.kind == 'termlabel' and p.termlabel_frac < 0.7:
        hints.append('add ENVO labels and IDs, e.g. "sea water [ENVO:00002149]"')
    if t.kind == 'duration' and p.duration_human_frac >= 0.8:
        hints.append('convert durations to ISO 8601, e.g. "2 days" to P2D')
    elif t.kind == 'duration' and p.numeric_frac >= 0.9 and p.header_time_unit in ISO_DURATION_UNITS:
        ex = p.examples[0] if p.examples else '2'
        word = {'d': 'days', 'h': 'hours', 'min': 'minutes', 'wk': 'weeks', 'mo': 'months', 'yr': 'years'}
        hints.append(f'write numbers in {word.get(p.header_time_unit, p.header_time_unit)} as ISO 8601 durations, '
                     f'e.g. {ex} as '
                     f'{iso_duration(ex, p.header_time_unit) if re.match(r"^[0-9.]+$", ex) else "P2D"}')
    if t.kind in ('number', 'integer', 'number_or_vocab') and p.quantity_frac >= 0.8 and not t.unit_term:
        want = fixed_unit(t)
        if want and any(u != want for u in p.quantity_units):
            hints.append(f"convert from {', '.join(p.quantity_units)} to {want} and keep the number only")
        else:
            hints.append('keep the number only' + (f' (in {want})' if want else ''))
    if p.constant and t.level == 'project':
        hints.append(f"project-level value: {p.examples[0] if p.examples else ''}")
    return '; '.join(hints)


def unit_base(column, columns):
    """If this column holds the units of another column, return that column."""
    toks = tokens_of(column)
    if 'unit' not in toks:
        return None
    rest = [t for t in toks if t != 'unit']
    if not rest:
        return None
    best, best_ov = None, 0.0
    for other in columns:
        if other == column:
            continue
        ot = tokens_of(other)
        if not ot or 'unit' in ot:
            continue
        ov = len(set(rest) & set(ot)) / len(set(rest) | set(ot))
        if ov > best_ov:
            best, best_ov = other, ov
    return best if best_ov >= 0.6 else None


def shortlist_length(cands, k, k_close):
    """k candidates, or k_close when the k-th scores within CLOSE of the first."""
    if k_close and k_close > k and len(cands) > k and cands[0].score - cands[k - 1].score < CLOSE:
        return k_close
    return k


# ------------------------------------------------------------------ comments for the reviewer
# Each crosswalk row explains itself in the same order: the FAIRe term and what it means, why the
# mapper chose it, what the apply mapping tool will do with the values, and (for rows to review)
# what the reviewer should check. Plain sentences with the reviewer's own values; scores stay in
# the confidence column.

BOOL_YES, BOOL_NO = {'1', 'yes', 'y', 'true', 't', '1.0'}, {'0', 'no', 'n', 'false', 'f', '0.0'}
# Hints the reviewer has to act on; the apply mapping tool carries out the others itself.
PERSON_HINTS = ('add ENVO', 'set ', 'project-level value')


def strength(score):
    return 'strong' if score >= 0.9 else ('moderate' if score >= ACCEPT else 'weak')


def _sentence(text):
    text = str(text).strip()
    if not text:
        return ''
    text = text[0].upper() + text[1:]
    return text if text[-1] in '.?!' else text + '.'


def term_gloss(t):
    """The first sentence of the checklist's description, and the allowed values when there are few."""
    d = re.sub(r'\s+', ' ', t.description).strip()
    m = re.match(r'(.+?[.?!])(?:\s|$)', d)
    d = m.group(1) if m else d
    if len(d) > 200:
        d = d[:197].rsplit(' ', 1)[0] + '...'
    vocab = [v.strip() for v in t.vocab if str(v).strip()]
    if vocab and len(vocab) <= 8 and not any(v.startswith('http') for v in vocab):
        shown = ['other (describe it)' if v == 'other:' else v for v in vocab]
        d = _sentence(d) + ' Allowed values: ' + ', '.join(shown)
    return _sentence(d)


def name_phrase(c):
    """Why the column name points to the term, in words."""
    if not c.name_why:
        return ''
    first = re.split(r'[;,] ', c.name_why)[0]
    label = first.split("'")[1] if "'" in first else ''
    what = (f"the FAIRe term's own name ('{label}')" if first.startswith('term name')
            else f"'{label}', another name for this FAIRe term")
    if c.from_desc:
        text = f"the column's description mentions {what}"
    elif c.name_score >= 0.95:
        text = f'the column name matches {what}'
    else:
        text = f'the column name partly matches {what}'
    if 'description names other terms' in c.name_why:
        text += ", although the column's description points to other FAIRe terms"
    return text


def _examples(p, n=3):
    ex = [e if len(e) <= 28 else e[:25] + '...' for e in p.examples[:n]]
    return ', '.join(ex)


def _value_problem(why):
    for prefix in ('conflict: ', 'check values: '):
        if why.startswith(prefix):
            return why[len(prefix):]
    return ''


CONFUSED_TERMS = Path(__file__).with_name('commonly_confused_terms.tsv')


def load_confused(path=CONFUSED_TERMS):
    """FAIRe terms that people often confuse (commonly_confused_terms.tsv): {term: (group, side, meaning)},
    where a side is the terms of one row, which go together (minimumDepthInMeters, maximumDepthInMeters),
    and {group: the question that tells its sides apart}."""
    terms, checks = {}, {}
    if not path or not Path(path).exists():
        return terms, checks
    table = pd.read_csv(path, sep='\t', comment='#', dtype=str, keep_default_na=False)
    for r in table.to_dict('records'):
        group = r.get('group', '').strip()
        side = tuple(t.strip() for t in r.get('term', '').split(',') if t.strip())
        for term in side if group else ():
            terms[term] = (group, side, r.get('meaning', '').strip())
        if group and side and r.get('check', '').strip() and group not in checks:
            checks[group] = r['check'].strip()
    return terms, checks


def confused_note(names, confused):
    """'Often confused with Z (its meaning). <the group's question>' for terms of one group, or ''."""
    terms, checks = confused
    names = [n for n in names if n in terms]
    if not names:
        return ''
    group = terms[names[0]][0]
    mine = {terms[n][1] for n in names}
    others = list(dict.fromkeys(side for g, side, _ in terms.values() if g == group and side not in mine))
    if not others:
        return ''
    meaning = {side: m for g, side, m in terms.values()}
    said = ' and '.join(f"{' and '.join(s)} ({meaning[s]})" if meaning[s] else ' and '.join(s) for s in others)
    return f"Often confused with {said}. {checks.get(group, '')}".strip()


def reader_comment(pr, p, c, t, ctx):
    """The comment a reviewer reads for one crosswalk row (see the block comment above)."""
    review = pr.route == 'review'
    why, happens, check = [], [], []
    if pr.route == 'confirmed':
        why.append('set by a reviewer')
    elif pr.route == 'model':
        why.append(pr.evidence)
        check.append('a language model chose this FAIRe term. Confirm it, change it, or delete this row')
    elif pr.column in ctx['flags']:
        was, kind, yes, no, n_yes, n_no, example = ctx['flags'][pr.column]
        why.append(f"{strength(pr.score)} match. The column holds {' and '.join(yes + no)}, and its name is "
                   f"close to {was}. That FAIRe term is one yes/no for the whole project, but these values "
                   f"change from row to row, so the mapper reads them as marking which rows are controls")
        happens.append(f"{'/'.join(yes)} ({n_yes} rows) becomes '{kind}' and {'/'.join(no)} ({n_no} rows) "
                       f"becomes 'sample'" + (f' (for example, {example} becomes {kind})' if example else ''))
        ctype = 'neg_cont_type' if kind.startswith('neg') else 'pos_cont_type'
        eg = ctx['control_example'].get(ctype, '')
        check.append(f"are all the {'/'.join(yes)} rows {kind}s? If so, confirm this row, then give each control a "
                     f"{ctype}" + (f" (for example '{eg}')" if eg else ''))
    else:
        if pr.column in ctx['unit_notes']:
            why.append(f"this column holds the {ctx['unit_notes'][pr.column]}")
        elif c is not None:
            bits = [f'{strength(pr.score)} match', name_phrase(c)]
            vwhy = re.split(r': split into ', c.value_why)[0]
            problem = _value_problem(vwhy)
            if p.n_values and not problem and vwhy and vwhy != 'no values':
                bits.append(vwhy)
                if '(' not in vwhy and p.examples:
                    bits.append(f'for example: {_examples(p)}')
            elif p.n_values and p.examples:
                bits.append(f'values include {_examples(p)}')
            why.append(' '.join(_sentence(b) for b in bits if b))
            problems = []
            if problem:
                problems.append(f'the values may not suit this FAIRe term ({problem})')
            level = c.level_why if 'varies between rows' in c.level_why else ctx['level_notes'].get(pr.column, '')
            if level:
                problems.append(f'this FAIRe term holds one value for the whole project or assay, but the column '
                                f'has {p.n_unique} different values')
            if problems:
                check.extend(problems)
                check.append('delete this row unless you are sure the column holds what the FAIRe term describes')
            if not p.n_values:
                check.append('the column is empty in your table. Delete this row, or fill the column and '
                             'propose the mapping again')
        if pr.column in ctx['clashes']:
            check.append(f"another column, '{ctx['clashes'][pr.column]}', was given the same FAIRe term and matches "
                         f"it better. Keep one of them")
        if pr.part:
            note = ctx['part_notes'].get(pr.column, '')
            happens.append(f"this column is part {pr.part} of {pr.term}, joined with "
                           + note.split(', with ', 1)[1].split(';')[0] + ' (country or sea name first, then '
                           'broader places before narrower ones)' if ', with ' in note else '')
            if 'is a guess' in note:
                check.append('the order of the parts is a guess, as some columns have the same number of '
                             'different values. Check the combine_order numbers')
            elif review:
                check.append(f'the columns that build {pr.term} are applied together. Confirm or delete them '
                             f'together')
        for h in [x.strip() for x in pr.hint.split(';') if x.strip()]:
            if h.startswith(PERSON_HINTS):
                check.append(h)
            else:
                happens.append(f'the tool will {h}')
        if pr.term == 'verbatimEventTime' and p.time_frac >= 0.8:
            happens.append('apply mapping joins these times to the dates in eventDate, adding the UTC offset if '
                           'you give one on its form (10:00 on 2021-11-01, with +11:00, becomes '
                           '2021-11-01T10:00+11:00)')
        if pr.value_part == 'latitude' and p.examples:
            ll = parse_lat_lon(p.examples[0])
            if ll:
                happens.append(f'for example, {p.examples[0]} becomes {ll[0]} and {ll[1]}')
    note = confused_note([pr.term] + pr.also_terms(), ctx.get('confused', ({}, {})))
    if note:
        check.insert(0, note)
    if review and not check:
        rival = next((x for x in ctx['rivals'].get(pr.column, []) if x != pr.term), '')
        check.append('confirm this row if the column holds what the FAIRe term describes. Otherwise change the '
                     'FAIRe term' + (f' (another possible one is {rival})' if rival else '') + ' or delete the row')
    parts = [f'FAIRe term: {pr.term}. {term_gloss(t)}' if t else f'FAIRe term: {pr.term}.']
    if why:
        parts.append('Why: ' + ' '.join(_sentence(w) for w in why if w))
    if happens:
        parts.append('What happens: ' + ' '.join(_sentence(h) for h in happens if h))
    if check:
        parts.append('Check: ' + ' '.join(_sentence(x) for x in check if x)
                     + (' To confirm, change skos:closeMatch to skos:exactMatch.' if review and p.n_values else ''))
    return ' '.join(parts)


# A MIxS or Darwin Core term needs at least this name match: on its own, a column of numbers fits hundreds.
OTHER_NAME_MIN = 0.75


HEADER_UNIT_RE = re.compile(r'[(\[]\s*([^()\[\]]{1,20}?)\s*[)\]]\s*$')


def header_unit_text(column):
    """The unit a column name gives in brackets at its end, as written: 'uM' for 'Phosphate (uM)'."""
    m = HEADER_UNIT_RE.search(str(column))
    return m.group(1) if m else ''


def with_header_unit(t, column):
    """The unit to add to each value when a column is named after a MIxS term: MIxS writes a number and its
    unit together (0.7 micromole per liter), so the unit in the column name, which the new name drops, goes
    into the values. '' when the term is not a MIxS number or the name gives no unit."""
    return header_unit_text(column) if t is not None and t.source == 'MIxS' and t.kind == 'number' else ''


def other_name_fit(scorer, header, t):
    """How well a header and a MIxS or Darwin Core term's names match, both ways. Every word of the header
    must match a word of the name, or be a common word (Sample year fits year, but Field bottle number
    does not fit fieldNumber, nor Field sheet page field)."""
    best = 0.0
    for a in t.aliases:
        if header != a and any(not any(scorer.same(x, y) for y in a) and scorer.w(x) >= 0.55 * scorer.max_w
                               for x in header):
            continue
        best = max(best, 1.0 if header == a else scorer.overlap(header, a))
    return best


# The MIxS extensions named first in a comment, as eDNA samples mostly come from them.
MIXS_FIRST = ['water', 'sediment', 'soil', 'air', 'host-associated', 'microbial mat/biofilm', 'plant-associated']


def other_comment(pr, p, c, t, rivals=()):
    """The comment a reviewer reads for a MIxS or Darwin Core term proposed for a column with no FAIRe term."""
    gloss = term_gloss(t)
    if t.unit:
        units = [u.strip() for u in t.unit.split(',') if u.strip()]
        said = units[0] if len(units) == 1 else ', '.join(units[:-1]) + ' or ' + units[-1]
        gloss += f" {t.source} gives it in {said}."
    scope = t.scope.split(': ', 1)
    if t.source == 'MIxS' and len(scope) == 2:
        names = sorted((x.strip() for x in scope[1].split(',')),
                       key=lambda x: (MIXS_FIRST.index(x) if x in MIXS_FIRST else len(MIXS_FIRST), x))
        kind = scope[0] if len(names) > 1 else scope[0].rstrip('s')
        shown = names[:3] + [f'{len(names) - 3} more'] if len(names) > 4 else names
        gloss += f" MIxS has it in its {shown[0] if len(shown) == 1 else ', '.join(shown[:-1]) + ' and ' + shown[-1]} {kind}."
    first = re.split(r'[;,] ', c.name_why)[0]
    label = first.split("'")[1] if "'" in first else t.name
    own = f"the {t.source} term's own name" if first.startswith('term name') else f"the {t.source} label"
    exact = tokens_of(pr.column) in t.aliases
    how = ("the column's description mentions" if c.from_desc else
           'the column name matches' if exact else
           'the column name is close to' if c.name_score >= 0.95 else 'the column name partly matches')
    why = [f'{strength(c.score)} match', f"no FAIRe term fits this column, and {how} {own} ('{label}')"]
    vwhy = c.value_why
    if vwhy and vwhy != 'no values' and not vwhy.startswith('numbers or dates in a text field'):
        why.append(vwhy)
    elif p.examples:
        why.append(f'values include {_examples(p)}')
    if header_unit_text(pr.column):
        why.append(f"the column's unit, from its name: {header_unit_text(pr.column)}")
    check = [f"does the column hold what the {t.source} term describes? Confirm this row to name the column "
             f"{t.name}, or delete the row to keep your own name ({pr.column})"]
    unit = with_header_unit(t, pr.column)
    happens = (f"if you confirm it, apply mapping keeps the column as a user-defined field named {t.name}, as the "
               f"FAIRe guidelines suggest for columns with no FAIRe term")
    if unit:
        ex = p.examples[0] if p.examples else '1'
        happens += f", and adds the unit from the column name to each value, as MIxS writes them ({ex} {unit})"
    elif t.unit and t.kind == 'number':
        check.append('the values are written as they are, and the column name gives no unit, so check their unit')
    if rivals:
        check.append('another possible term is ' + ' or '.join(f'{r.source} {r.name}' for r in rivals))
    return ' '.join([
        f'{t.source} term: {t.name} ({t.term_id}). {gloss}',
        'Why: ' + ' '.join(_sentence(w) for w in why),
        f'What happens: {_sentence(happens)}',
        'Check: ' + ' '.join(_sentence(x) for x in check) + ' To confirm, change skos:closeMatch to skos:exactMatch.'])


def also_comment(pr, term, note, t):
    return (f'FAIRe term: {term}. {term_gloss(t) if t else ""} Why: Same column as the {pr.term} row above. '
            f'What happens: {_sentence(note)}'
            + (' Check: confirm or delete it together with that row.' if pr.route == 'review' else ''))


def propose(df, terms, k=5, overrides=None, answered_by=None, descriptions=None, k_close=10, confused=None,
            other_terms=None):
    by_name = {t.name: t for t in terms}
    scorer = NameScorer(terms)
    profiles = profile_table(df)
    columns = [p.column for p in profiles]
    bases = {c: unit_base(c, columns) for c in columns}
    descriptions = descriptions or {}
    scored, desc_map = {}, {}
    for p in profiles:
        d = descriptions.get(p.column)
        desc_tokens = None
        if d:
            desc_tokens = (tokens_of(d['description'], keep_units=True), description_head(d['description']))
            u = d.get('units')
            if u and u not in p.header_units:
                p.header_units.append(u)
            if u in ISO_DURATION_UNITS and not p.header_time_unit:
                p.header_time_unit = u
        desc_map[p.column] = desc_tokens
        scored[p.column] = score_column(p, terms, scorer, tokens_of(p.column), desc_tokens)
    # Apply answers from a reviewer or model first: they fix those columns.
    overrides = overrides or {}
    assigned_col, assigned_term, clashes = {}, {}, {}

    def score_for(col, term):
        return next((c.score for c in scored[col] if c.term == term), 0.0)
    # When answers give one term to several columns, the column that matches it best keeps it;
    # the others go back for review.
    for col, term in sorted(overrides.items(), key=lambda kv: -score_for(kv[0], kv[1]) if kv[1] in by_name else 0):
        if col not in scored or not (term is None or term in by_name):
            continue
        assigned_col[col] = term
        if term and term in assigned_term and term not in COMBINABLE:
            clashes[col] = assigned_term[term]
        elif term:
            assigned_term.setdefault(term, col)
    prof = {p.column: p for p in profiles}

    # Greedy one-to-one assignment, best scores first. Unit columns wait for the column they describe.
    def unit_ok(col, c):
        # A unit term needs a header that mentions units, or values that are allowed units.
        return not c.term.endswith('_unit') or 'unit' in tokens_of(col) or c.value_score >= 1.0
    pairs = sorted(((c.score, col, c.term) for col, cands in scored.items() for c in cands
                    if c.score >= REVIEW and not bases[col] and unit_ok(col, c)), reverse=True)
    # A column with latitude and longitude in each cell fills both terms. A depth column fills both
    # ends of the depth range, unless another column gives one end (Minimum depth, Max depth).
    split_cols, also = set(), {}

    def depth_end(c):
        return DEPTH_END_RE.search(re.sub(r'[_\W]+', ' ', _CAMEL.sub(' ', str(c))))
    depth_ends = any(depth_end(c) and 'depth' in tokens_of(c) for c in columns)
    for score, col, term in pairs:
        if col in assigned_col or term in assigned_term:
            continue
        if term in LATLON_TERMS and prof[col].latlon_frac >= 0.8:
            free = [t for t in LATLON_TERMS if t not in assigned_term]
            assigned_col[col] = free[0]
            for t in free:
                assigned_term[t] = col
            if len(free) == 2:
                also[col] = [('decimalLongitude', 'longitude', 'the longitude part of the same cells')]
            split_cols.add(col)
            continue
        assigned_col[col], assigned_term[term] = term, col
        if term in DEPTH_TERMS and not depth_ends and not depth_end(col):
            other = DEPTH_TERMS[1 - DEPTH_TERMS.index(term)]
            if other not in assigned_term:
                assigned_term[other] = col
                also[col] = [(other, '', f'one depth for each sample: it fills {term} and {other}')]
    # Columns whose best match is a combinable term held by another column join it (giving up
    # their second choice), unless that column holds the whole value ("Australia: Queensland").
    # A joining column needs an accept-level score, or country or sea names as values.
    for term in COMBINABLE:
        holder = assigned_term.get(term)
        if holder is None or prof[holder].geoloc_frac >= 0.6:
            continue
        for col in columns:
            if col == holder or col in overrides or assigned_col.get(col) == term or bases[col]:
                continue
            best = scored[col][0] if scored[col] else None
            if best is not None and best.term == term and (
                    best.score >= ACCEPT or (best.score >= REVIEW and prof[col].country_frac >= 0.9)):
                old = assigned_col.get(col)
                if old and assigned_term.get(old) == col:
                    del assigned_term[old]
                assigned_col[col] = term
    # Order the columns that build one value: a country or sea name first, then broad to narrow
    # (fewer distinct values first), then table order. A column that already holds the whole value
    # ("Australia: Queensland") keeps the term alone.
    parts, part_notes, tied_groups = {}, {}, set()
    for term in COMBINABLE:
        cols = [c for c in columns if assigned_col.get(c) == term]
        if len(cols) < 2:
            continue
        whole = [c for c in cols if prof[c].geoloc_frac >= 0.6]
        if whole:
            keep = max(whole, key=lambda c: score_for(c, term))
            for c in cols:
                if c != keep and c not in overrides:
                    del assigned_col[c]
            assigned_term[term] = keep
            continue

        def broad(c):
            # On a tie, a header naming a broad area (reef, region, state) comes first.
            return -len(set(tokens_of(c)) & BROAD_PLACE_WORDS)
        cols.sort(key=lambda c: (0 if prof[c].country_frac >= 0.9 else 1, prof[c].n_unique, broad(c), columns.index(c)))
        assigned_term[term] = cols[0]
        rest = [c for c in cols if prof[c].country_frac < 0.9]
        ties = [(a, b) for a, b in zip(rest, rest[1:]) if prof[a].n_unique == prof[b].n_unique]
        for i, c in enumerate(cols, 1):
            parts[c] = i
            others = ', '.join(f"'{o}'" for o in cols if o != c)
            part_notes[c] = (f'part {i} of {len(cols)} of {term}, with {others}; order: country or sea name first, '
                             f'then fewer distinct values first')
            if ties:
                part_notes[c] += ('; the order of ' + ', '.join(f"'{a}' and '{b}'" for a, b in ties)
                                  + ' is a guess (same number of distinct values): check it')
        if ties:
            tied_groups.add(term)
    unit_notes = {}
    # A unit column whose header does not resemble any other header, e.g. "DIC units" next to
    # "Dissolved inorganic carbon": pair it through the names of the terms already assigned.
    for col in columns:
        if bases[col] or 'unit' not in tokens_of(col) or col in assigned_col:
            continue
        rest = [t for t in tokens_of(col) if t != 'unit']
        best, best_s = None, 0.0
        for term, tcol in assigned_term.items():
            if f'{term}_unit' in by_name and f'{term}_unit' not in assigned_term and rest:
                s_, _ = scorer.score(rest, by_name[term])
                if s_ > best_s:
                    best, best_s = tcol, s_
        if best and best_s >= 0.6:
            bases[col] = best
    for col, base in bases.items():
        if not base or col in assigned_col:
            continue
        base_term = assigned_col.get(base)
        unit_term = f'{base_term}_unit' if base_term else None
        if unit_term and unit_term in by_name and unit_term not in assigned_term:
            assigned_col[col], assigned_term[unit_term] = unit_term, col
            unit_notes[col] = f"units of column '{base}' ({base_term})"
            c = next((c for c in scored[col] if c.term == unit_term), None)
            if c is None or c.score < ACCEPT:
                # The pairing is the evidence; give it an accept-level score.
                scored[col] = [Candidate(unit_term, max(ACCEPT + 0.1, c.score if c else 0), 0, 0,
                                         unit_notes[col])] + [x for x in scored[col] if x.term != unit_term]
        else:
            unit_notes[col] = (f"units of column '{base}', which has no FAIRe term" if not base_term
                               else f"units of column '{base}' ({base_term}), which has no unit term")
    # A number and its unit in one cell ("1 L") fills the term and its unit term, unless another
    # column already holds the unit.
    unit_extra = {}
    for col, term in list(assigned_col.items()):
        t = by_name.get(term) if term else None
        if (t and t.unit_term and t.unit_term not in assigned_term and prof[col].quantity_frac >= 0.8
                and t.kind in ('number', 'integer', 'number_or_vocab')):
            unit_extra[col] = t.unit_term
            assigned_term[t.unit_term] = col
    # A yes/no column matched to neg_cont_0_1 or pos_cont_0_1 that varies between rows says which
    # samples are controls: it is samp_category (yes is the control, no is a sample).
    flags = {}
    for col, term in list(assigned_col.items()):
        p = prof[col]
        if (term in CONTROL_FLAGS and col not in overrides and 'samp_category' in by_name
                and 'samp_category' not in assigned_term and p.boolean_frac >= 0.9 and p.n_unique == 2):
            del assigned_term[term]
            assigned_col[col], assigned_term['samp_category'] = 'samp_category', col
            flags[col] = (term, score_for(col, term))
    proposals, level_notes = [], {}
    for p in profiles:
        cands = scored[p.column]
        term = assigned_col.get(p.column)
        shortlist = [f'{c.term} ({c.score:.2f})' for c in cands[:shortlist_length(cands, k, k_close)]]
        if p.column in overrides and p.column in assigned_col:
            # A model's answer is kept apart from a person's: only a person confirms.
            by = (answered_by or {}).get(p.column, '')
            from_model = by.lower().startswith('model')
            route = ('model' if from_model else 'confirmed') if term else 'no match'
            evidence = f'chosen by {by}, not yet checked by a person' if from_model else 'set by reviewer'
            if p.column in clashes:
                route = 'review'
                evidence = f"reviewer or model also chose {term} for column '{clashes[p.column]}', which matches it better"
            c = next((c for c in cands if c.term == term), None)
            proposals.append(Proposal(p.column, term or '', ';'.join(by_name[term].sheets) if term else '',
                                      c.score if c else 1.0, route, evidence,
                                      unit_hint(p, by_name[term], by_name) if term else '', shortlist))
            continue
        if not term:
            reason = unit_notes.get(p.column)
            taken = next((c for c in cands if c.score >= REVIEW and c.term in assigned_term), None)
            if not reason and taken is not None and cands and taken is cands[0]:
                reason = f"best term {taken.term} ({taken.score:.2f}) went to column '{assigned_term[taken.term]}'"
            reason = reason or ('no term scored high enough' if p.n_values else 'empty column')
            proposals.append(Proposal(p.column, '', '', cands[0].score if cands else 0.0, 'no match', reason, '', shortlist))
            continue
        if p.column in flags:
            was, s = flags[p.column]
            kind = CONTROL_FLAGS[was]
            evidence = (f'yes or no for each sample, under a header that matches {was} ({s:.2f}): yes is written '
                        f'as {kind} and no as sample. Fill {"neg" if kind.startswith("neg") else "pos"}_cont_type '
                        f'for the controls')
            proposals.append(Proposal(p.column, term, ';'.join(by_name[term].sheets), s,
                                      'accept' if s >= ACCEPT else 'review', evidence, '', shortlist,
                                      value_part=f'{kind} if yes'))
            continue
        c = next(c for c in cands if c.term == term)
        rivals = [x for x in cands if x.term != term and x.term not in assigned_term]
        margin = c.score - (rivals[0].score if rivals else 0.0)
        route = 'accept' if (c.score >= ACCEPT and (margin >= 0.05 or p.column in unit_notes)) else 'review'
        # A project-level term holds one value; a column whose values vary is at best a suggestion.
        level_note = ''
        if route == 'accept' and by_name[term].level == 'project' and not p.constant and p.n_unique > 1:
            route = 'review'
            if 'varies between rows' not in c.evidence:
                level_note = f'{p.n_unique} different values, but the term holds one value per project or assay'
        level_notes[p.column] = level_note
        if bases.get(p.column) and route == 'accept':
            base_prop = next((x for x in proposals if x.column == bases[p.column]), None)
            if base_prop is not None and base_prop.route != 'accept':
                route = 'review'
        evidence = '; '.join(x for x in (unit_notes.get(p.column, ''), c.evidence, level_note) if x)
        proposals.append(Proposal(p.column, term, ';'.join(by_name[term].sheets), c.score, route, evidence,
                                  unit_hint(p, by_name[term], by_name), shortlist))
    for pr in proposals:
        pr.part = parts.get(pr.column, 0) if pr.term else 0
        pr.unit_term = unit_extra.get(pr.column, '') if pr.term else ''
        if pr.unit_term:
            pr.value_part = 'number'
            pr.also = [(pr.unit_term, 'unit', f'the unit part of the same cells as {pr.term}')]
        if pr.term and pr.column in split_cols and pr.term in LATLON_TERMS:
            pr.value_part = 'latitude' if pr.term == 'decimalLatitude' else 'longitude'
            pr.also = also.get(pr.column, [])
            pr.hint = '; '.join(x for x in (f"split each cell into {' and '.join([pr.term] + pr.also_terms())}, "
                                            f"south and west negative", pr.hint) if x)
        elif pr.term and pr.column in also and pr.term in DEPTH_TERMS:
            pr.also = also[pr.column]
            pr.hint = '; '.join(x for x in (f"write the depth to {pr.term} and {pr.also_terms()[0]}", pr.hint) if x)
        if pr.part:
            pr.evidence = '; '.join(x for x in (part_notes[pr.column], pr.evidence) if x)
            pr.hint = '; '.join(x for x in (f'combine into {pr.term} with the other parts, in order', pr.hint) if x)
        if pr.unit_term:
            pr.hint = '; '.join(x for x in (f'split each cell into {pr.term} (the number) and {pr.unit_term} (the unit)',
                                            pr.hint) if x)
    # The columns that build one value are applied together: if any is for review, an accepted
    # part is for review too.
    for term in COMBINABLE:
        group = [pr for pr in proposals if pr.part and pr.term == term]
        if term in tied_groups or any(pr.route == 'review' for pr in group):
            for pr in group:
                if pr.route == 'accept':
                    pr.route = 'review'
                    pr.evidence += '; for review with the other parts'
    # Terms that people often confuse are always for review, however strong the match.
    confused = load_confused() if confused is None else confused
    for pr in proposals:
        if pr.route == 'accept' and any(x in confused[0] for x in [pr.term] + pr.also_terms()):
            pr.route = 'review'
            pr.evidence = '; '.join(x for x in (pr.evidence, 'a commonly confused FAIRe term, so for review') if x)
    # A column with no FAIRe term: a MIxS or Darwin Core term whose name matches, for review, as the FAIRe
    # guidelines ask for one before a made-up name. Not for unit columns, empty columns or columns answered
    # by a reviewer or model. A person confirms it; apply mapping then names the user-defined field after it.
    if other_terms:
        others = {t.name: t for t in other_terms if t.name not in by_name}
        other_list = list(others.values())
        other_scorer = NameScorer(other_list)
        for pr in proposals:
            p = prof[pr.column]
            # A column with no FAIRe match gets a suggestion; one whose FAIRe match is for review gets a
            # fallback, the name the column takes if the reviewer rejects that match (review sheet).
            if (pr.route not in ('no match', 'review') or not p.n_values or bases.get(pr.column)
                    or pr.column in unit_notes or (pr.route == 'no match' and pr.column in overrides)):
                continue
            header = tokens_of(pr.column)
            cands = [c for c in score_column(p, other_list, other_scorer, header, desc_map.get(pr.column))
                     if (c.from_desc and c.name_score >= 0.85 or other_name_fit(other_scorer, header, others[c.term])
                         >= OTHER_NAME_MIN) and not c.value_why.startswith(('conflict', 'check')) and c.score >= REVIEW]
            if cands and pr.route == 'review':
                pr.fallback = others[cands[0].term]
            elif cands:
                c = cands[0]
                pr.other, pr.other_score = others[c.term], c.score
                rivals = [others[x.term] for x in cands[1:3] if c.score - x.score < CLOSE]
                pr.other_comment = other_comment(pr, p, c, pr.other, rivals)
    # What the reviewer reads in the crosswalk.
    id_col = assigned_term.get('samp_name')
    flag_info = {}
    for col, (was, _s) in flags.items():
        kind = CONTROL_FLAGS[was]
        vals = [str(v).strip() for v in df[col] if not (v is None or (isinstance(v, float) and math.isnan(v)))]
        yes = list(dict.fromkeys(v for v in vals if v.lower() in BOOL_YES))
        no = list(dict.fromkeys(v for v in vals if v.lower() in BOOL_NO))
        example = ''
        if id_col is not None and id_col in df:
            hit = df.loc[df[col].astype(str).str.strip().str.lower().isin(BOOL_YES), id_col]
            example = str(hit.iloc[0]) if len(hit) else ''
        flag_info[col] = (was, kind, yes, no, sum(v.lower() in BOOL_YES for v in vals),
                          sum(v.lower() in BOOL_NO for v in vals), example)
    ctx = {'flags': flag_info, 'unit_notes': unit_notes, 'part_notes': part_notes, 'clashes': clashes,
           'confused': confused,
           'level_notes': level_notes,
           'rivals': {col: [x.term for x in cands if x.term not in assigned_term and x.score >= REVIEW]
                      for col, cands in scored.items()},
           'control_example': {n: next((v for v in by_name[n].vocab if v and 'negative' in v and v != 'site negative'),
                                       by_name[n].vocab[0] if by_name[n].vocab else '')
                               for n in ('neg_cont_type', 'pos_cont_type') if n in by_name}}
    for pr in proposals:
        if pr.term:
            c = next((x for x in scored[pr.column] if x.term == pr.term), None)
            pr.comment = reader_comment(pr, prof[pr.column], c, by_name.get(pr.term), ctx)
            pr.also = [(term, part, also_comment(pr, term, note, by_name.get(term))) for term, part, note in pr.also]
    return profiles, proposals


def missing_mandatory(terms, proposals, assay_type=None):
    """Mandatory terms no column provides, leaving out those the run settings supply
    (the checklist version, the assay type) and those conditional on the other assay type."""
    settings = {'checkls_ver'} | ({'assay_type'} if assay_type else set())
    mapped = {p.term for p in proposals if p.term} | {t for p in proposals if p.term for t in p.also_terms()}
    hinted = set()
    for p in proposals:
        for h in p.hint.split('; '):
            m = re.match(r'set (\S+) =', h)
            if m:
                hinted.add(m.group(1))
    rows = []
    for t in terms:
        if not t.mandatory or t.name in mapped or t.name in settings:
            continue
        m = re.match(r'if assay_type\s*=\s*(\w+)', t.condition.strip(), re.I)
        if assay_type and m and m.group(1).lower() != assay_type.lower():
            continue
        rows.append({'term': t.name, 'sheet': ';'.join(t.sheets), 'condition': t.condition,
                     'description': t.description, 'example': t.example,
                     'note': 'unit found in a header' if t.name in hinted else ''})
    return rows


# ------------------------------------------------------------------ outputs

def write_sssom(proposals, path, source_name, checklist_name):
    header = [
        '# curie_map:',
        '#   FAIRe: https://github.com/FAIR-eDNA/FAIRe_checklist#',
        "#   local: 'urn:faire-mapper:local:'",
        '#   skos: http://www.w3.org/2004/02/skos/core#',
        '#   semapv: https://w3id.org/semapv/vocab/',
        '#   MIXS: https://w3id.org/mixs/',
        '#   dwc: http://rs.tdwg.org/dwc/terms/',
        f'# mapping_set_id: urn:faire-mapper:{re.sub(r"[^A-Za-z0-9_.-]", "_", source_name)}',
        f'# mapping_set_description: Proposed mapping of the columns of {source_name} to FAIRe terms ({checklist_name})',
        '# license: https://creativecommons.org/publicdomain/zero/1.0/',
        f'# mapping_tool: faire_mapper {__version__}',
        f'# mapping_date: {dt.date.today().isoformat()}',
        '# extension_definitions:',
        '#   - slot_name: combine_order',
        '#     property: urn:faire-mapper:combine_order',
        '#     type_hint: xsd:integer',
        '#   - slot_name: value_part',
        '#     property: urn:faire-mapper:value_part',
        '#     type_hint: xsd:string',
        '# comment: each row\'s comment says what the FAIRe term means, why it was proposed, what the',
        '#   apply mapping tool will do with the values and, for rows to review, what to check.',
        '#   combine_order numbers the columns that together build one value, in order',
        '#   (geo_loc_name is country, then region, then locality). value_part says which part of each',
        '#   cell a term takes: number or unit (1 L fills samp_size and samp_size_unit), latitude or',
        '#   longitude (MIxS lat_lon), or a conversion (negative control if yes). The apply mapping',
        '#   tool applies rows with skos:exactMatch; change a row to skos:exactMatch to confirm it.',
        '#   A column with no skos:exactMatch row is kept as a user-defined field, unless the apply',
        '#   mapping tool is set to leave such columns out. Rows with a MIxS or Darwin Core term (MIXS: or',
        '#   dwc:) are for columns with no FAIRe term: confirmed, they name the user-defined field.',
    ]
    rows = crosswalk_rows(proposals)
    cols = ['subject_id', 'subject_label', 'predicate_id', 'object_id', 'object_label',
            'mapping_justification', 'confidence', 'comment', 'combine_order', 'value_part']
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(header) + '\n')
        pd.DataFrame(rows, columns=cols).to_csv(f, sep='\t', index=False)


CROSSWALK_COLUMNS = ['subject_id', 'subject_label', 'predicate_id', 'object_id', 'object_label',
                     'mapping_justification', 'confidence', 'comment', 'combine_order', 'value_part']


def crosswalk_rows(proposals):
    """The crosswalk's rows, as dicts."""
    rows = []
    for p in proposals:
        if not p.term and p.other is not None:
            rows.append({'subject_id': 'local:' + re.sub(r'[^A-Za-z0-9_.-]', '_', p.column), 'subject_label': p.column,
                         'predicate_id': 'skos:closeMatch', 'object_id': p.other.term_id, 'object_label': p.other.name,
                         'mapping_justification': 'semapv:CompositeMatching', 'confidence': round(p.other_score, 3),
                         'comment': p.other_comment, 'combine_order': '', 'value_part': ''})
            continue
        if not p.term:
            continue
        row = {
            'subject_id': 'local:' + re.sub(r'[^A-Za-z0-9_.-]', '_', p.column),
            'subject_label': p.column,
            'predicate_id': 'skos:exactMatch' if p.route in ('accept', 'confirmed', 'model') else 'skos:closeMatch',
            'object_id': f'FAIRe:{p.term}',
            'object_label': p.term,
            'mapping_justification': 'semapv:ManualMappingCuration' if p.route == 'confirmed' else 'semapv:CompositeMatching',
            'confidence': round(p.score, 3),
            'comment': p.comment or (f'{p.route}; {p.evidence}' + (f'; hint: {p.hint}' if p.hint else '')),
            'combine_order': p.part or '',
            'value_part': p.value_part,
        }
        rows.append(row)
        for term, part, note in p.also:
            rows.append({**row, 'object_id': f'FAIRe:{term}', 'object_label': term,
                         'comment': note if note.startswith('FAIRe term:') else f'{p.route}; {note}', 'value_part': part})
    return rows


def adjudication_requests(profiles, proposals, terms, descriptions=None):
    """Model-agnostic requests for columns routed to review or with no match."""
    descriptions = descriptions or {}
    by_name = {t.name: t for t in terms}
    prof = {p.column: p for p in profiles}
    reqs = []
    for pr in proposals:
        if pr.route not in ('review', 'no match') or not prof[pr.column].n_values:
            continue
        if pr.route == 'no match' and (not pr.candidates or float(pr.candidates[0].rsplit('(', 1)[1].rstrip(')')) < 0.25):
            continue  # nothing plausible to choose from
        p = prof[pr.column]
        options = []
        for item in pr.candidates:
            name = item.split(' (')[0]
            t = by_name[name]
            options.append({'term': name, 'description': t.description, 'type': t.term_type,
                            'allowed_values': list(t.vocab)[:20], 'example': t.example,
                            'sheet': ';'.join(t.sheets)})
        shared = [o['term'] for o in options if o['term'] in COMBINABLE]
        req = {
            'column': pr.column,
            'values': p.examples,
            'profile': p.summary(),
            'proposed': pr.term or None,
            'candidates': options,
            'instruction': ('Choose the FAIRe term that this column holds, from the candidates only, '
                            'or null if none fits. Use the values as well as the header. '
                            + (f'Several columns may share {shared[0]} when each holds one part of it '
                               '(country, region or locality). ' if shared else '')
                            + 'Reply as JSON: {"column": ..., "term": <candidate or null>, "reason": ...}'),
        }
        d = descriptions.get(pr.column)
        if d:
            req['description'] = d['description'] + (f" (units: {d['units']})" if d.get('units') else '')
            req['instruction'] = req['instruction'].replace('Use the values as well as the header.',
                                                            "Use the values, the header and the data provider's "
                                                            'description of the column.')
        reqs.append(req)
    return reqs


# Sample names that read as controls (Filt_control_3_4, Extbl19_4, PCRbl19_4, NTC, Field blank 2 ...)
CONTROL_NAME_RE = re.compile(r'control|blank|negative|\bneg\b|\bntc\b|ext_?bl|pcr_?bl|\bmock\b', re.I)
# Terms that say which rows are controls
CONTROL_TERMS = {'samp_category', 'neg_cont_type', 'pos_cont_type', *CONTROL_FLAGS}
REVIEW_COLUMNS = ['check', 'columns', 'rows', 'what_to_do']
TERM_ID_RE = re.compile(r'\[\s*[A-Za-z]+[:_]\s*\d+\s*\]')


def _first(items, k=10):
    return ', '.join(items[:k]) + (f' and {len(items) - k} more' if len(items) > k else '')


def _row_span(rows, n):
    return f'row {rows[0]} of {n}' if len(rows) == 1 else f'rows {rows[0]} to {rows[-1]} of {n}'


def review_list(df, profiles, proposals, confused=None):
    """What only a person can decide: a sample name used twice, controls named but not marked, columns
    of notes, and times of collection with no time zone. One row each, with what to do. The tool
    flags these and changes nothing."""
    out = []
    mapped = [pr for pr in proposals if pr.route != 'no match']
    name_col = next((pr.column for pr in mapped if pr.term == 'samp_name'), None)
    if name_col is not None and name_col in df.columns:
        names = [str(v).strip() for v in df[name_col].tolist() if not is_missing(v)]
        counts = pd.Series(names).value_counts() if names else pd.Series(dtype=int)
        repeats = [f'{k} ({v} rows)' for k, v in counts.items() if v > 1]
        if repeats:
            other = next((p.column for p in profiles if p.column != name_col and p.unique_per_row
                          and p.n_values == len(df) and p.filename_frac < 0.5 and p.numeric_frac < 0.5), None)
            out.append(['repeated sample names', name_col, _first(repeats),
                        'FAIRe needs one row per sample. Give each sample its own name in the table (a typing '
                        'slip, such as 8B for 9B, or a replicate letter or number), then propose mapping again'
                        + (f'. Or, if {other} (a different value on every row) names the samples, map it to '
                           f'samp_name instead' if other else '')])
        marked = any(pr.term in CONTROL_TERMS or CONTROL_TERMS & set(pr.also_terms()) for pr in mapped)
        controls = list(dict.fromkeys(n for n in names if CONTROL_NAME_RE.search(n)))
        if controls and not marked:
            out.append(['controls not marked', name_col, _first(controls),
                        'These names read as controls, but no column says which rows are controls, and the '
                        'tool does not decide from names. Add a sample type column (sample or negative control) '
                        'and a control type column (field, extraction or PCR negative ...), then propose mapping '
                        'again'])
    n = len(df)
    for c in df.columns:
        if str(c).startswith('Unnamed: '):   # no header (pandas names it), so never mapped
            continue
        rows = [i + 1 for i, v in enumerate(df[c].tolist()) if not is_missing(v) and str(v).strip()]
        # values in a few rows at the top only (not a column left empty for controls at the end)
        if n >= 6 and rows and len(rows) <= n // 2 and rows[-1] <= max(5, n // 10):
            out.append(['notes, not sample values', str(c), _row_span(rows, n),
                        'Values only in the first rows, so they may be notes about the whole study. If so, '
                        'leave the column out (delete its row in the crosswalk) and give anything FAIRe needs from them '
                        '(recordedBy, for example) as a project value. If they belong to those rows only, keep '
                        'the column'])
    # Several ontology terms in one cell ("Neritic Pelagic Zone Biome [ENVO:01000032]|Oceanic ..."): FAIRe
    # allows several, but a list may be choices that were never narrowed down
    for pr in mapped:
        if pr.column not in df.columns:
            continue
        cells = [str(v) for v in df[pr.column].tolist() if not is_missing(v) and '|' in str(v)]
        multi = [v for v in cells if len(TERM_ID_RE.findall(v)) >= 2]
        if multi:
            parts = list(dict.fromkeys(x.strip() for v in multi for x in v.split('|') if x.strip()))
            out.append(['several terms in one cell', pr.column, f'{len(multi)} rows: ' + _first(parts, 5),
                        f'FAIRe allows several terms in {pr.term}, separated by |, but check that each applies to '
                        f'these samples, and keep only the one that does if one is meant. The workbook gives these '
                        f'cells a drop-down of the terms'])
    # Terms that people often confuse, with the question that tells them apart
    confused = load_confused() if confused is None else confused
    for pr in mapped:
        names = [x for x in [pr.term] + pr.also_terms() if x in confused[0]]
        if names:
            out.append(['often confused terms', pr.column, ', '.join(names), confused_note(names, confused)])
    # The times that go into eventDate: a column matched to verbatimEventTime, or eventDate with times.
    # Daily cycles follow local time, so eventDate keeps it; the UTC offset adds the time zone.
    timed = {pr.column for pr in mapped if pr.term in ('verbatimEventTime', 'eventDate')}
    for p in profiles:
        if p.column not in timed or not p.n_values or not (p.time_frac >= 0.8 or p.date_format == 'ISO date-time'):
            continue
        rows = f"{p.n_values} rows ({', '.join(time_text(v) for v in p.examples[:3])} ...)"
        if re.search(r'\b(UTC|GMT)\b', p.column, re.I):
            out.append(['times in UTC', p.column, rows,
                        'Daily cycles follow local time. If the table also gives the local time, match that '
                        'column to verbatimEventTime instead; or give the UTC offset of the sampling sites on '
                        'apply mapping\'s form, which then converts these times to local time in eventDate '
                        '(taking the dates as UTC dates)'])
            continue
        zone = re.search(r'\(([A-Z]{2,4}T)\)', p.column)
        out.append(['times with no time zone', p.column, rows,
                    'The times are taken as local time, which daily cycles follow. '
                    + (f'The column name gives the time zone ({zone.group(1)}): give its UTC offset on apply '
                       f'mapping\'s form' if zone else
                       'Give their UTC offset on apply mapping\'s form (+11:00 for Australian Eastern Daylight '
                       'Time, for example)')
                    + ', so eventDate also gives the time zone. NCBI needs it, as it takes times in UTC only'])
    return out


DICT_NAME_COLS = {'column', 'columnname', 'variable', 'variablename', 'field', 'fieldname', 'name', 'header',
                  'attribute', 'columnheader', 'parameter'}
DICT_DESC_COLS = {'description', 'definition', 'meaning', 'explanation', 'details', 'notes', 'comment',
                  'comments', 'info', 'information'}
DICT_UNIT_COLS = {'unit', 'units', 'measurementunit'}
UNIT_IN_TEXT = re.compile(r'\b(?:in|units?:?|measured in)\s+(?:units of\s+)?([A-Za-zµμ°%/]+(?:\s?[A-Za-z]+)?)', re.I)


def _norm_col(s):
    return re.sub(r'[^a-z0-9]', '', str(s).lower())


def _match_column(name, columns):
    """The table column a dictionary entry names: exact, then ignoring case, spaces and punctuation."""
    name = str(name).strip()
    if name in columns:
        return name
    for c in columns:
        if str(c).strip() == name:
            return c
    key = _norm_col(name)
    hits = [c for c in columns if _norm_col(c) == key and key]
    return hits[0] if len(hits) == 1 else None


def _units_from(text):
    for m in UNIT_IN_TEXT.finditer(str(text)):
        u = UNIT_ALIASES.get(m.group(1).strip().lower())
        if u:
            return u
    for inner in re.findall(r'\(([^)]{1,20})\)', str(text)):
        u = UNIT_ALIASES.get(inner.strip().lower())
        if u:
            return u
    return ''


def read_dictionary(path, columns, sheet=None):
    """Column descriptions as {table column: {'description', 'units'}}, from a table (column,
    description, units) or from 'column: description' lines in a README. Entries that name no column
    of the table are left out. Returns (descriptions, notes)."""
    columns = list(columns)
    entries, form = [], ''
    raw = Path(path).read_bytes()
    is_excel = raw[:4] == b'PK\x03\x04'
    text = '' if is_excel else raw.decode('utf-8', errors='replace')
    table = None
    if is_excel:
        xl = pd.ExcelFile(path)
        name = sheet if sheet else xl.sheet_names[0]
        if name not in xl.sheet_names:
            raise SystemExit(f"ERROR: the data dictionary has no sheet called '{name}'. Sheets: {', '.join(xl.sheet_names)}")
        table = pd.read_excel(path, sheet_name=name, dtype=str).fillna('')
    else:
        first = next((ln for ln in text.splitlines() if ln.strip()), '')
        sep = '\t' if '\t' in first else (',' if first.count(',') >= 1 and not re.match(r'^[^,]{1,80}:', first) else None)
        if sep:
            try:
                table = pd.read_csv(io.StringIO(text), sep=sep, dtype=str, keep_default_na=False)
            except (pd.errors.ParserError, ValueError):
                table = None
    if table is not None and len(table.columns) >= 2:
        keys = [_norm_col(c) for c in table.columns]
        ncol = next((table.columns[i] for i, k in enumerate(keys) if k in DICT_NAME_COLS), None)
        dcol = next((table.columns[i] for i, k in enumerate(keys) if k in DICT_DESC_COLS), None)
        ucol = next((table.columns[i] for i, k in enumerate(keys) if k in DICT_UNIT_COLS), None)
        if ncol is None or dcol is None:
            hits = sum(_match_column(v, columns) is not None for v in table.iloc[:, 0])
            if hits >= max(1, len(table) // 2):
                ncol, dcol = table.columns[0], table.columns[1]
        if ncol is not None and dcol is not None:
            form = 'table'
            for r in table.to_dict('records'):
                entries.append((r[ncol], r[dcol], r[ucol] if ucol else ''))
    if not entries and text:
        form = 'lines'
        for ln in text.splitlines():
            ln = re.sub(r'^\s*(?:[-*•]|\d+[.)])\s+', '', ln.strip())
            if ln.startswith('|'):
                cells = [c.strip() for c in ln.strip('|').split('|')]
                if len(cells) >= 2:
                    entries.append((cells[0], cells[1], cells[2] if len(cells) > 2 else ''))
                continue
            m = re.match(r'^([^:\t]{1,80}?)\s*(?::|\t|\s[-–]\s)\s*(.+)$', ln)
            if m:
                entries.append((m.group(1), m.group(2), ''))
    out = {}
    for name, desc, units in entries:
        name = re.sub(r'^[*_`]+|[*_`]+$', '', str(name).strip())
        col = _match_column(name, columns)
        desc = str(desc).strip()
        if col is None or not desc or col in out:
            continue
        u = UNIT_ALIASES.get(str(units).strip().lower(), str(units).strip()) if str(units).strip() else _units_from(desc)
        out[col] = {'description': desc, 'units': u}
    notes = [f"data dictionary ({'table' if form == 'table' else 'README lines'}): descriptions for {len(out)} of "
             f"{len(columns)} columns"]
    missing = [c for c in columns if c not in out]
    if out and missing:
        notes.append('no description for: ' + ', '.join(str(c) for c in missing[:8]) + (' ...' if len(missing) > 8 else ''))
    return out, notes


def read_responses(path, with_source=False):
    """Answers as {column: term}. Each answer may say who gave it ("by": "model:<name>" or a person);
    with_source also returns {column: by}."""
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict):
        data = data.get('responses', [data])
    terms = {d['column']: (d.get('term') or None) for d in data}
    return (terms, {d['column']: str(d.get('by') or '') for d in data}) if with_source else terms


def comment_rows(rows, is_header=None):
    """The number of rows to skip above the header when it is preceded by comment lines starting
    with # (as in NCBI and ENA submission sheets): up to the first row that is neither blank nor a
    comment. A row starting with # that holds several cells is a header (#OTU ID in QIIME tables).
    0 when there are no comment lines."""
    seen = False
    for i, cells in enumerate(rows):
        cells = [str(c).strip() for c in cells if not _missing_cell(c)]
        if not cells:
            continue
        header = len(cells) > 1 if is_header is None else is_header(i)
        if cells[0].lstrip('"').startswith('#') and not header:
            seen = True
            continue
        return i if seen else 0
    return 0


def _text_comment_rows(lines):
    """comment_rows for lines of text: a line starting with # is a header when it splits into the
    same number of fields (two or more) as the lines after it."""
    import csv

    def is_header(i):
        rest = [ln for ln in lines[i + 1:] if ln.strip() and not ln.lstrip('"').startswith('#')][:2]
        for sep in ('\t', ',', ';', '|'):
            try:
                rows = list(csv.reader([lines[i]] + rest, delimiter=sep))
            except csv.Error:
                continue
            if rest and sum(bool(c.strip()) for c in rows[0]) > 1 and all(len(r) == len(rows[0]) for r in rows):
                return True
        return False
    return comment_rows([[ln.strip()] for ln in lines], is_header)


def _missing_cell(c):
    return c is None or (isinstance(c, float) and math.isnan(c)) or not str(c).strip()


def read_table(path, sheet=None, header_row=1):
    """A table with one header row. With the header row left at 1, comment lines starting with #
    above the header are skipped."""
    path = str(path)
    suffix = Path(path).suffix.lower()
    skip = max(0, int(header_row) - 1)
    notes = []
    if suffix in ('.xlsx', '.xlsm', '.xls') or (suffix not in ('.csv', '.tsv', '.txt', '.tabular') and _is_excel(path)):
        xl = pd.ExcelFile(path)
        name = sheet if sheet else xl.sheet_names[0]
        if name not in xl.sheet_names:
            raise SystemExit(f"ERROR: no sheet called '{name}'. Sheets: {', '.join(xl.sheet_names)}")
        if not skip:
            top = pd.read_excel(path, sheet_name=name, header=None, nrows=60, dtype=object)
            skip = comment_rows(top.values.tolist())
            if skip:
                notes.append(f'skipped {skip} comment lines (starting with #) above the header')
        df = pd.read_excel(path, sheet_name=name, skiprows=skip, dtype=object)
    else:
        enc = _text_encoding(path)
        if not skip:
            with open(path, encoding=enc) as f:
                top = [f.readline() for _ in range(60)]
            skip = _text_comment_rows([ln for ln in top if ln])
            if skip:
                notes.append(f'skipped {skip} comment lines (starting with #) above the header')
        with open(path, encoding=enc) as f:
            lines = [f.readline() for _ in range(skip + 6)]
        sep = _separator(lines[skip:])
        df = pd.read_csv(path, sep=sep, skiprows=skip, dtype=str, keep_default_na=False, na_values=[''],
                         encoding=enc)
        if enc != 'utf-8-sig':
            notes.append(f'read as {enc} text')
        if sep != ',':
            notes.append(f"separator {'tab' if sep == chr(9) else repr(sep)}")
        if sep != ',':
            fixed = _decimal_commas(df)
            if fixed:
                notes.append(f'decimal commas read as points in {len(fixed)} columns')
    df.attrs['read_notes'] = notes
    df = df.loc[:, [c for c in df.columns if not str(c).startswith('Unnamed:') or df[c].notna().any()]]
    df = df.dropna(how='all')
    if df.empty or not len(df.columns):
        raise SystemExit('ERROR: the table has no rows or no columns. Check the header row.')
    return df


def _text_encoding(path):
    """UTF-8 if the file decodes as UTF-8, otherwise Windows-1252 (a superset of Latin-1 for text)."""
    with open(path, 'rb') as f:
        raw = f.read()
    try:
        raw.decode('utf-8')
        return 'utf-8-sig'
    except UnicodeDecodeError:
        pass
    try:
        raw.decode('cp1252')
        return 'cp1252'
    except UnicodeDecodeError:
        return 'latin-1'


def _separator(lines):
    """The separator that splits the header and the first rows into the same, largest number of fields.
    Quoted fields are respected, so a header such as "Latitude (decimal; south is negative)" does not count."""
    import csv
    sample = ''.join(lines)
    best, best_n = ',', 1
    for sep in (',', '\t', ';', '|'):
        try:
            rows = [r for r in csv.reader(sample.splitlines(), delimiter=sep) if r]
        except csv.Error:
            continue
        rows = rows[:-1] if len(rows) > 2 else rows   # the last line read may be cut short
        if not rows:
            continue
        n = len(rows[0])
        if n > best_n and all(len(r) == n for r in rows[1:]):
            best, best_n = sep, n
    if best_n == 1:
        # Rows that leave off empty fields at the end (term<TAB>value under a header with an assay
        # column, as a text editor may save them): the separator that gives every row 2 fields or
        # more, and none more than the header.
        for sep in ('\t', ';', '|', ','):
            try:
                rows = [r for r in csv.reader(sample.splitlines(), delimiter=sep) if r]
            except csv.Error:
                continue
            rows = rows[:-1] if len(rows) > 2 else rows
            if rows and len(rows[0]) > 1 and all(2 <= len(r) <= len(rows[0]) for r in rows[1:]):
                return sep
    return best


DECIMAL_COMMA_RE = re.compile(r'^-?\d+,\d+$')


def _decimal_commas(df):
    """In a table not separated by commas, read 0,588 as 0.588 in columns where most values look like that."""
    fixed = []
    for c in df.columns:
        vals = df[c].dropna().astype(str).str.strip()
        vals = vals[vals != '']
        if len(vals) and vals.str.match(DECIMAL_COMMA_RE).mean() >= 0.5 and \
                vals.str.match(r'^-?\d+([.,]\d+)?$').mean() >= 0.9:
            df[c] = df[c].str.replace(r'^(-?\d+),(\d+)$', r'\1.\2', regex=True)
            fixed.append(c)
    return fixed


def _is_excel(path):
    with open(path, 'rb') as f:
        return f.read(4) == b'PK\x03\x04'


# ------------------------------------------------------------------ evaluation

def evaluate(proposals, gold):
    """gold: {column: term or None}. Reports top-1 accuracy, shortlist recall and abstention."""
    rows, hit, n, inlist, abst_ok, n_abst = [], 0, 0, 0, 0, 0
    for p in proposals:
        if p.column not in gold:
            continue
        g = gold[p.column]
        short = [c.split(' (')[0] for c in p.candidates]
        if g:
            n += 1
            hit += int(p.term == g)
            inlist += int(g in short)
        else:
            n_abst += 1
            abst_ok += int(not p.term)
        rows.append({'column': p.column, 'gold': g or '', 'proposed': p.term, 'route': p.route,
                     'correct': (p.term == g) if g else (not p.term), 'gold_in_shortlist': (g in short) if g else ''})
    res = {'columns': len(rows), 'with_term': n, 'top1_accuracy': round(hit / n, 3) if n else None,
           'shortlist_recall': round(inlist / n, 3) if n else None,
           'distractors': n_abst, 'distractors_left_unmatched': round(abst_ok / n_abst, 3) if n_abst else None}
    acc = [r for r in rows if r['route'] == 'accept']
    res['accepted'] = len(acc)
    res['accepted_correct'] = round(sum(r['correct'] for r in acc) / len(acc), 3) if acc else None
    return res, rows


# ------------------------------------------------------------------ command line

def cmd_profile(args):
    df = read_table(args.table, args.sheet, args.header_row)
    profiles = profile_table(df)
    rows = []
    for p in profiles:
        d = asdict(p)
        d['examples'] = ' | '.join(map(str, p.examples))
        d['header_units'] = ', '.join(p.header_units)
        d.pop('distinct')
        d['summary'] = p.summary()
        rows.append(d)
    out = pd.DataFrame(rows)
    first = ['column', 'summary', 'n_rows', 'n_values', 'n_unique', 'examples']
    out = out[first + [c for c in out.columns if c not in first]]
    out.to_csv(args.output, sep='\t', index=False)
    for note in df.attrs.get('read_notes', []):
        print(f'INFO: {note}')
    print(f'INFO: profiled {len(profiles)} columns and {len(df)} rows')
    return 0


def cmd_map(args):
    df = read_table(args.table, args.sheet, args.header_row)
    sample_types = [s.strip() for s in args.sample_types.split(',')] if args.sample_types else None
    terms = load_checklist(args.checklist, assay_type=args.assay_type, sample_types=sample_types)
    overrides, answered_by = read_responses(args.responses, with_source=True) if args.responses else (None, None)
    descriptions, dict_notes = read_dictionary(args.dictionary, df.columns, args.dictionary_sheet) \
        if args.dictionary else ({}, [])
    confused = load_confused(args.confused_terms)
    other_terms = [] if args.no_other_terms else load_other_terms(args.other_terms)
    profiles, proposals = propose(df, terms, k=args.shortlist, k_close=args.shortlist_close, overrides=overrides,
                                  answered_by=answered_by,
                                  descriptions=descriptions, confused=confused, other_terms=other_terms)
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    rep = pd.DataFrame([{'column': p.column, 'proposed_term': p.term, 'faire_sheet': p.sheet,
                         'route': p.route, 'score': round(p.score, 3), 'evidence': p.evidence,
                         'transform_hint': p.hint, 'shortlist': '; '.join(p.candidates),
                         'combine_order': p.part or '', 'unit_term': p.unit_term,
                         'also_fills': ', '.join(p.also_terms()),
                         'description': descriptions.get(p.column, {}).get('description', ''),
                         'other_standard': f'{p.other.source}: {p.other.name} ({p.other_score:.2f})' if p.other else ''}
                        for p in proposals])
    rep.to_csv(out / 'mapping_report.tsv', sep='\t', index=False)
    write_sssom(proposals, out / 'crosswalk.sssom.tsv', Path(args.table).name, Path(args.checklist).name)
    pd.DataFrame(missing_mandatory(terms, proposals, args.assay_type),
                 columns=['term', 'sheet', 'condition', 'description', 'example', 'note']).to_csv(
        out / 'missing_mandatory.tsv', sep='\t', index=False)
    reqs = adjudication_requests(profiles, proposals, terms, descriptions)
    with open(out / 'adjudication_requests.json', 'w') as f:
        json.dump(reqs, f, indent=1)
    review = review_list(df, profiles, proposals, confused)
    pd.DataFrame(review, columns=REVIEW_COLUMNS).to_csv(out / 'review_list.tsv', sep='\t', index=False)
    import faire_mapper_review   # here, as it imports this module
    faire_mapper_review.write_review_sheet(out / 'review_sheet.xlsx', proposals, profiles, terms, review,
                                           Path(args.table).name, k=args.shortlist)
    counts = rep.route.value_counts().to_dict()
    summary = {'table': Path(args.table).name, 'checklist': Path(args.checklist).name, 'columns': len(proposals),
               'accept': counts.get('accept', 0), 'review': counts.get('review', 0),
               'no_match': counts.get('no match', 0), 'confirmed': counts.get('confirmed', 0),
               'model': counts.get('model', 0),
               'other_standard': sum(p.other is not None for p in proposals),
               'terms_considered': len(terms),
               'missing_mandatory': int(len(missing_mandatory(terms, proposals, args.assay_type))),
               'to_decide': len(review),
               'read_notes': df.attrs.get('read_notes', []) + dict_notes,
               'faire_mapper_version': __version__}
    if args.gold:
        gold_df = pd.read_csv(args.gold, sep='\t', dtype=str, keep_default_na=False)
        gold = {r['column']: (r['term'] or None) for r in gold_df.to_dict('records')}
        res, rows = evaluate(proposals, gold)
        pd.DataFrame(rows).to_csv(out / 'evaluation.tsv', sep='\t', index=False)
        summary['evaluation'] = res
    with open(out / 'summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    for note in df.attrs.get('read_notes', []) + dict_notes:
        print(f'INFO: {note}')
    print(f"INFO: {summary['columns']} columns: {summary['accept']} accept, {summary['review']} review, "
          f"{summary['no_match']} no match, {summary['confirmed']} confirmed, {summary['model']} chosen by a model; "
          f"{summary['missing_mandatory']} mandatory FAIRe terms not covered")
    if summary['other_standard']:
        print(f"INFO: {summary['other_standard']} columns with no FAIRe term have a MIxS or Darwin Core term, for review: "
              + ', '.join(f"{p.column} ({p.other.source} {p.other.name})" for p in proposals if p.other))
    for check, col, rows, _ in review:
        print(f'INFO: to decide: {check} ({col}: {rows})')
    if args.gold:
        print('INFO: evaluation ' + json.dumps(summary['evaluation']))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog='faire_mapper', description=__doc__.splitlines()[0])
    ap.add_argument('--version', action='version', version=__version__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('profile', 'map'):
        s = sub.add_parser(name)
        s.add_argument('table', help='CSV, TSV or Excel table with one header row')
        s.add_argument('--sheet', help='Excel sheet name (default: first sheet)')
        s.add_argument('--header_row', type=int, default=1, help='row number of the column headers (default 1)')
    sub.choices['profile'].add_argument('-o', '--output', required=True, help='profile table (TSV)')
    m = sub.choices['map']
    m.add_argument('--checklist', required=True, help='FAIRe checklist workbook (FAIRe_checklist_v*.xlsx)')
    m.add_argument('--assay_type', choices=['metabarcoding', 'targeted'], help='leave out terms for the other assay type')
    m.add_argument('--sample_types', help='comma-separated sample types (Water, Soil, Sediment, Air, ...)')
    m.add_argument('--confused_terms', default=str(CONFUSED_TERMS),
                   help='table of FAIRe terms people often confuse (group, term, meaning, check); these are '
                        'always for review (default: commonly_confused_terms.tsv beside this script)')
    m.add_argument('--other_terms', default=str(OTHER_TERMS),
                   help='MIxS and Darwin Core terms that FAIRe lacks, suggested (for review) for columns with no FAIRe '
                        'term (default: mixs_dwc_terms.tsv beside this script)')
    m.add_argument('--no_other_terms', action='store_true', help='do not suggest MIxS or Darwin Core terms')
    m.add_argument('--shortlist', type=int, default=5, help='candidates listed per column (default 5)')
    m.add_argument('--shortlist_close', type=int, default=10,
                   help='candidates listed when the last of --shortlist scores within %.2f of the first, so no '
                        'term clearly leads (default 10; the same as --shortlist to turn this off)' % CLOSE)
    m.add_argument('--responses', help='JSON answers for review columns: [{"column": ..., "term": ... or null}]')
    m.add_argument('--dictionary', help='data dictionary: a table of column, description (and units), or a README '
                                        'with "column: description" lines')
    m.add_argument('--dictionary_sheet', help='Excel sheet of the data dictionary (default: first sheet)')
    m.add_argument('--gold', help='TSV with columns column, term: known answers, to measure accuracy')
    m.add_argument('-o', '--outdir', required=True)
    args = ap.parse_args(argv)
    return cmd_profile(args) if args.cmd == 'profile' else cmd_map(args)


if __name__ == '__main__':
    sys.exit(main())
