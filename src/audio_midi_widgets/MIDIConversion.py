import platform
if platform.system() == "Darwin" or platform.system() == "Windows":
    from src.primitives import *
    import src.classes as classes
else:
    from primitives import *
    import classes as classes


class MIDICCToSignal(AudioMIDIWidget):
    def __init__(self, server, clock, harmony_manager, parent=None, uuid=None, n_audio_in=0, n_audio_out=1, n_midi_in=1, n_midi_out=0, synth_name="MIDICCToSignal",
                 synth_args=None):
        super().__init__(server=server, clock=clock, harmony_manager=harmony_manager, parent=parent, uuid=uuid, n_audio_in=n_audio_in, n_audio_out=n_audio_out, n_midi_in=n_midi_in, n_midi_out=n_midi_out, synth_name=synth_name, synth_args=synth_args)
        self.midi_cc = 0
        self.value = 0
        self.min = 0.0
        self.max = 20000.0
        # print("self.output_channels[0] at init is:", self.output_channels[0])
        self.synth = Synth(self.server, self.synth_name, node=None,
                           args=["out_ch_0", self.output_channels[0], "value", self.value],
                           addAction="head", targetID=self.group.getNodeID())
        self.old_synth = -1
        self.old_synths = []

        self.lay = QVBoxLayout()
        # self.name = QLabel("MIDI CC To Signal")
        # self.name.setObjectName("widget-title")
        # self.lay.addWidget(self.name)
        self.ch_lay = QHBoxLayout()
        self.ch_lbl = QLabel("CC Number:")
        self.ch_lbl.setObjectName("widget-param")
        self.ch_lay.addWidget(self.ch_lbl)
        self.set_ch = QLineEdit()
        self.set_ch.setObjectName("widget-param")
        self.set_ch.setText(str(self.midi_cc))
        self.device_validator = QIntValidator(0, 16)
        self.set_ch.setValidator(self.device_validator)
        self.set_ch.textChanged.connect(self.set_cc_number)
        self.ch_lay.addWidget(self.set_ch)

        self.min_lay = QHBoxLayout()
        self.min_lbl = QLabel("Min Value:")
        self.min_lbl.setObjectName("widget-param")
        self.min_lay.addWidget(self.min_lbl)
        self.set_min = QLineEdit()
        self.set_min.setObjectName("widget-param")
        self.set_min.setText(str(self.min))
        self.min_validator = QDoubleValidator(-20000.0, 20000.0, 6)
        self.set_min.setValidator(self.min_validator)
        self.set_min.textChanged.connect(self.set_min_value)
        self.min_lay.addWidget(self.set_min)

        self.max_lay = QHBoxLayout()
        self.max_lbl = QLabel("Max Value:")
        self.max_lbl.setObjectName("widget-param")
        self.max_lay.addWidget(self.max_lbl)
        self.set_max = QLineEdit()
        self.set_max.setObjectName("widget-param")
        self.set_max.setText(str(self.max))
        self.max_validator = QDoubleValidator(-20000.0, 20000.0, 6)
        self.set_max.setValidator(self.max_validator)
        self.set_max.textChanged.connect(self.set_max_value)
        self.max_lay.addWidget(self.set_max)

        self.lay.addLayout(self.ch_lay)
        self.lay.addLayout(self.min_lay)
        self.lay.addLayout(self.max_lay)
        self.layout().addLayout(self.lay)

        self.initArgs()

    def freeSynth(self):
        self.synth.free()

    def set_cc_number(self):
        try:
            self.midi_cc = int(self.sender().text())
        except:
            pass

    def set_min_value(self):
        val = self.sender().text()
        val = val.replace(",", ".").replace("E+", "e")
        # print("Setting min value to", val)
        self.min = float(val)

    def set_max_value(self):
        val = self.sender().text()
        val = val.replace(",", ".").replace("E+", "e")
        # print("Setting max value to", val)
        self.max = float(val)

    def processRTMIDINote(self, note, velocity):
        pass

    def processRTCC(self, num, value):
        # print("RT CC Found!", num, value)
        if num == self.midi_cc:
            self.value = float(value) * (self.max - self.min) / 127. + self.min
            self.old_synth = self.synth
            self.old_synths.append(self.synth.node)
            if self.min <= self.value <= self.max:
                self.synth = Synth(self.server, self.synth_name, node=None, args=["out_ch_0", self.bus.getChan(0), "value", self.value], addAction="tail", targetID=self.group.getNodeID())
                self.old_synth.free()
            self.server.dumpNodeTree()

    def __getstate__(self):
        d = super().__getstate__()
        d.update({
            "uuid": self.uuid,
            "midi_cc": self.midi_cc,
            "value": self.value,
            "min": self.min,
            "max": self.max
        })
        return d

    def __setstate__(self, state):
        super().__setstate__(state)
        # UUID
        self.uuid = state["uuid"]
        self.midi_cc = state["midi_cc"]
        self.value = state["value"]
        self.min = state["min"]
        self.max = state["max"]
        self.set_ch.setText(str(self.midi_cc))
        self.set_min.setText(str(self.min))
        self.set_max.setText(str(self.max))
        # Set Geometry
        self.setGeometry(state["x"], state["y"], state["width"], state["height"])


class AudioTrigToMIDINoteOn(AudioMIDIWidget):
    def __init__(self, server, clock, harmony_manager, parent=None, uuid=None, n_audio_in=0, n_audio_out=0, n_midi_in=0, n_midi_out=1, synth_name=None, synth_args=None):
        super().__init__(server=server, clock=clock, harmony_manager=harmony_manager, parent=parent, uuid=uuid, n_audio_in=n_audio_in, n_audio_out=n_audio_out, n_midi_in=n_midi_in, n_midi_out=n_midi_out, synth_name="TrigReply", synth_args={"a_tfreq": {"desc": "Frequency (Hz)", "type": "audio", "min": 0.0, "max": 1000, "val": 1.0, "bus": -1}})
        # self.synth_args = {"a_freq": {"desc": "Frequency (Hz)", "type": "audio", "min": 0.0, "max": 1000, "val": 1.0, "bus": -1}}
        self.server.add_trigreply_widget(self)
        # print("self.output_channels[0] at init is:", self.output_channels[0])
        self.synth = Synth(self.server, self.synth_name, node=None, args=["uuid", self.uuid, "selector_tfreq", 0, "a_tfreq", self.synth_args["a_tfreq"]["val"]], addAction="head", targetID=self.group.getNodeID())

        self.lay = QVBoxLayout()
        self.layout().addLayout(self.lay)
        self.initArgs()

    def propagate_trig(self):
        for widget in self.midi_destinations:
            if hasattr(widget, "processNote"):
                widget.processNote(Note(duration=0))

    def freeSynth(self):
        self.server.remove_trigreply_widget(self)
        self.synth.free()

    def processRTMIDINote(self, note, velocity):
        pass

    def __getstate__(self):
        d = super().__getstate__()
        d.update({
            "uuid": self.uuid
        })
        return d

    def __setstate__(self, state):
        super().__setstate__(state)
        # UUID
        self.uuid = state["uuid"]
        # Set Geometry
        self.setGeometry(state["x"], state["y"], state["width"], state["height"])
        self.computeSynthArgs()
