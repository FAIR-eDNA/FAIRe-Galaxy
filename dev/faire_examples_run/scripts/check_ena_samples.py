"""Summarise an ENA SAMPLE XML: sample count, attribute fill, suspicious values."""
import collections
import re
import sys
import xml.etree.ElementTree as ET

ENA_DATE = re.compile(r"(^[12][0-9]{3}(-(0[1-9]|1[0-2])(-(0[1-9]|[12][0-9]|3[01])(T[0-9]{2}:[0-9]{2}(:[0-9]{2})?Z?([+-][0-9]{1,2})?)?)?)?(/[0-9]{4}(-[0-9]{2}(-[0-9]{2}(T[0-9]{2}:[0-9]{2}(:[0-9]{2})?Z?([+-][0-9]{1,2})?)?)?)?)?$)|(^not applicable$)|(^not collected$)|(^not provided$)|(^restricted access$)|(^missing: control sample$)|(^missing: sample group$)|(^missing: synthetic construct$)|(^missing: lab stock$)|(^missing: third party data$)|(^missing: data agreement established pre-2023$)|(^missing: endangered species$)|(^missing: human-identifiable$)|(^missing$)")

for path in sys.argv[1:]:
    root = ET.parse(path).getroot()
    samples = root.findall('SAMPLE')
    aliases = [s.get('alias') for s in samples]
    print(f"{path}: {len(samples)} SAMPLE, {len(set(aliases))} unique aliases")
    vals = collections.defaultdict(list)
    for s in samples:
        tags = collections.Counter()
        for a in s.iter('SAMPLE_ATTRIBUTE'):
            tag = a.findtext('TAG')
            tags[tag] += 1
            vals[tag].append(a.findtext('VALUE'))
        dup = [t for t, n in tags.items() if n > 1]
        if dup:
            print('  duplicate TAG in', s.get('alias'), dup)
    for tag in sorted(vals):
        v = vals[tag]
        c = collections.Counter(v)
        odd = [x for x in c if x is None or x.lower() in ('nan', 'unknown', 'none', '') or 'nan' == x.split(' ')[0].lower()]
        print(f"  {tag!r}: n={len(v)} distinct={len(c)} eg={list(c)[:2]}" + (f" ODD={[(o, c[o]) for o in odd]}" if odd else ''))
    bad_dates = [d for d in vals.get('collection date', []) if not ENA_DATE.match(d or '')]
    print('  collection dates failing ENA regex:', len(bad_dates), bad_dates[:3])
    print('  collection date forms:', collections.Counter(re.sub(r'\d', '9', d) for d in vals.get('collection date', [])).most_common(5))
