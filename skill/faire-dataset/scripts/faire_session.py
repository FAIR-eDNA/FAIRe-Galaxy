#!/usr/bin/env python3
"""Run the FAIRe tools one step at a time, for an assistant helping a researcher in conversation.

The tools themselves (scripts/tools/faire_mapper and scripts/tools/fairefier) are copies of the FAIRe
mapper and FAIRe-fier from https://github.com/FAIR-eDNA/FAIRe-Galaxy, unchanged. This script keeps the
session's settings, files and decisions in one working folder (faire_work/ in the current folder, or
the folder given with --work), runs each tool with the right options, and prints what each step found
in plain text for the assistant to talk through.

Steps, in order (python faire_session.py STEP --help for each):

  setup          check that Python has what the tools need
  start          record the study's settings (assay type, sample types, assays, project ID ...)
  identify       say what each uploaded file is and where it goes
  map            propose FAIRe terms for the columns of the sample table
  table          correct a copy of the sample table (the original is never changed)
  items          list the columns still to decide, with the facts needed to decide them
  decide         record the researcher's decision on one column
  load-review    take back a review sheet the researcher filled in themselves
  methods        read the methods for values for the whole study, and for primers
  method-items   list the method values still to decide
  method-decide  record the researcher's decision on one method value
  primers-use    use a primer pair from the reference table for an assay
  primers-lookup find primer pairs by name or citation
  set            record a value the researcher gives (for the whole study, or one assay)
  unset          remove a value recorded with set
  gaps           list the mandatory FAIRe terms still without a value
  build          write the FAIRe workbook
  check          check the workbook with FAIRe-fier
  envo           search the bundled ENVO for env_broad_scale, env_local_scale and env_medium
  convert        convert the checked workbook for NCBI, ENA, GBIF or OBIS, or QIIME 2
  summary        write the handover folder: the files, and where every value came from
  status         what has been done so far, and what is next
"""
import argparse
import csv
import datetime as dt
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


SKILL = HERE.parent


def tools_dir():
    """The FAIRe tools, in their usual layout. The skill package keeps their code in scripts/ and their data
    in assets/, as skill packages expect; assets/tool-layout.json says where each file goes. They are put
    back together once, in a folder the workspace can write to, and found there on later calls."""
    import hashlib
    import tempfile
    lay = SKILL / 'assets' / 'tool-layout.json'
    if not lay.exists():
        sys.exit('assets/tool-layout.json is missing: this copy of the skill is incomplete.')
    tag = hashlib.sha1(lay.read_bytes()).hexdigest()[:12]
    files = json.loads(lay.read_text(encoding='utf-8'))['files']
    user = getattr(os, 'getuid', lambda: 0)()
    for base in (Path(tempfile.gettempdir()), Path.home() / '.cache'):
        dest = base / f'faire_tools_{user}_{tag}'
        try:
            if (dest / '.complete').exists():
                return dest
            base.mkdir(parents=True, exist_ok=True)
            tmp = Path(tempfile.mkdtemp(prefix='faire_tools_tmp_', dir=base))
            for src, info in files.items():
                for to in info['to']:
                    (tmp / to).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(SKILL / src, tmp / to)
            (tmp / '.complete').write_text(tag + '\n', encoding='utf-8')
            try:
                tmp.rename(dest)
            except OSError:  # put together at the same moment by another call
                shutil.rmtree(tmp, ignore_errors=True)
            if (dest / '.complete').exists():
                return dest
        except OSError:
            continue
    sys.exit('Could not put the FAIRe tools together: no folder in this workspace can be written to. '
             'Use advisor mode (references/advisor-mode.md).')


TOOLS = tools_dir()
MAPPER = TOOLS / 'faire_mapper'
FAIREFIER = TOOLS / 'fairefier'
CHECKLIST = MAPPER / 'checklist' / 'FAIRe_checklist_v1.0.2.xlsx'
TEMPLATE = MAPPER / 'checklist' / 'FAIRe_checklist_v1.0.2_FULLtemplate.xlsx'
CONFUSED = MAPPER / 'commonly_confused_terms.tsv'

NEEDED = [('pandas', 'pandas', ''), ('openpyxl', 'openpyxl', ''), ('numpy', 'numpy', ''),
          ('pypdf', 'pypdf', 'reading methods given as PDF; text files still work'),
          ('pydantic', 'pydantic', 'FAIRe-fier, the check step'),
          ('jinja2', 'jinja2', "FAIRe-fier's highlighted workbook, in the check step"),
          ('yaml', 'pyyaml', 'the NCBI conversion, in the convert step')]
TESTED = 'Python 3.10, 3.12 and 3.13; pandas 2.2.2, 2.2.3 and 3.0; numpy 1.26 and 2; openpyxl 3.1.5; pypdf 5.1 and 6.17; pydantic 2'

VALUES_HEAD = ['term', 'value', 'assay', 'status', 'source']
DECISIONS = ('Accept', 'Reject', 'Change')
CALL, DEC, WHY = "Mapper's call", "Reviewer's decision", "Mapper's reasoning"


class Stop(Exception):
    """A problem the person or assistant can fix; printed without a traceback."""


# ---------------------------------------------------------------- the working folder

def work_dir(args):
    return Path(args.work or os.environ.get('FAIRE_WORK') or 'faire_work').resolve()


def load_state(w):
    f = w / 'session.json'
    if not f.exists():
        raise Stop(f'No session in {w}. Run: python {Path(__file__).name} start ... first.')
    return json.loads(f.read_text(encoding='utf-8'))


def save_state(w, s):
    w.mkdir(parents=True, exist_ok=True)
    (w / 'session.json').write_text(json.dumps(s, indent=1, ensure_ascii=False), encoding='utf-8')


def log_event(w, step, text):
    with open(w / 'session_log.tsv', 'a', encoding='utf-8', newline='') as f:
        f.write(f"{dt.datetime.now().isoformat(timespec='seconds')}\t{step}\t{text}\n")


def run_tool(script, args, cwd, quiet=False):
    """Run one of the tools with this Python. Returns (exit code, stdout + stderr)."""
    cmd = [sys.executable, '-W', 'ignore', str(script)] + [str(a) for a in args]
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    out = (p.stdout or '') + (p.stderr or '')
    if p.returncode != 0 and not quiet:
        tail = '\n'.join(out.strip().splitlines()[-25:])
        raise Stop(f'{Path(script).name} stopped (exit {p.returncode}). Its last messages:\n{tail}')
    return p.returncode, out


def short(text, n=160):
    text = re.sub(r'\s+', ' ', str(text or '')).strip()
    return text if len(text) <= n else text[:n - 1].rstrip() + '…'


def read_tsv(path):
    with open(path, encoding='utf-8', newline='') as f:
        lines = [ln for ln in f if not ln.startswith('#')]
    return list(csv.DictReader(lines, delimiter='\t'))


def checklist_terms(s=None):
    """FAIRe terms by name: the full checklist, so any term can be checked."""
    sys.path.insert(0, str(MAPPER))
    import faire_mapper as fm   # noqa: E402
    sheets = ('sampleMetadata', 'experimentRunMetadata', 'projectMetadata', 'otuRaw', 'otuFinal', 'taxaRaw',
              'taxaFinal', 'ampData', 'stdData', 'eLowQuantData')
    return {t.name: t for t in fm.load_checklist(str(CHECKLIST), sheets=sheets)}


# ---------------------------------------------------------------- setup and start

def cmd_setup(args):
    missing, found = [], []
    for mod, pip_name, purpose in NEEDED:
        try:
            m = __import__(mod)
            found.append(f'{mod} {getattr(m, "__version__", "")}'.strip())
        except ImportError:
            missing.append((pip_name, purpose))
    print(f'Python {sys.version.split()[0]}')
    print('Found: ' + ', '.join(found))
    if missing and args.install:
        cmd = [sys.executable, '-m', 'pip', 'install', '--quiet'] + [m for m, _ in missing]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 and 'externally-managed' in (r.stderr + r.stdout):
            r = subprocess.run(cmd + ['--break-system-packages'], capture_output=True, text=True)
        if r.returncode == 0:
            print('Installed: ' + ', '.join(m for m, _ in missing))
            missing = []
        else:
            print('pip could not install them (this workspace may have no internet access):\n'
                  + (r.stderr or r.stdout)[-800:])
    essential = [m for m, purpose in missing if not purpose]
    for m, purpose in missing:
        print(f'Missing: {m}' + (f' (needed for {purpose})' if purpose else ' (needed for every step)'))
    if missing and not args.install:
        print('Install with:  pip install ' + ' '.join(m for m, _ in missing)
              + '   (or run setup --install; add --break-system-packages if pip refuses the system Python)')
    commit = SKILL / 'references' / 'source-commit.txt'
    print(f'FAIRe tools: FAIRe-Galaxy commit {commit.read_text().split()[0][:7] if commit.exists() else "unknown"}'
          f'; tested with {TESTED}.')
    if essential:
        print('Not ready: the tools cannot run without ' + ', '.join(essential) + '. If they cannot be installed '
              'here, use advisor mode (references/advisor-mode.md).')
        return 1
    print('Ready.' if not missing else 'Ready, except for the steps named above.')
    return 0


def split_list(text):
    return [x.strip() for x in re.split(r'[,;]', text or '') if x.strip()]


def cmd_start(args):
    w = work_dir(args)
    s = json.loads((w / 'session.json').read_text(encoding='utf-8')) if (w / 'session.json').exists() else {}
    s.setdefault('created', dt.datetime.now().isoformat(timespec='seconds'))
    if args.assay_type:
        s['assay_type'] = args.assay_type
    if args.sample_types is not None:
        s['sample_types'] = split_list(args.sample_types)
    if args.assays is not None:
        names = split_list(args.assays)
        bad = [a for a in names if not re.fullmatch(r'[A-Za-z0-9_.-]+', a)]
        if bad:
            raise Stop(f'Assay names need letters, digits, _ . or - only (FAIRe asks for no spaces): {", ".join(bad)}')
        s['assays'] = names
    if args.project_id is not None:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', args.project_id):
            raise Stop('The project ID needs letters, digits, _ or - only (FAIRe asks for no spaces or special '
                       'characters), for example Smith2025_RiverFish.')
        s['project_id'] = args.project_id
    for k in ('country', 'utc_offset', 'date_order'):
        v = getattr(args, k)
        if v is not None:
            s[k] = v
    if s.get('utc_offset') and not re.fullmatch(r'Z|[+-]\d{2}:\d{2}', s['utc_offset']):
        raise Stop('Give the UTC offset as +HH:MM or -HH:MM (for example +08:00 for Perth, +10:00 for AEST), or Z.')
    s.setdefault('assay_type', 'metabarcoding')
    save_state(w, s)
    log_event(w, 'start', json.dumps({k: s.get(k) for k in ('assay_type', 'sample_types', 'assays', 'project_id',
                                                               'country', 'utc_offset', 'date_order')}))
    print(f'Session folder: {w}')
    for k, label in (('assay_type', 'Assay type'), ('sample_types', 'Sample types'), ('assays', 'Assays'),
                     ('project_id', 'Project ID'), ('country', 'Country or sea'), ('utc_offset', 'UTC offset'),
                     ('date_order', 'Date order')):
        v = s.get(k)
        print(f'  {label}: {", ".join(v) if isinstance(v, list) else (v or "(not given)")}')
    if not s.get('sample_types'):
        print('Note: no sample types given; the mapper will consider terms for every sample type.')
    return 0


# ---------------------------------------------------------------- identify

def cmd_identify(args):
    w = work_dir(args)
    s = load_state(w)
    d = w / 'identify'
    d.mkdir(parents=True, exist_ok=True)
    targs = ['--checklist', CHECKLIST]
    for f in args.files:
        p = Path(f).resolve()
        if not p.exists():
            raise Stop(f'No such file: {f}')
        targs += ['--file', p, '--name', p.name]
    targs += ['-o', d / 'identify_report.tsv']
    run_tool(MAPPER / 'faire_mapper_identify.py', targs, d)
    rows = read_tsv(d / 'identify_report.tsv')
    s['files'] = sorted(set(s.get('files', []) + [str(Path(f).resolve()) for f in args.files]))
    save_state(w, s)
    print(f'{len(rows)} tables or texts (each Excel sheet counts on its own):')
    for r in rows:
        name = r['file'] + (f" [sheet {r['sheet']}]" if r.get('sheet') else '')
        print(f"\n- {name}: {r['kind']}")
        print(f"  why: {short(r['why'], 300)}")
        print(f"  use: {short(r['give it as'], 200)}")
        if r.get('then'):
            print(f"  then: {short(r['then'], 300)}")
    return 0


# ---------------------------------------------------------------- map and the review sheet

def review_paths(w):
    return w / 'map' / 'out' / 'review_sheet.xlsx', w / 'map' / 'review_sheet_reviewed.xlsx'


