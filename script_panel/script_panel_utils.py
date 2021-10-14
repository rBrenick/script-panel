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


class LocalConstants:
    run_script_on_click = "Run Script on Double Click"
    edit_script_on_click = "Edit Script on Double Click"


lk = LocalConstants


def undefined_extension_func(file_path):
    file_ext = os.path.splitext(file_path)[-1]
    print("Action needed for extension: {}".format(file_ext))


def run_python_script(script_path):
    runpy.run_path(script_path, init_globals=globals())


EXTENSION_MAP = {
    ".py": run_python_script
}


def add_extension_func_to_map(extension, func):
    EXTENSION_MAP[extension] = func


def get_file_triggered_func(file_path):
    """
    Get defined function for this extension
    """

    file_ext = os.path.splitext(file_path)[-1]
    file_type_func = EXTENSION_MAP.get(file_ext, undefined_extension_func)
    return file_type_func


def file_triggered(file_path):
    trigger_func = get_file_triggered_func(file_path)
    trigger_func(file_path)


def get_scripts():
    # PLACEHOLDER
    root_folders = os.environ.get("SCRIPT_PANEL_ROOT_FOLDERS", "").split(";")
    if not any(root_folders):
        root_folders = [r"D:\Google Drive\Scripting\_Scripts"]

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
