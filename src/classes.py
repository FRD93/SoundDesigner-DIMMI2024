"""@package classes
Documentazione delle varie classi
"""
from PyQt6.QtCore import QThread, pyqtSignal, QObject, QMutex, QWaitCondition, Qt, QCoreApplication, QEventLoop, QEvent, QTimer
import ms3
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage
import time
from datetime import time as dtime
import numpy as np
from configparser import ConfigParser
from copy import deepcopy
import signal
from threading import Thread, Event
import sys
from PyQt6.QtWidgets import QApplication

from functions import *
from harmony import *
from supercollider import *
import threading
import re
import rtmidi
from log_coloring import c_print

"""
try:
    server = Server()
except:
    Exception("SuperColldier Server not running.......")
"""

# conf = ConfigParser()
# conf.read("config.ini")
# PPQN = conf.getint("GENERAL", "ppqn")


class ClockWorker(QObject):
    update_signal = pyqtSignal(str)

    def __init__(self, clock):
        super().__init__()
        self.running = True
        self.clock = clock

    def clock_event_thread(self):
        while self.running:
            self.update_signal.emit("High Priority Thread Started.")
            # self.clock.clock_event_thread_qt()

    def stop(self):
        self.running = False


class MIDIManager:
    def __init__(self, context):
        self.context = context
        # self.region_manager = self.context.parent.region_manager
        # self.region_line = self.context.parent.timeline.region_line
        self.midi_in_device_names = []
        self.midi_out_device_names = []
        self.midi_in_devices = []
        self.midi_out_devices = []
        self.midi_in_threads = []
        self.midi_out_threads = []
        self.midi_ins = []
        self.midi_outs = []

    def set_region_manager(self, rm):
        self.region_manager = rm

    def set_region_line(self, rl):
        self.region_line = rl

    def connectAll(self):
        self.midi_in_threads = []
        for device in self.midi_in_devices:
            # if sys.version_info <= (3, 10, 0):
            #     self.midi_ins.append(rtmidi.RtMidiIn(int(device)))  # Use RtMidiIn for python3.9 and MidiIn for python3.11
            # else:
            self.midi_ins.append(rtmidi.MidiIn(int(device)))
            # self.midi_ins[-1].openPort(device)
            self.midi_ins[-1].open_port(device)
            # print("Device:", device)
            self.midi_in_threads.append(MidiInput(device, self, self.region_manager, self.region_line))
            # print("Device:", device, "created")
            self.midi_in_threads[-1].start()
            # print("Device:", device, "started.")
        for device in self.midi_out_devices:
            # self.midi_outs.append(rtmidi.RtMidiOut(int(device)))
            self.midi_outs.append(rtmidi.MidiOut(int(device)))
            # self.midi_outs[-1].openPort(device)
            self.midi_outs[-1].open_port(device)

    def disconnectAll(self):
        for midiin_thread in self.midi_in_threads:
            try:
                midiin_thread.stop()
            except:
                pass
        for device in self.midi_ins:
            try:
                device.close()
            except:
                c_print("red", f"ERROR: Could not disconnect device {device} (type={type(device)})")
        for device in self.midi_outs:
            try:
                device.close()
            except:
                c_print("red", f"ERROR: Could not disconnect device {device}")

    def refreshDevices(self):
        self.disconnectAll()
        # self.midi_in_device_names = [rtmidi.RtMidiIn().getPortName(index) for index in range(rtmidi.RtMidiIn().getPortCount())]
        # self.midi_in_devices = [index for index in range(rtmidi.RtMidiIn().getPortCount())]
        # self.midi_out_device_names = [rtmidi.RtMidiOut().getPortName(index) for index in range(rtmidi.RtMidiOut().getPortCount())]
        # self.midi_out_devices = [index for index in range(rtmidi.RtMidiOut().getPortCount())]
        self.midi_in_device_names = [rtmidi.MidiIn(index) for index in range(rtmidi.MidiIn().get_port_count())]
        self.midi_in_devices = [index for index in range(rtmidi.MidiIn().get_port_count())]
        self.midi_out_device_names = [rtmidi.MidiOut(index) for index in range(rtmidi.MidiOut().get_port_count())]
        self.midi_out_devices = [index for index in range(rtmidi.MidiOut().get_port_count())]
        self.connectAll()

    def getMIDIIns(self):
        return self.midi_ins

    def getMIDIIn(self, name):
        try:
            return self.midi_ins[self.midi_in_devices.index(int(name))]
        except:
            c_print("red", f"ERROR: wrong MIDI In device name {int(name)}")
            if len(self.midi_ins) > 0:
                return self.midi_ins[-1]
            else:
                return -1

    def getMIDIOuts(self):
        return self.midi_outs

    def getMIDIOut(self, name):
        try:
            return self.midi_outs[self.midi_out_devices.index(name)]
        except:
            c_print("red", f"ERROR: wrong MIDI In device name {self.midi_out_devices.index(int(name))}")
            return -1


