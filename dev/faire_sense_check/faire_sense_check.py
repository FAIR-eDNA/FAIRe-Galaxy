#!/usr/bin/env python3
"""FAIRe sense check: a one-page summary of a FAIRe workbook, to look over before it goes to a
repository.

It draws the data in a few small pictures (where and when the samples were taken, the samples and
controls, the reads, the taxa, the qPCR results) and lists the things that look wrong, so that a
large mistake shows at a glance. It does not replace the review of the workbook or FAIRe-fier.

Output: one self-contained HTML page (no web requests) and, if asked, a table of the flags (level,
area, message). Hovering over a mark shows what it is, with the rows of the samples behind it;
clicking it opens the chart's table at those rows. That needs the page's one small script; where
scripts are removed (as Galaxy may do), the browser's own tooltips show the same text.

Usage: python faire_sense_check.py WORKBOOK.xlsx -o sense_check.html [--flags flags.tsv]
"""
import argparse
import datetime as dt
import gzip
import html
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
from openpyxl.utils import get_column_letter

__version__ = '0.1.0'

HERE = Path(__file__).resolve().parent
COASTLINE = HERE / 'data' / 'ne_50m_land.json.gz'

MISSING_RE = re.compile(r'^(missing|not applicable|not collected|not provided|restricted access|unknown)\b', re.I)
RANKS = ['kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'specificEpithet']
RANK_LABEL = {'specificEpithet': 'species'}

# Colours (light, dark): categorical slots 1 to 3, and the status colours, from a validated palette
CSS_COLOURS = """
.page { color-scheme: light; --surface:#ffffff; --plane:#f9f9f9; --ink:#191919; --ink2:#666666;
  --grid:#e7e7e7; --axis:#c2c2c2; --border:rgba(11,11,11,0.10); --land:#ebe8e2; --sea:#f4f8fc;
  --s1:#257de0; --s2:#f47230; --s3:#00b894; --muted:#b5b5b5;
  --good:#0aac23; --warn:#fbb315; --serious:#f18a59; --critical:#dc3c3d; }
@media (prefers-color-scheme: dark) { .page { color-scheme: dark; --surface:#191919; --plane:#0b0b0b;
  --ink:#efefef; --ink2:#9c9c9c; --grid:#303030; --axis:#474747; --border:rgba(255,255,255,0.10);
  --land:#2e2c29; --sea:#151a20; --s1:#338ced; --s2:#e76624; --s3:#00a888; --muted:#5a5a5a; } }
"""

LEVELS = {'problem': ('Problem', 'critical', '▲'), 'check': ('Check', 'warn', '●'),
          'note': ('Note', 'muted', '○')}

# Taxa that often come from people, food or lab work
CONTAMINANTS = ['Homo sapiens', 'Bos taurus', 'Sus scrofa', 'Gallus gallus', 'Ovis aries', 'Capra hircus',
                'Canis lupus', 'Canis familiaris', 'Felis catus', 'Equus caballus', 'Meleagris gallopavo',
                'Mus musculus', 'Rattus norvegicus']

ANIMAL_PHYLA = {'Chordata', 'Arthropoda', 'Mollusca', 'Annelida', 'Cnidaria', 'Porifera', 'Echinodermata',
                'Nematoda', 'Platyhelminthes', 'Bryozoa', 'Rotifera', 'Nemertea', 'Ctenophora', 'Brachiopoda',
                'Chaetognatha', 'Sipuncula', 'Tardigrada', 'Hemichordata', 'Xenacoelomorpha', 'Gastrotricha',
                'Kinorhyncha', 'Entoprocta', 'Phoronida', 'Placozoa', 'Priapulida', 'Onychophora',
                'Acanthocephala', 'Nematomorpha', 'Cycliophora', 'Loricifera', 'Gnathostomulida', 'Echiura'}
FISH = {'Actinopteri', 'Actinopterygii', 'Chondrichthyes', 'Elasmobranchii', 'Holocephali', 'Teleostei',
        'Myxini', 'Petromyzonti', 'Hyperoartia', 'Cladistia', 'Sarcopterygii', 'Dipnoi', 'Actinistia'}
TARGET_WORDS = [  # words in targetTaxonomicAssay, and the taxa they mean
    ('teleost', 'class', {'Actinopteri', 'Actinopterygii', 'Teleostei'}),
    ('elasmobranch', 'class', {'Chondrichthyes', 'Elasmobranchii'}),
    ('shark', 'class', {'Chondrichthyes', 'Elasmobranchii'}),
    ('fish', 'class', FISH),
    ('mammal', 'class', {'Mammalia'}), ('bird', 'class', {'Aves'}), ('amphibian', 'class', {'Amphibia'}),
    ('reptile', 'class', {'Reptilia', 'Squamata', 'Lepidosauria', 'Testudines', 'Crocodylia'}),
    ('insect', 'class', {'Insecta'}), ('arthropod', 'phylum', {'Arthropoda'}),
    ('vertebrat', 'phylum', {'Chordata'}), ('metazoa', 'phylum', ANIMAL_PHYLA),
    ('animal', 'phylum', ANIMAL_PHYLA), ('invertebrat', 'phylum', ANIMAL_PHYLA - {'Chordata'}),
]

SEA_RE = re.compile(r'marine|ocean|\bsea\b|seawater|sea water|coastal|reef|sea ?grass|pelagic|benthic|intertidal', re.I)
LAND_RE = re.compile(r'terrestrial|soil|dust|\bair\b|indoor|building|forest|grassland|freshwater|fresh water|'
                     r'river|lake|stream|pond|wetland|cave|desert|farm|agricultur', re.I)


# ---------------------------------------------------------------------------------------------
# Small helpers

def esc(s):
    return html.escape(str(s), quote=True)


def missing(v):
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    s = str(v).strip()
    return s == '' or bool(MISSING_RE.match(s))


def num(v):
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def fmt(n):
    if n is None:
        return ''
    if abs(n) >= 1e6:
        return f'{n / 1e6:.1f}M'
    if abs(n) >= 1e4:
        return f'{n / 1e3:.0f}K'
    if float(n).is_integer():
        return f'{int(n):,}'
    return f'{n:,.1f}' if abs(n) >= 10 else f'{n:.2g}'


def plural(n, word, words=None):
    return f'{n:,} {word if n == 1 else (words or word + "s")}'


def listing(items, n=6):
    items = [str(i) for i in items]
    more = len(items) - n
    return ', '.join(items[:n]) + (f' and {more} more' if more > 0 else '')


class Flags:
    def __init__(self):
        self.items = []

    def add(self, level, area, message):
        self.items.append((level, area, message))

    def html(self):
        if not self.items:
            return ('<p class="allclear"><span class="ico good">✓</span> Nothing stood out. The pictures '
                    'below are still worth a look.</p>')
        order = {'problem': 0, 'check': 1, 'note': 2}
        out = ['<ul class="flags">']
        for level, area, msg in sorted(self.items, key=lambda x: order[x[0]]):
            label, colour, icon = LEVELS[level]
            out.append(f'<li class="{level}"><span class="ico {colour}" aria-hidden="true">{icon}</span>'
                       f'<span class="lvl">{label}</span><span class="area">{esc(area)}</span>'
                       f'<span class="msg">{esc(msg)}</span></li>')
        out.append('</ul>')
        return ''.join(out)

    def counts(self):
        c = Counter(level for level, _, _ in self.items)
        return c['problem'], c['check'], c['note']


# ---------------------------------------------------------------------------------------------
# Reading the workbook

class Workbook:
    def __init__(self, path):
        self.path = Path(path)
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        self.sheets = wb.sheetnames
        self._rows = {s: [list(r) for r in wb[s].iter_rows(values_only=True)] for s in wb.sheetnames
                      if s not in ('README', 'Drop-down values')}
        wb.close()
        self.project, self.project_levels, self.assays = self._project()
        self.samples, self.levels = self._table('sampleMetadata')
        self.runs, self.run_levels = self._table('experimentRunMetadata')
        self.amp, self.amp_levels = self._table('ampData')
        self.otus = self._otu_tables()
        self.sample_row = ({str(n): int(r) for n, r in zip(self.samples['samp_name'], self.samples['_row'])}
                           if len(self.samples) and 'samp_name' in self.samples else {})

    def row(self, name):
        r = self.sample_row.get(str(name))
        return f'row {r}' if r else 'not in sampleMetadata'

    def _project(self):
        rows = self._rows.get('projectMetadata', [])
        if not rows:
            return {}, {}, []
        head = rows[0]
        assay_cols = list(range(4, len(head)))
        names, listed = {}, []
        for r in rows[1:]:
            if len(r) > 2 and r[2] == 'assay_name':
                names = {i: str(r[i]).strip() for i in assay_cols if i < len(r) and not missing(r[i])}
                if len(r) > 3 and not missing(r[3]):
                    listed = [a.strip() for a in str(r[3]).split('|') if a.strip()]
        project, levels = {}, {}
        for r in rows[1:]:
            if len(r) < 4 or not r[2]:
                continue
            levels[r[2]] = r[0]
            project[r[2]] = {'project': r[3], 'assays': {names[i]: r[i] for i in names if i < len(r) and not missing(r[i])}}
        return project, levels, list(names.values()) or listed

    def get(self, term, assay=None):
        p = self.project.get(term)
        if not p:
            return None
        if assay and assay in p['assays']:
            return p['assays'][assay]
        if not missing(p['project']):
            return p['project']
        vals = list(p['assays'].values())
        return vals[0] if len(vals) == 1 else None

    def _table(self, sheet):
        rows = self._rows.get(sheet)
        if not rows:
            return pd.DataFrame(), {}
        meta, i = {}, 0
        while i < len(rows) and isinstance(rows[i][0], str) and rows[i][0].startswith('#'):
            meta[rows[i][0].lstrip('#').strip()] = rows[i][1:]
            i += 1
        if i >= len(rows):
            return pd.DataFrame(), {}
        head = rows[i]
        keep = [j for j, h in enumerate(head) if h not in (None, '')]
        cols = [str(head[j]) for j in keep]
        data = [[r[j] if j < len(r) else None for j in keep] for r in rows[i + 1:]]
        df = pd.DataFrame(data, columns=cols)
        df['_row'] = range(i + 2, i + 2 + len(df))   # the row in the spreadsheet
        if len(df):
            empty = df.drop(columns='_row').apply(lambda r: all(v is None or v == '' for v in r), axis=1)
            df = df[~empty]
        levels = {}
        lv, sections = meta.get('requirement_level_code'), meta.get('section') or ()
        if lv:
            for j in keep[1:]:
                user = j - 1 < len(sections) and str(sections[j - 1] or '').lower().startswith('user')
                if j - 1 < len(lv) and not user:   # columns the user added are not FAIRe terms
                    levels[str(head[j])] = lv[j - 1]
            levels[cols[0]] = 'M'
        return df.reset_index(drop=True), levels

    def _otu_tables(self):
        out = []
        for s in self.sheets:
            m = re.match(r'^otu(Final|Raw)(?:_(.+))?$', s)
            if not m:
                continue
            stage, suffix = m.group(1), m.group(2) or ''
            rows = self._rows.get(s, [])
            if len(rows) < 2 or rows[0][0] != 'seq_id':
                continue
            head = [str(h) for h in rows[0] if h not in (None, '')]
            df = pd.DataFrame([r[:len(head)] for r in rows[1:] if r and r[0] not in (None, '')], columns=head)
            letters = {h: get_column_letter(j + 1) for j, h in enumerate(head)}
            df = df.set_index('seq_id').apply(pd.to_numeric, errors='coerce').fillna(0)
            assay, run = suffix, ''
            for a in sorted(self.assays, key=len, reverse=True):
                if suffix == a or suffix.startswith(a + '_'):
                    assay, run = a, suffix[len(a) + 1:]
                    break
            if not assay and len(self.assays) == 1:
                assay = self.assays[0]
            taxa_name = f'taxa{stage}' + (f'_{suffix}' if suffix else '')
            taxa, _ = self._table(taxa_name)
            if len(taxa) and 'seq_id' in taxa:
                taxa = taxa.drop_duplicates('seq_id').set_index('seq_id')
            out.append({'sheet': s, 'stage': stage, 'assay': assay, 'run': run, 'reads': df, 'taxa': taxa,
                        'letters': letters})
        return out

    def final_tables(self):
        finals = [t for t in self.otus if t['stage'] == 'Final']
        return finals or [t for t in self.otus if t['stage'] == 'Raw']


# ---------------------------------------------------------------------------------------------
# The coastline

class Land:
    def __init__(self, path=COASTLINE):
        self.polys = []
        if not Path(path).exists():
            return
        d = json.load(gzip.open(path, 'rt', encoding='utf-8'))
        s = float(d['scale'])
        for rings in d['polygons']:
            arrs = [np.asarray(r, dtype=float).reshape(-1, 2) / s for r in rings]
            o = arrs[0]
            self.polys.append(((o[:, 0].min(), o[:, 1].min(), o[:, 0].max(), o[:, 1].max()), arrs))

    @staticmethod
    def _crossings(ring, x, y):
        xi, yi, xj, yj = ring[:-1, 0], ring[:-1, 1], ring[1:, 0], ring[1:, 1]
        with np.errstate(divide='ignore', invalid='ignore'):
            hit = ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / (yj - yi) + xi)
        return int(hit.sum())

    def on_land(self, lon, lat):
        for (x0, y0, x1, y1), rings in self.polys:
            if x0 <= lon <= x1 and y0 <= lat <= y1:
                if sum(self._crossings(r, lon, lat) for r in rings) % 2 == 1:
                    return True
        return False

    def coast_km(self, lon, lat, reach=1.5):
        best = math.inf
        k = math.cos(math.radians(lat)) * 111.32
        for (x0, y0, x1, y1), rings in self.polys:
            if x1 < lon - reach or x0 > lon + reach or y1 < lat - reach or y0 > lat + reach:
                continue
            for r in rings:
                ax, ay = (r[:-1, 0] - lon) * k, (r[:-1, 1] - lat) * 110.57
                bx, by = (r[1:, 0] - lon) * k, (r[1:, 1] - lat) * 110.57
                dx, dy = bx - ax, by - ay
                with np.errstate(divide='ignore', invalid='ignore'):
                    t = np.clip(np.nan_to_num(-(ax * dx + ay * dy) / (dx * dx + dy * dy)), 0, 1)
                d = np.hypot(ax + t * dx, ay + t * dy)
                if len(d):
                    best = min(best, float(d.min()))
        return best

    def paths(self, x0, y0, x1, y1, project):
        out = []
        for (a0, b0, a1, b1), rings in self.polys:
            if a1 < x0 or a0 > x1 or b1 < y0 or b0 > y1:
                continue
            for r in rings:
                pts = project(r[:, 0], r[:, 1])
                d = 'M' + 'L'.join(f'{px:.1f},{py:.1f}' for px, py in zip(*pts)) + 'Z'
                out.append(d)
        return out


