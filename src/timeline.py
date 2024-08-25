from primitives import *
from supercollider import *
from curves import *
import numpy as np
from datetime import time as dtime
from graphics import *

class WidgetParams(QWidget):
    def __init__(self, parent=None, widget_curves=None):
        super(WidgetParams, self).__init__(parent)
        self.parent = parent
        self.widget_curves = widget_curves

        self.expanding_params_lay = QVBoxLayout()
        self.expanding_params_lay.setSpacing(0)
        self.expanding_params_lay.setContentsMargins(0, 0, 0, 0)
        self.expanding_params_wid = QWidget()
        self.expanding_params_wid.setLayout(self.expanding_params_lay)
        self.params_wid = QWidget()
        self.params_lay = QVBoxLayout()
        self.params_lay.setSpacing(0)
        self.params_lay.setContentsMargins(0, 0, 0, 0)
        self.params_wid.setHidden(True)
        self.expand_params_btn = QPushButton(self.widget_curves.name)
        self.expand_params_btn.setObjectName("widget-curves-name")
        self.expand_params_btn.setCheckable(True)
        self.expand_params_btn.setFixedHeight(25)
        self.expand_params_btn.clicked.connect(self.widget_curves.show_curves)
        self.param_frames = {}
        for env_key in self.widget_curves.envelopes.keys():
            self.param_frames[env_key] = self.widget_curves.envelopes[env_key].getParamFrame()
            self.params_lay.addWidget(self.param_frames[env_key], 0, Qt.AlignmentFlag.AlignLeft)
        self.params_wid.setLayout(self.params_lay)
        self.expanding_params_lay.addWidget(self.expand_params_btn)
        self.expanding_params_lay.addWidget(self.params_wid)
        self.setLayout(self.expanding_params_lay)


