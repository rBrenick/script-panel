
# Standard
import os
import sys

# Not even going to pretend to have Maya 2016 support
from PySide2 import QtCore
from PySide2 import QtWidgets
from PySide2 import QtGui
from shiboken2 import wrapInstance
from PySide2 import QtUiTools


UI_FILES_FOLDER = os.path.dirname(__file__)
ICON_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons")
"""
QT UTILS BEGIN
"""

def get_app_window():
    top_window = None
    try:
        from maya import OpenMayaUI as omui
        maya_main_window_ptr = omui.MQtUtil().mainWindow()
        top_window = wrapInstance(long(maya_main_window_ptr), QtWidgets.QMainWindow)
    except ImportError as e:
        pass
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
    ui_file_path = os.path.join(UI_FILES_FOLDER, ui_file_name) # get full path
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
    if "/" not in icon_path:
        icon_path = os.path.join(ICON_FOLDER, icon_path+".png") # find in icons folder if not full path
        if not os.path.exists(icon_path):
            return 
    
    return QtGui.QIcon(icon_path)

    
class BaseWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=get_app_window(), ui_file_name=None):
        delete_window(self)
        super(BaseWindow, self).__init__(parent)
        
        self.ui = None
        if ui_file_name:
            self.load_ui(ui_file_name)
        
        self.set_tool_icon("script_panel_icon")
        
        self.show()
    
    def set_tool_icon(self, icon_name):
        icon = create_qicon(icon_name)
        if icon:
            self.setWindowIcon(icon)
    
    def load_ui(self, ui_file_name):
        self.ui = load_ui_file(ui_file_name)
        self.setGeometry(self.ui.rect())
        self.setWindowTitle(self.ui.property("windowTitle"))
        self.setCentralWidget(self.ui)
        
        parent_window = self.parent()
        if not parent_window:
            return
        
        dcc_window_center = parent_window.mapToGlobal(parent_window.rect().center())
        window_offset_x = dcc_window_center.x() - self.geometry().width()/2
        window_offset_y = dcc_window_center.y() - self.geometry().height()/2
        self.move(window_offset_x, window_offset_y) # move to dcc screen center


def build_menu_from_action_list(actions, menu=None, is_sub_menu=False):
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
                on_trigger_command = action_command.get("on_trigger_command")  # function to trigger after setting value

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
                                                               choice_key,
                                                               on_trigger_command))
                    menu.addAction(action)
                    grp.addAction(action)

                grp.setExclusive(True)
                continue

            if isinstance(action_command, list):
                sub_menu = menu.addMenu(action_title)
                build_menu_from_action_list(action_command, menu=sub_menu, is_sub_menu=True)
                continue

            atn = menu.addAction(action_title)
            atn.triggered.connect(action_command)

    if not is_sub_menu:
        cursor = QtGui.QCursor()
        menu.exec_(cursor.pos())

    return menu

"""
QT UTILS END
"""



