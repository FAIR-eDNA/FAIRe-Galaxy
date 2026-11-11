"""Galaxy driver for FAIRe2ENA.

Runs the upstream FAIRe2ENA scripts (faire2ena_sample.py, faire2ena_run.py)
without modifying them, and adds:

  * checks that stop with a clear message where the upstream code would
    raise an unexplained KeyError or write invalid XML;
  * conversion of eventDate values with a +hh:mm/-hh:mm offset (or stored as
    Excel dates) to a form ENA accepts, so they are not replaced with
    'not provided';
  * a choice of NCBI taxon for the samples (upstream hard-codes 408172,
    marine metagenome);
  * filtering of runs to one assay or to some sequencing runs, and an optional FTP sub-directory prefix
    for read file names;
  * one experiment and run for a library that holds several assays (rows with the same sample
    and files), as ENA takes each set of files once, with the lab's name for the library as the
    aliases (FAIRe's lib_id is one amplicon of a sample; the FAIRe mapper writes it as the
    library name, assay_name and seq_run_id, so those two are taken off).
"""

import argparse
import datetime
import os
import re
import sys
import xml.etree.ElementTree as ET

import pandas as pd

sys.dont_write_bytecode = True  # tool directories are often read-only on Galaxy servers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import faire2ena_run as upstream_run  # noqa: E402
import faire2ena_sample as upstream_sample  # noqa: E402

SUBMISSION_XML = """<?xml version="1.0" encoding="UTF-8"?>
<SUBMISSION>
   <ACTIONS>
      <ACTION>
         <ADD/>
      </ACTION>
   </ACTIONS>
</SUBMISSION>
"""

OFFSET_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)([+-]\d{2}):?(\d{2})$'
)


def fail(message):
    sys.stderr.write(f"ERROR: {message}\n")
    sys.exit(1)


def is_blank(value):
    return value is None or (isinstance(value, float) and pd.isna(value)) or str(value).strip() == ''


def normalise_date(value):
    """Return a collection date string ENA's regular expression accepts."""
    if isinstance(value, (pd.Timestamp, datetime.datetime)):
        ts = pd.Timestamp(value)
        if ts.tzinfo is not None:
            ts = ts.tz_convert('UTC')
            return ts.strftime('%Y-%m-%dT%H:%M' + (':%S' if ts.second else '') + 'Z')
        if (ts.hour, ts.minute, ts.second) == (0, 0, 0):
            return ts.strftime('%Y-%m-%d')
        return ts.strftime('%Y-%m-%dT%H:%M' + (':%S' if ts.second else ''))
    if isinstance(value, datetime.date):
        return value.isoformat()
    if is_blank(value):
        return value
    text = str(value).strip()
    match = OFFSET_RE.match(text)
    if match:
        local, hours, minutes = match.groups()
        sign = -1 if hours.startswith('-') else 1
        offset = datetime.timedelta(hours=abs(int(hours)), minutes=int(minutes)) * sign
        utc = datetime.datetime.fromisoformat(local.split('.')[0]) - offset
        return utc.strftime('%Y-%m-%dT%H:%M' + (':%S' if utc.second else '') + 'Z')
    return text


def read_sheet(path, sheet, **kwargs):
    try:
        return pd.read_excel(path, sheet_name=sheet, **kwargs)
    except ValueError as err:
        fail(f"could not read the '{sheet}' sheet from the workbook ({err}).")


