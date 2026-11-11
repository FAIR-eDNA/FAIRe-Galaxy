"""Convert the Wilderlab assay list (sheet 'assays': one row per primer, the assay code on the
forward primer's row) into a primer table in faire_primers.py's columns.

Usage: convert_wilderlab.py Wilderlab_assay_details.xlsx OUTPUT.tsv
The PCR conditions (annealing temperature, cycles, replication) are Wilderlab's protocol, so they go
in the notes only: the same primers are used by others under other conditions.
"""
import re
import sys
from pathlib import Path

import pandas as pd

tools = Path(__file__).resolve().parent.parent.parent / 'tools' / 'faire_mapper'
sys.path.insert(0, str(tools))
import faire_primers as fp  # noqa: E402

GENE_WORDS = [('16S', '16S'), ('12S', '12S'), ('18S', '18S'), ('28S', '28S'), ('COI', 'COI'), ('trnL', 'trnL'),
              ('rbcL', 'rbcL'), ('ITS', 'ITS'), ('D-loop', 'D-loop'), ('tufA', 'other: tufA')]


def gene_and_region(notes):
    gene = next((g for w, g in GENE_WORDS if w.lower() in notes.lower()), '')
    region = re.search(r'\b(V\d(?:-V\d)?|ITS[12])\b', notes)
    prok = 'microbe' in notes.lower() or 'prokaryot' in notes.lower() and gene == '16S'
    faire = gene if gene.startswith('other:') else fp.faire_gene(gene, prokaryote=prok)
    return faire, (region.group(1) if region and not region.group(1).startswith('ITS') else '')


def convert(path):
    raw = pd.read_excel(path, sheet_name='assays', dtype=str)
    raw.columns = [c.strip() for c in raw.columns]
    rows, current = [], None
    for _, r in raw.iterrows():
        code = fp.given(r.get('AssayCode'))
        if code:
            current = {'code': code, 'fwd': r}
        elif current is not None:
            f, rv = current['fwd'], r
            star = re.sub(r'[^*]', '', current['code'])
            code = current['code'].strip('*')
            notes = fp.given(f.get('Notes'))
            gene, region = gene_and_region(notes + ' ' + fp.given(rv.get('Notes')))
            extra = [f"Wilderlab protocol: annealing {fp.given(f.get('AnnealingTemp'))} C, extension "
                     f"{fp.given(f.get('ExtensionTime'))} s, {fp.given(f.get('Cycles'))} cycles, "
                     f"{fp.given(f.get('Replication')).lower()}"]
            if star == '*':
                extra.append('read in one direction, trimmed at 150 bp')
            elif star == '**':
                extra.append('read in one direction, trimmed at 180 bp')
            rows.append({
                'assay_name': f'wilderlab_{code}', 'assay_type': 'metabarcoding',
                'targetTaxonomicScope': notes, 'target_gene': gene, 'target_subfragment': region,
                'pcr_primer_name_forward': fp.given(f.get('PrimerCode')),
                'pcr_primer_forward': fp.clean_seq(f.get('Sequence')),
                'pcr_primer_reference_forward': fp.given(f.get('Reference')),
                'pcr_primer_name_reverse': fp.given(rv.get('PrimerCode')),
                'pcr_primer_reverse': fp.clean_seq(rv.get('Sequence')),
                'pcr_primer_reference_reverse': fp.given(rv.get('Reference')),
                'bibliographicCitation': fp.given(f.get('Link')) if str(f.get('Link', '')).startswith('http') else '',
                'other_names': '; '.join(dict.fromkeys(n for n in (code, fp.given(f.get('OriginalName')),
                                                                     fp.given(rv.get('OriginalName'))) if n)),
                'notes': '; '.join(extra),
                'source': f'Wilderlab assay details ({Path(path).name}), assay {code}',
            })
            current = None
    return pd.DataFrame(rows, columns=fp.COLUMNS).fillna('')


if __name__ == '__main__':
    t = convert(sys.argv[1])
    t.to_csv(sys.argv[2], sep='\t', index=False)
    print(f'INFO: {len(t)} Wilderlab assays written')
