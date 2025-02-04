from PyQt5.QtWidgets import (
    QWidget, QPushButton, QLineEdit, QApplication, QMainWindow,
    QVBoxLayout, QHBoxLayout, QFrame, QSpacerItem, QSizePolicy,
    QMessageBox, QFileDialog, QCheckBox,
    QLabel, QAction, qApp, QDialog, QGridLayout
    )
from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtGui import QIcon
from modules import eudaq
from modules.ui.rootwidget import RootWidget
from modules.ui.run_progress import RunProgress
from modules.serial_connect import get_port
import serial
import modules.zaber.connect as zaber_connect
import modules.zaber.motion as motion
import json
import os
from os import path
import subprocess
import modules.alpide as alpide
import usb

class RunWidget(QWidget):
    def __init__(self, window):
        super(RunWidget, self).__init__()
        self._ser = None
        self._window = window
        self._run_type = 0
        self._pid = None
        self._w = None 
        self._opened_file = None
        self._first_file = None
        self._checks = [0, 0]
        self._connection_icons = [QIcon('./images/link-break-2.svg'), 
                                  QIcon('./images/link-2.svg')]
        self._connect_styles = [
        """
            QPushButton{
                color: rgb(100, 100, 100);
                font-size: 24px;
                background-color: rgb(255, 150, 150);
                border-radius: 10px;
            }
            QPushButton:hover{
                background-color: rgb(255, 200, 200);
            }
        """,       
        """
            QPushButton{
                font-size: 24px;
                background-color: rgb(100, 255, 100);
                border-radius: 10px;
            }
        """,
        ]
        self._firmware_btn = QPushButton("Install firmware")
        self._firmware_btn.setEnabled(self._window._alpide_connect)
        self._firmware_btn.clicked.connect(self.install_firmware)
        self._connection = {"alpide": QPushButton(" ALPIDE"),
                            "zaber": QPushButton(" Zaber"),
                            "fpga": QPushButton(" FPGA")}
        self._connection["alpide"].clicked.connect(lambda x: self.check_connection("alpide"))
        self._connection["fpga"].clicked.connect(lambda x: self.check_connection("fpga"))
        self._connection["zaber"].clicked.connect(lambda x: self.check_connection("zaber"))
        for v in self._connection.values():
            v.setCursor(Qt.CursorShape.PointingHandCursor)
            v.setIconSize(QSize(20, 20))
            v.setFixedWidth(150)
        self.check_connections()
    # for conn_name, is_conn in zip(["ALPIDE", "Zaber", "FPGA"], 
        #                      [self._window._alpide_connect, self._window._zaber_connect,
        #                       self._window._fpga_connect]):
        #     conn_layout = QHBoxLayout()
        #     conn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        #     conn_layout.addWidget(self._connection_icons[1] if is_conn else self._connection_icons[0])
        #     conn_label = QLabel(conn_name)
        #     conn_label.setStyleSheet("""
        #     QLabel{
        #         font-size: 24px;
        #     }
        #                              """)
        #     conn_icon_label = QLabel()
        #     conn_icon_label.setIcon
        #     conn_layout.addWidget()

        self._outpath_label = QLabel(path.join(os.getcwd(), 'output'))
        self._outpath_btn = QPushButton("output")
        self._outpath_btn.clicked.connect(self.chooseOutpath)
        self._current_file = None
        self._launch_eudaq_default = QPushButton("Launch default")
        self._launch_eudaq_default.setEnabled(False)
        self._kill_beam_btn = QPushButton("Kill beam")
        self._kill_beam_btn.setCheckable(True)
        self._kill_beam_btn.setEnabled(False)
        self._kill_beam_btn.clicked.connect(self.kill_beam_action)
        self._gate_checkbox = QCheckBox()
        # self._gate_checkbox.setText("Open Gate")
        # self._gate_checkbox.setStyleSheet("""
        # QCheckBox{
        #     font-size: 24px;
        # }
        # QCheckBox::indicator{
        #     width: 40px;
        #     height: 40px;
        # }
        #                                   """)
        # self._gate_checkbox.stateChanged.connect(lambda x: self.beam_action(1))
        self._enable_checkbox = QCheckBox()
        self._enable_checkbox.setText("Enable")
        self._enable_checkbox.setStyleSheet("""
        QCheckBox{
            font-size: 24px;
        }
        QCheckBox::indicator{
            width: 40px;
            height: 40px;
        }
                                          """)
        self._enable_checkbox.stateChanged.connect(self.enable_beam)
        self._enable_checkbox.setToolTip("Enable KCMH proton beam")
        self._launch_eudaq_default.clicked.connect(self.launch_eudaq)
        # self._kill_beam_btn.clicked.connect(lambda kind: self.launch_eudaq("auto"))
        self._kill_beam_btn.setFixedHeight(40)
        self._launch_eudaq_default.setFixedHeight(40)
        # self._launch_eudaq_default.setDisabled(True)
        self._launch_eudaq_default.setStyleSheet("""
            QPushButton{
                font-size: 24px;
                font-weight: bold;
                background-color: rgb(10, 200, 200)
            }
                                                 """)
        self._kill_beam_btn.setStyleSheet("""
            QPushButton{
                font-size: 24px;
                font-weight: bold;
                background-color: rgb(200, 10, 200)
            }
                                                 """)
        self._line_edits = {
            "num_alpides": QLineEdit(),
            "num_events": QLineEdit(),
            "strobe": QLineEdit(),
            "ithr": QLineEdit(),
            "energy": QLineEdit(),
            "MU": QLineEdit(),
            "current": QLineEdit(),
            "Exposure time (ms)": QLineEdit(),
            "Beam delay (ms)": QLineEdit(),
            "Loops": QLineEdit(),
            "Trigger Freq. (Hz)": QLineEdit(),
            "X step (mm)": QLineEdit(),
            "Y step (mm)": QLineEdit(),
            "R step (degree)": QLineEdit()
        }
                         
        self._line_edits["num_alpides"].setText("6")
        self._line_edits["num_alpides"].setToolTip("Number of ALPIDEs to do the test: 1 - 6")
        self._line_edits["num_events"].setText("30000")
        self._line_edits["num_events"].setToolTip("The total number of events to collect data")
        self._line_edits["strobe"].setText("100")
        self._line_edits["strobe"].setToolTip("The STROBE length used for the telescope: 100 - 500")
        self._line_edits["ithr"].setText("60")
        self._line_edits["ithr"].setToolTip("The threshold of all ALPIDEs: 1 - 400")
        self._line_edits["energy"].setText("200")
        self._line_edits["energy"].setToolTip("The energy used in the test: 70 - 220")
        self._line_edits["MU"].setText("1000")
        self._line_edits["MU"].setToolTip("The monitor unit used for the test: 10 - 10000")
        self._line_edits["current"].setText("10")
        self._line_edits["current"].setToolTip("The current used for KCMH beam: 4 - 300")
        self._line_edits["Exposure time (ms)"].setText("1000")
        self._line_edits["Exposure time (ms)"].setToolTip("The total exposure time used for the test: 1 - 100000")
        self._line_edits["Beam delay (ms)"].setText("200")
        self._line_edits["Beam delay (ms)"].setToolTip("The dalay beam hit event between phantom translations: 0 - 255")
        self._line_edits["Loops"].setText("1")
        self._line_edits["Loops"].setToolTip("The loop of radiation: must be less than exposure time")
        self._line_edits["Trigger Freq. (Hz)"].setText("9500")
        self._line_edits["Trigger Freq. (Hz)"].setToolTip("The trigger frequency: 1 - 95000")
        self._line_edits["X step (mm)"].setText("0")
        self._line_edits["Y step (mm)"].setText("0")
        self._line_edits["R step (degree)"].setText("0")
        for k, v in self._line_edits.items():
            v.editingFinished.connect(lambda x=k: self.validate_fields(x))
            v.setFixedSize(150, 30)
            v.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.setStyleSheet("""QLineEdit{
                font-size: 20px;
                background-color: rgb(255, 255, 255);
                border: 1px solid rgb(0, 0, 255);
                }""")
        # self._line_edits["num_alpides"].setToolTip("Number of alpide (1 - 6)")
        # self._line_edits["num_events"].setToolTip("")
        # self._line_edits["strobe"].setToolTip("")
        # self._line_edits["ithr"].setToolTip("")
        # self._line_edits["energy"].setToolTip("")
        # self._line_edits["MU"].setToolTip("")
        # self._line_edits["current"].setToolTip("")
        # self._line_edits["Exposure time (ms)"].setToolTip("")
        # self._line_edits["Beam delay (ms)"].setToolTip("")
        # self._line_edits["Loops"].setToolTip("")
        # self._line_edits["Trigger Freq. (Hz)"].setToolTip("")
        # self._line_edits["X step (mm)"].setToolTip("")
        # self._line_edits["Y step (mm)"].setToolTip("")
        # self._line_edits["R step (degree)"].setToolTip("")
        self._top_widget = QFrame()
        # self._top_widget.setStyleSheet("""
        # QFrame {
        #     border: 2px solid rgba(0, 0, 0, 0.1);
        #     border-radius: 10px;
        # }
        # """)
        self._bottom_widget = QFrame()
        # self._bottom_widget.setStyleSheet("""
        # QFrame {
        #     border: 2px solid rgba(0, 0, 0, 0.1);
        #     border-radius: 10px;
        # }
        # QLabel {
        #     border: 0;
        # }
        # """)
        self.init_ui()
    
    def init_ui(self):
        
        self._firmware_btn.setFixedHeight(60)
        self._firmware_btn.setFixedWidth(200)
        self._firmware_btn.setStyleSheet("""
        QPushButton {
            font-size: 20px;
            font-weight: bold;
            background-color: rgb(200, 200, 10);
        }""")
        main_layout = QVBoxLayout()

        top_layout = QVBoxLayout()
        
        sub_top_layout = QHBoxLayout()
        sub_top_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_top_layout.setSpacing(40)
        for v in self._connection.values():
            sub_top_layout.addWidget(v)
        top_layout.addLayout(sub_top_layout)
        sub_top_layout = QHBoxLayout()
        sub_top_layout.addWidget(QWidget(), 1)
        sub_top_layout.addWidget(self._firmware_btn, 1)
        sub_top_layout.addWidget(QWidget(), 1)
        top_layout.addLayout(sub_top_layout)
        self._top_widget.setLayout(top_layout)

        outpath_layout = QHBoxLayout()
        outpath_widget = QFrame()
        outpath_widget.setStyleSheet("""

            QLabel{
                border: 0px;
                font-size: 20px
            }
            QPushButton {
                font-size: 20px
            }
                                 """)
        self._outpath_btn.setFixedWidth(150)
        outpath_btn_icon = QIcon("./images/folder-open.svg")
        self._outpath_btn.setIcon(outpath_btn_icon)
        outpath_layout.addWidget(self._outpath_label)
        outpath_layout.addWidget(self._outpath_btn)
        outpath_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outpath_widget.setLayout(outpath_layout)
        
        ph_layout = QVBoxLayout()
        ph_widget = QFrame()
        ph_widget.setStyleSheet("""

        QLabel{
            font-size: 24px;
            border: 0px;
        }
                                """)
        ph_label = QLabel("Phantom")
        ph_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_label.setStyleSheet("""
        QLabel{
            font-weight: bold;
        }
                               """)
        sub_ph_layout = QHBoxLayout()
        
        ph_pos_layout = QHBoxLayout()
        self._ph_x_label = QLabel(self._window.orig_loc[0])
        ph_x_label = QLabel("X: ")
        ph_x_label.setFixedWidth(50)
        ph_x_unit = QLabel(" mm")
        ph_x_unit.setFixedWidth(50)
        ph_pos_layout.addWidget(ph_x_label)
        ph_pos_layout.addWidget(self._ph_x_label)
        ph_pos_layout.addWidget(ph_x_unit)
        ph_pos_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_ph_layout.addLayout(ph_pos_layout)
        
        ph_pos_layout = QHBoxLayout()
        self._ph_y_label = QLabel(self._window.orig_loc[1])
        ph_y_label = QLabel("Y: ")
        ph_y_label.setFixedWidth(50)
        ph_y_unit = QLabel(" mm")
        ph_y_unit.setFixedWidth(50)
        ph_pos_layout.addWidget(ph_y_label)
        ph_pos_layout.addWidget(self._ph_y_label)
        ph_pos_layout.addWidget(ph_y_unit)
        ph_pos_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_ph_layout.addLayout(ph_pos_layout)
        
        ph_pos_layout = QHBoxLayout()
        self._ph_r_label = QLabel(self._window.orig_loc[2])
        ph_r_label = QLabel("R: ")
        ph_r_label.setFixedWidth(50)
        ph_r_unit = QLabel(" degree")
        ph_r_unit.setFixedWidth(100)
        ph_pos_layout.addWidget(ph_r_label)
        ph_pos_layout.addWidget(self._ph_r_label)
        ph_pos_layout.addWidget(ph_r_unit)
        ph_pos_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_ph_layout.addLayout(ph_pos_layout)
        
        ph_layout.addWidget(ph_label)
        ph_layout.addLayout(sub_ph_layout)
        ph_widget.setLayout(ph_layout)
        
        ctrl_widget = QFrame()
        ctrl_widget.setStyleSheet("""
            QFrame{
                border: 2px solid rgba(0, 0, 0, 0.1);
                border-radius: 10px;
            }
            QLabel{
                border: 0px;
            }
                                 """)
        
        sup_ctrl_layout = QVBoxLayout()
        sup_ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl_layout = QGridLayout()
        ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controller_label = QLabel("Controller")
        controller_label.setStyleSheet("""
        QLabel{
            font-weight: bold;
            font-size: 24px;
        }
                                       """)
        controller_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sup_ctrl_layout.addWidget(controller_label)
        sup_ctrl_layout.addSpacerItem(QSpacerItem(2, 25))
        l_names = ["Exposure time (ms)", "Beam delay (ms)", "Loops", "Trigger Freq. (Hz)", 
                   "X step (mm)", "Y step (mm)", "R step (degree)"]
        for l_i, (l_name, le_name) in enumerate(zip(l_names, list(self._line_edits.keys())[7:])):
            sub_ctrl_layout = QVBoxLayout()
            widget = QFrame()
            widget.setStyleSheet("""
                QFrame{
                    border: 2px dotted rgba(0, 0, 0, 0.1);
                    border-radius: 10px;
                }
                QLabel{
                    border: 0px;
                }
                                 """)
            edit_lable = QLabel(l_name)
            edit_lable.setAlignment(Qt.AlignmentFlag.AlignCenter)
            edit_lable.setFixedHeight(25)
            edit_lable.setStyleSheet("""QLabel{
                    font-size: 20px;
                }""")
            sub_ctrl_layout.addWidget(QWidget(), 1)
            sub_ctrl_layout.addWidget(edit_lable)
            edit_layout = QHBoxLayout()
            edit_layout.addStretch()
            edit_layout.addWidget(self._line_edits[le_name])
            edit_layout.addStretch()
            sub_ctrl_layout.addLayout(edit_layout)
            sub_ctrl_layout.addWidget(QWidget(), 4)
            ctrl_layout.addLayout(sub_ctrl_layout, int(l_i/4), l_i%4)
        all_cb_layout = QVBoxLayout()
        enable_cb_layout = QHBoxLayout()
        enable_cb_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # enable_cb_layout.addWidget(QWidget(), 1)
        enable_cb_layout.addWidget(self._enable_checkbox, 1)
        enable_cb_layout.addWidget(QWidget(), 1)
        all_cb_layout.addLayout(enable_cb_layout)
        gate_cb_layout = QHBoxLayout()
        gate_cb_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # gate_cb_layout.addWidget(QWidget(), 1)
        # gate_cb_layout.addWidget(self._gate_checkbox, 1)
        # gate_cb_layout.addWidget(QWidget(), 1)
        # all_cb_layout.addLayout(gate_cb_layout)

        ctrl_layout.addLayout(all_cb_layout, 1, 3)
        sup_ctrl_layout.addLayout(ctrl_layout)
        ctrl_widget.setLayout(sup_ctrl_layout)

        bottom_layout = QVBoxLayout()
        eudaq_label = QLabel("EUDAQ")
        eudaq_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        eudaq_label.setStyleSheet("""
        QLabel{
            font-weight: bold;
            font-size: 24px;
        }
                               """)
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame{
                border: 2px dotted rgba(0, 0, 0, 0.1);
                border-radius: 10px;
            }
            QLabel{
                border: 0px;
            }
                                 """)

        beam_run_layout = QGridLayout()
        bottom_widget = QFrame()
        bottom_widget.setStyleSheet("""
        QFrame {
            border: 2px solid rgba(0, 0, 0, 0.1);
            border-radius: 10px;
        }
        QLabel {
            border: 0;
        }
        """)
        l_names = ["Number of ALPIDEs", "Number of events", "STROBE length", "I Threshold", 
                   "Energy (MeV)", "MU", "Current (nA)"]
        for l_i, (l_name, le_name) in enumerate(zip(l_names, list(self._line_edits.keys())[:7])):
            subsubsub_bottom_edit_layout = QVBoxLayout()
            edit_lable = QLabel(l_name)
            edit_lable.setAlignment(Qt.AlignmentFlag.AlignCenter)
            edit_lable.setFixedHeight(25)
            edit_lable.setStyleSheet("""QLabel{
                    font-size: 20px;
                }""")
            subsubsub_bottom_edit_layout.addWidget(edit_lable)
            edit_layout = QHBoxLayout()
            edit_layout.addStretch()
            edit_layout.addWidget(self._line_edits[le_name])
            edit_layout.addStretch()
            subsubsub_bottom_edit_layout.addLayout(edit_layout)
            if int(l_i/4) == 0:
                subsubsub_bottom_edit_layout.addWidget(QWidget(), 1)
            beam_run_layout.addLayout(subsubsub_bottom_edit_layout, int(l_i/4), l_i%4)
        subsub_bottom_layout = QVBoxLayout()
        subsub_bottom_layout.addWidget(eudaq_label)
        subsub_bottom_layout.addLayout(beam_run_layout)
        bottom_widget.setLayout(subsub_bottom_layout)
        bottom_layout.addWidget(bottom_widget, 2)

        run_btn_layout = QHBoxLayout()
        run_btn_layout.addWidget(QWidget(), 1)
        run_btn_layout.addWidget(self._launch_eudaq_default, 1)
        run_btn_layout.addWidget(QWidget(), 1)
        run_btn_layout.addWidget(QWidget(), 1)
        run_btn_layout.addWidget(self._kill_beam_btn, 1)
        run_btn_layout.addWidget(QWidget(), 1)
        # self._kill_beam_btn.setEnabled(False)
        # bottom_layout.addLayout(run_btn_layout, 1)
        widget_temp = QWidget()
        widget_temp.setLayout(run_btn_layout)
        bottom_layout.addWidget(widget_temp, 1)

        self._bottom_widget.setLayout(bottom_layout)
        main_layout.addWidget(self._top_widget, 1)
        main_layout.addWidget(outpath_widget, 1)
        main_layout.addWidget(ph_widget, 1)
        main_layout.addWidget(ctrl_widget, 1)
        main_layout.addWidget(self._bottom_widget, 2)
        self.setLayout(main_layout)
    
    def open_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","EDAQ Files (*.edaq)", options=options)
        if fileName:
            with open(fileName, 'r') as f:
                jsonData = json.load(f)
                for kdata in jsonData.keys():
                    self._line_edits[kdata].setText(str(jsonData[kdata]))
            self._opened_file = fileName
    
    def save_file(self, saveas=False):
        try:
            num_alpides = int(self._line_edits["num_alpides"].text())
            num_events = int(self._line_edits["num_events"].text())
            strobe_length = int(self._line_edits["strobe"].text())
            i_threshold = int(self._line_edits["ithr"].text())
            energy = int(self._line_edits["energy"].text())
            MU = int(self._line_edits["MU"].text())
            current = int(self._line_edits["current"].text())
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            if (not saveas and self._opened_file) or (saveas and not self.open_file):
                data_dict = {}
                for k, v in self._line_edits.items():
                    data_dict[k] = int(v.text())
                with open(self._opened_file, 'w') as f:
                    json.dump(data_dict, f)
            else:
                fileName, _ = QFileDialog.getSaveFileName(self,"QFileDialog.getSaveFileName()", "","EDAQ Files (*.edaq)", options=options)
                if not fileName:
                    return
                real_file_name = fileName.split('/')[-1]
                is_edaq_file = "edaq" == real_file_name.split('.')[-1]
                data_dict = {}
                for k, v in self._line_edits.items():
                    data_dict[k] = int(v.text())
                write_file_name = fileName if is_edaq_file else "/" + path.join('', *fileName.split('/')[:-1], real_file_name + ".edaq")
                with open(write_file_name, 'w') as f:
                    json.dump(data_dict, f)
        except:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Error")
            msg.setInformativeText('Invalid input feild')
            msg.setWindowTitle("Error")
            msg.exec_()
    
    def viewRecentRaw(self):
        if not self._current_file:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Error")
            msg.setInformativeText('No resent RAW output')
            msg.setWindowTitle("Error")
            msg.exec_()
        else:
            eudaq.monitor(self._current_file)

    def viewRawFile(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", self._outpath_label.text(),"RAW Files (*.raw)", options=options)
        if fileName:
            eudaq.monitor(fileName)
    
    def exportToRoot(self):
        self._exp_root_dialog = RootWidget(self)
        self._exp_root_dialog.exec_()
        """if self._w is None:
            self._w = RootWidget()
        self._w.show()"""

    def chooseOutpath(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        options |= QFileDialog.ShowDirsOnly
        dirName = QFileDialog.getExistingDirectory(self,"QFileDialog.getExistingDirectory()", self._outpath_label.text(), options=options)
        if dirName:
            self._outpath_label.setText(dirName)
    
    def initUI(self):
        main_layout = QVBoxLayout()
        top_layout = QVBoxLayout()
        sub_top_layout = QHBoxLayout()
        sub_top_layout.addWidget(QWidget(), 1)
        sub_top_layout.addWidget(self._firmware_btn, 1)
        sub_top_layout.addWidget(QWidget(), 1)
        top_layout.addLayout(sub_top_layout)
        self._top_widget.setLayout(top_layout)

        outpath_layout = QHBoxLayout()
        outpath_widget = QFrame()
        outpath_widget.setStyleSheet("""
            QFrame{
                border: 2px dotted rgba(0, 0, 0, 0.1);
                border-radius: 10px;
            }
            QLabel{
                border: 0px;
                font-size: 20px
            }
            QPushButton {
                font-size: 20px
            }
                                 """)
        self._outpath_btn.setFixedWidth(150)
        outpath_btn_icon = QIcon("./images/folder-open.svg")
        self._outpath_btn.setIcon(outpath_btn_icon)
        outpath_layout.addWidget(self._outpath_label)
        outpath_layout.addWidget(self._outpath_btn)
        outpath_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outpath_widget.setLayout(outpath_layout)

        bottom_layout = QVBoxLayout()
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame{
                border: 2px dotted rgba(0, 0, 0, 0.1);
                border-radius: 10px;
            }
            QLabel{
                border: 0px;
            }
                                 """)

        subsub_bottom_edit_layout = QHBoxLayout()
        l_names = ["Number of ALPIDEs", "Number of events", "STROBE length", "I Threshold"]
        for l_name, le_name in zip(l_names, list(self._line_edits.keys())[:4]):
            subsubsub_bottom_edit_layout = QVBoxLayout()
            widget = QFrame()
            widget.setStyleSheet("""
                QFrame{
                    border: 2px dotted rgba(0, 0, 0, 0.1);
                    border-radius: 10px;
                }
                QLabel{
                    border: 0px;
                }
                                 """)
            edit_lable = QLabel(l_name)
            edit_lable.setAlignment(Qt.AlignmentFlag.AlignCenter)
            edit_lable.setFixedHeight(25)
            edit_lable.setStyleSheet("""QLabel{
                    font-size: 20px;
                }""")
            subsubsub_bottom_edit_layout.addWidget(QWidget(), 1)
            subsubsub_bottom_edit_layout.addWidget(edit_lable)
            edit_layout = QHBoxLayout()
            edit_layout.addStretch()
            edit_layout.addWidget(self._line_edits[le_name])
            edit_layout.addStretch()
            subsubsub_bottom_edit_layout.addLayout(edit_layout)
            subsubsub_bottom_edit_layout.addWidget(QWidget(), 4)
            widget.setLayout(subsubsub_bottom_edit_layout)
            subsub_bottom_edit_layout.addWidget(widget)


        widget_temp = QWidget()
        widget_temp.setLayout(subsub_bottom_edit_layout)
        bottom_layout.addWidget(widget_temp, 2)

        subsub_bottom_edit_layout = QHBoxLayout()
        l_names = ["Energy (MeV)", "MU", "Current (nA)"]
        for l_name, le_name in zip(l_names, list(self._line_edits.keys())[4:]):
            widget = QFrame()
            widget.setStyleSheet("""
                QFrame{
                    border: 2px dotted rgba(0, 0, 0, 0.1);
                    border-radius: 10px;
                }
                QLabel{
                    border: 0px;
                }
                                 """)
            subsubsub_bottom_edit_layout = QVBoxLayout()
            edit_lable = QLabel(l_name)
            edit_lable.setAlignment(Qt.AlignmentFlag.AlignCenter)
            edit_lable.setFixedHeight(25)
            edit_lable.setStyleSheet("""QLabel{
                    font-size: 20px;
                }""")
            subsubsub_bottom_edit_layout.addWidget(QWidget(), 1)
            subsubsub_bottom_edit_layout.addWidget(edit_lable)
            edit_layout = QHBoxLayout()
            edit_layout.addStretch()
            edit_layout.addWidget(self._line_edits[le_name])
            edit_layout.addStretch()
            subsubsub_bottom_edit_layout.addLayout(edit_layout)
            subsubsub_bottom_edit_layout.addWidget(QWidget(), 4)
            widget.setLayout(subsubsub_bottom_edit_layout)
            subsub_bottom_edit_layout.addWidget(widget)


        widget_temp = QWidget()
        widget_temp.setLayout(subsub_bottom_edit_layout)
        bottom_layout.addWidget(widget_temp, 2)

        run_btn_layout = QHBoxLayout()
        run_btn_layout.addWidget(QWidget(), 1)
        run_btn_layout.addWidget(self._launch_eudaq_default, 1)
        run_btn_layout.addWidget(QWidget(), 1)
        run_btn_layout.addWidget(self._kill_beam_btn, 1)
        run_btn_layout.addWidget(QWidget(), 1)
        # self._kill_beam_btn.setEnabled(False)
        # bottom_layout.addLayout(run_btn_layout, 1)
        widget_temp = QWidget()
        widget_temp.setLayout(run_btn_layout)
        bottom_layout.addWidget(widget_temp, 1)

        self._bottom_widget.setLayout(bottom_layout)
        main_layout.addWidget(self._top_widget, 1)
        main_layout.addWidget(outpath_widget, 1)
        main_layout.addWidget(self._bottom_widget, 2)
        self.setLayout(main_layout)
        # self._main_widget.setLayout(main_layout)
    
    def install_firmware(self):
        eudaq.install_firware()
        # alpide_dir = "/home/pct-ubuntu/alpide-daq-software"
        # command_alpide = "alpide-daq-program --fx3={}/tmp/fx3.img --fpga={}/tmp/fpga-v1.0.0.bit --all"\
        #     .format(alpide_dir, alpide_dir)
        # command = f'gnome-terminal -- bash -c "cd {alpide_dir} && {command_alpide}; exec bash"'
        # process = subprocess.Popen(command_alpide, shell=True, stdout=subprocess.PIPE)
        # out, err = process.communicate()
        # out_lines = out.decode('utf-8').splitlines()
        # if out_lines[0] == "No unprogrammed FX3 device found. Skipping FX3 programming step." or\
        #     out_lines[1] == "No programmed FX3 device found. Skipping FPGA programming step.":
        #         print("XXXX")
    
    def clear_for_new(self):
        for line_edit in self._line_edits.values():
            line_edit.setText("")

    def launch_eudaq(self):
        self.check_connection('alpide')
        self.check_connection('fpga')
        connections = [
            self._window._alpide_connect,
            self.check_zaber_nohome(),
            self._window._zaber_connect,
            alpide.is_programmed()
            ]
        if not all(connections):
            fail_dialog = QMessageBox()
            fail_dialog.setIcon(QMessageBox.Icon.Critical)
            if connections[-1] == False:
                fail_dialog.setText("Unprogrammed DAQs.")
                fail_dialog.setWindowTitle("DAQs issue")
                fail_dialog.setDetailedText("Please program DAQs.")
            else:
                fail_dialog.setText("Fail to connect devices.")
                fail_dialog.setWindowTitle("Connection issue")
                fail_dialog.setDetailedText("Please reconnect devices.")
            fail_dialog.setStandardButtons(QMessageBox.Ok) 
            fail_dialog.exec_()
            return
        
        # fpga_data = self.get_fpga_data()
        # ser = serial.Serial(port=get_port("fpga"), baudrate=fpga_data["baudrate"], parity=fpga_data["parity"],
        #                 bytesize=fpga_data["bytesize"], stopbits=fpga_data["stopbits"], timeout=1)

        if self._enable_checkbox.checkState() != Qt.Checked:
            fail_dialog = QMessageBox()
            fail_dialog.setIcon(QMessageBox.Icon.Critical)
            fail_dialog.setText("Enable is off!")
            fail_dialog.setWindowTitle("KCMH error")
            fail_dialog.setDetailedText("KCMH need to be enabled.")
            fail_dialog.setStandardButtons(QMessageBox.Ok) 
            fail_dialog.exec_()
            self._kill_beam_btn.setChecked(False)
            return
        
        # for b in fpga_data["byte_start_list"]:
        #     self._ser.write(b)
        self._pid = eudaq.default_run(self._line_edits, self._outpath_label.text())
        self._run_progress_dialog = RunProgress(self)
        self._run_progress_dialog.exec_()
        
    def stop_run(self):
        if self._pid:
            eudaq.stop(self._pid)

        if self._pid and self.get_new_outfile() != self._first_file:
            self._first_file = self.get_new_outfile()
            self._current_file = self._first_file
            with open("./logs.txt", "a") as f:
                f.write(f"{self._current_file},{','.join([v.text() for v in self._line_edits.values()])}\n")
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText("Stoped run")
            msg.setInformativeText(f"Saved {self._first_file.split('/')[-1]}")
            msg.setWindowTitle("Notification")
            msg.exec_()
        elif self._pid and self.get_new_outfile() == self._first_file:
            self._current_file = None
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Error")
            msg.setInformativeText('Stoped run without output file')
            msg.setWindowTitle("Error")
            msg.exec_()
        self._pid = None

    def get_new_outfile(self):
        files = [os.path.join(self._outpath_label.text(), file) for file in os.listdir(self._outpath_label.text())]
        files = [myfile for myfile in files if os.path.isfile(myfile)]
        if files:
            return max(files, key=os.path.getmtime)
        else:
            None 
    
    def get_fpga_data(self):
        baudrate = 115200
        parity = serial.PARITY_NONE
        bytesize = serial.EIGHTBITS
        stopbits = serial.STOPBITS_ONE
        trigger_f_bin = bin(int(self._line_edits["Trigger Freq. (Hz)"].text())).lstrip('0b').zfill(16)
        trigger_f_byte_list = [int(trigger_f_bin[:-8], 2).to_bytes(1, 'big'), int(trigger_f_bin[-8:], 2).to_bytes(1, 'big')]
        alpide_delay = bin(int(self._line_edits["Beam delay (ms)"].text())).lstrip('0b').zfill(8)
        alpide_delay_byte = int(alpide_delay, 2).to_bytes(1, 'big')
        byte_start_list = [b'\x00', b'\x01', b'\x00', b'\x00', b'\x00', b'\x00', alpide_delay_byte, trigger_f_byte_list[0],
            trigger_f_byte_list[1]]
        return {
            "baudrate": baudrate,
            "parity": parity,
            "bytesize": bytesize,
            "stopbits": stopbits,
            "byte_start_list": byte_start_list
        }

    def enable_beam(self):
        try:
            if self._ser:
                try:
                    self.ser.close()
                except:
                    pass

            fpga_data = self.get_fpga_data()
            self._ser = serial.Serial(port=get_port("fpga"), baudrate=fpga_data["baudrate"], parity=fpga_data["parity"],
                            bytesize=fpga_data["bytesize"], stopbits=fpga_data["stopbits"], timeout=1)
            
            self._ser.write(b'\x00')
            self._ser.write(b'\x00')
                
            self._kill_beam_btn.setChecked(False)
            if self._enable_checkbox.checkState() == Qt.Checked:
                self._ser.write(b'\x02')
                for b in fpga_data["byte_start_list"][1:]:
                    self._ser.write(b)
                self._kill_beam_btn.setEnabled(True)
                self._launch_eudaq_default.setEnabled(True)
                self._window.running(True)
            else:
                self._ser.write(b'\xF2')
                self._kill_beam_btn.setEnabled(False)
                self._launch_eudaq_default.setEnabled(False)
                self._ser = None
                self._window.running(False)
            # ser.close()
            # except:
            #     pass
        except ConnectionError:
            fail_dialog = QMessageBox()
            fail_dialog.setIcon(QMessageBox.Icon.Critical)
            fail_dialog.setText("No FPGA connection")
            fail_dialog.setWindowTitle("FPGA error")
            fail_dialog.setDetailedText("Please connect to FPGA")
            fail_dialog.setStandardButtons(QMessageBox.Ok) 
            fail_dialog.exec_()
            self._kill_beam_btn.setChecked(False)
            self._kill_beam_btn.setEnabled(False)
            self._launch_eudaq_default.setEnabled(False)
            return
    
    def set_ph_loc(self, loc_str):
        self._ph_x_label.setText(loc_str[0])
        self._ph_y_label.setText(loc_str[1])
        self._ph_r_label.setText(loc_str[2])
    
    def check_connections(self):
        if self._window._alpide_connect:
            self._connection["alpide"].setIcon(self._connection_icons[1])
            self._connection["alpide"].setStyleSheet(self._connect_styles[1])
        else:
            self._connection["alpide"].setIcon(self._connection_icons[0])
            self._connection["alpide"].setStyleSheet(self._connect_styles[0])
        if self._window._zaber_connect:
            self._connection["zaber"].setIcon(self._connection_icons[1])
            self._connection["zaber"].setStyleSheet(self._connect_styles[1])
        else:
            self._connection["zaber"].setIcon(self._connection_icons[0])
            self._connection["zaber"].setStyleSheet(self._connect_styles[0])
        if self._window._fpga_connect:
            self._connection["fpga"].setIcon(self._connection_icons[1])
            self._connection["fpga"].setStyleSheet(self._connect_styles[1])
        else:
            self._connection["fpga"].setIcon(self._connection_icons[0])
            self._connection["fpga"].setStyleSheet(self._connect_styles[0])
            
        self._firmware_btn.setEnabled(self._window._alpide_connect)
    
    def check_connection(self, device):
        if device == "alpide":
            if alpide.found_daqs():
                self._window._alpide_connect = True
            else:
                self._window._alpide_connect = False
        elif device == "zaber":
            if self._window.check_zaber():
                self._window._zaber_connect = True
            else:
                self._window._zaber_connect = False
        elif device == "fpga":
            if self._window.check_fpga():
                self._window._fpga_connect = True
            else:
                self._window._fpga_connect = False
                
        if device == "alpide":
            if self._window._alpide_connect:
                self._connection["alpide"].setIcon(self._connection_icons[1])
                self._connection["alpide"].setStyleSheet(self._connect_styles[1])
            else:
                self._connection["alpide"].setIcon(self._connection_icons[0])
                self._connection["alpide"].setStyleSheet(self._connect_styles[0])
        elif device == "zaber":
            if self._window._zaber_connect:
                self._connection["zaber"].setIcon(self._connection_icons[1])
                self._connection["zaber"].setStyleSheet(self._connect_styles[1])
            else:
                self._connection["zaber"].setIcon(self._connection_icons[0])
                self._connection["zaber"].setStyleSheet(self._connect_styles[0])
        elif device == "fpga":
            if self._window._fpga_connect:
                self._connection["fpga"].setIcon(self._connection_icons[1])
                self._connection["fpga"].setStyleSheet(self._connect_styles[1])
            else:
                self._connection["fpga"].setIcon(self._connection_icons[0])
                self._connection["fpga"].setStyleSheet(self._connect_styles[0])
        
        self._firmware_btn.setEnabled(self._window._alpide_connect)
        
    def check_zaber_nohome(self):
        try:
            conn = zaber_connect.connect(get_port("zaber"))
            loc = motion.get_current_locations(conn)
            if ("_ph_widget" in self.__dict__.keys()):
                self._ph_widget.set_all_loc(loc)
            conn.close()
            return True
        except:
            return False
        
    def kill_beam_action(self):
        # fpga_data = self.get_fpga_data()
        # initailize serial may cause enable off
        # ser = serial.Serial(port=get_port("fpga"), baudrate=fpga_data["baudrate"], parity=fpga_data["parity"],
        #                 bytesize=fpga_data["bytesize"], stopbits=fpga_data["stopbits"], timeout=1)

        # ser.write(b'\xEF')
        # ser.close()
        
        
        # for b in fpga_data["byte_start_list"]:
        #         ser.write(b)
        if self._enable_checkbox.checkState() != Qt.Checked:
            fail_dialog = QMessageBox()
            fail_dialog.setIcon(QMessageBox.Icon.Critical)
            fail_dialog.setText("Enable is off!")
            fail_dialog.setWindowTitle("KCMH error")
            fail_dialog.setDetailedText("KCMH need to be enabled.")
            fail_dialog.setStandardButtons(QMessageBox.Ok) 
            fail_dialog.exec_()
            self._kill_beam_btn.setChecked(False)
            return
        if not self._ser:
            fail_dialog = QMessageBox()
            fail_dialog.setIcon(QMessageBox.Icon.Critical)
            fail_dialog.setText("FPGA not found!")
            fail_dialog.setWindowTitle("FPGA error")
            fail_dialog.setDetailedText("FPGA is not ready.")
            fail_dialog.setStandardButtons(QMessageBox.Ok) 
            fail_dialog.exec_()
            self._kill_beam_btn.setChecked(False)
            return
        

        if self._kill_beam_btn.isChecked():
            # self._ser.write(b'\x03')
            self._ser.write(b'\xFE')
            self._launch_eudaq_default.setEnabled(False)
            self._window.running(True)
            # self._window.running(True)
            # self._enable_checkbox.setDisabled(True)
            # self._gate_checkbox.setDisabled(True)
        else:
            # self._ser.write(b'\xF3')
            self._ser.write(b'\xEF')
            self._launch_eudaq_default.setEnabled(True)
            self._window.running(True)
            # self._window.running(False)
            # self._gate_checkbox.setDisabled(False)
            # self._enable_checkbox.setDisabled(False)

    def validate_fields(self, kind):
        # if kind == "num_alpides":
        msg = {
            "num_alpides": ["number of ALPIDEs", list(range(1, 7))],
            "num_events": ["number of events", list(range(1, 100_000))],
            "strobe": ["STROBE value", list(range(100, 801))],
            "ithr": ["I theshold", list(range(30, 121))],
            "energy": ["proton energy", list(range(70, 241))],
            "MU": ["MU", list(range(1, 100000))],
            "current": ["current", list(range(4, 300))],
            "Exposure time (ms)": ["exposure time", list(range(1, 100_000))],
            "Beam delay (ms)": ["beam dalay", list(range(0, 256))],
            "Loops": ["number of loops", list(range(1, 20))],
            "Trigger Freq. (Hz)": ["trigger frequency", list(range(1, 99001))],
            "X step (mm)": ["X step length", [-float(self._window.orig_loc[0]), 150 - float(self._window.orig_loc[0])]],
            "Y step (mm)": ["Y step length", [-float(self._window.orig_loc[1]), 40 - float(self._window.orig_loc[1])]],
            "R step (degree)": ["angle step", list(range(0, 360))]
        }
        try:
            if kind not in ["X step (mm)", "Y step (mm)"]:
                value = int(self._line_edits[kind].text())
                if value not in msg[kind][1]:
                    raise ValueError
            else:
                value = float(self._line_edits[kind].text())
                if value < msg[kind][1][0] or value > msg[kind][1][1]:
                    raise ValueError
        except ValueError:
            valiadated_popup(msg[kind][0], msg[kind][1]).exec_()
            self._line_edits[kind].setStyleSheet("""
                QLineEdit{
                    border: 4px solid rgb(255, 0, 0);
                    font-size: 20px;
                }
                                                            """)
            self._line_edits[kind].setText("")
            self._line_edits[kind].setFocus()
        else:
            self._line_edits[kind].setStyleSheet("""
                QLineEdit{
                    border: 1px solid rgb(0, 0, 255);
                    font-size: 20px;
                }
                                                            """)

def valiadated_popup(msg, allowed_values):
    fail_dialog = QMessageBox()
    fail_dialog.setIcon(QMessageBox.Icon.Critical)
    fail_dialog.setText("Invalid {} input.".format(msg))
    fail_dialog.setWindowTitle("Input error")
    fail_dialog.setDetailedText("[{}, {}]".format(allowed_values[0], allowed_values[-1]))
    fail_dialog.setStandardButtons(QMessageBox.Ok) 
    return fail_dialog