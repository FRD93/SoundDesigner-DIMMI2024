import os.path

from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
import numpy as np
from scipy.signal import argrelextrema
from array_processing import *
import functions
import configparser as cp
import math
import random
from log_coloring import c_print
from path_manager import STYLE_PATH, CONFIG_PATH
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100, data=[]):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.data = data
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)
        self.plot()

    def plot(self):
        x = [i for i in range(len(self.data))]
        y = self.data
        self.axes.plot(x, y)
        self.draw()

conf = cp.ConfigParser()
conf.read(CONFIG_PATH)
try:
    GRID_SIZE = conf.getint("TIMELINE", "grid_size_ppqn")
    MIN_TRIG_DELTA_PPQN = conf.getint("TIMELINE", "min_trig_delta_ppqn")
    PPQN = conf.getint("GENERAL", "ppqn")
except:
    c_print("red", "[ERROR]: Config File not found")
    PPQN = 96
    MIN_TRIG_DELTA_PPQN = 5
    GRID_SIZE = 20

class AddCurvePoint(QUndoCommand):
    def __init__(self, curve, x, y):
        super().__init__(f"Adding point to {(x, y)}")
        self.curve = curve
        self.x = x
        self.y = y
        # print("Inserting point at", [x, y], [curve_x, curve_y])
        self.insert_index = -1
        for index, point in enumerate(self.curve.gui_curve):
            point_x = point.x()
            if self.curve.snap_to_grid:
                point_x = int(point_x / GRID_SIZE) * GRID_SIZE
            if point_x < x:
                self.insert_index = index + 1

    def undo(self):
        self.curve.gui_curve.pop(self.insert_index)
        self.curve.x_values.pop(self.insert_index)
        self.curve.curve.pop(self.insert_index)
        self.curve.npoints -= 1
        self.curve.calcCurveFromGUI()
        # self.curve.parent.updateVisible()
        self.curve.update()

    def redo(self):
        if self.insert_index > 0:

            curve_x = (self.x * (self.curve.maxX - self.curve.minX) / self.curve.width()) + self.curve.minX
            curve_y = (self.y * (self.curve.maxY - self.curve.minY) / self.curve.height()) + self.curve.minY
            c_print("cyan", f"Y value before: {self.y} - after: {curve_y} - remapped: {int(functions.mmap(curve_y, [self.curve.minY, self.curve.maxY], [0, self.curve.height()]))}")
            if self.curve.snap_to_grid:
                curve_x = int(curve_x / GRID_SIZE) * GRID_SIZE
            self.curve.gui_curve.insert(self.insert_index, QPointF(int(functions.mmap(curve_x, [self.curve.minX, self.curve.maxX], [0, self.curve.width()])), int(functions.mmap(curve_y, [self.curve.minY, self.curve.maxY], [0, self.curve.height()]))))
            self.curve.curve.insert(self.insert_index, curve_y)
            self.curve.x_values.insert(self.insert_index, curve_x)
            self.curve.npoints += 1
            self.curve.calcCurveFromGUI()
            # self.curve.parent.updateVisible()
            self.curve.update()


class DeleteCurvePoint(QUndoCommand):
    def __init__(self, curve, index):
        super().__init__(f"Deleting point aiooo {index}")
        self.curve = curve
        self.index = index
        # print(f"deleting index {index}. X values: {self.curve.x_values}")
        # self.point_to_delete = (self.curve.x_values[self.index], self.curve.curve[self.index])
        self.point_to_delete = (self.curve.x_values[self.index], self.curve.gui_curve[self.index])

    def undo(self):
        curve_x, curve_y = self.point_to_delete
        # self.curve.gui_curve.insert(self.index, QPointF(int(functions.mmap(curve_x, [self.curve.minX, self.curve.maxX], [0, self.curve.width()])), int(functions.mmap(curve_y, [self.curve.minY, self.curve.maxY], [0, self.curve.height()]))))
        self.curve.gui_curve.insert(self.index, curve_y)
        self.curve.curve.insert(self.index, curve_y)
        self.curve.x_values.insert(self.index, curve_x)
        self.curve.npoints += 1
        self.curve.calcCurveFromGUI()
        print(f"Re-inserting point{(self.curve.x_values[self.index], self.curve.curve[self.index])}")
        # self.curve.parent.updateVisible()
        self.curve.update()

    def redo(self):
        print(f"Deleting point{(self.curve.x_values[self.index], self.curve.curve[self.index])}")
        self.curve.gui_curve.pop(self.index)
        self.curve.x_values.pop(self.index)
        self.curve.curve.pop(self.index)
        self.curve.npoints -= 1
        self.curve.calcCurveFromGUI()
        # self.curve.parent.updateVisible()
        self.curve.update()


class SetCurvePoints(QUndoCommand):
    def __init__(self, curve, points):
        super().__init__(f"Setting Curve Points")
        self.curve = curve
        self.points = points
        # c_print("green", f"curve x values ({len(self.curve.x_values)}): {self.curve.x_values}")
        # c_print("yellow", f"inserting points ({len(self.points)}): {self.points}")
        self.old_points = []
        for x_id, x_val in enumerate(self.curve.x_values):
            if int(self.points[0].x()) <= x_val <= int(self.points[-1].x()):
                # c_print("red", f"adding to old_points: {QPointF(x_id, self.curve.gui_curve[x_id].y())} - {int(self.points[0].x())} <= {x_val} <= {int(self.points[-1].x())}")
                self.old_points.append(QPointF(x_id, self.curve.gui_curve[x_id].y()))

    def add_point(self, x, y):
        insert_index = -1
        for index, point in enumerate(self.curve.gui_curve):
            point_x = point.x()
            if self.curve.snap_to_grid:
                point_x = int(point_x / GRID_SIZE) * GRID_SIZE
            if point_x < x:
                insert_index = index + 1
        if insert_index > 0:
            # c_print("cyan", f"Y value: {y} - remapped to height: {int(functions.mmap(y, [self.curve.minY, self.curve.maxY], [0, self.curve.height()]))}")
            if self.curve.snap_to_grid:
                x = int(x / GRID_SIZE) * GRID_SIZE
            self.curve.curve.insert(insert_index, y)
            self.curve.x_values.insert(insert_index, x)
            self.curve.npoints += 1
            self.curve.calcGUICurve()

    def remove_point(self, index):
        pass

    def undo(self):
        for point in reversed(self.points):
            command = DeleteCurvePoint(self.curve, int(point.x()))
            command.redo()
        for point in self.old_points:
            command = AddCurvePoint(self.curve, point.x(), point.y())
            command.redo()
        self.curve.update()

    def redo(self):
        for point in reversed(self.old_points):
            # c_print("cyan", f"Attempting to delete point: {point}")
            command = DeleteCurvePoint(self.curve, int(point.x()))
            command.redo()
        for point in self.points:
            # command = AddCurvePoint(self.curve, point.x(), point.y())
            # command.redo()
            self.add_point(point.x(), point.y())
        self.curve.update()


