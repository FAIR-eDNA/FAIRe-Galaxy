"""The review sheet: an Excel workbook in which a person checks propose mapping's matches, one row for
each column of their table, and which apply mapping reads in place of the crosswalk.

Its first sheet, Review, has one row per column: the input term (the column's heading), the proposed
FAIRe term (or a MIxS or Darwin Core term when no FAIRe term fits), the score, the mapper's call
(accept, review or no match), the mapper's reasoning, the reviewer's decision (Accept, Reject or
Change, from a drop-down), the replacement FAIRe term (a drop-down with the column's best candidates
first, a blank line, then every FAIRe term) and what the column is kept as if the match is rejected
(its own term). The other sheets give the additional checks to make, how to review, the full
crosswalk (Crosswalk (details)), which apply mapping uses to apply the decisions, and the drop-down
lists (Choices, hidden).
"""
import io
import re
import zipfile

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

import faire_mapper as fm

REVIEW = 'Review'
DETAILS = 'Crosswalk (details)'
CHOICES = 'Choices'
DECIDE = 'Additional checks to make'
HOW = 'How to review'
INPUT, PROPOSED, SCORE, CALL_HEAD, REASON, DECISION, REPLACEMENT, KEPT = (
    'Input term', 'Proposed FAIRe term', 'Score', "Mapper's call", "Mapper's reasoning", "Reviewer's decision",
    'Replacement FAIRe term', 'If rejected, kept as')
HEADERS = [INPUT, PROPOSED, SCORE, CALL_HEAD, REASON, DECISION, REPLACEMENT, KEPT]
DECISIONS = ('Accept', 'Reject', 'Change')
# The mapper's call, as the walkthrough shows it
CALL = {'accept': 'accept', 'review': 'review', 'confirmed': 'set by a reviewer', 'model': 'review (chosen by a model)',
        'no match': 'no match'}
TO_DECIDE = PatternFill('solid', fgColor='FBEFD9')
HEAD = PatternFill('solid', fgColor='DDE7F0')
# The crosswalk's words for what a reviewer does, in the review sheet's words
WORDING = [
    (r'\s*To confirm, change skos:closeMatch to skos:exactMatch\.', ''),
    (r'Confirm or delete them together', 'Accept or reject them together'),
    (r'confirm or delete it together with that row', 'accept or reject it together with that match'),
    (r'Confirm this row to name the column', 'Accept to name the column'),
    (r'or delete the row to keep your own name', 'or reject it to keep your own term'),
    (r'Confirm this row', 'Accept'), (r'confirm this row', 'accept'),
    (r'Delete this row', 'Reject the match'), (r'delete this row', 'reject the match'),
    (r'delete the row', 'reject the match'),
    (r'change the FAIRe term', 'choose Change and pick the right term'),
    (r'confirm it', 'accept it'), (r'this row', 'this match'), (r'The tool will', 'Apply mapping will'),
]


def _plain(text):
    for a, b in WORDING:
        text = re.sub(a, b, text)
    return text.strip()


def _parts(comment):
    """The Why, What happens and Check parts of a crosswalk comment."""
    out = {}
    for key, nxt in (('Why', 'What happens|Check'), ('What happens', 'Check'), ('Check', '$^')):
        m = re.search(rf'{key}: (.*?)(?= (?:{nxt}): |$)', comment)
        if m:
            out[key] = m.group(1).strip()
    return out


def _label(t):
    """How a MIxS or Darwin Core term is named in the review sheet: phosphate (MIxS term)."""
    return f'{t.name} ({t.source} term)'


