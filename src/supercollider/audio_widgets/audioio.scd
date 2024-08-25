(
SynthDef(\AudioIn_1, { | in_ch=0, out_ch_0=120 |
	var in0 = SoundIn.ar(in_ch);
	// in0.poll;
	Out.ar(out_ch_0, in0);
	Out.kr(out_ch_0, RMS.kr(in0));
}).writeDefFile;

SynthDef(\AudioIn_2, { | in_ch_0=0, out_ch_0=0, out_ch_1=1 |
	var in0 = SoundIn.ar(in_ch_0);
	var in1 = SoundIn.ar(in_ch_0 + 1);
	Out.ar(out_ch_0, in0);
	Out.ar(out_ch_1, in1);
	Out.kr(out_ch_0, RMS.kr(in0));
	Out.kr(out_ch_0, RMS.kr(in1));
}).writeDefFile;

SynthDef(\AudioOut_1, { | in_ch_0=120, out_ch=0 |
	var out_sig;
	out_sig = In.ar(in_ch_0, 1);
	// out_sig.poll;
	Out.ar(out_ch, out_sig);
}).writeDefFile;

SynthDef(\AudioOut_2, { | in_ch_0=0, in_ch_1=1, out_ch_0=0 |
	Out.ar(out_ch_0, [In.ar(in_ch_0, 1), In.ar(in_ch_1, 1)]);
}).writeDefFile;

SynthDef(\SubPatchAlias, { | in_ch_0=120, out_ch_0=0 |
	var out_sig;
	out_sig = In.ar(in_ch_0, 1);
	// out_sig.poll;
	Out.ar(out_ch_0, out_sig);
}).writeDefFile;

)

// .writeDefFile(dir: "".resolveRelative ++ "build/audioio")