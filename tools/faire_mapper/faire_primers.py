"""faire_primers: look up PCR primer sequences by assay name, primer name or reference.

Methods sections often name or cite their primers ("the MiFish primer set", "Bact16S_515F",
"universal eukaryote 18S assay (Pochon et al., 2013)") without giving the sequences, which FAIRe
requires (pcr_primer_forward, pcr_primer_reverse). This script finds candidate primer pairs in a
primer table and proposes them for review. It never decides between candidates.

Commands:
  build   make or update a primer table (TSV). Reads Tables S3 and S4 of Takahashi et al. 2023,
          the bacteria and archaea register (sheet "Primer pairs"), and spreadsheets or TSVs with
          this table's own columns. With --base, the new rows are merged into an existing table.
  lookup  find primer pairs for names or references.
  text    find primer pairs named or cited in a methods text.

The tools ship a table built from these sources (primers/faire_primers.tsv, see primers/README.md).
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

import pandas as pd

__version__ = '0.6.0'
# FAIRe term names wherever FAIRe has a term; the rest describe the table itself.
COLUMNS = ['primer_pair_id', 'assay_name', 'assay_type', 'targetTaxonomicAssay', 'targetTaxonomicScope',
           'target_gene', 'target_subfragment',
           'pcr_primer_name_forward', 'pcr_primer_forward', 'pcr_primer_reference_forward',
           'pcr_primer_name_reverse', 'pcr_primer_reverse', 'pcr_primer_reference_reverse',
           'ampliconSize', 'annealingTemp', 'pcr_cycles', 'pcr_rep',
           'bibliographicCitation', 'other_names', 'record_ids', 'notes', 'source']
OLD_NAMES = {'target_group': 'targetTaxonomicScope'}   # columns of earlier versions of the table
BUNDLED = Path(__file__).resolve().parent / 'primers' / 'faire_primers.tsv'
IUPAC = re.compile(r'^[ACGTURYSWKMBDHVNI]+$')
NOT_GIVEN = {'', 'nm', 'na', 'nan', 'none', 'see doi (column k)'}
GENES = {'12s': '12S', '16s': '16S', '18s': '18S', '28s': '28S', 'coi': 'COI', 'co1': 'COI', 'cox1': 'COI',
         'cytb': 'CytB', 'cyt b': 'CytB', 'cytochrome b': 'CytB', 'its': 'ITS', 'its1': 'ITS', 'its2': 'ITS',
         'd-loop': 'D-loop', 'control region': 'D-loop', 'nd1': 'ND1', 'nd2': 'ND2', 'nd4': 'ND4', 'nd5': 'ND5',
         'nd6': 'ND6', 'rbcl': 'rbcL', 'trnl': 'trnL', '23s': '23S'}
# Short gene names to the FAIRe target_gene vocabulary. 16S depends on the target: mitochondrial
# for animals, the prokaryote gene for bacteria and archaea.
FAIRE_GENES = {'12S': '12S rRNA (SSU mitochondria)', '18S': '18S rRNA (SSU eukaryote)', '28S': '28S rRNA (LSU eukaryote)',
               '23S': '23S rRNA (LSU prokaryote)', 'CytB': 'CytB', 'COI': 'COI', 'ITS': 'ITS', 'D-loop': 'D-loop',
               'rbcL': 'rbcL', 'trnL': 'trnL', 'ND1': 'ND1', 'ND2': 'ND2', 'ND3': 'ND3', 'ND4': 'ND4', 'ND5': 'ND5',
               'ND6': 'ND6'}


def faire_gene(value, prokaryote=False):
    """A gene as a FAIRe target_gene value: 'Cyt B' -> CytB, '12S' -> 12S rRNA (SSU mitochondria)."""
    v = given(value)
    if not v:
        return ''
    if v in FAIRE_GENES.values() or v in ('16S rRNA (LSU mitochondria)', '16S rRNA (SSU prokaryote)'):
        return v   # already a FAIRe value, such as the prokaryote 16S of a bacterial assay
    short = gene_of(v)
    if short == '16S':
        return '16S rRNA (SSU prokaryote)' if prokaryote else '16S rRNA (LSU mitochondria)'
    if short in FAIRE_GENES:
        return FAIRE_GENES[short]
    if v in FAIRE_GENES.values() or v.startswith('other:'):
        return v
    return f'other: {v}'


DESCRIPTORS = re.compile(r'\b(original|updated|variant|modified|common extended form)\b', re.I)


def given(v):
    return '' if v is None or str(v).strip().lower() in NOT_GIVEN else str(v).strip()


def clean_seq(s):
    s = re.sub(r'[\s\-]', '', given(s)).upper()
    return s if s and IUPAC.match(s) else ''


def pair_id(fwd, rev):
    """Stable identifier of a primer pair, from its two sequences."""
    return 'pp_' + hashlib.sha1(f'{fwd}|{rev}'.encode()).hexdigest()[:10]


def gene_of(v):
    """Short gene name: 'Cyt B' -> CytB, '12S rRNA (SSU mitochondria)' (FAIRe target_gene) -> 12S."""
    v = re.sub(r'^other:\s*', '', given(v))
    if v.lower() in GENES:
        return GENES[v.lower()]
    m = re.match(r'\s*(\d\dS|COI|CO1|COX1|CytB|Cyt b|ITS\d?|D-loop|ND\d|rbcL|trnL)\b', v, re.I)
    return GENES.get(m.group(1).lower(), m.group(1)) if m else v


def key(name):
    """Normalised name for matching: lower case, letters and digits only."""
    return re.sub(r'[^a-z0-9]', '', str(name).lower())


def ref_key(ref):
    """'Pochon et al., 2013' -> 'pochon 2013'; 'Sherwood and Presting 2007' -> 'sherwood 2007'."""
    m = re.match(r'\s*([A-Za-zÀ-ɏ\-\']+).*?((?:19|20)\d\d)', given(ref))
    return f'{m.group(1).lower()} {m.group(2)}' if m else ''


# ------------------------------------------------------------------ reading sources

def read_takahashi(path, label=None):
    """Takahashi et al. 2023, Sci. Total Environ. 873:162322, Table S3 (species-specific) or S4 (metabarcoding)."""
    raw = pd.read_excel(path, dtype=str)
    raw.columns = [str(c).strip() for c in raw.columns]
    fseq = next(c for c in raw.columns if c.startswith('Forward Sequence'))
    rseq = next(c for c in raw.columns if c.startswith('Reverse Sequence'))
    table = 'S4' if 'Assay name' in raw.columns else 'S3'
    rows, problems = [], []
    for i, r in raw.iterrows():
        f, rv = clean_seq(r.get(fseq)), clean_seq(r.get(rseq))
        where = f'{label or Path(path).name} row {i + 2}'
        for side, raw_s, s in (('forward', r.get(fseq), f), ('reverse', r.get(rseq), rv)):
            if given(raw_s) and not s:
                problems.append((where, f'{side} sequence is not a plain IUPAC sequence: {given(raw_s)[:60]}'))
        if not (f or rv):
            continue
        rows.append({
            'assay_name': given(r.get('Assay name')), 'assay_type': 'metabarcoding' if table == 'S4' else 'targeted',
            'targetTaxonomicAssay': given(r.get('Target Taxa Scientific Name(s)')),
            'targetTaxonomicScope': given(r.get('Target Group')),
            'target_gene': faire_gene(r.get('Barcode Region')),
            'bibliographicCitation': (f"https://doi.org/{given(r.get('DOI'))}" if given(r.get('DOI')) else ''),
            'pcr_primer_name_forward': given(r.get('Forward Name')), 'pcr_primer_forward': f,
            'pcr_primer_reference_forward': given(r.get('Forward Reference')),
            'pcr_primer_name_reverse': given(r.get('Reverse Name')), 'pcr_primer_reverse': rv,
            'pcr_primer_reference_reverse': given(r.get('Reverse Reference')),
            'ampliconSize': given(r.get('Amplicon Size', r.get('Amplicon size'))),
            'source': f'Takahashi et al. 2023 Table {table} row {i + 2}',
        })
    return rows, problems


def _labelled_seqs(text):
    """'515F: GTGY...; 806R: GGAC...' -> [('515F', 'GTGY...'), ('806R', 'GGAC...')]"""
    out = []
    for part in str(text).split(';'):
        if ':' in part:
            label, rest = part.split(':', 1)
            m = re.match(r'\s*([A-Za-z]+)', rest)
            out.append((label.strip(), clean_seq(m.group(1)) if m else '', rest.strip()))
    return out


def read_prokaryote_register(path, label=None):
    """The bacteria and archaea primer register (sheet 'Primer pairs': Basis, Formal primer pair,
    Common name(s), Primer sequence(s), Intended target, 16S region, ...)."""
    raw = pd.read_excel(path, sheet_name='Primer pairs', dtype=str)
    rows, problems = [], []
    for i, r in raw.iterrows():
        where = f'{label or Path(path).name} row {i + 2}'
        seqs = _labelled_seqs(r.get("Primer sequence(s), 5' to 3'", ''))
        if len(seqs) != 2 or not all(s for _, s, _ in seqs):
            problems.append((where, 'expected two labelled sequences, "name: SEQUENCE; name: SEQUENCE"'))
            continue
        (fl, f, fraw), (rl, rv, rraw) = seqs
        notes = [given(r.get('Notes'))]
        for lab, raw_s in ((fl, fraw), (rl, rraw)):
            extra = re.sub(r'^[A-Za-z]+\s*', '', raw_s).strip()
            if extra:
                notes.append(f'{lab}: {extra}')
        fname, rname = DESCRIPTORS.sub('', fl).strip(), DESCRIPTORS.sub('', rl).strip()
        others = []
        for field in ('Formal primer pair', 'Common name(s)'):
            for group in given(r.get(field)).split(';'):
                others += [DESCRIPTORS.sub('', n).strip() for n in group.split('/') if n.strip()]
        refs = re.findall(r'\(([^)]+)\)', given(r.get('Formal primer pair')))
        basis = given(r.get('Basis'))
        fref = refs[0] if len(refs) == 2 else ('Klindworth et al., 2013' if basis == 'Klindworth' else '')
        rref = refs[1] if len(refs) == 2 else fref
        rows.append({
            'assay_name': given(r.get('Common name(s)')), 'assay_type': 'metabarcoding',
            'targetTaxonomicAssay': given(r.get('Intended target')), 'targetTaxonomicScope': given(r.get('Intended target')),
            'target_gene': faire_gene('16S', prokaryote=True), 'target_subfragment': given(r.get('16S region')),
            'pcr_primer_name_forward': fname, 'pcr_primer_forward': f, 'pcr_primer_reference_forward': fref,
            'pcr_primer_name_reverse': rname, 'pcr_primer_reverse': rv, 'pcr_primer_reference_reverse': rref,
            'ampliconSize': given(r.get('Approx. amplicon (bp)')).lstrip('~'),
            'other_names': '; '.join(dict.fromkeys(n for n in others if n and n not in (fname, rname))),
            'notes': '; '.join(n for n in notes if n),
            'source': f'Bacteria and archaea primer register ({basis}) row {i + 2}; '
                      f'{given(r.get("Source URL"))}'.rstrip('; '),
        })
    return rows, problems


def read_own_format(path, label=None):
    """A spreadsheet or TSV with this table's columns (as written by build)."""
    if str(path).lower().endswith(('.xlsx', '.xls')):
        raw = pd.read_excel(path, dtype=str).fillna('')
    else:
        raw = pd.read_csv(path, sep='\t', dtype=str, keep_default_na=False)
    rows, problems = [], []
    for i, r in raw.iterrows():
        f, rv = clean_seq(r.get('pcr_primer_forward')), clean_seq(r.get('pcr_primer_reverse'))
        replaces = [x.strip() for x in str(given(r.get('replaces', ''))).split(';') if x.strip()]
        if not (given(r.get('pcr_primer_forward')) or given(r.get('pcr_primer_reverse'))) and replaces:
            # A row with no sequences that names pairs in 'replaces' removes them (a pair entered in error).
            rows.append({'_remove': replaces, 'notes': given(r.get('notes')),
                         'source': given(r.get('source')) or f'{label or Path(path).name} row {i + 2}'})
            continue
        if not (f and rv):
            problems.append((f'{label or Path(path).name} row {i + 2}', 'needs a forward and a reverse IUPAC sequence'))
            continue
        for old, new in OLD_NAMES.items():
            if old in r and new not in r:
                r[new] = r[old]
        row = {c: given(r.get(c, '')) for c in COLUMNS}
        prok = any(w in row['targetTaxonomicScope'].lower() for w in ('bacteri', 'archae', 'prokaryot'))
        row.update(pcr_primer_forward=f, pcr_primer_reverse=rv, target_gene=faire_gene(row['target_gene'], prok))
        if not row['source']:
            row['source'] = f'{label or Path(path).name} row {i + 2}'
        # A curation row can replace a pair it corrects: give the old pair's primer_pair_id in 'replaces'.
        row['_replaces'] = [x.strip() for x in str(given(r.get('replaces', ''))).split(';') if x.strip()]
        rows.append(row)
    return rows, problems


