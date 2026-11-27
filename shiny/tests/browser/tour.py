"""Screenshots of the app at each stage of the eelgrass demonstration, for before-and-after comparison.
Start the app first (on port 8765), then: python3 tests/browser/tour.py OUT_DIR [WIDTH]"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
width = int(sys.argv[2]) if len(sys.argv) > 2 else 1400
URL = 'http://127.0.0.1:8765/'


def tab(pg, value):
    pg.click(f"a[data-value='{value}']"); pg.wait_for_timeout(1500)


def shot(pg, name):
    pg.evaluate('() => window.scrollTo(0, 0)'); pg.wait_for_timeout(300)
    pg.screenshot(path=str(out / f'{name}.png'))
    print('saved', name)


with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    pg = b.new_page(viewport={'width': width, 'height': 1000})
    pg.goto(URL)
    pg.wait_for_selector('#load_demo', timeout=30000)
    pg.wait_for_function('() => window.Shiny && Shiny.shinyapp && Shiny.shinyapp.isConnected()', timeout=30000)
    shot(pg, '01_start_empty')
    pg.check('input[name=demo_choice][value=eelgrass]')
    pg.click('#load_demo'); pg.wait_for_timeout(1500)
    if pg.query_selector('#load_demo_ok'):
        pg.click('#load_demo_ok')
    pg.wait_for_selector('text=eelgrass_notes.md', timeout=30000); pg.wait_for_timeout(1500)
    shot(pg, '02_start_demo_loaded')
    pg.click('#start_mapper'); pg.wait_for_timeout(1500)
    shot(pg, '03_a_files')
    pg.click('#run_identify'); pg.wait_for_selector('#identify_result table, #identify_result .res-ok', timeout=120000)
    pg.wait_for_timeout(1500)
    shot(pg, '04_a_identified')
    tab(pg, 'b. Propose a mapping')
    shot(pg, '05_b_form')
    pg.click('#run_map'); pg.wait_for_timeout(3000)
    tab(pg, 'c. Review the mapping')
    pg.wait_for_selector('#demo_answers', state='visible', timeout=300000); pg.wait_for_timeout(2000)
    shot(pg, '06_c_review')
    pg.click('#demo_answers'); pg.wait_for_timeout(2000)
    shot(pg, '07_c_answers_unsaved')
    pg.click('#save_review'); pg.wait_for_timeout(2500)
    tab(pg, 'd. Methods and project values')
    shot(pg, '08_d_methods')
    tab(pg, 'e. Write the workbook')
    shot(pg, '09_e_write')
    tab(pg, '2. Check')
    shot(pg, '10_check')
    b.close()
