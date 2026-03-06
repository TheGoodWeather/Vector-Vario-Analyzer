#import time
import os
import shutil
from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtWidgets import QApplication, QLineEdit, QWidget, QVBoxLayout,QTableWidgetItem ,QButtonGroup , QPushButton, QHBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPen, QBrush
from logging_handler import QTextEditLogger, logger
from file_handler import igc2vva, csv2vva, generate_vva, load_vva_files
from table_handler import update_vva_table, delete_table_entries, update_table_button_state, analyze_table_entries
from PyQt6.QtCore import QThread
from moulinette_worker import MoulinetteWorker

import sys
from pathlib  import Path 
 
SOFTWARE_VERSION = "1.0.0"

class MainWindow(QtWidgets.QMainWindow):

    
    def __init__(self):
        super(MainWindow, self).__init__()
    
        uic.loadUi(self.resource_path("gui/mainwindow.ui"), self)  # Load the .ui file directly
        
        
        self.setWindowTitle(f"Vector Vario Software Utility v{SOFTWARE_VERSION}")
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
        self.pushButton_delete_entry.clicked.connect(self.on_button_delete_entries)
        self.pushButton_analyze_entry.clicked.connect(self.on_button_analyze_entries)
        
        self.logbox_handler = QTextEditLogger(self.textEdit_log)
        self.textEdit_log.verticalScrollBar().setValue(self.textEdit_log.verticalScrollBar().maximum())
        logger.addHandler(self.logbox_handler) 
        
        
        #Table ------------------------------------
        headers = ["","Flight date", "Start altitude","Max altitude", "Pilot", "Comment"]
        self.button_list_table = [self.pushButton_delete_entry,self.pushButton_analyze_entry,self.pushButton_export_entry_ge,self.pushButton_export_entry_csv]
        for button in self.button_list_table: #Disable table buttons
            button.setEnabled(False)
        self.tableWidget_database.setColumnCount(len(headers))
        self.tableWidget_database.setHorizontalHeaderLabels(headers)
        self.tableWidget_database.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidget_database.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableWidget_database.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_database.resizeColumnsToContents()
        self.tableWidget_database.itemChanged.connect(lambda: update_table_button_state(self.tableWidget_database, self.button_list_table))

        
        self.flight = load_vva_files()  #scan and load data from flight dir  # This variable contains all the data and metadata from flights 
        update_vva_table(self.flight, self.tableWidget_database)
        
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
        self.lineEdit_comment.clear()
        
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
            generate_vva(self.new_file_path, csv2vva(self.new_file_path, self.lineEdit_comment))
            logger.info("Converting .csv file to .vva")
        elif self.new_file_path.suffix == ".IGC":
            generate_vva(self.new_file_path, igc2vva(self.new_file_path, self.lineEdit_comment))
            logger.info("Converting .igc file to .vva")
        else:
            logger.info(f"{self.new_file_path.suffix} files are not supported on version {SOFTWARE_VERSION}")
            return
        
        self.flight = load_vva_files()
        update_vva_table(self.flight, self.tableWidget_database)
        update_table_button_state(self.tableWidget_database, self.button_list_table)
        
    
    def on_button_clear_log(self):
        self.textEdit_log.clear()
        return
    
    def on_button_delete_entries(self):
        reply =  QMessageBox.question(
        self,
        "Warning",
        "The source files will be deleted from the database.\n"
        "Are you sure to proceed ?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No
        )
    
        if reply != QMessageBox.StandardButton.Yes:
            logger.info("File deletion aborted")
            return  
        delete_table_entries(self.flight, self.tableWidget_database)
        update_table_button_state(self.tableWidget_database, self.button_list_table)
        return
    
    def on_button_analyze_entries(self):
        analyze_table_entries(self.flight, self.tableWidget_database)
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