"""Run a Galaxy driver script with normalise_faire.normalise as written, or replaced by a plain copy.

Usage: python3 -I run_driver.py {normalise|copy} DRIVER.py [driver arguments...]

For a workbook already in the FAIRe-NOAA layout, normalising is meant to change nothing, so the
driver's outputs in the two modes should be identical. Any difference is caused by normalise_faire.py.
"""
import runpy
import shutil
import sys
from pathlib import Path

mode, driver = sys.argv[1], Path(sys.argv[2]).resolve()
sys.path.insert(0, str(driver.parent))
import normalise_faire  # noqa: E402

if mode == 'copy':
    normalise_faire.normalise = lambda src, dst, *args, **kwargs: shutil.copy(src, dst)
elif mode != 'normalise':
    sys.exit(f'unknown mode {mode}')
sys.argv = [str(driver)] + sys.argv[3:]
runpy.run_path(str(driver), run_name='__main__')
