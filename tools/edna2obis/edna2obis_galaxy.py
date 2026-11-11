"""Galaxy driver for edna2obis.

Runs the upstream edna2obis code (main.py and src-v3/, copied unchanged) from a
Galaxy job. Two subcommands:

  match  Look up the taxonomy strings of each assay's taxonomy table in WoRMS or
         GBIF, using the pipeline's own taxonomy step (assign_taxonomy,
         create_taxa_assignment_info and the selected-match marking). Writes the
         taxa_mapping_INFO table with an added assay_name column. Needs internet.

  build  Run the full edna2obis pipeline (main.main) on a FAIRe workbook and the
         per-assay tables. The taxonomy comes either from a reviewed mapping
         table (no internet needed) or from WoRMS or GBIF.

The driver does not change any upstream file. It:

  * prepares a copy of the workbook (assay columns relabelled with
    normalise_faire.py; analysisMetadata sheets not used in the run dropped;
    cell values kept as upstream reads them, so text such as NA stays)
    and copies of the tables with their field names on the first row;
  * writes upstream's config.yaml (and EML and contacts files) from the form,
    in a working folder, because upstream reads them from the current folder;
  * replaces upstream's banner, colour console and browser opening;
  * with a mapping table, replaces the two functions that would call the WoRMS
    or GBIF API (get_worms_match_for_dataframe, get_gbif_match_for_dataframe)
    with one that takes each name's selected row from the table, and blocks
    any other API call;
  * without a mapping table, checks that the API can be reached before
    starting, and records every failed API request, because upstream turns
    failed requests into 'incertae sedis' without saying so;
  * stops with a plain message (not a traceback) when upstream reports an
    error or a requested output is missing, and zips the archive files.
"""

