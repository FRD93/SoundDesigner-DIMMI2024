# -*- coding: utf-8 -*-

"""
####################################################################################
# THIS LIBRARY CONTAINS CLASSES FOR INTERFACING WITH SCSYNTH AUDIO SYNTHESIS SERVER.
# 
# Copyright ©2017,  Francesco Roberto Dani
# Mail of the author: f.r.d@hotmail.it
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
####################################################################################
"""

import os
import pty
import threading
import time
import math
import random
import socket
import subprocess
import numpy as np
from threading import Thread
from pythonosc import udp_client
from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.osc_bundle_builder import OscBundleBuilder
from pythonosc import osc_message_builder
from osc4py3 import oscbuildparse
from osc4py3.as_eventloop import osc_startup, osc_udp_client, osc_send, osc_process, osc_terminate
from path_manager import STYLE_PATH, CONFIG_PATH
import functions
import configparser as cp
from log_coloring import c_print

"""
- - - SYNTH DEFAULT - - -
(
SynthDef(\default, { | pitch=60, amp=0.5, gate=1 |
	var env, osc;
	amp = AmpCompA.ir(pitch.midicps) * amp;
	env = EnvGen.ar(Env.adsr(0.01, 0, 1, 1), gate: gate, levelScale: amp, doneAction: 2);
	osc = LFSaw.ar(pitch.midicps + SinOsc.ar(Rand(0.02, 0.4), Rand(0.0, 2pi), Rand(0.0, 1.0)), 0, env);
	osc = MoogFF.ar(osc, pitch.midicps * 8 + SinOsc.ar(Rand(0.14, 0.53), Rand(0.0, 2pi), Rand(0.0, 1.0)), 3.4);
	osc = osc + CombC.ar(osc, 0.25, SinOsc.ar(Rand(0.01, 0.1), Rand(0.0, 2pi), Rand(0.01, 0.1), 0.15), Rand(0.5, 2.5), Rand(0.15, 0.75));
	Out.ar(0, osc ! 2);
}).writeDefFile.add;
)
"""

'''

- - Class SCSYNTH - -

This class connects to a running scsynth process
via OSC and allows to send and receive messages.


- Attributes:

- - ip: 
- - - ip address of the running scsynth process

- - port: 
- - - listening port of the running scsynth process


- Usage:

scsynth = SCSYNTH("127.0.0.1", 57110)
scsynth.sendMessage("/s_new", ["default", -1, 0, 0, "freq", 440, "amp", 0.5])

'''

conf = cp.ConfigParser()
if os.path.exists(os.path.abspath("config.ini")):
    config_path = "config.ini"
else:
    config_path = "/Users/francescodani/Documents/SoundDesigner/SoundDesigner/src/config.ini"

conf.read(CONFIG_PATH)  # config_path
try:
    PPQN = conf.getint("GENERAL", "ppqn")
    SCSYNTH_PATH = conf.get("SCSYNTH", "scsynth_path")
    SCSYNTH_SYNTHDEF_PATH = conf.get("SCSYNTH", "synthdef_path")
    AMBISONICS_KERNEL_PATH = conf.get("SCSYNTH", "ambisonics_kernels_path")
    ATK_BUFFER_SIZE = conf.get("SCSYNTH", "ATK_BUFFER_SIZE")
    DEBUG_SCSYNTH_LOG = True
except:
    c_print("red", "[ERROR]: Config File not found")
    PPQN = 96
    SCSYNTH_PATH = "/Applications/SuperCollider.app/Contents/Resources/scsynth"
    SCSYNTH_SYNTHDEF_PATH = "/Users/francescodani/Library/Application Support/SuperCollider/synthdefs"
    AMBISONICS_KERNEL_PATH = "/Users/francescodani/Documents/SoundDesigner/ATK/FOA kernels"
    DEBUG_SCSYNTH_LOG = True


