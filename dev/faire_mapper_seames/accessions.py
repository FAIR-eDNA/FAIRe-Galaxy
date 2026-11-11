"""Accession tables for the submission tools, made from ENA's run report for PRJNA1263580.

The samples are registered at NCBI already, so the trial links runs to them as a lab would after
registering: FAIRe2NCBI SRA takes NCBI's BioSample accession table, and FAIRe2ENA runs takes the
receipt of an ENA sample submission. Both are made here from the report's sample accessions
(SAMN... and SRS...); the receipt is a stand-in, as these samples were never submitted to ENA.
The sample name is the start of the library name (M159 in M159_16SFish_LerayCOI). The 12 10 L
samples sequenced for 18S were registered a second time with those libraries, so each has two
BioSamples; LIBRARY_TEXT keeps the libraries whose name holds it (16SFish), and with them the
BioSamples of file 1.

Usage: python accessions.py FILEREPORT.tsv BIOSAMPLE_ACCESSIONS.tsv ENA_RECEIPT.xml [LIBRARY_TEXT]
"""
import csv
import sys
from xml.sax.saxutils import quoteattr

report, accessions_out, receipt_out = sys.argv[1:4]
keep = sys.argv[4] if len(sys.argv) > 4 else ''
samples = {}
with open(report, encoding='utf-8') as f:
    for r in csv.DictReader(f, delimiter='\t'):
        if keep not in r['library_name']:
            continue
        name = r['library_name'].split('_')[0]
        samples.setdefault(name, (r['sample_accession'], r['secondary_sample_accession'], r['study_accession']))
with open(accessions_out, 'w', encoding='utf-8') as f:
    f.write('accession\tsample_name\tbioproject_accession\n')
    for name, (samn, _, study) in sorted(samples.items()):
        f.write(f'{samn}\t{name}\t{study}\n')
with open(receipt_out, 'w', encoding='utf-8') as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!-- A stand-in for an ENA receipt, made by accessions.py from the run report. -->\n'
            '<RECEIPT receiptDate="2026-11-04T00:00:00.000Z" submissionFile="submission.xml" success="true">\n')
    for name, (samn, srs, _) in sorted(samples.items()):
        f.write(f'     <SAMPLE accession={quoteattr(srs)} alias={quoteattr(name)} status="PUBLIC">\n'
                f'          <EXT_ID accession={quoteattr(samn)} type="biosample"/>\n     </SAMPLE>\n')
    f.write('     <ACTIONS>ADD</ACTIONS>\n</RECEIPT>\n')
print(f'{len(samples)} samples')
