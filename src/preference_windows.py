import webbrowser

from PyQt6 import QtWidgets, uic, QtGui
from PyQt6.QtWidgets import QMessageBox, QScrollArea, QVBoxLayout, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
import sys
from pathlib  import Path 
from constants import SOFTWARE_VERSION
import requests
from packaging.version import Version


GITHUB_OWNER = "TheGoodWeather"
GITHUB_REPO = "Vector-Vario-Analyzer"
DOWNLOAD_URL = "https://vectorvario.com/en/analyzer/"
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
        self.settings.setValue("vertical_speed", self.comboBox_vertical_speed.currentText())
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
        self.comboBox_vertical_speed.setCurrentText(self.settings.value("vertical_speed"))
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
        self.setFixedSize(24, 24)
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
    colorDynaChanged = pyqtSignal()

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

        # Map explorer
        self.color_button_windbarb = ColorButton(color="#000000")  # Start with black as default
        self.color_button_plot = ColorButton(color="#ff0000") #Start with red as default
        self.windbarbs_color_widget.layout().addWidget(self.color_button_windbarb)
        self.plot_color_widget.layout().addWidget(self.color_button_plot)

        # Dyna tab

        self.color_button_grid = ColorButton(color="#FFFFFF")  
        self.color_button_dynaplot = ColorButton(color="#ff0000") 
        self.color_button_background = ColorButton(color="#a29c9c") 
        self.color_button_model = ColorButton(color="#FF1717")
        
        self.grid_color_widget.layout().addWidget(self.color_button_grid)
        self.dynaplot_color_widget.layout().addWidget(self.color_button_dynaplot)
        self.background_color_widget.layout().addWidget(self.color_button_background)
        self.model_color_widget.layout().addWidget(self.color_button_model)
        
        self.buttonBox.accepted.connect(self.write_settings)    
        self.read_settings()


        
    def write_settings(self):
        self.settings.beginGroup("colors")
        self.settings.setValue("windbarbs", self.color_button_windbarb.color())
        self.settings.setValue("plot", self.color_button_plot.color())
        self.settings.setValue("grid", self.color_button_grid.color())
        self.settings.setValue("dynaplot", self.color_button_dynaplot.color())
        self.settings.setValue("background", self.color_button_background.color())
        self.settings.setValue("model", self.color_button_model.color())
        self.settings.endGroup()
        
        self.colorWindBarbsChanged.emit()
        self.colorPlotChanged.emit()
        self.colorDynaChanged.emit()
        self.close()
        
    def read_settings(self):
        
        
        self.settings.beginGroup("colors")
        self.color_button_windbarb.setColor(self.settings.value("windbarbs" , "#000000"))
        self.color_button_plot.setColor(self.settings.value("plot" , "#ff0000"))
        self.color_button_grid.setColor(self.settings.value("grid" , "#FFFFFF"))
        self.color_button_dynaplot.setColor(self.settings.value("dynaplot" , "#ff0000"))
        self.color_button_background.setColor(self.settings.value("background" , "#a29c9c"))
        self.color_button_model.setColor(self.settings.value("model" , "#FF1717"))
        self.settings.endGroup()



class LicenseDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Licence - GNU GPL v3")
        self.resize(700, 500)
        layout = QVBoxLayout(self)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setText(self.load_license_text())
        self.text_edit.setStyleSheet("font-family: monospace;")
        layout.addWidget(self.text_edit)

        btn_close = QPushButton("Fermer")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

    def load_license_text(self):
        try:
            return resource_path("LICENSE.txt").read_text(encoding="utf-8")
        except Exception as e:
            return f"Erreur chargement licence : {e}"


class RequirementsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Software Dependencies")
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
            content = resource_path("requirements.txt").read_text(encoding="utf-8")
            lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
            self.table.setRowCount(len(lines))
            for row, line in enumerate(lines):
                # Sépare "package==1.0.0" en ["package", "1.0.0"]
                if "==" in line:
                    package, version = line.split("==", 1)
                elif ">=" in line:
                    package, version = line.split(">=", 1)
                    version = f">= {version}"
                else:
                    package, version = line, ""

                self.table.setItem(row, 0, QTableWidgetItem(package.strip()))
                self.table.setItem(row, 1, QTableWidgetItem(version.strip()))

        except Exception as e:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem(f"Error : {e}"))
            

        
class AboutDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("About")
        self.resize(400, 300)
        
        logo_path      = str(resource_path("gui/icons/logo.png")).replace("\\", "/")
        author_path    = str(resource_path("gui/icons/author.jpg")).replace("\\", "/")
        youtube_path   = str(resource_path("gui/icons/youtube_icon.png")).replace("\\", "/")
        instagram_path = str(resource_path("gui/icons/instagram_icon.png")).replace("\\", "/")
        buy_path       = str(resource_path("gui/icons/buy_icon.jpg")).replace("\\", "/")
                
        layout = QVBoxLayout(self)

        label = QLabel()
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setOpenExternalLinks(True)
        label.setAlignment(Qt.AlignmentFlag.AlignTop)
        label.setWordWrap(True)
        label.setText(f"""
                <h2>Vector Vario Analyzer</h2>
        
                <p><b>Software Version:</b></p>
                <p>
                    <img src="{logo_path}" width="80"><br>
                    Version {SOFTWARE_VERSION}
                </p>
        
                <h3>About the Software</h3>
                <p>
                Vector Vario Analyzer is an open-source software.<br>
                It has been developed to improve the VV user experience by making it easy to visualize any raw data recorded by the Vector Vario.<br><br>
        
                Bear in mind that this software is only a handy tool to quickly represent data. It has not been made for scientific purpose.<br><br>
        
                New versions are coming with additional features.<br>
                To stay updated, visit:
                <a href="https://vectorvario.com/">Vector Vario Website</a>
                </p>
        
                <h3>About the Author</h3>
                <p>
                <img src="{author_path}" width="120"><br><br>
                My name is Félix, the main developer behind VV Analyzer.<br><br>
                As a polar field engineer, I develop this project voluntarily alongside my field work, dedicating my free time to its growth and improvement.<br><br>

                The origins of VV Analyzer trace back to the remote and frozen environments of Antarctica, where the project first came to life.<br><br>
        
                Please keep in mind that I am also not a software developer.<br>
                I am learning coding through this project, and thus not everything is perfect or well optimised (yet)!
                </p>
        
                <h3>Reach Us</h3>
                <p>
                For help with VVS crashes, errors, or to discuss improvements or suggest new features, you can join the Discord channel :<br>
                <a href="https://discord.com/invite/NA6kJbpJWa">
                https://discord.com/invite/NA6kJbpJWa
                </a>
                </p>
                You can also follow Vector Vario on Youtube and Instagram :<br>
                <p>
                <a href="https://www.youtube.com/@VectorVario">
                    <img src="{youtube_path}" width="40">
                </a>
                &nbsp;
                <a href="https://www.instagram.com/vectorvario/">
                    <img src="{instagram_path}" width="40">
                </a>
                </p>
        
                <h3>Buy Me a Coffee ☕</h3>
                <p>
                To help the project moving forward, your donation goes directly to funding Vector Vario Analyzer development and maintenance, and helps adding the features you want. <br><br>
        
                <a href="https://buymeacoffee.com/TheGoodWeather">
                    <img src="{buy_path}" width="40">
                </a>
                </p>
                """)
                
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(label)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        layout.addWidget(scroll)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)



def check_version(parent = None):

    def get_latest_version():
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            data = response.json()
            return data["tag_name"]

        except Exception:
            return None

    latest = get_latest_version()  
    if latest is None:
        QMessageBox.warning(
            parent,
            "Version",
            "Impossible to reach GitHub repository"
            f"Current : v{SOFTWARE_VERSION}"
        )
        return

    if Version(latest) > Version(SOFTWARE_VERSION):
        msg = QMessageBox(parent)
        msg.setWindowTitle("Update Available")
        msg.setIcon(QMessageBox.Information)

        msg.setText(
            f"A new version is available: {latest}\n\n"
            f"Current version: v{SOFTWARE_VERSION}"
        )

        download_btn = msg.addButton(
            "Download",
            QMessageBox.AcceptRole
        )

        msg.addButton(
            QMessageBox.Close
        )

        msg.exec()

        if msg.clickedButton() == download_btn:
            webbrowser.open(DOWNLOAD_URL)


    elif Version(latest) == Version(SOFTWARE_VERSION):
        QMessageBox.information(
            parent,
            "Version",
            f"You are using the latest version : v{SOFTWARE_VERSION}."
        )
    elif Version(latest) < Version(SOFTWARE_VERSION):
        QMessageBox.warning(
            parent,
            "Version",
            f"You are not using a stable version.\n"
            f"Current : v{SOFTWARE_VERSION}\n"
            f"Latest stable : {latest}"
        )

def resource_path(relative_path: str) -> Path:
    """Retourne le chemin absolu, compatible dev et PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        # Mode PyInstaller : ressources extraites dans un dossier temp
        base = Path(sys._MEIPASS)
    else:
        # Mode développement
        base = Path(__file__).parent.parent # remonte à src/

    return base / relative_path