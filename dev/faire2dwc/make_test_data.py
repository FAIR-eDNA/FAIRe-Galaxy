"""Make the small FAIRe workbooks in tools/faire2dwc/test-data.

The values are made up for the tests (the species are real; the samples, places and results are
not). The layouts are those of FAIRe-ator and apply mapping: projectMetadata with assay1, assay2
columns named by the assay_name row; sampleMetadata, ampData, otuFinal and taxaFinal with rows of
requirement levels and sections above the field names where FAIRe has them.

Usage: python dev/faire2dwc/make_test_data.py
"""

from pathlib import Path

from openpyxl import Workbook

OUT = Path(__file__).resolve().parents[2] / 'tools' / 'faire2dwc' / 'test-data'


def sheet(wb, name, header, rows, levels=True):
    ws = wb.create_sheet(name)
    if levels:
        ws.append(['# requirement_level_code'] + ['M'] * (len(header) - 1))
        ws.append(['# section'] + [''] * (len(header) - 1))
    ws.append(header)
    for r in rows:
        ws.append(r)


def project(wb, project_rows, assays=None):
    ws = wb.create_sheet('projectMetadata')
    header = ['requirement_level_code', 'section', 'term_name', 'project_level']
    if assays:
        header += [f'assay{i}' for i in range(1, len(assays) + 1)]
    ws.append(header)
    for term, value, *per_assay in project_rows:
        ws.append(['M', '', term, value] + (list(per_assay) if assays else []))


def targeted():
    wb = Workbook()
    wb.remove(wb.active)
    assays = ['CmaeCOI', 'CmaeND2']
    project(wb, [
        ('project_id', 'crab_qpcr_test', '', ''),
        ('project_name', 'Green crab qPCR test data', '', ''),
        ('recordedBy', 'A. Sampler | B. Sampler', '', ''),
        ('assay_type', 'targeted', '', ''),
        ('assay_name', '', 'CmaeCOI', 'CmaeND2'),
        ('license', 'https://creativecommons.org/licenses/by/4.0/legalcode', '', ''),
        ('neg_cont_0_1', 1, '', ''),
        ('targetTaxonomicAssay', '', 'Carcinus maenas', 'Carcinus maenas'),
        ('target_gene', '', 'COI', 'ND2'),
        ('pcr_primer_forward', '', 'ACGTACGTACGTACGTAC', 'TTGACCAATGCAAGTCGA'),
        ('pcr_primer_reverse', '', 'GGCCTTAAGGCCTTAAGG', 'CAGTCAGTCAGTCAGTCA'),
        ('pcr_primer_reference_forward', '', 'Made-up et al. (2020)', 'Other et al. (2021)'),
        ('pcr_primer_reference_reverse', '', 'Made-up et al. (2020)', 'Other et al. (2021)'),
        ('probeReporter', '', 'FAM', 'FAM'),
        ('probeQuencher', '', 'BHQ-1', 'BHQ-1'),
        ('ampliconSize', '', 121, 95),
        ('annealingTemp', '', 60, 58),
        ('amp_vis_method', 'qPCR', '', ''),
        ('detection_criteria', 'At least one of three technical replicates amplified', '', ''),
        ('pcr_assay_lod', '', 2, 5),
        ('pcr_assay_lod_unit', '', 'copies/µL', 'copies/µL'),
        ('thresholdQuantificationCycle', '', 0.2, 0.25),
    ], assays)
    sheet(wb, 'sampleMetadata',
          ['samp_name', 'samp_category', 'neg_cont_type', 'decimalLatitude', 'decimalLongitude', 'geo_loc_name',
           'eventDate', 'env_broad_scale', 'env_local_scale', 'env_medium', 'samp_collect_device', 'samp_size',
           'samp_size_unit', 'detected_notDetected_CmaeCOI', 'detected_notDetected_CmaeND2'],
          [['W1', 'sample', '', -42.8901, 147.3300, 'Australia: Tasmania, Derwent Estuary', '2024-03-05',
            'marine biome [ENVO:00000447]', 'estuary [ENVO:00000045]', 'sea water [ENVO:00002149]',
            'Niskin bottle', 2, 'L', 1, 1],
           ['W2', 'sample', '', -42.9105, 147.3512, 'Australia: Tasmania, Derwent Estuary', '2024-03-05',
            'marine biome [ENVO:00000447]', 'estuary [ENVO:00000045]', 'sea water [ENVO:00002149]',
            'Niskin bottle', 2, 'L', 0, 1],
           ['W3', 'sample', '', -42.9302, 147.3801, 'Australia: Tasmania, Derwent Estuary', '2024-03-06',
            'marine biome [ENVO:00000447]', 'estuary [ENVO:00000045]', 'sea water [ENVO:00002149]',
            'Niskin bottle', 2, 'L', 0, 0],
           ['W4', 'sample', '', -42.9500, 147.4000, 'Australia: Tasmania, Derwent Estuary', '2024-03-06',
            'marine biome [ENVO:00000447]', 'estuary [ENVO:00000045]', 'sea water [ENVO:00002149]',
            'Niskin bottle', 2, 'L', 'missing: not provided', ''],
           ['FB1', 'negative control', 'field negative', '', '', 'not applicable: control sample',
            'not applicable: control sample', '', '', '', '', '', '', 0, 0]])
    rows = []
    cq = {('W1', 'CmaeCOI'): [33.1, 34.0, 'Undetermined'], ('W1', 'CmaeND2'): [31.2, 31.9, 32.4],
          ('W2', 'CmaeCOI'): ['Undetermined'] * 3, ('W2', 'CmaeND2'): [36.5, 'Undetermined', 'Undetermined'],
          ('W3', 'CmaeCOI'): ['Undetermined'] * 3, ('W3', 'CmaeND2'): ['Undetermined'] * 3,
          ('W4', 'CmaeCOI'): [35.0, 'Undetermined', 'Undetermined'], ('W4', 'CmaeND2'): ['Undetermined'] * 3,
          ('FB1', 'CmaeCOI'): ['Undetermined'] * 3, ('FB1', 'CmaeND2'): ['Undetermined'] * 3}
    for (samp, assay), values in cq.items():
        for i, v in enumerate(values, 1):
            copies = round(10 ** ((40 - v) / 3.3), 2) if isinstance(v, float) else 0
            rows.append([samp, i, assay, 'plate1', v, copies, 'copies/µL'])
    sheet(wb, 'ampData', ['samp_name', 'technical_rep_id', 'assay_name', 'pcr_plate_id', 'quantificationCycle',
                          'estimatedNumberOfCopies', 'estimatedNumberOfCopies_unit'], rows)
    wb.save(OUT / 'targeted_two_assays.xlsx')
    (OUT / 'taxa_carcinus.tsv').write_text(
        'name\tscientificName\tscientificNameID\ttaxonRank\tkingdom\tphylum\tclass\torder\tfamily\tgenus\n'
        'Carcinus maenas\tCarcinus maenas (Linnaeus, 1758)\turn:lsid:marinespecies.org:taxname:107381\tspecies\t'
        'Animalia\tArthropoda\tMalacostraca\tDecapoda\tCarcinidae\tCarcinus\n')


