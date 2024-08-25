"""
import math
import platform
if platform.system() == "Darwin" or platform.system() == "Windows":
    from src.primitives import *
    import src.classes as classes
else:
    from primitives import *
    import classes as classes
import importlib.util
import pandas as pd
import torch
import copulas
import mediapipe as mp
import tensorboard
from torch.utils.tensorboard import SummaryWriter
import cv2
import sys
from functools import partial


holistic = mp.solutions.holistic.Holistic(min_tracking_confidence=0.8, enable_segmentation=True, model_complexity=1)
mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

conf = cp.ConfigParser()
conf.read("config.ini")
PyChiro_path = conf.get("PATHS", "PyChiro_path")

config = cp.ConfigParser()
config_file_path = os.path.join(PyChiro_path, 'config.ini')
# config.read("./config.ini")
config.read(config_file_path)

dataset_path = PyChiro_path + "Notes/" + config.get("DATASET", "c1c2_dataset_path")
dataset_eval_path = PyChiro_path + "Notes/" + config.get("DATASET", "c1c2_dataset_eval_path")
model_name = config.get("NETWORK", "model_name")
volume_model_name = config.get("NETWORK", "volume_model_name")
batch_size = config.getint("NETWORK", "batch_size")
num_epochs = config.getint("NETWORK", "num_epochs")
learning_rate = config.getfloat("NETWORK", "learning_rate")
save_checkpoints = config.getboolean("NETWORK", "save_checkpoints")
save_last_checkpoint = config.getboolean("NETWORK", "save_last_checkpoint")
checkpoint_dir = PyChiro_path + "checkpoints/" + "Notes/" + model_name + "/"
load_checkpoint = checkpoint_dir + config.get("NETWORK", "load_checkpoint")

video_recordings_path = config.get("DATASET", "video_recordings_path")
mediapipe_analysis_path = config.get("DATASET", "mediapipe_analysis_path")
hand_landmark_header = eval(config.get("DATASET", "hand_landmark_header"))
notes_onehot = eval(config.get("DATASET", "notes_onehot"))
notes_onehot_header = eval(config.get("DATASET", "notes_onehot_header"))
measure_types = eval(config.get("DATASET", "measure_types"))
volume_measure_types = eval(config.get("DATASET", "volume_measure_types"))
left_hand_inclination_measure_types = eval(config.get("LEFT HAND INCLINATION NETWORK", "measure_types"))
measures_augmentation_steps = config.getint("DATASET", "measures_augmentation_steps")

save_checkpoints_epoch_delta = config.getint("NETWORK", "save_checkpoints_epoch_delta")
eval_each_batch_delta = config.getint("NETWORK", "eval_each_batch_delta")
early_stop = config.getint("NETWORK", "early_stop")
measures_model = config.getboolean("NETWORK", "measures_model")
run_checkpoint = checkpoint_dir + config.get("RUN", "run_checkpoint")
volume_run_checkpoint = PyChiro_path + "checkpoints/" + "Volume/" + volume_model_name + "/" + config.get("RUN", "volume_run_checkpoint")


def import_module_from_path(module_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def list_available_cameras():
    available_cameras = []
    index = 0
    while True:
        # Try to open the camera with the current index
        print("YEEE")
        cap = cv2.VideoCapture(index)
        print("OOO")
        if not cap.isOpened():
            break
        else:
            # Get some properties of the camera
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = cap.get(cv2.CAP_PROP_FPS)
            # Add camera information to the list
            camera_info = {
                'index': index,
                'width': width,
                'height': height,
                'fps': fps
            }
            available_cameras.append(camera_info)
            # Release the camera
            cap.release()
            index += 1
    return available_cameras


def add_text_to_frame(frame, text="---", org=(50, 50)):
    # Add text to the frame
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    color = (0, 255, 0)
    thickness = 2
    cv2.putText(frame, text, org, font, font_scale, color, thickness, cv2.LINE_AA)
    return frame


def predict_single_input(model, input_vector):
    global normalization_coefficients
    model.eval()  # Set the model to evaluation mode
    # input_vector = normalize_input(input_vector)  # Normalize input
    with torch.no_grad():  # Disable gradient calculation during prediction
        # Convert the input vector to a PyTorch tensor
        input_tensor = torch.tensor(input_vector, dtype=torch.float32)
        # Reshape the input tensor to match the expected shape (batch_size=1, input_size)
        input_tensor = input_tensor.unsqueeze(0)
        # Forward pass through the model to get the predictions
        predictions = model(input_tensor)
        # Convert the predictions tensor to a numpy array and return it
        return predictions.squeeze().numpy()


def correct_notes_network_output(output):
    output[notes_onehot_header.index("E1")] *= 3
    output[notes_onehot_header.index("B1")] /= 10
    return output


class PyChiro(MIDIWidget):
    def __init__(self, server, clock, harmony_manager, parent=None, uuid=None, n_midi_in=0, n_midi_out=2):
        super().__init__(clock, harmony_manager, parent, n_midi_in=n_midi_in, n_midi_out=n_midi_out, uuid=uuid)
        self.server = server
        self.camera_list = list_available_cameras()
        self.selected_camera = -1
        self.start_note = 64
        self.has_to_stop = False
        self.scale = "Major"
        self.note_to_number_maj = {"C1": 0, "D1": 2, "E1": 4, "F1": 5, "G1": 7, "A1": -3, "B1": -1}
        self.note_to_number_min = {"asc": {"C1": 0, "D1": 2, "E1": 3, "F1": 5, "G1": 7, "A1": -3, "B1": -1}, "desc": {"C1": 0, "D1": 2, "E1": 3, "F1": 5, "G1": 7, "A1": -4, "B1": -2}}
        self.current_note = -1
        print("Camera List:", self.camera_list)

        self.data_creator = import_module_from_path(PyChiro_path + "data_creator.py", "data_creator")
        self.notes_network = import_module_from_path(PyChiro_path + "notes_network.py", "notes_network")
        self.volume_network = import_module_from_path(PyChiro_path + "volume_network.py", "volume_network")

        self.lbl = QLabel("PyChiro")
        self.lbl.setObjectName("widget-title")
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_lbl = QLabel("Camera")
        self.camera_lbl.setObjectName("widget-param")
        self.camera_btn = QPushButton()
        self.camera_btn.setObjectName("widget-param")
        self.camera_menu = QMenu()
        self.camera_btn.setMenu(self.camera_menu)
        for camera_info in self.camera_list:
            action = QAction(f"{camera_info['index']}: ({camera_info['width']},{camera_info['height']})", self)
            # self.camera_menu.triggered.connect(lambda checked, camera=camera_info['index']: self.set_camera(camera))
            action.triggered.connect(partial(self.set_camera, camera_info['index']))
            self.camera_menu.addAction(action)
        self.camera_lay = QHBoxLayout()
        self.camera_lay.addWidget(self.camera_lbl)
        self.camera_lay.addWidget(self.camera_btn)

        self.notes_network_chkbox = QCheckBox("Notes Network")
        self.notes_network_chkbox.setObjectName("widget-param")
        self.notes_network_lay = QHBoxLayout()
        self.notes_network_lay.addWidget(self.notes_network_chkbox)

        self.volume_network_chkbox = QCheckBox("Volume Network")
        self.volume_network_chkbox.setObjectName("widget-param")
        self.volume_network_lay = QHBoxLayout()
        self.volume_network_lay.addWidget(self.volume_network_chkbox)

        self.start_note_lbl = QLabel("Start Note")
        self.start_note_lbl.setObjectName("widget-param")
        self.start_note_txt = QLineEdit(self)
        self.start_note_txt.setText(str(self.start_note))
        self.start_note_txt.setObjectName("widget-param")
        self.start_note_lay = QHBoxLayout()
        self.start_note_lay.addWidget(self.start_note_lbl)
        self.start_note_lay.addWidget(self.start_note_txt)

        self.scale_lbl = QLabel("Scale")
        self.scale_lbl.setObjectName("widget-param")
        self.scale_btn = QPushButton()
        self.scale_btn.setObjectName("widget-param")
        self.scale_menu = QMenu()
        self.scale_btn.setMenu(self.scale_menu)
        action = QAction("Major", self)
        action.triggered.connect(self.set_scale)
        self.scale_menu.addAction(action)
        action = QAction("minor", self)
        action.triggered.connect(self.set_scale)
        self.scale_menu.addAction(action)
        self.scale_lay = QHBoxLayout()
        self.scale_lay.addWidget(self.scale_lbl)
        self.scale_lay.addWidget(self.scale_btn)
        self.scale_btn.setText(self.scale)

        self.process_btn = QPushButton("Start Processing")
        self.process_btn.setObjectName("widget-param")
        self.process_btn.setCheckable(True)
        self.process_btn.setChecked(False)
        self.process_btn.clicked.connect(self.process_func)

        self.lay = QVBoxLayout()
        self.lay.setSpacing(0)
        self.lay.addWidget(self.lbl)
        self.lay.addLayout(self.camera_lay)
        self.lay.addLayout(self.notes_network_lay)
        self.lay.addLayout(self.volume_network_lay)
        self.lay.addLayout(self.start_note_lay)
        self.lay.addLayout(self.scale_lay)
        self.lay.addWidget(self.process_btn)
        self.setLayout(self.lay)

    def set_camera(self, camera):
        self.selected_camera = camera
        self.camera_btn.setText(f"{self.camera_list[int(camera)]['index']}: ({self.camera_list[int(camera)]['width']},{self.camera_list[int(camera)]['height']})")
        print("Camera:", self.selected_camera)

    def set_scale(self):
        self.scale = self.sender().text()

    def process_func(self):
        if self.sender().isChecked():
            self.process_btn.setText("STOP")
            self.has_to_stop = False
            self.processing_thread = Thread(target=self.processing_thread_func, args=(self.selected_camera, ))
            self.processing_thread.start()
        else:
            self.process_btn.setText("Start Processing")
            self.has_to_stop = True
            self.processing_thread.join()

    def processing_thread_func(self, camera):
        # model = getattr(sys.modules[__name__], model_name)()
        model = self.notes_network.MeasuresNetworkKodalyC1C2_slim()
        checkpoint_path = run_checkpoint
        if os.path.exists(checkpoint_path):
            checkpoint = torch.load(checkpoint_path)
            model.load_state_dict(checkpoint['model_state_dict'])
            print("Loaded NOTES model checkpoint:", checkpoint_path)

        # volume_model = getattr(sys.modules[__name__], volume_model_name)()
        volume_model = self.volume_network.MeasuresNetworkVolumeC1C2_slim()
        checkpoint_path = volume_run_checkpoint
        if os.path.exists(checkpoint_path):
            checkpoint = torch.load(checkpoint_path)
            volume_model.load_state_dict(checkpoint['model_state_dict'])
            print("Loaded VOLUME model checkpoint:", checkpoint_path)

        cap = cv2.VideoCapture(camera)
        if not cap.isOpened():
            print("Error: Failed to open camera.")
            return

        time.sleep(3)

        while True:
            if self.has_to_stop:
                break
            # Capture frame-by-frame
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to capture frame.")
                break
            frame = cv2.resize(frame, (960, 540))
            text = "---"
            volume = 0
            velocity = 0
            left_hand_features = self.data_creator.extract_mediapipe_data_from_frame_VOLUME(frame)
            if len(left_hand_features) == len(hand_landmark_header):
                left_hand_measures = self.data_creator.extract_measures_from_data_array_VOLUME(left_hand_features)
                left_hand_measures = self.data_creator.normalize_measures_array_VOLUME(left_hand_measures)
                output = float(predict_single_input(volume_model, left_hand_measures))
                # print("Output:", output)
                volume = 0 if output < 0.2 else math.pow(np.clip(output, 0.0, 1.0), 2)
                velocity = int(np.clip(volume * 127, 0, 127))
                self.propagateRTCC(7, velocity)
                # print("Volume:", volume)
            right_hand_features = self.data_creator.extract_mediapipe_data_from_frame(frame)
            if len(right_hand_features) == len(hand_landmark_header):
                right_hand_measures = self.data_creator.extract_measures_from_data_array(right_hand_features)
                right_hand_measures = self.data_creator.normalize_measures_array(right_hand_measures)
                output = predict_single_input(model, right_hand_measures)
                output = correct_notes_network_output(output)
                text = notes_onehot_header[np.argmax(output)]
                if self.scale == "Major":
                    note = self.note_to_number_maj[text] + self.start_note
                elif self.scale == "minor":
                    note = self.note_to_number_min["desc"][text] + self.start_note
                    if self.current_note > note:
                        note = self.note_to_number_min["desc"][text] + self.start_note
                    elif self.current_note < note:
                        note = self.note_to_number_min["asc"][text] + self.start_note
                # print("Note:", note, "Velocity:", velocity)
                if volume > 0:
                    if self.current_note != note:
                        if self.current_note > 0:
                            self.propagateRTMIDINote(self.current_note, 0)  # Release previous note if any
                        self.propagateRTMIDINote(note, velocity)
                        self.current_note = note
                        # print("Started Note:", note, "Velocity:", velocity)
                else:
                    self.propagateRTMIDINote(self.current_note, 0)
                    self.propagateRTMIDINote(note, 0)
                    # print("Closed Notes:", [self.current_note, note], "Velocity:", velocity)
                    self.current_note = -1

                # self.propagateRTCC(7, velocity)
            else:
                self.propagateRTMIDINote(self.current_note, 0)
                # self.propagateRTCC(7, velocity)
                self.current_note = -1

            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            results = holistic.process(frame)
            if results.right_hand_landmarks:
                mp_drawing.draw_landmarks(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.flip(frame, 1)

            # Process the frame (add text)
            frame = add_text_to_frame(frame, text=text, org=(50, 50))
            if text != "---":
                frame = add_text_to_frame(frame, text=f"C: {output[0]}", org=(50, 80))
                frame = add_text_to_frame(frame, text=f"D: {output[1]}", org=(50, 110))
                frame = add_text_to_frame(frame, text=f"E: {output[2]}", org=(50, 140))
                frame = add_text_to_frame(frame, text=f"F: {output[3]}", org=(50, 170))
                frame = add_text_to_frame(frame, text=f"G: {output[4]}", org=(50, 200))
                frame = add_text_to_frame(frame, text=f"A: {output[5]}", org=(50, 230))
                frame = add_text_to_frame(frame, text=f"B: {output[6]}", org=(50, 260))

            # Display the frame
            # cv2.imshow('Frame', frame)

            # Exit loop if 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    def __getstate__(self):
        d = super().__getstate__()
        d.update({
            "start_note": self.start_note,
            "scale": self.scale
        })
        return d

    def __setstate__(self, state):
        super().__setstate__(state)
        try:
            self.start_note = state["start_note"]
            self.scale = state["scale"]
            self.scale_btn.setText(self.scale)
        except:
            pass
        self.setGeometry(state["x"], state["y"], state["width"], state["height"])
"""