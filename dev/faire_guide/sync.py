"""Copy the shared guide, faire_guide.xml, into every tool folder.

Each tool folder is its own ToolShed repository, so each needs its own copy of the macro file that
holds @HELP_FAIRE_GUIDE@. Edit the copy next to this script, then run:

    python dev/faire_guide/sync.py          # copy it into every tool folder
    python dev/faire_guide/sync.py --check  # report folders whose copy differs (exit 1 if any)
"""

import argparse
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
tools = here.parent.parent / 'tools'
master = here / 'faire_guide.xml'


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--check', action='store_true', help='only report copies that differ')
    args = ap.parse_args()
    text = master.read_text()
    stale = []
    for folder in sorted(p for p in tools.iterdir() if p.is_dir()):
        copy = folder / 'faire_guide.xml'
        if copy.exists() and copy.read_text() == text:
            continue
        if args.check:
            stale.append(folder.name)
        else:
            copy.write_text(text)
            print(f'updated {copy.relative_to(tools.parent)}')
    if stale:
        print('out of date: ' + ', '.join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
