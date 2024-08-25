# Audio processing utilities
# ©2020, Francesco Roberto Dani
# mail: f.r.d@hotmail.it
import os.path
import os
import csv
import soundfile as sf
import librosa
import pyaudio
import numpy as np
from scipy.signal import butter, lfilter, freqz
from scipy.io.wavfile import write
from array_processing import *
from audio_analysis import *
from matplotlib.pyplot import GridSpec

DEFAULT_SAMPLE_RATE = 16000


# Read a sound file, take first channel and resample to DEFAULT_SAMPLE_RATE
def readMono(path):
    data, samplerate = librosa.load(path, sr=DEFAULT_SAMPLE_RATE, dtype=np.float32)
    return normalize2(data), samplerate


def saveMono(path, data, sr=16000):
    sf.write(path, np.multiply(data, 32767).astype(np.int16), sr, subtype="PCM_16", format="WAV")
    pass


def butter_filter(data, fs=16000, btype="lowpass", cutoff=300, order=2, analog=False):
    data = np.array(data)
    nyq = 0.5 * fs
    if type(cutoff) != list:
        cutoff = cutoff / nyq
    else:
        cutoff = [c / nyq for c in cutoff]
    b, a = butter(N=order, Wn=cutoff, btype=btype, analog=analog)
    y = lfilter(b, a, data)
    return y

def squiggle_xy(a, b, c, d, i=np.arange(0.0, 2*np.pi, 0.05)):
    return np.sin(i*a)*np.cos(i*b), np.sin(i*c)*np.cos(i*d)

def squiggle_xy_to_wav(a, b, c, d, fname, freq=440, num_samples=44100, sr=44100):
    i = np.linspace(0, int(freq * num_samples / sr), num_samples)
    x, y = squiggle_xy(a, b, c, d, i)
    waveform = np.zeros(num_samples)
    for ii in range(len(x)):
        waveform[ii] = x[ii] + y[ii]
    waveform /= np.max(np.abs(waveform))
    waveform_int = np.int16(waveform * 32767)
    write(fname, sr, waveform_int)


def squiggle_xy_transition_to_wav(a, b, c, d, t_factor, fname, freq=440, num_samples=44100, sr=44100):
    i = np.linspace(0, int(freq * num_samples / sr), num_samples)
    a = np.divide(np.linspace(a * num_samples, a * t_factor * num_samples, num_samples), num_samples)
    b = np.divide(np.linspace(b * num_samples, b * t_factor * num_samples, num_samples), num_samples)
    c = np.divide(np.linspace(c * num_samples, c * t_factor * num_samples, num_samples), num_samples)
    d = np.divide(np.linspace(d * num_samples, d * t_factor * num_samples, num_samples), num_samples)
    x, y = squiggle_xy(a, b, c, d, i)
    waveform = np.zeros(num_samples)
    for ii in range(len(x)):
        waveform[ii] = x[ii] + y[ii]
    waveform /= np.max(np.abs(waveform))
    waveform_int = np.int16(waveform * 32767)
    write(fname, sr, waveform_int)


