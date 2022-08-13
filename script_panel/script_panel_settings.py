__author__ = "Richard Brenick"

# Standard
import json
import os
import shutil
import time
import traceback

from script_panel import dcc
from script_panel.ui import ui_utils
from script_panel.ui.ui_utils import QtCore

dcc_interface = dcc.DCCInterface()
dcc_name = dcc_interface.name.lower()


class SettingsConstants:
    default_layout_name = "-user-"
    backup_folder_name = "_BACKUPS"
    active_layout = "active_layout"
    settings_version = "settings_version"

    run_script_on_click = "Run Script on Double Click"
    edit_script_on_click = "Edit Script on Double Click"

    # layout keys
    layouts = "layouts"
    meta_data = "__meta_data__"
    scripts_display = "script_display" # deprecated
    palette_layout = "palette_layout"
    palette_display = "palette_display"

    # snippet keys
    snippets = "snippets"

    max_backup_count = 30
    user_config_json_path = os.path.join(
        os.environ.get("APPDATA"),
        "script_panel",
        "user_config_{}.json".format(dcc_name)
    )


sk = SettingsConstants


class ScriptPanelSettings(ui_utils.BaseSettings):
    __settings_version__ = "1.00.00"
    k_version = "settings_version"
    k_layouts = "layouts"
    k_active_layout = "active_layout"
    k_double_click_action = "double_click_action"
    k_skyhook_enabled = "skyhook_enabled"
    k_main_splitter_sizes = "main_splitter_sizes"

    def __init__(self, *args, **kwargs):
        super(ScriptPanelSettings, self).__init__(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            "script_panel", "script_panel_{}".format(dcc_name),
            *args, **kwargs)

        self.active_layout = self.get_value(sk.active_layout, default=sk.default_layout_name)

        self.user_layouts_folder = os.path.join(os.path.dirname(self.fileName()), "{}_layouts".format(dcc_name))
        self.layout_backups_folder = os.path.join(self.user_layouts_folder, sk.backup_folder_name)
        if not os.path.exists(self.user_layouts_folder):
            os.makedirs(self.user_layouts_folder)
        if not os.path.exists(self.layout_backups_folder):
            os.makedirs(self.layout_backups_folder)

        loaded_settings_version = self.get_value(self.k_version, "0")

        # upgrade settings
        if loaded_settings_version == "0":
            self.update_settings_from_0_to_1()

        # stamp version info
        self.setValue(self.k_version, self.__settings_version__)

    def set_active_layout(self, layout_name):
        self.setValue(sk.active_layout, layout_name)
        self.active_layout = layout_name

    def get_layout(self, key):
        layout_path = os.path.join(self.user_layouts_folder, "{}.json".format(key))
        return self.get_layout_from_path(layout_path) if os.path.exists(layout_path) else {}

    @staticmethod
    def get_layout_from_path(path):
        with open(path, "r") as fp:
            layout_data = json.load(fp)
        return layout_data

    def update_layout(self, key, new_info=None):
        try:
            self.make_layout_backup(key)
        except Exception as e:
            traceback.print_exc()

        new_info = new_info or dict()
        layout_path = os.path.join(self.user_layouts_folder, "{}.json".format(key))
        with open(layout_path, "w+") as fp:
            json.dump(new_info, fp, indent=2)

    def make_layout_backup(self, key):
        layout_path = os.path.join(self.user_layouts_folder, "{}.json".format(key))
        if not os.path.exists(layout_path):
            return

        target_backup_folder = os.path.join(self.layout_backups_folder, key)
        if not os.path.exists(target_backup_folder):
            os.makedirs(target_backup_folder)

        existing_backups = os.listdir(target_backup_folder)
        if len(existing_backups) > sk.max_backup_count:
            old_backup_path = os.path.join(target_backup_folder, existing_backups[0])
            if os.path.exists(old_backup_path):
                os.remove(old_backup_path)

        backup_path = os.path.join(target_backup_folder, "LAYOUT_BACKUP_{}_{}".format(key, int(time.time())))
        shutil.copy(layout_path, backup_path)

    def get_layout_names(self):
        names = []
        for file_name in os.listdir(self.user_layouts_folder):
            if file_name == sk.backup_folder_name:
                continue
            names.append(os.path.splitext(file_name)[0])

        # make sure the default layout is there
        if sk.default_layout_name not in names:
            names.insert(0, sk.default_layout_name)

        return names

    def remove_script_from_active_layout(self, script_path):
        layout_info = self.get_layout(self.active_layout)

        scripts_display = layout_info.get(sk.scripts_display, dict())
        if script_path in list(scripts_display.keys()):
            scripts_display.pop(script_path)

        layout_info[sk.scripts_display] = scripts_display
        self.update_layout(self.active_layout, layout_info)

    ###########################################################################
    # Upgrade functions below
    def update_settings_from_0_to_1(self):
        """
        Convert from single favorite layout, to multiple with chooser
        """
        layout_info = dict()
        layout_info["script_paths"] = self.get_value("favorites", default=dict())
        layout_info[sk.scripts_display] = self.get_value("favorites_display", default=dict())
        layout_info[sk.palette_layout] = self.get_value("favorites_layout", default=dict())
        layout_info[sk.palette_display] = self.get_value("palette_display", default=dict())
        self.update_layout(sk.default_layout_name, layout_info)
        self.remove("favorites")
        self.remove("favorites_display")
        self.remove("favorites_layout")
        self.remove("palette_display")
