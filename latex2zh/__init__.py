import os

def _read_file(filename):
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, filename), encoding="utf-8") as f:
        return f.read().strip()


import appdata
app_paths = appdata.AppDataPaths('translatex')
app_dir = app_paths.app_data_path
os.makedirs(app_dir, exist_ok=True)


from . import encode_process
from . import config
from . import tencentcloud
from . import cache
from . import file_process
from . import text_process
from . import latex_process
from . import translatex
from . import utils
from . import tencnet
