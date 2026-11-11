"""Differential check of normalise_faire.py: does it change only what it is meant to change?

Usage:
  python3 check.py CASES_DIR [--examples DIR] [--report results/RESULTS.md]

For each named case and each copy of normalise_faire.py (the FAIRe2QIIME copy writes the three
metadata sheets; the FAIRe2NCBI and edna2obis copy writes every sheet) it:
  1. runs normalise_faire.py;
  2. compares every cell of the sheets it writes with the expected workbook, as openpyxl reads them
     (value and type) and as FAIRe2NCBI's driver reads them (pandas, literal text);
  3. runs upstream FAIRe2QIIME on the expected workbook and on the normalised one, and compares
     every output file.
Differences named in ALLOWED are intended; anything else is reported as UNEXPECTED, and the script
exits 1. With --examples, it also runs both copies on real FAIRe workbooks and counts changed
cells by sheet and type (no cell values are printed).
"""
import argparse
import datetime
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')
import openpyxl  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
VARIANTS = {
    'faire2qiime': ROOT / 'tools/faire2qiime/normalise_faire.py',
    'faire2ncbi+edna2obis': ROOT / 'tools/faire2ncbi/normalise_faire.py',
}
UPSTREAM_QIIME = ROOT / 'tools/faire2qiime/faire2qiime.py'
META = ('projectMetadata', 'sampleMetadata', 'experimentRunMetadata')

# case -> (expected workbook, or None to compare with the input; the reason for any intended difference)
EXPECTED = {
    'L01_faire_twin': 'P01_noaa_layout',
    'L02_faire_twin_spelling': 'P01_noaa_layout',
}
# (case, sheet, kind) -> reason. kind is 'cells' (cell-level differences in that sheet) or 'qiime'.
ALLOWED = {
    ('L03_single_assay', 'projectMetadata', 'cells'):
        'single-assay layout: project_level copied into a new column headed by the assay_name',
    ('L02_faire_twin_spelling', 'projectMetadata', 'cells'):
        'the test input spells assay2 SSU18Sv9_EMP in projectMetadata; the header is corrected (with a warning), the assay_name row keeps the input',
    ('L02_faire_twin_spelling', 'FAIRe2QIIME', 'qiime'):
        'the same assay_name row reaches the assay_name_PROJECT column of the 18S metadata table',
    ('P06_dates_and_times', 'sampleMetadata', 'cells'):
        'pandas reads an Excel time cell as a time, which is written back as text (10:23:00); pandas reads the same text '
        'from both, and no tool output changes (results/DOWNSTREAM_NCBI.md, upstream FAIRe2QIIME row)',
    ('L03_single_assay', 'FAIRe2QIIME', 'qiime'):
        'upstream cannot read the single-assay layout (KeyError on the assay name); converting it is what normalise_faire.py is for',
}


def cell_grid(path, sheets):
    """{sheet: {(row, col): (repr(value), type name and Excel cell type)}} as openpyxl reads them.
    The Excel cell type matters: text such as #N/A saved as an error cell reads back from openpyxl
    as the same text, but pandas reads it as empty."""
    try:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    except Exception as err:  # noqa: BLE001
        return {'__error__': str(err)}
    out = {}
    for name in sheets:
        if name not in wb.sheetnames:
            out[name] = None
            continue
        grid = {}
        for row in wb[name].iter_rows():
            for cell in row:
                v = getattr(cell, 'value', None)
                if v is not None:
                    grid[(cell.row, cell.column)] = (repr(v), f'{type(v).__name__}/{cell.data_type}')
        out[name] = grid
    return out


def pandas_literal(path, sheets):
    """As FAIRe2NCBI's driver reads a normalised workbook: pandas, literal text kept."""
    x = pd.read_excel(path, sheet_name=None, header=None, keep_default_na=False, na_values=[])
    return {s: x[s].astype(str).where(x[s].astype(str) != 'nan', '') for s in sheets if s in x}


def cell_name(r, c):
    return f'{openpyxl.utils.get_column_letter(c)}{r}'


