"""The review sheet: an Excel workbook in which a person checks propose mapping's matches, one row for
each column of their table, and which apply mapping reads in place of the crosswalk.

Its first sheet, Review, has one row per column: the input term (the column's name), the proposed
FAIRe term, the score, the mapper's reasoning, the reviewer's decision (Accept, Reject or Change, from
a drop-down), the replacement FAIRe term (a drop-down with the column's five best candidates first,
then every FAIRe term) and what the column is kept as if the match is rejected. The other sheets give
the things to decide, how to review, the full crosswalk (Crosswalk (details)), which apply mapping
uses to apply the decisions, and the drop-down lists (Choices, hidden).
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
DECIDE = 'Things to decide'
HOW = 'How to review'
INPUT, PROPOSED, SCORE, REASON, DECISION, REPLACEMENT, KEPT = (
    'Input term', 'Proposed FAIRe term', 'Score', "Mapper's reasoning", "Reviewer's decision",
    'Replacement FAIRe term', 'If rejected, kept as')
HEADERS = [INPUT, PROPOSED, SCORE, REASON, DECISION, REPLACEMENT, KEPT]
DECISIONS = ('Accept', 'Reject', 'Change')
CALL = {'accept': 'Accepted', 'review': 'For review', 'confirmed': 'Set by a reviewer',
        'model': 'Chosen by a language model, so check it', 'no match': 'No FAIRe term'}
TO_DECIDE = PatternFill('solid', fgColor='FBEFD9')
HEAD = PatternFill('solid', fgColor='DDE7F0')
# The crosswalk's words for what a reviewer does, in the review sheet's words
WORDING = [
    (r'\s*To confirm, change skos:closeMatch to skos:exactMatch\.', ''),
    (r'Confirm or delete them together', 'Accept or reject them together'),
    (r'confirm or delete it together with that row', 'accept or reject it together with that match'),
    (r'Confirm this row to name the column', 'Accept to name the column'),
    (r'or delete the row to keep your own name', 'or reject it to keep your own name'),
    (r'Confirm this row', 'Accept'), (r'confirm this row', 'accept'),
    (r'Delete this row', 'Reject the match'), (r'delete this row', 'reject the match'),
    (r'delete the row', 'reject the match'),
    (r'change the FAIRe term', 'choose Change and give the right FAIRe term'),
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


def reasoning(pr, p):
    """The mapper's reasoning for one column, in a few sentences."""
    call = CALL.get(pr.route, pr.route)
    if pr.term:
        parts = _parts(pr.comment)
    elif pr.other is not None:
        parts = _parts(pr.other_comment)
        call = f'No FAIRe term; a {pr.other.source} term instead'
    else:
        why = pr.evidence if pr.evidence != 'no term scored high enough' else 'no FAIRe term fits well enough'
        ex = fm._examples(p)
        return _plain(f'{call}: {why}.' + (f' Values include {ex}.' if ex else '')
                      + ' The column is kept under its own name.')
    text = f"{call}. {parts.get('Why', '')}"
    if parts.get('What happens'):
        text += f" {parts['What happens']}"
    if parts.get('Check') and pr.route != 'accept':
        text += f" Check: {parts['Check']}"
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
    for i, pr in enumerate(shown, 2):
        p = prof[pr.column]
        if pr.term:
            proposed = ' + '.join([pr.term] + pr.also_terms()) + (f' (part {pr.part})' if pr.part else '')
            score = round(pr.score, 2)
        elif pr.other is not None:
            proposed, score = f'{pr.other.name} ({pr.other.source})', round(pr.other_score, 2)
        else:
            proposed, score = '', None
        kept = (f'{pr.fallback.name} ({pr.fallback.source} term)' if pr.fallback is not None
                else f'{pr.column} (your own name)')
        decision = 'Accept' if pr.route in ('accept', 'confirmed') else None
        ws.append([pr.column, proposed, score, reasoning(pr, p), decision, None, kept])
        # The replacement drop-down: the column's best candidates first, then every FAIRe term
        best = [c.rsplit(' (', 1)[0] for c in pr.candidates]
        best = [t for t in dict.fromkeys(best) if t in by_name and t != pr.term][:k]
        options = best + [t for t in all_terms if t not in best]
        col = get_column_letter(i - 1)
        for j, t in enumerate(options, 1):
            choices.cell(j, i - 1, t)
        dv = DataValidation(type='list', formula1=f"'{CHOICES}'!${col}$1:${col}${len(options)}", allow_blank=True,
                            showErrorMessage=False)
        dv.add(f'F{i}')
        ws.add_data_validation(dv)
        gloss = _gloss(pr, by_name)
        if gloss:
            ws.cell(i, 2).comment = Comment(gloss, 'FAIRe mapper', width=320, height=160)
        if pr.route not in ('accept', 'confirmed'):
            for j in (1, 5, 6):
                ws.cell(i, j).fill = TO_DECIDE
    choices.sheet_state = 'hidden'
    dv = DataValidation(type='list', formula1='"' + ','.join(DECISIONS) + '"', allow_blank=True,
                        showErrorMessage=True, errorTitle='Decision', error='Choose Accept, Reject or Change')
    dv.add(f'E2:E{len(shown) + 1}')
    ws.add_data_validation(dv)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = HEAD
        c.alignment = Alignment(wrap_text=True, vertical='top')
    for j, w in enumerate((26, 30, 7, 80, 14, 30, 28), 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical='top')
    ws.freeze_panes = 'B2'
    ws.auto_filter.ref = f'A1:G{len(shown) + 1}'

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
    for r in fm.crosswalk_rows(proposals, fallbacks=True):
        x.append([r.get(c, '') for c in fm.CROSSWALK_COLUMNS])
    for c in x[1]:
        c.font = Font(bold=True)
    wb.active = 0
    wb.save(path)
    return len(shown)