def metabarcoding(two_runs=False):
    """One MiFish table; or, with two_runs, the same assay sequenced in two runs (P1 in runA; P2 and the
    blank in runB), as otuFinal_MiFish_runA and otuFinal_MiFish_runB."""
    wb = Workbook()
    wb.remove(wb.active)
    project(wb, [
        ('project_id', 'pond_12S_test', ''),
        ('project_name', 'Pond vertebrates test data', ''),
        ('recordedBy', 'C. Sampler', ''),
        ('project_contact', 'Casey Sampler (casey.sampler@example.org)', ''),
        ('institution', 'Test Lab', ''),
        ('assay_type', 'metabarcoding', ''),
        ('assay_name', 'MiFish', ''),
        ('targetTaxonomicAssay', 'Vertebrata', ''),
        ('target_gene', '12S rRNA (SSU mitochondria)', ''),
        ('pcr_primer_forward', 'GTCGGTAAAACTCGTGCCAGC', ''),
        ('pcr_primer_reverse', 'CATAGTGGGGTATCTAATCCCAGTTTG', ''),
        ('pcr_primer_name_forward', 'MiFish-U-F', ''),
        ('pcr_primer_name_reverse', 'MiFish-U-R', ''),
        ('otu_db', 'NCBI GenBank nucleotide', ''),
    ])
    sheet(wb, 'sampleMetadata',
          ['samp_name', 'samp_category', 'decimalLatitude', 'decimalLongitude', 'geo_loc_name', 'eventDate',
           'env_broad_scale', 'env_local_scale', 'env_medium'],
          [['P1', 'sample', -31.95, 115.80, 'Australia: Western Australia, Perth', '2023-10-01',
            'freshwater biome [ENVO:00000873]', 'pond [ENVO:00000033]', 'fresh water [ENVO:00002011]'],
           ['P2', 'sample', -31.96, 115.81, 'Australia: Western Australia, Perth', '2023-10-01',
            'freshwater biome [ENVO:00000873]', 'pond [ENVO:00000033]', 'fresh water [ENVO:00002011]'],
           ['EB', 'negative control', '', '', 'not applicable: control sample', 'not applicable: control sample',
            '', '', '']])
    taxa = [['asv1', 'CACCGCGGTTATACGAGAGGCCCAAGTTGATAGACATCGGCGTAAAGAGTGG', 'Animalia', 'Chordata', 'Actinopteri',
             'Cypriniformes', 'Cyprinidae', 'Carassius', 'Carassius auratus', 'species'],
            ['asv2', 'CACCGCGGTTATACGAGAGGCCCAAGTTGACAGACACCGGCGTAAAGCGTGG', 'Animalia', 'Chordata', 'Amphibia',
             'Anura', 'Limnodynastidae', 'Limnodynastes', '', 'genus'],
            ['asv3', 'CACCGCGGTCATACGATTAACCCAAGTCAATAGAAACCGGCGTAAAGAGTGT', '', '', '', '', '', '', '', '']]
    columns = ['seq_id', 'dna_sequence', 'kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'scientificName',
               'taxonRank']
    reads = {'asv1': {'P1': 1, 'P2': 0, 'EB': 0}, 'asv2': {'P1': 1, 'P2': 1, 'EB': 1},
             'asv3': {'P1': 0, 'P2': 1, 'EB': 0}}
    runs = {'_MiFish_runA': ['P1'], '_MiFish_runB': ['P2', 'EB']} if two_runs else {'': ['P1', 'P2', 'EB']}
    for suffix, samples in runs.items():
        sheet(wb, f'taxaFinal{suffix}', columns, taxa)
        ws = wb.create_sheet(f'otuFinal{suffix}')
        ws.append(['seq_id'] + samples)
        for seq_id, r in reads.items():
            ws.append([seq_id] + [r[x] for x in samples])
    wb.save(OUT / ('metabarcoding_two_runs.xlsx' if two_runs else 'metabarcoding_presence.xlsx'))


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    targeted()
    metabarcoding()
    metabarcoding(two_runs=True)
    print(f'written to {OUT}')
