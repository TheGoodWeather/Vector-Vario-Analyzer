#import time
import os
import shutil
from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtWidgets import QApplication, QLineEdit, QWidget, QVBoxLayout,QTableWidgetItem ,QButtonGroup , QPushButton, QHBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPen, QBrush
from logging_handler import QTextEditLogger, logger

import sys
from pathlib  import Path 
 
SOFTWARE_VERSION = "1.0.0"
VVA_VERSION = "1.0"

class MainWindow(QtWidgets.QMainWindow):

    
    def __init__(self):
        super(MainWindow, self).__init__()
    
        uic.loadUi(self.resource_path("gui/mainwindow.ui"), self)  # Load the .ui file directly
        
        self.setFocus()  #allow the main windows to receive key press event 
        
        self.flight_loaded = False
        self.new_file_path = None 
        
        """
        Widgets tab import  / export
        """
        
        self.pushButton_generate_vva.setEnabled(False)
        
        self.pushButton_load_file.clicked.connect(self.on_button_load_file)
        self.pushButton_generate_vva.clicked.connect(self.on_button_generate_vva)
        self.pushButton_clear_log.clicked.connect(self.on_button_clear_log)
        
        self.logbox_handler = QTextEditLogger(self.textEdit_log)
        self.textEdit_log.verticalScrollBar().setValue(self.textEdit_log.verticalScrollBar().maximum())
        logger.addHandler(self.logbox_handler) 
        
    def resource_path(self, relative_path):
        """
        Get absolute path to resource (for PyInstaller and development) 
        """
        if hasattr(sys, '_MEIPASS'):
            return Path(sys._MEIPASS) / relative_path
        return Path(__file__).parent / relative_path
    
    def external_path(self, relative_path):
        """
        Get the absolute path to an external file or folder (like config/) that is located
        next to the executable or script, but NOT bundled inside the .exe.
        """
        if getattr(sys, 'frozen', False):
            # Running from a PyInstaller bundle (.exe)
            base_path = Path(sys.executable).parent
        else:
            # Running from source (.py)
            base_path = Path(__file__).parent
    
        return base_path / relative_path
    
    def on_button_load_file(self):
        """
        Fetching new file path and copying it into flight folder
        """
        self.lineEdit_file_path.clear()
        self.new_file_path = QtWidgets.QFileDialog.getOpenFileName(self, "Open flight file", "", ".CSV .IGC Files (*.csv *.igc)")
        if self.new_file_path[0]:
            self.new_file_path = Path(self.new_file_path[0]) 
            self.lineEdit_file_path.setText(str(self.new_file_path))
            new_file_path_copy_name = Path(self.new_file_path).name
            new_file_path_copy = Path(os.path.join('./flight/',new_file_path_copy_name))
        else:
            return
        
        if not os.path.exists('./flight/'):
            logger.info("No directory 'flight' existing yet, creating it")
            os.makedirs('./flight/')
            
        if new_file_path_copy.exists():
            logger.info(f"The file « {new_file_path_copy.name} » has already been uploaded")
            reply =  QMessageBox.question(
            self,
            "File already existing",
            f"The file « {new_file_path_copy.name} » has already been uploaded\n"
            "Do you want to overwrite it ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

            if reply != QMessageBox.StandardButton.Yes:
                logger.info("Upload aborted")
                self.lineEdit_file_path.clear()
                self.pushButton_generate_vva.setEnabled(False)
                return  
        
        try:
            shutil.copy2(self.new_file_path, new_file_path_copy)
            logger.info("File copied")
            self.new_file_path = new_file_path_copy
            self.pushButton_generate_vva.setEnabled(True)
        except shutil.SameFileError:
            logger.info("Source and destination represent the same file.")
        except PermissionError:
            logger.info("Permission denied.")
        except FileNotFoundError:
            logger.info("Source file not found.")
        except Exception as e:
            logger.info(f"An error occurred: {e}")
        

    def on_button_generate_vva(self):
        if self.new_file_path.suffix == ".csv":
            #self.csv2vva(self.new_file_path)
            logger.info("Converting .csv file to .vva")
        elif self.new_file_path.suffix == ".IGC":
            self.igc2vva(self.new_file_path)
            logger.info("Converting .igc file to .vva")
        else:
            logger.info(f"{self.new_file_path.suffix} files are not supported on version {SOFTWARE_VERSION}")
            return
    
    # def csv2vva(self, filepath):
        
    #     with open(filepath, "r", encoding="utf-8") as file:
            
        
        
    def igc2vva(self, igc_filepath):
        vv_vva = VVA_VERSION
        vv_sn = None
        vv_hw = None 
        vv_fw = None
        pilot = None
        date = None
        hour = None
        altitude_max = None
        alitude_min = None 
        avg_windspeed = None
        avg_winddir = None
        with open(igc_filepath, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
    
                if line.startswith("AXVV"):
                    vv_sn = line[4:]  
                if line.startswith("HFRHWHARDWAREVERSION"):
                    vv_hw= line.split(":")[1]
                if line.startswith("HFRFWFIRMWAREVERSION"):
                    vv_fw= line.split(":")[1]
                if line.startswith("HFPLTPILOTINCHARGE"):
                    pilot= line.split(":")[1]
                if line.startswith("HFDTEDATE"):
                    line= line.split(":")[1]
                    date= line.split(",")[0]
                if vv_sn and vv_hw and vv_fw and pilot and date != None :
                    break 
            
            gps_altitude = []
            windspeed = []
            winddir = []
            for line in file:
                line = line.strip()
                
                if line.startswith("B"):
                    gps_altitude.append(int(line[-5:]))
                    lxvv_line = next(file, None)
                    wind_index = lxvv_line.index('W')
                    windspeed.append(int(str(lxvv_line[wind_index+1 : wind_index+3])))
                    winddir.append(int(str(lxvv_line[wind_index+4 : wind_index+7])))
            altitude_max = max(gps_altitude)
            altitude_min = min(gps_altitude)
            avg_winddir = sum(winddir) / len(winddir)
            avg_windspeed = sum(windspeed) / len(windspeed)
        
        vva_path = igc_filepath.with_suffix(igc_filepath.suffix + ".vva")


        with open(vva_path, "w", encoding="utf-8") as f:
            try :
                f.write(f"VV_VVA:{vv_vva}\n")
                f.write(f"VV_SN:{vv_sn}\n")
                f.write(f"VV_HW:{vv_hw}\n")
                f.write(f"VV_FW:{vv_fw}\n")
                f.write(f"pilot:{pilot}\n")
                f.write(f"date:{date}\n")
                f.write(f"hour:{hour}\n")
                f.write(f"altitude_max:{altitude_max}\n")
                f.write(f"altitude_min:{altitude_min}\n")
                f.write(f"avg_windspeed:{avg_windspeed}\n")
                f.write(f"avg_winddir:{avg_winddir}\n")

            except Exception as e:
                 logger.info(f"An error occurred: {e}")
                
                
        
    
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