def diff_grids(a, b):
    keys = sorted(set(a) | set(b))
    return [(cell_name(*k), a.get(k), b.get(k)) for k in keys if a.get(k) != b.get(k)]


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=600)
    return p.returncode, (p.stdout + p.stderr).strip()


def qiime_outputs(workbook, work):
    out = Path(work) / 'q'
    out.mkdir()
    rc, log = run([sys.executable, '-I', str(UPSTREAM_QIIME), '--path_faire', str(workbook),
                   '--sample_name_column', 'samp_name', '--absolute_path_sequences', '/data',
                   '--output_directory', str(out)], work)
    files = {p.name: p.read_bytes() for p in sorted(out.iterdir())} if rc == 0 else {}
    return rc, log.splitlines()[-1:] if rc else [], files


def check_case(case, cases_dir, report, unexpected):
    src = cases_dir / f'{case}.xlsx'
    expected = cases_dir / f"{EXPECTED.get(case, case)}.xlsx"
    for vname, script in VARIANTS.items():
        with tempfile.TemporaryDirectory() as work:
            out = Path(work) / 'normalised.xlsx'
            rc, log = run([sys.executable, '-I', str(script), str(src), str(out)], work)
            notes = [line for line in log.splitlines() if line.startswith(('WARNING', 'ERROR', 'Traceback')) or 'Error' in line][-2:]
            if rc != 0:
                report.append(f'| {case} | {vname} | normalise exit {rc} | {"; ".join(notes)[:200]} | **UNEXPECTED** |')
                unexpected.append((case, vname, 'exit'))
                continue
            sheets = META if vname == 'faire2qiime' else tuple(openpyxl.load_workbook(src, read_only=True).sheetnames)
            g_exp, g_out = cell_grid(expected, sheets), cell_grid(out, sheets)
            p_exp, p_out = pandas_literal(expected, sheets), pandas_literal(out, sheets)
            for s in sheets:
                d = diff_grids(g_exp.get(s) or {}, g_out.get(s) or {})
                lit = 0
                if s in p_exp and s in p_out:
                    a, b = p_exp[s], p_out[s]
                    if a.shape != b.shape:
                        lit = -1
                    else:
                        lit = int((a.values != b.values).sum())
                if not d and lit == 0:
                    continue
                reason = ALLOWED.get((case, s, 'cells'))
                status = 'allowed: ' + reason if reason else '**UNEXPECTED**'
                if not reason:
                    unexpected.append((case, vname, s))
                shown = '; '.join(f'{c}: {x[0] if x else "empty"} ({x[1] if x else ""}) -> {y[0] if y else "empty"} ({y[1] if y else ""})'
                                  for c, x, y in d[:4])
                more = f' (+{len(d) - 4} more)' if len(d) > 4 else ''
                report.append(f'| {case} | {vname} | {s}: {len(d)} cells differ (openpyxl), '
                              f'{"shape differs" if lit < 0 else str(lit) + " differ"} (pandas literal) | {shown}{more} | {status} |')
            if notes:
                report.append(f'| {case} | {vname} | log | {"; ".join(notes)[:200]} | note |')
        if vname != 'faire2qiime':
            continue
        with tempfile.TemporaryDirectory() as w1, tempfile.TemporaryDirectory() as w2:
            norm = Path(w2) / 'normalised.xlsx'
            run([sys.executable, '-I', str(VARIANTS['faire2qiime']), str(src), str(norm)], w2)
            rc1, err1, f1 = qiime_outputs(expected, w1)
            rc2, err2, f2 = qiime_outputs(norm, w2)
            if rc1 and rc2:
                report.append(f'| {case} | upstream FAIRe2QIIME | not comparable: upstream fails on both | {"; ".join(err1)[:160]} | not run |')
            elif (rc1, sorted(f1)) == (rc2, sorted(f2)) and all(f1[k] == f2[k] for k in f1):
                report.append(f'| {case} | upstream FAIRe2QIIME | {len(f1)} output files identical | | same |')
            else:
                changed = [k for k in sorted(set(f1) | set(f2)) if f1.get(k) != f2.get(k)]
                reason = ALLOWED.get((case, 'FAIRe2QIIME', 'qiime'))
                status = 'allowed: ' + reason if reason else '**UNEXPECTED**'
                if not reason:
                    unexpected.append((case, 'FAIRe2QIIME', 'outputs'))
                report.append(f'| {case} | upstream FAIRe2QIIME | exit {rc1} vs {rc2}; files differ: {", ".join(changed)[:160]} '
                              f'| {"; ".join(err1 + err2)[:160]} | {status} |')


