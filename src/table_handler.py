#import time
import os
import shutil
import pyqtgraph as pg
from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtWidgets import QApplication, QLineEdit, QWidget, QVBoxLayout,QTableWidgetItem ,QButtonGroup , QPushButton, QHBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPen, QBrush
from logging_handler import QTextEditLogger, logger
from file_handler import igc2vva, csv2vva, generate_vva, load_vva_files, save_alias_comment_to_vva
from moulinette import fetch_raw_csv, fetch_raw_igc
import sys
import numpy as np
from pathlib  import Path 
from units import get_unit, convert_array_to_unit
from utils import get_label

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
        table_widget.setItem(row, 1, QtWidgets.QTableWidgetItem(str(flight["file_name"].split('.')[0])))
        table_widget.setItem(row, 2, QtWidgets.QTableWidgetItem(flight["metadata"]["date"]))
        table_widget.setItem(row, 3, QtWidgets.QTableWidgetItem(str(flight["metadata"]["altitude_start"])))
        table_widget.setItem(row, 4, QtWidgets.QTableWidgetItem(str(flight["metadata"]["altitude_max"])))
        table_widget.setItem(row, 5, QtWidgets.QTableWidgetItem(str(flight["metadata"]["pilot"])))
        
        item_comment =  QtWidgets.QTableWidgetItem(str(flight["metadata"]["comment"]))
        item_comment.setFlags(Qt.ItemFlag.ItemIsEnabled |Qt.ItemFlag.ItemIsSelectable |Qt.ItemFlag.ItemIsEditable)
        table_widget.setItem(row, 6,item_comment)
        
        item_alias = QtWidgets.QTableWidgetItem(str(flight["metadata"]["alias"]))
        item_alias.setFlags(Qt.ItemFlag.ItemIsEnabled |Qt.ItemFlag.ItemIsSelectable |Qt.ItemFlag.ItemIsEditable)
        table_widget.setItem(row, 7, item_alias)
        
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
        if flight['file_name'].split(".")[0] == combobox_flight.currentText() or flight['metadata']['alias'] == combobox_flight.currentText() :
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
                
                
                
    
def save_comment_alias(item, flight_dic, table_widget):
    if item.column() not in [6, 7]:
       return
   
    flight_selected = table_widget.item(item.row(), 1).text()

    for flight in flight_dic:
        if flight['file_name'].split(".")[0] == flight_selected or flight['metadata']['alias'] == flight_selected :
            
            new_value = item.text()

            if item.column() == 6:  # comment
                flight["metadata"]["comment"] = new_value
        
            elif item.column() == 7:  # alias
                flight["metadata"]["alias"] = new_value    
            
            save_alias_comment_to_vva(flight['file_path'], flight["metadata"]["comment"], flight["metadata"]["alias"])
            return
            
        
def populate_table_1D_variable(flight_dic, table1, table2, choice):
    table1.blockSignals(True)
    table2.blockSignals(True)

    table1.setRowCount(0)   
    table2.setRowCount(0)  

    row = 0

    for flight in flight_dic:
        if (flight['file_name'].split(".")[0] == choice) or (flight['metadata']['alias'] == choice):
            if flight['is_data_processed'] and flight['data']:

                for variable in flight['data']:
                    if variable != 'GNSS_time':                       
                        data = flight['data'][variable]

                        if len(data) > 0 and not np.all(np.isnan(data)):

                            table1.insertRow(row)
                            table2.insertRow(row)

                            # TABLE 1
                            item1 = QTableWidgetItem(variable)
                            item1.setFlags(item1.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                            item1.setFlags(item1.flags() & ~Qt.ItemFlag.ItemIsEditable)
                            item1.setCheckState(Qt.CheckState.Unchecked)

                            # TABLE 2
                            item2 = QTableWidgetItem(variable)
                            item2.setFlags(item2.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                            item2.setFlags(item2.flags() & ~Qt.ItemFlag.ItemIsEditable)
                            item2.setCheckState(Qt.CheckState.Unchecked)

                            table1.setItem(row, 0, item1)
                            table2.setItem(row, 0, item2)

                            row += 1            
    
    table1.blockSignals(False)
    table2.blockSignals(False)
    