class WidgetCurves(QLabel):
    def __init__(self, parent=None, region_line=None, name="", synth_args=None, uuid=None, npoints=32767):
        super(WidgetCurves, self).__init__(parent)
        self.setObjectName("widget-curves")
        self.parent = parent
        self.name = name
        self.region_line = region_line

        assert uuid > 0
        self.uuid = uuid
        if synth_args is not None:
            self.synth_args = deepcopy(synth_args)
        else:
            self.synth_args = {}
        # print("Synth Args:", self.synth_args)
        self.npoints = npoints
        self.zoom = 1.0
        self.cursor_pos = 0
        self.anchor = False
        self.snap_to_grid = False
        # Main Layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setMargin(0)

        # Widget GUI
        self.expand_btn = QPushButton(self.name)
        self.expand_btn.setObjectName("widget-curves-name")
        self.expand_btn.setCheckable(True)
        self.expand_btn.setFixedHeight(25)
        self.expand_btn.clicked.connect(self.show_curves)

        # Curves GUI
        self.lay = QVBoxLayout()
        self.envelopes_wid = QWidget()
        self.envelopes_wid.setHidden(True)
        self.envelopes = {}
        for key in self.synth_args.keys():
            pa = self.synth_args[key]
            if pa["type"] != "buffer" and pa["type"] != "patch_buffer" and pa["type"] != "AmbisonicsKernel":
                self.envelopes[key] = Envelope(parent=self, name=pa["desc"], npoints=3, min_=pa["min"], max_=pa["max"], init_=pa["val"], length=self.npoints, interp="Quad")
                self.lay.addWidget(self.envelopes[key], 0, Qt.AlignmentFlag.AlignLeft)
        self.lay.setSpacing(0)
        self.lay.setContentsMargins(0, 0, 0, 0)

        self.envelopes_wid.setLayout(self.lay)
        self.main_layout.addWidget(self.expand_btn)
        self.main_layout.addWidget(self.envelopes_wid)
        self.setLayout(self.main_layout)
        self.widget_params = WidgetParams(widget_curves=self)
        self.computeWidth()
        self.computeHeight()

    def getParamsWidget(self):
        return self.widget_params

    def zoom_in(self):
        self.zoom *= 2.0
        self.setFixedWidth(int(self.npoints * 2))
        for key in self.envelopes.keys():
            self.envelopes[key].zoom_in()

    def zoom_out(self):
        self.zoom /= 2.0
        self.setFixedWidth(int(self.npoints / 2))
        for key in self.envelopes.keys():
            self.envelopes[key].zoom_out()

    def get_undo_stack(self):
        return self.parent.get_undo_stack()

    def move_points(self, from_, to_, move):
        if self.anchor:
            for key in self.envelopes.keys():
                self.envelopes[key].move_points(from_, to_, move)

    def stretch_points(self, old_region, from_, to_):
        if self.anchor:
            for key in self.envelopes.keys():
                self.envelopes[key].stretch_points(old_region, from_, to_)

    def set_anchor(self, anchor):
        self.anchor = anchor

    def set_snap_to_grid(self, snap):
        self.snap_to_grid = snap
        for key in self.envelopes.keys():
            self.envelopes[key].set_snap_to_grid(self.snap_to_grid)

    def set_cursor(self, cursor_pos):
        self.cursor_pos = cursor_pos * self.zoom
        for key in self.envelopes.keys():
            self.envelopes[key].set_cursor(self.cursor_pos)

    def change_length(self, new_length):
        self.npoints = new_length
        for key in self.envelopes.keys():
            self.envelopes[key].change_length(self.npoints)

    def show_curves(self):
        c_print("green", "Clicked on Show Curves")
        if self.sender() == self.widget_params.expand_params_btn:
            self.widget_params.params_wid.setHidden(not self.widget_params.expand_params_btn.isChecked())
            self.expand_btn.setChecked(self.widget_params.expand_params_btn.isChecked())
            self.envelopes_wid.setHidden(not self.expand_btn.isChecked())
        elif self.sender() == self.expand_btn:
            self.envelopes_wid.setHidden(not self.expand_btn.isChecked())
            self.widget_params.expand_params_btn.setChecked(self.expand_btn.isChecked())
            self.widget_params.params_wid.setHidden(not self.widget_params.expand_params_btn.isChecked())
        self.computeHeight()

    def change_curves_width(self, new_width):
        for key in self.envelopes.keys():
            self.envelopes[key].setFixedWidth(new_width)

    def computeWidth(self):
        keys = list(self.envelopes.keys())
        if len(keys) > 0:
            self.setFixedWidth(self.envelopes[keys[0]].width())

    def matchHeights(self):
        for key in self.envelopes.keys():
            self.envelopes[key].params_widget.setFixedHeight(140)
            self.envelopes[key].setFixedHeight(self.envelopes[key].params_widget.height())
            self.envelopes[key].curve.setFixedHeight(self.envelopes[key].params_widget.height())
            c_print("yellow", f"WidgetParams Height is: {self.envelopes[key].params_widget.height()} CurveXY Height is {self.envelopes[key].curve.height()} Envelope Height is {self.envelopes[key].height()}")

    def computeHeight(self):
        # height = self.expand_btn.height()
        # TODO: rimuovere questo settaggio critico alla riga seguente: "height = 17"
        height = 17
        self.matchHeights()
        if self.expand_btn.isChecked():
            for key in self.envelopes.keys():
                height += self.envelopes[key].curve.height()
            self.setFixedHeight(height)
            # self.setFixedHeight(self.widget_params.height())
        else:
            self.setFixedHeight(height)
        print(f"sdtting expanding_params_wid height to: {height}")
        self.widget_params.expanding_params_wid.setFixedHeight(height)

    def __getstate__(self):
        d = {"uuid": self.uuid, "synth_args": self.synth_args, "name": self.name, "envelopes": {}}
        for key in self.envelopes.keys():
            d["envelopes"][key] = self.envelopes[key].__getstate__()
        return d

    def __setstate__(self, state):
        self.uuid = state["uuid"]
        self.synth_args = state["synth_args"]
        self.name = state["name"]
        for i in reversed(range(0, self.lay.count())):
            self.lay.itemAt(i).widget().setParent(None)
        self.envelopes = {}
        for key in self.synth_args.keys():
            pa = self.synth_args[key]
            if pa["type"] != "buffer" and pa["type"] != "patch_buffer" and pa["type"] != "AmbisonicsKernel":
                self.envelopes[key] = Envelope(parent=self, name=pa["desc"], npoints=3, min_=pa["min"], max_=pa["max"], init_=pa["val"], length=self.npoints, interp="Quad")
                self.envelopes[key].__setstate__(state["envelopes"][key])
                self.lay.addWidget(self.envelopes[key])
        self.widget_params = WidgetParams(widget_curves=self)


