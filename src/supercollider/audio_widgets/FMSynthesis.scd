(
SynthDef(\AFM01, { | f0=100, f0bratio=1.01, ima=1, imb=2, amp=1, gate=1 |
	var f0b, osc, env, out;
	f0b = f0 * f0bratio;
	env = EnvGen.ar(Env.adsr, gate, levelScale: amp, doneAction: 2);
	osc = SinOsc.ar(f0 + SinOsc.ar(f0, Rand(0.0, 2pi), f0 * ima)) * SinOsc.ar(f0b + SinOsc.ar(f0b, Rand(0.0, 2pi), f0b * imb));
	osc = osc * env;
	Out.ar([0, 1], osc);
}).writeDefFile;

SynthDef(\AFM02, { | f0=100, f0bratio=1.01, f1=101, f1bratio=1.01, ima=1, imb=2, amp=1, gate=1 |
	var f0b, f1b, osca, oscb, osc, env, out;
	f0b = f0 * f0bratio;
	f1b = f1 * f1bratio;
	env = EnvGen.ar(Env.adsr, gate, levelScale: amp, doneAction: 2);
	osca = SinOsc.ar(f0 + SinOsc.ar(f0, Rand(0.0, 2pi), f0 * ima)) * SinOsc.ar(f0b + SinOsc.ar(f0b, Rand(0.0, 2pi), f0b * ima));
	oscb = SinOsc.ar(f1 + SinOsc.ar(f1, Rand(0.0, 2pi), f1* imb)) * SinOsc.ar(f1b + SinOsc.ar(f1b, Rand(0.0, 2pi), f1b * imb));
	osc = osca * oscb * env;
	Out.ar([0, 1], osc);

}).writeDefFile;
)


// TEST
/*
x = Synth(\AFM01, [\f0, 100, \f0bratio, 1.001, \ima, 1.0, \imb, 2.0, \gate, 1])
x.release

(
var size = 10;
size.do({ | i |
	Synth(\AFM01, [\f0, 100 * (i + 1) * 0.85, \f0bratio, 1.0 + exprand(0.01, 0.2), \ima, rrand(0.5, 3.0) * ((size - i) / size), \imb, rrand(0.5, 3.0) * ((size - i) / size), \amp, size.reciprocal, \gate, 1])
});
)


x = Synth(\AFM02, [\f0, 100, \f0bratio, 1.001, \f1, 101, \f0bratio, 1.1, \ima, 1.0, \imb, 2.0, \gate, 1])
x.release

(
var size = 3;
var freq = 263;
size.do({ | i |
	Synth(\AFM02, [\f0, freq * (i + 1), \f0bratio, 1.0 + exprand(0.01, 0.092), \f1, freq * 1.0001 * (i + 1), \f1bratio, 1.0 + exprand(0.003, 0.092), \ima, exprand(0.15, 13) * ((size - i) / size), \imb, exprand(0.15, 0.23) * ((size - i) / size), \amp, size.reciprocal, \gate, 1])
});
)
*/