def cmd_map(args):
    w = work_dir(args)
    s = load_state(w)
    if not args.table and not s.get('table'):
        raise Stop('Give the sample table to map.')
    table = Path(args.table).resolve() if args.table else Path(s['table']['path'])
    if not table.exists():
        raise Stop(f'No such file: {table}')
    if not args.table:   # mapping the session's table again (after corrections): keep its sheet and header row
        args.sheet = args.sheet or s['table'].get('sheet')
        args.header_row = s['table'].get('header_row', args.header_row) if args.header_row == 1 else args.header_row
    d = w / 'map'
    if (d / 'review_sheet_reviewed.xlsx').exists() and not args.earlier_review and not args.again:
        raise Stop('This session already has a review in progress (faire_work/map/review_sheet_reviewed.xlsx). '
                   'To map a changed table and keep the decisions made so far, run map again with --again '
                   '(it gives the current review as the earlier review).')
    earlier = None
    if args.again and (d / 'review_sheet_reviewed.xlsx').exists():
        earlier = d / f'earlier_review_{dt.datetime.now():%Y%m%d_%H%M%S}.xlsx'
        shutil.copy(d / 'review_sheet_reviewed.xlsx', earlier)
    elif args.earlier_review:
        earlier = Path(args.earlier_review).resolve()
    if (d / 'out').exists():
        shutil.rmtree(d / 'out')
    d.mkdir(parents=True, exist_ok=True)
    targs = ['map', table] + (['--sheet', args.sheet] if args.sheet else []) + ['--header_row', args.header_row,
             '--checklist', CHECKLIST, '--assay_type', s.get('assay_type', 'metabarcoding')]
    if s.get('sample_types'):
        targs += ['--sample_types', ','.join(s['sample_types'])]
    if args.dictionary:
        targs += ['--dictionary', Path(args.dictionary).resolve()]
        if args.dictionary_sheet:
            targs += ['--dictionary_sheet', args.dictionary_sheet]
    if earlier:
        targs += ['--earlier_review', earlier, '--earlier_review_name', 'the earlier review']
    targs += ['--table_name', table.name, '-o', d / 'out']
    _, out = run_tool(MAPPER / 'faire_mapper.py', targs, d)
    shutil.copy(d / 'out' / 'review_sheet.xlsx', d / 'review_sheet_reviewed.xlsx')
    keep = s.get('table', {}).get('original') if not args.table else None
    s['table'] = dict(path=str(table), sheet=args.sheet or '', header_row=args.header_row,
                      name=Path(keep).name if keep else table.name)
    if keep:
        s['table']['original'] = keep
    if Path(str(table)).suffix.lower() == '.xls':
        print('Note: .xls files are read, but corrections are saved as .xlsx.')
    s['dictionary'] = str(Path(args.dictionary).resolve()) if args.dictionary else ''
    save_state(w, s)
    log_event(w, 'map', f'{table.name}' + (' (earlier review carried over)' if earlier else ''))
    summ = json.loads((d / 'out' / 'summary.json').read_text(encoding='utf-8'))
    print(f"{summ['columns']} columns of {table.name}: {summ['accept']} matched clearly, "
          f"{summ['review']} to check, {summ['no_match']} with no FAIRe term"
          + (f", {summ.get('other_standard', 0)} with a MIxS or Darwin Core term to consider"
             if summ.get('other_standard') else '') + '.')
    for line in out.splitlines():
        if line.startswith('WARNING') or 'read as' in line and line.startswith('INFO: read'):
            print(line)
    if summ.get('read_notes'):
        print('How the file was read: ' + '; '.join(summ['read_notes']))
    if summ.get('ambiguous_dates'):
        print('Dates that read either day first or month first: ' + ', '.join(map(str, summ['ambiguous_dates']))
              + '. Ask which order, then run start --date_order dmy (or mdy).')
    show_review(w, s, only_open=False, brief=True)
    return 0


def open_review(w):
    from openpyxl import load_workbook
    _, reviewed = review_paths(w)
    if not reviewed.exists():
        raise Stop('No review sheet yet. Run map first.')
    wb = load_workbook(reviewed)
    ws = wb['Review']
    head = [str(c.value or '').strip() for c in ws[1]]
    return wb, ws, {h: i for i, h in enumerate(head)}


def review_rows(w):
    wb, ws, at = open_review(w)
    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r[at['Input term']]:
            continue
        rows.append({h: ('' if r[i] is None else r[i]) for h, i in at.items() if i < len(r)})
    return rows


def requests_by_column(w):
    f = w / 'map' / 'out' / 'adjudication_requests.json'
    return {r['column']: r for r in json.loads(f.read_text(encoding='utf-8'))} if f.exists() else {}


def crosswalk_comments(w):
    f = w / 'map' / 'out' / 'crosswalk.sssom.tsv'
    out = {}
    if f.exists():
        for r in read_tsv(f):
            out.setdefault(r.get('subject_label', ''), []).append(r.get('comment', ''))
    return out


def choices_for(w):
    """The replacement list for each column: its best candidates (before the blank line) and all terms."""
    from openpyxl import load_workbook
    _, reviewed = review_paths(w)
    ws = load_workbook(reviewed, read_only=True)['Choices']
    cols = list(ws.iter_rows(values_only=True))
    if not cols:
        return {}
    out = {}
    for j, col in enumerate(cols[0]):
        if not col:
            continue
        vals = [r[j] if j < len(r) else None for r in cols[1:]]
        best = []
        for v in vals:
            if v in (None, ''):
                break
            best.append(str(v))
        out[str(col)] = dict(best=best, all=[str(v) for v in vals if v not in (None, '')])
    return out


def confused_question(term):
    """For a commonly confused term: what it means, the terms it is confused with, and the question to ask."""
    if not CONFUSED.exists():
        return ''
    rows = read_tsv(CONFUSED)
    mine = [r for r in rows if term in [t.strip() for t in r.get('term', '').split(',')]]
    if not mine:
        return ''
    group = mine[0].get('group', '')
    same = [r for r in rows if r.get('group') == group]
    others = [r['term'] for r in same if r is not mine[0]]
    question = next((r.get('check') for r in same if r.get('check')), '')
    return (f"{term} means {mine[0].get('meaning', '').strip()}. Often confused with {', '.join(others)}. "
            f"Ask: {question}").strip()


def table_examples(s, n=3):
    """A few distinct values of each column of the session's table."""
    t = s.get('table') or {}
    if not t.get('path'):
        return {}
    try:
        sys.path.insert(0, str(MAPPER))
        import faire_mapper as fm   # noqa: E402
        df = fm.read_table(t['path'], t.get('sheet') or None, int(t.get('header_row') or 1))
    except Exception:
        return {}
    out = {}
    for c in df.columns:
        seen = []
        for v in df[c].tolist():
            if fm.is_missing(v):
                continue
            v = short(v, 30)
            if v not in seen:
                seen.append(v)
            if len(seen) == n:
                break
        out[str(c)] = seen
    return out


def show_review(w, s, only_open=True, brief=False):
    rows = review_rows(w)
    reqs = requests_by_column(w)
    comments = crosswalk_comments(w)
    accepted = [r for r in rows if r.get("Reviewer's decision") == 'Accept' and r.get("Mapper's call") == 'accept']
    open_rows = [r for r in rows if not r.get("Reviewer's decision")]
    decided = [r for r in rows if r.get("Reviewer's decision") and r not in accepted]
    if brief:
        if accepted:
            examples = table_examples(s)
            terms = checklist_terms()
            print('\nMatched clearly (marked Accept; check the values fit the term):')
            for r in accepted:
                col, prop = r['Input term'], str(r['Proposed FAIRe term'])
                eg = examples.get(col, [])
                line = f"  {col} -> {prop}" + (f"   e.g. {', '.join(eg)}" if eg else '')
                t = terms.get(re.sub(r'\s*\(.*\)$', '', prop.split('+')[0]).strip())
                if t is not None and t.vocab and not any(v.lower().startswith('http') for v in t.vocab):
                    allowed = {v.lower() for v in t.vocab}
                    if eg and any(v.lower() not in allowed for v in eg):
                        line += f"   [values are not {prop}'s allowed values: {short(' | '.join(t.vocab), 120)}]"
                print(line)
        if open_rows:
            print('\nTo decide with the researcher (run items for the details):')
            for r in open_rows:
                prop = r['Proposed FAIRe term'] or 'no FAIRe term proposed'
                print(f"  {r['Input term']} -> {prop} ({r[CALL]})")
    else:
        todo = open_rows if only_open else rows
        if not todo:
            print('Every column has a decision.')
        for r in todo:
            col = r['Input term']
            print(f"\n## {col}")
            print(f"Proposed: {r['Proposed FAIRe term'] or '(none)'}   mapper's call: {r[CALL]}"
                  + (f"   decision so far: {r[DEC]} {r.get('Replacement FAIRe term') or ''}"
                     if r.get("Reviewer's decision") else ''))
            print(f"Why: {short(r[WHY], 400)}")
            q = reqs.get(col)
            if q:
                vals = q.get('values') or []
                print(f"Values: {short(' | '.join(map(str, vals[:8])), 300)}" + (f'  ({q.get("profile")})'
                                                                                if q.get('profile') else ''))
                print('Candidates:')
                for c in q.get('candidates', [])[:6]:
                    allowed = f" Allowed: {short(' | '.join(c['allowed_values']), 150)}." if c.get('allowed_values') else ''
                    print(f"  - {c['term']} ({c.get('sheet', '').split(';')[0]}): {short(c.get('description'), 220)}"
                          f"{allowed}")
            for t in [x.strip() for x in str(r['Proposed FAIRe term']).split('+')]:
                cq = confused_question(re.sub(r'\s*\(.*\)$', '', t))
                if cq:
                    print(f'Commonly confused: {cq}')
            for c in comments.get(col, [])[:1]:
                if c:
                    print(f'Mapper\'s note: {short(c, 500)}')
    checks = w / 'map' / 'out' / 'review_list.tsv'
    if checks.exists():
        items = read_tsv(checks)
        if items:
            print('\nAdditional checks (only a person can settle these; changes go in the table, then map --again):')
            for r in items:
                print(f"  - {r['check']}: {short(r['columns'], 60)}; {short(r['rows'], 120)}. "
                      f"{short(r['what_to_do'], 260)}")
    n_open = len(open_rows)
    print(f"\n{len(rows)} columns: {len(accepted)} accepted by the mapper, {len(decided)} decided, {n_open} still to decide.")


def cmd_items(args):
    w = work_dir(args)
    s = load_state(w)
    show_review(w, s, only_open=not args.all)
    return 0


def cmd_decide(args):
    w = work_dir(args)
    load_state(w)
    wb, ws, at = open_review(w)
    decision = args.decision.capitalize()
    if decision not in DECISIONS:
        raise Stop('The decision is accept, reject or change.')
    term = (args.term or '').strip()
    if decision == 'Change' and not term:
        raise Stop('Change needs the replacement term, for example: decide "Volume (L)" change samp_vol_we_dna_ext')
    choices = choices_for(w)
    row = None
    for r in range(2, ws.max_row + 1):
        if str(ws.cell(r, at['Input term'] + 1).value or '').strip() == args.column.strip():
            row = r
            break
    if row is None:
        names = [str(ws.cell(r, at['Input term'] + 1).value or '') for r in range(2, ws.max_row + 1)]
        near = difflib.get_close_matches(args.column, names, n=3)
        raise Stop(f"No column '{args.column}' in the review sheet." + (f" Did you mean: {', '.join(near)}?" if near else ''))
    replacement = None
    if decision == 'Change':
        opts = choices.get(args.column.strip(), {}).get('all', [])
        exact = [o for o in opts if o == term]
        bare = [o for o in opts if re.sub(r'\s*\(.*\)\s*$', '', o).strip() == term]
        if exact:
            replacement = exact[0]
        elif bare:
            replacement = bare[0]
        else:
            terms = checklist_terms()
            if term in terms:
                replacement = term
            else:
                near = difflib.get_close_matches(term, list(terms) + opts, n=5)
                raise Stop(f"'{term}' is not a FAIRe term or one of this column's choices."
                           + (f" Close: {', '.join(near)}." if near else '')
                           + ' To keep the column under its own name, use reject.')
    ws.cell(row, at["Reviewer's decision"] + 1).value = decision
    ws.cell(row, at['Replacement FAIRe term'] + 1).value = replacement
    if args.by_model and "Mapper's call" in at:
        ws.cell(row, at["Mapper's call"] + 1).value = 'review (chosen by a model, confirmed by the reviewer)'
    _, reviewed = review_paths(w)
    wb.save(reviewed)
    with open(w / 'map' / 'decisions.tsv', 'a', encoding='utf-8', newline='') as f:
        f.write('\t'.join([dt.datetime.now().isoformat(timespec='seconds'), args.column, decision, replacement or '',
                           'model suggestion confirmed by the researcher' if args.by_model else 'researcher']) + '\n')
    log_event(w, 'decide', f'{args.column}: {decision} {replacement or ""}')
    left = sum(1 for r in review_rows(w) if not r.get("Reviewer's decision"))
    proposed = ws.cell(row, at['Proposed FAIRe term'] + 1).value or ''
    what = {'Accept': f'accepted {proposed}' if proposed else 'accepted',
            'Reject': f"rejected; kept as its own term '{args.column}'",
            'Change': f'changed to {replacement}'}[decision]
    print(f"{args.column}: {what}. {left} column(s) still to decide.")
    return 0


def cmd_load_review(args):
    """Take back a review sheet the researcher filled in themselves (in Excel), in place of the working one."""
    w = work_dir(args)
    load_state(w)
    src = Path(args.file).resolve()
    if not src.exists():
        raise Stop(f'No such file: {args.file}')
    sys.path.insert(0, str(MAPPER))
    if args.kind == 'columns':
        import faire_mapper_review as fr   # noqa: E402
        if not fr.is_review_sheet(src):
            raise Stop(f'{src.name} is not a review sheet from map (it needs the Review and Crosswalk (details) sheets).')
        target = review_paths(w)[1]
    else:
        import faire_method_details as fmd   # noqa: E402
        if not fmd.is_review_sheet(src):
            raise Stop(f'{src.name} is not a review sheet from methods (it needs the Method details sheet).')
        target = method_paths(w)[1]
    if not target.parent.exists():
        raise Stop('Run map (or methods) first, so the session knows the table (or the methods) this sheet reviews.')
    if args.kind == 'columns':
        from openpyxl import load_workbook
        ws = load_workbook(src, read_only=True)['Review']
        names = {str(r[0]).strip() for r in ws.iter_rows(min_row=2, values_only=True) if r and r[0]}
        cols = set(table_examples(load_state(w)))
        extra, missing = sorted(names - cols), sorted(cols - names)
        if cols and (extra or missing):
            msg = (f"The returned sheet does not match the table's columns. In the sheet only: {', '.join(extra) or 'none'}; "
                   f"in the table only: {', '.join(missing) or 'none'}.")
            if not args.force:
                raise Stop(msg + ' Check it is the review of this table (or run map again with --earlier_review '
                                 'FILE to carry its decisions over); --force loads it anyway.')
            print('Warning: ' + msg)
    shutil.copy(src, target)
    log_event(w, 'load-review', f'{args.kind}: {src.name}')
    print(f'Loaded {src.name} as the {"column" if args.kind == "columns" else "method details"} review.')
    return cmd_items(argparse.Namespace(work=args.work, all=False)) if args.kind == 'columns' else \
        cmd_method_items(argparse.Namespace(work=args.work, all=False))