class SCSYNTH:
    ''' Connect to scsynth '''

    def __init__(self, scsynthPath="/Applications/SuperCollider.app/Contents/Resources/scsynth", ip="127.0.0.1",
                 scsynthOSCPort=57110, pythonOSCPort=57110, tmpfile="sctmp.txt"):
        global SCSYNTH_PATH
        self.scsynthPath = SCSYNTH_PATH
        self.ip = ip
        self.scsynthOSCPort = scsynthOSCPort
        self.pythonOSCPort = pythonOSCPort
        self.tmpfile = tmpfile
        self.numHardwareAudioBusses = 2
        self.first_free_audio_bus = 100
        self.maxAudioBusses = 4096
        self.nodeOrder = []
        self.busyNodes = [0, 1000, 1001]
        self.busyBuffers = [0]
        self.busyAudioBusses = []
        self.bus_values = {}
        self.alloc_buffer_wait_event = ResettableEvent()
        self.atk_kernels = None
        self.is_alive_event = threading.Event()
        self.is_armed = False
        self.is_recording = False
        self.recording_buffer = -1
        self.recording_path = ""
        self.recording_synth = None


        conf = cp.ConfigParser()
        conf.read(CONFIG_PATH)  # config_path
        try:
            PPQN = conf.getint("GENERAL", "ppqn")
            SCSYNTH_PATH = conf.get("SCSYNTH", "scsynth_path")
            NUM_HW_IN = conf.get("SCSYNTH", "num_hw_in")
            NUM_HW_OUT = conf.get("SCSYNTH", "num_hw_out")
            MAX_AUDIO_BUSSES = conf.get("SCSYNTH", "max_audio_busses")
            MAX_AUDIO_BUFFERS = conf.get("SCSYNTH", "max_audio_buffers")
            SAMPLE_RATE = conf.getint("SCSYNTH", "sample_rate")
            BLOCK_SIZE = conf.get("SCSYNTH", "block_size")
            HARDWARE_BUFFER_SIZE = conf.get("SCSYNTH", "hardware_buffer_size")
            RT_MEM_SIZE = conf.get("SCSYNTH", "rt_mem_size")
            HARDWARE_DEVICE_NAME = conf.get("SCSYNTH", "hardware_device_name")
            RECORDING_NUM_CHANNELS = conf.getint("SCSYNTH", "recording_num_channels")
            RECORDING_HEADER_FORMAT = conf.get("SCSYNTH", "recording_header_format")
            RECORDING_SAMPLE_FORMAT = conf.get("SCSYNTH", "recording_sample_format")
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
        self.sample_rate = SAMPLE_RATE
        self.block_size = BLOCK_SIZE
        self.hardware_device_name = HARDWARE_DEVICE_NAME
        self.recording_num_channels = RECORDING_NUM_CHANNELS
        self.recording_header_format = RECORDING_HEADER_FORMAT
        self.recording_sample_format = RECORDING_SAMPLE_FORMAT

    # self.connect()

    ''' Get node order '''

    def get_node_order(self):
        return self.nodeOrder

    ''' Print scsynth's stdout thread '''

    def logging_thread_func(self):
        while True:
            line = self.process_stdout.readline()
            if DEBUG_SCSYNTH_LOG:
                c_print("yellow", line.replace("\n", ""))
            if line == "NODE TREE Group 0\n":  # This line delimits a new node order, so flush node order vector
                self.nodeOrder = []
            # print(line.split(" "))
            else:
                split = line.split(" ")
                if len(split) == 5:
                    if split[0] == '' and split[1] == '' and split[2] == '' and split[3].isnumeric():
                        self.nodeOrder.append([int(split[3]), split[4].replace("\n", "")])
                    # print(line.split(" "))

    ''' Start Server '''

    def start(self):
        conf = cp.ConfigParser()
        conf.read(CONFIG_PATH)  # "config.ini"
        try:
            PPQN = conf.getint("GENERAL", "ppqn")
            SCSYNTH_PATH = conf.get("SCSYNTH", "scsynth_path")
            AMBISONICS_KERNEL_PATH = "/Users/francescodani/Documents/SoundDesigner/ATK/FOA kernels"
            NUM_HW_IN = conf.getint("SCSYNTH", "num_hw_in")
            NUM_HW_OUT = conf.getint("SCSYNTH", "num_hw_out")
            NUM_WIRE_BUFFERS = conf.getint("SCSYNTH", "num_wire_buffers")
            MAX_AUDIO_BUSSES = conf.getint("SCSYNTH", "max_audio_busses")
            MAX_AUDIO_BUFFERS = conf.getint("SCSYNTH", "max_audio_buffers")
            SAMPLE_RATE = conf.getint("SCSYNTH", "sample_rate")
            BLOCK_SIZE = conf.getint("SCSYNTH", "block_size")
            HARDWARE_BUFFER_SIZE = conf.getint("SCSYNTH", "hardware_buffer_size")
            RT_MEM_SIZE = conf.getint("SCSYNTH", "rt_mem_size")
            HARDWARE_DEVICE_NAME = conf.get("SCSYNTH", "hardware_device_name")
            RECORDING_NUM_CHANNELS = conf.getint("SCSYNTH", "recording_num_channels")
            RECORDING_HEADER_FORMAT = conf.get("SCSYNTH", "recording_header_format")
            RECORDING_SAMPLE_FORMAT = conf.get("SCSYNTH", "recording_sample_format")
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
        self.mem_size = RT_MEM_SIZE
        self.sample_rate = SAMPLE_RATE
        self.block_size = BLOCK_SIZE
        self.hardware_device_name = HARDWARE_DEVICE_NAME
        self.recording_num_channels = RECORDING_NUM_CHANNELS
        self.recording_header_format = RECORDING_HEADER_FORMAT
        self.recording_sample_format = RECORDING_SAMPLE_FORMAT
        subprocess.call("killall scsynth", shell=True)
        self.master, slave = pty.openpty()
        print("self.master, slave = ", self.master, slave)
        # TODO: aggiungere set di SAMPLE_RATE etc.
        subprocess.call(
            SCSYNTH_PATH + f' -H "{HARDWARE_DEVICE_NAME}" -u {self.scsynthOSCPort} -m {self.mem_size} -B 0.0.0.0 -c 16384 -a {MAX_AUDIO_BUSSES} -w {NUM_WIRE_BUFFERS} -z {BLOCK_SIZE} -Z {HARDWARE_BUFFER_SIZE} -n 4096 -m 262144 -S {SAMPLE_RATE} -b {MAX_AUDIO_BUFFERS} -m {RT_MEM_SIZE} -D 1 &',
            shell=True, stdin=subprocess.PIPE, stdout=slave, stderr=slave, close_fds=True)
        self.process_stdout = os.fdopen(self.master)
        self.logging_thread = Thread(target=self.logging_thread_func, daemon=True)
        self.logging_thread.start()
        # self.start_scsynth()
        try:
            self.connect()
        except:
            print("scsynth already running with other client...")
        time.sleep(3)
        self.atk_kernels = AmbisonicsKernelBufferManager(AMBISONICS_KERNEL_PATH, scsynth, ATK_BUFFER_SIZE)
        self.atk_kernels.alloc_binaural_kernels()
        print(self.atk_kernels.get_binaural_kernels())

    def start_scsynth(self):
        # Avvia scsynth con porte specifiche
        command = [
            self.scsynthPath,
            '-u', str(self.scsynthOSCPort),  # Porta per i messaggi in arrivo
        ]
        self.scsynth_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for line in self.scsynth_process.stdout:
            line = line.decode('utf-8').strip()
            print(line)
            if "SuperCollider 3 server ready." in line:
                break

    ''' Create a OSC Client and a OSC Server to share data '''

    def connect(self):
        # OSC Client
        self.is_alive_event = threading.Event()
        self.client = None
        self.client = udp_client.SimpleUDPClient(self.ip, self.scsynthOSCPort)
        self.client._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.client._sock.bind(('', 0))
        adress, self.client_port = self.client._sock.getsockname()  # get source port
        print("self.client address:", adress, self.client_port)
        # OSC Dispatcher
        self.dispatcher = dispatcher.Dispatcher()
        # self.dispatcher.map("/*", print)
        self.dispatcher.map("/c_set", self.bus_value_update_func)  # QUESTO SERVE NON SOLO PER PRINT!!!!!!!
        self.dispatcher.map("/done", self.manage_done)
        self.dispatcher.map("/b_info", self.manage_b_info)
        self.scsynth_thread = Thread(target=self.start_server_in_thread_func, daemon=True)
        self.scsynth_thread.start()
        osc_startup()
        print("waiting for scsynth to start...")
        while not self.is_alive_event.is_set():
            self.notify()
            time.sleep(0.1)
        return self

    def start_server_in_thread_func(self):
        try:
            self.server.server_close()
        except:
            pass
        osc_server.ThreadingOSCUDPServer.allow_reuse_address = True
        self.server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", self.client_port), self.dispatcher)
        print("self.server address:", self.server.server_address)
        self.server.serve_forever()
        functions.kill_scsynth_on_sigkill()

    ''' Send a OSC Message to scsynth's OSC Server '''

    def sendMessage(self, tag="/s_new", args=["default", -1, 0, 0, "freq", 1240, "amp", 1]):
        self.client.send_message(tag, args)
        return self

    def sendBundle(self, main_msg, completion_msg):
        main_msg_bytes = oscbuildparse.encode_packet(main_msg)
        completion_msg_bytes = oscbuildparse.encode_packet(completion_msg)
        osc_packet = oscbuildparse.OSCBundle(0, [main_msg_bytes, completion_msg_bytes])
        bundle_bytes = oscbuildparse.encode_packet(osc_packet)
        self.client.send(osc_packet)

    def quit(self):
        print(f"Quitting scsynth listening on {self.client_port}")
        self.sendMessage("/quit", [])

    def notify(self):
        self.sendMessage("/notify", [1])

    def bus_value_update_func(self, *args):
        self.bus_values[str(args[1])] = args[2]
        # print("self.bus_values[str(args[1])]:", self.bus_values[str(args[1])])

    def manage_done(self, *args):
        print("Done found:", args)
        if str(args[1]) == "/notify":
            print(args)
            self.is_alive_event.set()
        if str(args[1]) == "/b_allocReadChannel":
            self.alloc_buffer_wait_event.set()

    def manage_b_info(self, *args):
        print("/b_info found:", args)

    def pollControlBus(self, bus=3):
        self.client.send_message("/c_get", bus)

    def freeNode(self, node):
        self.sendMessage(tag="/n_free", args=[node])

    """ Load a Synth Definition """

    def loadSynthDef(self, synthDefFilePath):
        self.client.send_message("/d_load", synthDefFilePath)

    """ Load a Folder of Synth Definition Files """

    def loadSynthDefDir(self, synthDefDir):
        for file in os.listdir(synthDefDir):
            if ".scsyndef" in file:
                self.loadSynthDef(synthDefDir + file)

    ''' Alloc a Buffer with number of frames and channel. "bufnum" must be unique for the session!!! '''

    def allocBuffer(self, frames, channels, bufnum):
        self.sendMessage("/b_alloc", [bufnum, frames, channels])

    ''' Alloc a soundfile and read its content into a Buffer. "bufnum" must be unique for the session!!! '''

    def allocReadBuffer(self, fullpath, bufnum):
        self.sendMessage("/b_allocRead", [bufnum, os.path.abspath(fullpath)])
        return bufnum

    def allocReadBufferChannel(self, fullpath, bufnum, channel):
        self.alloc_buffer_wait_event.clear()
        self.sendMessage("/b_allocReadChannel", [bufnum, os.path.abspath(fullpath), 0, 0, channel])
        self.alloc_buffer_wait_event.wait()
        return bufnum

    ''' Store a local buffer to file '''

    def writeBuffer(self, fullpath, bufnum, header="wav", fmt="int16"):
        c_print("green", f"saving buffer {bufnum} to {fullpath}")
        self.sendMessage("/b_write", [bufnum, fullpath, header, fmt, -1, 0, 0])

    ''' Load a synth definition file to the server '''

    def loadDefFile(self, fullpath):
        self.sendMessage("/d_load", [fullpath])

    ''' Add a new available node ID to the server '''

    def addNode(self, node_id):
        if node_id not in self.busyNodes:
            self.busyNodes.append(node_id)
        else:
            print("Node", node_id, "is already busy")

    ''' Remove an existing node ID from the server '''

    def removeNode(self, node_id):
        if node_id in self.busyNodes:
            self.busyNodes.remove(node_id)
        else:
            print("Node", node_id, "is already free")

    ''' Return an available node ID from the server and put it in busy node list '''

    def queryFreeNode(self):
        node = np.random.randint(1001, 999999)
        while node in self.busyNodes:
            node = np.random.randint(1001, 999999)
        self.addNode(node)
        return node

    ''' Get currently busy nodes '''

    def getBusyNodes(self):
        return self.busyNodes

    ''' Dump node tree of the server '''

    def dumpNodeTree(self, group=0, showArgs=True):
        if showArgs:
            self.sendMessage("/g_dumpTree", [group, 1])
        else:
            self.sendMessage("/g_dumpTree", [group, 0])

    ''' Add a new available buffer number to the server '''

    def addBuffer(self, bufnum):
        if bufnum not in self.busyBuffers:
            self.busyBuffers.append(bufnum)
            return bufnum
        else:
            c_print("red", f"Buffer {bufnum} is already busy")
            return -1

    ''' Remove an existing buffer from the server '''

    def removeBuffer(self, bufnum):
        if bufnum in self.busyBuffers:
            self.busyBuffers.remove(bufnum)
        else:
            print("Buffer", bufnum, "is already free")

    ''' Return an available bu from the server and put it in busy audio busses list '''

    def queryFreeBuffer(self):
        if len(self.busyBuffers) > 1:
            last_busy_buffer = max(self.busyBuffers)
            return 1 + last_busy_buffer
        elif len(self.busyBuffers) == 1:
            return 1 + self.busyBuffers[0]
        else:
            return 1

    ''' Add a new available bus to the server '''

    def addAudioBus(self, bus):
        if bus not in self.busyAudioBusses:
            self.busyAudioBusses.append(bus)
        else:
            print("Audio Bus", bus, "is already busy")

    ''' Remove an existing bus from the server '''

    def removeAudioBus(self, bus):
        if bus in self.busyAudioBusses:
            self.busyAudioBusses.remove(bus)
        else:
            print("Audio Bus", bus, "is already free")

    ''' Return an available bus from the server and put it in busy audio busses list '''

    def queryFreeAudioBus(self):
        # TODO: implementare ricerca di buchi di canali tra Bus, tipo "defragmentazione"
        if len(self.busyAudioBusses) > 1:
            last_busy_bus = 0
            for bus in self.busyAudioBusses:
                first_chan = bus.getFirstChan()
                n_chans = bus.getNumChans()
                if (first_chan + n_chans) > last_busy_bus:
                    last_busy_bus = first_chan + n_chans
            ret = self.first_free_audio_bus + last_busy_bus

        elif len(self.busyAudioBusses) == 1:
            ret = self.first_free_audio_bus + self.busyAudioBusses[0].getFirstChan() + self.busyAudioBusses[0].getNumChans()
        else:
            ret = self.first_free_audio_bus + 1
        # self.addAudioBus(ret)
        return ret

    def getDefaultInBus(self):
        return self.maxAudioBusses - 32

    def getDefaultOutBus(self):
        return self.maxAudioBusses - 16

    def getSampleRate(self):
        return self.sample_rate

    def freeAllNodes(self):
        for node in self.busyNodes:
            self.sendMessage("/n_free", [node])
        self.busyNodes = []

    def prepare_for_record(self, path):
        self.recording_path = path
        self.recording_buffer = self.addBuffer(self.queryFreeBuffer())
        main_msg = OscMessageBuilder(address="/b_alloc")
        main_msg.add_arg(int(self.recording_buffer))
        # main_msg.add_arg(65536)
        main_msg.add_arg(int(2**(math.ceil(math.log(self.sample_rate, 2)))))
        main_msg.add_arg(int(self.recording_num_channels))
        main_msg = main_msg.build()
        # Costruisci il messaggio di completamento
        completion_msg = OscMessageBuilder(address="/b_write")
        completion_msg.add_arg(int(self.recording_buffer))
        completion_msg.add_arg(self.recording_path)
        completion_msg.add_arg(self.recording_header_format)
        completion_msg.add_arg(self.recording_sample_format)
        completion_msg.add_arg(0)  # number of frames to write
        completion_msg.add_arg(0)  # starting frame in buffer
        completion_msg.add_arg(1)  # leave file open (1)
        completion_msg = completion_msg.build()
        # Crea un bundle contenente i due messaggi
        bundle = OscBundleBuilder(timestamp=0)
        bundle.add_content(main_msg)
        bundle.add_content(completion_msg)
        bundle = bundle.build()
        # Invia il bundle
        self.client.send(bundle)
        self.is_armed = True

    def is_armed_for_recording(self):
        return self.is_armed

    def start_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.recording_synth = Synth(self, "recording_synth_" + str(self.recording_num_channels), self.queryFreeNode(), ["in", 0, "bufnum", self.recording_buffer], "tail", 0)
            self.dumpNodeTree()
            c_print("red", f"Recording...")

    def stop_recording(self):
        if self.is_recording:
            # self.sendMessage("/b_write", [self.recording_buffer, self.recording_path, self.recording_header_format, self.recording_sample_format, -1, 0, 0])
            self.sendMessage("/b_query", [self.recording_buffer])
            self.sendMessage("/b_close", [self.recording_buffer])
            self.sendMessage("/b_free", [self.recording_buffer])
            self.removeBuffer(self.recording_buffer)
            self.recording_synth.free()
            self.recording_path = ""
            self.recording_synth = None
            self.is_recording = False
            self.is_armed = False


