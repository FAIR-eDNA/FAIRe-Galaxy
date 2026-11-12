"""Relabel FAIRe projectMetadata assay columns by their assay_name.

The FAIRe checklist (and FAIRe-ator) label assay-specific columns in
projectMetadata as 'assay1', 'assay2', ... and record the real assay name in
the 'assay_name' row. With a single assay, the assay-specific values sit in
'project_level'. FAIRe2QIIME expects one column per assay, headed by the
assay_name value (the FAIRe-NOAA layout).

This script writes a copy of the workbook in that layout. Workbooks already
in the FAIRe-NOAA layout pass through unchanged. The three metadata sheets are
copied as values only, which is all FAIRe2QIIME reads. Reading through pandas (read-only)
also accepts workbooks written by FAIRe-ator, which openpyxl cannot open in
full because of a dangling drawing reference.

Cell values are copied as they are. Only empty cells are read as empty, so text
such as NA or N/A is kept (upstream FAIRe2NCBI reads NA and N/A in
associatedSequences as filled), and text starting with '=' is saved as text.
"""

import argparse
import re
import sys

import pandas as pd

# The text pandas reads as empty by default (na_values of pandas.read_excel). Upstream FAIRe2QIIME
# reads the workbook with these defaults, so --check_filled treats them as empty.
PANDAS_NA = frozenset({'', '#N/A', '#N/A N/A', '#NA', '-1.#IND', '-1.#QNAN', '-NaN', '-nan', '1.#IND',
                       '1.#QNAN', '<NA>', 'N/A', 'NA', 'NULL', 'NaN', 'None', 'n/a', 'nan', 'null'})


def blank(value):
    return value is None or (isinstance(value, float) and pd.isna(value)) or str(value).strip() == ''


def read_as_empty(value):
    """True for an empty cell, or text that pandas reads as empty by default (such as NA)."""
    return blank(value) or (isinstance(value, str) and value in PANDAS_NA)


def write_values(sheets, path_out):
    """Write each sheet's values, keeping all text as text. openpyxl would otherwise save text
    starting with '=' as a formula with no result, and text such as #N/A as an Excel error, both of
    which read back as empty cells. (pandas reads a real formula as its value and a real error as
    empty, so neither can reach here.)"""
    with pd.ExcelWriter(path_out, engine='openpyxl') as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, header=False, index=False)
        for ws in writer.book.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    if cell.data_type in ('f', 'e'):
                        cell.data_type = 's'


def check_columns(sheets, columns):
    """Stop if a column is in neither experimentRunMetadata nor sampleMetadata (row 3)."""
    found = set()
    for name in ('experimentRunMetadata', 'sampleMetadata'):
        df = sheets[name]
        if len(df) >= 3:
            found.update(str(v) for v in df.iloc[2] if not blank(v))
    for col in columns:
        if col and col not in found:
            sys.exit(f"ERROR: column '{col}' is not in experimentRunMetadata or sampleMetadata "
                     "(field names are expected on row 3).")


def run_column(sheets, name):
    """Values of a column of experimentRunMetadata (field names on row 3, data from row 4)."""
    df = sheets['experimentRunMetadata']
    if len(df) < 3:
        return None
    header = [None if blank(v) else str(v).strip() for v in df.iloc[2]]
    if name not in header:
        return None
    return df.iloc[3:, header.index(name)]


def check_filled(sheets, columns):
    """Stop if a column of experimentRunMetadata is empty for any run."""
    for col in columns:
        values = run_column(sheets, col)
        if values is None:
            sys.exit(f"ERROR: experimentRunMetadata has no '{col}' column.")
        lib = run_column(sheets, 'lib_id')
        empty = [i for i, v in values.items() if read_as_empty(v)]
        if empty:
            names = [str(lib[i]) for i in empty[:5]] if lib is not None else [f'row {i + 1}' for i in empty[:5]]
            sys.exit(f"ERROR: {len(empty)} of {len(values)} runs have no {col} in experimentRunMetadata "
                     f"(for example {', '.join(names)}). Add them, or turn off the option that needs them.")


# FAIRe's terms for a value that is not given. FAIRe2QIIME names its files by target_gene and
# target_subfragment, so 'not applicable' would give 16S-not.
MISSING_TERMS = ('not applicable', 'missing', 'not collected', 'not provided', 'restricted access')
NAMING_TERMS = ('target_gene', 'target_subfragment')


def blank_missing_terms(pm, term_col):
    """Empty the cells of target_gene and target_subfragment that hold a FAIRe missing-value term."""
    terms = pm[pm.columns[term_col]].astype(str).str.strip()
    for term in NAMING_TERMS:
        seen = []
        for r in pm.index[terms == term]:
            for c in range(len(pm.columns)):
                v = pm.iat[r, c]
                if c != term_col and isinstance(v, str) and v.strip().lower().startswith(MISSING_TERMS):
                    pm.iat[r, c] = None
                    if v.strip() not in seen:
                        seen.append(v.strip())
        for v in seen:
            print(f"INFO: {term} '{v}' read as empty, as FAIRe's term for no value, so the output files are not "
                  f"named after it")