# ---------------------------------------------------------------- corrections to the sample table

def _where(spec):
    """'Sample ID=8B' (exact) or 'Sample ID~^Filtration' (regular expression) into (column, test)."""
    m = re.match(r'^(.+?)\s*(=|~)\s*(.*)$', spec or '')
    if not m:
        raise Stop(f"--where needs COLUMN=VALUE or COLUMN~PATTERN; got '{spec}'")
    col, op, val = m.group(1).strip(), m.group(2), m.group(3)
    if op == '=':
        return col, lambda v: str('' if v is None else v).strip() == val.strip()
    rx = re.compile(val, re.I)
    return col, lambda v: bool(rx.search(str('' if v is None else v)))


class EditableTable:
    """The sample table as cells, kept as Excel cells for .xlsx (dates and times stay as they are)."""

    def __init__(self, path, sheet, header_row):
        self.path, self.header_row = Path(path), int(header_row or 1)
        self.excel = self.path.suffix.lower() in ('.xlsx', '.xlsm')
        if self.excel:
            from openpyxl import load_workbook
            self.wb = load_workbook(self.path)
            self.ws = self.wb[sheet] if sheet else self.wb.worksheets[0]
            self.head = [str(c.value).strip() if c.value is not None else '' for c in self.ws[self.header_row]]
        else:
            raw = self.path.read_bytes()
            for enc in ('utf-8-sig', 'cp1252', 'latin-1'):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            self.enc = 'utf-8'
            lines = text.splitlines()
            self.pre = lines[:self.header_row - 1]
            sample = '\n'.join(lines[self.header_row - 1:self.header_row + 5])
            self.delim = max(['\t', ',', ';', '|'], key=lambda d: sample.count(d))
            rows = list(csv.reader(lines[self.header_row - 1:], delimiter=self.delim))
            self.head = [h.strip() for h in rows[0]]
            self.rows = [r + [''] * (len(self.head) - len(r)) for r in rows[1:] if any(c.strip() for c in r)]

    def col(self, name):
        if name not in self.head:
            near = difflib.get_close_matches(name, self.head, n=3)
            raise Stop(f"No column '{name}' in the table." + (f" Did you mean: {', '.join(near)}?" if near else ''))
        return self.head.index(name)

    def n(self):
        if self.excel:
            last = self.header_row
            for r in range(self.header_row + 1, self.ws.max_row + 1):
                if any(self.ws.cell(r, c + 1).value not in (None, '') for c in range(len(self.head))):
                    last = r
            return last - self.header_row
        return len(self.rows)

    def get(self, i, j):
        return self.ws.cell(self.header_row + 1 + i, j + 1).value if self.excel else self.rows[i][j]

    def set(self, i, j, v):
        if self.excel:
            self.ws.cell(self.header_row + 1 + i, j + 1).value = v
        else:
            self.rows[i][j] = '' if v is None else str(v)

    def add_column(self, name):
        if name in self.head:
            raise Stop(f"The table already has a column '{name}'.")
        self.head.append(name)
        if self.excel:
            self.ws.cell(self.header_row, len(self.head)).value = name
        else:
            for r in self.rows:
                r.append('')
        return len(self.head) - 1

    def drop_column(self, name):
        j = self.col(name)
        if self.excel:
            self.ws.delete_cols(j + 1)
        else:
            for r in self.rows:
                del r[j]
        del self.head[j]

    def add_row(self):
        if self.excel:
            return self.n()
        self.rows.append([''] * len(self.head))
        return len(self.rows) - 1

    def save(self, out):
        if self.excel:
            self.wb.save(out)
        else:
            with open(out, 'w', encoding='utf-8', newline='') as f:
                for ln in self.pre:
                    f.write(ln + '\n')
                wr = csv.writer(f, delimiter=self.delim, lineterminator='\n')
                wr.writerow(self.head)
                wr.writerows(self.rows)


def cmd_table(args):
    w = work_dir(args)
    s = load_state(w)
    other = None
    if args.file:   # another table, such as qPCR results: corrected in its own copy
        orig = str(Path(args.file).resolve())
        corrected = s.setdefault('corrected', {})
        current = corrected.get(orig, orig)
        if not Path(current).exists():
            raise Stop(f'No such file: {args.file}')
        t = dict(path=current, sheet=args.sheet or '', header_row=args.header_row or 1, original=orig)
        other = orig
    else:
        t = s.get('table')
        if not t:
            raise Stop('Map the sample table first (corrections are made to a copy of it), or give --file for '
                       'another table.')
    if args.action in ('set', 'add-column', 'drop-column', 'rename-column') and not args.column:
        raise Stop(f'{args.action} needs the column name.')
    tab = EditableTable(t['path'], t.get('sheet'), t.get('header_row', 1))
    n = tab.n()
    rows = list(range(n))
    if args.where:
        c, test = _where(args.where)
        j = tab.col(c)
        rows = [i for i in rows if test(tab.get(i, j))]
        if args.nth:
            if args.nth > len(rows):
                raise Stop(f'Only {len(rows)} row(s) match {args.where}.')
            rows = [rows[args.nth - 1]]
        if not rows:
            raise Stop(f'No row matches {args.where}.')

    def value_for(i):
        if args.template is None:
            return args.value
        vals = {h: ('' if tab.get(i, jj) is None else str(tab.get(i, jj)).strip()) for jj, h in enumerate(tab.head)}
        try:
            return args.template.format_map(vals)
        except KeyError as e:
            raise Stop(f'--template names a column the table does not have: {e}')

    if args.action in ('set', 'add-column') and args.value is not None and args.template is not None:
        raise Stop('Give --value or --template, not both.')
    what = ''
    where = f' where {args.where}' + (f' (match {args.nth})' if args.nth else '') if args.where else ' (every row)'
    if args.action == 'set':
        j = tab.col(args.column)
        if not args.where and not args.all:
            raise Stop('set needs --where (or --all), so only the intended rows change.')
        for i in rows:
            tab.set(i, j, value_for(i))
        shown = args.template if args.template is not None else args.value
        what = f"{args.column} = '{shown}' in {len(rows)} row(s){where}"
    elif args.action == 'add-column':
        j = tab.add_column(args.column)
        for i in range(n):
            v = value_for(i) if (args.value or args.template) else None
            tab.set(i, j, v if v else None)
        shown = args.template if args.template is not None else args.value
        what = f"new column '{args.column}'" + (f", '{shown}' in every row" if shown else ', empty')
    elif args.action == 'drop-column':
        tab.drop_column(args.column)
        what = f"column '{args.column}' left out"
    elif args.action == 'rename-column':
        j = tab.col(args.column)
        if not args.value or args.value in tab.head:
            raise Stop('rename-column needs --value with a new name not already used.')
        tab.head[j] = args.value
        if tab.excel:
            tab.ws.cell(tab.header_row, j + 1).value = args.value
        what = f"column '{args.column}' renamed '{args.value}'"
    elif args.action == 'add-row':
        i = tab.add_row()
        given = []
        for kv in args.cells or []:
            if '=' not in kv:
                raise Stop(f"add-row takes COLUMN=VALUE; got '{kv}'")
            k, v = kv.split('=', 1)
            tab.set(i, tab.col(k.strip()), v)
            given.append(f'{k.strip()}={v}')
        what = 'new row: ' + ', '.join(given)
    src = Path(t.get('original') or t['path'])
    out = w / 'table' / f'{src.stem}_corrected{src.suffix if src.suffix.lower() != ".xls" else ".xlsx"}'
    out.parent.mkdir(parents=True, exist_ok=True)
    tab.save(out)
    if other:
        s['corrected'][other] = str(out)
    else:
        t.setdefault('original', t['path'])
        t['path'] = str(out)
        s['table'] = t
    save_state(w, s)
    with open(w / 'table' / 'corrections.tsv', 'a', encoding='utf-8', newline='') as f:
        f.write(f"{dt.datetime.now().isoformat(timespec='seconds')}\t{src.name}: {what}\t{args.reason or ''}\n")
    log_event(w, 'table', f'{src.name}: {what}')
    print(f'{src.name}: {what}. Saved as {out} (the original file is unchanged).')
    print('Give this corrected copy to build.' if other else 'When the corrections are done, run: map --again')
    return 0


def cmd_new_table(args):
    """Start a sample table from the sample columns of an OTU table, for studies that published none."""
    w = work_dir(args)
    s = load_state(w)
    sys.path.insert(0, str(MAPPER))
    import faire_mapper as fm   # noqa: E402
    import pandas as pd
    src = Path(args.otu).resolve()
    df = fm.read_table(str(src), args.sheet or None, args.header_row)
    skip = set(split_list(args.exclude))
    if args.columns:
        cols = split_list(args.columns)
        bad = [c for c in cols if c not in df.columns]
        if bad:
            raise Stop(f"Not columns of {src.name}: {', '.join(bad)}")
    else:
        cols = []
        for c in df.columns:
            if str(c) in skip:
                continue
            if re.search(r'prob|conf|score|length|^len|taxid|identity|pident|evalue|bitscore|rank', str(c), re.I):
                continue
            v = pd.to_numeric(df[c], errors='coerce')
            if v.notna().mean() > 0.95 and (v.dropna() % 1 == 0).all() and (v.dropna() >= 0).all():
                cols.append(str(c))
        zero = [c for c in cols if pd.to_numeric(df[c], errors='coerce').fillna(0).sum() == 0]
        if zero:
            print(f"Samples with no reads (kept; check with the researcher): {', '.join(zero)}")
    if not cols:
        raise Stop('No columns of read counts found. Name the sample columns with --columns.')
    rows = [{'Sample ID': c} for c in cols]
    out = pd.DataFrame(rows)
    if args.split:
        rx = re.compile(args.split)
        if not rx.groupindex:
            raise Stop("--split needs named groups, such as '(?P<Site>[A-Z]+)-(?P<Replicate>\\d+)'")
        parts = [rx.fullmatch(c) for c in cols]
        missed = [c for c, m in zip(cols, parts) if not m]
        for g in rx.groupindex:
            out[g] = [m.group(g) if m else '' for m in parts]
        if missed:
            print(f"Names that do not fit --split (left blank): {', '.join(missed[:10])}")
    if args.join:
        left, right = (args.on or '').split('=', 1) if '=' in (args.on or '') else (None, None)
        if not left:
            raise Stop("--join needs --on 'COLUMN_HERE=COLUMN_THERE', such as 'Site=Code'.")
        other = fm.read_table(str(Path(args.join).resolve()))
        if right not in other.columns or left not in out.columns:
            raise Stop(f"--on: '{left}' must be a column made here and '{right}' a column of {Path(args.join).name}.")
        other = other.astype(str)
        tag = f' ({Path(args.join).stem})'
        out = out.merge(other, how='left', left_on=left, right_on=right, suffixes=('', tag))
        key = right if right in out.columns and right != left else right + tag if right == left else None
        nomatch = out[out[key].isna()]['Sample ID'].tolist() if key and key in out.columns else []
        if key and key in out.columns:
            out = out.drop(columns=[key])
        if nomatch:
            print(f"No match in {Path(args.join).name} for: {', '.join(nomatch[:10])}")
    d = w / 'table'
    d.mkdir(parents=True, exist_ok=True)
    path = d / f'samples_from_{src.stem}.csv'
    out.to_csv(path, index=False)
    s['table'] = dict(path=str(path), sheet='', header_row=1, name=path.name, original=str(path))
    save_state(w, s)
    with open(d / 'corrections.tsv', 'a', encoding='utf-8', newline='') as f:
        f.write(f"{dt.datetime.now().isoformat(timespec='seconds')}\t{path.name}: made from the {len(cols)} sample "
                f"columns of {src.name}" + (f', split by {args.split}' if args.split else '')
                + (f', joined to {Path(args.join).name} on {args.on}' if args.join else '') + '\t\n')
    log_event(w, 'new-table', f'{path.name} from {src.name}')
    print(f'{len(cols)} samples from the columns of {src.name}: {", ".join(cols[:8])}{" ..." if len(cols) > 8 else ""}')
    print(f'Columns: {", ".join(out.columns)}. Saved as {path}.')
    print('Check the sample list with the researcher, add what they know (dates, controls, depth ...) with '
          'table add-column / set, then run map with no table argument.')
    return 0


# ---------------------------------------------------------------- methods and primers

def method_paths(w):
    return w / 'methods' / 'method_details_review_sheet.xlsx', w / 'methods' / 'method_details_reviewed.xlsx'


