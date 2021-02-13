import can
import time
import sys
import csv

from PyQt5.QtWidgets import QWidget
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

lengths = {}
lengths["uint8"] = 1
lengths["int8"] = 1
lengths["uint16"] = 2
lengths["int16"] = 2
lengths["uint32"] = 2
lengths["int32"] = 2
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

class CANThread(QThread):
    update_measurement_signal = pyqtSignal(int,int,int)
    send_status_signal = pyqtSignal(int)
    
    def __init__(self):
        self.bus = None
        
        QThread.__init__(self)

    def connect(self, _type, _channel, _bitrate):
        try:
            self.bus = can.interface.Bus(bustype=_type, channel=_channel, bitrate=_bitrate)
            print("Connected to CAN device")
            self.send_status_signal.emit(0)
        except:
            self.bus = None
            print("Failed to find CAN device")
            traceback.print_exc()
            self.send_status_signal.emit(1)

    def disconnect(self):
        try:
            self.bus.shutdown()
            self.send_status_signal.emit(2)
        except:
            print("Failed to shut down bus")
        self.bus = None

    # run method gets called when we start the thread
    def run(self):
        while True:
            if self.bus != None:
                for msg in self.bus:
                    print(hex(msg.arbitration_id))
                    if msg.arbitration_id == SSCCP_UPDATE_ID:
                        device_id = msg.data[0] >> 4
                        message_type = msg.data[0] & 0x0F
                        var_start = msg.data[1]
                        var_start |= msg.data[2] << 8
                        var_len = msg.data[3]
                        value = msg.data[4]
                        value |= msg.data[5] << 8
                        value |= msg.data[6] << 16
                        value |= msg.data[7] << 24

                        #CAL_READ_SETTING
                        #CAL_READ_OVERRIDE
                        #CAL_READ_MEASUREMENT

                        print("UPDATE from: "+str(device_id)+" type: "+str(message_type)+" start: "+str(var_start)+" len: "+str(var_len)+" value: "+str(value)) 

                        if message_type == CAL_READ_MEASUREMENT:               
                            self.update_measurement_signal.emit(var_start,var_len,value)
                            continue


    @pyqtSlot(int,int,int,int)
    def setSetting(self, device_id, var_start, var_len, value):
        msg_data = [0,0,0,0,0,0,0,0]
        msg_id = SSCCP_COMMAND_ID

        msg_data[0] = (device_id << 4) | CAL_UPDATE_SETTING
        msg_data[1] = var_start & 0x0F
        msg_data[2] = var_start >> 8
        msg_data[3] = var_len
        msg_data[4] = value & 0x0F
        msg_data[5] = (value >> 8) & 0x0F
        msg_data[6] = (value >> 16) & 0x0F
        msg_data[7] = (value >> 24) & 0x0F

        msg = can.Message(arbitration_id=msg_id, is_extended_id=False, data=msg_data)
        if self.bus != None:
            try:
                self.bus.send(msg, 1)
            except:
                print("Failed to send CAN message")

    @pyqtSlot(int,int,int,int)
    def setOverride(self, enabled, device_id, var_start, value):
        msg_data = [0,0,0,0,0,0,0,0]
        msg_id = SSCCP_COMMAND_ID

        if enabled == True:
            msg_data[0] = (device_id << 4) | CAL_OVERRIDE_ON
        else:
            msg_data[0] = (device_id << 4) | CAL_OVERRIDE_OFF
        msg_data[1] = var_start & 0x0F
        msg_data[2] = var_start >> 8
        msg_data[3] = 4
        msg_data[4] = value & 0x0F
        msg_data[5] = (value >> 8) & 0x0F
        msg_data[6] = (value >> 16) & 0x0F
        msg_data[7] = (value >> 24) & 0x0F

        msg = can.Message(arbitration_id=msg_id, is_extended_id=False, data=msg_data)
        if self.bus != None:
            try:
                self.bus.send(msg, 1)
            except:
                print("Failed to send CAN message")

    @pyqtSlot()
    def sendHello(self):
        msg_data = [CAL_HELLO,0,0,0,0,0,0,0]
        msg_id = SSCCP_COMMAND_ID

        msg = can.Message(arbitration_id=msg_id, is_extended_id=False, data=msg_data)
        if self.bus != None:
            try:
                self.bus.send(msg, 1)
            except:
                print("Failed to send CAN message")

    @pyqtSlot(int,int,int)
    def readMeasurement(self, device_id, var_start, var_len):
        msg_data = [0,0,0,0,0,0,0,0]
        msg_id = SSCCP_COMMAND_ID

        msg_data[0] = (device_id << 4) | CAL_READ_MEASUREMENT
        msg_data[1] = var_start & 0x0F
        msg_data[2] = var_start >> 8
        msg_data[3] = var_len
        msg_data[4] = 0
        msg_data[5] = 0
        msg_data[6] = 0
        msg_data[7] = 0

        msg = can.Message(arbitration_id=msg_id, is_extended_id=False, data=msg_data)
        if self.bus != None:
            try:
                self.bus.send(msg, 1)
            except:
                print("Failed to send CAN message")
    

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

