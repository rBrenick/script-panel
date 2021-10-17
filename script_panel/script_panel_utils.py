import json
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

    dcc_maya = "Maya"
    dcc_blender = "Maya"
    dcc_standalone = "Standalone"

    env_key = "SCRIPT_PANEL_ROOT_FOLDERS"
    path_root_dir = "root_dir"
    root_type = "root_type"
    paths = "paths"
    default_indent = "default_indent"
    folder_display_prefix = "folder_prefix"


class PathInfoKeys:
    # keys for dicts being returned by get_scripts
    root_dir = "root"
    root_type = "root_type"
    folder_prefix = "folder_prefix"


lk = LocalConstants


def undefined_extension_func(file_path):
    file_ext = os.path.splitext(file_path)[-1]
    print("Action needed for extension: {}".format(file_ext))


def run_python_script(script_path):
    runpy.run_path(script_path, init_globals=globals(), run_name="__main__")


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


class EnvironmentData(object):
    """
    Handler class for environment properties
    """

    def __init__(self, env_data):
        self.path_data = env_data.get(lk.paths, [])
        self.default_expand_depth = env_data.get(lk.default_indent, 0)


def get_data_from_string(env_str):
    # if json data is in the env string, load info from that
    if env_str.startswith('{'):
        env_data = json.loads(env_str)
    else:
        # only folders specified in environment variable. extract the rest of the data from that
        root_folders = env_str.split(";")
        env_data = {}
        paths = []
        for root_folder in root_folders:
            paths.append({root_folder})
        env_data[lk.paths] = paths

    return env_data


def get_env_data():
    """
    find info about root paths from the environment variable

    :return:
    """
    env_str = os.environ.get(lk.env_key, "")

    # if nothing is defined, use example config
    if not env_str:
        env_str = os.path.join(os.path.dirname(__file__), "example_config", "example_script_panel_config.json")

    # if env_str is a path to a json config, read the contents from that file
    if env_str.endswith(".json") and os.path.exists(env_str):
        config_path = env_str
        with open(config_path, "r") as fp:
            env_data = json.load(fp)

        # replace "local file token" with full file path of config
        modified_data = json.dumps(env_data).replace("__THIS_FILE__", config_path.replace("\\", "\\\\"))
        env_data = json.loads(modified_data)

    # or parse data directly from environment variable
    else:
        env_data = get_data_from_string(env_str)

    return EnvironmentData(env_data)


def get_scripts(env_data=None):
    if not env_data:
        env_data = get_env_data()  # type: EnvironmentData

    script_paths = OrderedDict()
    for path_data in env_data.path_data:
        root_folder = path_data.get(lk.path_root_dir)
        root_type = path_data.get(lk.root_type)
        display_prefix = path_data.get(lk.folder_display_prefix)

        for folder, __, script_names in walk_func(root_folder):
            for script_name in script_names:
                if not script_name.endswith(".py"):
                    continue
                full_script_path = os.path.join(folder, script_name)
                full_script_path = full_script_path.replace("/", "\\")

                script_paths[full_script_path] = {
                    PathInfoKeys.root_dir: root_folder,
                    PathInfoKeys.root_type: root_type,
                    PathInfoKeys.folder_prefix: display_prefix,
                }

    return script_paths
