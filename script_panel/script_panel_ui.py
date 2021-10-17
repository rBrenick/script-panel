__author__ = "Richard Brenick"

# Standard
import os.path
import subprocess
import sys

from script_panel import script_panel_utils as spu
from script_panel.ui import folder_model
from script_panel.ui import ui_utils
from script_panel.ui.ui_utils import QtCore, QtWidgets, QtGui

try:
    from script_panel import script_panel_skyhook as sp_skyhook
except ImportError as e:
    print("Optional skyhook import failed: {}".format(e))
    sp_skyhook = None

active_dcc_is_maya = "maya" in os.path.basename(sys.executable).lower()

if active_dcc_is_maya:
    from . import script_panel_dcc_maya as dcc_module

    dcc_name = "Maya"
else:
    from . import script_panel_dcc_standalone as dcc_module

    dcc_name = "Standalone"


class ScriptPanelSettings(QtCore.QSettings):
    k_favorites = "favorites"
    k_double_click_action = "double_click_action"
    k_skyhook_enabled = "skyhook_enabled"

    def __init__(self, *args, **kwargs):
        super(ScriptPanelSettings, self).__init__(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            "script_panel", "script_panel_{}".format(dcc_name.lower()),
            *args, **kwargs)

    def get_value(self, key, default=None):
        data_type = None
        if default is not None:
            data_type = type(default)

        settings_val = self.value(key, defaultValue=default)

        if data_type == list and not isinstance(settings_val, list):
            settings_val = [settings_val] if settings_val else list()

        if data_type == dict and not isinstance(settings_val, dict):
            settings_val = dict(settings_val)

        if data_type == int and not isinstance(settings_val, int):
            settings_val = default if settings_val is None else int(settings_val)

        if data_type == float and not isinstance(settings_val, float):
            settings_val = default if settings_val is None else float(settings_val)

        if data_type == bool:
            settings_val = True if settings_val in ("true", "True", "1", 1, True) else False

        return settings_val

    def add_to_favorites(self, script_path):
        favorites = self.get_value(self.k_favorites, default=list())
        if script_path not in favorites:
            favorites.append(script_path)
        self.setValue(self.k_favorites, favorites)

    def remove_from_favorites(self, script_path):
        favorites = self.get_value(self.k_favorites, default=list())
        if script_path in favorites:
            favorites.remove(script_path)
        self.setValue(self.k_favorites, favorites)


class ScriptPanelWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(ScriptPanelWidget, self).__init__(*args, **kwargs)

        self.ui = ScriptPanelUI()
        self.settings = ScriptPanelSettings()

        self.env_data = spu.get_env_data()  # type: spu.EnvironmentData
        self.default_expand_depth = self.env_data.default_expand_depth

        # build model
        self.model = QtGui.QStandardItemModel()
        self.proxy = folder_model.ScriptPanelSortProxyModel(self.model)
        self.ui.scripts_TV.setModel(self.proxy)
        self.ui.scripts_TV.setSortingEnabled(True)
        self._model_folders = {}

        # connect signals
        self.ui.search_LE.textChanged.connect(self.filter_scripts)
        self.ui.refresh_BTN.clicked.connect(self.refresh_scripts)
        self.ui.script_double_clicked.connect(self.script_double_clicked)
        self.ui.favorites_LW.script_dropped.connect(self.add_script_to_favorites)
        self.ui.favorites_LW.order_updated.connect(self.save_favorites_layout)
        self.ui.favorites_LW.remove_favorites.connect(self.remove_scripts_from_favorites)

        # right click menu
        script_panel_context_actions = [
            {"Run": self.activate_script},
            {"Edit": self.open_script_in_editor},
            "-",
            {"RADIO_SETTING": {"settings": self.settings,
                               "settings_key": self.settings.k_double_click_action,
                               "choices": [spu.lk.run_script_on_click, spu.lk.edit_script_on_click],
                               "default": spu.lk.run_script_on_click,
                               }},
            "-",
            {"Show In Explorer": self.open_script_in_explorer},
        ]

        self.ui.scripts_TV.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.scripts_TV.customContextMenuRequested.connect(
            lambda: ui_utils.build_menu_from_action_list(script_panel_context_actions)
        )

        # build ui
        self.refresh_favorites()
        self.refresh_scripts()
        self.load_settings()

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.ui)
        self.setLayout(main_layout)

    def load_settings(self):
        if sp_skyhook:
            skyhook_enabled = self.settings.get_value(self.settings.k_skyhook_enabled, default=False)
            self.ui.skyhook_blender_CHK.setChecked(skyhook_enabled)

    def refresh_scripts(self):
        self.model.clear()
        self.model.setHorizontalHeaderLabels(["Name"])
        self._model_folders = {}

        # then add normal scripts
        for script_path, path_info in spu.get_scripts(env_data=self.env_data).items():
            self.add_script_to_model(script_path, path_info)

        self.ui.scripts_TV.expandToDepth(self.default_expand_depth)
        self.ui.scripts_TV.sortByColumn(0, QtCore.Qt.AscendingOrder)
        header = self.ui.scripts_TV.header()
        header.setSectionResizeMode(0, header.ResizeToContents)

    def add_script_to_model(self, script_path, path_info):
        path_root_dir = path_info.get(spu.lk.path_root_dir)
        display_prefix = path_info.get(spu.lk.folder_display_prefix)

        # display path in tree view
        display_dir_rel_path = os.path.relpath(os.path.dirname(script_path), path_root_dir)
        if display_prefix:
            display_dir_rel_path = "{}\\{}".format(display_prefix, display_dir_rel_path)

        parent_item = self.model

        # build needed folders
        folder_rel_split = display_dir_rel_path.split("\\")
        for i, token in enumerate(folder_rel_split):
            if token in [".", ""]:
                continue

            # combine together the token into a relative_path
            token_rel_path = "\\".join(folder_rel_split[:i + 1])

            # an Item for this folder has already been created
            existing_folder_item = self._model_folders.get(token_rel_path)
            if existing_folder_item is not None:
                parent_item = existing_folder_item
            else:
                new_folder_item = QtGui.QStandardItem(str(token))
                new_folder_item.setIcon(self.ui.icons.folder_icon)

                # mark as folder for sorting model
                folder_path_data = folder_model.PathData(token_rel_path, is_folder=True)
                new_folder_item.setData(folder_path_data, QtCore.Qt.UserRole)

                parent_item.appendRow(new_folder_item)
                parent_item = new_folder_item
                self._model_folders[token_rel_path] = new_folder_item

        item = ScriptModelItem(script_path)
        path_data = folder_model.PathData(script_path, is_folder=False)
        item.setData(path_data, QtCore.Qt.UserRole)

        if script_path.lower().endswith(".py"):
            item.setIcon(self.ui.icons.python_icon)
        else:
            item.setIcon(self.ui.icons.unknown_type_icon)

        parent_item.appendRow(item)

    def refresh_favorites(self):
        favorite_scripts = self.settings.get_value(ScriptPanelSettings.k_favorites, default=list())

        self.ui.favorites_LW.clear()

        # first add favorite scripts
        for script_path in favorite_scripts:
            self.add_favorite_widget(script_path)

    def add_script_to_favorites(self, script_path):
        self.settings.add_to_favorites(script_path)
        self.refresh_favorites()

    def remove_scripts_from_favorites(self, script_paths):
        for script_path in script_paths:
            self.settings.remove_from_favorites(script_path)
        self.refresh_favorites()

    def add_favorite_widget(self, script_path):
        script_widget = ScriptWidget(script_path)
        script_widget.script_clicked.connect(self.activate_script)

        lwi = QtWidgets.QListWidgetItem()
        lwi.setSizeHint(script_widget.sizeHint())
        self.ui.favorites_LW.addItem(lwi)
        self.ui.favorites_LW.setItemWidget(lwi, script_widget)

    def save_favorites_layout(self):
        # get order of widgets in list
        items = [self.ui.favorites_LW.item(i) for i in range(self.ui.favorites_LW.count())]
        favorites = []
        for lwi in items:
            item = self.ui.favorites_LW.itemWidget(lwi)  # type: ScriptWidget
            favorites.append(item.script_path)

        self.settings.setValue(self.settings.k_favorites, favorites)

    def filter_scripts(self, text):
        search = QtCore.QRegExp(text, QtCore.Qt.CaseInsensitive, QtCore.QRegExp.RegExp)
        self.proxy.setFilterRegExp(search)
        if not text:
            self.ui.scripts_TV.expandToDepth(self.default_expand_depth)
        else:
            self.ui.scripts_TV.expandAll()

    def script_double_clicked(self, script_path):
        user_setting = self.settings.get_value(self.settings.k_double_click_action, spu.lk.run_script_on_click)

        if user_setting == spu.lk.run_script_on_click:
            self.activate_script(script_path)
        else:
            self.open_script_in_editor(script_path)

    def activate_script(self, script_path=None):
        if not script_path:
            script_path = self.ui.scripts_TV.get_selected_script_paths()[0]

        if sp_skyhook:
            if self.ui.skyhook_blender_CHK.isChecked():
                sp_skyhook.run_script_in_blender(script_path)
                return

        spu.file_triggered(script_path)

    def open_script_in_editor(self, script_path=None):
        if "open_script" not in dir(dcc_module):
            print("Editor open not defined for this DCC")
            return
        if not script_path:
            script_path = self.ui.scripts_TV.get_selected_script_paths()[0]
        dcc_module.open_script(script_path)

    def open_script_in_explorer(self, script_path=None):
        if not script_path:
            script_path = self.ui.scripts_TV.get_selected_script_paths()[0]
        subprocess.Popen(r'explorer /select, "{}"'.format(script_path))


