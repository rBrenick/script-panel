import math
import sys

from script_panel.ui.ui_utils import QtCore, QtGui, QtWidgets, BaseSettings


# class ControlView(QtWidgets.QGraphicsView):
#     """
#     Base class to create the control view
#     """
#
#     def __init__(self, scene, parent):
#         """
#         @param scene: QGraphicsScene that defines the scene we want to visualize
#         @param parent: QWidget parent
#         """
#         super(ControlView, self).__init__(parent)
#
#         self.setObjectName('ControlView')
#         self.setScene(scene)
#         self.setRenderHint(QtGui.QPainter.Antialiasing)
#         self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
#         self.setViewportUpdateMode(QtWidgets.QGraphicsView.SmartViewportUpdate)
#
#         self.setAcceptDrops(True)
#         self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
#
#         self.dragOver = False
#
#     def dragMoveEvent(self, event):
#         pass
#
#     def dragEnterEvent(self, event):
#         if event.mimeData().hasText():
#             event.setAccepted(True)
#             self.dragOver = True
#             self.update()
#
#     def dropEvent(self, event):
#         pos = event.pos()
#         event.acceptProposedAction()

class CustomScene(QtWidgets.QGraphicsScene):
    def __init__(self, *args, **kwargs):
        super(CustomScene, self).__init__(*args, **kwargs)
        self._background_color = QtGui.QColor(50, 50, 50)
        self._background_color_light = QtGui.QColor(100, 100, 100)

        self.grid_size = 80
        self.grid_pen = QtGui.QPen(self._background_color_light)
        self.grid_pen.setWidth(5)

        self.setBackgroundBrush(self._background_color)

    def drawBackground(self, painter, rect):
        super(CustomScene, self).drawBackground(painter, rect)
        left = int(math.floor(rect.left()))
        right = int(math.ceil(rect.right()))
        top = int(math.floor(rect.top()))
        bottom = int(math.ceil(rect.bottom()))

        first_left = left - (left % self.grid_size)
        first_top = top - (top % self.grid_size)

        grid_lines = []
        for i in range(first_left, right, self.grid_size):
            grid_lines.append(QtCore.QLine(i, top, i, bottom))

        for i in range(first_top, bottom, self.grid_size):
            grid_lines.append(QtCore.QLine(left, i, right, i))

        painter.setPen(self.grid_pen)
        painter.drawLines(grid_lines)


class GraphicsProxyWidget(QtWidgets.QGraphicsProxyWidget):
    def __init__(self, *args, **kwargs):
        super(GraphicsProxyWidget, self).__init__(*args, **kwargs)


