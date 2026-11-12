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
    library name, assay_name and seq_run_id, so those two are taken off);
  * the units and plain numbers ENA's checklist asks for (see FIXED_UNITS below), and the
    checklist's size-fraction fields the right way round (SIZE_FRACTIONS);
  * single-end runs, when lib_layout is 'single end' (upstream writes only paired-end runs).
"""

import argparse
import contextlib
import datetime
import decimal
import io
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


# ENA's water checklist (ERC000024, read on 11 November 2026) wants these attributes as plain numbers
# with a unit, and refused samples without them in a test-server submission that day. FAIRe gives
# temp and samp_store_temp in degrees Celsius and salinity in psu (FAIRe checklist v1.0.2), so
# their units are fixed: {ENA attribute: (FAIRe term, ENA unit, sign allowed)}. The checklist writes
# temperature's unit with U+00BA and sample storage temperature's with U+00B0; both are kept.
FIXED_UNITS = {
    'temperature': ('temp', 'ºC', True),
    'salinity': ('salinity', 'psu', False),
    'sample storage temperature': ('samp_store_temp', '°C', True),
    # added 12 November 2026, from the FAIRe checklist's units and ERC000024's
    'chlorophyll': ('chlorophyll', 'mg/m3', False),
    'light intensity': ('light_intensity', 'lux', False),
    'suspended particulate matter': ('suspend_part_matter', 'mg/L', False),
    'turbidity': ('turbidity', 'NTU', False),
    'total depth of water column': ('tot_depth_water_col', 'm', False),
    'elevation': ('elev', 'm', True),
    'ph': ('ph', None, False),  # a number, with no unit
}
# FAIRe gives water_current in m/s; ERC000024 takes only m3/s or knot.
NO_ENA_UNIT = {'water current': ('water_current', "water_current is in m/s, and ENA takes only m3/s or knot")}
# Concentrations have a FAIRe unit term ({term}_unit). {ENA attribute: (FAIRe term, ENA units)}, with
# ERC000024's units. A FAIRe unit is converted when only a power of ten separates it from an ENA unit
# (UNIT_SCALES); mass, moles, litres and kilograms are not converted into one another.
CONCENTRATIONS = {
    'dissolved oxygen': ('diss_oxygen', ['µmol/kg']),
    'nitrate': ('nitrate', ['µmol/L']),
    'nitrite': ('nitrite', ['µmol/L']),
    'dissolved inorganic carbon': ('diss_inorg_carb', ['µg/L']),
    'dissolved inorganic nitrogen': ('diss_inorg_nitro', ['µg/L']),
    'dissolved organic carbon': ('diss_org_carb', ['µmol/L']),
    'dissolved organic nitrogen': ('diss_org_nitro', ['µg/L', 'mg/L']),
    'total dissolved nitrogen': ('tot_diss_nitro', ['µg/L']),
    'total inorganic nitrogen': ('tot_inorg_nitro', ['µg/L']),
    'total nitrogen concentration': ('tot_nitro', ['µmol/L']),
    'total particulate carbon': ('tot_part_carb', ['µmol/L', 'µg/L']),
    'particulate organic carbon': ('part_org_carb', ['µg/L']),
    'particulate organic nitrogen': ('part_org_nitro', ['µg/L']),
    'organic carbon': ('org_carb', ['µmol/L']),
    'organic matter': ('org_matter', ['µg/L']),
    'organic nitrogen': ('org_nitro', ['µg/L']),
}
# {unit, as unit_key gives it: (kind, size in µmol/L, µg/L or µmol/kg)}
UNIT_SCALES = {
    'µm': ('mol/L', '1'), 'µmol/l': ('mol/L', '1'), 'mmol/m3': ('mol/L', '1'), 'µmol/m3': ('mol/L', '0.001'),
    'mol/m3': ('mol/L', '1000'), 'mmol/l': ('mol/L', '1000'), 'mol/l': ('mol/L', '1000000'),
    'µg/l': ('g/L', '1'), 'mg/m3': ('g/L', '1'), 'mg/l': ('g/L', '1000'),
    'µmol/kg': ('mol/kg', '1'), 'mmol/kg': ('mol/kg', '1000'),
}
# Upstream also writes these, as "<value> <unit>" or "Unknown", beside the checklist's attributes.
UPSTREAM_EXTRA = ('dissolved_inorganic_carbon', 'dissolved_inorganic_nitrogen', 'dissolved_organic_carbon',
                  'dissolved_organic_nitrogen', 'dissolved_oxygen')
# Sample size and extraction volume have a FAIRe unit term. {ENA attribute: (FAIRe value term,
# FAIRe unit term, {FAIRe unit, lower case: (ENA unit, factor)})}, from the units FAIRe allows
# (mL, L, mg, g, kg, cm2, m2, cm3, m3) to the ones ENA allows.
VARIABLE_UNITS = {
    'amount or size of sample collected': ('samp_size', 'samp_size_unit', {
        'ml': ('L', '0.001'), 'l': ('L', '1'), 'cm3': ('L', '0.001'), 'm3': ('m3', '1'),
        'mg': ('g', '0.001'), 'g': ('g', '1'), 'kg': ('kg', '1'), 'cm2': ('m2', '0.0001'), 'm2': ('m2', '1')}),
    'sample volume or weight for DNA extraction': ('samp_vol_we_dna_ext', 'samp_vol_we_dna_ext_unit', {
        'ml': ('mL', '1'), 'l': ('mL', '1000'), 'cm3': ('mL', '1'), 'm3': ('mL', '1000000'),
        'mg': ('mg', '1'), 'g': ('g', '1'), 'kg': ('g', '1000')}),
}
# Upstream also writes the extraction volume under this misspelt name, as "<value> <unit>" or "Unknown".
MISSPELT = 'sample volume for weight for DNA extraction'
# ERC000024 (read on 12 November 2026) defines its size-fraction lower threshold as "the mesh/pore size
# used to retain the sample. Materials smaller than the size threshold are excluded from the sample",
# and its upper threshold as "the mesh/pore size used to pre-filter/pre-sort the sample. Materials
# larger than the size threshold are excluded". FAIRe's size_frac is the "filtering pore size used in
# sample filtration" and size_frac_low the pre-filter, both in µm (FAIRe checklist v1.0.2). So
# {ENA attribute: FAIRe term}. Upstream writes them the other way round, under labels without the
# hyphen (UPSTREAM_SIZE), which ENA keeps as extra attributes with no unit.
SIZE_FRACTIONS = {
    'size-fraction lower threshold': 'size_frac',
    'size-fraction upper threshold': 'size_frac_low',
}
UPSTREAM_SIZE = ('sizefraction lower threshold', 'sizefraction upper threshold')


def is_missing_term(value):
    """FAIRe's missing-value terms (not applicable, missing: not collected, ...)."""
    return str(value).strip().lower().startswith(('not applicable', 'missing', 'not collected', 'not provided',
                                                  'restricted access'))