import argparse
import collections
import datetime
import functools
import html
import json
import logging
import os
import re
import shutil
import sys
import types
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src-v3')
sys.dont_write_bytecode = True  # tool directories are often read-only on Galaxy servers
for p in (SRC, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd  # noqa: E402
import yaml  # noqa: E402

WORK = 'e2o_work'           # upstream runs here (it reads config.yaml etc. from the current folder)
RUN_NAME = 'galaxy'         # edna2obis_run_name; outputs go to processed/galaxy/
OUT_DIR = 'processed'
API_FAILURES = 'api_failures.log'
# feature ID field names, compared without '#', '_', '-' and spaces
FEATURE_ID_NAMES = {'featureid', 'seqid', 'sequenceid', 'otuid', 'asvid', 'otu', 'asv'}
TRUE_WORDS = {'true', '1', 'yes', 'y', 't'}
FALSE_WORDS = {'false', '0', 'no', 'n', 'f', ''}
WORMS_FIELDS = ['scientificName', 'scientificNameID', 'taxonRank', 'nameAccordingTo', 'replaced_unaccepted',
                'unaccepted_match', 'environment', 'kingdom', 'phylum', 'class', 'order', 'family', 'genus',
                'species', 'higherClassification', 'match_type_debug', 'cleanedTaxonomy', 'assignment_score',
                'ranks_matched', 'ranks_provided']
GBIF_FIELDS = ['scientificName', 'taxonID', 'kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'taxonRank',
               'confidence', 'nameAccordingTo', 'match_type_debug', 'cleanedTaxonomy', 'environment',
               'higherClassification', 'replaced_unaccepted', 'unaccepted_match', 'assignment_score',
               'ranks_matched', 'ranks_provided']
API_HOSTS = {'WoRMS': 'www.marinespecies.org', 'GBIF': 'api.gbif.org'}
WORMS_REST = 'https://www.marinespecies.org/rest/'


class Stop(BaseException):
    """Stop the run with a message. BaseException, so that upstream
    'except Exception' blocks do not swallow it."""


def fail(message):
    sys.stdout.flush()
    sys.stderr.write(f"ERROR: {message}\n")
    sys.exit(1)


def info(message):
    print(f"INFO: {message}", flush=True)


def warn(message):
    print(f"WARNING: {message}", flush=True)


def blank(value):
    return value is None or (isinstance(value, float) and pd.isna(value)) or str(value).strip() == ''


def plain(text):
    """Report HTML to plain text for the log."""
    text = re.sub(r'<[^>]+>', ' ', str(text))
    return re.sub(r'\s+', ' ', html.unescape(text)).strip()


def listing(items, limit=10):
    items = list(items)
    shown = ', '.join(str(i) for i in items[:limit])
    return shown + (f' and {len(items) - limit} more' if len(items) > limit else '')


def split_list(text):
    return [v.strip() for v in str(text or '').split(',') if v.strip()]


# --------------------------------------------------------------- input tables

def is_xlsx(path, ext):
    with open(path, 'rb') as fh:
        return ext == 'xlsx' or fh.read(4) == b'PK\x03\x04'


def read_any(path, ext):
    """Read a Galaxy dataset as strings, one DataFrame per sheet. ext is the Galaxy datatype."""
    if is_xlsx(path, ext):
        return pd.read_excel(path, sheet_name=None, header=None, dtype=str)
    sep = ',' if ext == 'csv' else '\t'
    with open(path, 'rb') as fh:
        raw = fh.read()
    text = raw.decode('utf-8-sig', errors='replace').replace('\r\n', '\n').replace('\r', '\n')
    import csv
    import io
    rows = list(csv.reader(io.StringIO(text), delimiter=sep))
    width = max((len(r) for r in rows), default=0)
    rows = [r + [''] * (width - len(r)) for r in rows]
    return {'': pd.DataFrame(rows, dtype=str)}


def find_header_row(df, limit=10):
    """Index of the first row whose first cell is a feature ID column name."""
    for i in range(min(limit, len(df))):
        first = re.sub(r'[#_\s-]', '', str(df.iat[i, 0]).lower()) if df.shape[1] else ''
        if first in FEATURE_ID_NAMES:
            return i
    return None


def prepare_table(dataset, label, out_name):
    """Copy a taxonomy or abundance table to TSV with its field names on row 1.
    FAIRe templates have two rows ('# requirement_level_code', '# section')
    above the field names; spreadsheets may have other sheets."""
    path, ext = dataset['source_path'], dataset['ext']
    sheets = read_any(path, ext)
    chosen = None
    for name, df in sheets.items():
        if str(name).strip().lower() in ('drop-down values', 'readme', 'instructions'):
            continue
        row = find_header_row(df.fillna(''))
        if row is not None:
            chosen = (name, df.fillna(''), row)
            break
    if chosen is None:
        fail(f"{label}: no row starting with a feature ID field (seq_id, featureid, '#OTU ID' ...) in the "
             "first 10 rows" + (" of any sheet" if len(sheets) > 1 else "") + ". The first column must hold "
             "the ASV or OTU identifiers.")
    name, df, row = chosen
    header = [str(v).strip() for v in df.iloc[row]]
    body = df.iloc[row + 1:]
    unnamed = [i for i, h in enumerate(header) if not h and (body.iloc[:, i].astype(str).str.strip() != '').any()]
    if unnamed:
        warn(f"{label}: left out {len(unnamed)} column(s) with values but no field name")
    keep = [i for i, h in enumerate(header) if h]
    body = body.iloc[:, keep]
    # upstream's two readers know different feature ID names; both know 'featureid'
    body.columns = ['featureid'] + [header[i] for i in keep[1:]]
    body = body[body.iloc[:, 0].astype(str).str.strip() != '']
    if body.empty:
        fail(f"{label}: no rows below the field names.")
    if body.columns.duplicated().any():
        fail(f"{label}: repeated column names: {listing(sorted(set(body.columns[body.columns.duplicated()])))}")
    body.to_csv(out_name, sep='\t', index=False)
    where = f" (sheet '{name}')" if name else ''
    note = f", field names on row {row + 1}" if row else ''
    info(f"{label}: {len(body)} rows, {body.shape[1]} columns{where}{note}")
    return out_name


# ------------------------------------------------------------ upstream set-up

def setup_upstream():
    """Import upstream modules and replace the console banner, colours and browser opening."""
    logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(levelname)s: %(message)s', force=True)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)  # imported by pygbif; font cache messages
    from rich.console import Console
    import html_reporter
    import main as upstream_main
    console = Console(file=sys.stdout, color_system=None, force_terminal=False, force_interactive=False,
                      highlight=False, soft_wrap=True, emoji=False)
    upstream_main.console = console
    for name in ('print_header', 'print_usage', 'print_separator'):
        setattr(upstream_main, name, lambda *a, **k: None)
    html_reporter.HTMLReporter._open_in_browser = lambda self: None
    return upstream_main


def keep_values_as_written(workbook):
    """While upstream runs, replace two of its reads that change values (no file is changed):

      * the workbook's sheets are read without dtype, so a column of IDs written as text (001) becomes
        numbers (1): reads of the workbook get dtype=object, which keeps each cell's own type;
      * the occurrence table is written to a file and read back with pandas' defaults twice: by the
        taxonomy step (taxa_assignment_manager.py, occurrence.csv) and by main.py's final file check
        (final_output_validation), which writes a table again when it drops an empty column. Both turn
        001 into 1 and text such as NA into empty cells, so these reads get dtype=str, with only empty
        cells as empty. (main.py also reads the occurrence core back to remove match_type_debug, when
        that column is there; that read is treated the same way.)

    Returns a function to call after the run, which puts pandas back and stops if a read was not
    seen, so that the workaround cannot stop working without anyone noticing."""
    target = os.path.abspath(workbook)
    main_py = os.path.realpath(os.path.join(HERE, 'main.py'))
    taxonomy_py = os.path.realpath(os.path.join(HERE, 'src-v3', 'taxonomic_alignment', 'taxa_assignment_manager.py'))
    seen = {'sheets': set(), 'final_check': 0, 'taxonomy_step': 0}
    read_excel, read_csv = pd.read_excel, pd.read_csv

    def excel(io, *args, **kwargs):
        if isinstance(io, (str, os.PathLike)) and os.path.abspath(io) == target and 'dtype' not in kwargs:
            kwargs['dtype'] = object
            seen['sheets'].add(kwargs.get('sheet_name', args[0] if args else 0))
        return read_excel(io, *args, **kwargs)

    def csv(path, *args, **kwargs):
        caller = sys._getframe(1)
        where = os.path.realpath(caller.f_code.co_filename)
        as_text = None
        if 'dtype' in kwargs:
            pass
        elif where == main_py and caller.f_code.co_name == 'main' and (
                'files_to_validate' in caller.f_locals or 'final_occurrence_path' in caller.f_locals):
            as_text = 'final_check' if 'files_to_validate' in caller.f_locals else 'match_type_debug'
        elif where == taxonomy_py and os.path.basename(str(path)) == 'occurrence.csv':
            as_text = 'taxonomy_step'
        if as_text:
            kwargs.update(dtype=str, keep_default_na=False, na_values=[''])
            seen[as_text] = seen.get(as_text, 0) + 1
        return read_csv(path, *args, **kwargs)

    pd.read_excel, pd.read_csv = excel, csv

    def check():
        pd.read_excel, pd.read_csv = read_excel, read_csv
        missing = [s for s in ('projectMetadata', 'sampleMetadata', 'experimentRunMetadata') if s not in seen['sheets']]
        if missing:
            fail("edna2obis no longer reads " + ', '.join(missing) + " as this tool expects, so values such as 001 "
                 "may have been changed. The Galaxy wrapper needs updating for this edna2obis version.")
        if not seen['final_check'] or not seen['taxonomy_step']:
            step = 'checks its output tables' if not seen['final_check'] else 'reads the occurrence table back'
            fail(f"edna2obis no longer {step} as this tool expects, so values such as 001 or NA may have been "
                 "changed. The Galaxy wrapper needs updating for this edna2obis version.")
    return check


def api_name(value):
    return {'worms': 'WoRMS', 'gbif': 'GBIF'}.get(str(value).strip().lower())


def matcher_settings(api_form):
    api = api_form['api_select']
    s = {'taxonomic_api_source': api}
    if api == 'WoRMS':
        adv = api_form.get('worms_advanced') or {}
        s.update({
            'worms_return_all_matches': bool(api_form.get('worms_return_all_matches')),
            'worms_min_ranks_matched': int(adv.get('worms_min_ranks_matched') or 1),
            'worms_max_walkup_steps': adv.get('worms_max_walkup_steps'),
            'worms_return_higher_classification': bool(adv.get('worms_return_higher_classification')),
            'worms_consider_unaccepted_for_selection': bool(adv.get('worms_consider_unaccepted_for_selection')),
            'worms_n_proc': int(adv.get('n_proc') or 1),
        })
    else:
        adv = api_form.get('gbif_advanced') or {}
        s.update({
            'gbif_match_limit': int(adv.get('gbif_match_limit') or 3),
            'gbif_use_assignment_score_for_selection': bool(adv.get('gbif_use_assignment_score_for_selection')),
            'gbif_return_higher_classification': bool(adv.get('gbif_return_higher_classification')),
            'gbif_n_proc': int(adv.get('n_proc') or 1),
        })
    return s


def describe_request_error(err):
    text = str(err)
    if 'NameResolution' in text or 'Name or service not known' in text or 'Temporary failure in name' in text:
        return 'the server name could not be looked up'
    if 'ProxyError' in type(err).__name__ or 'proxy' in text.lower():
        return 'a proxy refused the connection'
    if 'Timeout' in type(err).__name__ or 'timed out' in text:
        return 'no reply within 30 seconds'
    return f'{type(err).__name__}: {text[:200]}'


def worms_over_https():
    """pyworms has WoRMS's address as plain HTTP (http://www.marinespecies.org/rest/, port 80), in
    every version on conda-forge. WoRMS serves the same REST API over HTTPS, so the driver points
    pyworms there. Every pyworms function builds its address with worms_url(), looked up in the
    pyworms module; the reachability check uses pyworms.utils.worms_url()."""
    import pyworms
    import pyworms.utils
    if not hasattr(pyworms, 'worms_url'):
        fail("this pyworms version has no worms_url(), so the driver cannot point it at WoRMS over "
             "HTTPS (please report this).")

    def worms_url():
        return WORMS_REST
    pyworms.worms_url = worms_url
    pyworms.utils.worms_url = worms_url


def check_api_reachable(api):
    """One request with a short timeout, so an unreachable API gives a clear message at once.
    (pyworms retries each failed request 10 times, 5 s apart, and upstream then
    reports the names as 'incertae sedis'.)"""
    import requests
    if api == 'WoRMS':
        worms_over_https()
        import pyworms.utils
        base = pyworms.utils.worms_url()
        url, key, want = base + 'AphiaRecordByAphiaID/2', 'AphiaID', 2
    else:
        base = 'https://api.gbif.org/v1/'
        url, key, want = base + 'species/1', 'key', 1
    host = API_HOSTS[api]
    advice = (f"Looking up names needs internet access from the Galaxy server. Try again later; if it keeps "
              f"failing, ask the Galaxy administrators whether jobs can reach {host}. To build the Darwin Core "
              "tables without internet access, use a mapping table made earlier by 'edna2obis: match taxa'.")
    try:
        r = requests.get(url, timeout=30)
    except requests.exceptions.RequestException as err:
        fail(f"could not reach the {api} API at {host}: {describe_request_error(err)}. {advice}")
    if r.status_code != 200:
        fail(f"the {api} API at {host} answered with HTTP status {r.status_code}. {advice}")
    try:
        ok = r.json().get(key) == want
    except ValueError:
        ok = False
    if not ok:
        fail(f"the {api} API at {host} did not return the expected test record. {advice}")
    info(f"{api} API reachable ({base})")


def record_api_failures(api):
    """Wrap the API functions upstream calls so that failed requests are written
    to a file (worker processes are forked and inherit the wrappers)."""
    import requests
    path = os.path.abspath(API_FAILURES)

    def is_service_failure(err, name):
        if isinstance(err, requests.exceptions.HTTPError):
            code = getattr(err.response, 'status_code', 0) or 0
            # GBIF's match and search answer every name, found or not, so any error status from
            # them means the service failed (or, for pygbif 0.6.5, that GBIF has withdrawn its v1
            # matching service). name_usage's 404 for an unknown key is an ordinary answer.
            return code >= 500 or code == 429 or name in ('name_backbone', 'name_lookup')
        if isinstance(err, requests.exceptions.RequestException):
            return True
        return type(err) is Exception  # pyworms raises a bare Exception after its retries

    def wrap(module, name):
        original = getattr(module, name)

        @functools.wraps(original)
        def wrapper(*args, **kwargs):
            try:
                return original(*args, **kwargs)
            except Exception as err:
                # A TypeError means upstream's call does not fit the installed library (as with
                # pygbif 0.6.6's name_backbone); upstream logs it and goes on with fewer matches.
                kind = 'service' if is_service_failure(err, name) else \
                    'call' if isinstance(err, TypeError) else None
                if kind:
                    with open(path, 'a', encoding='utf-8') as fh:
                        fh.write(f"{kind}\t{name}\t{type(err).__name__}: {str(err)[:300]}\n")
                raise
        setattr(module, name, wrapper)

    if api == 'WoRMS':
        import pyworms
        for name in ('aphiaRecordsByMatchNames', 'aphiaRecordByAphiaID', 'aphiaClassificationByAphiaID'):
            wrap(pyworms, name)
    else:
        from pygbif import species
        for name in ('name_lookup', 'name_backbone', 'name_usage'):
            wrap(species, name)
    if sys.platform.startswith('linux'):
        import multiprocess
        multiprocess.set_start_method('fork', force=True)  # so worker processes inherit the wrappers


def check_api_failures(api):
    if not os.path.exists(API_FAILURES):
        return
    with open(API_FAILURES, encoding='utf-8') as fh:
        lines = [line.rstrip('\n') for line in fh if line.strip()]
    calls = [line.split('\t', 1)[1].replace('\t', ': ', 1) for line in lines if line.startswith('call\t')]
    if calls:
        fail(f"{len(calls)} call(s) to the {api} library failed because the call does not fit the installed "
             f"version (first: {calls[0]}). The matches would be incomplete, so the tool has stopped "
             "(please report this).")
    lines = [line.split('\t', 1)[1].replace('\t', ': ', 1) for line in lines]
    if lines:
        fail(f"{len(lines)} request(s) to the {api} API failed during matching (first: {lines[0]}). edna2obis "
             "reports names whose lookup failed as 'incertae sedis', so the results would be incomplete and the "
             "tool has stopped. Try again later, or with fewer parallel requests.")


def block_api_calls():
    """With a mapping table no API call should happen; make sure none can."""
    def blocked(*args, **kwargs):
        raise Stop("an API call was attempted although a mapping table was given (please report this).")
    import pyworms
    for name in ('aphiaRecordsByMatchNames', 'aphiaRecordByAphiaID', 'aphiaClassificationByAphiaID'):
        setattr(pyworms, name, blocked)
    from pygbif import species
    for name in ('name_lookup', 'name_backbone', 'name_usage'):
        setattr(species, name, blocked)
    import urllib.request
    urllib.request.urlopen = blocked


def reporter_errors(reporter):
    return [plain(s['content']).replace('ERROR:', '').strip() for s in reporter.sections if s['type'] == 'error']


def write_yaml(path, data, header=''):
    with open(path, 'w', encoding='utf-8') as fh:
        if header:
            fh.write(header)
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True, default_flow_style=False)