class Curve(QWidget):
    def __init__(self, parent=None, npoints=3, min_=0.0, max_=1.0, initial_values=0.0, unit="", interp="Cubic"):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumSize(200, 100)
        self.catch_point = 10
        self.point_radius = 5
        self.track = None
        self.min = min_
        self.max = max_
        self.npoints = max(3, npoints)
        self.unit = unit
        self.interp = interp
        self.curve = [initial_values] * self.npoints
        self.gui_curve = self.curve.copy()
        self.calcGUICurve()

    def mousePressEvent(self, event):
        for index, point in enumerate(self.gui_curve):
            if np.sqrt((event.position().x() - point.x())**2 + (event.position().y() - point.y())**2) <= self.catch_point:
                self.track = index

    def mouseMoveEvent(self, event):
        if self.track is not None:
            print("self.track:", self.track)
            self.gui_curve[self.track].setX(np.clip(event.position().x(), 0, self.width()))
            self.gui_curve[self.track].setY(np.clip(event.position().y(), 0, self.height()))
            self.calcCurveFromGUI()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.track is not None:
            self.track = None
            self.calcCurveFromGUI()
            self.update()

    def setMin(self, min_):
        for index, point in enumerate(self.curve):
            self.curve[index] = functions.mmap(point, [self.min, self.max], [min_, self.max])
        self.min = min_
        self.calcCurveFromGUI()

    def setMax(self, max_):
        for index, point in enumerate(self.curve):
            self.curve[index] = functions.mmap(point, [self.min, self.max], [self.min, max_])
        self.max = max_
        self.calcCurveFromGUI()

    def setInterp(self, interp):
        if interp not in ["Step", "Linear", "Quad", "Cubic", "Trig"]:
            raise ValueError()
        self.interp = interp

    def calcCurveFromGUI(self):
        for index, point in enumerate(self.gui_curve):
            self.curve[index] = functions.mmap(point.y(), [0, self.height()], [self.max, self.min])
            print("\tself.curve[{}]".format(index), self.curve[index])

    def calcGUICurve(self):
        self.gui_curve = [QPointF(int(index * self.width() / (len(self.curve) - 1)), int(functions.mmap(point, [self.min, self.max], [self.height(), 0]))) for index, point in enumerate(self.curve)]

    def buildPath(self):
        factor = 0.25
        path = QPainterPath(self.gui_curve[0])
        for p, current in enumerate(self.gui_curve[1:-1], 1):
            # previous segment
            source = QLineF(self.gui_curve[p - 1], current)
            # next segment
            target = QLineF(current, self.gui_curve[p + 1])
            targetAngle = target.angleTo(source)
            if targetAngle > 180:
                angle = (source.angle() + source.angleTo(target) / 2) % 360
            else:
                angle = (target.angle() + target.angleTo(source) / 2) % 360
            revTarget = QLineF.fromPolar(source.length() * factor, angle + 180).translated(current)
            cp2 = revTarget.p2()
            if p == 1:
                path.quadTo(cp2, current)
            else:
                # use the control point "cp1" set in the *previous* cycle
                path.cubicTo(cp1, cp2, current)
            revSource = QLineF.fromPolar(target.length() * factor, angle).translated(current)
            cp1 = revSource.p2()
        # the final curve, that joins to the last point
        path.quadTo(cp1, self.gui_curve[-1])
        return path

    def paintEvent(self, event):
        self.calcGUICurve()
        painter = QPainter(self)
        path = QPainterPath()
        painter.setPen(Qt.GlobalColor.darkBlue)
        painter.setBrush(Qt.GlobalColor.darkYellow)
        last_point = None
        if self.interp != "Quad":
            for index, point in enumerate(self.gui_curve):
                if last_point is not None:
                    path.moveTo(last_point)
                    if self.interp == "Step":
                        painter.drawLine(last_point, QPointF(point.x(), last_point.y()))
                        painter.drawLine(QPointF(point.x(), last_point.y()), point)
                    elif self.interp == "Linear":
                        painter.drawLine(last_point, point)
                    elif self.interp == "Cubic":
                        path.cubicTo(QPointF(int((point.x() + last_point.x()) / 2), point.y()), QPointF(int((point.x() + last_point.x()) / 2), last_point.y()), point)
                        #path.cubicTo(QPointF(last_point.x(), point.y()), QPointF(self.gui_curve[np.clip(index + 1, 0, len(self.gui_curve) - 1)].x(), last_point.y()), point)
                if self.interp == "Cubic":
                    painter.drawPath(path)
                last_point = point
        else:
            path = self.buildPath()
            painter.drawPath(path)
        # draw points
        for index, point in enumerate(self.gui_curve):
            painter.drawEllipse(point, self.point_radius, self.point_radius)
            if self.track == index:
                val = str(self.curve[index])
                x = point.x()
                if x > (self.width() - 30):
                    x -= 30
                y = point.y() - 10
                if y < 30:
                    y += 30
                if len(val) >= max(len(str(self.min)), len(str(self.max))) + 2:
                    val = val[:max(len(str(self.min)), len(str(self.max))) + 2]
                val = val + " " + self.unit
                painter.drawText(x, y, val)

    def __getstate__(self):
        pass

    def __setstate__(self, state):
        pass


