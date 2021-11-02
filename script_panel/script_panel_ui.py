__author__ = "Richard Brenick"

# Standard
import os.path
import subprocess
import sys

from script_panel import dcc
from script_panel import script_panel_utils as spu
from script_panel.ui import command_palette
from script_panel.ui import folder_model
from script_panel.ui import ui_utils
from script_panel.ui.ui_utils import QtCore, QtWidgets, QtGui

try:
    from script_panel.dcc import script_panel_skyhook as sp_skyhook
except ImportError as e:
    print("Optional skyhook import failed: {}".format(e))
    sp_skyhook = None

standalone_app = None
if not QtWidgets.QApplication.instance():
    standalone_app = QtWidgets.QApplication(sys.argv)

dcc_interface = dcc.DCCInterface()
BACKGROUND_COLOR_FORM = "background-color:rgb({0}, {1}, {2})"


class ScriptPanelSettings(ui_utils.BaseSettings):
    k_favorites = "favorites"
    k_favorites_layout = "favorites_layout"
    k_favorites_display = "favorites_display"
    k_palette_display = "palette_display"
    k_double_click_action = "double_click_action"
    k_skyhook_enabled = "skyhook_enabled"

    def __init__(self, *args, **kwargs):
        super(ScriptPanelSettings, self).__init__(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            "script_panel", "script_panel_{}".format(dcc_interface.name.lower()),
            *args, **kwargs)

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
        self.ui.script_dropped_in_favorites.connect(self.add_script_to_favorites)
        self.ui.save_palette_BTN.clicked.connect(self.save_favorites_layout)
        self.ui.load_palette_BTN.clicked.connect(self.load_favorites_layout)

        # right click menus
        self.ui.scripts_TV.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.scripts_TV.customContextMenuRequested.connect(self.build_context_menu)

        self.ui.command_palette_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.command_palette_widget.customContextMenuRequested.connect(self.build_palette_context_menu)

        # shortcuts
        self.setup_palette_shortcuts()

        # build ui
        self.load_favorites_layout()
        self.refresh_scripts()
        self.load_settings()

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.ui)
        self.setLayout(main_layout)

    def setup_palette_shortcuts(self):
        del_hotkey = QtWidgets.QShortcut(
            QtGui.QKeySequence("DEL"),
            self.ui.command_palette_widget.graphics_view,
            self.remove_scripts_from_favorites,
        )
        del_hotkey.setContext(QtCore.Qt.WidgetShortcut)

        save_layout_hotkey = QtWidgets.QShortcut(
            QtGui.QKeySequence("Ctrl+S"),
            self.ui.command_palette_widget.graphics_view,
            self.save_favorites_layout,
        )
        save_layout_hotkey.setContext(QtCore.Qt.WidgetShortcut)

        load_layout_hotkey = QtWidgets.QShortcut(
            QtGui.QKeySequence("F5"),
            self.ui.command_palette_widget.graphics_view,
            self.load_favorites_layout,
        )
        load_layout_hotkey.setContext(QtCore.Qt.WidgetShortcut)

    def build_context_menu(self):
        script_is_selected = any(self.ui.scripts_TV.get_selected_script_paths())

        # right click menu
        script_panel_context_actions = []
        if script_is_selected:
            script_panel_context_actions.extend([
                {"Run": self.activate_script},
                {"Edit": self.open_script_in_editor},
                {"Create Hotkey": self.open_hotkey_editor},
                "-",
            ])

        script_panel_context_actions.extend([
            {"RADIO_SETTING": {"settings": self.settings,
                               "settings_key": self.settings.k_double_click_action,
                               "choices": [spu.lk.run_script_on_click, spu.lk.edit_script_on_click],
                               "default": spu.lk.run_script_on_click,
                               }},
            "-",
            {"Show In Explorer": self.open_script_in_explorer},
        ])
        ui_utils.build_menu_from_action_list(script_panel_context_actions)

    def build_palette_context_menu(self):

        selected_items = self.ui.command_palette_widget.get_selected_items()
        if len(selected_items) == 1:
            selected_script_widget = selected_items[-1].wrapped_widget  # type: ScriptWidget
        else:
            selected_script_widget = None

        action_list = [
            {"Edit": self.open_favorites_script_in_editor},
            {"Remove from favorites": self.remove_scripts_from_favorites},
            {"Hide Headers": self.ui.command_palette_widget.hide_headers},
            {"Show Headers": self.ui.command_palette_widget.show_headers},
        ]

        if selected_script_widget:
            action_list.extend([
                "-",
                {"Set Label": selected_script_widget.open_label_editor},
                {"Set Color": selected_script_widget.open_display_color_picker},
                {"Set Icon": selected_script_widget.open_icon_browser},
                "-",
                {"Reset Display": selected_script_widget.reset_display},
                {"Reset Display - Label": selected_script_widget.reset_display_label},
                {"Reset Display - Color": selected_script_widget.reset_display_color},
                {"Reset Display - Icon": selected_script_widget.reset_display_icon},
            ])

        ui_utils.build_menu_from_action_list(action_list)

    def load_settings(self):
        if sp_skyhook:
            skyhook_enabled = self.settings.get_value(self.settings.k_skyhook_enabled, default=False)
            self.ui.skyhook_blender_CHK.setChecked(skyhook_enabled)
        palette_display_settings = self.settings.get_value(ScriptPanelSettings.k_palette_display, default=dict())
        self.ui.command_palette_widget.set_ui_settings(palette_display_settings)

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
        path_root_dir = path_info.get(spu.PathInfoKeys.root_dir)
        display_prefix = path_info.get(spu.PathInfoKeys.folder_prefix)
        root_type = path_info.get(spu.PathInfoKeys.root_type)

        # display path in tree view
        script_rel_path = os.path.relpath(script_path, path_root_dir)
        dir_rel_path = os.path.relpath(os.path.dirname(script_path), path_root_dir)
        display_dir_rel_path = dir_rel_path
        if display_prefix:
            display_dir_rel_path = "{}\\{}".format(display_prefix, display_dir_rel_path)

        root_folder_icon = icons.get_root_folder_icon_for_type(root_type)
        folder_icon = icons.get_folder_icon_for_type(root_type)
        parent_item = self.model

        # build needed folders
        folder_rel_split = display_dir_rel_path.split("\\")
        for i, token in enumerate(folder_rel_split):
            if token in [".", ""]:
                continue

            # combine together the token into a relative_path
            token_rel_display_path = "\\".join(folder_rel_split[:i + 1])
            token_rel_real_path = "\\".join(folder_rel_split[1:i + 1]) if display_prefix else token_rel_display_path
            token_full_path = os.path.join(path_root_dir, token_rel_real_path)

            # an Item for this folder has already been created
            existing_folder_item = self._model_folders.get(token_rel_display_path)
            if existing_folder_item is not None:
                parent_item = existing_folder_item
            else:
                new_folder_item = QtGui.QStandardItem(str(token))

                # set special icon if this is the root folder
                new_folder_item.setIcon(root_folder_icon) if i == 0 else new_folder_item.setIcon(folder_icon)

                # mark as folder for sorting model
                folder_path_data = folder_model.PathData(relative_path=token_rel_real_path,
                                                         full_path=token_full_path,
                                                         is_folder=True,
                                                         )
                new_folder_item.setData(folder_path_data, QtCore.Qt.UserRole)

                parent_item.appendRow(new_folder_item)
                parent_item = new_folder_item
                self._model_folders[token_rel_display_path] = new_folder_item

        item = ScriptModelItem(script_path)
        path_data = folder_model.PathData(relative_path=script_rel_path,
                                          full_path=script_path,
                                          is_folder=False,
                                          )
        item.setData(path_data, QtCore.Qt.UserRole)

        script_icon = icons.get_script_icon_for_type(script_path, root_type)
        item.setIcon(script_icon)

        parent_item.appendRow(item)

    def load_favorites_layout(self):
        favorite_scripts = self.settings.get_value(ScriptPanelSettings.k_favorites, default=list())
        self.ui.command_palette_widget.clear()

        for script_path in favorite_scripts:
            self.add_favorite_widget(script_path)

        user_layout = self.settings.get_value(ScriptPanelSettings.k_favorites_layout, default=dict())
        self.ui.command_palette_widget.set_scene_layout(user_layout)

    def add_script_to_favorites(self, script_path):
        self.settings.add_to_favorites(script_path)
        self.add_favorite_widget(script_path)

    def remove_scripts_from_favorites(self):
        for item in self.ui.command_palette_widget.get_selected_items():  # type: command_palette.PaletteRectItem
            script_widget = item.wrapped_widget  # type: ScriptWidget
            self.settings.remove_from_favorites(script_widget.script_path)
        self.ui.command_palette_widget.remove_selected_items()

    def open_favorites_script_in_editor(self):
        for item in self.ui.command_palette_widget.get_selected_items():  # type: command_palette.PaletteRectItem
            script_widget = item.wrapped_widget  # type: ScriptWidget
            self.open_script_in_editor(script_widget.script_path)

    def add_favorite_widget(self, script_path):
        all_display_info = self.settings.get_value(ScriptPanelSettings.k_favorites_display, default=dict())
        display_info = all_display_info.get(script_path)

        script_widget = ScriptWidget(script_path)
        script_widget.script_clicked.connect(self.activate_script)
        if display_info:
            script_widget.set_display_from_info(display_info)

        script_id = os.path.basename(script_path)
        self.ui.command_palette_widget.add_widget(
            id=script_id,
            widget=script_widget,
            pos=self.ui.command_palette_widget.get_mouse_pos(),
        )

    def save_favorites_layout(self):
        favorite_scripts = []
        scripts_display_info = {}
        for script_widget in self.ui.command_palette_widget.scene_widgets:  # type: ScriptWidget
            favorite_scripts.append(script_widget.script_path)
            scripts_display_info[script_widget.script_path] = script_widget.get_display_info()

        user_layout = self.ui.command_palette_widget.get_scene_layout()

        self.settings.setValue(self.settings.k_favorites, favorite_scripts)
        self.settings.setValue(self.settings.k_favorites_layout, user_layout)
        self.settings.setValue(self.settings.k_favorites_display, scripts_display_info)
        self.settings.setValue(self.settings.k_palette_display, self.ui.command_palette_widget.get_ui_settings())
        print("Layout Saved")

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
        if not script_path:
            script_path = self.ui.scripts_TV.get_selected_script_paths()[0]
        dcc_interface.open_script(script_path)

    def open_hotkey_editor(self, script_path=None):
        if not script_path:
            script_path = self.ui.scripts_TV.get_selected_script_paths()[0]

        from .ui import hotkey_editor
        hotkey_editor.main(reload=True, script_path=script_path)

    def open_script_in_explorer(self, script_path=None):
        if not script_path:
            script_path = self.ui.scripts_TV.get_selected_script_paths(allow_folders=True)[0]
        subprocess.Popen(r'explorer /select, "{}"'.format(script_path))


