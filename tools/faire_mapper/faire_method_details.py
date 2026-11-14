#!/usr/bin/env python3
"""Find FAIRe values for the laboratory and bioinformatic methods in a study's methods text.

Usage:
    python faire_method_details.py METHODS [METHODS ...] --checklist CHECKLIST
        [--assay_type metabarcoding] [--assay_names Fish16S,COI] -o PROPOSALS.tsv
        [--review_sheet REVIEW.xlsx]

The methods can be plain text, markdown or a PDF. The script reads them sentence by sentence and
proposes a value for each FAIRe term it can recognise, with the sentence it came from: the PCR
conditions, master mix, thermocycler and reaction volumes; the sequencing instrument, kit and read
layout; the software used for each bioinformatic step with its version and settings; the reference
databases and identity thresholds; and the filtration, extraction and storage of the samples.

It works by rules, not a language model. The rules look for two kinds of thing:

- named things listed in method_details/vocabulary.tsv (instruments, kits, master mixes, software,
  reference databases, filters, sampling devices, sequencing facilities), which anyone can add to;
- the ways methods sections usually state a value ("40 cycles of", "in 25 uL reactions", "maximum
  expected errors = 2", "query coverage of 96%"), each seen in at least two of the methods texts the
  rules were developed on (see README.md).

Every value is a proposal for a person to check. The review sheet lists each one with its sentence,
for the person to accept, reject or change, and lists the FAIRe method terms not found, for the
person to fill in. Apply mapping reads the reviewed sheet as values for the whole project.

When the text is a whole paper, only its Methods section is read (from the Methods heading to the
Results, Discussion or References heading), with any supplementary methods after the references:
other parts of a paper name tools and kits that other studies used.
"""

import argparse
import csv
import re
import sys
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

import faire_mapper_text as ft

__version__ = '0.9.0'

HERE = Path(__file__).resolve().parent
VOCABULARY = HERE / 'method_details' / 'vocabulary.tsv'
CONFUSED = HERE / 'commonly_confused_terms.tsv'

# Terms find primers gives (from the primer table), so this tool leaves them out of its list of terms
# still to give.
PRIMER_TERMS = {'assay_name', 'targetTaxonomicAssay', 'targetTaxonomicScope', 'target_gene', 'target_subfragment',
                'ampliconSize', 'pcr_primer_forward', 'pcr_primer_reverse', 'pcr_primer_name_forward',
                'pcr_primer_name_reverse', 'pcr_primer_reference_forward', 'pcr_primer_reference_reverse'}
# Sample terms the rules look for; the other sample terms come from the sample table.
SAMPLE_TERMS = {'samp_collect_device', 'samp_size', 'samp_size_unit', 'samp_mat_process', 'filter_passive_active_0_1',
                'size_frac', 'size_frac_low', 'filter_diameter', 'filter_material', 'filter_name',
                'samp_store_temp', 'samp_store_sol', 'prepped_samp_store_temp', 'samp_vol_we_dna_ext', 'samp_vol_we_dna_ext_unit',
                'nucl_acid_ext_lysis', 'nucl_acid_ext_sep', 'nucl_acid_ext_kit', 'nucl_acid_ext_modify',
                'dna_cleanup_0_1', 'dna_cleanup_method'}
METHOD_SECTIONS = ('PCR', 'Library preparation sequencing', 'Bioinformatics')
# Terms that hold a description: the sentences found for one are joined into one value, for the
# person to shorten.
DESCRIPTION_TERMS = {'sterilise_method', 'samp_mat_process', 'lib_screen', 'nucl_acid_ext_modify', 'inhibition_check',
                     'tax_class_collapse', 'tax_class_other', 'screen_contam_method', 'screen_geograph_method',
                     'screen_nontarget_method', 'bioinfo_method_additional', 'otu_db_custom', 'seq_method_additional'}
SECTION_NAMES = OrderedDict([
    ('Project', 'Field and laboratory hygiene'),
    ('Sample collection', 'Sample collection'), ('Sample preparation', 'Filtration'),
    ('Sample storage', 'Sample storage'), ('Nucleic acid extraction', 'DNA extraction'),
    ('PCR', 'PCR'), ('Library preparation sequencing', 'Library preparation and sequencing'),
    ('Bioinformatics', 'Bioinformatics')])

# ------------------------------------------------------------------ the methods section of a paper

_NUM = r'(?:[0-9IVX]+(?:\.\d+)*\s*[.|)]?\s*\|?\s*)?'
START = re.compile(r'^\s*' + _NUM + r'(?:materials?\s+(?:and|&)\s+methods|methods(?:\s+(?:and|&)\s+materials?)?|'
                   r'methodology|experimental\s+procedures?)\s*:?\s*$', re.I | re.M)
END_HEADING = re.compile(r'^\s*' + _NUM + r'(?:results?(?:\s+(?:and|&)\s+discussion)?|discussion|conclusions?|references|'
                         r'literature\s+cited|bibliography|acknowledge?ments?)\s*:?\s*$', re.I | re.M)
REFERENCES_HEADING = re.compile(r'^\s*(?:references|literature\s+cited|bibliography)\s*:?\s*$', re.I | re.M)
YEAR = re.compile(r'\b(?:19|20)\d\d\b')


class _Headings:
    """A heading pattern that skips table column labels: a references heading counts only when
    references follow it, and a results heading only when sentences follow it."""

    def __init__(self, rx, refs=False):
        self.rx, self.refs = rx, refs

    def search(self, text, pos=0):
        for m in self.rx.finditer(text, pos):
            after = text[m.end():m.end() + 600]
            if re.match(r'\s*(?:references|literature|bibliography)', m.group(0).strip(' \t\n0123456789.|'), re.I) \
                    or self.refs:
                if len(YEAR.findall(after)) >= 3:
                    return m
            elif re.search(r'[a-z]{3,}[^.\n]{20,}\.', after):
                return m
        return None


END = _Headings(END_HEADING)
REFERENCES = _Headings(REFERENCES_HEADING, refs=True)
SUPPLEMENT = re.compile(r'^\s*(?:supporting\s+information|supplementa(?:ry|l)\s+(?:methods|information|materials?|text)|'
                        r'appendix\s+s?\d*|(?:section|methods?|text)\s+s\d+)\b[^\n]{0,80}$', re.I | re.M)
LAB_WORDS = re.compile(r'extract|\bPCR|sequenc|filter|bioinformatic|reads\b|amplif', re.I)


def supplementary_methods(text, m):
    """True if a supplementary heading starts methods, not a note that supplements exist or a
    reference list."""
    after = text[m.end():m.end() + 1200]
    return len(set(x.lower()[:5] for x in LAB_WORDS.findall(after))) >= 2 and len(YEAR.findall(after)) < 8 and \
        not re.match(r'\s*additional\s+supporting\s+information\s+can\s+be\s+found', after, re.I)