def run_sample(args):
    df = read_sheet(args.input_file, 'sampleMetadata', skiprows=2)
    project_df = read_sheet(args.input_file, 'projectMetadata')

    for col in ('term_name', 'project_level'):
        if col not in project_df.columns:
            fail(f"projectMetadata needs a '{col}' column in its first row.")
    pid = project_df.loc[project_df['term_name'] == 'project_id', 'project_level']
    if pid.empty or is_blank(pid.values[0]):
        fail("projectMetadata has no value for project_id (project_level column).")
    project_name = pid.values[0]

    for col in ('samp_name', 'samp_category'):
        if col not in df.columns:
            fail(f"sampleMetadata has no '{col}' column. Field names are expected on row 3.")
    df = df[~df['samp_name'].apply(is_blank)].copy()
    if df.empty:
        fail("sampleMetadata has no samples (no samp_name values below row 3).")

    if args.convert_dates and 'eventDate' in df.columns:
        # repr() keeps Excel dates (read as Timestamps) apart from text, so they count as converted
        before = df['eventDate'].apply(lambda v: v if isinstance(v, str) else repr(v))
        df['eventDate'] = df['eventDate'].apply(normalise_date).astype(object)
        changed = int((before != df['eventDate'].apply(lambda v: v if isinstance(v, str) else repr(v))).sum())
        print(f"INFO: converted {changed} eventDate value(s) to a form ENA accepts")
    elif 'eventDate' in df.columns:
        df['eventDate'] = df['eventDate'].apply(lambda v: v if is_blank(v) else str(v)).astype(object)

    # Upstream fills only some missing mandatory fields with defaults and raises
    # a KeyError for the rest. Find those first and report them together.
    problems = {}
    for row in df.to_dict(orient='records'):
        ena_data = upstream_sample.convert_faire_to_ena(row, project_name)
        _, missing = upstream_sample.validate_mandatory_fields(ena_data)
        for field in missing:
            faire_term = upstream_sample.ENA_TO_FAIRE_MAPPING.get(field)
            if field == 'geographic location (country and/or sea)':
                faire_term = 'geo_loc_name'
            if faire_term not in upstream_sample.DEFAULTS_DICT:
                problems.setdefault((field, faire_term or 'unknown'), []).append(row['samp_name'])
    if problems:
        lines = ["these mandatory ENA fields are empty and have no default:"]
        for (field, term), samples in problems.items():
            shown = ', '.join(map(str, samples[:5])) + (' ...' if len(samples) > 5 else '')
            lines.append(f"  - '{field}' (FAIRe term {term}): {len(samples)} sample(s): {shown}")
        lines.append("Fill these terms in sampleMetadata and run the tool again.")
        fail('\n'.join(lines))

    upstream_sample.process_faire_df(
        df, args.output_file, project_name, taxon_id=str(args.taxon_id), center_name=args.center_name
    )
    with open(args.output_file, encoding='utf-8') as f:
        n = f.read().count('<SAMPLE ')
    print(f"INFO: wrote {n} sample(s) for project {project_name} with taxon {args.taxon_id}")

    if args.submission_file:
        with open(args.submission_file, 'w', encoding='utf-8') as f:
            f.write(SUBMISSION_XML)


def receipt_accessions(path):
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as err:
        fail(f"the ENA receipt is not valid XML ({err}).")
    if root.tag != 'RECEIPT':
        fail("the receipt file is not an ENA receipt (no <RECEIPT> element).")
    if root.get('success', '').lower() == 'false':
        errors = [e.text for e in root.iter('ERROR') if e.text]
        fail("the ENA receipt reports a failed submission:\n  " + '\n  '.join(errors or ['(no message)']))
    return {s.get('alias') for s in root.iter('SAMPLE') if s.get('alias') and s.get('accession')}


# Fields that must agree for the rows of one library to be joined.
SHARED_SAME = ('samp_name', 'checksum_filename', 'checksum_filename2', 'lib_conc', 'lib_conc_unit', 'lib_conc_meth')


def library_name(lib, assay, run):
    """The lab's name for a library, from a lib_id made as the FAIRe mapper makes it (the library
    name, assay_name and seq_run_id, as FAIRe takes a library to be one amplicon of a sample):
    M097_16SFish_LerayCOI_Fish16S_AGRF_2024-12 -> (M097_16SFish_LerayCOI, AGRF_2024-12). A lib_id
    that does not end with its assay is returned as it is. The second value is the run taken off."""
    if assay and run and lib.endswith(f'_{assay}_{run}') and len(lib) > len(assay) + len(run) + 2:
        return lib[:-len(assay) - len(run) - 2], run
    if assay and lib.endswith(f'_{assay}') and len(lib) > len(assay) + 1:
        return lib[:-len(assay) - 1], ''
    return lib, ''


