import os
import sys

active_dcc_is_maya = "maya" in os.path.basename(sys.executable).lower()

if active_dcc_is_maya:
    from . import script_panel_dcc_maya as dcc_module

    DCCInterface = dcc_module.MayaInterface
else:
    from . import script_panel_dcc_standalone as dcc_module

    DCCInterface = dcc_module.StandaloneInterface