def unit_key(unit):
    """A unit written as UNIT_SCALES has it: lower case, no spaces, and µ for u, μ or the micro sign."""
    text = str(unit).strip().lower().replace(' ', '').replace('μ', 'µ')
    return 'µ' + text[1:] if text.startswith('u') else text


def concentration_factor(unit, ena_units):
    """(ENA unit, factor) to convert a value in this FAIRe unit, or None."""
    faire = UNIT_SCALES.get(unit_key(unit))
    for ena_unit in ena_units:
        ena = UNIT_SCALES[unit_key(ena_unit)]
        if faire and faire[0] == ena[0]:
            return ena_unit, str(decimal.Decimal(faire[1]) / decimal.Decimal(ena[1]))
    return None


def ena_number(value, factor='1', signed=False):
    """The value as a plain number ENA accepts (times factor), or None if it is not one."""
    if is_blank(value) or isinstance(value, bool):
        return None
    try:
        number = decimal.Decimal(str(value).strip()) * decimal.Decimal(factor)
    except decimal.InvalidOperation:
        return None
    if not number.is_finite() or (number < 0 and not signed):
        return None
    text = format(number.normalize(), 'f')
    return '0' if text in ('-0', '0') else text


def fix_ena_values(ena_data, faire_data, notes):
    """Make the attributes in FIXED_UNITS, VARIABLE_UNITS and CONCENTRATIONS plain numbers ENA
    accepts, and return {attribute: unit} for them. Values that cannot be made so are left out (all
    are optional in ERC000024) and noted as {(attribute, reason): {sample, ...}}."""
    name = str(faire_data.get('samp_name'))
    units = {}
    for extra in (MISSPELT,) + UPSTREAM_EXTRA + UPSTREAM_SIZE:
        ena_data.pop(extra, None)

    def leave_out(attribute, reason):
        ena_data.pop(attribute, None)
        notes.setdefault((attribute, reason), set()).add(name)

    for attribute, (term, unit, signed) in FIXED_UNITS.items():
        if attribute not in ena_data:
            continue
        number = ena_number(ena_data[attribute], signed=signed)
        if number is not None:
            ena_data[attribute] = number
            if unit:
                units[attribute] = unit
        elif is_missing_term(ena_data[attribute]):
            ena_data.pop(attribute)
        else:
            leave_out(attribute, f'{term} is not a number')
    for attribute, (term, unit_term, conversions) in VARIABLE_UNITS.items():
        value, unit = faire_data.get(term), faire_data.get(unit_term)
        if is_blank(value) or is_missing_term(value):
            ena_data.pop(attribute, None)
            continue
        if ena_number(value) is None:
            leave_out(attribute, f'{term} is not a number')
        elif is_blank(unit):
            leave_out(attribute, f'{unit_term} is empty')
        elif str(unit).strip().lower() not in conversions:
            leave_out(attribute, f"{unit_term} '{unit}' has no ENA equivalent")
        else:
            ena_unit, factor = conversions[str(unit).strip().lower()]
            ena_data[attribute], units[attribute] = ena_number(value, factor), ena_unit
    for attribute, (term, ena_units) in CONCENTRATIONS.items():
        value, unit_term = faire_data.get(term), f'{term}_unit'
        unit = faire_data.get(unit_term)
        if is_blank(value) or is_missing_term(value):
            ena_data.pop(attribute, None)
            continue
        conversion = None if is_blank(unit) else concentration_factor(unit, ena_units)
        if ena_number(value) is None:
            leave_out(attribute, f'{term} is not a number')
        elif is_blank(unit):
            leave_out(attribute, f'{unit_term} is empty')
        elif conversion is None:
            leave_out(attribute, f"{unit_term} '{unit}' cannot be converted to ENA's {' or '.join(ena_units)}")
        else:
            ena_data[attribute], units[attribute] = ena_number(value, conversion[1]), conversion[0]
    for attribute, term in SIZE_FRACTIONS.items():
        value = faire_data.get(term)
        if is_blank(value) or is_missing_term(value):
            continue
        number = ena_number(value)
        if number is None:
            leave_out(attribute, f'{term} is not a number')
        else:
            ena_data[attribute], units[attribute] = number, 'µm'
    for attribute, (term, reason) in NO_ENA_UNIT.items():
        if attribute in ena_data:
            if is_missing_term(ena_data[attribute]):
                ena_data.pop(attribute)
            else:
                leave_out(attribute, reason)
    return units