class ResettableEvent:
    def __init__(self):
        self._condition = threading.Condition()
        self._flag = False

    def set(self):
        with self._condition:
            self._flag = True
            self._condition.notify_all()

    def clear(self):
        with self._condition:
            self._flag = False

    def wait(self, timeout=None):
        with self._condition:
            while not self._flag:
                if not self._condition.wait(timeout):
                    return False
            return True


'''

- - Class Synth - -

This class is a convenient port of SuperCollider's Synth class.


- Attributes:

- - server: 
- - - an istance of SCSYNTH class

- - name: 
- - - name of the SynthDef to run

- - args:
- - - pairs of argument name and value

- - addAction:
- - - "head", "tail", "before" or "after"

- - targetID:
- - - addAction's target node


- Usage:

scsynth = SCSYNTH()
id = 0
while True:
	if id % 4 == 0:
		x = Synth(scsynth, "default", ["freq", 440])
	if id % 3 == 0:
		y = Synth(scsynth, "default", ["freq", 660])
	if id % 5 == 0:
		z = Synth(scsynth, "default", ["freq", 880])
	if id % 7 == 0:
		q = Synth(scsynth, "default", ["freq", 220, "amp", 1])
	id = id + 1
	time.sleep(0.125)

'''


class Synth:
    ''' Run the Synth (as SuperCollider's "Synth.new();") '''

    def __init__(self, server, name="default", node=None, args=[], addAction="head", targetID=1000):
        self.server = server
        self.name = name
        # self.name = "default"
        self.args = args
        self.targetID = targetID
        # find a free node in the server
        if node is not None:
            self.node = node
        else:
            self.node = self.server.queryFreeNode()
        # check addAction
        if addAction == "head":
            self.addAction = 0
            self.args = [self.name, self.node, 0, 0] + self.args
        elif addAction == "tail":
            self.addAction = 1
            self.args = [self.name, self.node, self.addAction, self.targetID] + self.args
        elif addAction == "before":
            self.addAction = 2
            self.args = [self.name, self.node, self.addAction, self.targetID] + self.args
        elif addAction == "after":
            self.addAction = 3
            self.args = [self.name, self.node, self.addAction, self.targetID] + self.args
        # run synth in the server
        # print("Sending \s_new to Server with args:", self.args)

        self.server.sendMessage("/s_new", self.args)
        # print("Started Node:", self.node)

    ''' Set a parameter's value of the synth (as SuperCollider's "Synth.set();") '''

    def set(self, param, value):
        # print("synth:", self.name, "node:", self.node, "param:", param, "set to:", value)
        # c_print("red", f"setting synth parameter {param} to {value}")
        self.server.sendMessage("/n_set", [self.node, param, value])
        return self

    ''' Set a set of parameter's value of the synth (as SuperCollider's "Synth.setn();") '''

    def setn(self, paramValuePairs):
        self.server.sendMessage("/n_setn", paramValuePairs)
        return self

    ''' Map an audio rate parameter of the synth to a Bus (as SuperCollider's "Synth.map();") '''

    def map(self, param, value):
        # print("AUDIO MAP: synth:", self.name, "node:", self.node, "param:", param, "set to Bus:", value)
        self.server.sendMessage("/n_mapa", [self.node, param, value])
        return self

    ''' Free the Synth (as SuperCollider's "Synth.free();") '''

    def free(self):
        self.server.sendMessage("/n_free", [self.node])
        self.server.removeNode(self.node)
        # print("\tFreed Node:", self.node)
        return self

    """ Put this synth exactly before the target synth in the server's node order """

    def moveBefore(self, synth):
        self.server.sendMessage("/n_before", [self.node, synth.node])

    """ Put this synth exactly after the target synth in the server's node order """

    def moveAfter(self, synth):
        self.server.sendMessage("/n_after", [self.node, synth.node])

    def moveToTail(self, group=0):
        self.server.sendMessage("/n_order", [1, group, self.node])

    def moveToHead(self, group=0):
        self.server.sendMessage("/n_order", [0, group, self.node])


