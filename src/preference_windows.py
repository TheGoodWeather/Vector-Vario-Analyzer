from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtWidgets import QListWidgetItem, QApplication, QLineEdit, QWidget, QVBoxLayout,QTableWidgetItem ,QButtonGroup , QPushButton, QHBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from PyQt6.QtGui import QColor, QPen, QBrush
from logging_handler import QTextEditLogger, logger
import sys
from pathlib  import Path 

class UnitDialog(QtWidgets.QDialog):
    
    
    unitsChanged = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.settings = QSettings("Vector Vario", "VVA")
   
        def resource_path(relative_path):
            #Get absolute path to resource (for PyInstaller and development) , I don't really understand but it seems useful for lauching as a onefile exe
            if hasattr(sys, '_MEIPASS'):
                return Path(sys._MEIPASS) / relative_path
            return Path(__file__).parent / relative_path


        uic.loadUi(resource_path("gui/unitwindow.ui"), self)  # Load the .ui file directly
        self.read_settings()
        self.buttonBox.accepted.connect(self.write_settings)
    
    
    def write_settings(self):
        self.settings.beginGroup("units")
        self.settings.setValue("heading", self.comboBox_heading.currentText())
        self.settings.setValue("speed", self.comboBox_speed.currentText())
        self.settings.setValue("coordinates", self.comboBox_coordinates.currentText())
        self.settings.setValue("altitude", self.comboBox_altitude.currentText())
        self.settings.setValue("temperature", self.comboBox_temperature.currentText())
        self.settings.setValue("angle", self.comboBox_angle.currentText())
        self.settings.setValue("pressure", self.comboBox_pressure.currentText())
        self.settings.endGroup()
        self.unitsChanged.emit()
      
        self.close()
        
    def read_settings(self):
        
        
        self.settings.beginGroup("units")
        self.comboBox_heading.setCurrentText(self.settings.value("heading"))
        self.comboBox_speed.setCurrentText(self.settings.value("speed"))
        self.comboBox_coordinates.setCurrentText(self.settings.value("coordinates"))
        self.comboBox_altitude.setCurrentText(self.settings.value("altitude"))
        self.comboBox_temperature.setCurrentText(self.settings.value("temperature"))
        self.comboBox_angle.setCurrentText(self.settings.value("angle"))
        self.comboBox_pressure.setCurrentText(self.settings.value("pressure"))
        self.settings.endGroup()
        
        
        
    
        
        
    

        