import sys
import random
from script_panel.ui.ui_utils import QtCore, QtWidgets


class CustomizedLayout(QtWidgets.QListWidget):
    def __init__(self):
        super(CustomizedLayout, self).__init__()

        self.setFlow(self.LeftToRight)
        self.setResizeMode(self.Adjust)
        self.setGridSize(QtCore.QSize(256, 256))
        self.setViewMode(self.IconMode)
        self.setSpacing(0)


class CommandButton(QtWidgets.QPushButton):
    def __init__(self, *args, **kwargs):
        super(CommandButton, self).__init__(*args, **kwargs)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )


class FlowLayout(QtWidgets.QLayout):
    """Custom layout that mimics the behaviour of a flow layout"""

    def __init__(self, parent=None, margin=0, spacing=-1):
        """Create a new FlowLayout instance.
        This layout will reorder the items automatically.
        @param parent (QWidget)
        @param margin (int)
        @param spacing (int)"""
        super(FlowLayout, self).__init__(parent)
        # Set margin and spacing
        if parent is not None: self.setMargin(margin)
        self.setSpacing(spacing)

        self.itemList = []

    def __del__(self):
        """Delete all the items in this layout"""
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        """Add an item at the end of the layout.
        This is automatically called when you do addWidget()
        item (QWidgetItem)"""
        self.itemList.append(item)

    def count(self):
        """Get the number of items in the this layout
        @return (int)"""
        return len(self.itemList)

    def itemAt(self, index):
        """Get the item at the given index
        @param index (int)
        @return (QWidgetItem)"""
        if index >= 0 and index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        """Remove an item at the given index
        @param index (int)
        @return (None)"""
        if index >= 0 and index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def insertWidget(self, index, widget):
        """Insert a widget at a given index
        @param index (int)
        @param widget (QWidget)"""
        item = QtWidgets.QWidgetItem(widget)
        self.itemList.insert(index, item)

    def expandingDirections(self):
        """This layout grows only in the horizontal dimension"""
        return QtCore.Qt.Horizontal

    def hasHeightForWidth(self):
        """If this layout's preferred height depends on its width
        @return (boolean) Always True"""
        return True

    def heightForWidth(self, width):
        """Get the preferred height a layout item with the given width
        @param width (int)"""
        height = self.doLayout(QtCore.QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        """Set the geometry of this layout
        @param rect (QRect)"""
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        """Get the preferred size of this layout
        @return (QSize) The minimum size"""
        return self.minimumSize()

    def minimumSize(self):
        """Get the minimum size of this layout
        @return (QSize)"""
        # Calculate the size
        size = QtCore.QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        # Add the margins
        size += QtCore.QSize(2 * self.margin(), 2 * self.margin())
        return size

    def doLayout(self, rect, testOnly):
        """Layout all the items
        @param rect (QRect) Rect where in the items have to be laid out
        @param testOnly (boolean) Do the actual layout"""
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for item in self.itemList:
            spaceX = self.spacing()
            spaceY = self.spacing()
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()


class ExampleWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(ExampleWindow, self).__init__(*args, **kwargs)

        # main_widget = CustomizedLayout()
        # self.setCentralWidget(main_widget)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        main_widget = QtWidgets.QWidget()
        flow_layout = FlowLayout(main_widget)

        ratios = [
            [100, 100],
            [100, 100],
            [200, 100],
            [200, 200],
        ]

        for i in range(50):
            btn = CommandButton("BTN_{}".format(i))
            btn.setFixedSize(*random.choice(ratios))
            flow_layout.addWidget(btn)
        scroll_area.setWidget(main_widget)
        self.setCentralWidget(scroll_area)

        # for i in range(20):
        #     btn = CommandButton()
        #     btn.setText("BTN_{}".format(i))

            # list_widget_item = QtWidgets.QListWidgetItem()
            # list_widget_item.setSizeHint(btn.sizeHint())
            # main_widget.addItem(list_widget_item)
            # main_widget.setItemWidget(list_widget_item, btn)


if __name__ == '__main__':
    standalone_app = None
    if not QtWidgets.QApplication.instance():
        standalone_app = QtWidgets.QApplication(sys.argv)

    win = ExampleWindow()
    win.show()
    win.resize(1000, 1000)

    if standalone_app:
        sys.exit(standalone_app.exec_())