def read_faire_register(path, label=None):
    """A primer register already in FAIRe terms: sheets 'targeted_assays' and 'metabarcoding_assays' with
    columns such as primer_record_id, assay_type, assay_name, targetTaxonomicAssay, target_gene,
    pcr_primer_forward ... (the metazoan register compiled from Takahashi et al. 2023)."""
    xl = pd.ExcelFile(path)
    rows, problems = [], []
    for sheet in [s for s in xl.sheet_names if s in ('targeted_assays', 'metabarcoding_assays')]:
        raw = pd.read_excel(path, sheet_name=sheet, dtype=str)
        for i, r in raw.iterrows():
            where = f'{label or Path(path).name} {sheet} row {i + 2}'
            f, rv = clean_seq(r.get('pcr_primer_forward')), clean_seq(r.get('pcr_primer_reverse'))
            for side, raw_s, sq in (('forward', r.get('pcr_primer_forward'), f), ('reverse', r.get('pcr_primer_reverse'), rv)):
                if given(raw_s) and not sq:
                    problems.append((where, f'{side} sequence is not a plain IUPAC sequence: {given(raw_s)[:60]}'))
            if not (f or rv):
                continue
            cite = given(r.get('bibliographicCitation'))
            rows.append({
                'assay_name': given(r.get('assay_name')), 'assay_type': given(r.get('assay_type')),
                'targetTaxonomicAssay': given(r.get('targetTaxonomicAssay')),
                'targetTaxonomicScope': given(r.get('targetTaxonomicScope')),
                'target_gene': faire_gene(r.get('target_gene')),
                'pcr_primer_name_forward': given(r.get('pcr_primer_name_forward')), 'pcr_primer_forward': f,
                'pcr_primer_reference_forward': given(r.get('pcr_primer_reference_forward')),
                'pcr_primer_name_reverse': given(r.get('pcr_primer_name_reverse')), 'pcr_primer_reverse': rv,
                'pcr_primer_reference_reverse': given(r.get('pcr_primer_reference_reverse')),
                'ampliconSize': given(r.get('ampliconSize')),
                'bibliographicCitation': cite if not cite or cite.startswith('http') else f'https://doi.org/{cite}',
                'record_ids': given(r.get('primer_record_id')),
                'notes': given(r.get('curation_note')),
                'source': f"{given(r.get('source_dataset')) or 'FAIRe primer register'}"
                          + (f" row {given(r.get('source_row'))}" if given(r.get('source_row')) else '')
                          + f" ({label or Path(path).name}, {given(r.get('primer_record_id'))})",
            })
    return rows, problems


