"""Does normalise_faire.py change what the Galaxy tools write? A two-mode comparison.

Usage: python3 -I downstream.py WORKBOOK [WORKBOOK ...] [--no-values]

Each workbook must already be in the FAIRe-NOAA layout, where normalising is meant to change nothing.
Each Galaxy driver runs twice in a fresh folder: once as written, and once with normalise_faire.normalise
replaced by a plain copy (run_driver.py). Every output table is then compared cell by cell.
With --no-values, only the field names and counts of changed cells are shown (for workbooks with no
stated licence).
"""
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NCBI = ROOT / 'tools/faire2ncbi/faire2ncbi_galaxy.py'
OBIS = ROOT / 'tools/edna2obis/edna2obis_galaxy.py'
OBIS_DATA = ROOT / 'tools/edna2obis/test-data'
RUNS = {
    'FAIRe2NCBI BioSample': (NCBI, ['biosample', '--organism', 'seawater metagenome', '--mandatory_fill', 'not applicable',
                                    '--output', 'out.tsv', '--config_out', 'config.yaml'], 'out.tsv'),
    'FAIRe2NCBI SRA': (NCBI, ['sra', '--output', 'out.tsv', '--config_out', 'config.yaml'], 'out.tsv'),
    'FAIRe2NCBI BioSample, new samples only': (NCBI, ['biosample', '--organism', 'seawater metagenome',
                                                      '--mandatory_fill', 'not applicable', '--associated', 'blank_only',
                                                      '--output', 'out.tsv', '--config_out', 'config.yaml'], 'out.tsv'),
    'FAIRe2NCBI SRA, new runs only': (NCBI, ['sra', '--associated', 'blank_only', '--output', 'out.tsv',
                                             '--config_out', 'config.yaml'], 'out.tsv'),
}


def obis_form(workbook, work):
    """The inputs of the edna2obis Darwin Core tool's first test (offline: taxonomy from a mapping table),
    with this workbook. Only for workbooks built from faire_two_assays.xlsx."""
    d = lambda name, ext: {'source_path': str(OBIS_DATA / name), 'ext': ext}  # noqa: E731
    form = {
        'input_file': {'source_path': str(workbook), 'ext': 'xlsx'},
        'analyses': [
            {'assay_name': 'ssu16sv4v5-emp', 'run_name': 'gomecc4_16s', 'skip_species': False,
             'taxonomy': d('gomecc_16s_taxonomy.xlsx', 'xlsx'), 'abundance': d('gomecc_16s_abundance.tsv', 'tabular')},
            {'assay_name': 'ssu18sv9-emp', 'run_name': '', 'skip_species': False,
             'taxonomy': d('gomecc_18s_taxonomy.tsv', 'tabular'), 'abundance': d('gomecc_18s_abundance.csv', 'csv')},
        ],
        'taxa': {'source': 'mapping', 'mapping_file': d('test_mapping_worms_made_for_test.tsv', 'tabular')},
        'samples': {'control_column': 'samp_category', 'control_values': 'negative control, positive control, PCR standard',
                    'location_fields': 'line_id, station_id'},  # the tool's defaults
        'emof': {'emof_select': 'custom', 'emof_template': d('emof_template_sample_fields.tsv', 'tabular')},
        'eml': {'eml_select': 'none'},
        'core_type': 'occurrence',
    }
    path = Path(work) / 'form.json'
    path.write_text(json.dumps(form), encoding='utf-8')
    return path


def run_obis(mode, workbook, work):
    """Returns (exit code, log lines, {output file: table})."""
    form = obis_form(workbook, work)
    p = subprocess.run([sys.executable, '-I', str(HERE / 'run_driver.py'), mode, str(OBIS), 'build',
                        '--form', str(form), '--outputs', str(Path(work) / 'outputs')],
                       cwd=work, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=900)
    tables = {}
    if p.returncode == 0:
        for f in sorted((Path(work) / 'outputs').rglob('*')):
            if f.suffix in ('.csv', '.tsv'):
                rows = list(csv.reader(open(f, encoding='utf-8', newline=''), delimiter='\t' if f.suffix == '.tsv' else ','))
                tables[f.name] = rows
    return p.returncode, (p.stdout + p.stderr).strip().splitlines(), tables


