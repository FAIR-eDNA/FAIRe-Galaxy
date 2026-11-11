"""Galaxy driver for FAIRe2NCBI.

Runs the upstream FAIRe2NCBI scripts (scripts/FAIRe2NCBI.py and the
FAIRe2BioSample and FAIRe2SRA modules) without modifying them. The upstream
scripts ask questions with input(); a Galaxy job cannot answer them. This
driver:

  * prepares a copy of the workbook (assay columns relabelled by assay_name
    with normalise_faire.py, eventDate values converted for NCBI, organism
    and empty mandatory fields filled, rows filtered), finding empty cells
    as upstream does: text such as NA is empty in sampleMetadata and
    projectMetadata, and a value in experimentRunMetadata;
  * answers every question from the Galaxy form, and writes those answers to
    a YAML config that the upstream script accepts with --config_file;
  * runs with stdin closed, and turns any question it did not answer into a
    plain error naming the question (upstream would raise EOFError);
  * stops if the upstream script loops on a rejected answer, or returns
    without writing its output;
  * checks the output (unique library_ID and file names, accessions) and
    links SRA rows to their BioSamples;
  * joins the SRA rows of a library that holds several assays (the same
    sample and files), as NCBI takes one row for each set of files: the
    title and design description then name every assay;
  * gives library_ID as the lab's name for the library: FAIRe's lib_id is
    one amplicon of a sample, and the FAIRe mapper writes it as the library
    name, assay_name and seq_run_id, so those two are taken off.

Two upstream functions are replaced while it runs (patch_upstream), as the
scripts themselves are not changed:

  * the workbook is read with each cell's own type, so a column of whole
    numbers with empty cells stays whole (14, not 14.0), and units can be
    added to it (upstream stops on an all-integer column such as
    samp_store_temp -80);
  * lat_lon keeps the decimal places of the workbook (upstream rounds to 3,
    about 100 m).
"""

import argparse
import builtins
import collections
import datetime
import os
import re
import sys

import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True  # tool directories are often read-only on Galaxy servers
sys.path.insert(0, os.path.join(HERE, 'scripts'))
sys.path.insert(0, HERE)
import FAIRe2BioSample as upstream_bs  # noqa: E402
import FAIRe2NCBI as upstream_main  # noqa: E402
import FAIRe2SRA as upstream_sra  # noqa: E402
import normalise_faire  # noqa: E402

# NCBI SRA platform and instrument_model values: the 'Library and Platform Terms'
# sheet of docs/NCBI_SRA_Metadata_Template.xlsx, limited to the instruments that
# the upstream FAIRe2SRA.py accepts for each platform.
NCBI_INSTRUMENTS = {
    '_LS454': ['454 GS', '454 GS 20', '454 GS FLX', '454 GS FLX+', '454 GS FLX Titanium', '454 GS Junior'],
    'ABI_SOLID': ['AB 5500 Genetic Analyzer', 'AB 5500xl Genetic Analyzer', 'AB 5500x-Wl Genetic Analyzer',
                  'AB SOLiD 3 Plus System', 'AB SOLiD 4 System', 'AB SOLiD 4hq System', 'AB SOLiD PI System',
                  'AB SOLiD System', 'AB SOLiD System 2.0', 'AB SOLiD System 3.0'],
    'BGISEQ': ['BGISEQ-50', 'BGISEQ-500', 'MGISEQ-2000RS'],
    'CAPILLARY': ['AB 310 Genetic Analyzer', 'AB 3130 Genetic Analyzer', 'AB 3130xL Genetic Analyzer',
                  'AB 3500 Genetic Analyzer', 'AB 3500xL Genetic Analyzer', 'AB 3730 Genetic Analyzer',
                  'AB 3730xL Genetic Analyzer'],
    'COMPLETE_GENOMICS': ['Complete Genomics'],
    'DNBSEQ': ['DNBSEQ-G400', 'DNBSEQ-G50', 'DNBSEQ-T7', 'DNBSEQ-G400 FAST'],
    'ELEMENT': ['Element AVITI'],
    'GENAPSYS': ['GS111'],
    'GENEMIND': ['GenoCare 1600', 'GenoLab M'],
    'HELICOS': ['Helicos HeliScope'],
    'ILLUMINA': ['HiSeq X Five', 'HiSeq X Ten', 'Illumina Genome Analyzer', 'Illumina Genome Analyzer II',
                 'Illumina Genome Analyzer IIx', 'Illumina HiScanSQ', 'Illumina HiSeq 1000', 'Illumina HiSeq 1500',
                 'Illumina HiSeq 2000', 'Illumina HiSeq 2500', 'Illumina HiSeq 3000', 'Illumina HiSeq 4000',
                 'Illumina HiSeq X', 'Illumina MiSeq', 'Illumina MiniSeq', 'Illumina NovaSeq 6000',
                 'Illumina NovaSeq X', 'Illumina NovaSeq X Plus', 'Illumina iSeq 100', 'NextSeq 1000',
                 'NextSeq 2000', 'NextSeq 500', 'NextSeq 550'],
    'ION_TORRENT': ['Ion Torrent PGM', 'Ion Torrent Proton', 'Ion Torrent S5 XL', 'Ion Torrent S5',
                    'Ion Torrent Genexus', 'Ion GeneStudio S5', 'Ion GeneStudio S5 Plus', 'Ion GeneStudio S5 Prime'],
    'OXFORD_NANOPORE': ['GridION', 'MinION', 'PromethION'],
    'PACBIO_SMRT': ['PacBio RS', 'PacBio RS II', 'Revio', 'Sequel', 'Sequel II', 'Sequel IIe', 'Onso'],
    'TAPESTRI': ['Tapestri'],
    'ULTIMA': ['UG 100'],
    'VELA_DIAGNOSTICS': ['Sentosa SQ301'],
}
INSTRUMENT_PLATFORM = {m: p for p, models in NCBI_INSTRUMENTS.items() for m in models}

