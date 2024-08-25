import os
import essentia
import essentia.standard
import librosa
from scipy.signal import lfilter, savgol_filter, find_peaks
from array_processing import *
import numpy as np
import matplotlib.pyplot as plt
import time
from classes import *
from functions import *


def compute_spectral_peaks_essentia(filepath, n_peaks=20, n_fft=1024, win_size=512, hop_size=256):
    loader = essentia.standard.MonoLoader(filename=filepath)
    audio = loader()
    win = essentia.standard.Windowing(type='hann')
    spectrum = essentia.standard.Spectrum(size=n_fft)
    spec_peaks = essentia.standard.SpectralPeaks(minFrequency=100, maxFrequency=15000)
    mags = []
    peaks = []
    peak_amps = []
    min_min = 1e7
    for frame in essentia.standard.FrameGenerator(audio, frameSize=win_size, hopSize=hop_size, startFromZero=True):
        magnitudes = spectrum(win(frame))
        mags.append(magnitudes)
        res = spec_peaks(magnitudes)
        peaks.append(res[0])
        peak_amps.append(res[1])

        min_min = min(min_min, min(len(res[0]), len(res[1])))
    print("min min:", min_min)
    peaks = np.array([peak[:min_min] for peak in peaks])
    # peaks = savgol_filter(peaks, window_length=2, polyorder=1, axis=0)
    peak_amps = np.array([peak[:min_min] for peak in peak_amps])
    # peak_amps = savgol_filter(peak_amps, window_length=2, polyorder=1, axis=0)
    print("Peaks:", peaks)
    return peaks, peak_amps

def compute_spectral_peaks_from_audio_file(filepath, n_peaks=20, n_fft=2048, win_size=1024, hop_size=256):
    data, sr = librosa.load(filepath)
    stft = librosa.stft(data, n_fft=n_fft, win_length=win_size, hop_length=hop_size).T
    fft_freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    mags = np.abs(stft)
    peaks = [find_peaks(mag, distance=15)[0] for mag in mags]
    amplitudes = [mags[index][peak][:n_peaks] for index, peak in enumerate(peaks)]
    frequencies = [fft_freqs[peak][:n_peaks] for index, peak in enumerate(peaks)]
    sortings = []
    for index, frqs in enumerate(frequencies):
        while len(frequencies[index]) < n_peaks:
            frequencies[index] = np.concatenate((frequencies[index], [0]))
        sortings.append(np.argsort(frequencies[index]))
        frequencies[index] = frequencies[index][sortings[-1]]
    for index, amps in enumerate(amplitudes):
        while len(amplitudes[index]) < n_peaks:
            amplitudes[index] = np.concatenate((amplitudes[index], [0]))
        amplitudes[index] = amplitudes[index][sortings[index]]
    # frequencies = savgol_filter(np.array(frequencies), window_length=18, polyorder=3, axis=0)
    # amplitudes = savgol_filter(np.array(amplitudes), window_length=18, polyorder=3, axis=0)
    return frequencies, amplitudes


def compute_onsets_detection_essentia(filepath, method="complex", samplerate=44100, win_size=1024, hop_size=512):  # method: one of ["hfc", "complex"]
    loader = essentia.standard.MonoLoader(filename=filepath, sampleRate=samplerate)
    audio = loader()
    if method == "hfc":
        od = essentia.standard.OnsetDetection(method='hfc')
    else:
        od = essentia.standard.OnsetDetection(method='complex')
    w = essentia.standard.Windowing(type='hann')
    fft = essentia.standard.FFT()
    c2p = essentia.standard.CartesianToPolar()
    pool = essentia.Pool()
    for frame in essentia.standard.FrameGenerator(audio, frameSize=win_size, hopSize=hop_size):
        magnitude, phase = c2p(fft(w(frame)))
        if method == "hfc":
            pool.add('odf.hfc', od(magnitude, phase))
        else:
            pool.add('odf.complex', od(magnitude, phase))
    onsets = essentia.standard.Onsets()
    if method == "hfc":
        onsets = onsets(essentia.array([pool['odf.hfc']]), [1])
    else:
        onsets = onsets(essentia.array([pool['odf.complex']]), [1])
    return onsets

