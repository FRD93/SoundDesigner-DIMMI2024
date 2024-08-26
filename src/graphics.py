import os
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtSvg import QSvgRenderer
import configparser as cp
import threading
import classes
import time
import pickle


from PyQt6 import sip
import numpy as np
from collections import defaultdict, deque
import functions
import supercollider
# from parameters import *
from primitives import *
from timeline import *
from curves import *
import datetime
from settings_window import Settings
# Import Custom Widgets
from midi_widgets.players import *
from midi_widgets.midiio import *
from midi_widgets.midimapping import *
from midi_widgets.controllers import *
from audio_midi_widgets.MIDIConversion import *
from datetime import datetime
from path_manager import STYLE_PATH, CONFIG_PATH, STYLESHEET_PATH, WIDGETS_PATH, GRAPHICS_PATH

# Load styles
import json
try:
    with open(STYLE_PATH, "r") as f:  # "./style.json"
        APP_STYLE = json.load(f)
except:
    with open("/Users/francescodani/Documents/SoundDesigner/SoundDesigner/src/style.json", "r") as f:  # "./style.json"
        APP_STYLE = json.load(f)
print("APP_STYLE:", APP_STYLE)

conf = cp.ConfigParser()
conf.read(CONFIG_PATH)  # "config.ini"
try:
    PPQN = conf.getint("GENERAL", "ppqn")
    SCSYNTH_SYNTHDEF_PATH = conf.get("SCSYNTH", "synthdef_path")
    AMBISONICS_KERNEL_PATH = conf.get("SCSYNTH", "ambisonics_kernels_path")
    _6color_palette_01 = "#242326"
    _6color_palette_02 = "#242326"
    _6color_palette_03 = "#323436"
    _6color_palette_04 = "#323436"
    _6color_palette_05 = "#464850"
    _6color_palette_06 = "#464850"
    icon_size = conf.getint("APPEARENCE", "icon_size")
except:
    c_print("red", "[ERROR]: Config File not found")
    PPQN = 96
    BUS_VISUAL_UPDATE_FREQ = 20.0
    SCSYNTH_SYNTHDEF_PATH = "/Users/francescodani/Library/Application Support/SuperCollider/synthdefs"
    AMBISONICS_KERNEL_PATH = "/Users/francescodani/Documents/SoundDesigner/ATK/FOA kernels"
    _6color_palette_01 = "#242326"
    _6color_palette_02 = "#242326"
    _6color_palette_03 = "#323436"
    _6color_palette_04 = "#323436"
    _6color_palette_05 = "#464850"
    _6color_palette_06 = "#464850"
    icon_size = 24


"""
Patch:

serve per creare catene di generatori di suono ed effetti.
In questo modo si riesce a frammentare la GUI in più livelli:
un livello generale che permette di creare e connettere Patch, e un livello
di Patch dove si possono editare i singoli generatori ed effetti di ciascun Patch.
Un Patch avrà dei canali di Output e (non sempre) dei canali di Input. La gestione
dei canali che connettono i vari Patch tra loro o verso il MasterOutput è affidata
alla classe PatchManager.
"""


class DeleteCable(QUndoCommand):
    def __init__(self, patch_area, cable, type="Audio"):
        super(DeleteCable, self).__init__(f"Deleting cable {cable}")
        self.patch_area = patch_area
        self.cable = cable
        self.cable_type = type

    def undo(self):
        if self.cable_type == "Audio":
            self.patch_area.audio_cables.append(self.cable)
            self.cable.hide()
            del self.cable
        elif self.cable_type == "MIDI":
            self.patch_area.midi_cables.append(self.cable)
            self.cable.hide()
            del self.cable
        else:
            c_print("red", f"Cable Type not supported: {self.cable_type}")

    def redo(self):
        if self.cable_type == "Audio":
            self.patch_area.audio_cables.remove(self.cable)
            self.cable.hide()
            del self.cable
        elif self.cable_type == "MIDI":
            self.patch_area.midi_cables.remove(self.cable)
            self.cable.hide()
            del self.cable
        else:
            c_print("red", f"Cable Type not supported: {self.cable_type}")


class PatchArea(QLabel):
    def __init__(self, patch, context, parent=None):
        super().__init__(parent=parent)
        self.setMouseTracking(True)
        self.setObjectName("patch_area")
        self.patch = patch
        self.setMinimumSize(1920, 1080)
        self.grid_size = 25
        self.context = context
        self.audio_cables = []
        self.midi_cables = []
        self.current_cable = None

    def get_undo_stack(self):
        return self.patch.get_undo_stack()

    def repatch_audio(self):
        print("\nBeginning audio repatch:")
        widget_ins = defaultdict(list)
        node_order = []
        sources = []
        # Conta quanti inlet (connessi) ha ciascun widget
        for widget in self.patch.audio_widgets:
            widget_ins[widget.getUUID()] = []
            for cable in self.audio_cables:
                if cable.widget_in:
                    if widget.getUUID() == cable.widget_in.getUUID():
                        widget_ins[widget.getUUID()].append(cable.widget_out.getUUID())
        is_first_widget = True
        # Metti in Head i widget con zero inlet (connessi)
        for widget in self.patch.audio_widgets + self.patch.subpatch_widgets:
            if len(widget_ins[widget.getUUID()]) == 0:
                if is_first_widget == True:
                    print("Moving to Head:", widget.getUUID(), widget.synth_name)
                    if hasattr(widget, "group"):
                        widget.group.moveToHead()
                    elif hasattr(widget, "synth"):
                        widget.synth.moveToHead()
                else:
                    print("Moving", widget.getUUID(), widget.synth_name, "AFTER", is_first_widget.getUUID(), is_first_widget.synth_name)
                    print(f"widget: {widget} ; is_first_widget: {is_first_widget}")
                    if hasattr(is_first_widget, "group"):
                        widget.moveAfter(is_first_widget.group)
                    elif hasattr(widget, "synth"):
                        widget.moveAfter(is_first_widget.synth)
                is_first_widget = widget
                sources.append(widget.getUUID())
                del widget_ins[widget.getUUID()]
        # Metti in After i widget con 1 inlet i cui nodi Before siano stati rimossi dalla lista
        # TODO: mettere loop infinito al posto di range(3)!!!
        for _ in range(3):
            # TODO: concatenare self.patch.audio_widgets con self.patch.subpatch_widgets
            for widget in self.patch.audio_widgets + self.patch.subpatch_widgets:
                if widget.getUUID() in widget_ins.keys():
                    if len(widget_ins[widget.getUUID()]) == 1:
                        for cable in self.audio_cables:
                            if cable.widget_in and cable.widget_out:
                                if (widget.getUUID() == cable.widget_in.getUUID()) and (widget_ins[widget.getUUID()][0] == cable.widget_out.getUUID()):  # Trova il cavo associato
                                    if cable.widget_out.getUUID() not in widget_ins.keys():
                                        if hasattr(cable.widget_out, "group"):
                                            widget.moveAfter(cable.widget_out.group)
                                        elif hasattr(cable.widget_out, "synth"):
                                            widget.moveAfter(cable.widget_out.synth)
                                        node_order.append(widget.getUUID())
                                        print("Moving", widget.getUUID(), widget.synth_name, "AFTER", cable.widget_out.getUUID(), cable.widget_out.synth_name)
                                        del widget_ins[widget.getUUID()]
            # Se trovi un widget con >1 inlet i cui nodi Before siano stati TUTTI rimossi dalla lista, prendi l'ultimo e mettilo After a quello
            for widget in self.patch.audio_widgets + self.patch.subpatch_widgets:
                if widget.getUUID() in widget_ins.keys():
                    if len(widget_ins[widget.getUUID()]) > 1:
                        # print(f"Found {widget.getUUID()}, {widget.synth_name} with length: >1")
                        target_node = -1
                        to_be_processed = 0  # Trova i nodi dipendenti ancora da processare
                        for w_in in widget_ins[widget.getUUID()]:
                            if w_in in widget_ins.keys():
                                to_be_processed += 1
                        if to_be_processed == 0:  # Se non hai nodi dipendenti ancora da processare
                            # Trova l'ultimo nodo messo in After
                            for node in reversed(node_order):
                                if node in widget_ins[widget.getUUID()]:
                                    target_node = node
                                    break
                            if target_node == -1:
                                target_node = sources[-1]
                            # Metti il widget After target_node
                            has_to_break = False
                            for node_widget in self.patch.audio_widgets + self.patch.subpatch_widgets:
                                if node_widget.getUUID() == target_node:
                                    for cable in self.audio_cables:
                                        if target_node == cable.widget_out.getUUID():  # Trova il cavo associato
                                            if hasattr(cable.widget_out, "group"):
                                                widget.moveAfter(cable.widget_out.group)
                                            elif hasattr(cable.widget_out, "synth"):
                                                widget.moveAfter(cable.widget_out.synth)
                                            node_order.append(widget.getUUID())
                                            print("Moving", widget.getUUID(), widget.synth_name, "AFTER", cable.widget_out.getUUID(), cable.widget_out.synth_name)
                                            del widget_ins[widget.getUUID()]
                                            has_to_break = True
                                            break
                                        if has_to_break:
                                            break
        for wid in self.patch.subpatch_widgets:
            wid.repatch_audio()
        print("Ended audio repatch!\n")
        self.patch.audiostatus.populate()

    def redraw_cables(self):
        for cable in self.audio_cables:
            cable.repaint()
        for cable in self.midi_cables:
            cable.repaint()

    def lower_cables(self):
        for cable in self.audio_cables:
            cable.lower()
        for cable in self.midi_cables:
            cable.lower()

    def add_audio_cable(self, cable):
        self.audio_cables.append(cable)
        self.current_cable = cable

    def add_midi_cable(self, cable):
        self.midi_cables.append(cable)
        self.current_cable = cable

    def is_placing_cable(self):
        return self.current_cable is not None

    def place_cable(self):
        self.current_cable = None

    def flush_current_cable(self):
        try:
            self.audio_cables.remove(self.current_cable)
            self.current_cable.hide()
            del self.current_cable
        except:
            pass
        try:
            self.midi_cables.remove(self.current_cable)
            self.current_cable.hide()
            del self.current_cable
        except:
            pass
        self.current_cable = None

    def flush_cable(self, cable):
        try:
            self.audio_cables.remove(cable)
            cable.hide()
            del cable
        except:
            pass
        try:
            self.midi_cables.remove(cable)
            cable.hide()
            del cable
        except:
            pass

    def propagateCableMouseClick(self, event, cable_sender, subtractGlobalPos=False):
        self.patch.parent.settings_bar.inspect_widget(None)
        for cable in self.audio_cables:
            if cable_sender != cable:
                cable.mousePressEvent(event, recursion=True)
        for cable in self.midi_cables:
            if cable_sender != cable:
                cable.mousePressEvent(event, recursion=True)
        self.patch.propagateCableMouseClick(event, subtractGlobalPos)

    def deselectCables(self):
        for cable in self.audio_cables:
            cable.unselect()
        for cable in self.midi_cables:
            cable.unselect()

    def mouseMoveEvent(self, event):
        if not event.buttons():
            if self.current_cable is not None:
                self.current_cable.changeDestination(event.position().x(), event.position().y())

    def calcMaxDimensions(self):
        max_audio_width = [wid.geometry().x() for wid in self.patch.audio_widgets]
        if len(max_audio_width) == 0:
            max_audio_width = [400]
        max_midi_width = [wid.geometry().x() for wid in self.patch.midi_widgets]
        if len(max_midi_width) == 0:
            max_midi_width = [400]
        max_audio_width = np.amax(max_audio_width)
        max_midi_width = np.amax(max_midi_width)
        max_width = max(max_audio_width, max_midi_width)
        max_width += 400
        max_audio_height = [wid.geometry().y() for wid in self.patch.audio_widgets]
        if len(max_audio_height) == 0:
            max_audio_height = [400]
        max_midi_height = [wid.geometry().y() for wid in self.patch.midi_widgets]
        if len(max_midi_height) == 0:
            max_midi_height = [400]
        max_audio_height = np.amax(max_audio_height)
        max_midi_height = np.amax(max_midi_height)
        max_height = max(max_audio_height, max_midi_height)
        max_height += 400
        return max_width, max_height

    def __getstate__(self):
        print("audio cables:", self.audio_cables)
        d = {
            "audio_cables": [cable.__getstate__() for cable in self.audio_cables],
            "midi_cables": [cable.__getstate__() for cable in self.midi_cables],
        }
        print("saving cables dictionary:", d)
        return d

    def __setstate__(self, state):
        self.audio_cables = []
        print("Setting audio cables states:", state["audio_cables"])
        for index, cable_state in enumerate(state["audio_cables"]):
            widget_out = None
            widget_in = None
            print("OUT UUID:", cable_state["widget_out_uuid"])
            print("IN UUID:", cable_state["widget_in_uuid"])
            print("audio uuids:", [widget.getUUID() for widget in self.patch.audio_widgets])
            print("audio_midi uuids:", [widget.getUUID() for widget in self.patch.audio_midi_widgets])
            print("midi uuids:", [widget.getUUID() for widget in self.patch.midi_widgets])
            print("subpatch uuids:", [widget.getUUID() for widget in self.patch.subpatch_widgets])
            # is SubPatchInstance Widget?
            for widget in self.patch.subpatch_widgets:
                if widget.getUUID() == cable_state["widget_out_uuid"]:
                    widget_out = widget
                if widget.getUUID() == cable_state["widget_in_uuid"]:
                    widget_in = widget
            # is Audio Widget?
            for widget in self.patch.audio_widgets:
                if widget.getUUID() == cable_state["widget_out_uuid"]:
                    widget_out = widget
                if widget.getUUID() == cable_state["widget_in_uuid"]:
                    widget_in = widget
            # is AudioMIDI Widget?
            for widget in self.patch.audio_midi_widgets:
                if widget.getUUID() == cable_state["widget_out_uuid"]:
                    widget_out = widget
                if widget.getUUID() == cable_state["widget_in_uuid"]:
                    widget_in = widget
            cable = AudioCable(cable_state["x"], cable_state["y"], widget_out, cable_state["widget_out_id"], self)
            if type(cable_state["widget_in_id"]) == str:
                cable.addParameterWidget(widget_in, cable_state["widget_in_id"])
            else:
                print("type(widget_in):", type(widget_in))
                if type(widget_in) == SubPatchInstanceWidget:
                    widget_in.subpatch.update_subpatch_instances()
                    cable.addSubPatchInletWidget(widget_in, cable_state["widget_in_id"])
                else:
                    cable.addInletWidget(widget_in, cable_state["widget_in_id"])
            self.add_audio_cable(cable)
            self.place_cable()
        # MIDI Cables
        try:
            _ = state["midi_cables"]
        except KeyError:
            state["midi_cables"] = []
        for index, cable_state in enumerate(state["midi_cables"]):
            widget_out = None
            widget_in = None
            # is MIDI Widget?
            for widget in self.patch.midi_widgets:
                if widget.getUUID() == cable_state["widget_out_uuid"]:
                    widget_out = widget
                if widget.getUUID() == cable_state["widget_in_uuid"]:
                    widget_in = widget
            # is AudioMIDI Widget?
            for widget in self.patch.audio_midi_widgets:
                if widget.getUUID() == cable_state["widget_out_uuid"]:
                    widget_out = widget
                if widget.getUUID() == cable_state["widget_in_uuid"]:
                    widget_in = widget
            cable = MIDICable(cable_state["x"], cable_state["y"], widget_out, cable_state["widget_out_id"], self)
            cable.addInletWidget(widget_in, cable_state["widget_in_id"])
            self.add_midi_cable(cable)
        print("Number of audio cables:", len(self.audio_cables))
        self.repatch_audio()
        self.lower_cables()


