"""Write the made-up test data for the FAIRe mapper's day-night fixes (README.md here) to
tools/faire_mapper/test-data.

Usage: python make_testdata.py

The files copy the layouts of the day-night study's inputs, with made-up reef samples:

- apply_reef_times.xlsx: a sample sheet with the time of collection in its own column (Excel time
  cells), latitudes stored as text with trailing non-breaking spaces, a field blank and an
  extraction blank (no date, place or coordinates);
- apply_reef_times.sssom.tsv: its crosswalk, as propose mapping and a review would leave it;
- apply_reef_times_values.tsv: values for the whole project and two assays, with no trailing tab on
  the rows without an assay, an amplicon size given as a range, and habitat terms for every sample;
- otu_lca_ranks.tsv: an eDNAFlow LCA output (domain to species, then the OTU column, then one
  column per sample), and otu_lca_ranks.fasta: its ASV sequences;
- library_file_list.csv: a list of fastq files with their MD5s, as Windows PowerShell's
  Get-FileHash -Algorithm MD5 | Export-Csv writes it (a #TYPE line, then Algorithm, Hash and the
  full Path): the forward and reverse reads of four libraries, named, as the day-night study names
  its files, with the assay at the end (LIZ_01_Fish16S); library_md5sum.txt: the same files as
  md5sum writes them (checksum, two spaces, file name); library_file_names.txt: their names only,
  one per line with their folder, as the Data Access Portal lists the day-night study's files.

It also writes tools/faire2qiime/test-data/faire_subfragment_na.xlsx: faire_single_assay.xlsx with
target_subfragment 'not applicable' (FAIRe's term for no value), as for a fish 16S marker with no
named region.
"""
import datetime as dt
import os

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'tools', 'faire_mapper', 'test-data')
QIIME = os.path.join(HERE, '..', '..', 'tools', 'faire2qiime', 'test-data')
NBSP = ' '

SAMPLES = [
    # Sample ID, Site, Time, Latitude (text), Longitude, Date, Sample type, Control type
    ('LIZ_01', 'Lizard Island', dt.time(10, 0), f'-14.68472{NBSP * 4} ', 145.44247, dt.datetime(2017, 9, 6),
     'sample', None),
    ('LIZ_02', 'Lizard Island', dt.time(16, 0), f'-14.68390{NBSP * 4} ', 145.44310, dt.datetime(2017, 9, 6),
     'sample', None),
    ('LIZ_03', 'Lizard Island', dt.time(22, 0), f'-14.68211{NBSP * 4} ', 145.44502, dt.datetime(2017, 9, 6),
     'sample', None),
    ('LIZ_FB', 'Lizard Island', dt.time(22, 0), f'-14.68211{NBSP * 4} ', 145.44502, dt.datetime(2017, 9, 6),
     'negative control', 'field negative'),
    ('LIZ_EB', None, None, None, None, None, 'negative control', 'extraction negative'),
]
CROSSWALK = [
    ('Sample ID', 'samp_name'), ('Site', 'geo_loc_name'), ('Time', 'verbatimEventTime'),
    ('Latitude', 'decimalLatitude'), ('Longitude', 'decimalLongitude'), ('Date', 'eventDate'),
    ('Sample type', 'samp_category'), ('Control type', 'neg_cont_type'),
]
VALUES = """term	value	assay
project_contact	A. Person (a.person@example.org)
env_broad_scale	marine biome [ENVO:00000447]
env_local_scale	marine subtidal rocky reef [ENVO:01000150]
env_medium	ocean water [ENVO:00002149]
samp_size	1
samp_size_unit	L
pcr_0_1	1
target_gene	16S rRNA (LSU mitochondria)	Fish16S
ampliconSize	178-228	Fish16S
pcr_primer_forward	GACCCTATGGAGCTTTAGAC	Fish16S
pcr_primer_reverse	CGCTGTTATCCCTADRGTAACT	Fish16S
target_gene	COI	COILeray
ampliconSize	313	COILeray
pcr_primer_forward	GGWACWGGWTGAACWGTWTAYCCYCC	COILeray
pcr_primer_reverse	TAIACYTCIGGRTGICCRAARAAYCA	COILeray
"""
LCA = [
    # domain, phylum, class, order, family, genus, species, OTU, reads in LIZ_01, LIZ_02, LIZ_03, LIZ_FB, LIZ_EB
    ('Eukaryota', 'Chordata', 'Actinopteri', 'Perciformes', 'Lutjanidae', 'Lutjanus', 'Lutjanus carponotatus',
     'ASV_1', 1520, 88, 0, 0, 0),
    ('Eukaryota', 'Chordata', 'Actinopteri', 'Labriformes', 'Labridae', 'Thalassoma', None, 'ASV_2', 0, 412, 37,
     0, 0),
    ('Eukaryota', 'Chordata', 'Mammalia', 'Primates', 'Hominidae', 'Homo', 'Homo sapiens', 'ASV_4', 5, 0, 0, 12, 0),
]
FASTA = {
    'ASV_1': 'ACCAAAACAGACCATGTTAAAGACCCTAAAACAAAAGACTAAACTTAATGTCCCCTGCCTTGATGTCTTCGGTTGGG',
    'ASV_2': 'ACTAAGGTAGTTCACGTCAAACACCCCAGTTTAATGGGCCGAACTAAGTGAACCCTATCCTAATGTCTTTGGTTGGG',
    'ASV_3': 'ACTAAGGTAGTTCACGTCAAACACCCCAGTTTAATGGGCCGAACTAAGTGAACCCTATCCTAATGTCTTTGGTTGGA',
    'ASV_4': 'ACCAAACCTAGCCCTAATAAACAACAATAACAAACATTACAATCCAAGCAGGCCCTTTAACCCTAAGCTAAGGGCCC',
}


