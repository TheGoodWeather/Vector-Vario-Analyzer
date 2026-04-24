from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtWidgets import QListWidgetItem, QApplication, QLineEdit, QWidget, QVBoxLayout,QTableWidgetItem ,QButtonGroup , QPushButton, QHBoxLayout, QFileDialog, QMessageBox, QTextEdit, QTableWidget
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
        
        
        
    

class ColorButton(QtWidgets.QPushButton):
    colorChanged = pyqtSignal(object)

    def __init__(self, *args, color=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._color = None
        self._default = color
        self.pressed.connect(self.onColorPicker)
        self.setColor(self._default)

    def setColor(self, color):
        if color != self._color:
            self._color = color
            self.colorChanged.emit(color)
        if self._color:
            # Affiche un petit carré coloré comme icône
            pixmap = QtGui.QPixmap(16, 16)
            pixmap.fill(QtGui.QColor(self._color))
            self.setIcon(QtGui.QIcon(pixmap))
        else:
            self.setIcon(QtGui.QIcon())

    def color(self):
        return self._color

    def onColorPicker(self):
        dlg = QtWidgets.QColorDialog(self)
        dlg.setOption(QtWidgets.QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
        if self._color:
            dlg.setCurrentColor(QtGui.QColor(self._color))
        if dlg.exec():
            self.setColor(dlg.currentColor().name())

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.RightButton:
            self.setColor(self._default)
        return super().mousePressEvent(e)      


class ColorDialog(QtWidgets.QDialog):
    
    
    colorWindBarbsChanged = pyqtSignal()
    colorPlotChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        def resource_path(relative_path):
            #Get absolute path to resource (for PyInstaller and development) , I don't really understand but it seems useful for lauching as a onefile exe
            if hasattr(sys, '_MEIPASS'):
                return Path(sys._MEIPASS) / relative_path
            return Path(__file__).parent / relative_path

        uic.loadUi(resource_path("gui/colorwindow.ui"), self)  # Load the .ui file directly
        self.settings = QSettings("Vector Vario", "VVA")
        self.color_button_windbarb = ColorButton(color="#000000")  # Start with black as default
        self.color_button_plot = ColorButton(color="#ff0000") #Start with red as default
        self.windbarbs_color_widget.layout().addWidget(self.color_button_windbarb)
        self.plot_color_widget.layout().addWidget(self.color_button_plot)

        
        self.read_settings()
        self.buttonBox.accepted.connect(self.write_settings)    
        

        
    def write_settings(self):
        self.settings.beginGroup("colors")
        self.settings.setValue("windbarbs", self.color_button_windbarb.color())
        self.settings.setValue("plot", self.color_button_plot.color())
        self.settings.endGroup()
        self.colorWindBarbsChanged.emit()
        self.colorPlotChanged.emit()
        self.close()
        
    def read_settings(self):
        
        
        self.settings.beginGroup("colors")
        self.color_button_windbarb.setColor(self.settings.value("windbarbs" , "#000000"))
        self.color_button_plot.setColor(self.settings.value("plot" , "#ff0000"))

        self.settings.endGroup()



class LicenseDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Licence - GNU GPL v3")
        self.resize(700, 500)

        layout = QVBoxLayout(self)

        # Zone de texte scrollable
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setText(self.load_license_text())
        self.text_edit.setStyleSheet("font-family: monospace;")

        layout.addWidget(self.text_edit)

        # Bouton fermer
        btn_close = QPushButton("Fermer")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

    def load_license_text(self):
        try:
            base_path = Path(__file__).resolve().parent
            license_path = base_path.parent / "LICENSE.txt"
    
            return license_path.read_text(encoding="utf-8")
    
        except Exception as e:
            return f"Erreur chargement licence : {e}"
        
        
        
class RequirementsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Software Dependancies")
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Package", "Version"])
        self.table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.table)

        btn_close = QPushButton("Fermer")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        self.load_requirements()

    def load_requirements(self):
        try:
            base_path = Path(__file__).resolve().parent
            req_path = base_path.parent / "requirements.txt"

            lines = req_path.read_text(encoding="utf-8").splitlines()

            data = []
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "==" in line:
                    pkg, ver = line.split("==")
                else:
                    pkg, ver = line, ""

                data.append((pkg, ver))

            self.table.setRowCount(len(data))

            for row, (pkg, ver) in enumerate(data):
                self.table.setItem(row, 0, QTableWidgetItem(pkg))
                self.table.setItem(row, 1, QTableWidgetItem(ver))

        except Exception as e:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("Error"))
            self.table.setItem(0, 1, QTableWidgetItem(str(e)))