def read_source(path, label=None):
    p = str(path)
    if p.lower().endswith(('.xlsx', '.xls')):
        xl = pd.ExcelFile(p)
        first = pd.read_excel(p, sheet_name=xl.sheet_names[0], nrows=0)
        cols = [str(c).strip() for c in first.columns]
        if 'Primer pairs' in xl.sheet_names:
            return read_prokaryote_register(p, label)
        if {'targeted_assays', 'metabarcoding_assays'} & set(xl.sheet_names):
            return read_faire_register(p, label)
        if any(c.startswith('Forward Sequence') for c in cols):
            return read_takahashi(p, label)
        if 'pcr_primer_forward' in cols:
            return read_own_format(p, label)
        raise SystemExit(f'ERROR: {label or Path(p).name}: not a primer table this script knows. Use the columns '
                         f'of the bundled table ({", ".join(COLUMNS[1:])}).')
    return read_own_format(p, label)


def build(inputs, base=None, labels=None):
    """Combine sources into one table. Rows with the same pair of sequences are merged: later
    inputs fill in or replace their fields, names are kept as other names, and sources are listed."""
    problems = []
    table = {}
    if base is not None:
        for r in load(base).to_dict('records'):
            table[r['primer_pair_id'] or pair_id(r['pcr_primer_forward'], r['pcr_primer_reverse'])] = r
    labels = list(labels or [])
    for n, p in enumerate(inputs):
        rows, probs = read_source(p, labels[n] if n < len(labels) else None)
        problems += probs
        for r in rows:
            if '_remove' in r:
                for old_id in r['_remove']:
                    gone = table.pop(old_id, None)
                    if gone is None:
                        problems.append((r['source'], f'removes {old_id}, which is not in the table'))
                    else:
                        problems.append((r['source'], f"removed {old_id} ({gone['assay_name'] or 'no name'}: "
                                                      f"{gone['pcr_primer_forward']} / {gone['pcr_primer_reverse']})"
                                                      + (f"; {r['notes']}" if r['notes'] else '')))
                continue
            for old_id in r.get('_replaces', []):
                gone = table.pop(old_id, None)
                if gone is None:
                    problems.append((r.get('source', ''), f'replaces {old_id}, which is not in the table'))
                else:
                    was = f"replaces {old_id} ({gone['pcr_primer_forward']} / {gone['pcr_primer_reverse']})"
                    r['notes'] = '; '.join(x for x in (r.get('notes', ''), was) if x)
            r = {c: r.get(c, '') for c in COLUMNS}
            pid = pair_id(r['pcr_primer_forward'], r['pcr_primer_reverse'])
            r['primer_pair_id'] = pid
            old = table.get(pid)
            if old is None:
                table[pid] = r
                continue
            merged = {c: (r[c] or old.get(c, '')) for c in COLUMNS}
            names = [n for n in (old.get('other_names', '').split('; ') + r['other_names'].split('; ')
                                 + [old.get('pcr_primer_name_forward', ''), old.get('pcr_primer_name_reverse', ''),
                                    old.get('assay_name', '')]) if n]
            merged['other_names'] = '; '.join(dict.fromkeys(
                n for n in names if n not in (merged['pcr_primer_name_forward'], merged['pcr_primer_name_reverse'],
                                              merged['assay_name'])))
            for col in ('source', 'record_ids', 'notes'):
                if r[col] and r[col] not in old.get(col, ''):
                    merged[col] = '; '.join(x for x in (old.get(col, ''), r[col]) if x)
            table[pid] = merged
    t = pd.DataFrame(list(table.values()), columns=COLUMNS).fillna('')
    # The same two primers listed in opposite orientations stay separate rows; report them.
    by_seq = {(r['pcr_primer_forward'], r['pcr_primer_reverse']): r for r in table.values()}
    for (f, rv), r in by_seq.items():
        other = by_seq.get((rv, f))
        if other is not None and f and rv and f < rv:
            problems.append(('table', f"{r['assay_name'] or r['primer_pair_id']} and {other['assay_name'] or other['primer_pair_id']} "
                                      f"are the same primers in opposite orientations ({f} / {rv})"))
    # The same primer name for different sequences is common (515F, 806R); report it for curators.
    for side in ('forward', 'reverse'):
        name, seq = f'pcr_primer_name_{side}', f'pcr_primer_{side}'
        g = t[t[name] != ''].groupby(t[name].map(key))[seq].nunique()
        for n in g[g > 1].index:
            problems.append(('table', f'{side} primer name {n} is used for {g[n]} different sequences'))
    return t, problems


