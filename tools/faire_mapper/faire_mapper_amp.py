"""qPCR and ddPCR results for apply mapping (targeted assays).

A results table has one row per reaction: the sample, the assay, and the Cq (or the copies, for
ddPCR), and may have the technical replicate and the plate. Its rows are written to ampData, and
each sample's detection for each assay (detected_notDetected) is worked out from them where the
sample table gives none: detected (1) when at least one reaction amplified, not detected (0) when
none did. Columns are found by their names (Cq, Ct, quantificationCycle; Sample ID, samp_name ...).
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd

import faire_mapper as fm
import faire_mapper_otu as fo

# Column names (compared lower case, with spaces, dots, dashes and underscores removed)
COLUMNS = {
    'samp_name': ('sampname', 'sample', 'sampleid', 'samplename', 'samplecode', 'sampleno'),
    'assay_name': ('assayname', 'assay', 'target', 'targetname', 'detector'),
    'quantificationCycle': ('quantificationcycle', 'cq', 'ct', 'cqvalue', 'ctvalue', 'cp', 'crt'),
    'technical_rep_id': ('technicalrepid', 'technicalreplicate', 'replicate', 'rep', 'pcrreplicate', 'pcrrep',
                         'techrep'),
    'pcr_plate_id': ('pcrplateid', 'plate', 'plateid', 'platename', 'runname', 'plateno'),
    'rfu': ('rfu',),
    'estimatedNumberOfCopies': ('estimatednumberofcopies', 'copies', 'copynumber', 'quantity', 'conc',
                                'concentration', 'copiesul', 'copiesperul'),
    'estimatedNumberOfCopies_unit': ('estimatednumberofcopiesunit', 'copiesunit', 'quantityunit', 'concunit',
                                     'unit', 'units'),
}
NO_AMPLIFICATION = {'undetermined', 'noct', 'nocq', 'na', 'n/a', 'nan', 'none', '-', 'neg', 'negative', 'nd', ''}
NOT_APPLICABLE = 'not applicable'


def _key(name):
    return re.sub(r'[\s._\-/()]+', '', str(name)).lower()


def find_columns(columns, assay_column=''):
    """FAIRe term -> column of the results table. The first column with a known name wins; a named
    assay column replaces the one found by name."""
    found = {}
    for c in columns:
        k = _key(c)
        for term, names in COLUMNS.items():
            if term not in found and k in names:
                found[term] = c
                break
    if assay_column:
        if assay_column not in columns:
            raise ValueError(f"the results table has no column called '{assay_column}'")
        found['assay_name'] = assay_column
    return found


def _number(v):
    if fo._blank(v):
        return None
    try:
        x = float(str(v).strip().replace(',', ''))
    except ValueError:
        return None
    return None if math.isnan(x) else x


def amplified(row):
    """True when a reaction amplified: a Cq above 0, or (ddPCR, no Cq column) copies above 0."""
    cq = row.get('quantificationCycle')
    if cq is not None:
        x = _number(cq)
        return x is not None and x > 0
    copies = _number(row.get('estimatedNumberOfCopies'))
    return copies is not None and copies > 0


def read_results(paths, sheets, names, assay_columns, assays, sample_names, say):
    """Rows for ampData (FAIRe terms) from the results tables, and {(samp_name, assay): 0 or 1}.
    say(section, line) writes to the log."""
    rows, notes = [], {'zero': 0, 'text': {}, 'unknown_samples': set(), 'numbered': 0}
    known = {fo.norm_id(s): s for s in sample_names if not fo._blank(s)}
    norm_assays = {_key(a): a for a in assays}
    for i, path in enumerate(paths):
        sheet = (sheets[i] if sheets and i < len(sheets) else '') or None
        label = (names[i] if names and i < len(names) and names[i] else '') or Path(path).name
        df = fm.read_table(path, sheet)
        cols = find_columns(list(df.columns), (assay_columns[i] if assay_columns and i < len(assay_columns) else '')
                            or '')
        if 'samp_name' not in cols:
            raise ValueError(f'{label}: no column of sample names (samp_name, Sample, Sample ID ...)')
        if 'quantificationCycle' not in cols and 'estimatedNumberOfCopies' not in cols:
            raise ValueError(f'{label}: no column of Cq values (Cq, Ct, quantificationCycle) or copies')
        if 'assay_name' not in cols and len(assays) != 1:
            raise ValueError(f'{label}: no assay column (assay_name, Assay, Target), and there are '
                             f'{len(assays)} assays; name the column that gives the assay')
        unknown = sorted({str(v).strip() for v in df[cols['assay_name']].dropna()
                          if _key(v) not in norm_assays}) if 'assay_name' in cols else []
        if unknown:
            raise ValueError(f"{label}: assay values not among the assay names ({', '.join(assays)}): "
                             f"{', '.join(unknown[:6])}. Give the assay names as they are in this table, or add a "
                             f"column of assay names to it")
        say('Inputs', f"qPCR results: {label}, {len(df)} reactions; columns "
                      + ', '.join(f"'{c}' as {t}" for t, c in cols.items()))
        counter = {}
        for _, r in df.iterrows():
            samp = fo.norm_id(r[cols['samp_name']])
            if not samp:
                continue
            assay = norm_assays[_key(r[cols['assay_name']])] if 'assay_name' in cols else assays[0]
            row = {'samp_name': known.get(samp, samp), 'assay_name': assay}
            if samp not in known:
                notes['unknown_samples'].add(samp)
            for term in ('pcr_plate_id', 'rfu', 'estimatedNumberOfCopies', 'estimatedNumberOfCopies_unit'):
                if term in cols and not fo._blank(r[cols[term]]):
                    v = r[cols[term]]
                    row[term] = _number(v) if term in ('rfu', 'estimatedNumberOfCopies') and _number(v) is not None \
                        else str(v).strip()
            if 'quantificationCycle' in cols:
                raw = '' if fo._blank(r[cols['quantificationCycle']]) else str(r[cols['quantificationCycle']]).strip()
                x = _number(raw)
                if x is not None and x > 0:
                    row['quantificationCycle'] = x
                else:
                    if x == 0:
                        notes['zero'] += 1
                    elif raw.lower().replace(' ', '') not in NO_AMPLIFICATION:
                        notes['text'][raw] = notes['text'].get(raw, 0) + 1
                    row['quantificationCycle'] = NOT_APPLICABLE
                row['_amplified'] = x is not None and x > 0
            else:
                row['_amplified'] = amplified(row)
            plate = row.get('pcr_plate_id', '')
            k = (row['samp_name'], assay, plate)
            counter[k] = counter.get(k, 0) + 1
            if 'technical_rep_id' in cols and not fo._blank(r[cols['technical_rep_id']]):
                row['technical_rep_id'] = fo.norm_id(r[cols['technical_rep_id']])
            else:
                row['technical_rep_id'] = counter[k]
                notes['numbered'] += 1
            rows.append(row)
    detected = {}
    for row in rows:
        key = (fo.norm_id(row['samp_name']), row['assay_name'])
        detected[key] = max(detected.get(key, 0), 1 if row.pop('_amplified') else 0)
    if notes['numbered']:
        say('Columns written', f"ampData: technical_rep_id numbered 1, 2, 3 ... in table order for each sample, "
                               f"assay and plate ({notes['numbered']} reactions), as the results table has no "
                               f"replicate column")
    if any(r['quantificationCycle'] == NOT_APPLICABLE for r in rows if 'quantificationCycle' in r):
        k = sum(1 for r in rows if r.get('quantificationCycle') == NOT_APPLICABLE)
        say('Columns written', f"ampData: '{NOT_APPLICABLE}' written as quantificationCycle for the {k} reactions "
                               f"that did not amplify (Undetermined, or empty)")
    if notes['zero']:
        say('Warnings', f"{notes['zero']} reactions have a Cq of 0, read as no amplification; check them")
    for text, n in notes['text'].items():
        say('Warnings', f"Cq '{text}' ({n} reactions) is not a number; read as no amplification")
    if notes['unknown_samples']:
        s = sorted(notes['unknown_samples'])
        say('Warnings', f"{len(s)} samples in the qPCR results are not in the sample table, e.g. "
                        f"{', '.join(s[:4])}; their reactions are written to ampData, but FAIRe needs each "
                        f"sample in sampleMetadata")
    if not any('pcr_plate_id' in r for r in rows):
        say('Mandatory terms with no value', 'pcr_plate_id (ampData; mandatory if assay_type = targeted): the '
                                             'qPCR results have no plate column')
    return rows, detected


def check_cycles(rows, cycles, say):
    """Warn about Cq values above the assay's number of PCR cycles (pcr_cycles), which no run can give."""
    for assay, n in cycles.items():
        n = _number(n)
        if not n:
            continue
        over = [r['quantificationCycle'] for r in rows
                if r['assay_name'] == assay and isinstance(r.get('quantificationCycle'), float)
                and r['quantificationCycle'] > n]
        if over:
            say('Warnings', f"{assay}: {len(over)} reactions have a Cq above pcr_cycles ({n:g}), up to {max(over):g}; "
                            f"check the Cq values and the cycling conditions")