class MidiInput(Thread):
    def __init__(self, device, midi_manager, region_manager, region_line):
        Thread.__init__(self)
        self.stop_event = Event()
        self.setDaemon(True)
        self.device = device
        self.midi_manager = midi_manager
        self.region_manager = region_manager
        self.region_line = region_line
        self.widgets = []
        c_print("cyan", f"getting MIDI in {device}")
        self.mididev = self.midi_manager.getMIDIIn(device)
        self.running = False

    def setRegionLine(self, rl):
        self.region_line = rl

    def setRegionManager(self, rm):
        self.region_manager = rm

    def setMidiManager(self, mm):
        self.midi_manager = mm

    def addListener(self, widget):
        if not widget in self.widgets:
            self.widgets.append(widget)

    def removeListener(self, widget):
        if widget in self.widgets:
            self.widgets.remove(widget)

    def stop(self):
        self.stop_event.set()

    def run(self):
        # if type(self.mididev) == rtmidi.RtMidiIn:
        if type(self.mididev) == rtmidi.MidiIn:
            self.stop_event.clear()
            self.running = True
            while not self.stop_event.is_set():
                msg = self.mididev.get_message()
                # print(f"Widgets of device {self.device}: {self.widgets}")
                if msg:
                    # print(f"Message received from device {self.device}: {msg}")
                    if msg.isNoteOn():
                        for widget in self.widgets:
                            widget.propagateRTMIDINote(msg.getMidiNoteName(msg.getNoteNumber()), msg.getVelocity())
                        # c_print('yellow', f'RT NOTE ON: {msg.getMidiNoteName(msg.getNoteNumber()), msg.getVelocity()}')
                    elif msg.isNoteOff():
                        for widget in self.widgets:
                            widget.propagateRTMIDINote(msg.getMidiNoteName(msg.getNoteNumber()), 0)
                        # c_print('yellow', f'RT NOTE OFF: {msg.getMidiNoteName(msg.getNoteNumber())}')
                    elif msg.isController():
                        # print("MIDI Controller msg:", msg)
                        print(f"I am: {self}; midi_manager here is: {self.midi_manager}")
                        for widget in self.widgets:
                            # print("\twidget:", widget)
                            widget.propagateRTCC(msg.getControllerNumber(), msg.getControllerValue())
                        # c_print('yellow', f'RT CONTROLLER -> num: {msg.getControllerNumber()} val: {msg.getControllerValue()}')
                    elif msg.isProgramChange():
                        for widget in self.widgets:
                            widget.propagateRTProgramChange(msg.getProgramChangeNumber())
                        for key in self.region_manager.regions_buttons.keys():
                            # print(self.region_line, self.region_line.regions.keys())
                            try:
                                if int(self.region_line.regions[key]["program"]) == msg.getProgramChangeNumber():
                                    self.region_manager.regions_buttons[key].click()
                                    c_print('cyan', f'Switching to region {key}')
                            except:
                                c_print('red', f'Wrong region name: {key}')
                        # c_print('yellow', f'RT PROGRAM CHANGE -> {msg.getProgramChangeNumber()}')
        else:
            c_print('red', f'ERROR: mididev is not a RTMidiIn: {self.mididev}')


class Note:
    """
    Rappresentazione di una singola nota
    """
    def __init__(self, midi_note=60, velocity=127, start_tick=0, duration=96, chord=None, key=None, tuning=440, bpm=120):
        self.midi_note = midi_note
        self.velocity = velocity
        self.start_tick = start_tick
        self.duration = duration
        self.chord = chord
        self.key = key
        self.tuning = tuning
        self.bpm = bpm

    def setTuning(self, tuning=440):
        self.tuning = tuning

    def getNote(self):
        return self.midi_note

    def noteToFreq(self, note):
        # return (self.tuning / 32) * (2 ** ((note - 9) / 12))
        return midicps(note, self.tuning)

    def getFrequency(self):
        return self.noteToFreq(int(self.midi_note))

    def setNote(self, midi_note):
        self.midi_note = midi_note

    def getVelocity(self):
        return self.velocity

    def setVelocity(self, velocity):
        self.velocity = velocity

    def getStartTick(self):
        return self.start_tick

    def setStartTick(self, start_tick):
        self.start_tick = start_tick

    def getDuration(self):
        return self.duration

    def setDuration(self, duration):
        self.duration = duration

    def getBPM(self):
        return self.bpm

    def setBPM(self, bpm):
        self.bpm = bpm

    def getChord(self):
        return self.chord

    def setChord(self, chord):
        self.chord = chord

    def getKey(self):
        return self.key

    def setKey(self, key):
        self.key = key

    def describe(self):
        print("Note:", midiToNote(self.getNote()), "(n=" + str(self.getNote()) + ")")
        print("\tStartTick:", self.getStartTick())
        print("\tDuration:", self.getDuration())
        print("\tChord:", self.getChord())
        print("\tKey:", self.getKey())

    def tokenize(self, encode_start_time=False, encode_velocity=False, encode_chord=False, encode_key=False):
        # ATM, notes are described as "note_duration_velocity|chord"
        note_name = list(MIDI_NOTE_NAMES.keys())[list(MIDI_NOTE_NAMES.values()).index(self.midi_note)]
        velocity = str(self.velocity)
        duration = str(self.duration)
        start_tick = str(self.start_tick)
        token = "" + note_name + "_" + duration  # Basic note token is expressed as "note_duration"
        # if encode_start_time:  # TODO: start_time is maybe a  nonsense, remove it from arguments!
        #     token += ("_" + str(start_tick))
        if encode_velocity:
            token += ("_" + velocity)
        if encode_key:
            token += ("_" + note2KeySig(self.getKey()))
        if encode_chord:
            if self.chord is not None:
                if isinstance(self.chord, str):
                    token += ("|" + self.chord)
                elif isinstance(self.chord, Chord):
                    token += ("|" + self.chord.getChord())
            else:
                token += "|NA"  # No chord found for note -> append "|NA"
        return token


