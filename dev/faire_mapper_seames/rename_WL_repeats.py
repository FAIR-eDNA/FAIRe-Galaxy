"""Name Wilderlab's repeated sample columns as the authors confirmed.

Usage: python rename_WL_repeats.py WILDERLAB.csv OUT.csv

Wilderlab's table (file 8) has CN065 and CN066 twice, with different counts. The second of each is
CN165 and CN166 (B. Deagle, 6 November 2026; to be corrected in the data record). Only the header
line changes: the second CN065 becomes CN165 and the second CN066 becomes CN166, with the quoting as
written. Without this step, apply mapping keeps the first of each and leaves the second out.
"""
import re
import sys

SECOND = {'CN065': 'CN165', 'CN066': 'CN166'}


def main(src, dst):
    with open(src, encoding='utf-8', newline='') as fh:
        text = fh.read()
    head, sep, body = text.partition('\n')
    fields = head.rstrip('\r').split(',')
    seen, renamed = set(), []
    for i, f in enumerate(fields):
        name = f.strip().strip('"')
        if name in SECOND and name in seen:
            fields[i] = re.sub(re.escape(name), SECOND[name], f)
            renamed.append(f'{name} -> {SECOND[name]}')
        seen.add(name)
    cr = '\r' if head.endswith('\r') else ''
    with open(dst, 'w', encoding='utf-8', newline='') as fh:
        fh.write(','.join(fields) + cr + sep + body)
    print('renamed the second column of ' + (', '.join(renamed) if renamed else 'none (no repeats found)'))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
