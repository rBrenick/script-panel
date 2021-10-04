__author__ = "Richard Brenick"

# Standard
import os.path
import sys

from script_panel import script_panel_utils as spu
from script_panel.ui import ui_utils
from script_panel.ui.ui_utils import QtCore, QtWidgets, QtGui


class ScriptPanelSettings(QtCore.QSettings):
    k_favorites = "favorites"

    def __init__(self, *args, **kwargs):
        super(ScriptPanelSettings, self).__init__(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            "script_panel", "script_panel_standalone",
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


class ScriptPanelWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(ScriptPanelWidget, self).__init__(*args, **kwargs)

        self.ui = ScriptPanelUI()
        self.settings = ScriptPanelSettings()

        # build model
        self.model = QtGui.QStandardItemModel()
        self.proxy = QtCore.QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.ui.scripts_LV.setModel(self.proxy)

        # connect signals
        self.ui.search_LE.textChanged.connect(self.filter_scripts)
        self.ui.script_double_clicked.connect(spu.run_script)
        self.ui.favorites_LW.script_dropped.connect(self.add_script_to_favorites)

        # build ui
        self.build_model()

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.ui)
        self.setLayout(main_layout)

    def build_model(self):
        favorite_scripts = self.settings.get_value(ScriptPanelSettings.k_favorites, default=list())

        self.model.clear()
        self.ui.favorites_LW.clear()
        for script_path in spu.get_scripts():
            item = ScriptModelItem(script_path)
            self.model.appendRow(item)

            if script_path in favorite_scripts:
                self.add_favorite_widget(script_path)

    def add_script_to_favorites(self, script_path):
        self.settings.add_to_favorites(script_path)
        self.build_model()

    def add_favorite_widget(self, script_path):

        script_widget = ScriptWidget(script_path)

        lwi = QtWidgets.QListWidgetItem()
        self.ui.favorites_LW.addItem(lwi)
        self.ui.favorites_LW.setItemWidget(lwi, script_widget)

    def filter_scripts(self, text):
        search = QtCore.QRegExp(text, QtCore.Qt.CaseInsensitive, QtCore.QRegExp.RegExp)
        self.proxy.setFilterRegExp(search)


class ScriptWidget(QtWidgets.QPushButton):
    def __init__(self, script_path="ExampleScript.py", *args, **kwargs):
        super(ScriptWidget, self).__init__(*args, **kwargs)

        self.script_path = script_path
        self.setText(os.path.basename(script_path))

        self.clicked.connect(self.run_script)

    def run_script(self):
        spu.run_script(self.script_path)


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
        self.resize(600, 800)


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

        self.favorites_LW = ScriptFavoritesWidget()
        self.favorites_LW.setDropIndicatorShown(True)
        self.favorites_LW.setAcceptDrops(True)
        self.favorites_LW.setDragEnabled(True)
        self.favorites_LW.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.favorites_LW.setDragDropOverwriteMode(False)

        # self.favorites_message_overlay = FavoritesTextOverlay(self.favorites_LW)
        # self.favorites_LW.overlay_widget = self.favorites_message_overlay

        self.scripts_LV = ScriptListView()
        self.scripts_LV.setAlternatingRowColors(True)
        self.scripts_LV.setDragEnabled(True)
        self.scripts_LV.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.scripts_LV.setDragDropOverwriteMode(False)
        self.scripts_LV.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.scripts_LV.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.scripts_LV.setWindowTitle('Example List')
        self.scripts_LV.doubleClicked.connect(self.action_script_double_clicked)

        scripts_and_search_layout = QtWidgets.QVBoxLayout()
        scripts_and_search_layout.addWidget(self.search_LE)
        scripts_and_search_layout.addWidget(self.scripts_LV)
        scripts_and_search_layout.setSpacing(2)
        scripts_and_search_layout.setContentsMargins(0, 0, 0, 0)
        scripts_and_search_widget = QtWidgets.QWidget()
        scripts_and_search_widget.setLayout(scripts_and_search_layout)

        main_splitter = QtWidgets.QSplitter()
        main_splitter.setOrientation(QtCore.Qt.Orientation.Vertical)
        main_splitter.addWidget(self.favorites_LW)
        main_splitter.addWidget(scripts_and_search_widget)

        # main_layout.addWidget(self.favorites_LW)
        # main_layout.addWidget(self.search_LE)
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)

    def action_script_double_clicked(self, index):
        script_item = self.scripts_LV.model().itemFromIndex(index)  # type: ScriptModelItem
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

class ScriptListView(QtWidgets.QListView):
    def dragEnterEvent(self, event):
        if not event.mimeData().hasText():
            script_item = self.model().itemFromIndex(self.currentIndex())  # type: ScriptModelItem
            event.mimeData().setText(script_item.script_path)
        event.accept()


class ScriptFavoritesWidget(QtWidgets.QListWidget):
    script_dropped = QtCore.Signal(str)

    def __init__(self, *args, **kwargs):
        super(ScriptFavoritesWidget, self).__init__(*args, **kwargs)
        # self.overlay_widget = None

    def dropEvent(self, *args, **kwargs):
        drop_event = args[0]  # type: QtGui.QDropEvent
        script_path = drop_event.mimeData().text()
        self.script_dropped.emit(script_path)

    # def resizeEvent(self, event):
    #     self.overlay_widget.resize(event.size())
    #     event.accept()


def main():
    standalone_app = None
    if not QtWidgets.QApplication.instance():
        standalone_app = QtWidgets.QApplication(sys.argv)

    win = ScriptPanelWindow()

    if standalone_app:
        sys.exit(standalone_app.exec_())

    return win


if __name__ == '__main__':
    main()