# Mandatory MIMARKS water fields and the FAIRe terms the upstream script fills
# them from (the hard-coded mapping in FAIRe2BioSample.biosample_mode).
MANDATORY_SOURCES = {
    '*organism': ['organism'],
    '*collection_date': ['eventDate'],
    '*depth': ['maximumDepthInMeters'],
    '*env_broad_scale': ['env_broad_scale'],
    '*env_local_scale': ['env_local_scale'],
    '*env_medium': ['env_medium'],
    '*geo_loc_name': ['geo_loc_name'],
    '*lat_lon': ['decimalLatitude', 'decimalLongitude'],
}

# INSDC missing-value terms (https://www.insdc.org/missing-value-reporting)
INSDC_MISSING = ('not applicable', 'missing', 'not collected', 'not provided', 'restricted access')

OFFSET_RE = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)([+-]\d{2}):?(\d{2})$')
NCBI_DATE_RE = re.compile(
    r'^(\d{4}(-\d{2}(-\d{2}(T\d{2}:\d{2}(:\d{2})?Z)?)?)?'
    r'|(\d{2}-)?[A-Z][a-z]{2}-\d{4})'
    r'(/(\d{4}(-\d{2}(-\d{2}(T\d{2}:\d{2}(:\d{2})?Z)?)?)?|(\d{2}-)?[A-Z][a-z]{2}-\d{4}))?$'
)
MAX_REPEATS = 20


class Stop(BaseException):
    """Stop the run with a message. BaseException, so that upstream
    'except Exception' blocks do not swallow it."""


def fail(message):
    sys.stdout.flush()
    sys.stderr.write(f"ERROR: {message}\n")
    sys.exit(1)


def info(message):
    print(f"INFO: {message}")


def warn(message):
    print(f"WARNING: {message}")


def blank(value):
    return value is None or (isinstance(value, float) and pd.isna(value)) or str(value).strip() == ''


def is_missing_term(value):
    return str(value).strip().lower().startswith(INSDC_MISSING)


def split_list(text):
    return [v.strip() for v in (text or '').split(',') if v.strip()]


# --------------------------------------------------------------- stdout capture

class Tee:
    """Copy stdout to the log without colour codes, and keep recent lines."""

    ansi = re.compile(r'\x1b\[[0-9;]*m')

    def __init__(self, stream):
        self.stream = stream
        self.lines = collections.deque(maxlen=2000)
        self._partial = ''

    def write(self, text):
        text = self.ansi.sub('', text)
        self.stream.write(text)
        self._partial += text
        *done, self._partial = self._partial.split('\n')
        self.lines.extend(done)
        return len(text)

    def flush(self):
        self.stream.flush()

    def recent(self, n=200):
        return list(self.lines)[-n:] + ([self._partial] if self._partial else [])

    def after(self, marker):
        """Lines printed after the last line matching the regular expression marker."""
        lines = self.recent(len(self.lines) + 1)
        starts = [i for i, line in enumerate(lines) if re.search(marker, line)]
        return lines[starts[-1] + 1:] if starts else []

    def numbered(self, marker):
        """{name: number} from an upstream list such as '   3. temp (e.g., 28.5, 29.2)'."""
        listed = {}
        for line in self.after(marker):
            m = re.match(r'^\s+(\d+)\. (\S+) \(e\.g\.', line)
            if m:
                listed[m.group(2)] = m.group(1)
        return listed


# --------------------------------------------------------------- workbook copy

class Sheet:
    """A FAIRe sheet read with header=None: two header rows, field names on row 3."""

    def __init__(self, df):
        self.df = df

    @property
    def fields(self):
        return [None if blank(v) else str(v).strip() for v in self.df.iloc[2]]

    def col(self, name):
        try:
            return self.df.columns[self.fields.index(name)]
        except ValueError:
            return None

    def data_index(self):
        return self.df.index[3:]

    def add_column(self, name):
        new = self.df.columns.max() + 1
        self.df = self.df.copy()   # a sheet with many columns is fragmented; pandas warns on each insert
        self.df[new] = None
        self.df.iat[2, self.df.columns.get_loc(new)] = name
        return new

    def drop_rows(self, keep_mask):
        """keep_mask: boolean list for the data rows."""
        keep = [True, True, True] + list(keep_mask)
        self.df = self.df[keep]


def read_prepared(path):
    """The normalised workbook, with each sheet's empty cells as upstream will find them.
    Upstream reads sampleMetadata and projectMetadata with pandas' default missing values, so text
    such as NA or N/A in those sheets is empty here too (and the form's fill for empty mandatory
    fields applies to it). It reads experimentRunMetadata as literal text, where NA or N/A in
    associatedSequences marks a run as submitted, so that sheet is kept as it is."""
    try:
        sheets = pd.read_excel(path, sheet_name=None, header=None, keep_default_na=False, na_values=[])
    except Exception as err:  # noqa: BLE001
        fail(f"could not read the workbook ({err}).")
    for name in ('sampleMetadata', 'experimentRunMetadata'):
        df = sheets[name]
        if len(df) < 3:
            fail(f"the {name} sheet needs field names on row 3.")
        df = df.astype(object).where(df.astype(str) != '', None)
        sheets[name] = df
    sheets['projectMetadata'] = sheets['projectMetadata'].astype(object).where(
        sheets['projectMetadata'].astype(str) != '', None)
    for name in ('sampleMetadata', 'projectMetadata'):
        na_text = sheets[name].isin(normalise_faire.PANDAS_NA)
        count = int(na_text.to_numpy().sum())
        if count:
            sheets[name] = sheets[name].mask(na_text, None)
            info(f"{name}: {count} cell(s) of text such as NA or N/A read as empty, as upstream reads this sheet")
    return sheets


def write_workbook(sheets, path):
    normalise_faire.write_values(sheets, path)