# ------------------------------------------------------------ mapping table

def truthy(value, where):
    v = str(value).strip().lower()
    if v in TRUE_WORDS:
        return True
    if v in FALSE_WORDS:
        return False
    raise Stop(f"{where}: selected_match must be True or False, not '{value}'.")


class Mapping:
    """A reviewed taxa_mapping_INFO table: one selected row per name (and assay)."""

    def __init__(self, dataset):
        path, ext = dataset['source_path'], dataset['ext']
        if is_xlsx(path, ext):
            sheets = pd.read_excel(path, sheet_name=None, dtype=str, keep_default_na=False)
            df = sheets.get('taxa_mapping_INFO', next(iter(sheets.values())))
        else:
            df = pd.read_csv(path, sep=',' if ext == 'csv' else '\t', dtype=str, keep_default_na=False,
                             encoding='utf-8-sig')
        df.columns = [str(c).strip() for c in df.columns]
        need = ['verbatimIdentification', 'selected_match', 'scientificName', 'nameAccordingTo']
        missing = [c for c in need if c not in df.columns]
        if missing:
            raise Stop(f"the mapping table has no {', '.join(missing)} column. Use the table written by "
                       "'edna2obis: match taxa' (or edna2obis's taxa_mapping_INFO file).")
        df = df.fillna('')
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        df['_selected'] = [truthy(v, f"mapping table row {i + 2}") for i, v in enumerate(df['selected_match'])]
        selected = df[df['_selected']]
        if selected.empty:
            raise Stop("no row of the mapping table has selected_match = True.")
        apis = set(selected['nameAccordingTo'])
        if len(apis) != 1 or api_name(next(iter(apis))) is None:
            raise Stop(f"the selected rows of the mapping table must all have nameAccordingTo WoRMS, or all GBIF "
                       f"(found: {', '.join(sorted(apis)) or 'empty'}).")
        self.api = api_name(next(iter(apis)))
        self.id_col = 'scientificNameID' if self.api == 'WoRMS' else 'taxonID'
        if self.id_col not in df.columns:
            raise Stop(f"a {self.api} mapping table needs a {self.id_col} column.")
        self.has_assay = 'assay_name' in df.columns
        self.df = df
        self.fields = WORMS_FIELDS if self.api == 'WoRMS' else GBIF_FIELDS
        self.by_pair, self.by_name = {}, {}
        for _, row in selected.iterrows():
            assay = row['assay_name'] if self.has_assay else ''
            self.by_pair.setdefault((row['verbatimIdentification'], assay), []).append(row)
            self.by_name.setdefault(row['verbatimIdentification'], []).append(row)
        conflicts = [f"'{v}'" + (f" ({a})" if a else '')
                     for (v, a), rows in self.by_pair.items() if len({self.taxon(r) for r in rows}) > 1]
        if conflicts:
            raise Stop(f"{len(conflicts)} name(s) have more than one row marked selected_match = True with "
                       f"different taxa: {listing(conflicts, 5)}. Keep one selected row for each name"
                       + (" and assay." if self.has_assay else "."))
        self.candidates = set(df['verbatimIdentification'])
        info(f"mapping table: {len(df)} rows, {len(self.by_name)} names with a selected {self.api} match"
             + (", by assay" if self.has_assay else ""))

    def taxon(self, row):
        return (row.get(self.id_col, ''), row.get('scientificName', ''))

    def lookup(self, name, assay):
        """The selected row for a name, or a reason why there is none."""
        rows = self.by_pair.get((name, assay if self.has_assay else ''))
        if rows:
            return rows[0], None
        rows = self.by_name.get(name)
        if not rows:
            return None, 'unselected' if name in self.candidates else 'missing'
        if len({self.taxon(r) for r in rows}) == 1:
            return rows[0], None
        return None, 'ambiguous'

    def record(self, row):
        rec = {}
        for col in self.fields:
            value = row.get(col, '') if col in row.index else ''
            rec[col] = pd.NA if value == '' else value
        return rec

    def info_rows(self, names):
        rows = self.df[self.df['verbatimIdentification'].isin(names)]
        return rows.drop(columns=['_selected', 'assay_name'], errors='ignore').drop_duplicates()