def how_to_review(table_name):
    return [
        f'How to review the proposed FAIRe terms for {table_name}',
        '',
        'The Review sheet has one row for each column of your table, with the FAIRe term the mapper proposes, '
        'its score (0 to 1), and why. Rows to decide are shaded.',
        '',
        "For each row, choose a Reviewer's decision:",
        '- Accept: the proposed term is right.',
        "- Reject: the column has no FAIRe term. It is kept in the workbook as a user-defined field, under the "
        "name in 'If rejected, kept as': your own column name, or a MIxS or Darwin Core term when the mapper "
        'found one, as the FAIRe guidelines ask.',
        '- Change: another FAIRe term is right. Pick it in Replacement FAIRe term: the drop-down lists the '
        "column's best candidates first, then every FAIRe term.",
        '',
        'Rows already marked Accept were accepted by the mapper; change them if they are wrong. A row with no '
        'decision is applied as the mapper called it: accepted matches are applied, and matches for review are '
        'left out.',
        '',
        'Hover over a proposed term to see what it means. The Things to decide sheet lists what only a person '
        'can settle, such as terms people often confuse.',
        '',
        'Save the workbook (as .xlsx) and give it to FAIRe mapper: apply mapping as the crosswalk. Keep the '
        'Crosswalk (details) sheet: apply mapping uses it to apply your decisions.',
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
    match, Reject leaves the column out of the FAIRe terms (named after its MIxS or Darwin Core term if
    the sheet gives one), Change applies the replacement term, and no decision keeps the mapper's call."""
    with open(path, 'rb') as f:   # a file object, as Galaxy's file names end in .dat
        wb = load_workbook(io.BytesIO(f.read()), data_only=True)
    ws = wb[REVIEW]
    head = [str(c.value or '').strip() for c in ws[1]]
    need = {INPUT, DECISION, REPLACEMENT}
    if not need <= set(head):
        raise ValueError(f"the review sheet needs the columns {', '.join(sorted(need))}; found {', '.join(head)}")
    at = {h: i for i, h in enumerate(head)}
    details = pd.read_excel(path, sheet_name=DETAILS, dtype=str, engine='openpyxl').fillna('')
    rows, counts, problems = [], {'Accept': 0, 'Reject': 0, 'Change': 0, '': 0}, []
    for r in ws.iter_rows(min_row=2, values_only=True):
        column = str(r[at[INPUT]] or '').strip()
        if not column:
            continue
        decision = str(r[at[DECISION]] or '').strip().capitalize()
        decision = decision if decision in DECISIONS else ''
        counts[decision] += 1
        mine = details[details['subject_label'].str.strip() == column].to_dict('records')
        main = [x for x in mine if x['predicate_id'] != 'skos:relatedMatch']
        fallback = [x for x in mine if x['predicate_id'] == 'skos:relatedMatch']
        if decision == 'Accept':
            if not main:
                problems.append(f"'{column}': Accept, but no term was proposed; kept under its own name")
            rows += [{**x, 'predicate_id': 'skos:exactMatch'} for x in main]
        elif decision == 'Reject':
            rows += [{**x, 'predicate_id': 'skos:exactMatch'} for x in fallback]
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
    log(f"review sheet: {counts['Accept']} accepted, {counts['Reject']} rejected, {counts['Change']} changed"
        + (f", {counts['']} with no decision (the mapper's accepted matches applied, its matches for review "
           f"left out)" if counts[''] else ''))
    return pd.DataFrame(rows, columns=fm.CROSSWALK_COLUMNS).fillna(''), problems
