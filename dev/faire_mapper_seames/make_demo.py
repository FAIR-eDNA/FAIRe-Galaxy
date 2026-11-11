"""Cut the SEA-MES data record down to a demonstration set with the same files and layouts.

Usage: python make_demo.py DATA_DIR OUT_DIR

DATA_DIR needs files 4, 7 and 8 of the record, which are not stored in the repository (each over
1 MB): download them from the record (see README.md).

Keeps a few samples and the sequences with reads in them, and leaves everything else as the
authors wrote it: file names, sheet and column names, the comment lines above the NCBI headers,
the quoting of the CSV files, the sample details below the 18S counts, and Wilderlab's repeated
column names. The COI table (file 6) is left out: the authors did not use it. The samples:

- the 11 10 L samples that are in every file (stations CTD32, CTD35 and CTD50: surface,
  chlorophyll maximum and two bottom samples each), and two of the field controls (M056 and M172);
- six deep-tow samples (three pairs: the Mini Bongo and the OCD water at sites S4.1, S11.3 and N18).
  Wilderlab's table names the N18 pair CN065 and CN066, a second time; the authors confirmed they
  are CN165 and CN166, and run.sh renames them;
- four 2 L samples in the 18S and Wilderlab tables, and S099, which only Wilderlab's table has;
- MQ1, the Milli-Q control that is in Wilderlab's table only.

Sequences with no reads in the kept samples are left out (except the ASVs the kept curated 16S
rows are named after), and of the 18S and Wilderlab tables
only the 300 sequences of each assay with the most reads in them are kept (TOP). The 16S tables are
kept whole for those samples, as each curated row's ASV must be in the ASV table. The authors'
ASV-level table of curated 16S names, if it is in DATA_DIR/private, is cut the same way into
OUT_DIR/private; it is unpublished, so both folders are kept out of the repository (.gitignore).
Its sample columns carry the prefix S_ (S_M097). The 18S table's
Total reads column is the total over the kept samples. The run report keeps the libraries of the kept samples, and the
18S SRA sheet its rows for them, with its formulas written as their values.
"""
import gzip
import re
import shutil
import sys
from pathlib import Path

import openpyxl

CORE_10L = ['M097', 'M099', 'M100', 'M106', 'M107', 'M108', 'M109', 'M153', 'M154', 'M155', 'M156']
DEEP_TOW = ['CN021', 'CN022', 'CN065', 'CN066', 'CN165', 'CN166']
CONTROLS = ['M056', 'M172']   # two field controls with 16S and Wilderlab reads
TWO_L = ['S029', 'S030', 'S035', 'S036']
WL_ONLY = ['S099', 'MQ1']
COPY = ['ReadMe_Description.md', 'methods.txt', 'methods_consolidated.txt', 'dublincore-000065684v002.xml']
PRIVATE = 'private/SEA_MES_Fish16S_ASV_Feb_27_2025_editColRename.csv'
TOP = 300