def make_offline_matcher(mapping):
    """Stands in for get_worms_match_for_dataframe / get_gbif_match_for_dataframe.
    Returns the same {'main_df', 'info_df'} structure, taking each name's
    selected row from the mapping table instead of calling the API."""

    def offline_match(occurrence_df, params_dict, n_proc=0):
        df = occurrence_df.copy()
        for col in ('verbatimIdentification', 'assay_name'):
            df[col] = df[col].apply(lambda x: '' if pd.isna(x) else str(x).strip())
        empty_record = {c: pd.NA for c in mapping.fields}
        # upstream's record for rows with no taxonomy string at all
        empty_record.update({'scientificName': 'incertae sedis', 'nameAccordingTo': mapping.api,
                             'match_type_debug': 'incertae_sedis_truly_empty_fallback', 'cleanedTaxonomy': '',
                             'replaced_unaccepted': 'False', 'unaccepted_match': 'False'})
        if mapping.api == 'WoRMS':
            empty_record['scientificNameID'] = 'urn:lsid:marinespecies.org:taxname:12'
        results, problems = {}, {'missing': [], 'unselected': [], 'ambiguous': []}
        for name, assay in df[['verbatimIdentification', 'assay_name']].drop_duplicates().itertuples(index=False):
            if name == '':
                results[(name, assay)] = empty_record
                continue
            row, why = mapping.lookup(name, assay)
            if row is None:
                problems[why].append(f"'{name}' ({assay})" if mapping.has_assay else f"'{name}'")
            else:
                results[(name, assay)] = mapping.record(row)
        messages = []
        if problems['missing']:
            messages.append(f"{len(problems['missing'])} name(s) are not in the mapping table: "
                            f"{listing(problems['missing'], 5)}")
        if problems['unselected']:
            messages.append(f"{len(problems['unselected'])} name(s) have no row marked selected_match = True: "
                            f"{listing(problems['unselected'], 5)}")
        if problems['ambiguous']:
            messages.append(f"{len(problems['ambiguous'])} name(s) have different selected taxa for other assays "
                            f"and none for this one: {listing(problems['ambiguous'], 5)}")
        if messages:
            raise Stop('; '.join(messages) + ". Run 'edna2obis: match taxa' on these taxonomy tables (or add the "
                       "names to the table) so every name with reads has one selected row.")
        keys = list(zip(df['verbatimIdentification'], df['assay_name']))
        for col in mapping.fields:
            df[col] = pd.Series([results[k][col] for k in keys], index=df.index, dtype=object)
        info_df = mapping.info_rows(set(df['verbatimIdentification']))
        info(f"taxonomy from the mapping table for {len(results)} name and assay pair(s)")
        return {'main_df': df, 'info_df': info_df}

    return offline_match


# ------------------------------------------------------------- the workbook

# eventDate: FAIRe asks for year-first ISO 8601. Upstream reads other text dates with pandas, which
# takes 7/6/19 as 6 July 2019 (month first) but 13/6/19 as 13 June, so a day-first column comes out
# partly swapped without warning. The driver passes ISO values and FAIRe missing-value terms as they
# are, and stops on dates written day or month first unless the form says which way to read them.
ISO_DATE = re.compile(r'^\d{4}(-\d{2}(-\d{2})?)?'
                      r'([T ]\d{2}(:\d{2}(:\d{2}(\.\d+)?)?)?(Z|[+-]\d{2}(:?\d{2})?)?)?$')
ISO_INTERVAL_END = re.compile(r'^\d{2}(-\d{2})?$')  # 2008-01-23/25 or 2008-01-23/02-05
YEAR_FIRST = re.compile(r'^(\d{4})[/.](\d{1,2})[/.](\d{1,2})$')
DAY_OR_MONTH_FIRST = re.compile(r'^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4}|\d{2})'
                                r'(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?$')
MISSING_TERMS = ('missing', 'not applicable', 'not collected', 'not provided', 'restricted access')
# The form's choices for text such as NA or N/A: FAIRe's missing-value terms (FAIRe checklist, section 4.3.3)
NA_TERMS = {'not_provided': 'missing: not provided', 'not_collected': 'missing: not collected',
            'not_applicable': 'not applicable', 'restricted_access': 'missing: restricted access'}
TEXT_DATE_ORDERS = {'dmy': 'day first', 'mdy': 'month first'}


def iso_date_ok(text):
    """True for a valid ISO 8601 date, date and time, or interval (year first)."""
    parts = text.split('/')
    if len(parts) > 2 or not ISO_DATE.match(parts[0]):
        return False
    if len(parts) == 2 and not (ISO_DATE.match(parts[1]) or ISO_INTERVAL_END.match(parts[1])):
        return False
    for part in parts:
        if ISO_DATE.match(part):
            ymd = part[:10].split('-')
            try:
                datetime.date(int(ymd[0]), int(ymd[1]) if len(ymd) > 1 else 1, int(ymd[2]) if len(ymd) > 2 else 1)
            except ValueError:
                return False
    return True


def text_date_to_iso(text, order):
    """'7/6/19' read day first ('dmy') or month first ('mdy') as ISO 8601. ValueError if not a date."""
    m = DAY_OR_MONTH_FIRST.match(text)
    first, second, year = int(m[1]), int(m[2]), m[3]
    day, month = (first, second) if order == 'dmy' else (second, first)
    year = int(year) if len(year) == 4 else (2000 + int(year) if int(year) < 70 else 1900 + int(year))
    iso = datetime.date(year, month, day).isoformat()
    if m[4]:
        hour, minute = int(m[4]), int(m[5])
        if hour > 23 or minute > 59:
            raise ValueError('time out of range')
        iso += f'T{hour:02d}:{minute:02d}' + (f':{m[6]}' if m[6] else '')
    return iso