class RegionLine(QLabel):
    def __init__(self, parent=None, length=4096):
        super(RegionLine, self).__init__(parent)
        self.time_line = parent
        self.region_manager = None
        self.setObjectName("region-line")
        self.setMouseTracking(True)
        self.ppqn_per_pixel = 10
        self.pixel_step = PPQN
        self.length = length
        self.clock = None
        self.zoom = 1.0
        self.cursor_pos = 0
        self.regions = {}
        self.current_region = ""
        self.current_region_kind = "move"
        self.current_region_copy = None
        self.tmp_region_start = -1
        self.tmp_region_end = self.tmp_region_start
        self.setFixedHeight(50)
        self.setFixedWidth(int(self.length * self.zoom))

    def get_undo_stack(self):
        return self.time_line.patch.patch_area.get_undo_stack()

    def getVisibleRect(self):
        return QRect(self.time_line.main_scroll.horizontalScrollBar().value(), 0, self.time_line.main_scroll.width(), self.time_line.main_scroll.height())

    def update_cursor_pos(self, cursor_pos):
        self.cursor_pos = cursor_pos / self.zoom
        self.updateCursors()
        self.update(self.getVisibleRect())

    def updateCursors(self):
        for key in self.time_line.widget_curves.keys():
            wcurve = self.time_line.widget_curves[key]
            wcurve.set_cursor(self.cursor_pos)

    def mousePressEvent(self, event):
        # Check if delete Region first!
        if event.button() == Qt.MouseButton.RightButton:
            for key in self.regions.keys():
                region = self.regions[key]
                if region["start"] <= event.position().x() / self.zoom <= region["end"]:  # If clicking a region
                    del self.regions[key]
                    self.time_line.region_manager.refresh_regions()
                    event.accept()
                    break
        else:  # Check if inside Region
            self.cursor_pos = int(event.position().x() / self.zoom)
            self.updateCursors()
            for key in self.regions.keys():
                region = self.regions[key]
                if region["start"] <= event.position().x() / self.zoom <= region["end"]:  # If clicking a region
                    self.current_region = key
                    self.current_region_copy = region.copy()
                    if ((event.position().x() / self.zoom) - region["start"]) < 10:  # If clicking the left corner, then "left"
                        self.current_region_kind = "left"
                    elif (region["end"] - (event.position().x() / self.zoom)) < 10:  # If clicking the right corner, then "right"
                        self.current_region_kind = "right"
                    else:  # If clicking the middle, then "move"
                        self.current_region_kind = "move"
                    print(self.current_region_kind)
            # Start Region if dragging outside regions
            self.tmp_region_start = self.cursor_pos
            self.tmp_region_end = self.tmp_region_start
        self.getVisibleRect()
        self.update(self.getVisibleRect())

    def mouseMoveEvent(self, event):
        delta = int((event.position().x() - (self.cursor_pos * self.zoom)) / self.zoom)
        if not self.current_region:  # If no Region is selected, create new temp region
            self.tmp_region_end = int(event.position().x() / self.zoom)
        else:  # If Region is selected
            if self.current_region_kind == "left":
                self.regions[self.current_region]["start"] = int(event.position().x() / self.zoom)
                # self.time_line.stretch_points(self.current_region_copy, self.regions[self.current_region]["start"] - 1, self.regions[self.current_region]["end"] + 1)
                # self.current_region_copy = self.regions[self.current_region].copy()
            elif self.current_region_kind == "right":
                self.regions[self.current_region]["end"] = int(event.position().x() / self.zoom)
                # self.time_line.stretch_points(self.current_region_copy, self.regions[self.current_region]["start"] - 1, self.regions[self.current_region]["end"] + 1)
                # self.current_region_copy = self.regions[self.current_region].copy()
            elif self.current_region_kind == "move":
                if delta != 0:
                    self.time_line.move_points(self.regions[self.current_region]["start"] - 1, self.regions[self.current_region]["end"] + 1, delta)
                    self.regions[self.current_region]["start"] += delta
                    self.regions[self.current_region]["end"] += delta
        self.cursor_pos += delta
        self.updateCursors()
        self.getVisibleRect()
        self.update(self.getVisibleRect())

    def mouseReleaseEvent(self, event):
        self.tmp_region_end = int(event.position().x() / self.zoom)
        if self.tmp_region_start > 0 and not self.current_region:  # If no Region is selected and tmp Region is wide enough, create new temp region
            if abs(self.tmp_region_end - self.tmp_region_start) > 20:
                tmp = {
                    "name": "tmp",
                    "start": min(self.tmp_region_start, self.tmp_region_end),
                    "end": max(self.tmp_region_start, self.tmp_region_end),
                    # "length": max(self.tmp_region_start, self.tmp_region_end) - min(self.tmp_region_start, self.tmp_region_end),
                    "program": -1
                }
                self.addRegion(tmp)
        if self.current_region_kind == "left" or self.current_region_kind == "right":
            self.time_line.stretch_points(self.current_region_copy, self.regions[self.current_region]["start"] - 1, self.regions[self.current_region]["end"] + 1)
            if self.time_line.main_window.region_manager.active_region == self.regions[self.current_region]["name"]:
                print("Updating current region play length for region: " + self.current_region)
                self.time_line.main_window.clock.set_bounds(self.regions[self.current_region]["start"], self.regions[self.current_region]["end"])
        self.current_region = ""
        self.tmp_region_start = -1
        self.tmp_region_end = -1
        self.update(self.getVisibleRect())

    def change_length(self, new_length):
        self.length = new_length
        self.setFixedWidth(int(self.length * self.zoom))
        self.update(self.getVisibleRect())

    def zoom_in(self):
        self.zoom *= 2.0
        self.setFixedWidth(int(self.length * self.zoom))
        print(self.zoom)
        self.update(self.getVisibleRect())

    def zoom_out(self):
        self.zoom /= 2.0
        self.setFixedWidth(int(self.length * self.zoom))
        print(self.zoom)
        self.update(self.getVisibleRect())

    def addRegion(self, region):
        edit_region = EditRegionDialog(region, self)
        edit_region.exec()
        if edit_region:
            region = {
                "name": edit_region.getRegionName(),
                "start": edit_region.getRegionStart(),
                "end": edit_region.getRegionEnd(),
                "program": -1
            }
            self.regions[region["name"]] = region
            print("Timeline:", self.time_line)
            print("region_manager:", self.time_line.main_window.region_manager)
            self.time_line.main_window.region_manager.refresh_regions()
            print("Region added:", region)
            self.update(self.getVisibleRect())

    def getRegions(self):
        return self.regions

    def setClock(self, clock):
        self.clock = clock

    def getTimeOfTick(self, tick):
        t_millis = int(1000 * (60. / self.clock.getBPM()) * (tick / PPQN))
        ms = int(t_millis % 1000)
        s = int((t_millis / 1000) % 60)
        m = int((t_millis / 60000) % 60)
        h = int((t_millis / 3600000) % 24)
        return str(h) + ":" + str(m) + ":" + str(s) + "." + str(ms)[:3]

    def getTickOfSeconds(self, seconds):
        return int((self.clock.getBPM() * PPQN * seconds) / 60.)

    def getSecondsOfTick(self, tick):
        return (60. / self.clock.getBPM()) * (tick / PPQN)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(1.0)
        painter.setFont(QFont("Arial", 6))
        pen = QPen()
        pen.setColor(Qt.GlobalColor.darkGreen)
        painter.setPen(pen)
        # Times
        for x in range(0, self.width(), self.pixel_step):
            i = int(x / self.zoom)
            painter.drawLine(x, 0, x, self.height())
            # painter.drawText(QPoint(x + 2, 10), str(i))
            # measure text
            painter.drawText(QPoint(x + 2, 10), str(int(i / (PPQN * 4))) + ":" + str(int((i / PPQN) % 4)))
            # time text
            if self.clock is not None:
                painter.drawText(QPoint(x + 2, 16), self.getTimeOfTick(i))
        # Cursor
        painter.drawLine(int(self.cursor_pos * self.zoom), 0, int(self.cursor_pos * self.zoom), self.height())
        painter.drawText(QPoint(int(self.cursor_pos * self.zoom), 10), "cursor")

        # Tmp Region
        painter.setOpacity(0.5)
        if self.tmp_region_start > 0:
            painter.fillRect(QRect(QPoint(int(min(self.tmp_region_start, self.tmp_region_end) * self.zoom), 0), QPoint(int(max(self.tmp_region_start, self.tmp_region_end) * self.zoom), self.height())), Qt.GlobalColor.darkGreen)
        # Regions
        painter.setFont(QFont("Arial", 16))
        pen.setColor(Qt.GlobalColor.black)
        painter.setPen(pen)
        self.draw_regions(painter)

    def draw_regions(self, painter):
        for key in self.regions.keys():
            region = self.regions[key]
            start = int(region["start"] * self.zoom)
            end = int(region["end"] * self.zoom)
            rect = QRect(QPoint(start, 0), QPoint(end, self.height()))

            # Create a gradient fill
            gradient = QLinearGradient(start, 0, end, self.height())
            gradient.setColorAt(0, Qt.GlobalColor.red)
            gradient.setColorAt(1, Qt.GlobalColor.darkRed)
            painter.setBrush(QBrush(gradient))

            # Draw rounded rectangle
            painter.setPen(Qt.GlobalColor.black)
            painter.drawRoundedRect(rect, 10, 10)
            painter.fillRect(rect, QBrush(gradient))

            # Draw text with shadow effect
            text_pos = QPoint(int(start + 5), self.height() - 10)
            shadow_offset = QPoint(2, 2)

            painter.setPen(Qt.GlobalColor.black)
            painter.drawText(text_pos + shadow_offset, region["name"])

            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(text_pos, region["name"])

    def __getstate__(self):
        d = {
            "regions": self.regions
        }
        return d

    def __setstate__(self, state):
        self.regions = state["regions"]