def load_widgets_list(base_path: str) -> dict:
    # base_path = os.path.abspath(base_path) + "/"
    base_path = WIDGETS_PATH
    widgets = {}
    for keyword in ["audio", "midi", "audio_midi"]:
        widgets[keyword] = {}
        for filename in os.listdir(base_path + keyword + "_widgets/"):
            if ".json" in filename:
                name = filename.replace(".json", "")
                widgets[keyword][name] = {}
                # print("path:", base_path + keyword + "_widgets/" + filename)
                with open(base_path + keyword + "_widgets/" + filename, "r") as fi:
                    data = json.loads(fi.read())
                    for key in data.keys():
                        widgets[keyword][name][key] = data[key]
    return widgets


class WidgetButton(QWidget):
    def __init__(self, widget_name, icon, parent=None, type="Audio"):
        super().__init__(parent)
        self.widget_name = widget_name
        self.parent = parent
        self.type = type
        layout = QVBoxLayout()
        self.setLayout(layout)

        button = QToolButton()
        button.setIcon(icon)
        button.setIconSize(QSize(200, 200))
        # button.setFlat(True)  # Rimuove il bordo del pulsante
        button.setText(widget_name)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        if self.type == "Audio":
            button.clicked.connect(self.parent.patch.add_audio_widget)
        elif self.type == "MIDI":
            button.clicked.connect(self.parent.patch.add_midi_widget)
        elif self.type == "AudioMIDI":
            button.clicked.connect(self.parent.patch.add_audio_midi_widget)
        elif self.type == "SubPatch":
            button.clicked.connect(self.parent.patch.add_sub_patch_widget)
        label = QLabel(widget_name)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(button)
        layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)  # Allinea la label al centro


class WidgetSearchDialog(QDialog):
    def __init__(self, audio_widgets, midi_widgets, audio_midi_widgets, parent=None):
        super().__init__(parent)
        self.audio_widgets = audio_widgets
        self.midi_widgets = midi_widgets
        self.audio_midi_widgets = audio_midi_widgets
        self.parent = parent
        # self.patch = self.parent.patch
        self.patch = self.parent.getCurrentPatch()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Search Widgets")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet(f"background-color: {_6color_palette_06};")  # Cambia il colore di sfondo

        layout = QVBoxLayout()

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setObjectName("widget-param")
        self.search_input.setPlaceholderText("Search by name or type (Audio, MIDI, Audio/MIDI)...")
        self.search_input.textChanged.connect(self.filter_widgets)
        self.search_input.setStyleSheet("background-color: #f0f0f0;")
        layout.addWidget(self.search_input)

        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # Results widget
        self.results_widget = QWidget()
        self.results_layout = QGridLayout()
        self.results_widget.setLayout(self.results_layout)
        scroll_area.setWidget(self.results_widget)

        self.setLayout(layout)

        # Populate the grid initially
        self.filter_widgets()

    def create_icon(self, widget_name, category):
        # Cerca l'icona PNG nelle sottocartelle delle directory audio, audio_midi e midi
        base_paths = {
            "audio": os.path.join(GRAPHICS_PATH, "widgets/audio"),
            "audio_midi": os.path.join(GRAPHICS_PATH, "widgets/audio_midi"),
            "midi": os.path.join(GRAPHICS_PATH, "widgets/midi"),
            "subpatch": os.path.join(GRAPHICS_PATH, "widgets/subpatch")
        }
        for subdir, dirs, files in os.walk(base_paths[category]):
            for file in files:
                if file == f"{widget_name}.png":
                    pixmap = QPixmap(os.path.join(subdir, file))
                    icon = QIcon(pixmap)
                    return icon
        return QIcon()  # Icona di fallback nel caso in cui l'icona non venga trovata

    def filter_widgets(self):
        search_text = self.search_input.text().lower()
        for i in reversed(range(self.results_layout.count())):
            widget_to_remove = self.results_layout.itemAt(i).widget()
            self.results_layout.removeWidget(widget_to_remove)
            widget_to_remove.setParent(None)

        row = 0
        col = 0
        if "audio" in search_text or "midi" in search_text or "audio/midi" in search_text or "audio midi" in search_text:
            # Search by type
            if "audio" in search_text and "audio/midi" not in search_text and "audio midi" not in search_text:
                for widget_name in self.audio_widgets:
                    icon = self.create_icon(widget_name, "audio")
                    button = WidgetButton(widget_name, icon, self, type="Audio")
                    self.results_layout.addWidget(button, row, col)
                    col += 1
                    if col > 3:
                        col = 0
                        row += 1

            if "audio/midi" in search_text or "audio midi" in search_text:
                for widget_name in self.audio_midi_widgets:
                    icon = self.create_icon(widget_name, "audio_midi")
                    button = WidgetButton(widget_name, icon, self, type="AudioMIDI")
                    self.results_layout.addWidget(button, row, col)
                    col += 1
                    if col > 3:
                        col = 0
                        row += 1

            if "midi" in search_text and "audio/midi" not in search_text and "audio midi" not in search_text:
                for widget_name in self.midi_widgets:
                    icon = self.create_icon(widget_name, "midi")
                    button = WidgetButton(widget_name, icon, self, type="MIDI")
                    self.results_layout.addWidget(button, row, col)
                    col += 1
                    if col > 3:
                        col = 0
                        row += 1
        else:
            # Search by name
            # SubPatch
            for key in self.parent.patches.keys():
                widget_name = key.split(":")[1]
                if (widget_name != "main") and (widget_name != self.patch.name):
                    if search_text in widget_name.lower():
                        icon = self.create_icon("Default", "subpatch")
                        button = WidgetButton(widget_name, icon, self, type="SubPatch")
                        self.results_layout.addWidget(button, row, col)
                        col += 1
                        if col > 3:
                            col = 0
                            row += 1

            for widget_name in self.audio_widgets:
                if search_text in widget_name.lower():
                    icon = self.create_icon(widget_name, "audio")
                    button = WidgetButton(widget_name, icon, self, type="Audio")
                    self.results_layout.addWidget(button, row, col)
                    col += 1
                    if col > 3:
                        col = 0
                        row += 1

            for widget_name in self.audio_midi_widgets:
                if search_text in widget_name.lower():
                    icon = self.create_icon(widget_name, "audio_midi")
                    button = WidgetButton(widget_name, icon, self, type="AudioMIDI")
                    self.results_layout.addWidget(button, row, col)
                    col += 1
                    if col > 3:
                        col = 0
                        row += 1

            for widget_name in self.midi_widgets:
                if search_text in widget_name.lower():
                    icon = self.create_icon(widget_name, "midi")
                    button = WidgetButton(widget_name, icon, self, type="MIDI")
                    self.results_layout.addWidget(button, row, col)
                    col += 1
                    if col > 3:
                        col = 0
                        row += 1


