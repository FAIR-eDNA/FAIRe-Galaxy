"""Browser tests of the journeys through the app: what the next-step card and the journey bar say at each
stage, as a person would go through it with the mouse and keyboard. Start the app first:

    FAIRE_PYTHON=python3 Rscript -e 'shiny::runApp(".", port = 8765, launch.browser = FALSE)'

then, from the shiny folder: python3 tests/browser/journeys.py [WORKBOOK]

WORKBOOK is a FAIRe workbook for the existing-workbook journey (the eelgrass flow's, by default). Needs
Playwright and Google Chrome. Prints PASS or FAIL for each check and exits 1 on a failure."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = 'http://127.0.0.1:8765/'
WORKBOOK = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ux_091/eelgrass_workbook.xlsx'
WORDS = {'Done', 'To do', 'Optional', 'Out of date', 'Waiting', 'Not needed'}
failures = []


def check(ok, what):
    print('PASS' if ok else 'FAIL', what)
    if not ok:
        failures.append(what)


def open_app(b, width=1400, height=950):
    pg = b.new_page(viewport={'width': width, 'height': height})
    pg.goto(URL)
    pg.wait_for_selector('#load_demo', timeout=30000)
    pg.wait_for_function('() => window.Shiny && Shiny.shinyapp && Shiny.shinyapp.isConnected()', timeout=30000)
    pg.wait_for_selector('#next-step-side .ns-title, #next-step-top .ns-title', state='attached', timeout=30000)
    pg.wait_for_timeout(800)
    return pg


def card(pg, where='side'):
    return pg.inner_text(f'#next-step-{where} .ns-title').strip()


def wait_card(pg, title, timeout=300000, where='side'):
    try:
        pg.wait_for_function(
            '([w, t]) => { const e = document.querySelector(`#next-step-${w} .ns-title`); return e && e.textContent.trim() === t; }',
            arg=[where, title], timeout=timeout)
        return True
    except Exception:
        return False


def expect_card(pg, title, what, timeout=300000):
    ok = wait_card(pg, title, timeout)
    check(ok, f'{what}: next step "{title}"' + ('' if ok else f' (it says "{card(pg)}")'))


def bar_status(pg, n):
    return pg.inner_text(f'.journey li:nth-child({n}) .st-tag').strip()


def active_pill(pg):
    return pg.evaluate("() => { const a = document.querySelector('#mapper_steps .nav-link.active'); return a ? a.innerText.split('\\n')[0] : ''; }")


def wait_rd_table(pg):
    """The readiness table, once it has its 'This workbook' column (the workbook is read)."""
    pg.wait_for_function("() => document.querySelectorAll('.rd-table thead th').length === 3", timeout=30000)
    pg.wait_for_timeout(500)


def rd_row(pg, dest):
    """The 'This workbook' cell of a destination in the Convert page's readiness table."""
    return pg.evaluate("""(d) => { const r = Array.from(document.querySelectorAll('.rd-table tbody tr'))
                                     .find(tr => tr.cells[0].innerText.trim() === d);
                                   return r && r.cells[2] ? r.cells[2].innerText : ''; }""", dest)


def active_cv_tab(pg):
    return pg.evaluate("() => { const a = document.querySelector('#cv_tabs .nav-link.active'); return a ? a.innerText.trim() : ''; }")


def shown(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return !!(e && e.offsetParent); }", sel)


def menus_closed(pg):
    return not pg.evaluate("() => Array.from(document.querySelectorAll('.navbar .dropdown-menu')).some(m => m.classList.contains('show'))")


def go_card(pg):
    pg.click('#next-step-side .ns-go')
    pg.wait_for_timeout(1500)
    if not menus_closed(pg):
        check(False, 'after going to a step, the Make a workbook menu is closed')


def load_demo(pg, name):
    pg.check(f'input[name=demo_choice][value={name}]')
    pg.click('#load_demo')
    pg.wait_for_timeout(1500)
    if pg.query_selector('#load_demo_ok'):
        pg.click('#load_demo_ok')
    pg.wait_for_timeout(2500)


def colour_free(pg, what):
    """Every status shown carries a word, not only a colour"""
    tags = pg.evaluate("() => Array.from(document.querySelectorAll('.st-tag')).filter(e => e.offsetParent !== null)"
                       ".map(e => [e.textContent.trim(), !!e.querySelector('i, svg')])")
    check(len(tags) > 0 and all(t in WORDS or t.endswith(':') for t, _ in tags) and all(i for _, i in tags),
          f'{what}: every status has an icon and a word ({len(tags)} shown)')
    pills = pg.evaluate("() => Array.from(document.querySelectorAll('#mapper_steps .step-status')).map(e => e.textContent.trim())")
    check(all(any(w in p for w in WORDS) for p in pills), f'{what}: each mapper step says its status in words')