def check_event_dates(sm, col, names, text_dates):
    """Check sampleMetadata eventDate text, and rewrite dates written day or month first as ISO 8601
    when the form says how to read them. names: samp_name for each row, for messages."""
    unreadable, ambiguous, invalid, converted, year_first, partial = [], [], [], [], [], []
    for i in sm.index[3:]:
        value = sm.at[i, col]
        if blank(value) or isinstance(value, (datetime.datetime, pd.Timestamp)):
            continue
        label = f"'{names.get(i) or f'row {i + 1}'}': {str(value).strip()}"
        if isinstance(value, (int, float)):
            if float(value).is_integer() and 1000 <= value <= 2999:
                continue  # a year
            unreadable.append(label)
            continue
        text = str(value).strip()
        if iso_date_ok(text):
            if re.fullmatch(r'\d{4}(-\d{2})?', text):
                partial.append(label)
            continue
        if text.lower().startswith(MISSING_TERMS):
            continue
        m = YEAR_FIRST.match(text)
        if m:
            try:
                iso = datetime.date(int(m[1]), int(m[2]), int(m[3])).isoformat()
            except ValueError:
                unreadable.append(label)
                continue
            sm.at[i, col] = iso
            year_first.append((text, iso))
            continue
        if not DAY_OR_MONTH_FIRST.match(text):
            unreadable.append(label)
        elif text_dates not in TEXT_DATE_ORDERS:
            ambiguous.append(label)
        else:
            try:
                iso = text_date_to_iso(text, text_dates)
            except ValueError:
                invalid.append(label)
                continue
            sm.at[i, col] = iso
            converted.append((text, iso))
    if unreadable:
        fail(f"{len(unreadable)} eventDate value(s) in sampleMetadata are neither dates this tool can read nor "
             f"FAIRe missing-value terms: {listing(unreadable, 5)}. Write them as ISO 8601, year first (for "
             "example 2019-06-07, or 2019-06-07T09:30+08:00 with a time), as FAIRe requires.")
    if ambiguous:
        fail(f"{len(ambiguous)} eventDate value(s) in sampleMetadata are written day or month first, which "
             f"cannot be read safely (7/6/19 is 7 June 2019 in Australia but 6 July 2019 in the USA): "
             f"{listing(ambiguous, 5)}. Write them as ISO 8601, year first (for example 2019-06-07), as FAIRe "
             "requires, or choose how to read them under 'Text dates in eventDate'.")
    if invalid:
        fail(f"read {TEXT_DATE_ORDERS[text_dates]}, {len(invalid)} eventDate value(s) are not valid dates: "
             f"{listing(invalid, 5)}. Check whether the dates are written "
             f"{'month' if text_dates == 'dmy' else 'day'} first, or correct them in the workbook.")
    if partial:
        warn(f"{len(partial)} eventDate value(s) give only a year or a month: {listing(partial, 5)}. edna2obis "
             "writes these as the first day (2019-06 becomes 2019-06-01). If the day is not known, write the "
             "date as an interval, for example 2019-06-01/2019-06-30.")
    if year_first:
        info(f"wrote {len(year_first)} year-first eventDate value(s) as ISO 8601, for example "
             f"{year_first[0][0]} as {year_first[0][1]}")
    if converted:
        two_digit = any(len(re.split(r'[/.\- T]', t)[2]) == 2 for t, _ in converted)
        info(f"read {len(converted)} eventDate value(s) {TEXT_DATE_ORDERS[text_dates]} and wrote them as "
             f"ISO 8601, for example {converted[0][0]} as {converted[0][1]}"
             + ("; two-digit years 00 to 69 were read as 2000 to 2069, and 70 to 99 as 1970 to 1999"
                if two_digit else ""))


def analysis_sheets(sheets):
    """{sheet: (assay_name, analysis_run_name, term column)} for analysisMetadata sheets."""
    found = {}
    for name, df in sheets.items():
        if not str(name).startswith('analysisMetadata'):
            continue
        cells = df.fillna('').astype(str).apply(lambda s: s.str.strip())
        term_col = None
        for j in range(cells.shape[1] - 1):
            if 'assay_name' in set(cells.iloc[:, j]):
                term_col = j
                break
        if term_col is None:
            fail(f"workbook sheet '{name}' has no assay_name row.")
        values = dict(zip(cells.iloc[:, term_col], cells.iloc[:, term_col + 1]))
        found[name] = (values.get('assay_name', ''), values.get('analysis_run_name', ''), term_col + 1)
    return found


def na_text_cells(sheets, na_values):
    """[(sheet, row, column, label, field)] of the metadata values that are text such as NA or N/A. Only values:
    rows below the field names, and in projectMetadata the columns after term_name."""
    found = []
    for name in ('projectMetadata', 'sampleMetadata', 'experimentRunMetadata'):
        df = sheets.get(name)
        if df is None or df.empty:
            continue
        if name == 'projectMetadata':
            headers = [None if blank(v) else str(v).strip() for v in df.iloc[0]]
            if 'term_name' not in headers:
                continue
            term = headers.index('term_name')
            cells = [(r, c) for r in range(1, len(df)) for c in range(term + 1, df.shape[1])]
            label = lambda r, c: f"projectMetadata {df.iat[r, term]} ({headers[c]})"  # noqa: E731
            field = lambda r, c: str(df.iat[r, term])  # noqa: E731
        else:
            if len(df) < 4:
                continue
            fields = [None if blank(v) else str(v).strip() for v in df.iloc[2]]
            key = fields.index('samp_name') if 'samp_name' in fields else 0
            cells = [(r, c) for r in range(3, len(df)) for c in range(df.shape[1])]
            label = lambda r, c: f"{name} '{df.iat[r, key]}' {fields[c]}"  # noqa: E731
            field = lambda r, c: str(fields[c])  # noqa: E731
        for r, c in cells:
            v = df.iat[r, c]
            if isinstance(v, str) and v.strip() in na_values:
                found.append((name, r, c, label(r, c), field(r, c)))
    return found


def handle_na_text(sheets, choice, na_values):
    """Text such as NA or N/A in the metadata, as the form says: replace it with a FAIRe missing-value
    term (the default), keep it as written (upstream edna2obis passes it on), or stop and list it."""
    found = na_text_cells(sheets, na_values)
    if not found:
        return
    if choice == 'stop':
        fail(f"{len(found)} cell(s) in the workbook hold text such as NA or N/A, which is not one of FAIRe's "
             f"missing-value terms: {listing([f'{lab}: {sheets[s].iat[r, c]}' for s, r, c, lab, _ in found], 5)}. "
             "Write the reason in the workbook (not applicable, missing: not collected, missing: not provided or "
             "missing: restricted access), or choose a term under 'Text such as NA or N/A'.")
    if choice == 'keep':
        for name in dict.fromkeys(s for s, *_ in found):
            count = sum(1 for s, *_ in found if s == name)
            info(f"{name}: {count} cell(s) hold text such as NA or N/A, kept as written; edna2obis passes it on "
                 "(into locationID, for example). FAIRe's missing-value terms, such as 'missing: not provided', "
                 "may suit better")
        return
    term = NA_TERMS[choice]
    where = collections.Counter()
    for name, r, c, _, field in found:
        sheets[name].iat[r, c] = term
        where[field] += 1
    info(f"replaced {len(found)} cell(s) of text such as NA or N/A with '{term}': "
         + ', '.join(f"{field} ({n})" for field, n in where.items()))


