"""
YACPGUI.py
Yet Another Calibration Protocol (YACP)

This is the main calibration GUI for interfacing with YACP implementing firmware projects.

Matthew Bergman 2021

MIT license, all text above must be included in any redistribution.
See license.txt at the root of the repository for full license text.
"""

import can
import time
import sys
import csv
import json
import struct
import configparser
import os

from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QMenu
from PyQt5.QtWidgets import QBoxLayout
from PyQt5.QtWidgets import QGridLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QGroupBox
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QTableWidget
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtWidgets import QAbstractItemView
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtWidgets import QFrame
from PyQt5.QtWidgets import QInputDialog, QLineEdit, QFileDialog

from PyQt5.QtCore import Qt
from PyQt5.QtCore import QThread
from PyQt5.QtCore import QIODevice
from PyQt5.QtCore import QWaitCondition
from PyQt5.QtCore import QMutex
from PyQt5.QtCore import QByteArray
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QIcon

lengths = {}
lengths["uint8"] = 1
lengths["int8"] = 1
lengths["uint16"] = 2
lengths["int16"] = 2
lengths["uint32"] = 4
lengths["int32"] = 4
lengths["float"] = 4

SSCCP_COMMAND_ID = 0x100
SSCCP_UPDATE_ID = 0x101

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

class CANThread(QThread):
    update_measurement_signal = pyqtSignal(int,int,int,int,int,int)
    update_setting_signal = pyqtSignal(int,int,int,int,int,int)
    update_override_signal = pyqtSignal(bool,int,int,int,int,int,int)
    update_hello_signal = pyqtSignal(int)
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
                    if msg.arbitration_id == SSCCP_UPDATE_ID:
                        device_id = msg.data[0] >> 4
                        message_type = msg.data[0] & 0x0F
                        var_start = msg.data[1]
                        var_start |= msg.data[2] << 8
                        var_len = msg.data[3]

                        if message_type == CAL_HELLO:
                            self.update_hello_signal.emit(device_id)

                        if device_id != self.device_id:
                            continue

                        if message_type == CAL_READ_MEASUREMENT:               
                            self.update_measurement_signal.emit(var_start,var_len,msg.data[4],msg.data[5],msg.data[6],msg.data[7])
                        elif message_type == CAL_READ_SETTING:
                            self.update_setting_signal.emit(var_start,var_len,msg.data[4],msg.data[5],msg.data[6],msg.data[7])
                        elif message_type == CAL_OVERRIDE_ON:
                            self.update_override_signal.emit(True,var_start,var_len,msg.data[4],msg.data[5],msg.data[6],msg.data[7])
                        elif message_type == CAL_OVERRIDE_OFF:
                            self.update_override_signal.emit(False,var_start,var_len,msg.data[4],msg.data[5],msg.data[6],msg.data[7])

    @pyqtSlot(int)
    def setDeviceId(self, device_id):
        self.device_id = device_id

    @pyqtSlot(int,int,int,int,int,int)
    def setSetting(self, var_start, var_len, b0,b1,b2,b3):
        msg_data = [0,0,0,0,0,0,0,0]
        msg_id = SSCCP_COMMAND_ID

        msg_data[0] = (self.device_id << 4) | CAL_UPDATE_SETTING
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
        msg_id = SSCCP_COMMAND_ID

        if enabled == True:
            msg_data[0] = (self.device_id << 4) | CAL_OVERRIDE_ON
        else:
            msg_data[0] = (self.device_id << 4) | CAL_OVERRIDE_OFF
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
        msg_data = [CAL_HELLO,0,0,0,0,0,0,0]
        msg_id = SSCCP_COMMAND_ID

        msg = can.Message(arbitration_id=msg_id, is_extended_id=False, data=msg_data)
        if self.bus != None:
            try:
                self.bus.send(msg, 1)
            except:
                traceback.print_exc()

    @pyqtSlot()
    def sendSaveSettings(self):
        msg_data = [0,0,0,0,0,0,0,0]
        msg_id = SSCCP_COMMAND_ID

        msg_data[0] = (self.device_id << 4) | CAL_SAVE_SETTINGS

        self.sendCANMessage(msg_id, msg_data)

    @pyqtSlot(int,int)
    def readMeasurement(self, var_start, var_len):
        msg_data = [0,0,0,0,0,0,0,0]
        msg_id = SSCCP_COMMAND_ID

        msg_data[0] = (self.device_id << 4) | CAL_READ_MEASUREMENT
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
        msg_id = SSCCP_COMMAND_ID

        msg_data[0] = (self.device_id << 4) | CAL_READ_SETTING
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
        msg_id = SSCCP_COMMAND_ID

        msg_data[0] = (self.device_id << 4) | CAL_READ_OVERRIDE
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
    
