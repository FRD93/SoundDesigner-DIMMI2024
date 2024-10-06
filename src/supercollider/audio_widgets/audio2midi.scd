(
SynthDef(\TrigReply, { | selector_tfreq=0, a_tfreq=1.0, uuid=1234 |
	var op;
	a_tfreq = Select.ar(selector_tfreq, [K2A.ar(a_tfreq), a_tfreq]); // Without Lag here
	// a_tfreq = (a_tfreq - 0.1).clip(0.0, inf) + 0.1; // allow values in the range of [0] and (0.1, inf): this will prevent looong delays if you set small values (e.g.: 0.001) as well as negative values
	op = Impulse.ar(a_tfreq);
	SendReply.ar(op, '/trigreply', [uuid, a_tfreq])
}).writeDefFile;
)