def analyze_squiggle_xy(out_path="/Users/francescodani/Desktop/squiggle/dataset/"):
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    from_ = 100
    to_ = 200
    step = 10
    max_peaks = 128
    a_ = [val / 100. for val in list(range(from_, to_, step))]
    b_ = [val / 100. for val in list(range(from_, to_, step))]
    c_ = [val / 100. for val in list(range(from_, to_, step))]
    d_ = [val / 100. for val in list(range(from_, to_, step))]
    with open(out_path + f"data_full_maxPeaks_{max_peaks}_from_{from_/100}_to_{to_/100}_step{step/100}.csv", "w") as csvfile:
        writer = csv.writer(csvfile, delimiter=";")
        header = ["a", "b", "c", "d"]
        for index in range(max_peaks):
            header.append(f"freq_ratio_{index}")
        for index in range(max_peaks):
            header.append(f"amp_ratio_{index}")
        writer.writerow(header)
        # writer.writerow(["a", "b", "c", "d", "freqs", "amps"])
        for ai, a in enumerate(a_):
            for bi, b in enumerate(b_):
                for ci, c in enumerate(c_):
                    for di, d in enumerate(d_):
                        squiggle_xy_to_wav(a, b, c, d, fname=out_path + "tmp.wav")
                        peaks, p_amps = compute_spectral_peaks_from_audio_file(out_path + "tmp.wav", n_peaks=max_peaks)

                        first_non_zero_peak = 0
                        for idx in range(len(peaks[2])):
                            if peaks[2][idx] > 0:
                                first_non_zero_peak = idx
                                break

                        freqs = peaks[2]
                        amps = p_amps[2]

                        freq_ratios = np.divide(freqs, freqs[first_non_zero_peak])
                        amp_ratios = np.divide(amps, amps[first_non_zero_peak])
                        # real_freq_ratios = [freq_ratios[0]]
                        # real_amp_ratios = [amp_ratios[0]]
                        # for amp_ratio_id, amp_ratio in enumerate(amp_ratios):
                        #     if amp_ratio_id > 0:
                        #         if amp_ratio > 0.0005:
                        #             real_freq_ratios.append(freq_ratios[amp_ratio_id])
                        #             real_amp_ratios.append(amp_ratios[amp_ratio_id])
                        # print(real_freq_ratios, real_amp_ratios)
                        # print(freq_ratios, amp_ratios)
                        row = []
                        row.append(a)
                        row.append(b)
                        row.append(c)
                        row.append(d)
                        for freq in freq_ratios:
                            row.append(freq)
                        for amp in amp_ratios:
                            row.append(amp)
                        writer.writerow(row)
                        # writer.writerow([a, b, c, d, real_freq_ratios, real_amp_ratios])


def plot_squiggle_xy_to_wav(from_=10, to_=22, step=3, out_path="/Users/francescodani/Desktop/squiggle/static/"):
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    from matplotlib import pyplot as plt
    values = [val / 10. for val in list(range(from_, to_, step))]
    for a in values:
        for b in values:
            for c in values:
                for d in values:
                    plt.clf()
                    fname = out_path + f"squiggle_xy_a{a}_b{b}_c{c}_d{d}.wav"
                    squiggle_xy_to_wav(a, b, c, d, fname=fname)
                    fig = plt.figure(figsize=(10, 10))
                    gs = GridSpec(1, 1, width_ratios=[1], height_ratios=[1])
                    ax1 = fig.add_subplot(gs[0, 0], aspect='auto')
                    ax1.plot(*squiggle_xy(a, b, c, d), label=f"Values: a={a}, b={b}, c={c}, d={d}", color="blue")
                    plt.legend()
                    plt.suptitle("sin(a)*cos(b))+(sin(c)*cos(d)", fontsize=32, ha='center')
                    plt.tight_layout()
                    plt.savefig(fname.replace("wav", "png"), dpi=300)


def plot_squiggle_xy_transition_to_wav(from_=10, to_=22, step=3, t_factor=3, out_path="/Users/francescodani/Desktop/squiggle/transition/"):
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    from matplotlib import pyplot as plt
    values = [val / 10. for val in list(range(from_, to_, step))]
    for a in values:
        for b in values:
            for c in values:
                for d in values:
                    plt.clf()
                    fname = out_path + f"squiggle_xy_a{a}_b{b}_c{c}_d{d}.wav"
                    # squiggle_xy_to_wav(a, b, c, d, fname=fname)
                    squiggle_xy_transition_to_wav(a, b, c, d, t_factor=t_factor, fname=fname)
                    fig = plt.figure(figsize=(10, 10))
                    gs = GridSpec(1, 1, width_ratios=[1], height_ratios=[1])
                    ax1 = fig.add_subplot(gs[0, 0], aspect='auto')
                    ax1.plot(*squiggle_xy(a, b, c, d), label=f"From: a={a}, b={b}, c={c}, d={d}", color="blue")
                    ax1.plot(*squiggle_xy(a*t_factor, b*t_factor, c*t_factor, d*t_factor), label=f"To: a={round(a*t_factor, 1)}, b={round(b*t_factor, 1)}, c={round(c*t_factor, 1)}, d={round(d*t_factor, 1)}", color="red")
                    plt.legend()
                    plt.suptitle("sin(a)*cos(b))+(sin(c)*cos(d)", fontsize=32, ha='center')
                    plt.tight_layout()
                    plt.savefig(fname.replace("wav", "png"), dpi=300)


if __name__ == "__main__":
    # plot_squiggle_xy_to_wav()
    analyze_squiggle_xy()
