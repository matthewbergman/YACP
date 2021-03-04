"""
yacp.py
Yet Another Calibration Protocol (YACP)

This is the main calibration GUI for interfacing with YACP implementing firmware projects.

Matthew Bergman 2021

MIT license, all text above must be included in any redistribution.
See license.txt at the root of the repository for full license text.
"""

import traceback
import csv
import json
import struct
import sys
import time
import can

from PyQt5.QtCore import Qt, QObject
from PyQt5.QtCore import QThread
from PyQt5.QtCore import QIODevice
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QTimer

lengths = {}
lengths["uint8"] = 1
lengths["int8"] = 1
lengths["uint16"] = 2
lengths["int16"] = 2
lengths["uint32"] = 4
lengths["int32"] = 4
lengths["float"] = 4

class CANThread(QThread):
    YACP_COMMAND_ID = 0x100
    YACP_UPDATE_ID = 0x101

    update_measurement_signal = pyqtSignal(int,int,int,int,int,int)
    update_setting_signal = pyqtSignal(int,int,int,int,int,int)
    update_override_signal = pyqtSignal(bool,int,int,int,int,int,int)
    update_hello_signal = pyqtSignal(int,int,int,int,int)
    send_status_signal = pyqtSignal(int)
    
    def __init__(self):
        self.bus = None
        self.device_id = -1
        self.stop = False
        
        QThread.__init__(self)

    def connect(self, _type, _channel, _bitrate):
        try:
            self.bus = can.interface.Bus(bustype=_type, channel=_channel, bitrate=_bitrate)
            self.send_status_signal.emit(0)
        except:
            self.bus = None
            traceback.print_exc()
            self.send_status_signal.emit(1)

    def disconnect(self):
        try:
            self.bus.shutdown()
            self.send_status_signal.emit(2)
        except:
            pass
        self.bus = None

    # run method gets called when we start the thread
    def run(self):
        while self.stop == False:
            if self.bus != None:
                for msg in self.bus:
                    if msg.arbitration_id == YACPProtocol.YACP_UPDATE_ID:
                        device_id = msg.data[0] >> 4
                        message_type = msg.data[0] & 0x0F
                        var_start = msg.data[1]
                        var_start |= msg.data[2] << 8
                        var_len = msg.data[3]

                        if message_type == YACPProtocol.CAL_HELLO:
                            firmware_version = msg.data[4]
                            product_id = msg.data[5]
                            cal_revision = msg.data[6]
                            cal_protocol = msg.data[7]
                            
                            self.update_hello_signal.emit(device_id, firmware_version, product_id, cal_revision, cal_protocol)

                        if device_id != self.device_id:
                            continue

                        if message_type == YACPProtocol.CAL_READ_MEASUREMENT:               
                            self.update_measurement_signal.emit(var_start,var_len,msg.data[4],msg.data[5],msg.data[6],msg.data[7])
                        elif message_type == YACPProtocol.CAL_READ_SETTING:
                            self.update_setting_signal.emit(var_start,var_len,msg.data[4],msg.data[5],msg.data[6],msg.data[7])
                        elif message_type == YACPProtocol.CAL_OVERRIDE_ON:
                            self.update_override_signal.emit(True,var_start,var_len,msg.data[4],msg.data[5],msg.data[6],msg.data[7])
                        elif message_type == YACPProtocol.CAL_OVERRIDE_OFF:
                            self.update_override_signal.emit(False,var_start,var_len,msg.data[4],msg.data[5],msg.data[6],msg.data[7])

    @pyqtSlot(int)
    def setDeviceId(self, device_id):
        self.device_id = device_id

    @pyqtSlot(int,int,int,int,int,int)
    def setSetting(self, var_start, var_len, b0,b1,b2,b3):
        msg_data = [0,0,0,0,0,0,0,0]
        msg_id = YACPProtocol.YACP_COMMAND_ID

        msg_data[0] = (self.device_id << 4) | YACPProtocol.CAL_UPDATE_SETTING
        msg_data[1] = var_start & 0xFF
        msg_data[2] = var_start >> 8
        msg_data[3] = var_len
        msg_data[4] = b0
        msg_data[5] = b1
        msg_data[6] = b2
        msg_data[7] = b3

        self.sendCANMessage(msg_id, msg_data)

    @pyqtSlot(int,int,int,int,int,int,int)
    def setOverride(self, enabled, var_start, var_len, b0,b1,b2,b3):
        msg_data = [0,0,0,0,0,0,0,0]
        msg_id = YACPProtocol.YACP_COMMAND_ID

        if enabled == True:
            msg_data[0] = (self.device_id << 4) | YACPProtocol.CAL_OVERRIDE_ON
        else:
            msg_data[0] = (self.device_id << 4) | YACPProtocol.CAL_OVERRIDE_OFF
        msg_data[1] = var_start & 0xFF
        msg_data[2] = var_start >> 8
        msg_data[3] = var_len
        msg_data[4] = b0
        msg_data[5] = b1
        msg_data[6] = b2
        msg_data[7] = b3

        self.sendCANMessage(msg_id, msg_data)

    @pyqtSlot()
    def sendHello(self):
        msg_data = [YACPProtocol.CAL_HELLO,0,0,0,0,0,0,0]
        msg_id = YACPProtocol.YACP_COMMAND_ID

        msg = can.Message(arbitration_id=msg_id, is_extended_id=False, data=msg_data)
        if self.bus != None:
            try:
                self.bus.send(msg, 1)
            except:
                traceback.print_exc()

    @pyqtSlot()
    def sendSaveSettings(self):
        msg_data = [0,0,0,0,0,0,0,0]
        msg_id = YACPProtocol.YACP_COMMAND_ID

        msg_data[0] = (self.device_id << 4) | CAL_SAVE_SETTINGS

        self.sendCANMessage(msg_id, msg_data)

    @pyqtSlot(int,int)
    def readMeasurement(self, var_start, var_len):
        msg_data = [0,0,0,0,0,0,0,0]
        msg_id = YACPProtocol.YACP_COMMAND_ID

        msg_data[0] = (self.device_id << 4) | YACPProtocol.CAL_READ_MEASUREMENT
        msg_data[1] = var_start & 0xFF
        msg_data[2] = var_start >> 8
        msg_data[3] = var_len
        msg_data[4] = 0
        msg_data[5] = 0
        msg_data[6] = 0
        msg_data[7] = 0

        self.sendCANMessage(msg_id, msg_data)

    @pyqtSlot(int,int)
    def readSetting(self, var_start, var_len):
        msg_data = [0,0,0,0,0,0,0,0]
        msg_id = YACPProtocol.YACP_COMMAND_ID

        msg_data[0] = (self.device_id << 4) | YACPProtocol.CAL_READ_SETTING
        msg_data[1] = var_start & 0xFF
        msg_data[2] = var_start >> 8
        msg_data[3] = var_len
        msg_data[4] = 0
        msg_data[5] = 0
        msg_data[6] = 0
        msg_data[7] = 0

        self.sendCANMessage(msg_id, msg_data)

    @pyqtSlot(int,int)
    def readOverride(self, var_start, var_len):
        msg_data = [0,0,0,0,0,0,0,0]
        msg_id = YACPProtocol.YACP_COMMAND_ID

        msg_data[0] = (self.device_id << 4) | YACPProtocol.CAL_READ_OVERRIDE
        msg_data[1] = var_start & 0xFF
        msg_data[2] = var_start >> 8
        msg_data[3] = var_len
        msg_data[4] = 0
        msg_data[5] = 0
        msg_data[6] = 0
        msg_data[7] = 0

        self.sendCANMessage(msg_id, msg_data)

    def sendCANMessage(self, msg_id, msg_data):
        if self.device_id == -1:
            return
        
        msg = can.Message(arbitration_id=msg_id, is_extended_id=False, data=msg_data)
        if self.bus != None:
            try:
                self.bus.send(msg, 1)
            except:
                traceback.print_exc()

