import os

import pymel.core as pm
from maya import cmds


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


def setup_dcc_hotkey(shortcut_name, shortcut, command_str, category="Custom"):
    """
    Create a hotkey command
    if a shortcut is provided, connect the command to that shortcut
    """
    hotkey_set_name = "UserHotkeys"

    # make sure we have a user editable hotkey set active
    if not cmds.about(batch=True):
        if cmds.hotkeySet(current=True, q=True) == "Maya_Default":
            if not cmds.hotkeySet(hotkey_set_name, exists=True):
                cmds.hotkeySet(hotkey_set_name, source="Maya_Default")
            cmds.hotkeySet(hotkey_set_name, edit=True, current=True)

    name_command = '{0}Command'.format(shortcut_name)

    if cmds.runTimeCommand(shortcut_name, exists=True):
        cmds.runTimeCommand(shortcut_name, edit=True, delete=True)

    cmds.runTimeCommand(
        shortcut_name,
        command=command_str,
        annotation="Generated Hotkey - Launch {}".format(shortcut_name),
        category=category,
    )

    cmds.nameCommand(
        name_command,
        command=shortcut_name,
        annotation="Generated Hotkey - Launch {}".format(shortcut_name),
    )

    if shortcut:
        shortcut_key = shortcut.split("+")[-1].lower()
        cmds.hotkey(
            name=name_command,
            keyShortcut=shortcut_key,
            ctl="ctrl" in shortcut.lower(),
            alt="alt" in shortcut.lower(),
            sht="shift" in shortcut.lower(),
        )
