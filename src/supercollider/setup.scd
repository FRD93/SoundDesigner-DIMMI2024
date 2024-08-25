/*
SuperCollider Setup Process
2024, Francesco Roberto Dani

1) Install (a.k.a.: copy downloaded dirs of) FRDSCLib (https://github.com/FRD93/FRDSClib) and SC3-Plug-Ins (http://supercollider.github.io/sc3-plugins/) into Platform.userExtensionDir
2) Run the following code fragment to build synth definitions required by FRDSCLib classes
*/


(
var path = "".resolveRelative;
FRDBufferGranulator().writeSynthDef();
FRDChimes().writeSynthDef();
FRDContinuousBufferGranulator(Buffer.alloc(s, 44100)).writeSynthDef();
FRDContinuousBusGranulator().writeSynthDef();
FRDDX7PlugIn().writeSynthDef();
FRDExplosion().writeSynthDef();
FRDLiveInputPlugIn().writeSynthDef();
FRDLooperPlugIn().writeSynthDef();
FRDMIDIBassSynth().writeSynthDef();
FRDMIDIDrums().writeSynthDef();
// FRDMIDISampler().writeSynthDef();
FRDMono2StereoPlugIn().writeSynthDef();
FRDPitchTrackRingModulatorPlugIn().writeSynthDef();
FRDRingModulatorPlugIn().writeSynthDef();
FRDSampler("").writeSynthDef();
FRDSpatPlugIn().writeDefFile();
FRDThunders().writeSynthDef();

["backend/", "audio_widgets/"].do({ | subpath |
	PathName(path ++ subpath).filesDo({ | file |
		file = file.asAbsolutePath;
		f = File(file, "r");
		f = f.readAllString.interpret;
	});
});
0.exit();
)