'''

- - Class Bus - -

This class emulates SuperCollider's Bus class.

- Attributes:

- - n_chans: 
- - - number of channels

- Usage:

'''


class Bus:
    def __init__(self, server, n_chans=1, chans=None):
        self.server = server
        self.n_chans = n_chans
        if chans is not None:
            self.chans = chans
        else:
            self.chans = []
            first_free_chan = self.server.queryFreeAudioBus()
            for i in range(self.n_chans):
                self.chans.append(first_free_chan + i)
        # self.chans = [self.server.queryFreeAudioBus() for _ in range(self.n_chans)]
        self.server.addAudioBus(self)

    def getNumChans(self):
        return self.n_chans

    def getChan(self, index):
        return self.chans[index]

    def getChans(self):
        return self.chans

    def getFirstChan(self):
        if len(self.chans) > 0:
            return self.chans[0]
        else:
            return 0

    def free(self):
        self.server.removeAudioBus(self)

    def __getstate__(self):
        d = {
            "n_chans": self.n_chans,
            "chans": self.chans
        }
        return d

    def __setstate__(self, state):
        self.n_chans = state["n_chans"]
        self.chans = state["chans"]
        if self not in self.server.busyAudioBusses:
            self.server.addAudioBus(self)


'''

- - Class Group --
'''