class Form(QWidget):
    set_setting_signal = pyqtSignal(int,int,int,int)
    set_override_signal = pyqtSignal(int,int,int,int)
    send_hello_signal = pyqtSignal()
    read_measurement_signal = pyqtSignal(int,int,int)

    device_id = 1 # TODO: from dropdown
    
    def __init__(self):
        QWidget.__init__(self, flags=Qt.Widget)

        self.state = 0
        self.read_measurement_index = 0

        self.measurements = {}
        self.overrides = {}
        self.settings = {}
        
        self.num_measurements = 0
        self.num_settings = 0
        self.num_overrides = 0
	
        self.init_widget()

        self.can_thread = CANThread()
        
        self.can_thread.update_measurement_signal.connect(self.updateMeasurement)
        self.can_thread.send_status_signal.connect(self.handleCANStatus)
        
        self.set_setting_signal.connect(self.can_thread.setSetting)
        self.set_override_signal.connect(self.can_thread.setOverride)
        self.send_hello_signal.connect(self.can_thread.sendHello)
        self.read_measurement_signal.connect(self.can_thread.readMeasurement)

        self.can_thread.start()
        
    def init_widget(self):
        self.setWindowTitle("VSCCP GUI")
        form_lbx = QBoxLayout(QBoxLayout.LeftToRight, parent=self)
        self.setLayout(form_lbx)


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

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.clicked.connect(self.connect)

        self.btn_hello = QPushButton("Scan for targets")
        self.btn_hello.clicked.connect(self.sendHello)

        self.btn_open = QPushButton("Open Cal CSV")
        self.btn_open.clicked.connect(self.openFileNameDialog)

        self.btn_read_measurement = QPushButton("Read Measurement")
        self.btn_read_measurement.clicked.connect(self.readMeasurement)
        
        self.lbl_status = QLabel("")

        row = 0
        grid.addWidget(self.combo_bustype, row, 0)
        grid.addWidget(self.combo_rate, row, 1)
        grid.addWidget(self.btn_connect, row, 2)
        row += 1
        
        grid.addWidget(self.lbl_status, row, 0)
        row += 1

        grid.addWidget(self.btn_open, row, 0)
        grid.addWidget(self.btn_hello, row, 1)
        grid.addWidget(self.btn_read_measurement, row, 2)
        row += 1


        # Measurements / Settings / Overrides

        self.measurements_table = QTableWidget(0, 2)
        self.measurements_table.verticalHeader().hide()
        self.measurements_table.setHorizontalHeaderItem(0, QTableWidgetItem("Measurement"))
        self.measurements_table.setHorizontalHeaderItem(1, QTableWidgetItem("Value"))
        form_lbx.addWidget(self.measurements_table)


        self.settings_table = QTableWidget(0, 2)
        self.settings_table.verticalHeader().hide()
        self.settings_table.setHorizontalHeaderItem(0, QTableWidgetItem("Setting"))
        self.settings_table.setHorizontalHeaderItem(1, QTableWidgetItem("Value"))
        self.settings_table.cellChanged.connect(self.on_setting_change)
        form_lbx.addWidget(self.settings_table)

        self.overrides_table = QTableWidget(0, 3)
        self.overrides_table.verticalHeader().hide()
        self.overrides_table.setHorizontalHeaderItem(0, QTableWidgetItem("Override"))
        self.overrides_table.setHorizontalHeaderItem(1, QTableWidgetItem("Status"))
        self.overrides_table.setHorizontalHeaderItem(2, QTableWidgetItem("Value"))
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
            row += 1

        row = 0
        self.settings_table.cellChanged.disconnect()
        for offset in self.settings:
            setting = self.settings[offset]

            item = QTableWidgetItem(setting.name)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.settings_table.setItem(row, 0, item)
            
            self.settings_table.setItem(row, 1, QTableWidgetItem(str(setting.value)))
            row += 1
        self.settings_table.cellChanged.connect(self.on_setting_change)

        row = 0
        for offset in self.overrides:
            override = self.overrides[offset]

            item = QTableWidgetItem(override.name)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.overrides_table.setItem(row, 0, item)

            combobox = QComboBox()
            combobox.addItem("Passthrough")
            combobox.addItem("Override")
            item = QTableWidgetItem()
            self.overrides_table.setItem(row, 1, item)
            self.overrides_table.setCellWidget(row, 1, combobox)
            
            self.overrides_table.setItem(row, 2, QTableWidgetItem(str(override.value)))
            row += 1

    def on_setting_change(self, table_index, column):
        if column != 1:
            return

        setting_key = [*self.settings][table_index]
        setting = self.settings[setting_key]

        setting.value = int(self.settings_table.item(table_index, column).text())
        print("Set "+str(table_index)+" to "+str(setting.value))

        self.set_setting_signal.emit(self.device_id, setting.offset, lengths[setting.cal_type], setting.value)
        

    def openFileNameDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"Open Cal CSV", "","Cal Files (*.csv)", options=options)
        if fileName:
            with open(fileName, newline='\n') as csvfile:
                reader = csv.reader(csvfile, delimiter=',', quotechar='"')
                measurement_offset = 0
                override_offset = 0
                setting_offset = 0
                
                for row in reader:                
                    role = row[0]
                    name = row[1]
                    cal_type = row[2]
                    default_value = row[3]
                    value = row[4]

                    if role.strip().lower() == 'measurement':
                        measurement = Measurement(name, cal_type, measurement_offset, self.num_measurements)
                        self.measurements[measurement_offset] = measurement
                        measurement_offset += lengths[cal_type]
                        self.num_measurements += 1
                    elif role.strip().lower() == 'setting':
                        setting = Setting(name, value, cal_type, default_value, setting_offset, self.num_settings)
                        self.settings[setting_offset] = setting
                        setting_offset += lengths[cal_type]
                        self.num_settings += 1
                    elif role.strip().lower() == 'override':
                        override = Override(name, cal_type, override_offset, self.num_overrides)
                        self.overrides[override_offset] = override
                        override_offset += lengths[cal_type]
                        self.num_overrides += 1
            self.update_widgets()

    @pyqtSlot(int,int,int)
    def updateMeasurement(self, var_start, var_len, value):
        table_index = self.measurements[var_start].index
        self.measurements_table.item(table_index, 1).setText(str(value))
        print("Set measurement "+str(var_start)+" to "+str(value))

    def sendHello(self):
        self.send_hello_signal.emit()

    def readMeasurement(self):
        measurement_key = [*self.measurements][self.read_measurement_index]
        measurement = self.measurements[measurement_key]
        
        var_start = measurement.offset
        var_len = lengths[measurement.cal_type]
        
        self.read_measurement_signal.emit(self.device_id, var_start, var_len)

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

        if self.state == 0:
            self.lbl_status.setText("Connecting...")
            self.can_thread.connect(bustype, interface, bitrate)
        elif self.state == 1:
            self.lbl_status.setText("Disconnecting...")
            self.can_thread.disconnect()

    @pyqtSlot(int)
    def handleCANStatus(self, status):
        if status == 1:
            self.lbl_status.setText("Failed to find CAN device")
            self.state = 0
        if status == 0:
            self.lbl_status.setText("CAN device connected")
            self.btn_connect.setText("Disconnect")
            self.state = 1

            self.combo_rate.setEnabled(False)
            self.combo_bustype.setEnabled(False)
        if status == 2:
            self.lbl_status.setText("CAN device disconnected")
            self.btn_connect.setText("Connect")
            self.state = 0
            
            self.combo_rate.setEnabled(True)
            self.combo_bustype.setEnabled(True)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    excepthook = sys.excepthook
    sys.excepthook = lambda t, val, tb: excepthook(t, val, tb)
    form = Form()
    form.setGeometry(100, 100, 1800, 500)
    form.show()
    exit(app.exec_())
