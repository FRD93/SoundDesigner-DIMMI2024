import platform
if platform.system() == "Darwin" or platform.system() == "Windows":
    from src.primitives import *
    import src.classes as classes
else:
    from primitives import *
    import classes as classes


class MIDIClipPlayer(MIDIWidget):
    def __init__(self, server, clock, harmony_manager, midi_folder="/", parent=None, uuid=None, n_midi_in=0, n_midi_out=1):
        super().__init__(clock, harmony_manager, parent, n_midi_in=n_midi_in, n_midi_out=n_midi_out, uuid=uuid)
        self.instr_path = SCSYNTH_SYNTHDEF_PATH
        self.server = server
        self.folder = midi_folder
        self.midi_file_name = None
        self.midi_clip = None
        self.midi_clip_player = classes.MIDIClipPlayer(midiclip=self.midi_clip, clock=self.clock.clock, widget=self, server=self.server, loop=False)

        # select midi file menu
        self.select_midi_clip_butt = QPushButton(text="Apri cartella ->")
        self.select_midi_clip_butt.setObjectName("widget-param")
        self.select_midi_clip_menu = QMenu()
        self.select_midi_clip_butt.setMenu(self.select_midi_clip_menu)
        # set midi folder button
        self.set_folder_butt = QPushButton()
        self.set_folder_butt.setObjectName("widget-param")
        self.set_folder_icon = QIcon("./img/folder.svg")
        self.set_folder_butt.setIcon(self.set_folder_icon)
        self.set_folder_butt.setIconSize(QSize(10, 10))
        self.set_folder_butt.setToolTip("Apri cartella MIDI")
        self.set_folder_butt.clicked.connect(self.open_folder)
        # set tonality
        self.set_tonality_butt = QPushButton(text="<---")
        self.set_tonality_butt.setObjectName("widget-param")
        self.set_tonality_menu = QMenu()
        self.set_tonality_butt.setMenu(self.set_tonality_menu)
        # set instrument
        self.set_instr_lbl = QLabel("Scegli strumento:")
        self.set_instr_lbl.setObjectName("widget-param")
        self.set_instr_butt = QPushButton(text=self.midi_clip_player.instr)
        self.set_instr_butt.setObjectName("widget-param")
        self.set_instr_menu = QMenu()
        self.set_instr_butt.setMenu(self.set_instr_menu)
        # set start measure
        self.set_measure_lbl = QLabel("Misura di inizio:")
        self.set_measure_lbl.setObjectName("widget-param")
        self.set_measure_spin = QSpinBox()
        self.set_measure_spin.setObjectName("widget-param")
        self.set_measure_spin.setRange(0, 100000)
        self.set_measure_spin.setValue(0)
        self.set_measure_spin.valueChanged.connect(self.setStartMeasure)
        # allow to play
        self.allow_to_play_check = QCheckBox("Abilita Play")
        # if self.midi_clip_player.midiclip is None:
        #     self.allow_to_play_check.setCheckable(False)
        self.allow_to_play_check.toggled.connect(self.allow_to_play)
        # loop
        self.loop_check = QCheckBox("Loop")
        self.loop_check.toggled.connect(self.set_loop)

        self.lbl = QLabel("MIDIClipPlayer")
        self.lbl.setObjectName("widget-title")
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.row1 = QHBoxLayout()
        self.row1.setSpacing(0)
        self.row1.addWidget(self.select_midi_clip_butt)
        self.row1.addWidget(self.set_folder_butt)
        self.row1.addWidget(self.set_tonality_butt)

        self.row2 = QHBoxLayout()
        self.row2.setSpacing(0)
        self.row2.addWidget(self.set_instr_lbl)
        self.row2.addWidget(self.set_instr_butt)

        self.row3 = QHBoxLayout()
        self.row3.setSpacing(0)
        self.row3.addWidget(self.set_measure_lbl)
        self.row3.addWidget(self.set_measure_spin)
        self.row3.addWidget(self.allow_to_play_check)
        self.row3.addWidget(self.loop_check)

        self.lay = QVBoxLayout()
        self.lay.setSpacing(0)
        self.lay.addWidget(self.lbl)
        self.lay.addLayout(self.row1)
        # self.lay.addLayout(self.row2)  # Disabilitato "Scegli strumento"
        self.lay.addLayout(self.row3)

        self.setLayout(self.lay)

        self.reset_tonalities()
        self.reset_instr_menu()

    def process_tick(self, tick):
        # if tick == 0:
        #     c_print("green", f"Processing tick in MIDIClipPlayer(MIDIWidget) {self.uuid}")
        self.midi_clip_player.process_tick(tick)

    def setStartMeasure(self, value):
        value = int(value)
        # print("Setting MIDIClipPlayer's MIDIClip start measure to:", value)
        self.set_measure_spin.setValue(value)
        self.midi_clip_player.setStartMeasure(value)

    def getStartMeasure(self):
        self.midi_clip_player.getStartMeasure()

    def set_loop(self):
        if self.loop_check.isChecked():
            print("Setting loop to True")
            self.midi_clip_player.setLoop(True)
        else:
            print("Setting loop to False")
            self.midi_clip_player.setLoop(False)

    def allow_to_play(self):
        # print("Checking Allow To Play...")
        if self.allow_to_play_check.isChecked():
            # print("\tPlay Allowed")
            self.midi_clip_player.play()
        else:
            # print("\tPlay Denied")
            self.midi_clip_player.stop()

    def reset_tonalities(self):
        self.set_tonality_menu.clear()
        for note in range(-5, 7, 1):
            self.set_tonality_menu.addAction(functions.note2KeySig(note), self.change_key)

    def change_key(self):
        key = self.sender().text()
        note = functions.keySig2Fund(key)
        self.set_tonality_butt.setText(key)
        try:
            self.midi_clip_player.midiclip.setKey(note)
        except:
            print("Select a MIDIClip first!")

    def set_key(self, key):
        note = functions.keySig2Fund(key)
        self.set_tonality_butt.setText(key)
        try:
            self.midi_clip_player.midiclip.setKey(note)
        except:
            print("Select a MIDIClip first!")

    def get_key(self):
        return self.set_tonality_butt.text()

    def reset_instr_menu(self):
        self.set_instr_menu.clear()
        for f in os.listdir(self.instr_path):
            if ".scsyndef" in f:
                self.set_instr_menu.addAction(os.path.splitext(f)[0], self.change_instr)

    def change_instr(self):
        instr = self.sender().text()
        self.midi_clip_player.setInstr(instr)
        self.set_instr_butt.setText(instr)

    def set_instr(self, instr):
        print("Setting instrument to:", instr)
        self.midi_clip_player.setInstr(instr)
        self.set_instr_butt.setText(instr)

    def get_instr(self):
        return self.set_instr_butt.text()

    def reset_midi_clip_menu(self):
        self.select_midi_clip_menu.clear()
        if os.path.exists(self.folder):
            for f in os.listdir(self.folder):
                if f.lower().endswith(".mid"):
                    print("Adding file midi:", f)
                    self.select_midi_clip_menu.addAction(os.path.splitext(f)[0], self.open_midi_clip)
        self.select_midi_clip_butt.setText("Scegli un file")
        self.set_tonality_butt.setText("")

    def set_midi_clip(self, fname):
        if fname is not None:
            self.midi_file_name = fname
            print("fname:", fname)
            print("folder:", self.folder)
            fullpath = ""
            for f in os.listdir(self.folder):
                if fname in f and ".mid" in f.lower():
                    fullpath = self.folder + "/" + f
            print("fullpath:", fullpath)
            self.midi_clip = classes.MIDIClip(path=fullpath, transpose_to_C=False)
            self.midi_clip_player.setMIDIClip(self.midi_clip)
            self.select_midi_clip_butt.setText(fname)
            self.allow_to_play_check.setCheckable(True)
            if self.harmony_manager.isTonalityLocked():
                self.midi_clip_player.midiclip.setKey(self.harmony_manager.getNote())
            self.set_tonality_butt.setText(functions.note2KeySig(self.midi_clip_player.midiclip.getKey()))
        else:
            pass

    def open_midi_clip(self):
        fname = self.sender().text()
        self.midi_file_name = fname
        print("fname:", fname)
        print("folder:", self.folder)
        fullpath = ""
        for f in os.listdir(self.folder):
            if fname in f and ".mid" in f.lower():
                fullpath = self.folder + "/" + f
        print("fullpath:", fullpath)
        self.midi_clip = classes.MIDIClip(path=fullpath, transpose_to_C=False)
        self.midi_clip_player.setMIDIClip(self.midi_clip)
        self.select_midi_clip_butt.setText(fname)
        self.allow_to_play_check.setCheckable(True)
        if self.harmony_manager.isTonalityLocked():
            self.midi_clip_player.midiclip.setKey(self.harmony_manager.getNote())
        self.set_tonality_butt.setText(functions.note2KeySig(self.midi_clip_player.midiclip.getKey()))

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(None, 'Apri cartella', '/Users/admin/Music/midi_files/grieg')
        self.set_folder(folder)

    def set_folder(self, folder):
        self.folder = folder
        if os.path.exists(self.folder):
            self.reset_midi_clip_menu()

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
        d = super().__getstate__()
        d.update({
            "uuid": self.uuid,
            "midi_folder": self.folder,
            "midi_file": self.midi_file_name,
            "loop": self.loop_check.isChecked(),
            "play": self.allow_to_play_check.isChecked(),
            "start_measure": self.midi_clip_player.getStartMeasure(),
            "key": self.get_key(),
            "instrument": self.get_instr(),
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height()
        })
        print("MIDIClipPlayer state:", d)
        return d

    def __setstate__(self, state):
        super().__setstate__(state)
        # UUID
        self.uuid = state["uuid"]
        # Set Geometry
        self.setGeometry(state["x"], state["y"], state["width"], state["height"])
        # Setta Folder MIDI
        self.set_folder(state["midi_folder"])
        # Resetta Menu Selezione File MIDI
        self.reset_midi_clip_menu()
        # Setta il File MIDI precedentemente selezionato
        self.set_midi_clip(state["midi_file"])
        self.select_midi_clip_butt.setText(self.midi_file_name)
        # Ricrea il MIDIClipPlayer
        start_tick = int(PPQN * 4 * float(state["start_measure"]))
        self.midi_clip_player = classes.MIDIClipPlayer(midiclip=self.midi_clip, clock=self.clock.clock, server=self.server, loop=self.loop_check, start_tick=start_tick, widget=self)
        # self.midi_clip_player.recalcNotes()
        # Setta Tonalità
        self.set_key(state["key"])
        # Setta Strumento
        self.set_instr(state["instrument"])
        # Setta Play, Loop, Misura di Inizio
        self.loop_check.setChecked(state["loop"])
        self.set_loop()
        self.allow_to_play_check.setChecked(state["play"])
        self.setStartMeasure(state["start_measure"])
