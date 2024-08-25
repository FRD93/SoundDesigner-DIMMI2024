(
SynthDef(\LPF_1, { | in_ch_0=0, out_ch_0=120, a_cutoff=20000, selector_cutoff=0, a_gain=1.0, selector_gain=0 |
	var in0, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	in0 = In.ar(in_ch_0, 1);
	sig = LPF.ar(in0, a_cutoff, a_gain);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\LPF_2, { | in_ch_0=0, in_ch_1=1, out_ch_0=120, out_ch_1=121, a_cutoff=20000, selector_cutoff=0, a_gain=1.0, selector_gain=0 |
	var in0, in1, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	in0 = In.ar(in_ch_0, 1);
	in1 = In.ar(in_ch_1, 1);
	sig = LPF.ar([in0, in1], a_cutoff, a_gain);
	Out.ar(out_ch_0, sig[0]);
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;

SynthDef(\HPF_1, { | in_ch_0=0, out_ch_0=120, a_cutoff=100, selector_cutoff=0, a_gain=1.0, selector_gain=0 |
	var in0, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	in0 = In.ar(in_ch_0, 1);
	sig = HPF.ar(in0, a_cutoff, a_gain);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\HPF_2, { | in_ch_0=0, in_ch_1=1, out_ch_0=120, out_ch_1=121, a_cutoff=100, selector_cutoff=0, a_gain=1.0, selector_gain=0 |
	var in0, in1, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	in0 = In.ar(in_ch_0, 1);
	in1 = In.ar(in_ch_1, 1);
	sig = HPF.ar([in0, in1], a_cutoff, a_gain);
	Out.ar(out_ch_0, sig[0]);
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;

SynthDef(\BLowPass_1, { | in_ch_0=0, out_ch_0=120, a_cutoff=20000, selector_cutoff=0, a_rq=1.0, selector_rq=0, a_gain=1.0, selector_gain=0 |
	var in0, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_rq = Select.ar(selector_rq, [Lag.ar(K2A.ar(a_rq), 0.001), a_rq]);
	in0 = In.ar(in_ch_0, 1);
	sig = BLowPass.ar(in0, a_cutoff, a_rq, a_gain);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\BLowPass_2, { | in_ch_0=0, in_ch_1=1, out_ch_0=120, out_ch_1=121, a_cutoff=20000, selector_cutoff=0, a_rq=1.0, selector_rq=0, a_gain=1.0, selector_gain=0 |
	var in0, in1, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_rq = Select.ar(selector_rq, [Lag.ar(K2A.ar(a_rq), 0.001), a_rq]);
	in0 = In.ar(in_ch_0, 1);
	in1 = In.ar(in_ch_1, 1);
	sig = BLowPass.ar([in0, in1], a_cutoff, a_rq, a_gain);
	Out.ar(out_ch_0, sig[0]);
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;

SynthDef(\BHiPass_1, { | in_ch_0=0, out_ch_0=120, a_cutoff=20000, selector_cutoff=0, a_rq=1.0, selector_rq=0, a_gain=1.0, selector_gain=0 |
	var in0, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_rq = Select.ar(selector_rq, [Lag.ar(K2A.ar(a_rq), 0.001), a_rq]);
	in0 = In.ar(in_ch_0, 1);
	sig = BHiPass.ar(in0, a_cutoff, a_rq, a_gain);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\BHiPass_2, { | in_ch_0=0, in_ch_1=1, out_ch_0=120, out_ch_1=121, a_cutoff=20000, selector_cutoff=0, a_rq=1.0, selector_rq=0, a_gain=1.0, selector_gain=0 |
	var in0, in1, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_rq = Select.ar(selector_rq, [Lag.ar(K2A.ar(a_rq), 0.001), a_rq]);
	in0 = In.ar(in_ch_0, 1);
	in1 = In.ar(in_ch_1, 1);
	sig = BHiPass.ar([in0, in1], a_cutoff, a_rq, a_gain);
	Out.ar(out_ch_0, sig[0]);
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;

SynthDef(\BLowPass4_1, { | in_ch_0=0, out_ch_0=120, a_cutoff=20000, selector_cutoff=0, a_rq=1.0, selector_rq=0, a_gain=1.0, selector_gain=0 |
	var in0, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_rq = Select.ar(selector_rq, [Lag.ar(K2A.ar(a_rq), 0.001), a_rq]);
	in0 = In.ar(in_ch_0, 1);
	sig = BLowPass4.ar(in0, a_cutoff, a_rq, a_gain);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\BLowPass4_2, { | in_ch_0=0, in_ch_1=1, out_ch_0=120, out_ch_1=121, a_cutoff=20000, selector_cutoff=0, a_rq=1.0, selector_rq=0, a_gain=1.0, selector_gain=0 |
	var in0, in1, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_rq = Select.ar(selector_rq, [Lag.ar(K2A.ar(a_rq), 0.001), a_rq]);
	in0 = In.ar(in_ch_0, 1);
	in1 = In.ar(in_ch_1, 1);
	sig = BLowPass4.ar([in0, in1], a_cutoff, a_rq, a_gain);
	Out.ar(out_ch_0, sig[0]);
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;

SynthDef(\BHiPass4_1, { | in_ch_0=0, out_ch_0=120, a_cutoff=20000, selector_cutoff=0, a_rq=1.0, selector_rq=0, a_gain=1.0, selector_gain=0 |
	var in0, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_rq = Select.ar(selector_rq, [Lag.ar(K2A.ar(a_rq), 0.001), a_rq]);
	in0 = In.ar(in_ch_0, 1);
	sig = BHiPass4.ar(in0, a_cutoff, a_rq, a_gain);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\BHiPass4_2, { | in_ch_0=0, in_ch_1=1, out_ch_0=120, out_ch_1=121, a_cutoff=20000, selector_cutoff=0, a_rq=1.0, selector_rq=0, a_gain=1.0, selector_gain=0 |
	var in0, in1, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_rq = Select.ar(selector_rq, [Lag.ar(K2A.ar(a_rq), 0.001), a_rq]);
	in0 = In.ar(in_ch_0, 1);
	in1 = In.ar(in_ch_1, 1);
	sig = BHiPass4.ar([in0, in1], a_cutoff, a_rq, a_gain);
	Out.ar(out_ch_0, sig[0]);
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;

SynthDef(\BLowShelf_1, { | in_ch_0=0, out_ch_0=120, a_cutoff=20000, selector_cutoff=0, a_rS=1, selector_rS=0, a_dB=0, selector_dB=0, a_gain=1.0, selector_gain=0 |
	var in0, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_rS = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(selector_rS), 0.001), a_rS]);
	a_dB = Select.ar(selector_dB, [Lag.ar(K2A.ar(a_dB), 0.001), a_dB]);
	in0 = In.ar(in_ch_0, 1);
	sig = BLowShelf.ar(in0, a_cutoff, a_rS, a_dB, a_gain);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\BLowShelf_2, { | in_ch_0=0, in_ch_1=1, out_ch_0=120, out_ch_1=121, a_cutoff=20000, selector_cutoff=0, a_rS=1, selector_rS=0, a_dB=0, selector_dB=0, a_gain=1.0, selector_gain=0 |
	var in0, in1, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_rS = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(selector_rS), 0.001), a_rS]);
	a_dB = Select.ar(selector_dB, [Lag.ar(K2A.ar(a_dB), 0.001), a_dB]);
	in0 = In.ar(in_ch_0, 1);
	in1 = In.ar(in_ch_1, 1);
	sig = BLowShelf.ar([in0, in1], a_cutoff, a_rS, a_dB);
	Out.ar(out_ch_0, sig[0]);
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;

SynthDef(\BHiShelf_1, { | in_ch_0=0, out_ch_0=120, a_cutoff=20000, selector_cutoff=0, a_rS=1, selector_rS=0, a_dB=0, selector_dB=0, a_gain=1.0, selector_gain=0 |
	var in0, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_rS = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(selector_rS), 0.001), a_rS]);
	a_dB = Select.ar(selector_dB, [Lag.ar(K2A.ar(a_dB), 0.001), a_dB]);
	in0 = In.ar(in_ch_0, 1);
	sig = BHiShelf.ar(in0, a_cutoff, a_rS, a_dB, a_gain);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\BHiShelf_2, { | in_ch_0=0, in_ch_1=1, out_ch_0=120, out_ch_1=121, a_cutoff=20000, selector_cutoff=0, a_rS=1, selector_rS=0, a_dB=0, selector_dB=0, a_gain=1.0, selector_gain=0 |
	var in0, in1, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_rS = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(selector_rS), 0.001), a_rS]);
	a_dB = Select.ar(selector_dB, [Lag.ar(K2A.ar(a_dB), 0.001), a_dB]);
	in0 = In.ar(in_ch_0, 1);
	in1 = In.ar(in_ch_1, 1);
	sig = BHiShelf.ar([in0, in1], a_cutoff, a_rS, a_dB, a_gain);
	Out.ar(out_ch_0, sig[0]);
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;

SynthDef(\BandPass_1, { | in_ch_0=0, out_ch_0=120, a_cutoff=20000, selector_cutoff=0, a_bw=1, selector_bw=0, a_gain=1.0, selector_gain=0 |
	var in0, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_bw = Select.ar(selector_bw, [Lag.ar(K2A.ar(a_bw), 0.001), a_bw]);
	in0 = In.ar(in_ch_0, 1);
	sig = BBandPass.ar(in0, a_cutoff, a_bw, a_gain);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\BandPass_2, { | in_ch_0=0, in_ch_1=1, out_ch_0=120, out_ch_1=121, a_cutoff=20000, selector_cutoff=0, a_bw=1, selector_bw=0, a_gain=1.0, selector_gain=0 |
	var in0, in1, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_bw = Select.ar(selector_bw, [Lag.ar(K2A.ar(a_bw), 0.001), a_bw]);
	in0 = In.ar(in_ch_0, 1);
	in1 = In.ar(in_ch_1, 1);
	sig = BBandPass.ar([in0, in1], a_cutoff, a_bw, a_gain);
	Out.ar(out_ch_0, sig[0]);
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;

SynthDef(\BandStop_1, { | in_ch_0=0, out_ch_0=120, a_cutoff=20000, selector_cutoff=0, a_bw=1, selector_bw=0, a_gain=1.0, selector_gain=0 |
	var in0, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_bw = Select.ar(selector_bw, [Lag.ar(K2A.ar(a_bw), 0.001), a_bw]);
	in0 = In.ar(in_ch_0, 1);
	sig = BBandStop.ar(in0, a_cutoff, a_bw, a_gain);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef(\BandStop_2, { | in_ch_0=0, in_ch_1=1, out_ch_0=120, out_ch_1=121, a_cutoff=20000, selector_cutoff=0, a_bw=1, selector_bw=0, a_gain=1.0, selector_gain=0 |
	var in0, in1, sig;
	a_cutoff = Select.ar(selector_cutoff, [Lag.ar(K2A.ar(a_cutoff), 0.001), a_cutoff]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_bw = Select.ar(selector_bw, [Lag.ar(K2A.ar(a_bw), 0.001), a_bw]);
	in0 = In.ar(in_ch_0, 1);
	in1 = In.ar(in_ch_1, 1);
	sig = BBandStop.ar([in0, in1], a_cutoff, a_bw, a_gain);
	Out.ar(out_ch_0, sig[0]);
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;
)