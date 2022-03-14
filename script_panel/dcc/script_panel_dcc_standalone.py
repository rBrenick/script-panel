import os
import subprocess

from . import script_panel_dcc_base


class StandaloneInterface(script_panel_dcc_base.BaseInterface):
    name = "Standalone"

    @staticmethod
    def open_script(script_path):
        return open_script(script_path)


def open_script(script_path):
    notepad_plus_path = r"C:\Program Files\Notepad++\notepad++.exe"
    if os.path.exists(notepad_plus_path):
        editor_path = notepad_plus_path
    else:
        editor_path = r"C:\Windows\System32\notepad.exe"
    subprocess.Popen([editor_path, script_path])
