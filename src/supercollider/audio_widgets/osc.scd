(
SynthDef(\SinOsc, { | out_ch_0=0, a_freq=440, selector_freq=0, a_mul=1, selector_mul=0, a_add=0, selector_add=0 |
	var sig;
	a_freq = Select.ar(selector_freq, [Lag.ar(K2A.ar(a_freq), 0.001), a_freq]);
	a_mul = Select.ar(selector_mul, [Lag.ar(K2A.ar(a_mul), 0.001), a_mul]);
	a_add = Select.ar(selector_add, [Lag.ar(K2A.ar(a_add), 0.001), a_add]);
	sig = SinOsc.ar(a_freq, 0, a_mul, a_add);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\LFSaw, { | out_ch_0=0, a_freq=440, selector_freq=0, a_mul=1, selector_mul=0, a_add=0, selector_add=0 |
	var sig;
	a_freq = Select.ar(selector_freq, [Lag.ar(K2A.ar(a_freq), 0.001), a_freq]);
	a_mul = Select.ar(selector_mul, [Lag.ar(K2A.ar(a_mul), 0.001), a_mul]);
	a_add = Select.ar(selector_add, [Lag.ar(K2A.ar(a_add), 0.001), a_add]);
	sig = LFSaw.ar(a_freq, 0, a_mul, a_add);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\Pulse, { | out_ch_0=0, a_freq=440, selector_freq=0, a_width=0.5, selector_width=0, a_mul=1, selector_mul=0, a_add=0, selector_add=0 |
	var sig;
	a_freq = Select.ar(selector_freq, [Lag.ar(K2A.ar(a_freq), 0.001), a_freq]);
	a_mul = Select.ar(selector_mul, [Lag.ar(K2A.ar(a_mul), 0.001), a_mul]);
	a_add = Select.ar(selector_add, [Lag.ar(K2A.ar(a_add), 0.001), a_add]);
	a_width = Select.ar(selector_width, [Lag.ar(K2A.ar(a_width), 0.001), a_width]);
	sig = LFPulse.ar(a_freq, 0, a_width, a_mul, a_add);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\LFPar, { | out_ch_0=0, a_freq=440, selector_freq=0, a_mul=1, selector_mul=0, a_add=0, selector_add=0 |
	var sig;
	a_freq = Select.ar(selector_freq, [Lag.ar(K2A.ar(a_freq), 0.001), a_freq]);
	a_mul = Select.ar(selector_mul, [Lag.ar(K2A.ar(a_mul), 0.001), a_mul]);
	a_add = Select.ar(selector_add, [Lag.ar(K2A.ar(a_add), 0.001), a_add]);
	sig = LFPar.ar(a_freq, 0, a_mul, a_add);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\LFTri, { | out_ch_0=0, a_freq=440, selector_freq=0, a_mul=1, selector_mul=0, a_add=0, selector_add=0 |
	var sig;
	a_freq = Select.ar(selector_freq, [Lag.ar(K2A.ar(a_freq), 0.001), a_freq]);
	a_mul = Select.ar(selector_mul, [Lag.ar(K2A.ar(a_mul), 0.001), a_mul]);
	a_add = Select.ar(selector_add, [Lag.ar(K2A.ar(a_add), 0.001), a_add]);
	sig = LFTri.ar(a_freq, 0, a_mul, a_add);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\WhiteNoise, { | out_ch_0=0, a_mul=1, selector_mul=0, a_add=0, selector_add=0 |
	var sig;
	a_mul = Select.ar(selector_mul, [Lag.ar(K2A.ar(a_mul), 0.001), a_mul]);
	a_add = Select.ar(selector_add, [Lag.ar(K2A.ar(a_add), 0.001), a_add]);
	sig = WhiteNoise.ar(a_mul, a_add);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\PinkNoise, { | out_ch_0=0, a_mul=1, selector_mul=0, a_add=0, selector_add=0 |
	var sig;
	a_mul = Select.ar(selector_mul, [Lag.ar(K2A.ar(a_mul), 0.001), a_mul]);
	a_add = Select.ar(selector_add, [Lag.ar(K2A.ar(a_add), 0.001), a_add]);
	sig = PinkNoise.ar(a_mul, a_add);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\BrownNoise, { | out_ch_0=0, a_mul=1, selector_mul=0, a_add=0, selector_add=0 |
	var sig;
	a_mul = Select.ar(selector_mul, [Lag.ar(K2A.ar(a_mul), 0.001), a_mul]);
	a_add = Select.ar(selector_add, [Lag.ar(K2A.ar(a_add), 0.001), a_add]);
	sig = BrownNoise.ar(a_mul, a_add);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

)