class Group:
    def __init__(self, server, node=None, addAction="head", targetID=1000):
        self.server = server
        if node is not None:
            self.node = node
            self.server.addNode(self.node)
        else:
            self.node = self.server.queryFreeNode()
        self.targetID = targetID
        if addAction == "head":
            self.addAction = 0
        elif addAction == "tail":
            self.addAction = 1
        elif addAction == "before":
            self.addAction = 2
        elif addAction == "after":
            self.addAction = 3
        self.server.sendMessage("/g_new", [self.node, self.addAction, self.targetID])

    """ Put this synth exactly before the target synth in the server's node order """

    def moveBefore(self, synth):
        self.server.sendMessage("/n_before", [self.node, synth.node])

    """ Put this synth exactly after the target synth in the server's node order """

    def moveAfter(self, synth):
        self.server.sendMessage("/n_after", [self.node, synth.node])

    def moveToTail(self, group=0):
        self.server.sendMessage("/n_order", [1, group, self.node])

    def moveToHead(self, group=0):
        self.server.sendMessage("/n_order", [0, group, self.node])

    def getNodeID(self):
        return self.node

    def getAddAction(self):
        return self.addAction

    def retutrnTargetID(self):
        return self.targetID

    def free(self):
        self.server.sendMessage("/n_free", [self.node])