class Patch(QWidget):
    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent=parent)
        self.setObjectName("patch")
        # Global Access
        self.parent = parent
        self.main_window = self.parent
        self.context = self.parent.context
        self.audiostatus = self.parent.audiostatus
        self.group = 0
        self.meter_enabled = True
        self.name = "main"
        # PatchBuffers
        self.patch_buffers = PatchBuffers(server=scsynth, patch=self)
        # PatchArea
        self.patch_area = PatchArea(patch=self, context=self.parent.context)
        self.widgets = load_widgets_list("./")
        self.reinit_state = None
        # Load Class Names
        self.audio_widgets_names = [key for kind in self.widgets["audio"].keys() for key in self.widgets["audio"][kind]]
        self.midi_widgets_names = [cls.__name__ for cls in MIDIWidget.__subclasses__()]
        self.audio_midi_widgets_names = [key for kind in self.widgets["audio_midi"].keys() for key in self.widgets["audio_midi"][kind]] + [cls.__name__ for cls in AudioMIDIWidget.__subclasses__()]
        print(self.audio_midi_widgets_names)
        self.audio_widgets = []
        self.midi_widgets = []
        self.audio_midi_widgets = []
        self.subpatch_widgets = []
        self.subpatches = {}
        # WORKSPACE PER WIDGET
        self.patch_scroll = QScrollArea()
        self.patch_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.patch_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.patch_scroll.setWidget(self.patch_area)
        self.lay = QVBoxLayout()
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(0)
        # WIDGET TOOLBAR
        # self.lay.addWidget(self.tool_bar)
        self.lay.addWidget(self.patch_scroll)
        self.setLayout(self.lay)

    def getGroup(self):
        return self.group

    def update_subpatches(self):
        self.subpatches = {key.split(":")[1]: val for key, val in self.main_window.patches.items() if key != "0:main"}
        print(f"self.subpatches is {self.subpatches}")

    def update_subpatch_instances(self):
        print("Calling update_subpatch_instances on patch 0:main")
        for subpatch_widget in self.subpatch_widgets:
            subpatch_widget.initArgs()
            subpatch_widget.reinitUI()

    def set_meter_enable(self, enabled: bool):
        self.meter_enabled = enabled

    def draw_widget_pngs(self):
        # Audio Widgets
        if not os.path.exists("./graphic_files/widgets/audio/"):
            os.makedirs("./graphic_files/widgets/audio/")
        for kind in self.widgets["audio"].keys():
            if not os.path.exists(f"./graphic_files/widgets/audio/{kind}/"):
                os.makedirs(f"./graphic_files/widgets/audio/{kind}/")
            for class_name in self.widgets["audio"][kind].keys():
                instance = AudioWidget(server=scsynth, parent=self.patch_area, synth_name=self.widgets["audio"][kind][class_name]["synth_name"], n_in=self.widgets["audio"][kind][class_name]["n_in"], n_out=self.widgets["audio"][kind][class_name]["n_out"], synth_args=self.widgets["audio"][kind][class_name]["args"], name=class_name)
                pixmap = instance.grab()
                img = pixmap.toImage()
                img.save(f"./graphic_files/widgets/audio/{kind}/{class_name}.png")
        # MIDI Widgets
        if not os.path.exists("./graphic_files/widgets/midi/"):
            os.makedirs("./graphic_files/widgets/midi/")
        for class_name in self.midi_widgets_names:
            instance = globals()[class_name](server=self.context.server, parent=self.patch_area, clock=self.patch_area.patch.main_window.clock, harmony_manager=self.context.harmony_manager)
            pixmap = instance.grab()
            img = pixmap.toImage()
            img.save(f"./graphic_files/widgets/midi/{class_name}.png")
        # Audio/MIDI Widgets
        if not os.path.exists("./graphic_files/widgets/audio_midi/"):
            os.makedirs("./graphic_files/widgets/audio_midi/")
        if not os.path.exists(f"./graphic_files/widgets/audio_midi/Custom/"):
            os.makedirs(f"./graphic_files/widgets/audio_midi/Custom/")
        for kind in self.widgets["audio_midi"].keys():
            if not os.path.exists(f"./graphic_files/widgets/audio_midi/{kind}/"):
                os.makedirs(f"./graphic_files/widgets/audio_midi/{kind}/")
            for class_name in self.widgets["audio_midi"][kind].keys():
                instance = AudioMIDIWidget(server=scsynth, clock=self.patch_area.patch.main_window.clock, harmony_manager=self.context.harmony_manager, parent=self.patch_area, synth_name=self.widgets["audio_midi"][kind][class_name]["synth_name"], n_audio_in=self.widgets["audio_midi"][kind][class_name]["n_audio_in"], n_audio_out=self.widgets["audio_midi"][kind][class_name]["n_audio_out"], n_midi_in=self.widgets["audio_midi"][kind][class_name]["n_midi_in"], n_midi_out=self.widgets["audio_midi"][kind][class_name]["n_midi_out"], synth_args=self.widgets["audio_midi"][kind][class_name]["args"])
                pixmap = instance.grab()
                img = pixmap.toImage()
                img.save(f"./graphic_files/widgets/audio_midi/{kind}/{class_name}.png")
        for class_name in [cls.__name__ for cls in AudioMIDIWidget.__subclasses__()]:
            instance = eval(class_name)(server=scsynth, clock=self.patch_area.patch.main_window.clock, harmony_manager=self.context.harmony_manager, parent=self.patch_area)
            pixmap = instance.grab()
            img = pixmap.toImage()
            img.save(f"./graphic_files/widgets/audio_midi/Custom/{class_name}.png")

    def create_icon(self, path):
        # Crea un'icona ridimensionata a 50x50px
        pixmap = QPixmap(path).scaled(50, 50)
        icon = QIcon(pixmap)
        return icon

    def get_undo_stack(self):
        return self.main_window.get_undo_stack()

    def set_context(self, context):
        self.context = context

    def set_main_window(self, win):
        self.main_window = win

    def flushPatch(self):
        for widget in self.audio_widgets:
            self.remove_audio_widget(widget)

    def propagateCableMouseClick(self, event, subtractGlobalPos=False):
        for audio_widget in self.audio_widgets:
            audio_widget.mouseCablePressEvent(event, subtractGlobalPos)
        for midi_widget in self.audio_widgets:
            midi_widget.mouseCablePressEvent(event, subtractGlobalPos)

    def reset_widgets(self):
        for widget in self.audio_widgets:
            widget.resetSynthArgs()

    def redraw_audio_widgets(self):
        for widget in self.audio_widgets:
            widget.initUI()

    def add_sub_patch_widget(self):
        # TODO: implement add_sub_patch_widget method
        class_name = self.sender().text()
        subpatch_instance_name = [key for key in self.main_window.patches.keys() if key.split(":")[1] == class_name]
        subpatch_instance = self.main_window.patches[subpatch_instance_name[0]]
        instance = SubPatchInstanceWidget(server=scsynth, parent=self.patch_area, subpatch=subpatch_instance, target_patch=self)
        instance.setGeometry(20, 20, instance.width(), instance.height())
        instance.show()
        self.subpatch_widgets.append(instance)
        subpatch_instance.create_instance_graph(instance)
        self.parent.timeline.populate_widgets()

    def remove_sub_patch_widget(self, widget):
        # TODO: implement remove_sub_patch_widget method
        widget.subpatch.delete_instance_graph(widget)
        self.subpatch_widgets.remove(widget)
        widget.hide()
        del widget
        self.parent.timeline.populate_widgets()

    def add_audio_widget(self):
        class_name = self.sender().text()
        class_kind = ""
        for kind in self.widgets["audio"].keys():
            if class_name in self.widgets["audio"][kind].keys():
                class_kind = kind
        data = self.widgets["audio"][class_kind][class_name]
        instance = AudioWidget(server=scsynth, parent=self.patch_area, synth_name=data["synth_name"], n_in=data["n_in"], n_out=data["n_out"], synth_args=data["args"], name=class_name)
        instance.setGeometry(20, 20, instance.width(), instance.height())
        instance.show()
        self.audio_widgets.append(instance)
        self.parent.timeline.populate_widgets()

    def remove_audio_widget(self, widget):
        for _ in range(widget.n_in + widget.n_out):
            for cable in self.patch_area.audio_cables:
                if cable.widget_in.getUUID() == widget.getUUID() or cable.widget_out.getUUID() == widget.getUUID():
                    cable.disconnectWidgets()
                    self.patch_area.audio_cables.remove(cable)
                    cable.hide()
                    del cable
            for cable in self.patch_area.midi_cables:
                if cable.widget_in == widget or cable.widget_out == widget:
                    cable.disconnectWidgets()
                    self.patch_area.midi_cables.remove(cable)
                    cable.hide()
                    del cable
        widget.freeSynth()
        self.audio_widgets.remove(widget)
        widget.hide()
        del widget
        self.parent.timeline.populate_widgets()

    def add_midi_widget(self):
        class_name = self.sender().text()
        class_ = eval(class_name)
        instance = class_(server=scsynth, clock=self.main_window.clock, harmony_manager=self.context.harmony_manager, parent=self.patch_area)
        instance.setGeometry(20, 20, instance.width(), instance.height())
        instance.show()
        self.midi_widgets.append(instance)
        self.parent.timeline.populate_widgets()

    def add_midi_widget_from_name(self, class_name):
        class_ = eval(class_name)
        instance = class_(server=scsynth, clock=self.main_window.clock, harmony_manager=self.context.harmony_manager, parent=self.patch_area)
        instance.setGeometry(20, 20, instance.width(), instance.height())
        instance.show()
        self.midi_widgets.append(instance)
        self.parent.timeline.populate_widgets()

    def remove_midi_widget(self, widget):
        self.midi_widgets.remove(widget)
        widget.hide()
        del widget
        self.parent.timeline.populate_widgets()

    def add_audio_midi_widget(self):
        class_name = self.sender().text()
        class_kind = ""
        for kind in self.widgets["audio_midi"].keys():
            if class_name in self.widgets["audio_midi"][kind].keys():
                class_kind = kind
        data = self.widgets["audio_midi"][class_kind][class_name]
        instance = AudioMIDIWidget(server=scsynth, clock=self.main_window.clock, harmony_manager=self.context.harmony_manager, parent=self.patch_area, synth_name=data["synth_name"], n_audio_in=data["n_audio_in"], n_audio_out=data["n_audio_out"], n_midi_in=data["n_midi_in"], n_midi_out=data["n_midi_out"], synth_args=data["args"])
        instance.setGeometry(20, 20, instance.width(), instance.height())
        instance.show()
        self.audio_midi_widgets.append(instance)
        self.parent.timeline.populate_widgets()

    def add_custom_audio_midi_widget(self):
        class_name = self.sender().text()
        class_ = eval(class_name)
        instance = class_(server=scsynth, clock=self.main_window.clock, harmony_manager=self.context.harmony_manager, parent=self.patch_area)
        instance.setGeometry(20, 20, instance.width(), instance.height())
        instance.show()
        self.audio_midi_widgets.append(instance)
        self.parent.timeline.populate_widgets()

    def remove_audio_midi_widget(self, widget):
        widget.freeSynth()
        self.audio_midi_widgets.remove(widget)
        widget.hide()
        del widget
        self.parent.timeline.populate_widgets()

    def start_add_audio_cable(self, audio_widget):
        pass

    def reload_patch(self):
        with open("tmp.p", "wb") as f:
            f.write(pickle.dumps(self, protocol=pickle.HIGHEST_PROTOCOL))
        with open("tmp.p", "rb") as f:
            self.context.server.freeAllNodes()
            data = f.read()
            _ = pickle.loads(data)
        time.sleep(1)
        self.patch_area.repatch_audio()

    def __getstate__(self):
        d = {
            "audio_widgets": [cls.__class__.__name__ for cls in self.audio_widgets],
            "audio_widgets_states": [cls.__getstate__() for cls in self.audio_widgets],
            "subpatch_widgets": [cls.__class__.__name__ for cls in self.subpatch_widgets],
            "subpatch_widgets_states": [cls.__getstate__() for cls in self.subpatch_widgets],
            "midi_widgets": [cls.__class__.__name__ for cls in self.midi_widgets],
            "midi_widgets_states": [cls.__getstate__() for cls in self.midi_widgets],
            "audio_midi_widgets": [cls.__class__.__name__ for cls in self.audio_midi_widgets],
            "audio_midi_widgets_states": [cls.__getstate__() for cls in self.audio_midi_widgets],
            "patch_buffers": self.patch_buffers.__getstate__(),
            "patch_area": self.patch_area.__getstate__()
        }
        return d

    def __setstate__(self, state):
        super(Patch, self).__init__()
        self.__init__(win)  # TODO: CONTROLLARE BENE QUESTA RIGA!!!!!!!!!
        print("Qui win è:", win)
        self.reinit_state = state
        # self.reinit()

    def reinit(self):
        if self.reinit_state is not None:
            state = self.reinit_state
            # Prima ricreo i PatchBuffers
            self.patch_buffers = PatchBuffers(server=scsynth, patch=self)
            self.patch_buffers.__setstate__(state["patch_buffers"])
            # Poi ricreo i Widget Audio
            self.audio_widgets = []
            self.flushPatch()
            for index, cls in enumerate(state['audio_widgets']):
                data = state["audio_widgets_states"][index]
                name = ""
                if "name" in list(data.keys()):
                    name = data["name"]
                instance = AudioWidget(server=self.context.server, parent=self.patch_area, uuid=data["uuid"],
                                       n_in=data["n_in"], n_out=data["n_out"], synth_name=data["synth_name"],
                                       synth_args=data["Settings"]["Parameters"], name=name)
                instance.__setstate__(data)
                print(f"Adding Patch AudioWidget: {data}")
                self.audio_widgets.append(instance)

            # Poi ricreo i Widget MIDI
            for index, cls in enumerate(state['midi_widgets']):
                if cls == "MIDIWidget":
                    data = state["midi_widgets_states"][index]
                    instance = MIDIWidget(server=self.context.server, parent=self.patch_area, clock=self.main_window.clock,
                                          harmony_manager=self.context.harmony_manager, uuid=data["uuid"],
                                          n_midi_in=data["n_midi_in"], n_midi_out=data["n_midi_out"])
                    instance.__setstate__(state["midi_widgets_states"][index])
                    self.midi_widgets.append(instance)
                else:
                    data = state["midi_widgets_states"][index]
                    print("cls:", cls, type(cls))
                    print("data:", data)
                    instance = globals()[cls](server=self.context.server, parent=self.patch_area, clock=self.main_window.clock,
                                          harmony_manager=self.context.harmony_manager, uuid=data["uuid"],
                                          n_midi_in=data["n_midi_in"], n_midi_out=data["n_midi_out"])
                    instance.__setstate__(state["midi_widgets_states"][index])
                    self.midi_widgets.append(instance)

            # Poi ricreo i Widget AudioMIDI
            for index, cls in enumerate(state['audio_midi_widgets']):
                if cls == "AudioMIDIWidget":
                    data = state["audio_midi_widgets_states"][index]
                    instance = AudioMIDIWidget(server=self.context.server, clock=self.main_window.clock,
                                          harmony_manager=self.context.harmony_manager, parent=self.patch_area, uuid=data["uuid"],
                                               n_audio_in=data["n_audio_in"], n_audio_out=data["n_audio_out"],
                                               n_midi_in=data["n_midi_in"], n_midi_out=data["n_midi_out"],
                                               synth_name=data["synth_name"], synth_args=data["Settings"]["Parameters"])
                    instance.__setstate__(state["audio_midi_widgets_states"][index])
                    self.audio_midi_widgets.append(instance)
                else:
                    data = state["audio_midi_widgets_states"][index]
                    instance = globals()[cls](server=self.context.server, clock=self.main_window.clock,
                                          harmony_manager=self.context.harmony_manager, parent=self.patch_area, uuid=data["uuid"],
                                               n_audio_in=data["n_audio_in"], n_audio_out=data["n_audio_out"],
                                               n_midi_in=data["n_midi_in"], n_midi_out=data["n_midi_out"],
                                               synth_name=data["synth_name"], synth_args=data["Settings"]["Parameters"])
                    instance.__setstate__(state["audio_midi_widgets_states"][index])
                    self.audio_midi_widgets.append(instance)

            # Poi ricreo i Widget SubPatchInstance
            if 'subpatch_widgets' in state.keys():
                for index, cls in enumerate(state['subpatch_widgets']):
                    data = state["subpatch_widgets_states"][index]
                    correct_subpatch_name = [key for key in self.main_window.patches.keys() if data["subpatch_name"] in key][0]
                    c_print("cyan", f"SUBPATCH INSTANCE STORED Data is {data}")
                    instance = SubPatchInstanceWidget(server=self.context.server, parent=self.patch_area, uuid=data["uuid"],
                                                      subpatch=self.main_window.patches[correct_subpatch_name], target_patch=self)  # , target_patch=data["target_patch"]
                    data["target_patch"] = self
                    data["subpatch"] = self.main_window.patches[correct_subpatch_name]
                    instance.__setstate__(data)
                    self.subpatch_widgets.append(instance)
                    # self.main_window.patches[correct_subpatch_name].create_instance_graph(instance)
                    c_print("green", f"setting instance graph state for SubPatchInstanceWidget: {correct_subpatch_name}")
                    self.main_window.patches[correct_subpatch_name].set_instance_graph_state(data["subpatch_instance_data"], instance)
                    c_print("green", f"instance graphs keys: {self.main_window.patches[correct_subpatch_name].instance_graphs.keys()}")
                    for wid in self.main_window.patches[correct_subpatch_name].instance_graphs[str(instance.getUUID())]["SubPatch"].audio_widgets:
                        c_print("cyan", f"SubPatch Instance widget state: {wid.__getstate__()}")
                    instance.calcInletOutletPos()

            # Poi ricreo il Patch
            self.patch_area.__setstate__(state["patch_area"])
            self.reset_widgets()
            # print("Opening patch (PATCH): audio widgets:", self)
            # print("\taudio_widgets:", self.audio_widgets)
            # Quindi aggiorno il RegionManager
            self.main_window.region_manager.refresh_regions()
            scsynth.dumpNodeTree()