# ---------------------------------------------------------------------------------------------
# Sample facts

def sample_kind(row):
    cat = str(row.get('samp_category') or '').strip().lower()
    if cat in ('', 'sample') or cat.startswith('missing'):
        return 'sample', 'sample'
    if cat == 'negative control':
        t = row.get('neg_cont_type')
        return 'control', (str(t).strip() if not missing(t) else 'negative control')
    if cat == 'positive control':
        return 'control', 'positive control'
    return 'control', cat


def detection(v):
    """'detected', 'not detected' or None for a detected_notDetected value (1, 0 or the words)."""
    if missing(v):
        return None
    s = str(v).strip().lower()
    if s in ('1', '1.0', 'detected', 'present', 'yes', 'true'):
        return 'detected'
    if s in ('0', '0.0', 'not detected', 'notdetected', 'absent', 'no', 'false'):
        return 'not detected'
    return s


def parse_date(v):
    """(start, end, kind) for an eventDate: a date, a date-time, a month, a year or an interval."""
    if missing(v):
        return None
    if isinstance(v, dt.datetime):
        return v.date(), v.date(), 'day'
    if isinstance(v, dt.date):
        return v, v, 'day'
    s = str(v).strip()
    if '/' in s:
        a, b = (parse_date(x) for x in s.split('/', 1))
        if a and b:
            return a[0], b[1], 'interval'
        return None
    for pat, kind in ((r'^(\d{4})-(\d{2})-(\d{2})', 'day'), (r'^(\d{4})-(\d{2})$', 'month'), (r'^(\d{4})$', 'year')):
        m = re.match(pat, s)
        if m:
            g = [int(x) for x in m.groups()]
            try:
                if kind == 'day':
                    d = dt.date(*g)
                    return d, d, kind
                if kind == 'month':
                    start = dt.date(g[0], g[1], 1)
                    end = (dt.date(g[0] + (g[1] == 12), g[1] % 12 + 1, 1) - dt.timedelta(days=1))
                    return start, end, 'interval'
                return dt.date(g[0], 1, 1), dt.date(g[0], 12, 31), 'interval'
            except ValueError:
                return None
    return None


def environment(row):
    text = ' '.join(str(row.get(c) or '') for c in ('env_medium', 'env_local_scale', 'env_broad_scale'))
    if re.search(r'estuar|brackish|mangrove|salt marsh', text, re.I):
        return None
    sea, land = bool(SEA_RE.search(text)), bool(LAND_RE.search(text))
    if sea and not land:
        return 'sea'
    if land and not sea:
        return 'land'
    return None


# ---------------------------------------------------------------------------------------------
# SVG pieces

def svg_open(w, h, label):
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{esc(label)}" '
            f'preserveAspectRatio="xMidYMid meet" class="chart">')


def nice_ticks(vmax, n=4):
    if vmax <= 0:
        return [0, 1]
    raw = vmax / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    ticks = [0]
    while ticks[-1] < vmax:
        ticks.append(ticks[-1] + step)
    return ticks


def bar_path(x, y, w, h):
    """A column growing up from y + h, rounded 4 px at the top only."""
    r = min(4, w / 2, h)
    if h <= 0:
        return ''
    return (f'M{x:.1f},{y + h:.1f}V{y + r:.1f}Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f}H{x + w - r:.1f}'
            f'Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f}V{y + h:.1f}Z')


def hbar_path(x, y, w, h):
    """A bar growing right from x, rounded 4 px at its end only."""
    r = min(4, h / 2, w)
    if w <= 0:
        return ''
    return (f'M{x:.1f},{y:.1f}H{x + w - r:.1f}Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f}V{y + h - r:.1f}'
            f'Q{x + w:.1f},{y + h:.1f} {x + w - r:.1f},{y + h:.1f}H{x:.1f}Z')


def legend(items):
    return '<div class="legend">' + ''.join(
        f'<span><i style="background:var({c})" class="{shape}"></i>{esc(t)}</span>' for c, t, shape in items) + '</div>'


def table_view(head, rows, summary='Show the numbers', keys=None):
    """A folded table under a chart. keys: one per row, so a click on a mark can find its rows."""
    if not rows:
        return ''
    h = ''.join(f'<th>{esc(x)}</th>' for x in head)
    keys = keys or [None] * len(rows)
    b = ''.join((f'<tr data-key="{esc(k)}">' if k else '<tr>') + ''.join(f'<td>{esc(x)}</td>' for x in r) + '</tr>'
                for r, k in zip(rows, keys))
    return f'<details><summary>{esc(summary)}</summary><div class="tv"><table><tr>{h}</tr>{b}</table></div></details>'


