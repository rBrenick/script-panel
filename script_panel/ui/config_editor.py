import collections
import json
import os

import script_panel.script_panel_settings as sps
import script_panel.script_panel_utils as spu
from . import python_syntax
from . import ui_utils
from .ui_utils import QtWidgets, QtCore, QtGui


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

        # add snippets
        for display_key, snippet_text in self.user_config_data.user_snippets.items():
            self.add_snippet(display_key, snippet_text)

        # connect
        self.ui.add_path_btn.clicked.connect(self.add_new_path)
        self.ui.remove_path_btn.clicked.connect(self.remove_selected_paths)
        self.ui.save_config_btn.clicked.connect(self.save_user_config)
        self.ui.add_snippet_btn.clicked.connect(self.add_snippet)
        self.ui.remove_snippet_btn.clicked.connect(self.remove_selected_snippets)
        self.ui.snippet_shortcut_LE.textChanged.connect(self.ui.set_snippet_label_text)

        current_shortcut = self.user_config_data.get_user_data().get(spu.lk.snippet_shortcut)
        if current_shortcut:
            self.ui.snippet_shortcut_LE.setText(current_shortcut)

        self.ui.display_save_required(False)

    def save_user_config(self):
        snippet_key = self.ui.snippet_shortcut_LE.text() if self.ui.snippet_shortcut_LE.text() else None

        user_config_data = collections.OrderedDict()
        user_config_data[spu.lk.paths] = self.get_user_config_paths_from_ui()
        user_config_data[spu.lk.snippets] = self.get_snippets_from_ui()
        user_config_data[spu.lk.snippet_shortcut] = snippet_key
        with open(sps.sk.user_config_json_path, "w") as fp:
            json.dump(user_config_data, fp, indent=2)

        try:
            # noinspection PyUnreachableCode
            if 0:
                import script_panel.script_panel_ui
                self.parent_window = script_panel.script_panel_ui.ScriptPanelWidget()

            self.parent_window.config_refresh()
            self.parent_window.save_settings()
            self.parent_window.register_snippet_shortcut()

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

    def get_snippets_from_ui(self):
        snippet_data = {}
        for i in range(self.ui.snippets_TW.topLevelItemCount()):
            item = self.ui.snippets_TW.topLevelItem(i)  # type: QtWidgets.QTreeWidgetItem
            snippet_data[item.text(0)] = item.text(1)
        return snippet_data

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

    def add_snippet(self, display_key=None, snippet_text=None):
        if display_key is None and snippet_text is None:
            display_key, snippet_text = new_snippet_dialog(self)
            if not display_key and not snippet_text:
                return

        root_twi = QtWidgets.QTreeWidgetItem()
        root_twi.setFlags(root_twi.flags() | QtWidgets.QTreeWidget.AllEditTriggers)
        root_twi.setText(0, display_key)
        root_twi.setText(1, snippet_text)
        self.ui.snippets_TW.addTopLevelItem(root_twi)
        root_twi.setExpanded(True)
        self.ui.snippets_TW.resizeColumnToContents(0)
        self.ui.display_save_required()

    def remove_selected_paths(self):
        self.remove_selected_tree_widget_items(self.ui.user_paths_TW)

    def remove_selected_snippets(self):
        self.remove_selected_tree_widget_items(self.ui.snippets_TW)

    def remove_selected_tree_widget_items(self, tree_widget):
        something_changed = False
        for item in tree_widget.selectedItems():
            try:
                if item.parent():
                    continue
                item_index = tree_widget.indexFromItem(item)  # type: QtCore.QModelIndex
                tree_widget.takeTopLevelItem(item_index.row())
                something_changed = True
            except Exception as except_info:
                print(except_info)

        if something_changed:
            self.ui.display_save_required()


def new_snippet_dialog(parent=None):
    if parent is None:
        parent = ui_utils.get_app_window()

    prompt_window = QtWidgets.QDialog(parent)
    prompt_window.setWindowTitle("Add Snippet")

    display_key_LE = QtWidgets.QLineEdit()
    display_key_LE.setPlaceholderText("Display Text")

    snippet_TE = QtWidgets.QTextEdit()
    snippet_TE.setPlaceholderText("Snippet text")
    python_syntax.PythonHighlighter(snippet_TE.document())

    font = QtGui.QFont("Courier New")
    snippet_TE.document().setDefaultFont(font)

    buttons = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
        QtCore.Qt.Horizontal,
        prompt_window
    )
    buttons.accepted.connect(prompt_window.accept)
    buttons.rejected.connect(prompt_window.reject)

    prompt_layout = QtWidgets.QVBoxLayout()
    prompt_layout.addWidget(display_key_LE)
    prompt_layout.addWidget(snippet_TE)
    prompt_layout.addWidget(buttons)
    prompt_window.setLayout(prompt_layout)

    result = prompt_window.exec_()

    if result == QtWidgets.QDialog.Accepted:
        return display_key_LE.text(), snippet_TE.toPlainText()

    return None, None