class Context(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.app = app
        self.midi_manager = classes.MIDIManager(self)
        # self.midi_manager.refreshDevices()
        self.tempo = 120
        self.server = scsynth
        scsynth.start()
        self.lay = QVBoxLayout()
        # self.clock = TempoClock(main_window=parent, bpm=self.tempo)
        self.harmony_manager = HarmonyManager()
        # self.lay.addWidget(self.clock)
        self.lay.addWidget(self.harmony_manager)
        self.setLayout(self.lay)

    def set_region_manager(self, rm):
        self.midi_manager.set_region_manager(rm)

    def set_region_line(self, rl):
        self.midi_manager.set_region_line(rl)

    def refresh_midi_devices(self):
        self.midi_manager.refreshDevices()

    def __getstate__(self):
        pass

    def __setstate__(self, state):
        pass


class AudioStatus(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent=parent)
        self.app = app
        self.parent = parent
        self.server = scsynth
        self.lay = QVBoxLayout()
        self.nodeOrderWidget = QTableWidget()
        self.nodeOrderWidget.setColumnCount(1)
        self.nodeOrderWidget.setColumnWidth(0, 200)
        self.nodeOrderWidget.itemClicked.connect(self.select_func)
        self.lay.addWidget(self.nodeOrderWidget)
        self.setLayout(self.lay)
        self.node_order = []

    def select_func(self, item):
        id = item.row()
        node = self.node_order[id]
        for audio_widget in self.parent.patch.audio_widgets:
            if node[0] == audio_widget.getUUID():
                audio_widget.setSelected(True)
            else:
                audio_widget.setSelected(False)
        print("Widget", id, "selected!")

    def populate(self):
        # Clear rows
        for index in reversed(range(self.nodeOrderWidget.rowCount())):
            self.nodeOrderWidget.removeRow(index)
        self.nodeOrderWidget.setRowCount(0)
        # Query current scsynth's node order and reconstruct widgets
        self.node_order = self.server.get_node_order()
        self.nodeOrderWidget.setRowCount(len(self.node_order))
        for index, node in enumerate(self.node_order):
            uuid = node[0]
            class_str = node[1]
            text = class_str  # + " (" + str(uuid) + ")"
            wid = QTableWidgetItem()
            wid.setText(text)
            self.nodeOrderWidget.setItem(index, 0, wid)

    def __getstate__(self):
        pass

    def __setstate__(self, state):
        pass


class MainWindow(QMainWindow):
    def __init__(self, app):
        super(MainWindow, self).__init__()
        self.setMouseTracking(True)
        self.setWindowTitle("Sound Designer - ©2024, Francesco Roberto Dani")
        self.setGeometry(0, 0, 800, 400)
        self.app = app
        # STYLING & COLORS
        with open(STYLESHEET_PATH, "r") as style:  # "./style.stylesheet"
            style = style.read()
            # Text
            style = style.replace("font-size-small", "8px")
            style = style.replace("font-size-medium", "10px")
            style = style.replace("font-size-large", "12px")
            style = style.replace("font-size-Large", "14px")
            style = style.replace("font-type", "Arial")
            style = style.replace("widget-param-height", "15px")
            # Audio / MIDI / AudioMIDI - Widget
            style = style.replace("audio-widget-background", _6color_palette_02)
            style = style.replace("audio-widget-border", _6color_palette_01)
            style = style.replace("midi-widget-background", _6color_palette_04)
            style = style.replace("midi-widget-border", _6color_palette_06)
            # PatchArea
            style = style.replace("patch-area-background", _6color_palette_03)
            # Application Background
            style = style.replace("app-background", _6color_palette_04)
            # TabWidget
            style = style.replace("tab-widget-height", "20px")
            style = style.replace("tab-widget-color", "rgba(0, 0, 0, 0)")
            style = style.replace("tab-widget-tab-color", "rgba(0, 0, 0, 0)")
            style = style.replace("tab-widget-tab-selected-color", "rgba(0, 0, 0, 0)")
            # ToolBar & QMenu
            style = style.replace("menu-widget-color", _6color_palette_03)
            style = style.replace("menu-widget-item-color", _6color_palette_03)
            style = style.replace("menu-widget-item-selected-color", _6color_palette_04)
            # Curves & Envelopes
            style = style.replace("curvexy-background-color", _6color_palette_02)
            style = style.replace("envelope-background-color", _6color_palette_01)

            self.app.setStyleSheet(style)

        # Global QUndoStack
        self.undoStack = QUndoStack(self)

        # Main Menu
        loadPatchAct = QAction('&Open Patch', self)
        loadPatchAct.setShortcut('Ctrl+O')
        loadPatchAct.setStatusTip('Open Patch')
        loadPatchAct.triggered.connect(self.load_patch)

        savePatchAct = QAction('&Save Patch', self)
        savePatchAct.setShortcut('Ctrl+S')
        savePatchAct.setStatusTip('Save Patch')
        savePatchAct.triggered.connect(self.save_patch)

        sAct = QAction("&Settings", self)
        sAct.setShortcut("Ctrl+E")
        sAct.setStatusTip('Show Settings')
        sAct.triggered.connect(self.open_settings)

        escAct = QAction("&Abort Cable", self)
        escAct.setShortcut(Qt.Key.Key_Escape)
        escAct.setStatusTip('Abort Placing Cable')
        escAct.triggered.connect(self.escape_pressed)

        openGestureCreatorAct = QAction('&Gesture Creator', self)
        openGestureCreatorAct.setShortcut('Ctrl+G')
        openGestureCreatorAct.setStatusTip('Open Gesture Creator Window')
        openGestureCreatorAct.triggered.connect(self.open_gesture_creator)

        undoAct = QAction('&Undo', self)
        undoAct.setShortcut('Ctrl+Z')
        undoAct.triggered.connect(self.undoStack.undo)

        redoAct = QAction('&Redo', self)
        redoAct.setShortcut('Ctrl+Shift+Z')
        redoAct.triggered.connect(self.undoStack.redo)

        addWidgetAct = QAction('&Add Widget', self)
        addWidgetAct.setShortcut('Ctrl+A')
        addWidgetAct.triggered.connect(self.addWidget)

        newSubPatchAct = QAction('&Create New SubPatch', self)
        newSubPatchAct.setShortcut('Ctrl+Shift+P')
        newSubPatchAct.setStatusTip('Create New SubPatch')
        newSubPatchAct.triggered.connect(self.create_new_subpatch)

        deleteSubPatchAct = QAction('&Delete SubPatch', self)
        deleteSubPatchAct.setShortcut('Ctrl+Shift+D')
        deleteSubPatchAct.setStatusTip('Delete SubPatch')
        deleteSubPatchAct.triggered.connect(self.delete_subpatch)

        # self.statusBar()
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(loadPatchAct)
        fileMenu.addAction(savePatchAct)
        fileMenu.addAction(sAct)
        fileMenu.addAction(openGestureCreatorAct)
        fileMenu.addAction(undoAct)
        fileMenu.addAction(redoAct)
        fileMenu.addAction(escAct)
        fileMenu.addAction(addWidgetAct)
        fileMenu.addAction(newSubPatchAct)
        fileMenu.addAction(deleteSubPatchAct)

        # Main Widget & Layout
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)

        # Creating default AudioStatus widget
        self.audiostatus = AudioStatus(app=self.app, parent=self)
        # Whole screen Patch + Settings on the Left when needed
        self.patch_layout = QHBoxLayout()
        self.patch_layout.setSpacing(0)
        self.patch_layout.setContentsMargins(0, 0, 0, 0)
        # Creating default Context widget
        self.context = Context(app=self.app, parent=self)

        # Creating default Patch widget
        self.patch = Patch(parent=self)
        # Sub-Patch Management
        self.patches_btns_layout = QVBoxLayout()
        self.patches_btns_layout.setSpacing(0)
        self.patches_btns_layout.setContentsMargins(0, 0, 0, 0)
        self.patches = {"0:main": self.patch}
        self.patch_layout.addLayout(self.patches_btns_layout)
        # Stacked Layout for Patch and SubPatches
        self.patch_stack_layout = QStackedLayout()
        self.patch_stack_layout.setSpacing(0)
        self.patch_stack_layout.setContentsMargins(0, 0, 0, 0)
        self.patch_stack_layout.addWidget(self.patch)
        self.patch_layout.addLayout(self.patch_stack_layout)
        # self.patch_layout.addWidget(self.patch)
        self.patch_widget = QWidget()
        self.patch_widget.setLayout(self.patch_layout)

        # Creating Widget Settings Side Bar
        self.settings_bar = WidgetSettingsSideBar(parent=None, context=self.context, audiostatus=self.audiostatus)
        self.patch_layout.addWidget(self.settings_bar)

        # Creating default TimeLine widget
        self.timeline = TimeLine(parent=self)
        self.timeline.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.timeline_layout = QVBoxLayout()
        self.timeline_layout.setSpacing(0)
        self.timeline_layout.setContentsMargins(0, 0, 0, 0)
        self.timeline_widget = QWidget()
        self.timeline_widget.setLayout(self.timeline_layout)
        self.timeline_layout.addWidget(self.timeline)

        # Creating default TempoClock widget
        self.clock = TempoClock(self, self, 120)
        self.clock.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.clock.setMaximumHeight(40)
        self.timeline.setClock(self.clock)
        self.clock_lay = QHBoxLayout()
        self.clock_lay.setSpacing(0)
        self.clock_lay.setContentsMargins(0, 0, 0, 0)
        self.clock_lay.addWidget(self.clock)

        # Create default Region Manager
        self.region_manager = RegionManager(self)
        self.region_manager.setMaximumHeight(80)
        self.context.set_region_manager(self.region_manager)
        self.context.set_region_line(self.timeline.region_line)
        self.context.refresh_midi_devices()
        self.timeline.setRegionManager(self.region_manager)
        self.region_manager_lay = QHBoxLayout()
        self.region_manager_lay.setSpacing(0)
        self.region_manager_lay.setContentsMargins(0, 0, 0, 0)
        self.region_manager_lay.addWidget(self.region_manager)
        self.main_layout.addLayout(self.region_manager_lay)

        # Tab Widget for switching between Patch and TimeLine
        self.patch_timeline_tab = QTabWidget()
        self.patch_timeline_tab.setIconSize(QSize(icon_size, icon_size))
        self.patch_timeline_tab.setTabPosition(QTabWidget.TabPosition.South)
        self.patch_timeline_tab.addTab(self.patch_widget, QIcon(os.path.join(GRAPHICS_PATH, "ButtonPatch.svg")), "")
        self.patch_timeline_tab.addTab(self.timeline_widget, QIcon(os.path.join(GRAPHICS_PATH, "ButtonTimeline.svg")), "")

        self.main_layout.addWidget(self.patch_timeline_tab)
        self.main_layout.addLayout(self.clock_lay)
        # self.patch.draw_widget_pngs()
        # self.addSubPatch(name="SPT")

    def getCurrentPatch(self):
        curr_id = str(self.patch_stack_layout.currentIndex()) + ":"
        for key in self.patches.keys():
            if curr_id in key:
                return self.patches[key]
        return None

    def addSubPatch(self, name="SubPatchTest"):
        subpatch = SubPatch(self, name=name)
        next_id = max([int(key.split(":")[0]) for key in self.patches.keys()]) + 1
        sp_key = str(next_id) + ":" + name
        self.patches[sp_key] = subpatch
        self.patch_stack_layout.addWidget(subpatch)
        self.refreshSubPatchButtons()
        self.patch.update_subpatches()

    def removeSubPatch(self, name="SubPatchTest"):
        self.patch_stack_layout.removeWidget(self.patches[name])
        sip.delete(self.patches[name])
        self.refreshSubPatchButtons()
        self.patch.update_subpatches()

    def create_new_subpatch(self):
        print("Creating new SubPatch...")
        item, ok = QInputDialog.getText(self, "Create New SubPatch", "Enter SubPatch Name")
        if ok and len(item) > 0:
            print(f"\tName: {item}")
            self.addSubPatch(name=item)
        else:
            print(f"\tAborting...")
        pass

    def delete_subpatch(self):
        print("Deleting SubPatch...")
        subpatch_names = [key.split(":")[1] for key in self.patches.keys() if key != "0:main"]
        subpatch_indexes = [key.split(":")[0] for key in self.patches.keys() if key != "0:main"]
        print(f"subpatch_names: {subpatch_names}")
        item, ok = QInputDialog.getItem(self, "Create New SubPatch", "Select SubPatch", subpatch_names, 0, False)
        if ok and len(item) > 0:
            item = str(subpatch_indexes[subpatch_names.index(item)]) + ":" + item
            print(f"\tName: {item}")
            subpatch_to_delete = self.patches[item]
            self.patches[item] = None
            self.patches.pop(item, None)
            sip.delete(subpatch_to_delete)

            self.patch.update_subpatches()
            self.refreshSubPatchButtons()
        else:
            print(f"\tAborting...")

    def closeEvent(self, event):
        # Sovrascrivi il metodo closeEvent per prevenire la chiusura della finestra con Ctrl+Q
        print("Tentativo di chiudere la finestra")
        scsynth.quit()

    def refreshSubPatchButtons(self):
        while self.patches_btns_layout.count() > 0:
            # self.patches_btns_layout.itemAt(0).widget().deleteLater()
            wid = self.patches_btns_layout.itemAt(0).widget()
            self.patches_btns_layout.removeItem(self.patches_btns_layout.itemAt(0))
            wid.deleteLater()
        sorted_keys = list(self.patches.keys())
        sorted_keys.sort(key=lambda x: x.split(":")[0])
        print("Sorted SubPatch keys:", sorted_keys)
        for skey in sorted_keys:
            print("Adding subpatch:", skey)
            btn = QPushButton(skey.split(":")[1])
            btn.setFixedWidth(60)
            btn.clicked.connect(lambda v, i=int(skey.split(":")[0]): self.showSubPatch(i))
            self.patches_btns_layout.addWidget(btn)

    def showSubPatch(self, index):
        print("SubPatch Index:", index, [self.patches_btns_layout.itemAt(id) for id in range(self.patches_btns_layout.count())])
        self.patch_stack_layout.setCurrentIndex(index)

    def addWidget(self):
        dialog = WidgetSearchDialog(self.patch.audio_widgets_names, self.patch.midi_widgets_names, self.patch.audio_midi_widgets_names, self)
        dialog.exec()

    def get_undo_stack(self):
        return self.undoStack

    def save_patch(self):
        filename = QFileDialog.getSaveFileName(None, directory="/Users/francescodani/Documents/SoundDesigner/SoundDesigner/src/patches/", filter="Patch (*.p)")
        if filename[0] != "":
            with open(filename[0], "wb") as f:
                f.write(pickle.dumps([self.patch, self.timeline]))
                f.write(b"---")
                f.write(pickle.dumps([key for key in self.patches.keys() if key != "0:main"]))
                f.write(b"---")
                f.write(pickle.dumps([self.patches[key] for key in self.patches.keys() if key != "0:main"]))

    def load_patch(self):
        for audio_widget in self.patch.audio_widgets:
            if audio_widget.synth is not None:
                audio_widget.synth.free()
        filename = QFileDialog.getOpenFileName(None, directory="/Users/francescodani/Documents/SoundDesigner/SoundDesigner/src/patches/", filter="Patch (*.p)")
        if os.path.exists(filename[0]):
            with open(filename[0], "rb") as f:
                self.main_layout.removeWidget(self.patch)
                self.timeline_layout.removeWidget(self.timeline)
                self.patch.setParent(None)
                self.timeline.setParent(None)

                while self.patch_layout.count() > 0:
                    self.patch_layout.removeItem(self.patch_layout.itemAt(0))
                while self.patches_btns_layout.count() > 0:
                    wid = self.patches_btns_layout.itemAt(0).widget()
                    self.patches_btns_layout.removeItem(self.patches_btns_layout.itemAt(0))
                    wid.deleteLater()
                self.patch_layout.addLayout(self.patches_btns_layout)

                data = f.read()
                data_split = data.split(b"---")
                patch_timeline_data = data_split[0]
                patch_timeline_data = pickle.loads(patch_timeline_data)
                del self.patch
                del self.timeline
                self.patch = patch_timeline_data[0]
                self.patches = {"0:main": self.patch}
                if len(data_split) > 1:
                    subatch_names = pickle.loads(data_split[1])
                    subpatches_data = pickle.loads(data_split[2])
                else:
                    subatch_names = []
                    subpatches_data = []
                print(f"patch_timeline_data: {patch_timeline_data}; subatch_names:{subatch_names}; subpatches_data: {subpatches_data}")
                for subpatch_index, subpatch_name in enumerate(subatch_names):
                    c_print("green", f"SubPatch Saved Data: {subpatches_data[subpatch_index]}")
                    self.patches[subpatch_name] = subpatches_data[subpatch_index]
                self.patch.reinit()

                self.patch.set_main_window(self)
                for key in self.patches.keys():
                    if key != "0:main":
                        self.patches[key].set_main_window(self)
                # self.timeline = data[1]
                self.timeline = patch_timeline_data[1]
                self.timeline.reset_parent(self)

                # Stacked Layout for Patch and SubPatches
                self.patch_stack_layout = QStackedLayout()
                self.patch_stack_layout.addWidget(self.patch)
                for subpatch_index, subpatch_name in enumerate(subatch_names):
                    self.patch_stack_layout.addWidget(self.patches[subpatch_name])
                    self.refreshSubPatchButtons()
                    self.patch.update_subpatches()
                self.patch_layout.addLayout(self.patch_stack_layout)

                self.patch_layout.addWidget(self.settings_bar)

                self.patch_widget.setLayout(self.patch_layout)
                self.refreshSubPatchButtons()

                self.timeline_layout.insertWidget(0, self.timeline)
                self.timeline.setClock(self.clock)

                self.clock.reloadParents(self)
                self.region_manager.reloadParents(self)
                self.region_manager.refresh_regions()
                self.context.set_region_manager(self.region_manager)
                self.context.set_region_line(self.timeline.region_line)
                self.context.refresh_midi_devices()
                print("Numb of items:", self.patch_layout.count(), self.patches)

    def open_settings(self):
        settings = Settings(self)
        settings.exec()

    def open_gesture_creator(self):
        creator = GestureCreator(self)
        creator.exec()

    def escape_pressed(self):
        # print("Escape Button Pressed!")
        for key in self.patches.keys():
            patch = self.patches[key]
            if patch.patch_area.is_placing_cable():
                patch.patch_area.flush_current_cable()


