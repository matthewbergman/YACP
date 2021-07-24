"""
YACPGUI.py
Yet Another Calibration Protocol (YACP)

This is the main calibration GUI for interfacing with YACP implementing firmware projects.

Matthew Bergman 2021

MIT license, all text above must be included in any redistribution.
See license.txt at the root of the repository for full license text.
"""

import time
import sys
import configparser
import os
import traceback

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
from PyQt5.QtWidgets import QAction, QMenu

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
from PyQt5.QtGui import QCursor

from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg

from version import VERSION

from yacp import YACPProtocol, CANThread, Measurement, Setting, Override, Device

class YACPcal(QMainWindow):
        
    def __init__(self):
        super().__init__()
        
        self.projectPath = ""

        self.config = configparser.ConfigParser()
        self.recentDefFiles = {}
        self.recentCalFiles = {}
        
        self.graph_row = -1
        self.graph_x = list(x*10 for x in range(-100,0,1))
        self.graph_y = list(0 for _ in range(100))
        
        self.readConfig()
	
        self.init_widget()

        self.yacp = YACPProtocol()
        
        self.yacp.app_update_device_state_signal.connect(self.updateDeviceState)
        self.yacp.app_update_measurement_signal.connect(self.updateMeasurement)
        self.yacp.app_update_setting_signal.connect(self.updateSetting)
        self.yacp.app_update_override_signal.connect(self.updateOverride)
        self.yacp.app_update_devices_signal.connect(self.updateDeviceList)
        self.yacp.app_update_can_status_signal.connect(self.updateCANStatus)

        self.show()

    def closeEvent(self, event):
        self.saveConfig()
        self.yacp.close()

    def readConfig(self):
        inifile = self.config.read('yacp.ini')

        if len(inifile) == 0:
            self.config['YACP'] = {'CANAdaptor': 'PCAN', 'CANBAUD': '500'}
            self.config['RecentCals'] = {}
            self.config['RecentDefs'] = {}
            self.saveConfig()
            return

        for file, path in self.config.items("RecentDefs"):
            if not os.path.exists(path):
                self.config.remove_option("RecentDefs", file)
            else:
                self.recentDefFiles[file] = path

        for file, path in self.config.items("RecentCals"):
            if not os.path.exists(path):
                self.config.remove_option("RecentCals", file)
            else:
                self.recentCalFiles[file] = path

        # TODO: load CAN settigns

    def saveConfig(self):
        with open('yacp.ini', 'w') as configfile:
            self.config.write(configfile)
            configfile.close()
        
    def init_widget(self):
        self.setWindowTitle("YACPcal "+VERSION)
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
            recentOpenAct.triggered.connect(lambda c=calFile,f=calFile: self.loadCalFile(self.recentCalFiles[f]))
            self.recentCalMenu.addAction(recentOpenAct)

        for defFile in self.recentDefFiles.keys():
            recentOpenAct = QAction(defFile, self)
            recentOpenAct.triggered.connect(lambda c=defFile,f=defFile: self.loadDefFile(self.recentDefFiles[f])) # var c is used to handle the triggered first arg
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

        self.btn_save = QPushButton("Persist and Save Cal")
        self.btn_save.clicked.connect(self.saveSettings)
        self.btn_save.setEnabled(False)

        
        pen = pg.mkPen(color=(255, 0, 0))
        self.graph = pg.PlotWidget()
        self.graph.setBackground('default')
        self.graph.showGrid(x=True, y=True)
        self.graph.setLabel('left', 'Measurement')
        self.graph.setLabel('bottom', 'Ticks')
        self.graph_line = self.graph.plot(self.graph_x, self.graph_y, pen=pen)

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

        grid.addWidget(self.graph, row, 0, 1, 3)
        row += 1


        # Measurements / Settings / Overrides

        self.measurements_table = QTableWidget(0, 4)
        self.measurements_table.verticalHeader().hide()
        self.measurements_table.setHorizontalHeaderItem(0, QTableWidgetItem("Measurement"))
        self.measurements_table.setHorizontalHeaderItem(1, QTableWidgetItem("Value"))
        self.measurements_table.setHorizontalHeaderItem(2, QTableWidgetItem("Type"))
        self.measurements_table.setHorizontalHeaderItem(3, QTableWidgetItem("Unit"))
        self.measurements_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.measurements_table.customContextMenuRequested.connect(self.handleContextMenu)
        form_lbx.addWidget(self.measurements_table)

        self.settings_table = QTableWidget(0, 5)
        self.settings_table.verticalHeader().hide()
        self.settings_table.setHorizontalHeaderItem(0, QTableWidgetItem("Setting"))
        self.settings_table.setHorizontalHeaderItem(1, QTableWidgetItem("Value"))
        self.settings_table.setHorizontalHeaderItem(2, QTableWidgetItem("Type"))
        self.settings_table.setHorizontalHeaderItem(3, QTableWidgetItem("Unit"))
        self.settings_table.setHorizontalHeaderItem(4, QTableWidgetItem("Default"))
        self.settings_table.cellChanged.connect(self.on_setting_change)
        form_lbx.addWidget(self.settings_table)

        self.overrides_table = QTableWidget(0, 5)
        self.overrides_table.verticalHeader().hide()
        self.overrides_table.setHorizontalHeaderItem(0, QTableWidgetItem("Override"))
        self.overrides_table.setHorizontalHeaderItem(1, QTableWidgetItem("Status"))
        self.overrides_table.setHorizontalHeaderItem(2, QTableWidgetItem("Value"))
        self.overrides_table.setHorizontalHeaderItem(3, QTableWidgetItem("Type"))
        self.overrides_table.setHorizontalHeaderItem(4, QTableWidgetItem("Unit"))
        self.overrides_table.cellChanged.connect(self.on_override_change)
        form_lbx.addWidget(self.overrides_table)

    def handleContextMenu(self, event):
        row = self.measurements_table.rowAt(event.y())
        col = self.measurements_table.columnAt(event.x())
        cell = self.measurements_table.item(row, col)
        if cell == None:
            return
        
        menu = QMenu()
        graph_action = QAction('Graph')
        graph_action.setProperty('measurements_table_row', row)
        menu.addAction(graph_action)
        menu.triggered[QAction].connect(self.contextMenuClicked)
        menu.exec_(QCursor.pos())

    def contextMenuClicked(self, item):
        if item.text() == 'Graph':
            self.graph_row = item.property('measurements_table_row')
        
    def update_widgets(self):
        self.measurements_table.setRowCount(self.yacp.num_measurements)
        self.settings_table.setRowCount(self.yacp.num_settings)
        self.overrides_table.setRowCount(self.yacp.num_overrides)
        
        row = 0
        for offset in self.yacp.measurements:
            measurement = self.yacp.measurements[offset]

            item = QTableWidgetItem(measurement.name)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.measurements_table.setItem(row, 0, item)

            val = str(measurement.value)
            for value in measurement.values.keys():
                if val == value:
                    val = measurement.values[value]
                    break

            item = QTableWidgetItem(val)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.measurements_table.setItem(row, 1, item)

            item = QTableWidgetItem(str(measurement.cal_type))
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.measurements_table.setItem(row, 2, item)

            item = QTableWidgetItem(str(measurement.unit))
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.measurements_table.setItem(row, 3, item)
            row += 1

        row = 0
        self.settings_table.cellChanged.disconnect()
        for offset in self.yacp.settings:
            setting = self.yacp.settings[offset]

            item = QTableWidgetItem(setting.name)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.settings_table.setItem(row, 0, item)

            if len(setting.choices) == 0:
                self.settings_table.setItem(row, 1, QTableWidgetItem(str(setting.value)))
            else:
                combobox = QComboBox()
                for choice_value in setting.choices.keys():
                    combobox.addItem(setting.choices[choice_value], choice_value)
                combobox.setProperty('row', row)
                combobox.currentIndexChanged.connect(self.on_setting_combobox_change)
                item = QTableWidgetItem()
                self.settings_table.setItem(row, 1, item)
                self.settings_table.setCellWidget(row, 1, combobox)

            item = QTableWidgetItem(setting.cal_type)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.settings_table.setItem(row, 2, item)

            item = QTableWidgetItem(setting.unit)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.settings_table.setItem(row, 3, item)

            item = QTableWidgetItem(str(setting.value))
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.settings_table.setItem(row, 4, item)
            row += 1
        self.settings_table.cellChanged.connect(self.on_setting_change)

        row = 0
        self.overrides_table.cellChanged.disconnect()
        for offset in self.yacp.overrides:
            override = self.yacp.overrides[offset]

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

            item = QTableWidgetItem(override.unit)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.overrides_table.setItem(row, 4, item)
            row += 1
        self.overrides_table.cellChanged.connect(self.on_override_change)

    def on_setting_change(self, table_index, column):
        if column != 1 or table_index == None:
            return

        setting_key = [*self.yacp.settings][table_index]
        str_val = self.settings_table.item(table_index, column).text()
        
        self.yacp.sendSettingChange(setting_key, str_val)
        
    def on_override_change(self, table_index, column):
        if column != 2 or table_index == None:
            return

        override_key = [*self.yacp.overrides][table_index]
        str_val = self.overrides_table.item(table_index, 2).text()
        override_status = self.overrides_table.cellWidget(table_index, 1).currentText()

        self.yacp.sendOverrideChange(override_key, str_val, override_status)
        
    def on_override_status_change(self):
        combo = self.sender()
        table_index = combo.property('row')
        self.on_override_change(table_index, 2)

    def on_setting_combobox_change(self):
        combo = self.sender()
        table_index = combo.property('row')

        if table_index == None:
            return

        setting_key = [*self.yacp.settings][table_index]
        choice = combo.currentData()

        self.yacp.sendSettingChange(setting_key, choice)
        

    def loadDefFileDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"Open build def", self.projectPath,"Def Files (*.json)", options=options)
        if fileName:
            self.loadDefFile(fileName)

    def loadDefFile(self, fileName):
        self.measurements_table.setRowCount(0)
        self.settings_table.setRowCount(0)
        self.overrides_table.setRowCount(0)
                
        revision = self.yacp.loadDefFile(fileName)

        if revision == -1:
            print("No revision found...")
            return

        self.setWindowTitle("YACP Cal // Def: "+fileName+" REVISION: "+str(revision))

        self.btn_hello.setEnabled(True)
        self.calOpenAct.setEnabled(True)
        self.recentCalMenu.setEnabled(True)
                
        self.config["RecentDefs"][os.path.basename(fileName)] = fileName
        self.recentDefFiles[os.path.basename(fileName)] = fileName
        self.projectPath = os.path.split(fileName)[0]
        self.saveConfig()

        self.update_widgets()
        
    def updateMeasurement(self, table_index, offset):
        measurement = self.yacp.measurements[offset]
        val = str(measurement.value)
        for value in measurement.values.keys():
            if val == value:
                val = measurement.values[value]
                break

        if self.graph_row != -1 and self.graph_row == table_index:
            self.graph_y = self.graph_y[1:]
            self.graph_y.append(float(val)) 
            self.graph_line.setData(self.graph_x, self.graph_y)   
        
        self.measurements_table.item(table_index, 1).setText(val)

    def updateSetting(self, table_index, offset):
        self.settings_table.cellChanged.disconnect()
        
        setting = self.yacp.settings[offset]
        if len(setting.choices) == 0:
            self.settings_table.item(table_index, 1).setText(str(setting.value))
        else:
            index = self.settings_table.cellWidget(table_index, 1).findData(setting.value)
            self.settings_table.cellWidget(table_index, 1).setCurrentIndex(index)

        self.settings_table.cellChanged.connect(self.on_setting_change)

    def updateOverride(self, table_index, offset, overridden):
        override = self.yacp.overrides[offset]
        
        self.overrides_table.item(table_index, 2).setText(str(override.value))
        if overridden:
            self.overrides_table.cellWidget(table_index, 1).setCurrentText("Overridden")
        else:
            self.overrides_table.cellWidget(table_index, 1).setCurrentText("Passthrough")
        
    def updateDeviceList(self):
        self.combo_devices.clear()
        
        for device_id in self.yacp.devices:
            self.combo_devices.addItem(str(device_id))

        if len(self.yacp.devices) > 0:
            self.btn_device_connect.setEnabled(True)

    def sendHello(self):
        self.combo_devices.clear()
        self.btn_device_connect.setEnabled(False)
        
        self.yacp.sendHello()

    def deviceConnect(self):
        device_id = int(self.combo_devices.currentText())
        if device_id != None and device_id != "":
            self.yacp.deviceConnect(device_id)

    def saveSettings(self):
        self.yacp.saveSettings()
        self.exportSettingsCSV()

    def exportSettingsCSV(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getSaveFileName(self,"Save Cal File",self.projectPath,"Cal Files (*.csv)", options=options)
        if fileName:
            self.yacp.exportSettingsCSV(fileName)
            
            self.statusBar().showMessage("Cal saved to "+fileName)

    def loadCalFileDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"Open Cal File",self.projectPath,"Cal Files (*.csv)", options=options)
        if fileName:
            self.loadCalFile(fileName)

    def loadCalFile(self, fileName):
        self.yacp.loadCalFile(fileName)
        
        for offset in self.yacp.settings:
            setting = self.yacp.settings[offset]
            table_index = setting.index

            if len(setting.choices) == 0:
                self.settings_table.item(table_index, 1).setText(str(setting.value))
            else:
                for choice in setting.choices.keys():
                    if choice == str(setting.value):
                        break
                    i += 1
                    
                if i >= len(setting.choices):
                    i = 0
                
                self.settings_table.cellWidget(table_index, 1).setCurrentIndex(i)

        self.config["RecentCals"][os.path.basename(fileName)] = fileName
        self.recentCalFiles[os.path.basename(fileName)] = fileName
        self.projectPath = os.path.split(fileName)[0]
        self.saveConfig()

    def updateDeviceState(self):
        if self.yacp.device_state == YACPProtocol.DEVICE_STATE_DISCONNECTED:
            pass
        
        elif self.yacp.device_state == YACPProtocol.DEVICE_STATE_READING_SETTINGS:
            self.statusBar().showMessage("Reading setting "+str(self.yacp.read_setting_index+1)+"/"+str(self.yacp.num_settings))        
                           
        elif self.yacp.device_state == YACPProtocol.DEVICE_STATE_READING_OVERRIDES:
            self.statusBar().showMessage("Reading override "+str(self.yacp.read_override_index+1)+"/"+str(self.yacp.num_overrides))
        
        elif self.yacp.device_state == YACPProtocol.DEVICE_STATE_READING_MEASUREMENTS:
            self.statusBar().showMessage("Reading measurement "+str(self.yacp.read_measurement_index+1)+"/"+str(self.yacp.num_measurements))
            
        elif self.yacp.device_state == YACPProtocol.DEVICE_STATE_CONNECTED:
            self.statusBar().showMessage("Connected to device ID "+str(self.yacp.device_id))
            self.btn_save.setEnabled(True)

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

        if self.yacp.can_state == 0:
            self.statusBar().showMessage("Connecting...")
            self.yacp.connect(bustype, interface, bitrate, True)
        elif self.yacp.can_state == 1:
            self.statusBar().showMessage("Disconnecting...")
            self.yacp.connect(bustype, interface, bitrate, False)

    def updateCANStatus(self):
        if self.yacp.can_state == 1:
            self.statusBar().showMessage("CAN device connected")
            self.btn_connect.setText("Disconnect")

            self.combo_rate.setEnabled(False)
            self.combo_bustype.setEnabled(False)
        elif self.yacp.can_state == 0:
            self.statusBar().showMessage("CAN device disconnected")
            self.btn_connect.setText("Connect")
            
            self.combo_rate.setEnabled(True)
            self.combo_bustype.setEnabled(True)
            
            self.btn_hello.setEnabled(False)
            self.btn_device_connect.setEnabled(False)
            self.btn_save.setEnabled(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('icon.ico'))
    
    excepthook = sys.excepthook
    sys.excepthook = lambda t, val, tb: excepthook(t, val, tb)
    
    gui = YACPcal()
    gui.setGeometry(100, 100, 1900, 500)
    gui.show()
    
    app.exec_()
