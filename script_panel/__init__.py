# content
def main():
    from script_panel import script_panel_ui
    return script_panel_ui.main()

def reload_modules():
    from script_panel import script_panel_utils
    from script_panel import script_panel_ui
    reload(script_panel_utils)
    reload(script_panel_ui)