def compute_onsets_features_essentia(filepath, samplerate=44100, win_size=1024, hop_size=512, maskbinwidth=2, attenuation_dB=100):  # onsets_method: one of ["hfc", "complex"]
    loader = essentia.standard.MonoLoader(filename=filepath, sampleRate=samplerate)
    audio = loader()
    od_hfc = essentia.standard.OnsetDetection(method='hfc')
    od_com = essentia.standard.OnsetDetection(method='complex')
    w = essentia.standard.Windowing(type='hann')
    fft = essentia.standard.FFT()
    c2p = essentia.standard.CartesianToPolar()
    pool = essentia.Pool()
    for frame in essentia.standard.FrameGenerator(audio, frameSize=win_size, hopSize=hop_size):
        magnitude, phase = c2p(fft(w(frame)))
        pool.add('odf.hfc', od_hfc(magnitude, phase))
        pool.add('odf.complex', od_com(magnitude, phase))
    onsets = essentia.standard.Onsets()
    onsets = onsets(essentia.array([pool['odf.complex']]), [1])
    pExt = essentia.standard.PredominantPitchMelodia(frameSize=win_size, hopSize=hop_size)
    pitch, pitchConf = pExt(audio)
    onsets_frame_indexes = [int(onset * samplerate / hop_size) for onset in onsets]
    onsets_pitchs = np.array([pitch[pindex] for pindex in onsets_frame_indexes])
    onsets_hfcs = np.array([pool['odf.hfc'][pindex] for pindex in onsets_frame_indexes])
    return onsets, onsets_pitchs, onsets_hfcs


def onsets_features_to_midi_notes(onsets, onsets_pitchs):
    output = []
    midi_onsets = [int(onset * PPQN) for onset in onsets]
    midi_notes = [cpsmidi(pitch) if pitch > 0 else 0 for pitch in onsets_pitchs]
    for i in range(len(midi_onsets)):
        if midi_notes[i] > 0:
            if i < len(midi_notes) - 1:
                duration = midi_onsets[i + 1] - midi_onsets[i]
            else:
                duration = PPQN * 2
            output.append(Note(midi_notes[i], 127, midi_onsets[i], duration))
    return output


if __name__ == '__main__':
    test = "onsets features"
    # test = "features"
    # test = "peaks"
    if test == "onsets":
        """ Test Onsets Extraction """
        o = compute_onsets_detection_essentia('/Users/francescodani/Documents/Insegnamento/SintesiConSuperCollider/SintesiAdditiva/04 Heart of Gold.wav',
                                            method="complex")
        print(o)
    elif test == "onsets features":
        """ Test Onsets Features Extraction (onsets, pitchs, hfcs) """
        o, p, h = compute_onsets_features_essentia('/Users/francescodani/Documents/Insegnamento/SintesiConSuperCollider/SintesiAdditiva/04 Heart of Gold.wav')
        print(o)
        print(p)
        print(h)
        notes = onsets_features_to_midi_notes(o, p)
        midi_clip = MIDIClip(custom_data={
            "name": "test",
            "notes": notes,
            "chords": [],
            "bpm": 120,
            "key": "C",
            "mode": "major"
        })
        for note in notes:
            note.describe()
    elif test == "peaks":
        """ Test SpectralPeaks Extraction """
        filepath = '/Users/francescodani/Documents/Insegnamento/SintesiConSuperCollider/SintesiAdditiva/Tromba.WAV'
        # filepath = '/Users/francescodani/Documents/Insegnamento/SintesiConSuperCollider/SintesiAdditiva/Domanda.wav'
        # filepath = '/Users/francescodani/Documents/Insegnamento/SintesiConSuperCollider/SintesiAdditiva/04 Heart of Gold.wav'
        # filepath = '/Users/francescodani/Documents/Insegnamento/SintesiConSuperCollider/SintesiAdditiva/CampioniOrchestra/1.WAV'
        # filepath = '/Users/francescodani/Desktop/Vocali.wav'
        filename = os.path.splitext(os.path.basename(filepath))[0]
        print(filename)
        f, a = compute_spectral_peaks_essentia(filepath)
        print(f"Freq shape: {f.shape}")
        print(f"Amp shape: {a.shape}")
        with open(os.path.abspath("../SoundDesigner/data/AdditiveAnalysis/" + filename + ".txt"), "w") as txt:
            txt.write(f"frequencies: {[list(ff) for ff in f]}\nmagnitudes: {[list(aa) for aa in a]}")
        f = f.T
        for ff in f:
            plt.plot(ff)
        plt.show()
