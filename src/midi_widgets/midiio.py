import platform
if platform.system() == "Darwin" or platform.system() == "Windows":
    from src.primitives import *
    import src.classes as classes
else:
    from primitives import *
    import classes as classes


class MIDIIn(MIDIWidget):
    def __init__(self, server, clock, harmony_manager, parent=None, uuid=None, n_midi_in=0, n_midi_out=1, device=0):
        super().__init__(clock, harmony_manager, parent, n_midi_in=n_midi_in, n_midi_out=n_midi_out, uuid=uuid)
        self.device = device
        self.patch_area = parent
        self.context = self.patch_area.context
        self.midi_manager = self.context.midi_manager
        # self.midiin = classes.MidiInput(self.device, self)
        # self.midiin.start()
        self.lay = QVBoxLayout()
        self.name = QLabel("MIDI Input")
        self.name.setObjectName("widget-title")
        self.lay.addWidget(self.name)
        self.device_lay = QHBoxLayout()
        self.device_lbl = QLabel("Device:")
        self.device_lbl.setObjectName("widget-param")
        self.device_lay.addWidget(self.device_lbl)
        self.set_device = QLineEdit()
        self.set_device.setObjectName("widget-param")
        self.set_device.setText(str(self.device))
        self.device_validator = QIntValidator(0, 16)
        self.set_device.setValidator(self.device_validator)
        self.set_device.textChanged.connect(self.reconnectDevice)
        self.device_lay.addWidget(self.set_device)
        self.lay.addLayout(self.device_lay)
        self.setLayout(self.lay)

        self.reconnectDevice(self.device)
        # c_print("cyan", "MIDI In Thread Started Successfully")

    def getDevice(self):
        return self.device

    def reconnectDevice(self, device):
        self.midi_manager.unregister_widget(self)
        self.device = device
        self.midi_manager.register_widget(self)
        # for thread in self.midi_manager.midi_in_threads:
        #     thread.removeListener(self)
        #     print("LEN", len(self.midi_manager.midi_in_threads) - 1, int(device))
        # max_connected_device = min(len(self.midi_manager.midi_in_threads) - 1, int(device))
        # print(f"max_connected_device (min between {len(self.midi_manager.midi_in_threads) - 1} and {int(device)}): {max_connected_device}")
        # print(f"He is (device {self.device}): {self.midi_manager.midi_in_threads[max_connected_device]}; midi_manager there is: {self.midi_manager}")
        # self.midi_manager.midi_in_threads[max_connected_device].addListener(self)

    def __getstate__(self):
        d = super().__getstate__()
        d.update({
            "device": self.device
        })
        # print(f"EHI I'm saving the device as {self.device}")
        return d

    def __setstate__(self, state):
        # print(f"EHI setting device to {state['device']}")
        super().__setstate__(state)
        self.device = state["device"]
        self.set_device.setText(str(self.device))
        self.reconnectDevice(self.device)


class MIDICCTest(MIDIWidget):
    def __init__(self, server, clock, harmony_manager, parent=None, uuid=None, n_midi_in=0, n_midi_out=1, device=0):
        super().__init__(clock, harmony_manager, parent, n_midi_in=n_midi_in, n_midi_out=n_midi_out, uuid=uuid)
        self.num = 0
        self.val = 127
        self.lay = QVBoxLayout()
        self.name = QLabel("Send MIDI CC")
        self.name.setObjectName("widget-title")
        self.lay.addWidget(self.name)

        self.num_lay = QHBoxLayout()
        self.num_lbl = QLabel("CC Number:")
        self.num_lbl.setObjectName("widget-param")
        self.num_lay.addWidget(self.num_lbl)
        self.num_val = QLineEdit()
        self.num_val.setObjectName("widget-param")
        self.num_val.setText(str(self.num))
        self.from_validator = QIntValidator(0, 127)
        self.num_val.setValidator(self.from_validator)
        self.num_val.textChanged.connect(self.set_num)
        self.num_lay.addWidget(self.num_val)
        self.lay.addLayout(self.num_lay)

        self.val_lay = QHBoxLayout()
        self.val_lbl = QLabel("CC Value:")
        self.val_lbl.setObjectName("widget-param")
        self.val_lay.addWidget(self.val_lbl)
        self.val_val = QLineEdit()
        self.val_val.setObjectName("widget-param")
        self.val_val.setText(str(self.val))
        self.val_validator = QIntValidator(0, 127)
        self.val_val.setValidator(self.val_validator)
        self.val_val.textChanged.connect(self.set_val)
        self.val_lay.addWidget(self.val_val)
        self.lay.addLayout(self.val_lay)

        self.send_cc = QPushButton("Send CC")
        self.send_cc.setObjectName("widget-param")
        self.send_cc.clicked.connect(self.propagateRTCC)
        self.lay.addWidget(self.send_cc)

        self.setLayout(self.lay)

    def set_num(self):
        val = int(float(self.sender().text()))
        self.num = val

    def set_val(self):
        val = int(float(self.sender().text()))
        self.val = val

    def propagateRTCC(self):
        print("Clicking...")
        super().propagateRTCC(self.num, self.val)

    def __getstate__(self):
        d = super().__getstate__()
        d.update({
            "num": self.num,
            "val": self.val
        })
        return d

    def __setstate__(self, state):
        super().__setstate__(state)
        self.num = state["num"]
        self.val = state["val"]