class ScriptWidget(QtWidgets.QWidget):
    script_clicked = QtCore.Signal(str)

    def __init__(self, script_path="ExampleScript.py", *args, **kwargs):
        super(ScriptWidget, self).__init__(*args, **kwargs)

        self.script_path = script_path

        btn = QtWidgets.QPushButton(parent=self)
        btn.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        btn.setText(os.path.basename(script_path))
        btn.clicked.connect(self.activate_script)

        if self.script_path.lower().endswith(".py"):
            python_icon = ui_utils.create_qicon("python_icon")
            btn.setIcon(python_icon)

        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addWidget(btn)
        main_layout.setContentsMargins(20, 2, 20, 2)
        self.setLayout(main_layout)

    def activate_script(self):
        self.script_clicked.emit(self.script_path)


class ScriptModelItem(QtGui.QStandardItem):
    def __init__(self, script_path=None):
        super(ScriptModelItem, self).__init__()
        self.script_path = script_path.replace("/", "\\")
        self.script_name = os.path.basename(script_path)
        self.setData(self.script_name, QtCore.Qt.DisplayRole)
        self.setFlags(self.flags() ^ QtCore.Qt.ItemIsDropEnabled)


###################################
# General UI

class ScriptPanelWindow(ui_utils.BaseWindow):
    def __init__(self, *args, **kwargs):
        super(ScriptPanelWindow, self).__init__(*args, **kwargs)

        self.main_widget = ScriptPanelWidget()
        self.setCentralWidget(self.main_widget)
        self.setWindowTitle("Script Panel")
        self.resize(1000, 1000)


class Icons(object):
    def __init__(self):
        self.python_icon = ui_utils.create_qicon("python_icon")
        self.unknown_type_icon = ui_utils.create_qicon("unknown_icon")
        self.folder_icon = ui_utils.create_qicon("folder_icon")