def load(*paths, labels=None):
    """Read one or more primer tables; rows of later tables replace earlier rows with the same pair.
    Tables other than the bundled one are checked as they are read, and bad rows are left out."""
    parts = []
    labels = dict(labels or {})
    for p in paths:
        if Path(p).resolve() == BUNDLED:
            t = pd.read_csv(p, sep='\t', dtype=str, keep_default_na=False)
        else:
            rows, problems = read_own_format(p, labels.get(str(p)))
            for where, why in problems:
                sys.stderr.write(f'WARNING: {where} left out: {why}\n')
            t = pd.DataFrame(rows)
        t = t.rename(columns={o: n for o, n in OLD_NAMES.items() if o in t and n not in t})
        for c in COLUMNS:
            if c not in t:
                t[c] = ''
        t['primer_pair_id'] = [pid or pair_id(f, r) for pid, f, r in
                               zip(t.primer_pair_id, t.pcr_primer_forward, t.pcr_primer_reverse)]
        parts.append(t[COLUMNS])
    t = pd.concat(parts, ignore_index=True)
    return t.drop_duplicates('primer_pair_id', keep='last').reset_index(drop=True)


# ------------------------------------------------------------------ matching

POSITION_NAME = re.compile(r'^\d{3,4}[fr]$')   # 515f, 806r, 1391f


