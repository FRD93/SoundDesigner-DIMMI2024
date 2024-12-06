(
SynthDef(\FM1, { | out_ch_0=4096, out_ch_1=4096, freq=440, a_imod=1, a_gain=1.0, a_pan=0, gate=1 |
	var sig, env;
	env = EnvGen.ar(Env.adsr(), gate: gate, levelScale: a_gain, doneAction: 2);
	sig = SinOsc.ar(freq + SinOsc.ar(freq, 0, freq * a_imod * env), 0, env);
	sig = Pan2.ar(sig, a_pan);
	Out.ar(out_ch_0, sig[0]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;

SynthDef(\GrainFM, { | out_ch_0=4096, out_ch_1=4096, freq=440, a_imod=1, selector_gain=0, a_gain=1.0, selector_pan=0, a_pan=0.0, selector_atk=0, a_atk=0.5, selector_dur=0, a_dur=1.0, gate=1 |
	var sig, env;
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_pan = Select.ar(selector_pan, [Lag.ar(K2A.ar(a_pan), 0.001), a_pan]);
	a_pan = Gate.ar(a_pan, Impulse.ar(0));
	a_dur = Select.ar(selector_dur, [Lag.ar(K2A.ar(a_dur), 0.001), a_dur]);
	a_atk = Select.ar(selector_atk, [Lag.ar(K2A.ar(a_atk), 0.001), a_atk]);
	env = EnvGen.ar(Env.new([0, 1, 0], [a_atk, 1.0 - a_atk], [4, -4]), gate: gate, levelScale: a_gain, timeScale: a_dur, doneAction: 2);
	sig = SinOsc.ar(freq + SinOsc.ar(freq, 0, freq * a_imod * env), 0, env);
	sig = Pan2.ar(sig, a_pan);
	Out.ar(out_ch_0, sig[0]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;

SynthDef(\AudioTrigger, { | out_ch_0=4096 |
	var sig, env;
	env = EnvGen.ar(Env.new([0,0], [0.001]), doneAction: 2); // wait 1ms, then clear synth
	sig = Impulse.ar(0);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\SineGrain, { | out_ch_0=4096, out_ch_1=4096, pitch=1440.0, phase=0, gain=1.0, pan=0.0, atk=0.5, dur=1.0, gate=1 |
	var sig, env;
	env = EnvGen.ar(Env.new([0, 1, 0], [atk, 1.0 - atk], [4, -4]), gate: gate, levelScale: gain, timeScale: dur, doneAction: 2);
	sig = SinOsc.ar(pitch, phase, env);
	sig = Pan2.ar(sig, pan);
	Out.ar(out_ch_0, sig[0]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;

SynthDef(\AMGrain, { | out_ch_0=4096, out_ch_1=4096, pitch=1440.0, phase=0, gain=1.0, imod=1.0, pan=0.0, atk=0.5, dur=1.0, gate=1 |
	var sig, env;
	env = EnvGen.ar(Env.new([0, 1, 0], [atk, 1.0 - atk], [4, -4]), gate: gate, levelScale: gain, timeScale: dur, doneAction: 2);
	sig = SinOsc.ar(pitch, phase, env) * SinOsc.ar(pitch, 0, imod / 2, imod / 2);
	sig = Pan2.ar(sig, pan);
	Out.ar(out_ch_0, sig[0]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;

SynthDef(\FMGrain, { | out_ch_0=4096, out_ch_1=4096, pitch=1440.0, phase=0, gain=1.0, fmod=1440.0, imod=1.0, pan=0.0, atk=0.5, dur=1.0, gate=1 |
	var sig, env;
	env = EnvGen.ar(Env.new([0, 1, 0], [atk, 1.0 - atk], [4, -4]), gate: gate, levelScale: gain, timeScale: dur, doneAction: 2);
	sig = SinOsc.ar(pitch + SinOsc.ar(fmod, 0.0, fmod * imod), phase, env);
	sig = Pan2.ar(sig, pan);
	Out.ar(out_ch_0, sig[0]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;

SynthDef(\InGrain, { | in_ch_0=0, out_ch_0=4096, out_ch_1=4096, pitch=1440.0, gain=1.0, delay=0.0, pan=0.0, atk=0.5, dur=1.0, gate=1 |
	var sig, env;
	env = EnvGen.ar(Env.new([0, 1, 0, 0], [atk * dur, 1.0 - (atk * dur), delay], [4, -4, 0]), gate: gate, levelScale: gain, doneAction: 2);
	sig = In.ar(in_ch_0, 1) * env;
	// sig = DelayC.ar(sig, 0.2, delay);
	sig = Pan2.ar(sig, pan);
	Out.ar(out_ch_0, sig[0]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;
)