def column_chart(values, colours, labels, label, height=170, ref=None, ref_label='', w=640, vline=None, keys=None):
    """Columns side by side (values in order), each its own colour variable; ref = a horizontal line;
    vline = (position in slots, label) for a vertical line."""
    left, bottom, top = 44, 22, 10
    n = max(1, len(values))
    vmax = max(max(values or [0]), ref or 0)
    ticks = nice_ticks(vmax)
    top_v = ticks[-1] or 1
    ph = height - bottom - top
    slot = (w - left - 6) / n
    bw = max(1.0, min(24, slot - (2 if slot > 4 else 0.5)))
    out = [svg_open(w, height, label)]
    for t in ticks:
        y = top + ph - ph * t / top_v
        out.append(f'<line x1="{left}" x2="{w}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>'
                   f'<text x="{left - 6}" y="{y + 4:.1f}" class="tick" text-anchor="end">{fmt(t)}</text>')
    keys = keys or [None] * n
    for i, (v, c, lab, key) in enumerate(zip(values, colours, labels, keys)):
        h = ph * v / top_v
        x = left + i * slot + (slot - bw) / 2
        p = bar_path(x, top + ph - h, bw, h)
        tip = lab if '\n' in lab else f'{lab}: {fmt(v)}'
        if p:
            out.append(f'<path d="{p}" fill="var({c})"/>')
        k = f' data-key="{esc(key)}" class="hit"' if key and v else ''
        out.append(f'<rect x="{left + i * slot:.1f}" y="{top}" width="{slot:.1f}" height="{ph}" fill="transparent"{k}>'
                   f'<title>{esc(tip)}</title></rect>')
    if vline is not None:
        x = left + vline[0] * slot
        right = x > w - 80
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top}" y2="{top + ph}" class="ref"/>'
                   f'<text x="{x - 4 if right else x + 4:.1f}" y="{top + 10}" class="tick" '
                   f'text-anchor="{"end" if right else "start"}">{esc(vline[1])}</text>')
    if ref is not None:
        y = top + ph - ph * ref / top_v
        out.append(f'<line x1="{left}" x2="{w}" y1="{y:.1f}" y2="{y:.1f}" class="ref"/>'
                   f'<text x="{w - 2}" y="{y - 4:.1f}" class="tick" text-anchor="end">{esc(ref_label)}</text>')
    out.append(f'<line x1="{left}" x2="{w}" y1="{top + ph}" y2="{top + ph}" class="axis"/></svg>')
    return ''.join(out)


def ranked_bars(items, label, value_fmt=fmt, total=None, tips=None):
    """Horizontal bars for (name, value, note) in the order given; one series. tips: extra lines per bar."""
    w, left, rowh = 640, 150, 22
    h = rowh * len(items) + 8
    vmax = max([v for _, v, _ in items] or [1]) or 1
    out = [svg_open(w, h, label)]
    for i, (name, v, note) in enumerate(items):
        y = 4 + i * rowh
        bw = (w - left - 190) * v / vmax
        p = hbar_path(left, y + 4, bw, rowh - 8)
        colour = '--muted' if name in ('Other', 'Not assigned') else '--s1'
        share = f' ({100 * v / total:.0f}%)' if total else ''
        out.append(f'<text x="{left - 8}" y="{y + 15}" class="lab" text-anchor="end">{esc(name[:28])}</text>')
        if p:
            extra = ('\n' + tips[i]) if tips and tips[i] else ''
            out.append(f'<path d="{p}" fill="var({colour})"/>'
                       f'<rect x="0" y="{y}" width="{w}" height="{rowh}" fill="transparent" class="hit" data-key="{esc(name)}">'
                       f'<title>{esc(name)}: {value_fmt(v)}{share}{esc(extra)}</title></rect>')
        out.append(f'<text x="{left + bw + 6:.1f}" y="{y + 15}" class="val">{value_fmt(v)}{share}'
                   f'{(" · " + esc(note)) if note else ""}</text>')
    out.append(f'<line x1="{left}" x2="{left}" y1="0" y2="{h}" class="axis"/></svg>')
    return ''.join(out)


# ---------------------------------------------------------------------------------------------
# The panels

def card(title, sub, body, wide=False):
    return (f'<section class="card{" wide" if wide else ""}"><h2>{esc(title)}</h2>'
            f'{f"<p class=sub>{sub}</p>" if sub else ""}{body}</section>')


def panel_map(wb, flags, land):
    s = wb.samples
    if not len(s) or 'decimalLatitude' not in s or 'decimalLongitude' not in s:
        flags.add('check', 'Where', 'The sample sheet has no decimalLatitude or decimalLongitude column.')
        return card('Where the samples were taken', '', '<p class="empty">No coordinates in the workbook.</p>')
    targeted = any(c.startswith('detected_notDetected') for c in s.columns)
    pts, no_coords, bad = [], [], []
    for _, row in s.iterrows():
        kind, ctype = sample_kind(row)
        lat, lon = num(row.get('decimalLatitude')), num(row.get('decimalLongitude'))
        name = str(row['samp_name'])
        if lat is None or lon is None:
            no_coords.append((name, kind))
            continue
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            swapped = -90 <= lon <= 90 and -180 <= lat <= 180
            bad.append((name, f'{lat}, {lon}' + (' (latitude and longitude swapped?)' if swapped else '')))
            continue
        if lat == 0 and lon == 0:
            bad.append((name, '0, 0'))
            continue
        detected = None
        if targeted and kind == 'sample':
            vals = [detection(row[c]) for c in s.columns if c.startswith('detected_notDetected')]
            vals = [v for v in vals if v in ('detected', 'not detected')]
            detected = ('detected' in vals) if vals else None
        pts.append({'name': name, 'kind': kind, 'ctype': ctype, 'lat': lat, 'lon': lon, 'env': environment(row),
                    'detected': detected})
    for name, where in bad:
        flags.add('problem', 'Where', f'{name}: coordinates {where} cannot be right.')
    miss = [n for n, k in no_coords if k == 'sample']
    if miss:
        flags.add('check', 'Where', f'{plural(len(miss), "sample")} with no coordinates: {listing(miss)}.')
    if not pts:
        return card('Where the samples were taken', '', '<p class="empty">No usable coordinates.</p>')

    # positions against the coastline
    if land.polys:
        seen = {}
        for p in pts:
            if not p['env']:
                continue
            key = (round(p['lon'], 4), round(p['lat'], 4), p['env'])
            if key not in seen:
                inside = land.on_land(p['lon'], p['lat'])
                wrong = (p['env'] == 'sea') == inside
                seen[key] = land.coast_km(p['lon'], p['lat']) if wrong else 0.0
            p['off_km'] = seen[key]
        for env, where in (('sea', 'on land'), ('land', 'at sea')):
            far = [p for p in pts if p['env'] == env and p.get('off_km', 0) > 10]
            if far:
                worst = max(p['off_km'] for p in far)
                level = 'problem' if worst > 25 else 'check'
                what = 'marine' if env == 'sea' else 'land or freshwater'
                flags.add(level, 'Where', f'{plural(len(far), "sample")} described as {what} plot {where}, up to '
                                          f'{worst:.0f} km from the coast: {listing(sorted({p["name"] for p in far}))}.')
                for p in far:
                    p['flag'] = True

    lons = [p['lon'] for p in pts]
    lats = [p['lat'] for p in pts]
    x0, x1, y0, y1 = min(lons), max(lons), min(lats), max(lats)
    span = max(x1 - x0, y1 - y0, 0.4)
    padx, pady = max((x1 - x0) * 0.15, span * 0.15), max((y1 - y0) * 0.15, span * 0.15)
    x0, x1, y0, y1 = x0 - padx, x1 + padx, max(-85, y0 - pady), min(85, y1 + pady)
    k = math.cos(math.radians((y0 + y1) / 2))
    n_pos = len({(round(p['lon'], 4), round(p['lat'], 4)) for p in pts})
    W, H = 1100.0, (300.0 if n_pos <= 3 else 440.0)
    sx = W / ((x1 - x0) * k)
    sy = H / (y1 - y0)
    scale = min(sx, sy)
    if sx > sy:   # widen the longitude range to fill the frame
        extra = (W / scale / k - (x1 - x0)) / 2
        x0, x1 = x0 - extra, x1 + extra
    else:
        extra = (H / scale - (y1 - y0)) / 2
        y0, y1 = y0 - extra, y1 + extra

    def project(lon, lat):
        return (np.asarray(lon) - x0) * k * scale, (y1 - np.asarray(lat)) * scale

    out = [svg_open(int(W), int(H), 'Map of the sample positions'),
           f'<defs><clipPath id="mapclip"><rect width="{W:.0f}" height="{H:.0f}" rx="6"/></clipPath></defs>',
           f'<g clip-path="url(#mapclip)"><rect width="{W:.0f}" height="{H:.0f}" fill="var(--sea)"/>']
    paths = land.paths(x0 - 1, y0 - 1, x1 + 1, y1 + 1, project) if land.polys else []
    if paths:
        out.append(f'<path d="{"".join(paths)}" fill="var(--land)" fill-rule="evenodd" stroke="var(--axis)" '
                   f'stroke-width="0.6"/>')
    groups = defaultdict(list)
    for p in pts:
        cat = 'control' if p['kind'] == 'control' else ('det' if p['detected'] else ('nondet' if p['detected'] is False else 'sample'))
        groups[(round(p['lon'], 4), round(p['lat'], 4), cat)].append(p)
    position_rows = []
    order = {'nondet': 0, 'sample': 1, 'det': 2, 'control': 3}
    shift = {'nondet': -7, 'sample': 0, 'det': 0, 'control': 7}
    for (lon, lat, cat), ps in sorted(groups.items(), key=lambda g: order[g[0][2]]):
        px, py = project(lon, lat)
        px, py = float(px) + shift[cat], float(py)
        r = 4 + min(3.0, math.sqrt(len(ps)) - 1)
        colour = {'sample': '--s1', 'det': '--s1', 'nondet': '--surface', 'control': '--s2'}[cat]
        stroke = 'var(--ink2)' if cat == 'nondet' else 'var(--surface)'
        what = {'sample': 'sample', 'det': 'sample, detected', 'nondet': 'sample, not detected',
                'control': 'control'}[cat]
        named = [f'{p["name"]} ({wb.row(p["name"])})' for p in sorted(ps, key=lambda p: p['name'])]
        shown = named[:12] + ([f'and {len(named) - 12} more'] if len(named) > 12 else [])
        extra = ''.join(f'\n{p["name"]}: {p["off_km"]:.0f} km on the wrong side of the coast' for p in ps if p.get('flag'))[:300]
        title = f'{lat}, {lon}\n{plural(len(ps), what if cat != "control" else "control")}:\n' + '\n'.join(shown) + extra
        key = f'{lat},{lon},{cat}'
        position_rows.append(((lat, lon, what), ', '.join(named), key))
        if any(p.get('flag') for p in ps):
            out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r + 4:.1f}" fill="none" stroke="var(--critical)" stroke-width="2"/>')
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r:.1f}" fill="var({colour})" stroke="{stroke}" stroke-width="2"/>'
                   f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{max(r + 5, 10):.1f}" fill="transparent" class="hit" '
                   f'data-key="{esc(key)}"><title>{esc(title)}</title></circle>')
    out.append('</g>')
    if land.polys and max(x1 - x0, y1 - y0) < 4:   # where the area is, for a small map
        iw, ih = 200.0, 150.0
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        ix0, ix1, iy0, iy1 = cx - 14, cx + 14, cy - 10, cy + 10
        ik = math.cos(math.radians(cy))
        isc = min(iw / ((ix1 - ix0) * ik), ih / (iy1 - iy0))

        def iproject(lon, lat):
            return W - iw - 10 + (np.asarray(lon) - ix0) * ik * isc, 10 + (iy1 - np.asarray(lat)) * isc
        ipaths = land.paths(ix0 - 1, iy0 - 1, ix1 + 1, iy1 + 1, iproject)
        rx, ry = iproject(x0, y1)
        rx2, ry2 = iproject(x1, y0)
        out.append(f'<defs><clipPath id="insetclip"><rect x="{W - iw - 10:.0f}" y="10" width="{iw:.0f}" height="{ih:.0f}" rx="4"/></clipPath></defs>'
                   f'<g clip-path="url(#insetclip)"><rect x="{W - iw - 10:.0f}" y="10" width="{iw:.0f}" height="{ih:.0f}" fill="var(--sea)"/>'
                   f'<path d="{"".join(ipaths)}" fill="var(--land)" fill-rule="evenodd" stroke="var(--axis)" stroke-width="0.5"/>'
                   f'<rect x="{float(rx) - 3:.1f}" y="{float(ry) - 3:.1f}" width="{max(6, float(rx2 - rx)) + 6:.1f}" '
                   f'height="{max(6, float(ry2 - ry)) + 6:.1f}" fill="none" stroke="var(--critical)" stroke-width="1.5"/></g>'
                   f'<rect x="{W - iw - 10:.0f}" y="10" width="{iw:.0f}" height="{ih:.0f}" rx="4" fill="none" stroke="var(--axis)"/>')
    # scale bar
    km_w = W / scale / k * 111.32
    target = km_w / 5
    mag = 10 ** math.floor(math.log10(target))
    bar_km = next(m * mag for m in (5, 2, 1) if m * mag <= target)
    bar_px = bar_km / km_w * W
    out.append(f'<rect x="10" y="{H - 30:.0f}" width="{bar_px + 16:.1f}" height="22" rx="4" fill="var(--surface)" opacity="0.85"/>'
               f'<line x1="18" x2="{18 + bar_px:.1f}" y1="{H - 16:.0f}" y2="{H - 16:.0f}" stroke="var(--ink)" stroke-width="2"/>'
               f'<text x="18" y="{H - 20:.0f}" class="tick">{fmt(bar_km)} km</text>')
    out.append('</svg>')

    def deg(v, pos, neg):
        return f'{abs(v):.2f}°{pos if v >= 0 else neg}'
    extent = f'{deg(min(lons), "E", "W")} to {deg(max(lons), "E", "W")}, {deg(min(lats), "N", "S")} to {deg(max(lats), "N", "S")}'
    n_sites = len({(round(p['lon'], 4), round(p['lat'], 4)) for p in pts if p['kind'] == 'sample'})
    sub = (f'{plural(sum(p["kind"] == "sample" for p in pts), "sample")} at {plural(n_sites, "position")}, '
           f'{extent}. Controls are set a little to the right of their site.')
    if no_coords:
        sub += f' Not shown: {plural(len(no_coords), "row")} with no coordinates ({sum(k == "control" for _, k in no_coords)} of them controls).'
    items = []
    if targeted:
        items = [('--s1', 'Detected', 'dot'), ('--surface', 'Not detected', 'ring'), ('--s2', 'Control', 'dot')]
    else:
        items = [('--s1', 'Sample', 'dot'), ('--s2', 'Control', 'dot')]
    if any(p.get('flag') for p in pts):
        items.append(('--critical', 'Flagged: on the wrong side of the coast', 'ring'))
    position_rows.sort()
    body = legend(items) + ''.join(out) + table_view(
        ['Latitude', 'Longitude', 'Kind', 'Rows (sampleMetadata row)'],
        [(a, b, c, names) for (a, b, c), names, _ in position_rows], 'Show the positions and samples',
        keys=[k for _, _, k in position_rows])
    return card('Where the samples were taken', esc(sub), body, wide=True)