def cmd_methods(args):
    w = work_dir(args)
    s = load_state(w)
    d = w / 'methods'
    if d.exists() and (d / 'method_details_reviewed.xlsx').exists() and not args.again:
        raise Stop('The methods have been read already and a review is in progress. Run methods --again to read '
                   'them afresh (the decisions made so far on method values are then lost).')
    d.mkdir(parents=True, exist_ok=True)
    texts = [Path(t).resolve() for t in args.texts]
    for t in texts:
        if not t.exists():
            raise Stop(f'No such file: {t}')
    targs = [*texts]
    for t in texts:
        targs += ['--label', t.name]
    targs += ['--checklist', CHECKLIST, '--assay_type', s.get('assay_type', 'metabarcoding')]
    if s.get('assays'):
        targs += ['--assay_names', ','.join(s['assays'])]
    if args.whole_text:
        targs += ['--whole_text']
    targs += ['-o', d / 'method_details.tsv', '--review_sheet', d / 'method_details_review_sheet.xlsx']
    _, out = run_tool(MAPPER / 'faire_method_details.py', targs, d)
    shutil.copy(d / 'method_details_review_sheet.xlsx', d / 'method_details_reviewed.xlsx')
    for line in out.splitlines():
        if line.startswith('WARNING'):
            print(line)
    s['methods'] = [str(t) for t in texts]
    save_state(w, s)
    log_event(w, 'methods', ', '.join(t.name for t in texts))
    show_methods(w, only_open=True)
    if s.get('assay_type') == 'metabarcoding' or args.primers:
        pargs = ['text', *texts, '-o', d / 'primer_candidates.tsv']
        code, pout = run_tool(MAPPER / 'faire_primers.py', pargs, d, quiet=True)
        if code == 0:
            show_primers(w)
        else:
            print('\nFind primers stopped: ' + short(pout.strip().splitlines()[-1] if pout.strip() else '', 300))
    return 0


def method_rows(w, path=None):
    from openpyxl import load_workbook
    _, reviewed = method_paths(w)
    path = path or reviewed
    if not path.exists():
        raise Stop('The methods have not been read yet. Run methods first.')
    ws = load_workbook(path)['Method details']
    rows = list(ws.iter_rows(values_only=True))
    head = [str(h or '').strip() for h in rows[0]]
    out, part = [], ''
    for i, r in enumerate(rows[1:], 2):
        rec = {h: ('' if j >= len(r) or r[j] is None else str(r[j]).strip()) for j, h in enumerate(head) if h}
        if rec.get('Section') and not rec.get('FAIRe term'):
            low = rec['Section'].lower()
            part = 'reliable' if low.startswith('found reliably') else 'check' if low.startswith('also found') else \
                'not found' if 'not found' in low else part
            continue
        if not rec.get('FAIRe term'):
            continue
        rec['_row'], rec['_part'] = i, part
        out.append(rec)
    return out


def show_methods(w, only_open=True):
    rows = method_rows(w)
    found = [r for r in rows if r['_part'] in ('reliable', 'check')]
    for part, title in (('reliable', 'Found reliably (check each against its sentence; can be confirmed together):'),
                        ('check', 'Also found, to check one at a time:')):
        sel = [r for r in found if r['_part'] == part and (not only_open or not r.get("Reviewer's decision"))]
        if not sel:
            continue
        print('\n' + title)
        for r in sel:
            assay = f" [{r['Assay']}]" if r.get('Assay') else ''
            dec = f"   decision: {r[DEC]} {r.get('Your value', '')}" if r.get("Reviewer's decision") else ''
            print(f"  - row {r['_row']}: {r['FAIRe term']}{assay} = {short(r['Proposed value'], 120)} "
                  f"({r.get('FAIRe level', '')}){dec}")
            print('      from: "' + short(r.get('From the methods'), 260) + '"')
            if r.get('Note'):
                print(f"      note: {short(r['Note'], 200)}")
    nf = [r for r in rows if r['_part'] == 'not found']
    mand = [r['FAIRe term'] for r in nf if r.get('FAIRe level') == 'Mandatory' and not r.get('Your value')]
    n_open = sum(1 for r in found if not r.get("Reviewer's decision"))
    print(f"\n{len(found)} values found, {n_open} still to decide; {len(nf)} method terms not found"
          + (f" (mandatory among them: {', '.join(mand)})" if mand else '') + '.')


def show_primers(w):
    f = w / 'methods' / 'primer_candidates.tsv'
    if not f.exists():
        return
    rows = read_tsv(f)
    if not rows:
        print('\nPrimers: none found in the methods. Ask for the primer names or a citation, then use primers-use '
              'after a lookup (python faire_session.py primers-lookup NAME).')
        return
    order = ['exact match', 'close match', 'as written', 'possible', 'less likely']
    rows.sort(key=lambda r: next((i for i, o in enumerate(order) if r.get('how_likely', '').startswith(o)), 9))
    print('\nPrimer pairs (most likely first; use primers-use PAIR_ID --assay NAME for the ones the study used):')
    for r in rows[:10]:
        print(f"  - {r['primer_pair_id']}  {r.get('assay_name') or ''}: {r.get('pcr_primer_name_forward')} "
              f"{r.get('pcr_primer_forward')} / {r.get('pcr_primer_name_reverse')} {r.get('pcr_primer_reverse')}"
              f"  [{r.get('target_gene', '')}; {short(r.get('how_likely'), 60)}; found by {short(r.get('matched_by'), 40)}]")
    if len(rows) > 10:
        print(f'  ... and {len(rows) - 10} less likely candidates in methods/primer_candidates.tsv')


def cmd_method_items(args):
    w = work_dir(args)
    load_state(w)
    show_methods(w, only_open=not args.all)
    show_primers(w)
    return 0


def cmd_method_decide(args):
    from openpyxl import load_workbook
    w = work_dir(args)
    load_state(w)
    _, reviewed = method_paths(w)
    rows = method_rows(w)
    decision = args.decision.capitalize()
    if decision not in DECISIONS:
        raise Stop('The decision is accept, reject or change.')
    if args.all_reliable:
        if decision != 'Accept':
            raise Stop('--all-reliable is only for accepting the reliable values the researcher has checked.')
        targets = [r for r in rows if r['_part'] == 'reliable' and not r.get("Reviewer's decision")]
        if args.except_rows:
            skip = {int(x) for x in split_list(args.except_rows)}
            targets = [r for r in targets if r['_row'] not in skip]
    else:
        if args.row:
            targets = [r for r in rows if r['_row'] == args.row]
        else:
            if not args.term:
                raise Stop('Give the FAIRe term (or --row N from method-items).')
            targets = [r for r in rows if r['FAIRe term'] == args.term and (not args.assay or r.get('Assay') == args.assay)
                       and r['_part'] in ('reliable', 'check')]
            if len(targets) > 1:
                raise Stop(f"{args.term} has {len(targets)} values: give --row with one of "
                           + ', '.join(str(r['_row']) for r in targets) + ' (rows from method-items).')
        if not targets:
            raise Stop('No such method value. Run method-items to see the rows. To give a value for a term that was '
                       'not found, use set TERM VALUE.')
    if decision == 'Change' and not args.value:
        raise Stop('Change needs the right value.')
    wb = load_workbook(reviewed)
    ws = wb['Method details']
    head = [str(c.value or '').strip() for c in ws[1]]
    cd, cv, ca = head.index("Reviewer's decision") + 1, head.index('Your value') + 1, head.index('Assay') + 1
    for r in targets:
        ws.cell(r['_row'], cd).value = decision
        if decision == 'Change':
            ws.cell(r['_row'], cv).value = args.value
        if args.assay is not None and args.set_assay:
            ws.cell(r['_row'], ca).value = args.assay
    wb.save(reviewed)
    for r in targets:
        log_event(w, 'method-decide', f"row {r['_row']} {r['FAIRe term']}: {decision} {args.value or ''}")
    left = sum(1 for r in method_rows(w) if r['_part'] in ('reliable', 'check') and not r.get("Reviewer's decision"))
    names = ', '.join(r['FAIRe term'] for r in targets)
    print(f"{decision}: {names}. {left} method value(s) still to decide.")
    return 0


def values_path(w):
    return w / 'values.tsv'


def read_values(w):
    p = values_path(w)
    return read_tsv(p) if p.exists() else []


def write_values(w, rows):
    with open(values_path(w), 'w', encoding='utf-8', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=VALUES_HEAD, delimiter='\t', extrasaction='ignore', lineterminator='\n')
        wr.writeheader()
        for r in rows:
            wr.writerow({k: r.get(k, '') for k in VALUES_HEAD})


def put_value(w, term, value, assay, source):
    rows = [r for r in read_values(w) if not (r['term'] == term and (r.get('assay') or '') == (assay or ''))]
    rows.append(dict(term=term, value=value, assay=assay or '', status='confirmed', source=source))
    write_values(w, rows)


def cmd_primers_use(args):
    w = work_dir(args)
    s = load_state(w)
    f = w / 'methods' / 'primer_candidates.tsv'
    rows = read_tsv(f) if f.exists() else []
    if args.lookup_file:
        rows += read_tsv(Path(args.lookup_file))
    hit = [r for r in rows if r.get('primer_pair_id') == args.pair_id]
    if not hit:
        raise Stop(f'No primer pair {args.pair_id} among the candidates. Run method-items (or primers-lookup) to see them.')
    r = hit[0]
    if s.get('assays') and args.assay not in s['assays']:
        raise Stop(f"'{args.assay}' is not one of the study's assays ({', '.join(s['assays'])}). Add it with start --assays.")
    src = f"primer reference table ({short(r.get('source'), 80)}), pair {args.pair_id}, chosen by the researcher"
    keys = ['pcr_primer_name_forward', 'pcr_primer_forward', 'pcr_primer_reference_forward',
            'pcr_primer_name_reverse', 'pcr_primer_reverse', 'pcr_primer_reference_reverse', 'target_gene',
            'target_subfragment']
    if args.with_target:
        keys += ['targetTaxonomicAssay']
    done = []
    for k in keys:
        v = (r.get(k) or '').strip()
        if v:
            put_value(w, k, v, args.assay if len(s.get('assays', [])) > 1 or args.assay else '', src)
            done.append(f'{k} = {short(v, 60)}')
    log_event(w, 'primers-use', f'{args.pair_id} for {args.assay}')
    print(f'For assay {args.assay}:\n  ' + '\n  '.join(done))
    print('Annealing temperature, cycles and amplicon size come from the study\'s own methods, not the reference table.')
    return 0


def cmd_primers_lookup(args):
    w = work_dir(args)
    load_state(w)
    d = w / 'methods'
    d.mkdir(parents=True, exist_ok=True)
    out = d / 'primer_lookup.tsv'
    pargs = ['lookup', *args.names] + (['--gene', args.gene] if args.gene else []) + ['-o', out]
    run_tool(MAPPER / 'faire_primers.py', pargs, d)
    rows = read_tsv(out)
    if not rows:
        print('No pairs found for those names. Ask for the sequences as written in the paper or protocol, and record '
              'them with set (pcr_primer_forward, pcr_primer_reverse and their names, for the assay).')
        return 0
    for r in rows[:12]:
        print(f"  - {r['primer_pair_id']}  {r.get('assay_name') or ''}: {r.get('pcr_primer_name_forward')} "
              f"{r.get('pcr_primer_forward')} / {r.get('pcr_primer_name_reverse')} {r.get('pcr_primer_reverse')} "
              f"[{r.get('target_gene', '')}; {short(r.get('bibliographicCitation') or r.get('pcr_primer_reference_forward'), 80)}]")
    print(f'Use one with: primers-use PAIR_ID --assay NAME --lookup-file {out}')
    return 0


# ---------------------------------------------------------------- values the researcher gives

def _norm_value(v):
    """A value as text for comparing: numbers as numbers, text without case, spaces or punctuation."""
    v = str(v or '').strip()
    try:
        f = float(v)
        return str(int(f)) if f == int(f) else str(f)
    except ValueError:
        return re.sub(r'[\s.,;:()]+', ' ', v.lower()).strip()


def _assay_fits(row_assay, assay):
    """A method value with no assay fits every assay; one named for an assay fits it and its variants
    (Olson fits OlsonViiA7)."""
    row_assay = (row_assay or '').strip().lower()
    return not row_assay or not assay or row_assay in assay.lower() or assay.lower() in row_assay


def methods_conflicts(w, s, term, value, assay):
    """Where the researcher's files give this term a value and none of them is the value given:
    [(value in the files, sentence)]. Nothing when the value given matches any of them."""
    mine = _norm_value(value)
    found = []   # (value as written, value for comparing, sentence)
    try:
        for r in method_rows(w):
            if r['FAIRe term'] == term and _assay_fits(r.get('Assay'), assay) and r.get('Proposed value'):
                found.append((r['Proposed value'], _norm_value(r['Proposed value']), r.get('From the methods', '')))
    except Stop:
        pass
    texts = []
    if term in ('ampliconSize', 'pcr_primer_forward', 'pcr_primer_reverse', 'probe_seq') and s.get('methods'):
        sys.path.insert(0, str(MAPPER))
        import faire_mapper_text as ft   # noqa: E402
        for m in s['methods']:
            try:
                texts.append(ft.read_text(m))
            except Exception:
                continue
    if term == 'ampliconSize':
        sentences = [x.strip() for t in texts for x in re.split(r'(?<=[.!?])\s+(?=[A-Z])', re.sub(r'\s+', ' ', t))]
        for sen in sentences:
            for size in dict.fromkeys(re.findall(r'(\d+)\s*-?\s*(?:bp|base[- ]pairs?)\b', sen, re.I)):
                found.append((size + ' bp', size, sen))
        mine = set(re.findall(r'\d+', str(value)))
        if not found or any(f[1] in mine for f in found):
            return []
    elif term in ('pcr_primer_forward', 'pcr_primer_reverse', 'probe_seq'):
        seq = re.sub(r'[^A-Za-z]', '', str(value)).upper()
        joined = [re.sub(r"(?<=[A-Za-z])[ -](?=[A-Za-z])|5'-|-3'", '', t) for t in texts]
        seqs = {x.upper() for t in joined
                for x in re.findall(r'(?<![A-Za-z])[ACGTRYSWKMBDHVNIacgtryswkmbdhvni]{15,}(?![A-Za-z])', t)}
        if seqs and seq and seq not in seqs and not any(f[1] == mine for f in found):
            near = difflib.get_close_matches(seq, sorted(seqs), n=1, cutoff=0.6)
            return [(near[0] if near else ', '.join(sorted(seqs)[:4]),
                     'the closest sequence written in the methods' if near else 'the sequences written in the methods')]
        return []
    if not found or any(f[1] == mine for f in found):
        return []
    out = []
    for v, _, sen in found:
        if (v, sen) not in out:
            out.append((v, sen))
    return out[:3]