class ScriptWidget(QtWidgets.QWidget):
    script_clicked = QtCore.Signal(str)

    def __init__(self, script_path="ExampleScript.py", *args, **kwargs):
        super(ScriptWidget, self).__init__(*args, **kwargs)

        self.script_path = script_path
        self.script_name = os.path.basename(script_path)
        self.display_color = None
        self.icon_path = None

        self.trigger_btn = QtWidgets.QPushButton(parent=self)
        self.trigger_btn.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.trigger_btn.setText(self.script_name)
        self.trigger_btn.clicked.connect(self.activate_script)

        self.default_icon = icons.get_script_icon_for_type(script_path)
        self.trigger_btn.setIcon(self.default_icon)

        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addWidget(self.trigger_btn)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

    def activate_script(self):
        self.script_clicked.emit(self.script_path)

    def get_display_info(self):
        return {
            "label": self.trigger_btn.text(),
            "color": self.display_color,
            "icon_path": self.icon_path,
        }

    def set_display_from_info(self, display_info):
        self.set_display_label(display_info.get("label", self.script_name))
        self.set_display_color(display_info.get("color"))
        self.set_icon_from_path(display_info.get("icon_path"))

    def reset_display(self):
        self.set_display_from_info(dict())

    def reset_display_label(self):
        self.set_display_label(self.script_name)

    def reset_display_color(self):
        self.set_display_color(None)

    def reset_display_icon(self):
        self.set_icon_from_path(None)

    #########################################
    # Display utility functions
    def open_label_editor(self):
        current_text = self.trigger_btn.text()
        new_text, ok = QtWidgets.QInputDialog.getText(
            ui_utils.get_app_window(),
            "New Display Label",
            "Enter new display label for: {}".format(self.script_name),
            text=current_text,
        )
        if ok:
            self.set_display_label(new_text)

    def set_display_label(self, text):
        self.trigger_btn.setText(text)

    def open_display_color_picker(self):
        new_color = ui_utils.open_color_picker(current_color=self.display_color,
                                               color_signal=self.update_display_color)
        if new_color:
            self.set_display_color(new_color.getRgb()[:3])
        else:
            self.update_display_color(self.display_color)

    def set_display_color(self, color):
        """Set the internal variable and apply the color on the widget"""
        self.display_color = color
        self.update_display_color(color)

    def update_display_color(self, color):
        """Change the display of the background color"""
        if not color:
            self.trigger_btn.setStyleSheet("")
            return

        if isinstance(color, QtGui.QColor):
            color = color.getRgb()[:3]

        self.trigger_btn.setStyleSheet(BACKGROUND_COLOR_FORM.format(*color))

    def open_icon_browser(self):
        selected_file, _ = QtWidgets.QFileDialog.getOpenFileName(ui_utils.get_app_window(), "Select icon")
        if selected_file:
            self.set_icon_from_path(selected_file)

    def set_icon_from_path(self, icon_path):
        if not icon_path:
            self.icon_path = icon_path
            self.trigger_btn.setIcon(self.default_icon)
            return

        try:
            q_icon = ui_utils.create_qicon(icon_path)
            self.trigger_btn.setIcon(q_icon)
            self.icon_path = icon_path
        except Exception as e:
            print("Unable to set icon: ", e)


