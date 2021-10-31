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

class PaletteScene(QtWidgets.QGraphicsScene):
    def __init__(self, *args, **kwargs):
        super(PaletteScene, self).__init__(*args, **kwargs)
        self._background_color = QtGui.QColor(50, 50, 50)
        self._background_color_light = QtGui.QColor(100, 100, 100)

        self.grid_size = 40
        self.grid_pen = QtGui.QPen(self._background_color_light)
        self.grid_pen.setWidth(3)

        self.setBackgroundBrush(self._background_color)

    def drawBackground(self, painter, rect):
        super(PaletteScene, self).drawBackground(painter, rect)
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


class PaletteGraphicsView(QtWidgets.QGraphicsView):
    item_dropped = QtCore.Signal(object)

    def __init__(self, scene, *args, **kwargs):
        super(PaletteGraphicsView, self).__init__(*args, **kwargs)
        self.setScene(scene)

        self._is_dragging = False

        self.zoom = 10
        self.zoom_in_factor = 1.25
        self.zoom_step = 1
        self.zoom_range = [0, 10]

        self.setAcceptDrops(True)
        self.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.setTransformationAnchor(self.AnchorUnderMouse)
        self.setRenderHints(
            QtGui.QPainter.Antialiasing
            | QtGui.QPainter.HighQualityAntialiasing
            | QtGui.QPainter.SmoothPixmapTransform
        )
        self.setViewportUpdateMode(self.FullViewportUpdate)

    def keyPressEvent(self, event):
        if not event.isAutoRepeat() and event.key() == QtCore.Qt.Key_Space:
            self.toggle_drag_mode(True)
        super(PaletteGraphicsView, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if not event.isAutoRepeat() and event.key() == QtCore.Qt.Key_Space:
            self.toggle_drag_mode(False)
        super(PaletteGraphicsView, self).keyReleaseEvent(event)

    def wheelEvent(self, event):
        """
        :type event: QtGui.QWheelEvent
        """
        if event.modifiers() != QtCore.Qt.ControlModifier:
            return super(PaletteGraphicsView, self).wheelEvent(event)

        zoom_out_factor = 1.0 / self.zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = self.zoom_in_factor
            self.zoom += self.zoom_step
        else:
            zoom_factor = zoom_out_factor
            self.zoom -= self.zoom_step

        self.scale(zoom_factor, zoom_factor)

    def toggle_drag_mode(self, state=False):
        if state:
            self.setDragMode(self.ScrollHandDrag)
        else:
            self.setDragMode(self.DragMode.NoDrag)

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        self.item_dropped.emit(event)


class ResizeHandleRect(QtWidgets.QGraphicsRectItem):
    def __init__(self, *args, **kwargs):
        super(ResizeHandleRect, self).__init__(*args, **kwargs)
        self._being_resized = False

    def mousePressEvent(self, event):
        """
        :type event: QtWidgets.QGraphicsSceneMouseEvent
        """
        if event.type() == QtCore.QEvent.Type.GraphicsSceneMousePress:
            self._being_resized = True

    def mouseReleaseEvent(self, event):
        self._being_resized = False
        super(ResizeHandleRect, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """
        :type event: QtWidgets.QGraphicsSceneMouseEvent
        """
        if self._being_resized:
            parent_item = self.parentItem()  # type: PaletteRectItem
            handle_pos = event.scenePos()
            parent_pos = parent_item.scenePos()
            resized_x = handle_pos.x() - parent_pos.x()
            resized_y = handle_pos.y() - parent_pos.y()

            parent_item.set_size([resized_x, resized_y], snap_to_grid=True)

        return super(ResizeHandleRect, self).mouseMoveEvent(event)


class PaletteRectItem(QtWidgets.QGraphicsRectItem):
    def __init__(self, id, *args, **kwargs):
        super(PaletteRectItem, self).__init__(*args, **kwargs)

        self.id = id
        self.header_height = 40
        self.resize_handle_size = 30
        self._being_resized = False
        self._wrapped_widget = None

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setBrush(QtCore.Qt.darkGray)

        self.proxy_widget = QtWidgets.QGraphicsProxyWidget(self)
        self.resize_button = ResizeHandleRect(0, 0, self.resize_handle_size, self.resize_handle_size)
        self.resize_button.setParentItem(self)
        self.resize_button.setBrush(QtCore.Qt.lightGray)
        self.text_item = QtWidgets.QGraphicsTextItem(self)
        self.text_item.setPlainText(id)

    def set_widget_geometry(self):
        box_width, box_height = self.rect().width(), self.rect().height()
        self._wrapped_widget.setGeometry(0, 0, box_width, box_height - self.header_height)
        self.proxy_widget.setPos(0, self.header_height)
        self.resize_button.setPos(box_width - self.resize_handle_size, box_height - self.resize_handle_size)

    def wrap_widget(self, widget):
        self._wrapped_widget = widget
        self.proxy_widget.setWidget(widget)
        self.set_widget_geometry()

    def set_size(self, size, snap_to_grid=False):
        if snap_to_grid:
            resized_pos = QtCore.QPoint(*size)
            self.snap_pos_to_grid(resized_pos)
            size = resized_pos.toTuple()

        rect = self.rect()
        rect.setWidth(size[0])
        rect.setHeight(size[1])
        self.setRect(rect)
        self.set_widget_geometry()

    def set_pos(self, pos):
        self.setPos(*pos)  # will automatically trigger itemChange

    def snap_pos_to_grid(self, pos):
        """
        :type pos:  QtCore.QPointF
        """
        grid_size = self.scene().grid_size
        snapped_x = max(round(pos.x() / grid_size) * grid_size, 0)
        snapped_y = max(round(pos.y() / grid_size) * grid_size, 0)
        pos.setX(snapped_x)
        pos.setY(snapped_y)
        return pos

    def itemChange(self, change, value):
        if change == self.ItemPositionChange and self.scene():
            value = self.snap_pos_to_grid(value)

        return super(PaletteRectItem, self).itemChange(change, value)


class CommandPaletteWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(CommandPaletteWidget, self).__init__(*args, **kwargs)

        self._scene_items = []
        self.scene_widgets = []

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.scene = PaletteScene()
        self.graphics_view = PaletteGraphicsView(self.scene, self)

        # set ui
        self.main_layout.addWidget(self.graphics_view)
        self.setLayout(self.main_layout)

    def add_widget(self, id, widget, pos=None):
        rect_item = PaletteRectItem(id, 0, 0, self.scene.grid_size * 3, self.scene.grid_size * 3)
        rect_item.wrap_widget(widget)
        self.scene.addItem(rect_item)
        if pos:
            rect_item.setPos(rect_item.snap_pos_to_grid(QtCore.QPoint(*pos)))
        self._scene_items.append(rect_item)
        self.scene_widgets.append(widget)
        return rect_item

    def get_scene_layout(self):
        user_layout = {}
        for scene_item in self._scene_items:  # type: PaletteRectItem
            user_layout[scene_item.id] = {
                "pos": scene_item.pos().toTuple(),
                "size": [scene_item.rect().width(), scene_item.rect().height()],
            }
        return user_layout

    def set_scene_layout(self, user_layout):
        for scene_item in self._scene_items:  # type: PaletteRectItem
            layout_info = user_layout.get(scene_item.id)  # type: dict
            if not layout_info:
                continue

            user_pos = layout_info.get("pos")
            if user_pos:
                scene_item.set_pos(user_pos)

            user_size = layout_info.get("size")
            if user_size:
                scene_item.set_size(user_size)

    def clear(self):
        for item in self._scene_items:
            self.scene.removeItem(item)
        self._scene_items = []
        self.scene_widgets = []

    def get_mouse_pos(self):
        scene_cursor_pos = self.graphics_view.mapFromGlobal(self.graphics_view.cursor().pos())
        return scene_cursor_pos.toTuple()


class CommandPanelSettings(BaseSettings):
    def __init__(self, *args, **kwargs):
        super(CommandPanelSettings, self).__init__(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            "command_panel", "command_panel_settings",
            *args, **kwargs)


class CommandPaletteSystem(object):
    def __init__(self):
        pass

    def get_palettes(self):
        return ["Test"]


class ExampleWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(ExampleWindow, self).__init__(*args, **kwargs)

        self.settings = CommandPanelSettings()

        # menu_bar = QtWidgets.QMenuBar()
        # layout_menu = menu_bar.addMenu("Layout")
        # layout_menu.addAction("Save Layout", self.save_layout)
        # layout_menu.addAction("Load Layout", self.load_layout)
        # self.setMenuBar(menu_bar)

        self.command_palette_system = CommandPaletteSystem()
        self.command_palette_widget = CommandPaletteWidget()

        self.scene_chooser = QtWidgets.QComboBox()
        self.scene_chooser.addItems(self.command_palette_system.get_palettes())
        self.command_palette_widget.main_layout.insertWidget(0, self.scene_chooser)

        self.setCentralWidget(self.command_palette_widget)

        self.create_test_items()
        self.load_layout()

    def save_layout(self):
        self.settings.setValue("user_layout", self.command_palette_widget.get_scene_layout())

    def load_layout(self):
        user_layout = self.settings.get_value("user_layout", default={})  # type: dict
        self.command_palette_widget.set_scene_layout(user_layout)

    def create_test_items(self):
        for i in range(4):
            btn_text = "Hello_{}".format(i)
            btn = QtWidgets.QPushButton(btn_text)
            btn.clicked.connect(test_func)

            self.command_palette_widget.add_widget(
                id="COMMAND_{:03d}".format(i),
                widget=btn,
                pos=[i * 200, i * 200],
            )

    def closeEvent(self, event):
        self.save_layout()
        super(ExampleWindow, self).closeEvent(event)


def test_func():
    print("a_random_string")


if __name__ == '__main__':
    standalone_app = None
    if not QtWidgets.QApplication.instance():
        standalone_app = QtWidgets.QApplication(sys.argv)

    win = ExampleWindow()
    win.show()
    win.resize(1000, 1000)

    if standalone_app:
        sys.exit(standalone_app.exec_())