def ncbi_date(value):
    """Return (value, changed, note) for an eventDate value."""
    if isinstance(value, (pd.Timestamp, datetime.datetime)):
        ts = pd.Timestamp(value)
        if (ts.hour, ts.minute, ts.second) == (0, 0, 0):
            return ts.strftime('%Y-%m-%d'), True, None
        return ts.strftime('%Y-%m-%dT%H:%M' + (':%S' if ts.second else '')), True, 'local time without a time zone'
    if isinstance(value, datetime.date):
        return value.isoformat(), True, None
    if blank(value):
        return value, False, None
    text = str(value).strip()
    match = OFFSET_RE.match(text)
    if match:
        local, hours, minutes = match.groups()
        sign = -1 if hours.startswith('-') else 1
        offset = datetime.timedelta(hours=abs(int(hours)), minutes=int(minutes)) * sign
        utc = datetime.datetime.fromisoformat(local.split('.')[0]) - offset
        return utc.strftime('%Y-%m-%dT%H:%M' + (':%S' if utc.second else '') + 'Z'), True, None
    return text, False, None


def associated_blank(value):
    return upstream_bs._associated_sequences_is_blank('' if value is None else value)


def prepare_common(sheets, args):
    """Steps shared by both modes. Returns a list of notes for the config header."""
    notes = []
    sm = Sheet(sheets['sampleMetadata'])
    erm = Sheet(sheets['experimentRunMetadata'])

    if sm.col('samp_name') is None:
        fail("sampleMetadata has no 'samp_name' field (field names are expected on row 3).")
    names = [sm.df.at[i, sm.col('samp_name')] for i in sm.data_index()]
    keep = [not blank(n) for n in names]
    if not all(keep):
        info(f"ignored {keep.count(False)} sampleMetadata row(s) with no samp_name")
        sm.drop_rows(keep)
    if len(sm.df) <= 3:
        fail("sampleMetadata has no samples (no samp_name values below row 3).")

    # Organism: FAIRe has no organism term, so FAIRe-ator workbooks leave it out.
    org_col = sm.col('organism')
    if org_col is None:
        org_col = sm.add_column('organism')
    filled = 0
    for i in sm.data_index():
        if blank(sm.df.at[i, org_col]):
            sm.df.at[i, org_col] = args.organism
            filled += 1
    if filled:
        info(f"set organism to '{args.organism}' for {filled} sample(s) with no organism")
        notes.append(f"organism set to '{args.organism}' for {filled} sample(s)")

    sheets['sampleMetadata'] = sm.df
    sheets['experimentRunMetadata'] = erm.df
    return notes


def prepare_biosample(sheets, args):
    notes = prepare_common(sheets, args)
    sm = Sheet(sheets['sampleMetadata'])
    erm = Sheet(sheets['experimentRunMetadata'])
    samp_col = sm.col('samp_name')

    if args.associated == 'blank_only':
        for needed in ('samp_name', 'associatedSequences'):
            if erm.col(needed) is None:
                fail(f"experimentRunMetadata has no '{needed}' field, so samples cannot be filtered by associatedSequences.")
        submitted = set()
        has_runs = set()
        for i in erm.data_index():
            name = erm.df.at[i, erm.col('samp_name')]
            if blank(name):
                continue
            has_runs.add(str(name).strip())
            if not associated_blank(erm.df.at[i, erm.col('associatedSequences')]):
                submitted.add(str(name).strip())
        names = [str(sm.df.at[i, samp_col]).strip() for i in sm.data_index()]
        keep = [n in has_runs and n not in submitted for n in names]
        if not any(keep):
            fail("every sample already has associatedSequences in experimentRunMetadata (or has no runs), "
                 "so there are no new BioSamples to register.")
        dropped = [n for n, k in zip(names, keep) if not k]
        info(f"kept {keep.count(True)} sample(s) with no associatedSequences; left out {len(dropped)}: "
             + ', '.join(dropped[:10]) + (' ...' if len(dropped) > 10 else ''))
        notes.append(f"left out {len(dropped)} sample(s) that already have associatedSequences or no runs")
        sm.drop_rows(keep)

    if args.convert_dates and sm.col('eventDate') is not None:
        col = sm.col('eventDate')
        changed, local = 0, []
        for i in sm.data_index():
            value, did, note = ncbi_date(sm.df.at[i, col])
            sm.df.at[i, col] = value
            changed += did
            if note:
                local.append(str(sm.df.at[i, samp_col]))
        info(f"converted {changed} eventDate value(s) to a form NCBI accepts")
        if changed:
            notes.append(f"converted {changed} eventDate value(s) for NCBI (time zone offsets to UTC)")
        if local:
            warn("these eventDate values have a time but no time zone; NCBI expects UTC: " + ', '.join(local[:10]))
        odd = sorted({str(sm.df.at[i, col]) for i in sm.data_index()
                      if not blank(sm.df.at[i, col]) and not is_missing_term(sm.df.at[i, col])
                      and not NCBI_DATE_RE.match(str(sm.df.at[i, col]))})
        if odd:
            warn("these eventDate values are not in a date format NCBI lists (for example 2021-09-14 "
                 "or 2021-09-14T15:00Z): " + ', '.join(odd[:10]) + (' ...' if len(odd) > 10 else ''))
    elif sm.col('eventDate') is not None:
        col = sm.col('eventDate')
        for i in sm.data_index():
            value = sm.df.at[i, col]
            if not blank(value):
                sm.df.at[i, col] = str(value)

    # Mandatory fields
    problems = []
    for field, sources in MANDATORY_SOURCES.items():
        for source in sources:
            col = sm.col(source)
            if col is None:
                problems.append((field, source, 'all samples (field not in sampleMetadata)'))
                continue
            empty = [str(sm.df.at[i, samp_col]) for i in sm.data_index() if blank(sm.df.at[i, col])]
            if empty:
                problems.append((field, source, ', '.join(empty[:5]) + (' ...' if len(empty) > 5 else '')))
                if args.mandatory_fill != 'stop':
                    for i in sm.data_index():
                        if blank(sm.df.at[i, col]):
                            sm.df.at[i, col] = args.mandatory_fill
    if problems and args.mandatory_fill == 'stop':
        lines = ["these mandatory BioSample fields are empty:"]
        lines += [f"  - {field} (FAIRe term {source}): {where}" for field, source, where in problems]
        lines.append("Fill them in sampleMetadata, or choose a missing-value term under "
                     "'Empty mandatory fields' on the tool form.")
        fail('\n'.join(lines))
    if problems:
        info(f"filled empty mandatory fields with '{args.mandatory_fill}': "
             + '; '.join(f"{f} ({s})" for f, s, _ in problems))
        notes.append(f"empty mandatory fields filled with '{args.mandatory_fill}'")

    if args.duplicates_column and sm.col(args.duplicates_column) is None:
        fail(f"sampleMetadata has no '{args.duplicates_column}' field to tell samples apart.")

    sheets['sampleMetadata'] = sm.df
    return notes


