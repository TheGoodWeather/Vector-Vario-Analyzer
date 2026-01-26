#import time
import os
import shutil
from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtWidgets import QApplication, QLineEdit, QWidget, QVBoxLayout,QTableWidgetItem ,QButtonGroup , QPushButton, QHBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPen, QBrush
from logging_handler import QTextEditLogger, logger
from file_handler import igc2vva, csv2vva, generate_vva, load_vva_files

import sys
from pathlib  import Path 


def update_vva_table(data, table_widget):
    
    table_widget.blockSignals(True)
    table_widget.setRowCount(0)

    for row, flight in enumerate(data):
        table_widget.insertRow(row)

        checkbox_item = QtWidgets.QTableWidgetItem()
        checkbox_item.setFlags(
        Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        checkbox_item.setCheckState(Qt.CheckState.Unchecked)
        table_widget.setItem(row, 0, QtWidgets.QTableWidgetItem(str(flight["metadata"]["date"])))
        table_widget.setItem(row, 1, checkbox_item)
        table_widget.setItem(row, 2, QtWidgets.QTableWidgetItem(str(flight["metadata"]["hour"])))
        table_widget.setItem(row, 3, QtWidgets.QTableWidgetItem(str(flight["metadata"]["altitude_max"])))
        table_widget.setItem(row, 4, QtWidgets.QTableWidgetItem(str(flight["metadata"]["altitude_min"])))
        table_widget.setItem(row, 5, QtWidgets.QTableWidgetItem(str(flight["metadata"]["avg_winddir"])))
        table_widget.setItem(row, 6, QtWidgets.QTableWidgetItem(str(flight["metadata"]["avg_windspeed"])))
        table_widget.setItem(row, 7, QtWidgets.QTableWidgetItem(str(flight["metadata"]["pilot"])))
        table_widget.setItem(row, 8, QtWidgets.QTableWidgetItem(str(flight["metadata"]["comment"])))
        

    table_widget.resizeColumnsToContents()
    table_widget.blockSignals(False)
    return
    
def delete_table_entries(data, table_widget):
    rows_to_remove = []
    for row in range(table_widget.rowCount()):
        checkbox_item = table_widget.item(row, 1)  
        if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
            rows_to_remove.append(row)
    if len(rows_to_remove) == 0:
        logger.info("Nothing to delete")
        return
            
    for row in reversed(rows_to_remove):
        logger.info(f"files {data[row]['file_name']} deleted")
        table_widget.removeRow(row)
        data[row]["file_path"].unlink() # delete source file 
        data[row]["origin_file_path"].unlink() # delete source file 
        data.pop(row)
    return

def update_table_button_state(table_widget, button_list):
    for row in range(table_widget.rowCount()):
        checkbox_item = table_widget.item(row, 1)  # colonne checkbox
        if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
            for button in button_list:
                button.setEnabled(True)
            return
        
    for button in button_list:
        button.setEnabled(False)
