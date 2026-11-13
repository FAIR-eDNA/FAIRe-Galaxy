"""Say what each input file looks like and where it goes in the FAIRe mapper tools.

Usage: python faire_mapper_identify.py --checklist CHECKLIST --file PATH [--name NAME] [--format EXT]
           [--file PATH ...] -o REPORT.tsv

Each sheet of an Excel file is reported on its own. The sample tables found are read first, and
their sample names used to recognise the OTU tables (whose columns or rows are those samples).
A best guess from each table's shape, headers and values (faire_mapper_kinds.describe): the user
decides.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pandas as pd

import faire_mapper as fm
import faire_mapper_kinds as fk
import faire_mapper_library as fl
import faire_mapper_otu as fo

# What to check or do next, for each kind
NEXT = {
    'sample': 'Run FAIRe mapper: profile a table to check how it is read, then propose mapping.',
    'otu': "Set 'Write this table as' to otuFinal and taxaFinal if these are the reads you report (after "
           "filtering and curation), or to otuRaw and taxaRaw if this is the table before that.",
    'taxonomy': 'Give it beside the OTU table whose sequence IDs it lists.',
    'library': 'Each row should be one library: one amplicon of one sample.',
    'crosswalk': 'Check it before apply mapping uses it.',
    'dictionary': 'Its descriptions help propose mapping match columns whose headers are unclear.',
    'project_values': "Two columns: the FAIRe term and its value (or one column per assay).",
    'primers': 'Find primers and build primer table can use it.',
    'sequences': ("Give it beside the OTU table that names these sequences (ASV_1, ASV_2 ...) but doesn't hold "
                  "them, such as an LCA output."),
    'text': 'Find primers reads primer names and sequences from methods text.',
    'unknown': '',
}


def sheets_of(path):
    if fm._is_excel(path):
        return pd.ExcelFile(path).sheet_names
    return [None]


def sample_names(df):
    """The sample names of a sample table: its samp_name column, or its first column."""
    col = fl.find_columns(list(df.columns)).get('samp_name', df.columns[0])
    return [fo.norm_id(v) for v in df[col] if fo.norm_id(v)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--checklist', required=True, help='FAIRe checklist (xlsx)')
    ap.add_argument('--file', action='append', required=True, help='a file to look at; repeat for each')
    ap.add_argument('--name', action='append', help='name of each file for the report (default: file name)')
    ap.add_argument('--format', action='append', help="Galaxy format of each file (txt marks text)")
    ap.add_argument('-o', '--output', required=True, help='report (tab-separated)')
    args = ap.parse_args(argv)

    k = len(args.file)
    names = ((args.name or []) + [''] * k)[:k]
    formats = ((args.format or []) + [''] * k)[:k]
    terms = fm.load_checklist(args.checklist)
    term_names = {frozenset(a) for t in terms if 'sampleMetadata' in t.sheets for a in t.aliases}
    faire_terms = {t.name for t in terms}

    # Read every table once; text files and unreadable sheets are noted
    items = []
    for path, name, fmt in zip(args.file, names, formats):
        name = name or Path(path).name
        known_kind = fk.describe_file(path)   # FASTA files and PDFs, by their content
        if known_kind:
            items.append({'name': name, 'sheet': '', 'df': None, 'error': '', 'fmt': fmt, 'path': path,
                          'kind': known_kind})
            continue
        files, form = fl.read_file_list(path)
        if files is not None:   # md5sum's output or a list of file names: no header, so not a table otherwise
            items.append({'name': name, 'sheet': '', 'df': files, 'error': '', 'fmt': fmt, 'path': path,
                          'file_list': form})
            continue
        try:
            sheets = sheets_of(path)
        except Exception as e:   # not a readable spreadsheet
            items.append({'name': name, 'sheet': '', 'df': None, 'error': str(e), 'fmt': fmt, 'path': path})
            continue
        for sh in sheets:
            item = {'name': name, 'sheet': sh or '', 'df': None, 'error': '', 'fmt': fmt, 'path': path}
            try:
                item['df'] = fo.read_table_any(path, sh)
            except SystemExit as e:
                item['error'] = str(e).replace('ERROR: ', '')
            except Exception as e:
                item['error'] = str(e)
            items.append(item)

    # First pass: find the sample tables and their sample names
    known = []
    for it in items:
        if it['df'] is not None:
            kind, _ = fk.describe(it['df'], (), term_names, faire_terms)
            if kind == 'sample':
                known += sample_names(it['df'])

    rows = []
    for it in items:
        if it.get('kind'):
            kind, why = it['kind']
        elif it['df'] is None:
            if it['fmt'] == 'txt' or Path(it['name']).suffix.lower() in ('.txt', '.md'):
                kind, why = fk.describe_text(it['path'])
            else:
                kind, why = 'unknown', [it['error'] or 'could not be read as a table']
        else:
            kind, why = fk.describe(it['df'], known, term_names, faire_terms)
            if it.get('file_list') and kind == 'library':
                why = [fl.FILE_LIST_NOTES[it['file_list']]] + why
            if kind in ('unknown', 'text') and (it['fmt'] == 'txt' or Path(it['name']).suffix.lower() in ('.txt', '.md')):
                kind, why = fk.describe_text(it['path'])
        nxt = NEXT[kind]
        if kind == 'otu' and any('reads summed per taxon' in w for w in why):
            nxt = "Reads summed per taxon (curated): give it as final (otuFinal and taxaFinal)."
        elif kind == 'otu' and any('curated names' in w for w in why):
            nxt += " If its column of names holds your curated names, give that column as 'Column of curated names'."
        elif kind == 'text' and not any('primer' in w for w in why):
            nxt = ("If it describes the columns of your table, give it as the 'Data dictionary' in propose "
                   "mapping; if it describes your methods, find primers can read it.")
        if kind == 'text' and fk.ft.is_pdf(it['path']):
            nxt = ("If it describes your methods, find primers can read it. The other values for the whole "
                   "project come from the methods too: give them as the values for the whole project, with this "
                   "document beside you.")
        rows.append({'file': it['name'], 'sheet': it['sheet'], 'kind': fk.SHORT[kind], 'looks like': fk.NAME[kind],
                     'why': '; '.join(why), 'give it as': fk.WHERE[kind] if kind != 'text' else
                     "'Methods text' in FAIRe mapper: find primers, or 'Data dictionary' in propose mapping",
                     'then': nxt})

    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter='\t')
        w.writeheader()
        w.writerows(rows)
    counts = {}
    for r in rows:
        counts[r['kind']] = counts.get(r['kind'], 0) + 1
    print(f'INFO: {k} files ({len(rows)} tables or texts, counting each Excel sheet): '
          + ', '.join(f'{kind} {n}' for kind, n in counts.items()))
    if not known:
        print('INFO: no sample table was found, so OTU tables were recognised by their counts alone')
    return 0


if __name__ == '__main__':
    sys.exit(main())