# ---------------------------------------------------------------- ENVO

ENVO_TABLE = SKILL / 'assets' / 'envo-terms.tsv'
# Which ENVO branches suit each habitat term (MIxS and FAIRe guidance)
ENVO_FITS = {'env_broad_scale': ('biome',),
             'env_local_scale': ('astronomical body part', 'construction', 'environmental system',
                                 'other material entity'),
             'env_medium': ('environmental material',)}
_ENVO = {}


def envo_terms():
    """The bundled ENVO release: {id: row}, the release name, and the narrower terms of each label."""
    if not _ENVO:
        if not ENVO_TABLE.exists():
            raise Stop('assets/envo-terms.tsv is missing: this copy of the skill is incomplete.')
        lines = ENVO_TABLE.read_text(encoding='utf-8').splitlines()
        _ENVO['release'] = re.sub(r'^# (ENVO [^;]+);.*', r'\1', lines[0]).replace('releases/', '')
        rows = list(csv.DictReader(lines[1:], delimiter='\t', quoting=csv.QUOTE_NONE))
        _ENVO['rows'] = {r['id']: r for r in rows}
        kids = {}
        for r in rows:
            for p in filter(None, r['parents'].split('; ')):
                kids.setdefault(p, []).append(r['label'])
        _ENVO['kids'] = kids
    return _ENVO


def envo_fits(branch, term):
    if term not in ENVO_FITS:
        return ''
    return 'fits' if any(b in branch for b in ENVO_FITS[term]) else 'not usually for'


def envo_words(x):
    return re.findall(r'[a-z0-9]+', x.lower())


def envo_search(queries, term=None, limit=15):
    """Rank ENVO classes for one or more wordings: exact label or synonym first, then the wording as a
    phrase, then all its words, in the label, synonyms or definition. Classes that suit the term rank higher."""
    e = envo_terms()
    best = {}
    for q in queries:
        qw = envo_words(q)
        if not qw:
            continue
        phrase = ' '.join(qw)
        for r in e['rows'].values():
            lab = ' '.join(envo_words(r['label']))
            syns = [' '.join(envo_words(x)) for x in r['synonyms'].split(' | ') if x]
            text = set(envo_words(r['label'] + ' ' + r['synonyms']))
            if lab == phrase:
                sc = 100
            elif phrase in syns:
                sc = 90
            elif re.search(rf'\b{re.escape(phrase)}\b', lab):
                sc = 70
            elif any(re.search(rf'\b{re.escape(phrase)}\b', x) for x in syns):
                sc = 60
            elif set(qw) <= set(lab.split()):
                sc = 50
            elif set(qw) <= text:
                sc = 40
            elif set(qw) <= text | set(envo_words(r['definition'])):
                sc = 15
            else:
                continue
            sc -= min(len(lab.split()) - len(qw), 8)  # nearer wordings first
            if term and envo_fits(r['branch'], term) == 'fits':
                sc += 12
            elif term and 'not for' in r['branch']:
                sc -= 30
            if sc > best.get(r['id'], (-99,))[0]:
                best[r['id']] = (sc, q)
    order = sorted(best, key=lambda i: (-best[i][0], e['rows'][i]['label']))
    return [(e['rows'][i], best[i][1]) for i in order[:limit]], len(order)


def envo_print(r, term=None, full=False):
    e = envo_terms()
    fit = envo_fits(r['branch'], term) if term else ''
    print(f"{r['id']}  {r['label']}   [{r['branch']}{'; ' + fit + ' ' + term if fit else ''}]")
    print(f"    is a: {r['parents'] or '-'}" + (f"; also called: {short(r['synonyms'], 150)}" if r['synonyms'] else ''))
    if r['definition']:
        print(f"    {short(r['definition'], 400 if full else 200)}")
    kids = sorted(e['kids'].get(r['label'], []))
    if kids:
        print(f"    narrower: {', '.join(kids[:12 if full else 6])}" + (f' (and {len(kids) - (12 if full else 6)} more)'
                                                                       if len(kids) > (12 if full else 6) else ''))


def cmd_envo(args):
    e = envo_terms()
    if args.id:
        for i in args.id:
            i = i.strip().replace('_', ':')
            r = e['rows'].get(i)
            if r is None:
                print(f'{i}: not a current ENVO class in {e["release"]} (obsolete, mistyped, or not ENVO).')
            else:
                envo_print(r, args.term, full=True)
        return 0
    if not args.query:
        raise Stop('Give one or more wordings to search for, such as: envo dust "house dust" --term env_medium')
    found, n = envo_search(args.query, args.term, args.limit)
    print(f'{e["release"]} (bundled): {n} class(es) match ' + ', '.join(f'"{q}"' for q in args.query)
          + (f'; ranked for {args.term}' if args.term else '') + '.')
    for r, _ in found:
        envo_print(r, args.term)
    if not found:
        print('Nothing matched. Try other wordings: a broader word, a synonym, the material or the place.')
    else:
        print('Show the researcher the closest few, with their definitions, and the narrower terms where one may '
              'fit better. envo --id ID shows a class in full.')
    return 0


def envo_check(term, value):
    """Check ENVO identifiers in a habitat value against the bundled ENVO. Returns (problems, notes)."""
    if term not in ENVO_FITS:
        return [], []
    e = envo_terms()
    problems, notes = [], []
    for part in [p.strip() for p in value.split('|') if p.strip()]:
        if part.lower().startswith(('not applicable', 'missing', 'not provided', 'not collected', 'restricted')):
            continue
        m = re.fullmatch(r'(.*?)\s*\[(ENVO[:_]\d{8})\]', part)
        if not m:
            notes.append(f"'{part}' has no ENVO identifier: find one with envo \"{part}\" --term {term}, or keep the "
                         f"label alone and say it needs its identifier.")
            continue
        label, i = m.group(1).strip(), m.group(2).replace('_', ':')
        r = e['rows'].get(i)
        if r is None:
            problems.append(f'{i} is not a current ENVO class in {e["release"]} (obsolete, mistyped or invented). '
                            f'Search with envo "{label}" --term {term}.')
            continue
        names = [r['label'].lower()] + [x.lower() for x in r['synonyms'].split(' | ') if x]
        if label.lower() != r['label'].lower():
            problems.append(f"{i} is '{r['label']}' in ENVO, not '{label}'"
                            + (' (a synonym; FAIRe takes the ENVO label)' if label.lower() in names else '')
                            + f". Use '{r['label']} [{i}]', or search again.")
        elif envo_fits(r['branch'], term) != 'fits':
            notes.append(f"'{r['label']}' is in ENVO's {r['branch']} branch, not usually used for {term} "
                         f"(which takes {' or '.join(ENVO_FITS[term])} classes). Confirm with the researcher.")
    return problems, notes


def cmd_set(args):
    w = work_dir(args)
    s = load_state(w)
    terms = checklist_terms()
    t = terms.get(args.term)
    if t is None:
        near = difflib.get_close_matches(args.term, list(terms), n=5)
        raise Stop(f"'{args.term}' is not a FAIRe term." + (f" Close: {', '.join(near)}." if near else ''))
    value = args.value.strip()
    notes = []
    if t.vocab and not any(v.lower().startswith('http') for v in t.vocab):
        parts = [p.strip() for p in value.split('|')]
        low = {v.lower(): v for v in t.vocab}
        fixed = [low.get(p.lower(), p) for p in parts]
        numeric_ok = 'numeric value' in [v.lower() for v in t.vocab]
        off = [p for p in fixed if p not in t.vocab and not p.lower().startswith('other')
               and not (numeric_ok and re.fullmatch(r'-?\d+(\.\d+)?', p))
               and not p.lower().startswith(('not applicable', 'missing', 'not provided', 'not collected', 'restricted'))]
        if off:
            if not args.force:
                import pandas as pd
                ck = pd.read_excel(CHECKLIST, sheet_name='checklist', dtype=str).fillna('')
                raw = ' '.join(ck.loc[ck['term_name'] == args.term, 'controlled_vocabulary_options'])
                other = "'other: <text>' where none fits, or " if 'other' in raw.lower() else ''
                raise Stop(f"'{', '.join(off)}' is not an allowed value of {args.term}. Allowed: "
                           f"{short(' | '.join(t.vocab), 400)}. Use {other}a FAIRe missing-value term "
                           f"(such as 'not applicable' or 'missing: not collected') if the value is not known.")
            notes.append('kept as given (--force), although it is not one of the allowed values.')
        value = ' | '.join(fixed)
    problems, envo_notes = envo_check(args.term, value)
    if problems and not args.force:
        raise Stop(' '.join(problems))
    notes += problems + envo_notes
    if args.assay and s.get('assays') and args.assay not in s['assays']:
        raise Stop(f"'{args.assay}' is not one of the study's assays ({', '.join(s['assays'])}).")
    put_value(w, args.term, value, args.assay or '', args.source or 'given by the researcher in conversation')
    log_event(w, 'set', f"{args.term}{' (' + args.assay + ')' if args.assay else ''} = {value}")
    print(f"{args.term}{' for ' + args.assay if args.assay else ''} = {value}  ({t.requirement or 'no level'}; "
          f"{'project' if t.level == 'project' else 'every sample, unless a column gives it'})")
    for n in notes:
        print('Check: ' + n)
    cq = confused_question(args.term)
    if cq:
        print(f'Commonly confused, so confirm with the researcher: {cq}')
    conflicts = methods_conflicts(w, s, args.term, value, args.assay or '')
    if conflicts:
        print('Differs from the methods, which give:')
        for theirs, sentence in conflicts:
            where = sentence if sentence.startswith('the ') else '"' + short(sentence, 300) + '"'
            print(f'  - {short(theirs, 120)}: {where}')
        print('Ask the researcher which is right. To keep the value given, nothing more is needed; to use the '
              'other, run set again.')
    return 0


def cmd_unset(args):
    w = work_dir(args)
    load_state(w)
    rows = read_values(w)
    keep = [r for r in rows if not (r['term'] == args.term and (args.assay is None or (r.get('assay') or '') == args.assay))]
    write_values(w, keep)
    print(f'Removed {len(rows) - len(keep)} value(s) for {args.term}.')
    return 0


# ---------------------------------------------------------------- gaps

def covered_terms(w):
    """Terms that have a value: mapped columns, accepted method values and the researcher's values."""
    got = {r['term'] for r in read_values(w) if r.get('value')}
    try:
        for r in method_rows(w):
            dec = r.get("Reviewer's decision", '').lower()
            if dec == 'accept' or (dec != 'reject' and r.get('Your value')):
                got.add(r['FAIRe term'])
    except Stop:
        pass
    try:
        for r in review_rows(w):
            dec = r.get("Reviewer's decision")
            if dec == 'Change':
                got.add(re.sub(r'\s*\(.*\)\s*$', '', str(r.get('Replacement FAIRe term'))).strip())
            elif dec == 'Accept' or (not dec and r.get("Mapper's call") == 'accept'):
                for t in str(r.get('Proposed FAIRe term') or '').split('+'):
                    got.add(re.sub(r'\s*\(.*\)\s*$', '', t).strip())
    except Stop:
        pass
    return got


def cmd_gaps(args):
    w = work_dir(args)
    s = load_state(w)
    f = w / 'map' / 'out' / 'missing_mandatory.tsv'
    if not f.exists():
        raise Stop('Run map first: the list of mandatory terms comes from mapping the sample table.')
    got = covered_terms(w)
    if s.get('project_id'):
        got.add('project_id')
    if s.get('assays'):
        got.add('assay_name')
    rows = [r for r in read_tsv(f) if r['term'] not in got]
    vals = {r['term']: r['value'] for r in read_values(w)}
    later = {'lib_id', 'seq_run_id', 'detected_notDetected'}
    def applies(r):
        cond = (r.get('condition') or '').lower()
        if 'positive control' in cond and vals.get('pos_cont_0_1') == '0':
            return False
        if 'negative control' in cond and 'samp_category = negative control' in cond and vals.get('neg_cont_0_1') == '0':
            return False
        return r['term'] not in later
    rows = [r for r in rows if applies(r)]
    if args.recommended:
        extra = recommended_gaps(w, s, got)
    if not rows:
        print('Every mandatory term the mapper listed has a value now (the build log gives the final word).')
    else:
        print(f'{len(rows)} mandatory term(s) still without a value:')
        for r in rows:
            cond = f" Only if: {short(r['condition'], 120)}." if r.get('condition') else ''
            ex = f" Example: {short(r['example'], 80)}." if r.get('example') else ''
            print(f"  - {r['term']} ({r['sheet'].split(';')[0]}): {short(r['description'], 260)}{cond}{ex}")
    if s.get('assay_type') == 'metabarcoding':
        print('\nThe sequencing run ID (seq_run_id) and library IDs (lib_id) come from the build options '
              '(--otu ... run=RUN_ID, or a library table), not from set.')
    else:
        print('\ndetected_notDetected comes from the qPCR or ddPCR results given to build (--amp), with the '
              'detection criteria; it is not set by hand.')
    if args.recommended:
        print(f'\n{len(extra)} highly recommended term(s) without a value. These are optional: offer only those '
              'that the methods, the sample table or the researcher can answer, as one checklist, and leave the rest.')
        section = None
        for t in extra:
            if t.section != section:
                section = t.section
                print(f'  {section or "Other"}:')
            print(f'    - {t.name}: {short(t.description, 160)}')
    return 0


