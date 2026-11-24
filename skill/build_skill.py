#!/usr/bin/env python3
"""Build the faire-dataset skill package from this repository.

The skill's own files (SKILL.md, references/, scripts/faire_session.py, scripts/tools/LICENSES.md) live
in skill/faire-dataset/. The FAIRe tools it runs are copied in from tools/ at build time, so the
package always carries the repository's current tools, and references/faire_terms.md is made from the
bundled FAIRe checklist.

Usage: python skill/build_skill.py [OUTDIR]     (default: skill/dist)
Writes OUTDIR/faire-dataset/ and OUTDIR/faire-dataset.zip (one top-level folder, as Claude, ChatGPT
and Microsoft 365 Copilot expect for an uploaded skill).
"""
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SRC = HERE / 'faire-dataset'

MAPPER_FILES = ['faire_mapper.py', 'faire_mapper_amp.py', 'faire_mapper_apply.py', 'faire_mapper_identify.py',
                'faire_mapper_kinds.py', 'faire_mapper_library.py', 'faire_mapper_otu.py', 'faire_mapper_review.py',
                'faire_mapper_text.py', 'faire_method_details.py', 'faire_primers.py',
                'commonly_confused_terms.tsv', 'mixs_dwc_terms.tsv', 'LICENSE']
MAPPER_DIRS = ['checklist', 'method_details', 'primers']
FAIREFIER_FILES = ['fairefier_cli.py', 'create_validator.py', 'config_data.py', 'LICENSE', 'LICENSE.upstream']
FAIREFIER_CHECKLISTS = ['FAIRe_checklist_v1.0.2.xlsx', 'FAIRe_checklist_v1.0.xlsx', 'LICENSE']


def terms_reference(checklist, out):
    """references/faire_terms.md: the mandatory and highly recommended terms of the checklist."""
    import pandas as pd
    ck = pd.read_excel(checklist, sheet_name='checklist', dtype=str).fillna('')
    sel = ck[ck.requirement_level.isin(['Mandatory', 'Highly recommended'])]

    def clean(x):
        return re.sub(r'\s+', ' ', x).strip()

    lines = ['# FAIRe terms: mandatory and highly recommended', '',
             f'From the FAIRe checklist ({Path(checklist).name}, CC BY 4.0), bundled at '
             '`scripts/tools/faire_mapper/checklist/`.',
             f'The checklist has {len(ck)} terms; these are its {len(sel)} mandatory and highly recommended ones. '
             'The sheets in brackets are where each term goes in the workbook. Allowed values are given where the '
             'checklist fixes them (`other:` means free text may follow `other: `).', '']
    for level in ('Mandatory', 'Highly recommended'):
        lines += [f'## {level}', '']
        for section, g in sel[sel.requirement_level == level].groupby('section', sort=False):
            lines += [f'### {section}', '']
            for _, r in g.iterrows():
                sheets = ', '.join(x.strip() for x in r.data_type.split('|') if x.strip())
                d = clean(r.description)
                if len(d) > 300:
                    d = d[:297].rsplit(' ', 1)[0] + ' ...'
                parts = [f'**{r.term_name}** ({sheets})', d]
                if r.requirement_level_condition:
                    parts.append(f'Condition: {clean(r.requirement_level_condition)}.')
                if r.controlled_vocabulary_options:
                    parts.append(f'Allowed: {clean(r.controlled_vocabulary_options)}.')
                if r.unit:
                    parts.append(f'Unit: {clean(r.unit)}.')
                if r.fixed_format:
                    parts.append(f'Format: {clean(r.fixed_format)}.')
                if r.example:
                    parts.append(f'Example: {clean(r.example)[:120]}.')
                if r.sample_type_specificity and r.sample_type_specificity != 'ALL':
                    parts.append(f'Sample types: {clean(r.sample_type_specificity)}.')
                lines.append('- ' + ' '.join(parts))
            lines.append('')
    Path(out).write_text('\n'.join(lines), encoding='utf-8')


def main(outdir=None):
    out = Path(outdir or HERE / 'dist').resolve()
    pkg = out / 'faire-dataset'
    if pkg.exists():
        shutil.rmtree(pkg)
    shutil.copytree(SRC, pkg, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    tools = pkg / 'scripts' / 'tools'
    (tools / 'faire_mapper').mkdir(parents=True, exist_ok=True)
    (tools / 'fairefier' / 'checklist').mkdir(parents=True, exist_ok=True)
    for f in MAPPER_FILES:
        shutil.copy(REPO / 'tools' / 'faire_mapper' / f, tools / 'faire_mapper' / f)
    for d in MAPPER_DIRS:
        shutil.copytree(REPO / 'tools' / 'faire_mapper' / d, tools / 'faire_mapper' / d)
    for f in FAIREFIER_FILES:
        shutil.copy(REPO / 'tools' / 'fairefier' / f, tools / 'fairefier' / f)
    for f in FAIREFIER_CHECKLISTS:
        shutil.copy(REPO / 'tools' / 'fairefier' / 'checklist' / f, tools / 'fairefier' / 'checklist' / f)
    try:
        commit = subprocess.run(['git', '-C', str(REPO), 'log', '-1', '--format=%H %cs'], capture_output=True,
                                text=True, check=True).stdout.strip()
        dirty = subprocess.run(['git', '-C', str(REPO), 'status', '--porcelain', '--', 'tools', 'skill'],
                               capture_output=True, text=True).stdout.strip()
        if dirty:
            commit += ' (with uncommitted changes)'
    except (subprocess.CalledProcessError, FileNotFoundError):
        commit = 'unknown'
    (tools / 'SOURCE_COMMIT').write_text(commit + '\n', encoding='utf-8')
    terms_reference(tools / 'faire_mapper' / 'checklist' / 'FAIRe_checklist_v1.0.2.xlsx',
                    pkg / 'references' / 'faire_terms.md')
    z = out / 'faire-dataset.zip'
    if z.exists():
        z.unlink()
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(pkg.rglob('*')):
            if f.is_file():
                zf.write(f, f.relative_to(out).as_posix())
    size = z.stat().st_size / 1e6
    print(f'Built {pkg}\n      {z} ({size:.1f} MB), FAIRe-Galaxy {commit}')


if __name__ == '__main__':
    main(*sys.argv[1:2])