def check_examples(examples, report):
    books = []
    for p in sorted(Path(examples).rglob('*.xlsx')):
        try:
            if 'projectMetadata' in openpyxl.load_workbook(p, read_only=True).sheetnames:
                books.append(p)
        except Exception:  # noqa: BLE001
            pass
    report += ['', '## Published FAIRe example workbooks', '',
               'Each normalised copy compared with its input, as FAIRe2NCBI\'s driver reads it (pandas, literal text). '
               'projectMetadata headers are meant to change; every other cell is meant to stay as it was. '
               'Counts only; no cell values are shown, as the examples carry no stated licence.', '',
               '| Workbook | Copy | Result | projectMetadata cells changed | other sheets: cells changed |', '|---|---|---|---|---|']
    for book in books:
        for vname, script in VARIANTS.items():
            with tempfile.TemporaryDirectory() as work:
                out = Path(work) / 'normalised.xlsx'
                rc, log = run([sys.executable, '-I', str(script), str(book), str(out)], work)
                if rc != 0:
                    msg = [line for line in log.splitlines() if 'ERROR' in line or 'Error' in line][-1:]
                    report.append(f'| {book.name} | {vname} | exit {rc}: {"; ".join(msg)[:150]} | | |')
                    continue
                a = pd.read_excel(book, sheet_name=None, header=None, keep_default_na=False, na_values=[])
                b = pd.read_excel(out, sheet_name=None, header=None, keep_default_na=False, na_values=[])
                pm, other = 0, []
                for s in b:
                    x, y = a[s].astype(str), b[s].astype(str)
                    if x.shape != y.shape:
                        n = 'shape ' + f'{x.shape}->{y.shape}'
                    else:
                        n = int((x.values != y.values).sum())
                    if s == 'projectMetadata':
                        pm = n
                    elif n:
                        other.append(f'{s}: {n}')
                kinds = {}
                if other:
                    ga, gb = cell_grid(book, [s for s in b if s != 'projectMetadata']), cell_grid(out, [s for s in b if s != 'projectMetadata'])
                    for s in gb:
                        for c, x, y in diff_grids(ga.get(s) or {}, gb.get(s) or {}):
                            key = f'{x[1] if x else "empty"}->{y[1] if y else "empty"}'
                            kinds[key] = kinds.get(key, 0) + 1
                report.append(f'| {book.name} | {vname} | exit 0 | {pm} | {"; ".join(other) or "none"}'
                              f'{" (" + ", ".join(f"{k}: {v}" for k, v in kinds.items()) + ")" if kinds else ""} |')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cases')
    ap.add_argument('--examples')
    ap.add_argument('--report', default=str(Path(__file__).parent / 'results' / 'RESULTS.md'))
    a = ap.parse_args()
    cases_dir = Path(a.cases).resolve()
    cases = sorted(p.stem for p in cases_dir.glob('*.xlsx'))
    report = [f'# normalise_faire.py differential check ({datetime.date.today().isoformat()})', '',
              '| Case | Copy or tool | What differs | First differences (expected -> normalised) | Status |', '|---|---|---|---|---|']
    unexpected = []
    for case in cases:
        check_case(case, cases_dir, report, unexpected)
    if a.examples:
        check_examples(a.examples, report)
    report += ['', f'Unexpected differences: {len(unexpected)}']
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text('\n'.join(report) + '\n', encoding='utf-8')
    print('\n'.join(report))
    sys.exit(1 if unexpected else 0)


if __name__ == '__main__':
    main()
