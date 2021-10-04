import os
import runpy


def get_scripts():

    # PLACEHOLDER
    # import pymel.core as pm
    # root_folder = pm.optionVar.get("SCRIPT_PANEL_ROOT_PATH")
    root_folder = "D:\Google Drive\Scripting\_Scripts"

    script_paths = []
    for script_name in os.listdir(root_folder):
        full_script_path = os.path.join(root_folder, script_name)
        full_script_path = full_script_path.replace("/", "\\")
        script_paths.append(full_script_path)

    return script_paths


def run_script(script_path):
    runpy.run_path(script_path)