# Highly recommended terms that only apply to some studies.
PROBE_TERMS = {'probeReporter', 'probeQuencher', 'probe_seq', 'probe_ref', 'probe_conc'}
PRECIP_TERMS = {'precip_chem_prep', 'precip_force_prep', 'precip_time_prep', 'precip_temp_prep'}
FILTER_TERMS = {'filter_passive_active_0_1', 'size_frac', 'filter_diameter', 'filter_material', 'filter_name'}


def known_values(w):
    """Values given with set, and method values accepted or changed."""
    vals = {r['term']: r['value'] for r in read_values(w) if r.get('value')}
    try:
        for r in method_rows(w):
            dec = r.get("Reviewer's decision", '').lower()
            v = r.get('Your value') or (r.get('Proposed value') if dec == 'accept' else '')
            if v and dec != 'reject':
                vals.setdefault(r['FAIRe term'], v)
    except Stop:
        pass
    return vals


def recommended_gaps(w, s, got):
    """The highly recommended terms still empty that can apply to this study, in checklist order."""
    vals = known_values(w)
    sys.path.insert(0, str(MAPPER))
    import faire_mapper as fm   # noqa: E402
    assay_type = s.get('assay_type')
    terms = fm.load_checklist(str(CHECKLIST), assay_type=assay_type,
                              sheets=('projectMetadata', 'sampleMetadata', 'experimentRunMetadata'))
    out = []
    for t in terms:
        if t.requirement.lower() != 'highly recommended' or t.name in got:
            continue
        if assay_type == 'metabarcoding' and t.name in PROBE_TERMS:
            continue
        if t.name in PRECIP_TERMS and got & FILTER_TERMS:
            continue   # the samples were filtered, so there was no precipitation step
        if t.name == 'screen_contam_method' and vals.get('screen_contam_0_1') == '0':
            continue
        out.append(t)
    return out


# ---------------------------------------------------------------- build

def log_sections(path):
    """The sections of apply mapping's log, by heading."""
    out, cur = {}, None
    if not Path(path).exists():
        return out
    for ln in Path(path).read_text(encoding='utf-8').splitlines():
        if ln.startswith('## '):
            cur = ln[3:].strip()
            out[cur] = []
        elif cur and ln.strip().startswith('- '):
            out[cur].append(ln.strip()[2:])
    return out


def parse_spec(items, kind, allowed, corrected=None):
    """--otu PATH key=value ... into (path, {key: value}). A file corrected with table --file is used as corrected."""
    path = Path(items[0]).resolve()
    if corrected and str(path) in corrected:
        print(f'Using the corrected copy of {path.name}.')
        path = Path(corrected[str(path)])
    if not path.exists():
        raise Stop(f'No such file for --{kind}: {items[0]}')
    opts = {}
    for it in items[1:]:
        if '=' not in it:
            raise Stop(f"--{kind} options are key=value (for example assay=MiFish); got '{it}'")
        k, v = it.split('=', 1)
        if k not in allowed:
            raise Stop(f"Unknown --{kind} option '{k}'. Options: {', '.join(allowed)}")
        opts[k] = v
    return path, opts


OTU_OPTS = ['assay', 'run', 'stage', 'sequences', 'taxa', 'taxa_sheet', 'layout', 'sheet', 'curated', 'lineage',
            'assay_column']
LIB_OPTS = ['assay', 'filter', 'run', 'sheet']
AMP_OPTS = ['assay_column', 'sheet']


def cmd_build(args):
    w = work_dir(args)
    s = load_state(w)
    if not s.get('table'):
        raise Stop('Run map on the sample table first.')
    if not s.get('project_id'):
        raise Stop('The project needs an ID first: start --project_id SomeName2025 (letters, digits, _ or -).')
    _, reviewed = review_paths(w)
    open_cols = [r['Input term'] for r in review_rows(w) if not r.get("Reviewer's decision")]
    d = w / 'build'
    d.mkdir(parents=True, exist_ok=True)
    t = s['table']
    targs = [t['path']] + (['--sheet', t['sheet']] if t.get('sheet') else []) + ['--header_row', t.get('header_row', 1),
             '--crosswalk', reviewed, '--checklist', CHECKLIST, '--template', TEMPLATE,
             '--assay_type', s.get('assay_type', 'metabarcoding'), '--project_id', s['project_id']]
    if s.get('sample_types'):
        targs += ['--sample_types', ','.join(s['sample_types'])]
    if s.get('assays'):
        targs += ['--assay_name', ','.join(s['assays'])]
    if s.get('country'):
        targs += ['--country', s['country']]
    if s.get('utc_offset'):
        targs += [f"--utc_offset={s['utc_offset']}"]
    targs += ['--date_order', s.get('date_order') or 'stop']
    if read_values(w):
        targs += ['--project_values', values_path(w)]
    _, md = method_paths(w)
    if md.exists():
        targs += ['--project_values', md]
    if args.include_review:
        targs += ['--include_review']
    if args.drop_unmapped:
        targs += ['--drop_unmapped']
    if args.req_lev:
        targs += ['--req_lev', args.req_lev]
    assays = s.get('assays') or []
    for items in args.otu or []:
        p, o = parse_spec(items, 'otu', OTU_OPTS, s.get('corrected'))
        if len(assays) > 1 and not o.get('assay') and not o.get('assay_column'):
            raise Stop(f'{p.name}: say which assay it is (assay=NAME), as the study has several ({", ".join(assays)}).')
        targs += ['--otu', p, '--otu_name', p.name, '--otu_sheet', o.get('sheet', ''),
                  '--otu_assay', o.get('assay', assays[0] if len(assays) == 1 else ''), '--otu_run', o.get('run', ''),
                  '--otu_assay_column', o.get('assay_column', ''), '--otu_curated_column', o.get('curated', ''),
                  '--otu_lineage', o.get('lineage', ''), '--otu_stage', o.get('stage', 'final'),
                  '--otu_layout', o.get('layout', 'detect'),
                  '--otu_sequences', str(Path(o['sequences']).resolve()) if o.get('sequences') else '',
                  '--otu_sequences_name', Path(o['sequences']).name if o.get('sequences') else '',
                  '--taxa', str(Path(o['taxa']).resolve()) if o.get('taxa') else '',
                  '--taxa_sheet', o.get('taxa_sheet', '')]
    for items in args.library or []:
        p, o = parse_spec(items, 'library', LIB_OPTS, s.get('corrected'))
        targs += ['--library', p, '--library_name', p.name, '--library_sheet', o.get('sheet', ''),
                  '--library_assay', o.get('assay', ''), '--library_filter', o.get('filter', ''),
                  '--library_run', o.get('run', '')]
    for items in args.amp or []:
        p, o = parse_spec(items, 'amp', AMP_OPTS, s.get('corrected'))
        targs += ['--amp', p, '--amp_name', p.name, '--amp_sheet', o.get('sheet', ''),
                  '--amp_assay_column', o.get('assay_column', '')]
    out_xlsx = d / f"{s['project_id']}_FAIRe.xlsx"
    targs += ['--table_name', t['name'], '--crosswalk_name', 'review sheet (reviewed in conversation)',
              '-o', out_xlsx, '--log', d / 'apply_mapping_log.txt']
    code, out = run_tool(MAPPER / 'faire_mapper_apply.py', targs, d, quiet=True)
    if code != 0 or not out_xlsx.exists():
        lines = [ln for ln in out.strip().splitlines() if ln.strip()]
        msg = '\n'.join(ln for ln in lines if 'ERROR' in ln or 'Stop' in ln or 'stop' in ln) or '\n'.join(lines[-12:])
        raise Stop('Apply mapping stopped:\n' + msg)
    s['workbook'] = str(out_xlsx)
    s['built'] = dt.datetime.now().isoformat(timespec='seconds')
    s.pop('checked', None)
    save_state(w, s)
    log_event(w, 'build', out_xlsx.name)
    print(f'Wrote {out_xlsx.name}.')
    if open_cols:
        print(f"Columns with no decision ({len(open_cols)}), applied as the mapper called them (matches for review "
              f"left out): {', '.join(open_cols)}")
    sec = log_sections(d / 'apply_mapping_log.txt')
    for title, label in (('Review', 'How the review was done'),
                         ('Commonly confused terms', 'Commonly confused terms: confirm each with the researcher'),
                         ('Warnings', 'Warnings'), ('Mandatory terms with no value', 'Mandatory terms with no value')):
        items = sec.get(title) or []
        if items:
            print(f'\n{label}:')
            for it in items[:30]:
                print('  - ' + short(it, 400))
            if len(items) > 30:
                print(f'  ... {len(items) - 30} more in build/apply_mapping_log.txt')
    print('\nThe full log is build/apply_mapping_log.txt. Next: check (FAIRe-fier).')
    return 0


# ---------------------------------------------------------------- check

def cmd_check(args):
    w = work_dir(args)
    s = load_state(w)
    wbk = Path(args.workbook).resolve() if args.workbook else Path(s.get('workbook', ''))
    if not wbk or not wbk.exists():
        raise Stop('No workbook to check. Run build first (or give --workbook).')
    d = w / 'check'
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    code, out = run_tool(FAIREFIER / 'fairefier_cli.py',
                         [wbk, '-o', d, '--checklist_dir', FAIREFIER / 'checklist', '--checklist_version', 'auto'],
                         d, quiet=True)
    summ = d / 'fairefier_summary.json'
    if not summ.exists():
        s['checked'] = dict(ran=False, when=dt.datetime.now().isoformat(timespec='seconds'))
        save_state(w, s)
        raise Stop('FAIRe-fier did not run to the end, so the workbook has NOT been checked. Its last messages:\n'
                   + '\n'.join(out.strip().splitlines()[-15:])
                   + '\nTell the researcher to check the workbook with FAIRe-fier in the Shiny app or Galaxy.')
    j = json.loads(summ.read_text(encoding='utf-8'))
    s['checked'] = dict(ran=True, when=dt.datetime.now().isoformat(timespec='seconds'), summary=j)
    save_state(w, s)
    log_event(w, 'check', json.dumps(j)[:500])
    print('FAIRe-fier ran on ' + wbk.name + '.')
    print(json.dumps(j, indent=1, ensure_ascii=False)[:2500])
    issues = d / 'fairefier_issues.tsv'
    if issues.exists():
        rows = read_tsv(issues)
        if rows:
            groups = {}
            for r in rows:
                key = (r.get('level', ''), r.get('worksheet', ''), r.get('term', ''), r.get('message', ''))
                groups.setdefault(key, []).append(r.get('record', '') or r.get('input', ''))
            order = sorted(groups.items(), key=lambda kv: (kv[0][0] != 'error', -len(kv[1])))
            print(f'\n{len(rows)} issue(s) in {len(groups)} group(s):')
            for (level, sheet, term, msg), recs in order[:args.show]:
                eg = ', '.join(x for x in recs[:4] if x)
                print(f'  - {level} in {sheet}, {term}: {short(msg, 200)} ({len(recs)} row(s)'
                      + (f', e.g. {eg}' if eg else '') + ')')
            print('All of them: check/fairefier_issues.tsv; the highlighted workbook: check/fairefier_warn_error.xlsx')
    print('\nA pass means the format and required fields are right. Whether the values are right rests on the review.')
    return 0


# ---------------------------------------------------------------- convert

CONVERT_NOTES = {
    'ncbi': ('NCBI (BioSample and SRA)', [
        'biosample.tsv: upload at https://submit.ncbi.nlm.nih.gov/subs/biosample/ (choose a batch submission '
        'and the MIMARKS survey package the table names).',
        'sra.tsv (metabarcoding): upload at https://submit.ncbi.nlm.nih.gov/subs/sra/ with the sequence files, '
        'after the BioSamples have accessions.']),
    'ena': ('ENA (samples)', [
        'samples.xml and submission.xml: submit with your ENA Webin account (Webin-REST or the Webin portal). '
        'The receipt gives each sample an accession.',
        'Experiments and runs come after the samples: they need the receipt and your study accession, so run '
        'this step again later in the Shiny app or Galaxy (FAIRe2ENA: experiments and runs).']),
    'gbif': ('a Darwin Core archive for GBIF or OBIS', [
        'dwca.zip: publish it through an IPT (Integrated Publishing Toolkit) that your organisation or a GBIF or '
        'OBIS node runs, or ask your GBIF node for help. report.md says what went into it.']),
    'qiime': ('QIIME 2 metadata', [
        'The metadata (and manifest) files go into your QIIME 2 analysis; nothing to upload.']),
}