class EditRegionDialog(QDialog):
    def __init__(self, region, region_line, parent=None):
        super().__init__(parent)
        self.region = region
        print("Region:", self.region)
        self.region_line = region_line
        self.setWindowTitle("Edit Region")

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QVBoxLayout()

        self.name_lay = QHBoxLayout()
        self.name_lbl = QLabel("Name:")
        self.name = QLineEdit(self.region["name"])
        self.name_lay.addWidget(self.name_lbl)
        self.name_lay.addWidget(self.name)
        self.layout.addLayout(self.name_lay)

        self.start_lay = QHBoxLayout()
        self.start_lbl = QLabel("Region Start (sec):")
        self.start = QLineEdit(str(round(self.region_line.getSecondsOfTick(self.region["start"]), 3)))
        self.start_valid = QDoubleValidator(0.0, 1000.0, 4)
        self.start.setValidator(self.start_valid)
        self.start_lay.addWidget(self.start_lbl)
        self.start_lay.addWidget(self.start)
        self.layout.addLayout(self.start_lay)

        self.end_lay = QHBoxLayout()
        self.end_lbl = QLabel("Region End (sec):")
        self.end = QLineEdit(str(round(self.region_line.getSecondsOfTick(self.region["end"]), 3)))
        self.end_valid = QDoubleValidator(0.0, 1000.0, 4)
        self.end.setValidator(self.end_valid)
        self.end_lay.addWidget(self.end_lbl)
        self.end_lay.addWidget(self.end)
        self.layout.addLayout(self.end_lay)

        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def getRegionStart(self):
        return self.region_line.getTickOfSeconds(float(self.start.text()))

    def getRegionEnd(self):
        return self.region_line.getTickOfSeconds(float(self.end.text()))

    def getRegionName(self):
        return self.name.text()


