# Standard
import functools
import os
import sys
from functools import partial

# Not even going to pretend to have Maya 2016 support
from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtUiTools
from PySide2 import QtWidgets
from shiboken2 import wrapInstance

if sys.version_info.major >= 3:
    long = int

UI_FILES_FOLDER = os.path.dirname(__file__)
ICON_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons")

active_dcc_is_maya = "maya" in os.path.basename(sys.executable).lower()
active_dcc_is_houdini = "houdini" in os.path.basename(sys.executable).lower()

standalone_app_window = None


class BaseSettings(QtCore.QSettings):
    def get_value(self, key, default=None):
        data_type = None
        if default is not None:
            data_type = type(default)

        settings_val = self.value(key, defaultValue=default)
        if settings_val is None:
            return default

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


def get_app_window():
    top_window = standalone_app_window

    if active_dcc_is_maya:
        from maya import OpenMayaUI as omui
        maya_main_window_ptr = omui.MQtUtil().mainWindow()
        top_window = wrapInstance(long(maya_main_window_ptr), QtWidgets.QMainWindow)

    elif active_dcc_is_houdini:
        import hou
        top_window = hou.qt.mainWindow()

    return top_window


def delete_window(object_to_delete):
    qApp = QtWidgets.QApplication.instance()
    if not qApp:
        return

    for widget in qApp.topLevelWidgets():
        if "__class__" in dir(widget):
            if str(widget.__class__) == str(object_to_delete.__class__):
                widget.deleteLater()
                widget.close()


def load_ui_file(ui_file_name):
    ui_file_path = os.path.join(UI_FILES_FOLDER, ui_file_name)  # get full path
    if not os.path.exists(ui_file_path):
        sys.stdout.write("UI FILE NOT FOUND: {}\n".format(ui_file_path))
        return None

    ui_file = QtCore.QFile(ui_file_path)
    ui_file.open(QtCore.QFile.ReadOnly)
    loader = QtUiTools.QUiLoader()
    window = loader.load(ui_file)
    ui_file.close()
    return window


def create_qicon(icon_path):
    icon_path = icon_path.replace("\\", "/")
    if icon_path.startswith(":"):
        return QtGui.QIcon(icon_path)

    if "/" not in icon_path:
        icon_path = os.path.join(ICON_FOLDER, icon_path + ".png")  # find in icons folder if not full path

    if not os.path.exists(icon_path):
        return

    return QtGui.QIcon(icon_path)


class CoreToolWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=get_app_window()):
        super(CoreToolWindow, self).__init__(parent)

        self.ui = None
        self.setWindowTitle(self.__class__.__name__)

    def main(self, *args, **kwargs):
        self.show()

    #########################################################
    # convenience functions to make a simple button layout

    def ensure_main_layout(self):
        if self.ui is None:
            main_widget = QtWidgets.QWidget()
            main_layout = QtWidgets.QVBoxLayout()
            main_widget.setLayout(main_layout)
            self.ui = main_widget
            self.setCentralWidget(main_widget)

    def add_button(self, text, command, clicked_args=None):
        self.ensure_main_layout()

        main_layout = self.ui.layout()

        btn = QtWidgets.QPushButton(text)
        btn.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        main_layout.addWidget(btn)

        if clicked_args:
            btn.clicked.connect(partial(command, *clicked_args))
        else:
            btn.clicked.connect(command)


class WindowCache:
    window_instances = {}


if active_dcc_is_maya:

    from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
    from maya import OpenMayaUI as omui
    from maya import cmds


    class ToolWindow(MayaQWidgetDockableMixin, CoreToolWindow):
        def __init__(self, parent=None):
            if parent is None:
                parent = get_app_window()
            super(ToolWindow, self).__init__(parent=parent)
            self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

            class_name = self.__class__.__name__
            self.setObjectName(class_name)

        def main(self, restore=False, reload=False):
            object_name = self.objectName()

            if reload:
                WindowCache.window_instances.pop(object_name, None)

                workspace_control_name = object_name + "WorkspaceControl"
                if cmds.workspaceControl(workspace_control_name, q=True, exists=True):
                    cmds.workspaceControl(workspace_control_name, e=True, close=True)
                    cmds.deleteUI(workspace_control_name, control=True)

            if restore:
                restored_control = omui.MQtUtil.getCurrentParent()

            launch_ui_script = "import {module}; {module}.{class_name}().main(restore=True)".format(
                module=self.__class__.__module__,
                class_name=self.__class__.__name__
            )

            window_instance = WindowCache.window_instances.get(object_name)
            if not window_instance:
                window_instance = self
                WindowCache.window_instances[object_name] = window_instance

            if restore:
                mixin_ptr = omui.MQtUtil.findControl(window_instance.objectName())
                omui.MQtUtil.addWidgetToMayaLayout(long(mixin_ptr), long(restored_control))
            else:
                window_instance.show(dockable=True, height=600, width=480, uiScript=launch_ui_script)

            return window_instance

        def show_ui(self, *args, **kwargs):
            """EXISTING WORKSPACES SAFETY - redirect calls from users who already have this window in their workspace"""
            return self.main(*args, **kwargs)

