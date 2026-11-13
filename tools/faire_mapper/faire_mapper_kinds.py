"""What kind of input a table looks like, and where it goes in the FAIRe mapper tools.

Used by apply mapping, to say what a file in the wrong place looks like, and by identify input
files, which reports on every file a user uploads. A best guess from the table's shape, headers and
values: the user decides.

Kinds: sample, otu, taxonomy, library, crosswalk, dictionary, project_values, primers, sequences, text,
unknown. Sequences (FASTA) and PDF documents are recognised from their content (describe_file), whatever
their names.
"""

from __future__ import annotations

import re

import faire_mapper as fm
import faire_mapper_library as fl
import faire_mapper_otu as fo
import faire_mapper_text as ft

# Plain words for each kind, and where it goes (tool and field).
NAME = {
    'sample': 'a sample table (one row per sample, with sample details)',
    'otu': 'an OTU or ASV table (read counts per sequence or taxon and sample)',
    'taxonomy': 'a taxonomy table (one row per sequence, with its taxonomy and no read counts)',
    'library': 'a library table or run report (library names, sequence files or run accessions)',
    'crosswalk': 'a crosswalk (SSSOM) from FAIRe mapper: propose mapping',
    'dictionary': 'a data dictionary (column names with their descriptions)',
    'project_values': 'a table of values for the whole project (FAIRe term names with their values)',
    'primers': 'a primer table (primer names and sequences)',
    'sequences': 'sequences in FASTA format (a header line starting with > before each sequence)',
    'text': 'text, such as methods or a ReadMe (plain text or PDF)',
    'unknown': 'not recognised',
}
SHORT = {'sample': 'sample table', 'otu': 'OTU or ASV table', 'taxonomy': 'taxonomy table',
         'library': 'library table', 'crosswalk': 'crosswalk', 'dictionary': 'data dictionary',
         'project_values': 'project values', 'primers': 'primer table', 'sequences': 'sequences (FASTA)',
         'text': 'text', 'unknown': 'not recognised'}
WHERE = {
    'sample': "'Your table' in FAIRe mapper: profile a table, propose mapping and apply mapping",
    'otu': "'OTU or ASV table' in FAIRe mapper: apply mapping",
    'taxonomy': "'Taxonomy table', beside its OTU table, in FAIRe mapper: apply mapping",
    'library': "'Library table' in FAIRe mapper: apply mapping",
    'crosswalk': "'Crosswalk' in FAIRe mapper: apply mapping",
    'dictionary': "'Data dictionary' in FAIRe mapper: propose mapping",
    'project_values': "'Values for the whole project' in FAIRe mapper: apply mapping",
    'primers': "'My primer table' in FAIRe mapper: find primers, or 'Primer sources' in build primer table",
    'sequences': "'Sequences of this table (FASTA)', beside the OTU table whose sequence IDs it names, in FAIRe "
                 "mapper: apply mapping",
    'text': "'Methods text' in FAIRe mapper: find primers, if it describes the methods; a ReadMe can serve "
            "as the 'Data dictionary' in propose mapping if it describes the columns",
    'unknown': 'check the file; it may need its header row or sheet set',
}

DETAIL_WORDS = {'date', 'collected', 'collection', 'lat', 'latitude', 'lon', 'long', 'longitude', 'depth', 'site',
                'station', 'location', 'locality', 'volume', 'filter', 'filtered', 'temperature', 'temp', 'salinity',
                'control', 'replicate', 'time', 'country', 'habitat', 'elevation', 'coordinates', 'latlon', 'geo',
                'region', 'reef', 'voyage', 'cruise', 'sampler', 'pore', 'frozen', 'storage', 'substrate',
                'bore', 'well', 'transect', 'tide', 'weather', 'ph', 'turbidity', 'oxygen', 'conductivity'}
ID_VALUE = re.compile(r'^(asv|otu|zotu|esv|seq|feature|sv|cluster|denovo|ref)[_.\-]?\d+$', re.I)
HASH_ID = re.compile(r'^[0-9a-f]{32,64}$')
RUN_ACC = re.compile(r'^[SED]RR\d{5,}$')
# Headers of sequence ID columns ('id' alone is too common: sample tables use it too)
SEQ_ID_KEYS = {'seqid', 'featureid', 'asv', 'asvid', 'otu', 'otuid', 'zotu', 'zotuid', 'sequenceid', 'otuname',
               'asvname'}
