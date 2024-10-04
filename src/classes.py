"""@package classes
Documentazione delle varie classi
"""
import mido
import time
from datetime import time as dtime
import numpy as np
from configparser import ConfigParser
from copy import deepcopy
import signal
from threading import Thread, Event
from functions import *
from harmony import *
from supercollider import *
import threading
import re
import rtmidi
from rtmidi.midiutil import open_midiinput
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


class MidiInputHandler(object):
    def __init__(self, port, device, midi_manager):
        self.port = port
        self.device = device
        self.midi_manager = midi_manager
        self._wallclock = time.time()

    def __call__(self, event, data=None):
        message, deltatime = event
        self._wallclock += deltatime
        # print("[%s] @%0.6f %r" % (self.port, self._wallclock, message))
        msg_type = message[0]
        # print("Registered widgets:", self.midi_manager.registered_widgets)

        if msg_type == 144:  # Note On
            c_print("green", f"NoteOn found: {message}")
            note_number = message[1]
            note_name = [key for key, value in MIDI_NOTE_NAMES.items() if value == note_number][0]
            velocity = message[2]
            c_print("green", f"NoteOn found: {message}; note {note_number}")
            c_print("yellow", f"{MIDI_NOTE_NAMES}")
            # note_name = rtmidi.MidiIn.getNoteName(note_number)
            # Process Note On
            for uuid in self.midi_manager.registered_widgets.keys():
                print("EHIII", int(self.midi_manager.registered_widgets[uuid]["device"]), self.device, int(self.midi_manager.registered_widgets[uuid]["device"]) == self.device)
                if int(self.midi_manager.registered_widgets[uuid]["device"]) == self.device:
                    print(f"Propagating RT MIDI Note to {self.midi_manager.registered_widgets[uuid]['widget']}")
                    self.midi_manager.registered_widgets[uuid]["widget"].propagateRTMIDINote(note_name, velocity)
                    # self.midi_manager.registered_widgets[uuid]["widget"].propagateRTMIDINote(note_number, velocity)
        elif msg_type == 128:  # Note Off
            c_print("green", f"NoteOff found: {message}")
            note_number = message[1]
            note_name = [key for key, value in MIDI_NOTE_NAMES.items() if value == note_number][0]
            # Process Note Off
            for uuid in self.midi_manager.registered_widgets.keys():
                if int(self.midi_manager.registered_widgets[uuid]["device"]) == self.device:
                    self.midi_manager.registered_widgets[uuid]["widget"].propagateRTMIDINote(note_name, 0)
        elif msg_type == 176:  # Control Change
            controller_number = message[1]
            controller_value = message[2]
            # Process Control Change
            for uuid in self.midi_manager.registered_widgets.keys():
                if int(self.midi_manager.registered_widgets[uuid]["device"]) == self.device:
                    self.midi_manager.registered_widgets[uuid]["widget"].propagateRTCC(controller_number, controller_value)
        elif msg_type == 192:  # Program Change
            program_change_number = message[1]
            # Process Program Change
            for uuid in self.midi_manager.registered_widgets.keys():
                if int(self.midi_manager.registered_widgets[uuid]["device"]) == self.device:
                    self.midi_manager.registered_widgets[uuid]["widget"].propagateRTProgramChange(program_change_number)
            # Check regions
            for key in self.midi_manager.region_manager.regions_buttons.keys():
                try:
                    if int(self.midi_manager.region_line.regions[key]["program"]) == program_change_number:
                        self.midi_manager.region_manager.regions_buttons[key].click()
                        c_print('cyan', f'Switching to region {key}')
                except:
                    c_print('red', f'Wrong region name: {key}')


