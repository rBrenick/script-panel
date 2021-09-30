import os
import runpy


def get_scripts():

    # PLACEHOLDER
    import pymel.core as pm
    root_folder = pm.optionVar.get("SCRIPT_PANEL_ROOT_PATH")

    script_paths = []
    for script_name in os.listdir(root_folder):
        script_paths.append(root_folder + "/" + script_name)

    return script_paths


def run_script(script_path):
    runpy.run_path(script_path)
