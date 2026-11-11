"""Run FAIRe-fier's own Shiny server code headlessly, as a reference for check.sh.

A stand-in 'shiny' module replaces the decorators and widgets with simple
recorders, so validate_module.validate_server() can run outside a browser.
The script then calls the same functions the Submit and Download buttons call
and writes the two downloads to an output folder.

Usage: python run_shiny_reference.py FAIRE_FIER_DIR WORKBOOK CHECKLIST_VERSION OUTDIR
(run with the current directory holding the FAIRe_checklist_*.xlsx files)
"""
import os
import sys
import types

fairefier_dir, workbook, version, outdir = sys.argv[1:5]

registry = {}


def recorder(*args, **kwargs):
    # Used bare (@reactive.calc) or with arguments (@reactive.event(x)).
    if len(args) == 1 and isinstance(args[0], types.FunctionType) and not kwargs:
        fn = args[0]
        registry[fn.__name__] = fn
        return fn

    def deco(fn):
        registry[fn.__name__] = fn
        return fn
    return deco


class Value:
    def __init__(self, v=None):
        self.v = v

    def get(self):
        return self.v

    def set(self, v):
        self.v = v

    def __call__(self):
        return self.v


shiny = types.ModuleType('shiny')
reactive = types.SimpleNamespace(calc=recorder, effect=recorder, event=recorder, value=Value)
render = types.SimpleNamespace(ui=recorder, data_frame=recorder, text=recorder, download=recorder)
ui = types.SimpleNamespace(notification_show=lambda *a, **k: print('NOTIFY:', a[0]),
                           download_button=lambda *a, **k: None, input_file=lambda *a, **k: None)
shiny.reactive, shiny.render, shiny.ui = reactive, render, ui
shiny.Inputs = shiny.Outputs = shiny.Session = object
sys.modules['shiny'] = shiny

sys.path.insert(0, fairefier_dir)
import validate_module  # noqa: E402


class Inp:
    def file_upload(self):
        return [{'datapath': workbook}]

    dropdown_checklistv = Value(version)
    button_submit = Value(0)
    button_clear = Value(0)


validate_module.validate_server(Inp(), None, None)
result = registry['read_worksheets']()
if result[0] is None:
    print('READ ERROR:', result[1])
    sys.exit(2)
registry['on_button_submit']()
msg = registry['textbox_display']()
print(msg)
os.makedirs(outdir, exist_ok=True)
with open(os.path.join(outdir, 'message.txt'), 'w') as f:
    f.write(msg)
out_pm = registry['dataframe_out_projectmetadata']()
out_sm = registry['dataframe_out_samplemetadata']()
if not out_pm.empty or not out_sm.empty:
    with open(os.path.join(outdir, 'fairefier_metadata.xlsx'), 'wb') as f:
        f.write(registry['ddl_out']().getvalue())
frames = [registry[n]() for n in ('dataframe_warn_projectmetadata', 'dataframe_error_projectmetadata',
                                  'dataframe_warn_samplemetadata', 'dataframe_error_samplemetadata')]
if any(not d.empty for d in frames):
    with open(os.path.join(outdir, 'fairefier_warn_error.xlsx'), 'wb') as f:
        f.write(registry['ddl_warn_error']().getvalue())
print('files:', sorted(os.listdir(outdir)))
