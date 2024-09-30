(
SynthDef(\FRDDistortion, { | in_ch_0=0, out_ch_0=0, selector_distort=0, a_distort=1, selector_gain=0, a_gain=1 |
	var sig;
	a_distort = Select.ar(selector_distort, [Lag.ar(K2A.ar(a_distort), 0.001), a_distort]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	sig = In.ar(in_ch_0, 1);
	sig = FRDExpDistorsion.ar(sig, a_distort) * a_gain;
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

SynthDef( \PitchTrackRingModulator, { | in_ch_0=0, in_ch_1=1, no_pitch_freq=440, inertia=1, selector_gain=0, a_gain=1, t_trig=0, out_ch_0=0, out_ch_1=1 |
	var rm, sig, freqs, pitch, hasPitch, env, freq2, hasFreq;
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	env = EnvGen.ar( Env.perc( inertia, inertia, 1, [ 4, 4 ] ), t_trig ) * a_gain;
	sig = [In.ar(in_ch_0, 1), In.ar(in_ch_0, 1)];
	# pitch, hasPitch = Pitch.kr( in:sig.sum, initFreq:no_pitch_freq, minFreq:80, maxFreq:7500, execFreq:256, maxBinsPerOctave:16, median:32, ampThreshold:0.01, peakThreshold:0.5, downSample:1, clar:1 );
	freqs = Lag.ar( K2A.ar( pitch ), 0.01 ) * [ 0.75, 1, 1.5, 2, 3 ];
	rm = SinOsc.ar( freqs, 0, 0.5, 0.5 );
	rm = rm * SinOsc.ar( ( { Rand( 0.100, 0.50 ) } ! freqs.size ), { Rand( 0.0, 2pi ) } ! freqs.size, 1 );
	sig = SelectX.ar( env, [ sig, ( sig * rm.sum ) ] );
	Out.ar(out_ch_0, sig[0]);
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.kr(out_ch_1, RMS.kr(sig[1]));
} ).writeDefFile;

SynthDef(\Stoppato, { | in_ch_0=0, out_ch_0=0, selector_aggressive=0, a_aggressive=0, rise_time=0.3, fall_time=0.2 |
	var main, side, sideAmp, signal, ampfollow;
	a_aggressive = Select.ar(selector_aggressive, [Lag.ar(K2A.ar(a_aggressive), 0.001), a_aggressive]);

	main = In.ar(in_ch_0, 1);

	ampfollow = Amplitude.ar(main, 0.001, 0.05);
	ampfollow = (ampfollow * 30).clip(0.0, 1.0);
	ampfollow = ((ampfollow - 0.5) * 2).clip(0.0, 1.0);
	ampfollow = LagUD.ar(ampfollow, rise_time, fall_time);
	ampfollow = (1 - (ampfollow * a_aggressive)).clip(0.0, 1.0);
	main = main * ampfollow;

	Out.ar(out_ch_0, main);
	Out.kr(out_ch_0, RMS.kr(main));
}).writeDefFile;

SynthDef(\Compressor, { | in_ch_0=0, out_ch_0=0, selector_threshold=0, a_threshold=0.5, selector_slopeBelow=0, a_slopeBelow=1.0, selector_slopeAbove=0, a_slopeAbove=0.5, selector_clampTime=0, a_clampTime=0.01, selector_relaxTime=0, a_relaxTime=0.01, selector_gain=0, a_gain=1 |
	var main, side, sideAmp, signal, ampfollow;
	a_threshold = Select.ar(selector_threshold, [Lag.ar(K2A.ar(a_threshold), 0.001), a_threshold]);
	a_slopeBelow = Select.ar(selector_slopeBelow, [Lag.ar(K2A.ar(a_slopeBelow), 0.001), a_slopeBelow]);
	a_slopeAbove = Select.ar(selector_slopeAbove, [Lag.ar(K2A.ar(a_slopeAbove), 0.001), a_slopeAbove]);
	a_clampTime = Select.ar(selector_clampTime, [Lag.ar(K2A.ar(a_clampTime), 0.001), a_clampTime]);
	a_relaxTime = Select.ar(selector_relaxTime, [Lag.ar(K2A.ar(a_relaxTime), 0.001), a_relaxTime]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);

	main = In.ar(in_ch_0, 1);
	main = CompanderD.ar(main, a_threshold, a_slopeBelow, a_slopeAbove, a_clampTime, a_relaxTime, a_gain);

	Out.ar(out_ch_0, main);
	Out.kr(out_ch_0, RMS.kr(main));
}).writeDefFile;

SynthDef(\Compressor2CH, { | in_ch_0=0, in_ch_1=1, out_ch_0=0, out_ch_1=1, selector_threshold=0, a_threshold=0.5, selector_slopeBelow=0, a_slopeBelow=1.0, selector_slopeAbove=0, a_slopeAbove=0.5, selector_clampTime=0, a_clampTime=0.01, selector_relaxTime=0, a_relaxTime=0.01, selector_gain=0, a_gain=1 |
	var main, side, sideAmp, signal, ampfollow;
	a_threshold = Select.ar(selector_threshold, [Lag.ar(K2A.ar(a_threshold), 0.001), a_threshold]);
	a_slopeBelow = Select.ar(selector_slopeBelow, [Lag.ar(K2A.ar(a_slopeBelow), 0.001), a_slopeBelow]);
	a_slopeAbove = Select.ar(selector_slopeAbove, [Lag.ar(K2A.ar(a_slopeAbove), 0.001), a_slopeAbove]);
	a_clampTime = Select.ar(selector_clampTime, [Lag.ar(K2A.ar(a_clampTime), 0.001), a_clampTime]);
	a_relaxTime = Select.ar(selector_relaxTime, [Lag.ar(K2A.ar(a_relaxTime), 0.001), a_relaxTime]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);

	main = [In.ar(in_ch_0, 1), In.ar(in_ch_1, 1)];
	main = CompanderD.ar(main, a_threshold, a_slopeBelow, a_slopeAbove, a_clampTime, a_relaxTime, a_gain);

	Out.ar(out_ch_0, main[0]);
	Out.ar(out_ch_1, main[1]);
	Out.kr(out_ch_0, RMS.kr(main[0]));
	Out.kr(out_ch_1, RMS.kr(main[1]));
}).writeDefFile;

SynthDef(\PingPongDelay, { | in_ch_0=0, in_ch_1=1, out_ch_0=0, out_ch_1=1, selector_delaytime=0, a_delaytime=1, selector_width=0, a_width=0.5, selector_feedback=0, a_feedback=0.5, selector_gain=0, a_gain=1 |
	var sig, del;
	a_delaytime = Select.ar(selector_delaytime, [Lag.ar(K2A.ar(a_delaytime), 0.001), a_delaytime]);
	a_width = Select.ar(selector_width, [Lag.ar(K2A.ar(a_width), 0.001), a_width]);
	a_feedback = Select.ar(selector_feedback, [Lag.ar(K2A.ar(a_feedback), 0.001), a_feedback]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	sig = [In.ar(in_ch_0, 1), In.ar(in_ch_1, 1)];
	del = DelayC.ar(LocalIn.ar(2), 2.0, a_delaytime, mul: a_feedback);
	LocalOut.ar([sig[0] + (del[1] * a_width) + (del[0] * (1.0 - a_width)), sig[0] + (del[0] * a_width) + (del[1] * (1.0 - a_width))]);
	sig = sig + del;
	sig = sig * a_gain;
	Out.ar(out_ch_0, sig[0]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;

SynthDef(\Chorus, { | in_ch_0 = 0, out_ch_0 = 0, selector_delaytime=0, a_delaytime = 0.03, selector_depth=0, a_depth = 0.01, selector_rate = 0, a_rate = 0.25, selector_gain=0, a_gain=0.75 |
    var input, chorus, delays, modulatedDelays, n_delays=32;
	a_delaytime = Select.ar(selector_delaytime, [Lag.ar(K2A.ar(a_delaytime), 0.001), a_delaytime]);
	a_depth= Select.ar(selector_depth, [Lag.ar(K2A.ar(a_depth), 0.001), a_depth]).clip(0.0, 1.0);
	a_rate = Select.ar(selector_rate, [Lag.ar(K2A.ar(a_rate), 0.001), a_rate]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
    // Read the mono input
    input = In.ar(in_ch_0, 1);
    // Create multiple modulated delay lines to simulate chorus
    delays = Array.fill(n_delays, { |i|
		var modRate = a_rate * (1.0 + (LFNoise1.kr(0.1) * Rand(0.05, 1.15)));
		var mod = SinOsc.kr(modRate, {Rand(0.0, 2pi)} ! n_delays, a_depth, a_delaytime);
		DelayC.ar(input, a_delaytime + {Rand(a_depth / 10, a_depth)} ! n_delays, a_delaytime + mod)
    });
    // Mix the delayed signals
    chorus = Mix.new(delays) / n_delays;
	chorus = (input * (1.0 - a_depth)) + (chorus * a_depth);
    // Output the processed signal
    Out.ar(out_ch_0, chorus);
	Out.kr(out_ch_0, RMS.kr(chorus));
}).writeDefFile;

SynthDef(\Chorus2CH, { | in_ch_0=0, in_ch_1=1, out_ch_0=0, out_ch_1=1, selector_delaytime=0, a_delaytime = 0.03, selector_depth=0, a_depth = 0.01, selector_rate = 0, a_rate = 0.25, selector_gain=0, a_gain=0.75 |
    var input, chorus, delays, modulatedDelays, n_delays=32;
	a_delaytime = Select.ar(selector_delaytime, [Lag.ar(K2A.ar(a_delaytime), 0.001), a_delaytime]);
	a_depth= Select.ar(selector_depth, [Lag.ar(K2A.ar(a_depth), 0.001), a_depth]).clip(0.0, 1.0);
	a_rate = Select.ar(selector_rate, [Lag.ar(K2A.ar(a_rate), 0.001), a_rate]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
    // Read the mono input
	input = [In.ar(in_ch_0, 1), In.ar(in_ch_1, 1)];
    // Create multiple modulated delay lines to simulate chorus
    delays = Array.fill(64, { |i|
		var modRate = a_rate * (1.0 + ({LFNoise1.kr(0.1)} ! 2 * {Rand(0.05, 1.15)} ! 2));
        var mod = SinOsc.kr(modRate, {Rand(0.0, 2pi)} ! n_delays, a_depth, a_delaytime);
        DelayC.ar(input, a_delaytime + {Rand(a_depth / 10, a_depth)} ! n_delays, a_delaytime + mod)
    });
    // Mix the delayed signals
    chorus = Mix.new(delays) / n_delays;
	chorus = (input * (1.0 - a_depth)) + (chorus * a_depth);
    // Output the processed signal
	Out.ar(out_ch_0, chorus[0]);
	Out.kr(out_ch_0, RMS.kr(chorus[0]));
	Out.ar(out_ch_1, chorus[1]);
	Out.kr(out_ch_1, RMS.kr(chorus[1]));
}).writeDefFile;

SynthDef(\PitchShift, { | in_ch_0 = 0, out_ch_0 = 0, selector_time_dispersion=0, a_time_dispersion = 0.0, selector_pitch_dispersion=0, a_pitch_dispersion = 0.0, selector_rate = 0, a_rate = 0.25, selector_gain=0, a_gain=0.75 |
    var input, chorus, trigger, granulator, localbuf;
	a_time_dispersion = Select.ar(selector_time_dispersion, [Lag.ar(K2A.ar(a_time_dispersion), 0.001), a_time_dispersion]);
	a_pitch_dispersion= Select.ar(selector_pitch_dispersion, [Lag.ar(K2A.ar(a_pitch_dispersion), 0.001), a_pitch_dispersion]).clip(0.0, 1.0);
	a_rate = Select.ar(selector_rate, [Lag.ar(K2A.ar(a_rate), 0.001), a_rate]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
    // Read the mono input & create the trigge
    input = In.ar(in_ch_0, 1);

	granulator = PitchShift.ar(input, 0.2, a_rate, a_pitch_dispersion, a_time_dispersion, a_gain);
    // Output the processed signal
    Out.ar(out_ch_0, granulator);
	Out.kr(out_ch_0, RMS.kr(granulator));
}).writeDefFile;
)





















