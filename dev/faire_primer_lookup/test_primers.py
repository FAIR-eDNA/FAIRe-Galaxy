"""Checks of faire_primers.py on a small primer table written for the test.
Run: python test_primers.py   (needs pandas)"""
import sys
from pathlib import Path

import pandas as pd

tools = Path(__file__).resolve().parent.parent.parent / 'tools' / 'faire_mapper'
sys.path.insert(0, str(tools))
import faire_primers as fp  # noqa: E402

rows = [
    # assay, group, gene, fwd name, fwd, fwd ref, rev name, rev, rev ref
    ('12S MiFish-U', 'Fish', '12S', 'MiFish-U-F', 'GTCGGTAAAACTCGTGCCAGC', 'Miya et al., 2015',
     'MiFish-U-R', 'CATAGTGGGGTATCTAATCCCAGTTTG', 'Miya et al., 2015'),
    ('teleo', 'Fish', '12S', 'teleo_F', 'ACACCGCCCGTCACTCT', 'Valentini et al., 2016',
     'teleo_R', 'CTTCCGGTACACTTACCATG', 'Valentini et al., 2016'),
    ('18S Universal', 'Eukaryotes', '18S', '18S_1F', 'GCCAGTAGTCATATGCTTGTCT', 'Pochon et al., 2013',
     '18S_400R', 'GCCTGCTGCCTTCCTT', 'Pochon et al., 2013'),
    ('mlCOIint', 'Metazoan', 'COI', 'mlCOIintF', 'GGWACWGGWTGAACWGTWTAYCCYCC', 'Leray et al., 2013',
     'jgHCO2198', 'TAIACYTCIGGRTGICCRAARAAYCA', 'Geller et al., 2013'),
    ('', 'Frog', '16S', 'Forward', 'AAAGTCTAACCTGCCCACTGAGTTA', '', 'Reverse', 'TTTAAGCCTTTTCACTTAAAGGTCA', ''),
]
FIELDS = ['assay_name', 'target_group', 'target_gene', 'pcr_primer_name_forward', 'pcr_primer_forward',
          'pcr_primer_reference_forward', 'pcr_primer_name_reverse', 'pcr_primer_reverse',
          'pcr_primer_reference_reverse']
t = pd.DataFrame([{**dict(zip(FIELDS, r)), 'source': 'test', 'primer_pair_id': fp.pair_id(r[4], r[7])} for r in rows],
                 columns=fp.COLUMNS).fillna('')

assert fp.gene_of('12S rRNA (SSU mitochondria)') == '12S' and fp.gene_of('Cyt B') == 'CytB'
assert fp.ref_key('Pochon et al., 2013') == 'pochon 2013'
assert fp.compatible('CCGCCCGTCACYCTCCT', 'CCGCCCGTCACCCTCCT') and not fp.compatible('ACGT', 'ACGA')

# exact names, names inside longer names, and author-plus-gene assay names
assert fp.lookup(t, 'teleo')[0]['matched_by'] == 'name'
assert fp.lookup(t, 'ILF_mlCOIintF')[0]['pcr_primer_forward'] == 'GGWACWGGWTGAACWGTWTAYCCYCC'
assert fp.lookup(t, 'LerayCOI')[0]['matched_by'] == 'author and gene'
assert fp.lookup(t, 'MiFish', gene='12S rRNA (SSU mitochondria)')[0]['assay_name'] == '12S MiFish-U'
assert fp.lookup(t, 'MiFish', gene='16S') == []
# a citation matches references only
assert [c['assay_name'] for c in fp.lookup(t, 'Pochon et al., 2013')] == ['18S Universal']

text = ("Libraries were amplified with the MiFish primer set and sequenced. "
        "We used a universal eukaryote18S assay (Pochon et al., 2013). "
        "This assay has detected stygofauna before (Leray et al., 2013). "
        "Forward and reverse reads were merged. Files: Site_teleo_table_motu.csv.")
found = {e['assay_name']: e['evidence'] for e in fp.text_candidates(t, text)}
assert set(found) == {'12S MiFish-U', '18S Universal', 'teleo'}, found   # no Leray (no COI in that sentence)
assert found['18S Universal'] == ['Pochon et al., 2013']                 # and no "Forward"/"Reverse" pair
# position names at the end of longer names, and aliases in other_names
t.loc[len(t)] = {**{c: '' for c in fp.COLUMNS}, 'assay_name': '515F-Y / 806R', 'target_gene': '16S',
                 'pcr_primer_name_forward': '515F', 'pcr_primer_forward': 'GTGYCAGCMGCCGCGGTAA',
                 'pcr_primer_name_reverse': '806R', 'pcr_primer_reverse': 'GGACTACNVGGGTWTCTAAT',
                 'other_names': '515F-Y; S-D-Bact-0515-a-S-19', 'primer_pair_id': 'pp_test515'}
