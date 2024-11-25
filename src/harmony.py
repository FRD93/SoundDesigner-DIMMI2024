from array_processing import *

"""
In questo file sono contenute informazioni di armonia
"""

""" Nomi delle note """
NOTE_NAMES = ["C", "C#/Db", "D", "D#/Eb", "E", "F", "F#/Gb", "G", "G#/Ab", "A", "A#/Bb", "B"]

BEMOLLE_TO_DIESIS = {"Bb": "A#", "Ab": "G#", "Gb": "F#", "Fb": "E", "Eb": "D#", "Db": "C#"}

# Numeration of MIDI Notes taken here: https://www.phys.unsw.edu.au/jw/notes.html with modification for starting form C0 instead of A0
MIDI_NOTE_NAMES = {note + str(octave): 12 + note_index + (12 * octave) for note_index, note in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]) for octave in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]}

# print(f"MIDI_NOTE_NAMES: {MIDI_NOTE_NAMES}")

""" Gradi delle scale musicali in note MIDI """
MUSICAL_SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
}

""" Accordi delle scale maggiori """
CHORDS_OF_MAJOR_SCALES = {
    #         1°       2°         3°         4°       5°         6°        7°
    "C": ["C", "Dm", "Em", "F", "G7", "Am", "Bdim"],
    "C#/Db": ["C#/Db", "D#m/Ebm", "Fm", "Gb", "G#7/Ab7", "A#m/Bm", "Cdim"],
    "D": ["D", "Em", "F#m", "G", "A7", "Bm", "C#dim"],
    "D#/Eb": ["D#/Eb", "Fm", "Gm", "G#/Ab", "A#7/Bb7", "Cm", "Ddim"],
    "E": ["E", "F#m", "G#m", "A", "B7", "C#m", "D#dim"],
    "F": ["F", "Gm", "Am", "Bb", "C7", "Dm", "Edim"],
    "F#/Gb": ["F#/Gb", "G#m/Abm", "A#m/Bbm", "B", "C#7/Db7", "D#m/Ebm", "E#dim/Fdim"],
    "G": ["G", "Am", "Bm", "C", "D7", "Em", "F#dim"],
    "G#/Ab": ["G#/Ab", "A#m/Bbm", "Cm", "C#/Db", "D#7/Eb7", "E#m/Fm", "Gdim"],
    "A": ["A", "Bm", "C#m", "D", "E7", "F#m", "G#dim"],
    "A#/Bb": ["A#/Bb", "Cm", "Dm", "Eb", "F7", "Gm", "Adim"],
    "B": ["B", "C#m/Dbm", "D#m/Ebm", "E", "F#7", "G#m", "A#dim"]
}

""" Cellule melodiche """
MELODIC_CELLS = []

""" Storia degli eventi nota (noteEvent: [midinote, notedelta]) """
MELODIC_HISTORY = []

""" Movimenti melodici di 2, 3 o 4 note successive """
MELODIC_MOVIMENTI = {
    "2": {},
    "3": {},
    "4": {}
}

""" Feature dei Movimenti melodici """
MELODIC_MOVIMENTI_FEAT = ["Distance", "DistanceFrom", "DistanceTo", "Mean", "Std", "AbsDerivativeMean",
                          "DerivativeMean", "DerivativeMin", "DerivativeMax", "Andamento"]
MELODIC_MOVIMENTI_FEAT_SIZE = len(MELODIC_MOVIMENTI_FEAT)
for id in ["2", "3", "4"]:
    MELODIC_MOVIMENTI[id]["Indexes"] = []
    MELODIC_MOVIMENTI[id]["Notes"] = []
    MELODIC_MOVIMENTI[id]["Distance"] = []
    MELODIC_MOVIMENTI[id]["DistanceFrom"] = []
    MELODIC_MOVIMENTI[id]["DistanceTo"] = []
    MELODIC_MOVIMENTI[id]["Mean"] = []
    MELODIC_MOVIMENTI[id]["Std"] = []
    MELODIC_MOVIMENTI[id]["AbsDerivativeMean"] = []
    MELODIC_MOVIMENTI[id]["DerivativeMean"] = []
    MELODIC_MOVIMENTI[id]["DerivativeMin"] = []
    MELODIC_MOVIMENTI[id]["DerivativeMax"] = []
    MELODIC_MOVIMENTI[id]["Andamento"] = []

index = 0
for note1 in range(0, 7):
    for note2 in range(0, 7):
        if note1 != note2:
            mean = (note1 - note2) / 2
            MELODIC_MOVIMENTI["2"]["Indexes"].append(index)
            index += 1
            MELODIC_MOVIMENTI["2"]["DistanceFrom"].append(note1)
            MELODIC_MOVIMENTI["2"]["DistanceTo"].append(note2)
            MELODIC_MOVIMENTI["2"]["Distance"].append(note2 - note1)
            MELODIC_MOVIMENTI["2"]["Mean"].append(mean)
            MELODIC_MOVIMENTI["2"]["Std"].append((((note1 - mean) ** 2) + ((note2 - mean) ** 2)) / 2)
            MELODIC_MOVIMENTI["2"]["AbsDerivativeMean"].append(abs(note2 - note1) / 2)
            MELODIC_MOVIMENTI["2"]["DerivativeMean"].append((note2 - note1) / 2)
            MELODIC_MOVIMENTI["2"]["DerivativeMin"].append(note2 - note1)
            MELODIC_MOVIMENTI["2"]["DerivativeMax"].append(note2 - note1)
            MELODIC_MOVIMENTI["2"]["Notes"].append([note1, note2])
            if (note2 - note1) > 0:
                MELODIC_MOVIMENTI["2"]["Andamento"].append(1)
            elif (note2 - note1) < 0:
                MELODIC_MOVIMENTI["2"]["Andamento"].append(-1)
            else:
                MELODIC_MOVIMENTI["2"]["Andamento"].append(0)