def panel_dates(wb, flags):
    s = wb.samples
    if 'eventDate' not in s:
        return card('When', '', '<p class="empty">No eventDate column.</p>')
    today = dt.date.today()
    days, intervals, none = Counter(), Counter(), []
    on_day = defaultdict(list)
    for _, row in s.iterrows():
        kind, _ = sample_kind(row)
        if kind != 'sample':
            continue
        d = parse_date(row.get('eventDate'))
        if not d:
            none.append(str(row['samp_name']))
            continue
        start, end, how = d
        if start > today:
            flags.add('problem', 'When', f'{row["samp_name"]}: eventDate {row["eventDate"]} is in the future.')
        elif start.year < 1970:
            flags.add('problem', 'When', f'{row["samp_name"]}: eventDate {row["eventDate"]} is before 1970.')
        if how == 'interval':
            intervals[(start, end)] += 1
        else:
            days[start] += 1
            on_day[start].append(str(row['samp_name']))
    if none:
        flags.add('check', 'When', f'{plural(len(none), "sample")} with no usable eventDate: {listing(none)}.')
    if intervals:
        n = sum(intervals.values())
        flags.add('note', 'When', f'{plural(n, "sample")} dated by a period, not a day '
                                  f'({listing(f"{a} to {b}" for a, b in intervals)}).')
    if not days and not intervals:
        return card('When the samples were taken', '', '<p class="empty">No dates to show.</p>')
    all_dates = list(days) + [a for a, _ in intervals] + [b for _, b in intervals]
    first, last = min(all_dates), max(all_dates)
    span = (last - first).days
    unit = 'day' if span <= 120 else ('month' if span <= 3 * 366 else 'year')

    def bucket(d):
        return d if unit == 'day' else (dt.date(d.year, d.month, 1) if unit == 'month' else dt.date(d.year, 1, 1))

    def step(d):
        if unit == 'day':
            return d + dt.timedelta(days=1)
        if unit == 'month':
            return dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        return dt.date(d.year + 1, 1, 1)
    keys = []
    k = bucket(first)
    while k <= bucket(last):
        keys.append(k)
        k = step(k)
    counts, members = Counter(), defaultdict(list)
    for d, c in days.items():
        counts[bucket(d)] += c
        members[bucket(d)] += on_day[d]
    vals = [counts[k] for k in keys]
    lab = {'day': lambda d: d.isoformat(), 'month': lambda d: d.strftime('%b %Y'), 'year': lambda d: str(d.year)}[unit]
    tips = [f'{lab(k)}: {plural(counts[k], "sample")}\n' + listing(sorted(members[k]), 15) for k in keys]
    chart = ''
    if days:
        chart = column_chart(vals, ['--s1'] * len(vals), tips, 'Samples per ' + unit, height=150,
                             keys=[lab(k) for k in keys])
        chart += (f'<div class="axislabels"><span>{lab(keys[0])}</span><span>{lab(keys[-1])}</span></div>')
    ivs = ''.join(f'<li>{plural(c, "sample")} dated {a} to {b}</li>' for (a, b), c in sorted(intervals.items()))
    sub = f'Samples per {unit}, {first.isoformat()} to {last.isoformat()}'
    if span:
        sub += f' ({plural(span + 1, "day")})'
    body = chart + (f'<ul class="plain">{ivs}</ul>' if ivs else '') + table_view(
        [unit.capitalize(), 'Samples', 'Names'], [(lab(k), c, ', '.join(sorted(members[k]))) for k, c in zip(keys, vals) if c],
        keys=[lab(k) for k, c in zip(keys, vals) if c])
    return card('When the samples were taken', esc(sub), body)


ENV_LIMITS = {  # term: (low, high, level) for values that cannot be right or are worth a look
    'minimumDepthInMeters': (0, 11000, 'problem'), 'maximumDepthInMeters': (0, 11000, 'problem'),
    'temp': (-2.5, 45, 'check'), 'salinity': (0, 45, 'check'), 'ph': (0, 14, 'problem'),
    'samp_size': (0.0001, None, 'problem'), 'samp_vol_we_dna_ext': (0.0001, None, 'problem'),
    'size_frac_low': (0, None, 'problem'), 'size_frac': (0, None, 'problem'),
}
SKIP_NUMERIC = {'decimalLatitude', 'decimalLongitude', 'coordinateUncertaintyInMeters', 'replicate', 'Replicate',
                'biological_rep', 'tech_rep', 'technical_rep_id'}