with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])

    print('== 1. Blank template (FAIRe-ator)')
    pg = open_app(b)
    expect_card(pg, 'Add your files to start', 'empty')
    check(bar_status(pg, 2) == 'Waiting', 'empty: mapping waits for files')
    pg.click('#next-step-side .ns-more:has-text("Make a blank template")')
    pg.wait_for_timeout(1200)
    pg.fill('#fa_project_id', 'UXtest')
    pg.fill('#fa_assay_name', 'Fish16S')
    check(not shown(pg, '#faireator_result'), 'FAIRe-ator: no result panel before the template is made')
    pg.click('#run_faireator')
    expect_card(pg, 'Fill in your template', 'template made', 120000)
    check(shown(pg, '#faireator_result'), 'FAIRe-ator: the result panel appears once the template is made')
    href = pg.get_attribute('#next-step-side a.ns-go', 'href') or ''
    check(href.endswith('UXtest.xlsx'), 'template made: the card downloads the template')
    check(bar_status(pg, 1) == 'Not needed', 'template: the mapper steps are not needed')
    tmpl = Path('/tmp/ux_template_UXtest.xlsx')
    with pg.expect_download() as dl:
        pg.click('#next-step-side a.ns-go')
    dl.value.save_as(tmpl)
    pg.set_input_files('#upload', str(tmpl))
    expect_card(pg, 'Check the workbook', 'template added', 60000)
    go_card(pg)
    pg.click('#run_fairefier')
    expect_card(pg, 'Fix the errors and check again', 'blank template checked')
    colour_free(pg, 'template')
    pg.close()

    print('== 2. Mapper, metabarcoding (eelgrass), with unsaved, missing and out-of-date states')
    pg = open_app(b)
    load_demo(pg, 'eelgrass')
    expect_card(pg, 'Identify your files', 'demo loaded')
    go_card(pg)
    check(active_pill(pg).startswith('a. Prepare your files'), 'the card goes to a.')
    pg.click('#run_identify')
    expect_card(pg, 'Map your sample information', 'identified')
    go_card(pg)
    check(not shown(pg, '#map_result'), 'b: no Proposed mapping panel before the mapping is proposed')
    pg.click('#run_map')
    expect_card(pg, 'Review the uncertain matches', 'mapped')
    check(shown(pg, '#map_result'), 'b: the Proposed mapping panel appears once the mapping is proposed')
    check('need' in pg.inner_text('#next-step-side .ns-attention'), 'mapped: the card says how many columns need a decision')
    go_card(pg)
    check(menus_closed(pg), 'after going to a step, the Make a workbook menu is closed')
    pg.wait_for_selector('#demo_answers', state='visible', timeout=60000)
    # the high-confidence matches are in a fold below the rows to decide, closed at first
    fold_btn = '#rv_show_accepted_btn'

    def shown():
        return pg.evaluate("() => Array.from(document.querySelectorAll('#rv_show_accepted_rows .rv-row')).filter(e => e.offsetParent !== null).length")
    label = pg.inner_text(fold_btn)
    check('high-confidence match' in label and 'accepted by default' in label and shown() == 0,
          f'review: the accepted matches are folded under "{label.splitlines()[0]}"')
    pg.click(fold_btn)
    pg.wait_for_timeout(400)
    n_open = shown()
    check(n_open > 0 and pg.get_attribute(fold_btn, 'aria-expanded') == 'true', f'review: opening the fold shows the {n_open} matches')
    pg.click('#demo_answers')
    expect_card(pg, 'Save your review', 'decisions changed, not saved', 30000)
    check('To do' in pg.inner_text('#mapper_steps .nav-link.active'), 'unsaved: step c says To do')
    decided = pg.evaluate("() => Array.from(document.querySelectorAll('#review-grid select[id^=rvd]')).filter(s => s.value).length")
    # away and back, by the bar: nothing is lost
    pg.click('.journey li:nth-child(1) .j-link')
    pg.wait_for_timeout(1200)
    check(active_pill(pg).startswith('a.'), 'the bar goes back to a.')
    pg.click('.journey li:nth-child(3) .j-link')
    pg.wait_for_timeout(1500)
    again = pg.evaluate("() => Array.from(document.querySelectorAll('#review-grid select[id^=rvd]')).filter(s => s.value).length")
    check(active_pill(pg).startswith('c.') and again == decided, f'back at c., the {decided} decisions are still there')
    check(card(pg) == 'Save your review', 'moving about does not lose the unsaved state')
    pg.click('#save_review')
    expect_card(pg, 'Find the primers and method details', 'review saved', 30000)
    pg.wait_for_timeout(1000)
    check(shown() == n_open, 'review: the fold stays open after saving')
    go_card(pg)
    pg.click('#methods_steps > .accordion-item[data-value=primers] .accordion-button')
    pg.wait_for_timeout(800)
    pg.click('#run_primers')
    pg.wait_for_selector('.pr-item', timeout=180000)
    pg.wait_for_timeout(1000)
    pg.click('#pr_add')
    pg.wait_for_timeout(2000)
    pg.click('#methods_steps > .accordion-item[data-value=details] .accordion-button')
    pg.wait_for_timeout(800)
    pg.click('#run_details')
    pg.wait_for_selector('#md_add', timeout=180000)
    pg.wait_for_timeout(1000)
    pg.click('#md_add')
    pg.wait_for_timeout(2000)
    if pg.query_selector('.modal #md_add_confirm'):
        pg.click('#md_add_confirm')
        pg.wait_for_timeout(1500)
    expect_card(pg, 'Complete the mandatory project information', 'values found', 30000)
    n_missing = len(pg.query_selector_all('.mt-row'))
    check(f'{n_missing} mandatory term' in pg.inner_text('#next-step-side .ns-attention'),
          f'missing: the card states the number ({n_missing})')
    go_card(pg)
    values = {'recordedBy': 'A Person', 'project_contact': 'a.person@example.org', 'project_id': 'NS_eelgrass_eDNA'}
    for row in pg.query_selector_all('.mt-row'):
        term = row.query_selector('label b').inner_text().strip()
        box = row.query_selector('input[type=text]:not([id^=mt_assay])')
        if row.query_selector('select'):
            row.query_selector('.selectize-input').click()
            pg.keyboard.type('1')
            pg.keyboard.press('Enter')
        elif box:
            box.fill(values.get(term, 'missing: not provided'))
    pg.click('#mt_add')
    expect_card(pg, 'Build the FAIRe workbook', 'mandatory terms given', 30000)
    go_card(pg)
    pg.click('#run_apply')
    expect_card(pg, 'Check the workbook', 'workbook built', 240000)
    check(pg.query_selector('.wb-card') is not None, 'built: the workbook is in use in the sidebar')
    # a change after building makes the workbook out of date
    pg.wait_for_timeout(1100)
    pg.evaluate("() => { Shiny.setInputValue('pv_term', 'samp_store_sol'); Shiny.setInputValue('pv_value', 'none');"
                " Shiny.setInputValue('pv_assay', ''); Shiny.setInputValue('pv_add', Math.random(), {priority: 'event'}); }")
    expect_card(pg, 'Rebuild the workbook', 'project values changed after building', 30000)
    check(bar_status(pg, 5) == 'Out of date' and bar_status(pg, 6) == 'Waiting', 'out of date: step 5 Out of date, step 6 Waiting')
    check(pg.query_selector('#current_workbook .stale-note') is not None, 'out of date: the sidebar says so')
    colour_free(pg, 'out of date')
    go_card(pg)
    pg.click('#run_apply')
    expect_card(pg, 'Check the workbook', 'rebuilt', 240000)
    go_card(pg)
    pg.click('#run_fairefier')
    ok = wait_card(pg, 'Convert it, if you need to', 240000) or wait_card(pg, 'Fix the errors and check again', 1000)
    check(ok, f'checked: the card says "{card(pg)}"')
    if card(pg) == 'Convert it, if you need to':
        check(bar_status(pg, 7) == 'Optional', 'passed: converting is optional')
        go_card(pg)
        check(pg.evaluate("() => document.querySelector('.navbar .nav-link.active').textContent.includes('Convert')"),
              'passed: the card goes to the Convert page')
        # The demonstration gives no sequencing run ID: the table says GBIF (MDT) needs one, its link opens
        # the tab, and the box above the button goes to the run ID of the OTU table in step e
        wait_rd_table(pg)
        check('Needs a run ID' in rd_row(pg, 'GBIF (MDT)'), 'convert: the table says GBIF (MDT) needs a run ID')
        check('Ready' in rd_row(pg, 'GBIF and OBIS (presence and absence)'), 'convert: the table says presence records are ready')
        pg.click('.rd-table a:has-text("GBIF (MDT)")')
        pg.wait_for_selector('#rdbox_mdt button', timeout=20000)
        check(active_cv_tab(pg) == 'GBIF (MDT)', 'convert: the table opens the GBIF (MDT) tab')
        check('run ID' in pg.inner_text('#rdbox_mdt'), 'convert: FAIRe2MDT says the workbook has no run ID')
        pg.click('#rdbox_mdt button')
        pg.wait_for_timeout(1500)
        focus = pg.evaluate("() => document.activeElement && document.activeElement.id")
        check(focus.endswith('_1_run') and pg.is_visible(f'#{focus}'), f'convert: the button goes to the run ID in step e ({focus})')
        check(menus_closed(pg), 'convert: no menu left open after going to step e')
        pg.fill(f'#{focus}', 'AGRF_2024-12')
        pg.click('#run_apply')
        expect_card(pg, 'Check the workbook', 'rebuilt with a run ID', 240000)
        pg.click('a.nav-link:has-text("Convert")')
        pg.click('a.nav-link:has-text("GBIF (MDT)")')
        pg.wait_for_timeout(2000)
        runs = pg.evaluate("() => { const s = document.getElementById('mdt_run'); return s ? Array.from(s.options).map(o => o.value) : []; }")
        check(runs == ['AGRF_2024-12'] and pg.locator('#rdbox_mdt.rd-ready').count() == 1, f'convert: FAIRe2MDT now offers the run ({runs})')
        check(rd_row(pg, 'GBIF (MDT)').strip().startswith('Ready'), 'convert: the table says GBIF (MDT) is ready')
        pg.click('#run_mdt')
        pg.wait_for_selector('#mdt_result .res-ok, #mdt_result .res-fail', timeout=240000)
        check(pg.locator('#mdt_result .res-ok').count() > 0, 'convert: FAIRe2MDT writes the MDT workbook')
    pg.close()

    print('== 3. An existing FAIRe workbook')
    pg = open_app(b)
    pg.set_input_files('#upload', WORKBOOK)
    expect_card(pg, 'Check the workbook', 'workbook added', 60000)
    check(all(bar_status(pg, i) == 'Not needed' for i in range(1, 6)), 'workbook: steps 1 to 5 not needed')
    go_card(pg)
    pg.click('#run_fairefier')
    ok = wait_card(pg, 'Convert it, if you need to', 240000)
    check(ok, f'workbook checked: the card says "{card(pg)}"')
    go_card(pg)
    check(pg.evaluate("() => document.querySelector('.navbar .nav-link.active').textContent.includes('Convert')"),
          'workbook: on to the Convert page')
    # The eelgrass workbook gives no sequencing run ID: the table says so before FAIRe2MDT is run, and, as
    # the workbook was added rather than written here, the box says to fill it in the workbook
    wait_rd_table(pg)
    check('Needs a run ID' in rd_row(pg, 'GBIF (MDT)'), 'convert: the table says the workbook has no run ID')
    check('read file names' in rd_row(pg, 'NCBI'), 'convert: the table says NCBI SRA needs read file names')
    pg.click('a.nav-link:has-text("GBIF (MDT)")')
    pg.wait_for_selector('#rdbox_mdt', timeout=20000)
    note = pg.inner_text('#rdbox_mdt')
    check('run ID' in note and 'fill seq_run_id' in note and pg.locator('#rdbox_mdt button').count() == 0,
          'convert: FAIRe2MDT says why it is not ready, and where to add a run ID')
    # The QIIME 2 box follows its form: metadata only needs no read files
    pg.click('a.nav-link:has-text("QIIME 2")')
    pg.wait_for_selector('#rdbox_qiime', timeout=20000)
    check('rd-needs' in pg.get_attribute('#rdbox_qiime', 'class'), 'convert: QIIME 2 with manifests needs read file names')
    pg.check('input[name=qi_manifests][value=no]')
    pg.wait_for_timeout(1500)
    check('rd-ready' in pg.get_attribute('#rdbox_qiime', 'class'), 'convert: QIIME 2 metadata only is ready')
    pg.click('#run_qiime')
    pg.wait_for_selector('#qiime_result .res-ok, #qiime_result .res-fail', timeout=240000)
    check(pg.locator('#qiime_result .res-ok').count() > 0, 'convert: QIIME 2 writes the metadata, as the box said it would')
    pg.close()

    print('== 4. Targeted (khapra)')
    pg = open_app(b)
    load_demo(pg, 'khapra')
    pg.click('.journey li:nth-child(5) .j-link')
    pg.wait_for_timeout(2000)
    titles = pg.evaluate("() => Array.from(document.querySelectorAll('.e-src-sheet')).map(e => e.textContent)")
    check(any('qPCR or ddPCR' in t for t in titles) and not any('OTU' in t for t in titles), 'targeted: e asks for qPCR or ddPCR results')
    heads = pg.evaluate("() => Array.from(document.querySelectorAll('.step-card > .card-header')).filter(e => e.offsetParent !== null).map(e => e.innerText.trim())")
    check(any(h.startswith('3. Build the workbook') for h in heads), 'targeted: three steps in e')
    pg.close()
    # The khapra workbook the flows wrote, next to WORKBOOK: only presence and absence records suit it
    khapra = Path(WORKBOOK).with_name('khapra_workbook.xlsx')
    if not khapra.exists():
        check(False, f'targeted: no {khapra} (run tests/flows/khapra.R with the same FAIRE_TEST_OUT)')
    else:
        pg = open_app(b)
        pg.set_input_files('#upload', str(khapra))
        expect_card(pg, 'Check the workbook', 'targeted workbook added', 60000)
        pg.click('.navbar a.nav-link:has-text("Convert")')
        wait_rd_table(pg)
        check('Not for a targeted study' in rd_row(pg, 'GBIF (MDT)') and 'Not for a targeted study' in rd_row(pg, 'NCBI'),
              'targeted: the table says the sequence conversions are not for this study')
        check(rd_row(pg, 'GBIF and OBIS (presence and absence)').strip().startswith('Ready'),
              'targeted: presence and absence is ready')
        pg.click('a.nav-link:has-text("QIIME 2")')
        pg.wait_for_selector('#rdbox_qiime.rd-not button', timeout=20000)
        pg.click('#rdbox_qiime button')
        pg.wait_for_timeout(1000)
        check(active_cv_tab(pg) == 'GBIF and OBIS (presence and absence)', 'targeted: the box opens the presence and absence tab')
        pg.close()

    print('== 5. Narrow screen')
    pg = open_app(b, 390, 844)
    pg.wait_for_selector('#next-step-top .ns-title', timeout=20000)
    pg.wait_for_selector('.journey ol', timeout=20000)
    check(pg.is_visible('#next-step-top') and not pg.is_visible('#next-step-side'), 'narrow: the next step is at the top of the page')
    over = pg.evaluate('() => document.documentElement.scrollWidth - window.innerWidth')
    check(over <= 1, f'narrow: the page does not scroll sideways ({over}px)')
    check(pg.evaluate("() => { const o = document.querySelector('.journey ol'); return o.scrollWidth >= o.clientWidth; }"),
          'narrow: the journey bar scrolls within itself')
    pg.click('#next-step-top .ns-more:has-text("Try the demonstration data")')
    pg.wait_for_timeout(1200)
    check(pg.is_visible('#load_demo'), 'narrow: the card leads to the demonstration')
    pg.screenshot(path='/tmp/ux_narrow.png')
    pg.close()

    print('== 6. Keyboard')
    pg = open_app(b)
    load_demo(pg, 'eelgrass')
    pg.focus('#next-step-side .ns-go')
    pg.keyboard.press('Enter')
    pg.wait_for_timeout(1500)
    check(active_pill(pg).startswith('a.'), 'keyboard: Enter on the card\'s button goes to the step')
    focused = pg.evaluate('() => document.activeElement && document.activeElement.className')
    check('card-header' in (focused or ''), 'keyboard: focus moves to the step\'s heading')
    pg.focus('.journey li:nth-child(2) .j-link')
    pg.keyboard.press('Enter')
    pg.wait_for_timeout(1500)
    check(active_pill(pg).startswith('b.'), 'keyboard: Enter on a journey step goes there')
    check(menus_closed(pg), 'keyboard: the Make a workbook menu is closed after going to a step')
    summ = pg.locator('summary:visible', has_text='More about this step').first
    summ.focus()
    pg.keyboard.press('Enter')
    pg.wait_for_timeout(300)
    check(pg.evaluate("() => Array.from(document.querySelectorAll('details.more-about')).some(d => d.open && d.offsetParent !== null)"),
          'keyboard: Enter opens More about this step')
    pg.locator('#map_more .accordion-button').focus()
    pg.keyboard.press('Enter')
    pg.wait_for_timeout(600)
    check(pg.is_visible('#map_header_row'), 'keyboard: Enter opens the table-reading settings')
    tabbable = pg.evaluate("() => Array.from(document.querySelectorAll('.journey .j-link, #next-step-side .ns-go')).every(e => e.tabIndex >= 0)")
    check(tabbable, 'keyboard: the journey steps and the card\'s action are in the tab order')
    pg.close()
    b.close()

print(f'{len(failures)} failed' if failures else 'All passed')
sys.exit(1 if failures else 0)
