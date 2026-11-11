#!/usr/bin/env bash
# Rebuild the cases and run every check. Usage: bash run_all.sh [FAIRe examples folder]
set -u
cd "$(dirname "$0")"
rm -rf cases && python3 -I make_cases.py cases
python3 -I check.py cases ${1:+--examples "$1"} > /dev/null; status=$?
python3 -I downstream.py cases/P00_ncbi_noaa_fixture.xlsx cases/P01_noaa_layout.xlsx cases/P03_na_like_text.xlsx \
    cases/P04_text_starting_with_equals.xlsx cases/P06_dates_and_times.xlsx cases/N01_associated_sequences_na.xlsx \
    --report results/DOWNSTREAM_NCBI.md > /dev/null
python3 -I downstream.py cases/P01_noaa_layout.xlsx cases/P03_na_like_text.xlsx cases/P04_text_starting_with_equals.xlsx \
    cases/P07_numbers_and_ids.xlsx cases/P08_whitespace.xlsx --only-obis --report results/DOWNSTREAM_EDNA2OBIS.md > /dev/null
echo "check.py exit $status (1 means unexpected differences); see results/"
exit $status