class RegionManager(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.time_line = self.main_window.timeline
        self.region_line = self.time_line.region_line
        self.regions_buttons = {}
        self.active_region = ""
        self.layout = QHBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setFixedHeight(40)

        # Meter Enable/Disable
        self.meter_btn = QPushButton(QIcon(os.path.join(GRAPHICS_PATH, "AudioMeter.svg")), "")
        self.meter_btn.setObjectName("palette")
        self.meter_btn.setFixedWidth(40)
        self.meter_btn.setCheckable(True)
        self.meter_btn.clicked.connect(self.set_meter_enable)
        # self.set_meter_enable()
        self.meter_btn.setChecked(True)
        self.layout.addWidget(self.meter_btn)

        # Anchor
        self.anchor_btn = QPushButton(QIcon(os.path.join(GRAPHICS_PATH, "Anchor.svg")), "")
        self.anchor_btn.setObjectName("palette")
        self.anchor_btn.setFixedWidth(40)
        self.anchor_btn.setCheckable(True)
        self.anchor_btn.setChecked(False)
        self.anchor_btn.clicked.connect(self.set_anchor)
        self.layout.addWidget(self.anchor_btn)

        # Shap To Grid
        self.snap_to_grid_btn = QPushButton(QIcon(os.path.join(GRAPHICS_PATH, "SnapToGrid.svg")), "")
        self.snap_to_grid_btn.setObjectName("palette")
        self.snap_to_grid_btn.setFixedWidth(40)
        self.snap_to_grid_btn.setCheckable(True)
        self.snap_to_grid_btn.setChecked(False)
        self.snap_to_grid_btn.clicked.connect(self.set_snap_to_grid)
        self.layout.addWidget(self.snap_to_grid_btn)

        # Region Play Type
        self.region_play_type = QPushButton(QIcon(os.path.join(GRAPHICS_PATH, "Loop.svg")), "")
        self.region_play_type.setObjectName("palette")
        self.region_play_type.setFixedWidth(40)
        self.region_play_type.setCheckable(True)
        self.region_play_type.setChecked(False)
        # self.main_window.clock.set_region_play_type(self.region_play_type.isChecked())
        self.main_window.clock.set_region_play_type(False)
        self.region_play_type.clicked.connect(self.switch_region_play_type)
        self.layout.addWidget(self.region_play_type)

        self.regions_lay = QHBoxLayout()
        self.layout.addLayout(self.regions_lay)
        spacer = QSpacerItem(40, 40, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.layout.addItem(spacer)

        self.setLayout(self.layout)
        self.refresh_regions()

    def reloadParents(self, main_window):
        self.main_window = main_window
        self.time_line = self.main_window.timeline
        self.region_line = self.time_line.region_line

    def set_anchor(self):
        self.time_line.set_anchor(self.anchor_btn.isChecked())

    def set_meter_enable(self):
        self.main_window.patch.set_meter_enable(self.meter_btn.isChecked())

    def set_snap_to_grid(self):
        self.time_line.set_snap_to_grid(self.snap_to_grid_btn.isChecked())

    def switch_region_play_type(self, value):
        # self.main_window.clock.set_region_play_type(not self.region_play_type.isChecked())
        self.main_window.clock.set_region_play_type(self.region_play_type.isChecked())

    def refresh_regions(self):
        # Cleanup
        self.regions_buttons = {}
        for i in reversed(range(self.regions_lay.count())):
            self.regions_lay.itemAt(i).widget().setParent(None)
        # New Regions
        for key in self.region_line.regions.keys():
            self.regions_buttons[key] = QPushButton(key)
            self.regions_buttons[key].setCheckable(True)
            self.regions_buttons[key].clicked.connect(lambda v, k=key: self.activate_region(value=v, which=k))
            self.regions_lay.addWidget(self.regions_buttons[key])

    def activate_region(self, value, which):
        # Set active region
        ## Use this if you want a selection to always be enalbed at all times
        self.active_region = which
        self.main_window.clock.goToTick(self.region_line.regions[which]["start"])
        self.main_window.clock.set_bounds(self.region_line.regions[which]["start"], self.region_line.regions[which]["end"])
        for key in self.regions_buttons.keys():
            if key != which:
                self.regions_buttons[key].blockSignals(True)  # Use this to do not trigger the action when checking
                self.regions_buttons[key].setChecked(False)
                self.regions_buttons[key].blockSignals(False)
        self.regions_buttons[which].blockSignals(True)  # Use this to do not trigger the action when checking
        self.regions_buttons[which].setChecked(False)
        self.regions_buttons[which].blockSignals(False)

        ## Use this if you want to allow no region selected
        # if value:
        #     self.active_region = which
        #     self.main_window.clock.goToTick(self.region_line.regions[which]["start"])
        #     self.main_window.clock.set_bounds(self.region_line.regions[which]["start"], self.region_line.regions[which]["end"])
        # else:
        #     self.active_region = ""
        #     self.main_window.clock.remove_bounds()
        # Set all other regions to False
        # for key in self.regions_buttons.keys():
        #     if key != which:
        #         self.regions_buttons[key].blockSignals(True)  # Use this to do not trigger the action when checking
        #         self.regions_buttons[key].setChecked(False)
        #         self.regions_buttons[key].blockSignals(False)