'''

- - Class Lag - -

This class emulates SuperCollider's Lag class.

- Attributes:

- - lagTime: 
- - - time to reach a value from another

- - power: 
- - - shape of the curves

- - numSteps:
- - - number of steps to reach the end value

- - startValue:
- - - start point of the curve

- - name:
- - - name of the lag


- Usage:

lags = np.ndarray(5, dtype=np.object)
for i in range(len(lags)):
	lags[i] = Lag(name=str(i))
	lags[i].setNewValue(np.random.randint(1.0, 30.0))

'''


class Lag():
    def __init__(self, lagTime=0.1, power=1, numSteps=100, startValue=0.0, name="lag1"):
        self.name = name
        self.lagTime = lagTime
        self.startValue = startValue
        self.currentValue = self.startValue
        self.endValue = self.startValue
        self.power = power
        self.numSteps = numSteps
        self.counter = 0
        self.break_ = False
        self.isRunning = False

    def process(self, newValue=1.0):
        self.endValue = newValue
        self.isRunning = True
        while self.counter <= self.numSteps:
            if self.break_ == True:
                self.break_ = False
                self.startValue = self.currentValue
                break
            self.currentValue = self.startValue + (
                        (self.endValue - self.startValue) * np.power(self.counter / self.numSteps, self.power))
            self.counter = self.counter + 1
            time.sleep(self.lagTime / self.numSteps)
        self.startValue = self.currentValue
        self.isRunning = False
        self.counter = 0

    def setNewValue(self, newValue=1.0):
        if (self.isRunning == True):
            self.break_ = True
        self.thread = Thread(target=self.process, args=[newValue])
        self.thread.start()

    def setLagTime(self, newLagTime=0.1):
        self.lagTime = newLagTime

    def getValue(self):
        return self.currentValue


