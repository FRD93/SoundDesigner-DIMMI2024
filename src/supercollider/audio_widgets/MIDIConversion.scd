(
SynthDef(\MIDICCToSignal, { | out_ch_0=0, value=1.0 |
	var signal;
	signal = K2A.ar(value);
	// signal.poll;
	ReplaceOut.ar(out_ch_0, signal);
}).writeDefFile.add;
)

// Synth(\MIDICCToSignal)