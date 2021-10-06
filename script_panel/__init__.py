# content
def main():
    from script_panel import script_panel_ui
    return script_panel_ui.main()


def reload_modules():
    import sys
    if sys.version_info.major >= 3:
        from importlib import reload
    else:
        from imp import reload

    from script_panel import script_panel_utils
    from script_panel import script_panel_ui
    reload(script_panel_utils)
    reload(script_panel_ui)