def clean_instrument(value):
    """'Illumina MiSeq [OBI_0002003]' -> 'Illumina MiSeq'."""
    if blank(value):
        return value
    return re.sub(r'\s*\[[A-Za-z]+[_:]\d+\]\s*$', '', str(value).strip())


def prepare_sra(sheets, args):
    notes = prepare_common(sheets, args)
    erm = Sheet(sheets['experimentRunMetadata'])
    pm = sheets['projectMetadata']

    for needed in ('samp_name', 'assay_name', 'lib_id', 'filename'):
        if erm.col(needed) is None:
            fail(f"experimentRunMetadata has no '{needed}' field (field names are expected on row 3).")

    # Runs to include
    if args.runs_by != 'all':
        column = {'assay': 'assay_name', 'seq_run': 'seq_run_id', 'lib_id': 'lib_id'}[args.runs_by]
        if erm.col(column) is None:
            fail(f"experimentRunMetadata has no '{column}' field.")
        wanted = split_list(args.runs_values)
        if not wanted:
            fail(f"give at least one {column} value.")
        values = [None if blank(erm.df.at[i, erm.col(column)]) else str(erm.df.at[i, erm.col(column)]).strip()
                  for i in erm.data_index()]
        available = list(dict.fromkeys(v for v in values if v))
        unknown = [w for w in wanted if w not in available]
        if unknown:
            fail(f"no runs with {column} " + ', '.join(f"'{u}'" for u in unknown)
                 + f". Values in the workbook: {', '.join(available[:20])}" + (' ...' if len(available) > 20 else ''))
        keep = [v in wanted for v in values]
        info(f"kept {keep.count(True)} run(s) with {column} in: {', '.join(wanted)}")
        notes.append(f"kept {keep.count(True)} run(s) with {column} in: {', '.join(wanted)}")
        erm.drop_rows(keep)

    if args.associated == 'blank_only':
        if erm.col('associatedSequences') is None:
            fail("experimentRunMetadata has no 'associatedSequences' field, so runs cannot be filtered by it.")
        keep = [associated_blank(erm.df.at[i, erm.col('associatedSequences')]) for i in erm.data_index()]
        if not any(keep):
            fail("every selected run already has associatedSequences, so there are no new runs to submit.")
        info(f"kept {keep.count(True)} run(s) with no associatedSequences; left out {keep.count(False)}")
        notes.append(f"left out {keep.count(False)} run(s) that already have associatedSequences")
        erm.drop_rows(keep)

    lib_ids = [erm.df.at[i, erm.col('lib_id')] for i in erm.data_index()]
    if not any(not blank(v) for v in lib_ids):
        fail("no runs left to convert (no lib_id values).")

    # Platform and instrument
    headers = [None if blank(v) else str(v).strip() for v in pm.iloc[0]]
    term_col = pm.columns[headers.index('term_name')]
    first_value_col = headers.index('project_level')
    terms = pm[term_col].astype(str).str.strip()
    platform_rows = pm.index[terms == 'platform']
    instrument_rows = pm.index[terms.isin(['instrument', 'instrument_model'])]
    value_cols = pm.columns[first_value_col:]

    if args.instrument_model:
        platform = INSTRUMENT_PLATFORM[args.instrument_model]
        if len(platform_rows) == 0 or len(instrument_rows) == 0:
            fail("projectMetadata needs 'platform' and 'instrument' rows (term_name column).")
        for c in value_cols:
            pm.at[platform_rows[0], c] = platform
            pm.at[instrument_rows[0], c] = args.instrument_model
        if erm.col('instrument') is not None:
            for i in erm.data_index():
                erm.df.at[i, erm.col('instrument')] = args.instrument_model
        info(f"set platform '{platform}' and instrument_model '{args.instrument_model}' for all runs")
        notes.append(f"platform {platform} and instrument_model {args.instrument_model} set for all runs")
    else:
        changed = 0
        for r in instrument_rows:
            for c in value_cols:
                new = clean_instrument(pm.at[r, c])
                changed += new != pm.at[r, c]
                pm.at[r, c] = new
        if erm.col('instrument') is not None:
            for i in erm.data_index():
                new = clean_instrument(erm.df.at[i, erm.col('instrument')])
                changed += new != erm.df.at[i, erm.col('instrument')]
                erm.df.at[i, erm.col('instrument')] = new
        if changed:
            info(f"removed ontology codes such as [OBI_0002003] from {changed} instrument value(s)")
            notes.append(f"removed ontology codes from {changed} instrument value(s)")

    sheets['experimentRunMetadata'] = erm.df
    sheets['projectMetadata'] = pm
    return notes


# --------------------------------------------------------------- answering prompts

class Answerer:
    """Answers the upstream questions, records them, and stops on anything unexpected."""

    def __init__(self, static, dynamic, tee):
        self.static = static
        self.dynamic = dynamic
        self.tee = tee
        self.record = {}
        self.counts = collections.Counter()
        self.last_prompt = None

    def wrap(self, module):
        original = module.get_config_value

        def get_config_value(config, key, prompt_func, question, use_config_file, *args, **kwargs):
            self.counts[question] += 1
            if self.counts[question] > MAX_REPEATS:
                raise Stop(f"FAIRe2NCBI rejected the answer '{self.record.get(key, '')}' to this question "
                           f"{MAX_REPEATS} times and would loop for ever:\n  {question.strip()}")
            if key in self.static:
                answer = self.static[key]
            else:
                answer = self.dynamic(key, question)
            if answer is not None:
                print(f"{question.strip()} {answer}")
                module.add_qa(config, question, answer, use_config_file)
                if key:
                    config[key] = answer
                self.record[key] = answer
                return answer
            value = original(config, key, prompt_func, question, use_config_file, *args, **kwargs)
            self.record[key] = value
            return value

        module.get_config_value = get_config_value

    def input(self, prompt=''):
        self.last_prompt = prompt
        try:
            return self.original_input(prompt)
        except EOFError:
            raise Stop("FAIRe2NCBI asked a question that this Galaxy tool does not answer:\n  "
                       + ' '.join(str(prompt).split())
                       + "\nThe workbook may have something the tool does not expect. The log shows what "
                         "FAIRe2NCBI was doing. Please report it to the tool maintainers.") from None

    def install(self):
        self.original_input = builtins.input
        builtins.input = self.input
        self.wrap(upstream_bs)
        self.wrap(upstream_sra)

    def recent_groups(self):
        return [line.strip() for line in self.tee.after(r'Sample names for all duplicate rows')
                if re.match(r'^\s+Group \d+: \[', line)]