class WidgetSettings(QWidget):
    def __init__(self, parent, widget):
        super(WidgetSettings, self).__init__(parent)
        self.parent = parent
        self.widget = widget
        print("Widget Settings:", self.widget.getSettings())
        self.settings = deepcopy(self.widget.getSettings())
        # self.settings = self.widget.getSettings()
        print("Widget UUID:", self.widget.getUUID(), self.settings)
        self.settings_widgets = {}
        self.lay = QVBoxLayout()
        self.main_layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        self.lay.addWidget(QLabel(str(self.widget.getUUID())))

        for key in self.settings.keys():
            self.settings_widgets[key] = QWidget()
            lay = QVBoxLayout()
            self.main_layout.addWidget(QLabel(key))
            if (key != "Inputs") and (key != "Outputs"):  # Do this for Parameters and other EDITABLE things...
                for param_key in self.settings[key].keys():
                    param_val = self.settings[key][param_key]
                    lay2 = QHBoxLayout()
                    lay2.addWidget((QLabel(param_key)))
                    wid = QLineEdit()
                    wid.setMaximumWidth(100)
                    # int, float, or audio params validators
                    if type(param_val) is int:
                        valid = QIntValidator()
                        valid.setRange(param_val["min"], param_val["max"])
                        wid.setValidator(valid)
                    elif param_val["type"] is float:
                        valid = QDoubleValidator()
                        valid.setRange(param_val["min"], param_val["max"])
                        wid.setValidator(valid)
                    elif param_val["type"] == "audio":
                        if param_val["bus"] > 0:
                            wid.setReadOnly(True)
                            wid.setObjectName("widget-param-readonly")
                        else:
                            wid.setReadOnly(False)
                            wid.setObjectName("widget-param")
                    # trigger, or gate params (params which require a Button to test a trigger)
                    if param_val["type"] == "trigger":  # TODO
                        wid = QPushButton()
                        wid.setObjectName("widget-param")
                        wid.setText("Trigger")
                        wid.clicked.connect(lambda v, kk=key, k=param_key: self.trigger_param(v, kk, k))
                    elif param_val["type"] == "gate":  # TODO
                        wid = QPushButton()
                        wid.setObjectName("widget-param")
                        wid.setText("Gate")
                        wid.setCheckable(True)
                        wid.setChecked(False)
                        wid.clicked.connect(lambda v, kk=key, k=param_key: self.gate_param(v, kk, k))
                    elif param_val["type"] == "buffer":  # TODO
                        wid = QPushButton()
                        wid.setObjectName("widget-param")
                        wid.setText("Select Sound File")
                        wid.clicked.connect(lambda v, kk=key, k=param_key, w=wid: self.buffer_param(v, kk, k, w))
                    else:
                        wid.setText(str(param_val["val"]))
                        wid.setObjectName("widget-param")
                        wid.textChanged.connect(lambda v, kk=key, k=param_key: self.param_change(v, kk, k))
                    lay2.addWidget(wid)
                    lay.addLayout(lay2)
                self.settings_widgets[key].setLayout(lay)
                self.main_layout.addWidget(self.settings_widgets[key])
            else:  # Do this for Inputs and Outputs (NON EDITABLE!)
                for param_key in self.settings[key].keys():
                    param_val = self.settings[key][param_key]
                    lay2 = QHBoxLayout()
                    lay2.addWidget(QLabel(param_key))
                    lbl = QLabel(str(param_val))
                    lbl.setMaximumWidth(100)
                    lay2.addWidget(lbl)
                    lay.addLayout(lay2)
                self.settings_widgets[key].setLayout(lay)
                self.main_layout.addWidget(self.settings_widgets[key])
        self.lay.addLayout(self.main_layout)
        self.setLayout(self.lay)

    def update_settings(self):
        self.widget.setSettings(deepcopy(self.settings))
        # self.widget.setSettings(self.settings)

    def param_change(self, v, kk, k):
        self.settings[kk][k]["val"] = v
        self.update_settings()

    def trigger_param(self, v, kk, k):
        self.widget.synth.set(k, -1)
        time.sleep(5e-4)
        self.widget.synth.set(k, 1)
        # self.update_settings()

    def trigger_stop(self, v, kk, k):
        self.widget.synth.set(k, -1)

    def gate_param(self, v, kk, k):
        if self.settings[kk][k]["val"] == "True":
            self.settings[kk][k]["val"] = 1
        elif self.settings[kk][k]["val"] == "False":
            self.settings[kk][k]["val"] = 0
        self.settings[kk][k]["val"] = abs(int(self.settings[kk][k]["val"]) - 1)
        # self.update_settings()

    def buffer_param(self, v, kk, k, w):
        fname, _ = QFileDialog.getOpenFileName(self, "Open Audio File", "./", "Uncompressed Audio Files (*.wav *.aif *.aiff *.flac *.ogg)")
        if fname is not None:
            bufnum = scsynth.queryFreeBuffer()
            scsynth.allocBuffer(fname, bufnum)
            self.settings[kk][k]["val"][0] = bufnum
            self.settings[kk][k]["val"][1] = fname
            self.widget.synth.set(k, bufnum)
            w.setText(fname.split("/")[-1].split(".")[0])
            self.update_settings()


class WidgetSettingsSideBar(QTabWidget):
    def __init__(self, parent=None, context=None, audiostatus=None):
        super().__init__(parent)
        self.parent = parent
        self.setIconSize(QSize(icon_size, icon_size))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.context = context
        self.audiostatus = audiostatus
        self.current_widget = None
        self.setFixedWidth(20)
        self.setTabPosition(QTabWidget.TabPosition.West)
        settings_lbl = QLabel("Inspect a Widget\nby selecting it")
        self.settings_layout = QVBoxLayout()
        self.settings_layout.addWidget(settings_lbl)
        self.implode_tab_widget = QWidget()
        self.implode_tab_widget.setMaximumWidth(20)
        self.settings_widget = QWidget()
        self.settings_widget.setMinimumWidth(200)
        self.settings_widget.setLayout(self.settings_layout)
        self.addTab(self.implode_tab_widget, QIcon(os.path.join(GRAPHICS_PATH, "Arrow-double-down.svg")), "")
        self.addTab(self.settings_widget, QIcon(os.path.join(GRAPHICS_PATH, "Inspect.svg")), "")
        self.addTab(self.context, QIcon(os.path.join(GRAPHICS_PATH, "MIDI.svg")), "")
        self.addTab(self.audiostatus, QIcon(os.path.join(GRAPHICS_PATH, "Audio.svg")), "")
        self.currentChanged.connect(self.tabChanged)
        # TODO: make open/close animation work!
        self.animation = QPropertyAnimation(self, b"geometry")
        # self.animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.animation.setDuration(1000)
        # self.animate(False)

    def tabChanged(self, index):
        if self.widget(index) == self.implode_tab_widget:
            self.setFixedWidth(20)
            # self.animate(False)
        else:
            self.setFixedWidth(300)
            # self.animate(True)

    def animate(self, expand=True):
        if expand:
            self.animation.setStartValue(self.minimumSize())
            self.animation.setEndValue(self.maximumSize())
            # self.animation.setDirection(self.animation.Direction.Forward)
        else:
            self.animation.setStartValue(self.maximumSize())
            self.animation.setEndValue(self.minimumSize())
            # self.animation.setDirection(self.animation.Direction.Backward)
        self.animation.start()

    def delete_layout(self):
        for i in reversed(range(self.settings_layout.count())):
            self.settings_layout.itemAt(i).widget().setParent(None)

    def inspect_widget(self, widget):
        self.delete_layout()
        self.current_widget = widget
        self.show_widget_settings()

    def show_widget_settings(self):
        if self.current_widget is not None:
            settings_widget = WidgetSettings(parent=self, widget=self.current_widget)
        else:
            settings_widget = QLabel("Inspect a Widget\nby selecting it")
        # self.settings_layout.addWidget(settings_widget)
        self.settings_layout.insertWidget(0, settings_widget)

    def show_midi_settings(self):
        self.delete_layout()

    def show_general_settings(self):
        pass


"""
AudioWidgets
"""


class TempoClock(QWidget):
    def __init__(self, parent=None, main_window=None, bpm=120):
        super().__init__(parent)
        self.bpm = bpm
        self.main_window = main_window
        self.clock = classes.TempoClock(main_window=self.main_window, bpm=self.bpm)

        # set bpm
        self.bpm_spinbox = QDoubleSpinBox()
        self.bpm_spinbox.setRange(1, 500)
        self.bpm_spinbox.setSingleStep(0.1)
        self.bpm_spinbox.setValue(self.bpm)
        self.bpm_spinbox.valueChanged.connect(self.clock.setBPM)
        self.bpm_lay = QHBoxLayout()
        self.bpm_lay.setSpacing(0)
        self.bpm_lbl = QLabel("")
        self.bpm_pixmap = QPixmap(os.path.join(GRAPHICS_PATH, "Metronome.svg")).scaled(20, 20)
        self.bpm_lbl.setPixmap(self.bpm_pixmap)
        # self.bpm_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bpm_lay.addWidget(self.bpm_lbl)
        self.bpm_lay.addWidget(self.bpm_spinbox)
        # visualize clock
        self.clock_value = QLineEdit("0")
        self.clock_value.setMaximumWidth(30)
        self.clock_value.setObjectName("widget-param")
        self.clock_time = QLabel("00:00:00.000")
        self.clock_value.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.clock_value.textEdited.connect(self.goto)
        self.clock_lay = QHBoxLayout()
        self.clock_lay.setSpacing(0)
        self.clock_lbl = QLabel("")
        self.clock_pixmap = QPixmap(os.path.join(GRAPHICS_PATH, "Measure.svg")).scaled(20, 20)
        self.clock_lbl.setPixmap(self.clock_pixmap)
        # self.clock_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_lbl = QLabel("")
        self.time_pixmap = QPixmap(os.path.join(GRAPHICS_PATH, "Timer.svg")).scaled(20, 20)
        self.time_lbl.setPixmap(self.time_pixmap)
        self.time_lay = QHBoxLayout()
        self.time_lay.addWidget(self.time_lbl)
        self.time_lay.addWidget(self.clock_time)

        self.clock_lay.addWidget(self.clock_lbl)
        self.clock_lay.addWidget(self.clock_value)
        self.bpm_clock_lay = QHBoxLayout()
        self.bpm_clock_lay.setSpacing(0)

        self.bpm_clock_lay.addLayout(self.bpm_lay)
        self.bpm_clock_lay.addLayout(self.clock_lay)
        self.bpm_clock_lay.addLayout(self.time_lay)

        self.start_clock_but = QPushButton(QIcon(os.path.join(GRAPHICS_PATH, "ButtonPlay_rounded.svg")), "")
        self.start_clock_but.setStyleSheet(f"background-color: transparent;")
        self.start_clock_but.setFixedHeight(20)
        self.start_clock_but.clicked.connect(self.start)
        # pause clock
        self.pause_clock_but = QPushButton(QIcon(os.path.join(GRAPHICS_PATH, "ButtonPause_rounded.svg")), "")
        self.pause_clock_but.setStyleSheet(f"background-color: transparent;")
        self.pause_clock_but.setFixedHeight(20)
        self.pause_clock_but.clicked.connect(self.pause)
        # stop clock
        self.stop_clock_but = QPushButton(QIcon(os.path.join(GRAPHICS_PATH, "ButtonStop_rounded.svg")), "")
        self.stop_clock_but.setStyleSheet(f"background-color: transparent;")
        self.stop_clock_but.setFixedHeight(20)
        self.stop_clock_but.clicked.connect(self.stop)
        # reset clock
        self.reset_clock_but = QPushButton(QIcon(os.path.join(GRAPHICS_PATH, "ButtonReset_rounded.svg")), "")
        self.reset_clock_but.setStyleSheet(f"background-color: transparent;")
        self.reset_clock_but.setFixedHeight(20)
        self.reset_clock_but.clicked.connect(self.reset)
        # arm for record
        self.arm_for_record_but = QPushButton(QIcon(os.path.join(GRAPHICS_PATH, "ButtonArmForRecord_FALSE.svg")), "")
        self.arm_for_record_but.setCheckable(True)
        self.arm_for_record_but.setChecked(False)
        self.arm_for_record_but.setStyleSheet(f"background-color: transparent;")
        self.arm_for_record_but.setFixedHeight(20)
        self.arm_for_record_but.clicked.connect(self.arm_for_record)

        self.btn_lay = QHBoxLayout()
        self.btn_lay.setSpacing(0)
        self.btn_lay.addWidget(self.start_clock_but)
        self.btn_lay.addWidget(self.pause_clock_but)
        self.btn_lay.addWidget(self.stop_clock_but)
        self.btn_lay.addWidget(self.reset_clock_but)
        self.btn_lay.addWidget(self.arm_for_record_but)

        # layout
        self.lay = QHBoxLayout()
        self.lay.setSpacing(0)
        self.lay.addLayout(self.btn_lay)
        self.lay.addLayout(self.bpm_clock_lay)
        spacer = QSpacerItem(800, 40, QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        self.lay.addItem(spacer)
        self.setLayout(self.lay)

        self.clock_handler = threading.Thread(target=self.clock_value_event_handler, args=(self.clock,), daemon=True)
        self.clock_handler.start()

    def arm_for_record(self):
        if self.sender().isChecked():
            self.sender().setIcon(QIcon(os.path.join(GRAPHICS_PATH, "ButtonArmForRecord_TRUE.svg")))
            cf = cp.ConfigParser()
            cf.read(CONFIG_PATH)
            rec_path = cf.get("SCSYNTH", "recording_path")
            scsynth.prepare_for_record(os.path.join(rec_path, "SD_" + datetime.now().strftime("%Y%m%d_%H%M%S") + "." + scsynth.recording_header_format.lower()))
        else:
            self.sender().setIcon(QIcon(os.path.join(GRAPHICS_PATH, "ButtonArmForRecord_FALSE.svg")))
            scsynth.stop_recording()

    def set_bounds(self, start, end):
        self.clock.set_bounds(start, end)

    def remove_bounds(self):
        self.clock.remove_bounds()

    def reloadParents(self, main_window):
        self.clock.reloadParents(main_window=main_window)

    def getHMSMSFromTick(self, tick):
        return self.clock.getHMSMSFromTick(tick)

    def getBPM(self):
        return self.clock.getBPM()

    def start(self):
        if scsynth.is_armed_for_recording():
            scsynth.start_recording()
        self.clock.start()

    def reset(self):
        self.clock.reset()
        self.clock_time.setText(self.clock.getCurrentTime().strftime("%H:%M:%S.%f")[:-3])
        self.clock_value.setText(str(int(self.clock.getCount() / (PPQN * 4))))
        self.arm_for_record_but.setChecked(False)
        self.arm_for_record_but.setIcon(QIcon(os.path.join(GRAPHICS_PATH, "ButtonArmForRecord_FALSE.svg")))

    def pause(self):
        self.clock.pause()

    def stop(self):
        self.clock.stop()
        scsynth.stop_recording()
        self.reset()

    def goto(self, value):
        try:
            self.clock.goto(int(value) * PPQN * 4)
        except:
            self.clock.goto(0)

    def goToTick(self, tick):
        try:
            self.clock.goto(int(tick))
        except:
            self.clock.goto(0)
        self.clock_time.setText(self.clock.getCurrentTime().strftime("%H:%M:%S.%f")[:-3])

    def set_region_play_type(self, type: bool):
        self.clock.set_region_play_type(type)

    def clock_value_event_handler(self, clock):
        while True:
            clock.wait()
            if (clock.getCount() % 32) == 0:  # Update Time every 32 ticks
                self.clock_time.setText(self.clock.getCurrentTime().strftime("%H:%M:%S.%f")[:-3])
            if (clock.getCount() % (PPQN * 4)) == 0:  # Update Measure every measure
                # print("\tHey!", clock.getCount(), (PPQN * 4), str(int(clock.getCount() / (PPQN * 4))))
                self.clock_value.setText(str(int(clock.getCount() / (PPQN * 4))))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Qt.GlobalColor.darkGray)
        painter.drawRect(QRect(0, 0, self.width(), self.height()))

    def __getstate__(self):
        pass

    def __setstate__(self, state):
        pass


