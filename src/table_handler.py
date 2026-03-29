#import time
import os
import shutil
import pyqtgraph as pg
from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtWidgets import QApplication, QLineEdit, QWidget, QVBoxLayout,QTableWidgetItem ,QButtonGroup , QPushButton, QHBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPen, QBrush
from logging_handler import QTextEditLogger, logger
from file_handler import igc2vva, csv2vva, generate_vva, load_vva_files
from moulinette import fetch_raw_csv, fetch_raw_igc
import sys
from pathlib  import Path 
from units import get_unit

def update_vva_table(data, table_widget):
    
    table_widget.blockSignals(True)
    table_widget.setRowCount(0)

    for row, flight in enumerate(data):
        table_widget.insertRow(row)

        checkbox_item = QtWidgets.QTableWidgetItem()
        checkbox_item.setFlags(
        Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        checkbox_item.setCheckState(Qt.CheckState.Unchecked)
        table_widget.setItem(row, 0, checkbox_item)
        table_widget.setItem(row, 1, QtWidgets.QTableWidgetItem(flight["metadata"]["date"]))
        table_widget.setItem(row, 2, QtWidgets.QTableWidgetItem(str(flight["metadata"]["altitude_start"])))
        table_widget.setItem(row, 3, QtWidgets.QTableWidgetItem(str(flight["metadata"]["altitude_max"])))
        table_widget.setItem(row, 4, QtWidgets.QTableWidgetItem(str(flight["metadata"]["pilot"])))
        table_widget.setItem(row, 5, QtWidgets.QTableWidgetItem(str(flight["metadata"]["comment"])))
        
    table_widget.resizeColumnsToContents()
    table_widget.blockSignals(False)
    return
    
def delete_table_entries(data, table_widget):
    rows_to_remove = []
    for row in range(table_widget.rowCount()):
        checkbox_item = table_widget.item(row, 0)  
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

def update_table_button_state(table_widget, flight, export_button_csv, delete_button, analyze_button, export_button_ge , tab_list, tab_widget):
    """
    This function disables all the buttons when no flight is selected
    It enables the export buttons when all the flight selected are analyzed 
    It enables the other tabs when all the flight selected are analyzed 
    """
    all_processed = False
    at_least_one_processed = False
    selected_row = []
    #BUTTONS
    for row in range(table_widget.rowCount()):
        checkbox_item = table_widget.item(row, 0)  # colonne checkbox
        if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
            selected_row.append(row)
            
    if not selected_row:
        export_button_csv.setEnabled(False)
        delete_button.setEnabled(False)
        analyze_button.setEnabled(False)
        export_button_ge.setEnabled(False)
    else : 
    
        delete_button.setEnabled(True)
        analyze_button.setEnabled(True)
    
    all_processed = all(flight[row]["is_data_processed"] for row in selected_row)
    export_button_csv.setEnabled(all_processed)
    export_button_ge.setEnabled(all_processed)     
    
    ##TABS
    at_least_one_processed = any(flight[row]["is_data_processed"] for row, data in enumerate(flight))
    for tab in tab_list:
        index = tab_widget.indexOf(tab)
        tab_widget.setTabEnabled(index, at_least_one_processed)
    
        
def return_selected_row(data, table_widget):
    rows_selected = []
    for row in range(table_widget.rowCount()):
        checkbox_item = table_widget.item(row, 0)  
        if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
            rows_selected.append(row)
    if len(rows_selected) == 0:
        logger.info("No rows selected")
        return
    
    return rows_selected

def create_polar_table(flight_dic, table_widget, combobox_flight):
    """
    Display and create the table when a flight is selected into the polar tab
    The rows display Vx, Vz , Glide and IAS 
    """
    table_widget.setRowCount(0)  # Clear the table
    table_widget.setHorizontalHeaderLabels([f"Vx {get_unit('IAS')}", f"Vz {get_unit('IAS')}", "Glide", f"IAS {get_unit('IAS')}"])
    for i, flight in enumerate(flight_dic):
        if flight['file_name'].split(".")[0] == combobox_flight.currentText():
            for row, roi_data in enumerate(flight['plot']['roi_polar']):
                table_widget.insertRow(row)
                
                vx_item = QTableWidgetItem(str(roi_data[2]))
                vx_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                table_widget.setItem(row, 0, vx_item)
                
                vz_item = QTableWidgetItem(str(roi_data[3]))
                vz_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                table_widget.setItem(row, 1, vz_item)
                
                glide_item = QTableWidgetItem(str(roi_data[4]))
                glide_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                table_widget.setItem(row, 2, glide_item)
                
                
                
    
    