class MIDINoteTest(MIDIWidget):
    def __init__(self, server, clock, harmony_manager, parent=None, uuid=None, n_midi_in=0, n_midi_out=1, device=0):
        super().__init__(clock, harmony_manager, parent, n_midi_in=n_midi_in, n_midi_out=n_midi_out, uuid=uuid)
        self.num = 20
        self.val = 100
        self.lay = QVBoxLayout()
        self.name = QLabel("Send MIDI Note")
        self.name.setObjectName("widget-title")
        self.lay.addWidget(self.name)

        self.num_lay = QHBoxLayout()
        self.num_lbl = QLabel("Note Number:")
        self.num_lbl.setObjectName("widget-param")
        self.num_lay.addWidget(self.num_lbl)
        self.num_val = QLineEdit()
        self.num_val.setObjectName("widget-param")
        self.num_val.setText(str(self.num))
        self.from_validator = QIntValidator(0, 127)
        self.num_val.setValidator(self.from_validator)
        self.num_val.textChanged.connect(self.set_num)
        self.num_lay.addWidget(self.num_val)
        self.lay.addLayout(self.num_lay)

        self.val_lay = QHBoxLayout()
        self.val_lbl = QLabel("Note Velocity:")
        self.val_lbl.setObjectName("widget-param")
        self.val_lay.addWidget(self.val_lbl)
        self.val_val = QLineEdit()
        self.val_val.setObjectName("widget-param")
        self.val_val.setText(str(self.val))
        self.val_validator = QIntValidator(0, 127)
        self.val_val.setValidator(self.val_validator)
        self.val_val.textChanged.connect(self.set_val)
        self.val_lay.addWidget(self.val_val)
        self.lay.addLayout(self.val_lay)

        self.send_lay = QHBoxLayout()
        self.send_cc = QPushButton("Send Note")
        self.send_cc.setObjectName("widget-param")
        self.send_cc.clicked.connect(self.propagateRTMIDINote)
        self.send_lay.addWidget(self.send_cc)
        self.clear_notes = QPushButton("Clear Notes")
        self.clear_notes.setObjectName("widget-param")
        self.clear_notes.clicked.connect(self.propagateRTMIDINoteClear)
        self.send_lay.addWidget(self.clear_notes)
        self.lay.addLayout(self.send_lay)

        self.setLayout(self.lay)

    def set_num(self):
        val = int(float(self.sender().text()))
        self.num = val

    def set_val(self):
        val = int(float(self.sender().text()))
        self.val = val

    def propagateRTMIDINote(self):
        super().propagateRTMIDINote(self.num, self.val)

    def propagateRTMIDINoteClear(self):
        for i in range(127):
            super().propagateRTMIDINote(i, 0)

    def __getstate__(self):
        d = super().__getstate__()
        d.update({
            "num": self.num,
            "val": self.val
        })
        return d

    def __setstate__(self, state):
        super().__setstate__(state)
        self.num = state["num"]
        self.val = state["val"]


class MIDIMessageLogger(MIDIWidget):
    def __init__(self, server, clock, harmony_manager, parent=None, uuid=None, n_midi_in=1, n_midi_out=0, device=0):
        super().__init__(clock, harmony_manager, parent, n_midi_in=n_midi_in, n_midi_out=n_midi_out, uuid=uuid)
        self.lay = QVBoxLayout()
        self.name = QLabel("MIDI Message Logger")
        self.name.setObjectName("widget-title")
        self.lay.addWidget(self.name)
        self.setLayout(self.lay)

    def propagateRTProgramChange(self, num):
        c_print("green", f"MIDIMessageLogger:: RT MIDI Program Change {num}")

    def propagateRTMIDINote(self, note, velocity):
        c_print("green", f"MIDIMessageLogger:: RT MIDI Note Number {note} -> Velocity: {velocity}")

    def propagateMIDINote(self, note):
        c_print("green", f"MIDIMessageLogger:: MIDI Note {note}")

    def propagateRTCC(self, num, value):
        c_print("green", f"MIDIMessageLogger:: RT MIDI Control Change Number {num} -> Value: {value}")

    def __getstate__(self):
        d = super().__getstate__()
        return d

    def __setstate__(self, state):
        super().__setstate__(state)
