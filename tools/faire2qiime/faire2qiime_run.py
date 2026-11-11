"""Run upstream FAIRe2QIIME with a reader that keeps the workbook's values as written.

Usage: python faire2qiime_run.py UPSTREAM.py ARGUMENTS   (FAIRe2QIIME's own arguments)

FAIRe2QIIME reads each sheet with pd.read_excel(..., comment='#'), to skip the two rows above the field
names that start with '#'. pandas then treats a '#' anywhere in a cell as the start of a comment, so
'Sta1 #2' becomes 'Sta1 ' and the rest of that row is lost. pandas also gives each column one type, so
IDs written as text (001) become numbers (1). While FAIRe2QIIME runs, its calls to read the three
metadata sheets go to a reader that skips only the rows whose first cell starts with '#', and keeps
each cell's own type (dtype=object). Missing values are read as upstream reads them (pandas' defaults).
The upstream file is not changed. If FAIRe2QIIME no longer reads a sheet this way, the run stops, so
the workaround cannot stop working without anyone noticing.
"""
import os
import runpy
import sys

import pandas as pd

SHEETS = ('projectMetadata', 'sampleMetadata', 'experimentRunMetadata')
original_read_excel = pd.read_excel
read_through_us = set()


def read_excel(io, sheet_name=0, *args, **kwargs):
    if kwargs.get('comment') != '#' or args or sheet_name not in SHEETS or set(kwargs) - {'comment'}:
        return original_read_excel(io, sheet_name, *args, **kwargs)
    first = original_read_excel(io, sheet_name=sheet_name, header=None, usecols=[0], dtype=object)
    skip = [i for i, v in enumerate(first.iloc[:, 0]) if isinstance(v, str) and v.lstrip().startswith('#')]
    read_through_us.add(sheet_name)
    return original_read_excel(io, sheet_name=sheet_name, header=0, skiprows=skip, dtype=object)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    upstream = os.path.abspath(sys.argv[1])
    sys.argv = [upstream] + sys.argv[2:]
    pd.read_excel = read_excel
    runpy.run_path(upstream, run_name='__main__')
    missing = [s for s in SHEETS if s not in read_through_us]
    if missing:
        sys.exit("ERROR: FAIRe2QIIME no longer reads " + ', '.join(missing) + " with comment='#', so the "
                 "Galaxy wrapper's reader (which keeps '#' inside cells and IDs such as 001) was not used. "
                 "The wrapper needs updating for this FAIRe2QIIME version.")


if __name__ == '__main__':
    main()
