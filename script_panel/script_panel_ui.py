__author__ = "Richard Brenick"

# Standard
import os.path
import sys

from script_panel import script_panel_utils as spu
from script_panel.ui import ui_utils
from script_panel.ui.ui_utils import QtCore, QtWidgets, QtGui


class ScriptPanelWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(ScriptPanelWidget, self).__init__(*args, **kwargs)

        self.ui = ScriptPanelUI()

        self.model = QtGui.QStandardItemModel()
        self.ui.scripts_LV.setModel(self.model)
        self.ui.script_double_clicked.connect(spu.run_script)

        self.build_model()

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.ui)
        self.setLayout(main_layout)

    def build_model(self):
        for script_path in spu.get_scripts():
            item = ScriptModelItem(script_path)
            self.model.appendRow(item)

            # build custom widget for the script
            # item_widget = ScriptWidget(script_path)
            # qindex_child = item.index()
            # self.ui.scripts_LV.setIndexWidget(qindex_child, item_widget)


# class ScriptWidget(QtWidgets.QWidget):
#     def __init__(self, script_path="ExampleScript.py", *args, **kwargs):
#         super(ScriptWidget, self).__init__(*args, **kwargs)
#
#         main_layout = QtWidgets.QHBoxLayout()
#         btn = QtWidgets.QPushButton(script_path)
#         main_layout.addWidget(btn)
#         self.setLayout(main_layout)

class ScriptModelItem(QtGui.QStandardItem):
    def __init__(self, script_path):
        super(ScriptModelItem, self).__init__()
        self.script_path = script_path
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


class ScriptPanelUI(QtWidgets.QWidget):
    script_double_clicked = QtCore.Signal(str)

    def __init__(self, *args, **kwargs):
        super(ScriptPanelUI, self).__init__(*args, **kwargs)

        main_layout = QtWidgets.QVBoxLayout()

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

        self.scripts_LV = QtWidgets.QListView()
        self.scripts_LV.setAlternatingRowColors(True)
        self.scripts_LV.setDragEnabled(True)
        self.scripts_LV.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.scripts_LV.setDragDropOverwriteMode(False)
        self.scripts_LV.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.scripts_LV.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.scripts_LV.setWindowTitle('Example List')
        self.scripts_LV.doubleClicked.connect(self.action_script_double_clicked)

        main_layout.addWidget(self.favorites_LW)
        main_layout.addWidget(self.search_LE)
        main_layout.addWidget(self.scripts_LV)
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


class ScriptFavoritesWidget(QtWidgets.QListWidget):
    def __init__(self, *args, **kwargs):
        super(ScriptFavoritesWidget, self).__init__(*args, **kwargs)
        # self.overlay_widget = None

    def dropEvent(*args, **kwargs):
        print(args, kwargs)

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