def prepare_workbook(src, analyses, text_dates='stop', na_text='not_provided'):
    """Copy of the workbook in the layout upstream reads, with run names resolved.
    Returns (path, metadata_format, field_name_column).
    Cell values are read as upstream reads them (na_values=[""], keep_default_na=False): only empty
    cells are empty. Text such as NA or N/A is then handled as the form says (handle_na_text)."""
    import normalise_faire
    normalise_faire.normalise(src, 'workbook_normalised.xlsx')
    sheets = pd.read_excel('workbook_normalised.xlsx', sheet_name=None, header=None, keep_default_na=False,
                           na_values=[''])
    # pandas' default missing values, except '' and 'None' (which can be a real answer, such as no treatment)
    handle_na_text(sheets, na_text, normalise_faire.PANDAS_NA - {'', 'None'})
    sm = sheets['sampleMetadata']
    sm_fields = [None if blank(v) else str(v).strip() for v in sm.iloc[2]] if len(sm) > 2 else []
    if 'eventDate' in sm_fields:
        # Excel date cells would reach the occurrence core as '2021-09-14 11:00:00'
        col = sm.columns[sm_fields.index('eventDate')]
        cells = [i for i in sm.index[3:] if isinstance(sm.at[i, col], (datetime.datetime, pd.Timestamp))]
        for i in cells:
            sm.at[i, col] = pd.Timestamp(sm.at[i, col]).isoformat()
        if cells:
            info(f"wrote {len(cells)} eventDate Excel date cell(s) as ISO 8601 text, for example "
                 f"{sm.at[cells[0], col]} (no time zone; add one in the workbook if known)")
        name_col = sm.columns[sm_fields.index('samp_name')] if 'samp_name' in sm_fields else sm.columns[0]
        names = {i: (None if blank(sm.at[i, name_col]) else str(sm.at[i, name_col]).strip()) for i in sm.index[3:]}
        check_event_dates(sm, col, names, text_dates)
    pm = sheets['projectMetadata']
    headers = [None if blank(v) else str(v).strip() for v in pm.iloc[0]]
    erm = sheets['experimentRunMetadata']
    erm_fields = [None if blank(v) else str(v).strip() for v in erm.iloc[2]] if len(erm) > 2 else []
    erm_assays = set()
    if 'assay_name' in erm_fields:
        erm_assays = {str(v).strip() for v in erm.iloc[3:, erm_fields.index('assay_name')] if not blank(v)}
    pm_assays = [h for h in headers if h and h not in ('requirement_level_code', 'section', 'term_name',
                                                       'project_level')]
    am = analysis_sheets(sheets)
    fmt = 'NOAA' if am else 'GENERIC'
    for a in analyses:
        assay = a['assay']
        if assay not in pm_assays:
            fail(f"assay '{assay}' has no column in projectMetadata "
                 f"(its assays are: {', '.join(pm_assays) or 'none'}).")
        if erm_assays and assay not in erm_assays:
            fail(f"assay '{assay}' is not used in experimentRunMetadata (assay_name values: "
                 f"{', '.join(sorted(erm_assays))}).")
        if fmt == 'NOAA':
            runs = [r for s, (an, r, _) in am.items() if an == assay]
            if a['run']:
                if a['run'] not in runs:
                    fail(f"analysis run '{a['run']}' for assay '{assay}' is not in the workbook's analysisMetadata "
                         f"sheets (runs for this assay: {', '.join(runs) or 'none'}).")
            elif len(runs) == 1:
                a['run'] = runs[0]
                info(f"assay '{assay}': analysis run '{runs[0]}' from the workbook's analysisMetadata sheet")
            else:
                fail(f"assay '{assay}' has {len(runs)} analysisMetadata sheets in the workbook "
                     f"({', '.join(runs) or 'none'}); enter the analysis run name for these tables.")
        elif not a['run']:
            a['run'] = assay
    names = [a['run'] for a in analyses]
    dups = sorted({n for n in names if names.count(n) > 1})
    if dups:
        fail(f"each set of tables needs its own analysis run name; repeated: {', '.join(dups)}. Enter a run name "
             "for each set (it becomes part of every occurrenceID).")
    if fmt == 'NOAA':
        used = {a['run'] for a in analyses}
        drop = [s for s, (_, r, _) in am.items() if r not in used]
        for s in drop:
            del sheets[s]
        if drop:
            info(f"left out analysisMetadata sheets with no tables in this run: {', '.join(drop)}")
        cols = {c for s, (_, r, c) in am.items() if r in used}
        if len(cols) > 1:
            fail("the analysisMetadata sheets have their term_name column in different places.")
        field_col = cols.pop()
    else:
        field_col = 3
    normalise_faire.write_values(sheets, 'workbook.xlsx')  # text starting with '=' stays text
    layout = 'FAIRe-NOAA with analysisMetadata sheets' if fmt == 'NOAA' else 'generic FAIRe'
    info(f"workbook layout for edna2obis: {layout}")
    return 'workbook.xlsx', fmt, field_col


def read_run_sheet(workbook):
    erm = pd.read_excel(workbook, 'experimentRunMetadata', header=2, dtype=str, keep_default_na=False, na_values=[''])
    erm.columns = [str(c).strip() for c in erm.columns]
    for col in ('samp_name', 'lib_id', 'assay_name'):
        if col not in erm.columns:
            fail(f"experimentRunMetadata has no {col} column (field names are expected on row 3).")
        erm[col] = erm[col].fillna('').astype(str).str.strip()
    return erm[erm['lib_id'] != '']


def headers_to_lib_id(path, label, assay, erm):
    """Rename abundance columns named by samp_name to the lib_id of that sample's run for the assay.
    edna2obis does this itself, but only after removing control samples by lib_id, so controls
    in tables with samp_name columns would stay in the output."""
    runs = erm[erm['assay_name'] == assay]
    lib_ids = set(runs['lib_id'])
    libs_of = runs.groupby('samp_name')['lib_id'].apply(lambda s: sorted(set(s))).to_dict()
    df = pd.read_csv(path, sep='\t', dtype=str, keep_default_na=False)
    rename, several, unknown = {}, [], []
    for col in df.columns[1:]:
        if col in lib_ids:
            continue
        libs = libs_of.get(col, [])
        if len(libs) == 1:
            rename[col] = libs[0]
        elif libs:
            several.append(f"{col} ({', '.join(libs)})")
        else:
            unknown.append(col)
    if several:
        fail(f"{label}: these columns are sample names with more than one run for assay '{assay}', so the run "
             f"is unclear: {listing(several, 5)}. Name the abundance columns by lib_id.")
    new = [rename.get(c, c) for c in df.columns]
    if len(set(new)) != len(new):
        fail(f"{label}: after renaming sample names to lib_id, some columns would share a name. Name the "
             "abundance columns by lib_id.")
    if rename:
        df.columns = new
        df.to_csv(path, sep='\t', index=False)
        info(f"{label}: {len(rename)} column(s) named by samp_name renamed to the lib_id of their run")
    if unknown:
        warn(f"{label}: {len(unknown)} column(s) match no lib_id or samp_name of assay '{assay}' in "
             f"experimentRunMetadata: {listing(unknown, 5)}")
    return lib_ids


# --------------------------------------------------------------------- EML

LICENCES = {
    'CC0': None,  # upstream writes the CC0 block itself
    'CC-BY': {'license_name': 'Creative Commons Attribution 4.0 International',
              'url': 'https://spdx.org/licenses/CC-BY-4.0.html', 'identifier': 'CC-BY-4.0'},
    'CC-BY-NC': {'license_name': 'Creative Commons Attribution Non Commercial 4.0 International',
                 'url': 'https://spdx.org/licenses/CC-BY-NC-4.0.html', 'identifier': 'CC-BY-NC-4.0'},
}


def eml_from_form(f):
    person = {'individual_name': {'given_name': f['given_name'].strip(), 'surname': f['surname'].strip()},
              'organization_name': (f.get('organisation') or '').strip(),
              'email': f['email'].strip()}
    if (f.get('orcid') or '').strip():
        orcid = f['orcid'].strip()
        person['user_id'] = orcid if orcid.startswith('http') else f'https://orcid.org/{orcid}'
    meta = {
        'title': (f.get('title') or '').strip(),
        'title_source_field': 'project_name',
        'abstract': f['abstract'].strip(),
        'language': 'eng',
        'creators': [person],
        'contact': dict(person),
        'keywords': [{'keyword': k} for k in split_list(f.get('keywords'))],
        'license': f['licence'],
        'geographic_coverage': {'description': (f.get('geographic_description') or '').strip(),
                                'description_source_fields': ['locality']},
        'temporal_coverage': {'event_date_field': 'eventDate'},
        'taxonomic_coverage': {'rank_fields': ['kingdom', 'phylum', 'class', 'order']},
        'project': {'title_source_field': 'project_name'},
    }
    if LICENCES[f['licence']]:
        meta['licensed'] = LICENCES[f['licence']]
    if (f.get('publication_date') or '').strip():
        meta['publication_date'] = f['publication_date'].strip()
    if (f.get('sampling_description') or '').strip():
        meta['methods'] = {'sampling_description': f['sampling_description'].strip(),
                           'method_steps': [{'description': f['sampling_description'].strip()}]}
    if not meta['title']:
        del meta['title']
    return {'eml_metadata': meta}


def eml_from_yaml(dataset, contacts):
    try:
        with open(dataset['source_path'], encoding='utf-8-sig') as fh:
            full = yaml.safe_load(fh)
    except yaml.YAMLError as err:
        fail(f"the EML YAML file could not be read: {err}")
    if not isinstance(full, dict) or not isinstance(full.get('eml_metadata'), dict):
        fail("the EML YAML file needs an 'eml_metadata:' section, as in edna2obis's EML_config.yaml.")
    # Contacts come only from the contacts file given on the form, never from a path in the YAML
    for d in (full, full['eml_metadata']):
        if d.pop('contacts_path', None):
            warn("ignored contacts_path in the EML YAML file; give the contacts file on the form instead")
    if contacts:
        try:
            with open(contacts['source_path'], encoding='utf-8-sig') as fh:
                book = yaml.safe_load(fh)
        except yaml.YAMLError as err:
            fail(f"the contacts YAML file could not be read: {err}")
        if not isinstance(book, dict):
            fail("the contacts YAML file should hold one entry per person, as in edna2obis's contacts.yaml.")
        return full, book
    return full, {}