def split_raw(line):
    """CSV fields as written, quotes included, so the cut file keeps the authors' quoting."""
    out, cur, quoted = [], [], False
    for ch in line:
        if ch == '"':
            quoted = not quoted
        if ch == ',' and not quoted:
            out.append(''.join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append(''.join(cur))
    return out


def bare(field):
    return field.strip().strip('"').lstrip('﻿')


def reads(field):
    try:
        return float(bare(field) or 0)
    except ValueError:
        return None


def open_text(path, mode):
    return gzip.open(path, mode + 't', encoding='utf-8', newline='') if str(path).endswith('.gz') \
        else open(path, mode, encoding='utf-8', newline='')


def sample_of(header):
    """M108_S7_L001 (an Illumina file name, as the 18S table has) -> M108."""
    return re.sub(r'_S\d+_L\d+$', '', header)


def cut_csv(src, dst, keep, recount=None, footer_after_blank=False, top=None, group=None, also=(), prefix=''):
    """Columns that are not samples, then the kept sample columns; rows with reads in them (of
    each group, such as Wilderlab's target, the `top` with the most reads). `prefix` is taken off
    the sample columns' names to read them (S_ in S_M097)."""
    with open_text(src, 'r') as fh:
        lines = fh.read().split('\n')
    eol_cr = lines[0].endswith('\r')
    lines = [x.rstrip('\r') for x in lines]
    last = lines[-1] == ''
    lines = lines[:-1] if last else lines
    header = split_raw(lines[0])
    names = [bare(h) for h in header]
    names = [n[len(prefix):] if prefix and n.startswith(prefix) else n for n in names]
    is_sample = [bool(re.match(r'^(M|S|CN|P|MQ)\d', sample_of(n))) for n in names]
    cols = [i for i, n in enumerate(names) if not is_sample[i] or sample_of(n) in keep]
    kept_samples = [i for i in cols if is_sample[i]]
    gi = names.index(group) if group else None
    parsed, footer = [], False
    for k, line in enumerate(lines):
        f = split_raw(line)
        if k and footer_after_blank and not footer and all(not bare(x) for x in f):
            footer = True   # the blank row above the sample details
        body = bool(k and not footer)
        total = sum(reads(f[i]) or 0 for i in kept_samples) if body else None
        parsed.append((f, body, total))
    also = set(also)
    chosen = {k for k, (f, body, total) in enumerate(parsed) if body and (total > 0 or bare(f[0]) in also)}
    if top:
        by = {}
        for k in sorted(chosen):
            by.setdefault(bare(parsed[k][0][gi]) if gi is not None else '', []).append(k)
        chosen = {k for ks in by.values() for k in sorted(ks, key=lambda k: -parsed[k][2])[:top]}
    out, n_rows, n_kept = [], 0, 0
    for k, (f, body, total) in enumerate(parsed):
        if body:
            n_rows += 1
            if k not in chosen:
                continue
            n_kept += 1
            if recount is not None and recount < len(f):
                f[recount] = str(int(total)) if float(total).is_integer() else str(total)
        out.append(','.join(f[i] if i < len(f) else '' for i in cols))
    eol = '\r\n' if eol_cr else '\n'
    with open_text(dst, 'w') as fh:
        fh.write(eol.join(out) + (eol if last else ''))
    found = sorted({sample_of(names[i]) for i in kept_samples})
    return n_rows, n_kept, found, [bare(x.split(',')[0]) for x in out[1:]]


def cut_ncbi_sheet(src, dst, keep):
    """An NCBI BioSample sheet: the comment lines and header as they are, the kept rows."""
    wb = openpyxl.load_workbook(src)
    ws = wb.worksheets[0]
    header = next(r for r in range(1, ws.max_row + 1) if str(ws.cell(r, 1).value or '').startswith('*sample_name'))
    drop = [r for r in range(header + 1, ws.max_row + 1) if str(ws.cell(r, 1).value or '').strip() not in keep]
    for r in reversed(drop):
        ws.delete_rows(r)
    wb.save(dst)
    return [str(ws.cell(r, 1).value) for r in range(header + 1, ws.max_row + 1) if ws.cell(r, 1).value]


def cut_sra_sheet(src, dst, keep):
    """The 18S SRA sheet: the SRA_data rows of the kept samples. Its formulas (library_ID, and the
    file names on the sandpit sheet) are written as their values, as Excel stored them: a copy
    saved by openpyxl would keep the formulas but lose the stored values that other programs read."""
    wb = openpyxl.load_workbook(src, data_only=True)
    ws = wb['SRA_data']
    drop = [r for r in range(2, ws.max_row + 1) if str(ws.cell(r, 1).value or '').strip() not in keep]
    for r in reversed(drop):
        ws.delete_rows(r)
    wb.save(dst)
    return [str(ws.cell(r, 1).value) for r in range(2, ws.max_row + 1) if ws.cell(r, 1).value]


def main(data, out):
    data, out = Path(data), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    picked = CONTROLS
    keep_10l = CORE_10L + picked
    keep = set(keep_10l + DEEP_TOW + TWO_L + WL_ONLY)

    report['1'] = cut_ncbi_sheet(data / '1_SEA-MES_M_samples_metadata_10L.xlsx',
                                 out / '1_SEA-MES_M_samples_metadata_10L.xlsx', set(keep_10l))
    report['2'] = cut_ncbi_sheet(data / '2_SEA-MES_CN_samples_metadata_OCD.xlsx',
                                 out / '2_SEA-MES_CN_samples_metadata_OCD.xlsx', set(DEEP_TOW))
    report['3'] = cut_sra_sheet(data / '3_SRA_metadata_SEAMES_18S.xlsx', out / '3_SRA_metadata_SEAMES_18S.xlsx',
                                keep)
    # The curated rows first: the ASV each is named after stays in the ASV table, reads or not.
    report['5'] = cut_csv(data / '5_SEA_MES_Fish16S_Tax_Feb_27_2025.csv', out / '5_SEA_MES_Fish16S_Tax_Feb_27_2025.csv',
                          keep)
    named = list(report['5'][3])
    if (data / PRIVATE).exists():
        (out / PRIVATE).parent.mkdir(exist_ok=True)
        report['private'] = cut_csv(data / PRIVATE, out / PRIVATE, keep, prefix='S_')
        named += report['private'][3]
    report['4'] = cut_csv(data / '4_SEA-MES_16S_ASV_level_output_with_seq.csv',
                          out / '4_SEA-MES_16S_ASV_level_output_with_seq.csv', keep, also=named)
    report['8'] = cut_csv(data / '8_WL_Full_SEA_MES_samples.csv.gz', out / '8_WL_Full_SEA_MES_samples.csv.gz', keep,
                          top=TOP, group='target')
    with gzip.open(data / '7_SEA-MES_2025_EUK_18S_for_DAT.csv.gz', 'rt', encoding='utf-8') as fh:
        names = [bare(x) for x in split_raw(fh.readline().rstrip('\r\n'))]
    report['7'] = cut_csv(data / '7_SEA-MES_2025_EUK_18S_for_DAT.csv.gz', out / '7_SEA-MES_2025_EUK_18S_for_DAT.csv.gz',
                          keep, recount=names.index('Total reads'), footer_after_blank=True, top=TOP)
    # ENA's run report: the libraries of the kept samples
    src = data / 'filereport_read_run_PRJNA1263580.tsv'
    lines = src.read_text(encoding='utf-8').split('\n')
    head = lines[0].split('\t')
    li = head.index('library_name')
    kept = [lines[0]] + [x for x in lines[1:] if x and re.split(r'_', x.split('\t')[li])[0] in keep]
    (out / src.name).write_text('\n'.join(kept) + '\n', encoding='utf-8')
    report['run report'] = len(kept) - 1
    for name in COPY:
        shutil.copy2(data / name, out / name)

    print(f"10 L samples: {len(report['1'])} ({', '.join(picked)} the field controls); deep-tow: {len(report['2'])}; "
          f"18S SRA rows: {len(report['3'])}; run report libraries: {report['run report']}")
    for k in ['4', '5', '7', '8', 'private']:
        if k in report:
            n, m, found, _ = report[k]
            print(f'file {k}: {m} of {n} rows kept; {len(found)} kept samples have a column')
    files = [p for p in out.iterdir() if p.is_file()]
    print(f'{len(files)} files, {sum(p.stat().st_size for p in files) / 1e6:.1f} MB'
          + ('; the curated names in private/' if 'private' in report else ''))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
