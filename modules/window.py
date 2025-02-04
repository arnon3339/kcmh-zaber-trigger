from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QWidget, QSlider, QDial, QLineEdit, QMessageBox, QToolButton,
                             QSpacerItem, QTabWidget, QAction, qApp)
from PyQt5.QtGui import QIcon

from modules.ui.phantom import PhWidget
from modules.ui.run import RunWidget

import modules.zaber.connect as zaber_connect
import modules.fpga.connect as fpga_connect
import modules.zaber.motion as motion
from modules.serial_connect import get_port
import modules.alpide as alpide
import subprocess

class MyWindow(QMainWindow):
    def __init__(self):
        super(MyWindow, self).__init__()
        self._fpga_connect = False
        self._zaber_connect = False
        self._alpide_connect = False
        self.init_connect_devices()
        
        try:
            conn = zaber_connect.connect(get_port("zaber"))
            loc = motion.get_current_locations(conn)
            conn.close()
            self.orig_loc = ["{:.2f}".format(l) for l in loc]
        except:
            self._zaber_connect = False
            self.orig_loc = ["0"]*3
        
        self.init_ui()
    
    def init_ui(self):
        self._run_widget = RunWidget(self)
        self._ph_widget = PhWidget(self)
        self._tab_widget = QTabWidget()
        self._tab_widget.addTab(self._run_widget, "Run")
        self._tab_widget.addTab(self._ph_widget, "Phantom")
        self.setCentralWidget(self._tab_widget)
        self.initMenuBar()
        
    def initMenuBar(self):
        # new action
        newAction = QAction(QIcon("./images/file.svg"), 'New', self) 
        newAction.setShortcut('Ctrl+N')
        newAction.triggered.connect(lambda x: self.run_widget_fn("New"))

        # open action
        openAction = QAction(QIcon("./images/folder-open.svg"), 'Open', self)
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip("Open new file")
        openAction.triggered.connect(lambda x: self.run_widget_fn("Open"))

        # save action
        saveAction = QAction(QIcon("./images/save.svg"), 'Save', self)
        saveAction.setShortcut('Ctrl+S')
        saveAction.setStatusTip("Save a file")
        saveAction.triggered.connect(lambda x: self.run_widget_fn("Save"))

        # save as action
        saveAsAction = QAction(QIcon("./images/save-all.svg"), 'Save As', self)
        saveAsAction.setShortcut('Ctrl+Shift+S')
        saveAsAction.setStatusTip("Save a file as")
        saveAsAction.triggered.connect(lambda x: self.run_widget_fn("SaveAs"))

        # exit action
        exitAct = QAction(QIcon('./images/log-out.svg'), 'Exit', self)
        exitAct.setShortcut('Ctrl+Q')
        exitAct.setStatusTip('Exit application')
        exitAct.triggered.connect(qApp.quit)
        
        viewRecentAction = QAction(QIcon('./images/view.svg'), 'View recent', self)
        viewRecentAction.setShortcut('Ctrl+M')
        viewRecentAction.setStatusTip('View current raw')
        viewRecentAction.triggered.connect(lambda x: self.run_widget_fn("ViewRecent"))

        viewFile = QAction(QIcon('./images/scan-eye.svg'), 'View file', self)
        viewFile.setShortcut('Ctrl+Shift+M')
        viewFile.setStatusTip('View raw file')
        viewFile.triggered.connect(lambda x: self.run_widget_fn("ViewFile"))

        expRoot = QAction(QIcon('./images/file-up.svg'), 'Export root', self)
        expRoot.setShortcut('Ctrl+R')
        expRoot.setStatusTip('Export to root file')
        expRoot.triggered.connect(lambda x: self.run_widget_fn("ExportROOT"))
        
        fpga_connect = QAction(QIcon('./images/view.svg'), 'Connect FPGA', self)
        fpga_connect.setStatusTip('Connect FPGA')
        fpga_connect.triggered.connect(lambda x: self.reconnect_devices("fpga"))

        zaber_connect = QAction(QIcon('./images/scan-eye.svg'), 'Connec ZABERs', self)
        zaber_connect.setStatusTip('Connec ZABERs')
        zaber_connect.triggered.connect(lambda x: self.reconnect_devices("zaber"))

        alpide_connect = QAction(QIcon('./images/file-up.svg'), 'Connect ALPIDEs', self)
        alpide_connect.setStatusTip('Connect ALPIDEs')
        alpide_connect.triggered.connect(lambda x: self.reconnect_devices("alpide"))
        
        all_connect = QAction(QIcon('./images/file-up.svg'), 'Connect All', self)
        all_connect.setStatusTip('Connect all devices')
        all_connect.triggered.connect(lambda x: self.reconnect_devices("all"))

        menubar = self.menuBar()
        
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(newAction)
        fileMenu.addAction(openAction)
        fileMenu.addAction(saveAction)
        fileMenu.addAction(saveAsAction)
        fileMenu.addAction(exitAct)

        monitorFile = menubar.addMenu('&Monitor')
        monitorFile.addAction(viewRecentAction)
        monitorFile.addAction(viewFile)
        monitorFile.addAction(expRoot)
                
        # connectionMenu = menubar.addMenu('&Connection')
        # connectionMenu.addAction(alpide_connect)
        # connectionMenu.addAction(zaber_connect)
        # connectionMenu.addAction(fpga_connect)
        # connectionMenu.addAction(all_connect)
    
    def init_connect_devices(self):
        if alpide.found_daqs():
            self._alpide_connect = True
        else:
            self._alpide_connect = False
            
        if self.check_zaber():
            self._zaber_connect = True
        else:
            self._zaber_connect = False
            
        if self.check_fpga():
            self._fpga_connect = True
        else:
            self._fpga_connect = False

    def reconnect_devices(self, device):
        if device in ["zaber", "fpga", "alpide"]:
            self._run_widget.check_connection(device)
        else: 
            if alpide.found_daqs():
                self._alpide_connect = True
            else:
                self._alpide_connect = False
                
            if self.check_zaber():
                self._zaber_connect = True
            else:
                self._zaber_connect = False
                
            if self.check_fpga():
                self._fpga_connect = True
            else:
                self._fpga_connect = False
            
            self._run_widget.check_connections()
                
    def check_zaber(self):
        try:
            conn = zaber_connect.connect(get_port("zaber"))
            motion.to_home(conn)
            loc = motion.get_current_locations(conn)
            if ("_ph_widget" in self.__dict__.keys()):
                self._ph_widget.set_all_loc(loc)
            conn.close()
            return True
        except:
            return False
    
    def check_fpga(self):
        try:
            connection = fpga_connect.check_connection(get_port("fpga"))
            return connection
        except:
            return False
    
    def run_widget_fn(self, menu):
        if menu == "New":
            self._run_widget.clear_for_new()
        elif menu == "Open":
            self._run_widget.open_file()
        elif menu == "Save":
            self._run_widget.save_file()
        elif menu == "SaveAs":
            self._run_widget.save_file(True)
        elif menu == "ViewRecent":
            self._run_widget.viewRecentRaw()
        elif menu == "ViewFile":
            self._run_widget.viewRawFile()
        elif menu == "ExportROOT":
            self._run_widget.exportToRoot()
    
    def set_run_ph_loc(self, loc):
        self._run_widget.set_ph_loc(loc)
    
    def running(self, is_running):
        if is_running:
            self._ph_widget.setDisabled(True)
            # self._run_widget._gate_checkbox.setDisabled(True)
            # self._run_widget._firmware_btn.setDisabled(True)
            self._run_widget._outpath_btn.setDisabled(True)
            for v in self._run_widget._connection.values():
                v.setDisabled(True)
            
            for ledit in self._run_widget._line_edits.values():
                ledit.setDisabled(True)
        else:
            self._ph_widget.setDisabled(False)
            self._run_widget._outpath_btn.setDisabled(False)
            for v in self._run_widget._connection.values():
                v.setDisabled(False)
            # self._run_widget._firmware_btn.setDisabled(True)
            # self._run_widget._gate_checkbox.setDisabled(False)
            for ledit in self._run_widget._line_edits.values():
                ledit.setDisabled(False)