def panel_environment(wb, flags):
    s = wb.samples
    rows = []
    for c in s.columns:
        if (c in SKIP_NUMERIC or c == 'samp_name' or c not in wb.levels or c.endswith('_unit')
                or c.endswith('_0_1') or c.startswith('detected_')):
            continue
        rows_s = s[[sample_kind(r)[0] == 'sample' for _, r in s.iterrows()]]
        sub = rows_s[c]
        vals = [num(v) for v in sub if not missing(v)]
        given = [v for v in sub if not missing(v)]
        who = [(str(n), num(v)) for n, v in zip(rows_s['samp_name'], sub) if not missing(v) and num(v) is not None]
        if not given or sum(v is not None for v in vals) < 0.8 * len(given):
            continue
        vals = [v for v in vals if v is not None]
        if len(set(vals)) == 0:
            continue
        unit = ''
        if f'{c}_unit' in s:
            units = {str(u) for u in s[f'{c}_unit'] if not missing(u)}
            unit = ' or '.join(sorted(units))
        lim = ENV_LIMITS.get(c)
        if lim:
            lo, hi, level = lim
            outside = [v for v in vals if (lo is not None and v < lo) or (hi is not None and v > hi)]
            if outside:
                flags.add(level, 'Values', f'{c}: {plural(len(outside), "value")} outside {lo} to {hi if hi is not None else "any"}'
                                           f'{(" " + unit) if unit else ""} (for example {fmt(outside[0])}).')
        rows.append((c, unit, vals, who))
    if not rows:
        return ''
    out = []
    for c, unit, vals, who in rows:
        lo, hi = min(vals), max(vals)
        w, pad = 220, 8
        rng = (hi - lo) or 1
        at = defaultdict(list)
        for n, v in who:
            at[v].append(n)
        dots = ''.join(f'<circle cx="{pad + (w - 2 * pad) * (v - lo) / rng:.1f}" cy="10" r="4" fill="var(--s1)" '
                       f'fill-opacity="0.5"/><circle cx="{pad + (w - 2 * pad) * (v - lo) / rng:.1f}" cy="10" r="7" '
                       f'fill="transparent"><title>{esc(fmt(v))} {esc(unit)}\n'
                       f'{esc(listing([f"{n} ({wb.row(n)})" for n in sorted(ns)], 10))}</title></circle>'
                       for v, ns in sorted(at.items()))
        strip = (f'<svg viewBox="0 0 {w} 20" width="{w}" height="20" aria-label="Values of {esc(c)}">'
                 f'<line x1="{pad}" x2="{w - pad}" y1="10" y2="10" class="grid"/>{dots}</svg>')
        out.append(f'<tr><td>{esc(c)}</td><td>{esc(unit)}</td><td class="n">{fmt(lo)}</td>'
                   f'<td class="n">{fmt(float(np.median(vals)))}</td><td class="n">{fmt(hi)}</td><td>{strip}</td></tr>')
    body = ('<div class="tv"><table class="env"><tr><th>Term</th><th>Unit</th><th>Lowest</th><th>Median</th>'
            '<th>Highest</th><th>Each sample</th></tr>' + ''.join(out) + '</table></div>')
    return card('Measured values', 'The numeric columns of the sample sheet, samples only.', body)


def panel_counts(wb, flags):
    s = wb.samples
    if not len(s):
        flags.add('problem', 'Samples', 'The sample sheet is empty.')
        return ''
    kinds = Counter()
    sites = Counter()
    for _, row in s.iterrows():
        kind, ctype = sample_kind(row)
        kinds[ctype] += 1
        if kind == 'sample':
            lat, lon = num(row.get('decimalLatitude')), num(row.get('decimalLongitude'))
            if lat is not None and lon is not None:
                sites[(round(lat, 4), round(lon, 4))] += 1
    n_samples = kinds.get('sample', 0)
    controls = {k: v for k, v in kinds.items() if k != 'sample'}
    if not controls:
        flags.add('check', 'Samples', 'No controls in the sample sheet. If the study had blanks, add them, '
                                      'with samp_category and neg_cont_type.')
    elif not any('negative' in k for k in controls):
        flags.add('note', 'Samples', 'No negative controls are marked (neg_cont_type).')
    per_site = Counter(sites.values())
    if sites and len(sites) > 2:
        common = max(per_site, key=per_site.get)
        singles = [k for k, v in sites.items() if v == 1]
        if common > 1 and singles and len(singles) <= 0.25 * len(sites):
            flags.add('note', 'Samples', f'{plural(len(singles), "position")} with one sample, where most have {common}.')
    tiles = [('Samples', n_samples), ('Positions', len(sites)), ('Controls', sum(controls.values()))]
    tiles_html = '<div class="tiles">' + ''.join(f'<div class="tile"><div class="tl">{esc(a)}</div>'
                                                 f'<div class="tv2">{fmt(b)}</div></div>' for a, b in tiles) + '</div>'
    ctab = ''.join(f'<tr><td>{esc(k)}</td><td class="n">{v}</td></tr>' for k, v in sorted(controls.items()))
    stab = ', '.join(f'{c} at {plural(n, "position")}' for c, n in sorted(per_site.items(), reverse=True))
    body = (tiles_html + (f'<table class="small"><tr><th>Control</th><th>Rows</th></tr>{ctab}</table>' if ctab else '')
            + (f'<p class="small">Samples per position: {esc(stab)}.</p>' if stab else ''))
    return card('Samples and controls', '', body)


def panel_links(wb, flags):
    s = wb.samples
    names = set(map(str, s['samp_name'])) if len(s) else set()
    kinds = {str(r['samp_name']): sample_kind(r)[0] for _, r in s.iterrows()} if len(s) else {}
    lines = []

    def line(ok, text):
        lines.append(f'<li><span class="ico {"good" if ok else "warn"}">{"✓" if ok else "●"}</span>{esc(text)}</li>')

    tables = wb.final_tables()
    by_assay = defaultdict(set)
    for t in tables:
        cols = set(map(str, t['reads'].columns))
        by_assay[t['assay']] |= cols
        extra = sorted(cols - names)
        if extra:
            flags.add('problem', 'Links', f'{t["sheet"]}: {plural(len(extra), "column")} not in sampleMetadata: {listing(extra)}.')
        line(not extra, f'{t["sheet"]}: {plural(len(cols), "column")}, '
                        + ('all in the sample sheet' if not extra else f'{len(extra)} not in the sample sheet'))
    if tables:
        all_cols = set().union(*by_assay.values())
        no_reads = sorted(n for n in names if kinds.get(n) == 'sample' and n not in all_cols)
        if no_reads:
            flags.add('check', 'Links', f'{plural(len(no_reads), "sample")} with no column in any OTU table: {listing(no_reads)}.')
        line(not no_reads, 'Every sample has reads' if not no_reads else f'{plural(len(no_reads), "sample")} with no reads column')
    r = wb.runs
    if len(r) and 'samp_name' in r:
        lib_names = set(map(str, r['samp_name']))
        orphans = sorted(lib_names - names)
        if orphans:
            flags.add('problem', 'Links', f'experimentRunMetadata: {plural(len(orphans), "library", "libraries")} for samples '
                                          f'not in sampleMetadata: {listing(orphans)}.')
        line(not orphans, f'experimentRunMetadata: {plural(len(r), "library", "libraries")}'
                          + (', all for samples in the sample sheet' if not orphans else f', {len(orphans)} for unknown samples'))
        if tables and 'assay_name' in r:
            empty = []
            for _, row in r.iterrows():
                cols = by_assay.get(str(row['assay_name']))
                if cols is not None and str(row['samp_name']) not in cols:
                    empty.append(f'{row["samp_name"]} ({row["assay_name"]})')
            if empty:
                flags.add('note', 'Links', f'{plural(len(empty), "library", "libraries")} with no column in the OTU '
                                           f'table of its assay: {listing(empty)}. Fine if they gave no reads.')
            line(not empty, 'Each library has a reads column' if not empty else f'{plural(len(empty), "library", "libraries")} with no reads column')
        fcol = 'filename' if 'filename' in r else None
        if fcol:
            nofile = int(sum(missing(v) for v in r[fcol]))
            if nofile:
                flags.add('note', 'Links', f'{plural(nofile, "library", "libraries")} with no filename. ENA and NCBI '
                                           f'need the names of the reads files.')
            line(not nofile, 'Every library has its reads file names' if not nofile else f'{plural(nofile, "library", "libraries")} with no reads file name')
    elif wb.otus:
        flags.add('note', 'Links', 'experimentRunMetadata is empty, so no libraries or reads files are listed.')
        line(False, 'No libraries listed in experimentRunMetadata')
    a = wb.amp
    if len(a) and 'samp_name' in a:
        amp_names = set(map(str, a['samp_name']))
        orphans = sorted(amp_names - names)
        if orphans:
            flags.add('problem', 'Links', f'ampData: reactions for samples not in sampleMetadata: {listing(orphans)}.')
        untested = sorted(n for n in names if kinds.get(n) == 'sample' and n not in amp_names)
        if untested:
            flags.add('check', 'Links', f'{plural(len(untested), "sample")} with no qPCR reactions in ampData: {listing(untested)}.')
        line(not orphans and not untested, f'ampData: {plural(len(a), "reaction")} for {plural(len(amp_names), "sample")}')
    if not lines:
        return ''
    return card('Links between the sheets', 'Sample names should match across the sheets.', f'<ul class="checks">{"".join(lines)}</ul>')


def taxon_name(taxa, sid):
    if not len(taxa) or sid not in taxa.index:
        return str(sid)
    row = taxa.loc[sid]
    for c in ('scientificName', 'verbatimIdentification'):
        if c in row and not missing(row[c]):
            return str(row[c])
    for c in reversed(RANKS):
        if c in row and not missing(row[c]):
            if c == 'specificEpithet' and 'genus' in row and not missing(row['genus']):
                return f'{row["genus"]} {row[c]}'
            return str(row[c])
    return str(sid)


