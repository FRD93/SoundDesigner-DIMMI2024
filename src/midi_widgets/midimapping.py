import platform
if platform.system() == "Darwin" or platform.system() == "Windows":
    from src.primitives import *
    import src.classes as classes
else:
    from primitives import *
    import classes as classes


class MIDICCMap(MIDIWidget):
    def __init__(self, server, clock, harmony_manager, parent=None, uuid=None, n_midi_in=1, n_midi_out=1, device=0):
        super().__init__(clock, harmony_manager, parent, n_midi_in=n_midi_in, n_midi_out=n_midi_out, uuid=uuid)
        self.from_ = 0.0
        self.to_ = 127.0
        self.lay = QVBoxLayout()
        self.name = QLabel("Map MIDI CC Value")
        self.name.setObjectName("widget-title")
        self.lay.addWidget(self.name)

        self.from_lay = QHBoxLayout()
        self.from_lbl = QLabel("Minimum Value:")
        self.from_lbl.setObjectName("widget-param")
        self.from_lay.addWidget(self.from_lbl)
        self.from_val = QLineEdit()
        self.from_val.setObjectName("widget-param")
        self.from_val.setText(str(self.from_))
        self.from_validator = QDoubleValidator(-20000.0, 20000.0, 6)
        self.from_val.setValidator(self.from_validator)
        self.from_val.textChanged.connect(self.set_from)
        self.from_lay.addWidget(self.from_val)
        self.lay.addLayout(self.from_lay)

        self.to_lay = QHBoxLayout()
        self.to_lbl = QLabel("Maximum Value:")
        self.to_lbl.setObjectName("widget-param")
        self.to_lay.addWidget(self.to_lbl)
        self.to_val = QLineEdit()
        self.to_val.setObjectName("widget-param")
        self.to_val.setText(str(self.to_))
        self.to_validator = QDoubleValidator(-20000.0, 20000.0, 6)
        self.to_val.setValidator(self.to_validator)
        self.to_val.textChanged.connect(self.set_to)
        self.to_lay.addWidget(self.to_val)
        self.lay.addLayout(self.to_lay)

        self.setLayout(self.lay)

    def set_from(self):
        val = float(self.sender().text())
        self.from_ = val

    def set_to(self):
        val = float(self.sender().text())
        self.to_ = val

    def propagateRTCC(self, num, value):
        print(f"val {value}, -> from {self.from_} to {self.to_}")
        value = ((value / 127.) * (self.to_ - self.from_)) + self.from_
        print("New value:", value)
        super().propagateRTCC(num, value)

    def __getstate__(self):
        d = super().__getstate__()
        d.update({
            "from_": self.from_,
            "to_": self.to_
        })
        return d

    def __setstate__(self, state):
        super().__setstate__(state)
        self.from_ = state["from_"]
        self.to_ = state["to_"]
        self.from_val.setText(str(self.from_))
        self.to_val.setText(str(self.to_))


class MIDINoteTranspose(MIDIWidget):
    def __init__(self, server, clock, harmony_manager, parent=None, uuid=None, n_midi_in=1, n_midi_out=1, device=0):
        super().__init__(clock, harmony_manager, parent, n_midi_in=n_midi_in, n_midi_out=n_midi_out, uuid=uuid)
        self.transpose = 0
        self.lay = QVBoxLayout()
        self.name = QLabel("Transpose MIDI Note")
        self.name.setObjectName("widget-title")
        self.lay.addWidget(self.name)

        self.from_lay = QHBoxLayout()
        self.from_lbl = QLabel("Transpose:")
        self.from_lbl.setObjectName("widget-param")
        self.from_lay.addWidget(self.from_lbl)
        self.from_val = QLineEdit()
        self.from_val.setObjectName("widget-param")
        self.from_val.setText(str(self.transpose))
        self.from_validator = QIntValidator(-127, 127)
        self.from_val.setValidator(self.from_validator)
        self.from_val.textChanged.connect(self.set_transpose)
        self.from_lay.addWidget(self.from_val)
        self.lay.addLayout(self.from_lay)

        self.setLayout(self.lay)

    def set_transpose(self):
        try:
            val = int(self.sender().text())
            self.transpose = val
        except ValueError:
            print(f"Invalid value:{self.sender().text()}")

    def set_to(self):
        val = float(self.sender().text())
        self.to_ = val

    def propagateRTMIDINote(self, note, value):
        print("MIDI Note before transpose:", note, "transpose:", self.transpose)
        note += self.transpose
        if note < 0:
            note = 0
        if note > 127:
            note = 127
        print("MIDI Note after transpose:", note)
        super().propagateRTMIDINote(note, value)

    def __getstate__(self):
        d = super().__getstate__()
        d.update({
            "transpose": self.transpose,
        })
        return d

    def __setstate__(self, state):
        super().__setstate__(state)
        self.transpose = state["transpose"]
        self.from_val.setText(str(self.transpose))