class MIDIManager:
    def __init__(self, context):
        self.context = context
        # self.region_manager = self.context.parent.region_manager
        # self.region_line = self.context.parent.timeline.region_line
        self.registered_widgets = {}
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

    # def connectAll_BAK(self):
    #     self.midi_in_threads = []
    #     for device in self.midi_in_devices:
    #         self.midi_ins.append(rtmidi.MidiIn(int(device)))
    #         self.midi_ins[-1].open_port(device)
    #         # print("Device:", device)
    #         self.midi_in_threads.append(MidiInput(device, self, self.region_manager, self.region_line))
    #         # print("Device:", device, "created")
    #         self.midi_in_threads[-1].start()
    #         # print("Device:", device, "started.")
    #     for device in self.midi_out_devices:
    #         self.midi_outs.append(rtmidi.MidiOut(int(device)))
    #         self.midi_outs[-1].open_port(device)
    #         # self.midi_in_threads.append(MidiOutput(device, self, self.region_manager, self.region_line))

    def connectAll(self):
        self.midi_in_threads = []
        for device in self.midi_in_devices:
            midiin, port_name = open_midiinput(device)
            self.midi_ins.append(midiin)
            self.midi_ins[-1].set_callback(MidiInputHandler(port_name, device, self))
            # self.midi_ins.append(rtmidi.MidiIn(int(device)))
            # self.midi_ins[-1].open_port(device)
            # self.midi_ins[-1].set_callback(self.midi_callback, int(device))
            c_print("cyan", f"Successfully opened MIDI Input Device: {device}")
        for device in self.midi_out_devices:
            self.midi_outs.append(rtmidi.MidiOut(int(device)))
            self.midi_outs[-1].open_port(device)
            c_print("cyan", f"Successfully opened MIDI Output Device: {device}")

    def disconnectAll(self):
        for midiin_thread in self.midi_in_threads:
            try:
                midiin_thread.stop()
            except:
                pass
        for device in self.midi_ins:
            try:
                device.close_port()
            except:
                c_print("red", f"ERROR: Could not disconnect device {device} (type={type(device)})")
        for device in self.midi_outs:
            try:
                device.close_port()
            except:
                c_print("red", f"ERROR: Could not disconnect device {device}")

    def refreshDevices(self):
        self.disconnectAll()
        self.midi_in_device_names = [rtmidi.MidiIn().get_port_name(index) for index in range(rtmidi.MidiIn().get_port_count())]
        self.midi_in_devices = [index for index in range(rtmidi.MidiIn().get_port_count())]
        self.midi_out_device_names = [rtmidi.MidiOut().get_port_name(index) for index in range(rtmidi.MidiOut().get_port_count())]
        self.midi_out_devices = [index for index in range(rtmidi.MidiOut().get_port_count())]
        self.connectAll()

    def register_widget(self, widget):
        self.registered_widgets[str(widget.getUUID())] = {"widget": widget, "device": widget.getDevice()}
        c_print("cyan", f"Registered widget {widget.getUUID()} to device {widget.getDevice()}")

    def unregister_widget(self, widget):
        if str(widget.getUUID()) in self.registered_widgets.keys():
            del self.registered_widgets[str(widget.getUUID())]

    def midi_callback(self, message, time_stamp, device):
        # `message` is a list of MIDI data bytes
        # `time_stamp` is the delta time
        c_print("green", f"MIDI message received from device {device}: {message}")
        msg_type = message[0] & 0xF0  # Extract the message type

        if msg_type == 0x90:  # Note On
            note_number = message[1]
            velocity = message[2]
            note_name = rtmidi.MidiIn.getNoteName(note_number)
            # Process Note On
            for uuid in self.registered_widgets.keys():
                if self.registered_widgets[uuid]["device"] == device:
                    self.registered_widgets[uuid]["widget"].propagateRTMIDINote(note_name, velocity)
        elif msg_type == 0x80:  # Note Off
            note_number = message[1]
            note_name = rtmidi.MidiIn.getNoteName(note_number)
            # Process Note Off
            for uuid in self.registered_widgets.keys():
                if self.registered_widgets[uuid]["device"] == device:
                    self.registered_widgets[uuid]["widget"].propagateRTMIDINote(note_name, 0)
        elif msg_type == 0xB0:  # Control Change
            controller_number = message[1]
            controller_value = message[2]
            # Process Control Change
            for uuid in self.registered_widgets.keys():
                if self.registered_widgets[uuid]["device"] == device:
                    self.registered_widgets[uuid]["widget"].propagateRTCC(controller_number, controller_value)
        elif msg_type == 0xC0:  # Program Change
            program_change_number = message[1]
            # Process Program Change
            for uuid in self.registered_widgets.keys():
                if self.registered_widgets[uuid]["device"] == device:
                    self.registered_widgets[uuid]["widget"].propagateRTProgramChange(program_change_number)
            # Check regions
            for key in self.region_manager.regions_buttons.keys():
                try:
                    if int(self.region_line.regions[key]["program"]) == program_change_number:
                        self.region_manager.regions_buttons[key].click()
                        c_print('cyan', f'Switching to region {key}')
                except:
                    c_print('red', f'Wrong region name: {key}')

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
        if type(self.mididev) == rtmidi.MidiIn:
            self.stop_event.clear()
            self.running = True
            while not self.stop_event.is_set():
                msg = self.mididev.get_message(100)
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
        return (self.tuning / 32) * (2 ** ((note - 9) / 12))

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
        print("Chord:", getChordFromGradeOfScale(grade=self.getChord(), key=self.getKey()), "(n=" + str(self.getChord()) + ")")
        print("\tStartTick:", self.getStartTick())
        print("\tRivolto:", self.getRivolto())
        print("\tPrevious Chord:", self.getPreviousChord())
        print("\tNext Chord:", self.getNextChord())


