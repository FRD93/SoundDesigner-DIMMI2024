(
SynthDef(\TRand, { | in_ch_0=0, out_ch_0=0, selector_from=0, a_from=1, selector_to=0, a_to=1 |
	var sig;
	a_from = Select.ar(selector_from, [Lag.ar(K2A.ar(a_from), 0.001), a_from]);
	a_to = Select.ar(selector_to, [Lag.ar(K2A.ar(a_to), 0.001), a_to]);
	sig = In.ar(in_ch_0, 1);
	sig = TRand.ar(a_from, a_to, sig);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\TExpRand, { | in_ch_0=0, out_ch_0=0, selector_from=0, a_from=1, selector_to=0, a_to=1 |
	var sig;
	a_from = Select.ar(selector_from, [Lag.ar(K2A.ar(a_from), 0.001), a_from]).clip(0.00001, inf);
	a_to = Select.ar(selector_to, [Lag.ar(K2A.ar(a_to), 0.001), a_to]).clip(0.00001, inf);
	sig = In.ar(in_ch_0, 1);
	sig = TExpRand.ar(a_from, a_to, sig);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile.add;
)