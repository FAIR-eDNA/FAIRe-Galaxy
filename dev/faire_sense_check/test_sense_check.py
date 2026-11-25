#!/usr/bin/env python3
"""Tests for the sense check: a small workbook with one of each problem, and one with none.

Usage: python test_sense_check.py      (prints ok or the failures; exits 1 on a failure)
"""
import datetime as dt
import sys
import tempfile
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import faire_sense_check as sc  # noqa: E402

SAMPLE_COLS = ['samp_name', 'samp_category', 'neg_cont_type', 'decimalLatitude', 'decimalLongitude', 'eventDate',
               'env_broad_scale', 'env_medium', 'minimumDepthInMeters']


def workbook(path, samples, otu, taxa, amp=None, project=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'README'
    pm = wb.create_sheet('projectMetadata')
    pm.append(['requirement_level_code', 'section', 'term_name', 'project_level', 'assay1'])
    for term, value in (project or {'project_id': 'TEST', 'assay_type': 'metabarcoding', 'assay_name': 'A1',
                                    'targetTaxonomicAssay': 'fish'}).items():
        pm.append(['M', 'Project', term, value if term != 'targetTaxonomicAssay' else None,
                   value if term in ('assay_name', 'targetTaxonomicAssay', 'pcr_cycles') else None])
    sm = wb.create_sheet('sampleMetadata')
    cols = list(samples[0].keys())
    sm.append(['# requirement_level_code'] + ['M'] * (len(cols) - 1))
    sm.append(['# section'] + ['Sample'] * (len(cols) - 1))
    sm.append(cols)
    for s in samples:
        sm.append([s[c] for c in cols])
    if otu:
        tx = wb.create_sheet('taxaFinal_A1')
        tx.append(['# requirement_level_code', 'M', 'R', 'R', 'R', 'R'])
        tx.append(['# section'] * 6)
        tx.append(['seq_id', 'dna_sequence', 'phylum', 'class', 'genus', 'specificEpithet'])
        for row in taxa:
            tx.append(row)
        ot = wb.create_sheet('otuFinal_A1')
        names = list(otu[next(iter(otu))].keys())
        ot.append(['seq_id'] + names)
        for sid, reads in otu.items():
            ot.append([sid] + [reads[n] for n in names])
    if amp:
        am = wb.create_sheet('ampData')
        am.append(['# requirement_level_code', 'M', 'M', 'M'])
        am.append(['# section'] * 4)
        am.append(['samp_name', 'technical_rep_id', 'assay_name', 'quantificationCycle'])
        for row in amp:
            am.append(row)
    wb.save(path)


def sample(name, lat=-42.9, lon=147.9, date='2023-03-01', cat='sample', neg=None, env='sea water', depth=5):
    return dict(zip(SAMPLE_COLS, [name, cat, neg, lat, lon, date, 'marine biome', env, depth]))


def flags_of(path):
    out = Path(path).with_suffix('.html')
    return sc.build(path, out).items, out


def main():
    fails = []

    def expect(items, level, area, words, label):
        if not any(lv == level and ar == area and all(w in msg for w in words) for lv, ar, msg in items):
            fails.append(f'{label}: no {level} flag in {area} with {words}; got {items}')

    with tempfile.TemporaryDirectory() as tmp:
        # one of each problem
        future = (dt.date.today() + dt.timedelta(days=30)).isoformat()
        samples = [sample('S1'), sample('S2'), sample('S3', lat=0, lon=0), sample('S4', lat=147.9, lon=-42.9),
                   sample('S5', date=future), sample('S6', lat=-35.3, lon=149.1),  # marine, in Canberra
                   sample('S7', depth=-3),
                   sample('B1', cat='negative control', neg='extraction negative', lat=None, lon=None, date=None)]
        otu = {'ASV1': {'S1': 500, 'S2': 400, 'S5': 300, 'S6': 200, 'S7': 100, 'B1': 50, 'X9': 10},
               'ASV2': {'S1': 0, 'S2': 0, 'S5': 0, 'S6': 0, 'S7': 0, 'B1': 30, 'X9': 0},
               'ASV3': {'S1': 100, 'S2': 0, 'S5': 0, 'S6': 0, 'S7': 0, 'B1': 0, 'X9': 0}}
        taxa = [['ASV1', 'ACGT', 'Chordata', 'Actinopteri', 'Sardinops', 'sagax'],
                ['ASV2', 'ACGT', 'Chordata', 'Actinopteri', 'Trachurus', 'novaezelandiae'],
                ['ASV3', 'ACGT', 'Chordata', 'Mammalia', 'Homo', 'sapiens']]
        p = Path(tmp, 'bad.xlsx')
        workbook(p, samples, otu, taxa)
        items, html = flags_of(p)
        expect(items, 'problem', 'Where', ['S3', '0, 0'], 'coordinates 0, 0')
        expect(items, 'problem', 'Where', ['S4', 'swapped'], 'swapped coordinates')
        expect(items, 'problem', 'Where', ['S6', 'on land'], 'marine sample inland')
        expect(items, 'problem', 'When', ['S5', 'future'], 'future date')
        expect(items, 'problem', 'Values', ['minimumDepthInMeters'], 'negative depth')
        expect(items, 'problem', 'Links', ['X9'], 'column with no sample')
        expect(items, 'check', 'Controls', ['B1', 'Trachurus'], 'control with reads')
        expect(items, 'check', 'Taxa', ['Homo sapiens'], 'human reads')
        page = html.read_text(encoding='utf-8')
        for words in ('Where the samples were taken', 'Reads per sample', 'What was detected', '<svg'):
            if words not in page:
                fails.append(f'page lacks {words!r}')

        # qPCR: a Cq above the cycles run, and a negative control that amplified
        samples = [sample('Q1'), sample('Q2'), sample('N1', cat='negative control', neg='field negative')]
        for s in samples:
            s['detected_notDetected_T1'] = 1 if s['samp_name'] == 'Q1' else 0
        amp = [['Q1', 1, 'T1', 38.2], ['Q1', 2, 'T1', 41.5], ['Q2', 1, 'T1', 'not applicable'], ['N1', 1, 'T1', 36.0]]
        p = Path(tmp, 'qpcr.xlsx')
        workbook(p, samples, None, None, amp=amp,
                 project={'project_id': 'Q', 'assay_type': 'targeted', 'assay_name': 'T1', 'pcr_cycles': 40})
        items, _ = flags_of(p)
        expect(items, 'problem', 'qPCR', ['Q1', '40 cycles'], 'Cq above the cycles')
        expect(items, 'check', 'qPCR', ['N1'], 'negative control amplified')

        # nothing wrong
        samples = [sample('S1'), sample('S2'), sample('S3', lat=-42.95),
                   sample('B1', cat='negative control', neg='extraction negative', lat=None, lon=None, date=None)]
        otu = {'ASV1': {'S1': 500, 'S2': 400, 'S3': 450, 'B1': 0}}
        p = Path(tmp, 'good.xlsx')
        workbook(p, samples, otu, [['ASV1', 'ACGT', 'Chordata', 'Actinopteri', 'Sardinops', 'sagax']])
        items, _ = flags_of(p)
        serious = [i for i in items if i[0] in ('problem', 'check')]
        if serious:
            fails.append(f'clean workbook flagged: {serious}')

    if fails:
        print('\n'.join(fails))
        return 1
    print('ok: all sense check tests pass')
    return 0


if __name__ == '__main__':
    sys.exit(main())
