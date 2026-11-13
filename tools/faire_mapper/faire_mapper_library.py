"""Library tables for faire_mapper_apply: which sequence files belong to which sample.

Reads a run report from ENA (a "filereport", the read_run table of a study) or the SRA (RunInfo, or
the SRA submission sheet), or a lab's own run sheet, and turns it into rows of experimentRunMetadata:
lib_id, filename and filename2, their checksums, and associatedSequences (links to the run, the
BioSample and the BioProject). Each library is matched to a sample of the sample table by a sample
name column, or by its library name starting with the sample name (M159_16SFish matches M159).
"""

from __future__ import annotations

import re
from pathlib import Path

import faire_mapper as fm

# Column names, lower case with spaces and punctuation removed, in order of preference.
COLUMNS = {
    'lib_id': ['libid', 'libraryname', 'libraryid', 'library', 'libraryalias', 'libraryidentifier'],
    'samp_name': ['sampname', 'samplename', 'samplealias', 'sampleid', 'sample', 'samplecode'],
    'filename': ['filename', 'filename1', 'file1', 'forwardfile', 'forwardfilename', 'forwardreads', 'read1',
                 'readfile1', 'r1', 'r1file', 'fastq1', 'fastqr1', 'forwardfastq', 'file', 'fastq', 'fastqfile',
                 'path'],
    'filename2': ['filename2', 'file2', 'reversefile', 'reversefilename', 'reversereads', 'read2', 'readfile2',
                  'r2', 'r2file', 'fastq2', 'fastqr2', 'reversefastq'],
    'checksum_filename': ['checksumfilename', 'checksum', 'checksum1', 'md5', 'md51', 'md5r1', 'md5forward',
                          'filemd5', 'filename1md5', 'hash'],
    'checksum_filename2': ['checksumfilename2', 'checksum2', 'md52', 'md5r2', 'md5reverse', 'filename2md5'],
    'seq_run_id': ['seqrunid', 'sequencingrun', 'sequencingrunid', 'runid', 'runname', 'flowcell'],
    'files': ['submittedftp', 'fastqftp', 'submittedaspera', 'fastqaspera', 'submittedgalaxy', 'fastqgalaxy'],
    'md5s': ['submittedmd5', 'fastqmd5'],
    'run_acc': ['runaccession', 'run', 'srarun', 'srrun', 'runacc'],
    'sample_acc': ['sampleaccession', 'biosample', 'biosampleaccession', 'biosampleid'],
    'study_acc': ['studyaccession', 'bioproject', 'bioprojectaccession', 'study', 'projectaccession'],
    'instrument': ['instrumentmodel', 'instrument', 'model', 'sequencer'],
    'platform': ['instrumentplatform', 'platform'],
    'layout': ['librarylayout', 'layout', 'liblayout'],
}
RUN_ACC = re.compile(r'^[SED]RR\d+$')
SAMPLE_ACC = re.compile(r'^(SAM[NED][A-Z]?\d+|[SED]RS\d+)$')
STUDY_ACC = re.compile(r'^(PRJ[NED][AB]\d+|[SED]RP\d+)$')
FASTQ = re.compile(r'\.(fastq|fq)(\.gz|\.bz2)?$', re.I)
# Illumina's file names: sample, sample number, lane, read and segment (M108_S7_L001_R1_001.fastq.gz).
ILLUMINA_TAIL = re.compile(r'_S\d+(_L\d{3})?(_[RI][12](_\d{3})?)?$')
READ_TAIL = re.compile(r'([._](R?[12])(_\d{3})?)$', re.I)
MD5 = re.compile(r'^[0-9a-f]{32}$', re.I)
# A line of md5sum's output: the checksum, two spaces (or a space and * for binary mode), the file.
MD5SUM_LINE = re.compile(r'^([0-9a-f]{32}) [ *](\S.*)$', re.I)


class LibraryError(Exception):
    """A problem with a library table that the user has to fix."""


def _key(s):
    return re.sub(r'[^a-z0-9]', '', str(s).lower())


def fm_text(v):
    if v is None or (isinstance(v, float) and v != v):
        return ''
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def file_stem(name):
    """A sequence file name without folders, extension and read number: M108_S7_L001_R1_001.fastq.gz
    and SRR33695780_1.fastq.gz become M108_S7_L001 and SRR33695780."""
    s = Path(str(name).strip().split('/')[-1]).name
    s = FASTQ.sub('', s)
    return READ_TAIL.sub('', s)


def illumina_sample(name):
    """The sample part of an Illumina file or library name: M108_S7_L001 becomes M108."""
    return ILLUMINA_TAIL.sub('', file_stem(name))