def norm_name(name):
    return re.sub(r'[^a-z0-9]', '', str(name).lower())


def match_assay_names(pm, sheets):
    """Every assay_name used in experimentRunMetadata needs a projectMetadata column of the same name.
    A spelling that differs only in case or punctuation (12S-V5 and 12S_V5) is corrected, with a
    warning; anything else stops with a plain message."""
    used = run_column(sheets, 'assay_name')
    if used is None:
        return
    used = [str(v).strip() for v in used if not blank(v)]
    headers = [None if blank(v) else str(v).strip() for v in pm.iloc[0]]
    for assay in dict.fromkeys(used):
        if assay in headers:
            continue
        near = [i for i, h in enumerate(headers) if h and norm_name(h) == norm_name(assay)]
        if len(near) == 1:
            print(f"WARNING: assay_name '{assay}' in experimentRunMetadata is written '{headers[near[0]]}' in "
                  f"projectMetadata; using '{assay}'. Correct the workbook so the names match.")
            pm.iat[0, near[0]] = assay
            headers[near[0]] = assay
        else:
            known = [h for h in headers if h and h not in ('requirement_level_code', 'section', 'term_name',
                                                           'project_level')]
            sys.exit(f"ERROR: assay_name '{assay}' in experimentRunMetadata has no matching column in "
                     f"projectMetadata (its assays are: {', '.join(known) or 'none'}). The names must match.")


def normalise(path_in, path_out, columns=(), filled=()):
    try:
        sheets = pd.read_excel(path_in, sheet_name=None, header=None, keep_default_na=False, na_values=[''])
    except Exception as err:  # noqa: BLE001 - report any read failure plainly
        sys.exit(f"ERROR: could not read the workbook ({err}).")
    for name in ('projectMetadata', 'sampleMetadata', 'experimentRunMetadata'):
        if name not in sheets:
            sys.exit(f"ERROR: the workbook has no '{name}' sheet.")
    check_columns(sheets, columns)
    check_filled(sheets, filled)

    pm = sheets['projectMetadata']
    headers = [None if blank(v) else str(v).strip() for v in pm.iloc[0]]
    for needed in ('term_name', 'project_level'):
        if needed not in headers:
            sys.exit(f"ERROR: projectMetadata has no '{needed}' column in its first row.")
    term_col = headers.index('term_name')
    level_col = headers.index('project_level')

    rows = pm.index[pm[pm.columns[term_col]].astype(str).str.strip() == 'assay_name']
    if len(rows) == 0:
        sys.exit("ERROR: projectMetadata has no 'assay_name' row.")
    name_row = rows[0]

    numbered = [(h, i) for i, h in enumerate(headers) if h and re.fullmatch(r'assay\d+', h)]
    if numbered:
        for header, i in numbered:
            assay = pm.iat[name_row, i]
            if blank(assay):
                continue
            pm.iat[0, i] = str(assay).strip()
            print(f"INFO: projectMetadata column '{header}' relabelled as '{assay}'")
    else:
        assay = pm.iat[name_row, level_col]
        listed = [] if blank(assay) else [a.strip() for a in str(assay).split('|') if a.strip()]
        if listed and all(a in headers for a in listed):
            print("INFO: projectMetadata already has assay columns named by assay_name")
        elif len(listed) > 1:
            sys.exit(f"ERROR: projectMetadata lists several assays ('{assay}') in project_level "
                     "but has no assay1, assay2, ... columns for their details.")
        elif listed:
            # Single-assay layout: copy project_level into a column named by the assay.
            new = pm.iloc[:, level_col].copy()
            new.iloc[0] = str(assay).strip()
            pm[pm.columns.max() + 1] = new
            print(f"INFO: single assay '{assay}': copied project_level values to an assay column")
        else:
            print("INFO: projectMetadata already has assay columns named by assay_name")

    match_assay_names(pm, sheets)
    blank_missing_terms(pm, term_col)
    # Only the three metadata sheets, which is all FAIRe2QIIME reads: OTU and taxonomy sheets can be large,
    # and FAIRe2QIIME opens the workbook once for each sheet it reads.
    write_values({name: sheets[name] for name in ('projectMetadata', 'sampleMetadata', 'experimentRunMetadata')},
                 path_out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('input')
    parser.add_argument('output')
    parser.add_argument('--check_column', action='append', default=[],
                        help='column that must exist in experimentRunMetadata or sampleMetadata')
    parser.add_argument('--check_filled', action='append', default=[],
                        help='experimentRunMetadata column that must have a value for every run')
    args = parser.parse_args()
    normalise(args.input, args.output, args.check_column, args.check_filled)