'''

- - Class CSThread - -

This class executes a concatenative synthesis thread with real time control.


- Attributes:

- - server: 
- - - an istance of SCSYNTH class

- - name: 
- - - name of the SynthDef to run

- - args:
- - - pairs of argument name and value

- - addAction:
- - - "head", "tail", "before" or "after"

- - targetID:
- - - target node 


- Usage:

scsynth = SCSYNTH()
id = 0
while True:
	if id % 4 == 0:
		x = Synth(scsynth, "default", ["freq", 440])
	if id % 3 == 0:
		y = Synth(scsynth, "default", ["freq", 660])
	if id % 5 == 0:
		z = Synth(scsynth, "default", ["freq", 880])
	if id % 7 == 0:
		q = Synth(scsynth, "default", ["freq", 220, "amp", 1])
	id = id + 1
	time.sleep(0.125)

'''


class CSThread(Thread):
    def __init__(self, server, bufnum=0, grainFreq=100, grainDur=0.1, pos=0, amp=0.5, pan=0.5, rate=1, atk=0.5,
                 outCh=20):
        Thread.__init__(self)
        self.verbose = False
        self.scsynth = server
        self.bufnum = bufnum
        self.grainFreq = grainFreq
        self.roundGFreq = 0.0
        self.grainDur = grainDur
        self.pos = pos
        self.amp = amp
        self.pan = pan
        self.rate = rate
        self.roundPitch = 0.0
        self.atk = atk
        self.outCh = outCh
        self.neighborMode = 'Random'
        self.isRunning = False
        self.grainCounter = 0
        self.daemon = True
        self.start()

    def _round(self, number, thresh):
        if thresh != 0:
            result = round(float(number) / thresh) * thresh
            if result != 0:
                return result
            else:
                return thresh
        else:
            return number

    def run(self):
        self.isRunning = True
        self.grainCounter = 0
        while self.isRunning:
            if self.verbose:
                print('buf: {} dur: {} pos: {} amp: {} pan: {} rate: {} atk: {}'.format(type(self.bufnum),
                                                                                        type(self.grainDur),
                                                                                        type(self.pos), type(self.amp),
                                                                                        type(self.pan), type(self.rate),
                                                                                        type(self.atk)))

            if self.isRunning == False:
                break
            # RUN SYNTH ONLY IF AMPLITUDE > 0.0
            if self.amp > 0.0:
                # print(self.bufnum, self.outCh)
                if isinstance(self.pos, (list, np.ndarray, tuple)):
                    if self.neighborMode == 'Circular':
                        self.pos = np.concatenate((self.pos, self.pos[::-1]), axis=0)
                    if self.neighborMode == 'Random':
                        random.shuffle(self.pos)
                        self.chosenPos = int(self.pos[self.grainCounter % len(self.pos)])
                    Synth(self.scsynth, "SCGrain",
                          ["buf", self.bufnum, "dur", self.grainDur, "pos", self.chosenPos, "amp", self.amp, "pan",
                           self.pan, "rate", self._round(self.rate, self.roundPitch), "atk", self.atk, "outCh",
                           self.outCh])
                else:
                    self.chosenPos = self.pos
                    Synth(self.scsynth, "SCGrain",
                          ["buf", self.bufnum, "dur", self.grainDur, "pos", int(self.pos), "amp", self.amp, "pan",
                           self.pan, "rate", self.rate, "atk", self.atk, "outCh", self.outCh])
            '''
			if isinstance(self.grainFreq, (list, np.ndarray, tuple)):
				time.sleep(1.0 / self.grainFreq[self.grainCounter % (len(self.grainFreq)-1)])
			else:
			'''
            time.sleep(self._round(1.0 / self.grainFreq, self.roundGFreq))
            self.grainCounter = self.grainCounter + 1

    def stop(self):
        self.isRunning = False
        self.grainCounter = 0

    def setGrainFreq(self, newGrainFreq):
        self.grainFreq = float(newGrainFreq)

    def setGrainDur(self, newGrainDur):
        self.grainDur = float(newGrainDur)

    def setBufnum(self, newBufnum):
        self.bufnum = int(newBufnum)

    def setPos(self, newPos):
        self.pos = newPos

    def setAmp(self, newAmp):
        self.amp = float(newAmp)

    def setPan(self, newPan):
        self.pan = float(newPan)

    def setRate(self, newRate):
        self.rate = float(newRate)

    def setAtk(self, newAtk):
        self.atk = float(newAtk)

    def setOutCh(self, newOutCh):
        self.outCh = int(newOutCh)

    def setRoundGFreq(self, newRoundGFreq):
        self.roundGFreq = float(newRoundGFreq)

    def setRoundPitch(self, newRoundPitch):
        self.roundPitch = float(newRoundPitch)

    def setParam(self, param, value):
        if param == "Pos":
            self.setPos(value)
        if param == "GrainFreq":
            self.setGrainFreq(value)
        if param == "RoundGFreq":
            self.setRoundGFreq(value)
        if param == "GrainDur":
            self.setGrainDur(value)
        if param == "Amplitude":
            self.setAmp(value)
        if param == "Panning":
            self.setPan(value)
        if param == "GrainAtk":
            self.setAtk(value)
        if param == "Pitch":
            self.setRate(value)
        if param == "RoundPitch":
            self.setRoundPitch(value)

    def getParameters(self):
        self.params = {'Pos': self.pos, 'GrainFreq': self.grainFreq, 'GrainDur': self.grainDur, 'Amplitude': self.amp,
                       'Panning': self.pan, 'GrainAtk': self.atk, 'Pitch': self.rate, 'RoundGFreq': self.roundGFreq,
                       'RoundPitch': self.roundPitch}
        return self.params


