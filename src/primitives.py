import ast
import math
import time

from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from parameters import *
from supercollider import *
import json
from copy import deepcopy
from classes import Note
from log_coloring import c_print
from harmony import *
from path_manager import STYLE_PATH, CONFIG_PATH, GRAPHICS_PATH

conf = cp.ConfigParser()
conf.read(CONFIG_PATH)  # "config.ini"
try:
    PPQN = conf.getint("GENERAL", "ppqn")
    BUS_VISUAL_UPDATE_FREQ = conf.getfloat("SCSYNTH", "BUS_VISUAL_UPDATE_FREQ")
    SCSYNTH_SYNTHDEF_PATH = conf.get("SCSYNTH", "synthdef_path")
    _6color_palette_01 = conf.get("APPEARENCE", "6color_palette_01")
    _6color_palette_02 = conf.get("APPEARENCE", "6color_palette_02")
    _6color_palette_03 = conf.get("APPEARENCE", "6color_palette_03")
    _6color_palette_04 = conf.get("APPEARENCE", "6color_palette_04")
    _6color_palette_05 = conf.get("APPEARENCE", "6color_palette_05")
    _6color_palette_06 = conf.get("APPEARENCE", "6color_palette_06")
except:
    c_print("red", "[ERROR]: Config File not found")
    PPQN = 96
    BUS_VISUAL_UPDATE_FREQ = 20.0
    SCSYNTH_SYNTHDEF_PATH = "/Users/francescodani/Library/Application Support/SuperCollider/synthdefs"
    _6color_palette_01 = "#242326"
    _6color_palette_02 = "#242326"
    _6color_palette_03 = "#323436"
    _6color_palette_04 = "#323436"
    _6color_palette_05 = "#464850"
    _6color_palette_06 = "#464850"