def run(mode, driver, args, workbook, work):
    p = subprocess.run([sys.executable, '-I', str(HERE / 'run_driver.py'), mode, str(driver),
                        args[0], '--input_file', str(workbook)] + args[1:],
                       cwd=work, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=600)
    return p.returncode, (p.stdout + p.stderr).strip().splitlines()


def table(path, skip_comments):
    rows = list(csv.reader(open(path, encoding='utf-8', newline=''), delimiter='\t'))
    return [r for r in rows if not (skip_comments and r and r[0].startswith('#'))]


def compare(a, b, show_values):
    if len(a) != len(b):
        return [f'rows {len(a)} (copy) vs {len(b)} (normalised)']
    head = b[0] if b else []
    if a and a[0] != head:
        added = [h for h in head if h not in a[0]]
        lost = [h for h in a[0] if h not in head]
        return [f'columns differ: only after normalising {added}; only with a plain copy {lost}']
    out = {}
    for ra, rb in zip(a[1:], b[1:]):
        for j, (x, y) in enumerate(zip(ra, rb)):
            if x != y:
                out.setdefault(head[j], []).append((x, y))
    return [f'{field}: {len(v)} cell(s)' + (f', e.g. {v[0][0]!r} -> {v[0][1]!r}' if show_values else '')
            for field, v in out.items()]


def report(line, lines):
    print(line, flush=True)
    lines.append(line)


def main():
    """--no-values: field names and counts only. --obis: also run edna2obis (workbooks built from
    faire_two_assays.xlsx only). --only-obis: edna2obis only. --report FILE: also write the lines there."""
    argv = sys.argv[1:]
    show_values = '--no-values' not in argv
    report_path = argv[argv.index('--report') + 1] if '--report' in argv else None
    books = [Path(a).resolve() for i, a in enumerate(argv)
             if not a.startswith('--') and not (i and argv[i - 1] == '--report')]
    lines = []
    for book in books:
        for name, (driver, args, output) in ({} if '--only-obis' in argv else RUNS).items():
            results = {}
            for mode in ('copy', 'normalise'):
                with tempfile.TemporaryDirectory() as work:
                    rc, log = run(mode, driver, args, book, work)
                    out = Path(work) / output
                    results[mode] = (rc, table(out, True) if rc == 0 and out.exists() else None,
                                     [line for line in log if 'ERROR' in line or 'Error' in line][-1:])
            (rc1, t1, e1), (rc2, t2, e2) = results['copy'], results['normalise']
            if rc1 or rc2:
                verdict = f'not comparable: exit {rc1} (copy) vs {rc2} (normalised): ' + '; '.join(e1 + e2)[:200]
            else:
                diffs = compare(t1, t2, show_values)
                verdict = 'identical' if not diffs else '**differs**: ' + '; '.join(diffs)
            report(f'| {book.stem} | {name} | {verdict} |', lines)
        if '--obis' in argv or '--only-obis' in argv:
            results = {}
            for mode in ('copy', 'normalise'):
                with tempfile.TemporaryDirectory() as work:
                    rc, log, tables = run_obis(mode, book, work)
                    results[mode] = (rc, tables, [line for line in log if 'ERROR' in line or 'Error' in line][-1:])
            (rc1, t1, e1), (rc2, t2, e2) = results['copy'], results['normalise']
            if rc1 or rc2:
                report(f'| {book.stem} | edna2obis Darwin Core | not comparable: exit {rc1} (copy) vs {rc2} (normalised): '
                       + '; '.join(e1 + e2)[:200] + ' |', lines)
                continue
            for f in sorted(set(t1) | set(t2)):
                if f not in t1 or f not in t2:
                    verdict = '**differs**: only ' + ('after normalising' if f in t2 else 'with a plain copy')
                else:
                    diffs = compare(t1[f], t2[f], show_values)
                    verdict = 'identical' if not diffs else '**differs**: ' + '; '.join(diffs)
                report(f'| {book.stem} | edna2obis Darwin Core: {f} | {verdict} |', lines)
    if report_path:
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        head = ['| Workbook | Tool and output | With normalise_faire.py vs a plain copy |', '|---|---|---|']
        Path(report_path).write_text('\n'.join(head + lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
