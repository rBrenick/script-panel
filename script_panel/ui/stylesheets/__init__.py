import os

try:  # Qt6 / PySide6 (Maya 2025 and newer)
    from PySide6 import QtWidgets
except ImportError:  # Qt5 / PySide2 (Maya 2024 and older)
    from PySide2 import QtWidgets


def apply_standalone_stylesheet():
    app = QtWidgets.QApplication.instance()

    with open(get_main_stylesheet_path()) as fp:
        app.setStyleSheet(fp.read())


def get_main_stylesheet_path():
    return os.path.join(os.path.dirname(__file__), "Combinear.qss")
