import collections
import json
import os

import script_panel.script_panel_settings as sps
import script_panel.script_panel_utils as spu
from . import ui_utils
from .ui_utils import QtWidgets, QtCore


class LocalConstants:
    reference_script = "Reference"
    copy_script = "Copy"

    extension_comment_character = {
        ".py": "#",
        ".mel": "//",
    }


BACKGROUND_COLOR_FORM = "background-color:rgb({0}, {1}, {2})"
BACKGROUND_COLOR_GREEN = BACKGROUND_COLOR_FORM.format(46, 113, 46)
BACKGROUND_COLOR_RED = BACKGROUND_COLOR_FORM.format(161, 80, 55)

lk = LocalConstants


class ConfigEditorWindow(ui_utils.ToolWindow):
    def __init__(self, parent=None, *args, **kwargs):
        super(ConfigEditorWindow, self).__init__(parent, *args, **kwargs)
        self.parent_window = parent
        self.setWindowTitle("Config Editor")

        self.ui = ConfigEditorWidget()
        self.setCentralWidget(self.ui)

        # load settings
        self.settings = sps.ScriptPanelSettings()

        self.env_config_data = spu.ConfigurationData(environment=True, user=False)
        self.user_config_data = spu.ConfigurationData(environment=False, user=True)
        for path_data in self.env_config_data.path_data:
            self.add_path_config(
                path_data,
                tree_widget=self.ui.env_paths_TW,
            )

        for path_data in self.user_config_data.path_data:
            self.add_path_config(
                path_data,
                tree_widget=self.ui.user_paths_TW,
                editable=True,
            )
        self.ui.env_paths_TW.expandToDepth(1)
        self.ui.user_paths_TW.expandToDepth(1)

        # connect
        self.ui.add_path_btn.clicked.connect(self.add_new_path)
        self.ui.remove_path_btn.clicked.connect(self.remove_selected_paths)
        self.ui.save_paths_btn.clicked.connect(self.save_user_config)

        self.ui.display_save_required(False)

    def save_user_config(self):
        user_config_data = collections.OrderedDict()
        user_config_data[spu.lk.paths] = self.get_user_config_paths_from_ui()
        with open(sps.sk.user_config_json_path, "w") as fp:
            json.dump(user_config_data, fp, indent=2)

        try:
            self.parent_window.config_refresh()
        except Exception as e:
            print(e)

        self.ui.display_save_required(False)

    def get_user_config_paths_from_ui(self):
        user_path_data = []
        for i in range(self.ui.user_paths_TW.topLevelItemCount()):
            item = self.ui.user_paths_TW.topLevelItem(i)  # type: QtWidgets.QTreeWidgetItem
            path_data = dict()
            for child_item in [item.child(_) for _ in range(item.childCount())]:
                value_type = child_item.text(2)
                if value_type == "bool":
                    item_val = child_item.text(1).lower() == "true"
                else:
                    item_val = child_item.text(1)
                path_data[child_item.text(0)] = item_val
            user_path_data.append(path_data)

        return user_path_data

    def add_new_path(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory()
        if not folder:
            return
        path_data = dict()
        path_data[spu.lk.path_root_dir] = folder
        path_data[spu.lk.root_type] = spu.FolderTypes.local
        path_data[spu.lk.folder_display_prefix] = os.path.basename(folder).title()
        self.add_path_config(
            path_data,
            tree_widget=self.ui.user_paths_TW,
            editable=True,
        )
        self.ui.display_save_required()

    def add_path_config(self, path_data, tree_widget, editable=False):
        root_twi = QtWidgets.QTreeWidgetItem()

        root_folder_name = path_data.get(spu.lk.folder_display_prefix)
        root_twi.setText(0, root_folder_name)
        for key, val in path_data.items():
            twi = QtWidgets.QTreeWidgetItem()
            if editable:
                twi.setFlags(twi.flags() | QtWidgets.QTreeWidget.AllEditTriggers)

            twi.setText(0, key)
            twi.setText(1, str(val))
            twi.setText(2, str(type(val)))
            root_twi.addChild(twi)
        tree_widget.addTopLevelItem(root_twi)
        root_twi.setExpanded(True)
        tree_widget.resizeColumnToContents(0)

    def remove_selected_paths(self):
        something_changed = False
        for item in self.ui.user_paths_TW.selectedItems():
            try:
                if item.parent():
                    continue
                item_index = self.ui.user_paths_TW.indexFromItem(item)  # type: QtCore.QModelIndex
                self.ui.user_paths_TW.takeTopLevelItem(item_index.row())
                something_changed = True
            except Exception as except_info:
                print(except_info)

        if something_changed:
            self.ui.display_save_required()


class ConfigEditorWidget(QtWidgets.QWidget):
    def __init__(self):
        super(ConfigEditorWidget, self).__init__()

        self.main_layout = QtWidgets.QVBoxLayout()

        self.user_paths_label = QtWidgets.QLabel("User Defined Paths")
        self.pre_paths_label = QtWidgets.QLabel("Environment Paths")
        self.add_path_btn = QtWidgets.QPushButton("Add Path")
        self.remove_path_btn = QtWidgets.QPushButton("Remove Path")
        self.remove_path_btn.setShortcut("DEL")
        self.save_paths_btn = QtWidgets.QPushButton("Save")
        self.save_paths_btn.setShortcut("Ctrl+S")
        self.env_paths_TW = QtWidgets.QTreeWidget()
        self.env_paths_TW.setHeaderLabels(["Key", "Val"])
        self.env_paths_TW.setHeaderHidden(True)
        self.user_paths_TW = QtWidgets.QTreeWidget()
        self.user_paths_TW.setHeaderLabels(["Key", "Val"])
        self.user_paths_TW.setHeaderHidden(True)

        self.config_layout = QtWidgets.QVBoxLayout()
        self.config_buttons_layout = QtWidgets.QHBoxLayout()
        self.config_buttons_layout.addWidget(self.add_path_btn)
        self.config_buttons_layout.addWidget(self.remove_path_btn)
        self.config_buttons_layout.addWidget(self.save_paths_btn)
        self.config_layout.addWidget(self.user_paths_label)
        self.config_layout.addLayout(self.config_buttons_layout)
        self.config_layout.addWidget(self.user_paths_TW)
        self.config_layout.addWidget(self.pre_paths_label)
        self.config_layout.addWidget(self.env_paths_TW)
        self.main_layout.addLayout(self.config_layout)
        self.setLayout(self.main_layout)

    def display_save_required(self, needs_save=True):
        if needs_save:
            self.save_paths_btn.setStyleSheet(BACKGROUND_COLOR_RED)
        else:
            self.save_paths_btn.setStyleSheet(BACKGROUND_COLOR_GREEN)


class PathListWidgetItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, *args, **kwargs):
        super(PathListWidgetItem, self).__init__(*args, **kwargs)


def main(parent_window=None, reload=False):
    win = ConfigEditorWindow(parent=parent_window)
    win.main(reload=reload)
    return win
