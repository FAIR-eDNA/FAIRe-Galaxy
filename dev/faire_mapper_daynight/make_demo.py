"""Cut the day-night study's files down to a demonstration set with the same files and layouts.

Usage: python make_demo.py DATA_DIR OUT_DIR

DATA_DIR holds the study's files as the authors provide them (README.md): the sample sheet, the two
LCA outputs, the two FASTA files, the fastq ReadMe (eDNA_fastq_READ_ME.txt) and the paper
(West_2024.pdf). OUT_DIR gets:

- the sample sheet and the fastq ReadMe as they are;
- each LCA output with every sample column but only the TOP sequences with the most reads, and
  each FASTA file with the sequences of those rows;
- methods.txt: sections 2.1 to 2.3 of the paper (with Table 1), as pdftotext writes them, without
  the publisher's download notes in the margins.

Nothing else is edited.
"""
import os
import re
import shutil
import subprocess
import sys

import pandas as pd

TOP = 150
SHEET = 'Day_night_Tasmania_sample_data.xlsx'
README = 'eDNA_fastq_READ_ME.txt'


def cut_assay(src, out, assay):
    lca = os.path.join(src, f'Day_night_{assay}_LCA_output.txt')
    df = pd.read_csv(lca, sep='\t', dtype=str, keep_default_na=False)
    samples = list(df.columns[8:])
    reads = df[samples].apply(pd.to_numeric).sum(axis=1)
    keep = df.loc[reads.sort_values(ascending=False, kind='stable').index[:TOP]].sort_index()
    keep.to_csv(os.path.join(out, os.path.basename(lca)), sep='\t', index=False)
    wanted, write = set(keep['OTU']), False
    fasta = os.path.join(src, f'Day_night_{assay}_ASV.fasta')
    target = os.path.join(out, os.path.basename(fasta))
    with open(fasta, encoding='utf-8') as f, open(target, 'w', encoding='utf-8') as g:
        for line in f:
            if line.startswith('>'):
                write = line[1:].split()[0] in wanted
            if write:
                g.write(line)
    print(f'{assay}: {len(keep)} of {len(df)} sequences, {len(samples)} samples')


def methods(src, out):
    text = subprocess.run(['pdftotext', os.path.join(src, 'West_2024.pdf'), '-'], check=True,
                          capture_output=True, text=True).stdout
    # The headings are spaced with narrow no-break spaces (2.1 | Day/Night ...)
    start = re.search(r'2\.1\W+Day/Night UVC and eDNA Surveys', text).start()
    end = re.search(r'2\.4\W+Statistical Analyses', text).start()
    lines = [ln for ln in text[start:end].splitlines()
             if not re.search(r'Downloaded from|Terms and Conditions|Wiley Online Library|Environmental DNA, 2024|of 12$',
                              ln)]
    with open(os.path.join(out, 'methods.txt'), 'w', encoding='utf-8') as f:
        f.write('# Sections 2.1 to 2.3 of West et al. (2024) Environmental DNA 6: e70018,\n'
                '# https://doi.org/10.1002/edn3.70018 (CC BY 4.0), as text from the PDF.\n\n')
        f.write(re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip() + '\n')


def main():
    src, out = sys.argv[1:3]
    os.makedirs(out, exist_ok=True)
    for name in (SHEET, README):
        shutil.copyfile(os.path.join(src, name), os.path.join(out, name))
    for assay in ('16S', 'COI'):
        cut_assay(src, out, assay)
    methods(src, out)


if __name__ == '__main__':
    main()
