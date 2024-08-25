import random
import time
import numpy as np
from lxml import etree
from harmony import *
from array_processing import *
from signal import *
import subprocess
from collections import defaultdict
import bisect

def kill_scsynth_on_sigkill():
    def killall_scsynth(*args):
        subprocess.call("killall scsynth", shell=True)

    for sig in (SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM):
        signal(sig, killall_scsynth)


def find_nearest_greater_or_equal_index(sorted_list, target):
    # Find the insertion point where the target would fit in the sorted list
    index = bisect.bisect_left(sorted_list, target)

    # Check if the index is within the bounds of the list
    if index < len(sorted_list):
        return index
    else:
        return None  # No such element exists


def midicps(midi, fA4InHz=440):
    def convert_midi2freq_scalar(p, fA4InHz):
        if p <= 0:
            return 0
        else:
            return fA4InHz * 2 ** ((p - 69) / 12)

    midi = np.asarray(midi)
    if midi.ndim == 0:
        return convert_midi2freq_scalar(midi, fA4InHz)
    fInHz = np.zeros(midi.shape)
    for k, p in enumerate(midi):
        fInHz[k] = convert_midi2freq_scalar(p, fA4InHz)
    return (fInHz)


def cpsmidi(freq):
    return int((12 * np.log(freq / 220) / np.log(2.0)) + 57.01)


def getChordFromGradeOfScale(grade, key=0, kind="major"):
    return CHORDS_OF_MAJOR_SCALES[note2KeySig(key)][grade]