class Measurement:
    def __init__(self, name, cal_type, offset, index):
        self.name = name
        self.cal_type = cal_type
        self.value = 0
        self.offset = offset
        self.index = index

class Setting:
    def __init__(self, name, value, cal_type, default_value, offset, index):
        self.name = name
        self.cal_type = cal_type
        if value != None:
            self.value = value
        elif default_value != None:
            self.value = default_value
        else:
            self.value = 0
        self.offset = offset
        self.index = index

class Override:
    def __init__(self, name, cal_type, offset, index):
        self.name = name
        self.cal_type = cal_type
        self.offset = offset
        self.status = "Passthrough"
        self.value = 0
        self.index = index

class Form(QMainWindow):
    set_setting_signal = pyqtSignal(int,int,int,int,int,int)
    set_override_signal = pyqtSignal(int,int,int,int,int,int,int)
    send_hello_signal = pyqtSignal()
    save_settings_signal = pyqtSignal()
    set_device_id_signal = pyqtSignal(int)
    read_measurement_signal = pyqtSignal(int,int)
    read_setting_signal = pyqtSignal(int,int)
    read_override_signal = pyqtSignal(int,int)
    
    def __init__(self):
        super().__init__()

        self.can_state = 0
        self.device_state = DEVICE_STATE_DISCONNECTED
        self.read_measurement_index = 0
        self.read_setting_index = 0
        self.read_override_index = 0
        self.device_id = -1
        self.projectPath = ""

        self.measurements = {}
        self.overrides = {}
        self.settings = {}
        
        self.num_measurements = 0
        self.num_settings = 0
        self.num_overrides = 0

        self.config = configparser.ConfigParser()
        self.recentDefFiles = {}
        self.recentCalFiles = {}
        self.readConfig()
	
        self.init_widget()

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

        self.show()

    def closeEvent(self, event):
        self.timer.stop()
        self.can_thread.disconnect()
        self.can_thread.stop = True
        self.saveConfig()
        self.can_thread.wait()

    def readConfig(self):
        inifile = self.config.read('yacp.ini')

        if len(inifile) == 0:
            self.config['YACP'] = {'CANAdaptor': 'PCAN', 'CANBAUD': '500'}
            self.config['RecentCals'] = {}
            self.config['RecentDefs'] = {}
            self.saveConfig()
            return

        for file, path in self.config.items("RecentDefs"):
            self.recentDefFiles[file] = path

        for file, path in self.config.items("RecentCals"):
            self.recentCalFiles[file] = path

        # TODO: load CAN settigns

    def saveConfig(self):
        with open('yacp.ini', 'w') as configfile:
            self.config.write(configfile)
            configfile.close()
        
    def init_widget(self):
        self.setWindowTitle("YACP Cal")
        self.statusBar().showMessage('Disconnected')


        menubar = self.menuBar()
        
        fileMenu = menubar.addMenu('&File')
        recentDefMenu = QMenu('Recent Defs...', self)
        self.recentCalMenu = QMenu('Recent Cals...', self)
        self.recentCalMenu.setEnabled(False)

        self.defOpenAct = QAction(QIcon('open.png'), '&Open Def', self)
        self.defOpenAct.setShortcut('Ctrl+D')
        self.defOpenAct.setStatusTip('Open Def file')
        self.defOpenAct.triggered.connect(self.loadDefFileDialog)

        self.calOpenAct = QAction(QIcon('open.png'), '&Open Cal', self)
        self.calOpenAct.setShortcut('Ctrl+C')
        self.calOpenAct.setStatusTip('Open Cal file')
        self.calOpenAct.triggered.connect(self.loadCalFileDialog)
        self.calOpenAct.setEnabled(False)


        for calFile in self.recentCalFiles.keys():
            recentOpenAct = QAction(calFile, self)
            recentOpenAct.triggered.connect(lambda: self.loadCalFile(self.recentCalFiles[calFile]))
            self.recentCalMenu.addAction(recentOpenAct)

        for defFile in self.recentDefFiles.keys():
            recentOpenAct = QAction(defFile, self)
            recentOpenAct.triggered.connect(lambda: self.loadDefFile(self.recentDefFiles[defFile]))
            recentDefMenu.addAction(recentOpenAct)
        

        fileMenu.addAction(self.defOpenAct)
        fileMenu.addAction(self.calOpenAct)
        fileMenu.addMenu(recentDefMenu)
        fileMenu.addMenu(self.recentCalMenu)
        
        
        
        
        
        form_lbx = QBoxLayout(QBoxLayout.LeftToRight, parent=self)
        main_frame = QFrame(self)
        main_frame.setLayout(form_lbx)
        self.setCentralWidget(main_frame)


        # CAN controls

        grid_frame = QFrame(self) 
        grid_frame.setFrameShape(QFrame.StyledPanel)
        grid_frame.setFrameShadow(QFrame.Raised)
        grid = QGridLayout(grid_frame)

        form_lbx.addWidget(grid_frame)

        self.combo_bustype = QComboBox()
        self.combo_bustype.addItem("PCAN")
        self.combo_bustype.addItem("KVaser")     

        self.combo_rate = QComboBox()
        self.combo_rate.addItem("500k")
        self.combo_rate.addItem("250k")
        self.combo_rate.addItem("1M")
        self.combo_rate.addItem("125k")

        self.btn_connect = QPushButton("Open")
        self.btn_connect.clicked.connect(self.connect)

        self.btn_hello = QPushButton("Scan for targets")
        self.btn_hello.clicked.connect(self.sendHello)
        self.btn_hello.setEnabled(False)

        self.combo_devices = QComboBox()

        self.btn_device_connect = QPushButton("Connect")
        self.btn_device_connect.clicked.connect(self.deviceConnect)
        self.btn_device_connect.setEnabled(False)

        self.btn_save = QPushButton("Push and Save Cal")
        self.btn_save.clicked.connect(self.saveSettings)
        self.btn_save.setEnabled(False)

        row = 0
        grid.addWidget(self.combo_bustype, row, 0)
        grid.addWidget(self.combo_rate, row, 1)
        grid.addWidget(self.btn_connect, row, 2)
        row += 1
        
        grid.addWidget(self.btn_hello, row, 0)
        grid.addWidget(self.combo_devices, row, 1)
        grid.addWidget(self.btn_device_connect, row, 2)
        row += 1

        grid.addWidget(self.btn_save, row, 0)
        row += 1


        # Measurements / Settings / Overrides

        self.measurements_table = QTableWidget(0, 3)
        self.measurements_table.verticalHeader().hide()
        self.measurements_table.setHorizontalHeaderItem(0, QTableWidgetItem("Measurement"))
        self.measurements_table.setHorizontalHeaderItem(1, QTableWidgetItem("Value"))
        self.measurements_table.setHorizontalHeaderItem(2, QTableWidgetItem("Type"))
        form_lbx.addWidget(self.measurements_table)


        self.settings_table = QTableWidget(0, 3)
        self.settings_table.verticalHeader().hide()
        self.settings_table.setHorizontalHeaderItem(0, QTableWidgetItem("Setting"))
        self.settings_table.setHorizontalHeaderItem(1, QTableWidgetItem("Value"))
        self.settings_table.setHorizontalHeaderItem(2, QTableWidgetItem("Type"))
        self.settings_table.cellChanged.connect(self.on_setting_change)
        form_lbx.addWidget(self.settings_table)

        self.overrides_table = QTableWidget(0, 4)
        self.overrides_table.verticalHeader().hide()
        self.overrides_table.setHorizontalHeaderItem(0, QTableWidgetItem("Override"))
        self.overrides_table.setHorizontalHeaderItem(1, QTableWidgetItem("Status"))
        self.overrides_table.setHorizontalHeaderItem(2, QTableWidgetItem("Value"))
        self.overrides_table.setHorizontalHeaderItem(3, QTableWidgetItem("Type"))
        self.overrides_table.cellChanged.connect(self.on_override_change)
        form_lbx.addWidget(self.overrides_table)
        
    def update_widgets(self):
        self.measurements_table.setRowCount(self.num_measurements)
        self.settings_table.setRowCount(self.num_settings)
        self.overrides_table.setRowCount(self.num_overrides)
        
        row = 0
        for offset in self.measurements:
            measurement = self.measurements[offset]

            item = QTableWidgetItem(measurement.name)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.measurements_table.setItem(row, 0, item)

            item = QTableWidgetItem(str(measurement.value))
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.measurements_table.setItem(row, 1, item)

            item = QTableWidgetItem(str(measurement.cal_type))
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.measurements_table.setItem(row, 2, item)
            row += 1

        row = 0
        self.settings_table.cellChanged.disconnect()
        for offset in self.settings:
            setting = self.settings[offset]

            item = QTableWidgetItem(setting.name)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.settings_table.setItem(row, 0, item)
            
            self.settings_table.setItem(row, 1, QTableWidgetItem(str(setting.value)))

            item = QTableWidgetItem(setting.cal_type)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.settings_table.setItem(row, 2, item)
            row += 1
        self.settings_table.cellChanged.connect(self.on_setting_change)

        row = 0
        self.overrides_table.cellChanged.disconnect()
        for offset in self.overrides:
            override = self.overrides[offset]

            item = QTableWidgetItem(override.name)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.overrides_table.setItem(row, 0, item)

            combobox = QComboBox()
            combobox.addItem("Passthrough")
            combobox.addItem("Overridden")
            combobox.setProperty('row', row)
            combobox.currentIndexChanged.connect(self.on_override_status_change)
            
            item = QTableWidgetItem()
            self.overrides_table.setItem(row, 1, item)
            self.overrides_table.setCellWidget(row, 1, combobox)
            
            self.overrides_table.setItem(row, 2, QTableWidgetItem(str(override.value)))

            item = QTableWidgetItem(override.cal_type)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.overrides_table.setItem(row, 3, item)
            row += 1
        self.overrides_table.cellChanged.connect(self.on_override_change)

    def on_setting_change(self, table_index, column):
        if column != 1 or table_index == None:
            return

        setting_key = [*self.settings][table_index]
        setting = self.settings[setting_key]

        if setting.cal_type == 'float':
            setting.value = float(self.settings_table.item(table_index, column).text())
        else:
            setting.value = int(self.settings_table.item(table_index, column).text())

        [b0,b1,b2,b3] = self.getBytesFromValue(setting.cal_type, setting.value)

        self.set_setting_signal.emit(setting.offset, lengths[setting.cal_type], b0,b1,b2,b3)

    def on_override_change(self, table_index, column):
        if column != 2 or table_index == None:
            return

        override_key = [*self.overrides][table_index]
        override = self.overrides[override_key]
        
        if override.cal_type == 'float':
            override.value = float(self.overrides_table.item(table_index, 2).text())
        else:
            override.value = int(self.overrides_table.item(table_index, 2).text())

        override.status = self.overrides_table.cellWidget(table_index, 1).currentText()
        enabled = False
        if override.status == "Overridden":
            enabled = True

        [b0,b1,b2,b3] = self.getBytesFromValue(override.cal_type, override.value)

        #print(str(enabled)+" "+str(b0)+" "+str(b1)+" "+str(b2)+" "+str(b3)+" "+str(override.value))

        self.set_override_signal.emit(enabled, override.offset, lengths[override.cal_type], b0,b1,b2,b3)

    def on_override_status_change(self):
        combo = self.sender()
        table_index = combo.property('row')
        self.on_override_change(table_index, 2)

    def loadDefFileDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"Open build def", self.projectPath,"Def Files (*.json)", options=options)
        if fileName:
            self.loadDefFile(fileName)

    def loadDefFile(self, fileName):
        with open(fileName, newline='\n') as def_file:
            defs = json.load(def_file)

            measurement_offset = 0
            override_offset = 0
            setting_offset = 0

            for m in defs["measurements"]:
                measurement = Measurement(m["name"], m["type"], measurement_offset, self.num_measurements)
                self.measurements[measurement_offset] = measurement
                measurement_offset += lengths[m["type"]]
                self.num_measurements += 1
                
            for s in defs["settings"]:
                setting = Setting(s["name"], 0, s["type"], s["default"], setting_offset, self.num_settings)
                self.settings[setting_offset] = setting
                setting_offset += lengths[s["type"]]
                self.num_settings += 1

            for o in defs["overrides"]:
                override = Override(o["name"], o["type"], override_offset, self.num_overrides)
                self.overrides[override_offset] = override
                override_offset += 5
                self.num_overrides += 1

            self.btn_hello.setEnabled(True)
            self.calOpenAct.setEnabled(True)
            self.recentCalMenu.setEnabled(True)
            
            self.config["RecentDefs"][os.path.basename(fileName)] = fileName
            self.recentDefFiles[os.path.basename(fileName)] = fileName
            self.projectPath = os.path.split(fileName)[0]
                      
            self.update_widgets()

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

    @pyqtSlot(int,int,int,int,int,int)
    def updateMeasurement(self, var_start, var_len, b0,b1,b2,b3):
        table_index = self.measurements[var_start].index
        cal_type = self.measurements[var_start].cal_type
        value = self.getValueFromBytes(cal_type,b0,b1,b2,b3)        
        self.measurements_table.item(table_index, 1).setText(str(value))

    @pyqtSlot(int,int,int,int,int,int)
    def updateSetting(self, var_start, var_len, b0,b1,b2,b3):
        table_index = self.settings[var_start].index
        cal_type = self.settings[var_start].cal_type
        value = self.getValueFromBytes(cal_type,b0,b1,b2,b3) 
        self.settings_table.item(table_index, 1).setText(str(value))

    @pyqtSlot(bool,int,int,int,int,int,int)
    def updateOverride(self, overridden, var_start, var_len, b0,b1,b2,b3):
        table_index = self.overrides[var_start].index
        cal_type = self.overrides[var_start].cal_type
        value = self.getValueFromBytes(cal_type,b0,b1,b2,b3)
        
        self.overrides_table.item(table_index, 2).setText(str(value))
        if overridden:
            self.overrides_table.cellWidget(table_index, 1).setCurrentText("Overridden")
        else:
            self.overrides_table.cellWidget(table_index, 1).setCurrentText("Passthrough")
        
    @pyqtSlot(int)
    def updateDeviceList(self, device_id):
        self.combo_devices.addItem(str(device_id))
        self.btn_device_connect.setEnabled(True)

    def sendHello(self):
        self.combo_devices.clear()
        self.send_hello_signal.emit()

    def deviceConnect(self):
        device_id = int(self.combo_devices.currentText())
        if device_id != None and device_id != "":
            self.device_id = device_id
            self.set_device_id_signal.emit(device_id)

            self.read_measurement_index = 0
            self.read_setting_index = 0
            self.read_override_index = 0
            self.device_state = DEVICE_STATE_READING_SETTINGS

            self.btn_save.setEnabled(True)

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

    def saveSettings(self):
        self.save_settings_signal.emit()
        self.exportSettingsCSV()

    def exportSettingsCSV(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getSaveFileName(self,"Save Cal File",self.projectPath,"Cal Files (*.csv)", options=options)
        if fileName:
            with open(fileName, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter=',',quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(['Name','Value'])

                for i in range(0, self.num_settings):
                    setting_key = [*self.settings][i]
                    setting = self.settings[setting_key]
                    writer.writerow([setting.name,setting.value])

                self.statusBar().showMessage("Cal saved to "+fileName)

    def loadCalFileDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"Open Cal File",self.projectPath,"Cal Files (*.csv)", options=options)
        if fileName:
            self.loadCalFile(fileName)

    def loadCalFile(self, fileName):
        with open(fileName, newline='\n') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in reader:
                name = row[0]
                str_val = row[1]

                for offset in self.settings:
                    if self.settings[offset].name != name:
                        continue

                    if self.settings[offset].cal_type == "float":
                        self.settings[offset].value = float(str_val)
                    else:
                        self.settings[offset].value = int(str_val)
                    table_index = self.settings[offset].index
                    self.settings_table.item(table_index, 1).setText(str_val)

            self.config["RecentCals"][os.path.basename(fileName)] = fileName
            self.recentCalFiles[os.path.basename(fileName)] = fileName
            self.projectPath = os.path.split(fileName)[0]


    def tick(self):
        if self.device_state == DEVICE_STATE_DISCONNECTED:
            pass
        
        elif self.device_state == DEVICE_STATE_READING_SETTINGS:
            self.statusBar().showMessage("Reading setting "+str(self.read_setting_index+1)+"/"+str(self.num_settings))        
            self.readSetting()

            self.read_setting_index += 1
            if self.read_setting_index >= self.num_settings:
                self.device_state = DEVICE_STATE_READING_OVERRIDES
                self.read_setting_index = 0
                
        elif self.device_state == DEVICE_STATE_READING_OVERRIDES:
            self.statusBar().showMessage("Reading override "+str(self.read_override_index+1)+"/"+str(self.num_overrides))
            
            self.readOverride()

            self.read_override_index += 1
            if self.read_override_index >= self.num_overrides:
                self.device_state = DEVICE_STATE_READING_MEASUREMENTS
                self.read_overrides_index = 0
        
        elif self.device_state == DEVICE_STATE_READING_MEASUREMENTS:
            self.statusBar().showMessage("Reading measurement "+str(self.read_measurement_index+1)+"/"+str(self.num_measurements))
            
            self.readMeasurement()

            self.read_measurement_index += 1
            if self.read_measurement_index >= self.num_measurements:
                self.device_state = DEVICE_STATE_CONNECTED
                self.statusBar().showMessage("Connected to device ID "+str(self.device_id))
                self.read_measurement_index = 0
            
        elif self.device_state == DEVICE_STATE_CONNECTED:
            self.readMeasurement()
            self.read_measurement_index += 1
            if self.read_measurement_index >= self.num_measurements:
                self.read_measurement_index = 0

    def connect(self):
        bustype = self.combo_bustype.currentText()
        bitrate = self.combo_rate.currentText()

        if bustype == 'PCAN':
            bustype = 'pcan'
            interface = 'PCAN_USBBUS1'
        elif bustype == 'KVaser':
            bustype = 'kvaser'
            interface = '0'

        if bitrate == "125k":
            bitrate = 125000
        elif bitrate == "250k":
            bitrate = 250000
        elif bitrate == "500k":
            bitrate = 500000
        elif bitrate == "1M":
            bitrate = 1000000

        if self.can_state == 0:
            self.statusBar().showMessage("Connecting...")
            self.can_thread.connect(bustype, interface, bitrate)
        elif self.can_state == 1:
            self.statusBar().showMessage("Disconnecting...")
            self.can_thread.disconnect()

    @pyqtSlot(int)
    def handleCANStatus(self, status):
        if status == 1:
            self.statusBar().showMessage("Failed to find CAN device")
            self.can_state = 0

            self.btn_hello.setEnabled(False)
            self.btn_device_connect.setEnabled(False)
            self.btn_save.setEnabled(False)
        if status == 0:
            self.statusBar().showMessage("CAN device connected")
            self.btn_connect.setText("Disconnect")
            self.can_state = 1

            self.combo_rate.setEnabled(False)
            self.combo_bustype.setEnabled(False)
        if status == 2:
            self.statusBar().showMessage("CAN device disconnected")
            self.btn_connect.setText("Connect")
            self.can_state = 0
            
            self.combo_rate.setEnabled(True)
            self.combo_bustype.setEnabled(True)
            
            self.btn_hello.setEnabled(False)
            self.btn_device_connect.setEnabled(False)
            self.btn_save.setEnabled(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    excepthook = sys.excepthook
    sys.excepthook = lambda t, val, tb: excepthook(t, val, tb)
    form = Form()
    form.setGeometry(100, 100, 1900, 500)
    form.show()
    exit(app.exec_())