class CurveXY(QLabel):
    def __init__(self, parent=None, npoints=3, minY=0.0, maxY=1.0, initial_valuesY=0.0, unitY="", minX=0, maxX=1000, unitX="", interp="Quad", log_scale=False, name=""):
        super().__init__(parent)
        self.parent = parent
        self.params_widget = self.parent.params_widget
        self.name = name
        self.setObjectName("curvexy")
        self.setAutoFillBackground(True)
        self.setMouseTracking(True)
        # self.setMinimumSize(100, 20)
        self.setContentsMargins(0, 0, 0, 0)
        self.catch_point = 10
        self.point_radius = 5
        self.cursor_pos = 0
        self.zoom = 1.0
        self.track = None
        self.snap_to_grid = False
        self.minY = minY
        self.maxY = maxY
        self.npoints = max(3, npoints)
        self.unitY = unitY
        self.minX = minX
        self.maxX = maxX
        self.log_scale_y = log_scale
        # if self.minY > 0 and self.maxY > 0:
        #     self.log_scale_y = True
        # else:
        #     self.log_scale_y = False
        self.setFixedWidth(int(self.maxX))
        self.unitX = unitX
        self.x_gui = [(i * self.width() / (self.npoints - 1)) for i in range(self.npoints)]
        print(f"self.x_gui: {self.x_gui}; [self.minX, self.maxX]: {[self.minX, self.maxX]}")
        self.x_values = [functions.mmap(val, [0, self.width()], [self.minX, self.maxX]) for val in self.x_gui]
        print(f"self.x_values: {self.x_values}")
        self.interp = interp
        self.curve = [initial_valuesY] * self.npoints
        self.gui_curve = self.curve.copy()
        self.calcGUICurve()
        # c_print("cyan", f"GUI Curve is {self.gui_curve}")

    def set_snap_to_grid(self, snap):
        self.snap_to_grid = snap

    def log_to_lin(self, value):
        return math.pow(10, value)

    def set_cursor(self, cursor_pos):
        self.cursor_pos = int(cursor_pos)
        self.update()

    def send_set_cursor(self):
        self.parent.region_line.update_cursor_pos(self.cursor_pos)

    def move_points(self, from_, to_, move):
        for i in range(len(self.x_values)):
            if 0 < i < (len(self.x_values) - 1):
                if from_ <= self.x_values[i] <= to_:
                    self.x_values[i] += move
        self.x_values.sort()
        self.calcGUICurve()
        self.update()

    def stretch_points(self, old_region, from_, to_):
        old_from = old_region["start"]
        old_to = old_region["end"]
        for i in range(len(self.x_values)):
            if 0 < i < (len(self.x_values) - 1):
                if old_from <= self.x_values[i] <= old_to:
                    print(f"Remapping x_value: from {self.x_values[i]}; ", sep="")
                    self.x_values[i] = functions.mmap(self.x_values[i], [old_from, old_to], [from_, to_])
                    print(f"to {self.x_values[i]}; ")
        self.x_values.sort()
        self.calcGUICurve()
        self.update()

    def change_length(self, new_length):
        self.setGeometry(0, 0, int(new_length), self.height())
        self.maxX = float(new_length)
        scale_factor = self.maxX / self.x_values[-1]
        # print(f"self.x_values before zoom: {self.x_values}")
        self.x_values = [x_v * scale_factor for x_v in self.x_values]
        self.calcGUICurve()
        # self.calcCurveFromGUI()
        self.update()

    def zoom_in(self):
        self.zoom *= 2.0
        self.setFixedWidth(int(self.width() * 2))
        self.change_length(self.maxX)
        print(self.zoom)

    def zoom_out(self):
        self.zoom /= 2.0
        self.setFixedWidth(int(self.width() / 2))
        self.change_length(self.maxX)
        print(self.zoom)

    def getXValues(self):
        return self.x_values

    def getYValues(self):
        return self.curve

    def get_undo_stack(self):
        return self.parent.get_undo_stack()

    def insertPoint(self, x, y):
        command = AddCurvePoint(self, x, y)
        self.get_undo_stack().push(command)

    def deletePoint(self, index):
        command = DeleteCurvePoint(self, index)
        self.get_undo_stack().push(command)

    def mousePressEvent(self, event):
        self.track = None
        modifiers = QApplication.keyboardModifiers()
        if event.button() == Qt.MouseButton.LeftButton:
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.insertPoint(event.position().x(), event.position().y())
            for index, point in enumerate(self.gui_curve):
                if np.sqrt((event.position().x() - point.x())**2 + (event.position().y() - point.y())**2) <= self.catch_point:
                    if modifiers == Qt.KeyboardModifier.ControlModifier:
                        settings = EnvelopePointSettings(parent=None, curve=self, point_val=self.curve[index], point_pos=self.x_values[index])
                        if settings.exec():
                            val, pos = settings.getInputs()
                            self.x_values[index] = pos
                            self.curve[index] = val
                            self.calcGUICurve()
                            self.update()
                    else:
                        self.track = index
        if event.button() == Qt.MouseButton.RightButton:
            for index, point in enumerate(self.gui_curve):
                if np.sqrt((event.position().x() - point.x())**2 + (event.position().y() - point.y())**2) <= self.catch_point:
                    self.deletePoint(index)
        self.update()

    def mouseMoveEvent(self, event):
        self.cursor_pos = int(event.position().x())
        self.send_set_cursor()
        if self.track is not None:
            # self.x_gui[self.track] = np.clip(event.position().x(), 0, self.width())
            if 0 < self.track < len(self.gui_curve) - 1:
                new_x = event.position().x()
                if self.snap_to_grid:
                    new_x = new_x + (GRID_SIZE / 2)
                self.gui_curve[self.track].setX(np.clip(new_x, 0, self.width()))
            self.gui_curve[self.track].setY(np.clip(event.position().y(), 0, self.height()))
            # print(self.x_gui[self.track], self.width())
            c_print("red", f"tracked index: {self.track}")
            self.calcCurveFromGUI()
        self.update()

    def mouseReleaseEvent(self, event):
        if self.track is not None:
            self.track = None
            self.calcCurveFromGUI()
            self.update()

    def setMin(self, min_):
        for index, point in enumerate(self.curve):
            self.curve[index] = functions.mmap(point, [self.minY, self.maxY], [min_, self.maxY])
        self.minY = min_
        # self.calcCurveFromGUI()
        self.calcGUICurve()

    def setMax(self, max_):
        for index, point in enumerate(self.curve):
            self.curve[index] = functions.mmap(point, [self.minY, self.maxY], [self.minY, max_])
        self.maxY = max_
        # self.calcCurveFromGUI()
        self.calcGUICurve()

    def setInterp(self, interp):
        if interp not in ["Step", "Linear", "Quad", "Cubic", "Trig"]:
            raise ValueError()
        self.interp = interp

    def setScale(self, scale):
        if scale not in ["Lin", "Log"]:
            raise ValueError()
        if scale == "Lin":
            self.log_scale_y = False
        else:
            if self.minY > 0 and self.maxY > 0:
                self.log_scale_y = True
            else:
                self.log_scale_y = False
        self.params_widget.scale_btn.setText("Log" if self.log_scale_y else "Lin")
        self.calcGUICurve()
        # self.calcCurveFromGUI()

    def recalc_y_GUI(self):
        for index, point in enumerate(self.gui_curve):
            self.curve[index] = functions.mmap(point.y(), [0, self.height()], [self.maxY, self.minY])

    def calcGUICurve(self):
        self.gui_curve = []
        for i in range(len(self.curve)):
            x = self.x_values[i] * self.zoom
            y_value = self.curve[i]

            # Trasformazione dei valori Y in base alla scala
            if self.log_scale_y:
                minY_log = math.log10(self.minY) if self.minY > 0 else 0
                maxY_log = math.log10(self.maxY) if self.maxY > 0 else 0
                y_value_log = math.log10(y_value) if y_value > 0 else 0
                y = functions.mmap(y_value_log, [minY_log, maxY_log], [self.height(), 0])
            else:
                y = functions.mmap(y_value, [self.minY, self.maxY], [self.height(), 0])

            self.gui_curve.append(QPointF(x, y))

    def calcCurveFromGUI(self):
        for i in range(len(self.gui_curve)):
            x = self.gui_curve[i].x() / self.zoom
            y = self.gui_curve[i].y()

            if self.log_scale_y:
                minY_log = math.log10(self.minY) if self.minY > 0 else 0
                maxY_log = math.log10(self.maxY) if self.maxY > 0 else 0
                y_value_log = functions.mmap(y, [self.height(), 0], [minY_log, maxY_log])
                self.curve[i] = 10 ** y_value_log  # Inverso della trasformazione logaritmica
            else:
                self.curve[i] = functions.mmap(y, [self.height(), 0], [self.minY, self.maxY])
            c_print("green", f"self.curve is {self.curve}")
            self.x_values[i] = functions.mmap(x, [0, self.width()], [self.minX, self.maxX]) * self.zoom

    def resizeEvent(self, event):
        self.calcGUICurve()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw grid (optional, can be customized)
        self.draw_grid(painter)

        # Draw curve
        self.draw_curve(painter)

        # Draw points
        self.draw_points(painter)

        # Draw cursor
        self.draw_cursor(painter)

    def draw_grid(self, painter):
        # Implement grid drawing if necessary
        pass

    def draw_curve(self, painter):
        painter.setPen(QPen(Qt.GlobalColor.gray, 2))
        if self.interp == "Quad":
            path = QPainterPath()
            last_point = self.gui_curve[0]
            path.moveTo(last_point)
            for point in self.gui_curve[1:]:
                path.quadTo(QPointF((last_point.x() + point.x()) / 2, last_point.y()), point)
                last_point = point
            painter.drawPath(path)
        elif self.interp == "Cubic":
            path = QPainterPath()
            last_point = self.gui_curve[0]
            path.moveTo(last_point)
            for point in self.gui_curve[1:]:
                mid_point = QPointF((last_point.x() + point.x()) / 2, (last_point.y() + point.y()) / 2)
                path.cubicTo(mid_point, mid_point, point)
                last_point = point
            painter.drawPath(path)
        elif self.interp == "Trig":
            for point in self.gui_curve:
                painter.drawLine(QPointF(point), QPointF(point.x(), self.height()))
        elif self.interp == "Step":
            for pindex, point in enumerate(self.gui_curve[1:]):
                pindex += 1
                last_point = self.gui_curve[pindex-1]
                painter.drawLine(last_point, QPointF(point.x(), last_point.y()))
                painter.drawLine(QPointF(point.x(), last_point.y()), point)
        else:
            path = QPainterPath()
            last_point = self.gui_curve[0]
            path.moveTo(last_point)
            for point in self.gui_curve[1:]:
                path.lineTo(point)
                last_point = point
            painter.drawPath(path)

    def draw_points(self, painter):
        painter.setPen(Qt.GlobalColor.white)
        painter.setBrush(Qt.GlobalColor.gray)
        for index, point in enumerate(self.gui_curve):
            gradient = QRadialGradient(point, self.point_radius)
            gradient.setColorAt(0, Qt.GlobalColor.white)
            gradient.setColorAt(1, Qt.GlobalColor.gray)
            painter.setBrush(gradient)
            painter.drawEllipse(point, self.point_radius, self.point_radius)
            if self.track == index:
                self.draw_point_label(painter, point, index)

    def draw_point_label(self, painter, point, index):
        x = int(point.x())
        y = int(point.y())
        val = f"{self.curve[index]:.2f} {self.unitY}"
        c_print("yellow", f"point value is {val} - scale: {'log' if self.log_scale_y else 'lin'}")
        xval = f"{self.x_values[index]:.2f} {self.unitX}"

        if y < self.height() / 2:
            y_offset = 20  # Posiziona l'etichetta sotto il punto
        else:
            y_offset = -20  # Posiziona l'etichetta sopra il punto

        painter.drawText(x, y + y_offset, val)
        # painter.drawText(x, y + y_offset + 10 if y < self.height() / 2 else y + y_offset - 10, xval)
        i = int(x / self.zoom)
        painter.drawText(QPoint(x + 2,  y + y_offset + 10 if y < self.height() / 2 else y + y_offset - 10), str(int(i / (PPQN * 4))) + ":" + str(int((i / PPQN) % 4)))
        painter.drawText(QPoint(x + 2,  y + y_offset + 20 if y < self.height() / 2 else y + y_offset - 20), self.getTimeOfTick(i))

    def draw_cursor(self, painter):
        painter.drawLine(self.cursor_pos, 0, self.cursor_pos, self.height())

    def getTimeOfTick(self, tick):
        t_millis = int(1000 * (60. / self.parent.region_line.clock.getBPM()) * (tick / PPQN))
        ms = int(t_millis % 1000)
        s = int((t_millis / 1000) % 60)
        m = int((t_millis / 60000) % 60)
        h = int((t_millis / 3600000) % 24)
        # print("h:", h, "m:", m, "s:", s, "ms:", ms)
        # return dtime(hour=h, minute=m, second=s, microsecond=ms * 1000)
        return str(h) + ":" + str(m) + ":" + str(s) + "." + str(ms)[:3]

    def __getstate__(self):
        d = {
            "npoints": self.npoints,
            "gui_curve": self.gui_curve,
            "x_values": self.x_values,
            "curve": self.curve,
            "minX": self.minX,
            "maxX": self.maxX,
            "minY": self.minY,
            "maxY": self.maxY,
            "interp": self.interp,
            "log_scale_y": self.log_scale_y
        }
        return d

    def __setstate__(self, state):
        self.npoints = state["npoints"]
        # self.gui_curve = state["gui_curve"]
        self.x_values = state["x_values"]
        self.curve = state["curve"]
        self.minX = state["minX"]
        self.maxX = state["maxX"]
        self.minY = state["minY"]
        self.maxY = state["maxY"]
        self.setInterp(state["interp"])
        try:
            self.setScale("Log" if state["log_scale_y"] else "Lin")
        except:
            c_print("yellow", "WARNING: CurveXY has no log_scale_y saved! Please check and resave the file to remove this discrepancy.")
        # self.calcGUICurve()
        self.update()