class ScriptPanelUI(QtWidgets.QWidget):
    script_double_clicked = QtCore.Signal(str)

    def __init__(self, *args, **kwargs):
        super(ScriptPanelUI, self).__init__(*args, **kwargs)

        self.icons = Icons()  # putting this here because it needs to initialize after the QAppliaction

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setSpacing(2)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.search_LE = QtWidgets.QLineEdit()
        self.search_LE.setClearButtonEnabled(True)
        self.search_LE.setPlaceholderText("Search...")
        self.search_LE.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Minimum)

        self.refresh_BTN = QtWidgets.QPushButton("Refresh")

        self.favorites_LW = ScriptFavoritesWidget()
        self.favorites_LW.setSelectionMode(QtWidgets.QListWidget.ExtendedSelection)
        self.favorites_LW.setDropIndicatorShown(True)
        self.favorites_LW.setAcceptDrops(True)
        self.favorites_LW.setDragEnabled(True)
        self.favorites_LW.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.favorites_LW.setDragDropOverwriteMode(False)

        # self.favorites_message_overlay = FavoritesTextOverlay(self.favorites_LW)
        # self.favorites_LW.overlay_widget = self.favorites_message_overlay

        self.scripts_TV = ScriptTreeView()
        self.scripts_TV.setSelectionMode(QtWidgets.QListView.ExtendedSelection)
        self.scripts_TV.setAlternatingRowColors(True)
        self.scripts_TV.setDragEnabled(True)
        self.scripts_TV.setDefaultDropAction(QtCore.Qt.IgnoreAction)
        self.scripts_TV.setDragDropOverwriteMode(False)
        self.scripts_TV.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.scripts_TV.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.scripts_TV.doubleClicked.connect(self.action_script_double_clicked)

        scripts_and_search_layout = QtWidgets.QVBoxLayout()
        search_bar_layout = QtWidgets.QHBoxLayout()
        search_bar_layout.addWidget(self.search_LE)
        search_bar_layout.addWidget(self.refresh_BTN)
        scripts_and_search_layout.addLayout(search_bar_layout)
        scripts_and_search_layout.addWidget(self.scripts_TV)
        scripts_and_search_layout.setSpacing(2)
        scripts_and_search_layout.setContentsMargins(0, 0, 0, 0)
        scripts_and_search_widget = QtWidgets.QWidget()
        scripts_and_search_widget.setLayout(scripts_and_search_layout)

        main_splitter = QtWidgets.QSplitter()
        main_splitter.setOrientation(QtCore.Qt.Orientation.Vertical)
        main_splitter.addWidget(self.favorites_LW)
        main_splitter.addWidget(scripts_and_search_widget)

        if sp_skyhook:
            skyhook_dccs_layout = QtWidgets.QHBoxLayout()
            self.skyhook_blender_CHK = QtWidgets.QCheckBox(text="Skyhook to Blender")
            self.skyhook_blender_CHK.setChecked(True)
            skyhook_dccs_layout.addWidget(self.skyhook_blender_CHK)
            main_layout.addLayout(skyhook_dccs_layout)

        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)

    def action_script_double_clicked(self, index):
        proxy = self.scripts_TV.model()  # type: QtCore.QSortFilterProxyModel
        model_index = proxy.mapToSource(index)
        script_item = proxy.sourceModel().itemFromIndex(model_index)  # type: ScriptModelItem

        self.script_double_clicked.emit(script_item.script_path)


