# content
import os.path


def main(*args, **kwargs):
    from script_panel import script_panel_ui
    if kwargs.get("reload"):
        reload_modules()
    return script_panel_ui.main(*args, **kwargs)


def reload_modules():
    import sys
    if sys.version_info.major >= 3:
        from importlib import reload
    else:
        from imp import reload

    from script_panel.ui import folder_model
    from script_panel.ui import hotkey_editor
    from script_panel import script_panel_dcc_standalone
    from script_panel import script_panel_utils
    from script_panel import script_panel_ui

    try:
        from script_panel import script_panel_skyhook
        reload(script_panel_skyhook)
    except Exception as e:
        pass

    # maya specific modules
    try:
        from script_panel import script_panel_dcc_maya
        reload(script_panel_dcc_maya)
    except Exception as e:
        print(e)

    reload(folder_model)
    reload(hotkey_editor)
    reload(script_panel_dcc_standalone)
    reload(script_panel_utils)
    reload(script_panel_ui)


def trigger_file(file_path):
    """
    Small utility function to trigger via hotkeys and such things.
    """
    if not os.path.exists(file_path):
        from . import script_panel_ui
        script_panel_ui.show_warning_path_does_not_exist(file_path)
        return

    from . import script_panel_utils
    script_panel_utils.file_triggered(file_path)