def join_shared_libraries(df):
    """One row for each library: rows of one sample with the same files (the amplicons of a library
    that holds several assays) are joined, as ENA takes each set of files once. lib_id, which
    becomes the experiment and run aliases, is the library's own name: the lib_id without its assay
    and run, with the run (then the whole lib_id) kept where names would repeat. Returns the rows,
    the number of libraries joined, the assays seen, any problems (rows that share files but differ
    in another field), the lib_ids of those rows, and notes for the log."""
    val = lambda v: '' if is_blank(v) else str(v).strip()  # noqa: E731
    df = df.copy()
    runs = df['seq_run_id'].apply(val) if 'seq_run_id' in df.columns else pd.Series([''] * len(df), index=df.index)
    named = [library_name(val(lib), val(a), r) for lib, a, r in zip(df['lib_id'], df['assay_name'], runs)]
    df['_orig'] = df['lib_id'].apply(val)
    df['_name'] = [n for n, _ in named]
    df['_run'] = [r for _, r in named]
    keys = [('files', val(s), val(a), val(b)) if val(a) else ('lib', lib, '', '')
            for s, lib, a, b in zip(df['samp_name'], df['_orig'], df['filename'], df['filename2'])]
    df['_key'] = keys
    keep, problems, joined, assays, bad, one_id = [], [], 0, [], set(), set()
    for k in dict.fromkeys(keys):
        rows = df[df['_key'] == k]
        if len(rows) == 1:
            keep.append(rows)
            continue
        differ = [c for c in SHARED_SAME if c in rows and rows[c].apply(val).nunique() > 1]
        if differ:
            problems.append(f"{rows['_orig'].iloc[0]}: several rows have the same files, but they differ in "
                            f"{', '.join(differ)}")
            bad.update(rows['_orig'])
            keep.append(rows)
            continue
        if rows['_orig'].nunique() == 1:
            one_id.add(rows['_orig'].iloc[0])
        first = rows.iloc[[0]].copy()
        common = list(dict.fromkeys(rows['_name']))
        first['_name'] = common[0] if len(common) == 1 else (
            re.sub(r'_[^_]*$', '', os.path.commonprefix(common)) or common[0])
        first['_orig'] = first['_name'].iloc[0] + ('_' + first['_run'].iloc[0] if first['_run'].iloc[0] else '')
        keep.append(first)
        joined += 1
        assays += [a for a in rows['assay_name'].apply(val) if a and a not in assays]
    out = pd.concat(keep)
    first_ids = list(out['lib_id'].apply(val))
    level = [0] * len(out)

    def ids():
        return [n if lv == 0 else (f'{n}_{r}' if r else o) if lv == 1 else o
                for n, r, o, lv in zip(out['_name'], out['_run'], out['_orig'], level)]
    for _ in range(2):
        seen = {}
        for i, o in zip(ids(), out['_orig']):
            seen.setdefault(i, set()).add(o)
        level = [lv + 1 if len(seen[i]) > 1 and lv < 2 else lv for i, lv in zip(ids(), level)]
    out['lib_id'] = ids()
    notes = []
    changed = [(o, i) for o, i in zip(first_ids, out['lib_id']) if o and o != i]
    if changed:
        notes.append(f"the experiment and run aliases are each library's own name: the lib_id without its "
                     f"assay_name and seq_run_id (e.g. {changed[0][0]} -> {changed[0][1]})")
    if any(level):
        notes.append(f"{sum(lv > 0 for lv in level)} libraries keep the run or assay in their alias, so that each "
                     "is unique")
    if one_id:
        notes.append(f"{len(one_id)} lib_id{' names' if len(one_id) == 1 else 's name'} several assays (e.g. "
                     f"{sorted(one_id)[0]}); FAIRe takes a library to be one amplicon of a sample, so each assay's "
                     "row should have its own lib_id (the FAIRe mapper adds assay_name and seq_run_id to the "
                     "library name)")
    bad = {i for i, o in zip(out['lib_id'], out['_orig']) if o in bad}
    return out.drop(columns=['_orig', '_name', '_run', '_key']), joined, assays, problems, bad, notes


