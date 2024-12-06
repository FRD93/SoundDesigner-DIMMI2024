(
SynthDef(\Multiply, { | in_ch_0, in_ch_1, out_ch_0 |
	var op = In.ar(in_ch_0) * In.ar(in_ch_1);
	Out.ar(out_ch_0, op);
	Out.kr(out_ch_0, RMS.kr(op));
}).writeDefFile;

SynthDef(\Divide, { | in_ch_0, in_ch_1, out_ch_0 |
	var op = In.ar(in_ch_0) / In.ar(in_ch_1);
	Out.ar(out_ch_0, op);
	Out.kr(out_ch_0, RMS.kr(op));
}).writeDefFile;

SynthDef(\Add, { | in_ch_0, in_ch_1, out_ch_0 |
	var op = In.ar(in_ch_0) + In.ar(in_ch_1);
	Out.ar(out_ch_0, op);
	Out.kr(out_ch_0, RMS.kr(op));
}).writeDefFile;

SynthDef(\Subtract, { | in_ch_0, in_ch_1, out_ch_0 |
	var op = In.ar(in_ch_0) - In.ar(in_ch_1);
	Out.ar(out_ch_0, op);
	Out.kr(out_ch_0, RMS.kr(op));
}).writeDefFile;

SynthDef(\DC, { | out_ch_0, selector_value=0, a_value=0.0 |
	a_value = Select.ar(selector_value, [Lag.ar(K2A.ar(a_value), 0.001), a_value]);
	Out.ar(out_ch_0, a_value);
	Out.kr(out_ch_0, RMS.kr(a_value));
}).writeDefFile;
)