class ScriptModelItem(QtGui.QStandardItem):
    def __init__(self, script_path=None):
        super(ScriptModelItem, self).__init__()
        self.script_path = script_path.replace("/", "\\")
        self.script_name = os.path.basename(script_path)
        self.setData(self.script_name, QtCore.Qt.DisplayRole)
        self.setFlags(self.flags() ^ QtCore.Qt.ItemIsDropEnabled)


###################################
# General UI

class Icons(object):
    def __init__(self):
        self.script_panel_icon = ui_utils.create_qicon("script_panel_icon")

        self.python_icon = ui_utils.create_qicon("python_icon")
        self.mel_icon = ui_utils.create_qicon("mel_icon")
        self.unknown_type_icon = ui_utils.create_qicon("unknown_icon")
        self.folder_icon = ui_utils.create_qicon("folder_icon")

        self.network_folder_icon = ui_utils.create_qicon("network_folder_icon")

        self.p4_icon = ui_utils.create_qicon("p4_icon")
        self.p4_folder_icon = ui_utils.create_qicon("p4_folder_icon")
        self.p4_python_icon = ui_utils.create_qicon("p4_python_icon")

    def get_folder_icon_for_type(self, folder_type):
        """Get Icon for normal folders"""
        if folder_type == "local" or folder_type == "network":
            return self.folder_icon
        if folder_type == "p4":
            return self.p4_folder_icon

        return self.unknown_type_icon

    def get_root_folder_icon_for_type(self, folder_type):
        """Get Icon to display as the root folder"""
        if folder_type == "local":
            return self.folder_icon
        if folder_type == "network":
            return self.network_folder_icon
        if folder_type == "p4":
            return self.p4_icon

        return self.unknown_type_icon

    def get_script_icon_for_type(self, file_name, folder_type=""):
        """get icon for the script"""
        if file_name.endswith(".py"):
            if folder_type == "p4":
                return self.p4_python_icon
            return self.python_icon

        elif file_name.endswith(".mel"):
            return self.mel_icon

        return self.unknown_type_icon


