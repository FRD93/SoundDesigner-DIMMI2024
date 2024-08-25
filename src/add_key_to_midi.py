from mido import MidiFile, MetaMessage
path = "insert MIDI file path to be added with key_signature metadata (file will be overwritten!)"
key = "Dm"
m = MetaMessage("key_signature", key=key, time=0)
mid = MidiFile(path)
mid.tracks[0].append(MetaMessage("key_signature", key=key, time=0))
mid.save(path)