class QLabelT(QLabel):
    """
    A QLabel with a QToolTip.

    Attributes:
        parent (QWidget or None): Parent.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setToolTip("")

    def enterEvent(self, event):
        """
        Shows the QToolTip when mouse enters the QLabel.
        """
        QToolTip.showText(QCursor.pos(), self.toolTip())


class AudioMeter(QWidget):
    updateAmplitudeSignal = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(25)
        self.setMaximumHeight(25)
        self.setMinimumWidth(100)
        self.amplitude = 0.0  # Amplitude value between 0.0 and 1.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_thread_func)
        self.timer.start(int(1000 / BUS_VISUAL_UPDATE_FREQ))

    def update_in_thread(self):
        self.update()

    def update_thread_func(self):
        self.update()

    def setAmplitude(self, amp):
        self.amplitude = max(0.0, min(amp, 4.0))

    def paintEvent(self, event):
        painter = QPainter(self)
        font = painter.font()
        font.setWeight(8)
        font.setPointSize(8)
        painter.setFont(font)
        rect = self.rect()

        # Draw gradient bar
        gradient = QLinearGradient(0, 0, rect.width(), 0)
        gradient.setColorAt(0.0, QColor(0, 0, 255))  # Blue
        gradient.setColorAt(0.5, QColor(0, 255, 0))  # Green
        gradient.setColorAt(1.0, QColor(255, 0, 0))  # Red

        painter.fillRect(rect.adjusted(0, 20, 0, 0), gradient)

        # Convert amplitude to dB
        if self.amplitude > 0:
            db_value = 20 * math.log10(self.amplitude)
        else:
            db_value = -60  # Minimum dB value for silence

        # Clamp dB value to range
        db_value = max(-60, min(db_value, 12))

        # Convert dB value to width position
        level_width = (db_value + 60) / 72 * rect.width()
        painter.fillRect(QRect(int(level_width), 20, rect.width(), rect.height() - 20), QColor(0, 0, 0, 200))

        # Draw dB scale
        n_steps = 20 - max(2, min(18, int(self.width() / 30)))
        for i in range(-60, 13, n_steps):
            x = int(rect.width() * (i + 60) / 72)
            painter.drawText(x, 0, 25, 20, Qt.AlignmentFlag.AlignLeft, f'{i}dB')
            painter.drawLine(x, 10, x, 20)


class PlaceCable(QUndoCommand):
    def __init__(self, widget_in, inlet, type):
        super().__init__(f"Placing {type} Cable")
        self.widget_in = widget_in
        self.patch_area = self.widget_in.patch_area
        self.inlet = inlet
        self.type = type
        self.cable = self.patch_area.current_cable
        # print(f"self.cable is {self.cable}")

    def undo(self):
        if self.cable is not None:
            if type(self.widget_in) == SubPatchInstanceWidget:
                self.widget_in.subpatch.update_subpatch_instances()
                # print("SubPatchInstanceWidget -> self.widget_in.subpatch.update_subpatch_instances()")
                # print(self.widget_in, self.inlet)
                self.cable.disconnectSubPatchWidgets()
            else:
                self.cable.disconnectWidgets()
            self.patch_area.flush_cable(self.cable)
            self.cable = None

    def redo(self):
        if self.cable is not None:
            # print(f"Placing {self.type} cable from widget {self.cable.widget_out} to widget {self.widget_in}")
            if self.type == "Audio":
                if type(self.widget_in) == SubPatchInstanceWidget:
                    self.widget_in.subpatch.update_subpatch_instances()
                    # print("SubPatchInstanceWidget -> self.widget_in.subpatch.update_subpatch_instances()")
                    # print(self.widget_in, self.inlet)
                    self.cable.addSubPatchInletWidget(self.widget_in, self.inlet)
                else:
                    self.cable.addInletWidget(self.widget_in, self.inlet)
            elif self.type == "MIDI":
                self.cable.addInletWidget(self.widget_in, self.inlet)
            self.patch_area.place_cable()
            self.patch_area.lower_cables()


class AddCable(QUndoCommand):
    def __init__(self, widget, x, y, type, widget_out, outlet_id):
        super().__init__(f"Adding {type} Cable")
        self.widget = widget
        self.x = x
        self.y = y
        self.type = type
        self.widget_out = widget_out
        self.outlet_id = outlet_id
        self.is_first_undo = True

    def undo(self):
        if self.is_first_undo:
            self.widget.destination_widgets.remove(self.cable)
            if self.widget.patch_area.is_placing_cable():
                self.widget.patch_area.flush_cable(self.cable)
            self.is_first_undo = False

    def redo(self):
        if self.is_first_undo:
            if self.type == "Audio":
                if type(self.widget) == SubPatchInstanceWidget:
                    self.cable = AudioCable(x=self.x, y=self.y, widget_out=self.widget, widget_out_id=self.outlet_id,
                                            parent=self.widget.patch_area, is_inside_subpatch=True)
                else:
                    self.cable = AudioCable(x=self.x, y=self.y, widget_out=self.widget, widget_out_id=self.outlet_id,
                                            parent=self.widget.patch_area, is_inside_subpatch=False)
                self.cable.show()
                self.widget.patch_area.add_audio_cable(self.cable)
            elif self.type == "MIDI":
                self.cable = MIDICable(x=self.x, y=self.y, widget_out=self.widget, widget_out_id=self.outlet_id,
                                       parent=self.widget.patch_area)
                self.cable.show()
                self.widget.patch_area.add_midi_cable(self.cable)
            self.widget.destination_widgets.append(self.cable)


class ParameterChange(QUndoCommand):
    def __init__(self, widget, key, value):
        super().__init__(f"Changed parameter '{key}' to {value}")
        # print(f"Changed parameter '{key}' to {value}")
        self.widget = widget
        self.key = key
        self.value = value
        self.old_value = self.widget.synth_args[key]["val"]

    def undo(self):
        try:
            args_copy = deepcopy(self.widget.synth_args)
            if args_copy[self.key]["type"] != "string":
                self.old_value = float(self.old_value)
            args_copy[self.key]["val"] = self.old_value
            self.widget.synth_args = deepcopy(args_copy)
            if self.widget.type == "Audio":
                self.widget.resetSynthArgs()
            if self.widget.type == "AudioMIDI":
                if isinstance(self.widget.synth, Synth):
                    self.widget.synth.set(self.key, self.old_value)
            try:
                self.widget.patch_area.patch.update_subpatch_instances()
                c_print("green", "update_subpatch_instances successfull")
            except:
                pass
        except:
            pass

    def redo(self):
        args_copy = deepcopy(self.widget.synth_args)
        if args_copy[self.key]["type"] != "string":
            try:
                self.value = float(self.value)
            except:
                c_print("red", "ParameterChange: Bad. self.value is:" + str(self.value))
        args_copy[self.key]["val"] = self.value
        self.widget.synth_args = deepcopy(args_copy)
        if self.widget.type == "Audio":
            self.widget.resetSynthArgs()
        if self.widget.type == "AudioMIDI":
            if isinstance(self.widget.synth, Synth):
                self.widget.synth.set(self.key, self.value)
        try:
            self.widget.patch_area.patch.update_subpatch_instances()
            # c_print("green", "update_subpatch_instances successfull")
        except:
            c_print("red", "ParameterChange: Bad. self.widget.patch_area.patch.update_subpatch_instances()")
            pass


class PatchBufferParameterChange(QUndoCommand):
    def __init__(self, widget, key, value):
        super().__init__(f"Changed patch buffer parameter '{key}' to {value}")
        self.widget = widget
        self.key = key
        self.value = value.split(":")[0]
        self.old_value = self.widget.synth_args[key]["val"]

    def undo(self):
        args_copy = deepcopy(self.widget.synth_args)
        args_copy[self.key]["val"] = int(self.old_value)
        self.widget.synth_args = deepcopy(args_copy)
        if self.widget.type == "Audio":
            self.widget.instantiateSynth()
            self.widget.resetSynthArgs()

    def redo(self):
        args_copy = deepcopy(self.widget.synth_args)
        args_copy[self.key]["val"] = int(self.value)
        self.widget.synth_args = deepcopy(args_copy)
        if self.widget.type == "Audio":
            self.widget.instantiateSynth()
            self.widget.resetSynthArgs()


class SimpleWidget(QLabel):
    def __init__(self, parent=None, n_in=0, n_out=0, n_param=0, n_midi_in=0, n_midi_out=0, uuid=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)  # Enable hover events
        if uuid is None:
            self.uuid = scsynth.queryFreeNode()
        else:
            self.uuid = uuid
        self.type = "Simple"
        self.synth_name = ""
        self.patch_area = parent
        self.is_selected = False
        self.settings_sidebar = self.patch_area.patch.parent.settings_bar
        self.setMinimumSize(200, 100)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.widget_outer_colors = {"Audio": QColor(10, 128, 20), "MIDI": QColor(128, 10, 20),
                                    "SubPatch": QColor(50, 59, 180)}
        self.widget_inner_colors = {"Audio": QColor(125, 255, 150), "MIDI": QColor(255, 125, 150),
                                    "SubPatch": QColor(100, 100, 240)}
        self.inlet_svg = {"Audio": QIcon(os.path.join(GRAPHICS_PATH, "AudioInlet_new.svg")),
                          "MIDI": QIcon(os.path.join(GRAPHICS_PATH, "MIDIInlet_new.svg"))}
        self.outlet_svg = {"Audio": QIcon(os.path.join(GRAPHICS_PATH, "AudioOutlet_new.svg")),
                           "MIDI": QIcon(os.path.join(GRAPHICS_PATH, "MIDIOutlet_new.svg"))}
        self.param_svg = {"Audio": QIcon(os.path.join(GRAPHICS_PATH, "AudioParameter_new.svg"))}
        self.xlet_size = (10, 10)
        self.delete_svg = QIcon(os.path.join(GRAPHICS_PATH, "close-circle.svg"))
        self.is_resizing = False
        # chain communication audio
        self.n_in = n_in
        self.n_out = n_out
        self.args = []
        self.synth_args = None
        self.synth_args_gui = None
        self.input_channels = [scsynth.getDefaultInBus() + i for i in range(self.n_in)]
        self.output_channels = [scsynth.getDefaultOutBus() + i for i in range(self.n_out)]
        self.n_param = n_param
        # chain communication MIDI
        self.n_midi_in = n_midi_in
        self.n_midi_out = n_midi_out
        self.midi_destinations = []
        # aspect
        self.border_color = Qt.GlobalColor.darkBlue
        self.inlet_color = Qt.GlobalColor.darkYellow
        self.midi_inlet_color = Qt.GlobalColor.darkMagenta
        self.audio_param_color = Qt.GlobalColor.darkGreen
        self.delete_color = Qt.GlobalColor.darkRed
        # param offset and displacement (in pixels)
        self.params_offset_y = 30
        self.param_displacement_y = 20
        # mouse interaction
        self.right_corner_size = 20
        self.has_to_resize = False
        self.delete_cross_rect = [10, 10, 15, 15]
        self.has_to_move = False
        self.mouse_position = QPoint(0, 0)
        # SimpleCable I/O handling
        self.source_widgets = []
        self.destination_widgets = []
        self.calcInletOutletPos()
        # Shadow effect
        self.shadow_effect = QGraphicsDropShadowEffect()
        self.setGraphicsEffect(self.shadow_effect)
        self.reduceShadow()

    def get_undo_stack(self):
        return self.patch_area.get_undo_stack()

    def setSelected(self, is_selected: bool):
        self.is_selected = is_selected
        if self.is_selected:
            self.shadow_effect.setColor(QColor(32, 128, 128, 255))
            self.enlargeShadow()
        else:
            self.shadow_effect.setColor(QColor(63, 63, 63, 180))
            self.reduceShadow()

    def isSelected(self) -> bool:
        return self.is_selected

    def getUUID(self) -> int:
        return self.uuid

    def reduceShadow(self):
        self.shadow_effect.setBlurRadius(5)
        self.shadow_effect.setOffset(2)

    def enlargeShadow(self):
        self.shadow_effect.setBlurRadius(15)
        self.shadow_effect.setOffset(8)

    def getParameterPos(self, parameter_id):
        y_pos = self.synth_args_gui[parameter_id].y() + int(self.synth_args_gui[parameter_id].height() / 2)
        return QPoint(int(self.geometry().x()), int(self.geometry().y() + y_pos))

    def getOutletPos(self, outlet_id):
        return QPoint(int(self.geometry().x() + self.outs_x[outlet_id] + 2),
                      int(self.geometry().y() + int(self.height()) - 8))

    def getMIDIOutletPos(self, midi_outlet_id):
        return QPoint(int(self.geometry().x() + self.midi_outs_x[midi_outlet_id] + 2),
                      int(self.geometry().y() + int(self.height()) - 8))

    def getInletPos(self, inlet_id):
        return QPoint(int(self.geometry().x() + self.ins_x[inlet_id] + 2), int(self.geometry().y() + 4))

    def getMIDIInletPos(self, midi_inlet_id):
        try:
            return QPoint(int(self.geometry().x() + self.midi_ins_x[midi_inlet_id] + 2), int(self.geometry().y() + 4))
        except IndexError:
            return -1

    def addDestination(self, event, widget, outlet_id, type="Audio"):
        command = AddCable(widget=self, x=self.geometry().x() + event.position().x(),
                           y=self.geometry().y() + event.position().y(), widget_out=widget, outlet_id=outlet_id,
                           type=type)
        self.get_undo_stack().push(command)

    def removeDestination(self, cable):
        self.destination_widgets.remove(cable)

    def addParameterDestination(self, event, widget, outlet_id):
        cable = AudioCable(x=self.geometry().x() + event.position().x(), y=self.geometry().y() + event.position().y(),
                           widget_out=widget, widget_out_id=outlet_id, parent=self.patch_area)
        cable.show()
        self.patch_area.add_audio_cable(cable)
        self.destination_widgets.append(cable)

    def addMIDIReceiver(self, widget):
        self.midi_destinations.append(widget)

    def removeMIDIReceiver(self, widget):
        self.midi_destinations.remove(widget)

    def checkInletPressed(self, event, subtractGlobalPos=False):
        if subtractGlobalPos:
            for i in range(self.n_in):
                if QRect(int(self.ins_x[i]), 2, 10, 10).contains(
                        QPoint(int(event.position().x() - self.x()), int(event.position().y() - self.y()))):
                    return i
        else:
            for i in range(self.n_in):
                if QRect(int(self.ins_x[i]), 2, 10, 10).contains(
                        QPoint(int(event.position().x()), int(event.position().y()))):
                    return i
        return -1

    def checkMIDIInletPressed(self, event, subtractGlobalPos=False):
        if subtractGlobalPos:
            for i in range(self.n_midi_in):
                if QRect(int(self.midi_ins_x[i]), 2, 10, 10).contains(
                        QPoint(int(event.position().x() - self.x()), int(event.position().y() - self.y()))):
                    return i
        else:
            for i in range(self.n_midi_in):
                if QRect(int(self.midi_ins_x[i]), 2, 10, 10).contains(
                        QPoint(int(event.position().x()), int(event.position().y()))):
                    return i
        return -1

    def checkOutletPressed(self, event, subtractGlobalPos=False):
        if subtractGlobalPos:
            for i in range(self.n_out):
                if QRect(int(self.outs_x[i]), int(self.height()) - 12, 10, 10).contains(
                        int(event.position().x() - self.x()), int(event.position().y() - self.y())):
                    return i
        else:
            for i in range(self.n_out):
                if QRect(int(self.outs_x[i]), int(self.height()) - 12, 10, 10).contains(int(event.position().x()),
                                                                                        int(event.position().y())):
                    return i
        return -1

    def checkMIDIOutletPressed(self, event, subtractGlobalPos=False):
        if subtractGlobalPos:
            for i in range(self.n_midi_out):
                if QRect(int(self.midi_outs_x[i]), int(self.height()) - 12, 10, 10).contains(
                        int(event.position().x() - self.x()), int(event.position().y() - self.y())):
                    return i
        else:
            for i in range(self.n_midi_out):
                if QRect(int(self.midi_outs_x[i]), int(self.height()) - 12, 10, 10).contains(int(event.position().x()),
                                                                                             int(event.position().y())):
                    return i
        return -1

    def checkParameterPressed(self, event, subtractGlobalPos=False):
        if subtractGlobalPos:
            for index, key in enumerate(self.synth_args.keys()):
                param = self.synth_args[key]
                if param["type"] == "audio":
                    param_y_center = self.synth_args_gui[key].y() + int(self.synth_args_gui[key].height() / 2)
                    if QRectF(0, param_y_center - 4, 7, 7).contains(int(event.position().x() - self.x()),
                                                                    int(event.position().y() - self.y())):
                        return key
        else:
            if type(self.synth_args) == dict:
                for index, key in enumerate(self.synth_args.keys()):
                    param = self.synth_args[key]
                    if param["type"] == "audio":
                        param_y_center = self.synth_args_gui[key].y() + int(self.synth_args_gui[key].height() / 2)
                        if QRectF(0, param_y_center - 4, 7, 7).contains(int(event.position().x()),
                                                                        int(event.position().y())):
                            return key
        return -1

    def calcInletOutletPos(self):
        self.ins_x = [(x + 1) * self.width() / ((self.n_in + self.n_midi_in) + 1) for x in range(self.n_in)]
        self.midi_ins_x = [(x + self.n_in + 1) * self.width() / ((self.n_in + self.n_midi_in) + 1) for x in
                           range(self.n_midi_in)]
        self.outs_x = [(x + 1) * self.width() / ((self.n_out + self.n_midi_out) + 1) for x in range(self.n_out)]
        self.midi_outs_x = [(x + self.n_out + 1) * self.width() / ((self.n_out + self.n_midi_out) + 1) for x in
                            range(self.n_midi_out)]
        self.params_x = [(x + 1) * self.height() / (self.n_param + 1) for x in range(self.n_param)]

    def checkLowerRightCorner(self, event, subtractGlobalPos=False):
        if subtractGlobalPos:
            if ((event.position().x() - self.x()) > (self.width() - self.right_corner_size) and (
                    event.position().x() - self.x()) < self.width() and (
                    self.height() - self.right_corner_size) < (event.position().y() - self.y()) < self.height()):
                return True
            else:
                return False
        else:
            if (self.width() - self.right_corner_size) < event.position().x() < self.width() and (
                    self.height() - self.right_corner_size) < event.position().y() < self.height():
                return True
            else:
                return False

    def checkDeleteCrossPressed(self, event, subtractGlobalPos=False):
        rect = QRectF(self.width() - (self.delete_cross_rect[0] + 20), self.delete_cross_rect[1],
                      self.width() - (self.delete_cross_rect[2] + 20), self.delete_cross_rect[3])
        point = QPointF(event.position().x(), event.position().y())
        return rect.contains(point)

    def mousePressEvent(self, event):
        # print("Clicking on widget:", self.getUUID())
        # Show Settings in SideBar
        self.settings_sidebar.inspect_widget(self)
        # Try to start a Cable
        self.mouseCablePressEvent(event, False)
        # Set a wider shadow
        self.enlargeShadow()

    def mouseCablePressEvent(self, event, subtractGlobalPos=False):
        # Check if Delete button pressed
        if self.checkDeleteCrossPressed(event, subtractGlobalPos):
            if self.type == "Audio":
                self.patch_area.patch.remove_audio_widget(self)
            elif self.type == "MIDI":
                self.patch_area.patch.remove_midi_widget(self)
            elif self.type == "AudioMIDI":
                self.patch_area.patch.remove_audio_midi_widget(self)
            elif self.type == "SubPatch":
                self.patch_area.patch.remove_sub_patch_widget(self)
            self.patch_area.place_cable()
        # Check if inlet is pressed with a SimpleCable ON to connect the cable
        if self.checkInletPressed(event, subtractGlobalPos) != -1:
            if self.patch_area.is_placing_cable():
                # print("Audio Inlet Pressed")
                command = PlaceCable(self, self.checkInletPressed(event), "Audio")
                self.get_undo_stack().push(command)
        # Check if outlet is pressed to add a SimpleCable
        if self.checkOutletPressed(event, subtractGlobalPos) != -1:
            # print("Audio Outlet Pressed")
            self.addDestination(event, self, self.checkOutletPressed(event), type="Audio")
            self.patch_area.lower_cables()
            event.accept()
            return
        if self.checkMIDIInletPressed(event, subtractGlobalPos) != -1:
            # print("MIDI Inlet Pressed")
            if self.patch_area.is_placing_cable():
                # command = PlaceCable(self.patch_area, self.checkMIDIInletPressed(event), "MIDI")
                command = PlaceCable(self, self.checkMIDIInletPressed(event), "MIDI")
                self.get_undo_stack().push(command)
        if self.checkMIDIOutletPressed(event, subtractGlobalPos) != -1:
            # print("MIDI Outlet Pressed")
            self.addDestination(event, self, self.checkMIDIOutletPressed(event) + self.n_out, type="MIDI")
            self.patch_area.lower_cables()
            event.accept()
            return
        # Check if parameter is pressed with a SimpleCable ON to add a SimpleCable
        if self.checkParameterPressed(event, subtractGlobalPos) != -1:
            if self.patch_area.is_placing_cable():
                self.patch_area.current_cable.addParameterWidget(self, self.checkParameterPressed(event))
                self.patch_area.place_cable()
                self.patch_area.lower_cables()
                event.accept()
                return
        # Check if lower-right corner is pressed to resize this widget
        elif self.checkLowerRightCorner(event, subtractGlobalPos):
            self.has_to_resize = True
            self.begin_point = QPointF(event.position().x(), event.position().y())
            event.accept()
            return
        # Move widget if no hot-areas are pressed
        else:
            self.has_to_move = True
            self.begin_point = QCursor.pos()
            event.accept()
            return

    def event(self, event):
        if event.type() == QEvent.Type.HoverMove:
            self.mouse_position = event.position()
            self.update()  # Richiama paintEvent per ridisegnare
        return super().event(event)

    def mouseMoveEvent(self, event):
        if self.has_to_resize:
            diff = QPointF(event.position().x() - self.begin_point.x(), event.position().y() - self.begin_point.y())
            self.resize(int(self.width() + diff.x()), int(self.height() + diff.y()))
            self.begin_point = QPointF(event.position().x(), event.position().y())
            self.patch_area.redraw_cables()
        if self.has_to_move:
            pos = QCursor.pos()
            rect = self.geometry()
            diff = QPointF(pos.x() - self.begin_point.x(), pos.y() - self.begin_point.y())
            self.setGeometry(min(max(0, int(rect.x() + diff.x())), self.patch_area.width() - self.width()),
                             min(max(0, int(rect.y() + diff.y())), self.patch_area.height() - self.height()),
                             self.width(), self.height())
            self.begin_point = QCursor.pos()
            self.patch_area.redraw_cables()

    def mouseReleaseEvent(self, event):
        self.has_to_resize = False
        self.has_to_move = False
        # Set a smaller shadow
        self.reduceShadow()

    def resizeEvent(self, event):
        if not self.is_resizing:
            new_width = self.width()
            new_height = self.height()
            self.is_resizing = True
            self.resize(new_width, new_height)
            self.is_resizing = False

    def draw_tooltip(self, painter, text, pos, below=True):
        padding = 5
        fm = QFontMetrics(painter.font())
        text_rect = fm.boundingRect(text)

        # Calcola il rettangolo della tooltip centrato sotto il mouse
        rect_width = text_rect.width() + 2 * padding
        rect_height = text_rect.height() + 2 * padding
        rect_x = pos.x() - rect_width / 2
        if below:
            rect_y = pos.y() + 0  # Offset per posizionare la tooltip sotto il mouse
        else:
            rect_y = pos.y() - 20  # Offset per posizionare la tooltip sotto il mouse

        rect = QRectF(rect_x, rect_y, rect_width, rect_height)

        # Set background and border
        painter.setBrush(QBrush(QColor(255, 255, 225)))  # Light yellow background
        painter.setPen(QPen(QColor(0, 0, 0)))  # Black border
        painter.drawRect(rect)

        # Calcola la posizione del testo centrato verticalmente
        text_x = rect_x + padding
        text_y = rect_y + padding + fm.ascent()

        # Set text
        painter.setPen(QPen(QColor(0, 0, 0)))  # Black text
        painter.drawText(QPointF(text_x, text_y), text)

    def paintEvent(self, event):
        self.calcInletOutletPos()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen()
        pen.setWidth(4)
        # Definisci i rettangoli
        outer_rect = QRect(2, 2, self.width() - 3, self.height() - 3)
        inner_rect = QRect(10, 10, self.width() - 20, self.height() - 20)
        border_color = QColor(0, 0, 0)
        if self.type == "Audio":
            outer_color = self.widget_outer_colors["Audio"]
            inner_color = self.widget_inner_colors["Audio"]
        elif self.type == "MIDI":
            outer_color = self.widget_outer_colors["MIDI"]
            inner_color = self.widget_inner_colors["MIDI"]
        elif self.type == "SubPatch":
            outer_color = self.widget_outer_colors["SubPatch"]
            inner_color = self.widget_inner_colors["SubPatch"]
        else:
            outer_color = QLinearGradient(QPointF(outer_rect.topLeft()), QPointF(outer_rect.bottomLeft()))
            outer_color.setColorAt(0, self.widget_outer_colors["Audio"])
            outer_color.setColorAt(1, self.widget_outer_colors["MIDI"])
            inner_color = QLinearGradient(QPointF(inner_rect.topLeft()), QPointF(inner_rect.bottomLeft()))
            inner_color.setColorAt(0, self.widget_inner_colors["Audio"])
            inner_color.setColorAt(1, self.widget_inner_colors["MIDI"])

        # Raggio degli angoli
        radius = 10
        # Disegna il rettangolo esterno
        painter.setPen(QPen(border_color, 2))
        painter.setBrush(QBrush(outer_color))
        painter.drawRoundedRect(outer_rect, radius, radius)
        # Disegna il rettangolo interno
        painter.setPen(QPen(border_color, 2))
        painter.setBrush(QBrush(inner_color))
        painter.drawRoundedRect(inner_rect, radius, radius)
        # INLET & OUTLET
        # Audio Inlets
        pen.setColor(self.inlet_color)
        painter.setPen(pen)
        if self.n_in > 0:
            for xid, x in enumerate(self.ins_x):
                width = self.xlet_size[0]
                height = self.xlet_size[1]
                self.inlet_svg["Audio"].paint(painter, int(x - int(width / 2)), 0, width, height)
                if self.type == "SubPatch":
                    if QRect(int(x - int(width / 2)), 0, width, height).contains(int(self.mouse_position.x()),
                                                                                 int(self.mouse_position.y())):
                        self.draw_tooltip(painter, self.in_names[xid], QPoint(int(x + width - int(width / 2)), height))
        # MIDI Inlets
        pen.setColor(self.midi_inlet_color)
        painter.setPen(pen)
        if self.n_midi_in > 0:
            for x in self.midi_ins_x:
                width = self.xlet_size[0]
                height = self.xlet_size[1]
                self.inlet_svg["MIDI"].paint(painter, int(x - int(width / 2)), 0, width, height)
                if QRect(int(x - int(width / 2)), 0, width, height).contains(int(self.mouse_position.x()),
                                                                             int(self.mouse_position.y())):
                    self.draw_tooltip(painter, "TODO: Add Tooltip", QPoint(int(x + width - int(width / 2)), height))
        # Audio Outlets
        pen.setColor(self.inlet_color)
        painter.setPen(pen)
        if self.n_out > 0:
            for xid, x in enumerate(self.outs_x):
                width = self.xlet_size[0]
                height = self.xlet_size[1]
                self.outlet_svg["Audio"].paint(painter, int(x - int(width / 2)), self.height() - height, width, height)
                if self.type == "SubPatch":
                    if QRect(int(x - int(width / 2)), self.height() - height, width, height).contains(
                            int(self.mouse_position.x()), int(self.mouse_position.y())):
                        self.draw_tooltip(painter, self.out_names[xid],
                                          QPoint(int(x + width - int(width / 2)), self.height() - (height + 20)),
                                          below=False)
        # MIDI Outlets
        pen.setColor(self.midi_inlet_color)
        painter.setPen(pen)
        if self.n_midi_out > 0:
            for x in self.midi_outs_x:
                width = self.xlet_size[0]
                height = self.xlet_size[1]
                self.outlet_svg["MIDI"].paint(painter, int(x - int(width / 2)), self.height() - height, width, height)
                if QRect(int(x - int(width / 2)), self.height() - height, width, height).contains(
                        int(self.mouse_position.x()), int(self.mouse_position.y())):
                    self.draw_tooltip(painter, "TODO: Add Tooltip",
                                      QPoint(int(x + width - int(width / 2)), self.height() - (height + 20)),
                                      below=False)
        # PARAMETERS
        if type(self.synth_args) == dict:
            if len(self.synth_args.keys()) > 0:
                for index, key in enumerate(self.synth_args.keys()):
                    param = self.synth_args[key]
                    # se il parametro è audio, allora disegna un inlet
                    if param["type"] == "audio":
                        param_y_center = self.synth_args_gui[key].y() + int(self.synth_args_gui[key].height() / 2)
                        pen.setColor(self.audio_param_color)
                        painter.setPen(pen)
                        width = self.xlet_size[0]
                        height = self.xlet_size[1]
                        self.param_svg["Audio"].paint(painter, -int(width / 4), param_y_center - int(height / 2), width,
                                                      height)
                    # se il parametro non è audio, allora non fare nulla
                    else:
                        pass
        # DELETE WIDGET "BUTTON"
        self.delete_svg.paint(painter, self.width() - 25, 15, 10, 10)

    def initUI(self):
        # Reparent previous layout if exists
        if self.layout() is not None:
            QWidget().setLayout(self.layout())
        self.synth_args_gui = {}
        params_lay = QVBoxLayout()
        # Widget Title
        widget_title = QLabel(self.synth_name)
        widget_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        widget_title.setObjectName("widget-title")
        params_lay.addWidget(widget_title)
        # Widget Parameters
        for index, key in enumerate(self.synth_args.keys()):
            if self.synth_args[key]["type"] == "AmbisonicsKernel":
                pass  # TODO: DA IMPLEMENTARE!
            elif self.synth_args[key]["type"] == "patch_buffer":
                param_lay = QHBoxLayout()
                param = self.synth_args[key]
                param_lbl = QLabelT(key)
                param_lbl.setToolTip(param["desc"])
                param_lbl.setObjectName("widget-param")
                param_lay.addWidget(param_lbl)
                param_val = QPushButton()
                menu = QMenu()
                for key2 in self.patch.patch_buffers.getBuffers().keys():
                    buf = self.patch.patch_buffers.getBuffers()[key2]
                    menu.addAction(f"{buf['bufnum']}: {buf['name']} - dur: {buf['duration']} chans: {buf['channels']}",
                                   lambda j=key, k=key2: self.patch_buffer_param_change(j, k))
                param_val.setMenu(menu)
                param_val.setObjectName("widget-param")
                param_val.setText("Select a PatchBuffer")
                self.synth_args_gui[key] = param_val
                param_lay.addWidget(param_lbl)
                param_lay.addWidget(param_val)
                self.synth_args_gui[key] = param_val
                # print("key:", key, "self.synth_args_gui[key]", self.synth_args_gui[key])
            else:
                param_lay = QHBoxLayout()
                param = self.synth_args[key]
                param_lbl = QLabelT(key)
                param_lbl.setToolTip(param["desc"])
                param_lbl.setObjectName("widget-param")
                param_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                param_lay.addWidget(param_lbl)
                param_val = QLineEdit()
                param_val.setObjectName("widget-param")
                param_val.setText(str(param["val"]))
                param_val.textChanged.connect(lambda v, k=key: self.param_change(k, v))
                param_val.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                self.synth_args_gui[key] = param_val
                param_lay.addWidget(param_lbl)
                param_lay.addWidget(param_val)
                self.synth_args_gui[key] = param_val
            params_lay.addLayout(param_lay)
        self.setLayout(params_lay)
        if self.type == "Audio":
            for i in range(len(self.audio_meters)):
                params_lay.addWidget(self.audio_meters[i])
        self.setMinimumSize(params_lay.sizeHint())

    def param_change(self, key, value):
        command = ParameterChange(self, key, value)
        self.get_undo_stack().push(command)

    def patch_buffer_param_change(self, key, val):
        command = PatchBufferParameterChange(self, key, self.sender().text())
        self.get_undo_stack().push(command)

    def __getstate__(self):
        d = {}
        return d

    def __setstate__(self, state):
        pass


class AudioWidget(SimpleWidget):
    def __init__(self, server=None, parent=None, n_in=2, n_out=5, synth_name="default", synth_args=None, uuid=None,
                 name="", active=True, target_node=0, **kwargs):
        super().__init__(parent, n_in, n_out)
        self.type = "Audio"
        self.setObjectName(self.type)
        self.server = server
        self.patch = self.patch_area.patch
        if uuid is not None:
            self.uuid = uuid
        else:
            self.uuid = self.server.queryFreeNode()
        self.name = name
        self.synth_name = synth_name
        self.active = active
        if "SubPatch" in self.synth_name:
            self.widget_outer_colors["Audio"] = QColor(50, 50, 180)
            self.widget_inner_colors["Audio"] = QColor(100, 100, 240)
        if synth_args is not None:
            self.synth_args = deepcopy(synth_args)
        else:
            self.synth_args = {}
        self.synth = None
        self.bus = None
        self.n_in = n_in
        self.n_out = n_out
        self.in_ch = scsynth.getDefaultInBus()
        self.out_ch = scsynth.getDefaultOutBus()
        self.synth_args_gui = {}
        self.args = []
        self.input_channels = []
        self.output_channels = []
        self.bus_values = [.0 for _ in range(self.n_out)]
        self.audio_meters = [AudioMeter() for _ in range(self.n_out)]
        self.border_color = Qt.GlobalColor.darkBlue
        self.inlet_color = Qt.GlobalColor.darkYellow
        self.atk_kernels = self.server.atk_kernels
        self.loadATKParams()
        self.initUI()
        self.initArgs()
        self.resetSynthArgs()
        self.createSynth()
        if self.active:
            self.bus_update_thread = Thread(target=self.audio_bus_volume_update_func, args=(), daemon=True)
            self.bus_update_thread.start()

    def setActive(self, active):
        if active and not self.active:
            self.instantiateSynth()
            self.bus_update_thread = Thread(target=self.audio_bus_volume_update_func, args=(), daemon=True)
            self.bus_update_thread.start()
        if self.active and not active:
            self.freeSynth()
            self.bus_update_thread.join()
        self.active = active

    def loadATKParams(self):
        for arg in self.synth_args.keys():
            if self.synth_args[arg]["type"] == "AmbisonicsKernel":
                if "Binaural" in self.synth_args[arg]["desc"]:
                    self.synth_args[arg]["val"] = self.atk_kernels.get_binaural_kernels()[arg]
                else:
                    c_print("yellow", f"Warning: {arg} is not implemented yet.")

    def audio_bus_volume_update_func(self):
        while True:
            if self.patch.meter_enabled:
                for out_ch in self.output_channels:
                    scsynth.pollControlBus(out_ch)
                time.sleep(.95 / BUS_VISUAL_UPDATE_FREQ)
                # print(self.bus_values, scsynth.bus_values)
                for i in range(len(self.output_channels)):
                    try:
                        self.bus_values[i] = scsynth.bus_values[str(self.output_channels[i])]
                        self.audio_meters[i].setAmplitude(self.bus_values[i])
                    except:
                        print("Can't get bus...")
            time.sleep(.05 / BUS_VISUAL_UPDATE_FREQ)

    def initArgs(self):
        self.input_channels = [self.in_ch + i for i in range(self.n_in)]
        self.output_channels = [self.out_ch + i for i in range(self.n_out)]
        self.bus_values = [0 for _ in range(self.n_out)]

    def getSynthArgs(self):
        return deepcopy(self.synth_args)

    def getSettings(self):
        self.resetSynthArgs()
        inputs = {}
        outputs = {}
        for i in range(self.n_in):
            inputs["in_ch_{}".format(i)] = self.input_channels[i]
        for i in range(self.n_out):
            outputs["out_ch_{}".format(i)] = self.output_channels[i]
        a = {
            "Parameters": deepcopy(self.synth_args),
            "Inputs": inputs,
            "Outputs": outputs
        }
        return a

    def setSettings(self, settings):
        # c_print("green", f"AudioWidget {self.name}-{self.getUUID()} recreation settings: {settings}")
        self.synth_args = deepcopy(settings["Parameters"])
        # Inputs
        for index, key in enumerate(settings["Inputs"]):
            self.input_channels[index] = settings["Inputs"][key]
        # Outputs
        for index, key in enumerate(settings["Outputs"]):
            self.output_channels[index] = settings["Outputs"][key]
        # Parameters
        for arg in self.synth_args.keys():
            if self.synth_args[arg]["type"] == "patch_buffer":
                buf = self.patch.patch_buffers.getBuffers()[str(self.synth_args[arg]["val"])]
                # print("self.synth_args[arg]['val']", str(self.synth_args[arg]["val"]))
                self.synth_args_gui[arg].setText(
                    f"{buf['bufnum']}: {buf['name']} - dur: {buf['duration']} chans: {buf['channels']}")
            else:
                if self.synth_args[arg]["type"] != "AmbisonicsKernel":
                    self.synth_args_gui[arg].setText(str(self.synth_args[arg]["val"]))
        self.resetSynthArgs()

    def createSynth(self):
        if self.synth is not None:
            self.synth.free()
        self.bus = Bus(self.server, self.n_out)
        self.output_channels = self.bus.getChans()
        if self.active:
            self.instantiateSynth()

    def instantiateSynth(self):
        self.args = []
        for index, channel in enumerate(self.input_channels):
            self.args.append("in_ch_{}".format(index))
            self.args.append(channel)
        for index in range(self.n_out):
            self.args.append("out_ch_{}".format(index))
            self.args.append(self.bus.getChan(index))
        for arg in self.synth_args.keys():
            self.args.append(arg)
            self.args.append(self.synth_args[arg]["val"])
            # print(f"arg: {arg} -> {self.synth_args[arg]['val']}")
        try:
            self.synth.free()
        except:
            pass
        self.synth = Synth(self.server, node=self.uuid, name=self.synth_name, args=self.args)
        self.server.dumpNodeTree()

    def resetSynthArgs(self):
        if self.synth is not None:
            for index, channel in enumerate(self.input_channels):
                self.synth.set("in_ch_{}".format(index), channel)
            for index, channel in enumerate(self.output_channels):
                self.synth.set("out_ch_{}".format(index), channel)
            for arg in self.synth_args.keys():
                # Audio Parameter
                if self.synth_args[arg]["type"] == "audio":
                    if int(self.synth_args[arg]["bus"]) > 0:
                        self.synth.map(arg, self.synth_args[arg]["bus"])
                        self.synth.set(arg.replace("a_", "selector_"), 1)
                    else:
                        try:
                            self.synth.set(arg, float(self.synth_args[arg]["val"]))
                            self.synth.set(arg.replace("a_", "selector_"), 0)
                        except:
                            c_print("red", f"ERROR: Widget resetSynthArgs (Bad text: {self.synth_args[arg]['val']})")
                # Buffer Parameter
                elif self.synth_args[arg]["type"] == "buffer":
                    list_value = self.synth_args[arg]["val"]
                    if type(list_value) == str:
                        list_value = ast.literal_eval(list_value)
                    if int(list_value[0]) > 0 and os.path.exists(list_value[1]):
                        scsynth.allocReadBuffer(list_value[1], list_value[0])
                        self.synth.set(arg, int(list_value[0]))
                # PatchBuffer Parameter
                elif self.synth_args[arg]["type"] == "patch_buffer":
                    val = self.synth_args[arg]["val"]
                    if not str(val) in self.patch.patch_buffers.getBuffers().keys():
                        c_print("red", f"Fatal: PatchBuffer{val} not in list!")
                    else:
                        # c_print("green", f"setting buf to: {val}")
                        self.synth.set(arg, int(val))
                # AmbisonicsKernel Parameter
                elif self.synth_args[arg]["type"] == "AmbisonicsKernel":
                    pass  # TODO: DA IMPLEMENTARE!

                # Int/Float Parameter
                else:
                    try:
                        val = float(self.synth_args[arg]["val"])
                        if (val - int(val)) == 0:
                            val = int(val)
                        self.synth.set(arg, val)
                    except:
                        pass
        self.patch_area.repatch_audio()

    def freeSynth(self):
        if self.synth is not None:
            self.synth.free()
            self.synth = None
        else:
            pass

    def moveBefore(self, node):
        if self.synth is None:
            # print("No synth associated with graphic class: aborting...")
            pass
        else:
            # Set synth before other node (if AudioOut, wew would expect it to be at the bottom of the DSP chain)
            self.synth.moveBefore(node)

    def moveAfter(self, node):
        if self.synth is None:
            # print("No synth associated with graphic class: aborting...")
            pass
        else:
            # Set synth after other node (if AudioOut, wew would expect it to be at the bottom of the DSP chain)
            self.synth.moveAfter(node)

    def change_in_ch(self, index, value):
        self.input_channels[index] = value
        # self.synth.set("in_ch_{}".format(index), value)
        self.resetSynthArgs()
        # print("Input Channel {} changed to {}".format(index, self.input_channels[index]))

    def change_param(self, key, chan):
        synth_args = deepcopy(self.synth_args)
        synth_args[key]["bus"] = chan
        self.synth_args = deepcopy(synth_args)
        self.resetSynthArgs()
        # print("Param {} changed to bus {}".format(key, chan))

    def set_param_val(self, key, value):
        synth_args = deepcopy(self.synth_args)
        synth_args[key]["val"] = value
        self.synth_args = deepcopy(synth_args)
        self.resetSynthArgs()

    def __getstate__(self):
        self.args = []
        d = {
            "uuid": self.uuid,
            "n_in": self.n_in,
            "n_out": self.n_out,
            "name": self.name,
            "synth_name": self.synth_name,
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height(),
            "Settings": self.getSettings()
        }
        for i in range(self.n_in):
            self.args.append("in_ch_{}".format(i))
            d["in_ch_{}".format(i)] = self.input_channels[i]
        for i in range(self.n_out):
            self.args.append("out_ch_{}".format(i))
            d["out_ch_{}".format(i)] = self.bus.getChan(i)
        # c_print("green", f"AudioWidget Saving state: {d}")
        return d

    def __setstate__(self, state):
        self.uuid = state["uuid"]
        self.n_in = state["n_in"]
        self.n_out = state["n_out"]
        if "name" in list(state.keys()):
            self.name = state["name"]
        # self.in_ch = state["in_ch"]
        self.setSettings(state["Settings"])
        # c_print("yellow",f'AudioWidget {self.name} ins: {state["Settings"]["Inputs"]}; outs: {state["Settings"]["Outputs"]} ')
        self.setGeometry(state["x"], state["y"], state["width"], state["height"])
        self.freeSynth()
        # c_print("yellow", f'{[state["out_ch_{}".format(i)] for i in range(self.n_out)]}')
        self.bus = Bus(self.server, self.n_out, [state["out_ch_{}".format(i)] for i in range(self.n_out)])
        # TODO: check this line!
        self.resetSynthArgs()
        self.instantiateSynth()  # Qui instantiateSynth perchè non devo ricreare il Bus
        # c_print("green", f"AudioWidget Loading state: {state}")


class MIDIWidget(SimpleWidget):
    def __init__(self, clock, harmony_manager, parent=None, n_midi_in=0, n_midi_out=0, uuid=None, **kwargs):
        super().__init__(parent, n_midi_in=n_midi_in, n_midi_out=n_midi_out, uuid=uuid)
        self.type = "MIDI"
        self.setObjectName(self.type)
        self.border_color = Qt.GlobalColor.darkRed
        self.inlet_color = Qt.GlobalColor.darkGreen
        self.clock = clock
        self.harmony_manager = harmony_manager

    def process_tick(self, tick):
        pass

    def propagateRTCC(self, num, val):
        for widget in self.midi_destinations:
            if hasattr(widget, "processRTCC"):
                # print("calling processRTCC")
                widget.processRTCC(num, val)
            if hasattr(widget, "propagateRTCC"):
                # print("calling propagateRTCC")
                widget.propagateRTCC(num, val)

    def propagateRTProgramChange(self, num):
        pass

    def propagateRTMIDINote(self, note, velocity):
        for widget in self.midi_destinations:
            if hasattr(widget, "processRTMIDINote"):
                widget.processRTMIDINote(note, velocity)
            if hasattr(widget, "propagateRTMIDINote"):
                widget.propagateRTMIDINote(note, velocity)

    def processNote(self, note):
        self.propagateMIDINote(note)

    def propagateMIDINote(self, note):
        for widget in self.midi_destinations:
            if hasattr(widget, "processNote"):
                widget.processNote(note)

    def getSettings(self):
        d = {
            "Parameters": {},
            "Inputs": {},
            "Outputs": {}
        }
        return d

    def setSettings(self, settings):
        pass

    def __getstate__(self):
        self.args = []
        d = {
            "uuid": self.uuid,
            "n_in": self.n_in,
            "n_out": self.n_out,
            "n_midi_in": self.n_midi_in,
            "n_midi_out": self.n_midi_out,
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height(),
            "Settings": self.getSettings()
        }
        return d

    def __setstate__(self, state):
        self.uuid = state["uuid"]
        self.n_in = state["n_in"]
        self.n_out = state["n_out"]
        self.n_midi_in = state["n_midi_in"]
        self.n_midi_out = state["n_midi_out"]
        self.setSettings(state["Settings"])
        self.setGeometry(state["x"], state["y"], state["width"], state["height"])


class AudioMIDIWidget(SimpleWidget):
    def __init__(self, server=None, clock=None, harmony_manager=None, parent=None, uuid=None, n_audio_in=0,
                 n_audio_out=0, n_midi_in=0, n_midi_out=0, synth_name="", synth_args=None):
        super().__init__(parent=parent, n_in=n_audio_in, n_out=n_audio_out, n_midi_in=n_midi_in, n_midi_out=n_midi_out)
        if synth_args is None:
            synth_args = {}
        # AudioMIDI Synths MUST HAVE arguments "freq", "amp", "gate" !!!
        self.type = "AudioMIDI"
        self.setObjectName(self.type)
        self.server = server
        self.clock = clock
        self.harmony_manager = harmony_manager
        if uuid is not None:
            self.uuid = uuid
        else:
            self.uuid = self.server.queryFreeNode()
        self.synth_name = synth_name
        self.synth_args = synth_args
        self.synth = None
        self.note_synths = {str(i): None for i in range(128)}
        self.resetNoteSynths()
        self.n_in = n_audio_in
        self.n_out = n_audio_out
        self.bus = Bus(self.server, self.n_out)
        self.group = Group(self.server, self.uuid, "head", 0)
        self.in_ch = scsynth.getDefaultInBus()
        self.out_ch = scsynth.getDefaultOutBus()
        self.synth_args_gui = {}
        self.args = []
        self.input_channels = []
        self.output_channels = []
        self.border_color = Qt.GlobalColor.darkBlue
        self.inlet_color = Qt.GlobalColor.darkYellow

        self.initUI()
        self.initArgs()
        # print("output channels:", self.output_channels, "bus first channel:", [self.bus.getChan(i) for i in range(len(self.output_channels))])

    def freeSynth(self):
        try:
            self.synth.free()
        except:
            pass
        for key in self.note_synths.keys():
            try:
                self.note_synths[key].free()
            except:
                pass

    def initArgs(self):
        self.input_channels = [self.in_ch + i for i in range(self.n_in)]
        self.output_channels = [self.bus.getChan(i) for i in range(self.n_out)]

    def computeSynthArgs(self):
        args = []
        for index, channel in enumerate(self.input_channels):
            args.append("in_ch_{}".format(index))
            args.append(channel)
        for index, channel in enumerate(self.output_channels):
            args.append("out_ch_{}".format(index))
            args.append(channel)
        for arg in self.synth_args.keys():
            if self.synth_args[arg]["type"] == "audio":
                if self.synth_args[arg]["bus"] <= 0:
                    val = float(self.synth_args[arg]["val"])
                    args.append(arg)
                    args.append(val)
                    if isinstance(self.synth, Synth):
                        self.synth.set(arg.replace("a_", "selector_"), 0)
                        self.synth.set(arg, self.synth_args[arg]["val"])
                    arg = arg.replace("a_", "selector_")
                    args.append(arg)
                    args.append(0)
                else:
                    if isinstance(self.synth, Synth):
                        self.synth.map(arg, self.synth_args[arg]["bus"])
                        self.synth.set(arg.replace("a_", "selector_"), 1)
                    arg = arg.replace("a_", "selector_")
                    args.append(arg)
                    args.append(1)
            else:
                try:
                    val = float(self.synth_args[arg]["val"])
                    if (val - int(val)) == 0:
                        val = int(val)
                    args.append(arg)
                    args.append(val)
                    if isinstance(self.synth, Synth):
                        self.synth.set(arg, val)
                except:
                    pass
        return args

    def getSynthArgs(self):
        return deepcopy(self.synth_args)

    def moveBefore(self, node):
        # Set group before other node
        self.group.moveBefore(node)

    def moveAfter(self, node):
        # Set group after other node
        self.group.moveAfter(node)

    def resetNoteSynths(self):
        for i in range(128):
            try:
                self.note_synths[str(i)].set("gate", 0)  # release synth if any
            except:
                pass
            self.note_synths[str(i)] = None
        try:
            self.group.free()
        except:
            pass
        self.group = Group(self.server, self.uuid, "head",
                           0)  # TODO: check if inside a subpatch, targetID should not be 0!

    def processNote(self, note):
        # note.describe()
        thread = Thread(target=self.noteThread, args=(note,))
        thread.start()

    def processRTCC(self, num, val):
        pass

    def processRTMIDINote(self, note, velocity):
        # print(f"Processing RT MIDI Note {note}")
        if note in MIDI_NOTE_NAMES.keys():
            note = MIDI_NOTE_NAMES[note]
        note = Note(note, velocity)
        amplitude = note.getVelocity() / 127.0
        frequency = note.getFrequency()
        params = self.computeSynthArgs()

        params.append("freq")
        params.append(frequency)
        params.append("amp")
        params.append(amplitude)
        # print(f"params: {params}")
        if velocity > 0:  # Note On
            try:
                self.note_synths[str(note.getNote())].set("gate", 0)  # release synth if any
                self.note_synths[str(note.getNote())] = None
            except:
                pass
            self.note_synths[str(note.getNote())] = Synth(self.server, self.synth_name, node=None, args=params, addAction="head", targetID=self.group.getNodeID())
            for arg in self.synth_args.keys():
                if self.synth_args[arg]["type"] == "audio":
                    if int(self.synth_args[arg]["bus"]) > 0:
                        for knote in self.note_synths.keys():
                            synth = self.note_synths[knote]
                            # if type(synth) == Synth:
                            if isinstance(synth, Synth):
                                synth.map(arg, self.synth_args[arg]["bus"])
        else:  # Note Off
            try:
                self.note_synths[str(note.getNote())].set("gate", 0)  # release synth if any
                self.note_synths[str(note.getNote())] = None
            except:
                pass

    def noteThread(self, note):
        params = self.computeSynthArgs()
        amplitude = note.getVelocity() / 127.0
        frequency = note.getFrequency()
        duration = 60 * note.getDuration() / (self.clock.getBPM() * PPQN)
        params.append("freq")
        params.append(frequency)
        params.append("amp")
        params.append(amplitude)
        params.append("a_dur")
        if duration > 0:
            params.append(duration)
        else:
            try:
                params.append(self.synth_args["a_dur"]["val"])
            except:
                params.append(duration)

        # IMPORTANT: if a Synth has "a_dur" or "dur" parameter, it means than it owns a DoneAction=2, which means it will autonomously free itself after duration
        if not "a_dur" in self.synth_args.keys() and not "dur" in self.synth_args.keys():
            if self.note_synths[str(note.getNote())] is not None:
                self.note_synths[str(note.getNote())].set("gate", 0)  # release synth if any
                self.note_synths[str(note.getNote())] = None
        else:
            if self.note_synths[str(note.getNote())] is not None:
                del self.note_synths[str(note.getNote())]
                self.note_synths[str(note.getNote())] = None

        # Instantiate synth with args
        print(self.group.getNodeID(), params)
        self.note_synths[str(note.getNote())] = Synth(self.server, self.synth_name, node=None, args=params, addAction="head", targetID=self.group.getNodeID())
        # Map audio busses to arguments as needed
        for arg in self.synth_args.keys():
            if self.synth_args[arg]["type"] == "audio":
                if int(self.synth_args[arg]["bus"]) > 0:
                    self.note_synths[str(note.getNote())].map(arg, self.synth_args[arg]["bus"])

        time.sleep(duration)

        # IMPORTANT: if a Synth has "a_dur" or "dur" parameter, it means than it owns a DoneAction=2, which means it will free itself after duration
        if not "a_dur" in self.synth_args.keys() and not "dur" in self.synth_args.keys():
            if self.note_synths[str(note.getNote())] is not None:
                self.note_synths[str(note.getNote())].set("gate", 0)
                self.note_synths[str(note.getNote())] = None
        else:
            if self.note_synths[str(note.getNote())] is not None:
                del self.note_synths[str(note.getNote())]
                self.note_synths[str(note.getNote())] = None

    def change_in_ch(self, index, value):
        self.input_channels[index] = value
        # print("Input Channel {} changed to {}".format(index, self.input_channels[index]))

    def change_param(self, key, chan):
        self.synth_args[key]["bus"] = chan
        self.computeSynthArgs()
        # print("Param {} changed to bus {}".format(key, chan))

    def set_param(self, key, val):
        self.synth_args[key]["val"] = val
        if isinstance(self.synth, Synth):
            self.synth.set(key, val)

    def getSettings(self):
        inputs = {}
        outputs = {}
        for i in range(self.n_in):
            inputs["in_ch_{}".format(i)] = self.input_channels[i]
        for i in range(self.n_out):
            outputs["out_ch_{}".format(i)] = self.output_channels[i]
        a = {
            "Parameters": self.synth_args,
            "Inputs": inputs,
            "Outputs": outputs
        }
        return a

    def setSettings(self, settings):
        self.synth_args = settings["Parameters"]
        # print("Widget Settings:", settings)
        # Inputs
        for index, key in enumerate(settings["Inputs"]):
            self.input_channels[index] = settings["Inputs"][key]
        # Outputs
        for index, key in enumerate(settings["Outputs"]):
            self.output_channels[index] = settings["Outputs"][key]
        # Parameters
        for arg in self.synth_args.keys():
            self.synth_args_gui[arg].setText(str(self.synth_args[arg]["val"]))

    def __getstate__(self):
        self.args = []
        d = {
            "uuid": self.uuid,
            "n_in": self.n_in,
            "n_out": self.n_out,
            "n_audio_in": self.n_in,
            "n_audio_out": self.n_out,
            "n_midi_in": self.n_midi_in,
            "n_midi_out": self.n_midi_out,
            "synth_name": self.synth_name,
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height(),
            "Settings": self.getSettings()
        }
        for i in range(self.n_in):
            self.args.append("in_ch_{}".format(i))
            d["in_ch_{}".format(i)] = self.input_channels[i]
        for i in range(self.n_out):
            self.args.append("out_ch_{}".format(i))
            d["out_ch_{}".format(i)] = self.bus.getChan(i)
        # c_print("green", f"AudioMIDIWidget Saving state: {d}")
        return d

    def __setstate__(self, state):
        self.uuid = state["uuid"]
        self.n_in = state["n_in"]
        self.n_out = state["n_out"]
        self.n_midi_in = state["n_midi_in"]
        self.n_midi_out = state["n_midi_out"]
        # self.in_ch = state["in_ch"]
        self.setSettings(state["Settings"])
        self.setGeometry(state["x"], state["y"], state["width"], state["height"])
        self.bus = Bus(self.server, self.n_out, [state["out_ch_{}".format(i)] for i in range(self.n_out)])
        self.resetNoteSynths()
        # print("output channels:", self.output_channels, "bus first channel:", [self.bus.getChan(i) for i in range(len(self.output_channels))])
        # c_print("green", f"AudioMIDIWidget Loading state: {state}")


class SubPatchInstanceWidget(SimpleWidget):
    def __init__(self, parent=None, server=None, uuid=None, subpatch=None, target_patch=None):
        super().__init__(parent)
        self.type = "SubPatch"
        self.server = server
        self.subpatch = subpatch
        self.n_in, self.n_out = self.subpatch.getIO()
        self.in_names, self.out_names = self.subpatch.getIONames()
        self.target_patch = target_patch
        self.synth_name = self.subpatch.name
        self.synth_args = {}
        self.bus = None
        if uuid is not None:
            self.uuid = uuid
        else:
            self.uuid = self.server.queryFreeNode()
        self.group = Group(self.server, self.uuid, "head", self.target_patch.getGroup())
        self.subpatch.addSubPatchInstance(self)
        self.initUI()

    def repatch_audio(self):
        self.subpatch.patch_area.repatch_audio()

    def initArgs(self):
        self.input_channels, self.output_channels = self.subpatch.getIOChansForInstance(self)
        if self.n_out > 0:
            self.bus = Bus(self.server, self.n_out, self.output_channels)

    def getGroupNode(self):
        return self.group.getNodeID()

    def moveBefore(self, node):
        # Set group before other node
        self.group.moveBefore(node)

    def moveAfter(self, node):
        # Set group after other node
        self.group.moveAfter(node)

    def reinitUI(self):
        self.n_in, self.n_out = self.subpatch.getIO()
        self.in_names, self.out_names = self.subpatch.getIONames()
        # print(f"SUBPATCH INSTANCE's self.n_in, self.n_out are now:{(self.n_in, self.n_out)}")
        self.initUI()

    def change_in_ch(self, index, value):
        # print("self.input_channels, index, value", self.input_channels, index, value)
        self.input_channels[index] = value

    def getSettings(self):
        return {}

    def setSettings(self, data):
        self.settings = data

    def __getstate__(self):
        self.args = []
        d = {
            "uuid": self.uuid,
            "n_in": self.n_in,
            "n_out": self.n_out,
            "in_names": self.in_names,
            "out_names": self.out_names,
            "synth_name": self.synth_name,
            "subpatch_name": self.subpatch.name,
            "subpatch_instance_data": self.subpatch.get_instance_graph_state(self.uuid),
            "target_patch": None,
            "target_group_uuid": self.group.getNodeID(),
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height(),
            "Settings": self.getSettings()
        }
        for i in range(self.n_in):
            self.args.append("in_ch_{}".format(i))
            d["in_ch_{}".format(i)] = self.input_channels[i]
        for i in range(self.n_out):
            self.args.append("out_ch_{}".format(i))
            d["out_ch_{}".format(i)] = self.bus.getChan(i)
        # print("AudioWidget Saving state:", d)
        return d

    def __setstate__(self, state):
        self.uuid = state["uuid"]
        self.n_in = state["n_in"]
        self.n_out = state["n_out"]
        self.in_names = state["in_names"]
        self.out_names = state["out_names"]
        self.synth_name = state["synth_name"]
        # self.subpatch = state["subpatch"]
        self.target_patch = state["target_patch"]
        if "name" in list(state.keys()):
            self.name = state["name"]
        # self.in_ch = state["in_ch"]
        self.setSettings(state["Settings"])
        self.setGeometry(state["x"], state["y"], state["width"], state["height"])
        # self.freeSynth()
        self.bus = Bus(self.server, self.n_out, [state["out_ch_{}".format(i)] for i in range(self.n_out)])
        self.reinitUI()
        c_print("red",
                f'SubPatchInstanceWidget SETTING in_ch_ {[state["in_ch_{}".format(i)] for i in range(self.n_in)]}; out_ch_ {[state["out_ch_{}".format(i)] for i in range(self.n_out)]}')
        c_print("red",
                f'SubPatchInstanceWidget SETTING ins: {self.input_channels} out of {[state["in_ch_{}".format(i)] for i in range(self.n_in)]}; outs: {self.output_channels} out of {[state["out_ch_{}".format(i)] for i in range(self.n_out)]}')


class SimpleCable(QWidget):
    def __init__(self, x, y, widget_out, widget_out_id, parent=None):
        super().__init__(parent)
        self.patch_area = parent
        self.setMinimumSize(20, 20)
        self.setMouseTracking(True)
        self.brush = Qt.BrushStyle.NoBrush
        self.pen_color = Qt.GlobalColor.black
        # comincia con il cavo da tendere (questa classe è intesa per essere istanziata durante un mouseDownAction)
        self.is_dragging = True
        self.is_clicked = False
        self.type = "Simple"
        self.jack_dwn_svg = QIcon(os.path.join(GRAPHICS_PATH, "CableJackDown.svg"))
        self.jack_up_svg = QIcon(os.path.join(GRAPHICS_PATH, "CableJackUp.svg"))
        self.cable_svg = QIcon(os.path.join(GRAPHICS_PATH, "Cable.svg"))
        self.outlet_point = QPoint(int(x), int(y))
        self.drag_x = x
        self.drag_y = y
        self.widget_out = widget_out
        self.widget_out_id = widget_out_id
        self.widget_out_uuid = self.widget_out.getUUID()
        self.widget_in = None
        self.widget_in_id = -1
        self.widget_in_uuid = -1
        self.setGeometry(0, 0, self.patch_area.width(), self.patch_area.height())
        self.setWindowFlags(self.windowFlags() & Qt.WindowType.WindowTransparentForInput)

    def get_undo_stack(self):
        return self.patch_area.get_undo_stack()

    def select(self):
        self.is_clicked = True

    def unselect(self):
        self.is_clicked = False

    def addInletWidget(self, widget, inlet_id):
        self.widget_in = widget
        self.widget_in_id = inlet_id
        self.widget_in_uuid = self.widget_in.getUUID()

    def changeDestination(self, x, y):
        self.drag_x = x
        self.drag_y = y

    def onHovered(self, event):
        if self.is_dragging:
            self.drag_x = event.position().x()
            self.drag_y = event.position().y()
            self.repaint()

    def mousePressEvent(self, event, recursion=False):
        self.patch_area.deselectCables()
        self.patch_area.patch.parent.settings_bar.inspect_widget(None)
        pixmap = self.grab()
        img = pixmap.toImage()
        color = img.pixelColor(int(event.position().x()), int(event.position().y()))

        if self.checkEventInsideLine(event):
            # If Right-Click, delete Cable
            if event.button() == Qt.MouseButton.RightButton:
                self.is_dragging = not self.is_dragging
                self.disconnectWidgets()
                self.patch_area.place_cable()
                self.patch_area.flush_cable(self)
            if event.button() == Qt.MouseButton.LeftButton:
                self.patch_area.propagateCableMouseClick(event, self, subtractGlobalPos=True)
                self.select()
        else:
            self.unselect()
            if recursion:
                event.accept()
            else:
                self.patch_area.propagateCableMouseClick(event, self, subtractGlobalPos=True)
                event.ignore()

    def mouseMoveEvent(self, event):
        if not event.buttons():
            self.onHovered(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        pass

    def disconnectWidgets(self):
        pass

    def checkEventInsideLine(self, event):
        sensibility = 20
        if self.type == "MIDI":
            start_point = self.widget_out.getMIDIOutletPos(self.widget_out_id)
        else:
            start_point = self.widget_out.getOutletPos(self.widget_out_id)
        if self.widget_in is not None:
            if type(self.widget_in_id) == str:
                end_point = self.widget_in.getParameterPos(self.widget_in_id)
            else:
                if self.type == "MIDI":
                    end_point = self.widget_in.getMIDIInletPos(self.widget_in_id)
                else:
                    end_point = self.widget_in.getInletPos(self.widget_in_id)
        else:
            end_point = QPointF(self.drag_x, self.drag_y)
        rect = QPolygonF([
            QPointF(start_point.x() - sensibility, start_point.y() - sensibility),
            QPointF(start_point.x() + sensibility, start_point.y() + sensibility),
            QPointF(end_point.x() - sensibility, end_point.y() - sensibility),
            QPointF(end_point.x() + sensibility, end_point.y() + sensibility)
        ])
        pixmap = self.grab()

        image = pixmap.scaled(self.patch_area.width(), self.patch_area.height()).toImage()
        color = image.pixelColor(QPoint(int(event.position().x()), int(event.position().y())))
        # return rect.containsPoint(QPointF(event.position().x(), event.position().y()), Qt.FillRule.WindingFill)
        # print("Cable click at", QPoint(int(event.position().x()), int(event.position().y())), "image size",
        #       (image.width(), image.height()), "start-end points", start_point, end_point, "color sum:",
        #       (color.red() + color.green() + color.blue()))
        if (color.red() + color.green() + color.blue()) == 0:
            return True
        else:
            return False

    def paintEvent(self, event):
        if self.type == "MIDI":
            start_point = self.widget_out.getMIDIOutletPos(self.widget_out_id)
        else:
            start_point = self.widget_out.getOutletPos(self.widget_out_id)
        if self.widget_in is not None:
            if type(self.widget_in_id) == str:
                end_point = self.widget_in.getParameterPos(self.widget_in_id)
            else:
                if self.type == "MIDI":
                    end_point = self.widget_in.getMIDIInletPos(self.widget_in_id)
                else:
                    end_point = self.widget_in.getInletPos(self.widget_in_id)
        else:
            end_point = QPoint(int(self.drag_x), int(self.drag_y))
        painter = QPainter(self)
        path = QPainterPath()
        pen = QPen()
        pen.setWidth(4)
        if self.is_clicked:
            pen.setColor(Qt.GlobalColor.darkYellow)
        else:
            pen.setColor(Qt.GlobalColor.black)
        painter.setPen(pen)
        # Qui per linea retta
        # painter.drawLine(start_point.x(), start_point.y(), end_point.x(), end_point.y())
        path.moveTo(QPointF(start_point.x(), start_point.y()))
        # Qui per curva cubica
        path.cubicTo(start_point.x(), (start_point.y() + end_point.y()) / 2, end_point.x(),
                     (start_point.y() + end_point.y()) / 2, end_point.x(), end_point.y())
        painter.drawPath(path)
        if end_point.y() >= start_point.y():
            painter.translate(end_point.x(), end_point.y())
            self.jack_dwn_svg.paint(painter, -3, 0, 6, 20)
        else:
            painter.translate(end_point.x(), end_point.y())
            self.jack_up_svg.paint(painter, -3, -20, 6, 20)

    def __getstate__(self):
        d = {
            "x": self.drag_x,
            "y": self.drag_y,
            "widget_out_id": self.widget_out_id,
            "widget_out_uuid": self.widget_out_uuid,
            "widget_in_id": self.widget_in_id,
            "widget_in_uuid": self.widget_in_uuid
        }
        return d

    def __setstate__(self, state):
        self.widget_out_uuid = state["widget_out_uuid"]
        self.widget_out_uuid = state["widget_in_uuid"]
        self.widget_out_id = state["widget_out_id"]
        self.widget_out_id = state["widget_in_id"]


class AudioCable(SimpleCable):
    def __init__(self, x, y, widget_out, widget_out_id, parent=None, is_inside_subpatch=False):
        super().__init__(x, y, widget_out, widget_out_id, parent)
        self.type = "Audio"
        self.is_inside_subpatch = is_inside_subpatch
        self.connects_parameter = False
        if self.is_inside_subpatch:
            self.widget_out = widget_out
            self.widget_out_id = widget_out_id
            self.widget_out_out = self.widget_out.subpatch.getSubPatchInstanceOutletWidget(self.widget_out.getUUID(),
                                                                                           self.widget_out.out_names[
                                                                                               self.widget_out_id])
            self.widget_out_out_id = 0
            # print("self.widget_out_out", self.widget_out_out, "self.widget_out_out_id", self.widget_out_out_id)
        else:
            self.widget_out = widget_out
            self.widget_out_id = widget_out_id
        # print(f"Widget Out is {self.widget_out}; Its bus is: {self.widget_out.bus}")
        self.pen_color = QColor(_6color_palette_01)
        self.bus = None

    def connectWidgetParameter(self):
        # Widget In:  the widget that RECEIVES the PARAM
        # Widget Out: the widget that SENDS its OUTPUT
        # OUTPUTS pretrain Bus instances, and the PARAM are connected to OUTPUT's Buses
        if self.widget_out.bus is None:
            self.widget_in.change_param(self.widget_in_id, self.bus.getChan(self.widget_out_id))
        else:
            self.widget_in.change_param(self.widget_in_id, self.widget_out.bus.getChan(self.widget_out_id))

        if hasattr(self.widget_in, "group"):
            self.widget_out.moveBefore(self.widget_in.group)
        elif hasattr(self.widget_in, "synth"):
            self.widget_out.moveBefore(self.widget_in.synth)
        self.patch_area.repatch_audio()
        scsynth.dumpNodeTree(group=0, showArgs=True)

    def connectWidgets(self):
        # Widget In:  the widget that RECEIVES the INPUT
        # Widget Out: the widget that SENDS its OUTPUT
        # OUTPUTS pretrain Bus instances, and the INPUTS are connected to OUTPUT's Buses
        # if self.widget_out.bus is None:
        if self.is_inside_subpatch:
            bus = self.widget_out_out.bus if self.is_inside_subpatch else self.widget_out.bus
            # print("BUS IS:", bus, "self.widget_out.bus:", self.widget_out.bus, "; self.widget_out_out.bus:", self.widget_out_out.bus)
        else:
            bus = self.widget_out.bus

        if bus is None:
            if type(self.widget_in_id) == str:
                # self.widget_in.change_param(self.widget_in_id, self.bus.getChan(self.widget_out_id))
                self.widget_in.change_param(self.widget_in_id, self.bus.getChan(
                    self.widget_out_out_id if self.is_inside_subpatch else self.widget_out_id))
            else:
                # self.widget_in.change_in_ch(self.widget_in_id, self.bus.getChan(self.widget_out_id))
                self.widget_in.change_in_ch(self.widget_in_id, self.bus.getChan(
                    self.widget_out_out_id if self.is_inside_subpatch else self.widget_out_id))
        else:
            if type(self.widget_in_id) == str:
                # self.widget_in.change_param(self.widget_in_id, self.widget_out.bus.getChan(self.widget_out_id))
                self.widget_in.change_param(self.widget_in_id, bus.getChan(
                    self.widget_out_out_id if self.is_inside_subpatch else self.widget_out_id))
            else:
                # self.widget_in.change_in_ch(self.widget_in_id, self.widget_out.bus.getChan(self.widget_out_id))
                self.widget_in.change_in_ch(self.widget_in_id, bus.getChan(
                    self.widget_out_out_id if self.is_inside_subpatch else self.widget_out_id))
        if hasattr(self.widget_in, "group"):
            self.widget_out.moveBefore(self.widget_in.group)
        elif hasattr(self.widget_in, "synth"):
            self.widget_out.moveBefore(self.widget_in.synth)
        self.patch_area.repatch_audio()
        scsynth.dumpNodeTree(group=0, showArgs=True)

    def connectSubPatchWidgets(self):
        # Widget In:  the widget that RECEIVES the INPUT
        # Widget Out: the widget that SENDS its OUTPUT
        # OUTPUTS pretrain Bus instances, and the INPUTS are connected to OUTPUT's Buses
        self.widget_in_in = self.widget_in.subpatch.getSubPatchInstanceInletWidget(self.widget_in.getUUID(),
                                                                                   self.widget_in.in_names[
                                                                                       self.widget_in_id])
        # print("self.widget_in_in", self.widget_in_in.active, self.widget_in_in.getUUID())
        if self.widget_out.bus is None:
            # print("connecting widget_in_in 0 to", self.bus.getChan(self.widget_out_out_id if self.is_inside_subpatch else self.widget_out_id))
            # self.widget_in_in.change_in_ch(0, self.bus.getChan(self.widget_out_id))
            self.widget_in_in.change_in_ch(0, self.bus.getChan(
                self.widget_out_out_id if self.is_inside_subpatch else self.widget_out_id))
        else:
            # print("connecting widget_in_in 0 to", self.widget_out.bus.getChan(self.widget_out_out_id if self.is_inside_subpatch else self.widget_out_id))
            # self.widget_in_in.change_in_ch(0, self.widget_out.bus.getChan(self.widget_out_id))
            self.widget_in_in.change_in_ch(0, self.widget_out.bus.getChan(
                self.widget_out_out_id if self.is_inside_subpatch else self.widget_out_id))
        if hasattr(self.widget_in, "group"):
            # print("Moving group!")
            self.widget_out.moveBefore(self.widget_in.group)
        elif hasattr(self.widget_in, "synth"):
            self.widget_out.moveBefore(self.widget_in.synth)
        # print(f"widget_in_in in_ch_0 is now {self.widget_in_in.input_channels}")
        self.patch_area.repatch_audio()
        # print(f"widget_in_in in_ch_0 is now {self.widget_in_in.input_channels}")
        scsynth.dumpNodeTree(group=0, showArgs=True)

    def disconnectSubPatchWidgets(self):
        self.widget_in_in = self.widget_in.subpatch.getSubPatchInstanceInletWidget(self.widget_in.getUUID(),
                                                                                   self.widget_in.in_names[
                                                                                       self.widget_in_id])
        self.widget_in_in.synth.set(f"in_ch_0", scsynth.getDefaultInBus())
        settings = deepcopy(self.widget_in_in.getSettings())
        settings['Inputs'][f"in_ch_0"] = scsynth.getDefaultInBus()
        self.widget_in_in.setSettings(settings)
        self.widget_in = None
        self.widget_in_in = None
        self.widget_in_id = None
        scsynth.dumpNodeTree()

    def disconnectWidgets(self):
        # Widget In:  the widget that RECEIVES the INPUT
        # Widget Out: the widget that SENDS its OUTPUT
        # If parameter bus, set to -1
        if type(self.widget_in_id) == str:
            settings = self.widget_in.getSettings()
            settings["Parameters"][self.widget_in_id]["bus"] = -1
            self.widget_in.setSettings(settings)
            if issubclass(self.widget_in.__class__, AudioMIDIWidget):
                print("AudioMIDIWidget eheheh")
                self.widget_in.computeSynthArgs()
        else:
            try:
                self.widget_in.synth.set(f"in_ch_{self.widget_in_id}", scsynth.getDefaultInBus())
                settings = deepcopy(self.widget_in.getSettings())
                settings['Inputs'][f"in_ch_{self.widget_in_id}"] = scsynth.getDefaultInBus()
                self.widget_in.setSettings(settings)
                # print("Input is:", self.widget_in_id, self.widget_in.getSettings()['Inputs'][f"in_ch_{self.widget_in_id}"])
            except:  # in case of unconnected cable (e.g., when deleting a running cable), do nothing...
                pass
        self.widget_in = None
        self.widget_in_id = None
        scsynth.dumpNodeTree()

    def addInletWidget(self, widget, inlet_id):
        self.widget_in = widget
        self.widget_in_id = inlet_id
        self.widget_in_uuid = self.widget_in.getUUID()
        self.connectWidgets()

    def addSubPatchInletWidget(self, widget, inlet_id):
        self.widget_in = widget
        self.widget_in_id = inlet_id
        self.widget_in_uuid = self.widget_in.getUUID()
        self.connectSubPatchWidgets()

    def addParameterWidget(self, widget, inlet_id):
        self.widget_in = widget
        self.widget_in_id = inlet_id
        self.widget_in_uuid = self.widget_in.getUUID()
        self.connects_parameter = True
        self.connectWidgetParameter()


class MIDICable(SimpleCable):
    def __init__(self, x, y, widget_out, widget_out_id, parent=None):
        super().__init__(x, y, widget_out, widget_out_id, parent)
        self.type = "MIDI"
        self.widget_out = widget_out
        self.widget_out_id = widget_out_id
        self.widget_in = None
        self.widget_in_id = None
        self.widget_in_uuid = None
        self.pen_color = QColor(_6color_palette_06)

    def addInletWidget(self, widget, inlet_id):
        self.widget_in = widget
        self.widget_in_id = inlet_id
        self.widget_in_uuid = self.widget_in.getUUID()
        self.connectWidgets()

    def connectWidgets(self):
        # Widget In:  the widget that RECEIVES the INPUT
        # Widget Out: the widget that SENDS its OUTPUT
        # OUTPUTS pretrain Bus instances, and the INPUTS are connected to OUTPUT's Busses
        if not self.widget_in in self.widget_out.midi_destinations:
            self.widget_out.addMIDIReceiver(self.widget_in)

    def disconnectWidgets(self):
        try:
            self.widget_out.removeMIDIReceiver(self.widget_in)
        except:
            print("No MIDI Destination Widget to remove...")


""" Patch Buffers """


class PatchBuffers(QWidget):
    def __init__(self, parent=None, server=None, patch=None):
        super().__init__(parent)
        self.server = server
        self.patch = patch
        self.buffers = {}

    def getBuffers(self):
        return self.buffers

    def addBuffer(self, bufnum=-1, name="tmp", duration=1, channels=1):
        if bufnum < 0:
            bufnum = self.server.queryFreeBuffer()
        if name in [self.buffers[key]["name"] for key in self.buffers.keys()]:
            name += "_1"
        if duration <= 0.0:
            duration = 0.01
        # print("duration", duration, type(duration), "server sample_rate", self.server.sample_rate, type(self.server.sample_rate))
        numFrames = int(duration * self.server.sample_rate)
        self.buffers[str(bufnum)] = {
            "name": name,
            "bufnum": bufnum,
            "duration": duration,
            "channels": channels,
            "numFrames": numFrames
        }
        c_print("cyan", f"Allocating buffer {self.buffers[str(bufnum)]}")
        self.server.addBuffer(bufnum)
        self.server.allocBuffer(numFrames, channels, bufnum)

    def removeBuffer(self, bufnum):
        if str(bufnum) in self.buffers.keys():
            self.server.removeBuffer(self.buffers[str(bufnum)]["bufnum"])
            del self.buffers[str(bufnum)]

    def removeAllBuffers(self):
        for buf in self.buffers.keys():
            self.server.removeBuffer(self.buffers[buf]["bufnum"])
        self.buffers = {}

    def __getstate__(self):
        d = {"buffers": self.buffers}
        return d

    def __setstate__(self, state):
        self.removeAllBuffers()
        for buf in state["buffers"]:
            self.addBuffer(int(state["buffers"][buf]["bufnum"]), state["buffers"][buf]["name"],
                           float(state["buffers"][buf]["duration"]), int(state["buffers"][buf]["channels"]))


class QFloatEdit(QLineEdit):
    def __init__(self, *__args):
        super().__init__(*__args)

    def text(self):
        return self.text()

    def floatText(self):
        return float(self.text().replace(",", "."))
