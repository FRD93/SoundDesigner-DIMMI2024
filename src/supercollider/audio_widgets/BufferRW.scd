(
SynthDef(\BufferWrite, { | in_ch_0, bufnum, a_gain=10.0 |
	var in, read, old, erease_trig, erease_env, bufdur, write_signal;
	bufdur = BufDur.ir(bufnum);
	erease_trig = Trig.ar(K2A.ar(-1 * a_gain)); // Reverse gain signal to catch "erease" triggers
	erease_env = EnvGen.ar(Env.new([1, 0, 0, 1], [0.01, bufdur, 0.01], [-2, 0, 2]), erease_trig, doneAction: 0);
	in = In.ar(in_ch_0, 1);
	read = Phasor.ar(0, BufRateScale.kr(bufnum), 0, BufFrames.kr(bufnum));
	old = BufRd.ar(1, bufnum, read);
	write_signal = (in * Lag2.ar(Amplitude.ar(in) * a_gain, 0.01).clip(0.0, 1.0)) + (old * (1.0 - Lag2.ar(Amplitude.ar(in) * a_gain, 0.01).clip(0.0, 1.0)));
	write_signal = write_signal * erease_env;
	BufWr.ar(write_signal, bufnum, read);
	0.0
}).writeDefFile.add;

SynthDef(\BufferRead, { | bufnum, out_ch_0, rate=1.0, a_gain=1.0 |
	var read, sig;
	read = Phasor.ar(0, BufRateScale.kr(bufnum) * rate, 0, BufFrames.kr(bufnum));
	sig = BufRd.ar(1, bufnum, read) * a_gain;
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile.add;
)

// Test
/*
s.options.device_("MOTU_IN_MAC_OUT")
s.options.device_("Mac_IO")

b = Buffer.alloc(s, 44100 * 0.5);
x = Synth(\BufferWrite, [\in_ch_0, 2, \bufnum, b, \a_gain, 10])
y = Synth(\BufferRead, [\out_ch_0, 0, \bufnum, b, \a_gain, 0.75])
b.plot
x.free

s.sendMsg("/s_new", \BufferWrite, -1, 0, 0, \bufnum, b);
*/