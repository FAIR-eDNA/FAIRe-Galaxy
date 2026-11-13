"""Methods documents and sequence files, for the FAIRe mapper tools.

Methods often come as a PDF, and sequences as a FASTA file whatever its name. These helpers judge a
file by its content, not its name: Galaxy names its files dataset_N.dat, and people name FASTA files
.fa, .fasta, .fna, .txt or nothing at all.
"""

import gzip
import re

# A sequence line: nucleotide letters (IUPAC), gaps and the odd stop or end mark
SEQUENCE_LINE = re.compile(r'^[ACGTURYSWKMBDHVNI.*-]+$', re.I)
# A primer sequence wrapped in a table cell of a PDF: 15 or more bases, a line break, then 1 to 12 bases
# alone on their line
WRAPPED_SEQUENCE = re.compile(r'(?m)^([ACGTURYSWKMBDHVNI]{15,})[ \t]*\n([ACGTURYSWKMBDHVNI]{1,12})[ \t]*$')


def _head(path, n=4096):
    """The first n bytes of a file, uncompressed if it is gzipped."""
    with open(path, 'rb') as f:
        b = f.read(n)
    if b[:2] == b'\x1f\x8b':
        with gzip.open(path, 'rb') as g:
            b = g.read(n)
    return b


def _open_text(path):
    with open(path, 'rb') as f:
        gz = f.read(2) == b'\x1f\x8b'
    return (gzip.open if gz else open)(path, 'rt', encoding='utf-8-sig', errors='replace')


def is_pdf(path):
    """True if the file is a PDF document."""
    try:
        return _head(path, 1024).lstrip()[:5] == b'%PDF-'
    except OSError:
        return False


def fasta_summary(path, max_lines=50000):
    """For a FASTA file, {'n': sequences, 'shortest': length, 'longest': length, 'ids': first IDs};
    None for anything else. A FASTA file has a header line starting with > before each sequence, and
    lines of nucleotide letters between them. Only the first max_lines lines are read."""
    try:
        f = _open_text(path)
    except OSError:
        return None
    n, lengths, ids, current, seen_seq = 0, [], [], None, False
    with f:
        for i, line in enumerate(f):
            if i >= max_lines:
                current = None   # the last record may be cut short: leave it out of the lengths
                break
            s = line.strip()
            if not s:
                continue
            if s.startswith('>'):
                if current is not None:
                    lengths.append(current)
                n += 1
                if len(ids) < 3:
                    ids.append(s[1:].split()[0] if s[1:].split() else '')
                current = 0
            elif n == 0 or not SEQUENCE_LINE.match(s):
                return None    # text before the first header, or a line that is not sequence
            else:
                current += len(s)
                seen_seq = True
    if current is not None:
        lengths.append(current)
    if not n or not seen_seq:
        return None
    return {'n': n, 'shortest': min(lengths) if lengths else 0, 'longest': max(lengths) if lengths else 0,
            'ids': ids}


def pdf_text(path):
    """The text of a PDF, page by page. Empty for a PDF of scanned pages, which has no text layer."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise SystemExit('ERROR: reading a PDF needs the Python package pypdf. Install it, or save the methods '
                         'as text and give that instead.')
    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        t = (page.extract_text() or '').strip()
        # A PDF keeps the page's line breaks, and a table's cells come out one per line, so the lines are
        # kept as they are (joining them would run the cells of different rows together). Only a primer
        # sequence that wrapped in its cell is joined again: a line of 15 or more bases followed by a
        # short line of bases (GGWACWGGWTGAACWGTWTAYCC / YCC).
        t = WRAPPED_SEQUENCE.sub(r'\1\2', t)
        pages.append(t)
    return '\n\n'.join(pages)


def pdf_pages(path):
    try:
        from pypdf import PdfReader
        return len(PdfReader(path).pages)
    except Exception:
        return 0


def read_text(path):
    """The text of a methods file: plain text, markdown or a PDF (gzipped or not)."""
    if is_pdf(path):
        return pdf_text(path)
    with _open_text(path) as f:
        return f.read()