class ConfigEditorWidget(QtWidgets.QWidget):
    def __init__(self):
        super(ConfigEditorWidget, self).__init__()

        self.main_layout = QtWidgets.QVBoxLayout()

        self.save_config_btn = QtWidgets.QPushButton("Save")
        self.save_config_btn.setShortcut("Ctrl+S")
        self.save_config_btn.setMinimumHeight(40)

        self.add_path_btn = QtWidgets.QPushButton("Add Path")
        self.remove_path_btn = QtWidgets.QPushButton("Remove Path")
        self.remove_path_btn.setShortcut("DEL")

        self.user_paths_TW = QtWidgets.QTreeWidget()
        self.user_paths_TW.setHeaderLabels(["Key", "Val"])
        self.user_paths_TW.setHeaderHidden(True)

        self.env_paths_TW = QtWidgets.QTreeWidget()
        self.env_paths_TW.setHeaderLabels(["Key", "Val"])
        self.env_paths_TW.setHeaderHidden(True)

        self.snippets_label = QtWidgets.QLabel()
        self.set_snippet_label_text(spu.lk.default_snippet_shortcut)
        self.snippets_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByKeyboard | QtCore.Qt.TextSelectableByMouse)
        self.snippet_shortcut_LE = QtWidgets.QLineEdit()
        self.snippet_shortcut_LE.setPlaceholderText("Snippet Shortcut: default ({})".format(spu.lk.default_snippet_shortcut))
        self.add_snippet_btn = QtWidgets.QPushButton("Add Snippet")
        self.remove_snippet_btn = QtWidgets.QPushButton("Remove Snippet")
        self.remove_snippet_btn.setShortcut("DEL")
        self.snippets_TW = QtWidgets.QTreeWidget()
        self.snippets_TW.setHeaderLabels(["Display Text", "Snippet Text"])

        self.user_paths_label = QtWidgets.QLabel("Define custom paths to search for scripts.")
        self.user_paths_widget = QtWidgets.QWidget()
        self.user_paths_widget.setLayout(QtWidgets.QVBoxLayout())
        self.config_buttons_layout = QtWidgets.QHBoxLayout()
        self.config_buttons_layout.addWidget(self.add_path_btn)
        self.config_buttons_layout.addWidget(self.remove_path_btn)
        self.user_paths_widget.layout().addWidget(self.user_paths_label)
        self.user_paths_widget.layout().addLayout(self.config_buttons_layout)
        self.user_paths_widget.layout().addWidget(self.user_paths_TW)
        self.user_paths_widget.layout().setContentsMargins(0, 5, 0, 0)

        self.snippets_widget = QtWidgets.QWidget()
        self.snippets_widget.setLayout(QtWidgets.QVBoxLayout())
        self.snippet_buttons_layout = QtWidgets.QHBoxLayout()
        self.snippet_buttons_layout.addWidget(self.add_snippet_btn)
        self.snippet_buttons_layout.addWidget(self.remove_snippet_btn)
        self.snippets_widget.layout().addWidget(self.snippets_label)
        self.snippets_widget.layout().addLayout(self.snippet_buttons_layout)
        self.snippets_widget.layout().addWidget(self.snippets_TW)
        self.snippets_widget.layout().addWidget(self.snippet_shortcut_LE)
        self.snippets_widget.layout().setContentsMargins(0, 5, 0, 0)

        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.addTab(self.user_paths_widget, "User Defined Paths")
        self.tab_widget.addTab(self.env_paths_TW, "Environment Paths")
        self.tab_widget.addTab(self.snippets_widget, "Snippets")

        self.config_layout = QtWidgets.QVBoxLayout()
        self.config_layout.addWidget(self.tab_widget)
        self.config_layout.addWidget(self.save_config_btn)
        self.main_layout.addLayout(self.config_layout)
        self.setLayout(self.main_layout)

    def set_snippet_label_text(self, key=None):
        if not key:
            key = spu.lk.default_snippet_shortcut
        text = "Create snippets of code that can be accessed by {}.\n\nPut SP_SELECTED_TEXT in the snippet to use the currently selected text.".format(key)
        self.snippets_label.setText(text)

    def display_save_required(self, needs_save=True):
        if needs_save:
            self.save_config_btn.setStyleSheet(BACKGROUND_COLOR_RED)
            self.save_config_btn.setText("Save*")
        else:
            self.save_config_btn.setStyleSheet(BACKGROUND_COLOR_GREEN)
            self.save_config_btn.setText("Save")


class PathListWidgetItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, *args, **kwargs):
        super(PathListWidgetItem, self).__init__(*args, **kwargs)


def main(parent_window=None, reload=False):
    win = ConfigEditorWindow(parent=parent_window)
    win.main(reload=reload)
    return win
