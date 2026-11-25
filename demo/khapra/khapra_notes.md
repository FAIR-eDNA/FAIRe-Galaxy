# Khapra beetle: details of the qPCR assays from the paper

The Dryad README gives the primers, probes and cycling conditions, but not where the assays come from, their limits of detection, how a detection was called or why field controls amplified. These notes give those details from the paper, in our own words, for the FAIRe tools demonstration. They are not part of the published record.

The paper: Trujillo-González A, Thuo DN, Divi U, Sparks K, Wallenius T, Gleeson D (2022) Detection of khapra beetle environmental DNA using portable technologies in Australian biosecurity. Frontiers in Insect Science 2: 795379. https://doi.org/10.3389/finsc.2022.795379 (CC BY 4.0).

## The two TaqMan assays

The Olson assay (Olson et al. 2014) amplifies a 248 bp fragment of the mitochondrial 16S rRNA gene with the forward primer der16SF4 (CTAAAATTGAAAATTTCTATACT) and the reverse primer der16SR1 (CTAGCCTGCTCCCTGATTGA). The authors modified its probe, P1 (TGACTGTGCGAAGGTAGCAT), from the original sequence.

The Furui assay (Furui et al. 2019) amplifies an 83 bp fragment of the mitochondrial ND6 gene with the forward primer Furui F (CAGCCTTATATGACTTCTCATACC) and the reverse primer Furui R (GATTTCATGTTGGGAATGATG). Its probe is Furui P (GCAAATGGTGGCGAGTGTTGTC).

Both probes carry FAM as the reporter dye and QSY as the quencher.

## Limits of detection

The limit of detection of each assay came from a standard curve of synthetic gBlock gene fragments (double-stranded DNA from Integrated DNA Technologies) designed for that assay, diluted from 10^7 to 1 copy/µL, each run six times. The limit is the lowest dilution that amplified in all six runs: 100 copies/µL for the Olson assay and 10 copies/µL for the Furui assay. The paper gives no limit of quantification.

## Calling a detection

A replicate was positive when its amplification curve crossed a common fluorescence threshold, set in each qPCR run from the positive controls. The paper gives no fixed quantification cycle threshold for either assay. Replicates that amplified beyond the limit of detection were checked by Sanger sequencing.

## Field controls

Positive detections were common in the field negative controls (12.3% at Tuggeranong and 50% at Fyshwick). The authors attribute this mostly to contaminated vacuum cleaners. At Fyshwick the vacuum cleaner had been used in a separate khapra beetle response three days before. At Tuggeranong the vacuum cleaners were not sterilised between sampling grids.

## Licence

Dryad publishes every dataset under the Creative Commons Zero (CC0 1.0) waiver: http://creativecommons.org/publicdomain/zero/1.0/legalcode

## References

Furui S, Miyanoshita A, Imamura T, Minegishi Y, Kokutani R (2019) Qualitative real-time PCR identification of the khapra beetle, Trogoderma granarium (Coleoptera: Dermestidae). Applied Entomology and Zoology 54: 101-107.

Olson RLO, Farris RE, Barr NB, Cognato AI (2014) Molecular identification of Trogoderma granarium (Coleoptera: Dermestidae) using the 16s gene. Journal of Pest Science 87: 701-710.