icons = Icons()


class ScriptPanelWindow(ui_utils.ToolWindow):
    def __init__(self, *args, **kwargs):
        super(ScriptPanelWindow, self).__init__(*args, **kwargs)

        self.main_widget = ScriptPanelWidget()
        self.setCentralWidget(self.main_widget)
        self.setWindowTitle("Script Panel")
        self.setWindowIcon(icons.script_panel_icon)
        self.resize(1000, 1000)


class ScriptPanelUI(QtWidgets.QWidget):
    script_double_clicked = QtCore.Signal(str)
    script_dropped_in_favorites = QtCore.Signal(str)

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

        self.command_palette_widget = command_palette.CommandPaletteWidget()
        self.command_palette_widget.graphics_view.item_dropped.connect(self.palette_item_dropped)

        self.scripts_TV = ScriptTreeView()
        self.scripts_TV.setSelectionMode(QtWidgets.QListView.ExtendedSelection)
        self.scripts_TV.setAlternatingRowColors(True)
        self.scripts_TV.setDragEnabled(True)
        self.scripts_TV.setDefaultDropAction(QtCore.Qt.IgnoreAction)
        self.scripts_TV.setDragDropOverwriteMode(False)
        self.scripts_TV.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
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
        main_splitter.addWidget(self.command_palette_widget)
        main_splitter.addWidget(scripts_and_search_widget)

        if sp_skyhook:
            skyhook_dccs_layout = QtWidgets.QHBoxLayout()
            self.skyhook_blender_CHK = QtWidgets.QCheckBox(text="Skyhook to Blender")
            self.skyhook_blender_CHK.setChecked(True)
            skyhook_dccs_layout.addWidget(self.skyhook_blender_CHK)
            main_layout.addLayout(skyhook_dccs_layout)

        palette_buttons_layout = QtWidgets.QHBoxLayout()
        self.save_palette_BTN = QtWidgets.QPushButton(text="Save Layout")
        self.load_palette_BTN = QtWidgets.QPushButton(text="Load Layout")
        palette_buttons_layout.addWidget(self.save_palette_BTN)
        palette_buttons_layout.addWidget(self.load_palette_BTN)
        main_layout.addLayout(palette_buttons_layout)

        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)

    def action_script_double_clicked(self, index):
        proxy = self.scripts_TV.model()  # type: QtCore.QSortFilterProxyModel
        model_index = proxy.mapToSource(index)
        script_item = proxy.sourceModel().itemFromIndex(model_index)  # type: ScriptModelItem

        if isinstance(script_item, ScriptModelItem):
            self.script_double_clicked.emit(script_item.script_path)

    def palette_item_dropped(self, event):
        """
        :type event: QtGui.QDropEvent
        """
        if isinstance(event.source(), ScriptTreeView):
            selected_scripts = self.scripts_TV.get_selected_script_paths()
            if selected_scripts:
                self.script_dropped_in_favorites.emit(selected_scripts[0])


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

    def get_selected_script_paths(self, allow_folders=False):
        proxy = self.model()  # type: QtCore.QSortFilterProxyModel

        selected_paths = []
        for index in self.selectedIndexes():
            model_index = proxy.mapToSource(index)
            path_data = proxy.sourceModel().data(model_index, QtCore.Qt.UserRole)  # type: folder_model.PathData

            selected_path = path_data.full_path

            # skip folders if they're not allowed
            if allow_folders is False and path_data.is_folder:
                selected_path = None

            if selected_path:
                selected_paths.append(selected_path)

        return selected_paths


