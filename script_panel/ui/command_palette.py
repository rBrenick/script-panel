import math
import sys

from script_panel.ui import ui_utils
from script_panel.ui.ui_utils import QtCore, QtGui, QtWidgets, BaseSettings


class LocalConstants:
    default_grid_size = 20
    default_grid_color = QtGui.QColor(50, 50, 50)
    header_height = 15


lk = LocalConstants


class PaletteScene(QtWidgets.QGraphicsScene):
    def __init__(self, *args, **kwargs):
        super(PaletteScene, self).__init__(*args, **kwargs)
        self._background_color = lk.default_grid_color
        self._background_color_light = QtGui.QColor(100, 100, 100)

        self.grid_size = lk.default_grid_size
        self.grid_pen = QtGui.QPen(self._background_color_light)
        self.grid_pen.setWidth(1)

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
        self.setDragMode(self.RubberBandDrag)

    def keyPressEvent(self, event):
        if not event.isAutoRepeat() and event.key() == QtCore.Qt.Key_Space:
            self.toggle_drag_mode(True)
        super(PaletteGraphicsView, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if not event.isAutoRepeat() and event.key() == QtCore.Qt.Key_Space:
            self.toggle_drag_mode(False)
        super(PaletteGraphicsView, self).keyReleaseEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            if self.select_item_under_cursor():
                super(PaletteGraphicsView, self).mousePressEvent(event)

        elif event.button() == QtCore.Qt.MiddleButton:
            release_event = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease, event.localPos(), event.screenPos(),
                                              QtCore.Qt.LeftButton, QtCore.Qt.NoButton, event.modifiers())
            super(PaletteGraphicsView, self).mouseReleaseEvent(release_event)
            self.toggle_drag_mode(True)
            fake_event = QtGui.QMouseEvent(event.type(), event.localPos(), event.screenPos(),
                                           QtCore.Qt.LeftButton, event.buttons() | QtCore.Qt.LeftButton,
                                           event.modifiers())
            super(PaletteGraphicsView, self).mousePressEvent(fake_event)
        else:
            event.accept()
            super(PaletteGraphicsView, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MiddleButton:
            fake_event = QtGui.QMouseEvent(event.type(), event.localPos(), event.screenPos(),
                                           QtCore.Qt.LeftButton, event.buttons() & QtCore.Qt.LeftButton,
                                           event.modifiers())
            super(PaletteGraphicsView, self).mouseReleaseEvent(fake_event)
            self.toggle_drag_mode(False)
        else:
            event.accept()
            super(PaletteGraphicsView, self).mouseReleaseEvent(event)

    def select_item_under_cursor(self):
        item_under_cursor = self.get_item_under_cursor()
        if item_under_cursor:
            self.scene().clearSelection()
            item_under_cursor.setSelected(True)
            return True

    def get_cursor_scene_pos(self):
        graphics_view_pos = self.mapFromGlobal(QtGui.QCursor().pos())
        scene_pos = self.mapToScene(graphics_view_pos)
        return scene_pos

    def get_item_under_cursor(self):
        scene_pos = self.get_cursor_scene_pos()
        item_under_cursor = self.scene().itemAt(scene_pos, QtGui.QTransform())
        if not item_under_cursor:
            return

        # if child item_selected, go up to parent rect item
        if item_under_cursor.parentItem():
            item_under_cursor = item_under_cursor.parentItem()  # type: PaletteRectItem

        return item_under_cursor

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
            self.setDragMode(self.RubberBandDrag)

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        self.item_dropped.emit(event)


class ResizeHandle(QtWidgets.QGraphicsPolygonItem):
    def __init__(self, *args, **kwargs):
        super(ResizeHandle, self).__init__(*args, **kwargs)
        self._being_resized = False
        self._being_moved = False

        self.handle_size = lk.default_grid_size
        self.update_size(self.handle_size)

        self.setAcceptHoverEvents(True)
        self.default_cursor = QtCore.Qt.SizeFDiagCursor
        self.setCursor(self.default_cursor)

    def update_size(self, new_size):
        self.handle_size = new_size
        handle_points = [[new_size, 0], [0, new_size], [new_size, new_size]]
        self.myPolygon = QtGui.QPolygonF([QtCore.QPointF(v1, v2) for v1, v2 in handle_points])
        self.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0)))
        self.setPolygon(self.myPolygon)

    def mousePressEvent(self, event):
        """
        :type event: QtWidgets.QGraphicsSceneMouseEvent
        """
        if event.type() == QtCore.QEvent.Type.GraphicsSceneMousePress:
            if event.modifiers() == QtCore.Qt.ControlModifier:
                self._being_moved = True
            else:
                self._being_resized = True

    def mouseReleaseEvent(self, event):
        self._being_moved = False
        self._being_resized = False
        super(ResizeHandle, self).mouseReleaseEvent(event)

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

        if self._being_moved:
            parent_item = self.parentItem()  # type: PaletteRectItem
            handle_pos = event.scenePos()
            relative_x = handle_pos.x() - parent_item.rect().width()
            relative_y = handle_pos.y() - parent_item.rect().height()
            parent_item.set_pos([relative_x, relative_y])

        return super(ResizeHandle, self).mouseMoveEvent(event)

    def hoverEnterEvent(self, event):
        self.update_cursor_shape(event)
        super(ResizeHandle, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.update_cursor_shape(event)
        super(ResizeHandle, self).hoverLeaveEvent(event)

    def hoverMoveEvent(self, event):
        self.update_cursor_shape(event)
        super(ResizeHandle, self).hoverMoveEvent(event)

    def update_cursor_shape(self, event):
        if event.modifiers() == QtCore.Qt.ControlModifier:
            self.setCursor(QtCore.Qt.SizeAllCursor)
        else:
            self.setCursor(self.default_cursor)


class PaletteRectItem(QtWidgets.QGraphicsRectItem):
    def __init__(self, internal_id, display_name, *args, **kwargs):
        super(PaletteRectItem, self).__init__(*args, **kwargs)

        self.internal_id = internal_id
        self.header_height = lk.header_height
        self.show_header = True
        self.resize_handle_size = lk.default_grid_size
        self._being_resized = False
        self.wrapped_widget = None
        self.is_selected = False

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setBrush(QtCore.Qt.darkGray)
        self.setCursor(QtCore.Qt.SizeAllCursor)

        self.proxy_widget = QtWidgets.QGraphicsProxyWidget(self)
        self.resize_button = ResizeHandle()
        self.resize_button.setParentItem(self)
        self.resize_button.setBrush(QtCore.Qt.lightGray)
        self.text_item = QtWidgets.QGraphicsSimpleTextItem(self)
        self.text_item.setText(display_name)

    def set_widget_geometry(self):
        header_height = self.header_height if self.show_header else 0
        box_width, box_height = self.rect().width(), self.rect().height()

        if self.show_header:
            self.text_item.show()

            # center header text in rect
            text_width = self.text_item.boundingRect().width()
            text_mid_point = (self.rect().width() / 2) - (text_width / 2)
            self.text_item.setPos(text_mid_point, 0)
        else:
            self.text_item.hide()

        self.wrapped_widget.setGeometry(0, 0, box_width, box_height - header_height)
        self.proxy_widget.setPos(0, header_height)
        self.resize_button.setPos(box_width - self.resize_handle_size, box_height - self.resize_handle_size)

    def update_brush(self):
        if self.is_selected:
            self.setBrush(QtCore.Qt.white)
        else:
            self.setBrush(QtCore.Qt.darkGray)

    def wrap_widget(self, widget):
        self.wrapped_widget = widget
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
        if change == self.ItemSelectedChange and self.scene():
            self.is_selected = bool(value)
            self.update_brush()
        return super(PaletteRectItem, self).itemChange(change, value)


class CommandPaletteWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(CommandPaletteWidget, self).__init__(*args, **kwargs)

        self._display_headers = True

        self._scene_items = []
        self.scene_widgets = []

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.scene = PaletteScene()
        self.graphics_view = PaletteGraphicsView(self.scene, self)

        # set ui
        self.main_layout.addWidget(self.graphics_view)
        self.setLayout(self.main_layout)

    def get_ui_settings(self):
        ui_settings = dict()
        ui_settings["show_headers"] = self._display_headers
        ui_settings["grid_size"] = self.scene.grid_size
        ui_settings["grid_background_color"] = self.scene.backgroundBrush().color().getRgb()[:3]

        v = self.graphics_view.viewportTransform()  # type: QtGui.QTransform
        ui_settings["viewport_transform"] = [
            v.m11(), v.m12(), v.m13(),
            v.m21(), v.m22(), v.m23(),
            v.m31(), v.m32(), v.m33(),
        ]
        return ui_settings

    def set_ui_settings(self, ui_data):
        self.display_headers(ui_data.get("show_headers", True))
        self.set_grid_size(ui_data.get("grid_size"))
        self.set_grid_color(ui_data.get("grid_background_color"))
        view_transform = ui_data.get("viewport_transform")
        # if view_transform:
        #     self.graphics_view.setTransform(QtGui.QTransform(*view_transform))

    def add_widget(self, internal_id, display_name, widget, pos=None):
        rect_item = PaletteRectItem(internal_id, display_name, 0, 0, self.scene.grid_size * 8, self.scene.grid_size * 4)
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
            scene_info = {
                "pos": scene_item.pos().toTuple(),
                "size": [scene_item.rect().width(), scene_item.rect().height()],
            }

            item_widget = scene_item.wrapped_widget

            # noinspection PyUnreachableCode
            if 0:
                import script_panel.script_panel_ui
                item_widget = script_panel.script_panel_ui.ScriptWidget()  # example widget

            # if the wrapped widget has a custom id, use that instead
            palette_id = scene_item.internal_id
            if item_widget and hasattr(item_widget, "palette_id"):
                palette_id = item_widget.palette_id

            # if get_display_info has been implemented, bring it along
            if item_widget and hasattr(item_widget, "get_display_info"):
                scene_info["display_info"] = item_widget.get_display_info()

            user_layout[palette_id] = scene_info

        return user_layout

    def set_scene_layout(self, user_layout):
        for scene_item in self._scene_items:  # type: PaletteRectItem
            layout_info = user_layout.get(scene_item.internal_id)  # type: dict
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

    def remove_selected_items(self):
        for scene_item in self.get_selected_items():  # type: PaletteRectItem
            self.scene.removeItem(scene_item)
            self.scene_widgets.remove(scene_item.wrapped_widget)
            self._scene_items.remove(scene_item)

    def hide_headers(self):
        self.display_headers(False)

    def show_headers(self):
        self.display_headers(True)

    def display_headers(self, state):
        self._display_headers = state
        for scene_item in self._scene_items:  # type: PaletteRectItem
            scene_item.show_header = state
            scene_item.set_widget_geometry()

    def open_grid_size_setter(self):
        new_size, ok = QtWidgets.QInputDialog.getInt(
            self,
            "Set Grid Size",
            "Size (default is {}):".format(lk.default_grid_size),
            self.scene.grid_size,
            1,  # min
            1000,  # max
            1  # precision
        )
        if not ok:
            return

        self.set_grid_size(new_size)

    def set_grid_size(self, new_size):
        if new_size is None:
            return
        self.scene.grid_size = new_size
        for scene_item in self._scene_items:  # type: PaletteRectItem
            scene_item.resize_button.update_size(new_size)
            scene_item.resize_handle_size = new_size
            scene_item.set_widget_geometry()

    def open_grid_background_color_setter(self):
        brush = self.scene.backgroundBrush()  # type: QtGui.QBrush
        pre_color = brush.color()

        new_color = ui_utils.open_color_picker(
            current_color=pre_color,
            color_signal=self.set_grid_color,
        )
        if new_color:
            self.set_grid_color(new_color)
        else:
            self.set_grid_color(pre_color)

    def set_grid_color(self, color=None):
        if color is None:
            color = lk.default_grid_color

        if isinstance(color, (list, tuple)):
            color = QtGui.QColor.fromRgb(*color)

        self.scene.setBackgroundBrush(color)

    def reset_grid_display(self):
        self.reset_grid_size()
        self.reset_grid_color()

    def reset_grid_size(self):
        self.set_grid_size(lk.default_grid_size)

    def reset_grid_color(self):
        self.set_grid_color(lk.default_grid_color)

    def get_mouse_pos(self):
        return self.graphics_view.get_cursor_scene_pos().toTuple()

    def get_selected_items(self):
        return [item for item in self._scene_items if item.is_selected]


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

        menu_bar = QtWidgets.QMenuBar()
        layout_menu = menu_bar.addMenu("Layout")
        layout_menu.addAction("Save Layout", self.save_layout, QtGui.QKeySequence("CTRL+S"))
        layout_menu.addAction("Reload Layout", self.load_layout, QtGui.QKeySequence("CTRL+R"))
        self.setMenuBar(menu_bar)

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
            btn = QtWidgets.QToolButton()
            btn.setText(btn_text)
            btn.clicked.connect(test_func)

            self.command_palette_widget.add_widget(
                internal_id="COMMAND_{:03d}".format(i),
                display_name="Script {}".format(i),
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