def insdc_tokens():
    """Upstream ignores 'not applicable', 'missing' ... when deciding whether a
    column is numeric, but not the INSDC forms with a reason, such as
    'not applicable: control sample'. One such value makes the whole column
    non-numeric, so no units are added. Extend the set used by the check."""
    base = upstream_bs._MISSING_VALUE_TOKENS

    class Tokens(frozenset):
        def __contains__(self, item):
            return frozenset.__contains__(self, item) or str(item).startswith(
                tuple(t + ':' for t in INSDC_MISSING))

    return Tokens(base)


def _degrees(x):
    s = repr(abs(float(x)))
    if 'e' in s:
        s = f'{abs(float(x)):.8f}'.rstrip('0').rstrip('.')
    return s


def format_lat_lon(lat, lon):
    """'40.57773667 S 148.7301917 E': the decimal places given, as NCBI accepts."""
    return f"{_degrees(lat)} {'S' if lat < 0 else 'N'} {_degrees(lon)} {'W' if lon < 0 else 'E'}"


def patch_upstream():
    """Read FAIRe sheets with each cell's own type, and keep the precision of lat_lon."""
    original = upstream_bs._read_faire_sheet_df

    def read_sheet(faire_path, sheet_name, header=0, keep_default_na=True):
        df = original(faire_path, sheet_name, header=header, keep_default_na=keep_default_na)
        if df is None or str(faire_path).lower().endswith('.tsv'):
            return df
        try:
            typed = pd.read_excel(faire_path, sheet_name=sheet_name, header=header,
                                  keep_default_na=keep_default_na, dtype=object, engine='openpyxl')
        except Exception:
            return df
        return typed if typed.shape == df.shape and list(typed.columns) == list(df.columns) else df
    upstream_bs._read_faire_sheet_df = read_sheet
    upstream_bs.format_lat_lon = format_lat_lon


def run_upstream(argv, answerer, expected_output):
    sys.argv = ['FAIRe2NCBI.py'] + argv
    patch_upstream()
    answerer.install()
    try:
        upstream_main.main()
    except Stop as err:
        fail(str(err))
    if not os.path.exists(expected_output) or os.path.getsize(expected_output) == 0:
        messages = [line.strip() for line in answerer.tee.recent()
                    if re.match(r'^\s*(Error|Aborted|Warning)', line)]
        fail("FAIRe2NCBI finished without writing its output."
             + ("\nIts last messages were:\n  " + '\n  '.join(messages[-5:]) if messages else ''))


def write_config(record, notes, mode, path):
    header = [
        f"# FAIRe2NCBI {mode} answers used by the Galaxy tool.",
        "# Rerun locally with:",
        f"#   python scripts/FAIRe2NCBI.py {mode} --FAIReMetadata WORKBOOK.xlsx "
        + ("--BioSample_Metadata out.tsv" if mode == 'BioSample' else "--SRA_Metadata out.tsv")
        + " --config_file THIS_FILE.yaml --force",
        "# Empty answers ('') make FAIRe2NCBI ask the question again.",
    ]
    if notes:
        header.append("# Before running FAIRe2NCBI, the Galaxy tool did the following:")
        header += [f"#   - {n}" for n in notes]
        header.append("# Make the same changes to your workbook for a local rerun to give the same result.")
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(header) + '\n')
        yaml.safe_dump({k: v for k, v in record.items() if k}, f, sort_keys=False, allow_unicode=True,
                       default_flow_style=False)


# --------------------------------------------------------------- BioSample

def template_columns():
    with open(upstream_bs.DEFAULT_BIOSAMPLE_TEMPLATE, encoding='utf-8') as f:
        return f.readlines()[11].rstrip('\n').split('\t')