def file_list():
    """The same eight files as Windows PowerShell's Get-FileHash -Algorithm MD5 | Export-Csv writes
    them (a #TYPE line, then Algorithm, Hash and the full Path), and as md5sum writes them (the
    checksum, two spaces and the file name, with no header)."""
    files = [(f'{sample}_Fish16S_R{read}.fastq.gz', i, read)
             for i, sample in enumerate(('LIZ_01', 'LIZ_02', 'LIZ_03', 'LIZ_FB')) for read in (1, 2)]
    with open(os.path.join(OUT, 'library_file_list.csv'), 'w', encoding='utf-8', newline='') as f:
        f.write('#TYPE Microsoft.PowerShell.Commands.FileHashInfo\r\n"Algorithm","Hash","Path"\r\n')
        for name, i, read in files:
            f.write(f'"MD5","{(str(i) + str(read)) * 16}","C:\\Users\\lab\\reads\\{name}"\r\n')
    with open(os.path.join(OUT, 'library_md5sum.txt'), 'w', encoding='utf-8') as f:
        for name, i, read in files:
            f.write(f'{("ab" + str(i) + str(read)) * 8}  {name}\n')
    with open(os.path.join(OUT, 'library_file_names.txt'), 'w', encoding='utf-8') as f:
        for name, i, read in files:
            f.write(f'Fish16S_fastq_files/{name}\n')


def main():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['Sample ID', 'Site', 'Time', 'Latitude', 'Longitude', 'Date', 'Sample type', 'Control type'])
    for row in SAMPLES:
        ws.append(list(row))
    for r in range(2, ws.max_row + 1):
        ws.cell(r, 3).number_format = 'h:mm'
        ws.cell(r, 6).number_format = 'mm-dd-yy'
    wb.save(os.path.join(OUT, 'apply_reef_times.xlsx'))
    with open(os.path.join(OUT, 'apply_reef_times.sssom.tsv'), 'w', encoding='utf-8') as f:
        f.write('subject_id\tsubject_label\tpredicate_id\tobject_id\tobject_label\tmapping_justification\n')
        for column, term in CROSSWALK:
            f.write(f"local:{column.replace(' ', '_')}\t{column}\tskos:exactMatch\tFAIRe:{term}\t{term}\t"
                    'semapv:ManualMappingCuration\n')
    with open(os.path.join(OUT, 'apply_reef_times_values.tsv'), 'w', encoding='utf-8') as f:
        f.write(VALUES)
    with open(os.path.join(OUT, 'otu_lca_ranks.tsv'), 'w', encoding='utf-8') as f:
        f.write('\t'.join(['domain', 'phylum', 'class', 'order', 'family', 'genus', 'species', 'OTU',
                           'LIZ_01', 'LIZ_02', 'LIZ_03', 'LIZ_FB', 'LIZ_EB']) + '\n')
        for row in LCA:
            f.write('\t'.join('NA' if v is None else str(v) for v in row) + '\n')
    with open(os.path.join(OUT, 'otu_lca_ranks.fasta'), 'w', encoding='utf-8') as f:
        for name, seq in FASTA.items():
            f.write(f'>{name}\n{seq}\n')


def qiime_subfragment():
    wb = openpyxl.load_workbook(os.path.join(QIIME, 'faire_single_assay.xlsx'))
    ws = wb['projectMetadata']
    header = [c.value for c in ws[1]]
    term, level = header.index('term_name') + 1, header.index('project_level') + 1
    row = next(r for r in range(2, ws.max_row + 1) if ws.cell(r, term).value == 'target_subfragment')
    ws.cell(row, level).value = 'not applicable'
    wb.save(os.path.join(QIIME, 'faire_subfragment_na.xlsx'))


if __name__ == '__main__':
    main()
    qiime_subfragment()
    file_list()
