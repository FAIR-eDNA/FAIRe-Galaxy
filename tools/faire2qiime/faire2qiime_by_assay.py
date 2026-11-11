"""Run FAIRe2QIIME, once for each assay when two assays would get the same file names.

FAIRe2QIIME names its files by target_gene and target_subfragment ({project_id}_{gene}_metadata.tsv,
{seq_run_id}_{gene}_manifest.tsv), so two assays of the same gene and fragment (Wilderlab's RV, LG
and RJ, all 12S) overwrite each other's files. When that would happen, this runs FAIRe2QIIME on a
copy of the workbook for each assay, and names every file by its assay_name instead
({project_id}_{assay}_metadata.tsv). Otherwise it runs FAIRe2QIIME once, as it is.

Usage: python faire2qiime_by_assay.py UPSTREAM.py WORKBOOK.xlsx OUTDIR -- ARGUMENTS
       (ARGUMENTS: FAIRe2QIIME's own, except --path_faire and --output_directory)

The workbook is the one normalise_faire.py writes: projectMetadata with one column per assay,
headed by its assay_name. FAIRe2QIIME runs through faire2qiime_run.py, which reads the workbook so that
a '#' inside a cell and IDs such as 001 are kept.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pandas as pd

import normalise_faire

HERE = os.path.dirname(os.path.abspath(__file__))

SHEETS = ('projectMetadata', 'sampleMetadata', 'experimentRunMetadata')


def blank(v):
    return v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == ''


def header_row(df):
    """The first row whose first cell does not start with # (FAIRe2QIIME reads with comment='#')."""
    for i in range(len(df)):
        first = df.iat[i, 0]
        if not blank(first) and not str(first).strip().startswith('#'):
            return i
    sys.exit('ERROR: a sheet of the workbook has no row of column names.')


def short_names(sheets):
    """{assay_name: the short name FAIRe2QIIME uses in file names}, with the rule FAIRe2QIIME uses:
    the first word of target_gene, and the first word of target_subfragment without - or _."""
    pm = sheets['projectMetadata']
    h = header_row(pm)
    headers = [None if blank(v) else str(v).strip() for v in pm.iloc[h]]
    term, level = headers.index('term_name'), headers.index('project_level')
    terms = [None if blank(v) else str(v).strip() for v in pm.iloc[:, term]]

    def value(row_name, col):
        if row_name not in terms:
            return None
        r = terms.index(row_name)
        v = pm.iat[r, col]
        return pm.iat[r, level] if blank(v) else v

    out = {}
    for col in range(level + 1, len(headers)):
        assay = headers[col]
        if not assay:
            continue
        gene = value('target_gene', col)
        gene = str(gene).split(' ')[0] if not blank(gene) else 'nan'
        sub = value('target_subfragment', col)
        part = str(sub).split(' ')[0].replace('-', '').replace('_', '') if not blank(sub) else ''
        out[assay] = f'{gene}-{part}' if part else gene
    return out


def one_assay(sheets, assay):
    """The three metadata sheets, with only this assay's projectMetadata column and runs."""
    out = {}
    for name, df in sheets.items():
        df = df.copy()
        if name == 'projectMetadata':
            h = header_row(df)
            headers = [None if blank(v) else str(v).strip() for v in df.iloc[h]]
            level = headers.index('project_level')
            keep = [i for i, x in enumerate(headers) if i <= level or x == assay]
            df = df.iloc[:, keep]
        elif name == 'experimentRunMetadata':
            h = header_row(df)
            headers = [None if blank(v) else str(v).strip() for v in df.iloc[h]]
            col = headers.index('assay_name')
            rows = [i for i in range(len(df)) if i <= h or str(df.iat[i, col]).strip() == assay]
            df = df.iloc[rows]
        out[name] = df
    return out


BANNER = re.compile(r'F A I R e 2 Q I I M E|NOAA FAIRe Excel to QIIME2|pyfiglet|^\W*=+\W*$')


def run(upstream, workbook, outdir, rest, echo=True):
    """FAIRe2QIIME's output lines; printed as they are when echo is set."""
    r = subprocess.run([sys.executable, os.path.join(HERE, 'faire2qiime_run.py'), upstream, '--path_faire', workbook,
                        '--output_directory', outdir, *rest], capture_output=True, text=True)
    if echo or r.returncode:
        sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    if r.returncode:
        sys.exit(r.returncode)
    return r.stdout.splitlines()


def main(upstream, workbook, outdir, rest):
    # FAIRe2QIIME reads these three sheets only; the OTU and taxonomy sheets can be large.
    # Values as written: only empty cells are empty.
    sheets = pd.read_excel(workbook, sheet_name=list(SHEETS), header=None, keep_default_na=False, na_values=[''])
    shorts = short_names(sheets)
    erm = sheets['experimentRunMetadata']
    h = header_row(erm)
    headers = [None if blank(v) else str(v).strip() for v in erm.iloc[h]]
    if 'assay_name' not in headers:
        sys.exit("ERROR: experimentRunMetadata has no assay_name column.")
    used = {str(v).strip() for v in erm.iloc[h + 1:, headers.index('assay_name')] if not blank(v)}
    shorts = {a: s for a, s in shorts.items() if a in used}
    by_short = {}
    for a, s in shorts.items():
        by_short.setdefault(s, []).append(a)
    shared = {s: a for s, a in by_short.items() if len(a) > 1}
    if not shared:
        run(upstream, workbook, outdir, rest)
        return
    print('Note: these assays share a target gene and fragment, so their files would have the same names: '
          + '; '.join(f"{', '.join(a)} ({s})" for s, a in shared.items())
          + '. Each assay was converted on its own, and every file is named by its assay_name.')
    for k, (assay, short) in enumerate(shorts.items()):
        safe = re.sub(r'[^A-Za-z0-9_.-]', '_', assay)
        with tempfile.TemporaryDirectory() as tmp:
            wb = os.path.join(tmp, 'assay.xlsx')
            normalise_faire.write_values(one_assay(sheets, assay), wb)  # text starting with '=' stays text
            os.mkdir(os.path.join(tmp, 'out'))
            lines = run(upstream, wb, os.path.join(tmp, 'out'), rest, echo=False)
            for line in lines:
                # the banner once; FAIRe2QIIME's own lines on the files are replaced by ours below
                if (BANNER.search(line) and k == 0) or not (BANNER.search(line) or line.startswith('Generated ')):
                    print(line)
            for f in sorted(os.listdir(os.path.join(tmp, 'out'))):
                m = re.fullmatch(r'(.*)_' + re.escape(short) + r'_(metadata|manifest)\.tsv', f)
                if not m:
                    sys.exit(f'ERROR: FAIRe2QIIME wrote a file that was not expected for assay {assay}: {f}')
                new = f'{m.group(1)}_{safe}_{m.group(2)}.tsv'
                shutil.move(os.path.join(tmp, 'out', f), os.path.join(outdir, new))
                print(f'Generated {m.group(2)} file {new} (assay {assay}; FAIRe2QIIME named it {f})')


if __name__ == '__main__':
    if len(sys.argv) < 5 or sys.argv[4] != '--':
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[5:])