def cmd_convert(args):
    w = work_dir(args)
    s = load_state(w)
    wbk = Path(s.get('workbook', ''))
    if not s.get('workbook') or not wbk.exists():
        raise Stop('Build the workbook first (build), and check it (check).')
    c = s.get('checked') or {}
    if not c.get('ran'):
        raise Stop('Check the workbook with FAIRe-fier first (check): converting an unchecked workbook passes its '
                   'problems on to the archives.')
    summ = c.get('summary') or {}
    errors = [k for k, v in summ.items() if isinstance(v, dict) and v.get('errors')]
    if summ.get('valid') is False and not args.anyway:
        raise Stop('FAIRe-fier found errors in the workbook. Fix them and check again before converting, or add '
                   '--anyway if the researcher wants a draft conversion.' + (f' Sheets with errors: {errors}' if errors else ''))
    if args.target == 'ncbi':
        import importlib.util
        if importlib.util.find_spec('yaml') is None:
            raise Stop('The NCBI conversion needs PyYAML: run setup --install (or pip install pyyaml). If it '
                       'cannot be installed, the researcher can run FAIRe2NCBI in the Shiny app or Galaxy.')
    d = w / 'convert' / args.target
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    made, logs = [], []
    if args.target == 'ncbi':
        tool = TOOLS / 'faire2ncbi' / 'faire2ncbi_galaxy.py'
        bargs = ['biosample', '--input_file', wbk, '--organism', args.organism, '--output', d / 'biosample.tsv',
                 '--config_out', d / 'biosample_config.yaml', '--mandatory_fill', args.mandatory_fill] + (
                    ['--duplicates_column', args.duplicates_column] if args.duplicates_column else []) + (['--bioproject', args.bioproject] if args.bioproject else [])
        code, out = run_tool(tool, bargs, d, quiet=True)
        logs.append(('BioSample', code, out))
        if s.get('assay_type') == 'metabarcoding':
            sargs = ['sra', '--input_file', wbk, '--organism', args.organism, '--output', d / 'sra.tsv',
                     '--config_out', d / 'sra_config.yaml'] + (['--instrument_model', args.instrument_model]
                                                               if args.instrument_model else [])
            code, out = run_tool(tool, sargs, d, quiet=True)
            logs.append(('SRA', code, out))
    elif args.target == 'ena':
        if not args.center_name:
            raise Stop('ENA needs the centre name of the researcher\'s Webin account (--center_name).')
        code, out = run_tool(TOOLS / 'faire2ena' / 'faire2ena_galaxy.py',
                             ['sample', '--input_file', wbk, '--center_name', args.center_name, '--taxon_id',
                              args.taxon_id, '--output_file', d / 'samples.xml', '--submission_file',
                              d / 'submission.xml'], d, quiet=True)
        logs.append(('ENA samples', code, out))
    elif args.target == 'gbif':
        targs = [wbk, '--workbook_name', wbk.name, '--target', args.publish_to,
                 '--absences' if not args.no_absences else '--no-absences',
                 '--archive', d / 'dwca.zip', '--occurrence', d / 'occurrence.txt', '--dna', d / 'dna_derived_data.txt',
                 '--eml', d / 'eml.xml', '--report', d / 'report.md']
        for k in ('assays', 'country_code', 'title', 'abstract', 'keywords', 'licence', 'given_name', 'surname',
                  'organisation', 'email', 'orcid', 'taxa'):
            v = getattr(args, k)
            if v:
                targs += [f'--{k}', str(Path(v).resolve()) if k == 'taxa' else v]
        code, out = run_tool(TOOLS / 'faire2dwc' / 'faire2dwc.py', targs, d, quiet=True)
        logs.append(('Darwin Core archive', code, out))
    elif args.target == 'qiime':
        q = TOOLS / 'faire2qiime'
        code, out = run_tool(q / 'normalise_faire.py', [wbk, d / 'normalised.xlsx', '--check_column',
                                                       args.sample_name_column], d, quiet=True)
        logs.append(('normalise', code, out))
        if code == 0:
            (d / 'out').mkdir()
            code, out = run_tool(q / 'faire2qiime_by_assay.py',
                                 [q / 'faire2qiime.py', d / 'normalised.xlsx', d / 'out', '--', '--sample_name_column',
                                  args.sample_name_column, '--absolute_path_sequences', args.sequences_folder], d,
                                 quiet=True)
            out = '\n'.join(ln for ln in out.splitlines() if ln.strip() and 'pyfiglet' not in ln
                            and not set(ln.strip()) <= set('=_|/\\ ()`\'-.,<>'))
            logs.append(('FAIRe2QIIME', code, out))
    made = sorted(str(p.relative_to(d)) for p in d.rglob('*')
                  if p.is_file() and p.name not in ('normalised.xlsx', 'prepared.xlsx', 'answers.yaml'))
    ok = all(c == 0 for _, c, _ in logs)
    title, notes = CONVERT_NOTES[args.target]
    print(f"Conversion to {title}: {'done' if ok else 'stopped'}.")
    for step, code, out in logs:
        lines = [ln for ln in out.splitlines() if ln.strip() and 'PerformanceWarning' not in ln
                 and not ln.lstrip().startswith(('frame.insert', 'newframe', 'df[', 'self.'))]
        if code != 0:
            print(f'\n{step} stopped. Its last messages:')
            print('\n'.join('  ' + short(ln, 300) for ln in lines[-15:]))
            continue
        # The same message for many samples is shown once, with a count and a few of the samples.
        groups = {}
        for ln in lines:
            if (not re.search(r'warn|error|missing|cannot|could not|skipp|left out|default', ln, re.I)
                    or re.match(r"\s*(Default value:|Use default value|Note: 'blank')", ln)):
                continue
            m = re.search(r"(?i)(sample(?: name)?) '?([^\s',]+)'?", ln)
            key = ln.replace(m.group(2), '…', 1) if m else ln
            groups.setdefault(key, []).append(m.group(2) if m else '')
        if groups:
            print(f'\n{step}: messages to read with the researcher:')
            for key, who in list(groups.items())[:20]:
                names = [x for x in who if x]
                extra = (f' ({len(who)} samples, such as {", ".join(names[:4])})' if len(who) > 1 else '')
                print('  - ' + short(key, 300) + extra)
    if made:
        print(f'\nFiles in convert/{args.target}/: ' + ', '.join(made))
    rep = d / 'report.md'
    if ok and rep.exists():
        # The parts of the Darwin Core report to go through with the researcher.
        part, keep = None, []
        for ln in rep.read_text(encoding='utf-8').splitlines():
            if ln.startswith('## '):
                part = ln[3:]
                if part in ('Records', 'What GBIF and OBIS will want', 'Notes'):
                    keep.append('\n' + part + ':')
            elif part in ('Records', 'What GBIF and OBIS will want', 'Notes') and ln.strip():
                keep.append('  ' + ln)
        print('\n'.join(keep))
    if ok:
        print('\nWhat to do with them (the researcher submits them with their own account):')
        for n in notes:
            print('  - ' + n)
    else:
        print('\nNothing to submit yet. Go through the messages above with the researcher: fix the workbook (set, '
              'then build and check again) or choose an option of convert, then convert again.')
    s.setdefault('converted', {})[args.target] = dict(ok=ok, files=made,
                                                      when=dt.datetime.now().isoformat(timespec='seconds'))
    save_state(w, s)
    log_event(w, 'convert', f"{args.target}: {'done' if ok else 'stopped'}")
    return 0 if ok else 2


# ---------------------------------------------------------------- summary and handover