def methods_part(text):
    """The parts of a text to read, and a note of what was read. A text with a Methods heading is read
    from each Methods heading to the next Results, Discussion or References heading, plus any
    supplementary sections; other texts are read whole, apart from a references list."""
    starts = list(START.finditer(text))
    spans = []
    for m in starts:
        end = END.search(text, m.end())
        spans.append((m.start(), end.start() if end else len(text)))
    last = max((e for _, e in spans), default=0)
    for m in SUPPLEMENT.finditer(text, last):
        if any(s <= m.start() < e for s, e in spans) or not supplementary_methods(text, m):
            continue
        end = REFERENCES.search(text, m.end())
        spans.append((m.start(), end.start() if end else len(text)))
    if not starts:
        ref = REFERENCES.search(text)
        if not ref:
            return text, 'the whole text (no Methods heading found)'
        spans = [(0, ref.start())] + [s for s in spans if s[0] >= ref.start()]
        return '\n\n'.join(text[s:e] for s, e in sorted(spans)), \
            'the text up to the references (no Methods heading found)' + (', and the supplementary methods' if len(spans) > 1 else '')
    spans = sorted(spans)
    merged = [list(spans[0])]
    for s, e in spans[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    words = sum(len(text[s:e].split()) for s, e in merged)
    supp = any(SUPPLEMENT.match(text, s) for s, _ in merged)
    return '\n\n'.join(text[s:e] for s, e in merged), \
        f'the Methods section ({words} words)' + (' and the supplementary methods' if supp else '')


# ------------------------------------------------------------------ sentences

@dataclass
class Sentence:
    text: str
    para: int
    index: int
    reference_work: bool = False   # about specimens for a reference library, not the eDNA samples
    source: str = ''


SENT_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9(\[“"‘\'])')
ABBREV_END = re.compile(r'(?:\bet\s+al|\be\.g|\bi\.e|\bapprox|\bca|\bcf|\bFigs?|\bvs|\bNo|\bInc|\bLtd|\bCo|\bCorp|\bDr|'
                        r'\bSt|\bspp?|\bv|\bver|\bvol|\bpp|\bU\.S\.A|\bU\.S|(?<![°º˚\d])\b[A-Z])\.$')
# Lines a PDF repeats on every page: the publisher's footer, download notices and page numbers
FURNITURE = re.compile(r'^.*(?:Downloaded\s+from\s+https?://|See\s+the\s+Terms\s+and\s+Conditions|Wiley\s+Online\s+Library\s+for\s+rules|'
                       r'governed\s+by\s+the\s+applicable\s+Creative\s+Commons).*$|^\s*(?:Page\s+)?\d{1,3}(?:\s+of\s+\d{1,3})?\s*$',
                       re.I | re.M)
REFERENCE_WORK = re.compile(r'\bspecimens?\b|\bvouchers?\b|\btissue\s+samples?\b', re.I)


def split_sentences(text, source=''):
    text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\u00ad', '')
    text = FURNITURE.sub('', text)
    text = re.sub(r'(?<=[a-z])-\n(?=[a-z])', '', text)
    out = []
    paras = []
    for para in re.split(r'\n\s*\n', text):
        para = re.sub(r'\s+', ' ', para).strip()
        if not para:
            continue
        if len(para.split()) <= 12 and not re.search(r'[.!?:;)]["”’]?$', para) and not re.match(r'[a-z(]', para):
            continue   # a heading
        # A sentence broken by a page break (a PDF's blank line) is joined again
        if paras and not re.search(r'[.!?:]["”’)]?$', paras[-1]) and re.match(r'[a-z(]', para):
            paras[-1] += ' ' + para
        else:
            paras.append(para)
    for pi, para in enumerate(paras):
        ref = bool(REFERENCE_WORK.search(para))
        merged = []
        for piece in SENT_SPLIT.split(para):
            if merged and ABBREV_END.search(merged[-1]):
                merged[-1] += ' ' + piece
            else:
                merged.append(piece)
        for s in merged:
            out.append(Sentence(s, pi, len(out), ref, source))
    return out


# ------------------------------------------------------------------ the vocabulary

@dataclass
class Entry:
    kind: str
    name: str
    regex: object
    maker: str = ''
    extra: str = ''
    uses: tuple = ()
    parent: str = ''
    source: str = ''


def alias_regex(alias):
    if alias.startswith('re:'):
        return alias[3:]
    parts = re.split(r'\s+', alias.strip())
    sep = r'[®™]?(?:[\s \-‐–]*)'
    body = sep.join(re.escape(p).replace(r'\&', r'(?:&|and)') for p in parts)
    return body + r'[®™]?'


def split_aliases(text):
    """Aliases separated by |, leaving alone a | inside the brackets of a regular expression."""
    out, depth, cur = [], 0, ''
    for ch in text:
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth -= 1
        if ch == '|' and depth == 0:
            out.append(cur)
            cur = ''
        else:
            cur += ch
    return out + [cur]


def load_vocabulary(path=VOCABULARY):
    lines = [ln for ln in Path(path).read_text(encoding='utf-8').splitlines() if ln.strip() and not ln.startswith('#')]
    rows = list(csv.DictReader(lines, delimiter='\t'))
    vocab = {}
    for r in rows:
        r = {k: (v or '').strip() for k, v in r.items()}
        aliases = [a for a in split_aliases(r['aliases']) if a.strip()] or [r['name']]
        pattern = '|'.join(f'(?:{alias_regex(a)})' for a in sorted(aliases, key=len, reverse=True))
        flags = 0 if r['case'] == 'exact' else re.I
        rx = re.compile(r'(?<![A-Za-z0-9])(?:' + pattern + r')(?![A-Za-z0-9])', flags)
        uses, parent = (), ''
        if r['uses'].startswith('parent='):
            parent = r['uses'][7:]
        elif r['uses']:
            uses = tuple(u.strip() for u in r['uses'].split(',') if u.strip())
        if r['source'].startswith('parent='):
            parent = r['source'][7:]
        vocab.setdefault(r['kind'], []).append(Entry(r['kind'], r['name'], rx, r['maker'], r['extra'], uses, parent,
                                                     r['source']))
    return vocab


def find_named(entries, text):
    """The vocabulary entries named in a text, as (entry, match), longest first and not overlapping,
    in the order they appear."""
    hits = []
    for e in entries:
        for m in e.regex.finditer(text):
            hits.append((m.start(), -(m.end() - m.start()), e, m))
    hits.sort(key=lambda h: (h[0], h[1]))
    out, taken = [], []
    for start, neg, e, m in sorted(hits, key=lambda h: h[1]):
        if any(start < b and m.end() > a for a, b in taken):
            continue
        taken.append((start, m.end()))
        out.append((e, m))
    return sorted(out, key=lambda x: x[1].start())


VERSION = re.compile(r'\s*(?:\(\s*|,\s*)?(?:v(?:ersion)?\.?\s*(\d+(?:\.\d+){0,3}[a-z]?\+?)|(\d+\.\d+(?:\.\d+){0,2}[a-z]?\+?))\b')


def version_after(text, end):
    m = VERSION.match(text, end)
    if not m:
        return ''
    return 'v' + (m.group(1) or m.group(2))


# ------------------------------------------------------------------ proposals

@dataclass
class Proposal:
    term: str
    value: str
    sentence: Sentence
    found_by: str
    note: str = ''
    assay: str = ''
    span: tuple = ()
    others: int = 0
    extra_sentences: list = field(default_factory=list)


class Finder:
    def __init__(self, sentences, vocab, assay_names=()):
        self.sentences = sentences
        self.vocab = vocab
        self.assay_names = [a for a in assay_names if a]
        self.out = []

    def add(self, term, value, s, found_by, note='', span=(), extra=()):
        value = str(value).strip()
        if not value:
            return
        if value == s.text and (len(value.split()) < 8 or not re.search(r'[.!?)]["”’]?$', value)):
            return   # a heading, not a sentence
        self.out.append(Proposal(term, value, s, found_by, note, self.assay_of(s), span, 0, list(extra)))

    def assay_of(self, s):
        if len(self.assay_names) < 2:
            return ''
        key = re.sub(r'[\s_\-]', '', s.text.lower())
        named = [a for a in self.assay_names if re.sub(r'[\s_\-]', '', a.lower()) in key]
        return named[0] if len(named) == 1 else ''

    def lab(self):
        return [s for s in self.sentences if not s.reference_work]


def num(x):
    x = float(x)
    return str(int(x)) if x == int(x) else f'{x:.3f}'.rstrip('0').rstrip('.')


WORD_NUMBERS = {'no': 0, 'zero': 0, 'one': 1, 'single': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
                'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'twelve': 12, 'duplicate': 2, 'triplicate': 3,
                'quadruplicate': 4}
NUMBER = r'(\d+(?:\.\d+)?|no|zero|one|two|three|four|five|six|seven|eight|nine|ten|twelve)'


def as_number(word):
    w = word.lower()
    return WORD_NUMBERS[w] if w in WORD_NUMBERS else float(w)


MU = r'(?:µ|μ|u|micro)'
TEMP = r'([-−–]?\d{1,3}(?:\.\d+)?)(?:\s*[-–]\s*(\d{1,3}(?:\.\d+)?))?\s*(?:°|º|˚|degrees?\s*)\s?C\b'
TIME = (r'(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|min|seconds?|secs?|sec|s)\b'
        r'(?:\s*(?:and\s*)?(\d+)\s*(?:seconds?|secs?|sec|s)\b)?')


def minutes(n, unit, extra_s=None):
    x = float(n)
    u = unit.lower()
    if u.startswith('h'):
        x *= 60
    elif u.startswith('s'):
        x /= 60
    if extra_s:
        x += float(extra_s) / 60
    return num(round(x, 3))


def temp_value(a, b=None):
    a = a.replace('−', '-').replace('–', '-')
    return f'{num(a)}-{num(b)}' if b else num(a)


# ------------------------------------------------------------------ PCR

SECOND_PCR = re.compile(r'second[- ]?(?:stage|round|step)|(?:stage|round|step)[- ]?(?:2|two)\b|index(?:ing)?\s+PCR|'
                        r'\bindexing\b|library\s+PCR|\bPCR\s?2\b|second\s+PCR', re.I)
PCR_WORDS = re.compile(r'\bPCR|\bqPCR|amplif|\breactions?\b', re.I)


def stage(s):
    return 'pcr2_' if SECOND_PCR.search(s.text) else ''


def pcr_term(pre, term):
    """The FAIRe term for a PCR value: pcr_cond, or pcr2_cond for the second PCR of a two-step library
    preparation."""
    if not pre:
        return term
    return {'pcr_cond': 'pcr2_cond', 'pcr_cycles': 'pcr2_cycles', 'pcr_dna_vol': 'pcr2_dna_vol'}.get(term, 'pcr2_' + term)


def _temp(a, b):
    deg = r'\s*(?:°|º|˚|degrees?\s*)\s?C\b'
    return (rf'(?<![-−–\d])(?P<{a}>\d{{1,3}}(?:\.\d+)?)(?:(?:{deg})?\s*[-–]\s*(?P<{b}>\d{{1,3}}(?:\.\d+)?))?{deg}')


def _time(d, u, x):
    return (rf'(?P<{d}>\d+(?:\.\d+)?)\s*(?P<{u}>hours?|hrs?|h|minutes?|mins?|min|seconds?|secs?|sec|s)\b'
            rf'(?:\s*(?:and\s*)?(?P<{x}>\d+)\s*(?:seconds?|secs?|sec|s)\b)?')


# A step of a PCR programme: 95 °C for 30 s, or 30 s at 95 °C
STEP = re.compile(rf'(?:{_temp("ta", "tb")}\s*(?:for|,|:|\()?\s*{_time("da", "ua", "sa")})|'
                  rf'(?:(?:for\s+)?{_time("db", "ub", "sb")}\s*(?:at|@)\s*{_temp("tc", "td")})', re.I)
CYCLES = re.compile(r'(\d+)(?:\s*[-–]\s*(\d+))?\s*(?:PCR\s+|thermal\s+|amplification\s+)?cycles?\b', re.I)
FINAL = re.compile(r'final\s+(?:extension|elongation)|extension\s+(?:step\s+)?(?:at|of)\s+\d+\s*°|(?:followed\s+by|and|with)\s+'
                   r'(?:a\s+)?(?:final\s+)?(?:hold|extension)', re.I)
MELT = re.compile(r'(?:,\s*)?(?:a\s+|and\s+)?melt(?:ing)?\s*curve.*?(?=(?:,?\s*(?:and|with|followed\s+by)\s+)?'
                  r'(?:a\s+)?final|$)', re.I | re.S)


def parse_cycling(text):
    """The steps of a PCR programme written as a sentence, in the FAIRe pcr_cond format
    (initial denaturation:95_15;denaturation:95_0.5;annealing:54_1.5;elongation:72_1.5;final
    elongation:72_10;40), with the annealing temperature and the number of cycles; None if the
    sentence is not a PCR programme."""
    text = MELT.sub('', text)
    cyc = CYCLES.search(text)
    if not cyc:
        return None
    steps = []
    for m in STEP.finditer(text):
        if m.group('ta'):
            t, t2, d, u, s2 = m.group('ta'), m.group('tb'), m.group('da'), m.group('ua'), m.group('sa')
        else:
            t, t2, d, u, s2 = m.group('tc'), m.group('td'), m.group('db'), m.group('ub'), m.group('sb')
        steps.append((m.start(), float(t.replace('−', '-').replace('–', '-')), temp_value(t, t2), minutes(d, u, s2)))
    if len(steps) < 2:
        return None
    fin = FINAL.search(text, cyc.end())
    before = [x for x in steps if x[0] < cyc.start()]
    inside = [x for x in steps if x[0] >= cyc.start() and (not fin or x[0] < fin.start())]
    after = [x for x in steps if fin and x[0] >= fin.start()]
    parts, anneal = [], None
    for _, t, tv, mins in before:
        parts.append(f"{'initial denaturation' if t >= 90 else 'initial step'}:{tv}_{mins}")
    for i, (_, t, tv, mins) in enumerate(inside):
        if t >= 90:
            label = 'denaturation'
        elif 68 <= t <= 75 and i == len(inside) - 1 and len(inside) > 1:
            label = 'elongation'
        else:
            label = 'annealing'
            anneal = anneal or tv
        parts.append(f'{label}:{tv}_{mins}')
    for _, t, tv, mins in after:
        if t > 15:
            parts.append(f'final elongation:{tv}_{mins}')
    if not inside:
        return None
    cycles = f'{cyc.group(1)}-{cyc.group(2)}' if cyc.group(2) else cyc.group(1)
    return ';'.join(parts + [cycles]), anneal, cycles


def rule_pcr(f):
    sents = f.lab()
    for i, s in enumerate(sents):
        txt = s.text
        if not PCR_WORDS.search(txt) and not CYCLES.search(txt):
            continue
        pre = stage(s)
        # The PCR programme, joined to a sentence before it that gives the initial denaturation and to
        # one after it that gives the final extension.
        if CYCLES.search(txt) and len(re.findall(TEMP, txt)) >= 2:
            joined, extra = txt, []
            if i and sents[i - 1].para == s.para and re.search(r'denatur', sents[i - 1].text, re.I) \
                    and not CYCLES.search(sents[i - 1].text) and re.search(TEMP, sents[i - 1].text):
                joined = sents[i - 1].text + ' ' + joined
                extra.append(sents[i - 1])
            if i + 1 < len(sents) and re.match(r'\s*(?:a\s+|the\s+)?final', sents[i + 1].text, re.I):
                joined = joined + ' ' + sents[i + 1].text
                extra.append(sents[i + 1])
            got = parse_cycling(joined)
            if got:
                cond, anneal, cycles = got
                f.add(pcr_term(pre, 'pcr_cond'), cond, s, 'the PCR programme in this sentence, in the FAIRe format '
                      '(step:temperature_minutes; the number of cycles last)', extra=extra,
                      span=CYCLES.search(txt).span())
                if anneal and '-' not in anneal:
                    f.add(pcr_term(pre, 'annealingTemp'), anneal, s, 'the annealing step of the PCR programme')
                elif anneal:
                    f.add(pcr_term(pre, 'annealingTemp'), anneal, s, 'the annealing step of the PCR programme',
                          'a range: give each assay its own annealing temperature')
                if '-' in cycles:
                    f.add(pcr_term(pre, 'pcr_cycles'), cycles, s, 'the number of cycles in the PCR programme',
                          'a range: give the number of cycles used (for each assay if they differ)')
                else:
                    f.add(pcr_term(pre, 'pcr_cycles'), cycles, s, 'the number of cycles in the PCR programme')
        for m in re.finditer(r'anneal\w*\s+(?:temperature\s+)?(?:(?:of|at|was|=)\s+)?' + TEMP, txt, re.I):
            f.add(pcr_term(pre, 'annealingTemp'), temp_value(m.group(1), m.group(2)), s, "an annealing temperature",
                  span=m.span())
        # Reaction volume and template volume
        for m in re.finditer(r'(?:in\s+(?:a\s+)?(?:total\s+(?:reaction\s+)?volume\s+of\s+)?|reaction\s+volume\s+of\s+|'
                             r'total\s+volume\s+of\s+)(\d+(?:\.\d+)?)\s*[-‐]?\s*' + MU + r'?\s?[lL]\b'
                             r'(?=[^.;]{0,25}(?:reaction|volume|containing|consisting|comprising|mix))', txt):
            f.add(pcr_term(pre, 'amplificationReactionVolume'), num(m.group(1)), s, 'the volume of the PCR reaction (µL)',
                  span=m.span())
        for m in re.finditer(r'(\d+(?:\.\d+)?)(?:\s*[-–]\s*(\d+(?:\.\d+)?))?\s*' + MU + r'?\s?[lL]\s+of\s+(?:\w+\s+){0,3}?'
                             r'(?:template|DNA|extract|eDNA)\b', txt):
            v = f'{num(m.group(1))}-{num(m.group(2))}' if m.group(2) else num(m.group(1))
            f.add(pcr_term(pre, 'pcr_dna_vol'), v, s, 'the volume of DNA template in each PCR (µL)',
                  'a range: give the volume used' if m.group(2) else '', span=m.span())
        # Replicates
        if re.search(r'\bPCR|\bqPCR|amplif', txt, re.I):
            for m in re.finditer(r'\b(?:in|as)\s+(duplicate|triplicate|quadruplicate)\b|\b(duplicate|triplicate|quadruplicate)\s+'
                                 r'(?:q?PCRs?|reactions|amplifications)|' + NUMBER + r'\s+(?:technical\s+)?(?:q?PCR\s+)?'
                                 r'replicates?\b', txt, re.I):
                w = m.group(1) or m.group(2) or m.group(3)
                if w and as_number(w) >= 1:
                    f.add('pcr_rep', num(as_number(w)), s, 'the number of PCR replicates', span=m.span())
        # Master mix: a named one, or the reaction's own recipe
        named = find_named(f.vocab.get('master_mix', []), txt)
        for e, m in named:
            f.add(pcr_term(pre, 'commercial_mm'), f'{e.name}, {e.maker}' if e.maker else e.name, s,
                  'a commercial PCR master mix named in the methods', span=m.span())
        if not named and re.search(r'MgCl', txt) and re.search(r'dNTP', txt, re.I):
            m = re.search(r'(?:containing|consisting\s+of|comprising|comprised|contained)\s*:?\s*(.+)$', txt, re.I)
            recipe = m.group(1).rstrip('.') if m else txt
            f.add(pcr_term(pre, 'custom_mm'), recipe, s, 'the recipe of the PCR reaction (MgCl2, dNTPs and so on)')
        for e, m in find_named(f.vocab.get('thermocycler', []), txt):
            model = m.group(0).replace('®', '').strip()
            f.add(pcr_term(pre, 'thermocycler'), f'{e.maker}, {model}' if e.maker else model, s, 'a thermocycler named in the methods',
                  span=m.span())
        for e, m in find_named(f.vocab.get('qpcr_software', []), txt):
            f.add(pcr_term(pre, 'pcr_analysis_software'), f'{e.maker} {e.name}' if e.maker else e.name, s,
                  'qPCR or ddPCR analysis software named in the methods', span=m.span())
        # Inhibition
        m = re.search(r'inhibit', txt, re.I)
        if m and re.search(r'test|assess|screen|determin|check|free\s+of|dilution|spike', txt, re.I):
            f.add('inhibition_check_0_1', '1', s, 'the methods describe a test for PCR inhibition')
            f.add('inhibition_check', txt, s, 'the sentence that describes the test for PCR inhibition')
    if any(PCR_WORDS.search(s.text) and re.search(r'\bPCR|\bqPCR', s.text) for s in sents):
        s = next(s for s in sents if re.search(r'\bPCR|\bqPCR', s.text))
        f.add('pcr_0_1', '1', s, 'the methods describe PCR')


# ------------------------------------------------------------------ library preparation and sequencing

def rule_library(f):
    sents = f.lab()
    instruments = []
    for s in sents:
        txt = s.text
        # How the samples were indexed
        if re.search(r'two[- ]step|second[- ]stage|second[- ]round|first[- ]stage|index(?:ing)?\s+PCR', txt, re.I) and \
                re.search(r'PCR|librar|index', txt, re.I):
            f.add('barcoding_pcr_appr', 'two-step PCR', s, 'the methods describe a second PCR that adds the indexes')
        elif re.search(r'single[- ]step|one[- ]step|fusion[- ]?tag|fusion\s+PCR|fusion\s+primers?|MID[- ]tag\w*\s+(?:q?PCR|primers?)',
                       txt, re.I):
            f.add('barcoding_pcr_appr', 'one-step PCR', s, 'the indexes are part of the PCR primers (one PCR)')
        elif re.search(r'ligation[- ]based|ligat\w+\s+(?:of\s+)?(?:the\s+)?adapt', txt, re.I):
            f.add('barcoding_pcr_appr', 'ligation-based', s, 'the adapters are ligated to the amplicons')
        # Instrument and platform
        if re.search(r'sequenc|platform|flow\s*cell|run\b|librar|\bkit\b', txt, re.I):
            for e, m in find_named(f.vocab.get('instrument', []), txt):
                value = f'{e.name} [{e.extra}]' if e.extra else e.name
                note = '' if e.extra else ('FAIRe asks for the instrument with its OBI identifier in brackets, '
                                           'such as Illumina MiSeq [OBI_0002003]; the tool has none for this one')
                if e.name in ('Illumina NovaSeq', 'Illumina NextSeq', 'Illumina HiSeq'):
                    note = 'the model is not given: give it if you know it'
                f.add('instrument', value, s, 'a sequencing instrument named in the methods', note, span=m.span())
                if e.uses:
                    f.add('platform', e.uses[0], s, 'the platform of the instrument named in the methods')
                instruments.append(e)
            if not instruments and re.search(r'\bIllumina\b', txt) and re.search(r'sequenc', txt, re.I):
                f.add('platform', 'ILLUMINA', s, 'the methods name Illumina sequencing')
        # Sequencing kit
        spans = []
        for m in SEQ_KIT.finditer(txt):
            if spans and m.start() - spans[-1][1] <= 3:
                spans[-1][1] = m.end()
            else:
                spans.append([m.start(), m.end()])
        for a, b in spans:
            f.add('seq_kit', kit_phrase(txt, a, b), s, 'a sequencing kit or flow cell named in the methods', span=(a, b))
        # Read layout
        if re.search(r'paired[- ]end|\b2\s*[x×]\s*\d{2,3}\b', txt, re.I) and re.search(r'sequenc|reads?|kit|cycle', txt, re.I):
            f.add('lib_layout', 'paired end', s, 'the methods describe paired-end reads')
        elif re.search(r'single[- ](?:end|read)|\b1\s*[x×]\s*\d{2,3}\b', txt, re.I):
            f.add('lib_layout', 'single end', s, 'the methods describe single-end reads')
        # Where the sequencing was done
        for e, m in find_named(f.vocab.get('facility', []), txt):
            if re.search(r'sequenc|sent|platform|housed|run', txt, re.I):
                f.add('sequencing_location', e.name, s, 'a sequencing facility named in the methods', span=m.span())
        # Library checks: size selection, clean-up, quantification, pooling
        if re.search(r'size[- ]selec|Pippin|purif|clean(?:ed)?(?:[- ]up)?\b|AMPure|bead|quantif|Qubit|TapeStation|Bioanalyzer|'
                     r'equimolar|normali[sz]ed\s+(?:prior|before)', txt, re.I) and re.search(r'librar|amplicon|pool', txt, re.I) \
                and not re.search(r'rarefi|subsampl|dataset', txt, re.I):
            f.add('lib_screen', txt, s, 'a sentence about checking, cleaning or pooling the libraries')
        if re.search(r'\bMD5\b', txt):
            f.add('checksum_method', 'MD5', s, 'the methods name MD5 checksums')
        elif re.search(r'SHA-?256', txt):
            f.add('checksum_method', 'SHA-256', s, 'the methods name SHA-256 checksums')
        if re.search(r'\bPhiX\b', txt, re.I):
            f.add('seq_method_additional', txt, s, 'the methods name a PhiX spike-in')


SEQ_KIT = re.compile(
    r'(?:\d{2,4}[\s-]*cycles?\b[^.;()]{0,30}?(?:kit|flow\s*cell|cartridge|chemistry|\bv[1-3]\b(?:\.\d)?))|'
    r'(?:(?:kit|flow\s*cell)[^.;()]{0,15}?\d{2,4}[\s-]*cycles?\b)|'
    r'(?:\b(?:P[1-4]|SP|S[124]|XLEAP|Nano|Micro|Mid[- ]Output|High[- ]Output|Standard)\s+(?:Reagent\s+)?(?:kit|flow\s*cell)\b'
    r'(?:\s*\(\s*\d{2,4}\s*cycles?\s*\))?)|'
    r'(?:\b(?:MiSeq|NextSeq|NovaSeq|iSeq|MiniSeq|HiSeq)[®™]?\s*[-‐–]?\s*(?:Reagent\s+)?(?:Kit\s+)?v[1-3](?:\.\d)?\b'
    r'(?:[^.;()]{0,20}?\bkit\b)?)|'
    r'(?:\bSQK-[A-Z0-9-]+\b)|(?:\b(?:Ligation|Native\s+Barcoding|Rapid\s+Barcoding)\s+(?:Sequencing\s+)?Kit\b)', re.I)


def kit_phrase(txt, a, b):
    """The words around a sequencing kit's match: the whole parenthesis it sits in, or the match with
    the instrument and kit words before it."""
    open_ = txt.rfind('(', 0, a)
    if open_ != -1 and txt.find(')', open_) >= b and ')' not in txt[open_:a]:
        return txt[open_ + 1:txt.find(')', open_)].strip()
    start = a
    before = re.search(r'((?:(?:Illumina|MiSeq|NextSeq|NovaSeq|iSeq|MiniSeq|HiSeq|\d{3,4}|v[1-3]|V[1-3])[®™]?\s+){1,3})$',
                       txt[:start])
    if before:
        start = before.start(1)
    return txt[start:b].strip()


# ------------------------------------------------------------------ bioinformatics

STAGE_WORDS = {
    'trim': r'\btrim|adapt[eo]rs?\b.{0,30}remov|primers?\s+(?:sequences?\s+)?(?:were|was)\s+(?:removed|trimmed)|'
            r'remov\w*\s+(?:the\s+)?(?:primers?|adapt)|clip',
    'demux': r'demultiplex|de-multiplex|sorted\b.{0,40}\bback|assigned\s+to\s+(?:their|each|the)\s+(?:respective\s+)?samples?|'
             r'ngsfilter|obisplit',
    'merge': r'\bmerg|paired[- ]end\s+reads?\s+(?:were\s+)?(?:joined|assembled|overlapped)|\bjoin|overlap|illuminapairedend|'
             r'fastq_mergepairs|mergePairs',
    'filter': r'quality[- ]?(?:filter|control|trim|check)|\bfiltered\b|maxEE|expected\s+errors?|phred|quality\s+scores?|'
              r'minimum\s+(?:sequence\s+|read\s+)?length|minlen',
    'denoise': r'denois|\bASVs?\b|\bZOTUs?\b|\bzOTUs?\b|\bESVs?\b|amplicon\s+sequence\s+variants?|unoise',
    'cluster': r'\bclust',
    'chimera': r'chim[ae]r|bimera|uchime',
    'taxonomy': r'taxonom(?!ic\s+units?)|\bBLAST|classif|queried|\bquery\b|reference\s+(?:database|library|sequences)|assign',
    'collapse': r'lowest\s+common\s+ancestor|\bLCA\b',
    'curation': r'curat|\bLULU\b|tag[- ]?jump|cross[- ]?talk',
    'decontam': r'contamin|\bblanks?\b|negative\s+controls?',
    'normalise': r'rarefi|rarefaction|subsampl|normali[sz]',
}
STAGE_TERMS = {'trim': ['trim_method'], 'demux': ['demux_tool'], 'merge': ['merge_tool'],
               'filter': ['error_rate_tool', 'min_len_tool'], 'denoise': ['otu_clust_tool'], 'cluster': ['otu_clust_tool'],
               'chimera': ['chimera_check_method'], 'taxonomy': ['otu_seq_comp_appr']}
TOOL_FOUND_BY = {'trim_method': 'software for trimming named in this sentence',
                 'demux_tool': 'software for demultiplexing named in this sentence',
                 'merge_tool': 'software for merging paired reads named in this sentence',
                 'error_rate_tool': 'software for quality filtering named in this sentence',
                 'min_len_tool': 'software for length filtering named in this sentence',
                 'otu_clust_tool': 'software for denoising or clustering named in this sentence',
                 'chimera_check_method': 'software for removing chimeras named in this sentence',
                 'otu_seq_comp_appr': 'software for comparing sequences with the reference named in this sentence'}


def tools_in(f, s):
    """The software named in a sentence, with versions, and commands grouped under their program:
    [(entry, label)]."""
    named = find_named(f.vocab.get('software', []), s.text)
    by_name = {e.name: (e, m) for e, m in named}
    out = []
    for e, m in named:
        if e.parent and e.parent in by_name:
            continue
        label = e.name + ((' ' + version_after(s.text, m.end())) if version_after(s.text, m.end()) else '')
        cmds = [c.name for c, _ in named if c.parent == e.name]
        if cmds:
            label += f" ({', '.join(cmds)})"
        if e.parent:
            label = f'{e.parent} {label}'
            e = Entry(e.kind, e.name, e.regex, e.maker, e.extra, e.uses or (), e.parent)
        out.append((e, label, m))
    return out


def rule_bioinformatics(f):
    sents = f.sentences
    for i, s in enumerate(sents):
        txt = s.text
        stages = {k for k, rx in STAGE_WORDS.items() if re.search(rx, txt, re.I)}
        if not stages:
            continue
        tools = tools_in(f, s)
        # Which software did which step
        for stg in ('trim', 'demux', 'merge', 'filter', 'denoise', 'cluster', 'chimera', 'taxonomy'):
            if stg not in stages:
                continue
            names = [label for e, label, _ in tools if stg in (e.uses or ())]
            if not names:
                continue
            value = ', '.join(dict.fromkeys(names))
            for term in STAGE_TERMS[stg]:
                if term == 'min_len_tool' and not re.search(r'length|minlen', txt, re.I):
                    continue
                if term == 'error_rate_tool' and not re.search(r'quality|error|phred|maxEE', txt, re.I):
                    continue
                if term == 'otu_seq_comp_appr':
                    for e, label, m in tools:
                        if 'taxonomy' in (e.uses or ()):
                            f.add(term, label + tool_settings(txt, m), s, TOOL_FOUND_BY[term])
                    continue
                if term == 'chimera_check_method' and re.search(r'de\s?novo|denovo', txt, re.I):
                    value_c = 'de novo, ' + value
                    f.add(term, value_c, s, TOOL_FOUND_BY[term])
                    continue
                f.add(term, value, s, TOOL_FOUND_BY[term])
        if 'taxonomy' in stages:
            for e, label, m in tools:
                if 'taxonomy' in (e.uses or ()) and e.extra:
                    f.add('tax_assign_cat', e.extra, s, f'{e.name} assigns taxonomy by {e.extra}')
        if 'trim' in stages and re.search(r'custom\s+(?:R|Python|Perl|bash|shell)?\s*script', txt, re.I) and not tools:
            m = re.search(r'custom\s+(?:R|Python|Perl|bash|shell)?\s*script', txt, re.I)
            f.add('trim_method', m.group(0), s, 'a custom script used for trimming')
            if 'demux' in stages:
                f.add('demux_tool', m.group(0), s, 'a custom script used for demultiplexing')
        # Pipelines
        for e, m in find_named(f.vocab.get('pipeline', []), txt):
            urls = re.findall(r'https?://\S+|github\.com/\S+', txt)
            value = urls[0].rstrip('.,;)') if urls else (e.extra or e.name)
            f.add('sop_bioinformatics', value, s, f'the {e.name} pipeline named in the methods', span=m.span())
        # Settings
        for m in re.finditer(r'(?:minimum|min\.?)\s+(?:sequence\s+|read\s+|amplicon\s+)?length\s*(?:of|=|was|:)?\s*(\d+)|'
                             r'minlen\s*=\s*(\d+)|(?:shorter|less)\s+than\s+(\d+)\s*(?:bp|nt|bases)', txt, re.I):
            f.add('min_len_cutoff', next(g for g in m.groups() if g), s, 'a minimum read length', span=m.span())
        for m in re.finditer(r'(?:maximum|max\.?)\s+(?:number\s+of\s+)?expected\s+errors?\s*(?:of|=|was|:|\()?\s*(\d+(?:\.\d+)?)|'
                             r'maxEE\s*=?\s*(?:c\()?\s*(\d+(?:\.\d+)?)', txt, re.I):
            f.add('error_rate_type', 'expected error rate', s, 'a maximum number of expected errors', span=m.span())
            f.add('error_rate_cutoff', num(m.group(1) or m.group(2)), s, 'a maximum number of expected errors',
                  span=m.span())
        for m in re.finditer(r'(?:phred|quality)\s+(?:quality\s+)?score\s*(?:of|was\s+set\s+(?:at|to)|=|:|>|≥|above|below)?\s*'
                             r'(?:of\s+)?(\d{1,2})\b|\bQ(\d{2})\b', txt, re.I):
            f.add('error_rate_type', 'Phred score', s, 'a minimum quality (Phred) score', span=m.span())
            f.add('error_rate_cutoff', m.group(1) or m.group(2), s, 'a minimum quality (Phred) score', span=m.span())
        for m in re.finditer(r'minimum\s+(?:overlap|alignment)\s*(?:length\s*)?(?:of|=|was|:)?\s*(\d+)|'
                             r'overlap\s+of\s+(?:at\s+least\s+)?(\d+)\s*(?:bp|nt|bases)', txt, re.I):
            f.add('merge_min_overlap', m.group(1) or m.group(2), s, 'a minimum overlap for merging paired reads',
                  span=m.span())
        for m in re.finditer(NUMBER + r'\s+(?:primer\s+)?mismatch(?:es)?\s+(?:allowed\s+)?(?:in|at|for|within)\s+(?:the\s+)?'
                             r'([\w-]+(?:\s+[\w-]+)?)|(?:allowing|allowed|maximum(?:\s+of)?)\s+(?:for\s+)?(?:up\s+to\s+)?'
                             + NUMBER + r'\s+(primer\s+)?mismatch(?:es)?(?:\s+(?:in|at|for|within)\s+(?:the\s+)?([\w-]+(?:\s+[\w-]+)?))?',
                             txt, re.I):
            n = m.group(1) or m.group(3)
            where = ' '.join(x for x in (m.group(2), m.group(4), m.group(5)) if x)
            if re.search(r'primer', where, re.I):
                f.add('trim_param', f'{num(as_number(n))} mismatches allowed in the primers', s,
                      'mismatches allowed in the primer sequences', span=m.span())
            elif re.search(r'tag|index|barcode|MID', where + ' ' + txt[max(0, m.start() - 40):m.end() + 40], re.I):
                f.add('demux_max_mismatch', num(as_number(n)), s, 'mismatches allowed in the index or tag sequences',
                      span=m.span())
        # Clustering threshold, or ASVs (not clustered)
        cl = re.search(r'clust\w*[^.;]{0,60}?(\d{2,3}(?:\.\d+)?)\s*%|(\d{2,3}(?:\.\d+)?)\s*%\s+(?:sequence\s+)?'
                       r'(?:similarity|identity)[^.;]{0,40}clust', txt, re.I)
        if cl:
            f.add('otu_clust_cutoff', num(cl.group(1) or cl.group(2)), s, 'the similarity threshold for clustering',
                  span=cl.span())
        elif 'denoise' in stages and re.search(r'denois|unoise', txt, re.I):
            f.add('otu_clust_cutoff', '100', s, 'the reads were denoised into ASVs or ZOTUs, which are not clustered',
                  'FAIRe gives 100% for ASVs')
        # Low-abundance filter
        for m in re.finditer(r'minimum\s+(?:abundance|size|read\s+count|number\s+of\s+reads)\s*(?:of|=|was)?\s*(\d+)|'
                             r'minsize\s*=?\s*(\d+)|(?:fewer|less)\s+than\s+(\d+)\s+(?:reads|copies|sequences)', txt, re.I):
            f.add('min_reads_cutoff', m.group(1) or m.group(2) or m.group(3), s, 'a minimum number of reads',
                  span=m.span())
            f.add('min_reads_cutoff_unit', 'reads', s, 'a minimum number of reads')
            for e, label, _ in tools:
                f.add('min_reads_tool', label, s, 'software named with the minimum number of reads')
        if re.search(r'singletons?\b[^.]{0,60}(?:removed|discarded|excluded)|(?:removed|discarded|excluded)[^.]{0,40}singletons?',
                     txt, re.I):
            f.add('min_reads_cutoff', '2', s, 'singletons (one read) were removed', 'singletons removed: at least 2 reads')
            f.add('min_reads_cutoff_unit', 'reads', s, 'singletons (one read) were removed')
        # Reference databases
        if 'taxonomy' in stages or re.search(r'database|library', txt, re.I):
            dbs = []
            for e, m in find_named(f.vocab.get('database', []), txt):
                v = e.name + db_version(txt, m.end())
                dbs.append(v)
            custom = re.search(r'(?:custom|in[- ]house|local|curated|own)\s+(?:[\w-]+\s+){0,5}?(?:reference\s+|barcode\s+)?'
                               r'(?:database|library|db)\b', txt, re.I)
            if custom and len(txt.split()) >= 8:
                dbs.append('custom')
                f.add('otu_db_custom', txt, s, 'a custom reference database described in this sentence')
            if dbs and ('taxonomy' in stages or custom):
                f.add('otu_db', ' | '.join(dict.fromkeys(dbs)), s, 'reference databases named in this sentence')
        # Identity and coverage thresholds
        for m in re.finditer(r'(?:minimum|min\.?)\s+(?:percentage\s+|percent\s+|%\s*)?(?:sequence\s+)?identity\s*(?:match\s+)?'
                             r'(?:of|=|was|:)?\s*(\d{2,3}(?:\.\d+)?)|perc_identity\s+(\d{2,3})|'
                             r'(\d{2,3}(?:\.\d+)?)\s*%\s+(?:sequence\s+)?(?:identity|similarity)(?:\s+match)?|'
                             r'identity\s+(?:threshold|cut-?off)\s+(?:of\s+)?(\d{2,3}(?:\.\d+)?)', txt, re.I):
            if re.search(r'clust', txt[max(0, m.start() - 60):m.end() + 40], re.I):
                continue
            v = num(next(g for g in m.groups() if g))
            near = txt[max(0, m.start() - 80):m.end() + 30]
            if re.search(r'species', near, re.I):
                f.add('tax_class_id_cutoff', v, s, 'a minimum identity for a species-level assignment', span=m.span(),
                      note='the threshold for a species-level assignment; FAIRe asks for the minimum identity '
                           'for any assignment, and the species threshold can go in tax_class_other')
                f.add('tax_class_other', txt, s, 'a sentence about the threshold for a species-level assignment')
            else:
                f.add('tax_class_id_cutoff', v, s, 'a minimum identity for a taxonomic assignment', span=m.span())
        for m in re.finditer(r'(?:query\s+coverage|qcov(?:_hsp_perc|s)?)\s*(?:\(qcov\)\s*)?(?:of|=|was|:)?\s*(\d{2,3}(?:\.\d+)?)|'
                             r'(\d{2,3}(?:\.\d+)?)\s*%\s+(?:query\s+)?coverage', txt, re.I):
            f.add('tax_class_query_cutoff', num(m.group(1) or m.group(2)), s, 'a minimum query coverage', span=m.span())
        if 'collapse' in stages and ('taxonomy' in stages or re.search(r'collaps|assign', txt, re.I)):
            f.add('tax_class_collapse', txt, s, 'a sentence about collapsing assignments to the lowest common ancestor')
        # Screening the taxa
        if re.search(r'\b(?:blanks?|negative\s+controls?|NTCs?|field\s+controls?|extraction\s+controls?)\b', txt, re.I) and \
                re.search(r'removed|subtract|exclud|discard|filtered|threshold|decontam|deducted', txt, re.I) and \
                re.search(r'ASV|OTU|ZOTU|reads?|taxa|sequences', txt, re.I):
            f.add('screen_contam_method', txt, s, 'a sentence about removing taxa or reads found in the controls')
        if re.search(r'distribution|geographic|biogeograph|\brange\b|occur', txt, re.I) and \
                re.search(r'FishBase|WoRMS|\bOBIS\b|\bGBIF\b|Atlas\s+of\s+Living\s+Australia|\bALA\b|Fishes\s+of\s+Australia|'
                          r'checklists?|checked|https?://', txt, re.I):
            f.add('screen_geograph_method', txt, s, 'a sentence about checking the taxa against their known distribution')
        if re.search(r'non[- ]?target|off[- ]target|\bhumans?\b|domestic|livestock', txt, re.I) and \
                re.search(r'removed|exclud|discard|filtered', txt, re.I):
            f.add('screen_nontarget_method', txt, s, 'a sentence about removing taxa the study did not target')
        if 'curation' in stages and re.search(r'LULU|tag[- ]?jump|cross[- ]?talk|UNCROSS|pseudogene', txt, re.I):
            f.add('bioinfo_method_additional', txt, s, 'a sentence about curating the ASVs or OTUs')
        if 'normalise' in stages and re.search(r'rarefi|rarefaction|subsampl', txt, re.I):
            f.add('bioinfo_method_additional', txt, s, 'a sentence about rarefying the reads')


def tool_settings(txt, m):
    """The settings written after a tool's name in parentheses, such as BLASTn (minimum percentage
    identity of 85%, query coverage of 96%)."""
    rest = txt[m.end():]
    v = re.match(r'\s*(\((?:[^()]|\([^()]*\))*\))', rest)
    if v and re.search(r'%|\d|identity|coverage|-\w', v.group(1)) and not re.match(r'\(\s*[A-Z][a-z]+(?:\s+et\s+al|,)', v.group(1)):
        return ' ' + v.group(1)
    return ''


def db_version(txt, end):
    v = re.match(r'\s*(?:\(\s*)?(?:(?:release|version|v\.?|r)\s*(\d+(?:\.\d+)*\w*)|(\d+(?:\.\d+)+))', txt[end:], re.I)
    out = ''
    if v:
        out = ' ' + (v.group(1) or v.group(2))
    acc = re.search(r'\(?\s*(?:accessed|downloaded|retrieved)(?:\s+(?:in|on))?\s+([A-Z][a-z]+\s+)?(\d{4}(?:/\d{2,4})?)',
                    txt[end:end + 80])
    if acc:
        out += f" (accessed {(acc.group(1) or '')}{acc.group(2)})"
    return out


# ------------------------------------------------------------------ samples: collection, filtration, extraction, storage

def rule_samples(f):
    sents = f.lab()
    for s in sents:
        txt = s.text
        filt = re.search(r'filter|filtrat|membrane', txt, re.I)
        # Sampling device
        if re.search(r'collect|sampl|taken|using|from', txt, re.I):
            for e, m in find_named(f.vocab.get('device', []), txt):
                f.add('samp_collect_device', e.name, s, 'a sampling device named in the methods', span=m.span())
        # Volumes of water
        for m in re.finditer(r'(\d+(?:\.\d+)?|one|two|five|ten)[\s-]*(L|l|litres?|liters?|mL|ml|millilit(?:re|er)s?)\b'
                             r'(?!\s*(?:Niskin|bottle|Nalgene|container|of\s+(?:ATL|buffer|ethanol)))', txt):
            if not re.search(r'water|seawater|sample|replicate', txt[max(0, m.start() - 60):m.end() + 60], re.I):
                continue
            n = as_number(m.group(1))
            unit = 'L' if m.group(2).lower().startswith('l') else 'mL'
            near = txt[max(0, m.start() - 60):m.end() + 80]
            if re.search(r'filter', near, re.I):
                f.add('samp_vol_we_dna_ext', num(n), s, 'a volume of water filtered for DNA extraction', confused('samp_vol_we_dna_ext'),
                      span=m.span())
                f.add('samp_vol_we_dna_ext_unit', unit, s, 'the unit of the volume filtered')
            elif re.search(r'collect|sampled|taken|replicates?', txt, re.I):
                f.add('samp_size', num(n), s, 'a volume of water collected', confused('samp_size'), span=m.span())
                f.add('samp_size_unit', unit, s, 'the unit of the volume collected')
        if filt:
            for m in re.finditer(r'(\d+(?:\.\d+)?)\s*' + MU + r'm\b', txt):
                near = txt[max(0, m.start() - 15):m.end() + 25]
                if re.search(r'mesh|pre-?filter', near, re.I):
                    f.add('size_frac_low', num(m.group(1)), s, 'the mesh or pre-filter size (µm)', span=m.span())
                elif float(m.group(1)) <= 20:
                    f.add('size_frac', num(m.group(1)), s, 'the pore size of the filter (µm)', span=m.span())
            for m in re.finditer(r'(\d{2,3})\s*mm\b', txt):
                if 10 <= float(m.group(1)) <= 300:
                    f.add('filter_diameter', m.group(1), s, 'the diameter of the filter (mm)', span=m.span())
            mats = [('cellulose ester', r'(?:mixed\s+)?cellulose\s+(?:nitrate\s+)?esters?|\bMCE\b'),
                    ('polyethersulfone', r'polyethersulph?one|\bPES\b'), ('nylon', r'\bnylon\b'),
                    ('glass fiber', r'glass[- ]fib(?:re|er)|\bGF/[CDF]\b'),
                    ('track etched polycarbonate', r'polycarbonate'), ('other: PVDF', r'\bPVDF\b|polyvinylidene')]
            for value, rx in mats:
                m = re.search(rx, txt, re.I)
                if m:
                    f.add('filter_material', value, s, 'the material of the filter', span=m.span())
            for e, m in find_named(f.vocab.get('filter', []), txt):
                f.add('filter_name', f'{e.name} ({e.maker})' if e.maker else e.name, s, 'a filter named in the methods',
                      span=m.span())
                if e.extra:
                    f.add('filter_material', e.extra, s, f'{e.name} filters are {e.extra}')
            if re.search(r'filtered|filtration|filtering', txt, re.I):
                if re.search(r'\bpump|peristaltic|vacuum|syringe', txt, re.I):
                    f.add('filter_passive_active_0_1', '1', s, 'the water was pumped or pushed through the filter (active)')
                elif re.search(r'passive', txt, re.I):
                    f.add('filter_passive_active_0_1', '0', s, 'passive filtration')
                if re.search(r'(?:filtered|filtering)\s+(?:\w+\s+){0,6}?(?:through|across|onto|using|with)|filtration\s+(?:was|through)',
                             txt, re.I):
                    f.add('samp_mat_process', txt, s, 'a sentence about how the samples were filtered')
        # Storage of the samples (not of the DNA)
        if not re.search(r'\bextracts?\b|\bDNA\s+(?:was|were)\s+(?:stored|kept)|eluted', txt, re.I):
            for m in re.finditer(r'(?:stored|frozen|kept|preserved|held|transported)\s+(?:\w+\s+){0,3}?(?:at|in\s+a)\s+' + TEMP,
                                 txt, re.I):
                clause = txt[max(0, m.start() - 120):m.start()]
                if re.search(r'membranes?|filters?\b|filtrate|filtered|post-filter|after\s+filtration', clause + ' ' + txt[:40],
                             re.I) and \
                        not re.search(r'(?:before|prior\s+to|until)\s+(?:being\s+)?filt|filtered\s+within', txt, re.I):
                    f.add('prepped_samp_store_temp', temp_value(m.group(1), m.group(2)), s,
                          'the temperature the filters were stored at after filtering', span=m.span())
                else:
                    f.add('samp_store_temp', temp_value(m.group(1), m.group(2)), s,
                          'the temperature the samples were stored at',
                          'FAIRe asks for the storage temperature before any processing (filtering, say); the storage '
                          'temperature after it goes in prepped_samp_store_temp', span=m.span())
            m = re.search(r'(?:preserved|stored|fixed|immersed)\s+(?:\w+\s+){0,3}?in\s+(?:\w+\s+){0,3}?'
                          r"(Longmire['’]?s?(?:\s+(?:buffer|solution))?|ethanol|RNAlater|lysis\s+buffer|sodium\s+acetate)", txt, re.I)
            if m:
                word = m.group(1).lower()
                value = ('longmire' if word.startswith('longmire') else 'ethanol' if word == 'ethanol' else
                         'lysis buffer' if 'lysis' in word else 'sodium acetate' if 'acetate' in word else 'other: RNAlater')
                f.add('samp_store_sol', value, s, 'what the samples were preserved in', span=m.span())
        # DNA extraction
        if re.search(r'extract|isolat|purif|lys', txt, re.I):
            for e, m in find_named(f.vocab.get('extraction_kit', []), txt):
                value = f'{e.name} ({e.maker})' if e.maker else e.name
                f.add('nucl_acid_ext_kit', value, s, 'an extraction kit named in the methods', span=m.span())
                if e.extra:
                    f.add('nucl_acid_ext_sep', e.extra, s, f'the {e.name} separates DNA by {e.extra.replace("other: ", "")}')
            if re.search(r'proteinase\s*K', txt, re.I):
                f.add('nucl_acid_ext_lysis', 'enzymatic', s, 'Proteinase K digests the cells (enzymatic lysis)')
            if re.search(r'bead[- ]?beat|TissueLyser|bead\s+mill|homogeni[sz]ed\s+(?:for|at|using|with)', txt, re.I):
                f.add('nucl_acid_ext_lysis', 'physical', s, 'the cells were broken by bead beating (physical lysis)')
            if re.search(r'magnetic\s+beads?', txt, re.I):
                f.add('nucl_acid_ext_sep', 'magnetic beads', s, 'the DNA was separated with magnetic beads')
            elif re.search(r'silica\s+(?:column|membrane)|spin\s+column', txt, re.I):
                f.add('nucl_acid_ext_sep', 'column-based', s, 'the DNA was separated on a silica column')
            for e, m in find_named(f.vocab.get('cleanup_kit', []), txt):
                f.add('dna_cleanup_0_1', '1', s, 'a DNA clean-up kit named in the methods')
                f.add('dna_cleanup_method', f'{e.name} ({e.maker})' if e.maker else e.name, s,
                      'a DNA clean-up kit named in the methods', span=m.span())
    # Changes to the extraction kit's protocol: the sentence that says so, and the sentences after it
    # that give the changes.
    for i, s in enumerate(sents):
        if re.search(r'modif', s.text, re.I) and re.search(r'extract|protocol|kit', s.text, re.I) and \
                not re.search(r'primer|(?<!pre-)(?<!pre)\bPCR', s.text):
            m = re.search(r'modifications?\s*(?:to\s+the\s+manufacturer[’\']?s\s+protocol)?\s*[:;–-]\s*(.+)$', s.text, re.I)
            parts, extra = [m.group(1)] if m and len(m.group(1)) > 20 else [], []
            for nxt in sents[i + 1:i + 4]:
                if re.search(r'digest|lysis|buffer|proteinase|elut|incubat|\bbead|\bATL\b|\bAL\b|\bAE\b|\bEB\b|cut\s+into', nxt.text, re.I):
                    parts.append(nxt.text)
                    extra.append(nxt)
                else:
                    break
            if parts:
                f.add('nucl_acid_ext_modify', ' '.join(parts), s, 'the changes made to the extraction kit\'s protocol',
                      extra=extra)
    # Field and laboratory hygiene
    for s in f.sentences:
        if re.search(r'bleach|hypochlorite|steril[iy]s|decontaminat|\bUV\b|DNA\s?Away|ELIMINase', s.text, re.I) and \
                not s.reference_work:
            f.add('sterilise_method', s.text, s, 'a sentence about cleaning equipment or preventing contamination')


def confused(term):
    """The commonly-confused-terms check for a term, as a note."""
    try:
        lines = [ln for ln in CONFUSED.read_text(encoding='utf-8').splitlines() if ln and not ln.startswith('#')]
    except OSError:
        return ''
    rows = list(csv.DictReader(lines, delimiter='\t'))
    group = next((r['group'] for r in rows if term in [t.strip() for t in r['term'].split(',')]), None)
    check = ' '.join(r['check'] for r in rows if r['group'] == group and r.get('check'))
    return f'People often mix this term up with others: {check}' if check else ''


# ------------------------------------------------------------------ checklist and output

def load_terms(checklist, assay_type=None):
    """FAIRe terms by name: (section, requirement code, description, unit, sheet), in checklist order."""
    import pandas as pd
    d = pd.read_excel(checklist, sheet_name='checklist', dtype=str).fillna('')
    terms = OrderedDict()
    for r in d.to_dict('records'):
        sec = r['section']
        if assay_type == 'metabarcoding' and sec == 'Targeted assay detection':
            continue
        if assay_type == 'targeted' and sec in ('Library preparation sequencing', 'Bioinformatics'):
            continue
        sheet = 'projectMetadata' if r['data_type'].strip() == 'projectMetadata' else 'sampleMetadata'
        terms[r['term_name']] = dict(section=sec, level=r['requirement_level_code'], description=r['description'],
                                     unit=r['unit'], sheet=sheet, vocab=r['controlled_vocabulary_options'])
    return terms


def find(texts, vocab, assay_names=(), whole_text=False):
    """Proposals from the methods texts: (proposals, notes on what was read)."""
    sentences, read = [], []
    for label, text in texts:
        part, where = (text, 'the whole text') if whole_text else methods_part(text)
        read.append(f'{label}: {where}')
        for s in split_sentences(part, label):
            s.index = len(sentences)
            sentences.append(s)
    f = Finder(sentences, vocab, assay_names)
    rule_samples(f)
    rule_pcr(f)
    rule_library(f)
    rule_bioinformatics(f)
    return f.out, read, sentences


def tidy(proposals, terms):
    """One row per term and value (and assay), the first sentence kept, others counted; a note on
    each term found with different values."""
    seen = OrderedDict()
    for p in proposals:
        if p.term not in terms:
            continue
        key = (p.term, re.sub(r'\s+', ' ', p.value.lower()), p.assay)
        if key in seen:
            seen[key].others += 1
            continue
        seen[key] = p
    rows = []
    joined = {}
    for p in seen.values():
        if p.term in DESCRIPTION_TERMS:
            key = (p.term, p.assay)
            if key in joined:
                first = joined[key]
                if p.value not in first.value:
                    first.value += ' ' + p.value
                    first.extra_sentences.append(p.sentence)
                continue
            joined[key] = p
        rows.append(p)
    for p in joined.values():
        n = 1 + len(p.extra_sentences)
        if n > 1:
            p.found_by = f'{n} sentences: {p.found_by}'
            p.note = 'several sentences joined: shorten to what describes your eDNA samples'
    # An instrument named without its model ("the Illumina NovaSeq") once the model is known
    models = [p.value for p in rows if p.term == 'instrument']
    rows = [p for p in rows
            if not (p.term == 'instrument' and any(v != p.value and v.startswith(p.value + ' ') for v in models))]
    counts = {}
    for p in rows:
        counts[p.term] = counts.get(p.term, 0) + 1
    for p in rows:
        if counts[p.term] > 1:
            extra = (f'{counts[p.term]} different values found for this term: keep the one that applies to your '
                     'eDNA samples (for each assay, if they differ), and reject the others')
            p.note = f'{extra}. {p.note}' if p.note else extra
    order = {t: i for i, t in enumerate(terms)}
    sec_order = {s: i for i, s in enumerate(SECTION_NAMES)}
    rows.sort(key=lambda p: (sec_order.get(terms[p.term]['section'], 99), order[p.term], p.sentence.index))
    return rows


def excerpt(p, limit=500):
    if p.term in DESCRIPTION_TERMS and p.value.startswith(p.sentence.text[:60]):
        return 'The proposed value is the sentences themselves.'
    texts = [p.sentence.text] + [x.text for x in p.extra_sentences]
    t = ' '.join(texts)
    if len(t) <= limit:
        return t
    if p.span:
        a = max(0, p.span[0] - 200)
        return ('…' if a else '') + t[a:a + limit] + '…'
    return t[:limit] + '…'


COLUMNS = ['section', 'term', 'value', 'assay', 'evidence', 'found_by', 'note', 'status', 'source']


def write_tsv(rows, terms, path):
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, delimiter='\t', lineterminator='\n')
        w.writerow(COLUMNS)
        for p in rows:
            w.writerow([SECTION_NAMES.get(terms[p.term]['section'], terms[p.term]['section']), p.term, clean(p.value),
                        p.assay, clean(excerpt(p)), p.found_by + (f' (and {p.others} more sentences)' if p.others else ''),
                        clean(p.note), 'review', p.sentence.source])


def clean(v):
    return re.sub(r'\s+', ' ', str(v)).strip()


def missing_terms(rows, terms):
    """The method terms not found: project terms of the PCR, library and bioinformatics sections, the
    hygiene term and the sample terms the rules look for, mandatory to recommended, without the
    primer terms."""
    found = {p.term for p in rows}
    out = []
    for name, t in terms.items():
        if name in found or name in PRIMER_TERMS or name.startswith('probe') or t['level'] not in ('M', 'HR', 'R'):
            continue
        if (t['sheet'] == 'projectMetadata' and t['section'] in METHOD_SECTIONS) or name == 'sterilise_method' or \
                name in SAMPLE_TERMS:
            out.append(name)
    sec_order = {s: i for i, s in enumerate(SECTION_NAMES)}
    order = {t: i for i, t in enumerate(terms)}
    return sorted(out, key=lambda n: (sec_order.get(terms[n]['section'], 99), order[n]))


REVIEW_HEADERS = ['Section', 'FAIRe term', 'What FAIRe asks for', 'Proposed value', 'Assay', 'From the methods',
                  'How it was found', 'Note', "Reviewer's decision", 'Your value']
SHEET = 'Method details'


def write_review_sheet(rows, terms, path, read, label):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET
    ws.append(REVIEW_HEADERS)
    found_fill = PatternFill('solid', fgColor='FFF7E6')
    for p in rows:
        t = terms[p.term]
        ws.append([SECTION_NAMES.get(t['section'], t['section']), p.term, asks(t), clean(p.value), p.assay,
                   clean(excerpt(p)), p.found_by + (f' (and {p.others} more sentences)' if p.others else ''),
                   clean(p.note), '', ''])
        for c in ws[ws.max_row][8:10]:
            c.fill = found_fill
    for name in missing_terms(rows, terms):
        t = terms[name]
        ws.append([SECTION_NAMES.get(t['section'], t['section']), name, asks(t), '', '', '',
                   'not found in the methods', '', '', ''])
    widths = [16, 26, 48, 50, 12, 70, 34, 40, 14, 30]
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(65 + i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical='top')
    for c in ws[1]:
        c.font = Font(bold=True)
        c.alignment = Alignment(wrap_text=True, vertical='top')
    ws.freeze_panes = 'C2'
    ws.auto_filter.ref = f'A1:J{ws.max_row}'
    dv = DataValidation(type='list', formula1='"Accept,Reject,Change"', allow_blank=True)
    dv.error = 'Choose Accept, Reject or Change'
    ws.add_data_validation(dv)
    dv.add(f'I2:I{max(2, ws.max_row)}')
    how = wb.create_sheet('How to review')
    lines = [
        f'Values for the whole study found in {label} by FAIRe mapper: find method details {__version__}.',
        'Read: ' + '; '.join(read) + '.',
        '',
        'The first rows are values the tool found, each with the sentence it came from. For each one, choose a '
        "Reviewer's decision:",
        '  Accept: the proposed value is right.',
        '  Change: the value is nearly right; write the right one in Your value.',
        '  Reject: the value does not apply (it may describe other work in the paper, or another assay).',
        'When a term has several values (two storage temperatures, say), keep the one that applies to your eDNA '
        'samples and reject the others. A value that holds for one assay only needs the assay name in Assay, '
        'as it is written in the other files (Fish16S, say).',
        '',
        'The rows after them are FAIRe method terms the tool did not find. If you know a value, write it in Your '
        'value: it is used as given. Leave the others empty.',
        '',
        'Rows with no decision and no value of your own are left out of the workbook, and apply mapping lists '
        'them. The sheet can be sorted and filtered: each row is read on its own.',
        '',
        'Give this sheet to FAIRe mapper: apply mapping as values for the whole project (with your other project '
        'values, if any). Project terms go to projectMetadata, and sample terms (filter, extraction and storage) '
        'are written for every sample, unless a column of your sample table gives them.',
        '',
        'The tool reads the methods by rules, not with a language model: it knows the instruments, kits, '
        'software and databases in its vocabulary and the usual ways methods state a value. It can miss values '
        'written in other ways, and it cannot tell which assay a value belongs to unless the sentence names it.']
    for ln in lines:
        how.append([ln])
    how.column_dimensions['A'].width = 120
    for row in how.iter_rows():
        row[0].alignment = Alignment(wrap_text=True, vertical='top')
    wb.save(path)


def asks(t):
    d = t['description'].strip()
    if t['unit'] and 'select from' not in t['unit'].lower() and 'unit' not in d.lower():
        d += f" Unit: {t['unit']}."
    if t['vocab'] and 'numeric value' not in t['vocab']:
        d += f" One of: {t['vocab']}."
    return d


def read_review_sheet(path):
    """The reviewed values of a review sheet from this tool, as dicts with term, value, assay and status:
    Accept gives the proposed value, Change or a value of your own gives yours, and a row with neither
    is left for review (apply mapping lists it)."""
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    if SHEET not in wb.sheetnames:
        raise SystemExit(f'ERROR: {Path(path).name} has no sheet called {SHEET}, so it is not a review sheet from find '
                         'method details')
    rows = list(wb[SHEET].iter_rows(values_only=True))
    if not rows:
        return []
    head = [str(h or '').strip() for h in rows[0]]
    need = ['FAIRe term', 'Proposed value', "Reviewer's decision", 'Your value']
    missing = [h for h in need if h not in head]
    if missing:
        raise SystemExit(f"ERROR: the {SHEET} sheet needs the columns {', '.join(missing)}")
    col = {h: head.index(h) for h in head if h}
    out = []
    for r in rows[1:]:
        def get(h):
            i = col.get(h)
            return '' if i is None or i >= len(r) or r[i] is None else str(r[i]).strip()
        term = get('FAIRe term')
        if not term:
            continue
        decision, proposed, yours = get("Reviewer's decision").lower(), get('Proposed value'), get('Your value')
        assay = get('Assay')
        if decision == 'reject':
            continue
        if decision == 'change' or (yours and decision != 'accept'):
            if yours:
                out.append(dict(term=term, value=yours, assay=assay, status='confirmed'))
            continue
        if decision == 'accept':
            if proposed:
                out.append(dict(term=term, value=proposed, assay=assay, status='confirmed'))
            continue
        if proposed:
            out.append(dict(term=term, value=proposed, assay=assay, status='review'))
    return out


def is_review_sheet(path):
    try:
        from openpyxl import load_workbook
        return SHEET in load_workbook(path, read_only=True).sheetnames
    except Exception:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('methods', nargs='+', help='methods text, markdown or PDF (one or more)')
    ap.add_argument('--label', action='append', help='a name for each methods file, as the user knows it')
    ap.add_argument('--checklist', required=True, help='FAIRe checklist (FAIRe_checklist_v1.0.2.xlsx)')
    ap.add_argument('--assay_type', choices=['metabarcoding', 'targeted'], default='metabarcoding')
    ap.add_argument('--assay_names', default='', help='assay names, separated by commas: a sentence that names one of '
                                                      'them gives its values to that assay')
    ap.add_argument('--vocabulary', default=str(VOCABULARY), help='table of named things (method_details/vocabulary.tsv)')
    ap.add_argument('--whole_text', action='store_true', help='read the whole text, not only its Methods section')
    ap.add_argument('-o', '--output', required=True, help='proposals (TSV)')
    ap.add_argument('--review_sheet', help='review sheet to write (Excel)')
    ap.add_argument('--version', action='version', version=__version__)
    args = ap.parse_args(argv)

    labels = args.label or []
    texts = []
    for i, p in enumerate(args.methods):
        label = labels[i] if i < len(labels) else Path(p).name
        text = ft.read_text(p)
        if not text.strip():
            raise SystemExit(f'ERROR: {label} has no text to read. A PDF of scanned pages holds pictures of the text: '
                             'save it as text first.')
        texts.append((label, text))
    vocab = load_vocabulary(args.vocabulary)
    terms = load_terms(args.checklist, args.assay_type)
    names = [a.strip() for a in args.assay_names.split(',') if a.strip()]
    proposals, read, sentences = find(texts, vocab, names, args.whole_text)
    rows = tidy(proposals, terms)
    write_tsv(rows, terms, args.output)
    label = ', '.join(t[0] for t in texts)
    if args.review_sheet:
        write_review_sheet(rows, terms, args.review_sheet, read, label)
    by_section = OrderedDict()
    for p in rows:
        sec = SECTION_NAMES.get(terms[p.term]['section'], terms[p.term]['section'])
        by_section.setdefault(sec, set()).add(p.term)
    print(f'FAIRe mapper: find method details {__version__}')
    for r in read:
        print(f'Read {r}: {sum(1 for s in sentences if s.source == r.split(": ")[0])} sentences.')
    print(f'{len(rows)} values proposed for {len({p.term for p in rows})} FAIRe terms:')
    for sec, ts in by_section.items():
        print(f"  {sec}: {', '.join(sorted(ts))}")
    print(f'{len(missing_terms(rows, terms))} other method terms not found (listed in the review sheet to fill in).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