class Chord:
    """
    Rappresentazione di un accordo
    """
    def __init__(self, start_tick, chord, key, rivolto, previous_chord, next_chord):
        self.start_tick = start_tick
        self.chord = chord
        self.key = key
        self.rivolto = rivolto
        self.previous_chord = previous_chord
        self.next_chord = next_chord

    def getStartTick(self):
        return self.start_tick

    def setStartTick(self, start_tick):
        self.start_tick = start_tick

    def getChord(self):
        return self.chord

    def setChord(self, chord):
        self.chord = chord

    def getKey(self):
        return self.key

    def setKey(self, key):
        self.key = key

    def getChordName(self):
        return getChordFromGradeOfScale(grade=self.getChord(), key=self.getKey())

    def getRivolto(self):
        return self.rivolto

    def setRivolto(self, rivolto):
        self.rivolto = rivolto

    def getPreviousChord(self):
        return self.previous_chord

    def setPreviousChord(self, previous_chord):
        self.previous_chord = previous_chord

    def getNextChord(self):
        return self.next_chord

    def setNextChord(self, next_chord):
        self.next_chord = next_chord

    def describe(self):
        # print("Chord:", getChordFromGradeOfScale(grade=self.getChord(), key=self.getKey()), "(n=" + str(self.getChord()) + ")")
        print("Chord:", str(self.getChord()))
        print("\tStartTick:", self.getStartTick())
        print("\tRivolto:", self.getRivolto())
        print("\tPrevious Chord:", self.getPreviousChord())
        print("\tNext Chord:", self.getNextChord())


