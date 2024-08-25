(
SynthDef(\EnvADSR, { | out_ch_0=0, bias=0.0, attack=0.005, peak=1, decay=0.05, sustain=0.8, release=0.5, gate=0 |
	var env;
	env = Env.adsr(attack, decay, sustain, release, peak, bias: bias);
	env = EnvGen.ar(env, gate);
	Out.ar(out_ch_0, env);
	Out.kr(out_ch_0, RMS.kr(env));
}).writeDefFile;

SynthDef(\EnvPerc, { | out_ch_0=0, peak=1.0, bias=0.0, attack=0.005, release=0.5, t_gate=0 |
	var env;
	env = Env.perc(attack, release, peak);
	env = EnvGen.ar(env, t_gate, levelBias: bias);
	Out.ar(out_ch_0, env);
	Out.kr(out_ch_0, RMS.kr(env));
}).writeDefFile;

SynthDef(\AmplitudeFollower, { | in_ch_0=0, out_ch_0=0, rise_t=0.1, fall_t=0.1 |
	var sig, env;
	sig = In.ar(in_ch_0, 1);
	env = Amplitude.ar(sig);
	env = Lag2UD.ar(env, rise_t, fall_t);
	Out.ar(out_ch_0, env);
	Out.kr(out_ch_0, RMS.kr(env));
}).writeDefFile;

SynthDef(\SideChain, { | in_ch_0=0, in_ch_1=1, out_ch_0=0, rise_t=0.1, fall_t=0.1 |
	var sig, env;
	sig = In.ar(in_ch_0, 1);
	env = Amplitude.ar(In.ar(in_ch_1, 1)).clip(0.0, 1.0);
	env = Lag2UD.ar(env, rise_t, fall_t);
	env = 1.0 - env;
	sig = sig * env;
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;
)












