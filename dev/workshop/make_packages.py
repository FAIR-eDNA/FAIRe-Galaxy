"""Makes a zip of each demonstration dataset, for a workshop that wants handouts: the published files
as downloaded (where the repository holds them) in published/, the files prepared for the app
(shiny/demo/<name>) in prepared/ (files/ for SEA-MES), the dataset's README, and the page of steps
(dev/workshop/sheets/<name>.md, as Markdown and as a web page made with pandoc if it is installed).
The pages link to the files in this repository; in a zip, the same files sit beside the page.

Usage: python dev/workshop/make_packages.py OUTDIR
"""

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
sheets = repo / 'dev' / 'workshop' / 'sheets'
PACKAGES = {
    # name: (zip name, published folder or None, published files, folder name for the app's files)
    'khapra': ('FAIRe_workshop_khapra_qPCR', repo / 'demo' / 'khapra',
               ['Sample_metadata.csv', 'Amplification_data_khapra_05012022_dryad.csv',
                'Trujillo_Gonzalez_et_al_2022_README.txt'], 'prepared'),
    'eelgrass': ('FAIRe_workshop_eelgrass_metabarcoding', repo / 'demo' / 'eelgrass',
                 ['Final_ASVTable_withTaxonomy_Filtered.csv', 'Site_coordinates.csv', 'Dryad_README.md'], 'prepared'),
    'seames': ('FAIRe_workshop_SEA-MES_metabarcoding', None, [], 'files'),
}

out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
pandoc = shutil.which('pandoc')
for name, (zip_name, published, files, app_folder) in PACKAGES.items():
    app = repo / 'shiny' / 'demo' / name
    sheet = (sheets / f'{name}.md').read_text(encoding='utf-8')
    zpath = out / f'{zip_name}.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(f'{zip_name}/STEPS.md', sheet)
        if pandoc:
            html = subprocess.run([pandoc, '--standalone', '--metadata', f'title={sheet.splitlines()[0][2:]}',
                                   '-f', 'markdown', '-t', 'html5'], input=sheet.split('\n', 1)[1],
                                  capture_output=True, text=True, check=True).stdout
            z.writestr(f'{zip_name}/STEPS.html', html)
        readme = (published / 'README.md') if published else (app / 'README.md')
        z.write(readme, f'{zip_name}/README.md')
        for f in files:
            z.write(published / f, f'{zip_name}/published/{f}')
        for f in sorted(app.iterdir()):
            if f.name != 'README.md':
                z.write(f, f'{zip_name}/{app_folder}/{f.name}')
    print(f'{zpath.name}: {zpath.stat().st_size / 1024:.0f} KB')
