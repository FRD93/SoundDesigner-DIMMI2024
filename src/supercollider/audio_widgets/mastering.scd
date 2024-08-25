(
SynthDef(\SpectralMastering, { |
	/*  IN/OUT variables */
	in_ch_0, in_ch_1, out_ch_0, out_ch_1,
	in=0, out=0,
	/* EQ variables */
	low_shelf_f=20, low_shelf_g=0, low_shelf_q=0.1, low_shelf_e=0,
	hi_shelf_f=18000, hi_shelf_g=0, hi_shelf_q=0.1, hi_shelf_e=0,
	bp1_f=440, bp1_g=0, bp1_q=0.1, bp1_e=0,
	bp2_f=440, bp2_g=0, bp2_q=0.1, bp2_e=0,
	bp3_f=440, bp3_g=0, bp3_q=0.1, bp3_e=0,
	bp4_f=440, bp4_g=0, bp4_q=0.1, bp4_e=0,
	/* COMPRESSOR variables */
	comp_t=0.5, comp_sb=1, comp_sa=0.3, comp_atk=0.03, comp_rel=0.2,
	/* LIMITER variables */
	limit_l=1.0, limit_e=0,
	/* PAN variables */
	pan=0,
	/* REVERB variables */
	rev_w=0.33, rev_r=0.4, rev_d=0.2, rev_e=0, irbufnum,
	/* GAIN variables */
	pre_gain=0, post_gain=0,
	/* GATE */
	gate=1 |
	var sig, env, sig_pre_master;
	var fftsize = 1024, history_size = 4;
	var fft_filter = Array.fill(fftsize, {| id |     ((id/(fftsize-1)).pow(1/1.2) * 0.3) + 0.7     });
	var bin_history = Array.fill( fftsize, { Array.fill( history_size, { 0 } ) } );
	var chainL, chainR, sig_fft;
	env = EnvGen.ar(Env.asr(0.1, 1, 3, [-4, -4]), gate, doneAction: 2);
	/* GAIN */
	sig = [In.ar(in_ch_0, 1), In.ar(in_ch_1, 1)] * pre_gain.dbamp;
	/* CONV REVERB */
	// sig = sig + (PartConv.ar(sig, 2048, irbufnum) * rev_w);
	sig = sig + FreeVerb.ar(sig, rev_w);

	/* EQ */
	sig = SelectX.ar(low_shelf_e, [sig, BLowShelf.ar(sig, low_shelf_f, rs:1, db: ((low_shelf_g + 1.00001) / 4.75).ampdb)]);
	sig = SelectX.ar(bp1_e, [sig, sig + BBandPass.ar(sig, bp1_f, bp1_q, bp1_g.clip(-1.0, 4.0))]); // limite a +12dB, per sicurezza...
	sig = SelectX.ar(bp2_e, [sig, sig + BBandPass.ar(sig, bp2_f, bp2_q, bp2_g.clip(-1.0, 4.0))]);
	sig = SelectX.ar(bp3_e, [sig, sig + BBandPass.ar(sig, bp3_f, bp3_q, bp3_g.clip(-1.0, 4.0))]);
	sig = SelectX.ar(bp4_e, [sig, sig + BBandPass.ar(sig, bp4_f, bp4_q, bp4_g.clip(-1.0, 4.0))]);
	sig = SelectX.ar(hi_shelf_e, [sig, BHiShelf.ar(sig, hi_shelf_f, rs: 1, db: ((hi_shelf_g + 1.00001) / 4.75).ampdb)]);

	/* COMPRESSOR */
	comp_sa = comp_sa.reciprocal.reciprocal.clip(-20, 20);
	sig = SoftKneeCompressor.ar(sig, sig, comp_t.ampdb, comp_sa, 6, comp_atk, comp_rel);
	sig_pre_master = sig;

	// MASTERING DELLA MADONNA
	chainL = FFT(LocalBuf(fftsize, 1), sig[0], wintype: 0);
	chainL = chainL.pvcollect( fftsize, { | mag, phase, bin, index |
		var mean, std_dev;
		// Inserisco nuova magnitudine nella storia delle magnitudini
		bin_history[index] = bin_history[index].rotate(1);
		bin_history[index][0] = mag;
		// Calcolo media e deviazione standard corretta (N-1)
		mean = bin_history[index].sum / bin_history[index].size;
		std_dev = (bin_history[index].collect({ | bbin | ( bbin - mean ).pow(2) }).sum / (bin_history[index].size - 1)).sqrt * 3;
		// Se la magnitudine è sopra media + std, la clippo a media + std
		mag = mag.clip2(mean + std_dev) * fft_filter[index];

		[mag, phase]
	});
	chainR = FFT(LocalBuf(fftsize, 1), sig[1], wintype: 0);
	chainR = chainR.pvcollect( fftsize, { | mag, phase, bin, index |
		var mean, std_dev;
		// Calcolo media e deviazione standard corretta (N-1)
		mean = bin_history[index].sum / bin_history[index].size;
		std_dev = (bin_history[index].collect({ | bbin | ( bbin - mean ).pow(2) }).sum / (bin_history[index].size - 1)).sqrt * 3;
		// Se la magnitudine è sopra media + std, la clippo a media + std
		mag = mag.clip2(mean + std_dev) * fft_filter[index];
		[mag, phase]
	});

	sig_fft = [IFFT(chainL, wintype: 0), IFFT(chainR, wintype: 0)];

	sig_fft = sig_fft + HPF.ar(sig_pre_master, 10000);

	sig = sig_fft;

	sig = sig * env * post_gain.dbamp;

	Out.ar(out_ch_0, sig[0]);
	Out.ar(out_ch_1, sig[1]);
	Out.kr(out_ch_0, RMS.kr(sig[0]));
	Out.kr(out_ch_1, RMS.kr(sig[1]));
}).writeDefFile;
)