def find_columns(columns):
    """{field: column} for the columns this module knows, each column used once."""
    out, used = {}, set()
    keys = {c: _key(c) for c in columns}
    for field, names in COLUMNS.items():
        for name in names:
            col = next((c for c in columns if keys[c] == name and c not in used), None)
            if col is not None:
                out[field] = col
                used.add(col)
                break
    return out


FILE_LIST_NOTES = {'md5sum': 'checksums and file names, as md5sum writes them',
                   'names': 'a list of sequence file names, one per line'}


def read_file_list(path):
    """A list of sequence files with no header: md5sum's output (the checksum, two spaces and the
    file name on each line), as a table with the columns md5 and file; or file names, one per line
    (a folder listing), as a table with the column file. Returns the table and its form ('md5sum' or
    'names'), or (None, '') for any other file."""
    if fm._is_excel(path):
        return None, ''
    import pandas as pd
    try:
        with open(path, encoding='utf-8-sig') as f:
            lines = [ln.strip() for ln in f if ln.strip()]
    except (UnicodeDecodeError, OSError):
        return None, ''
    if not lines:
        return None, ''
    found = [MD5SUM_LINE.match(ln) for ln in lines]
    if all(found):
        return pd.DataFrame([m.groups() for m in found], columns=['md5', 'file']), 'md5sum'
    if all(FASTQ.search(ln) and not re.search(r'[,;\t]', ln) for ln in lines):
        return pd.DataFrame({'file': lines}), 'names'
    return None, ''


def _pick_sheet(path, sheet):
    """The sheet to read: the one given, or the first whose header names libraries or files (the SRA
    submission sheet keeps its instructions on the first sheet)."""
    if sheet or not fm._is_excel(path):
        return sheet or None
    import pandas as pd
    xl = pd.ExcelFile(path)
    for name in xl.sheet_names:
        try:
            df = fm.read_table(path, name)
        except SystemExit:   # an empty sheet
            continue
        cols = find_columns(list(df.columns))
        if {'lib_id', 'filename', 'files', 'run_acc'} & set(cols):
            return name
    return None


def url(acc):
    """A link to an INSDC accession: NCBI for the accessions NCBI gives, the ENA browser for others."""
    acc = acc.strip()
    if re.match(r'^SRR\d+$', acc):
        return f'https://www.ncbi.nlm.nih.gov/sra/{acc}'
    if re.match(r'^SAMN\d+$', acc):
        return f'https://www.ncbi.nlm.nih.gov/biosample/{acc}'
    if re.match(r'^PRJNA\d+$', acc):
        return f'https://www.ncbi.nlm.nih.gov/bioproject/{acc}'
    return f'https://www.ebi.ac.uk/ena/browser/view/{acc}'


def _split_files(files, md5s):
    """Forward and reverse files (and their checksums) from a list such as ENA's fastq_ftp. A lone
    file beside a pair (reads that could not be paired) is left out."""
    names = [f.strip() for f in files.split(';') if f.strip()]
    sums = [m.strip() for m in md5s.split(';')] if md5s else []
    sums += [''] * (len(names) - len(sums))
    base = [n.split('/')[-1] for n in names]
    fwd = [i for i, b in enumerate(base) if re.search(r'([._]R?1)(_\d{3})?\.(fastq|fq)', b, re.I)]
    rev = [i for i, b in enumerate(base) if re.search(r'([._]R?2)(_\d{3})?\.(fastq|fq)', b, re.I)]
    if fwd and rev:
        return base[fwd[0]], base[rev[0]], sums[fwd[0]], sums[rev[0]], len(names) - 2
    if len(base) == 1:
        return base[0], '', sums[0], '', 0
    if len(base) == 2:
        return base[0], base[1], sums[0], sums[1], 0
    return (base[0] if base else ''), '', (sums[0] if sums else ''), '', max(0, len(base) - 1)


