(
SynthDef(\FM1, { | out_ch_0, out_ch_1, freq=440, a_imod=1, a_gain=1.0, a_pan=0, gate=1 |
	var sig, env;
	// a_gain.poll;
	env = EnvGen.ar(Env.adsr(), gate: gate, levelScale: a_gain, doneAction: 2);
	sig = SinOsc.ar(freq + SinOsc.ar(freq, 0, freq * a_imod * env), 0, env);
	sig = Pan2.ar(sig, a_pan);
	Out.ar(out_ch_0, sig[0]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;
)