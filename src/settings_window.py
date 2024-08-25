from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
import configparser as cp
import sounddevice as sd
import rtmidi
from supercollider import scsynth
from datetime import datetime
from log_coloring import c_print
from path_manager import STYLE_PATH, CONFIG_PATH

config = cp.ConfigParser()
config.read(CONFIG_PATH)
try:
    pbuf_path = config.get("PATHS", "pbuf_path")
    GRID_SIZE = config.getint("TIMELINE", "grid_size_ppqn")
except:
    c_print("red", "[ERROR]: Config File not found")
    pbuf_path = "/Users/francescodani/Music/SoundDesigner/"
    GRID_SIZE = 20

class Settings(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setModal(True)
        self.setWindowTitle("Settings")
        self.lay = QVBoxLayout()
        self.tab_wid = QTabWidget()
        self.lay.addWidget(self.tab_wid)
        self.setLayout(self.lay)
        self.tab_wid.addTab(AudioSettings(self, self.main_window), "Audio")
        self.tab_wid.addTab(MIDISettings(self, self.main_window), "MIDI")
        self.tab_wid.addTab(ProjectSettings(self, self.main_window), "Project")


class AudioSettings(QWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.config = cp.ConfigParser()
        self.config.read('config.ini')

        self.lay = QVBoxLayout()
        self.audio_param_lay = QLabel("Audio Parameters")
        self.audio_param_lay.setObjectName("widget-title")
        self.lay.addWidget(self.audio_param_lay)
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Parameter", "Value"])

        # scsynth path
        self.scsynth_path_lbl = QLabel("Scsynth Path")
        self.scsynth_path_lbl.setObjectName("widget-param")
        self.scsynth_path = QLineEdit()
        self.scsynth_path.returnPressed.connect(self.change_scsynth_path)
        self.table.insertRow(0)
        self.table.setCellWidget(0, 0, self.scsynth_path_lbl)
        self.table.setCellWidget(0, 1, self.scsynth_path)

        # synthdef path
        self.synthdef_path_lbl = QLabel("SynthDef Path")
        self.synthdef_path_lbl.setObjectName("widget-param")
        self.synthdef_path = QLineEdit()
        self.synthdef_path.returnPressed.connect(self.change_synthdef_path)
        self.table.insertRow(1)
        self.table.setCellWidget(1, 0, self.synthdef_path_lbl)
        self.table.setCellWidget(1, 1, self.synthdef_path)

        # recording path
        self.recording_path_lbl = QLabel("Recording Path")
        self.recording_path_lbl.setObjectName("widget-param")
        self.recording_path = QLineEdit()
        self.recording_path.returnPressed.connect(self.change_recording_path)
        self.table.insertRow(1)
        self.table.setCellWidget(1, 0, self.recording_path_lbl)
        self.table.setCellWidget(1, 1, self.recording_path)

        # audio device
        self.ad_lbl = QLabel("Audio Device")
        self.ad_lbl.setObjectName("widget-param")
        self.ad = QPushButton()
        self.ad_menu = QMenu()
        self.audio_devices = sd.query_devices()
        self.audio_devices = [f'{self.audio_devices[i]["name"]} -> max_input_channels: {self.audio_devices[i]["max_input_channels"]}, max_output_channels: {self.audio_devices[i]["max_output_channels"]}' for i in range(len(self.audio_devices))]
        for ad in self.audio_devices:
            action = QAction(ad, self)
            action.triggered.connect(lambda checked, text=ad: self.change_audio_device(text))
            self.ad_menu.addAction(action)
        self.ad.setMenu(self.ad_menu)
        self.table.insertRow(2)
        self.table.setCellWidget(2, 0, self.ad_lbl)
        self.table.setCellWidget(2, 1, self.ad)

        # sample rate
        self.sr_lbl = QLabel("Sample Rate")
        self.sr_lbl.setObjectName("widget-param")
        self.sr = QLineEdit()
        self.sr.returnPressed.connect(self.change_samplerate)
        self.table.insertRow(3)
        self.table.setCellWidget(3, 0, self.sr_lbl)
        self.table.setCellWidget(3, 1, self.sr)

        # block size
        self.bs_lbl = QLabel("Block Size")
        self.bs_lbl.setObjectName("widget-param")
        self.bs = QLineEdit()
        self.bs.returnPressed.connect(self.change_block_size)
        self.table.insertRow(4)
        self.table.setCellWidget(4, 0, self.bs_lbl)
        self.table.setCellWidget(4, 1, self.bs)

        # Hardware buffer size
        self.hbs_lbl = QLabel("Hardware Buffer Size")
        self.hbs_lbl.setObjectName("widget-param")
        self.hbs = QLineEdit()
        self.hbs.returnPressed.connect(self.change_hardware_buffer_size)
        self.table.insertRow(5)
        self.table.setCellWidget(5, 0, self.hbs_lbl)
        self.table.setCellWidget(5, 1, self.hbs)

        self.apply = QPushButton("Apply Changes")
        self.apply.setObjectName("widget-param")
        self.apply.clicked.connect(self.apply_changes)
        self.lay.addWidget(self.table)
        self.lay.addWidget(self.apply)
        self.setLayout(self.lay)
        self.read_config()

    def reset_values(self):
        self.scsynth_path.setText(self.config.get("SCSYNTH", "scsynth_path"))
        self.synthdef_path.setText(self.config.get("SCSYNTH", "synthdef_path"))
        self.sr.setText(self.config.get("SCSYNTH", "sample_rate"))
        self.ad.setText(self.config.get("SCSYNTH", "hardware_device_name").replace('"', ''))
        self.bs.setText(self.config.get("SCSYNTH", "block_size").replace('"', ''))
        self.hbs.setText(self.config.get("SCSYNTH", "hardware_buffer_size").replace('"', ''))

    def read_config(self):
        self.config = cp.ConfigParser()
        self.config.read('config.ini')
        self.reset_values()

    def change_scsynth_path(self):
        self.config.set("SCSYNTH", "scsynth_path", self.scsynth_path.text())
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)
        self.read_config()

    def change_synthdef_path(self):
        self.config.set("SCSYNTH", "synthdef_path", self.synthdef_path.text())
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)
        self.read_config()

    def change_recording_path(self):
        self.config.set("SCSYNTH", "recording_path", self.recording_path.text())
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)
        self.read_config()

    def change_audio_device(self, device):
        self.ad.setText(device.split(" ->")[0])
        in_ch = device.split("max_input_channels: ")[1].split(",")[0]
        out_ch = device.split("max_output_channels: ")[1]
        self.config.set("SCSYNTH", "num_hw_in", str(in_ch))
        self.config.set("SCSYNTH", "num_hw_out", str(out_ch))
        self.config.set("SCSYNTH", "hardware_device_name", '"'+device.split(" ->")[0]+'"')
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)
        self.read_config()

    def change_samplerate(self):
        self.config.set("SCSYNTH", "sample_rate", self.sr.text())
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)
        self.read_config()

    def change_hardware_buffer_size(self):
        self.config.set("SCSYNTH", "hardware_buffer_size", self.hbs.text())
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)
        self.read_config()

    def change_block_size(self):
        self.config.set("SCSYNTH", "block_size", self.bs.text())
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)
        self.read_config()

    def apply_changes(self):
        self.change_samplerate()
        self.change_block_size()
        self.change_hardware_buffer_size()
        self.change_scsynth_path()
        self.change_synthdef_path()
        self.read_config()
        scsynth.start()
        self.main_window.patch.reload_patch()