def cmd_summary(args):
    w = work_dir(args)
    s = load_state(w)
    h = w / 'handover'
    if h.exists():
        shutil.rmtree(h)
    h.mkdir(parents=True)
    copies = []

    def take(src, name=None):
        src = Path(src)
        if src.exists():
            shutil.copy(src, h / (name or src.name))
            copies.append(name or src.name)

    if s.get('workbook'):
        take(s['workbook'])
        take(w / 'build' / 'apply_mapping_log.txt')
    take(review_paths(w)[1], 'review_sheet.xlsx')
    take(method_paths(w)[1], 'method_details_review_sheet.xlsx')
    if read_values(w):
        take(values_path(w), 'project_values.tsv')
    for f in ('fairefier_issues.tsv', 'fairefier_warn_error.xlsx', 'fairefier_summary.json'):
        take(w / 'check' / f)
    for target, info in (s.get('converted') or {}).items():
        for f in info.get('files', []):
            src = w / 'convert' / target / f
            if src.exists():
                (h / 'convert' / target / Path(f).parent).mkdir(parents=True, exist_ok=True)
                shutil.copy(src, h / 'convert' / target / f)
                copies.append(f'convert/{target}/{f}')
    L = [f"# FAIRe dataset: {s.get('project_id') or '(no project ID yet)'}", '',
         f"Prepared in conversation with an AI assistant using the FAIRe tools from FAIR-eDNA/FAIRe-Galaxy, on "
         f"{dt.date.today().isoformat()}.", '',
         '## Settings', '',
         f"- Assay type: {s.get('assay_type', '')}",
         f"- Sample types: {', '.join(s.get('sample_types', [])) or '(not given)'}",
         f"- Assays: {', '.join(s.get('assays', [])) or '(not given)'}",
         f"- Country or sea: {s.get('country') or '(not given)'}",
         f"- UTC offset of collection times: {s.get('utc_offset') or '(not given)'}",
         f"- Sample table: {s.get('table', {}).get('name', '(none)')}",
         f"- Methods: {', '.join(Path(m).name for m in s.get('methods', [])) or '(none)'}", '']
    # columns
    try:
        rows = review_rows(w)
        dec_log = {}
        if (w / 'map' / 'decisions.tsv').exists():
            for ln in (w / 'map' / 'decisions.tsv').read_text(encoding='utf-8').splitlines():
                p = ln.split('\t')
                if len(p) >= 5:
                    dec_log[p[1]] = p[4]
        L += ['## Columns of the sample table', '', '| Column | Decision | FAIRe term | Decided by |', '|---|---|---|---|']
        for r in rows:
            dec = r.get("Reviewer's decision") or '(none)'
            term = (r.get('Replacement FAIRe term') if dec == 'Change' else
                    r.get('Proposed FAIRe term') if dec == 'Accept' else
                    'kept as its own term' if dec == 'Reject' else r.get('Proposed FAIRe term') or '')
            by = dec_log.get(r['Input term']) or ('mapper (strong match)' if dec == 'Accept' else
                                                    'no decision: applied as the mapper called it')
            L.append(f"| {r['Input term']} | {dec} | {term} | {by} |")
        L.append('')
    except Stop:
        pass
    try:
        mrows = [r for r in method_rows(w) if r.get("Reviewer's decision") or r.get('Your value')]
        if mrows:
            L += ['## Values from the methods', '', '| FAIRe term | Assay | Value | Decision | From the methods |',
                  '|---|---|---|---|---|']
            for r in mrows:
                dec = r.get("Reviewer's decision") or 'given'
                val = r.get('Your value') if dec in ('Change', 'given') else r.get('Proposed value')
                L.append(f"| {r['FAIRe term']} | {r.get('Assay', '')} | {short(val, 80)} | {dec} | "
                         f"{short(r.get('From the methods'), 140).replace('|', '&#124;')} |")
            L.append('')
    except Stop:
        pass
    corr = w / 'table' / 'corrections.tsv'
    if corr.exists():
        L += ['## Corrections to the sample table', '',
              f"Made in a copy of {s.get('table', {}).get('name', 'the table')}; the original file was not changed. "
              'Make the same corrections in your own file.', '']
        for ln in corr.read_text(encoding='utf-8').splitlines():
            p = ln.split('\t')
            if len(p) >= 2:
                L.append(f'- {p[1]}' + (f' ({p[2]})' if len(p) > 2 and p[2] else ''))
        L.append('')
        if s.get('table', {}).get('original'):
            take(s['table']['path'])
        for c in (s.get('corrected') or {}).values():
            take(c)
    vals = read_values(w)
    if vals:
        L += ['## Values given or confirmed by the researcher', '', '| FAIRe term | Assay | Value | Source |',
              '|---|---|---|---|']
        for r in vals:
            L.append(f"| {r['term']} | {r.get('assay', '')} | {short(r['value'], 80).replace('|', '&#124;')} | "
                     f"{short(r.get('source'), 120)} |")
        L.append('')
    L += ['## Checks', '']
    if s.get('workbook'):
        L.append(f"- Workbook written: {Path(s['workbook']).name} ({s.get('built', '')}).")
        sec = log_sections(w / 'build' / 'apply_mapping_log.txt')
        empty = [e for e in sec.get('Mandatory terms with no value', []) if e.strip().lower() != 'none']
        L.append('- Mandatory terms with no value, from the build log: ' + ('none.' if not empty else ''))
        L += [f'  - {short(e, 300)}' for e in empty[:30]]
        for e in sec.get('Commonly confused terms', [])[:10]:
            L.append(f'- Commonly confused term to double-check: {short(e, 300)}')
    else:
        L.append('- The workbook has not been written in this session. Load the review sheet, the method details '
                 'review sheet and project_values.tsv into FAIRe mapper: apply mapping (Shiny app or Galaxy), with the '
                 'full sample table and OTU tables.')
    c = s.get('checked')
    if c and c.get('ran'):
        L.append(f"- FAIRe-fier ran ({c['when']}): {short(json.dumps(c.get('summary'), ensure_ascii=False), 400)}")
    else:
        L.append('- FAIRe-fier has NOT been run on this workbook in this session. Run it in the Shiny app or Galaxy '
                 'before sharing the data.')
    conv = s.get('converted') or {}
    if conv:
        L += ['', '## Conversions', '']
        for target, info in conv.items():
            title, notes = CONVERT_NOTES[target]
            L.append(f"- {title}: {'done' if info.get('ok') else 'stopped'} ({info.get('when', '')}); "
                     f"files in convert/{target}/. " + ' '.join(notes))
    L += ['', '## Next steps', '',
          '- Open the workbook and check it, especially the values marked for checking and the terms still empty.',
          '- Keep the review sheet: give it as the earlier review if you map a changed or larger table later.',
          '- To share the data: FAIRe2MDT (GBIF), edna2obis (OBIS and GBIF), FAIRe2ENA or FAIRe2NCBI (sequence '
          'archives), in the FAIRe tools Shiny app or the Galaxy eDNA Lab.', '',
          '## Files', ''] + [f'- {c}' for c in copies]
    (h / 'README.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    zpath = w / f"{s.get('project_id') or 'faire'}_handover.zip"
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(h.rglob('*')):
            if f.is_file():
                z.write(f, f'{s.get("project_id") or "faire"}_handover/{f.relative_to(h).as_posix()}')
    print(f'Handover folder: {h}\nZip: {zpath}\nFiles: ' + ', '.join(['README.md'] + copies))
    return 0


# ---------------------------------------------------------------- status

def cmd_status(args):
    w = work_dir(args)
    s = load_state(w)
    print(f'Session folder: {w}')
    print(f"Settings: {s.get('assay_type')}; samples {', '.join(s.get('sample_types', [])) or '?'}; assays "
          f"{', '.join(s.get('assays', [])) or '?'}; project {s.get('project_id') or '?'}")
    nxt = None
    if s.get('table'):
        rows = review_rows(w)
        n = sum(1 for r in rows if not r.get("Reviewer's decision"))
        print(f"Sample table: {s['table']['name']}: {len(rows)} columns, {n} still to decide")
        if n:
            nxt = nxt or 'items, then decide for each column'
    else:
        nxt = 'identify the files, then map the sample table'
    try:
        mr = method_rows(w)
        n = sum(1 for r in mr if r['_part'] in ('reliable', 'check') and not r.get("Reviewer's decision"))
        print(f'Methods: {n} value(s) still to decide')
        if n:
            nxt = nxt or 'method-items, then method-decide'
    except Stop:
        print('Methods: not read yet')
        nxt = nxt or 'methods (the paper or protocol)'
    print(f'Values given: {len(read_values(w))}')
    print(f"Workbook: {Path(s['workbook']).name if s.get('workbook') else 'not built'}")
    c = s.get('checked')
    print(f"FAIRe-fier: {'ran' if c and c.get('ran') else 'not run'}")
    if not nxt:
        nxt = 'gaps, then build' if not s.get('workbook') else ('check' if not (c and c.get('ran')) else 'summary')
    print(f'Next: {nxt}')
    return 0


# ---------------------------------------------------------------- command line

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--work', help='session folder (default faire_work, or $FAIRE_WORK)')
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('setup', help='check that Python has what the tools need')
    p.add_argument('--install', action='store_true', help='install what is missing with pip')
    p.set_defaults(fn=cmd_setup)

    p = sub.add_parser('start', help="record the study's settings (run again to change any of them)")
    p.add_argument('--assay_type', choices=['metabarcoding', 'targeted'])
    p.add_argument('--sample_types', help='comma-separated: Water, Sediment, Soil, Air, Biofilm, Tissue, Other ...')
    p.add_argument('--assays', help='assay names, comma-separated, no spaces (MiFish_12S, Fish16S ...)')
    p.add_argument('--project_id', help='letters, digits, _ or -')
    p.add_argument('--country', help='country or sea for geo_loc_name when the table has none (INSDC name)')
    p.add_argument('--utc_offset', help='UTC offset of the local collection times: +08:00, -03:30 or Z')
    p.add_argument('--date_order', choices=['stop', 'dmy', 'mdy'], help='how to read dates like 03/04/2023')
    p.set_defaults(fn=cmd_start)

    p = sub.add_parser('identify', help='say what each file is and where it goes')
    p.add_argument('files', nargs='+')
    p.set_defaults(fn=cmd_identify)

    p = sub.add_parser('table', help='correct a copy of the sample table (the original is never changed)')
    p.add_argument('action', choices=['set', 'add-column', 'drop-column', 'rename-column', 'add-row'])
    p.add_argument('column', nargs='?', help='the column to set, add or drop')
    p.add_argument('--value', help='the value to write')
    p.add_argument('--where', help="rows to change: 'COLUMN=VALUE' (exact) or 'COLUMN~PATTERN' (regular expression)")
    p.add_argument('--nth', type=int, help='only the nth row that matches --where (1 for the first)')
    p.add_argument('--cells', nargs='+', help="for add-row: 'COLUMN=VALUE' for each cell to fill")
    p.add_argument('--template', help="a value made from each row's cells, such as '{Assay}{machine}'")
    p.add_argument('--all', action='store_true', help='for set: change every row')
    p.add_argument('--file', help='correct another table (such as qPCR results) in place of the sample table')
    p.add_argument('--sheet', help='with --file: the Excel sheet')
    p.add_argument('--header_row', type=int, help='with --file: the header row (default 1)')
    p.add_argument('--reason', help='why, in a few words, for the record of corrections')
    p.set_defaults(fn=cmd_table)

    p = sub.add_parser('map', help='propose FAIRe terms for the columns of the sample table')
    p.add_argument('table', nargs='?', help="the sample table (leave out to map the session's corrected table again)")
    p.add_argument('--sheet')
    p.add_argument('--header_row', type=int, default=1)
    p.add_argument('--dictionary', help='a data dictionary or README describing the columns')
    p.add_argument('--dictionary_sheet')
    p.add_argument('--again', action='store_true', help='map a changed table, carrying over the decisions so far')
    p.add_argument('--earlier_review', help='a review sheet from an earlier session, to carry its decisions over')
    p.set_defaults(fn=cmd_map)

    p = sub.add_parser('items', help='the columns still to decide, with values, candidates and notes')
    p.add_argument('--all', action='store_true', help='every column, decided or not')
    p.set_defaults(fn=cmd_items)

    p = sub.add_parser('decide', help="record the researcher's decision on a column")
    p.add_argument('column', help='the column heading, as in the table')
    p.add_argument('decision', help='accept, reject (keep as its own term) or change')
    p.add_argument('term', nargs='?', help='for change: the right FAIRe term (or a MIxS term as listed)')
    p.add_argument('--by-model', dest='by_model', action='store_true',
                   help='the researcher agreed with a term the assistant suggested (recorded as such)')
    p.set_defaults(fn=cmd_decide)

    p = sub.add_parser('new-table', help='start a sample table from the sample columns of an OTU table')
    p.add_argument('otu')
    p.add_argument('--sheet')
    p.add_argument('--header_row', type=int, default=1)
    p.add_argument('--columns', help='the sample columns, comma-separated (default: the columns of read counts)')
    p.add_argument('--exclude', help='columns that look like counts but are not samples, comma-separated')
    p.add_argument('--split', help="a regular expression with named groups to split sample names, such as "
                                   "'(?P<Site>[A-Z]+[0-9]*)-(?P<Replicate>[0-9]+)'")
    p.add_argument('--join', help='a table of sites (or other details) to join to the samples')
    p.add_argument('--on', help="'COLUMN_HERE=COLUMN_THERE' to join on, such as 'Site=Code'")
    p.set_defaults(fn=cmd_new_table)

    p = sub.add_parser('load-review', help='take back a review sheet the researcher filled in themselves')
    p.add_argument('kind', choices=['columns', 'methods'])
    p.add_argument('file')
    p.add_argument('--force', action='store_true', help='load a sheet whose columns do not match the table')
    p.set_defaults(fn=cmd_load_review)

    p = sub.add_parser('methods', help='read methods text or PDF for values for the whole study, and primers')
    p.add_argument('texts', nargs='+')
    p.add_argument('--whole_text', action='store_true', help='read the whole text, not only its Methods section')
    p.add_argument('--primers', action='store_true', help='look for primers for a targeted assay too')
    p.add_argument('--again', action='store_true', help='read the methods afresh (decisions so far are lost)')
    p.set_defaults(fn=cmd_methods)

    p = sub.add_parser('method-items', help='method values still to decide, and the primer candidates')
    p.add_argument('--all', action='store_true')
    p.set_defaults(fn=cmd_method_items)

    p = sub.add_parser('method-decide', help="record the researcher's decision on a method value")
    p.add_argument('decision', help='accept, reject or change')
    p.add_argument('value', nargs='?', help='for change: the right value')
    p.add_argument('--row', type=int, help='the row number shown by method-items (the surest way to pick a value)')
    p.add_argument('--term', help='the FAIRe term, when it has only one value')
    p.add_argument('--assay', help='the assay this value is for')
    p.add_argument('--set-assay', dest='set_assay', action='store_true', help='write --assay into the row')
    p.add_argument('--all-reliable', dest='all_reliable', action='store_true',
                   help='accept every undecided reliable value (after the researcher has checked the list)')
    p.add_argument('--except', dest='except_rows', help='with --all-reliable: rows to leave out, comma-separated')
    p.set_defaults(fn=cmd_method_decide)

    p = sub.add_parser('primers-use', help='use a primer pair from the candidates for an assay')
    p.add_argument('pair_id')
    p.add_argument('--assay', required=True)
    p.add_argument('--with-target', dest='with_target', action='store_true',
                   help="also take targetTaxonomicAssay from the reference table (ask first)")
    p.add_argument('--lookup-file', dest='lookup_file', help='a primers-lookup result to choose from')
    p.set_defaults(fn=cmd_primers_use)

    p = sub.add_parser('primers-lookup', help='find primer pairs by name or citation in the reference table')
    p.add_argument('names', nargs='+')
    p.add_argument('--gene')
    p.set_defaults(fn=cmd_primers_lookup)

    p = sub.add_parser('set', help='record a value the researcher gives')
    p.add_argument('term')
    p.add_argument('value')
    p.add_argument('--assay', help='for a value that holds for one assay only')
    p.add_argument('--source', help="where it came from, if not the researcher's answer (a DOI, a file)")
    p.add_argument('--force', action='store_true', help='keep a value that is not one of the allowed values')
    p.set_defaults(fn=cmd_set)

    p = sub.add_parser('unset', help='remove a value recorded with set')
    p.add_argument('term')
    p.add_argument('--assay')
    p.set_defaults(fn=cmd_unset)

    p = sub.add_parser('gaps', help='mandatory FAIRe terms still without a value')
    p.add_argument('--recommended', action='store_true', help='list the highly recommended terms too')
    p.set_defaults(fn=cmd_gaps)

    p = sub.add_parser('build', help='write the FAIRe workbook')
    p.add_argument('--otu', nargs='+', action='append', metavar='PATH [key=value]',
                   help='OTU or ASV table, then options: ' + ', '.join(OTU_OPTS))
    p.add_argument('--library', nargs='+', action='append', metavar='PATH [key=value]',
                   help='library table or run report, then options: ' + ', '.join(LIB_OPTS))
    p.add_argument('--amp', nargs='+', action='append', metavar='PATH [key=value]',
                   help='qPCR or ddPCR results, then options: ' + ', '.join(AMP_OPTS))
    p.add_argument('--include_review', action='store_true', help='draft only: also apply matches still for review')
    p.add_argument('--drop_unmapped', action='store_true', help='leave out columns kept as their own terms')
    p.add_argument('--req_lev', help='requirement levels to include (default M,HR,R,O)')
    p.set_defaults(fn=cmd_build)

    p = sub.add_parser('check', help='check the workbook with FAIRe-fier')
    p.add_argument('--workbook')
    p.add_argument('--show', type=int, default=25, help='issues to print')
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser('convert', help='convert the checked workbook for a database or archive')
    p.add_argument('target', choices=['ncbi', 'ena', 'gbif', 'qiime'],
                   help='ncbi: BioSample and SRA tables; ena: ENA sample XML; gbif: a Darwin Core archive for GBIF '
                        'or OBIS (presence and absence); qiime: QIIME 2 metadata')
    p.add_argument('--anyway', action='store_true', help='convert although FAIRe-fier found errors (a draft)')
    p.add_argument('--organism', default='marine metagenome',
                   help='ncbi: the metagenome the samples are, such as freshwater metagenome or air metagenome')
    p.add_argument('--bioproject', help='ncbi: the BioProject accession, if there is one')
    p.add_argument('--mandatory_fill', default='stop',
                   choices=['stop', 'not collected', 'not provided', 'not applicable', 'missing',
                            'missing: control sample'],
                   help='ncbi: what to write in empty mandatory BioSample fields (default: stop and list them). '
                        'Only with the researcher\'s agreement')
    p.add_argument('--duplicates_column', help='ncbi: a sampleMetadata column that tells apart samples whose '
                                               'BioSample attributes are otherwise identical (such as replicate)')
    p.add_argument('--instrument_model', help='ncbi: the sequencer, when the workbook does not give it')
    p.add_argument('--center_name', help="ena: the centre name of the researcher's Webin account")
    p.add_argument('--taxon_id', default='408172',
                   help='ena: NCBI taxonomy ID of the metagenome (408172 marine, 449393 freshwater, 410658 soil, '
                        '655179 air)')
    p.add_argument('--publish_to', choices=['gbif', 'obis', 'both'], default='gbif', help='gbif: where it will go')
    p.add_argument('--no_absences', action='store_true', help='gbif: leave out absence records')
    p.add_argument('--assays', help='gbif: assays to publish, comma-separated (default all)')
    p.add_argument('--taxa', help='gbif: a taxon table (name, scientificName, scientificNameID ...); OBIS needs WoRMS IDs')
    p.add_argument('--country_code', help='gbif: ISO two-letter country code, when geo_loc_name is not enough')
    for k in ('title', 'abstract', 'keywords', 'licence', 'given_name', 'surname', 'organisation', 'email', 'orcid'):
        p.add_argument(f'--{k}', help='gbif: for the dataset description (EML)')
    p.add_argument('--sample_name_column', default='lib_id', help='qiime: the column that names the samples')
    p.add_argument('--sequences_folder', default='/path/to/sequences', help='qiime: where the fastq files are')
    p.set_defaults(fn=cmd_convert)

    p = sub.add_parser('envo', help='search the bundled ENVO for habitat terms, or show a class')
    p.add_argument('query', nargs='*', help='one or more wordings, each searched for ("dust" "house dust" shop)')
    p.add_argument('--term', choices=sorted(ENVO_FITS), help='rank the classes that suit this FAIRe term first')
    p.add_argument('--id', nargs='+', help='show these ENVO classes in full, with their narrower terms')
    p.add_argument('--limit', type=int, default=15, help='how many classes to show (default 15)')
    p.set_defaults(fn=cmd_envo)

    p = sub.add_parser('summary', help='write the handover folder and zip')
    p.set_defaults(fn=cmd_summary)

    p = sub.add_parser('status', help='what has been done, and what is next')
    p.set_defaults(fn=cmd_status)

    args = ap.parse_args(argv)
    try:
        return args.fn(args) or 0
    except Stop as e:
        print(f'STOPPED: {e}')
        return 2


if __name__ == '__main__':
    sys.exit(main())
