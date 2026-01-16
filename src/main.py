#import time
import os
from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtWidgets import QApplication, QLineEdit, QWidget, QVBoxLayout,QTableWidgetItem ,QButtonGroup , QPushButton, QHBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPen, QBrush
from logging_handler import QTextEditLogger, logger

import sys
from pathlib  import Path 

# from logging_handler import QTextEditLogger, logger
 



class MainWindow(QtWidgets.QMainWindow):

    
    def __init__(self):
        super(MainWindow, self).__init__()
    
        uic.loadUi(self.resource_path("gui/mainwindow.ui"), self)  # Load the .ui file directly
        
        self.setFocus()  #allow the main windows to receive key press event 
        
        self.flight_loaded = False
        
        """
        Widgets tab import  / export
        """
        self.pushButton_load_file.clicked.connect(self.on_button_load_file)
        self.pushButton_generate_vva.clicked.connect(self.on_button_generate_vva)
        self.pushButton_clear_log.clicked.connect(self.on_button_clear_log)
        
        self.logbox_handler = QTextEditLogger(self.textEdit_log)
        self.textEdit_log.verticalScrollBar().setValue(self.textEdit_log.verticalScrollBar().maximum())
        logger.addHandler(self.logbox_handler) 
        
    def resource_path(self, relative_path):
        #Get absolute path to resource (for PyInstaller and development) , I don't really understand but it seems useful for lauching as exe maybe for database folder
        if hasattr(sys, '_MEIPASS'):
            return Path(sys._MEIPASS) / relative_path
        return Path(__file__).parent / relative_path
    
    def on_button_load_file(self):
        return 

    def on_button_generate_vva(self):
        return
    
    def on_button_clear_log(self):
        self.textEdit_log.clear()
        return
    

if __name__ == "__main__":
    try:
        if not QtWidgets.QApplication.instance():
            app = QtWidgets.QApplication(sys.argv)
        else : 
            app = QtWidgets.QApplication.instance() 
        app.setStyle("Fusion")
        window = MainWindow()
        window.showMaximized()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Fatal error {e}")
        # logger.exception(f"Fatal error occurred during startup {e}")