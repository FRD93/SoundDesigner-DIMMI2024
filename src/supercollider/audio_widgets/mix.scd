(
SynthDef(\SideChainEfxMONO, { | in_ch_0, in_ch_1, out_ch_0, a_follower=0.2, a_gain=1.0 |
	var main, side, sideAmp, signal, ampfollow;
	main = In.ar(in_ch_0, 1);
	side = In.ar(in_ch_1, 1);
	side = GVerb.ar(side, 300, 30, drylevel: 0.1, earlyreflevel: 1, taillevel: 0.9);
	sideAmp = a_gain;

	ampfollow = Amplitude.ar(main, 0.001, 0.05);
	ampfollow = (ampfollow * 30).clip(0.0, 1.0);
	ampfollow = ((ampfollow - 0.5) * 2).clip(0.0, 1.0);
	ampfollow = LagUD.ar(ampfollow, 0.3, 0.2);
	ampfollow = (1 - (ampfollow * a_follower)).clip(0.0, 1.0);
	main = main * ampfollow;
	signal = (main * (1.0 - sideAmp)) + side;

	Out.ar(out_ch_0, signal);
	Out.kr(out_ch_0, RMS.kr(signal));
}).writeDefFile.add;
)