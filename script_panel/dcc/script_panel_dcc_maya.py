import os

import pymel.core as pm
from maya import mel

from . import script_panel_dcc_base

DCC_EXTENSIONS = {
    ".mel"
}


class MayaInterface(script_panel_dcc_base.BaseInterface):
    name = "Maya"

    @staticmethod
    def get_dcc_extension_map():
        extension_map = {
            ".mel": run_mel_script
        }
        return extension_map

    def open_script(self, script_path):
        return open_script(script_path)


def open_script(script_path):
    """
    This is pretty much a duplicate of scriptEditorPanel.mel - global proc loadFileInNewTab(),
    That function doesn't accept a path argument so we need to rebuild the logic
    """

    script_path = script_path.replace("\\", "/")

    if pm.mel.selectExecuterTabByName(script_path):  # tab exists, switch to it
        reload_selected_tab()
        return

    script_ext = os.path.splitext(script_path)[-1].lower()

    # create tab
    if script_ext == ".py":
        pm.mel.buildNewExecuterTab(-1, "Python", "python", 0)
    elif script_ext == ".mel":
        pm.mel.buildNewExecuterTab(-1, "MEL", "mel", 0)

    tabs = pm.melGlobals["$gCommandExecuterTabs"]
    tabs_layout = pm.tabLayout(tabs, q=True, ca=True)

    # Select newly created tab
    tabs_len = pm.tabLayout(tabs, q=True, numberOfChildren=True)
    pm.tabLayout(tabs, e=True, selectTabIndex=tabs_len)
    tab = tabs_layout[-1]

    # add script contents
    cmd_exec = pm.formLayout(tab, q=True, ca=True)[0]
    pm.cmdScrollFieldExecuter(cmd_exec, e=True, loadFile=script_path)

    # rename tab
    pm.mel.eval('renameCurrentExecuterTab("{}", 0);'.format(script_path))

    # hookup signals
    hookup_tab_signals(cmd_exec)


def reload_selected_tab():
    cmd_exec = get_selected_cmd_executer()
    script_path = pm.cmdScrollFieldExecuter(cmd_exec, q=True, filename=True)
    pm.cmdScrollFieldExecuter(cmd_exec, e=True, loadFile=script_path)


def get_selected_cmd_executer():
    tab_layout = pm.ui.TabLayout(pm.melGlobals["$gCommandExecuterTabs"])
    return pm.formLayout(tab_layout.getSelectTab(), q=True, ca=True)[0]


def hookup_tab_signals(cmd_exec):
    pm.cmdScrollFieldExecuter(cmd_exec, e=True,
                              modificationChangedCommand=lambda x: pm.mel.executerTabModificationChanged(x))
    pm.cmdScrollFieldExecuter(cmd_exec, e=True, fileChangedCommand=lambda x: pm.mel.executerTabFileChanged(x))


def run_mel_script(script_path):
    with open(script_path, "r") as fp:
        mel_script = fp.read()
    return mel.eval(mel_script)
