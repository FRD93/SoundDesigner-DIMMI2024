






/* AMBISONIC Resources
https://www.ambisonictoolkit.net/documentation/supercollider/
http://doc.sccode.org/Guides/Intro-to-the-ATK.html
http://doc.sccode.org/Guides/ATK-SynthDef-Examples.html
FoaDecoderMatrix.newStereo
*/






(
SynthDef(\Mono2StereoDBAP, { | in_ch_0=4096, out_ch_0=120, out_ch_1=121, a_panning=0, selector_panning=0, a_gain=1.0, selector_gain=0 |
	var in0, sig;
	a_panning = Select.ar(selector_panning, [Lag.ar(K2A.ar(a_panning), 0.001), a_panning]);
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	in0 = In.ar(in_ch_0, 1);
	sig = Pan2.ar(in0, a_panning, a_gain);
	Out.ar(out_ch_0, sig);
	Out.kr(out_ch_0, RMS.kr(sig));
}).writeDefFile;

/*
Mono2StereoImager - Spiegazione dei nuovi parametri
    Spread: Questo parametro varia da 0 a 1 e determina quanto il delay sui canali sinistro e destro differisce. Un valore di 0 rende il delay identico per entrambi i canali, mentre un valore di 1 massimizza la differenza.
    Depth: Questo parametro varia da 0 a 1 e controlla l'intensità del delay applicato ai canali. Un valore più alto aumenta il tempo di delay, creando un effetto di spazialità più pronunciato.
    Width: Questo parametro varia da 0 a 2 e controlla la larghezza stereo complessiva. Un valore di 1 lascia la larghezza invariata, valori inferiori a 1 restringono l'immagine stereo, e valori superiori a 1 la ampliano.
*/
SynthDef(\Mono2StereoImager, { | in_ch_0=4096, out_ch_0=120, out_ch_1=121, a_spread=0.5, selector_spread=0, a_depth=0.5, selector_depth=0, a_width=1.0, selector_width=0, a_gain=1.0, selector_gain=0 |
    var input, delayedLeft, delayedRight, mid, side, newMid, newSide, output, stereoInput, delayTime;
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_spread = Select.ar(selector_spread, [Lag.ar(K2A.ar(a_spread), 0.001), a_spread]);
	a_depth = Select.ar(selector_depth, [Lag.ar(K2A.ar(a_depth), 0.001), a_depth]);
	a_width = Select.ar(selector_width, [Lag.ar(K2A.ar(a_width), 0.001), a_width]);

    input = In.ar(in_ch_0, 1) * a_gain;
    delayTime = a_depth * 0.02; // Massimo 20 ms di delay
    delayedLeft = DelayC.ar(input, 0.1, delayTime);
    delayedRight = DelayC.ar(input, 0.1, delayTime * (1 - a_spread)); // Usare spread per diversificare il delay
    stereoInput = [delayedLeft, delayedRight];
	mid = (stereoInput[0] + stereoInput[1]) * 0.5;
    side = (stereoInput[0] - stereoInput[1]) * 0.5;
    newSide = side * a_width;
    newMid = mid; // Può essere manipolato separatamente se necessario
    output = [newMid + newSide, newMid - newSide];
	Out.ar(out_ch_0, output[0]);
	Out.ar(out_ch_1, output[1]);
	Out.kr(out_ch_0, RMS.kr(output[0]));
	Out.kr(out_ch_1, RMS.kr(output[1]));
}).writeDefFile;

SynthDef(\MonoToBFormat, { | in_ch_0=4096, out_ch_0=120, out_ch_1=121, out_ch_2=122, out_ch_3=123, a_azimuth=0, selector_azimuth=0, a_elevation=0, selector_elevation=0, a_gain=1.0, selector_gain=0 |
    var sig, w, x, y, z, aziRad, eleRad;
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	a_azimuth = Select.ar(selector_azimuth, [Lag.ar(K2A.ar(a_azimuth), 0.001), a_azimuth]);
	a_elevation = Select.ar(selector_elevation, [Lag.ar(K2A.ar(a_elevation), 0.001), a_elevation]);
    // Arguments already in radians!
    aziRad = a_azimuth;
    eleRad = a_elevation;
    // Input mono signal
    sig = In.ar(in_ch_0, 1) * a_gain;
    // B-format encoding
    w = sig * sqrt(2) / 2;  // Omnidirectional
    x = sig * cos(aziRad) * cos(eleRad);  // Front-back
    y = sig * sin(aziRad) * cos(eleRad);  // Left-right
    z = sig * sin(eleRad);  // Up-down
    // Output the four B-format channels
    Out.ar(out_ch_0, w);
	Out.ar(out_ch_1, x);
	Out.ar(out_ch_2, y);
	Out.ar(out_ch_3, z);
	Out.kr(out_ch_0, RMS.kr(w));
	Out.kr(out_ch_1, RMS.kr(x));
	Out.kr(out_ch_2, RMS.kr(y));
	Out.kr(out_ch_3, RMS.kr(z));
}).writeDefFile;

SynthDef(\BFormatToBinaural, { | in_ch_0=4096, in_ch_1=4096, in_ch_2=4096, in_ch_3=4096, out_ch_0=120, out_ch_1=121, a_gain=1, selector_gain=0, hrirW_L, hrirW_R, hrirX_L, hrirX_R, hrirY_L, hrirY_R, hrirZ_L, hrirZ_R |
	var w, x, y, z, left, right, hrirW_buf, hrirX_buf, hrirY_buf, hrirZ_buf;
	a_gain = Select.ar(selector_gain, [Lag.ar(K2A.ar(a_gain), 0.001), a_gain]);
	// Leggi il segnale B-format dai bus
	w = In.ar(in_ch_0, 1);
	x = In.ar(in_ch_1, 1);
	y = In.ar(in_ch_2, 1);
	z = In.ar(in_ch_3, 1);
	// Convolvi ciascun canale B-format con i corrispondenti HRIR
	left = Convolution2.ar(w, hrirW_L, framesize: 512) +
	Convolution2.ar(x, hrirX_L, framesize: 512) +
	Convolution2.ar(y, hrirY_L, framesize: 512) +
	Convolution2.ar(z, hrirZ_L, framesize: 512);
	right = Convolution2.ar(w, hrirW_R, framesize: 512) +
	Convolution2.ar(x, hrirX_R, framesize: 512) +
	Convolution2.ar(y, hrirY_R, framesize: 512) +
	Convolution2.ar(z, hrirZ_R, framesize: 512);
	left = left * a_gain;
	right = right * a_gain;
	// Uscita del segnale stereo
	Out.ar(out_ch_0, left);
	Out.ar(out_ch_1, right);
	Out.kr(out_ch_0, RMS.kr(left));
	Out.kr(out_ch_1, RMS.kr(right));
}).writeDefFile;
)



