def _names(r):
    names = [r.assay_name, r.pcr_primer_name_forward, r.pcr_primer_name_reverse]
    names += [n for n in str(r.other_names).split(';') if n.strip()]
    keys = [key(n) for n in names if n]
    keys += [key(p) for n in names if '/' in n for p in n.split('/')]   # assay names written "fwd/rev"
    return [k for k in keys if k]


_INDEX = {}


def _index(t):
    """Per row of the table: its name keys, reference keys, reference authors and gene, worked out
    once per table (a methods text looks up every word in it)."""
    hit = _INDEX.get(id(t))
    if hit is not None and hit[0] is t and hit[2] == len(t):   # rebuilt when rows are added
        return hit[1]
    rows = []
    for i, r in t.iterrows():
        refs = (ref_key(r.pcr_primer_reference_forward), ref_key(r.pcr_primer_reference_reverse))
        rows.append((i, _names(r), refs, {x.split(' ')[0] for x in refs} - {''}, gene_of(r.target_gene).lower()))
    _INDEX.clear()
    _INDEX[id(t)] = (t, rows, len(t))
    return rows


def _match_rows(t, query):
    """Rows whose assay or primer name matches the query, best matches first."""
    q = key(query)
    if len(q) < 2:
        return []
    short = len(q) < 3   # a two-letter name such as WV: exact matches only
    out = []
    as_ref = ref_key(query) if re.search(r'(19|20)\d\d', query) else ''
    parts = None
    for i, keys, refs, authors, gene in _index(t):
        if as_ref:   # a citation such as "Pochon et al., 2013": match the primer references only
            if as_ref in refs:
                out.append((1, i, 'reference'))
            continue
        if q in keys:
            out.append((3, i, 'name'))
        elif short:
            continue
        elif any(min(len(k), len(q)) >= 5 and (k in q or q in k) for k in keys):
            # e.g. ILF_mlCOIintF and mlCOIintF, Riaz_12S_V5F and 12S-V5-F, MiFish and MiFish-U-F
            out.append((2, i, 'part of name'))
        elif any(POSITION_NAME.match(k) and q.endswith(k) and not q[:-len(k)][-1:].isdigit() for k in keys):
            # position names at the end of a longer name, e.g. Bact16S_515F and 515F
            out.append((2, i, 'part of name'))
        else:
            # Assay names that join an author and a gene, e.g. LerayCOI or COILeray
            if parts is None:
                parts = {w.lower() for w in re.findall(r'[A-Z][a-z]{3,}|[a-z]{4,}', query)}
            if parts & authors and gene and gene in query.lower():
                out.append((1, i, 'author and gene'))
    return sorted(out, key=lambda x: -x[0])


def lookup(t, query, gene=None):
    rows = []
    for rank, i, how in _match_rows(t, query):
        r = t.loc[i]
        if gene and r.target_gene and gene_of(gene).lower() != gene_of(r.target_gene).lower():
            continue
        rows.append({**r.to_dict(), 'query': query, 'matched_by': how, 'rank': rank})
    best = max((x['rank'] for x in rows), default=0)
    return [x for x in rows if x['rank'] == best]


def compatible(a, b):
    """True when two primer sequences of the same length agree at every position, allowing IUPAC codes."""
    codes = {'A': 'A', 'C': 'C', 'G': 'G', 'T': 'TU', 'U': 'TU', 'R': 'AG', 'Y': 'CTU', 'S': 'CG', 'W': 'ATU',
             'K': 'GTU', 'M': 'AC', 'B': 'CGTU', 'D': 'AGTU', 'H': 'ACTU', 'V': 'ACG', 'N': 'ACGTU', 'I': 'ACGTU'}
    return len(a) == len(b) and all(set(codes.get(x, x)) & set(codes.get(y, y)) for x, y in zip(a, b))


def pairs(cands):
    """Distinct forward/reverse sequence pairs among candidates."""
    return sorted({(c['pcr_primer_forward'], c['pcr_primer_reverse']) for c in cands})


REF_IN_TEXT = re.compile(r"([A-Z][A-Za-zÀ-ɏ\-']+)(?:,? (?:et al\.?|and [A-Z][A-Za-z\-']+|& [A-Z][A-Za-z\-']+))?,?\s*\(?((?:19|20)\d\d)[a-z]?")
# Words that are primer names in some tables but ordinary words in methods text.
STOP = {'forward', 'reverse', 'primer', 'primers', 'probe', 'universal', 'fish', 'teleost', 'vertebrate',
        'mammal', 'mammals', 'bacteria', 'bacterial', 'eukaryote', 'metazoa', 'control', 'water', 'sample'}


def _name_like(word):
    """A word that looks like a primer or assay name: has a digit, an inner capital, '_' or '-'."""
    return bool(re.search(r'\d|[a-z][A-Z]|[_\-]', word))