def reasoning(pr, p):
    """The mapper's reasoning for one column, in a few sentences."""
    if pr.term:
        parts = _parts(pr.comment)
    elif pr.other is not None:
        parts = _parts(pr.other_comment)
    else:
        why = pr.evidence if pr.evidence != 'no term scored high enough' else 'no FAIRe term fits well enough'
        ex = fm._examples(p)
        return _plain(f'{fm._sentence(why)}' + (f' Values include {ex}.' if ex else '')
                      + f' The column is kept as your own term ({pr.column}).')
    text = parts.get('Why', '')
    if pr.other is not None:
        intro = (f"No FAIRe term fits, so the mapper suggests the {pr.other.source} term {pr.other.name}, as the "
                 f"FAIRe guidelines ask; accept it to use it. ")
        text = intro + text.replace('No FAIRe term fits this column, and the', 'The')
    if parts.get('What happens'):
        text += f" {parts['What happens']}"
    if parts.get('Check') and pr.route != 'accept':
        text += f" Check: {parts['Check']}"
    if pr.fallback is not None:
        text += (f" {pr.fallback.source} also has a term for this column, {pr.fallback.name}: if {pr.term} is "
                 f"wrong, choose Change and pick '{_label(pr.fallback)}', first in the replacement list.")
    return _plain(text)


def _gloss(pr, by_name):
    t = by_name.get(pr.term) if pr.term else pr.other
    if t is None:
        return ''
    return (f'{t.source} term {t.name}: ' if t.source != 'FAIRe' else f'{t.name}: ') + fm.term_gloss(t)


def write_review_sheet(path, proposals, profiles, terms, review_rows, table_name, k=5):
    """Write the review sheet for propose mapping's proposals (see the module's docstring)."""
    by_name = {t.name: t for t in terms}
    prof = {p.column: p for p in profiles}
    all_terms = sorted(by_name, key=str.lower)
    wb = Workbook()
    ws = wb.active
    ws.title = REVIEW
    ws.append(HEADERS)
    choices = wb.create_sheet(CHOICES)
    shown = [pr for pr in proposals if prof[pr.column].n_values]
    at = {h: j for j, h in enumerate(HEADERS, 1)}
    lists = []
    for i, pr in enumerate(shown, 2):
        p = prof[pr.column]
        if pr.term:
            proposed = ' + '.join([pr.term] + pr.also_terms()) + (f' (part {pr.part})' if pr.part else '')
            score, call = round(pr.score, 2), CALL.get(pr.route, pr.route)
        elif pr.other is not None:
            proposed, score, call = _label(pr.other), round(pr.other_score, 2), 'review'
        else:
            proposed, score, call = '', None, 'no match'
        decision = 'Accept' if pr.route in ('accept', 'confirmed') else None
        ws.append([pr.column, proposed, score, call, reasoning(pr, p), decision, None,
                   f'{pr.column} (your own term)'])
        # The replacement drop-down: the column's best candidates (a MIxS or Darwin Core term the mapper
        # found first), a blank line, then every FAIRe term
        best = [c.rsplit(' (', 1)[0] for c in pr.candidates]
        best = [t for t in dict.fromkeys(best) if t in by_name and t != pr.term][:k]
        if pr.fallback is not None:
            best = [_label(pr.fallback)] + best
        lists.append([pr.column] + best + [''] + [t for t in all_terms if t not in best])
        gloss = _gloss(pr, by_name)
        if gloss:
            ws.cell(i, at[PROPOSED]).comment = Comment(gloss, 'FAIRe mapper', width=320, height=160)
        if call not in ('accept', 'set by a reviewer', 'no match'):
            for j in range(1, len(HEADERS) + 1):
                ws.cell(i, j).fill = TO_DECIDE
    # Each column of Choices holds one input term's list, under the term itself in row 1. The replacement
    # drop-down finds its list by the input term in column A of its own row, not by its position, so it
    # stays right when the rows are sorted (Excel does not move drop-downs with sorted rows).
    for j, items in enumerate(lists, 1):
        for r, t in enumerate(items, 1):
            choices.cell(r, j, t or None)
    longest = max((len(x) for x in lists), default=2) - 1
    key = 'SUBSTITUTE(SUBSTITUTE(SUBSTITUTE($A2,"~","~~"),"*","~*"),"?","~?")'   # MATCH reads * ? ~ as wildcards
    rcol = get_column_letter(at[REPLACEMENT])
    dv = DataValidation(type='list', allow_blank=True, showErrorMessage=False,
                        formula1=f"OFFSET('{CHOICES}'!$A$2,0,MATCH({key},'{CHOICES}'!$1:$1,0)-1,{longest},1)")
    dv.add(f'{rcol}2:{rcol}{len(shown) + 1}')
    ws.add_data_validation(dv)
    choices.sheet_state = 'hidden'
    dcol = get_column_letter(at[DECISION])
    dv = DataValidation(type='list', formula1='"' + ','.join(DECISIONS) + '"', allow_blank=True,
                        showErrorMessage=True, errorTitle='Decision', error='Choose Accept, Reject or Change')
    dv.add(f'{dcol}2:{dcol}{len(shown) + 1}')
    ws.add_data_validation(dv)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = HEAD
        c.alignment = Alignment(wrap_text=True, vertical='top')
    for j, w in enumerate((26, 30, 7, 12, 80, 14, 30, 28), 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical='top')
    ws.freeze_panes = 'B2'
    ws.auto_filter.ref = f'A1:{get_column_letter(len(HEADERS))}{len(shown) + 1}'

    d = wb.create_sheet(DECIDE)
    d.append(['What to check', 'Columns', 'Rows', 'What to do'])
    for r in review_rows:
        d.append(list(r))
    for c in d[1]:
        c.font, c.fill = Font(bold=True), HEAD
    for j, w in enumerate((24, 24, 40, 100), 1):
        d.column_dimensions[get_column_letter(j)].width = w
    for row in d.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical='top')

    h = wb.create_sheet(HOW)
    h.column_dimensions['A'].width = 110
    for line in how_to_review(table_name):
        h.append([line])
        h.cell(h.max_row, 1).alignment = Alignment(wrap_text=True, vertical='top')
    h['A1'].font = Font(bold=True, size=12)

    x = wb.create_sheet(DETAILS)
    x.append(fm.CROSSWALK_COLUMNS)
    for r in fm.crosswalk_rows(proposals):
        x.append([r.get(c, '') for c in fm.CROSSWALK_COLUMNS])
    for c in x[1]:
        c.font = Font(bold=True)
    wb.active = 0
    wb.save(path)
    return len(shown)