DICT_NAME = {'column', 'columnname', 'columnheader', 'variable', 'variablename', 'field', 'fieldname', 'header',
             'attribute', 'name', 'term'}
DICT_DESC = re.compile(r'descr|defin|meaning|explan|detail', re.I)


def _vals(series, n=500):
    return [str(v).strip() for v in list(series)[:n] if not fo._blank(v)]


def _share(vals, test):
    return sum(1 for v in vals if test(v)) / len(vals) if vals else 0.0


def _whole_counts(series):
    """Read counts: every value empty or a number of 0 or more, nearly all whole."""
    if not fo._count_like(series):
        return False
    vals = _vals(series)
    return _share(vals, lambda v: float(v.replace(',', '')).is_integer()) >= 0.9


def _is_dna(v, least=30):
    return len(v) >= least and bool(fm.DNA_RE.match(v))


def _name_like(v):
    """A taxon or other name: letters, spaces and a few marks, no digits."""
    return bool(re.match(r"^[A-Za-z][A-Za-z .,'()/_-]*$", v)) and not re.search(r'\d', v)


def _detail(header, term_names=()):
    toks = set(fm.tokens_of(str(header)))
    return bool(toks & DETAIL_WORDS) or (bool(toks) and frozenset(toks) in term_names)


def describe(df, sample_names=(), term_names=(), faire_terms=()):
    """(kind, [reasons]) for a table. sample_names: samp_name values the counts should use (they
    make the call surer); term_names: frozensets of tokens of FAIRe terms' names and common names, to
    recognise sample details; faire_terms: FAIRe term names, to recognise project values."""
    cols = list(df.columns)
    keys = [fo._key(c) for c in cols]
    n_rows = len(df)
    known = {fo.norm_id(s) for s in sample_names if fo.norm_id(s)}

    # A crosswalk from propose mapping, or its review sheet
    if {'subjectid', 'objectid'} <= set(keys) or {'subjectid', 'predicateid'} <= set(keys):
        return 'crosswalk', ['has subject_id and object_id columns (SSSOM)']
    if {'inputterm', 'reviewersdecision'} <= set(keys):
        return 'crosswalk', ["has Input term and Reviewer's decision columns (the review sheet)"]

    # Text read as a table: the header is a sentence
    if sum(len(str(c)) for c in cols) / len(cols) > 40:
        return 'text', ['the first line is a sentence, not column names']
    unnamed = [c for c in cols if str(c).startswith('Unnamed:')]
    if len(unnamed) >= 0.5 * len(cols):
        return 'unknown', [f'{len(unnamed)} of {len(cols)} columns have no name: the column names may be on a '
                           f'later row (set the header row)']
    acc_cols = [c for c in cols if _share(_vals(df[c]), lambda v: bool(RUN_ACC.match(v))) >= 0.8]
    if acc_cols:
        return 'library', [f'run accessions in {acc_cols[0]}']

    first = cols[0]
    first_vals = _vals(df[first])

    def is_sample(name):
        n = fo.norm_id(name)
        return n in known or fl.illumina_sample(n) in known   # M108_S7_L001 for M108
    header_samples = [c for c in cols[1:] if is_sample(c)]
    row_samples = _share(first_vals, is_sample) if known else 0.0
    # Counts are judged on the top half of the rows, as some tables keep sample details below them
    top = df.iloc[:max(5, n_rows // 2)]
    counts = [c for c in cols[1:] if _whole_counts(top[c]) and fo._key(c) not in SEQ_ID_KEYS
              and fo._key(c) not in ('taxid', 'taxonid', 'ncbitaxid') and not _detail(c, term_names)]
    details = [c for c in cols if _detail(c, term_names)]
    # Some column, anywhere, with a different value on (nearly) every row: a sample ID, say
    unique_col = any(len(v) >= 2 and len(set(v)) >= 0.9 * len(v) for v in (_vals(df[c]) for c in cols[:120]))
    fastq_cols = [c for c in cols if _share(_vals(df[c]), lambda v: bool(re.search(r'\.f(ast)?q(\.gz)?\b', v))) >= 0.8]
    in_text = re.compile(r'\b[ACGTURYSWKMBDHVNI]{15,40}\b')

    # Long form: one row per sample and sequence
    if known:
        long = fo.long_form(df, lambda h: (h, '') if is_sample(h) else (None, ''))
        if long:
            return 'otu', [f'long form: sample names repeat in {long[0]}, counts in {long[2]}, '
                           f'sequences or taxa in {long[1]}']
    # A library table: library names with their sequence files (an SRA sheet, a run sheet), and few
    # sample details (a sample table may name each sample's library and files too)
    found = fl.find_columns(cols)
    lib_and_files = 'lib_id' in found and ('filename' in found or 'files' in found)
    if lib_and_files and len(details) < 4:
        return 'library', [f"library names ({found['lib_id']}) with their sequence files "
                           f"({found.get('filename', found.get('files'))})"]

    # A sample table: several columns of sample details, and not mostly counts. It may also hold
    # each sample's primers and sequence files.
    if len(header_samples) < 2 and len(counts) < 0.5 * (len(cols) - 1) and \
            ((len(details) >= 4 and (unique_col or row_samples >= 0.5)) or row_samples >= 0.8):
        why = []
        if known and row_samples >= 0.5:
            why.append(f'the first column holds sample names ({", ".join(first_vals[:2])} ...)')
        why.append(f'{len(details)} columns of sample details ({", ".join(map(str, details[:4]))} ...)')
        if lib_and_files or fastq_cols:
            col = found.get('filename', found.get('files')) if lib_and_files else fastq_cols[0]
            why.append(f'it also names sequence files ({col}), so it can serve as the library table too')
        primer_like = [c for c in cols if 'primer' in fo._key(c) and _vals(df[c])
                       and _share(_vals(df[c]), lambda v: bool(in_text.search(v))) >= 0.6]
        if primer_like:
            why.append(f'it also holds primer sequences ({primer_like[0]})')
        return 'sample', why

    # Primer tables: named primer columns, primer sequences under a primer header, or two columns of
    # primer-length sequences that differ from row to row (a sample table repeats its assay's primers)
    if any(k in ('pcrprimerforward', 'forwardprimer', 'primerforward', 'fwdprimer', 'forwardsequence') for k in keys):
        return 'primers', ['has a forward primer column']
    named = [c for c, k in zip(cols, keys) if 'primer' in k and _share(_vals(df[c]), lambda v: bool(in_text.search(v))) >= 0.6]
    if named:
        return 'primers', [f'primer sequences in {named[0]}']
    primer_cols = [c for c in cols if _share(_vals(df[c]), lambda v: 12 <= len(v) <= 45 and fm.DNA_RE.match(v)) >= 0.8
                   and len(set(_vals(df[c]))) >= 0.5 * len(_vals(df[c]))]
    if len(primer_cols) >= 2:
        return 'primers', [f'two columns of primer-length sequences ({primer_cols[0]}, {primer_cols[1]})']

    # Library tables and run reports
    if fastq_cols:
        if len(cols) <= 20:
            return 'library', [f'sequence file names in {fastq_cols[0]}']
        return 'sample', [f'sequence file names in {fastq_cols[0]}, with {len(cols)} other columns: probably a '
                          f'sample table that also names each sample\'s files']
    lineage = [c for c in cols if fo.is_lineage(c) or _share(_vals(df[c]), lambda v: v.count(';') >= 2) >= 0.8]
    ranks = [c for c in cols if fo._key(c) in fo.RANK_NAMES]
    id_first = (fo._key(first) in SEQ_ID_KEYS
                or _share(first_vals, lambda v: bool(ID_VALUE.match(v) or HASH_ID.match(v)) or _is_dna(v)) >= 0.6)
    names_first = not id_first and _share(first_vals, _name_like) >= 0.6

    # Counts with samples as columns
    if (known and len(header_samples) >= 2) or (len(counts) >= 3 and (id_first or names_first)):
        why = [f'{len(header_samples)} column headers are sample names' if known and header_samples
               else f'{len(counts)} columns of whole-number counts']
        if names_first:
            why.append('the rows are names, not sequence IDs: reads summed per taxon')
        elif any(_is_dna(v) for v in first_vals[:20]):
            why.append('the rows are DNA sequences (as DADA2 writes them)')
        elif id_first:
            why.append(f'the rows are sequence IDs ({first_vals[0] if first_vals else first})')
        named = [c for c in cols if fo._key(c) in fo.TAXA_ALIASES['scientificName']]
        if id_first and named:
            why.append(f'it has a column of names ({named[0]}), which may be curated names')
        return 'otu', why
    # Counts with samples as rows
    if (row_samples >= 0.5 or (not known and not id_first)) and len(counts) >= 3 \
            and len(counts) >= 0.5 * (len(cols) - 1):
        return 'otu', [f'{len(counts)} columns of whole-number counts, with the samples as rows']

    # Taxonomy without counts
    if (lineage or len(ranks) >= 3) and not header_samples:
        why = [f'a lineage column ({lineage[0]})' if lineage else f'{len(ranks)} rank columns ({", ".join(map(str, ranks[:3]))} ...)']
        why.append('no columns of read counts')
        return 'taxonomy', why

    # A data dictionary
    has_name = any(k in DICT_NAME for k in keys)
    has_desc = any(DICT_DESC.search(str(c)) for c in cols)
    long_text = [c for c in cols if _vals(df[c]) and sum(len(v) for v in _vals(df[c])) / len(_vals(df[c])) > 30]
    if len(cols) <= 6 and ((has_name and has_desc) or (has_desc and long_text)):
        return 'dictionary', ['a column of names and a column of descriptions']

    # Values for the whole project
    if faire_terms and len(cols) <= 5 and _share(first_vals, lambda v: v in faire_terms) >= 0.5:
        return 'project_values', [f'the first column holds FAIRe term names ({", ".join(first_vals[:3])} ...)']

    # A sample table with few details
    if (known and row_samples >= 0.5) or (unique_col and len(details) >= 2):
        why = []
        if known and row_samples >= 0.5:
            why.append(f'the first column holds sample names ({", ".join(first_vals[:2])} ...)')
        if details:
            why.append(f'{len(details)} columns of sample details ({", ".join(map(str, details[:4]))} ...)')
        return 'sample', why

    if len(cols) == 1 and n_rows and sum(len(v) for v in first_vals) / max(1, len(first_vals)) > 40:
        return 'text', ['one column of long lines']
    return 'unknown', [f'{len(cols)} columns, {n_rows} rows']


def describe_file(path):
    """(kind, [reasons]) for the files recognised by their content, whatever their names: FASTA files
    and PDF documents. None for anything else, which is read as a table or as text."""
    if ft.is_pdf(path):
        return describe_text(path)
    fa = ft.fasta_summary(path)
    if fa:
        size = (f"{fa['shortest']} to {fa['longest']} bases" if fa['shortest'] != fa['longest']
                else f"{fa['longest']} bases")
        return 'sequences', [f"{fa['n']} sequences of {size}, each after a header line starting with > "
                             f"({', '.join(fa['ids'])} ...)"]
    return None


def describe_text(path):
    """(kind, [reasons]) for a text file that is not a table, or a PDF."""
    try:
        text = ft.read_text(path)[:200000]
    except (OSError, SystemExit) as e:
        return 'unknown', [str(e).replace('ERROR: ', '')]
    except Exception as e:   # a damaged PDF
        return 'unknown', [f'could not be read: {e}']
    seqs = re.findall(r"\b[ACGTURYSWKMBDHVNI]{15,40}\b", text)
    why = [f'{len(text.split())} words']
    if ft.is_pdf(path):
        n = ft.pdf_pages(path)
        why = [f'a PDF of {n} page{"" if n == 1 else "s"}'] + why
        if not text.split():
            why.append('no text could be read: a PDF of scanned pages has none, so save the methods as text')
    if seqs:
        why.append(f'{len(seqs)} primer-length DNA sequences')
    if re.search(r'primer|PCR|amplif', text, re.I):
        why.append('mentions primers or PCR')
    return 'text', why


def hint(kind, reasons, expected):
    """A sentence for a log or error: what the file looks like, when that is not what its field expects."""
    if kind == expected or kind == 'unknown':
        return ''
    return f" It looks like {NAME[kind]}: {'; '.join(reasons)}. If so, give it as {WHERE[kind]}."
