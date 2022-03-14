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
    from script_panel.ui import command_palette
    from script_panel.dcc import script_panel_dcc_base
    from script_panel import dcc as script_panel_dcc
    from script_panel.ui import hotkey_editor
    from script_panel.ui import config_editor
    from script_panel.ui import snippet_popup
    from script_panel import script_panel_settings
    from script_panel import script_panel_utils
    from script_panel import script_panel_ui

    try:
        from script_panel.dcc import script_panel_skyhook
        reload(script_panel_skyhook)
    except Exception as e:
        pass

    reload(folder_model)
    reload(command_palette)
    reload(hotkey_editor)
    reload(config_editor)
    reload(script_panel_dcc_base)
    reload(script_panel_dcc.dcc_module)
    reload(script_panel_dcc)
    reload(script_panel_settings)
    reload(script_panel_utils)
    reload(script_panel_ui)


def startup():
    pass


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