def how_to_review(table_name):
    return [
        f'How to review the terms proposed for {table_name}',
        '',
        f'The rows come from the files you provided. Each row of the Review sheet is one column heading (an input '
        f'term) of your sample metadata, {table_name}: the table with one row for each sample. The mapper matched '
        'each heading to a term from the heading, the column\'s values and, if your files describe the columns, '
        'those descriptions. For each input term the sheet gives the proposed term, its score (0 to 1), the '
        'mapper\'s call and why.',
        '',
        "The mapper's call: accept (a strong match), review (a match to check), or no match (no term proposed; "
        'the column is kept as your own term). Rows to review are shaded: put your effort there.',
        '',
        "For each row, choose a Reviewer's decision:",
        '- Accept: the proposed term is right. When no FAIRe term fits, the mapper may propose a MIxS or Darwin '
        'Core term instead, as the FAIRe guidelines ask, shown as, for example, "silicate (MIxS term)". Accept it '
        'to use it.',
        '- Reject: no proposed term is right. The column is kept in the workbook as your own term (its heading), '
        'as a user-defined field.',
        "- Change: another term is right. Pick it in Replacement FAIRe term. The drop-down lists the column's best "
        'candidates first (with a MIxS or Darwin Core term first, when the mapper found one, such as '
        '"phosphate (MIxS term)"), then a blank line, then every FAIRe term.',
        '',
        'Rows the mapper accepted are marked Accept already; change them if they are wrong. A row with no '
        'decision is applied as the mapper called it: accepted matches are applied, and matches for review are '
        'left out.',
        '',
        'You can sort or filter the rows, for example to bring the rows to review to the top: each decision is '
        'read with its input term, wherever the row is. Do not delete rows: a column whose row is deleted is kept '
        'as your own term.',
        '',
        'Hover over a proposed term to see what it means. The Additional checks to make sheet lists what only a '
        'person can settle, such as terms people often confuse.',
        '',
        'Values for the whole project, such as the primers and protocols found in your methods, are not in this '
        'sheet. The log that comes with the FAIRe workbook lists them, for you to check.',
        '',
        'Save the workbook (as .xlsx) and give it as the review sheet when you write the FAIRe workbook. Keep the '
        'Crosswalk (details) sheet: it is used to apply your decisions.',
    ]


