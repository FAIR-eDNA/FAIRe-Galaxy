"""The ASVs behind the published species of the Nova Scotia eelgrass study, with their sequences.

The Dryad table (Final_ASVTable_withTaxonomy_Filtered.csv) gives reads per species. The authors'
GitHub repository (fetch_github.sh) gives reads per ASV, each ASV's RDP classification and its
sequence. This script keeps the ASVs the authors' code keeps (an RDP species probability above 0.90,
as in code/R/01a_Merge_taxonomy_andASVs.R) whose species is in the published table and that have
reads in at least one published sample. For each year it writes:

  eelgrass_<year>_asvs.csv     ASV (the sequence's MD5, as QIIME 2 names it), Phylum, Class, Species,
                               Probability, then one column per sample and control
  eelgrass_<year>_asvs.fasta   the sequence of each of those ASVs

Samples are named as in the published table (CAB-1, ASB-2 ...). Controls are named by site and code:
2019 field controls CAB-FC ..., the lab control CON-LC and the extraction negatives ENEG-637 ...;
2023 site controls ASB-C ... and the extraction control EXT-C. Rose Bay's third 2019 sample (RSE_03)
is left out, as in the published table.

differences.tsv lists each sample and species where the ASV reads do not add up to the published
table's (the authors' curation after classification, such as names checked against BLAST).

Usage: python prepare_asvs.py GITHUB_DIR Final_ASVTable_withTaxonomy_Filtered.csv OUTDIR
"""

import re
import sys
from pathlib import Path

import pandas as pd

SITE_2023 = {'Aspy Bay': 'ASB', 'Chebogue': 'CHB', 'Lingan': 'LIN', 'Mira': 'MIR', 'Cheticamp': 'CHT',
             'NorthR': 'NOR', 'EastBay': 'ESB', 'Extraction': 'EXT'}
MIN_PROBABILITY = 0.90


def norm(name):
    return re.sub(r'[\s_]+', '_', str(name).strip())


def read_fasta(path):
    seqs, name = {}, None
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        if line.startswith('>'):
            name = line[1:].split()[0]
            seqs[name] = []
        elif name:
            seqs[name].append(line)
    return {k: ''.join(v).upper() for k, v in seqs.items()}


def name_2019(col):
    """CAB_01_CO1 -> CAB-1; CAB_FC_CO1 -> CAB-FC; 637_ENEG_CO1 -> ENEG-637."""
    parts = col.replace('_CO1', '').split('_')
    if parts[1] == 'ENEG':
        return f'ENEG-{parts[0]}'
    return f'{parts[0]}-{int(parts[1])}' if parts[1].isdigit() else f'{parts[0]}-{parts[1]}'


def name_2023(label):
    """'Aspy Bay - 1' -> ASB-1; 'Aspy Bay - C' -> ASB-C; 'Extraction-C' -> EXT-C."""
    site, rep = [x.strip() for x in str(label).replace(' - ', '-').rsplit('-', 1)]
    return f'{SITE_2023[site]}-{rep}'


def main(github, final_path, out):
    github, out = Path(github), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    final = pd.read_csv(final_path)
    final['sp'] = final['Species'].map(norm)
    published = [c for c in final.columns if re.fullmatch(r'[A-Z]+\d*-\d+', c)]
    species = set(final['sp'])
    tables, diffs = {}, []

    # 2019: one table with the taxonomy beside the reads
    a = pd.read_csv(github / 'COI_TaxonomyPerSite_Coastal2019_modified.csv', encoding='latin-1')
    a = a.rename(columns={'#OTU ID': 'ASV'})
    cols = {c: name_2019(c) for c in a.columns[5:]}
    a = a.rename(columns=cols).drop(columns=['RSE-3'])
    tables[2019] = (a, read_fasta(github / '2019_COI_ASV_dna-sequences.fasta'))

    # 2023: reads (Sample-1 ...), the RDP classification, and the key to the sample codes
    ft = pd.read_csv(github / 'Trask_feature_table_export.tsv', sep='\t', skiprows=1).rename(columns={'#OTU ID': 'ASV'})
    rdp = pd.read_csv(github / 'Trask_RDPv5.tsv', sep='\t', header=None)
    rdp = pd.DataFrame({'ASV': rdp[0], 'Phylum': rdp[10], 'Class': rdp[13], 'Species': rdp[25],
                        'Probability': pd.to_numeric(rdp[27], errors='coerce')})
    key = pd.read_excel(github / 'Key for Eelgrass samples_2023.xlsx')
    cols = {f'Sample-{r.Code}': name_2023(r['Sites/samples']) for _, r in key.iterrows()}
    b = rdp.merge(ft.rename(columns=cols), on='ASV')
    tables[2023] = (b, read_fasta(github / '2023_ASV_dna-sequences.fasta'))

    for year, (t, seqs) in tables.items():
        t['sp'] = t['Species'].map(norm)
        samples = [c for c in t.columns if c in published]
        controls = [c for c in t.columns[5:] if c not in published and c != 'sp']
        t[samples + controls] = t[samples + controls].fillna(0).astype(int)
        keep = t[(t['Probability'] > MIN_PROBABILITY) & t['sp'].isin(species) & (t[samples].sum(axis=1) > 0)].copy()
        missing = [x for x in keep['ASV'] if x not in seqs]
        if missing:
            sys.exit(f'{year}: {len(missing)} ASVs have no sequence, for example {missing[0]}')
        # compare with the published table
        summed = keep.groupby('sp')[samples].sum()
        for s in samples:
            for sp, v in final.set_index('sp')[s].items():
                got = int(summed[s].get(sp, 0)) if sp in summed.index else 0
                if got != int(v):
                    diffs.append({'year': year, 'sample': s, 'species': sp.replace('_', ' '),
                                  'published_reads': int(v), 'asv_reads': got})
        keep = keep.sort_values(['Phylum', 'Class', 'Species', 'ASV'])
        keep[['ASV', 'Phylum', 'Class', 'Species', 'Probability'] + samples + controls].to_csv(
            out / f'eelgrass_{year}_asvs.csv', index=False)
        with open(out / f'eelgrass_{year}_asvs.fasta', 'w', encoding='utf-8') as f:
            for x in keep['ASV']:
                f.write(f'>{x}\n{seqs[x]}\n')
        in_controls = {c: int(keep[c].sum()) for c in controls if keep[c].sum() > 0}
        print(f'{year}: {len(keep)} ASVs of {keep["sp"].nunique()} species, {len(samples)} samples and '
              f'{len(controls)} controls; reads in controls: {in_controls or "none"}')
    pd.DataFrame(diffs).to_csv(out / 'differences.tsv', sep='\t', index=False)
    print(f'{len(diffs)} sample and species cells differ from the published table (differences.tsv)')


if __name__ == '__main__':
    main(*sys.argv[1:4])