else:
    ToolWindow = CoreToolWindow


def build_menu_from_action_list(actions, menu=None, is_sub_menu=False, extra_trigger=None):
    if not menu:
        menu = QtWidgets.QMenu()

    for action in actions:
        if action == "-":
            menu.addSeparator()
            continue

        for action_title, action_command in action.items():
            if action_title == "RADIO_SETTING":
                # Create RadioButtons for QSettings object
                settings_obj = action_command.get("settings")  # type: QtCore.QSettings
                settings_key = action_command.get("settings_key")  # type: str
                choices = action_command.get("choices")  # type: list
                default_choice = action_command.get("default")  # type: str

                # Has choice been defined in settings?
                item_to_check = settings_obj.value(settings_key)

                # If not, read from default option argument
                if not item_to_check:
                    item_to_check = default_choice

                grp = QtWidgets.QActionGroup(menu)
                for choice_key in choices:
                    action = QtWidgets.QAction(choice_key, menu)
                    action.setCheckable(True)

                    if choice_key == item_to_check:
                        action.setChecked(True)

                    action.triggered.connect(functools.partial(set_settings_value,
                                                               settings_obj,
                                                               settings_key,
                                                               choice_key))
                    if extra_trigger:
                        action.triggered.connect(extra_trigger)
                    menu.addAction(action)
                    grp.addAction(action)

                grp.setExclusive(True)
                continue

            # recursive
            if isinstance(action_command, list):
                sub_menu = menu.addMenu(action_title)
                build_menu_from_action_list(
                    action_command,
                    menu=sub_menu,
                    is_sub_menu=True,
                    extra_trigger=extra_trigger,
                )
                continue

            atn = menu.addAction(action_title)
            atn.triggered.connect(action_command)
            if extra_trigger:
                atn.triggered.connect(extra_trigger)

    if not is_sub_menu:
        cursor = QtGui.QCursor()
        menu.exec_(cursor.pos())

    return menu


def set_settings_value(settings_obj, key, value, post_set_command=None):
    settings_obj.setValue(key, value)
    if post_set_command:
        post_set_command()


def open_color_picker(current_color=None, color_signal=None):
    picker = QtWidgets.QColorDialog(parent=get_app_window())

    if current_color:
        if isinstance(current_color, (list, tuple)):
            color = QtGui.QColor()
            color.setRgb(*current_color)
        else:
            color = current_color
        picker.setCurrentColor(color)

    if color_signal:
        picker.currentColorChanged.connect(color_signal)

    if picker.exec_():
        return picker.currentColor()


def set_combo_index_via_text(cb, text):
    index = cb.findText(text, QtCore.Qt.MatchExactly)
    if index != -1:
        cb.setCurrentIndex(index)


class ScaledContentPushButton(QtWidgets.QPushButton):
    ###############################################################################
    # overloads
    def __init__(self, *args, **kwargs):
        super(ScaledContentPushButton, self).__init__(*args, **kwargs)
        self.max_icon_size = 0
        self.text_padding_multiplier = 0.8
        self.icon_padding_multiplier = 0.5

    def setIcon(self, q_icon):
        biggest_size = q_icon.availableSizes()[-1]  # type: QtCore.QSize
        self.max_icon_size = min(biggest_size.width(), biggest_size.height())
        super(ScaledContentPushButton, self).setIcon(q_icon)

    def resizeEvent(self, event):
        self.update_content_size()
        super(ScaledContentPushButton, self).resizeEvent(event)

    ###############################################################################
    def update_content_size(self):
        self.update_icon_size()
        self.update_button_text_size()

    def update_icon_size(self):
        min_size = min(self.size().width(), self.size().height())
        icon_size = QtCore.QSize(
            min_size * self.icon_padding_multiplier,
            min_size * self.icon_padding_multiplier,
        )
        self.setIconSize(icon_size)

    def update_button_text_size(self):
        # reset font size so .fontMetrics() make sense
        font = QtGui.QFont('Serif', 8, QtGui.QFont.Normal)
        self.setFont(font)

        # resize text to scale with widget
        size = self.size()
        icon_width = 0
        if self.icon():
            icon_width = min(self.iconSize().width(), self.max_icon_size)

        h_factor = float(size.height()) / self.fontMetrics().height()
        w_factor = float(size.width()) / max((self.fontMetrics().width(self.text()) + icon_width), 0.0001)

        # the smaller value determines max text size
        factor = min(h_factor, w_factor) * self.text_padding_multiplier

        # clamp output to a min size
        final_point_size = max(font.pointSizeF() * factor, 8.0)
        font.setPointSizeF(final_point_size)

        self.setFont(font)
