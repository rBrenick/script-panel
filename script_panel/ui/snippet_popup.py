from . import ui_utils
from .ui_utils import QtCore, QtWidgets, QtGui


class SnippetPopup(QtWidgets.QWidget):
    def __init__(self, focus_widget, snippet_data, focus_text=None, *args, **kwargs):
        super(SnippetPopup, self).__init__(parent=ui_utils.get_app_window(), *args, **kwargs)

        self.focus_widget = focus_widget
        self.focus_text = focus_text
        self.snippet_data = snippet_data

        self.ui = SnippetPopupUI()
        self.setWindowFlags(QtCore.Qt.Popup)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.ui)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

        # fill snippet list
        for snippet_key, snippet_text in snippet_data.items():
            self.ui.snippet_LW.addItem(snippet_key)
        self.ui.snippet_LW.setCurrentRow(0)

        # connect hotkeys
        snippet_shortcut = QtWidgets.QShortcut(
            QtGui.QKeySequence("Return"),
            self,
            self.insert_snippet,
        )
        snippet_shortcut.setContext(QtCore.Qt.ApplicationShortcut)

        # set our focus to the list of snippets
        self.ui.snippet_LW.setFocus()

    def insert_snippet(self):
        snippet_key = self.ui.snippet_LW.selectedItems()[0].text()
        text = self.snippet_data.get(snippet_key, "UNDEFINED")
        if self.focus_text:
            text = text.replace("SP_SELECTED_TEXT", self.focus_text)
        write_text_in_widget(self.focus_widget, text)
        self.close()


class SnippetPopupUI(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(SnippetPopupUI, self).__init__(*args, **kwargs)

        ui_layout = QtWidgets.QVBoxLayout()
        self.snippet_LW = QtWidgets.QListWidget()
        ui_layout.addWidget(self.snippet_LW)
        self.setLayout(ui_layout)


def write_text_in_widget(widget, text):
    if isinstance(widget, QtWidgets.QTextEdit):
        widget.insertPlainText(text)
    elif isinstance(widget, QtWidgets.QLineEdit):
        widget.insert(text)


def is_text_widget(widget):
    return isinstance(widget, (QtWidgets.QTextEdit, QtWidgets.QLineEdit))


def get_selected_text(widget):
    if isinstance(widget, QtWidgets.QTextEdit):
        return widget.textCursor().selectedText()
    elif isinstance(widget, QtWidgets.QLineEdit):
        return widget.selectedText()


def main(snippet_data=None):
    focus_widget = QtWidgets.QApplication.focusWidget()  # type: QtWidgets.QLineEdit
    if not is_text_widget(focus_widget):
        return
    focus_text = get_selected_text(focus_widget)

    # example use case
    if not snippet_data:
        snippet_data = {"First Selected": "pm.selected()[0]"}

    # only one snippet defined, just use that one
    if len(snippet_data.keys()) == 1:
        write_text_in_widget(focus_widget, list(snippet_data.values())[0])
        return

    popup_win = SnippetPopup(focus_widget, snippet_data, focus_text)
    popup_win.show()

    # move to mouse cursor location
    # popup_win.move(QtGui.QCursor().pos())

    # move to text cursor location
    text_cursor_pos = QtCore.QPoint(*focus_widget.cursorRect().getCoords()[:2])
    popup_win.move(focus_widget.mapToGlobal(text_cursor_pos))