def add_units(sample_xml, units):
    """Give each attribute in units its UNITS line, in place of any upstream wrote."""
    out, tag = [], None
    for line in sample_xml.split('\n'):
        text = line.strip()
        if text.startswith('<TAG>'):
            tag = text[len('<TAG>'):-len('</TAG>')]
        elif text.startswith('<UNITS>') and tag in units:
            continue
        out.append(line)
        if text.startswith('<VALUE>') and tag in units:
            out.append(f'        <UNITS>{units[tag]}</UNITS>')
    return '\n'.join(out)


def use_ena_units():
    """While upstream converts samples, fix their values and units (fix_ena_values, add_units).
    Returns the notes and a count of the calls, so the caller can check the fix was used."""
    notes, units, calls = {}, {}, {'convert': 0, 'xml': 0}
    convert, generate = upstream_sample.convert_faire_to_ena, upstream_sample.generate_ena_xml

    def convert_faire_to_ena(faire_data, project_name):
        calls['convert'] += 1
        ena_data = convert(faire_data, project_name)
        units[str(faire_data.get('samp_name'))] = fix_ena_values(ena_data, faire_data, notes)
        return ena_data

    def generate_ena_xml(ena_data, sample_alias, *args, **kwargs):
        calls['xml'] += 1
        return add_units(generate(ena_data, sample_alias, *args, **kwargs), units.get(str(sample_alias), {}))

    upstream_sample.convert_faire_to_ena = convert_faire_to_ena
    upstream_sample.generate_ena_xml = generate_ena_xml
    return notes, calls


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

    notes, calls = use_ena_units()

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

    # Upstream's own summary counts XML lines and calls them samples ("Generated ENA XML with 282
    # samples" for 3), so it is left out; its warnings are passed on, and the count is given below.
    upstream_log = io.StringIO()
    try:
        with contextlib.redirect_stdout(upstream_log):
            upstream_sample.process_faire_df(
                df, args.output_file, project_name, taxon_id=str(args.taxon_id), center_name=args.center_name
            )
    finally:
        for line in upstream_log.getvalue().splitlines():
            if not line.startswith('Generated ENA XML with '):
                print(line)
    if not calls['xml']:
        fail("FAIRe2ENA no longer writes samples through generate_ena_xml, so the wrapper could not add "
             "ENA's units. The wrapper needs updating for this FAIRe2ENA version.")
    for (attribute, reason), samples in sorted(notes.items()):
        shown = ', '.join(sorted(samples)[:5]) + (' ...' if len(samples) > 5 else '')
        print(f"INFO: '{attribute}' left out for {len(samples)} sample(s), as ENA needs a number with "
              f"a unit and {reason}: {shown}")
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


