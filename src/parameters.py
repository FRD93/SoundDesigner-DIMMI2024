from path_manager import STYLE_PATH, CONFIG_PATH
import configparser
from log_coloring import c_print


cp = configparser.ConfigParser()
cp.read(CONFIG_PATH, encoding="utf-8")

try:
    # GENERAL
    PPQN = int(cp["GENERAL"]["PPQN"])
    INSTRS = cp["GENERAL"]["INSTRS"]
    # SCSYNTH
    SCSYNTH_PATH = cp["SCSYNTH"]["scsynth_path"]
    SCSYNTH_SYNTHDEF_PATH = cp["SCSYNTH"]["synthdef_path"]
except:
    c_print("red", "[ERROR]: Config File not found")
    PPQN = 96
    SCSYNTH_PATH = "/Applications/SuperCollider.app/Contents/Resources/scsynth"
    SCSYNTH_SYNTHDEF_PATH = "/Users/francescodani/Library/Application Support/SuperCollider/synthdefs"
    AMBISONICS_KERNEL_PATH = "/Users/francescodani/Documents/SoundDesigner/ATK/FOA kernels"
    DEBUG_SCSYNTH_LOG = True
    NUM_HW_IN = 2
    NUM_HW_OUT = 2
    MAX_AUDIO_BUSSES = 4096
    MAX_AUDIO_BUFFERS = 256
    SAMPLE_RATE = 44100
    BLOCK_SIZE = 128
    HARDWARE_BUFFER_SIZE = 128
    RT_MEM_SIZE = 8192
    HARDWARE_DEVICE_NAME = "MacIO"
    RECORDING_NUM_CHANNELS = 2
    RECORDING_HEADER_FORMAT = "WAV"
    RECORDING_SAMPLE_FORMAT = "int32"