def is_review_sheet(path):
    """Whether a file is a review sheet (an Excel workbook with the Review and Crosswalk (details) sheets)."""
    try:
        with zipfile.ZipFile(path) as z:
            names = z.read('xl/workbook.xml').decode('utf-8', 'replace')
    except (zipfile.BadZipFile, KeyError, OSError):
        return False
    return f'name="{REVIEW}"' in names and f'name="{DETAILS}"' in names


def read_review_sheet(path, by_name, other_terms, log):
    """The crosswalk for apply mapping, from a review sheet's decisions: Accept applies the proposed
    term (a FAIRe term, or a MIxS or Darwin Core term), Reject keeps the column as its own term, Change
    applies the replacement term, and no decision keeps the mapper's call."""
    with open(path, 'rb') as f:   # a file object, as Galaxy's file names end in .dat
        wb = load_workbook(io.BytesIO(f.read()), data_only=True)
    ws = wb[REVIEW]
    head = [str(c.value or '').strip() for c in ws[1]]
    need = {INPUT, DECISION, REPLACEMENT}
    if not need <= set(head):
        raise ValueError(f"the review sheet needs the columns {', '.join(sorted(need))}; found {', '.join(head)}")
    at = {h: i for i, h in enumerate(head)}
    details = pd.read_excel(path, sheet_name=DETAILS, dtype=str, engine='openpyxl').fillna('')
    rows, counts, problems, seen = [], {'Accept': 0, 'Reject': 0, 'Change': 0, '': 0}, [], set()
    # Rows are read by their input term, so they can be sorted or filtered in any order.
    for r in ws.iter_rows(min_row=2, values_only=True):
        column = str(r[at[INPUT]] or '').strip()
        if not column:
            continue
        if column in seen:
            problems.append(f"'{column}' is in the review sheet twice; its first row is used")
            continue
        seen.add(column)
        decision = str(r[at[DECISION]] or '').strip().capitalize()
        decision = decision if decision in DECISIONS else ''
        counts[decision] += 1
        mine = details[details['subject_label'].str.strip() == column].to_dict('records')
        main = [x for x in mine if x['predicate_id'] != 'skos:relatedMatch']
        if decision == 'Accept':
            if not main:
                problems.append(f"'{column}': Accept, but no term was proposed; kept under its own name")
            rows += [{**x, 'predicate_id': 'skos:exactMatch'} for x in main]
        elif decision == 'Reject':
            continue
        elif decision == 'Change':
            term = re.sub(r'\s*\(.*\)\s*$', '', str(r[at[REPLACEMENT]] or '')).strip()
            term = term[6:] if term.startswith('FAIRe:') else term
            if not term:
                problems.append(f"'{column}': Change, but no replacement term; kept under its own name")
                continue
            oid = f'FAIRe:{term}' if term in by_name else (other_terms[term].term_id if term in other_terms else '')
            if not oid:
                problems.append(f"'{column}': {term} is not a FAIRe term for this assay and sample type, nor a "
                                f"MIxS or Darwin Core term; kept under its own name")
                continue
            rows.append({'subject_id': '', 'subject_label': column, 'predicate_id': 'skos:exactMatch',
                         'object_id': oid, 'object_label': term,
                         'mapping_justification': 'semapv:ManualMappingCuration', 'confidence': '',
                         'comment': 'changed by the reviewer', 'combine_order': '', 'value_part': ''})
        else:
            rows += main
    # In the crosswalk's order (the table's), however the rows of the sheet were sorted
    order = {c: i for i, c in enumerate(dict.fromkeys(details['subject_label'].str.strip()))}
    rows.sort(key=lambda x: order.get(str(x['subject_label']).strip(), len(order)))
    gone = [c for c in order if c and c not in seen]
    if gone:
        problems.append(f"{len(gone)} columns with a proposed term have no row in the review sheet, so they are kept as "
                        f"their own terms: " + fm._first(gone, 10))
    log(f"review sheet: {counts['Accept']} accepted, {counts['Reject']} rejected, {counts['Change']} changed"
        + (f", {counts['']} with no decision (the mapper's accepted matches applied, its matches for review "
           f"left out)" if counts[''] else ''))
    return pd.DataFrame(rows, columns=fm.CROSSWALK_COLUMNS).fillna(''), problems