class YACPProtocol(QObject):
    YACP_COMMAND_ID = 0x100
    YACP_UPDATE_ID = 0x101
    
    CAL_UPDATE_SETTING = 0
    CAL_READ_SETTING = 1
    CAL_OVERRIDE_ON = 2
    CAL_OVERRIDE_OFF = 3
    CAL_READ_OVERRIDE = 4
    CAL_READ_MEASUREMENT = 5
    CAL_SAVE_SETTINGS = 6
    CAL_HELLO = 7
    CAL_ACK = 8

    DEVICE_STATE_DISCONNECTED = 0
    DEVICE_STATE_READING_SETTINGS = 1
    DEVICE_STATE_READING_OVERRIDES = 2
    DEVICE_STATE_READING_MEASUREMENTS = 3
    DEVICE_STATE_CONNECTED = 4

    set_setting_signal = pyqtSignal(int,int,int,int,int,int)
    set_override_signal = pyqtSignal(int,int,int,int,int,int,int)
    send_hello_signal = pyqtSignal()
    save_settings_signal = pyqtSignal()
    set_device_id_signal = pyqtSignal(int)
    read_measurement_signal = pyqtSignal(int,int)
    read_setting_signal = pyqtSignal(int,int)
    read_override_signal = pyqtSignal(int,int)

    app_update_device_state_signal = pyqtSignal()
    app_update_measurement_signal = pyqtSignal(int,int)
    app_update_setting_signal = pyqtSignal(int,int)
    app_update_override_signal = pyqtSignal(int,int,int)
    app_update_devices_signal = pyqtSignal()
    app_update_can_status_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        
        self.measurements = {}
        self.overrides = {}
        self.settings = {}
        self.devices = {}

        self.num_measurements = 0
        self.num_settings = 0
        self.num_overrides = 0

        self.device_state = YACPProtocol.DEVICE_STATE_DISCONNECTED
        self.read_measurement_index = 0
        self.read_setting_index = 0
        self.read_override_index = 0
        self.device_id = -1
        self.can_state = 0

        self.can_thread = CANThread()
        
        self.can_thread.update_measurement_signal.connect(self.updateMeasurement)
        self.can_thread.update_setting_signal.connect(self.updateSetting)
        self.can_thread.update_override_signal.connect(self.updateOverride)
        self.can_thread.update_hello_signal.connect(self.updateDeviceList)
        self.can_thread.send_status_signal.connect(self.handleCANStatus)
        
        self.set_setting_signal.connect(self.can_thread.setSetting)
        self.set_override_signal.connect(self.can_thread.setOverride)
        self.send_hello_signal.connect(self.can_thread.sendHello)
        self.save_settings_signal.connect(self.can_thread.sendSaveSettings)
        self.set_device_id_signal.connect(self.can_thread.setDeviceId)
        self.read_measurement_signal.connect(self.can_thread.readMeasurement)
        self.read_setting_signal.connect(self.can_thread.readSetting)
        self.read_override_signal.connect(self.can_thread.readOverride)

        self.can_thread.start()

        self.timer = QTimer(self) 
        self.timer.timeout.connect(self.tick) 
        self.timer.start(20)

    def close(self):
        self.timer.stop()
        self.can_thread.disconnect()
        self.can_thread.stop = True
        self.can_thread.wait()

    def loadDefFile(self, fileName):
        self.measurements = {}
        self.settings = {}
        self.overrides = {}

        measurement_offset = 0
        override_offset = 0
        setting_offset = 0
        revision = -1
        
        with open(fileName, newline='\n') as def_file:
            defs = json.load(def_file)

            for m in defs["measurements"]:
                if "unit" not in m.keys():
                    unit = ""
                else:
                    unit = m["unit"]
                
                measurement = Measurement(m["name"], m["type"], unit, measurement_offset, self.num_measurements)

                if "values" in m.keys():
                    for value in m["values"]:
                        measurement.values[value["value"]] = value["name"]
                
                self.measurements[measurement_offset] = measurement
                measurement_offset += lengths[m["type"]]
                self.num_measurements += 1
                
            for s in defs["settings"]:
                if "unit" not in s.keys():
                    unit = ""
                else:
                    unit = s["unit"]
                    
                setting = Setting(s["name"], None, s["type"], unit, s["default"], setting_offset, self.num_settings)

                if "choices" in s.keys():
                    for choice in s["choices"]:
                        setting.choices[choice["value"]] = choice["name"]
                
                self.settings[setting_offset] = setting
                setting_offset += lengths[s["type"]]
                self.num_settings += 1

                if s["name"] == 'revision':
                    revision = s["default"]

            for o in defs["overrides"]:
                if "unit" not in o.keys():
                    unit = ""
                else:
                    unit = o["unit"]
                    
                override = Override(o["name"], o["type"], unit, override_offset, self.num_overrides)
                self.overrides[override_offset] = override
                override_offset += 5
                self.num_overrides += 1
                
        return revision

    def loadCalFile(self, fileName):
        with open(fileName, newline='\n') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in reader:
                try:
                    name = row[0]
                    str_val = row[1]
                    str_type = row[2]
                    str_unit = row[3]
                except:
                    print("Failed to load: "+",".join(row))
                    continue

                for offset in self.settings:
                    if self.settings[offset].name != name:
                        continue

                    if self.settings[offset].cal_type == "float":
                        self.settings[offset].value = float(str_val)
                    else:
                        self.settings[offset].value = int(str_val)

    def exportSettingsCSV(self, fileName):
        with open(fileName, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(['Name','Value'])

            for i in range(0, self.num_settings):
                setting_key = [*self.settings][i]
                setting = self.settings[setting_key]

                label = ""
                if len(setting.choices) != 0:
                    for choice in setting.choices.keys():
                        if str(choice) == str(setting.value):
                            label = setting.choices[choice]
                            break
                    
                writer.writerow([setting.name,setting.value,setting.cal_type,setting.unit,label])

                        
    def getValueFromBytes(self,cal_type,b0,b1,b2,b3):
        if cal_type == "uint8":
            [typed_value] = struct.unpack('>B',bytes([b0]))
        elif cal_type == "int8":
            [typed_value] = struct.unpack('>b',bytes([b0]))
        elif cal_type == "uint16":
            [typed_value] = struct.unpack('>H',bytes([b1,b0]))
        elif cal_type == "int16":
            [typed_value] = struct.unpack('>h',bytes([b1,b0]))
        elif cal_type == "uint32":
            [typed_value] = struct.unpack('>I',bytes([b3,b2,b1,b0]))
        elif cal_type == "int32":
            [typed_value] = struct.unpack('>i',bytes([b3,b2,b1,b0]))
        elif cal_type == "float":
            [typed_value] = struct.unpack('>f',bytes([b3,b2,b1,b0]))

        #print(str(b3)+" "+str(b2)+" "+str(b1)+" "+str(b0)+" = "+str(typed_value))
            
        return typed_value

    def getBytesFromValue(self,cal_type,val):
        if cal_type == "uint8":
            bs = struct.pack('>B',val)
        elif cal_type == "int8":
            bs = struct.pack('>b',val)
        elif cal_type == "uint16":
            bs = struct.pack('>H',val)
        elif cal_type == "int16":
            bs = struct.pack('>h',val)
        elif cal_type == "uint32":
            bs = struct.pack('>I',val)
        elif cal_type == "int32":
            bs = struct.pack('>i',val)
        elif cal_type == "float":
            bs = struct.pack('>f',val)

        ints = list(bs)
        ints += [0] * (4 - len(ints))

        #print(cal_type+" "+str(val)+" = "+str(ints[3])+" "+str(ints[2])+" "+str(ints[1])+" "+str(ints[0]))

        return ints

    def saveSettings(self):
        self.save_settings_signal.emit()

    #@pyqtSlot(int,int,int,int,int,int)
    def updateMeasurement(self, var_start, var_len, b0,b1,b2,b3):
        table_index = self.measurements[var_start].index
        cal_type = self.measurements[var_start].cal_type
        value = self.getValueFromBytes(cal_type,b0,b1,b2,b3)

        self.measurements[var_start].value = value

        self.app_update_measurement_signal.emit(table_index, var_start)

    #@pyqtSlot(int,int,int,int,int,int)
    def updateSetting(self, var_start, var_len, b0,b1,b2,b3):
        table_index = self.settings[var_start].index
        cal_type = self.settings[var_start].cal_type
        value = self.getValueFromBytes(cal_type,b0,b1,b2,b3)

        self.settings[var_start].value = value

        self.app_update_setting_signal.emit(table_index, var_start)

    #@pyqtSlot(bool,int,int,int,int,int,int)
    def updateOverride(self, overridden, var_start, var_len, b0,b1,b2,b3):
        table_index = self.overrides[var_start].index
        cal_type = self.overrides[var_start].cal_type
        value = self.getValueFromBytes(cal_type,b0,b1,b2,b3)

        self.overrides[var_start].value = value

        if overridden:
            self.overrides[var_start].status = "Overridden"
        else:
            self.overrides[var_start].status = "Passthrough"
        
        self.app_update_override_signal.emit(table_index, var_start, overridden)
        
    #@pyqtSlot(int,int,int,int,int)
    def updateDeviceList(self, device_id, firmware_version, product_id, cal_revision, cal_protocol):
        self.devices[device_id] = Device(device_id, firmware_version, product_id, cal_revision, cal_protocol)
        
        self.app_update_devices_signal.emit()

    def sendHello(self):
        self.devices.clear()
        
        self.send_hello_signal.emit()

    def deviceConnect(self, device_id):
        self.device_id = device_id
        self.set_device_id_signal.emit(device_id)

        self.read_measurement_index = 0
        self.read_setting_index = 0
        self.read_override_index = 0
        self.device_state = YACPProtocol.DEVICE_STATE_READING_SETTINGS

    def readMeasurement(self):
        measurement_key = [*self.measurements][self.read_measurement_index]
        measurement = self.measurements[measurement_key]
        
        var_start = measurement.offset
        var_len = lengths[measurement.cal_type]
        
        self.read_measurement_signal.emit(var_start, var_len)

    def readSetting(self):
        setting_key = [*self.settings][self.read_setting_index]
        setting = self.settings[setting_key]
        
        var_start = setting.offset
        var_len = lengths[setting.cal_type]
        
        self.read_setting_signal.emit(var_start, var_len)

    def readOverride(self):
        override_key = [*self.overrides][self.read_override_index]
        override = self.overrides[override_key]
        
        var_start = override.offset
        var_len = lengths[override.cal_type]
        
        self.read_override_signal.emit(var_start, var_len)

    def sendSettingChange(self, setting_key, str_val):
        setting = self.settings[setting_key]

        if setting.cal_type == 'float':
            setting.value = float(str_val)
        else:
            setting.value = int(str_val)

        [b0,b1,b2,b3] = self.getBytesFromValue(setting.cal_type, setting.value)

        self.set_setting_signal.emit(setting.offset, lengths[setting.cal_type], b0,b1,b2,b3)

    def sendOverrideChange(self, override_key, str_val, override_status):
        override = self.overrides[override_key]
        
        if override.cal_type == 'float':
            override.value = float(str_val)
        else:
            override.value = int(str_val)

        override.status = override_status
        enabled = False
        if override.status == "Overridden":
            enabled = True

        [b0,b1,b2,b3] = self.getBytesFromValue(override.cal_type, override.value)

        #print(str(enabled)+" "+str(b0)+" "+str(b1)+" "+str(b2)+" "+str(b3)+" "+str(override.value))

        self.set_override_signal.emit(enabled, override.offset, lengths[override.cal_type], b0,b1,b2,b3)

    def tick(self):
        if self.device_state == YACPProtocol.DEVICE_STATE_DISCONNECTED:
            pass
        
        elif self.device_state == YACPProtocol.DEVICE_STATE_READING_SETTINGS:
            self.app_update_device_state_signal.emit()
            
            self.readSetting()

            self.read_setting_index += 1
            if self.read_setting_index >= self.num_settings:
                self.device_state = YACPProtocol.DEVICE_STATE_READING_OVERRIDES
                self.read_setting_index = 0
                
        elif self.device_state == YACPProtocol.DEVICE_STATE_READING_OVERRIDES:
            self.app_update_device_state_signal.emit()
            
            self.readOverride()

            self.read_override_index += 1
            if self.read_override_index >= self.num_overrides:
                self.device_state = YACPProtocol.DEVICE_STATE_READING_MEASUREMENTS
                self.read_overrides_index = 0
        
        elif self.device_state == YACPProtocol.DEVICE_STATE_READING_MEASUREMENTS:
            self.app_update_device_state_signal.emit()
            
            self.readMeasurement()

            self.read_measurement_index += 1
            if self.read_measurement_index >= self.num_measurements:
                self.device_state = YACPProtocol.DEVICE_STATE_CONNECTED
                self.read_measurement_index = 0

                self.app_update_device_state_signal.emit()
            
        elif self.device_state == YACPProtocol.DEVICE_STATE_CONNECTED:
            self.readMeasurement()
            self.read_measurement_index += 1
            if self.read_measurement_index >= self.num_measurements:
                self.read_measurement_index = 0

    def connect(self, bustype, interface, bitrate, connect):
        if connect == True:
            self.can_thread.connect(bustype, interface, bitrate)
        else:
            self.can_thread.disconnect()

    @pyqtSlot(int)
    def handleCANStatus(self, status):
        if status == 1:
            self.can_state = 0
        elif status == 0:
            self.can_state = 1
        elif status == 2:
            self.can_state = 0
            
        self.app_update_can_status_signal.emit()
        
class Measurement:
    def __init__(self, name, cal_type, unit, offset, index):
        self.name = name
        self.cal_type = cal_type
        self.value = 0
        self.values = {}
        self.unit = unit
        self.offset = offset
        self.index = index

class Setting:
    def __init__(self, name, value, cal_type, unit, default_value, offset, index):
        self.name = name
        self.cal_type = cal_type
        if value != None:
            self.value = value
        elif default_value != None:
            self.value = default_value
        else:
            self.value = 0
        self.choices = {}
        self.unit = unit
        self.offset = offset
        self.index = index

class Override:
    def __init__(self, name, cal_type, unit, offset, index):
        self.name = name
        self.cal_type = cal_type
        self.offset = offset
        self.status = "Passthrough"
        self.value = 0
        self.unit = unit
        self.index = index

class Device:
    def __init__(self, device_id, firmware_version, product_id, cal_revision, cal_protocol):
        self.device_id = device_id
        self.firmware_version = firmware_version
        self.product_id = product_id
        self.cal_revision = cal_revision
        self.cal_protocol = cal_protocol

        