def panel_reads(wb, flags):
    out = []
    kinds = {str(r['samp_name']): sample_kind(r) for _, r in wb.samples.iterrows()} if len(wb.samples) else {}
    for t in wb.final_tables():
        reads = t['reads']
        if not reads.shape[1]:
            continue
        totals = reads.sum(axis=0)
        cols = list(map(str, totals.index))
        is_ctrl = [kinds.get(c, ('sample', ''))[0] == 'control' for c in cols]
        samp_tot = [v for v, c in zip(totals, is_ctrl) if not c]
        med = float(np.median(samp_tot)) if samp_tot else 0
        zero = [c for c, v, ct in zip(cols, totals, is_ctrl) if not ct and v == 0]
        low = [c for c, v, ct in zip(cols, totals, is_ctrl) if not ct and 0 < v < 0.1 * med]
        name = t['sheet']
        if zero:
            flags.add('check', 'Reads', f'{name}: {plural(len(zero), "sample")} with no reads: {listing(zero)}.')
        if low:
            flags.add('note', 'Reads', f'{name}: {plural(len(low), "sample")} with under a tenth of the median '
                                       f'({fmt(med)} reads): {listing(low)}.')
        order = sorted(range(len(cols)), key=lambda i: (is_ctrl[i], -totals.iloc[i]))
        vals = [float(totals.iloc[i]) for i in order]
        colours = ['--s2' if is_ctrl[i] else '--s1' for i in order]
        letters = t.get('letters', {})
        labels = [f'{cols[i]}, {kinds.get(cols[i], ("", "not in the sample sheet"))[1]}\n{fmt(vals[j])} reads\n'
                  f'sampleMetadata {wb.row(cols[i])}; {name} column {letters.get(cols[i], "?")}'
                  for j, i in enumerate(order)]
        chart = column_chart(vals, colours, labels, f'Reads per sample in {name}', ref=med,
                             ref_label=f'median {fmt(med)}', w=1100, height=200, keys=[cols[i] for i in order])
        ctrl_with = [cols[i] for i in order if is_ctrl[i] and totals.iloc[i] > 0]
        sub = (f'{plural(len(cols) - sum(is_ctrl), "sample")} and {plural(sum(is_ctrl), "control")}, '
               f'{fmt(float(totals.sum()))} reads in all. Samples from most reads to fewest, then the controls.')
        body = (legend([('--s1', 'Sample', 'sq'), ('--s2', 'Control', 'sq')]) + chart
                + table_view(['Sample', 'Kind', 'Reads', 'sampleMetadata', f'{name} column'],
                             [(cols[i], kinds.get(cols[i], ('', '?'))[1], fmt(float(totals.iloc[i])), wb.row(cols[i]),
                               letters.get(cols[i], '?')) for i in order],
                             keys=[cols[i] for i in order]))
        out.append(card(f'Reads per sample: {name}', esc(sub), body, wide=True))
        # the controls
        if ctrl_with:
            sample_cols = [c for c, ct in zip(cols, is_ctrl) if not ct]
            in_samples = set(reads.index[(reads[sample_cols] > 0).any(axis=1)]) if sample_cols else set()
            rows, summary, only_all = [], [], set()
            for c in ctrl_with:
                col = reads[c]
                hit = col[col > 0].sort_values(ascending=False)
                only = [sid for sid in hit.index if sid not in in_samples]
                top = listing([f'{taxon_name(t["taxa"], sid)} ({fmt(float(hit[sid]))})' for sid in hit.index[:3]], 3)
                rows.append((c, kinds.get(c, ('', ''))[1], fmt(float(col.sum())), len(hit), top,
                             f'{wb.row(c)}; column {letters.get(c, "?")}'))
                summary.append((float(col.sum()), f'{c} ({fmt(float(col.sum()))} reads, mostly '
                                                  f'{taxon_name(t["taxa"], hit.index[0])})'))
                only_all |= {taxon_name(t['taxa'], sid) for sid in only}
            n_ctrl = sum(is_ctrl)
            msg = (f'{name}: {len(ctrl_with)} of {plural(n_ctrl, "control")} {"has" if len(ctrl_with) == 1 else "have"} reads: '
                   f'{listing([x for _, x in sorted(summary, reverse=True)], 3)}')
            if only_all:
                msg += f'. In controls but in no sample: {listing(sorted(only_all), 4)}'
            flags.add('check', 'Controls', msg + '.')
            tab = ''.join(f'<tr><td>{esc(a)}</td><td>{esc(b)}</td><td class="n">{c}</td><td class="n">{d}</td>'
                          f'<td>{esc(e)}</td><td>{esc(f)}</td></tr>' for a, b, c, d, e, f in rows)
            out.append(card(f'Controls with reads: {name}', 'Reads in negative controls can mean contamination.',
                            f'<div class="tv"><table><tr><th>Control</th><th>Type</th><th>Reads</th><th>Taxa</th>'
                            f'<th>Most reads</th><th>Where (sampleMetadata; {esc(name)})</th></tr>{tab}</table></div>'))
    return ''.join(out)


def group_rank(taxa):
    for rank in ('class', 'phylum', 'order'):
        if rank in taxa and taxa[rank].map(lambda v: not missing(v)).mean() >= 0.3:
            return rank
    return None


def panel_taxa(wb, flags):
    out = []
    kinds = {str(r['samp_name']): sample_kind(r)[0] for _, r in wb.samples.iterrows()} if len(wb.samples) else {}
    by_assay = defaultdict(list)
    for t in wb.final_tables():
        by_assay[t['assay']].append(t)
    for assay, tables in by_assay.items():
        reads = pd.concat([t['reads'][[c for c in t['reads'].columns if kinds.get(str(c), 'sample') == 'sample']].sum(axis=1)
                           for t in tables])
        reads = reads.groupby(level=0).sum()
        taxa = pd.concat([t['taxa'] for t in tables if len(t['taxa'])]) if any(len(t['taxa']) for t in tables) else pd.DataFrame()
        if len(taxa):
            taxa = taxa[~taxa.index.duplicated()]
        total = float(reads.sum())
        if not total or not len(taxa):
            continue
        rank = group_rank(taxa)
        items = []
        tips, mains = [], []
        if rank:
            grp = Counter()
            ntax = Counter()
            members = defaultdict(Counter)
            for sid, v in reads.items():
                g = taxa.at[sid, rank] if sid in taxa.index and not missing(taxa.at[sid, rank]) else 'Not assigned'
                grp[str(g)] += float(v)
                if v > 0:
                    ntax[str(g)] += 1
                    members[str(g)][taxon_name(taxa, sid)] += float(v)
            ranked = [(g, v) for g, v in grp.most_common() if g != 'Not assigned']
            top, rest = ranked[:8], ranked[8:]
            items = [(g, v, plural(ntax[g], 'ASV')) for g, v in top]
            if rest:
                items.append(('Other', sum(v for _, v in rest), f'{len(rest)} {rank} groups'))
            if grp.get('Not assigned'):
                items.append(('Not assigned', grp['Not assigned'], f'no {rank}'))
            for g, _, _ in items:
                if g == 'Other':
                    m = Counter()
                    for o, _ in rest:
                        m.update(members[o])
                else:
                    m = members[g]
                mains.append(listing([f'{n} ({fmt(v)})' for n, v in m.most_common(5)], 5))
                tips.append('Most reads: ' + mains[-1] if mains[-1] else '')
        # how far down the reads are named
        assigned = []
        for r in RANKS:
            if r in taxa and taxa[r].map(lambda v: not missing(v)).any():
                named = taxa[r].map(lambda v: not missing(v))
                share = float(reads[[sid for sid in reads.index if sid in named.index and named[sid]]].sum()) / total
                assigned.append((RANK_LABEL.get(r, r), share))
        # the target group
        target = wb.get('targetTaxonomicAssay', assay)
        tnote = ''
        if target and not missing(target):
            sel = target_set(str(target), taxa)
            if sel:
                rk, names_ = sel
                in_t = [sid for sid in reads.index if sid in taxa.index and str(taxa.at[sid, rk]) in names_]
                has_rank = [sid for sid in reads.index if sid in taxa.index and not missing(taxa.at[sid, 'phylum'] if 'phylum' in taxa else None)]
                base = float(reads[has_rank].sum()) or total
                share = float(reads[in_t].sum()) / base if base else 0
                tnote = f'{100 * share:.0f}% of the reads named to a phylum are in the target group ({target}).'
                if share < 0.5:
                    flags.add('check', 'Taxa', f'{assay}: only {100 * share:.0f}% of the reads named to a phylum are in the '
                                               f'target group, {target}. Common for broad primers; worth a look otherwise.')
            else:
                tnote = f'The target group ({target}) could not be matched to the taxonomy, so it was not checked.'
        # people and domestic animals
        found = []
        for sid, v in reads.items():
            if v <= 0 or sid not in taxa.index:
                continue
            name = taxon_name(taxa, sid)
            for c in CONTAMINANTS:
                if name.startswith(c):
                    found.append((c, float(v)))
        if found:
            agg = Counter()
            for c, v in found:
                agg[c] += v
            flags.add('check', 'Taxa', f'{assay}: reads of {listing([f"{c} ({fmt(v)})" for c, v in agg.most_common()])}, '
                                       'which often come from people, food or the lab.')
        chart = ranked_bars(items, f'Reads by {rank} in {assay}', total=total, tips=tips) if items else ''
        meter = ''
        if assigned:
            meter = '<div class="ranks">' + ''.join(
                f'<div class="rk"><div class="rkl">{esc(n)}</div><div class="meter"><span style="width:{100 * v:.0f}%">'
                f'</span></div><div class="rkv">{100 * v:.0f}%</div></div>' for n, v in assigned) + '</div>'
        sub = (f'{plural(int((reads > 0).sum()), "ASV or taxon", "ASVs or taxa")} with reads in samples; '
               f'{fmt(total)} reads. Bars: share of reads by {rank}.')
        body = (chart + ('<h3>Share of reads named at each rank</h3>' + meter if meter else '')
                + (f'<p class="small">{esc(tnote)}</p>' if tnote else '')
                + table_view([rank.capitalize() if rank else 'Group', 'Reads', 'Share', 'ASVs', 'Most reads'],
                             [(g, fmt(v), f'{100 * v / total:.1f}%', n, m) for (g, v, n), m in zip(items, mains or [''] * len(items))],
                             keys=[g for g, _, _ in items]))
        out.append(card(f'What was detected: {assay}', esc(sub), body))
    return ''.join(out)