# ------------------------------------------------------------------ outputs

def write_table(df, path, fmt):
    if fmt == 'xlsx':
        # through a file handle: pandas refuses a path without .xlsx, such as Galaxy's .dat
        with open(path, 'wb') as fh, pd.ExcelWriter(fh, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='taxa_mapping_INFO', index=False)
    else:
        df.to_csv(path, sep='\t', index=False)


def summarise_mapping(info_df):
    sel = info_df[info_df['selected_match'].astype(str).str.lower() == 'true']
    names = info_df['verbatimIdentification'].nunique()
    incertae = int((sel['scientificName'].astype(str) == 'incertae sedis').sum())
    amb = info_df.loc[info_df['ambiguous'].astype(str).str.lower() == 'true', 'verbatimIdentification'].nunique() \
        if 'ambiguous' in info_df else 0
    return f"{names} name(s), {len(sel)} selected row(s), {incertae} 'incertae sedis', {amb} with several candidates"


# ------------------------------------------------------------- subcommands

def base_config(settings):
    cfg = {
        'run_config_path': 'config.yaml',
        'metadata_format': 'GENERIC',
        'edna2obis_run_name': RUN_NAME,
        'combined_metadata_file': True,
        'sampleMetadata': 'sampleMetadata',
        'experimentRunMetadata': 'experimentRunMetadata',
        'projectMetadata': 'projectMetadata',
        'field_name_row': 3,
        'project_and_analysis_header_rows_to_skip': 0,
        'field_name_column': 3,
        'field_names_row_asv': 1,
        'field_names_row_table': 1,
        'use_local_reference_database': False,
        'output_dir': OUT_DIR,
        'split_output_by_short_name': False,
        'include_performance_metrics_in_output': False,
    }
    cfg.update(settings)
    return cfg


def enter_workdir():
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    os.chdir(WORK)
    shutil.copy(os.path.join(HERE, 'data_mapper.yaml'), 'data_mapper.yaml')


def run_match(form, out_path):
    analyses = form['analyses']
    api_form = form['api']
    settings = matcher_settings(api_form)
    api = settings['taxonomic_api_source']
    fmt = form.get('mapping_format', 'tabular')
    start = os.getcwd()
    enter_workdir()
    upstream_main = setup_upstream()
    from html_reporter import HTMLReporter
    from taxonomic_alignment import taxa_assignment_manager as tam
    from taxonomic_alignment.taxa_assignment_info_export import read_taxa_assignment_info_dataframe
    check_api_reachable(api)
    record_api_failures(api)
    # load_config needs these keys; the match step reads no workbook
    write_yaml('config.yaml', base_config({**settings, 'excel_file': 'not_used.xlsx', 'datafiles': {}}))
    tables = []
    for i, a in enumerate(analyses, 1):
        assay = a['assay_name'].strip()
        run = f'analysis{i}'
        tax = prepare_table(a['taxonomy'], f"assay '{assay}' taxonomy table", f'{run}_taxonomy.tsv')
        out_dir = os.path.join(OUT_DIR, run)
        os.makedirs(out_dir, exist_ok=True)
        params = upstream_main.load_config('config.yaml')
        params.update({'output_dir': out_dir, 'datafiles': {run: {'assay_name': assay, 'taxonomy_file': tax}},
                       'assays_to_skip_species_match': [assay] if a.get('skip_species') else []})
        reporter = HTMLReporter(os.path.join(out_dir, 'report.html'), run)
        raw = upstream_main.load_asv_data(params, reporter)
        tax_df = raw[run]['taxonomy']
        if 'verbatimIdentification' not in tax_df.columns:
            fail(f"assay '{assay}': the taxonomy table has no verbatimIdentification (or taxonomy) column, so there "
                 "are no names to look up.")
        names = sorted({'' if pd.isna(v) else str(v).strip() for v in tax_df['verbatimIdentification']} - {''})
        if not names:
            fail(f"assay '{assay}': the verbatimIdentification column is empty.")
        info(f"assay '{assay}': looking up {len(names)} name(s) in {api}"
             + (" without the species level" if a.get('skip_species') else ""))
        pd.DataFrame({'verbatimIdentification': names, 'assay_name': assay}).to_csv(
            os.path.join(out_dir, 'occurrence.csv'), index=False)
        data = {'analysis_data_by_assay': {assay: {run: pd.DataFrame()}}}
        tam.assign_taxonomy(params, data, raw, reporter)
        check_api_failures(api)
        errors = reporter_errors(reporter)
        if errors:
            fail(f"assay '{assay}': {' '.join(errors)}")
        tam.create_taxa_assignment_info(params, reporter)
        if api == 'GBIF':
            from taxonomic_alignment.remove_GBIF_duplicates import remove_duplicates_from_gbif_taxa_info
            from taxonomic_alignment.mark_selected_gbif_match import mark_selected_gbif_matches
            remove_duplicates_from_gbif_taxa_info(params, reporter)
            mark_selected_gbif_matches(params, reporter)
        else:
            from taxonomic_alignment.mark_selected_worms_match import mark_selected_worms_matches
            mark_selected_worms_matches(params, reporter)
        errors = reporter_errors(reporter)
        if errors:
            fail(f"assay '{assay}': {' '.join(errors)}")
        info_path = os.path.join(out_dir, f'taxa_mapping_INFO_{api}.xlsx')
        if not os.path.exists(info_path):
            fail(f"assay '{assay}': edna2obis did not write its taxa mapping table.")
        df = read_taxa_assignment_info_dataframe(info_path)
        df.insert(1, 'assay_name', assay)
        info(f"assay '{assay}': {summarise_mapping(df)}")
        tables.append(df)
    check_api_failures(api)
    combined = pd.concat(tables, ignore_index=True)
    os.chdir(start)
    write_table(combined, out_path, fmt)
    info(f"wrote the mapping table: {len(combined)} rows. Review it, change selected_match where needed (one "
         "True row for each name and assay), then use it in 'edna2obis: build Darwin Core tables'.")