def pair_files(rows, cols, label, log):
    """A list with one sequence file per row (as a folder listing or Get-FileHash gives it): the
    forward and reverse reads of each library joined into one row, by the read number in their names
    (3A_16S_Fish_R1.fastq.gz and 3A_16S_Fish_R2.fastq.gz). The library is named by what comes before
    the read number. Rows whose names carry no read number are left as they are. Returns the rows
    and the columns, with the paired files under their own keys."""
    get = lambda r, f: fm_text(r.get(cols[f])) if f in cols else ''  # noqa: E731

    def base(name):   # the file name without its folders (Get-FileHash gives the full path)
        return re.split(r'[\\/]', name)[-1]
    reads = {}
    for r in rows:
        name = base(get(r, 'filename'))
        m = READ_TAIL.search(FASTQ.sub('', name))
        if m and m.group(2)[-1] in '12':
            reads.setdefault(file_stem(name), {})[m.group(2)[-1]] = r
    pairs = {stem: rs for stem, rs in reads.items() if set(rs) == {'1', '2'}}
    if not pairs:
        return rows, cols
    paired = {id(r) for rs in pairs.values() for r in rs.values()}
    out, done = [], set()
    for r in rows:
        if id(r) not in paired:
            out.append(r)
            continue
        stem = file_stem(base(get(r, 'filename')))
        if stem in done:
            continue
        done.add(stem)
        r1, r2 = pairs[stem]['1'], pairs[stem]['2']
        out.append({**r1, '_lib': stem, '_f1': base(get(r1, 'filename')), '_f2': base(get(r2, 'filename')),
                    '_c1': get(r1, 'checksum_filename'), '_c2': get(r2, 'checksum_filename')})
    cols = {**cols, 'lib_id': '_lib', 'filename': '_f1', 'filename2': '_f2'}
    if 'checksum_filename' in cols:
        cols.update({'checksum_filename': '_c1', 'checksum_filename2': '_c2'})
    log(f'{label}: {2 * len(pairs)} files paired into {len(pairs)} libraries by their read number (R1 and R2)'
        + (f'; {len(out) - len(pairs)} files without a pair kept as they are' if len(out) > len(pairs) else ''))
    return out, cols


def _matcher(samples):
    """A function from a name to the sample it names: the name itself, or the longest sample name it
    starts with, followed by _, -, . or a space. Case is ignored when nothing matches exactly."""
    exact = set(samples)
    lower = {}
    for s in samples:
        lower.setdefault(s.lower(), s)

    def match(name):
        name = str(name).strip()
        if not name:
            return None, ''
        if name in exact:
            return name, 'name'
        if name.lower() in lower:
            return lower[name.lower()], 'name'
        parts = re.split(r'([_.\- ])', name)
        for k in range(len(parts) - 2, 0, -2):
            prefix = ''.join(parts[:k])
            if prefix in exact:
                return prefix, 'prefix'
            if prefix.lower() in lower:
                return lower[prefix.lower()], 'prefix'
        stem = illumina_sample(name)
        if stem != name:
            return match(stem)
        return None, ''
    return match