def target_set(target, taxa):
    t = target.lower()
    for word, rank, names in TARGET_WORDS:
        if word in t and rank in taxa:
            return rank, names
    for word in re.findall(r'[A-Z][a-z]+', target):
        for rank in RANKS:
            if rank in taxa and (taxa[rank].astype(str) == word).any():
                return rank, {word}
    return None


def panel_qpcr(wb, flags):
    a = wb.amp
    if not len(a) or 'quantificationCycle' not in a:
        return ''
    kinds = {str(r['samp_name']): sample_kind(r) for _, r in wb.samples.iterrows()}
    out = []
    for assay, grp in a.groupby('assay_name', sort=False):
        cq = [(str(r['samp_name']), num(r['quantificationCycle'])) for _, r in grp.iterrows()]
        amp = [(n, v) for n, v in cq if v is not None]
        reps = [(str(r['samp_name']), r.get('technical_rep_id'), num(r['quantificationCycle']), r.get('_row'))
                for _, r in grp.iterrows() if num(r['quantificationCycle']) is not None]
        cycles = num(wb.get('pcr_cycles', assay))
        if cycles:
            over = sorted({n for n, v in amp if v > cycles})
            if over:
                flags.add('problem', 'qPCR', f'{assay}: {plural(len(over), "sample")} with a Cq above the {fmt(cycles)} cycles '
                                             f'run: {listing(over)}.')
        neg = sorted({n for n, v in amp if kinds.get(n, ('sample', ''))[0] == 'control'
                      and 'positive' not in kinds.get(n, ('', ''))[1]})
        if neg:
            flags.add('check', 'qPCR', f'{assay}: negative controls amplified: {listing(neg)}.')
        pos = sorted({n for n, (k, t) in kinds.items() if 'positive' in t})
        pos_fail = [n for n in pos if n in set(grp['samp_name'].astype(str)) and not any(m == n for m, _ in amp)]
        if pos_fail:
            flags.add('check', 'qPCR', f'{assay}: positive controls that did not amplify: {listing(pos_fail)}.')
        if not amp:
            continue
        lo = math.floor(min(v for _, v in amp))
        hi = math.ceil(max(max(v for _, v in amp), cycles or 0))
        bins = list(range(lo, hi + 1))

        def group(n):
            kind, ctype = kinds.get(n, ('sample', ''))
            return 'sample' if kind == 'sample' else ('positive' if 'positive' in ctype else 'negative')
        counts = {g: Counter(math.floor(v) for n, v in amp if group(n) == g) for g in ('sample', 'negative', 'positive')}
        present = [g for g in ('sample', 'negative', 'positive') if counts[g]]
        colour = {'sample': '--s1', 'negative': '--s2', 'positive': '--s3'}
        name = {'sample': 'samples', 'negative': 'negative controls', 'positive': 'positive controls'}
        vals, cols, labs, keys = [], [], [], []
        for b in bins:   # the groups as neighbouring columns in each cycle
            for g in present:
                these = [(n, rep, v) for n, rep, v, _ in reps if group(n) == g and math.floor(v) == b]
                vals.append(len(these))
                cols.append(colour[g])
                labs.append(f'Cq {b} to {b + 1}: {plural(len(these), "reaction")} of {name[g]}\n'
                            + listing([f'{n} (replicate {rep}, Cq {v:.1f})' for n, rep, v in sorted(these)], 10))
                keys.append('|'.join(sorted({n for n, _, _ in these})))
        vline = ((cycles - lo + 1) * len(present), f'{fmt(cycles)} cycles') if cycles and lo <= cycles <= hi else None
        chart = column_chart(vals, cols, labs, f'Cq values for {assay}', height=150, vline=vline, keys=keys)
        chart += f'<div class="axislabels"><span>Cq {lo}</span><span>Cq {hi}</span></div>'
        n_na = len(cq) - len(amp)
        sub = f'{plural(len(cq), "reaction")}: {len(amp)} amplified, {n_na} did not. Reactions per cycle.'
        det_col = f'detected_notDetected_{assay}'
        if det_col in wb.samples:
            d = Counter(detection(v) for v in wb.samples[det_col] if not missing(v))
            sub += ' Samples: ' + ', '.join(f'{v} {k}' for k, v in d.most_common()) + '.'
        keys = [(colour[g], name[g].capitalize(), 'sq') for g in present]
        table = table_view(['Sample', 'Kind', 'Replicate', 'Cq', 'ampData row', 'sampleMetadata'],
                           [(n, kinds.get(n, ('', '?'))[1], rep, f'{v:.2f}', r, wb.row(n)) for n, rep, v, r in sorted(reps, key=lambda x: -x[2])],
                           'Show the reactions that amplified', keys=[n for n, _, _, _ in sorted(reps, key=lambda x: -x[2])])
        out.append(card(f'qPCR: {assay}', esc(sub), legend(keys) + chart + table))
    return ''.join(out)


def filled(v):
    return not (v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip() == '')


def panel_completeness(wb, flags):
    rows = []
    level_names = [('M', 'Mandatory'), ('HR', 'Highly recommended'), ('R', 'Recommended')]

    def summarise(sheet, df, levels):
        cells = {}
        for code, _ in level_names:
            terms = [t for t, l in levels.items() if l == code and t in df]
            if not terms:
                cells[code] = None
                continue
            n_given = sum(any(filled(v) for v in df[t]) for t in terms)
            empties = sum(int(sum(not filled(v) for v in df[t])) for t in terms) if code == 'M' else 0
            cells[code] = (n_given, len(terms), empties)
        rows.append((sheet, cells))

    if wb.project:
        cells = {}
        for code, _ in level_names:
            terms = [t for t, l in wb.project_levels.items() if l == code]
            given = [t for t in terms if filled(wb.project[t]['project']) or wb.project[t]['assays']]
            cells[code] = (len(given), len(terms), 0) if terms else None
        rows.append(('projectMetadata', cells))
    if len(wb.samples):
        summarise('sampleMetadata', wb.samples, wb.levels)
    if len(wb.runs):
        summarise('experimentRunMetadata', wb.runs, wb.run_levels)
    if len(wb.amp):
        summarise('ampData', wb.amp, wb.amp_levels)
    missing_n = 0
    for df in (wb.samples, wb.runs):
        if len(df):
            missing_n += int(df.map(lambda v: isinstance(v, str) and v.lower().startswith('missing')).sum().sum())
    if missing_n:
        flags.add('note', 'Completeness', f'{plural(missing_n, "cell")} say "missing: ..." in the sample and run sheets.')
    head = ''.join(f'<th>{n}</th>' for _, n in level_names)
    body = []
    for sheet, cells in rows:
        tds = []
        for code, _ in level_names:
            c = cells.get(code)
            if not c:
                tds.append('<td class="na">none</td>')
                continue
            n, tot, _ = c
            tds.append(f'<td><div class="meter"><span style="width:{100 * n / tot:.0f}%"></span></div>'
                       f'<span class="small">{n} of {tot} terms</span></td>')
        body.append(f'<tr><td>{esc(sheet)}</td>{"".join(tds)}</tr>')
    return card('How complete', 'Terms with a value in at least one row, by requirement level. Some '
                                'mandatory terms apply only to some rows (pos_cont_type to positive controls); '
                                'FAIRe-fier checks the mandatory values.',
                f'<div class="tv"><table class="comp"><tr><th>Sheet</th>{head}</tr>{"".join(body)}</table></div>')


def panel_publish(wb):
    kinds = {str(r['samp_name']): sample_kind(r)[0] for _, r in wb.samples.iterrows()} if len(wb.samples) else {}
    tiles = []
    tables = wb.final_tables()
    if tables:
        recs = seqs = 0
        names = set()
        ctrl_cols = set()
        for t in tables:
            reads = t['reads']
            scols = [c for c in reads.columns if kinds.get(str(c), 'sample') == 'sample']
            ctrl_cols |= {str(c) for c in reads.columns if kinds.get(str(c)) == 'control'}
            nz = (reads[scols] > 0)
            per_taxon = nz.sum(axis=1)
            recs += int(per_taxon.sum())
            taxa = t['taxa']
            if len(taxa) and 'dna_sequence' in taxa:
                has = {sid for sid in taxa.index if filled(taxa.at[sid, 'dna_sequence'])}
                seqs += int(sum(v for sid, v in per_taxon.items() if sid in has))
            names |= {taxon_name(taxa, sid) for sid in per_taxon.index if per_taxon[sid] > 0}
        tiles = [('Occurrence records', recs), ('With a DNA sequence', seqs), ('Taxon names', len(names)),
                 ('Control columns left out', len(ctrl_cols))]
        sub = 'One record per sample and ASV or taxon with reads, as FAIRe2MDT, edna2obis and FAIRe to Darwin Core make them.'
    elif any(c.startswith('detected_notDetected') for c in wb.samples.columns):
        cols = [c for c in wb.samples.columns if c.startswith('detected_notDetected')]
        vals = Counter()
        for c in cols:
            for _, r in wb.samples.iterrows():
                if kinds.get(str(r['samp_name'])) == 'sample' and not missing(r[c]):
                    vals[detection(r[c])] += 1
        tiles = [('Present records', vals.get('detected', 0)), ('Absent records', vals.get('not detected', 0)),
                 ('Assays', len(cols))]
        sub = 'One record per sample and assay, as FAIRe to Darwin Core makes them; controls are left out.'
    else:
        return ''
    body = '<div class="tiles">' + ''.join(f'<div class="tile"><div class="tl">{esc(a)}</div><div class="tv2">{fmt(b)}</div></div>'
                                           for a, b in tiles) + '</div>'
    return card('What GBIF or OBIS would receive', esc(sub), body)