class HarmonyManager(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.force_global_harm_check = QCheckBox("Forza armonia globale")
        self.note = 0
        self.key = "C"
        # set tonality
        self.set_tonality_butt = QPushButton(text=self.key)
        self.set_tonality_menu = QMenu()
        self.set_tonality_butt.setMenu(self.set_tonality_menu)
        self.reset_tonalities()

        #layout
        self.lay = QVBoxLayout()
        self.lbl = QLabel("HarmonyManager")
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lay.addWidget(self.lbl)
        self.harm_lay = QHBoxLayout()
        self.harm_lay.addWidget(self.set_tonality_butt)
        self.harm_lay.addWidget(self.force_global_harm_check)
        self.lay.addLayout(self.harm_lay)
        self.setLayout(self.lay)

    def isTonalityLocked(self):
        return self.force_global_harm_check.isChecked()

    def getNote(self):
        return self.note

    def getKey(self):
        return self.key

    def reset_tonalities(self):
        self.set_tonality_menu.clear()
        for note in range(-5, 6, 1):
            self.set_tonality_menu.addAction(functions.note2KeySig(note), self.set_key)

    def set_key(self):
        key = self.sender().text()
        self.note = functions.keySig2Fund(key)
        self.set_tonality_butt.setText(key)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Qt.GlobalColor.darkRed)
        painter.drawRect(QRect(0, 0, self.width(), self.height()))

    def __getstate__(self):
        pass

    def __setstate__(self, state):
        pass


class EQ10(AudioWidget):
    def __init__(self, server, parent=None):
        super().__init__(parent=parent)
        self.server = server
        self.synth = None
        self.lbl = QLabel("EQ 10")
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.curve = CurveXY(npoints=10, minY=-32, maxY=12, initial_valuesY=0, unitY="dB", minX=20, maxX=20000, unitX="Hz", interp="Quad")
        #self.setMinimumSize(self.curve.width() + 50, self.curve.height() + 50)
        self.freq_args = ["freq" + str(i + 1) for i in range(10)]
        self.dB_args = ["dB" + str(i + 1) for i in range(10)]
        self.lay = QVBoxLayout()
        self.lay.setContentsMargins(20, 20, 20, 20)
        self.lay.addWidget(self.lbl)
        self.lay.addWidget(self.curve)
        self.setLayout(self.lay)

    def updateArgs(self):
        freqs = self.curve.getXValues()
        dBs = self.curve.getYValues()
        pairs = []
        for i in range(len(freqs)):
            pairs.append([self.freq_args[i]])
            pairs.append([freqs[i]])
            pairs.append([self.dB_args[i]])
            pairs.append([dBs[i]])
        if self.synth is not None:
            self.synth.setn(pairs)

    def createSynth(self):
        if self.synth is not None:
            self.synth.free()
        self.synth = supercollider.Synth(self.server, name="EQ10")

    def __getstate__(self):
        pass

    def __setstate__(self, state):
        pass


class TimeLine(QWidget):
    def __init__(self, parent=None, npoints=32767):
        super(TimeLine, self).__init__(parent)
        self.main_window = parent
        self.region_manager = None
        self.anchor = False
        self.snap_to_grid = False
        self.npoints = npoints
        self.patch = self.main_window.patch
        self.clock = None
        self.widget_curves = {}

        # RegionLine Scroll
        self.region_line_horizontal_layout = QHBoxLayout()
        self.region_line_horizontal_layout.setSpacing(0)
        self.region_line_horizontal_layout.setContentsMargins(0, 0, 0, 0)

        self.region_line_scroll = QScrollArea()
        self.region_line_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.region_line_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.region_line_scroll.horizontalScrollBar().valueChanged.connect(self.sync_scroll_areas)
        self.region_line_scroll_widget = QWidget()
        self.region_line_scroll.setWidget(self.region_line_scroll_widget)
        self.region_line_scroll.setWidgetResizable(True)
        self.region_line_scroll_layout = QVBoxLayout()
        self.region_line_scroll_layout.setSpacing(0)
        self.region_line_scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.region_line_scroll_widget.setLayout(self.region_line_scroll_layout)

        # WidgetCurves Envelope Params Scroll
        self.side_scroll = QScrollArea()
        self.side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.side_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.side_scroll.setFixedWidth(120)
        self.side_scroll.verticalScrollBar().valueChanged.connect(self.sync_vertical_scroll_areas)
        self.side_scroll_widget = QWidget()
        self.side_scroll.setWidget(self.side_scroll_widget)
        self.side_scroll.setWidgetResizable(True)
        self.side_scroll_layout = QVBoxLayout()
        self.side_scroll_layout.setSpacing(0)
        self.side_scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.side_scroll_widget.setLayout(self.side_scroll_layout)

        # WidgetCurves Envelopes Curves Scroll
        self.main_scroll = QScrollArea()
        self.main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.main_scroll.horizontalScrollBar().valueChanged.connect(self.sync_scroll_areas)
        self.main_scroll.verticalScrollBar().valueChanged.connect(self.sync_vertical_scroll_areas)
        self.main_scroll_widget = QWidget()
        # self.main_scroll_widget.setStyleSheet("background-color: red;")
        self.main_scroll.setWidget(self.main_scroll_widget)
        self.main_scroll.setWidgetResizable(True)
        self.main_scroll_layout = QVBoxLayout()
        self.main_scroll_layout.setSpacing(0)
        self.main_scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.main_scroll_widget.setLayout(self.main_scroll_layout)

        # Region + Params
        self.region_line_lay = QHBoxLayout()
        self.region_line_lay.setSpacing(0)
        self.region_line = RegionLine(parent=self, length=self.npoints)
        self.region_line_scroll.setFixedHeight(self.region_line.height())
        self.region_param_wid = QWidget()
        self.region_param_wid.setFixedWidth(120)
        self.region_zoom_lay = QHBoxLayout()
        self.region_param_wid.setLayout(self.region_zoom_lay)
        self.region_zoom_in = QPushButton("Zoom +")
        self.region_zoom_in.setObjectName("widget-param")
        self.region_zoom_in.clicked.connect(self.zoom_in)
        self.region_zoom_lay.addWidget(self.region_zoom_in)
        self.region_zoom_out = QPushButton("Zoom -")
        self.region_zoom_out.setObjectName("widget-param")
        self.region_zoom_out.clicked.connect(self.zoom_out)
        self.region_zoom_lay.addWidget(self.region_zoom_out)
        self.region_lay = QHBoxLayout()
        self.region_lay.setContentsMargins(0, 0, 0, 0)
        self.region_lay.setSpacing(0)
        self.region_line_horizontal_layout.addWidget(self.region_param_wid)
        self.region_lay.addWidget(self.region_line)
        self.region_line_scroll_layout.addLayout(self.region_lay)

        # WidgetCurves - Curves
        self.widget_curves_lay = QVBoxLayout()
        self.widget_curves_lay.setSpacing(0)
        self.widget_curves_lay.setContentsMargins(0, 0, 0, 0)
        self.widget_curves_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.main_scroll_layout.addLayout(self.widget_curves_lay)
        self.main_scroll_layout.setSpacing(0)
        self.main_scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.main_scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.main_scroll_layout.addStretch()

        # WidgetCurves - Params
        self.widget_curves_param_lay = QVBoxLayout()
        self.widget_curves_param_lay.setSpacing(0)
        self.widget_curves_param_lay.setContentsMargins(0, 0, 0, 0)
        self.widget_curves_param_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.side_scroll_layout.addLayout(self.widget_curves_param_lay)
        self.side_scroll_layout.setSpacing(0)
        self.side_scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.side_scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.side_scroll_layout.addStretch()

        self.layout = QVBoxLayout(self)
        self.layout.addLayout(self.region_line_horizontal_layout)
        self.region_line_horizontal_layout.addWidget(self.region_line_scroll)
        self.side_main_horizontal_layout = QHBoxLayout()
        self.side_main_horizontal_layout.setSpacing(0)
        self.side_main_horizontal_layout.setContentsMargins(0, 0, 0, 0)
        self.side_main_horizontal_layout.addWidget(self.side_scroll)
        self.side_main_horizontal_layout.addWidget(self.main_scroll)
        self.layout.addLayout(self.side_main_horizontal_layout)

    def get_undo_stack(self):
        return self.main_window.get_undo_stack()

    def sync_scroll_areas(self, value):
        sender = self.sender()
        if sender == self.main_scroll.horizontalScrollBar():
            self.region_line_scroll.horizontalScrollBar().setValue(value)
        elif sender == self.region_line_scroll.horizontalScrollBar():
            self.main_scroll.horizontalScrollBar().setValue(value)

    def sync_vertical_scroll_areas(self, value):
        sender = self.sender()
        if sender == self.main_scroll.verticalScrollBar():
            self.side_scroll.verticalScrollBar().setValue(value)
        elif sender == self.side_scroll.verticalScrollBar():
            self.main_scroll.verticalScrollBar().setValue(value)

    def set_anchor(self, anchor):
        self.anchor = anchor
        for key in self.widget_curves.keys():
            self.widget_curves[key].set_anchor(self.anchor)

    def set_snap_to_grid(self, snap):
        self.snap_to_grid = snap
        for key in self.widget_curves.keys():
            self.widget_curves[key].set_snap_to_grid(self.snap_to_grid)

    def move_points(self, from_, to_, move):
        for key in self.widget_curves.keys():
            self.widget_curves[key].move_points(from_, to_, move)

    def stretch_points(self, old_region, from_, to_):
        for key in self.widget_curves.keys():
            self.widget_curves[key].stretch_points(old_region, from_, to_)

    def setClock(self, clock):
        self.clock = clock
        self.region_line.setClock(self.clock)
        self.update()

    def setRegionManager(self, region_manager):
        self.region_manager = region_manager
        self.region_manager.set_anchor()
        self.update()

    def setDuration(self, seconds):
        self.npoints = int(seconds * PPQN * self.clock.bpm / 60)
        self.region_line.change_length(self.npoints)
        for key in self.widget_curves.keys():
            self.widget_curves[key].change_length(self.npoints)

    def getDuration(self):
        return (self.npoints * 60) / (PPQN * self.clock.bpm)

    def zoom_in(self):
        self.region_line.zoom_in()
        for key in self.widget_curves.keys():
            self.widget_curves[key].zoom_in()
        self.main_scroll_widget.setFixedWidth(self.region_line.width())

    def zoom_out(self):
        self.region_line.zoom_out()
        for key in self.widget_curves.keys():
            self.widget_curves[key].zoom_out()
        self.main_scroll_widget.setFixedWidth(self.region_line.width())

    def populate_widgets(self):
        widget_curve_states = {key: self.widget_curves[key].__getstate__() for key in self.widget_curves.keys()}
        self.widget_curves = {}

        for i in reversed(range(0, self.widget_curves_lay.count())):
            item = self.widget_curves_lay.itemAt(i)
            if item.widget() is None:
                self.widget_curves_lay.removeItem(item)
                pass
            else:
                self.widget_curves_lay.itemAt(i).widget().setParent(None)
        for i in reversed(range(0, self.widget_curves_param_lay.count())):
            item = self.widget_curves_param_lay.itemAt(i)
            if item.widget() is None:
                self.widget_curves_param_lay.removeItem(item)
                pass
            else:
                self.widget_curves_param_lay.itemAt(i).widget().setParent(None)

        for audio_widget in self.patch.audio_widgets:
            wc = WidgetCurves(parent=self, name=audio_widget.synth_name + " - " + str(audio_widget.getUUID()), region_line=self.region_line,
                              uuid=audio_widget.getUUID(), synth_args=audio_widget.getSynthArgs(), npoints=self.npoints)
            if str(wc.uuid) in widget_curve_states.keys():
                wc.__setstate__(widget_curve_states[str(wc.uuid)])
            self.widget_curves[str(audio_widget.getUUID())] = wc
            self.widget_curves_lay.addWidget(wc)
            wc.setFixedHeight(25)
            params = wc.getParamsWidget()
            self.widget_curves_param_lay.addWidget(params)

        for audio_midi_widget in self.patch.audio_midi_widgets:
            wc = WidgetCurves(parent=self, name=audio_midi_widget.synth_name + " - " + str(audio_midi_widget.getUUID()), region_line=self.region_line,
                              uuid=audio_midi_widget.getUUID(), synth_args=audio_midi_widget.getSynthArgs(), npoints=self.npoints)
            if str(wc.uuid) in widget_curve_states.keys():
                wc.__setstate__(widget_curve_states[str(wc.uuid)])
            self.widget_curves[str(audio_midi_widget.getUUID())] = wc
            self.widget_curves_lay.addWidget(wc)
            self.widget_curves_param_lay.addWidget(wc.getParamsWidget())
        self.widget_curves_param_lay.addStretch()
        self.widget_curves_lay.addStretch()

    def reset_parent(self, parent):
        self.main_window = parent
        self.patch = self.main_window.patch

    def __getstate__(self):
        d = {
            "RegionLine": self.region_line.__getstate__(),
            "WidgetCurves": {uuid: self.widget_curves[uuid].__getstate__() for uuid in self.widget_curves.keys()}
        }
        return d

    def __setstate__(self, state):
        super(TimeLine, self).__init__()
        self.__init__(win)
        self.main_window = win
        self.patch = self.main_window.patch
        self.region_line.__setstate__(state["RegionLine"])
        self.widget_curves = {}

        for i in reversed(range(0, self.widget_curves_lay.count())):
            item = self.widget_curves_lay.itemAt(i)
            if item.widget() is None:
                self.widget_curves_lay.removeItem(item)
                pass
            else:
                self.widget_curves_lay.itemAt(i).widget().setParent(None)
        for i in reversed(range(0, self.widget_curves_param_lay.count())):
            item = self.widget_curves_param_lay.itemAt(i)
            if item.widget() is None:
                self.widget_curves_param_lay.removeItem(item)
                pass
            else:
                self.widget_curves_param_lay.itemAt(i).widget().setParent(None)

        for key in state["WidgetCurves"].keys():
            wc_state = state["WidgetCurves"][key]
            wc = WidgetCurves(parent=self, name=wc_state["name"], region_line=self.region_line, uuid=wc_state["uuid"], synth_args=wc_state["synth_args"], npoints=self.npoints)
            self.widget_curves[str(wc_state["uuid"])] = wc
            self.widget_curves_lay.addWidget(wc)
            self.widget_curves[str(wc_state["uuid"])].__setstate__(wc_state)
            self.widget_curves_param_lay.addWidget(wc.getParamsWidget())
        self.widget_curves_param_lay.addStretch()
        self.widget_curves_lay.addStretch()