# class ScriptFavoritesWidget(QtWidgets.QListWidget):
#     script_dropped = QtCore.Signal(str)
#     order_updated = QtCore.Signal()
#     remove_favorites = QtCore.Signal(list)
#
#     def __init__(self, *args, **kwargs):
#         super(ScriptFavoritesWidget, self).__init__(*args, **kwargs)
#
#         del_hotkey = QtWidgets.QShortcut(QtGui.QKeySequence("DEL"), self, self.remove_scripts_from_favorites)
#         del_hotkey.setContext(QtCore.Qt.WidgetShortcut)
#
#         # right click menu
#         action_list = [
#             {"Edit": self.open_script_in_editor},
#             {"Remove from favorites": self.remove_scripts_from_favorites}
#         ]
#
#         self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
#         self.customContextMenuRequested.connect(lambda: ui_utils.build_menu_from_action_list(action_list))
#
#     def dropEvent(self, *args, **kwargs):
#
#         drop_event = args[0]  # type: QtGui.QDropEvent
#
#         if drop_event.mimeData().hasText():
#             drop_text = drop_event.mimeData().text()
#             if not drop_text:
#                 return
#             for script_path in drop_text.split(", "):
#                 self.script_dropped.emit(script_path)
#         else:
#             if type(drop_event.source()) == ScriptTreeView:
#                 return
#             drop_event.setDropAction(QtCore.Qt.MoveAction)
#             super(ScriptFavoritesWidget, self).dropEvent(*args, **kwargs)
#             self.order_updated.emit()
#
#     def get_selected_script_paths(self):
#         script_paths = []
#         for lwi in self.selectedItems():  # type: QtWidgets.QListWidgetItem
#             script_widget = self.itemWidget(lwi)  # type:ScriptWidget
#             script_paths.append(script_widget.script_path)
#         return script_paths
#
#     def remove_scripts_from_favorites(self):
#         self.remove_favorites.emit(self.get_selected_script_paths())
#
#     def open_script_in_editor(self):
#         for script_path in self.get_selected_script_paths():
#             dcc_interface.open_script(script_path)

# def resizeEvent(self, event):
#     self.overlay_widget.resize(event.size())
#     event.accept()


def show_warning_path_does_not_exist(file_path):
    """
    Show a prompt when a script file does not exist anywhere on disk
    """
    msgbox = QtWidgets.QMessageBox(ui_utils.get_app_window())
    msgbox.setIcon(QtWidgets.QMessageBox.Warning)
    msgbox.setWindowTitle("File does not exist")
    msgbox.setText("File could not be found at this location: \n{}".format(file_path))

    msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel)
    yes_button = msgbox.button(QtWidgets.QMessageBox.Yes)
    yes_button.setText("Open Folder")
    msgbox.exec_()

    if msgbox.clickedButton() == yes_button:
        folder_path = spu.get_existing_folder(file_path)

        if not folder_path:
            sys.stdout.write("No existing folder could be found anywhere from path: {}".format(file_path))
            return

        subprocess.Popen(r'explorer "{}"'.format(folder_path))


def main(reload=False):
    win = ScriptPanelWindow()
    win.main(reload=reload)

    if standalone_app:
        ui_utils.standalone_app_window = win
        sys.exit(standalone_app.exec_())

    return win


if __name__ == '__main__':
    main()