class MIDIClip:
    """
    Rappresentazione di una traccia MIDI

    arguments:
    - path: path to MIDI file
    - transpose_to_C: transpose all MIDI clip to Cmaj ? (see transpose funciton in "functions.py" file)
    - custom_data: if supplied with a dict, it will not read any data from file, but instead it will use this data:
    {
        "name": name to use,
        "notes": list of Note(s),
        "bpm": (int) beats per minute,
        "chords": list of Chord(s),
        "key": key to use (str; see keySig2Fund function in functions.py),
        "mode": mode to use (str: "minor" or "major"),
    }
    """
    def __init__(self, path="", custom_data=None, transpose_to_C=True):
        # If no key is found inside the file, then set to Cmaj by default
        self.key = 0
        self.mode = "major"
        self.thread = None
        self.notes = []
        self.chords = []
        self.tempo = 0.5
        if custom_data is None:
            print("custom_data is None")
            if ".mid" in path:
                print("Is MIDI File")
                self.bpm = int(mido.tempo2bpm(self.tempo))
                self.midi = mido.MidiFile(path)
                self.name = path.split("/")[-1].split(".")[0]
                self.instr = self.name.split("_")[0]
                self.ppqn = self.midi.ticks_per_beat  # self.ppqn is relative to the loaded MIDI file, whereas PPQN refers to the project ppqn. Remember: Notes are converted in PPQN!
                self.computeBPM()
                self.computeKey()
                self.computeChords()
                self.computeNotes()
                self.applyKeyChordsOnNotes()
                self.length = int(mido.second2tick(self.midi.length, self.ppqn, self.tempo) * PPQN / self.ppqn)
            elif (".mscx" in path) or (".mscz" in path):
                print("Is MuseScore File")
                self.parseMuseScoreFile(path)
        else:
            self.name = custom_data["name"]
            self.key = custom_data["key"]
            self.notes = custom_data["notes"]
            self.chords = custom_data["chords"]
            self.key = keySig2Fund(custom_data["key"])
            self.mode = custom_data["mode"]
            self.bpm = custom_data["bpm"]
            self.tempo = self.bpm / 60.
            self.ppqn = PPQN
            self.applyKeyChordsOnNotes()
            self.length = int(max([note.getDuration() + note.getStartTick() for note in self.notes]))
        if transpose_to_C:
            self.transpose(-1 * self.key)

    def parseMuseScoreFile(self, path):
        print("Parsing MuseScore File...")
        score = ms3.Score(path)
        print(score.mscx.notes().columns)
        print(dir(score.mscx))
        print(score.mscx.metadata)
        for label in score.mscx.labels_cfg.items():
            print("label:", label)

        notes = score.mscx.notes().to_numpy()
        chords = score.mscx.labels().to_numpy()
        self.key = 0  # Assume C major scale
        self.chords = []
        for chord in chords:
            data = {"measure": int(chord[0]), "name": chord[11]}
            intra_measure = [int(a) for a in str(chord[5]).split("/")]
            if len(intra_measure) == 1:
                data["intra-measure"] = int(intra_measure[0])
            else:
                data["intra-measure"] = intra_measure[0] / intra_measure[1]
            duration = [int(a) for a in str(chord[10]).split("/")]
            if len(duration) == 1:
                duration = int(duration[0] * PPQN)
            else:
                duration = int(duration[0] * PPQN / duration[1])
            data["duration"] = duration
            data["onset"] = int((data["measure"] * PPQN * 4) + (data["intra-measure"] * PPQN))
            self.chords.append(Chord(start_tick=data["onset"], chord=data["name"], key=0, previous_chord=0, next_chord=0, rivolto=0))

        self.notes = []
        for note in notes:
            # print("note:", note)
            data = {"measure": note[0], "name": note[16]}
            intra_measure = [int(a) for a in str(note[5]).split("/")]
            duration = [int(a) for a in str(note[10]).split("/")]
            velocity = int(note[15])
            if len(duration) == 1:
                duration = int(duration[0] * 4 * PPQN)
            else:
                duration = int(duration[0] * PPQN * 4 / duration[1])
            data["duration"] = duration
            if len(intra_measure) == 1:
                data["intra-measure"] = int(intra_measure[0])
            else:
                data["intra-measure"] = intra_measure[0] / intra_measure[1]
            data["onset"] = int((data["measure"] * PPQN * 4) + (data["intra-measure"] * PPQN))
            current_chord_index = find_nearest_greater_or_equal_index([chord.getStartTick() for chord in self.chords], data["onset"])
            try:
                current_chord = self.chords[current_chord_index].getChord()
            except:
                current_chord = None
            if current_chord is None:
                current_chord = ""
            self.notes.append(Note(midi_note=noteToMIDI(data["name"]), velocity=velocity, start_tick=data["onset"], duration=data["duration"], chord=current_chord))

    def matchToTrack(self, track):
        """Modella accordi e note di questa traccia sulla base di un'altra traccia (ritorna una copia di questa istanza modificata)
        """
        copy = deepcopy(self)
        alterations = get_alterations_for_chord_match(track.chords, copy.chords)
        copy.chords = track.chords.copy()
        copy.notes = change_notes_from_alterations(copy.notes, alterations, scale=track.mode)
        return copy

    def computeKey(self):
        """Trova la tonalità del file MIDI
        """
        self.key = 0
        self.mode = "major"
        for msg in self.midi:
            if msg.type == "key_signature":
                self.key = keySig2Fund(msg.key)
                if "m" in msg.key:
                    self.mode = "minor"
                else:
                    self.mode = "major"
                break

    def getKey(self):
        return self.key

    def setKey(self, key):
        semitones = key - self.key
        self.transpose(semitones=semitones, keepOctave=True)

    def computeBPM(self):
        """Trova i bpm ed il tempo in microsecondi del file MIDI
        """
        # If no tempo in track:
        self.tempo = 0.5
        self.bpm = int(mido.tempo2bpm(self.tempo))
        for msg in self.midi:
            if msg.type == "set_tempo":
                self.tempo = msg.tempo
                self.bpm = int(mido.tempo2bpm(msg.tempo))
                break

    def getBPM(self):
        return self.bpm

    def setBPM(self, bpm):
        self.bpm = bpm

    def getName(self):
        return self.name

    def setName(self, name):
        self.name = name

    def computeChords(self):
        """Trova gli accordi scritti nel file MIDI
        """
        tick = 0
        self.tmp_chords = np.empty((1, 3), dtype=object)
        self.chords = []
        for msg in self.midi:
            tick = tick + int(mido.second2tick(msg.time, self.ppqn, self.tempo) * PPQN / self.ppqn)
            if(msg.type == "text") and (len(msg.text.split(" ")) == 2) and re.match("^[0-9 ]+$", msg.text):
                self.tmp_chords = np.concatenate((self.tmp_chords, [[int(tick), msg.text, ""]]), axis=0)
        self.tmp_chords = self.tmp_chords[1:]
        for chord_id, chord in enumerate(self.tmp_chords):
            self.chords.append(Chord(start_tick=int(chord[0]), chord=int(chord[1].split(" ")[0]) - 1, key=self.getKey(), rivolto=chord[1].split(" ")[1], previous_chord=int(wrapAt(self.tmp_chords, chord_id-1)[1].split(" ")[0]) - 1, next_chord=int(wrapAt(self.tmp_chords, chord_id+1)[1].split(" ")[0]) - 1))

    def getChords(self):
        return self.chords

    def computeNotes(self):
        """Trova le note del file MIDI
        """
        tick = 0
        lastNoteOns = np.zeros(128)
        self.tmp_notes = np.empty((1, 4), dtype=object)
        self.notes = []
        for msg in self.midi:
            tick = tick + int(mido.second2tick(msg.time, self.ppqn, self.tempo) * PPQN / self.ppqn)
            if(msg.type == "note_on") and (int(msg.velocity) != 0):
                self.tmp_notes = np.concatenate((self.tmp_notes, [[int(tick), 1, int(msg.note), int(msg.velocity)]]), axis=0)
                lastNoteOns[msg.note] = tick
            if(msg.type == "note_off") or ((msg.type == "note_on") and (int(msg.velocity) == 0)):
                self.tmp_notes = np.concatenate((self.tmp_notes, [[int(tick), 0, int(msg.note), int(msg.velocity)]]), axis=0)
        self.tmp_notes = self.tmp_notes[1:].tolist()
        self.tmp_note_ons = [None] * 12744
        for index, note in enumerate(self.tmp_notes):
            if note[1] == 1:
                self.tmp_note_ons[note[2]] = [note[0], index]
            if note[1] == 0:
                if self.tmp_note_ons[note[2]] is not None:
                    self.tmp_notes[self.tmp_note_ons[note[2]][1]].append(note[0] - self.tmp_note_ons[note[2]][0])
                    self.tmp_note_ons[note[2]] = None
        for index, note in enumerate(self.tmp_notes):
            if len(note) == 5:
                self.notes.append(Note(midi_note=note[2], velocity=note[3], start_tick=note[0], duration=note[4], bpm=self.bpm))

    def getNotes(self):
        return self.notes

    def transpose(self, semitones, keepOctave=False):
        self.notes = transposeNotes(self.notes, semitones, keepOctave)
        self.key += semitones
        for chord in self.chords:
            chord.setKey(self.key)
        self.applyKeyChordsOnNotes()

    def applyKeyChordsOnNotes(self):
        for note in self.notes:
            note.setKey(self.getKey())
            for chord in self.chords:
                if note.getStartTick() >= chord.getStartTick():
                    note.setChord(chord)

    def events(self):
        return [msg for msg in self.midi]

    def describe(self):
        print("\n\t\t* * * * TRACK '" + self.name + "' * * * *\n")
        print("bpm:", self.bpm)
        print("key:", note2KeySig(self.key), "(n=" + str(self.key) + ")")
        print("ppqn:", self.ppqn, PPQN)
        print("\t\t* * CHORDS * *")
        for chord in self.chords:
            chord.describe()
        print("\t\t* * NOTES * *")
        for note in self.notes:
            note.describe()

    def tokenize(self, max_notes=200, encode_start_time=False, encode_velocity=False, encode_chord=False, encode_key=False):
        if len(self.notes) > max_notes:
            tokens = []
            for i in range(0, len(self.notes), max_notes // 3):
                token = ""
                last_onset = 0
                for j in range(max_notes):
                    if (i + j) < len(self.notes):
                        self.notes[i + j].setStartTick(5 * round(self.notes[i + j].getStartTick() / 5))
                        if last_onset != self.notes[i + j].getStartTick():
                            token += (self.notes[i + j].tokenize(encode_start_time=encode_start_time, encode_velocity=encode_velocity, encode_chord=encode_chord, encode_key=encode_key) + ", ")
                        else:
                            token = token[:-2] + ";"  # Encode chords as a spaced sequence of tokens (without ",", e.g.: "C3_60 G4_60, E3_120")
                            token += (self.notes[i + j].tokenize(encode_start_time=encode_start_time, encode_velocity=encode_velocity, encode_chord=encode_chord, encode_key=encode_key) + ", ")
                        last_onset = self.notes[i + j].getStartTick()
                tokens.append(token[:-2])
        else:
            tokens = ""
            last_onset = 0
            for note in self.notes:
                note.setStartTick(5 * round(note.getStartTick() / 5))
                if last_onset != note.getStartTick():
                    tokens += (note.tokenize(encode_start_time=encode_start_time, encode_velocity=encode_velocity, encode_chord=encode_chord, encode_key=encode_key) + ", ")
                else:
                    tokens = tokens[:-2] + ";"  # Encode chords as a spaced sequence of tokens (without ",", e.g.: "C3_60 G4_60, E3_120")
                    tokens += (note.tokenize(encode_start_time=encode_start_time, encode_velocity=encode_velocity, encode_chord=encode_chord, encode_key=encode_key) + ", ")
                last_onset = note.getStartTick()
            tokens = tokens[:-2]
        return tokens
    
    def load_from_tokens(self, tokens, reset_chords=True, encode_velocity=False):
        if isinstance(tokens, str):
            tokens = tokens.split(", ")
        self.notes = []
        if reset_chords:
            self.chords = []
            self.key = 0
        current_tick = 0
        for token in tokens:
            if len(token) > 3:
                if len(token.split(";")) > 1:
                    min_dur = 1e6
                    for tt in token.split(";"):
                        if len(tt) > 3:
                            tt = tt.split("|")[0]
                            print("tt", tt)
                            tt = tt.split("_")
                            midinote = noteToMIDI(tt[0])
                            duration = int(tt[1])
                            if encode_velocity and len(tt) > 2:
                                velocity = int(tt[2])
                            else:
                                velocity = 100
                            min_dur = min(min_dur, duration)
                            self.notes.append(Note(midinote, velocity, current_tick, duration))
                    current_tick += min_dur
                else:
                    token = token.split("|")[0]
                    print("token", token)
                    token = token.split("_")
                    midinote = noteToMIDI(token[0])
                    duration = int(token[1])
                    if encode_velocity and len(token) > 2:
                        velocity = int(token[2])
                    else:
                        velocity = 100
                    self.notes.append(Note(midinote, velocity, current_tick, duration))
                    current_tick += duration

    def save(self, filepath, ignore_first_bar=False):
        mid = MidiFile(ticks_per_beat=PPQN)
        track = MidiTrack()
        track.append(MetaMessage('set_tempo', tempo=mido.bpm2tempo(120)))
        mid.tracks.append(track)
        messages = []
        for note in self.notes:
            start_tick = note.getStartTick()
            duration = note.getDuration()
            messages.append(['note_on', note.getNote(), note.getVelocity(), start_tick])
            messages.append(['note_off', note.getNote(), note.getVelocity(), start_tick + duration])
        messages = sorted(messages, key=lambda msg: msg[3])
        last_time = 0
        for m in messages:
            if ignore_first_bar and m[3] < (PPQN * 4):
                pass
            else:
                start_time = m[3]
                delta_time = start_time - last_time
                track.append(Message(m[0], note=m[1], velocity=m[2], time=delta_time))
                last_time = start_time
        mid.save(filepath)
        print(f'MIDI file saved as {filepath}')


class MIDIClipPlayer:
    def __init__(self, midiclip, clock, server=None, loop=True, widget=None, start_tick=0):
        self.server = server
        self.clock = clock
        self.notes = []
        self.onsets = []
        self.start_tick = start_tick
        self.midiclip = midiclip
        self.loop = loop
        self.widget = widget
        self.isPlaying = False
        self.has_to_stop = False
        self.thread = None
        self.start_tick = 0
        self.instr = "default"
        self.recalcNotes()

    def recalcNotes(self):
        if self.midiclip is not None:
            print("Recalcing notes")
            self.notes = self.midiclip.getNotes()
            self.onsets = [note.getStartTick() + self.start_tick for note in self.notes]
        else:
            print("No midiclip available")

    def setStartMeasure(self, measure):
        self.start_tick = measure * PPQN * 4
        self.recalcNotes()

    def getStartMeasure(self):
        return self.start_tick / (PPQN * 4)

    def setServer(self, server):
        self.server = server

    def setMIDIClip(self, midiclip):
        self.midiclip = midiclip
        self.recalcNotes()

    def setInstr(self, instr):
        self.instr = instr

    def setLoop(self, loop):
        self.loop = loop

    def process_tick(self, tick):
        for index, onset in enumerate(self.onsets):
            if tick == onset:
                # print(f"Propagating MIDI Note to widget: {self.widget}")
                if self.widget is not None:
                    self.widget.propagateMIDINote(self.notes[index])

    def threadFunc(self, clock):
        notes = self.midiclip.getNotes()
        onsets = [note.getStartTick() + self.start_tick for note in notes]
        while len(self.midiclip.getNotes()) > 0:
            clock.wait()
            clock_count = clock.getCount()
            if self.loop and (clock_count >= self.start_tick):
                clock_count = ((clock_count - self.start_tick) % self.midiclip.length) + self.start_tick
            for index, onset in enumerate(onsets):
                if clock_count == onset:
                    if self.widget is not None:
                        self.widget.propagateMIDINote(self.midiclip.getNotes()[index])
                    if (index == (len(onsets) - 1)) and not self.loop:
                        self.has_to_stop = True
            if self.has_to_stop:
                self.isPlaying = False
                break

    def noteThread(self, note):
        print("\tPlaying note on scsynth:", note.getNote())
        synth = Synth(self.server, self.instr, ["pitch", note.getNote(), "amp", note.getVelocity() / 127.])
        time.sleep(60 * note.getDuration() / (self.midiclip.getBPM() * PPQN))
        synth.set("gate", 0)

    def play(self):
        if not self.isPlaying:
            self.has_to_stop = False
            self.thread = Thread(target=self.threadFunc, args=(self.clock,), daemon=True)
            self.thread.start()
        self.isPlaying = True

    def stop(self):
        if self.thread is not None:
            self.has_to_stop = True
            self.thread = None


class TempoClock(threading.Event):
    def __init__(self, main_window=None, bpm=120):
        super().__init__()
        self.drift_time = 0.0004395
        self.wait_time = 1
        self.main_window = main_window
        self.patch = self.main_window.patch
        self.timeline = self.main_window.timeline
        self.bpm = bpm
        self.setBPM(bpm)
        self.isPlaying = False
        self.has_to_stop = False
        self.counter_reset_value = PPQN * 32767 * 16
        self.shuffle_midi_clips = False
        self.tick_counter = 0
        self.thread = None
        # self.gui_thread = GuiUpdateThread()
        # self.gui_thread.setPriority(QThread.Priority.HighestPriority)
        self.gui_timer = QTimer()
        self.gui_timer.timeout.connect(self.processInputEvents)
        # self.gui_thread.update_signal.connect(QApplication.processEvents)
        self.event_listeners = {}
        self.time_bounds = {"start": 0, "end": self.counter_reset_value}
        self.loop_bounds = True
        self.current_region = None
        self.calcWaitTime()

    def set_bounds(self, start, end):
        self.time_bounds["start"] = start
        self.time_bounds["end"] = end

    def remove_bounds(self):
        self.time_bounds["start"] = 0
        self.time_bounds["end"] = self.counter_reset_value

    def reloadParents(self, main_window):
        self.main_window = main_window
        self.patch = self.main_window.patch
        self.timeline = self.main_window.timeline

    def getCurrentTick(self):
        return self.tick_counter

    def getCurrentTime(self):
        t_millis = int(1000 * (60. / self.bpm) * (self.tick_counter / PPQN))
        ms = int(t_millis % 1000)
        s = int((t_millis / 1000) % 60)
        m = int((t_millis / 60000) % 60)
        h = int((t_millis / 3600000) % 24)
        # print("h:", h, "m:", m, "s:", s, "ms:", ms)
        return dtime(hour=h, minute=m, second=s, microsecond=ms * 1000)

    def getHMSMSFromTick(self, tick):
        t_millis = int(1000 * (60. / self.bpm) * (tick / PPQN))
        ms = int(t_millis % 1000)
        s = int((t_millis / 1000) % 60)
        m = int((t_millis / 60000) % 60)
        h = int((t_millis / 3600000) % 24)
        # print("h:", h, "m:", m, "s:", s, "ms:", ms)
        return dtime(hour=h, minute=m, second=s, microsecond=ms * 1000)

    def setBPM(self, bpm):
        self.bpm = bpm
        self.calcWaitTime()

    def getBPM(self):
        return self.bpm

    def calcWaitTime(self):
        self.wait_time = 60 / (self.bpm * PPQN)

    def getCount(self):
        return self.tick_counter

    def goto(self, tick):
        self.tick_counter = tick

    def set_region_play_type(self, type: bool):
        self.loop_bounds = type

    def start(self):
        if not self.isPlaying:
            self.has_to_stop = False
            try:
                start = self.main_window.region_manager.region_line.regions[self.main_window.region_manager.active_region]["start"]
                end = self.main_window.region_manager.region_line.regions[self.main_window.region_manager.active_region]["end"]
                self.set_bounds(start, end)
            except:
                pass
            # if not self.gui_thread.isRunning():
            #     self.gui_thread.start()
            # self.gui_timer.start(100)

            self.worker = ClockWorker(clock=self)
            self.thread = QThread()
            self.worker.moveToThread(self.thread)
            self.worker.update_signal.connect(self.main_window.update)
            self.thread.started.connect(self.clock_event_thread_qt)
            self.thread.start()
            self.thread.setPriority(QThread.Priority.HighestPriority)  # .HighPriority

    def foo(self):
        pass

    def pause(self):
        if self.thread is not None:
            self.has_to_stop = True
            self.isPlaying = False
            # self.thread = None
            self.worker.stop()
            self.thread.quit()
            self.thread.wait()
            self.gui_timer.stop()
            # self.gui_thread.stop()
            # self.gui_thread.wait()

    def stop(self):
        if self.thread is not None:
            self.has_to_stop = True
            self.isPlaying = False
            # self.thread = None
            self.worker.stop()
            self.thread.quit()
            self.thread.wait()
            self.gui_timer.stop()
            # self.gui_thread.stop()
            # self.gui_thread.wait()
        self.reset()

    def next(self):
        if self.time_bounds["start"] <= self.tick_counter < self.time_bounds["end"]:
            self.tick_counter += 1
            for audio_widget in self.patch.audio_widgets:
                uuid = audio_widget.getUUID()
                wc = self.timeline.widget_curves[str(uuid)]
                for env_key in wc.envelopes.keys():
                    envelope = wc.envelopes[env_key]
                    if envelope.isEnabled():
                        if envelope.curve.interp == "Trig":
                            val = envelope.isTickInTrig(self.tick_counter, self.timeline.npoints)
                            if envelope.was_triggered == 0:
                                audio_widget.synth.set(env_key, val)
                            if val > 0:
                                audio_widget.synth.set(env_key, val)
                            envelope.was_triggered -= 1
                        else:
                            val = envelope.computeValueFromTick(self.tick_counter, self.timeline.npoints)
                            audio_widget.synth.set(env_key, val)
            for audio_midi_widget in self.patch.audio_midi_widgets:
                uuid = audio_midi_widget.getUUID()
                wc = self.timeline.widget_curves[str(uuid)]
                for env_key in wc.envelopes.keys():
                    envelope = wc.envelopes[env_key]
                    if envelope.isEnabled():
                        val = envelope.computeValueFromTick(self.tick_counter, self.timeline.npoints)
                        audio_midi_widget.set_param(env_key, val)
            # Send current tick to midi widgets
            for midi_widget in self.patch.midi_widgets:
                midi_widget.process_tick(self.tick_counter)

            for key in self.event_listeners:  # Instantiate connected event listener functions with current tick counter
                self.event_listeners[key](self.tick_counter)
            if self.tick_counter >= self.counter_reset_value:
                print("\tSto resettando il counter del clock per overflow: aumenta il suo limite!", self.tick_counter, "su un massimo di", self.counter_reset_value)
                self.reset()
        else:
            if self.loop_bounds:  # In this mode, when region ends the region is repeated
                if self.tick_counter >= self.time_bounds["end"]:
                    self.tick_counter = self.time_bounds["start"]
                if self.tick_counter < self.time_bounds["start"]:
                    self.tick_counter = self.time_bounds["start"]
            else:  # In this mode, when region ends the end value is maintained
                if self.tick_counter >= self.time_bounds["end"]:
                    self.tick_counter = self.time_bounds["end"]

    def reset(self):
        self.tick_counter = self.time_bounds["start"]

    def clock_event_thread(self):
        while True:
            self.set()
            self.clear()
            time.sleep(self.wait_time)
            self.next()
            if self.has_to_stop:
                break

    def clock_event_thread_qt(self):
        t = None
        residual_time = self.drift_time
        while True:
            if t is None:
                t = time.time()
            self.set()
            self.clear()
            if self.tick_counter % 100 == 0:
                QCoreApplication.processEvents()
            # Calculate time delta
            tdelta = time.time() - t
            # Adjust residual_time based on observed performance
            if self.wait_time >= (tdelta + residual_time):
                time.sleep(self.wait_time - (tdelta + residual_time))
                residual_time = self.drift_time
            else:
                residual_time = tdelta - self.wait_time
            t = time.time()
            self.next()
            if self.has_to_stop:
                break

    def onTimeout(self):
        print("Timer timeout - Proceeding with parent function")
        # Continue with the parent function logic here
        # For example:
        print("Parent function completed")

    def processInputEvents(self):
        # Process all events in the event queue
        print("Processing GUI Events")
        QCoreApplication.processEvents()


class GuiUpdateThread(QThread):
    def __init__(self):
        super().__init__()
        self._run_flag = True

    def run(self):
        while self._run_flag:
            QApplication.processEvents()
            time.sleep(1)

    def stop(self):
        self._run_flag = False


if __name__ == "__main__":
    note = Note(69, 127, 0, 120, Chord(0, 4, 0, 0, 0, 0), 0, 440, 120)
    print("PPQN", PPQN)
    print("Tokenized note:", note.tokenize(True, True, True))
    midiclip = MIDIClip("/Users/francescodani/Documents/Libri/Partiture/MIDI Files/Melodies/Ghosthack MIDI - C# - Wubsynth Seasons.mid")
    midiclip.describe()
    print(midiclip.tokenize(encode_start_time=True))
    print(note.noteToFreq(note.getNote()))