class SubPatch(QWidget):
    def __init__(self, parent=None, name=""):
        super(QWidget, self).__init__(parent=parent)
        # TODO: ad ogni cambio del grafo di sintesi, aggiornare inlet/outlet dei widget ad esso associati
        self.setObjectName("patch")
        # Global Access
        self.parent = parent
        self.name = name
        self.main_window = self.parent
        self.context = None
        self.meter_enabled = True
        self.context = self.parent.context
        self.audiostatus = self.parent.audiostatus
        self.group = 0
        # PatchBuffers
        self.patch_buffers = PatchBuffers(server=scsynth, patch=self)
        # PatchArea
        self.patch_area = SubPatchArea(self, self.parent.context, None)
        self.widgets = load_widgets_list("./")
        self.audio_widgets = []
        self.midi_widgets = []
        self.audio_midi_widgets = []
        self.subpatch_widgets = []

        self.instance_graphs = {}

        self.patch_scroll = QScrollArea()
        # self.patch_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # self.patch_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.patch_scroll.setWidget(self.patch_area)
        self.lay = QVBoxLayout()
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(0)
        self.lay.addWidget(self.patch_scroll)
        self.setLayout(self.lay)

    def update_subpatch_instances(self):
        print("Calling update_subpatch_instances on patch 0:main")
        for subpatch_widget in self.subpatch_widgets:
            subpatch_widget.initArgs()
            subpatch_widget.reinitUI()

    def getIO(self):
        print("Ehi diocane ci sono", self.audio_widgets)
        ins = 0
        outs = 0
        for wi in self.audio_widgets:
            # print("wi", wi)
            if wi.name == "SubPatch Input":
                ins += 1
                # print("OK: SubPatch Input")
            if wi.name == "SubPatch Output":
                outs += 1
                # print("OK: SubPatch Output")
        return ins, outs

    def getIONames(self):
        # print("Ehi diocane ci sono", self.audio_widgets)
        in_names = []
        out_names = []
        for wi in self.audio_widgets:
            # print("wi", wi)
            if wi.name == "SubPatch Input":
                in_names.append(wi.getSynthArgs()["name"]["val"])
                # print("OK: SubPatch Input")
            if wi.name == "SubPatch Output":
                out_names.append(wi.getSynthArgs()["name"]["val"])
                # print("OK: SubPatch Output")
        return in_names, out_names

    def getIOChansForInstance(self, instance):
        in_chans = []
        out_chans = []
        for key in self.instance_graphs[str(instance.getUUID())]["AudioWidgets"].keys():
            wi = self.instance_graphs[str(instance.getUUID())]["AudioWidgets"][key]
            # print("wi", wi)
            if wi.name == "SubPatch Input":
                in_chans.append(wi.getSettings()["Inputs"]["in_ch_0"])
                # print("OK: SubPatch Input")
            if wi.name == "SubPatch Output":
                out_chans.append(wi.getSettings()["Outputs"]["out_ch_0"])
                # print("OK: SubPatch Output")
        return in_chans, out_chans

    def getGroup(self):
        # TODO: implement this method to allow sub-sub-patch recursion handling
        return self.group

    def addSubPatchInstance(self, subpatch_widget):
        self.subpatch_widgets.append(subpatch_widget)

    def set_meter_enable(self, enabled: bool):
        self.meter_enabled = enabled

    def create_icon(self, path):
        # Crea un'icona ridimensionata a 50x50px
        pixmap = QPixmap(path).scaled(50, 50)
        icon = QIcon(pixmap)
        return icon

    def get_undo_stack(self):
        return self.main_window.get_undo_stack()

    def set_context(self, context):
        self.context = context

    def set_main_window(self, win):
        self.main_window = win

    def flushPatch(self):
        for widget in self.audio_widgets:
            self.remove_audio_widget(widget)

    def propagateCableMouseClick(self, event, subtractGlobalPos=False):
        for audio_widget in self.audio_widgets:
            audio_widget.mouseCablePressEvent(event, subtractGlobalPos)
        for midi_widget in self.audio_widgets:
            midi_widget.mouseCablePressEvent(event, subtractGlobalPos)

    def reset_widgets(self):
        for widget in self.audio_widgets:
            widget.resetSynthArgs()

    def redraw_audio_widgets(self):
        for widget in self.audio_widgets:
            widget.initUI()

    def get_instance_graph_state(self, uuid):
        if type(uuid) != str:
            uuid = str(uuid)
        graph = self.instance_graphs[uuid]
        d = {}
        d["InstanceUUID"] = uuid
        d["Target Node"] = graph["Target Node"]
        d["SubPatch"] = {"name": graph["SubPatch"].name, "state": graph["SubPatch"].__getstate__()}
        d["AudioWidgets"] = {}
        d["AudioCables"] = {}
        for key in graph["AudioWidgets"].keys():
            c_print("yellow", f'graph["AudioWidgets"][{key}] is: {graph["AudioWidgets"][key]}')
            if type(graph["AudioWidgets"][key]) != dict:
                graph["AudioWidgets"][key] = graph["AudioWidgets"][key].__getstate__()
        for key in graph["AudioCables"].keys():
            c_print("green", f'graph["AudioCables"][{key}] is: {graph["AudioCables"][key]}')
            graph["AudioCables"][key] = graph["AudioCables"][key].__getstate__()
        return d

    def set_instance_graph_state(self, state, instance):
        uuid = str(instance.getUUID())
        self.instance_graphs[uuid] = {}
        self.instance_graphs[uuid]["InstanceUUID"] = instance.getUUID()
        self.instance_graphs[uuid]["SubPatch"] = SubPatch(self.main_window, name=str(uuid))
        self.instance_graphs[uuid]["SubPatch"].__setstate__(state["SubPatch"]["state"])
        self.instance_graphs[uuid]["SubPatchArea"] = self.instance_graphs[uuid]["SubPatch"].patch_area
        self.instance_graphs[uuid]["AudioWidgets"] = {str(wid.getUUID()): wid for wid in self.instance_graphs[uuid]["SubPatch"].audio_widgets}
        # self.instance_graphs[state["InstanceUUID"]]["AudioCables"] = {str(cab.getUUID()): cab for cab in self.instance_graphs[state["InstanceUUID"]]["SubPatch"].patch_area.audio_cables}
        c_print("cyan", f'Instance Graph Audio Widgets after __setstate__ : {self.instance_graphs[uuid]["SubPatch"].audio_widgets}')
        self.instance_graphs[uuid]["SubPatchArea"].repatch_audio_instance(instance.getGroupNode())

    def create_instance_graph(self, instance):
        # TODO: implement this method
        # Crea una nuova data structure per il grafo appartenente ad un'istanza di subpatch. Per rendere le cose semplici,
        # meglio creare un SubPatch e un SubPatchArea fittizzi non editabili dove creare la copia del SubPatch editabile
        self.instance_graphs[str(instance.getUUID())] = {"SubPatch": SubPatch(self.main_window, name=str(instance.getUUID())), "Target Node": instance.group.getNodeID(), "AudioWidgets": {}, "AudioCables": {}}
        # self.instance_graphs[instance.getUUID()]["SubPatchArea"] = SubPatchArea(self.instance_graphs[instance.getUUID()]["SubPatch"], self.context, None)
        self.instance_graphs[str(instance.getUUID())]["SubPatchArea"] = self.instance_graphs[str(instance.getUUID())]["SubPatch"].patch_area
        # Per ogni widget di ogni tipo, creane una copia attiva con un nuovo UUID
        for widget in self.audio_widgets:
            widget_instance = AudioWidget(scsynth, self.instance_graphs[str(instance.getUUID())]["SubPatchArea"], widget.n_in, widget.n_out, widget.synth_name, widget.synth_args, scsynth.queryFreeNode(), widget.name, True)
            self.instance_graphs[str(instance.getUUID())]["AudioWidgets"][str(widget.getUUID())] = widget_instance
            self.instance_graphs[str(instance.getUUID())]["AudioWidgets"][str(widget.getUUID())].synth.moveToHead(instance.getGroupNode())
            self.instance_graphs[str(instance.getUUID())]["SubPatch"].audio_widgets.append(widget_instance)
        # Ora crea la copia dei cavi
        for cable in self.patch_area.audio_cables:
            widget_out = self.instance_graphs[str(instance.getUUID())]["AudioWidgets"][str(cable.widget_out.getUUID())]
            widget_in = self.instance_graphs[str(instance.getUUID())]["AudioWidgets"][str(cable.widget_in.getUUID())]
            # self.instance_graphs[instance.getUUID()]["AudioCables"][cable.getUUID()] = AudioCable(0, 0, widget_out, cable.widget_out_id, self.instance_graphs[instance.getUUID()]["SubPatchArea"])
            new_cable = AudioCable(0, 0, widget_out, cable.widget_out_id, self.instance_graphs[str(instance.getUUID())]["SubPatchArea"])
            if cable.connects_parameter:
                # self.instance_graphs[instance.getUUID()]["AudioCables"][cable.getUUID()].addParameterWidget(widget_in, cable.widget_in_id)
                new_cable.addParameterWidget(widget_in, cable.widget_in_id)
            else:
                # self.instance_graphs[instance.getUUID()]["AudioCables"][cable.getUUID()].addInletWidget(widget_in, cable.widget_in_id)
                new_cable.addInletWidget(widget_in, cable.widget_in_id)
            # add_audio_cable:
            # self.instance_graphs[instance.getUUID()]["SubPatchArea"].add_audio_cable(self.instance_graphs[instance.getUUID()]["AudioCables"][cable.getUUID()])
            self.instance_graphs[str(instance.getUUID())]["SubPatchArea"].add_audio_cable(new_cable)
        self.update_instance_graph(instance)

    def update_instance_graph(self, instance):
        # TODO: implement this method
        # TODO: check graph consistency (handle add/remove entries to be pushed)
        self.instance_graphs[str(instance.getUUID())]["SubPatchArea"].repatch_audio_instance(instance.getGroupNode())
        pass

    def delete_instance_graph(self, instance):
        # TODO: implement this method
        for widget in self.instance_graphs[str(instance.getUUID())]["SubPatch"].audio_widgets:
            widget.freeSynth()
        del self.instance_graphs[str(instance.getUUID())]
        pass

    def get_instance_graph(self, uuid):
        return self.instance_graphs[str(uuid)]

    def add_audio_widget(self):
        class_name = self.sender().text()
        class_kind = ""
        for kind in self.widgets["audio"].keys():
            if class_name in self.widgets["audio"][kind].keys():
                class_kind = kind
        data = self.widgets["audio"][class_kind][class_name]
        instance = AudioWidget(server=scsynth, parent=self.patch_area, synth_name=data["synth_name"], n_in=data["n_in"], n_out=data["n_out"], synth_args=data["args"], name=class_name, active=False)
        instance.setGeometry(20, 20, instance.width(), instance.height())
        instance.show()
        self.audio_widgets.append(instance)
        for key in self.parent.patches.keys():
            self.parent.patches[key].update_subpatch_instances()
        # self.parent.patches["0:main"].update_subpatch_instances()
        self.parent.timeline.populate_widgets()

    def remove_audio_widget(self, widget):
        widget.freeSynth()
        c_print("cyan", f"removing audio widget: {widget.getUUID()}")
        for cable in self.patch_area.audio_cables:
            if cable.widget_in.getUUID() == widget.getUUID() or cable.widget_out.getUUID() == widget.getUUID():
                print(f"trovato cable: {cable}")
                self.patch_area.audio_cables.remove(cable)
                cable.hide()
                del cable
        for cable in self.patch_area.midi_cables:
            if cable.widget_in == widget or cable.widget_out == widget:
                self.patch_area.midi_cables.remove(cable)
                cable.hide()
                del cable
        self.audio_widgets.remove(widget)
        widget.hide()
        del widget
        for key in self.parent.patches.keys():
            self.parent.patches[key].update_subpatch_instances()
        # self.parent.patches["0:main"].update_subpatch_instances()
        self.parent.timeline.populate_widgets()

    def add_midi_widget(self):
        class_name = self.sender().text()
        class_ = eval(class_name)
        instance = class_(server=scsynth, clock=self.main_window.clock, harmony_manager=self.context.harmony_manager, parent=self.patch_area)
        instance.setGeometry(20, 20, instance.width(), instance.height())
        instance.show()
        self.midi_widgets.append(instance)
        self.parent.timeline.populate_widgets()

    def add_midi_widget_from_name(self, class_name):
        class_ = eval(class_name)
        instance = class_(server=scsynth, clock=self.main_window.clock, harmony_manager=self.context.harmony_manager, parent=self.patch_area)
        instance.setGeometry(20, 20, instance.width(), instance.height())
        instance.show()
        self.midi_widgets.append(instance)
        self.parent.timeline.populate_widgets()

    def remove_midi_widget(self, widget):
        self.midi_widgets.remove(widget)
        widget.hide()
        del widget
        self.parent.timeline.populate_widgets()

    def add_audio_midi_widget(self):
        class_name = self.sender().text()
        class_kind = ""
        for kind in self.widgets["audio_midi"].keys():
            if class_name in self.widgets["audio_midi"][kind].keys():
                class_kind = kind
        data = self.widgets["audio_midi"][class_kind][class_name]
        instance = AudioMIDIWidget(server=scsynth, clock=self.main_window.clock, harmony_manager=self.context.harmony_manager, parent=self.patch_area, synth_name=data["synth_name"], n_audio_in=data["n_audio_in"], n_audio_out=data["n_audio_out"], n_midi_in=data["n_midi_in"], n_midi_out=data["n_midi_out"], synth_args=data["args"])
        instance.setGeometry(20, 20, instance.width(), instance.height())
        instance.show()
        self.audio_midi_widgets.append(instance)
        self.parent.timeline.populate_widgets()

    def add_custom_audio_midi_widget(self):
        class_name = self.sender().text()
        class_ = eval(class_name)
        instance = class_(server=scsynth, clock=self.main_window.clock, harmony_manager=self.context.harmony_manager, parent=self.patch_area)
        instance.setGeometry(20, 20, instance.width(), instance.height())
        instance.show()
        self.audio_midi_widgets.append(instance)
        self.parent.timeline.populate_widgets()

    def remove_audio_midi_widget(self, widget):
        widget.freeSynth()
        self.audio_midi_widgets.remove(widget)
        widget.hide()
        del widget
        self.parent.timeline.populate_widgets()

    def add_sub_patch_widget(self):
        # TODO: implement add_sub_patch_widget method
        class_name = self.sender().text()
        subpatch_instance_name = [key for key in self.main_window.patches.keys() if key.split(":")[1] == class_name]
        subpatch_instance_name.pop(subpatch_instance_name.index(self.name))  # remove self since it's wrong in this case
        subpatch_instance = self.main_window.patches[subpatch_instance_name[0]]
        instance = SubPatchInstanceWidget(server=scsynth, parent=self.patch_area, subpatch=subpatch_instance, target_patch=self)
        instance.setGeometry(20, 20, instance.width(), instance.height())
        instance.show()
        self.subpatch_widgets.append(instance)
        self.create_instance_graph(instance)
        self.parent.timeline.populate_widgets()

    def remove_sub_patch_widget(self, widget):
        # TODO: implement remove_sub_patch_widget method
        widget.freeSynth()
        self.delete_instance_graph(widget)
        self.subpatch_widgets.remove(widget)
        widget.hide()
        del widget
        self.parent.timeline.populate_widgets()

    def getSubPatchInstanceInletWidget(self, instance_uuid, inlet_name):
        if type(instance_uuid) != str:
            instance_uuid = str(instance_uuid)
        print(f"Checking for real inlet {inlet_name}...")
        print(f"SubPatch instance_graphs keys: {self.instance_graphs.keys()}")
        for wi in self.instance_graphs[instance_uuid]["SubPatch"].audio_widgets:
            print("wi", wi)
            if wi.name == "SubPatch Input":
                if wi.getSynthArgs()["name"]["val"] == inlet_name:
                    print(f"\tFound: {wi}")
                    return wi
        return -1

    def getSubPatchInstanceOutletWidget(self, instance_uuid, outlet_name):
        print(f"Checking for real outlet {outlet_name}...")
        if type(instance_uuid) != str:
            instance_uuid = str(instance_uuid)
        for wi in self.instance_graphs[instance_uuid]["SubPatch"].audio_widgets:
            print("wi", wi)
            if wi.name == "SubPatch Output":
                if wi.getSynthArgs()["name"]["val"] == outlet_name:
                    print(f"\tFound: {wi}")
                    return wi
        return -1

    def __getstate__(self):
        d = {
            "audio_widgets": [cls.__class__.__name__ for cls in self.audio_widgets],
            "audio_widgets_states": [cls.__getstate__() for cls in self.audio_widgets],
            "midi_widgets": [cls.__class__.__name__ for cls in self.midi_widgets],
            "midi_widgets_states": [cls.__getstate__() for cls in self.midi_widgets],
            "audio_midi_widgets": [cls.__class__.__name__ for cls in self.audio_midi_widgets],
            "audio_midi_widgets_states": [cls.__getstate__() for cls in self.audio_midi_widgets],
            "subpatch_widgets": [cls.__class__.__name__ for cls in self.subpatch_widgets],
            "subpatch_widgets_states": [cls.__getstate__() for cls in self.subpatch_widgets],
            "patch_buffers": self.patch_buffers.__getstate__(),
            "patch_area": self.patch_area.__getstate__()
        }
        return d

    def __setstate__(self, state):
        super(SubPatch, self).__init__()
        self.__init__(win)  # TODO: CONTROLLARE BENE QUESTA RIGA!!!!!!!!!
        print("Qui win è:", win)
        # Prima ricreo i PatchBuffers
        self.patch_buffers = PatchBuffers(server=scsynth, patch=self)
        self.patch_buffers.__setstate__(state["patch_buffers"])
        # Poi ricreo i Widget Audio
        self.audio_widgets = []
        self.flushPatch()
        for index, cls in enumerate(state['audio_widgets']):
            data = state["audio_widgets_states"][index]
            name = ""
            if "name" in list(data.keys()):
                name = data["name"]
            instance = AudioWidget(server=self.context.server, parent=self.patch_area, uuid=data["uuid"],
                                   n_in=data["n_in"], n_out=data["n_out"], synth_name=data["synth_name"],
                                   synth_args=data["Settings"]["Parameters"], name=name, active=False)
            c_print("yellow", f"Setting AudioWidget {name}-{data['uuid']} recreation settings: {data}")
            instance.__setstate__(data)
            instance.setActive(False)
            print(f"Adding SubPatch AudioWidget: {data}")
            self.audio_widgets.append(instance)

        # Poi ricreo i Widget MIDI
        for index, cls in enumerate(state['midi_widgets']):
            if cls == "MIDIWidget":
                data = state["midi_widgets_states"][index]
                instance = MIDIWidget(server=self.context.server, parent=self.patch_area, clock=self.main_window.clock,
                                      harmony_manager=self.context.harmony_manager, uuid=data["uuid"],
                                      n_midi_in=data["n_midi_in"], n_midi_out=data["n_midi_out"])
                instance.__setstate__(state["midi_widgets_states"][index])
                self.midi_widgets.append(instance)
            else:
                data = state["midi_widgets_states"][index]
                print("cls:", cls, type(cls))
                print("data:", data)
                instance = globals()[cls](server=self.context.server, parent=self.patch_area,
                                          clock=self.main_window.clock,
                                          harmony_manager=self.context.harmony_manager, uuid=data["uuid"],
                                          n_midi_in=data["n_midi_in"], n_midi_out=data["n_midi_out"])
                instance.__setstate__(state["midi_widgets_states"][index])
                self.midi_widgets.append(instance)

        # Poi ricreo i Widget AudioMIDI
        for index, cls in enumerate(state['audio_midi_widgets']):
            if cls == "AudioMIDIWidget":
                data = state["audio_midi_widgets_states"][index]
                instance = AudioMIDIWidget(server=self.context.server, clock=self.main_window.clock,
                                           harmony_manager=self.context.harmony_manager, parent=self.patch_area,
                                           uuid=data["uuid"],
                                           n_audio_in=data["n_audio_in"], n_audio_out=data["n_audio_out"],
                                           n_midi_in=data["n_midi_in"], n_midi_out=data["n_midi_out"],
                                           synth_name=data["synth_name"], synth_args=data["Settings"]["Parameters"])
                instance.__setstate__(state["audio_midi_widgets_states"][index])
                self.audio_midi_widgets.append(instance)
            else:
                data = state["audio_midi_widgets_states"][index]
                instance = globals()[cls](server=self.context.server, clock=self.main_window.clock,
                                          harmony_manager=self.context.harmony_manager, parent=self.patch_area,
                                          uuid=data["uuid"],
                                          n_audio_in=data["n_audio_in"], n_audio_out=data["n_audio_out"],
                                          n_midi_in=data["n_midi_in"], n_midi_out=data["n_midi_out"],
                                          synth_name=data["synth_name"], synth_args=data["Settings"]["Parameters"])
                instance.__setstate__(state["audio_midi_widgets_states"][index])
                self.audio_midi_widgets.append(instance)
        # Poi ricreo il Patch
        self.patch_area.__setstate__(state["patch_area"])
        self.reset_widgets()
        print("Opening patch (PATCH): audio widgets:", self)
        print("\taudio_widgets:", self.audio_widgets)
        # Quindi aggiorno il RegionManager
        self.main_window.region_manager.refresh_regions()
        scsynth.dumpNodeTree()