def read_library(path, sheet, samples, label, log, assays=(), name_filter='', run_id=''):
    """Rows of experimentRunMetadata, one per library and assay, for the libraries of the samples."""
    picked = _pick_sheet(path, sheet)
    if picked and not sheet:
        log(f'{label}: sheet {picked} read, the first that names libraries or files')
    df, form = read_file_list(path)
    if form == 'md5sum':
        log(f'{label}: read as a list of checksums and file names, as md5sum writes it')
    elif form == 'names':
        log(f'{label}: read as a list of sequence file names, one per line')
    else:
        df = fm.read_table(path, picked)
    for note in df.attrs.get('read_notes', []):
        log(f'{label}: {note}')
    cols = find_columns(list(df.columns))
    if not ({'lib_id', 'filename', 'files', 'run_acc', 'samp_name'} & set(cols)):
        raise LibraryError(f"{label}: no column names a library, a sample or a sequence file (for example "
                           f"library_name, sample_name, filename or fastq_ftp); found {', '.join(map(str, df.columns[:8]))}")
    # A sample column that holds accessions (SRS..., SAMN...) is the BioSample, not the sample name.
    if 'samp_name' in cols:
        vals = [fm_text(v) for v in df[cols['samp_name']] if fm_text(v)]
        if vals and sum(bool(SAMPLE_ACC.match(v)) for v in vals) >= 0.8 * len(vals):
            if 'sample_acc' not in cols:
                cols['sample_acc'] = cols['samp_name']
            del cols['samp_name']
    for field, rx in (('run_acc', RUN_ACC), ('sample_acc', SAMPLE_ACC), ('study_acc', STUDY_ACC)):
        if field in cols:
            vals = [fm_text(v) for v in df[cols[field]] if fm_text(v)]
            if vals and sum(bool(rx.match(v)) for v in vals) < 0.8 * len(vals):
                if field == 'run_acc' and 'seq_run_id' not in cols:
                    cols['seq_run_id'] = cols[field]   # a lab's run name, not an SRA run
                del cols[field]
    used = ', '.join(f'{c} as {f}' for f, c in cols.items() if f not in ('instrument', 'platform', 'layout'))
    log(f'{label}: {len(df)} rows; columns used: {used}')
    rows = df.to_dict('records')
    get = lambda r, f: fm_text(r.get(cols[f])) if f in cols else ''  # noqa: E731

    if name_filter:
        def name_of(r):
            return get(r, 'lib_id') or get(r, 'filename') or get(r, 'files')
        kept = [r for r in rows if name_filter.lower() in name_of(r).lower()]
        what = 'libraries' if 'lib_id' in cols or 'filename2' in cols or 'files' in cols else 'files'
        log(f"{label}: {len(kept)} of {len(rows)} {what} have '{name_filter}' in their name")
        rows = kept
    if not rows:
        raise LibraryError(f"{label}: no libraries left" + (f" with '{name_filter}' in their name" if name_filter else ''))

    if 'filename' in cols and not ({'filename2', 'files', 'lib_id'} & set(cols)):
        rows, cols = pair_files(rows, cols, label, log)
        get = lambda r, f: fm_text(r.get(cols[f])) if f in cols else ''  # noqa: E731
    match = _matcher(samples)
    out, unmatched, how, extra_files, ena_copies = [], [], {}, 0, 0
    instruments, platforms, layouts, md5 = {}, set(), set(), False
    for r in rows:
        lib = get(r, 'lib_id')
        s, by = (match(get(r, 'samp_name')) if get(r, 'samp_name') else (None, ''))
        if s is None and lib:
            s, by = match(lib)
            by = 'library name' if by == 'name' else ('start of the library name' if by == 'prefix' else by)
        elif s is not None:
            by = 'sample name'
        f1, f2, c1, c2 = get(r, 'filename'), get(r, 'filename2'), get(r, 'checksum_filename'), get(r, 'checksum_filename2')
        if 'files' in cols and not f1:
            f1, f2, c1, c2, extra = _split_files(get(r, 'files'), get(r, 'md5s'))
            extra_files += extra
            ena_copies += cols['files'].lower().startswith('fastq')
        if s is None and f1:
            s, by = match(file_stem(f1))
            by = 'file name' if s else by
        if s is None:
            unmatched.append(lib or f1 or '?')
            continue
        how[by] = how.get(by, 0) + 1
        links = [url(get(r, f)) for f in ('run_acc', 'sample_acc', 'study_acc') if get(r, f)]
        row = {'samp_name': s, 'lib_id': lib or None, 'filename': f1 or None, 'filename2': f2 or None,
               'checksum_filename': c1 or None, 'checksum_filename2': c2 or None,
               'associatedSequences': ' | '.join(links) or None, 'seq_run_id': get(r, 'seq_run_id') or run_id or None}
        md5 = md5 or (bool(c1 or c2) and any('md5' in _key(cols.get(f, ''))
                                             for f in ('md5s', 'checksum_filename', 'checksum_filename2'))) \
            or bool(c1 and MD5.match(c1))
        if get(r, 'instrument'):
            instruments[get(r, 'instrument')] = instruments.get(get(r, 'instrument'), 0) + 1
        if get(r, 'platform'):
            platforms.add(get(r, 'platform').upper())
        if get(r, 'layout'):
            layouts.add(get(r, 'layout').lower())
        for a in (assays or [None]):
            out.append({**row, 'assay_name': a})
    log(f'{label}: {len(out)} rows for {len({r["samp_name"] for r in out})} samples, matched by '
        + ', '.join(f'{b} ({k})' for b, k in how.items()))
    if unmatched:
        log(f"{label}: {len(unmatched)} "
            + ('library matches no samp_name and is left out: ' if len(unmatched) == 1
               else 'libraries match no samp_name and are left out: ')
            + ', '.join(unmatched[:5]) + (' ...' if len(unmatched) > 5 else ''))
    if extra_files:
        log(f'{label}: {extra_files} files beside a read pair (reads that could not be paired) left out')
    if ena_copies:
        log(f"{label}: file names and checksums are ENA's copies of the reads ({cols['files']}); a report with "
            f"submitted_ftp and submitted_md5 gives the files as the lab submitted them")
    seen = {}
    for r in out:
        seen.setdefault((r['lib_id'], r['assay_name']), []).append(r)
    dup = [k for k, v in seen.items() if len(v) > 1 and k[0]]
    if dup:
        log(f'{label}: WARNING {len(dup)} libraries have more than one row (several runs), e.g. {dup[0][0]}')
    return out, {'instruments': instruments, 'platforms': platforms, 'layouts': layouts, 'md5': md5}