def midiToNote(midi_note, octave=True):
    oct = str(midi_note // 12)
    note = NOTE_NAMES[midi_note % 12]
    if octave:
        return note + oct
    else:
        return note


def noteToMIDI(note):
    note_name = note[:-1]
    if "b" in note_name:
        note_name = BEMOLLE_TO_DIESIS[note_name]
    return MIDI_NOTE_NAMES[note_name + note[-1]]



def note2KeySig(note):
    note = note % 12
    if note > 6: note -= 12
    if note == 0:
        return "C"
    elif note == 1:
        return "C#/Db"
    elif note == 2:
        return "D"
    elif note == 3:
        return "D#/Eb"
    elif note == 4:
        return "E"
    elif note == 5:
        return "F"
    elif note == 6:
        return "F#/Gb"
    elif note == -5:
        return "G"
    elif note == -4:
        return "G#/Ab"
    elif note == -3:
        return "A"
    elif note == -2:
        return "A#/Bb"
    else:
        return "B"


def keySig2Fund(key):
    key = key.split("m")[
        0]  # qui non frega un cazzo se la tonalità è maggiore o minore ("m" è l'ultimo carattere in caso di scale minori)
    if (key == "C"):
        return 0
    elif (key == "C#") or (key == "Db") or (key == "C#/Db"):
        return 1
    elif (key == "D"):
        return 2
    elif (key == "D#") or (key == "Eb") or (key == "D#/Eb"):
        return 3
    elif key == "E":
        return 4
    elif key == "F":
        return 5
    elif (key == "F#") or (key == "Gb") or (key == "F#/Gb"):
        return 6
    elif key == "G":
        return -5
    elif (key == "G#") or (key == "Ab") or (key == "G#/Ab"):
        return -4
    elif key == "A":
        return -3
    elif (key == "A#") or (key == "Bb") or (key == "A#/Bb"):
        return -2
    elif key == "B":
        return -1
    else:
        return 0


def major2minor(note):
    """Converti una nota da scala maggiore a scala minore
	"""
    bias = int(note / 12)
    note12 = note % 12
    if note12 == 4:  note12 = 3
    if note12 == 9:  note12 = 8
    if note12 == 11: note12 = 10
    return note12 + (bias * 12)


def transpose(note, semitones, keepOctave=False):
    """Trasponi una singola nota
	"""
    if keepOctave:
        bias = int(note / 12)
        note12 = (note + semitones) % 12
        return note12 + (bias * 12)
    else:
        return note + semitones


def transpose_vec(vec, semitones, keepOctave=False):
    """Trasponi un vettore di note
	"""
    vec_cp = vec.copy()
    for note_id, note in enumerate(vec_cp):
        vec_cp[note_id][2] = transpose(vec_cp[note_id][2], semitones, keepOctave)
    return vec_cp


def transposeNotes(vec, semitones, keepOctave=False):
    """Trasponi un vettore di istanze di classe Note
	"""
    for note in vec:
        note.setNote(transpose(note.getNote(), semitones, keepOctave))
    return vec


def change_modality(chords, mode=0):
    """Cambia il modo di una sequenza di accordi (si assume che si parta da un modo Ionico in scala di Do Maggiore)
	"""
    out = chords.copy()
    for chord_vec_id, chord_vec in enumerate(chords):
        chord = int(chord_vec[1].split(" ")[0])
        rivolto = chord_vec[1].split(" ")[1]
        new_chord = str(wrap(chord + mode, 0, 6)) + " " + chord_vec[1].split(" ")[1]
        if (mode == 1) and ((chord == 4) or (chord == 5) or (chord == 6)): continue
        if (mode == 2) and ((chord == 2) or (chord == 3) or (chord == 4) or (chord == 5) or (chord == 6)): continue
        if (mode == 3) and (
                (chord == 0) or (chord == 1) or (chord == 3) or (chord == 4) or (chord == 5) or (chord == 6)): continue
        if (mode == 4) and ((chord == 2) or (chord == 4)): continue
        if (mode == 5) and ((chord == 1) or (chord == 3) or (chord == 5)): continue
        if (mode == 6): continue
        out[chord_vec_id][1] = new_chord
    for chord_vec_id, chord_vec in enumerate(out):
        last_chord_vec_id = wrap(chord_vec_id - 1, 0, len(out) - 1)
        next_chord_vec_id = wrap(chord_vec_id + 1, 0, len(out) - 1)
        out[chord_vec_id][2] = out[last_chord_vec_id][1].split(" ")[0] + chord_vec[1].split(" ")[0] + \
                               out[next_chord_vec_id][1].split(" ")[0]
    return out


def get_alterations_for_chord_match(bearing_chords, matching_chords):
    """Trova le alterazioni per cambiare una sequenza di accordi (matching) in base ad un'altra sequenza di accordi (bearing)
	"""
    tmp = bearing_chords.copy()
    bearing_chords = matching_chords.copy()
    matching_chords = tmp
    alterations = []
    if len(bearing_chords) >= len(matching_chords):
        for bear_vec_id, bear_vec in enumerate(bearing_chords):
            for match_vec_id, match_vec in enumerate(matching_chords):
                if int(match_vec[0]) >= int(bear_vec[0]):
                    alterations.append([match_vec[0], int(match_vec[1][0]) - int(bear_vec[1][0])])
                    break
    else:
        for bear_vec_id, bear_vec in enumerate(bearing_chords):
            deep_break = False
            for i in range(50):
                for match_vec_id, match_vec in enumerate(matching_chords):
                    if int(match_vec[0]) <= int(bear_vec[0]):
                        alterations.append([match_vec[0], str(int(match_vec[1][0]) - int(bear_vec[1][0]))])
                        deep_break = True
                        break
                if deep_break: break
    return np.asarray(alterations)


def change_notes_from_alterations(notes, alterations, scale="major"):
    """Cambia le note di un file MIDI in base ad un vettore di alterazioni
	"""
    if scale not in MUSICAL_SCALES.keys():
        raise Exception("'scale' is not a known scale.")
    new_notes = notes.copy()
    altered_notes = []
    for note_vec_id, note_vec in enumerate(notes):
        note_vec_copy = note_vec.copy()
        for alteration_id, alteration in enumerate(alterations):
            if ((int(note_vec[0]) >= int(alteration[0])) and (
                    int(note_vec[0] < int(alterations[np.clip(alteration_id + 1, 0, len(alterations) - 1)][0])))) or (
                    int(note_vec[0] >= int(alterations[-1][0]))):
                # noteOn
                if (note_vec[1] == 1) and (note_vec[3] > 0):
                    if (int(note_vec[2]) % 12) in MUSICAL_SCALES[scale]:
                        index_of_scale = MUSICAL_SCALES[scale].index(int(note_vec[2]) % 12)
                    else:
                        index_of_scale = MUSICAL_SCALES[scale].index((int(note_vec[2]) + 1) % 12)
                    new_index_of_scale = index_of_scale + int(alteration[1])
                    note_diff = wrapAt(MUSICAL_SCALES[scale], index_of_scale) - wrapAt(MUSICAL_SCALES[scale],
                                                                                       new_index_of_scale)
                    new_note = note_vec[2] + note_diff
                    if (int(alteration[1]) > 0) and (note_diff < 0): new_note += 12
                    if (int(alteration[1]) < 0) and (note_diff > 0): new_note -= 12
                    note_vec_copy[2] = new_note
                    altered_notes.append([note_vec[2], note_vec_copy[2]])
                    break
                # noteOff
                else:
                    if len(altered_notes) > 0:
                        if note_vec[2] in flop(altered_notes)[0]:
                            last_note_on_id = flop(altered_notes)[0].index(note_vec[2])
                            note_vec_copy[2] = altered_notes[last_note_on_id][1]
                            del altered_notes[last_note_on_id]
        new_notes[note_vec_id] = note_vec_copy
    return new_notes


def etree_to_dict(t):
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib:
        d[t.tag].update(('@' + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d


def read_features(feature_file_path):
    """Leggi le feature di una cartella di file MIDI
	"""
    feature_dict = etree_to_dict(etree.parse(feature_file_path).getroot())["feature_vector_file"]["data_set"]
    feature_dict = {
        dataset["data_set_id"].split("/")[-1]: {feature["name"]: feature["v"] for feature in dataset["feature"]} for
        dataset in feature_dict}
    for name, dataset in feature_dict.items():
        for key, value in dataset.items():
            if type(feature_dict[name][key]) == str:
                feature_dict[name][key] = float(value.replace(",", "."))
            if type(feature_dict[name][key]) == list:
                feature_dict[name][key] = np.asarray([float(val.replace(",", ".")) for val in value])
    return feature_dict


def analyze_feature_variance(feature_dict):
    features = [[] for i in range(len(feature_dict[list(feature_dict.keys())[0]]))]
    feature_names = [key for key in feature_dict[list(feature_dict.keys())[0]]]
    for filename, filefeatures in feature_dict.items():
        for index, fe_d in enumerate(filefeatures.items()):
            features[index].append(fe_d[1])
    print(features[18] == features[1])
    features = [np.asarray(feature) for feature in features]
    feature_variances = [np.var(normalize(feature)) for feature in features]
    print(feature_variances)
    for index, name in enumerate(feature_names):
        print(name, feature_variances[index])
    from matplotlib import pyplot as plt
    plt.plot(feature_variances)
    plt.show()


def decompose432(num):
    decomposed = []
    if num <= 1:
        return []  # sicuro di ritornare una lista vuota?
    else:
        while num > 0:
            if num % 4 == 0:
                decomposed.append(4)
                num = num - 4
            elif num % 3 == 0:
                decomposed.append(3)
                num = num - 3
            elif num % 2 == 0:
                decomposed.append(2)
                num = num - 2
            else:
                choice = random.choice([2, 3])
                decomposed.append(choice)
                num = num - choice
        return decomposed


def genMelodyFromRhythm(rhythm=[0.5, 1, 0.25, 0.25, 0.5, 0.5], pernoNotes=[0, 2, 4, 7], scale="major", chord=0,
                        nextchord=0, minpernodur=0.5):
    melody = []
    size = len(rhythm)
    perni = [True if rhy >= minpernodur else False for rhy in rhythm]
    notperno = True
    tmp = []
    for pid, perno in enumerate(perni):
        if perno == False and notperno == True:
            nexttrue = 0
            num = size - (pid + 1)
            for pid2 in range(pid + 1, size - 1):
                if perni[clip(pid + pid2, 0, len(perni) - 1)]:
                    nexttrue = pid + pid2
            if 0 < nexttrue < num:
                num = nexttrue
            notperno = perno
            tmp.append(num)
        else:
            noteperno = perno
            tmp.append(perno)
    perni = tmp
    for pid, perno in enumerate(perni):
        if type(perno) == int:
            suffix = 0
            decomposition = decompose432(perno)
            if pid > 0:
                if perni[pid + suffix - 1] is True:
                    perni[pid + suffix - 1] = random.choice(pernoNotes)
            for decid, dec in enumerate(decomposition):
                choice = queryKDTree(MELODIC_MOVIMENTI_KDTREE[str(dec)],
                                     [random.uniform(0.0, 1.0) for _ in range(MELODIC_MOVIMENTI_FEAT_SIZE)], 4)[0]
                notes = MELODIC_MOVIMENTI[str(dec)]["Notes"][choice]
                for noteid, note in enumerate(notes):
                    perni[(pid + suffix + noteid) % len(perni)] = note
                suffix += dec
    for pid, perno in enumerate(perni):
        if (perno is True) or (perno is False):
            perni[pid] = random.choice(pernoNotes)
    for pid, perno in enumerate(perni):
        octave = int((perno + chord) / len(MUSICAL_SCALES[scale]))
        melody.append(((MUSICAL_SCALES[scale][(perno + chord) % len(MUSICAL_SCALES[scale])] + (12 * octave)) % 12))
    return np.array(melody), np.array(rhythm), np.array([melody, rhythm]).T


def addMelodyToHistory(melody, maxHistorySize=100):
    global MELODIC_HISTORY
    for note in melody:
        MELODIC_HISTORY.append(note.tolist())
    if len(MELODIC_HISTORY) > maxHistorySize:
        MELODIC_HISTORY = MELODIC_HISTORY[(len(MELODIC_HISTORY) - maxHistorySize):]


def findMelodicCells():
    print("findMelodicCells():")
    hist = np.array(MELODIC_HISTORY)
    hist_rot = rotate(hist, 0).copy()  # first null rotation
    autocorr_matrix = []
    autocorr_matrix_2 = []
    for i in range(len(MELODIC_HISTORY) - 1):
        hist_rot = rotate(hist_rot, 1).copy()
        autocorr_matrix.append(
            [True if (hist[id][0] == hist_rot[id][0]) and (hist[id][1] == hist_rot[id][1]) else False for id in
             range(len(hist))])
    # print(autocorr_matrix)
    autocorr = np.sum(np.array(autocorr_matrix), axis=1)
    for i in range(len(MELODIC_HISTORY) - 1):
        autocorr_matrix_2.append(
            [True if (autocorr_matrix[i][i2] is True) and (autocorr_matrix[i][i2 + 1] is True) else False for i2 in
             range(len(hist) - 1)])
        autocorr_matrix_2[i].append(False)
    autocorr = [True if aut > 0 else False for aut in autocorr]
    # Cleanup 010, *10, 01*
    for i in range(1, len(autocorr) - 1):
        if autocorr[i] is True and autocorr[i - 1] is False and autocorr[i + 1] is False:
            autocorr[i] = False
    if autocorr[0] is True and autocorr[1] is False:
        autocorr[0] = False
    if autocorr[len(autocorr) - 1] is True and autocorr[len(autocorr) - 2] is False:
        autocorr[len(autocorr) - 1] = False
    autocorr.append(False)
    print(autocorr)
    hist = hist.tolist()
    print(len(hist), len(autocorr))
    autocorr = split_list_by_boolean(hist, autocorr)
    return autocorr


def showMelody(melody, rhythm, name="./tmp.png"):
    import muspy
    timer = 0
    notes = []
    notes.append(muspy.Note(0, int(melody[0]), rhythm[0]))
    timer += rhythm[0]
    for noteid, note in enumerate(melody):
        if noteid > 0:
            notes.append(muspy.Note(timer, int(melody[noteid]), timer + rhythm[noteid]))
            timer += rhythm[noteid]
    track = muspy.Track(notes=notes)
    music = muspy.Music(tracks=[track], resolution=960)

    plotter = muspy.visualization.show_score(music, figsize=(len(notes) * 2, 4))
    plotter.fig.savefig(name)


if __name__ == "__main__":
    import configparser as cp
    import ujson as json
    from classes import *
    from functions import *
    import os

    conf = cp.ConfigParser()
    conf.read("config.ini")
    instrs = json.loads(conf.get("GENERAL", "instrs"))

    feature_file_path = "/Users/admin/Documents/BackupGoogleDrive/PyMusic/data/midi/extracted_feature_values.xml"

    """
	#path1 = "/Users/admin/Documents/BackupGoogleDrive/PyMusic/data/midi/chord-progressions/progression_1.MID"
	path1 = "/Users/admin/Documents/MusicaDAmbiente/app_build/Purilian.app/Contents/Resources/Resources/mididb/Lo-Fi/piece_101/pad_101.mid"
	path2 = "/Users/admin/Documents/BackupGoogleDrive/PyMusic/data/midi/chord-progressions/progression_1.MID"


	print("\n\n")

	track1 = Track(path1)
	print("Track info:")
	print("name", track1.name)
	print("instr", track1.instr)
	print("bpm", track1.bpm)
	print("tempo", track1.tempo)
	print("key", track1.key)
	print("chords", track1.chords)
	#print("notes", track1.notes)
	
	#print(transpose_vec(track1.notes, 3, False))
	
	#print(change_modality(track1.chords, 4))

	print("\n\n")
	
	track2 = Track(path2)
	#track2.chords = track1.chords
	print("Track info:")
	print("name", track2.name)
	print("instr", track2.instr)
	print("bpm", track2.bpm)
	print("tempo", track2.tempo)
	print("key", track2.key)
	print("mode", track2.mode)
	print("chords", track2.chords)
	#print("notes", track2.notes)

	

	print("\n\n\n\n")
	
	'''
	print("Matching " + track2.name + " to " + track1.name)
	alterations = get_alterations_for_chord_match(bearing_chords=track1.chords, matching_chords=track2.chords)
	print("Changing notes of " + track2.name)
	notes = track2.notes.copy()
	track2.notes = change_notes_from_alterations(track2.notes, alterations, "major")
	print(track2.notes)
	'''

	track2To1 = track2.matchToTrack(track1)
	track1To2 = track1.matchToTrack(track2)


	dir = "/Users/admin/Documents/BackupGoogleDrive/PyMusic/data/midi/chord-progressions/"
	for file in os.listdir(dir):
		if not "." in file[0]:
			print(dir + file)
			Track(dir + file)
	"""

    # server = Server()

    # track2.play()
    # time.sleep(60)
    # track2.stop()

    '''
	while True:
		print(midicps(69))
		synth = Synth(server, "default", { "freq" : 440.0 })
		time.sleep(1)
		synth.set("gate", 0.0)
		print(midicps(72), midicps(81))
		synth = Synth(server, "default", { "freq" : 1320.0 })
		time.sleep(1)
		synth.set("gate", 0.0)
	'''

    # LETTURA E PROCESSING FEATURE FILES
    # feature_dic = read_features(feature_file_path)
    # analyze_feature_variance(feature_dict)

    # TEST MUSICA GENERATIVA

    notes, rhythm, melody = genMelodyFromRhythm(
        rhythm=[0.125, 0.125, 0.25, 0.5, 1, 0.25, 0.125, 0.125, 0.5, 1, 0.125, 0.125, 0.25, 0.5, 1, 0.25, 0.125, 0.125,
                0.5, 1], chord=0, minpernodur=0.5)
    addMelodyToHistory(melody)
    # MELODIC_HISTORY = MELODIC_HISTORY + MELODIC_HISTORY + MELODIC_HISTORY + MELODIC_HISTORY

    showMelody(np.add(melody.T[0], 60), np.multiply(melody.T[1], 960), name="./tmp_melody.png")

    print(np.array(MELODIC_HISTORY).T[0])
    showMelody(np.add(np.array(MELODIC_HISTORY).T[0], 60), np.multiply(np.array(MELODIC_HISTORY).T[1], 960),
               name="./tmp_melodic_history.png")

    melodic_repetitions = findMelodicCells()
    print(np.array(melodic_repetitions[0]).T)
    for id, rep in enumerate(melodic_repetitions):
        showMelody(np.add(np.array(rep).T[0], 60), np.multiply(np.array(rep).T[1], 960),
                   name="./tmp_melodic_repetition" + str(id) + ".png")

# print(features)


# 2->1 [['0', 5], ['384', 1], ['768', 2], ['1152', 0], ['1536', 5], ['1920', 1], ['2304', 3]]
# 1->2 [['0', -5], ['384', -1], ['768', -2], ['1152', 0], ['1536', -5], ['1920', -1], ['2304', -3], ['2688', 0]]
