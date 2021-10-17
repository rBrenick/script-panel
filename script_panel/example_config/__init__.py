# content
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
    from script_panel import script_panel_skyhook
    from script_panel import script_panel_dcc_maya
    from script_panel import script_panel_dcc_standalone
    from script_panel import script_panel_utils
    from script_panel import script_panel_ui
    reload(folder_model)
    reload(script_panel_skyhook)
    reload(script_panel_dcc_maya)
    reload(script_panel_dcc_standalone)
    reload(script_panel_utils)
    reload(script_panel_ui)
