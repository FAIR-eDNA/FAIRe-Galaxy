"""OTU and taxonomy tables for faire_mapper_apply: read a lab's abundance table (and optionally a
taxonomy table) and turn them into FAIRe otuRaw/otuFinal and taxaRaw/taxaFinal tables.

Handled forms:

  * samples as columns: one row per ASV or OTU, an identifier first (or the DNA sequence itself, as
    DADA2 writes it), the read counts, then optional taxonomy and sequence columns;
  * samples as rows: one row per sample, then one column per ASV, OTU or taxon (a matrix of reads
    summed per taxon, as often published), optionally followed by sample details, which are left out;
  * taxonomy as FAIRe columns (kingdom ... specificEpithet, scientificName ...), as rank columns
    (domain, phylum ... species), as one lineage string ("k__Animalia;p__Chordata;..." or
    "Animalia;Chordata;..."), as PR2 or SILVA lineages with classifier confidences
    ("Eukaryota(100);Obazoa(100);..."), or, when there is none, from the names themselves.

The OTU table's sample names must match samp_name (or lib_id) in the sample table.
"""

from __future__ import annotations

import math
import os
import re

import pandas as pd

import faire_mapper as fm
import faire_mapper_library as fl

RANKS = ['kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species']
RANK_NAMES = {'domain': 'kingdom', 'superkingdom': 'kingdom', 'kingdom': 'kingdom', 'phylum': 'phylum',
              'division': 'phylum', 'class': 'class', 'order': 'order', 'family': 'family', 'genus': 'genus',
              'species': 'species'}
PREFIX_RANK = {'d': 'kingdom', 'k': 'kingdom', 'p': 'phylum', 'c': 'class', 'o': 'order', 'f': 'family',
               'g': 'genus', 's': 'species'}
# Column names often used for the FAIRe taxonomy terms, lower case with spaces and punctuation removed.
TAXA_ALIASES = {
    'seq_id': ['seqid', 'featureid', 'asv', 'asvid', 'otu', 'otuid', 'id', 'sequenceid', 'zotu', 'zotuid'],
    'dna_sequence': ['dnasequence', 'sequence', 'seq', 'asvsequence', 'representativesequence', 'repseq'],
    'lineage': ['taxonomy', 'taxon', 'lineage', 'classification', 'consensus', 'consensustaxonomy'],
    'confidence_score': ['confidence', 'confidencescore', 'bootstrap'],
    'percent_match': ['percentmatch', 'pident', 'percidentity', 'identity', 'percentidentity'],
    'percent_query_cover': ['percentquerycover', 'qcov', 'querycover', 'qcovs', 'qcovhsp', 'querycoverage',
                            'percentquerycoverage'],
    'accession_id': ['accession', 'accessionid', 'sseqid'],
    'scientificName': ['scientificname', 'taxonname', 'speciesname', 'assignedtaxon', 'lca', 'name', 'newname',
                       'curatedname', 'curatedtaxon', 'finalname', 'finaltaxon', 'assignedname'],
    'taxonRank': ['taxonrank', 'rank'],
    'taxonID': ['taxonid', 'taxid', 'ncbitaxid'],
}
NUMERIC_TERMS = {'percent_match', 'percent_query_cover', 'confidence_score'}
# Domains that are not kingdoms, so are not written to kingdom (Bacteria and Archaea are both).
DOMAIN_ONLY = {'eukaryota', 'eukarya', 'eukaryote', 'eukaryotes'}
NOT_A_NAME = re.compile(r'^(|na|nan|none|unassigned|unclassified|unknown|unidentified|uncultured.*|'
                        r'metagenome|environmental.*|[a-z]__|.*_sp\.?|sp\.?)$', re.I)


class OtuError(Exception):
    """A problem with an OTU or taxonomy table that the user has to fix."""


LATIN_NAME = re.compile(r"^[A-Z][a-z]+(\s[a-z][a-z-]+)?(\s(sp|spp|cf|aff)\.?(\s.*)?)?$")


def _key(s):
    return re.sub(r'[^a-z0-9]', '', str(s).lower())


def _blank(v):
    return v is None or (isinstance(v, float) and math.isnan(v)) or (isinstance(v, str) and not v.strip())


def norm_id(v):
    """Sample or ASV identifier as text: 7, 7.0 and '7' are the same."""
    if _blank(v):
        return ''
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    s = str(v).strip()
    return s[:-2] if re.match(r'^-?\d+\.0$', s) else s


def _count_like(series):
    """Every value empty or a number of 0 or more (read counts, or relative values)."""
    vals = [v for v in series if not _blank(v)]
    if not vals:
        return False
    for v in vals:
        try:
            x = float(str(v).replace(',', ''))
        except ValueError:
            return False
        if not math.isfinite(x) or x < 0:
            return False
    return True


def read_table_any(path, sheet=None):
    """A table, skipping the two FAIRe header rows (requirement level, section) when present."""
    df = fm.read_table(path, sheet or None, 1)
    first = str(df.columns[0]).strip().lower()
    if first.startswith('# requirement_level_code') or first.startswith('#requirement'):
        df = fm.read_table(path, sheet or None, 3)
    return df


def count_block(df, start, is_detail=None):
    """Columns from `start` that hold counts, up to the first that does not, or whose header names a
    sample detail (such as Site depth). A repeat of the first column (Site and Site.1) is skipped."""
    first = str(df.columns[0])
    cols, left_out = [], []
    for c in df.columns[start:]:
        if re.match(rf'^{re.escape(first)}\.\d+$', str(c)):
            left_out.append(c)
            continue
        if is_detail is not None and is_detail(str(c)):
            break
        if _count_like(df[c]):
            cols.append(c)
        else:
            break
    rest = [c for c in df.columns[start:] if c not in cols and c not in left_out]
    return cols, left_out + rest


def shared_prefix(names, resolve):
    """A prefix on the count columns' names that, taken off, makes more of them sample names than
    without it: S_ in S_CN01 (a table whose columns were renamed), or the X that R puts before
    names that start with a digit (X1001). '' when there is none."""
    left = [n for n in names if n and resolve(n)[0] is None]
    if len(left) < 2:
        return ''
    direct = len(names) - len(left)
    common = os.path.commonprefix(left)
    # Each cut after a separator (S_ and S_LIZ_ in S_LIZ_01, S_LIZ_FB), and R's X; the one that
    # makes the most sample names, the shorter on a tie.
    cands = [common[:m.end()] for m in re.finditer(r'[_.\-]', common)] + (['X'] if common.startswith('X') else [])
    best, most = '', 0
    for p in sorted(cands, key=len):
        hits = sum(resolve(n[len(p):])[0] is not None for n in left)
        if hits > most:
            best, most = p, hits
    return best if most >= 2 and most > direct else ''