class MIDIClip:
    """
    Rappresentazione di una traccia MIDI

    arguments:
    - path: path to MIDI file
    - transpose_to_C: transpose to C ?
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
            self.bpm = int(mido.tempo2bpm(self.tempo))
            self.midi = mido.MidiFile(path)
            self.name = path.split("/")[-1].split(".")[0]
            self.instr = self.name.split("_")[0]
            self.ppqn = self.midi.ticks_per_beat
            self.computeBPM()
            self.computeKey()
            self.computeChords()
            self.computeNotes()
            self.applyKeyChordsOnNotes()
            self.length = self.get_eot_tick(midi_file=self.midi)
            if self.length is None:
                self.length = int(mido.second2tick(self.midi.length, self.ppqn, self.tempo) * PPQN / self.ppqn)
        else:
            self.name = custom_data["name"]
            self.key = custom_data["key"]
            self.mode = custom_data["mode"]
            self.notes = custom_data["notes"]
            self.chords = custom_data["chords"]
            self.key = keySig2Fund(custom_data["key"])
            self.mode = custom_data["mode"]
            self.bpm = custom_data["bpm"]
            self.tempo = self.bpm / 60.
            self.ppqn = PPQN
            self.applyKeyChordsOnNotes()
            self.length = self.get_eot_tick(midi_file=self.midi)
            if self.length is None:
                self.length = int(max([note.getDuration() + note.getStartTick() for note in self.notes]))
        print("MIDI File num ticks:", self.length)
        if transpose_to_C:
            self.transpose(-1 * self.key)

    def get_eot_tick(self, midi_file):
        eot_tick = None
        for i, track in enumerate(midi_file.tracks):
            for msg in reversed(track):
                if msg.type == 'end_of_track' and msg.time > 0:
                    eot_tick = msg.time
            if eot_tick is not None:
                return eot_tick  # Returns the tick of the EOT message
        return None  # Return None if no EOT message is found

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
        # If nothing found inside the file, then set to Cmaj by default
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
        self.tmp_note_ons = [None] * 12744  # TODO: check correctness of this fixed number
        for index, note in enumerate(self.tmp_notes):
            if (note[1] == 1):
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
        print("\t\t* * CHORDS * *")
        for chord in self.chords:
            chord.describe()
        print("\t\t* * NOTES * *")
        for note in self.notes:
            note.describe()


class MIDIClipPlayer:
    def __init__(self, midiclip, clock, server=None, loop=True, widget=None, start_tick=0, end_tick=-1):
        self.server = server
        self.clock = clock
        self.notes = []
        self.onsets = []
        self.start_tick = start_tick
        self.end_tick = end_tick
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
            self.notes = self.midiclip.getNotes()
            self.onsets = [note.getStartTick() + self.start_tick for note in self.notes]
            print("Onsets:", self.onsets)
        else:
            print("No midiclip available")

    def setStartMeasure(self, measure):
        self.start_tick = int(measure * PPQN * 4)
        self.recalcNotes()

    def setEndMeasure(self, measure):
        self.end_tick = int(measure * PPQN * 4)
        self.recalcNotes()

    def getStartMeasure(self):
        return self.start_tick / (PPQN * 4)

    def getEndMeasure(self):
        return self.end_tick / (PPQN * 4)

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
        # if tick == 0:
        #     c_print("green", f"Processing tick in MIDIClipPlayer(object) associated to MIDIClipPlayer(MIDIWidget): {self.widget.uuid}")
        if self.loop and (tick > self.start_tick) and (tick <= self.end_tick if self.end_tick > 0 else True):
            tick = ((tick - self.start_tick) % self.midiclip.length) + self.start_tick
        # print("Processing tick:", tick)
        for index, onset in enumerate(self.onsets):
            if tick == onset:
                self.widget.propagateMIDINote(self.notes[index])

    # def threadFunc(self, clock):
    #     notes = self.midiclip.getNotes()
    #     onsets = [note.getStartTick() + self.start_tick for note in notes]
    #     print("Onsets:", onsets)
    #     while len(self.midiclip.getNotes()) > 0:
    #         clock.wait()
    #         clock_count = clock.getCount()
    #         if self.loop and (clock_count >= self.start_tick):
    #             clock_count = ((clock_count - self.start_tick) % self.midiclip.length) + self.start_tick
    #         for index, onset in enumerate(onsets):
    #             if clock_count == onset:
    #                 if self.widget is not None:
    #                     self.widget.propagateMIDINote(self.midiclip.getNotes()[index])
    #                 if (index == (len(onsets) - 1)) and not self.loop:
    #                     self.has_to_stop = True
    #         if self.has_to_stop:
    #             self.isPlaying = False
    #             break

    def noteThread(self, note):
        synth = Synth(self.server, self.instr, ["pitch", note.getNote(), "amp", note.getVelocity() / 127.])
        time.sleep(60 * note.getDuration() / (self.midiclip.getBPM() * PPQN))
        synth.set("gate", 0)

    def play(self):
        if not self.isPlaying:
            self.has_to_stop = False
            # self.thread = Thread(target=self.threadFunc, args=(self.clock,), daemon=True)
            # self.thread.start()
        self.isPlaying = True

    def stop(self):
        self.has_to_stop = True
        # if self.thread is not None:
            # self.has_to_stop = True
            # self.thread = None


class TempoClock(threading.Event):
    def __init__(self, main_window=None, bpm=120):
        super().__init__()
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
        self.event_listeners = {}
        self.time_bounds = {"start": 0, "end": self.counter_reset_value}
        self.loop_bounds = True

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
            self.thread = threading.Thread(target=self.clock_event_thread)
            self.thread.start()

    def pause(self):
        if self.thread is not None:
            self.has_to_stop = True
            self.isPlaying = False
            self.thread = None

    def stop(self):
        if self.thread is not None:
            self.has_to_stop = True
            self.isPlaying = False
            self.thread = None
        self.reset()

    def next(self):
        if self.time_bounds["start"] <= self.tick_counter < self.time_bounds["end"]:
            # if (self.tick_counter % 100) == 0:
            #     print(self.getCurrentTime())
            # Compute Curve values at current tick for enabled WidgetCurves
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
        self.tick_counter += 1  # Moved from the beginning to the end of the function

    def reset(self):
        self.tick_counter = self.time_bounds["start"]

    def clock_event_thread(self):
        while True:
            self.set()
            self.clear()
            time.sleep(self.wait_time)
            if self.has_to_stop:
                break
            self.next()


if __name__ == "__main__":
    pass