def from_text(t, text):
    """Primer pairs named or cited in a methods text, keyed by the words that matched."""
    found = {}
    cited_authors = set()
    for sentence in re.split(r'(?<=[.;])\s+(?=[A-Z(])', text):
        genes = {gene_of(g).lower() for g in re.findall(r'(?<![0-9])(\d\dS|COI|CO1|cox1|CytB|cyt b|ITS\d?|D-loop|ND\d)(?![a-z])', sentence, re.I)}
        for m in REF_IN_TEXT.finditer(sentence):
            ref = f'{m.group(1)} et al., {m.group(2)}'
            cands = [c for c in lookup(t, ref) if c['matched_by'] == 'reference'
                     and c['target_gene'] and gene_of(c['target_gene']).lower() in genes]
            if cands:   # a citation counts only when the sentence names the primers' gene
                found.setdefault(m.group(0).strip(), []).extend(cands)
                cited_authors.add(key(m.group(1)))
    words = set(re.findall(r'[A-Za-z0-9][A-Za-z0-9_\-]{2,}[A-Za-z0-9]', text))
    words |= {p for w in list(words) for p in w.split('_') if len(p) >= 4}
    for w in sorted(words):
        k = key(w)
        if k in STOP or k in cited_authors or k.isdigit() or len(k) < 4:
            continue
        compound = w.count('_') >= 2   # e.g. a file name; its parts are checked on their own
        for c in lookup(t, w):
            if c['matched_by'] == 'name' or (c['matched_by'] == 'part of name' and _name_like(w) and not compound):
                found.setdefault(w, []).append(c)
    return found


# Primer sequences written in a text: 15 to 45 IUPAC letters (I for inosine), in capitals.
SEQ_IN_TEXT = re.compile(r'(?<![A-Za-z0-9])([ACGTURYSWKMBDHVNI]{15,45})(?![A-Za-z0-9])')
# Illumina adapters and overhangs, which methods often print with the primers; a fusion primer
# keeps only the part after them.
ADAPTERS = ('AATGATACGGCGACCACCGAGATCTACAC', 'CAAGCAGAAGACGGCATACGAGAT', 'TCGTCGGCAGCGTCAGATGTGTATAAGAGACAG',
            'GTCTCGTGGGCTCGGAGATGTGTATAAGAGACAG', 'ACACTCTTTCCCTACACGACGCTCTTCCGATCT',
            'GTGACTGGAGTTCAGACGTGTGCTCTTCCGATCT', 'ACACTGACGACATGGTTCTACA', 'TACGGTAGCAGAGACTTGGTCT')
NAME_BEFORE = re.compile(r"([A-Za-z0-9][A-Za-z0-9_\-/.']*[A-Za-z0-9])[\s:(=\[]*$")


def _primer_part(s):
    """The locus-specific part of a sequence, without a leading adapter; '' for an adapter alone."""
    for a in ADAPTERS:
        if s.startswith(a):
            s = s[len(a):]
        elif a.startswith(s) or a in s and len(s) - len(a) < 15:
            return ''
    return s if len(s) >= 15 and s.count('N') <= len(s) // 3 else ''


GENE_WORD = re.compile(r'^(mt)?(\d\dS|COI|CO1|cox1|CytB|ITS\d?|ND\d|V\d+)$', re.I)
FORWARD_NAME = re.compile(r'(f|fw|fwd|forward)\d*$|fwd|forward', re.I)
REVERSE_NAME = re.compile(r'(r|rv|rev|reverse)\d*$|rev|reverse', re.I)


def sequences_in_text(text):
    """Primer sequences written in the text, in order: (sequence, the name written just before it
    (TAReuk454FWD1 (CCAGCASC...)), unit number, line number, the sentence or row it is in)."""
    out, n = [], 0
    # A sequence broken across two lines, as text taken from a PDF table often has it
    # (GGWACWGGWTGAACWGTWTAYCC / YCC): a line of one sequence, then a line of a few IUPAC letters.
    text = re.sub(r'(?m)^(\s*[ACGTURYSWKMBDHVNI]{12,45})\s*\n\s*([ACGTURYSWKMBDHVNI]{1,14})\s*$', r'\1\2', text)
    for li, line in enumerate(text.splitlines()):
        for unit in re.split(r'(?<=[.;])\s+(?=[A-Z(])', line):
            n += 1
            for m in SEQ_IN_TEXT.finditer(unit):
                s = _primer_part(m.group(1))
                if not s:
                    continue
                before = NAME_BEFORE.search(unit[max(0, m.start() - 40):m.start()])
                name = before.group(1) if before else ''
                if (not name or not _name_like(name) or SEQ_IN_TEXT.fullmatch(name) or GENE_WORD.match(name)
                        or key(name) in STOP or re.fullmatch(r"\d+['′]?", name)):
                    name = ''
                out.append((s, name, n, li, unit.strip()))
    return out


def _orientation(name):
    if not name:
        return ''
    f, r = bool(FORWARD_NAME.search(name)), bool(REVERSE_NAME.search(name))
    return 'forward' if f and not r else ('reverse' if r and not f else '')