def run_biosample(args, tee):
    normalise_faire.normalise(args.input_file, 'normalised.xlsx')
    sheets = read_prepared('normalised.xlsx')
    notes = prepare_biosample(sheets, args)
    write_workbook(sheets, 'prepared.xlsx')
    sm_fields = set(Sheet(sheets['sampleMetadata']).fields)
    upstream_bs._MISSING_VALUE_TOKENS = insdc_tokens()
    notes.append("treated missing-value terms with a reason, such as 'not applicable: control sample', as "
                 "missing when adding units (FAIRe2NCBI on its own adds no units to a field that has one)")

    columns = template_columns()
    title_cols = []
    if args.sample_title == 'custom':
        for name in split_list(args.title_columns):
            match = [c for c in columns if c == name or c.lstrip('*') == name.lstrip('*')]
            if not match:
                fail(f"'{name}' is not a BioSample template column. Use names such as "
                     "*sample_name, *geo_loc_name, *collection_date or *depth.")
            title_cols.append(match[0])
        if not title_cols:
            fail("give the BioSample columns to build sample_title from.")

    static = {
        'bioproject_manual_entry': 'y' if args.bioproject else 'n',
        'add_sample_title': 'n' if args.sample_title == 'none' else 'y',
        'use_default_sample_title_columns': 'n' if args.sample_title == 'custom' else 'y',
        'custom_sample_title_columns': ','.join(title_cols),
        'add_all_additional_columns': 'y' if args.extra_columns == 'all' else 'n',
        'filter_experiment_run_blank_associatedSequences': 'all',
    }
    if args.bioproject:
        static.update({'bioproject_same_for_all': 'y', 'bioproject_single_value': args.bioproject})

    def dynamic(key, question):
        if key.startswith('use_mixs_preferred_unit_'):
            return 'y' if args.mixs_units else 'n'
        if key.startswith('unit_for_'):
            return ''
        if key.startswith('mandatory_field_'):
            if args.mandatory_fill == 'stop':
                raise Stop(f"the mandatory BioSample field {key[len('mandatory_field_'):]} is empty for every sample. "
                           "Choose a missing-value term under 'Empty mandatory fields'.")
            return args.mandatory_fill
        if key in ('duplicate_resolution_field', 'duplicate_fallback_column'):
            if not args.duplicates_column:
                unique = list(tee.numbered(r'fields with 100% unique values'))
                raise Stop("some samples have identical BioSample attributes apart from sample_name, "
                           "sample_title and description, and NCBI will not register them:\n  "
                           + '\n  '.join(answerer.recent_groups())
                           + "\nChoose a sampleMetadata field that tells them apart (for example a replicate "
                             "number or extract ID) under 'Field that tells apart samples with identical "
                             "attributes'."
                           + (f"\nFields with a different value for every sample: {', '.join(unique[:15])}"
                              if unique else ''))
            return args.duplicates_column
        if key.startswith('rename_duplicate_field'):
            return 'n'
        if key in ('add_column_to_resolve_duplicates', 'continue_despite_duplicates'):
            raise Stop(f"some samples still have identical attributes after adding '{args.duplicates_column}':\n  "
                       + '\n  '.join(answerer.recent_groups())
                       + "\nChoose a field with a different value for each of these samples.")
        if key == 'excluded_additional_columns':
            listed = tee.numbered(r'^Found \d+ additional columns')
            if args.extra_columns == 'none':
                return ','.join(listed.values())
            wanted = split_list(args.exclude_columns)
            absent = [w for w in wanted if w not in sm_fields]
            if absent:
                raise Stop(f"sampleMetadata has no field {', '.join(absent)} to leave out. "
                           f"Extra fields that would be added: {', '.join(listed)}")
            skipped = [w for w in wanted if w not in listed]
            if skipped:
                info(f"not an extra field (empty for every sample, or already a BioSample attribute), "
                     f"so nothing to leave out: {', '.join(skipped)}")
            chosen = [listed[w] for w in wanted if w in listed]
            return ','.join(chosen) if chosen else 'none'
        return None

    answerer = Answerer(static, dynamic, tee)
    with open('answers.yaml', 'w', encoding='utf-8') as f:
        yaml.safe_dump(static, f, sort_keys=False)
    output = os.path.abspath('biosample.tsv')
    run_upstream(['BioSample', '--FAIReMetadata', 'prepared.xlsx', '--BioSample_Metadata', output,
                  '--config_file', 'answers.yaml', '--force'], answerer, output)

    table = pd.read_csv(output, sep='\t', skiprows=11, dtype=str, keep_default_na=False)
    if args.extra_columns == 'none':
        extra = [c for c in table.columns if c not in columns and c != args.duplicates_column]
        if extra:
            fail(f"extra columns were added although none were asked for: {', '.join(extra)}")
    if os.path.abspath(args.output) != output:   # the same file when run by hand with --output biosample.tsv
        with open(output, encoding='utf-8') as src, open(args.output, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
    write_config(answerer.record, notes, 'BioSample', args.config_out)
    info(f"wrote {len(table)} BioSample(s) with {len(table.columns)} columns")


# --------------------------------------------------------------- SRA

# Fields that must agree for the SRA rows of one library to be joined.
SRA_SAME = ('biosample_accession', 'library_strategy', 'library_source', 'library_selection', 'library_layout',
            'platform', 'instrument_model', 'filetype', 'filename', 'filename2', 'filename3', 'filename4',
            'assembly', 'fasta_file')
FILE_FIELDS = ('filename', 'filename2', 'filename3', 'filename4')


def join_titles(titles):
    """'M1: Fish16S metabarcoding of ...' and 'M1: COILeray metabarcoding of ...' ->
    ('M1: Fish16S and COILeray metabarcoding of ...', ['Fish16S', 'COILeray']). The parts that differ
    are taken whole, cut at spaces (assay names have none); if there are none, the titles are joined
    with ' | '."""
    titles = list(dict.fromkeys(titles))
    if len(titles) == 1:
        return titles[0], None
    pre = os.path.commonprefix(titles)
    suf = os.path.commonprefix([t[::-1] for t in titles])[::-1]
    m = re.match(r'^.*\s', pre, re.S)
    pre = m.group(0) if m else ''
    m = re.search(r'\s.*$', suf, re.S)
    suf = m.group(0) if m else ''
    shortest = min(len(t) for t in titles)
    names = [t[len(pre):len(t) - len(suf)].strip() for t in titles]
    if len(pre) + len(suf) > shortest or not all(names):
        return ' | '.join(titles), None
    joined = names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' and ' + names[-1]
    return pre + joined + suf, names


def library_name(lib, pairs):
    """The lab's name for a library, from a lib_id made as the FAIRe mapper makes it (the library
    name, assay_name and seq_run_id, as FAIRe takes a library to be one amplicon of a sample):
    M097_16SFish_LerayCOI_Fish16S_AGRF_2024-12 -> (M097_16SFish_LerayCOI, AGRF_2024-12). pairs are
    the (assay_name, seq_run_id) of the lib_id's rows. A lib_id that does not end with its assay is
    returned as it is. The second value is the run taken off, if any."""
    lib = str(lib).strip()
    for assay, run in pairs:
        if assay and run and lib.endswith(f'_{assay}_{run}') and len(lib) > len(assay) + len(run) + 2:
            return lib[:-len(assay) - len(run) - 2], run
        if assay and lib.endswith(f'_{assay}') and len(lib) > len(assay) + 1:
            return lib[:-len(assay) - 1], ''
    return lib, ''


def join_shared_libraries(table, lib_info):
    """One SRA row for each library: rows of one sample with the same files (the amplicons of a
    library that holds several assays) are joined, with a title and design description naming each
    assay. library_ID is the library's own name, the lib_id without its assay and run, with the run
    (then the whole lib_id) kept where names would repeat, as for a library sequenced in several
    runs. lib_info: {lib_id: {'samps': set, 'pairs': [(assay_name, seq_run_id)]}}. Returns the
    table, the number of libraries joined, the assay names seen, any problems (rows that share
    files but differ in another field), the library_IDs of those rows, and notes for the log."""
    keep, problems, joined, assays, bad, one_id = [], [], 0, [], set(), set()
    info_of = lambda lib: lib_info.get(str(lib).strip(), {'samps': set(), 'pairs': []})  # noqa: E731

    def key(r):
        files = tuple(r.get(c, '') for c in FILE_FIELDS)
        samps = sorted(info_of(r['library_ID'])['samps'])
        return ('files', samps[0] if samps else '', files) if files[0] else ('lib', r['library_ID'])
    table = table.copy()
    table['_key'] = [key(r) for _, r in table.iterrows()]
    table['_first'] = table['library_ID']
    table['_samp'] = [(sorted(info_of(lib)['samps']) or [''])[0] for lib in table['library_ID']]
    for _, rows in table.groupby('_key', sort=False):
        rows = rows.copy()
        names = [library_name(lib, info_of(lib)['pairs']) for lib in rows['library_ID']]
        rows['_orig'] = list(rows['library_ID'])
        rows['_name'] = [n for n, _ in names]
        rows['_run'] = [r for _, r in names]
        if len(rows) == 1:
            keep.append(rows)
            continue
        differ = [c for c in SRA_SAME if c in rows and rows[c].nunique() > 1]
        if differ:
            problems.append(f"library {rows['library_ID'].iloc[0]} has several rows with the same files, but they "
                            "differ in " + ', '.join(differ))
            bad.update(rows['library_ID'])
            keep.append(rows)
            continue
        if rows['library_ID'].nunique() == 1:
            one_id.add(rows['library_ID'].iloc[0])
        first = rows.iloc[[0]].copy()
        title, names = join_titles(list(rows['title']))
        first['title'] = title
        descs = list(rows['design_description'])
        if names and len(names) == len(descs):
            first['design_description'] = (f"{len(names)} assays in one library. "
                                           + '; '.join(f"{n}: {d}" for n, d in zip(names, descs)))
            assays += [n for n in names if n not in assays]
        else:
            first['design_description'] = '; '.join(dict.fromkeys(descs))
        common = list(dict.fromkeys(rows['_name']))
        first['_name'] = common[0] if len(common) == 1 else (
            re.sub(r'_[^_]*$', '', os.path.commonprefix(common)) or common[0])
        first['_orig'] = first['_name'].iloc[0] + ('_' + first['_run'].iloc[0] if first['_run'].iloc[0] else '')
        keep.append(first)
        joined += 1
    out = pd.concat(keep, ignore_index=True)
    # The library's own name; where that repeats for different lib_ids, the run, then the lib_id.
    level = [0] * len(out)
    for _ in range(2):
        ids = [n if lv == 0 else (f'{n}_{r}' if r else o) if lv == 1 else o
               for n, r, o, lv in zip(out['_name'], out['_run'], out['_orig'], level)]
        seen = collections.defaultdict(set)
        for i, o in zip(ids, out['_orig']):
            seen[i].add(o)
        level = [lv + 1 if len(seen[i]) > 1 and lv < 2 else lv for i, lv in zip(ids, level)]
    out['library_ID'] = [n if lv == 0 else (f'{n}_{r}' if r else o) if lv == 1 else o
                         for n, r, o, lv in zip(out['_name'], out['_run'], out['_orig'], level)]
    bad = {i for i, o in zip(out['library_ID'], out['_first']) if o in bad}
    notes = []
    changed = [(o, i) for o, i in zip(out['_first'], out['library_ID']) if o != i]
    if changed:
        notes.append(f"library_ID is each library's own name: the lib_id without its assay_name and seq_run_id "
                     f"(e.g. {changed[0][0]} -> {changed[0][1]})")
    kept_run = sum(lv > 0 for lv in level)
    if kept_run:
        notes.append(f"{kept_run} libraries keep the run or assay in library_ID, so that each is unique")
    if one_id:
        notes.append(f"{len(one_id)} lib_id{' names' if len(one_id) == 1 else 's name'} several assays (e.g. "
                     f"{sorted(one_id)[0]}); FAIRe takes a library to be one amplicon of a sample, so each assay's "
                     "row should have its own lib_id (the FAIRe mapper adds assay_name and seq_run_id to the "
                     "library name)")
    return out.drop(columns=['_key', '_orig', '_name', '_run', '_first']), joined, assays, problems, bad, notes


def run_sra(args, tee):
    normalise_faire.normalise(args.input_file, 'normalised.xlsx')
    sheets = read_prepared('normalised.xlsx')
    notes = prepare_sra(sheets, args)
    write_workbook(sheets, 'prepared.xlsx')

    static = {
        'bioproject_strategy': 'combined',
        'lib_id_selection_choice': 'all',
        'filter_experiment_run_blank_associatedSequences': 'all',
        'library_field_library_strategy_choice': 'DEFAULT',
        'library_field_library_source_choice': 'DEFAULT',
        'library_field_library_selection_choice': 'DEFAULT',
        'instrument_missing_libid_fill_choice': 'n',
    }
    advice = "Choose the sequencing instrument on the tool form."

    def dynamic(key, question):
        if key.startswith(('platform_choice_', 'instrument_model_choice_')):
            return 'assay'
        if key == 'platform_value_input':
            raise Stop("projectMetadata gives no platform for one or more assays. " + advice)
        if key.startswith('instrument_model_manual_'):
            raise Stop(f"projectMetadata gives no instrument for assay '{key[len('instrument_model_manual_'):]}'. "
                       + advice)
        if key.startswith(('platform_validation_', 'instrument_model_validation_')):
            kind = 'platform' if key.startswith('platform') else 'instrument'
            value = re.search(r"keep '(.*)'\)", question)
            raise Stop(f"the {kind} '{value.group(1) if value else ''}' in the workbook is not one of NCBI's "
                       f"values. {advice}")
        return None

    argv = ['SRA', '--FAIReMetadata', 'prepared.xlsx', '--SRA_Metadata', os.path.abspath('sra.tsv'),
            '--config_file', 'answers.yaml', '--force']
    if args.accessions:
        os.symlink(os.path.abspath(args.accessions), 'accessions.tsv')
        argv += ['--NCBI_accession_number', 'accessions.tsv']
    answerer = Answerer(static, dynamic, tee)
    with open('answers.yaml', 'w', encoding='utf-8') as f:
        yaml.safe_dump(static, f, sort_keys=False)
    run_upstream(argv, answerer, os.path.abspath('sra.tsv'))

    table = pd.read_csv('sra.tsv', sep='\t', dtype=str, keep_default_na=False)
    erm = Sheet(sheets['experimentRunMetadata'])
    lib_info = {}
    run_col = erm.col('seq_run_id')
    for i in erm.data_index():
        lib, samp = erm.df.at[i, erm.col('lib_id')], erm.df.at[i, erm.col('samp_name')]
        if not blank(lib):
            entry = lib_info.setdefault(str(lib).strip(), {'samps': set(), 'pairs': []})
            entry['samps'].add(str(samp).strip())
            assay = erm.df.at[i, erm.col('assay_name')]
            run = erm.df.at[i, run_col] if run_col is not None else None
            entry['pairs'].append(('' if blank(assay) else str(assay).strip(), '' if blank(run) else str(run).strip()))
    table, joined, assays, problems, bad, join_notes = join_shared_libraries(table, lib_info)
    if joined:
        what = f" ({' and '.join(assays)})" if assays else ''
        info(f"joined the rows of {joined} libraries that hold several assays{what}: one row each, with the "
             "title and design description naming every assay")
        notes.append(f"joined the rows of {joined} libraries that hold several assays{what}")
    for note in join_notes:
        info(note)
        notes.append(note)
    dupes = sorted(set(table['library_ID'][table['library_ID'].duplicated()]) - bad)
    if dupes:
        problems.append("these library_ID values appear more than once: " + ', '.join(dupes[:5])
                        + (' ...' if len(dupes) > 5 else '')
                        + ". NCBI needs a unique library_ID for each row. FAIRe takes a library to be one amplicon "
                          "of a sample, so give each row of experimentRunMetadata its own lib_id (the FAIRe mapper "
                          "adds assay_name and seq_run_id to the library name), or run the tool once per assay "
                          "(Runs to include: assays).")
    files = [f for c in ('filename', 'filename2', 'filename3', 'filename4') if c in table for f in table[c] if f]
    dup_files = sorted({f for f in files if files.count(f) > 1})
    if dup_files:
        problems.append("these file names appear more than once: " + ', '.join(dup_files[:5]))
    no_file = table['library_ID'][table['filename'] == ''].tolist()
    if no_file:
        problems.append("these libraries have no file name: " + ', '.join(no_file[:5]))
    if problems:
        fail("the SRA table needs fixing before NCBI will accept it:\n  " + '\n  '.join(problems))

    if args.accessions:
        missing = table['library_ID'][table['biosample_accession'] == ''].tolist()
        if missing:
            fail(f"{len(missing)} librar{'y has' if len(missing) == 1 else 'ies have'} no BioSample accession in "
                 "the accession table (matched on samp_name = sample_name): " + ', '.join(missing[:10]))
        info(f"added BioSample accessions to all {len(table)} rows")
    else:
        table.insert(0, 'sample_name', table['_samp'])
        if (table['sample_name'] == '').any():
            fail("some libraries could not be matched to a samp_name.")
        table = table.drop(columns=['biosample_accession'])
        info("added a sample_name column to link each run to its BioSample, and removed the empty "
             "biosample_accession column")
    table.drop(columns=['_samp']).to_csv(args.output, sep='\t', index=False)
    write_config(answerer.record, notes, 'SRA', args.config_out)
    info(f"wrote {len(table)} SRA row(s) for {table['library_ID'].nunique()} libraries")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='mode', required=True)
    for name in ('biosample', 'sra'):
        p = sub.add_parser(name)
        p.add_argument('--input_file', required=True)
        p.add_argument('--output', required=True)
        p.add_argument('--config_out', required=True)
        p.add_argument('--organism', default='marine metagenome')
        p.add_argument('--associated', choices=['all', 'blank_only'], default='all')
    b = sub.choices['biosample']
    b.add_argument('--bioproject', default='')
    b.add_argument('--mandatory_fill', default='stop')
    b.add_argument('--no_date_conversion', dest='convert_dates', action='store_false')
    b.add_argument('--no_mixs_units', dest='mixs_units', action='store_false')
    b.add_argument('--sample_title', choices=['none', 'default', 'custom'], default='default')
    b.add_argument('--title_columns', default='')
    b.add_argument('--extra_columns', choices=['all', 'none', 'except'], default='all')
    b.add_argument('--exclude_columns', default='')
    b.add_argument('--duplicates_column', default='')
    s = sub.choices['sra']
    s.add_argument('--runs_by', choices=['all', 'assay', 'seq_run', 'lib_id'], default='all')
    s.add_argument('--runs_values', default='')
    s.add_argument('--instrument_model', default='')
    s.add_argument('--accessions')
    args = parser.parse_args()

    if getattr(args, 'instrument_model', '') and args.instrument_model not in INSTRUMENT_PLATFORM:
        fail(f"'{args.instrument_model}' is not an NCBI instrument_model.")
    if getattr(args, 'mandatory_fill', 'stop') != 'stop' and not args.mandatory_fill.strip():
        fail("give a value for empty mandatory fields.")

    tee = Tee(sys.stdout)
    sys.stdout = tee
    try:
        if args.mode == 'biosample':
            run_biosample(args, tee)
        else:
            run_sra(args, tee)
    finally:
        sys.stdout = tee.stream
        sys.stdout.flush()


if __name__ == '__main__':
    main()