PROJECT_COLUMNS = ('requirement_level_code', 'section', 'term_name', 'project_level')


def text(value):
    return '' if is_blank(value) else str(value).strip()


def library_layouts(path):
    """lib_layout from projectMetadata: ({assay_name: layout} for assays with their own value, the
    project_level value). FAIRe's values are 'paired end', 'single end' and 'other: ...'."""
    pm = read_sheet(path, 'projectMetadata')
    if 'term_name' not in pm.columns:
        return {}, ''
    terms = pm['term_name'].astype(str).str.strip()
    layout_rows, assay_rows = pm[terms == 'lib_layout'], pm[terms == 'assay_name']
    if layout_rows.empty:
        return {}, ''
    layout = layout_rows.iloc[0]
    project = text(layout['project_level']) if 'project_level' in pm.columns else ''
    per_assay = {}
    if not assay_rows.empty:
        for column in pm.columns:
            if column not in PROJECT_COLUMNS and text(assay_rows.iloc[0][column]) and text(layout[column]):
                per_assay[text(assay_rows.iloc[0][column])] = text(layout[column])
    return per_assay, project


def layout_kind(value):
    """'paired', 'single' or 'other' for a lib_layout value; an empty one is paired, as upstream
    writes every run as paired-end."""
    value = value.lower()
    if not value or value.startswith('paired'):
        return 'paired'
    return 'single' if value.startswith('single') else 'other'


def write_single_end(counts):
    """While upstream writes experiments, give the single-end ones (run_data['_layout'] 'single') a
    SINGLE layout in place of the PAIRED one upstream always writes. Counts them in counts['single']."""
    generate = upstream_run.generate_experiment_xml

    def generate_experiment_xml(run_data, *args, **kwargs):
        xml = generate(run_data, *args, **kwargs)
        if run_data.get('_layout') == 'single':
            if xml.count('<PAIRED/>') != 1:
                fail("FAIRe2ENA no longer writes the library layout as <PAIRED/>, so the wrapper could not "
                     "write single-end runs. The wrapper needs updating for this FAIRe2ENA version.")
            counts['single'] += 1
            xml = xml.replace('<PAIRED/>', '<SINGLE/>')
        return xml

    upstream_run.generate_experiment_xml = generate_experiment_xml


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
    per_assay, project_layout = library_layouts(args.input_file)
    df['_lib_layout'] = df['assay_name'].apply(lambda a: per_assay.get(text(a), project_layout))
    df['_layout'] = df['_lib_layout'].apply(layout_kind)
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
        if row['_layout'] == 'other':
            problems.append(f"{label}: lib_layout is '{row['_lib_layout']}', and ENA's runs need 'paired end' or "
                            "'single end'")
            continue
        files = [('filename', 'checksum_filename')]
        if row['_layout'] == 'paired':
            files.append(('filename2', 'checksum_filename2'))
        elif not is_blank(row['filename2']):
            problems.append(f"{label}: filename2 is given, but lib_layout is 'single end'. Set lib_layout to "
                            "'paired end' in projectMetadata, or leave filename2 empty")
        for name_col, sum_col in files:
            if is_blank(row[name_col]):
                problems.append(f"{label}: {name_col} is empty" + (
                    " (for single-end reads, set lib_layout to 'single end' in projectMetadata)"
                    if name_col == 'filename2' else ''))
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
    # Upstream writes a second FILE whenever filename2 is truthy, which an empty cell (NaN) is.
    for col in ('filename2', 'checksum_filename2'):
        if col in df.columns:
            df[col] = df[col].apply(lambda v: '' if is_blank(v) else v)
    counts = {'single': 0}
    write_single_end(counts)

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
    if counts['single']:
        print(f"INFO: {counts['single']} single-end run(s) (lib_layout 'single end'): one file each")
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