class AmbisonicsKernelBufferManager:
    def __init__(self, kernels_path, server, buffer_size):
        self.kernels_path = kernels_path
        self.server = server
        self.sample_rate = str(int(self.server.sample_rate))
        self.buffer_size = buffer_size
        self.binaural_kernels = None

    def alloc_binaural_kernels(self, listener="0165"):
        path = os.path.join(os.path.join(
            os.path.join(os.path.join(os.path.join(self.kernels_path, "decoders"), "cipic"), self.sample_rate),
            self.buffer_size), listener)
        bus_numbers = {}
        for key in ["hrirW_L", "hrirW_R", "hrirX_L", "hrirX_R", "hrirY_L", "hrirY_R", "hrirZ_L", "hrirZ_R"]:
            bufnum = self.server.addBuffer(self.server.queryFreeBuffer())
            bus_numbers[key] = bufnum
        # print("Trying Path:", os.path.join(path, "HRIR_W.wav"))
        self.binaural_kernels = {
            "hrirW_L": self.server.allocReadBufferChannel(os.path.join(path, "HRIR_W.wav"), bus_numbers["hrirW_L"], 0),
            "hrirW_R": self.server.allocReadBufferChannel(os.path.join(path, "HRIR_W.wav"), bus_numbers["hrirW_R"], 1),
            "hrirX_L": self.server.allocReadBufferChannel(os.path.join(path, "HRIR_X.wav"), bus_numbers["hrirX_L"], 0),
            "hrirX_R": self.server.allocReadBufferChannel(os.path.join(path, "HRIR_X.wav"), bus_numbers["hrirX_R"], 1),
            "hrirY_L": self.server.allocReadBufferChannel(os.path.join(path, "HRIR_Y.wav"), bus_numbers["hrirY_L"], 0),
            "hrirY_R": self.server.allocReadBufferChannel(os.path.join(path, "HRIR_Y.wav"), bus_numbers["hrirY_R"], 1),
            "hrirZ_L": self.server.allocReadBufferChannel(os.path.join(path, "HRIR_Z.wav"), bus_numbers["hrirZ_L"], 0),
            "hrirZ_R": self.server.allocReadBufferChannel(os.path.join(path, "HRIR_Z.wav"), bus_numbers["hrirZ_R"], 1)
        }
        return self.binaural_kernels

    def get_binaural_kernels(self):
        if self.binaural_kernels is None:
            self.alloc_binaural_kernels()
        return self.binaural_kernels


# INSTANTIATE SCSYNTH BY DEFAULT?
if True:
    scsynth = SCSYNTH()
    atk_kernels = None

if __name__ == "__main__":
    print(__doc__)