class GraphicsRectItem(QtWidgets.QGraphicsRectItem):
    def __init__(self, id, *args, **kwargs):
        super(GraphicsRectItem, self).__init__(*args, **kwargs)

        self.id = id
        self.header_height = 40
        self._being_resized = False
        self.widget = None

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setBrush(QtCore.Qt.darkGray)

        self.proxy_widget = GraphicsProxyWidget(self)
        self.text_item = QtWidgets.QGraphicsTextItem(self)
        self.text_item.setPlainText(id)

    def set_widget_geometry(self):
        self.widget.setGeometry(0, 0, self.rect().width(), self.rect().height() - self.header_height - 20)
        self.proxy_widget.setPos(0, self.header_height)

    def wrap_widget(self, widget):
        self.widget = widget
        self.proxy_widget.setWidget(widget)
        self.set_widget_geometry()

    def pos_within_resize_handle(self, pos):
        if pos.x() > self.rect().width() - 30:
            if pos.y() > self.rect().height() - 30:
                return True
        return False

    def mousePressEvent(self, event):
        """
        :type event: QtWidgets.QGraphicsSceneMouseEvent
        """
        if event.type() == QtCore.QEvent.Type.GraphicsSceneMousePress:
            if self.pos_within_resize_handle(event.pos()):
                self._being_resized = True
        return super(GraphicsRectItem, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._being_resized = False
        super(GraphicsRectItem, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """
        :type event: QtWidgets.QGraphicsSceneMouseEvent
        """
        if self._being_resized:
            snapped_pos = self.snap_pos_to_grid(event.pos())
            self.set_size([snapped_pos.x(), snapped_pos.y()])
            return

        return super(GraphicsRectItem, self).mouseMoveEvent(event)

    def set_size(self, size):
        rect = self.rect()
        rect.setWidth(size[0])
        rect.setHeight(size[1])
        self.setRect(rect)
        self.set_widget_geometry()

    def snap_pos_to_grid(self, pos):
        """
        :type pos:  QtCore.QPointF
        """
        grid_size = self.scene().grid_size
        pos.setX(round(pos.x() / grid_size) * grid_size)
        pos.setY(round(pos.y() / grid_size) * grid_size)
        return pos

    def itemChange(self, change, value):
        if change == self.ItemPositionChange and self.scene():
            value = self.snap_pos_to_grid(value)

        return super(GraphicsRectItem, self).itemChange(change, value)


class CommandPanelSettings(BaseSettings):
    def __init__(self, *args, **kwargs):
        super(CommandPanelSettings, self).__init__(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            "command_panel", "command_panel_settings",
            *args, **kwargs)


class ExampleWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(ExampleWindow, self).__init__(*args, **kwargs)

        self.settings = CommandPanelSettings()

        menu_bar = QtWidgets.QMenuBar()
        layout_menu = menu_bar.addMenu("Layout")
        layout_menu.addAction("Save Layout", self.save_layout)
        layout_menu.addAction("Load Layout", self.load_layout)
        self.setMenuBar(menu_bar)

        self.scene = CustomScene()
        self.scene_items = []

        # set main widget to scene
        main_widget = QtWidgets.QGraphicsView(self)
        main_widget.setScene(self.scene)
        self.setCentralWidget(main_widget)

        self.create_test_items()
        self.load_layout()

    def save_layout(self):
        user_layout = {}
        for scene_item in self.scene_items:  # type: GraphicsRectItem
            user_layout[scene_item.id] = {
                "pos": scene_item.pos(),
                "size": [scene_item.rect().width(), scene_item.rect().height()],
            }

        self.settings.setValue("user_layout", user_layout)

    def load_layout(self):
        user_layout = self.settings.get_value("user_layout", default={})  # type: dict
        for scene_item in self.scene_items:  # type: GraphicsRectItem
            layout_info = user_layout.get(scene_item.id)  # type: dict
            user_pos = layout_info.get("pos")
            if user_pos:
                scene_item.setPos(user_pos)
            user_size = layout_info.get("size")
            if user_size:
                scene_item.set_size(user_size)

    def add_widget(self, id, widget, pos):
        rect_item = GraphicsRectItem(id, 0, 0, self.scene.grid_size * 3, self.scene.grid_size * 3)
        rect_item.id = id
        rect_item.wrap_widget(widget)
        self.scene.addItem(rect_item)
        if pos:
            rect_item.setPos(rect_item.snap_pos_to_grid(QtCore.QPoint(*pos)))
        self.scene_items.append(rect_item)
        return rect_item

    def create_test_items(self):
        for i in range(4):
            btn_text = "Hello_{}".format(i)
            btn = QtWidgets.QPushButton(btn_text)

            self.add_widget(
                id="COMMAND_{:03d}".format(i),
                widget=btn,
                pos=[i * 200, i * 200],
            )

        # rect = self.scene.addRect(20, 20, 60, 60, QtGui.QPen(), QtGui.QBrush(QtCore.Qt.green))
        # rect.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)

    def closeEvent(self, event):
        self.save_layout()
        super(ExampleWindow, self).closeEvent(event)


if __name__ == '__main__':
    standalone_app = None
    if not QtWidgets.QApplication.instance():
        standalone_app = QtWidgets.QApplication(sys.argv)

    win = ExampleWindow()
    win.show()
    win.resize(1000, 1000)

    if standalone_app:
        sys.exit(standalone_app.exec_())