class MIDISettings(QWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.config = cp.ConfigParser()
        self.config.read('config.ini')
        self.lay = QVBoxLayout()

        self.midiins = rtmidi.RtMidiIn()
        self.midiins_lbl = QLabel("MIDI Input Ports")
        self.midiins_lbl.setObjectName("widget-title")
        self.midiins = [[i, self.midiins.getPortName(i)] for i in range(self.midiins.getPortCount())]
        self.in_table = QTableWidget()
        self.in_table.setColumnCount(2)
        self.in_table.setHorizontalHeaderLabels(["Port Number", "Port Name"])
        self.in_table.setRowCount(len(self.midiins))
        print(len(self.midiins), self.midiins)
        for c in [0, 1]:
            for r in range(len(self.midiins)):
                print(r, c)
                print(r, c, self.midiins[r][c])
                self.in_table.setItem(r, c, QTableWidgetItem(str(self.midiins[r][c])))

        self.midiouts = rtmidi.RtMidiIn()
        self.midiouts_lbl = QLabel("MIDI Output Ports")
        self.midiouts_lbl.setObjectName("widget-title")
        self.midiouts = [[i, self.midiouts.getPortName(i)] for i in range(self.midiouts.getPortCount())]
        self.out_table = QTableWidget()
        self.out_table.setColumnCount(2)
        self.out_table.setHorizontalHeaderLabels(["Port Number", "Port Name"])
        self.out_table.setRowCount(len(self.midiouts))
        for c in [0, 1]:
            for r in range(len(self.midiouts)):
                self.in_table.setItem(r, c, QTableWidgetItem(str(self.midiouts[r][c])))

        self.lay.addWidget(self.midiins_lbl)
        self.lay.addWidget(self.in_table)
        self.lay.addWidget(self.midiouts_lbl)
        self.lay.addWidget(self.out_table)
        self.setLayout(self.lay)
        self.read_config()

    def read_config(self):
        self.config = cp.ConfigParser()
        self.config.read('config.ini')
        self.reset_values()

    def reset_values(self):
        pass


class ProjectSettings(QWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.patch_buffers = main_window.patch.patch_buffers
        self.region_line = main_window.timeline.region_line
        self.region_manager = main_window.region_manager
        self.midi_manager = self.main_window.context.midi_manager
        self.lay = QVBoxLayout()

        # Patch Buffers Settings
        self.pbuf_lay = QVBoxLayout()
        self.pbuf_lbl = QLabel('Patch Buffers')
        self.pbuf_lbl.setObjectName("widget-title")
        self.pbuf_lay.addWidget(self.pbuf_lbl)
        self.pbuf_tbl = QTableWidget()
        self.pbuf_tbl.setColumnCount(5)  # {bufnum, name, duration, channels, store_btn}
        self.pbuf_tbl.setHorizontalHeaderLabels(["Bufnum", "Name", "Duration", "Channels"])
        self.pbuf_lay.addWidget(self.pbuf_tbl)
        self.pbuf_btn_lay = QHBoxLayout()
        self.pbuf_add = QPushButton('+')
        self.pbuf_add.setObjectName("widget-param")
        self.pbuf_add.clicked.connect(self.add_patch_buffer_dialog)
        self.pbuf_btn_lay.addWidget(self.pbuf_add)
        self.pbuf_rmv = QPushButton('-')
        self.pbuf_rmv.setObjectName("widget-param")
        self.pbuf_rmv.clicked.connect(self.remove_buffer)
        self.pbuf_btn_lay.addWidget(self.pbuf_rmv)
        self.pbuf_lay.addLayout(self.pbuf_btn_lay)
        self.lay.addLayout(self.pbuf_lay)

        # Regions Program Changes
        self.regions_names = []
        self.midi_device_number = 0
        self.prog_to_region_thread = None
        self.regions_lay = QVBoxLayout()
        self.regions_lbl = QLabel('Regions / Program Change Mapping')
        self.regions_lbl.setObjectName("widget-title")
        self.regions_lay.addWidget(self.regions_lbl)
        # self.regions_midi_device_lay = QHBoxLayout()
        # self.regions_midi_device_lbl = QLabel("MIDI Device:")
        # self.regions_midi_device_lbl.setObjectName("widget-param")
        # self.regions_midi_device = QLineEdit("0")
        # self.regions_midi_device.setObjectName("widget-param")
        # self.regions_midi_device.textChanged.connect(self.change_regions_midi_device)
        # self.regions_midi_device_lay.addWidget(self.regions_midi_device_lbl)
        # self.regions_midi_device_lay.addWidget(self.regions_midi_device)
        # self.regions_lay.addLayout(self.regions_midi_device_lay)
        self.regions_tbl = QTableWidget()
        self.regions_tbl.setColumnCount(2)
        self.regions_tbl.setHorizontalHeaderLabels(["Region", "Program Change"])
        self.regions_tbl.cellChanged.connect(self.region_edited)
        self.regions_lay.addWidget(self.regions_tbl)
        self.lay.addLayout(self.regions_lay)

        # TimeLine Settings
        self.timeline_len_lay = QHBoxLayout()
        self.timeline_len_lbl = QLabel('Project Timeline Length:')
        self.timeline_len_lbl.setObjectName("widget-param")
        self.timeline_len = QLineEdit(str(self.main_window.timeline.getDuration()))
        self.timeline_len_valid = QDoubleValidator(0.0, 100000000000.0, 4)
        self.timeline_len.setValidator(self.timeline_len_valid)
        self.timeline_len.returnPressed.connect(self.set_timeline_len)
        self.timeline_len_lay.addWidget(self.timeline_len_lbl)
        self.timeline_len_lay.addWidget(self.timeline_len)
        self.lay.addLayout(self.timeline_len_lay)
        self.setLayout(self.lay)
        self.populate_buffers_table()
        self.populate_regions_table()

    def connect_midi_device_to_regions(self, midi_device_number):
        # TODO: Attach RegionManager device change
        print("This is the midi_device_number:", midi_device_number)

    def change_regions_midi_device(self):
        text = self.sender().text()
        try:
            midi_device_number = int(text)
            self.connect_midi_device_to_regions(midi_device_number)

        except:
            print("Bad midi device number:", text)

    def region_edited(self, row, col):
        if col == 0:  # Editing Region Name
            new_name = self.regions_tbl.item(row, col).text()
            region = self.region_line.regions[self.regions_names[row]]
            start = region["start"]
            end = region["end"]
            program = region["program"]
            del self.region_line.regions[self.regions_names[row]]
            self.region_line.regions[new_name] = {
                "name": new_name,
                "start": start,
                "end": end,
                "program": program
            }
        elif col == 1:  # Editing Region Program Change Connection
            data = self.regions_tbl.item(row, col).text()
            try:
                data = int(data)
                self.region_line.regions[self.regions_names[row]]["program"] = data
            except:
                print("Bad program number for region:", data)
        self.populate_regions_table()
        self.region_line.update()
        self.region_manager.refresh_regions()

    def populate_regions_table(self):
        self.regions_tbl.blockSignals(True)
        self.regions_names = []
        nrows = self.regions_tbl.rowCount()
        for row in reversed(range(nrows)):
            self.regions_tbl.removeRow(row)
        row = 0
        for region in self.region_line.getRegions().keys():
            self.regions_names.append(str(self.region_line.getRegions()[region]["name"]))
            self.regions_tbl.insertRow(row)
            self.regions_tbl.setItem(row, 0, QTableWidgetItem(str(self.region_line.getRegions()[region]["name"])))
            self.regions_tbl.setItem(row, 1, QTableWidgetItem(str(self.region_line.getRegions()[region]["program"])))
            row += 1
        self.regions_tbl.blockSignals(False)

    def redraw_audio_widgets(self):
        self.main_window.patch.redraw_audio_widgets()

    def set_timeline_len(self):
        seconds = float(self.timeline_len.text())
        self.main_window.timeline.setDuration(seconds)
        print(self.main_window.timeline.getDuration())

    def add_patch_buffer_dialog(self):
        dialog = AddPatchBufferDialog()
        if dialog.exec():
            print("Name:", dialog.getName(), "Duration:", dialog.getDuration(), "Channels:", dialog.getChannels())
            self.patch_buffers.addBuffer(bufnum=-1, name=dialog.getName(), duration=dialog.getDuration(), channels=dialog.getChannels())
            self.populate_buffers_table()
            self.redraw_audio_widgets()

    def remove_buffer(self):
        row = self.pbuf_tbl.currentRow()
        print("row:", row)
        if row >= 0:
            self.patch_buffers.removeBuffer(int(self.pbuf_tbl.item(row, 0).text()))
            self.pbuf_tbl.removeRow(row)
            self.redraw_audio_widgets()

    def populate_buffers_table(self):
        self.pbuf_tbl.blockSignals(True)
        nrows = self.pbuf_tbl.rowCount()
        for row in reversed(range(nrows)):
            self.pbuf_tbl.removeRow(row)
        print("self.patch_buffers.getBuffers()", self.patch_buffers.getBuffers())
        row = 0
        pbufs = self.patch_buffers.getBuffers()
        for buf in self.patch_buffers.getBuffers().keys():
            store_btn = QPushButton("Store")
            store_btn.clicked.connect(lambda state, b=buf: self.store_pbuf(state=state, buf=b))
            self.pbuf_tbl.insertRow(row)
            self.pbuf_tbl.setItem(row, 0, QTableWidgetItem(str(pbufs[buf]["bufnum"])))
            self.pbuf_tbl.setItem(row, 1, QTableWidgetItem(str(pbufs[buf]["name"])))
            self.pbuf_tbl.setItem(row, 2, QTableWidgetItem(str(pbufs[buf]["duration"])))
            self.pbuf_tbl.setItem(row, 3, QTableWidgetItem(str(pbufs[buf]["channels"])))
            self.pbuf_tbl.setCellWidget(row, 4, store_btn)
            row += 1
        self.pbuf_tbl.blockSignals(False)

    def store_pbuf(self, state, buf):
        pbufs = self.patch_buffers.getBuffers()
        print(state, buf, type(buf), pbufs)
        bufnum = pbufs[buf]["bufnum"]
        name = pbufs[buf]["name"]
        nch = " - " + str(pbufs[buf]["channels"]) + " Ch" + datetime.now().strftime("%m.%d.%Y, %H.%M.%S")
        scsynth.writeBuffer(fullpath=pbuf_path + name + nch + ".wav", bufnum=bufnum, header="wav", fmt="int16")


class AddPatchBufferDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Patch Buffer")

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QVBoxLayout()

        self.name_lay = QHBoxLayout()
        self.name_lbl = QLabel("Name:")
        self.name = QLineEdit("tmp")
        self.name_lay.addWidget(self.name_lbl)
        self.name_lay.addWidget(self.name)
        self.layout.addLayout(self.name_lay)

        self.duration_lay = QHBoxLayout()
        self.duration_lbl = QLabel("Duration (sec):")
        self.duration = QLineEdit("1.0")
        self.duration_valid = QDoubleValidator(0.0001, 1000.0, 6)
        self.duration.setValidator(self.duration_valid)
        self.duration_lay.addWidget(self.duration_lbl)
        self.duration_lay.addWidget(self.duration)
        self.layout.addLayout(self.duration_lay)

        self.channels_lay = QHBoxLayout()
        self.channels_lbl = QLabel("Channels (num):")
        self.channels = QLineEdit("1")
        self.channels_valid = QIntValidator(1, 128)
        self.channels.setValidator(self.channels_valid)
        self.channels_lay.addWidget(self.channels_lbl)
        self.channels_lay.addWidget(self.channels)
        self.layout.addLayout(self.channels_lay)

        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def getDuration(self):
        return float(self.duration.text())

    def getChannels(self):
        return int(self.channels.text())

    def getName(self):
        return self.name.text()