index = 0
for note1 in range(0, 7):
    for note2 in range(0, 7):
        for note3 in range(0, 7):
            if (note1 != note2) and (note3 != note2):
                mean = (note1 + note2 + note3) / 3
                MELODIC_MOVIMENTI["2"]["Indexes"].append(index)
                index += 1
                MELODIC_MOVIMENTI["3"]["DistanceFrom"].append(note1)
                MELODIC_MOVIMENTI["3"]["DistanceTo"].append(note3)
                MELODIC_MOVIMENTI["3"]["Distance"].append(note3 - note1)
                MELODIC_MOVIMENTI["3"]["Mean"].append(mean)
                MELODIC_MOVIMENTI["3"]["Std"].append(
                    (((note1 - mean) ** 2) + ((note2 - mean) ** 2) + ((note3 - mean) ** 2)) / 3)
                MELODIC_MOVIMENTI["3"]["AbsDerivativeMean"].append((abs(note2 - note1) + abs(note3 - note2)) / 3)
                MELODIC_MOVIMENTI["3"]["DerivativeMean"].append(((note2 - note1) + (note3 - note2)) / 3)
                MELODIC_MOVIMENTI["3"]["DerivativeMin"].append(min([note2 - note1, note3 - note2]))
                MELODIC_MOVIMENTI["3"]["DerivativeMax"].append(max([note2 - note1, note3 - note2]))
                MELODIC_MOVIMENTI["3"]["Notes"].append([note1, note2, note3])
                if (note2 - note1) > 0 and (note3 - note2) > 0:
                    MELODIC_MOVIMENTI["3"]["Andamento"].append(1)
                elif (note2 - note1) < 0 and (note3 - note2) < 0:
                    MELODIC_MOVIMENTI["3"]["Andamento"].append(-1)
                else:
                    MELODIC_MOVIMENTI["3"]["Andamento"].append(0)

index = 0
for note1 in range(0, 7):
    for note2 in range(0, 7):
        for note3 in range(0, 7):
            for note4 in range(0, 7):
                if (note1 != note2) and (note3 != note2) and (note4 != note3):
                    mean = (note1 + note2 + note3 + note4) / 4
                    MELODIC_MOVIMENTI["2"]["Indexes"].append(index)
                    index += 1
                    MELODIC_MOVIMENTI["4"]["DistanceFrom"].append(note1)
                    MELODIC_MOVIMENTI["4"]["DistanceTo"].append(note4)
                    MELODIC_MOVIMENTI["4"]["Distance"].append(note4 - note1)
                    MELODIC_MOVIMENTI["4"]["Mean"].append(mean)
                    MELODIC_MOVIMENTI["4"]["Std"].append((((note1 - mean) ** 2) + ((note2 - mean) ** 2) + (
                                (note3 - mean) ** 2) + ((note4 - mean) ** 2)) / 4)
                    MELODIC_MOVIMENTI["4"]["AbsDerivativeMean"].append(
                        (abs(note2 - note1) + abs(note3 - note2) + abs(note4 - note3)) / 4)
                    MELODIC_MOVIMENTI["4"]["DerivativeMean"].append(
                        ((note2 - note1) + (note3 - note2) + (note4 - note3)) / 4)
                    MELODIC_MOVIMENTI["4"]["DerivativeMin"].append(min([note2 - note1, note3 - note2, note4 - note3]))
                    MELODIC_MOVIMENTI["4"]["DerivativeMax"].append(max([note2 - note1, note3 - note2, note4 - note3]))
                    MELODIC_MOVIMENTI["4"]["Notes"].append([note1, note2, note3, note4])
                    if (note2 - note1) > 0 and (note3 - note2) > 0:
                        MELODIC_MOVIMENTI["4"]["Andamento"].append(1)
                    elif (note2 - note1) < 0 and (note3 - note2) < 0:
                        MELODIC_MOVIMENTI["4"]["Andamento"].append(-1)
                    else:
                        MELODIC_MOVIMENTI["4"]["Andamento"].append(0)

""" KDTree (normalizzato) di Movimenti melodici di 2, 3 o 4 note successive """
MELODIC_MOVIMENTI_KDTREE = {
    "2": buildKDTree([normalize(np.array(MELODIC_MOVIMENTI["2"][feat])) for feat in MELODIC_MOVIMENTI_FEAT]),
    "3": buildKDTree([normalize(np.array(MELODIC_MOVIMENTI["3"][feat])) for feat in MELODIC_MOVIMENTI_FEAT]),
    "4": buildKDTree([normalize(np.array(MELODIC_MOVIMENTI["4"][feat])) for feat in MELODIC_MOVIMENTI_FEAT])
}


if __name__ == "__main__":
    print(MUSICAL_SCALES["minor"])
    a = MUSICAL_SCALES["major"]
    a = [[48, 49], [46, 46], [50, 51]]
    a_flop = list(map(list, zip(*a)))
    print(a_flop)
    print(46 in a_flop[0])
    print(MELODIC_MOVIMENTI_KDTREE)
    print("MIDI_NOTE_NAMES:", MIDI_NOTE_NAMES)
