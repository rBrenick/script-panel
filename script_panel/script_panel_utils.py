import os
import runpy
import sys
from collections import OrderedDict

if sys.version_info.major < 3:
    try:
        from scandir import walk as walk_func
    except ImportError as e:
        walk_func = os.walk
else:
    from os import walk as walk_func


def get_scripts():
    # PLACEHOLDER
    root_folders = os.environ.get("SCRIPT_PANEL_ROOT_FOLDERS", "").split(";")
    if not any(root_folders):
        root_folders = ["D:\Google Drive\Scripting\_Scripts"]

    script_paths = OrderedDict()

    for root_folder in root_folders:
        for folder, __, script_names in walk_func(root_folder):
            for script_name in script_names:
                if not script_name.endswith(".py"):
                    continue
                full_script_path = os.path.join(folder, script_name)
                full_script_path = full_script_path.replace("/", "\\")

                script_paths[full_script_path] = {
                    "root": root_folder,
                }

    return script_paths


def run_script(script_path):
    runpy.run_path(script_path)
