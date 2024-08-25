import random

import numpy
import json
from classes import *
from third_party.melody_generation_transformer.train import *

def tokenize_midi_file(path):
    midiclip = MIDIClip(path, transpose_to_C=True)
    return midiclip.tokenize(max_notes=15, encode_start_time=False, encode_velocity=True, encode_chord=True)

def tokenize_midi_folder(path):
    tokens = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".mid") or file.endswith(".mscx") or file.endswith(".mscz"):
                filepath = os.path.join(root, file)
                clip_tokens = tokenize_midi_file(filepath)
                print(file, clip_tokens)
                if isinstance(clip_tokens, list):
                    tokens.extend(clip_tokens)
                else:
                    tokens.append(clip_tokens)
    return tokens


def save_tokens(tokens, path):
    with open(path, "w") as fi:
        json.dump(tokens, fi, indent=4)


def load_tokens(path):
    with open(path, "r") as fi:
        return json.load(fi)


if __name__ == "__main__":
    task = "EVAL"  # either "TRAIN" or "EVAL"
    EPOCHS = 6
    LEARNING_RATE = 0.0005
    tokens = tokenize_midi_folder("/Users/francescodani/Documents/Libri/Partiture/MIDI Files/trainable_midi_files/tmp")
    save_tokens(tokens, "../data/melody_tokens.json")
    melody_preprocessor = MelodyPreprocessor("../data/melody_tokens.json", batch_size=64)
    training_dataset = melody_preprocessor.create_training_dataset()
    vocab_size = melody_preprocessor.number_of_tokens_with_padding
    print("vocab_size", vocab_size)
    print("max melody length:", melody_preprocessor.max_melody_length)
    transformer_model = Transformer(
        num_layers=4,
        d_model=256,
        num_heads=8,
        d_feedforward=256,
        input_vocab_size=vocab_size,
        target_vocab_size=vocab_size,
        max_num_positions_in_pe_encoder=MAX_POSITIONS_IN_POSITIONAL_ENCODING,
        max_num_positions_in_pe_decoder=MAX_POSITIONS_IN_POSITIONAL_ENCODING,
        dropout_rate=0.2,
    )
    transformer_model.optimizer = optimizer(transformer_model.parameters(), lr=LEARNING_RATE)
    if task == "TRAIN":
        train(training_dataset, transformer_model, EPOCHS, "../data/melody_transformer_model.ckpt")
    elif task == "EVAL":
        checkpoint = torch.load("../data/melody_transformer_model.ckpt")
        transformer_model.load_state_dict(checkpoint['model_state_dict'])

    print("Generating a melody...")
    transformer_model.eval()
    melody_generator = MelodyGenerator(
        transformer_model, melody_preprocessor.tokenizer
    )

    for _ in range(5):
        start_sequence = [f"{random.choice(['C', 'E', 'G'])}3_120_60;{random.choice(['B', 'F', 'G'])}3_60_60|C", "{random.choice(['C', 'E', 'G'])}3_30_60;{random.choice(['A', 'E', 'G'])}4_30_60|C", "{random.choice(['A', 'B', 'G'])}3_60_60|C"]
        new_melody = melody_generator.generate(start_sequence)
        print(new_melody)
        midiclip = MIDIClip(custom_data={"name": "", "key": "Cmaj", "mode": 0, "notes": [Note()], "chords": [], "bpm": 120})
        midiclip.load_from_tokens(new_melody, encode_velocity=True)
        midiclip.save(f"../data/midi/melodies/generated_melody-{int(random.uniform(0, 100000))}.mid", ignore_first_bar=True)
