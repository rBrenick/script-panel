__author__ = "Richard Brenick"

# Standard
import os.path
import subprocess
import sys

from script_panel import script_panel_utils as spu
from script_panel.ui import ui_utils
from script_panel.ui.ui_utils import QtCore, QtWidgets, QtGui

active_dcc_is_maya = "maya" in os.path.basename(sys.executable).lower()

if active_dcc_is_maya:
    from . import script_panel_dcc_maya as dcc_module

    dcc_name = "Maya"
else:
    dcc_name = "Standalone"


class ScriptPanelSettings(QtCore.QSettings):
    k_favorites = "favorites"
    k_double_click_action = "double_click_action"

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

        # build model
        self.model = QtGui.QStandardItemModel()
        self.proxy = QtCore.QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.ui.scripts_TV.setModel(self.proxy)

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

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.ui)
        self.setLayout(main_layout)

    def refresh_scripts(self):
        self.model.clear()
        self.model.setHorizontalHeaderLabels(["Name", "Path"])

        python_icon = ui_utils.create_qicon("python_icon")
        unknown_type_icon = ui_utils.create_qicon("unknown_icon")

        # then add normal scripts
        for script_path, path_info in spu.get_scripts().items():
            item = ScriptModelItem(script_path)

            folder_rel_path = os.path.relpath(os.path.dirname(script_path), path_info.get("root"))
            item_script_path = QtGui.QStandardItem("...\\" + folder_rel_path)

            if script_path.lower().endswith(".py"):
                item.setIcon(python_icon)
            else:
                item.setIcon(unknown_type_icon)

            self.model.appendRow([item, item_script_path])

        header = self.ui.scripts_TV.header()
        header.setSectionResizeMode(0, header.ResizeToContents)

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

    def script_double_clicked(self):
        user_setting = self.settings.get_value(self.settings.k_double_click_action, spu.lk.run_script_on_click)

        if user_setting == spu.lk.run_script_on_click:
            self.activate_script()
        else:
            self.open_script_in_editor()

    def activate_script(self):
        for script_path in self.ui.scripts_TV.get_selected_script_paths():
            spu.file_triggered(script_path)

    def open_script_in_editor(self):
        if not active_dcc_is_maya:
            print("ScriptEditor open not defined for this DCC")
            return
        for script_path in self.ui.scripts_TV.get_selected_script_paths():
            dcc_module.open_script(script_path)

    def open_script_in_explorer(self):
        for script_path in self.ui.scripts_TV.get_selected_script_paths():
            subprocess.Popen(r'explorer /select, "{}"'.format(script_path))


class ScriptWidget(QtWidgets.QWidget):

    def __init__(self, script_path="ExampleScript.py", *args, **kwargs):
        super(ScriptWidget, self).__init__(*args, **kwargs)

        self.script_path = script_path

        btn = QtWidgets.QPushButton(parent=self)
        btn.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        btn.setText(os.path.basename(script_path))
        btn.clicked.connect(self.run_script)

        if self.script_path.lower().endswith(".py"):
            python_icon = ui_utils.create_qicon("python_icon")
            btn.setIcon(python_icon)

        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addWidget(btn)
        main_layout.setContentsMargins(20, 2, 20, 2)
        self.setLayout(main_layout)

    def run_script(self):
        spu.file_triggered(self.script_path)


class ScriptModelItem(QtGui.QStandardItem):
    def __init__(self, script_path):
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


class ScriptPanelUI(QtWidgets.QWidget):
    script_double_clicked = QtCore.Signal(str)

    def __init__(self, *args, **kwargs):
        super(ScriptPanelUI, self).__init__(*args, **kwargs)

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
        if not active_dcc_is_maya:
            return
        for script_path in self.get_selected_script_paths():
            dcc_module.open_script(script_path)

    # def resizeEvent(self, event):
    #     self.overlay_widget.resize(event.size())
    #     event.accept()


def main(refresh=False):
    standalone_app = None
    if not QtWidgets.QApplication.instance():
        standalone_app = QtWidgets.QApplication(sys.argv)

    win = ScriptPanelWindow()
    win.show_ui(refresh=refresh)

    if standalone_app:
        sys.exit(standalone_app.exec_())

    return win


if __name__ == '__main__':
    main()