def run_build(form, outputs):
    start = os.getcwd()
    os.makedirs(outputs, exist_ok=True)
    outputs = os.path.abspath(outputs)
    analyses = []
    for a in form['analyses']:
        analyses.append({'assay': a['assay_name'].strip(), 'run': (a.get('run_name') or '').strip(),
                         'taxonomy': a['taxonomy'], 'abundance': a['abundance'],
                         'skip_species': bool(a.get('skip_species'))})
    workbook_src = os.path.abspath(form['input_file']['source_path'])
    enter_workdir()
    workbook, fmt, field_col = prepare_workbook(workbook_src, analyses, form.get('text_dates') or 'stop',
                                                form.get('na_text') or 'not_provided')

    erm = read_run_sheet(workbook)
    shared = erm.loc[erm['lib_id'].duplicated(keep=False), 'lib_id']
    datafiles = {}
    for i, a in enumerate(analyses, 1):
        label = f"assay '{a['assay']}' ({a['run']})"
        abundance = prepare_table(a['abundance'], f"{label} abundance table", f'analysis{i}_abundance.tsv')
        headers_to_lib_id(abundance, f"{label} abundance table", a['assay'], erm)
        datafiles[a['run']] = {
            'assay_name': a['assay'],
            'taxonomy_file': prepare_table(a['taxonomy'], f"{label} taxonomy table", f'analysis{i}_taxonomy.tsv'),
            'abundance_file': abundance,
        }

    taxa = form['taxa']
    mapping = None
    if taxa['source'] == 'mapping':
        try:
            mapping = Mapping(taxa['mapping_file'])
        except Stop as err:
            fail(str(err))
        settings = {'taxonomic_api_source': mapping.api}
    else:
        settings = matcher_settings(taxa['api'])
    api = settings['taxonomic_api_source']

    samples = form['samples']
    controls = split_list(samples.get('control_values'))
    cfg = base_config(settings)
    cfg.update({
        'metadata_format': fmt,
        'excel_file': workbook,
        'field_name_column': field_col,
        'datafiles': datafiles,
        'control_sample_detection': {'column_name': (samples.get('control_column') or 'samp_category').strip(),
                                     'control_values': controls},
        'locationID_components': split_list(samples.get('location_fields')),
        'assays_to_skip_species_match': sorted({a['assay'] for a in analyses if a['skip_species']}),
        'dwc_core_type': form.get('core_type', 'occurrence'),
    })

    emof = form['emof']
    if emof['emof_select'] == 'none':
        cfg['emof_enabled'] = False
    else:
        src = os.path.join(HERE, 'raw-v3', 'eMoF_Fields_edna2obis.tsv') if emof['emof_select'] == 'default' \
            else emof['emof_template']['source_path']
        shutil.copy(src, 'eMoF_template.tsv')
        cfg.update({'emof_enabled': True, 'emof_template_path': 'eMoF_template.tsv'})

    eml = form['eml']
    if eml['eml_select'] == 'none':
        cfg['eml_enabled'] = False
    else:
        if eml['eml_select'] == 'form':
            eml_cfg, book = eml_from_form(eml), {}
        else:
            eml_cfg, book = eml_from_yaml(eml['eml_yaml'], eml.get('contacts_yaml'))
        write_yaml('EML_config.yaml', eml_cfg)
        write_yaml('contacts.yaml', book)
        cfg.update({'eml_enabled': True, 'eml_config_path': 'EML_config.yaml',
                    'contacts_path': os.path.abspath('contacts.yaml')})

    header = (f"# edna2obis config written by the Galaxy tool on {datetime.date.today().isoformat()}.\n"
              "# Run edna2obis with this file as config.yaml, next to the workbook and tables named below.\n")
    if mapping:
        header += ("# The taxonomy came from a reviewed mapping table, not from the API: upstream edna2obis would\n"
                   f"# look the names up in {api} again.\n")
    write_yaml('config.yaml', cfg, header)

    upstream_main = setup_upstream()
    from taxonomic_alignment import GBIF_matching, WoRMS_v3_matching
    from taxonomic_alignment import taxa_assignment_manager as tam
    if mapping:
        # assign_taxonomy reloads the matcher modules, which would undo the replacement
        tam.importlib = types.SimpleNamespace(reload=lambda module: module)
        matcher = make_offline_matcher(mapping)
        WoRMS_v3_matching.get_worms_match_for_dataframe = matcher
        GBIF_matching.get_gbif_match_for_dataframe = matcher
        block_api_calls()
    else:
        check_api_reachable(api)
        record_api_failures(api)

    info(f"running edna2obis ({api}, {cfg['dwc_core_type']} core)")
    check_readers = keep_values_as_written(workbook)
    stopped = None
    try:
        upstream_main.main()
    except Stop as err:
        stopped = str(err)
    except Exception as err:  # noqa: BLE001 - upstream raises plain Exceptions with a message
        stopped = str(err)
    if not stopped:
        check_readers()
    reporter = getattr(upstream_main, 'reporter', None)
    if not mapping:
        check_api_failures(api)
    if reporter is None:
        fail(stopped or "edna2obis could not read its configuration.")
    for w in reporter.warnings:
        warn(plain(w))
    errors = reporter_errors(reporter)
    if stopped or errors:
        detail = stopped if stopped and not errors else ' '.join(dict.fromkeys(errors))
        if stopped and errors and stopped not in detail:
            detail = f"{stopped} ({detail})"
        if 'Internal alignment error' in detail and len(shared):
            detail += (f". The eMoF step joins runs by lib_id alone, and {shared.nunique()} lib_id value(s) are "
                       "used in "
                       f"more than one experimentRunMetadata row (for example {listing(sorted(set(shared)), 3)}). "
                       "Give each run its own lib_id, or use an eMoF template without experimentRunMetadata fields "
                       "(such as input_read_count), or leave the eMoF out")
        fail(f"edna2obis stopped: {detail}")

    run_dir = os.path.join(OUT_DIR, RUN_NAME)
    occ_name = f'occurrence_core_{api.lower()}.csv'
    wanted = {occ_name: 'occurrence_core.csv', 'dna_derived_extension.csv': 'dna_derived_extension.csv',
              'meta.xml': 'meta.xml', f'taxa_mapping_INFO_{api}.xlsx': None,
              f'edna2obis_report_{api}_{RUN_NAME}.html': 'report.html'}
    if cfg['emof_enabled']:
        wanted['eMoF.csv'] = 'emof.csv'
    if cfg['eml_enabled']:
        wanted['eml.xml'] = 'eml.xml'
    if cfg['dwc_core_type'] == 'event':
        wanted['event_core.csv'] = 'event_core.csv'
    missing = [f for f in wanted if not os.path.exists(os.path.join(run_dir, f))]
    if missing:
        fail(f"edna2obis finished without writing {', '.join(missing)}. See the log and the HTML report for the "
             "reason.")
    for src, dest in wanted.items():
        if dest:
            shutil.copy(os.path.join(run_dir, src), os.path.join(outputs, dest))
    from taxonomic_alignment.taxa_assignment_info_export import read_taxa_assignment_info_dataframe
    info_df = read_taxa_assignment_info_dataframe(os.path.join(run_dir, f'taxa_mapping_INFO_{api}.xlsx'))
    info_df.to_csv(os.path.join(outputs, 'taxa_mapping.tsv'), sep='\t', index=False)
    shutil.copy('config.yaml', os.path.join(outputs, 'config.yaml'))

    # Darwin Core Archive: the files meta.xml names, plus meta.xml (and eml.xml)
    import xml.etree.ElementTree as ET
    root = ET.parse(os.path.join(run_dir, 'meta.xml')).getroot()
    members = [loc.text.strip() for loc in root.iter('{http://rs.tdwg.org/dwc/text/}location')]
    if root.get('metadata'):
        members.append(root.get('metadata'))
    with zipfile.ZipFile(os.path.join(outputs, 'dwca.zip'), 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(os.path.join(run_dir, 'meta.xml'), 'meta.xml')
        for m in members:
            zf.write(os.path.join(run_dir, m), m)
    os.chdir(start)

    occ = pd.read_csv(os.path.join(outputs, 'occurrence_core.csv'), dtype=str, encoding='utf-8-sig')
    info(f"occurrence core: {len(occ)} rows; {occ['scientificName'].nunique()} taxa; "
         f"{int((occ['scientificName'] == 'incertae sedis').sum())} rows 'incertae sedis'")
    info(f"Darwin Core archive: meta.xml, {', '.join(members)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('mode', choices=['match', 'build'])
    parser.add_argument('--form', required=True, help='Galaxy inputs JSON (staging_path_and_source_path)')
    parser.add_argument('--mapping_out', help='match: output mapping table')
    parser.add_argument('--outputs', default='outputs', help='build: folder for the outputs')
    args = parser.parse_args()
    with open(args.form, encoding='utf-8') as fh:
        form = json.load(fh)
    try:
        if args.mode == 'match':
            run_match(form, os.path.abspath(args.mapping_out))
        else:
            run_build(form, args.outputs)
    except Stop as err:
        fail(str(err))


if __name__ == '__main__':
    main()
