"""Turn Table S1 of the West et al. Kimberley supplement (pdftotext -layout output) into a CSV.

Usage: python -I parse_kimberley_s1.py supp.txt OUTPUT.csv
Values are copied as printed; nothing is converted (dates stay dd/mm/yyyy as in the table).
"""
import csv
import re
import sys

text = open(sys.argv[1], encoding='utf-8').read()
start = text.index('Table S1. Site location information across the Canning/Kimberley bioregions.\n')
end = text.index('Section S1: Laboratory processing', start)
lines = text[start:end].splitlines()

ROW = re.compile(r'^\s*(\d{1,2})\s+(?:(-\d+\.\d+)\s+(\d+\.\d+)\s+)?(.+?)\s{2,}(Canning|Kimberley)\s{2,}'
                 r'(Dampier Peninsula|South Kimberley|North Kimberley)\s+(?:(Inshore|Coastal|Midshelf)\s+)?'
                 r'([\d.]+)\s+(\d{2}/\d{2}/\d{4})\s*$')
COORDS = re.compile(r'^\s*(-\d+\.\d+)\s+(\d+\.\d+)\b')

rows = []
for i, line in enumerate(lines):
    m = ROW.match(line)
    if not m:
        continue
    site, lat, lon, location, bioregion, subregion, habitat, depth, date = m.groups()
    nearby = lines[max(0, i - 1):i + 2]
    if lat is None:
        for other in lines[i + 1:i + 3]:
            c = COORDS.match(other)
            if c:
                lat, lon = c.groups()
                break
    if habitat is None and any('Nearshore' in x for x in nearby) and any('Estuarine' in x for x in nearby):
        habitat = 'Nearshore Estuarine'
    rows.append({'Site No.': int(site), 'Latitude': lat, 'Longitude': lon, 'Location': location.strip(),
                 'Bioregion': bioregion, 'Subregion': subregion, 'Habitat': habitat,
                 'Site Depth (m)': depth, 'Date Collected': date})

rows.sort(key=lambda r: r['Site No.'])
numbers = [r['Site No.'] for r in rows]
missing = sorted(set(range(1, 72)) - set(numbers))
dups = sorted({n for n in numbers if numbers.count(n) > 1})
gaps = [r['Site No.'] for r in rows if not all(r.values())]
print(f'{len(rows)} rows; missing site numbers {missing}; repeated {dups}; rows with a blank value {gaps}')
with open(sys.argv[2], 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
