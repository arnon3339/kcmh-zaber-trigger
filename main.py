from PyQt5.QtWidgets import QApplication
import sys
from modules.window import MyWindow
import subprocess
import serial
from modules.serial_connect import get_port

if __name__ == "__main__":
    subprocess.run(['tmux', 'kill-session', '-t', 'ITS3'])
    app = QApplication(sys.argv)
    w = MyWindow()
    w.showMaximized()
    app.exec_()
    subprocess.run(['tmux', 'kill-session', '-t', 'ITS3'])
    
    baudrate = 115200
    parity = serial.PARITY_NONE
    bytesize = serial.EIGHTBITS
    stopbits = serial.STOPBITS_ONE
    
    try:
        ser = serial.Serial(port=get_port("fpga"), baudrate=baudrate, parity=parity,
                            bytesize=bytesize, stopbits=stopbits, timeout=1)
        ser.write(b'\x00')
        ser.write(b'\x00')
        ser.close()
    except:
        pass
    