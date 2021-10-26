import os
import sys
import time

from . import ui_utils
from .ui_utils import QtWidgets

active_dcc_is_maya = "maya" in os.path.basename(sys.executable).lower()

if active_dcc_is_maya:
    from script_panel import script_panel_dcc_maya as dcc_module

    dcc_name = "Maya"
else:
    from script_panel import script_panel_dcc_standalone as dcc_module

    dcc_name = "Standalone"


class LocalConstants:
    reference_script = "Reference"
    copy_script = "Copy"


lk = LocalConstants


class HotkeyEditorWindow(ui_utils.ToolWindow):
    def __init__(self, *args, **kwargs):
        super(HotkeyEditorWindow, self).__init__(*args, **kwargs)
        self.setWindowTitle("Hotkey Editor")

        self.ui = HotkeyEditorWidget()
        self.setCentralWidget(self.ui)

        self.referenced_script_path = None
        self.command_type = lk.reference_script

        self.ui.create_hotkey_BTN.clicked.connect(self.create_hotkey)
        self.ui.command_type_CB.currentTextChanged.connect(self.toggle_command_type)

    def set_hotkey_script(self, script_path):
        self.referenced_script_path = script_path
        self.refresh_ui()

    def toggle_command_type(self, command_type):
        self.command_type = command_type
        self.refresh_ui()

    def refresh_ui(self):
        if not self.referenced_script_path:
            print("No script path referenced by hotkey editor")
            return

        script_name = os.path.splitext(os.path.basename(self.referenced_script_path))[0]

        if self.command_type == lk.reference_script:
            command_str = 'import script_panel\nscript_panel.trigger_file(r"{}")'.format(self.referenced_script_path)
        else:
            command_str = "# ScriptPanel Source Script: {}\n".format(self.referenced_script_path)
            command_str += "# ScriptPanel Copy Time: {}\n\n".format(time.time())
            with open(self.referenced_script_path, "r") as fp:
                command_str += fp.read()

        self.ui.shortcut_name_LE.setText(script_name)
        self.ui.hotkey_script_TE.setText(command_str)

    def create_hotkey(self):
        shortcut_name = "SPC_{}".format(self.ui.shortcut_name_LE.text())
        shortcut = self.ui.shortcut_hotkey_LE.text()
        command_str = self.ui.hotkey_script_TE.toPlainText()

        dcc_module.setup_dcc_hotkey(shortcut_name, shortcut, command_str, category="ScriptPanelCommands")
        sys.stdout.write("Hotkey created as a {}: {}\n".format(self.command_type, shortcut_name))


class HotkeyEditorWidget(QtWidgets.QWidget):
    def __init__(self):
        super(HotkeyEditorWidget, self).__init__()

        self.main_layout = QtWidgets.QVBoxLayout()

        # shortcut name
        self.shortcut_name_LE = QtWidgets.QLineEdit()
        self.shortcut_name_LE.setPlaceholderText("Shortcut name")
        self.shortcut_name_LE.setMinimumHeight(40)

        self.command_type_CB = QtWidgets.QComboBox()
        self.command_type_CB.addItems([lk.reference_script, lk.copy_script])
        self.command_type_CB.setMinimumHeight(40)

        # shortcut hotkey
        self.shortcut_hotkey_LE = QtWidgets.QLineEdit()
        self.shortcut_hotkey_LE.setPlaceholderText(
            "Hotkey (ex: Ctrl+Alt+X) - if this is blank, the command can also be connected via the maya hotkey editor"
        )
        self.shortcut_hotkey_LE.setMinimumHeight(40)

        # script command text
        self.hotkey_script_TE = QtWidgets.QTextEdit()

        # create hotkey button
        self.create_hotkey_BTN = QtWidgets.QPushButton("Create Hotkey")
        self.create_hotkey_BTN.setMinimumHeight(50)

        self.main_layout.addWidget(self.shortcut_name_LE)
        self.main_layout.addWidget(self.command_type_CB)
        self.main_layout.addWidget(self.hotkey_script_TE)
        self.main_layout.addWidget(self.shortcut_hotkey_LE)
        self.main_layout.addWidget(self.create_hotkey_BTN)
        self.setLayout(self.main_layout)


def main(reload=False, script_path=None):
    win = HotkeyEditorWindow()
    win.main(reload=reload)

    if script_path:
        win.set_hotkey_script(script_path)

    return win
