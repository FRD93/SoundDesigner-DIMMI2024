(
SynthDef(\SFPlayer2CH, { | soundfile, rate=1, start_frame=0, end_frame=0, loop=0, t_trig=0, out_ch_0=0,  out_ch_1=1 |
	var env, play, end, dur;
	end = Select.kr(end_frame > 0, [BufFrames.kr(soundfile), end_frame]);
	dur = (end - start_frame) * rate / SampleRate.ir;
	env = EnvGen.ar(Env.linen(dur, 0, 0, 1, 'lin'), t_trig, (end - start_frame), start_frame);
	play = BufRd.ar(2, soundfile, env);
	//play = PlayBuf.ar(2, soundfile, rate, t_trig, start_frame, loop);
	Out.ar(out_ch_0, play[0]);
	Out.ar(out_ch_1, play[1]);
	Out.kr(out_ch_0, RMS.kr(play[0]));
	Out.kr(out_ch_1, RMS.kr(play[1]));
}).writeDefFile;
)


/*
b = Buffer.read(s, "/Users/francescodani/Documents/Campioni/Brani Reference/Orchestra 1.wav");
x = Synth(\SFPlayer2CH, [\soundfile, b])
x.set(\t_trig, -1);
x.set(\t_trig, 1);

(
{
	Select.kr(1 > 0, [0, 1]);
}.play
)

Synth(\SpectralMastering)
*/