assert fp.lookup(t, 'Bact16S_515F')[0]['primer_pair_id'] == 'pp_test515'
assert fp.lookup(t, '515F-Y')[0]['matched_by'] == 'name'
assert fp.lookup(t, 'S-D-Bact-0515-a-S-19')[0]['primer_pair_id'] == 'pp_test515'
assert fp.lookup(t, 'Bact16S_1515F') == []          # a different position is not a match

# a curation row with 'replaces' and no sequences removes a pair entered in error, and says so
import tempfile  # noqa: E402
with tempfile.TemporaryDirectory() as d:
    base, fix = Path(d) / 'base.tsv', Path(d) / 'fix.tsv'
    t.to_csv(base, sep='\t', index=False)
    gone = t.loc[t.assay_name == 'teleo', 'primer_pair_id'].iloc[0]
    pd.DataFrame([{'pcr_primer_forward': '', 'pcr_primer_reverse': '', 'replaces': gone, 'notes': 'entered in error',
                   'source': 'test curation'}]).to_csv(fix, sep='\t', index=False)
    built, problems = fp.build([base, fix])
    assert gone not in set(built.primer_pair_id) and len(built) == len(t) - 1
    assert any(src == 'test curation' and msg.startswith(f'removed {gone} (teleo:') and 'entered in error' in msg
               for src, msg in problems), problems


# Sequences written in a text: pairs in one sentence or row, single rows paired with the next,
# adapters left out, and a pair in the table named from it.
seq_text = ('Fish were amplified with MiFish-U-F (GTCGGTAAAACTCGTGCCAGC) and MiFish-U-R '
            '(CATAGTGGGGTATCTAATCCCAGTTTG).\nOverhang TCGTCGGCAGCGTCAGATGTGTATAAGAGACAG.\n'
            'LabF  ACGTGGTCAGGATCCAAGTT\nLabR  TTGCAGGATCCTTAGCACGA\n')
occ = fp.sequences_in_text(seq_text)
assert [(o[0], o[1]) for o in occ] == [('GTCGGTAAAACTCGTGCCAGC', 'MiFish-U-F'), ('CATAGTGGGGTATCTAATCCCAGTTTG', 'MiFish-U-R'),
                                       ('ACGTGGTCAGGATCCAAGTT', 'LabF'), ('TTGCAGGATCCTTAGCACGA', 'LabR')], occ
by_seq = {c['pcr_primer_forward']: c for c in fp.text_candidates(t, seq_text)}
assert by_seq['ACGTGGTCAGGATCCAAGTT']['pcr_primer_reverse'] == 'TTGCAGGATCCTTAGCACGA'
# Out of order, as text from a PDF table often is: the table's pairs are found, and a sequence left
# over is listed on its own.
scrambled = ('CATAGTGGGGTATCTAATCCCAGTTTG\nACGTGGTCAGGATCCAAGTT\n\nGTCGGTAAAACTCGTGCCAGC\n')
got = {c['primer_pair_id']: c['matched_by'] for c in fp.text_candidates(t, scrambled)}
assert got[fp.pair_id('GTCGGTAAAACTCGTGCCAGC', 'CATAGTGGGGTATCTAATCCCAGTTTG')] == 'sequences in the text', got
assert sorted(got.values()) == ['a sequence in the text (not paired)', 'sequences in the text'], got
assert by_seq['GTCGGTAAAACTCGTGCCAGC']['assay_name'] == '12S MiFish-U'
assert by_seq['GTCGGTAAAACTCGTGCCAGC']['matched_by'] == 'sequences in the text'
assert by_seq['ACGTGGTCAGGATCCAAGTT']['matched_by'] == 'sequences in the text (not in the primer table)'
assert fp._primer_part('TCGTCGGCAGCGTCAGATGTGTATAAGAGACAG') == ''
assert fp._primer_part('TCGTCGGCAGCGTCAGATGTGTATAAGAGACAGCCAGCASCYGCGGTAATTCC') == 'CCAGCASCYGCGGTAATTCC'
assert fp.faire_gene('16S rRNA (SSU prokaryote)') == '16S rRNA (SSU prokaryote)'

print('all primer checks passed')

# laboratory names in the bundled table (curation, 5 November 2026)
bundled = fp.load(str(tools / 'primers' / 'faire_primers.tsv'))
for name, pp in [('vert01', 'pp_b8644fac14'), ('tele01', 'pp_5aadda4c79'), ('1391f', 'pp_0b73f81448'),
                 ('EukBr', 'pp_0b73f81448')]:
    hits = fp.lookup(bundled, name)
    assert [h['primer_pair_id'] for h in hits] == [pp] and hits[0]['matched_by'] == 'name', (name, hits)
print('laboratory names checked')