class SubPatchArea(PatchArea):
    def __init__(self, *args, **kwargs):
        super(SubPatchArea, self).__init__(*args, **kwargs)

    def repatch_audio(self):
        pass

    def repatch_audio_instance(self, group):
        print("\nBeginning audio repatch:")
        widget_ins = defaultdict(list)
        node_order = []
        sources = []
        # Conta quanti inlet (connessi) ha ciascun widget
        for widget in self.patch.audio_widgets + self.patch.subpatch_widgets:
            widget_ins[widget.getUUID()] = []
            for cable in self.audio_cables:
                if cable.widget_in:
                    if widget.getUUID() == cable.widget_in.getUUID():
                        widget_ins[widget.getUUID()].append(cable.widget_out.getUUID())
        is_first_widget = True
        # Metti in Head i widget con zero inlet (connessi)
        for widget in self.patch.audio_widgets + self.patch.subpatch_widgets:
            if len(widget_ins[widget.getUUID()]) == 0:
                if is_first_widget == True:
                    print("Moving to Head:", widget.getUUID(), widget.synth_name)
                    if hasattr(widget, "group"):
                        widget.group.moveToHead(group)
                    elif hasattr(widget, "synth"):
                        widget.synth.moveToHead(group)
                else:
                    print("Moving", widget.getUUID(), widget.synth_name, "AFTER", is_first_widget.getUUID(), is_first_widget.synth_name)
                    if hasattr(is_first_widget, "group"):
                        widget.moveAfter(is_first_widget.group)
                    elif hasattr(is_first_widget, "synth"):
                        widget.moveAfter(is_first_widget.synth)
                is_first_widget = widget
                sources.append(widget.getUUID())
                del widget_ins[widget.getUUID()]
        # Metti in After i widget con 1 inlet i cui nodi Before siano stati rimossi dalla lista
        # TODO: mettere loop infinito al posto di range(3)!!!
        for _ in range(3):
            for widget in self.patch.audio_widgets + self.patch.subpatch_widgets:
                if widget.getUUID() in widget_ins.keys():
                    if len(widget_ins[widget.getUUID()]) == 1:
                        for cable in self.audio_cables:
                            if cable.widget_in and cable.widget_out:
                                if (widget.getUUID() == cable.widget_in.getUUID()) and (widget_ins[widget.getUUID()][0] == cable.widget_out.getUUID()):  # Trova il cavo associato
                                    if cable.widget_out.getUUID() not in widget_ins.keys():
                                        if hasattr(cable.widget_out, "group"):
                                            widget.moveAfter(cable.widget_out.group)
                                        elif hasattr(cable.widget_out, "synth"):
                                            widget.moveAfter(cable.widget_out.synth)
                                        node_order.append(widget.getUUID())
                                        print("Moving", widget.getUUID(), widget.synth_name, "AFTER", cable.widget_out.getUUID(), cable.widget_out.synth_name)
                                        del widget_ins[widget.getUUID()]
            # Se trovi un widget con >1 inlet i cui nodi Before siano stati TUTTI rimossi dalla lista, prendi l'ultimo e mettilo After a quello
            for widget in self.patch.audio_widgets + self.patch.subpatch_widgets:
                if widget.getUUID() in widget_ins.keys():
                    if len(widget_ins[widget.getUUID()]) > 1:
                        # print(f"Found {widget.getUUID()}, {widget.synth_name} with length: >1")
                        target_node = -1
                        to_be_processed = 0  # Trova i nodi dipendenti ancora da processare
                        for w_in in widget_ins[widget.getUUID()]:
                            if w_in in widget_ins.keys():
                                to_be_processed += 1
                        if to_be_processed == 0:  # Se non hai nodi dipendenti ancora da processare
                            # Trova l'ultimo nodo messo in After
                            for node in reversed(node_order):
                                if node in widget_ins[widget.getUUID()]:
                                    target_node = node
                                    break
                            if target_node == -1:
                                target_node = sources[-1]
                            # Metti il widget After target_node
                            has_to_break = False
                            for node_widget in self.patch.audio_widgets + self.patch.subpatch_widgets:
                                if node_widget.getUUID() == target_node:
                                    for cable in self.audio_cables:
                                        if target_node == cable.widget_out.getUUID():  # Trova il cavo associato
                                            if hasattr(cable.widget_out, "group"):
                                                widget.moveAfter(cable.widget_out.group)
                                            elif hasattr(cable.widget_out, "synth"):
                                                widget.moveAfter(cable.widget_out.synth)
                                            node_order.append(widget.getUUID())
                                            print("Moving", widget.getUUID(), widget.synth_name, "AFTER", cable.widget_out.getUUID(), cable.widget_out.synth_name)
                                            del widget_ins[widget.getUUID()]
                                            has_to_break = True
                                            break
                                        if has_to_break:
                                            break
        print("Ended audio repatch!\n")
        self.patch.audiostatus.populate()

    def __getstate__(self):
        print("audio cables:", self.audio_cables)
        d = {
            "audio_cables": [cable.__getstate__() for cable in self.audio_cables],
            "midi_cables": [cable.__getstate__() for cable in self.midi_cables],
        }
        print("saving cables dictionary:", d)
        return d

    def __setstate__(self, state):
        self.audio_cables = []
        # print("Setting audio cables states:", state["audio_cables"])
        for index, cable_state in enumerate(state["audio_cables"]):
            widget_out = None
            widget_in = None
            # print("OUT UUID:", cable_state["widget_out_uuid"])
            # print("IN UUID:", cable_state["widget_in_uuid"])
            # print("audio uuids:", [widget.getUUID() for widget in self.patch.audio_widgets])
            # print("audio_midi uuids:", [widget.getUUID() for widget in self.patch.audio_midi_widgets])
            # print("midi uuids:", [widget.getUUID() for widget in self.patch.midi_widgets])
            # is Audio Widget?
            for widget in self.patch.audio_widgets:
                if widget.getUUID() == cable_state["widget_out_uuid"]:
                    widget_out = widget
                if widget.getUUID() == cable_state["widget_in_uuid"]:
                    widget_in = widget
            # is AudioMIDI Widget?
            for widget in self.patch.audio_midi_widgets:
                if widget.getUUID() == cable_state["widget_out_uuid"]:
                    widget_out = widget
                if widget.getUUID() == cable_state["widget_in_uuid"]:
                    widget_in = widget
            cable = AudioCable(cable_state["x"], cable_state["y"], widget_out, cable_state["widget_out_id"], self)
            if type(cable_state["widget_in_id"]) == str:
                cable.addParameterWidget(widget_in, cable_state["widget_in_id"])
            else:
                cable.addInletWidget(widget_in, cable_state["widget_in_id"])
            self.add_audio_cable(cable)
            self.place_cable()
        # MIDI Cables
        try:
            _ = state["midi_cables"]
        except KeyError:
            state["midi_cables"] = []
        for index, cable_state in enumerate(state["midi_cables"]):
            widget_out = None
            widget_in = None
            # is MIDI Widget?
            for widget in self.patch.midi_widgets:
                if widget.getUUID() == cable_state["widget_out_uuid"]:
                    widget_out = widget
                if widget.getUUID() == cable_state["widget_in_uuid"]:
                    widget_in = widget
            # is AudioMIDI Widget?
            for widget in self.patch.audio_midi_widgets:
                if widget.getUUID() == cable_state["widget_out_uuid"]:
                    widget_out = widget
                if widget.getUUID() == cable_state["widget_in_uuid"]:
                    widget_in = widget
            cable = MIDICable(cable_state["x"], cable_state["y"], widget_out, cable_state["widget_out_id"], self)
            cable.addInletWidget(widget_in, cable_state["widget_in_id"])
            self.add_midi_cable(cable)
        print("Number of audio cables:", len(self.audio_cables))
        self.lower_cables()


class GestureCreator(QDialog):
    def __init__(self, parent=None):
        super(QDialog, self).__init__(parent=parent)
        self.setModal(True)
        self.setWindowTitle("Gesture Creator")


if __name__ == "__main__":
    import sys
    sys.setrecursionlimit(60)
    app = QApplication(sys.argv)
    win = MainWindow(app=app)
    win.show()
    app.exec()