def fill_detections(sample_out, assays, detected, say):
    """detected_notDetected from the results, in the cells the sample table left empty. A sample with no
    reactions for an assay that has results for other samples was not tested with it: 'not applicable'."""
    counts, untested = {}, {}
    tested = {a for _, a in detected}
    for a in assays:
        col = 'detected_notDetected' if len(assays) == 1 else f'detected_notDetected_{a}'
        if col not in sample_out:
            continue
        for i, samp in enumerate(sample_out['samp_name']):
            if fo._blank(samp) or not fo._blank(sample_out[col][i]):
                continue
            key = (fo.norm_id(samp), a)
            if key in detected:
                sample_out[col][i] = detected[key]
                counts[a] = counts.get(a, 0) + 1
            elif a in tested:
                sample_out[col][i] = NOT_APPLICABLE
                untested[a] = untested.get(a, 0) + 1
    for a, n in counts.items():
        say('Columns written', f"detected_notDetected for {a}: {n} samples, from the qPCR results (1 when at least "
                               f"one reaction amplified, 0 when none did). Check this against the study's detection "
                               f"criteria (detection_criteria in projectMetadata)")
    for a, n in untested.items():
        say('Columns written', f"detected_notDetected for {a}: '{NOT_APPLICABLE}' for {n} samples with no reactions "
                               f"for this assay in the qPCR results (not tested with it)")
    return counts


def as_frame(rows, columns):
    return pd.DataFrame([{c: r.get(c) for c in columns} for r in rows], columns=columns)