class EnvelopeParams(QWidget):
    def __init__(self, parent=None, envelope=None):
        super(EnvelopeParams, self).__init__(parent)
        self.parent = parent
        self.envelope = envelope
        self.curve_set_width = 50

        self.min_label = QLabel("Min:")
        self.min_label.setObjectName("widget-param")
        self.min_label.setFixedWidth(self.envelope.p_width // 2)
        self.min_input = QDoubleSpinBox()
        self.min_input.setObjectName("widget-param")
        self.min_input.setFixedWidth(self.envelope.p_width // 2)
        self.min_input.setRange(-40000, 40000)
        self.min_input.setSingleStep((self.envelope.max - self.envelope.min) / 10)
        self.min_input.setValue(self.envelope.min)
        self.min_input.valueChanged.connect(self.envelope.setMin)
        self.min_lay = QHBoxLayout()
        self.min_lay.addWidget(self.min_label)
        self.min_lay.addWidget(self.min_input)
        self.min_lay.setSpacing(0)

        self.max_label = QLabel("Max:")
        self.max_label.setObjectName("widget-param")
        self.max_label.setFixedWidth(self.envelope.p_width // 2)
        self.max_input = QDoubleSpinBox()
        self.max_input.setObjectName("widget-param")
        self.max_input.setFixedWidth(self.envelope.p_width // 2)
        self.max_input.setRange(-40000, 40000)
        self.max_input.setSingleStep((self.envelope.max - self.envelope.min) / 10)
        self.max_input.setValue(self.envelope.max)
        self.max_input.valueChanged.connect(self.envelope.setMax)
        self.max_lay = QHBoxLayout()
        self.max_lay.addWidget(self.max_label)
        self.max_lay.addWidget(self.max_input)
        self.max_lay.setSpacing(0)

        self.interp_label = QLabel("Interp:")
        self.interp_label.setObjectName("widget-param")
        self.interp_label.setFixedWidth(self.envelope.p_width // 2)
        self.interp_btn = QPushButton()
        self.interp_btn.setObjectName("widget-param")
        self.interp_btn.setFixedWidth(self.envelope.p_width // 2)
        self.interp_menu = QMenu()
        self.interp_menu.setObjectName("widget-param")
        self.interp_menu.addAction("Step", self.envelope.change_interp_func)
        self.interp_menu.addAction("Linear", self.envelope.change_interp_func)
        self.interp_menu.addAction("Quad", self.envelope.change_interp_func)
        # self.interp_menu.addAction("Cubic", self.envelope.change_interp_func)
        self.interp_menu.addAction("Trig", self.envelope.change_interp_func)
        self.interp_btn.setText(self.envelope.interp)
        self.interp_btn.setMenu(self.interp_menu)
        self.interp_lay = QHBoxLayout()
        self.interp_lay.addWidget(self.interp_label)
        self.interp_lay.addWidget(self.interp_btn)
        self.interp_lay.setSpacing(0)

        self.scale_label = QLabel("Scale:")
        self.scale_label.setObjectName("widget-param")
        self.scale_label.setFixedWidth(self.envelope.p_width // 2)
        self.scale_btn = QPushButton()
        self.scale_btn.setObjectName("widget-param")
        self.scale_btn.setFixedWidth(self.envelope.p_width // 2)
        self.scale_menu = QMenu()
        self.scale_menu.setObjectName("widget-param")
        self.scale_menu.addAction("Lin", self.envelope.change_scale_func)
        self.scale_menu.addAction("Log", self.envelope.change_scale_func)
        self.scale_btn.setText("Lin")
        # self.envelope.change_scale_func()
        self.scale_btn.setMenu(self.scale_menu)
        self.scale_lay = QHBoxLayout()
        self.scale_lay.addWidget(self.scale_label)
        self.scale_lay.addWidget(self.scale_btn)
        self.scale_lay.setSpacing(0)

        self.expand_btn = QPushButton(self.envelope.name)
        self.expand_btn.setObjectName("widget-param")
        self.expand_btn.setCheckable(True)
        self.expand_btn.setFixedWidth(self.envelope.p_width - 20)
        self.expand_btn.clicked.connect(self.envelope.changeAspect)
        self.enabled_check = QCheckBox()
        self.enabled_check.setFixedWidth(20)
        self.enabled_check.setCheckable(True)
        self.enabled_check.setChecked(self.envelope.isEnabled())
        self.enabled_check.clicked.connect(self.print_enabled_check)
        self.expand_lay = QHBoxLayout()
        self.expand_lay.setSpacing(0)
        self.expand_lay.setContentsMargins(0, 0, 0, 0)
        self.expand_lay.addWidget(self.enabled_check)
        self.expand_lay.addSpacing(5)
        self.expand_lay.addWidget(self.expand_btn)

        # # Curve Generation / External Mapping
        self.curve_generation_lay = QHBoxLayout()
        self.curve_generation_lay.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # Mathematical Expression
        self.math_btn = QPushButton("ƒ")
        self.math_btn.setObjectName("widget-param")
        self.math_btn.setMaximumWidth(self.curve_set_width)
        self.math_btn.setCheckable(True)
        self.math_btn.clicked.connect(self.gen_function)
        self.curve_generation_lay.addWidget(self.math_btn)
        # NumPy Time Series Value
        self.time_series_param_btn = QPushButton("N")
        self.time_series_param_btn.setObjectName("widget-param")
        self.time_series_param_btn.setMaximumWidth(self.curve_set_width)
        self.time_series_param_btn.setCheckable(True)
        self.time_series_param_btn.clicked.connect(self.time_series_function)
        self.curve_generation_lay.addWidget(self.time_series_param_btn)
        # Network Value
        self.net_param_btn = QPushButton("\U0001F6E8")
        self.net_param_btn.setObjectName("widget-param")
        self.net_param_btn.setMaximumWidth(self.curve_set_width)
        self.net_param_btn.setCheckable(True)
        self.net_param_btn.clicked.connect(self.net_function)
        self.curve_generation_lay.addWidget(self.net_param_btn)

        self.curve_param_lay = QVBoxLayout()
        self.curve_param_lay.setContentsMargins(0, 0, 0, 0)
        self.curve_param_lay.setSpacing(0)
        self.curve_param_lay.addLayout(self.expand_lay)
        self.curve_param_lay.addSpacing(8)
        self.curve_param_lay.addLayout(self.curve_generation_lay)
        self.curve_param_lay.addLayout(self.max_lay)
        self.curve_param_lay.addLayout(self.min_lay)
        self.curve_param_lay.addLayout(self.interp_lay)
        self.curve_param_lay.addLayout(self.scale_lay)
        self.curve_param_lay.addStretch()
        self.setLayout(self.curve_param_lay)
        self.setFixedWidth(125)
        self.setFixedHeight(140)

    def print_enabled_check(self):
        self.envelope.setEnabled(self.enabled_check.isChecked())
        print(self.enabled_check.isChecked())

    def gen_function(self):
        dialog = FunctionInputDialog(self.envelope.region_line.regions, self.envelope.curve)
        dialog.exec()

    def time_series_function(self):
        dialog = NumPyInputDialog(self.envelope.region_line.regions, self.envelope.curve)
        dialog.exec()

    def net_function(self):
        dialog = NetworkInputDialog(self.envelope.curve)
        dialog.exec()

    def __getstate__(self):
        d = {
            "minY": self.envelope.min,
            "maxY": self.envelope.max,
            "interp": self.envelope.interp,
            "scale_y": self.scale_btn.text()
        }
        return d

    def __setstate__(self, state):
        try:
            self.scale_btn.setText(state["scale_y"])
            self.interp_btn.setText(state["interp"])
            self.min_input.setValue(state["minY"])
            self.max_input.setValue(state["maxY"])
            self.update()
        except:
            c_print("yellow", "WARNING: EnvelopeParams wasn't saved with __getstate__ ! Please check and resave the file to remove this discrepancy.")


class NetworkInputDialog(QDialog):
    def __init__(self, curve):
        super().__init__()
        self.curve = curve
        self.setWindowTitle("Open Network Port for Input Data")
        self.desc_lbl = QLabel("Open Network Port for mapping a Curve with Input Data.\nSet the receiver tag to be match with the input.")
        self.layout = QVBoxLayout()
        self.ok_button = QPushButton("OK", self)
        self.ok_button.clicked.connect(self.on_ok)
        self.layout.addWidget(self.desc_lbl)
        self.layout.addWidget(self.ok_button)
        self.setLayout(self.layout)

    def on_ok(self):
        self.close()


class NumPyInputDialog(QDialog):
    def __init__(self, regions, curve):
        super().__init__()
        self.curve = curve
        self.regions = regions.copy()
        self.min_x = 1
        self.max_x = self.curve.x_values[-1]
        self.step = 1
        self.npy_data = None
        self.simplified_indexes = None
        self.plot_canvas = None
        self.out_range_min = 20.0
        self.out_range_max = 20000.0
        self.regions["All Project"] = {"name": "All Project", "start": self.min_x, "end": self.max_x, "program": -1}
        self.regions["Custom"] = {"name": "Custom", "start": self.min_x, "end": self.max_x, "program": -1}
        self.setWindowTitle("Load Time Series")
        self.desc_lbl = QLabel("Resample a NumPy Time Series into Region")
        self.open_npy_btn = QPushButton("Open .npy file")
        self.open_npy_btn.clicked.connect(self.open_npy_fnc)
        self.layout = QVBoxLayout()
        self.ok_button = QPushButton("OK", self)
        self.ok_button.clicked.connect(self.on_ok)
        self.simplify_btn = QPushButton("Simplify", self)
        self.simplify_btn.clicked.connect(self.simplify_func)
        # Region From-To
        self.from_lbl = QLabel("From:")
        self.from_txt = QLineEdit()
        self.from_txt.textChanged.connect(self.from_changed)
        self.to_lbl = QLabel("To:")
        self.to_txt = QLineEdit()
        self.to_txt.textChanged.connect(self.to_changed)
        self.step_lbl = QLabel("Step:")
        self.step_txt = QLineEdit()
        self.step_txt.textChanged.connect(self.step_changed)
        self.from_to_lay = QHBoxLayout()
        self.from_to_lay.addWidget(self.from_lbl)
        self.from_to_lay.addWidget(self.from_txt)
        self.from_to_lay.addWidget(self.to_lbl)
        self.from_to_lay.addWidget(self.to_txt)
        self.from_to_lay.addWidget(self.step_lbl)
        self.from_to_lay.addWidget(self.step_txt)
        # Y-axis From-To
        self.y_from_lbl = QLabel("Y From:")
        self.y_from_txt = QLineEdit()
        self.y_from_txt.setText(str(self.out_range_min))
        self.y_from_txt.textChanged.connect(self.y_from_changed)
        self.y_to_lbl = QLabel("Y To:")
        self.y_to_txt = QLineEdit()
        self.y_to_txt.setText(str(self.out_range_max))
        self.y_to_txt.textChanged.connect(self.y_to_changed)
        self.y_to_lay = QHBoxLayout()
        self.y_to_lay.addWidget(self.y_from_lbl)
        self.y_to_lay.addWidget(self.y_from_txt)
        self.y_to_lay.addWidget(self.y_to_lbl)
        self.y_to_lay.addWidget(self.y_to_txt)

        self.set_region_lay = QHBoxLayout()
        self.set_region_btn = QPushButton()
        self.set_region_menu = QMenu()
        self.set_region_btn.setMenu(self.set_region_menu)
        for key in self.regions.keys():
            name = self.regions[key]["name"]
            self.set_region_menu.addAction(name, lambda x=name: self.set_region_func(x))
        self.set_region_lbl = QLabel("Region:")
        self.set_region_lay.addWidget(self.set_region_lbl)
        self.set_region_lay.addWidget(self.set_region_btn)
        self.layout.addWidget(self.desc_lbl)
        self.layout.addLayout(self.set_region_lay)
        self.layout.addLayout(self.from_to_lay)
        self.layout.addLayout(self.y_to_lay)
        self.layout.addWidget(self.open_npy_btn)
        self.layout.addWidget(self.simplify_btn)
        self.layout.addWidget(self.ok_button)
        self.setLayout(self.layout)
        self.set_region_func("Custom")

    def simplify_func(self):
        if type(self.npy_data) is np.ndarray and self.npy_data.shape[0] > 4:
            c_print("cyan", "shape of npy_data is {}".format(self.npy_data.shape))
            smoothed_curve = moving_average(self.npy_data, 5)  # Adjust window_size as needed
            # smoothed_curve = self.npy_data
            # Step 2: Compute first derivative
            first_derivative = np.gradient(smoothed_curve)

            # Step 3: Find local maxima and minima in the first derivative
            # You can adjust the order parameter based on the expected number of peaks and valleys
            minima_indexes = argrelextrema(first_derivative, np.less, order=2)[0]
            maxima_indexes = argrelextrema(first_derivative, np.greater, order=2)[0]

            # Step 4: Filter based on confidence (for example, keep peaks and valleys above a certain threshold)
            # Example: Filter based on a minimum difference from neighboring points
            # confidence_threshold = 0.5
            confidence_threshold = np.mean(np.abs(first_derivative)) / 2.
            filtered_minima_indexes = [idx for idx in minima_indexes
                                       if np.all(first_derivative[idx] < -confidence_threshold)]
            filtered_maxima_indexes = [idx for idx in maxima_indexes
                                       if np.all(first_derivative[idx] > confidence_threshold)]

            print(filtered_minima_indexes)
            print(filtered_maxima_indexes)

            # Step 5: Retrieve indexes of salient points in the original time series
            salient_point_indexes = sorted(filtered_minima_indexes + filtered_maxima_indexes)
            # salient_point_indexes = sorted(minima_indexes.tolist() + maxima_indexes.tolist())

            self.simplified_indexes = salient_point_indexes
            if 0 not in self.simplified_indexes:
                self.simplified_indexes = [0] + self.simplified_indexes
            if (self.npy_data.shape[0] - 1) not in self.simplified_indexes:
                self.simplified_indexes = self.simplified_indexes + [self.npy_data.shape[0] - 1]
            print(f"min value index is {list(self.npy_data).index(np.amin(self.npy_data))}")
            print(f"max value index is {list(self.npy_data).index(np.amax(self.npy_data))}")
            if list(self.npy_data).index(np.amax(self.npy_data)) not in self.simplified_indexes:
                print(f"\tinserting {list(self.npy_data).index(np.amax(self.npy_data))}")
                self.simplified_indexes = sorted(self.simplified_indexes + [list(self.npy_data).index(np.amax(self.npy_data))])
                print(f"\t\tnew self.simplified_indexes: {self.simplified_indexes}")
            if list(self.npy_data).index(np.amin(self.npy_data)) not in self.simplified_indexes:
                print(f"\tinserting {list(self.npy_data).index(np.amin(self.npy_data))}")
                self.simplified_indexes = sorted(self.simplified_indexes + [list(self.npy_data).index(np.amin(self.npy_data))])
                print(f"\t\tnew self.simplified_indexes: {self.simplified_indexes}")

            self.simplified_indexes = np.array(self.simplified_indexes)
            self.plot()

    def from_changed(self):
        try:
            val = int(float(self.sender().text()))
            self.min_x = val
            self.regions["Custom"]["start"] = self.min_x
        except:
            c_print("red", f"Bad text: {self.sender().text()}")

    def to_changed(self):
        try:
            val = int(float(self.sender().text()))
            self.max_x = val
            self.regions["Custom"]["end"] = self.max_x
        except:
            c_print("red", f"Bad text: {self.sender().text()}")

    def y_from_changed(self):
        try:
            val = int(float(self.sender().text()))
            self.out_range_min = val
        except:
            c_print("red", f"Bad text: {self.sender().text()}")

    def y_to_changed(self):
        try:
            val = int(float(self.sender().text()))
            self.out_range_max = val
        except:
            c_print("red", f"Bad text: {self.sender().text()}")

    def step_changed(self):
        try:
            val = int(float(self.sender().text()))
            self.step = val
        except:
            c_print("red", f"Bad text: {self.sender().text()}")

    def set_region_func(self, region_name):
        region = self.regions[region_name]
        self.set_region_btn.setText(region_name)
        if region_name == "Custom":
            self.from_txt.setEnabled(True)
            self.from_txt.setText(str(int(region["start"])))
            self.to_txt.setEnabled(True)
            self.to_txt.setText(str(int(region["end"])))
            self.step_txt.setText(str(int(self.step)))
            self.min_x = int(region["start"])
            self.max_x = int(region["end"])
        else:
            self.from_txt.setEnabled(False)
            self.from_txt.setText(str(int(region["start"])))
            self.to_txt.setEnabled(False)
            self.to_txt.setText(str(int(region["end"])))
            self.min_x = int(region["start"])
            self.max_x = int(region["end"])
            self.step_txt.setText(str(int(self.step)))

    def open_npy_fnc(self):
        context = {"start": self.min_x, "end": self.max_x, "math": math, "random": random}
        filename, _ = QFileDialog.getOpenFileName(self, "Select NumPy File", "/Users/francescodani/Downloads", filter="NumPy Files (*.npy)")
        if os.path.exists(filename) and ".npy" in filename:
            print("filename:", filename)
            self.npy_data = np.load(filename)
            if len(self.npy_data) > 1:
                self.npy_data = np.array([self.npy_data[i][0] for i in range(self.npy_data.shape[0])])
            print(self.npy_data.shape)
            self.simplified_indexes = None
            self.plot()

    def plot(self):
        resampled_data = functions.resample(self.npy_data, self.max_x - self.min_x)
        self.points = np.array([float(resampled_data[index - self.min_x]) for index in range(self.min_x, int(self.max_x / self.step))])
        self.points = functions.normalize(self.points)
        self.points = [functions.mmap(num, [0.0, 1.0], [self.out_range_min, self.out_range_max]) for num in self.points]
        try:
            self.plot_canvas.close()
            del self.plot_canvas
        except:
            pass
        self.plot_canvas = MplCanvas(parent=None, data=self.points)
        self.layout.addWidget(self.plot_canvas)

    def on_ok(self):
        try:
            c_print("green", f"self.points min {min(self.points)} max {max(self.points)}")
            if self.simplified_indexes is None:
                points = [QPointF(float(index), float(self.points[int(index - self.min_x)])) for index in range(self.min_x, self.max_x, self.step)]
            else:
                normalized_data = functions.normalize(self.npy_data)
                points = [QPointF(float(functions.mmap(index, [0, len(self.npy_data)], [self.min_x, self.max_x])), functions.mmap(float(normalized_data[index]), [0.0, 1.0], [self.out_range_min, self.out_range_max])) for index in self.simplified_indexes]
                pp = [p.y() for p in points]
                c_print("yellow", f"pp min {min(pp)} max {max(pp)}")
            command = SetCurvePoints(self.curve, points)
            self.curve.parent.region_line.get_undo_stack().push(command)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        try:
            self.plot_canvas.close()
            del self.plot_canvas
        except:
            pass
        self.close()


class FunctionInputDialog(QDialog):
    def __init__(self, regions, curve):
        super().__init__()
        self.regions = regions.copy()
        self.curve = curve
        self.plot_canvas = None
        self.min_x = 1
        self.max_x = self.curve.x_values[-1]
        self.step = 1
        self.regions["All Project"] = {"name": "All Project", "start": self.min_x, "end": self.max_x, "program": -1}
        self.regions["Custom"] = {"name": "Custom", "start": self.min_x, "end": self.max_x, "program": -1}

        self.setWindowTitle("Insert mathematical expression")
        self.layout = QVBoxLayout()

        self.from_lbl = QLabel("From:")
        self.from_txt = QLineEdit()
        self.from_txt.textChanged.connect(self.from_changed)
        self.to_lbl = QLabel("To:")
        self.to_txt = QLineEdit()
        self.to_txt.textChanged.connect(self.to_changed)
        self.step_lbl = QLabel("Step:")
        self.step_txt = QLineEdit()
        self.step_txt.textChanged.connect(self.step_changed)
        self.from_to_lay = QHBoxLayout()
        self.from_to_lay.addWidget(self.from_lbl)
        self.from_to_lay.addWidget(self.from_txt)
        self.from_to_lay.addWidget(self.to_lbl)
        self.from_to_lay.addWidget(self.to_txt)
        self.from_to_lay.addWidget(self.step_lbl)
        self.from_to_lay.addWidget(self.step_txt)

        self.set_region_lay = QHBoxLayout()
        self.set_region_btn = QPushButton()
        self.set_region_menu = QMenu()
        self.set_region_btn.setMenu(self.set_region_menu)
        for key in self.regions.keys():
            name = self.regions[key]["name"]
            self.set_region_menu.addAction(name, lambda x=name: self.set_region_func(x))
        self.set_region_lbl = QLabel("Region:")
        self.set_region_lay.addWidget(self.set_region_lbl)
        self.set_region_lay.addWidget(self.set_region_btn)
        self.layout.addLayout(self.set_region_lay)
        self.layout.addLayout(self.from_to_lay)

        self.description_text = QLabel("Write an expression to compute the points of the curve in the specified interval.\n"
                                       "The expression accepts 'start' (From point), 'end' (To point) and 'x' (Current point) as arguments.\n"
                                       "Note: 'x' is calculated each Step interval.\n"
                                       "Note: you can use the python libraries 'math' and 'random'.")
        self.description_text.setFont(QFont("Arial", 14, italic=True))
        self.layout.addWidget(self.description_text)

        self.input_text = QLineEdit(self)
        self.input_text.setPlaceholderText("e.g.: x**2 + 2*x + 1")
        self.input_text.textChanged.connect(self.on_plot)
        self.layout.addWidget(self.input_text)

        self.ok_button = QPushButton("Preview", self)
        self.ok_button.clicked.connect(self.on_plot)
        self.layout.addWidget(self.ok_button)

        self.ok_button = QPushButton("OK", self)
        self.ok_button.clicked.connect(self.on_ok)
        self.layout.addWidget(self.ok_button)

        self.setLayout(self.layout)
        self.set_region_func("Custom")

    def from_changed(self):
        try:
            val = int(float(self.sender().text()))
            self.min_x = val
            self.regions["Custom"]["start"] = self.min_x
        except:
            c_print("red", f"Bad text: {self.sender().text()}")

    def to_changed(self):
        try:
            val = int(float(self.sender().text()))
            self.max_x = val
            self.regions["Custom"]["end"] = self.max_x
        except:
            c_print("red", f"Bad text: {self.sender().text()}")

    def step_changed(self):
        try:
            val = int(float(self.sender().text()))
            self.step = val
        except:
            c_print("red", f"Bad text: {self.sender().text()}")

    def set_region_func(self, region_name):
        print("Region name:", region_name)
        region = self.regions[region_name]
        self.set_region_btn.setText(region_name)
        if region_name == "Custom":
            self.from_txt.setEnabled(True)
            self.from_txt.setText(str(int(region["start"])))
            self.to_txt.setEnabled(True)
            self.to_txt.setText(str(int(region["end"])))
            self.step_txt.setText(str(int(self.step)))
            self.min_x = int(region["start"])
            self.max_x = int(region["end"])
        else:
            self.from_txt.setEnabled(False)
            self.from_txt.setText(str(int(region["start"])))
            self.to_txt.setEnabled(False)
            self.to_txt.setText(str(int(region["end"])))
            self.min_x = int(region["start"])
            self.max_x = int(region["end"])
            self.step_txt.setText(str(int(self.step)))

    def on_plot(self):
        function_text = self.input_text.text()
        try:
            result = self.generate_list_from_function(function_text)
            points = [float(result[index - self.min_x]) for index in range(self.min_x, int((self.max_x + 1) / self.step))]
            try:
                self.plot_canvas.close()
                del self.plot_canvas
            except:
                pass
            self.plot_canvas = MplCanvas(parent=None, data=points)
            self.layout.addWidget(self.plot_canvas)
        except Exception as e:
            pass

    def on_ok(self):
        function_text = self.input_text.text()
        try:
            result = self.generate_list_from_function(function_text)
            # c_print("yellow", f"len results: {len(result)}; indexes: {[int((index - self.min_x) / self.step) for index in range(self.min_x, self.max_x + 1, self.step)]}")
            points = [QPointF(float(index), float(result[int((index - self.min_x) / self.step)])) for index in range(self.min_x, self.max_x + 1, self.step)]
            # c_print("cyan", f"points: {points}")
            command = SetCurvePoints(self.curve, points)
            self.curve.parent.region_line.get_undo_stack().push(command)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        try:
            self.plot_canvas.close()
            del self.plot_canvas
        except:
            pass

    def generate_list_from_function(self, func_text):
        context = {"start": self.min_x, "end": self.max_x, "math": math, "random": random}
        print(f"context: {context}; step: {self.step}")
        func = eval(f"lambda x, start=start, end=end, math=math, random=random: {func_text}", {}, context)
        c_print("green", f"Generated list: {[func(x, self.min_x, self.max_x) for x in range(0, self.max_x + 1 - self.min_x, self.step)]}")
        return [func(x, self.min_x, self.max_x) for x in range(0, self.max_x + 1 - self.min_x, self.step)]


class Envelope(QLabel):
    def __init__(self, parent=None, name="", npoints=3, min_=0.0, max_=1.0, length=32767, init_=0, interp="Quad"):
        super().__init__(parent)
        self.parent = parent
        self.region_line = self.parent.region_line
        self.setObjectName("envelope")
        self.setAutoFillBackground(True)
        self.p_width = 120
        self.p_height_collapse = 100
        self.p_height_expand = 250
        self.cursor_pos = 0
        self.setContentsMargins(0, 0, 0, 0)
        self.param_frame = QFrame()
        self.param_frame.setObjectName("curve-param-frame")
        self.param_frame.setContentsMargins(0, 0, 0, 0)
        self.param_frame.setFixedWidth(self.p_width)
        self.name = name
        self.min = min_
        self.max = max_
        self.is_enabled = False
        self.snap_to_grid = False
        self.was_triggered = 0
        self.npoints = max(3, npoints)
        self.length = length
        self.interp = interp
        self.zoom = 1.0
        self.params_widget = EnvelopeParams(envelope=self)
        self.curve = CurveXY(parent=self, npoints=self.npoints, minX=0, maxX=self.length, minY=self.min, maxY=self.max, initial_valuesY=init_, interp=self.interp, log_scale=False, name=self.name)
        self.lay = QHBoxLayout()
        self.lay.setSpacing(0)
        self.lay.addWidget(self.curve, alignment=Qt.AlignmentFlag.AlignLeft)
        self.lay.setSpacing(0)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.lay)
        print(f"self.params_widget.height() at init is: {self.params_widget.height()}")
        self.setFixedHeight(self.params_widget.height())
        self.curve.setFixedHeight(self.params_widget.height())
        self.setFixedWidth(self.curve.width())
        print(f"CurveXY height: {self.curve.height()}; EnvelopeParams height: {self.params_widget.height()}; Envelope height: {self.height()}")

    def set_snap_to_grid(self, snap):
        self.snap_to_grid = snap
        self.curve.set_snap_to_grid(self.snap_to_grid)

    def getParamFrame(self):
        # return self.param_frame
        return self.params_widget

    def zoom_in(self):
        self.zoom *= 2.0
        self.curve.zoom_in()
        self.setFixedWidth(self.curve.width() + self.param_frame.width())

    def zoom_out(self):
        self.zoom /= 2.0
        self.curve.zoom_out()
        self.setFixedWidth(self.curve.width() + self.param_frame.width())

    def get_undo_stack(self):
        return self.parent.get_undo_stack()

    def set_cursor(self, cursor_pos):
        self.cursor_pos = int(cursor_pos)
        self.curve.set_cursor(self.cursor_pos)

    def move_points(self, from_, to_, move):
        self.curve.move_points(from_, to_, move)

    def stretch_points(self, old_region, from_, to_):
        self.curve.stretch_points(old_region, from_, to_)

    def change_length(self, new_length):
        self.length = new_length
        self.curve.change_length(new_length)

    def isTickInTrig(self, tick, n_ticks):
        if float(tick) in self.curve.x_values:
            self.was_triggered = MIN_TRIG_DELTA_PPQN
            return 1
        return 0

    def computeValueFromTick(self, tick, n_ticks):
        x_frac = tick * (self.curve.x_values[-1] / n_ticks)
        x = int(x_frac)
        nearest_x = min(self.curve.x_values, key=lambda y: abs(x - y))
        nearest_i = self.curve.x_values.index(nearest_x)
        if x == nearest_x:
            return self.curve.curve[nearest_i]
        else:
            if x < nearest_x:
                nxt_x = nearest_x
                nxt_v = self.curve.curve[nearest_i]
                prv_i = functions.clip(nearest_i - 1, 0, len(self.curve.x_values) - 1)
                prv_x = self.curve.x_values[prv_i]
                prv_v = self.curve.curve[prv_i]
                if nxt_x == prv_x:
                    return prv_v
                else:
                    frac = np.clip(1.0 - ((nearest_x - x_frac) / (nxt_x - prv_x)), 0.0, 1.0)
                    # print("x < nearest_x", "tick:", tick, "x:", x, "previous x:", prv_x, "next x:", nxt_x, "frac:", frac)
                    if prv_v == nxt_v:
                        return prv_v
                    else:
                        return prv_v + ((nxt_v - prv_v) * frac)
            else:
                prv_x = self.curve.x_values[nearest_i]
                prv_v = self.curve.curve[nearest_i]
                nxt_i = functions.clip(nearest_i + 1, 0, len(self.curve.curve) - 1)
                nxt_x = self.curve.x_values[nxt_i]
                nxt_v = self.curve.curve[nxt_i]
                if nxt_x == prv_x:
                    return prv_v
                else:
                    frac = np.clip((x_frac - prv_x) / (nxt_x - prv_x), 0.0, 1.0)
                    # print("x > nearest_x", "tick:", tick, "x:", x, "previous x:", prv_x, "next x:", nxt_x, "frac:", frac)
                    if prv_v == nxt_v:
                        return prv_v
                    else:
                        return prv_v + ((nxt_v - prv_v) * frac)

    def isEnabled(self):
        # return self.params_widget.enabled_check.isChecked()
        return self.is_enabled

    def setEnabled(self, enabled: bool) -> None:
        # self.params_widget.enabled_check.setChecked(enabled)
        self.is_enabled = enabled

    def changeAspect(self):
        print(f"self.params_widget.height() at changeAspect is: {self.params_widget.height()}")
        if self.params_widget.expand_btn.isChecked():
            # self.setFixedHeight(self.p_height_expand)
            self.setFixedHeight(self.params_widget.height())
            self.curve.setFixedHeight(self.params_widget.height())
        else:
            # self.setFixedHeight(self.p_height_collapse)
            self.setFixedHeight(self.params_widget.height())
            self.curve.setFixedHeight(self.params_widget.height())
        self.parent.computeHeight()

    def updateVisible(self):
        self.params_widget.update(self.region_line.getVisibleRect())

    def expand(self):
        self.params_widget.expand_btn.setChecked(True)
        self.setMinimumHeight(250)
        self.setFixedHeight(250)
        self.setMaximumHeight(250)
        self.parent.computeHeight()

    def collapse(self):
        self.params_widget.expand_btn.setChecked(False)
        self.setMinimumHeight(100)
        self.setFixedHeight(100)
        self.setMaximumHeight(100)
        self.parent.computeHeight()

    def change_interp_func(self):
        action = self.sender()
        self.curve.setInterp(action.text())
        self.params_widget.interp_btn.setText(action.text())
        self.update(self.region_line.getVisibleRect())

    def change_scale_func(self):
        action = self.sender()
        self.curve.setScale(action.text())
        self.params_widget.scale_btn.setText(action.text())
        self.update(self.region_line.getVisibleRect())

    def setInterp(self, interp):
        self.interp = interp
        self.curve.setInterp(interp)

    def setMin(self, value):
        self.min = value
        self.curve.setMin(value)

    def setMax(self, value):
        self.max = value
        self.curve.setMax(value)

    def paintEvent(self, event):
        pass

    def __getstate__(self):
        d = {
            "npoints": self.npoints,
            "min": self.min,
            "max": self.max,
            "length": self.length,
            "interp": self.interp,
            "enabled": self.isEnabled(),
            "curve": self.curve.__getstate__(),
            "params_widget": self.params_widget
        }
        return d

    def __setstate__(self, state):
        self.npoints = state["npoints"]
        self.min = state["min"]
        self.max = state["max"]
        self.length = state["length"]
        self.interp = state["interp"]
        self.curve.__setstate__(state["curve"])
        self.setEnabled(state["enabled"])
        self.params_widget = EnvelopeParams(envelope=self)
        # TODO: implement __setstate__ method for EnvelopeParams Widget
        try:
            self.params_widget.__setstate__(state["params_widget"])
        except:
            c_print("yellow", "WARNING: Envelope has no params_widget saved! Please check and resave the file to remove this discrepancy.")
        # self.params_widget.enabled_check.setChecked(state["enabled"])
        self.collapse()
        self.update()


class EnvelopePointSettings(QDialog):
    def __init__(self, parent, curve=None, point_val=0, point_pos=0):
        super(EnvelopePointSettings, self).__init__(parent)
        self.curve = curve
        self.val = QLineEdit(self)
        self.pos = QLineEdit(self)

        val_valid = QDoubleValidator(self.curve.minY, self.curve.maxY, 5)
        pos_valid = QDoubleValidator(self.curve.minX, self.curve.maxX, 5)

        self.val.setValidator(val_valid)
        self.pos.setValidator(pos_valid)

        self.val.setText(str(point_val))
        self.pos.setText(str(point_pos))

        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)

        layout = QFormLayout(self)
        layout.addRow("Value", self.val)
        layout.addRow("Position", self.pos)
        layout.addWidget(buttonBox)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def getInputs(self):
        return float(self.val.text()), float(self.pos.text())