def sample_columns(df, is_sample):
    """Columns whose header is a sample, with any count columns between the first and last of them
    (controls missing from the sample table, say); the rest are annotations."""
    names = list(df.columns[1:])
    hits = [i for i, c in enumerate(names) if is_sample(norm_id(c)) and _count_like(df[c])]
    if not hits:
        return [], names
    cols = [c for i, c in enumerate(names) if hits[0] <= i <= hits[-1] and _count_like(df[c])]
    return cols, [c for c in names if c not in cols]


def _count(v):
    if _blank(v):
        return True
    try:
        x = float(str(v).replace(',', ''))
    except ValueError:
        return False
    return math.isfinite(x) and x >= 0


def drop_footer(df, sample_cols):
    """Rows below the counts that hold sample details instead (Sample ID, Voyage, Latitude ...), as
    some tables keep them: from the first row in the lower half whose sample columns are mostly not
    counts. Returns the table without them and their labels (first column)."""
    if not sample_cols:
        return df, []
    n = len(df)
    for i in range(n // 2, n):
        row = df.iloc[i]
        if sum(not _count(row[c]) for c in sample_cols) > len(sample_cols) / 2:
            labels = [str(v).strip() for v in df.iloc[i:, 0] if not _blank(v)]
            return df.iloc[:i], labels
    return df, []


LAYOUTS = {'columns': 'samples as columns', 'rows': 'samples as rows', 'long': 'long form'}
LAYOUT_SETTING = "'Layout of this table'"


def read_otu(path, sheet, sample_names, lib_to_samp, log, label, is_detail=None, frame=None, layout='detect'):
    """(counts DataFrame: index seq_id, columns samp_name; annotations DataFrame or None; seq labels).
    frame: the table already read (one assay's rows of a table that holds several). layout: detect,
    or the user's columns, rows or long, which overrides the detection."""
    df = read_table_any(path, sheet) if frame is None else frame
    first_header = str(df.columns[0])
    known = {norm_id(s) for s in sample_names if norm_id(s)}
    libs = {norm_id(k): v for k, v in (lib_to_samp or {}).items()}

    def resolve_plain(h):
        # A sample name, a library ID, or an Illumina file name (M108_S7_L001) of either.
        if h in known:
            return h, ''
        if h in libs:
            return libs[h], 'lib'
        st = fl.illumina_sample(h)
        if st != h and st in known:
            return st, 'file'
        if st != h and st in libs:
            return libs[st], 'file'
        return None, ''
    prefix = shared_prefix([norm_id(c) for c in df.columns[1:] if _count_like(df[c])], resolve_plain)

    def resolve(h):
        # ... or one of those with a prefix that every sample column has (S_CN01 for CN01)
        s, how = resolve_plain(h)
        if s is None and prefix and h.startswith(prefix):
            s = resolve_plain(h[len(prefix):])[0]
            how = 'prefix' if s is not None else ''
        return s, how
    layout = layout or 'detect'
    long = long_form(df, resolve) if layout in ('detect', 'long') else None
    if layout == 'long' and long is None:
        raise OtuError(f"{label}: {LAYOUT_SETTING} is long form, but the table has no column of sample names "
                       f"that repeat, with a column of read counts and a column of sequence IDs or names. Check the setting "
                       f"and the table.")
    if long is not None:
        if layout == 'long':
            log(f'{label}: read as long form, as set')
        return _read_long(df, long, resolve, known, log, label)
    headers = [norm_id(c) for c in df.columns[1:]]
    in_cols = sum(resolve(h)[0] is not None for h in headers)
    first_vals = [norm_id(v) for v in df.iloc[:, 0]]
    in_rows = sum(resolve(v)[0] is not None for v in first_vals)
    if layout == 'columns' and not in_cols:
        raise OtuError(f"{label}: {LAYOUT_SETTING} is samples as columns, but no column header matches samp_name in "
                       f"the sample table (table: {', '.join(headers[:3])} ...; samp_name: "
                       f"{', '.join(sorted(known)[:3])} ...). Check the setting and the sample names.")
    if layout == 'rows' and not in_rows:
        raise OtuError(f"{label}: {LAYOUT_SETTING} is samples as rows, but no value in the first column matches "
                       f"samp_name in the sample table (table: {', '.join(first_vals[:3])} ...; samp_name: "
                       f"{', '.join(sorted(known)[:3])} ...). Check the setting and the sample names.")
    if layout == 'detect' and in_cols and in_rows:
        log(f"{label}: both the column headers ({in_cols}) and the first column ({in_rows}) hold sample names; "
            f"read with the samples as {'columns' if in_cols >= in_rows else 'rows'} (if that is wrong, set "
            f"{LAYOUT_SETTING})")
    elif layout in ('columns', 'rows'):
        log(f'{label}: read with the {LAYOUTS[layout]}, as set')
    if layout == 'columns' or (layout == 'detect' and in_cols and in_cols >= in_rows):
        orientation = 'samples as columns'
        # pandas names a repeated header CN065.1: a repeat, unless that is itself a sample or library
        headers = {str(c) for c in df.columns}
        repeats = [c for c in df.columns[1:] if re.match(r'^(.+)\.\d+$', str(c))
                   and str(c).rsplit('.', 1)[0] in headers and norm_id(c) not in known and norm_id(c) not in libs
                   and resolve(norm_id(str(c).rsplit('.', 1)[0]))[0] is not None]
        if repeats:
            names = sorted({str(c).rsplit('.', 1)[0] for c in repeats})
            log(f"{label}: WARNING {len(names)} sample column names appear more than once ({', '.join(names[:5])}); "
                f"the first of each is used and the others left out, as the table does not say which samples they are")
            df = df.drop(columns=repeats)
        df, footer = drop_footer(df, [c for c in df.columns[1:] if resolve(norm_id(c))[0] is not None])
        if footer:
            log(f'{label}: {len(footer)} rows below the counts left out (sample details: '
                + ', '.join(footer[:5]) + (' ...' if len(footer) > 5 else '') + ')')
        cols, rest = sample_columns(df, lambda h: resolve(h)[0] is not None)
        outside = [str(c) for c in rest if _count_like(df[c])
                   and not any(_key(c) in names for names in TAXA_ALIASES.values())]   # taxid is not a count
        if outside:
            log(f'{label}: {len(outside)} columns of counts are not samples of the sample table and are left out: '
                + ', '.join(outside[:5]) + (' ...' if len(outside) > 5 else ''))
        df = df[[not _blank(v) for v in df.iloc[:, 0]]]
        ids = [norm_id(v) for v in df.iloc[:, 0]]
        counts = df[cols].copy()
        counts.index = ids
        counts.columns = [norm_id(c) for c in cols]
        ann = df[[df.columns[0]] + rest].copy()
        ann.index = ids
    elif in_rows:
        orientation = 'samples as rows'
        cols, rest = count_block(df, 1, is_detail)
        body = df[[bool(v) for v in first_vals]].copy()
        body.index = [v for v in first_vals if v]
        counts = body[cols].T
        counts.index = [str(c).strip() for c in cols]
        counts.columns = list(body.index)
        ann = None
    else:
        raise OtuError(f"{label}: no column headers or first-column values match samp_name in the sample table "
                       f"(table: {', '.join(headers[:3])} ...; samp_name: {', '.join(sorted(known)[:3])} ...)")
    # Library IDs and file names to sample names
    renamed, by = [], {'lib': [], 'file': [], 'prefix': []}
    for c in counts.columns:
        s, how = resolve(c)
        renamed.append(s if s is not None else c)
        if how:
            by[how].append((c, s))
    if by['lib']:
        log(f'{label}: library IDs (lib_id) or sequence file names in the table written as sample names (samp_name)')
    if by['file']:
        a, b = by['file'][0]
        log(f"{label}: {len(by['file'])} names read as sample names without Illumina's sample number and lane "
            f"('{a}' as '{b}')")
    if by['prefix']:
        a, b = by['prefix'][0]
        log(f"{label}: {len(by['prefix'])} column names read as sample names without the prefix '{prefix}' "
            f"('{a}' as '{b}')")
    counts.columns = renamed
    if counts.columns.duplicated().any():
        dup = sorted(set(counts.columns[counts.columns.duplicated()]))
        raise OtuError(f"{label}: samples appear more than once in the table: {', '.join(dup[:5])}")
    unknown = [c for c in counts.columns if c not in known]
    missing = sorted(known - set(counts.columns))
    log(f'{label}: {orientation}; {counts.shape[0]} sequences or taxa, {counts.shape[1]} samples')
    if orientation == 'samples as rows' and rest:
        log(f"{label}: columns after the counts were left out (sample details): "
            + ', '.join(str(c) for c in rest[:8]) + (' ...' if len(rest) > 8 else ''))
    if unknown:
        log(f"{label}: WARNING {len(unknown)} samples are not in sampleMetadata, kept: "
            + ', '.join(unknown[:5]) + (' ...' if len(unknown) > 5 else ''))
    if missing:
        log(f"{label}: {len(missing)} samples in sampleMetadata have no column (not sequenced, or named "
            f"differently): " + ', '.join(missing[:5]) + (' ...' if len(missing) > 5 else ''))
    # Counts: numbers; empty cells are 0 reads.
    empty = int(counts.map(_blank).sum().sum())
    counts = counts.map(lambda v: 0 if _blank(v) else float(str(v).replace(',', '')))
    whole = bool((counts % 1 == 0).all().all())
    if whole:
        counts = counts.astype('int64')
    else:
        log(f'{label}: WARNING some values are not whole numbers; FAIRe tables hold read counts')
    if empty:
        log(f'{label}: {empty} empty cells written as 0')
    # Identifiers that are DNA sequences (DADA2 writes the sequence as the row name).
    ids = list(counts.index)
    # Sequences as identifiers: 30 bases or more, or any length under a header such as 'sequence'
    # (short amplicons, such as Wilderlab's RJ assay, have reads of 20 bases).
    min_len = 10 if _key(first_header) in TAXA_ALIASES['dna_sequence'] else 30
    dna = [i for i in ids if len(i) >= min_len and fm.DNA_RE.match(i)]
    sequences = {}
    if orientation == 'samples as columns' and len(dna) >= 0.8 * len(ids):
        width = len(str(len(ids)))
        new = [f'ASV{n:0{width}d}' for n in range(1, len(ids) + 1)]
        sequences = dict(zip(new, ids))
        counts.index = new
        if ann is not None:
            ann.index = new
        log(f'{label}: the identifiers are DNA sequences; written as dna_sequence, with seq_id ASV1 ... ASV{len(ids)}')
    if counts.index.duplicated().any():
        raise OtuError(f"{label}: seq_id repeats: {', '.join(sorted(set(counts.index[counts.index.duplicated()]))[:5])}")
    return counts, ann, sequences, orientation


def all_counts(counts, ann):
    """The counts with any other columns of counts in the table (samples not in the sample table,
    totals), to compare two tables of one assay row by row."""
    if ann is None:
        return counts
    keep = []
    for c in ann.columns[1:]:
        k = _key(c)
        if any(k in names for names in TAXA_ALIASES.values()) or k in RANK_NAMES or is_lineage(c):
            continue
        if _count_like(ann[c]):
            keep.append(c)
    if not keep:
        return counts
    extra = ann[keep].map(lambda v: 0 if _blank(v) else float(str(v).replace(',', '')))
    extra.columns = [f'_{norm_id(c)}' if norm_id(c) in set(counts.columns) else norm_id(c) for c in keep]
    return pd.concat([counts, extra], axis=1)


COUNT_NAMES = {'count', 'counts', 'reads', 'readcount', 'readcounts', 'nreads', 'numreads', 'abundance',
               'value', 'sequences', 'seqcount', 'size', 'frequency', 'freq'}
SAMPLE_NAMES = {'sample', 'samplename', 'sampname', 'sampleid', 'samples', 'site', 'libid', 'library'}


def long_form(df, resolve):
    """(sample column, ID column, count column) when the table has one row per sample and sequence
    (or taxon): a column of sample names that repeat, a column of counts and a column of IDs."""
    if len(df) < 2:
        return None
    samp = None
    for c in df.columns:
        if _count_like(df[c]):
            continue   # counts, not names (and this keeps wide tables quick)
        vals = [norm_id(v) for v in df[c] if not _blank(v)]
        distinct = set(vals)
        if not vals or len(distinct) == len(vals):
            continue   # sample names repeat in a long table
        hits = sum(resolve(v)[0] is not None for v in distinct)
        if hits >= 0.8 * len(distinct):
            samp = c
            break
    if samp is None:
        return None
    rest = [c for c in df.columns if c != samp]
    counts = [c for c in rest if _count_like(df[c])]
    named = [c for c in counts if _key(c) in COUNT_NAMES]
    count = named[0] if named else (counts[0] if len(counts) == 1 else None)
    if count is None:
        return None
    ids = [c for c in rest if c != count and _key(c) in TAXA_ALIASES['seq_id']]
    if not ids:
        ids = [c for c in rest if c != count and _key(c) in TAXA_ALIASES['dna_sequence']]
    if not ids:
        ids = [c for c in rest if c != count and (_key(c) in TAXA_ALIASES['scientificName'] or is_lineage(c))]
    if not ids:
        return None
    return samp, ids[0], count


def _read_long(df, long, resolve, known, log, label):
    """A table in long form, pivoted to one row per sequence (or taxon) and one column per sample.
    Columns that hold one value per sequence (taxonomy, the sequence) become its annotations;
    columns that vary within a sequence (sample details) are left out."""
    samp, idc, count = long
    d = df[[not _blank(v) and not _blank(w) for v, w in zip(df[samp], df[idc])]].copy()
    d['_s'] = [resolve(norm_id(v))[0] or norm_id(v) for v in d[samp]]
    d['_i'] = [norm_id(v) for v in d[idc]]
    d['_n'] = [0 if _blank(v) else float(str(v).replace(',', '')) for v in d[count]]
    counts = d.pivot_table(index='_i', columns='_s', values='_n', aggfunc='sum', fill_value=0, sort=False)
    counts.columns.name = None
    counts.index.name = None
    if bool((counts % 1 == 0).all().all()):
        counts = counts.astype('int64')
    else:
        log(f'{label}: WARNING some values are not whole numbers; FAIRe tables hold read counts')
    kept, dropped = [], []
    for c in df.columns:
        if c in (samp, idc, count):
            continue
        per = d.groupby('_i')[c].nunique(dropna=True)
        (kept if (per <= 1).all() else dropped).append(c)
    first = d.groupby('_i', sort=False).first()
    ann = pd.DataFrame({'_id': counts.index}, index=counts.index)
    for c in kept:
        ann[c] = [first.at[i, c] for i in counts.index]
    if _key(idc) not in TAXA_ALIASES['seq_id']:
        ann[idc] = list(counts.index)   # the ID column is a sequence or a name: read it as one too
    repeats = int(d.duplicated(['_i', '_s']).sum())
    missing = sorted(known - set(counts.columns))
    unknown = [c for c in counts.columns if c not in known]
    log(f"{label}: long form (one row per sample and sequence: {samp}, {idc}, {count}); "
        f"{counts.shape[0]} sequences or taxa, {counts.shape[1]} samples")
    if repeats:
        log(f'{label}: {repeats} ' + ('row repeats' if repeats == 1 else 'rows repeat')
            + ' a sample and sequence; their counts are added')
    if dropped:
        log(f"{label}: columns that vary within a sequence were left out (sample details): "
            + ', '.join(str(c) for c in dropped[:8]) + (' ...' if len(dropped) > 8 else ''))
    if unknown:
        log(f"{label}: WARNING {len(unknown)} samples are not in sampleMetadata, kept: "
            + ', '.join(unknown[:5]) + (' ...' if len(unknown) > 5 else ''))
    if missing:
        log(f"{label}: {len(missing)} samples in sampleMetadata have no rows (not sequenced, or named "
            f"differently): " + ', '.join(missing[:5]) + (' ...' if len(missing) > 5 else ''))
    ids = list(counts.index)
    sequences = {}
    if all(len(i) >= 30 and fm.DNA_RE.match(i) for i in ids):
        width = len(str(len(ids)))
        new = [f'ASV{n:0{width}d}' for n in range(1, len(ids) + 1)]
        sequences = dict(zip(new, ids))
        counts.index = new
        ann.index = new
        log(f'{label}: the identifiers are DNA sequences; written as dna_sequence, with seq_id ASV1 ... ASV{len(ids)}')
    return counts, ann, sequences, 'long form'


# ------------------------------------------------------------------ taxonomy

def split_lineage(s):
    """'k__Animalia; p__Chordata; ...' or 'Animalia;Chordata;...' to {rank: name}."""
    parts = [p.strip() for p in re.split(r'[;|]', str(s)) if p.strip()]
    out, positional = {}, True
    for p in parts:
        m = re.match(r'^([a-zA-Z])_{1,2}(.*)$', p) or re.match(r'^D_(\d)__(.*)$', p)
        if m and m.group(1).lower() in PREFIX_RANK:
            positional = False
            rank, name = PREFIX_RANK[m.group(1).lower()], m.group(2).strip()
            if rank == 'kingdom' and name.lower() in DOMAIN_ONLY:
                continue
            if name and not NOT_A_NAME.match(name):
                out[rank] = name.replace('_', ' ')
        elif m and m.group(1).isdigit():
            positional = False
            i = int(m.group(1))
            name = m.group(2).strip()
            if i < len(RANKS) and name and not NOT_A_NAME.match(name):
                out[RANKS[i]] = name.replace('_', ' ')
    if positional and parts and parts[0].lower() in DOMAIN_ONLY:
        return {}   # PR2 and SILVA eukaryote lineages have more ranks than FAIRe's; their order is not FAIRe's
    if positional:
        for rank, name in zip(RANKS, parts):
            if name and not NOT_A_NAME.match(name):
                out[rank] = name.replace('_', ' ')
    return out


# Lineages without rank labels from a classifier, often with its confidence after each name
# ("Eukaryota(100);Obazoa(100);..."). PR2 v5 has 9 ranks and v4 8; their ranks between the domain
# and the genus (supergroup, division ...) are not Linnaean ones (Arthropoda is a PR2 class), so only
# the genus and species go to FAIRe's rank terms. SILVA 138 (as mothur and DADA2 format it) has the
# domain, then phylum, class, order, family and genus, and sometimes species.
PR2_RANKS = {9: ['domain', 'supergroup', 'division', 'subdivision', 'class', 'order', 'family', 'genus', 'species'],
             8: ['domain', 'supergroup', 'division', 'class', 'order', 'family', 'genus', 'species']}
SILVA_RANKS = ['domain', 'phylum', 'class', 'order', 'family', 'genus', 'species']
DOMAINS = {'eukaryota', 'eukarya', 'bacteria', 'archaea'}
# Names a classifier or database writes where it has none: Dinophyta_XX, Calanoida_fa,
# Pseudo-nitzschia_unclassified, Gyrodinium_sp., uncultured ...
PLACEHOLDER = re.compile(r'(_X+|_unclassified|_fa|_or|_ge|_cl|_ph|_sp\.?(_.*)?|_Incertae_Sedis|_incertae_sedis)$'
                         r'|^(uncultured|unclassified|unknown|unidentified|metagenome|environmental|Incertae)\b', re.I)
SPECIES_NAME = re.compile(r'^[A-Z][a-z-]+[_ ][a-z][a-z-]+$')
# FAIRe's rank terms are Linnaean ranks, and FAIRe has no term for the classification a row follows, so each
# row classified with PR2 says so here (the full PR2 lineage is in verbatimIdentification).
PR2_REMARK = ('classified with PR2, whose levels above genus are not Linnaean ranks, so they are not written to '
              'the rank terms; the PR2 lineage is in verbatimIdentification')


def lineage_parts(s):
    """[(name, confidence 0..1 or None)] from 'Eukaryota(100);Obazoa(98);...'."""
    out = []
    for p in re.split(r'[;|]', str(s)):
        p = p.strip()
        if not p:
            continue
        m = re.match(r'^(.*?)\s*\((\d+(?:\.\d+)?)\)$', p)
        name, conf = (m.group(1).strip(), float(m.group(2))) if m else (p, None)
        if conf is not None and conf > 1:
            conf = round(conf / 100, 4)
        out.append((name, conf))
    return out


def lineage_scheme(column, parts):
    """'pr2', 'silva' or '' (FAIRe's own order, or rank prefixes) for a lineage column."""
    k = _key(column)
    first = parts[0][0].lower() if parts else ''
    if 'pr2' in k:
        return 'pr2'
    if 'silva' in k:
        return 'silva'
    if first in DOMAINS and len(parts) in PR2_RANKS and first == 'eukaryota':
        return 'pr2'
    if first in DOMAINS and len(parts) <= len(SILVA_RANKS):
        return 'silva'
    return ''


def read_lineage(column, s):
    """FAIRe taxa terms from one lineage: rank terms, and scientificName, taxonRank and
    confidence_score from the lowest name that is not a placeholder."""
    parts = lineage_parts(s)
    scheme = lineage_scheme(column, parts)
    if not scheme:
        return split_lineage(';'.join(n for n, _ in parts)), scheme
    names = PR2_RANKS.get(len(parts)) if scheme == 'pr2' else SILVA_RANKS[:len(parts)]
    if names is None:   # a PR2 lineage of another length: its last two names may still be genus and species
        names = ['?'] * (len(parts) - 2) + ['genus', 'species']
    real = [(rank, name.strip(), conf) for rank, (name, conf) in zip(names, parts)
            if name.strip() and not PLACEHOLDER.search(name.strip()) and not NOT_A_NAME.match(name.strip())]
    out = {}
    for rank, name, _ in real:
        if rank == 'species' and not SPECIES_NAME.match(name):
            continue
        if rank == 'domain':
            if name.lower() in ('bacteria', 'archaea'):
                out['kingdom'] = name   # kingdoms as well as domains
            continue
        if scheme == 'pr2' and rank not in ('genus', 'species'):
            continue
        out[rank] = name.replace('_', ' ')
    lowest = next((x for x in reversed(real) if x[0] != 'species' or SPECIES_NAME.match(x[1])), None)
    if lowest:
        rank, name, conf = lowest
        if conf is not None:
            out['confidence_score'] = conf
        if rank == 'domain' and 'kingdom' not in out:   # Eukaryota, and nothing below it
            out['scientificName'], out['taxonRank'] = name, 'other: domain'
        elif scheme == 'pr2' and rank not in ('genus', 'species', 'domain'):
            out['scientificName'] = name.replace('_', ' ')
            out['taxonRank'] = f'other: PR2 {rank}' if rank != '?' else 'other:'
    return out, scheme


def from_name(label):
    """Ranks from a name alone: binomials are species; -idae family, -inae subfamily, -oidea superfamily,
    -iformes order (zoological endings); any other single word is taken as a genus."""
    s = re.sub(r'\s+', ' ', str(label).replace('_', ' ')).strip()
    s = re.sub(r'\s+(sp|spp|cf|aff)\.?(\s.*)?$', '', s)
    words = s.split(' ')
    if len(words) >= 2 and words[0][:1].isupper() and words[1][:1].islower():
        return {'genus': words[0], 'species': ' '.join(words[:2])}, 'species'
    w = words[0]
    if w.endswith('idae'):
        return {'family': w}, 'family'
    if w.endswith('iformes'):
        return {'order': w}, 'order'
    if w.endswith('inae'):
        return {}, 'other: subfamily'
    if w.endswith('oidea'):
        return {}, 'other: superfamily'
    return {'genus': w}, 'genus'


UNNAMED_SUFFIX = re.compile(r'^(\S+)\s+(sp|spp|sp\d+|cf|aff|nr)\.?\s*\d*(\s.*)?$', re.I)
RANK_ORDER = ['kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species']
# Names that mean no assignment (NCBI's root and 'cellular organisms'), and NCBI's placeholder nodes
# for sequences placed in a group but not below it ('unclassified Paracalanus').
NO_ASSIGNMENT = re.compile(r'^(root|cellular organisms|biota|life)$', re.I)
UNCLASSIFIED_IN = re.compile(r'^(?:unclassified|environmental samples of|unidentified)\s+(\S.*)$', re.I)
# Ranks that are not ranks (NCBI's 'no rank') are left out; others not in Darwin Core's list are
# written as 'other: <rank>'.
NOT_A_RANK = {'norank', 'none', 'na', 'unranked', ''}
DWC_RANKS = {'domain', 'superkingdom', 'kingdom', 'subkingdom', 'superphylum', 'phylum', 'subphylum', 'superclass',
             'class', 'subclass', 'infraclass', 'superorder', 'order', 'suborder', 'infraorder', 'superfamily',
             'family', 'subfamily', 'tribe', 'subtribe', 'genus', 'subgenus', 'section', 'species', 'subspecies',
             'variety', 'form'}


def given_rank(r, counts):
    """A scientificName given with its taxonRank (as in Wilderlab's tables, with NCBI names and
    ranks): 'root' is no assignment, so no name, rank or taxonID is written; 'unclassified
    Paracalanus' is named Paracalanus, its rank then read from the name; the name fills its rank term (genus,
    or genus and specificEpithet for a species), and 'no rank' is left out."""
    name = re.sub(r'\s+', ' ', str(r['scientificName'])).strip()
    rank = str(r.get('taxonRank', '')).strip()
    if NO_ASSIGNMENT.match(name):
        r['verbatimIdentification'] = r.get('verbatimIdentification') or name
        for k in ('scientificName', 'taxonRank', 'taxonID'):
            r.pop(k, None)
        counts['none'] += 1
        return
    m = UNCLASSIFIED_IN.match(name)
    if m:
        r['verbatimIdentification'] = r.get('verbatimIdentification') or name
        r['scientificName'] = name = m.group(1).strip()
        r.pop('taxonID', None)   # the placeholder's ID, not the group's
        rank = ''
        counts['unclassified'] += 1
    key = _key(rank)
    if key in NOT_A_RANK:
        r.pop('taxonRank', None)
        counts['no rank'] += bool(not m)
        return
    rank = rank.lower()
    if rank not in DWC_RANKS and not rank.startswith('other:'):
        counts['other'][rank] = counts['other'].get(rank, 0) + 1
        r['taxonRank'] = f'other: {rank}'
        return
    r['taxonRank'] = rank
    words = name.split(' ')
    if rank in ('species', 'subspecies', 'variety', 'form') and len(words) >= 2:
        r.setdefault('genus', words[0])
        r.setdefault('specificEpithet', words[1])
    elif rank in RANK_ORDER[:-1]:
        if not (rank == 'kingdom' and name.lower() in DOMAIN_ONLY):
            r.setdefault(rank, name)
    elif rank in ('superkingdom', 'domain') and name.lower() not in DOMAIN_ONLY:
        r.setdefault('kingdom', name)   # Bacteria and Archaea are kingdoms in FAIRe; Eukaryota is not


def given_name(r):
    """taxonRank, and genus and specificEpithet, from a scientificName given in the table (a curated
    name, an LCA name). 'Sardinops sagax' is a species. 'Trachurus Sp', 'Diaphus Sp1' or 'Thunnus
    albacares/obesus' is named to its first word, the genus Trachurus, Diaphus or Thunnus, and kept as
    written in verbatimIdentification. A single word takes the rank of the rank column holding it, or
    else the rank its ending shows. Ranks below the name's are dropped, and a binomial's genus
    replaces the genus column's, as the name is the assignment (often the current name, where the
    genus column is out of date). Two capitalised words whose first is in no rank column, such as
    'Atlantic Salmon', are not read as a scientific name: the name is kept in
    verbatimIdentification and the rank columns name the taxon. Returns (the genus column's genus
    when it differed, or None; whether the name was cut to its first word; whether it was not read
    as a scientific name)."""
    name = re.sub(r'\s+', ' ', str(r['scientificName'])).strip()
    words = name.split(' ')
    m = UNNAMED_SUFFIX.match(name)
    if m or ('/' in name and len(words) >= 2):
        base = m.group(1) if m else words[0]
        r['verbatimIdentification'] = r.get('verbatimIdentification') or name
        name, words = base, [base]
    cut = bool(m or ('/' in name and len(words) >= 2))
    if (len(words) >= 2 and words[0][:1].isupper() and words[1][:1].isupper()
            and not any(str(r.get(k, '')).strip() == words[0] for k in RANK_ORDER[:-1])):
        r['verbatimIdentification'] = r.get('verbatimIdentification') or name
        r.pop('scientificName', None)
        return None, False, True
    clash = None
    if len(words) >= 2 and words[0][:1].isupper() and words[1][:1].islower():
        rank = 'species'
        if r.get('genus') and r['genus'] != words[0]:
            clash = r['genus']
        r['genus'] = words[0]
        r['specificEpithet'] = words[1]
        r['scientificName'] = ' '.join(words[:2])
    else:
        rank = next((k for k in RANK_ORDER[:-1] if str(r.get(k, '')).strip() == words[0]), None)
        if rank is None:
            ranks, rank = from_name(words[0])
            for k, v in ranks.items():
                r.setdefault(k, v)
        r['scientificName'] = words[0]
    if rank in RANK_ORDER:
        for k in RANK_ORDER[RANK_ORDER.index(rank) + 1:]:
            r.pop(k, None)
        if rank != 'species':
            r.pop('specificEpithet', None)
    r['taxonRank'] = rank
    return clash, cut, False


def is_lineage(column):
    """A column of lineages: taxonomy, lineage ..., or one named for a reference database or ending
    in tax (PR2 tax, Silva 138.1 tax, taxonomy_silva)."""
    k = _key(column)
    return (k in TAXA_ALIASES['lineage'] or k.endswith('tax')
            or (re.search(r'pr2|silva|unite|gtdb|midori|greengenes|rdp', k) and re.search(r'tax|lineage|classif', k)))


def taxa_rows(seq_ids, ann, taxa_df, sequences, orientation, taxa_terms, log, label, lineage_column=None,
              report_missing=True):
    """{seq_id: {FAIRe taxa term: value}}. With several lineage columns, lineage_column (or the
    first) gives the assignment; the others are noted in identificationRemarks."""
    rows = {s: {'seq_id': s} for s in seq_ids}
    for s, q in sequences.items():
        rows[s]['dna_sequence'] = q
    sources = []
    frames = []
    if ann is not None and len(ann.columns) > 1:
        frames.append(('the OTU table', ann.iloc[:, 1:]))
    if taxa_df is not None:
        idcol = _find(taxa_df.columns, 'seq_id') or taxa_df.columns[0]
        seqcol = _find(taxa_df.columns, 'dna_sequence')
        t = taxa_df.copy()
        t.index = [norm_id(v) for v in t[idcol]]
        if idcol != seqcol:
            t = t.drop(columns=[idcol])
        hit = sum(i in t.index for i in seq_ids)
        if hit == 0 and sequences and seqcol:
            # Joined on the sequence when the OTU table's identifiers were sequences.
            seq_to_id = {q: s for s, q in sequences.items()}
            t.index = [seq_to_id.get(re.sub(r'\s', '', str(v)).upper(), k) for k, v in zip(t.index, t[seqcol])]
            hit = sum(i in t.index for i in seq_ids)
        if hit == 0:
            log(f'{label}: WARNING no seq_id of the taxonomy table matches the OTU table; taxonomy not used')
        else:
            if hit < len(seq_ids):
                log(f'{label}: WARNING {len(seq_ids) - hit} of {len(seq_ids)} sequences have no row in the taxonomy table')
            frames.append(('the taxonomy table', t[~t.index.duplicated()]))
    lowercase_terms = {k.lower(): k for k in taxa_terms}
    domains = 0
    lineage_cols = []
    unused = []
    for where, f in frames:
        used = []
        for c in f.columns:
            k = _key(c)
            term = lowercase_terms.get(str(c).strip().lower())
            if term is None:
                term = next((t for t, names in TAXA_ALIASES.items() if k in names and t != 'seq_id'), None)
            if term is None and is_lineage(c):
                term = 'lineage'
            rank = RANK_NAMES.get(k)
            if term is None and rank is None:
                if not _count_like(f[c]):   # counts of samples not in the sample table are reported already
                    unused.append(str(c))
                continue
            used.append(str(c))
            for s in seq_ids:
                if s not in f.index:
                    continue
                v = f.at[s, c]
                if _blank(v):
                    continue
                v = str(v).strip() if not isinstance(v, (int, float)) else v
                if term == 'lineage':
                    rows[s].setdefault('_lineages', []).append((str(c), str(v)))
                    if str(c) not in lineage_cols:
                        lineage_cols.append(str(c))
                elif rank:
                    if rank == 'kingdom' and str(v).strip().lower() in DOMAIN_ONLY:
                        domains += 1
                    elif not NOT_A_NAME.match(str(v)):
                        rows[s][rank] = str(v).replace('_', ' ')
                elif term == 'dna_sequence' and isinstance(v, str):
                    rows[s]['dna_sequence'] = re.sub(r'\s', '', v).upper()
                elif term == 'scientificName' and NOT_A_NAME.match(str(v)):
                    continue
                elif term in NUMERIC_TERMS:
                    try:
                        x = float(str(v).replace('%', ''))
                        rows[s][term] = int(x) if x.is_integer() and '.' not in str(v) else x
                    except ValueError:
                        rows[s][term] = v   # a range such as "0.97-0.99", as FAIRe allows
                else:
                    rows[s][term] = v
        if used:
            sources.append(f"{where} ({', '.join(used[:6])}{' ...' if len(used) > 6 else ''})")
    named = derived = 0
    if lineage_column and lineage_cols and lineage_column not in lineage_cols:
        raise OtuError(f"{label}: no lineage column '{lineage_column}'; the lineage columns are "
                       + ', '.join(f"'{c}'" for c in lineage_cols))
    primary = lineage_column or (lineage_cols[0] if lineage_cols else None)
    schemes, assigned = {}, {}
    from_given, as_written, clashes, not_names = 0, 0, {}, {}
    with_rank = {'none': 0, 'unclassified': 0, 'no rank': 0, 'other': {}}
    given_ranks = sum(bool(r.get('scientificName') and r.get('taxonRank')) for r in rows.values())
    for s, r in rows.items():
        if r.get('scientificName') and r.get('taxonRank'):
            given_rank(r, with_rank)
        if '_lineages' in r:
            lins = dict(r.pop('_lineages'))
            lin = lins.get(primary)
            notes = []
            if lin is not None:
                found, scheme = read_lineage(primary, lin)
                schemes[scheme] = schemes.get(scheme, 0) + 1
                for term, value in found.items():
                    r.setdefault(term, value)
                r.setdefault('verbatimIdentification', lin)
                if scheme == 'pr2':
                    notes.append(PR2_REMARK)
            others = [f"{c}: {v}" for c, v in lins.items() if c != primary]
            if others:
                notes.append('also classified as ' + '; '.join(others))
            if notes:
                r['identificationRemarks'] = '; '.join(x for x in (r.get('identificationRemarks'), *notes) if x)[:2000]
        if r.get('scientificName') and not r.get('taxonRank'):
            from_given += 1
            clash, cut, odd = given_name(r)
            as_written += cut
            if clash:
                k = f"{r['scientificName']} (genus column {clash})"
                clashes[k] = clashes.get(k, 0) + 1
            if odd:
                k = r['verbatimIdentification']
                not_names[k] = not_names.get(k, 0) + 1
        if (not any(k in r for k in RANKS + ['scientificName', 'specificEpithet']) and orientation == 'samples as rows'
                and LATIN_NAME.match(re.sub(r'\s+', ' ', s.replace('_', ' ')).strip())):
            ranks, rank_name = from_name(s)
            r.update(ranks)
            r['verbatimIdentification'] = s
            r['taxonRank'] = rank_name
            if rank_name.startswith('other:'):
                r['scientificName'] = s
            named += 1
        elif any(k in finish_taxon(r) for k in ('scientificName', 'taxonRank')):
            derived += 1
            continue
        finish_taxon(r)
    if named:
        sources.append('the names in the table (binomials as species; -idae family, -iformes order; other '
                       'single words as genus)')
        log(f'{label}: taxonomy for {named} taxa read from their names only; ranks above them are empty '
            f'(edna2obis: match taxa can fill them from WoRMS or GBIF)')
    if sources:
        log(f"{label}: taxonomy from {'; '.join(sources)}")
    unused = list(dict.fromkeys(unused))
    if unused:
        log(f"{label}: columns not used (no FAIRe taxonomy term): {', '.join(unused[:8])}"
            + (' ...' if len(unused) > 8 else ''))
    if given_ranks:
        parts = [f'{given_ranks} names given with their rank, written to their rank term']
        if with_rank['none']:
            parts.append(f"{with_rank['none']} named root or the like (no assignment): no name written, the "
                         f"name kept in verbatimIdentification")
        if with_rank['unclassified']:
            parts.append(f"{with_rank['unclassified']} such as 'unclassified Paracalanus' named for the group, "
                         f"without the placeholder's rank or taxonID")
        if with_rank['no rank']:
            parts.append(f"{with_rank['no rank']} with 'no rank' given no taxonRank")
        if with_rank['other']:
            parts.append('ranks not in Darwin Core written as other: ' + ', '.join(
                f'{k} ({v})' for k, v in with_rank['other'].items()))
        log(f'{label}: ' + '; '.join(parts))
    if from_given:
        log(f'{label}: taxonRank read from the names given, for {from_given} rows'
            + (f"; {as_written} name{'' if as_written == 1 else 's'} such as 'Trachurus Sp' or 'Diaphus Sp1' "
               f"{'is named to its' if as_written == 1 else 'are named to their'} first word (a "
               f"genus, family or order), and kept as written in verbatimIdentification" if as_written else ''))

    def rows_of(d):
        n = sum(d.values())
        return '' if n == len(d) else f" ({n} rows)"

    if clashes:
        log(f"{label}: WARNING {len(clashes)} " + ('name has' if len(clashes) == 1 else 'names have')
            + f" a genus that differs from the genus column{rows_of(clashes)}; the name's genus is written. "
              "Check for spelling mistakes: "
            + '; '.join(list(clashes)[:6]) + (' ...' if len(clashes) > 6 else ''))
    if not_names:
        log(f"{label}: WARNING {len(not_names)} " + ('name does' if len(not_names) == 1 else 'names do')
            + f" not read as a scientific name{rows_of(not_names)}, such as a common name: "
            + '; '.join(f"'{k}'" for k in list(not_names)[:6]) + (' ...' if len(not_names) > 6 else '')
            + ". The rank columns name the taxon, and the name is kept in verbatimIdentification; check it")
    if primary:
        how = {'pr2': "as PR2 levels. FAIRe's rank terms are Linnaean ranks, so only the genus and species "
                      "are written to them; a name above genus goes in scientificName with taxonRank 'other: "
                      "PR2 <level>', and identificationRemarks notes on each row that PR2 was used",
               'silva': 'as SILVA ranks (phylum to genus)',
               '': 'in FAIRe rank order, or by rank prefix'}
        log(f"{label}: lineages read from '{primary}' " + '; '.join(how[k] for k in schemes)
            + (f"; the other lineage columns ({', '.join(c for c in lineage_cols if c != primary)}) are kept in "
               f"identificationRemarks" if len(lineage_cols) > 1 else ''))
    if domains:
        log(f'{label}: the domain Eukaryota (not a kingdom) left out of kingdom for {domains} rows')
    if derived:
        log(f"{label}: scientificName or taxonRank filled from the lowest rank given, for {derived} "
            f"row{'' if derived == 1 else 's'}")
    if primary:
        for r in rows.values():
            rk = r.get('taxonRank') or 'no name'
            assigned[rk] = assigned.get(rk, 0) + 1
        ranked = sorted(assigned.items(), key=lambda kv: -kv[1])
        log(f'{label}: lowest rank named: ' + ', '.join(f'{k} {v}' for k, v in ranked))
    no_seq = sum(not r.get('dna_sequence') for r in rows.values())
    if no_seq and report_missing:
        log(f'{label}: WARNING dna_sequence (mandatory in FAIRe) is empty for {no_seq} of {len(rows)} rows'
            + ('; the table has reads summed per taxon, without sequences' if orientation == 'samples as rows' else ''))
    return rows


def curated_final(counts, ann, column, sequences, orientation, taxa_terms, log, label, compare):
    """FAIRe's final tables from an ASV table with a column of curated names: taxaFinal with one row
    per ASV that has a curated name (its own sequence, and taxonomy from the curated name and the
    rank columns), and otuFinal with the reads of each name summed under its most abundant ASV.
    ASVs without a curated name (removed in curation) are left out of both."""
    names = {s: re.sub(r'\s+', ' ', str(v)).strip() for s, v in zip(ann.index, ann[column])
             if not _blank(v) and not NOT_A_NAME.match(str(v).strip())}
    kept = [s for s in counts.index if s in names]
    if not kept:
        raise OtuError(f"{label}: no ASV has a curated name in '{column}'")
    totals = counts.loc[kept].sum(axis=1)
    groups = {}
    for s in kept:
        groups.setdefault(names[s], []).append(s)
    rep = {n: max(ids, key=lambda s: (totals[s], -kept.index(s))) for n, ids in groups.items()}
    order = sorted(rep.values(), key=kept.index)
    by_rep = {rep[names[s]]: names[s] for s in kept}
    key = [rep[names[s]] for s in kept]
    fin = counts.loc[kept].groupby(key, sort=False).sum().loc[order]
    # Taxonomy from the curated name: other name, rank and ID columns are the preliminary assignment.
    drop = [c for c in ann.columns[1:] if c != column and (_key(c) in TAXA_ALIASES['scientificName']
            or _key(c) in TAXA_ALIASES['taxonRank'] or _key(c) in TAXA_ALIASES['taxonID'] or is_lineage(c))]
    fa = ann.loc[kept].drop(columns=drop).rename(columns={column: 'scientificName'})
    rows = taxa_rows(kept, fa, None, {s: q for s, q in sequences.items() if s in names}, orientation, taxa_terms,
                     log, label, report_missing=False)
    for n, ids in groups.items():
        if len(ids) < 2:
            continue
        r = rep[n]
        for s in ids:
            note = (f"otuFinal row for {n}: the reads of its {len(ids)} ASVs summed under this, the most abundant"
                    if s == r else f"reads summed in otuFinal under {r}, the most abundant ASV of {n}")
            rows[s]['identificationRemarks'] = '; '.join(x for x in (rows[s].get('identificationRemarks'), note) if x)
    several = sum(len(ids) > 1 for ids in groups.values())
    log(f"{label}: curated names from '{column}': {len(kept)} of {len(counts)} ASVs have one, in {len(groups)} taxa "
        f"({several} with several ASVs). As FAIRe asks, taxaFinal lists each of these ASVs, and otuFinal sums the "
        f"reads of each taxon's ASVs under its most abundant one"
        + ('' if len(counts) == len(kept) else '; the ASV without a curated name is in the raw tables only'
           if len(counts) - len(kept) == 1 else
           f'; the {len(counts) - len(kept)} ASVs without a curated name are in the raw tables only'))
    assert set(by_rep) == set(order)
    # taxaFinal has a row for each ASV, so a sequence taken from the raw table is compared ASV by ASV
    return {'counts': fin, 'taxa': rows, 'compare': compare.loc[kept]}


def finish_taxon(r):
    """specificEpithet, scientificName and taxonRank from the ranks, where not given. Returns the
    terms filled."""
    before = set(r)
    sp = r.pop('species', None)
    if sp:
        words = sp.split()
        if len(words) >= 2:
            r.setdefault('genus', words[0])
            r.setdefault('specificEpithet', words[1])
            r.setdefault('scientificName', ' '.join(words[:2]))
        elif r.get('genus'):
            r.setdefault('specificEpithet', sp)
            r.setdefault('scientificName', f"{r['genus']} {sp}")
    lowest = next((k for k in ['specificEpithet', 'genus', 'family', 'order', 'class', 'phylum', 'kingdom']
                   if r.get(k)), None)
    if lowest:
        rank = 'species' if lowest == 'specificEpithet' else lowest
        if rank == 'species':
            ep = r['specificEpithet']
            r.setdefault('scientificName', ep if ' ' in ep else f"{r.get('genus', '')} {ep}".strip())
        else:
            r.setdefault('scientificName', r[lowest])
        r.setdefault('taxonRank', rank)
    return set(r) - before - {'genus', 'specificEpithet'}


def _find(columns, term):
    names = TAXA_ALIASES.get(term, [])
    for c in columns:
        if str(c).strip().lower() == term.lower() or _key(c) in names:
            return c
    return None
