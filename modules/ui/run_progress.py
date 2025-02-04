from PyQt5.QtWidgets import (
    QWidget, QPushButton, QLineEdit, QApplication, QMainWindow,
    QVBoxLayout, QHBoxLayout, QFrame, QSpacerItem, QSizePolicy,
    QMessageBox, QFileDialog, QProgressBar,
    QLabel, QAction, qApp, QDialog
    )
from PyQt5.QtCore import Qt, QRect, QRunnable, QObject, pyqtSlot, pyqtSignal, QThreadPool
from PyQt5.QtGui import QIcon
import sys, traceback
# from modules.window import MyWindow
import modules.zaber.connect as zaber_connect
from modules.serial_connect import get_port
from modules.zaber.motion import (apply_steps, 
                                  apply_steps_loop,
                                  get_current_locations
                                  )
import serial
import math
import time
import asyncio
import datetime
import subprocess

force_stop = False
baudrate = 115200
parity = serial.PARITY_NONE
bytesize = serial.EIGHTBITS
stopbits = serial.STOPBITS_ONE

class WorkerSignals(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(dict)
    error = pyqtSignal(tuple)
    # progress = pyqtSignal(int)
    
class ProgressWorker(QRunnable):
    def __init__(self, *args, **kwargs):
        super(ProgressWorker, self).__init__()
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        
        # self.kwargs['progress_callback'] = self.signals.progress
            
    @pyqtSlot()
    def run(self):
        try:
            # trigger_f_bin = self.kwargs['trigger_f_bin']
            # trigger_f_byte_list = [int(trigger_f_bin[:-8], 2).to_bytes(1, 'big'), int(trigger_f_bin[-8:], 2).to_bytes(1, 'big')]
            # alpide_delay = self.kwargs['alpide_delay']
            # alpide_delay_byte = int(alpide_delay, 2).to_bytes(1, 'big')
            ser = serial.Serial(port=get_port("fpga"), baudrate=baudrate, parity=parity,
                            bytesize=bytesize, stopbits=stopbits, timeout=1)
            # byte_start_list = [b'\x00', b'\x01', b'\x00', b'\x00', b'\x00', b'\x00', alpide_delay_byte, trigger_f_byte_list[0],
            #         trigger_f_byte_list[1]]
            # for b in byte_start_list:
            #     ser.write(b)
            step_current_datetime = datetime.datetime.now()
            current_time = datetime.datetime.now()
            value = 0
            step = 1
            ser.write(b'\xFE')
            locs = self.kwargs['locs']
            while True:
                if force_stop == True:
                    self.signals.progress.emit({"type": "progress", "value": 1000})
                    ser.write(b'\x00')
                    ser.close()
                    break
                
                if (datetime.datetime.now() - step_current_datetime).total_seconds() > self.args[1]:
                    ser.write(b'\xEF')
                    self.signals.progress.emit({"type": "step", "value": step, "locs": locs})
                    if step < self.args[2]:
                        locs = apply_steps_loop(self.kwargs['conn'], self.kwargs['steps'], self.kwargs['event_loop'])
                    ser.write(b'\xFE')
                    value = int(step*1000/self.args[2])
                    step += 1
                    step_current_datetime = datetime.datetime.now()       
                    current_time = datetime.datetime.now()  
                    if step > self.args[2]:
                        # ser.write(b'\x00')
                        ser.write(b'\xEF')
                        ser.close()
                        break
                elif (datetime.datetime.now() - current_time).total_seconds() > self.args[0]:
                    value += 1
                    self.signals.progress.emit({"type": "progress", "value": value, "locs": locs})
                    current_time = datetime.datetime.now()    
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        finally:
            self.signals.finished.emit()
            
# class StepWorker(QRunnable):
#     def __init__(self, *args, **kwargs):
#         super(StepWorker, self).__init__()
#         self.args = args
#         self.kwargs = kwargs
#         self.signals = WorkerSignals()
        
#     @pyqtSlot()
#     def run(self):
#         try:
#             current_time = datetime.datetime.now()
#             value = 0
#             while True:
#                 if value == self.args[1]:
#                     break
#                 if (datetime.datetime.now() - current_time).total_seconds() > self.args[0]:
#                     value += 1
#                     self.signals.progress.emit(value)     
#                     current_time = datetime.datetime.now()          
#         except:
#             traceback.print_exc()
#             exctype, value = sys.exc_info()[:2]
#             self.signals.error.emit((exctype, value, traceback.format_exc()))
#         finally:
#             self.signals.finished.emit()

class RunProgress(QDialog):
    def __init__(self, window):
        super(RunProgress, self).__init__()
        self._loop = asyncio.get_event_loop()
        asyncio.set_event_loop(self._loop)
        self._window = window
        self._is_text_visible = False
        self._is_running = True
        self._is_thread = False
        self._threadpool = QThreadPool()
        self.init_ui()
    
    # def close_running(self):
    #     subprocess.run(['tmux', 'kill-session', '-t', 'ITS3'])
    #     print("closing running")
    
    def closeEvent(self, event):
        subprocess.run(['tmux', 'kill-session', '-t', 'ITS3'])
        if self._is_running:
            ser = serial.Serial(port=get_port("fpga"), baudrate=baudrate, parity=parity,
                            bytesize=bytesize, stopbits=stopbits, timeout=1)
            ser.write(b'\x00')
            ser.close()
        print("closing running")
        
    def init_ui(self):
        m_layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        pos_layout = QHBoxLayout()
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximum(1000)
        self._progress_bar.setFixedWidth(600)
        self._progress_bar.setFixedHeight(42)
        self._ph_locs = [
            QLabel("X: " + self._window._ph_x_label.text() + " mm"),
            QLabel("Y: " + self._window._ph_y_label.text() + " mm"),
            QLabel("R: " + self._window._ph_r_label.text() + " degree")
            ]
        for ph_loc in self._ph_locs:
            ph_loc.setStyleSheet("""
            QLabel{
                font-size: 24px;
            }
                                 """)
            pos_layout.addWidget(ph_loc)
        # self._progress_bar.setTextVisible(False)
        self._progress_bar.setFormat('')
        self._progress_bar.setStyleSheet("""
        QProgressBar{
            color: #0a9dff;
            border-style: solid;
            border-width: 2px;
            border-color: #999999;
            border-radius: 10px;
            text-align: center;
            font-size: 24px;
        }
        QProgressBar::chunk
        {
            background-color: rgb(150, 255, 100);
            border-radius: 6px;
        }
                                         """)
        self._run_btn = QPushButton("Run")
        self._stop_btn = QPushButton("Stop")
        btn_layout.addWidget(self._run_btn)
        btn_layout.addWidget(self._stop_btn)
        self._run_btn.clicked.connect(self.start_with_thread)
        self._stop_btn.clicked.connect(self.force_stop)
        self._stop_btn.setEnabled(False)
        m_layout.addWidget(self._progress_bar)
        m_layout.addLayout(pos_layout)
        m_layout.addLayout(btn_layout)
        self.setLayout(m_layout)
        self.setModal(True)
            
    def force_stop(self):
        global force_stop
        force_stop = True
        
    def update_progress(self, value):
        if value['type'] == 'step':
            self._progress_bar.setFormat("{}/{}".format(value['value'] if value['value']\
                < self._num_step_loops else self._num_step_loops,
                                                        self._num_step_loops))
            self._progress_bar.setValue(int(value['value']*1000/self._num_step_loops))
        else:
            self._progress_bar.setValue(value['value'])
        self._window._window._ph_widget.set_all_loc(value['locs'])
        self._locs = value['locs']
        self._ph_locs[0].setText("X: " + self._window._ph_x_label.text() + " mm")
        self._ph_locs[1].setText("Y: " + self._window._ph_y_label.text() + " mm")
        self._ph_locs[2].setText("R: " + self._window._ph_r_label.text() + " degree")
    
    def progress_finish(self):
        global force_stop
        force_stop = False
        self._is_running = False
        self._conn.close()
        self._window.stop_run()
        self.close()
    
        
    def start_with_thread(self): 
        self._num_step_loops = int(self._window._line_edits["Loops"].text())
        expose_time = (float(self._window._line_edits["Exposure time (ms)"].text()) + 
                       float(self._window._line_edits["Beam delay (ms)"].text())
                       )*int(self._window._line_edits["Loops"].text())*1e-3
        time_step = expose_time/self._num_step_loops
        time_prog_size = expose_time/(1000)
        self._zaber_steps = [
            float(self._window._line_edits["X step (mm)"].text()),
            float(self._window._line_edits["Y step (mm)"].text()),
            float(self._window._line_edits["R step (degree)"].text())
        ]
        self._conn = zaber_connect.connect(get_port("zaber"))
        self._locs = [
            float(self._window._ph_x_label.text()),
            float(self._window._ph_y_label.text()),
            float(self._window._ph_r_label.text())
                ]
        self._progress_bar.setFormat("0/{}".format(self._num_step_loops))
        self._event_loop = asyncio.get_event_loop()
        
        self._start_time = datetime.datetime.now()
        self._is_running = True
        self._stop_btn.setEnabled(True)
        progress_worker = ProgressWorker(time_prog_size, time_step, self._num_step_loops, conn=self._conn,
                                         steps=self._zaber_steps, event_loop=self._event_loop,
            trigger_f_bin = bin(int(self._window._line_edits["Trigger Freq. (Hz)"].text())).lstrip('0b').zfill(16),
            alpide_delay = bin(int(self._window._line_edits["Beam delay (ms)"].text())).lstrip('0b').zfill(8),
            locs=self._locs
            )
        progress_worker.signals.progress.connect(self.update_progress)
        progress_worker.signals.finished.connect(self.progress_finish)
    
        self._threadpool.start(progress_worker)