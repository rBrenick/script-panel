import os
import subprocess


def open_script(script_path):
    notepad_plus_path = r"C:\Program Files\Notepad++\notepad++.exe"
    if os.path.exists(notepad_plus_path):
        editor_path = notepad_plus_path
    else:
        editor_path = r"C:\Windows\System32\notepad.exe"
    subprocess.call([editor_path, script_path])
