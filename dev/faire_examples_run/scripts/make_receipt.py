"""Make a stand-in ENA sample receipt (invented accessions) from a SAMPLE XML. No network."""
import sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import quoteattr

samples_xml, out = sys.argv[1], sys.argv[2]
aliases = [s.get('alias') for s in ET.parse(samples_xml).getroot().findall('SAMPLE')]
lines = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<RECEIPT receiptDate="2026-11-03T00:00:00.000Z" submissionFile="submission.xml" success="true">']
for i, a in enumerate(aliases, 1):
    lines.append(f'  <SAMPLE accession="ERS99{i:05d}" alias={quoteattr(a)} status="PRIVATE"/>')
lines.append('  <SUBMISSION accession="ERA9999999" alias="test"/>')
lines.append('</RECEIPT>')
open(out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print(f"{len(aliases)} aliases -> {out}")