def _table_matches(t, f, r):
    """Table rows for a written pair: exact, then written reverse first, then base for base allowing
    IUPAC codes (only when nothing matches exactly)."""
    exact = [(i, 'sequences in the text') for i, row in t.iterrows()
             if row.pcr_primer_forward == f and row.pcr_primer_reverse == r]
    if exact:
        return exact
    swapped = [(i, 'sequences in the text (reverse written first)') for i, row in t.iterrows()
               if row.pcr_primer_forward == r and row.pcr_primer_reverse == f]
    if swapped:
        return swapped
    return [(i, 'sequences in the text (matching allowing IUPAC codes)') for i, row in t.iterrows()
            if compatible(row.pcr_primer_forward, f) and compatible(row.pcr_primer_reverse, r)]


def sequence_candidates(t, text):
    """Primer pairs whose sequences are written in the text, as (row, evidence), found in turn:
    1. sequences written together in one sentence or table row, paired in order;
    2. sequences on rows of their own that are the two primers of a pair in the table (text taken
       from a PDF often lists them out of order);
    3. a sequence on a row of its own named as a forward primer with the next one, within three
       lines, named as a reverse primer (Lab-F ACGT... / Lab-R TTGC...).
    Each pair is named from the table when its sequences match a pair there. Sequences left over
    are listed one by one, as their pairing is not clear."""
    occ = sequences_in_text(text)
    by_unit = {}
    for k, o in enumerate(occ):
        by_unit.setdefault(o[2], []).append(k)
    pairs_, used = [], set()
    for ks in by_unit.values():
        if len(ks) >= 2:
            for a, b in zip(ks[0::2], ks[1::2]):
                pairs_.append((occ[a], occ[b]))
                used |= {a, b}
    out, matched = [], set()

    def add(f_o, r_o):
        f, r = f_o[0], r_o[0]
        hits = _table_matches(t, f, r)
        if hits:
            out.extend(({**t.loc[i].to_dict(), 'matched_by': how, 'rank': 4}, f'{f} / {r}') for i, how in hits)
        else:
            line = f_o[4] if f_o[4] == r_o[4] else f'{f_o[4]} ... {r_o[4]}'
            out.append((_as_written(f, r, f_o[1], r_o[1], line), f'{f} / {r}'))
        matched.update({f, r})
    for f_o, r_o in pairs_:
        add(f_o, r_o)
    single = [k for k in range(len(occ)) if k not in used and occ[k][0] not in matched]
    seqs = {occ[k][0]: k for k in single}
    for exact in (True, False):
        for _, row in t.iterrows():
            f, r = row.pcr_primer_forward, row.pcr_primer_reverse
            if not f or not r:
                continue
            same = (lambda s, a: s == a) if exact else compatible
            # A primer shared by two pairs (two forward primers with one reverse) can be used twice,
            # as long as the other primer is new.
            fa = next((s for s in seqs if same(s, f)), None)
            fb = next((s for s in seqs if same(s, r) and s != fa), None)
            if fa and fb and not (fa in matched and fb in matched):
                add(occ[seqs[fa]], occ[seqs[fb]])
                used |= {seqs[fa], seqs[fb]}
    single = [k for k in single if k not in used and occ[k][0] not in matched]
    for a, b in zip(single, single[1:]):
        if a in used or b in used:
            continue
        oa, ob = occ[a], occ[b]
        if ob[3] - oa[3] <= 3 and _orientation(oa[1]) == 'forward' and _orientation(ob[1]) == 'reverse':
            add(oa, ob)
            used |= {a, b}
    for k in single:
        if k in used or occ[k][0] in matched:
            continue
        s, name, _, _, line = occ[k]
        side = _orientation(name) or 'forward'
        row = _as_written(s if side == 'forward' else '', s if side == 'reverse' else '',
                          name if side == 'forward' else '', name if side == 'reverse' else '', line)
        row['matched_by'] = 'a sequence in the text (not paired)'
        row['notes'] = (f"pairing not clear{'' if _orientation(name) else '; forward or reverse not known'}; "
                        f"as written: {line[:200]}")
        out.append((row, s))
        matched.add(s)
    return out


def _as_written(f, r, fname, rname, line):
    """A candidate pair as the text gives it, for sequences not in the primer table."""
    genes = {gene_of(g) for g in re.findall(r'(?<![0-9])(\d\dS|COI|CO1|cox1|CytB|ITS\d?|ND\d)(?![a-z])', line, re.I)}
    refs = [f'{m.group(1)} et al., {m.group(2)}' for m in REF_IN_TEXT.finditer(line)]
    row = {c: '' for c in COLUMNS}
    row.update({'primer_pair_id': pair_id(f, r), 'pcr_primer_forward': f, 'pcr_primer_reverse': r,
                'pcr_primer_name_forward': fname, 'pcr_primer_name_reverse': rname,
                'target_gene': faire_gene(next(iter(genes))) if len(genes) == 1 else '',
                'pcr_primer_reference_forward': refs[0] if refs and f else '',
                'pcr_primer_reference_reverse': refs[-1] if refs and r else '',
                'notes': f'not in the primer table; as written: {line[:200]}', 'source': 'the methods text',
                'matched_by': 'sequences in the text (not in the primer table)', 'rank': 4})
    return row


