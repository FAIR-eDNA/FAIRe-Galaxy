#!/usr/bin/env bash
# Downloads the authors' per-ASV files for the Nova Scotia eelgrass study from their GitHub repository
# (dfo-mar-mpas/coastal-invertebrate-metabarcoding), at a fixed commit, and checks each against its
# SHA-256. These files link each ASV to its sequence, which the Dryad files do not. Nick Jeffery
# (DFO) agreed on 24 November 2026 that we can use them, and is adding a licence to the repository.
# Usage: fetch_github.sh OUTDIR        (OUTDIR must be new or empty)
set -euo pipefail
repo=https://raw.githubusercontent.com/dfo-mar-mpas/coastal-invertebrate-metabarcoding
commit=161dd75bdf180358d6201537a3154827adb21036
out=${1:?usage: fetch_github.sh OUTDIR}
mkdir -p "$out"
[ -z "$(ls -A "$out")" ] || { echo "$out is not empty" >&2; exit 1; }
while IFS='|' read -r sha path name; do
    url="$repo/$commit/$(printf '%s' "$path" | sed 's/ /%20/g')"
    curl -fsSL --retry 3 -o "$out/$name" "$url"
    echo "$sha  $out/$name" | sha256sum -c --quiet - || { echo "checksum failed: $path" >&2; exit 1; }
    echo "$name"
done <<'EOF'
58bfc2ca640666b3d88279a7d7d09c3ec0741e9e16852280f3558a8ce55a07c9|data/OldDataSets/COI_TaxonomyPerSite_Coastal2019_modified.csv|COI_TaxonomyPerSite_Coastal2019_modified.csv
10a4d1d555b04175627f08db5a1e335c3a7cd0c4c8ad6bd625841e4e7a355701|data/2019_COI_ASV_dna-sequences.fasta|2019_COI_ASV_dna-sequences.fasta
8499864db30a7bca78a65fe6b65209002f2309ff01626fe2997cb6ba4ec6c7f8|data/2023_PostBioinformaticsData/Trask_feature_table_export.tsv|Trask_feature_table_export.tsv
4fb13f87004f0e015c0fdf9b765adbb62e14c90ebab5ec5d027e91d993e687a2|data/2023_PostBioinformaticsData/Trask_RDPv5.tsv|Trask_RDPv5.tsv
85e8aed16ba4d5d8ed4bdd7f542a87d63afa48187b55de2137a5ff5f81f5b8ff|data/2023_PostBioinformaticsData/2023_ASV_dna-sequences.fasta|2023_ASV_dna-sequences.fasta
37326ad63350c8592c7eb7375d3a9ca4fad4082516b8842d3fe1386ee941e80a|data/Key for Eelgrass samples_2023.xlsx|Key for Eelgrass samples_2023.xlsx
4ca1b34883268abc1e942be3f308e184346a8f4736780830f80e201c859d051c|data/Site_coordinates.csv|Site_coordinates.csv
EOF
echo "downloaded to $out"