# class FavoritesTextOverlay(QtWidgets.QWidget):
#     def __init__(self, parent=None):
#         super(FavoritesTextOverlay, self).__init__(parent)
#
#         palette = QtGui.QPalette(self.palette())
#         palette.setColor(palette.Background, QtCore.Qt.transparent)
#
#         self.font_size = 13
#         self.empty_list_message = "Drag and drop a script here to favorite it"
#
#         self.setPalette(palette)
#
#     def paintEvent(self, event):
#         painter = QtGui.QPainter()
#         painter.begin(self)
#         painter.setRenderHint(QtGui.QPainter.Antialiasing)
#         painter.fillRect(event.rect(), QtGui.QBrush(QtGui.QColor(100, 100, 100, 100)))
#         painter.setFont(QtGui.QFont("seqoe", self.font_size))
#         painter.drawText(event.rect(), QtCore.Qt.AlignCenter, self.empty_list_message)
#         painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))

class ScriptTreeView(QtWidgets.QTreeView):
    def __init__(self, *args, **kwargs):
        super(ScriptTreeView, self).__init__(*args, **kwargs)

    def dragEnterEvent(self, event):
        if not event.mimeData().hasText():
            selected_script_paths = self.get_selected_script_paths()
            event.mimeData().setText(", ".join(selected_script_paths))

        event.accept()

    def get_selected_script_paths(self):
        proxy = self.model()  # type: QtCore.QSortFilterProxyModel

        selected_script_paths = []
        for index in self.selectedIndexes():
            model_index = proxy.mapToSource(index)
            script_item = proxy.sourceModel().itemFromIndex(model_index)  # type: ScriptModelItem
            if not isinstance(script_item, ScriptModelItem):
                continue
            selected_script_paths.append(script_item.script_path)

        return selected_script_paths


class ScriptFavoritesWidget(QtWidgets.QListWidget):
    script_dropped = QtCore.Signal(str)
    order_updated = QtCore.Signal()
    remove_favorites = QtCore.Signal(list)

    def __init__(self, *args, **kwargs):
        super(ScriptFavoritesWidget, self).__init__(*args, **kwargs)

        del_hotkey = QtWidgets.QShortcut(QtGui.QKeySequence("DEL"), self, self.remove_scripts_from_favorites)
        del_hotkey.setContext(QtCore.Qt.WidgetShortcut)

        # right click menu
        action_list = [
            {"Edit": self.open_script_in_editor},
            {"Remove from favorites": self.remove_scripts_from_favorites}
        ]

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda: ui_utils.build_menu_from_action_list(action_list))

    def dropEvent(self, *args, **kwargs):

        drop_event = args[0]  # type: QtGui.QDropEvent

        if drop_event.mimeData().hasText():
            drop_text = drop_event.mimeData().text()
            if not drop_text:
                return
            for script_path in drop_text.split(", "):
                self.script_dropped.emit(script_path)
        else:
            if type(drop_event.source()) == ScriptTreeView:
                return
            drop_event.setDropAction(QtCore.Qt.MoveAction)
            super(ScriptFavoritesWidget, self).dropEvent(*args, **kwargs)
            self.order_updated.emit()

    def get_selected_script_paths(self):
        script_paths = []
        for lwi in self.selectedItems():  # type: QtWidgets.QListWidgetItem
            script_widget = self.itemWidget(lwi)  # type:ScriptWidget
            script_paths.append(script_widget.script_path)
        return script_paths

    def remove_scripts_from_favorites(self):
        self.remove_favorites.emit(self.get_selected_script_paths())

    def open_script_in_editor(self):
        if "open_script" not in dir(dcc_module):
            print("Editor open not defined for this DCC")
            return
        for script_path in self.get_selected_script_paths():
            dcc_module.open_script(script_path)

    # def resizeEvent(self, event):
    #     self.overlay_widget.resize(event.size())
    #     event.accept()


def main(reload=False):
    standalone_app = None
    if not QtWidgets.QApplication.instance():
        standalone_app = QtWidgets.QApplication(sys.argv)

    win = ScriptPanelWindow()
    win.show_ui(reload=reload)

    if standalone_app:
        sys.exit(standalone_app.exec_())

    return win


if __name__ == '__main__':
    main()