def run_run(args):
    df = read_sheet(args.input_file, 'experimentRunMetadata', skiprows=2)
    for col in ('samp_name', 'lib_id', 'assay_name', 'filename', 'filename2'):
        if col not in df.columns:
            fail(f"experimentRunMetadata has no '{col}' column. Field names are expected on row 3.")

    if args.assay_name:
        available = sorted({str(a) for a in df['assay_name'].dropna()})
        df = df[df['assay_name'].astype(str) == args.assay_name]
        if df.empty:
            fail(f"no runs with assay_name '{args.assay_name}'. Assays in the workbook: {', '.join(available)}")
    if args.seq_run_id:
        # Sequencing runs to include, as FAIRe2NCBI SRA allows.
        if 'seq_run_id' not in df.columns:
            fail("experimentRunMetadata has no 'seq_run_id' column, so runs cannot be chosen by sequencing run.")
        wanted = [v.strip() for v in args.seq_run_id.split(',') if v.strip()]
        values = df['seq_run_id'].apply(lambda v: '' if is_blank(v) else str(v).strip())
        available = list(dict.fromkeys(v for v in values if v))
        unknown = [w for w in wanted if w not in available]
        if unknown:
            fail("no runs with seq_run_id " + ', '.join(f"'{u}'" for u in unknown)
                 + (f" for assay '{args.assay_name}'" if args.assay_name else '')
                 + f". Sequencing runs in the workbook: {', '.join(available[:20])}"
                 + (' ...' if len(available) > 20 else ''))
        df = df[values.isin(wanted)]
        print(f"INFO: kept {len(df)} row(s) with seq_run_id in: {', '.join(wanted)}")

    df, joined, assays, join_problems, bad, join_notes = join_shared_libraries(df)
    if joined:
        print(f"INFO: joined the rows of {joined} libraries that hold several assays ({' and '.join(assays)}): "
              "one experiment and run each")
    for note in join_notes:
        print(f"INFO: {note}")

    accessions = receipt_accessions(args.receipt_file)
    selected = df[df['samp_name'].isin(accessions)].copy()
    if selected.empty:
        fail("none of the samp_name values in experimentRunMetadata match a sample alias in the ENA receipt.")

    problems = list(join_problems)
    md5 = re.compile(r'^[0-9a-fA-F]{32}$')
    for col in ('checksum_filename', 'checksum_filename2'):
        if col not in selected.columns:
            selected[col] = None
    for _, row in selected.iterrows():
        label = row['lib_id'] if not is_blank(row['lib_id']) else row['samp_name']
        for name_col, sum_col in (('filename', 'checksum_filename'), ('filename2', 'checksum_filename2')):
            if is_blank(row[name_col]):
                problems.append(f"{label}: {name_col} is empty (only paired-end runs are supported)")
            elif is_blank(row[sum_col]) or not md5.match(str(row[sum_col]).strip()):
                problems.append(f"{label}: {sum_col} is missing or is not an MD5 checksum")
    aliases = selected['lib_id'].where(~selected['lib_id'].apply(is_blank), selected['samp_name']).astype(str)
    dupes = sorted(set(aliases[aliases.duplicated()]) - bad)
    # Listed first, so the advice is not lost below a long list of file problems.
    if dupes and not args.assay_name:
        problems.insert(
            0,
            "these lib_id values appear more than once: " + ', '.join(dupes[:5])
            + (' ...' if len(dupes) > 5 else '')
            + ". FAIRe takes a library to be one amplicon of a sample, so give each row of experimentRunMetadata "
              "its own lib_id (the FAIRe mapper adds assay_name and seq_run_id to the library name), or run the "
              "tool once per assay (set 'Assay to include')"
            + ("." if args.seq_run_id else ", or once per sequencing run.")
        )
    elif dupes:
        problems.insert(
            0,
            "these lib_id values appear more than once within the assay: " + ', '.join(dupes[:5])
            + (' ...' if len(dupes) > 5 else '')
            + ". ENA needs one lib_id per run: a library sequenced in two runs needs two lib_ids "
            "(for example with the run added) in experimentRunMetadata."
        )
    if problems:
        shown = problems[:20] + ([f"... and {len(problems) - 20} more"] if len(problems) > 20 else [])
        fail("the run metadata needs fixing before ENA will accept it:\n  " + '\n  '.join(shown))

    if args.ftp_subdir:
        subdir = args.ftp_subdir.strip('/')
        for col in ('filename', 'filename2'):
            df[col] = df[col].apply(lambda v: v if is_blank(v) else f"{subdir}/{v}")
    for col in ('checksum_filename', 'checksum_filename2'):
        if col in df.columns:
            df[col] = df[col].apply(lambda v: v if is_blank(v) else str(v).strip().lower())

    suffix = args.assay_name if args.add_assay_suffix else None
    if suffix and selected['lib_id'].astype(str).str.endswith(suffix).all():
        print(f"INFO: every lib_id already ends with '{suffix}', so it is not added again")
        suffix = None
    upstream_run.process_run_metadata(
        df,
        args.receipt_file,
        args.study_accession,
        args.center_name,
        args.experiment_output,
        args.run_output,
        args.instrument_model,
        suffix,
    )
    if args.submission_file:
        with open(args.submission_file, 'w', encoding='utf-8') as f:
            f.write(SUBMISSION_XML)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='mode', required=True)

    s = sub.add_parser('sample', help='write ENA SAMPLE XML')
    s.add_argument('--input_file', required=True)
    s.add_argument('--center_name', required=True)
    s.add_argument('--output_file', required=True)
    s.add_argument('--taxon_id', type=int, default=408172)
    s.add_argument('--no_date_conversion', dest='convert_dates', action='store_false')
    s.add_argument('--submission_file')

    r = sub.add_parser('run', help='write ENA EXPERIMENT and RUN XML')
    r.add_argument('--input_file', required=True)
    r.add_argument('--receipt_file', required=True)
    r.add_argument('--study_accession', required=True)
    r.add_argument('--center_name', required=True)
    r.add_argument('--experiment_output', required=True)
    r.add_argument('--run_output', required=True)
    r.add_argument('--instrument_model', required=True)
    r.add_argument('--assay_name')
    r.add_argument('--seq_run_id', help='sequencing runs to include (seq_run_id values, comma-separated)')
    r.add_argument('--add_assay_suffix', action='store_true')
    r.add_argument('--ftp_subdir')
    r.add_argument('--submission_file')

    args = parser.parse_args()
    if args.mode == 'sample':
        run_sample(args)
    else:
        if args.add_assay_suffix and not args.assay_name:
            fail("an assay suffix needs an assay to be selected.")
        run_run(args)


if __name__ == '__main__':
    main()