# ---------------------------------------------------------------------------------------------
# The page

CSS = CSS_COLOURS + """
.page { margin:0; background:var(--plane); color:var(--ink); font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif; }
.wrap { max-width:1180px; margin:0 auto; padding:24px 20px 48px; }
header h1 { font-size:22px; margin:0 0 4px; font-weight:600; }
header p { margin:0; color:var(--ink2); }
.summary { display:flex; gap:16px; margin:16px 0 8px; flex-wrap:wrap; }
.summary span { background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:6px 12px; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(520px,1fr)); gap:16px; margin-top:16px; }
.card { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:16px 18px; min-width:0; }
.card.wide { grid-column:1/-1; }
.card h2 { font-size:16px; margin:0 0 2px; font-weight:600; }
.card h3 { font-size:13px; margin:14px 0 6px; font-weight:600; color:var(--ink2); }
.sub, .small { color:var(--ink2); font-size:12.5px; margin:0 0 10px; }
.empty { color:var(--ink2); }
.flagbox { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px 18px; margin-top:16px; }
.flagbox h2 { font-size:16px; margin:0 0 8px; }
.flags { list-style:none; padding:0; margin:0; }
.flags li { display:grid; grid-template-columns:18px 64px 110px 1fr; gap:6px; padding:5px 0; border-top:1px solid var(--grid); align-items:baseline; }
.flags li:first-child { border-top:0; }
.flags .lvl { font-weight:600; font-size:12.5px; }
.flags .area { color:var(--ink2); font-size:12.5px; }
.ico { display:inline-block; width:14px; text-align:center; font-size:12px; }
.ico.critical { color:var(--critical); } .ico.warn { color:var(--warn); } .ico.muted { color:var(--muted); } .ico.good { color:var(--good); }
.allclear { margin:0; }
svg.chart { display:block; max-width:100%; height:auto; }
.grid line, line.grid { stroke:var(--grid); stroke-width:1; }
line.axis { stroke:var(--axis); stroke-width:1; }
line.ref { stroke:var(--ink2); stroke-width:1; }
text.tick, text.lab, text.val { fill:var(--ink2); font-size:11px; font-variant-numeric:tabular-nums; }
text.lab { fill:var(--ink); font-size:12px; }
.legend { display:flex; gap:14px; flex-wrap:wrap; margin:0 0 8px; font-size:12.5px; color:var(--ink2); }
.legend i { display:inline-block; width:10px; height:10px; margin-right:6px; vertical-align:-1px; }
.legend i.dot { border-radius:50%; } .legend i.sq { border-radius:2px; }
.legend i.ring { border-radius:50%; background:transparent !important; border:2px solid var(--ink2); width:8px; height:8px; }
.legend i.ring[style*="critical"] { border-color:var(--critical); }
.axislabels { display:flex; justify-content:space-between; color:var(--ink2); font-size:11px; padding-left:44px; }
details { margin-top:10px; font-size:12.5px; } summary { cursor:pointer; color:var(--ink2); }
.tv { overflow-x:auto; } table { border-collapse:collapse; font-size:12.5px; margin-top:6px; }
th, td { text-align:left; padding:4px 10px 4px 0; border-bottom:1px solid var(--grid); vertical-align:middle; }
th { color:var(--ink2); font-weight:600; } td.n { text-align:right; font-variant-numeric:tabular-nums; }
td.na { color:var(--muted); }
.tiles { display:flex; gap:12px; flex-wrap:wrap; margin:4px 0 10px; }
.tile { border:1px solid var(--border); border-radius:10px; padding:8px 14px; min-width:110px; }
.tl { color:var(--ink2); font-size:12px; } .tv2 { font-size:24px; font-weight:600; }
ul.plain { margin:6px 0 0; padding-left:18px; color:var(--ink2); font-size:12.5px; }
ul.checks { list-style:none; padding:0; margin:0; } ul.checks li { padding:3px 0; }
.meter { height:8px; border-radius:4px; background:var(--grid); overflow:hidden; min-width:80px; }
.meter span { display:block; height:100%; background:var(--s1); border-radius:4px; }
table.comp td { min-width:120px; } table.comp .small { display:block; margin:2px 0 0; }
.ranks { display:grid; gap:4px; }
.rk { display:grid; grid-template-columns:70px 1fr 40px; gap:8px; align-items:center; font-size:12px; color:var(--ink2); }
.rkv { text-align:right; font-variant-numeric:tabular-nums; }
footer { margin-top:24px; color:var(--ink2); font-size:12px; }
#tip { position:fixed; display:none; pointer-events:none; z-index:10; max-width:380px; white-space:pre-line;
  background:var(--ink); color:var(--surface); padding:7px 10px; border-radius:6px; font-size:12px; line-height:1.4;
  box-shadow:0 2px 8px rgba(0,0,0,0.25); }
svg .hit { cursor:pointer; }
tr.hit td { background:color-mix(in srgb, var(--s1) 16%, transparent); }
@media (max-width:600px) { .grid { grid-template-columns:1fr; } .flags li { grid-template-columns:18px 1fr; } .flags .area, .flags .lvl { display:none; } }
"""


TIP_SCRIPT = """<div id="tip" role="tooltip"></div>
<script>
(function () {
  var tip = document.getElementById('tip');
  document.querySelectorAll('svg title').forEach(function (t) {
    t.parentNode.setAttribute('data-tip', t.textContent); t.remove();
  });
  document.addEventListener('mousemove', function (e) {
    var el = e.target.closest ? e.target.closest('[data-tip]') : null;
    if (!el) { tip.style.display = 'none'; return; }
    tip.textContent = el.getAttribute('data-tip'); tip.style.display = 'block';
    var r = tip.getBoundingClientRect(), x = e.clientX + 14, y = e.clientY + 14;
    if (x + r.width > window.innerWidth - 8) { x = e.clientX - r.width - 14; }
    if (y + r.height > window.innerHeight - 8) { y = e.clientY - r.height - 14; }
    tip.style.left = Math.max(4, x) + 'px'; tip.style.top = Math.max(4, y) + 'px';
  });
  document.addEventListener('click', function (e) {
    var el = e.target.closest ? e.target.closest('svg [data-key]') : null;
    if (!el) { return; }
    var card = el.closest('.card'), keys = el.getAttribute('data-key').split('|'), first = null;
    if (!card) { return; }
    card.querySelectorAll('details').forEach(function (d) { d.open = true; });
    card.querySelectorAll('tr.hit').forEach(function (r) { r.classList.remove('hit'); });
    card.querySelectorAll('tr[data-key]').forEach(function (r) {
      var mine = r.getAttribute('data-key').split('|');
      if (mine.some(function (k) { return keys.indexOf(k) >= 0; })) { r.classList.add('hit'); first = first || r; }
    });
    if (first) { first.scrollIntoView({block: 'center', behavior: 'smooth'}); }
  });
})();
</script>"""


def build(path, out_html, flags_tsv=None, coastline=COASTLINE):
    wb = Workbook(path)
    flags = Flags()
    land = Land(coastline)
    panels = [panel_map(wb, flags, land), panel_dates(wb, flags), panel_counts(wb, flags),
              panel_environment(wb, flags), panel_links(wb, flags), panel_reads(wb, flags),
              panel_taxa(wb, flags), panel_qpcr(wb, flags), panel_publish(wb), panel_completeness(wb, flags)]
    title = wb.get('project_name') or wb.get('project_id') or wb.path.stem
    pid = wb.get('project_id') or ''
    assay_type = wb.get('assay_type') or ''
    p, c, n = flags.counts()
    summary = (f'<div class="summary"><span><span class="ico critical">▲</span> {plural(p, "problem")}</span>'
               f'<span><span class="ico warn">●</span> {plural(c, "thing")} to check</span>'
               f'<span><span class="ico muted">○</span> {plural(n, "note")}</span></div>')
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sense check: {esc(title)}</title><style>{CSS}</style></head>
<body class="page"><div class="wrap">
<header><h1>Sense check: {esc(title)}</h1>
<p>{esc(pid)}{" · " if pid else ""}{esc(assay_type)}{" · " if assay_type else ""}{esc(" | ".join(wb.assays))} · {esc(wb.path.name)}</p></header>
{summary}
<section class="flagbox"><h2>What to look at</h2>{flags.html()}</section>
<div class="grid">{"".join(x for x in panels if x)}</div>
<footer>FAIRe sense check {__version__}, {dt.date.today().isoformat()}. A quick look at the data, not a full
check: review the workbook and run FAIRe-fier before you submit it. Coastline: Natural Earth 1:50 million
(public domain). Hover over a mark to see what it is; click it to find its rows in the chart's table.
Row numbers are those of the workbook's sheets.</footer>
</div>{TIP_SCRIPT}</body></html>"""
    Path(out_html).write_text(page, encoding='utf-8')
    if flags_tsv:
        pd.DataFrame(flags.items, columns=['level', 'area', 'message']).to_csv(flags_tsv, sep='\t', index=False)
    return flags


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('workbook', help='a FAIRe workbook (.xlsx)')
    ap.add_argument('-o', '--output', default='sense_check.html', help='the HTML page to write')
    ap.add_argument('--flags', help='also write the flags as a tab-separated table')
    ap.add_argument('--coastline', default=str(COASTLINE), help=argparse.SUPPRESS)
    ap.add_argument('--version', action='version', version=__version__)
    a = ap.parse_args(argv)
    flags = build(a.workbook, a.output, a.flags, a.coastline)
    p, c, n = flags.counts()
    print(f'INFO: wrote {a.output}: {plural(p, "problem")}, {plural(c, "thing")} to check, {plural(n, "note")}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
