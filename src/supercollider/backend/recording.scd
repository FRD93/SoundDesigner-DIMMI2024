





// USE THIS TO CREATE THE RECORDING SYNTHDEFS
(
a = (1..256).collect({ | num_chans |
	"SynthDef(\\recording_synth_%, { | in, bufnum |
DiskOut.ar(bufnum, In.ar(in, %));
}).writeDefFile.add;".format(num_chans, num_chans).interpret;
});
)








// USE THIS CODE TO TEST THE RECORDING PROCESS
/*
(
OSCdef(\doneMonitor, {
    | msg, time, addr, recvPort |
    // Controlla se il messaggio è di tipo "/done"
    if(msg[0] == '/done') {
        "Received /done message:".postln;
        msg.postln;
    }
}, '/done');  // Ascolta solo i messaggi di completamento

b = Buffer.alloc(s,
	44100.nextPowerOfTwo,
	1,
	{| buf |
		buf.writeMsg('/Users/francescodani/Music/SuperCollider Recordings/SC_240619_142147.aiff', s.recHeaderFormat, s.recSampleFormat, 0, 0, true)
	}
);

SynthDef(\rrsc, {
	Out.ar(20, SinOsc.ar(440));
}).send(s);

SynthDef(\rrec, { |in, bufnum|
	DiskOut.ar(bufnum, In.ar(in, 1));
}).send(s);
)

Synth.head(s, \rrsc);
Synth.tail(s, \rrec, [\in, 20, \bufnum, b]);

b.writeMsg('/Users/francescodani/Music/SuperCollider Recordings/SC_240619_142147.aiff', s.recHeaderFormat, s.recSampleFormat, -1, 0, 0);

b.numFrames
b.close

r = Recorder(s);
r.record()
r.stopRecording()
r.getRecordBufFrames
*/