def text_candidates(t, text):
    """One entry per distinct primer pair found in the text, with the words that point to it, in
    the order they appear. Pairs supported by more words (for example both primer names) come first;
    sequences written in the text count as the strongest evidence."""
    by_pair = {}
    found = from_text(t, text)
    named = [c for cands in found.values() for c in cands]
    for row, evidence in sequence_candidates(t, text):
        if row['matched_by'] == 'a sequence in the text (not paired)':
            # One primer of a pair the text also names: evidence for that pair, not a pair of its own.
            s = row['pcr_primer_forward'] or row['pcr_primer_reverse']
            same = [c for c in named if s in (c['pcr_primer_forward'], c['pcr_primer_reverse'])]
            if same:
                found.setdefault(evidence, []).extend(same)
                continue
        found.setdefault(evidence, []).append(row)
    for words, cands in found.items():
        for c in cands:
            e = by_pair.setdefault(c['primer_pair_id'], {**c, 'evidence': []})
            if words not in e['evidence']:
                e['evidence'].append(words)
            if c['rank'] > e['rank']:   # report the strongest way the pair was matched
                e['rank'], e['matched_by'] = c['rank'], c['matched_by']
    for e in by_pair.values():
        e['evidence'].sort(key=lambda w: (text.find(w.split(' / ')[0]), w))
    return sorted(by_pair.values(), key=lambda e: (-len(e['evidence']), -e['rank'], e['assay_name']))


# ------------------------------------------------------------------ command line

OUT_COLUMNS = ['query', 'matched_by', 'candidates_for_query'] + COLUMNS


def write_candidates(path, rows):
    pd.DataFrame(rows, columns=OUT_COLUMNS).to_csv(path, sep='\t', index=False)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--version', action='version', version=f'faire_primers {__version__}')
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build', help='make or update a primer table')
    b.add_argument('inputs', nargs='+', help='primer spreadsheets or TSVs')
    b.add_argument('--base', help='an existing primer table to update (for example the bundled one)')
    b.add_argument('-o', '--output', required=True)
    b.add_argument('--report', help='write the problems found to this TSV')
    b.add_argument('--labels', nargs='+', help='names for the inputs, used in sources and messages')
    for name, helptext in (('lookup', 'look up names or citations'), ('text', 'find primers in a methods text')):
        s = sub.add_parser(name, help=helptext)
        if name == 'lookup':
            s.add_argument('queries', nargs='*', help='primer or assay names, or citations')
            s.add_argument('--queries_file', help='a text file with one name or citation per line')
            s.add_argument('--gene', help='keep only primers for this gene (12S, 16S, 18S, COI ...)')
        else:
            s.add_argument('text', nargs='+', help='methods or README text files')
        s.add_argument('--primers', action='append',
                       help=f'primer table; repeat to add tables, later ones winning (default {BUNDLED.name})')
        s.add_argument('--primers_label', action='append', default=[],
                       help='a name for each --primers table, used as its rows\' source')
        s.add_argument('--no_bundled', action='store_true', help='do not start from the bundled table')
        s.add_argument('-o', '--output', help='write the candidates to this TSV')
    args = ap.parse_args(argv)

    if args.cmd == 'build':
        t, problems = build(args.inputs, base=args.base, labels=args.labels)
        t.sort_values(['target_gene', 'assay_name', 'pcr_primer_name_forward']).to_csv(args.output, sep='\t', index=False)
        if args.report:
            pd.DataFrame(problems, columns=['where', 'problem']).to_csv(args.report, sep='\t', index=False)
        print(f'INFO: {len(t)} primer pairs written; {len(problems)} problems noted')
        return 0

    tables = ([] if args.no_bundled else [BUNDLED]) + (args.primers or [])
    if not tables:
        sys.stderr.write('ERROR: no primer table: give --primers or leave out --no_bundled\n')
        return 2
    t = load(*tables, labels=dict(zip(map(str, args.primers or []), args.primers_label)))
    out = []
    if args.cmd == 'lookup':
        queries = list(args.queries)
        if args.queries_file:
            queries += [ln.strip() for ln in Path(args.queries_file).read_text(errors='replace').splitlines() if ln.strip()]
        for q in queries:
            c = lookup(t, q, args.gene)
            print(f'{q}: {len(pairs(c))} sequence pairs')
            for x in c:
                print(f"  {x['matched_by']}: {x['assay_name'] or '-'} {x['pcr_primer_name_forward']}/"
                      f"{x['pcr_primer_name_reverse']} {x['pcr_primer_forward']} {x['pcr_primer_reverse']} "
                      f"({x['pcr_primer_reference_forward']}; {x['source']})")
                out.append({**x, 'candidates_for_query': len(pairs(c))})
            if not c:
                out.append({'query': q, 'matched_by': 'not found', 'candidates_for_query': 0})
    else:
        text = '\n\n'.join(Path(p).read_text(encoding='utf-8', errors='replace') for p in args.text)
        found = text_candidates(t, text)
        for e in found:
            print(f"{e['assay_name'] or '-'} {e['pcr_primer_name_forward']}/{e['pcr_primer_name_reverse']} "
                  f"{e['pcr_primer_forward']} {e['pcr_primer_reverse']} [{e['target_gene']}] "
                  f"({e['pcr_primer_reference_forward']}) <- {'; '.join(e['evidence'][:3])}")
            out.append({**e, 'query': '; '.join(e['evidence'][:5]), 'matched_by': e['matched_by'],
                        'candidates_for_query': len(found)})
        print(f'INFO: {len(found)} candidate primer pairs')
    if args.output:
        write_candidates(args.output, out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
