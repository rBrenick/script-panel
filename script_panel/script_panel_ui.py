__author__ = "Richard Brenick"

# Standard
import os
import sys

# UI
from script_panel.ui import ui_utils
from script_panel.ui.ui_utils import QtCore, QtWidgets, QtGui

# DCC
# import pymel.core as pm

# Tool
from script_panel import script_panel_utils as spu

class ScriptPanelWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(ScriptPanelWidget, self).__init__(*args, **kwargs)
        
        self.ui = ScriptPanelUI()
        
        self.model = QtGui.QStandardItemModel()
        self.ui.scripts_LV.setModel(self.model)
        
        self.build_model()

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(ScriptWidget())
        main_layout.addWidget(self.ui)
        self.setLayout(main_layout)
        
    def build_model(self):
        for script_path in ["ScriptName.py", "ScriptName2.py", "ScriptName3.py"]:
            item = QtGui.QStandardItem()
            self.model.appendRow(item)
            
            # build custom widget for the script
            item_widget = ScriptWidget(script_path)
            qindex_child = item.index()
            self.ui.scripts_LV.setIndexWidget(qindex_child, item_widget)


class ScriptWidget(QtWidgets.QWidget):
    def __init__(self, script_path="ExampleScript.py", *args, **kwargs):
        super(ScriptWidget, self).__init__(*args, **kwargs)
        
        main_layout = QtWidgets.QHBoxLayout()
        btn = QtWidgets.QPushButton(script_path)
        main_layout.addWidget(btn)
        self.setLayout(main_layout)


###################################
# General UI

class ScriptPanelWindow(ui_utils.BaseWindow):
    def __init__(self, *args, **kwargs):
        super(ScriptPanelWindow, self).__init__(*args, **kwargs)
        
        self.main_widget = ScriptPanelWidget()
        self.setCentralWidget(self.main_widget)


class ScriptPanelUI(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(ScriptPanelUI, self).__init__(*args, **kwargs)
        
        main_layout = QtWidgets.QVBoxLayout()
        
        self.search_LE = QtWidgets.QLineEdit()
        self.search_LE.setClearButtonEnabled(True)
        self.search_LE.setPlaceholderText("Search...")
        
        self.scripts_LV = QtWidgets.QListView()
        self.scripts_LV.setWindowTitle('Example List')
        
        main_layout.addWidget(self.search_LE)
        main_layout.addWidget(self.scripts_LV)
        self.setLayout(main_layout)
        


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
    
    




