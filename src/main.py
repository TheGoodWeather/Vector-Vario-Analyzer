#import time
import os
import shutil
from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtWidgets import QListWidgetItem, QApplication, QLineEdit, QWidget, QVBoxLayout,QTableWidgetItem ,QButtonGroup , QPushButton, QHBoxLayout, QFileDialog, QMessageBox, QMainWindow
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize
from PyQt6.QtGui import QColor, QPen, QBrush
from logging_handler import QTextEditLogger, logger
from file_handler import igc2vva, csv2vva, generate_vva, load_vva_files
from table_handler import update_vva_table, delete_table_entries, update_table_button_state, return_selected_row, create_polar_table, on_table_cell_clicked
from PyQt6.QtCore import QThread, QThreadPool, QSettings
from moulinette_worker import MoulinetteWorker
from pyqtgraph import ErrorBarItem 
import pyqtgraph as pg
from export import export_file_csv
import sys
from pathlib  import Path 
import pprint
import numpy as np
from preference_windows import UnitDialog
import plot 

SOFTWARE_VERSION = "1.0.0"

class MainWindow(QtWidgets.QMainWindow):

    
    def __init__(self):
        super(MainWindow, self).__init__()
    
        uic.loadUi(self.resource_path("gui/mainwindow.ui"), self)  # Load the .ui file directly
        self.unit_dialog = UnitDialog(parent = self)  
        self.unit_dialog.unitsChanged.connect(lambda: plot.update_1D_plot(self.flight, self.comboBox_flight_tab1D, self.listWidget_variable_plot1, self.graph1_tab1D))
        self.unit_dialog.unitsChanged.connect(lambda: plot.update_1D_plot(self.flight, self.comboBox_flight_tab1D, self.listWidget_variable_plot2, self.graph2_tab1D))
        self.unit_dialog.unitsChanged.connect(lambda : plot.update_polartab_timeserie_plot(self.flight, self.comboBox_flight_select_polartab, self.comboBox_variable_select_polartab, self.graph_tabpolar_timeserie))
        self.settings = QSettings("Vector Vario", "VVA") #Initialize settings
        self.threadpool = QThreadPool() #initialize thread
        # To manage export threads sequentially 
        self.analyze_queue = []
        self.analyze_running = False
        
        self.setWindowTitle(f"Vector Vario Software Utility v{SOFTWARE_VERSION}")
        self.setFocus()  #allow the main windows to receive key press event 
        self.read_settings_main()
        
        self.new_file_path = None 
        
        
        
        """
        Widgets Menu Bar
        """
        
        self.actionUnits.triggered.connect(self.display_unit_window)
        
        """
        Widgets tab import  / export
        """
        
        self.pushButton_generate_vva.setEnabled(False)
        
        self.pushButton_load_file.clicked.connect(self.on_button_load_file)
        self.pushButton_generate_vva.clicked.connect(self.on_button_generate_vva)
        self.pushButton_clear_log.clicked.connect(self.on_button_clear_log)
        self.pushButton_delete_entry.clicked.connect(self.on_button_delete_entries)
        self.pushButton_analyze_entry.clicked.connect(self.on_button_analyze_entries)
        self.pushButton_export_entry_csv.clicked.connect(self.on_button_export_entries_csv)
        
        self.logbox_handler = QTextEditLogger(self.textEdit_log)
        self.textEdit_log.verticalScrollBar().setValue(self.textEdit_log.verticalScrollBar().maximum())
        logger.addHandler(self.logbox_handler) 
        
        #initialize progress bar to 0
        self.progressBar.setValue(0)
        
        #Table ------------------------------------
        headers = ["","Flight date", "Start altitude","Max altitude", "Pilot", "Comment"]
        self.tab_list = [self.oneDplotter_tab,self.twoDplotter_tab,self.polar_tab,self.atmo_tab, self.dynamic_tab]
        for tab in self.tab_list:
            index = self.tabWidget.indexOf(tab)
            self.tabWidget.setTabEnabled(index, False)
        self.tableWidget_database.setColumnCount(len(headers))
        self.tableWidget_database.setHorizontalHeaderLabels(headers)
        self.tableWidget_database.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidget_database.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableWidget_database.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_database.resizeColumnsToContents()
        self.tableWidget_database.itemChanged.connect(lambda : update_table_button_state(self.tableWidget_database,self.flight, self.pushButton_export_entry_csv, self.pushButton_delete_entry, self.pushButton_analyze_entry, self.pushButton_export_entry_ge, self.tab_list, self.tabWidget))

        
        self.flight = load_vva_files()  #scan and load data from flight dir  # This variable contains all the data and metadata from flights 
        update_vva_table(self.flight, self.tableWidget_database)
        
        """
        Widgets tab 1D plot
        """
        self.graph1_tab1D.setBackground("w")
        self.graph1_tab1D.setLabel('left', 'No variable selected')
        self.graph1_tab1D.setLabel('bottom', 'GNSS Time (s)')
        self.graph1_tab1D.setTitle("Select a variable to plot in time")
        self.graph1_tab1D.showGrid(x=True, y=True, alpha=0.3)
        self.graph1_tab1D.setEnabled(True)
        
        self.graph2_tab1D.setBackground("w")
        self.graph2_tab1D.setLabel('left', 'No variable selected')
        self.graph2_tab1D.setLabel('bottom', 'GNSS Time (s)')
        self.graph2_tab1D.setTitle("Select a variable to plot in time")
        self.graph2_tab1D.showGrid(x=True, y=True, alpha=0.3)
        self.graph2_tab1D.setEnabled(True)
        
        self.comboBox_flight_tab1D.currentTextChanged.connect(lambda choice: self.populate_combobox_1D_variable(self.flight, self.listWidget_variable_plot1, self.listWidget_variable_plot2, choice))
        self.comboBox_flight_tab1D.currentTextChanged.connect(lambda: plot.clear_plots_1D(self.graph1_tab1D, self.graph2_tab1D))
        self.comboBox_flight_tab1D.currentTextChanged.connect(lambda: plot.restore_checked_variables_1D(self.flight, self.comboBox_flight_tab1D, self.listWidget_variable_plot1, self.listWidget_variable_plot2))
        self.comboBox_flight_tab1D.currentTextChanged.connect(lambda: plot.restore_checked_variables_1D(self.flight, self.comboBox_flight_tab1D, self.listWidget_variable_plot1 , self.listWidget_variable_plot2))

        self.listWidget_variable_plot1.itemChanged.connect(lambda: self.handle_checkboxes_on_widgetlist_1D(self.listWidget_variable_plot1))
        self.listWidget_variable_plot1.itemChanged.connect(lambda: plot.save_checked_variables_1D(self.flight, self.comboBox_flight_tab1D, self.listWidget_variable_plot1, self.listWidget_variable_plot2))
        self.listWidget_variable_plot2.itemChanged.connect(lambda: self.handle_checkboxes_on_widgetlist_1D(self.listWidget_variable_plot2))
        self.listWidget_variable_plot1.itemChanged.connect(lambda: plot.update_1D_plot(self.flight, self.comboBox_flight_tab1D, self.listWidget_variable_plot1, self.graph1_tab1D))
        self.listWidget_variable_plot2.itemChanged.connect(lambda: plot.save_checked_variables_1D(self.flight, self.comboBox_flight_tab1D, self.listWidget_variable_plot1, self.listWidget_variable_plot2))
        self.listWidget_variable_plot2.itemChanged.connect(lambda: plot.update_1D_plot(self.flight, self.comboBox_flight_tab1D, self.listWidget_variable_plot2, self.graph2_tab1D))
        self.checkBox_x_axis_link.stateChanged.connect(lambda: plot.toggle_x_link(self.graph1_tab1D, self.graph2_tab1D, self.checkBox_x_axis_link))
        
        """
        Widgets tab 2D plot
        """
        self.checkboxes_variables_plot2D = [self.checkBox_altitude_plot2D, self.checkBox_LCL_plot2D, self.checkBox_temp_plot2D, self.checkBox_hum_plot2D]
        
        self.graph_tab2D.setBackground("w")
        self.graph_tab2D.setLabel("left", "Latitudes")
        self.graph_tab2D.setLabel("bottom", "Longitudes")
        self.graph_tab2D.addLegend()
        self.graph_tab2D.showGrid(x=True, y=True, alpha=0.3)
        self.graph_tab2D.setEnabled(True)
        self.colorbar = pg.ColorBarItem(values=(0, 1),width=10,colorMap=pg.colormap.get('turbo'), interactive=False, orientation='horizontal')
        self.color_gradient_bar_widget.addItem(self.colorbar)
        self.color_gradient_bar_widget.setBackground("w")
        self.colorbar.setOpacity(0) 
        
        #signals
        self.listWidget_flights_plot2D.itemChanged.connect(lambda: plot.update_2D_plot(self.flight, None, None,self.listWidget_flights_plot2D , self.graph_tab2D ,self.colorbar))
        self.listWidget_flights_plot2D.itemChanged.connect(lambda: self.reset_checkboxes_color_variable(self.checkboxes_variables_plot2D, self.checkBox_windbarbs, self.colorbar))
        self.listWidget_flights_plot2D.itemChanged.connect(lambda: plot.update_wind_barbs_2D(self.flight, self.listWidget_flights_plot2D, self.graph_tab2D, self.checkBox_windbarbs, self.horizontalSlider_reswind, self.horizontalSlider_reswind.value()))
        self.checkBox_altitude_plot2D.stateChanged.connect(lambda: plot.update_2D_plot(self.flight, self.checkBox_altitude_plot2D, 'GNSS_alt',self.listWidget_flights_plot2D , self.graph_tab2D, self.colorbar))
        self.checkBox_hum_plot2D.stateChanged.connect(lambda: plot.update_2D_plot(self.flight, self.checkBox_hum_plot2D, 'air_RH',self.listWidget_flights_plot2D , self.graph_tab2D, self.colorbar))
        self.checkBox_temp_plot2D.stateChanged.connect(lambda: plot.update_2D_plot(self.flight, self.checkBox_temp_plot2D, 'air_T', self.listWidget_flights_plot2D , self.graph_tab2D, self.colorbar))
        self.checkBox_LCL_plot2D.stateChanged.connect(lambda: plot.update_2D_plot(self.flight, self.checkBox_LCL_plot2D, 'LCL', self.listWidget_flights_plot2D , self.graph_tab2D, self.colorbar))
        self.checkBox_altitude_plot2D.stateChanged.connect(lambda: self.handle_checkboxes_color_variable(self.checkboxes_variables_plot2D,  self.checkBox_windbarbs,self.listWidget_flights_plot2D))
        self.checkBox_hum_plot2D.stateChanged.connect(lambda: self.handle_checkboxes_color_variable(self.checkboxes_variables_plot2D,  self.checkBox_windbarbs,self.listWidget_flights_plot2D))
        self.checkBox_LCL_plot2D.stateChanged.connect(lambda: self.handle_checkboxes_color_variable(self.checkboxes_variables_plot2D,  self.checkBox_windbarbs,self.listWidget_flights_plot2D))
        self.checkBox_temp_plot2D.stateChanged.connect(lambda: self.handle_checkboxes_color_variable(self.checkboxes_variables_plot2D, self.checkBox_windbarbs, self.listWidget_flights_plot2D))
        self.checkBox_altitude_plot2D.stateChanged.connect(lambda: plot.update_wind_barbs_2D(self.flight, self.listWidget_flights_plot2D, self.graph_tab2D, self.checkBox_windbarbs, self.horizontalSlider_reswind, self.horizontalSlider_reswind.value()))
        self.checkBox_hum_plot2D.stateChanged.connect(lambda: plot.update_wind_barbs_2D(self.flight, self.listWidget_flights_plot2D, self.graph_tab2D, self.checkBox_windbarbs, self.horizontalSlider_reswind, self.horizontalSlider_reswind.value()))
        self.checkBox_temp_plot2D.stateChanged.connect(lambda: plot.update_wind_barbs_2D(self.flight, self.listWidget_flights_plot2D, self.graph_tab2D, self.checkBox_windbarbs, self.horizontalSlider_reswind, self.horizontalSlider_reswind.value()))
        self.checkBox_LCL_plot2D.stateChanged.connect(lambda: plot.update_wind_barbs_2D(self.flight, self.listWidget_flights_plot2D, self.graph_tab2D, self.checkBox_windbarbs, self.horizontalSlider_reswind, self.horizontalSlider_reswind.value()))
        self.checkBox_windbarbs.stateChanged.connect(lambda: plot.update_wind_barbs_2D(self.flight, self.listWidget_flights_plot2D, self.graph_tab2D, self.checkBox_windbarbs, self.horizontalSlider_reswind, self.horizontalSlider_reswind.value()))
        self.horizontalSlider_reswind.valueChanged.connect(lambda: plot.update_wind_barbs_2D(self.flight, self.listWidget_flights_plot2D, self.graph_tab2D, self.checkBox_windbarbs, self.horizontalSlider_reswind, self.horizontalSlider_reswind.value()) )
    
    
        """
        Widgets tab POLAR
        """
        self.tableView_polar_points.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableView_polar_points.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tableView_polar_points.cellClicked.connect(lambda row, column: on_table_cell_clicked(row, self.flight, self.comboBox_flight_select_polartab, self.tableView_polar_points, self.graph_tabpolar_timeserie, self.graph_tabpolar_vxvz, self.pushButton_remove_polar_point))
        self.graph_tabpolar_vxvz.setBackground("w")
        self.graph_tabpolar_vxvz.setLabel('left', 'Vz (m/s)')
        self.graph_tabpolar_vxvz.setLabel('bottom', 'Vx (m/s)')
        self.graph_tabpolar_vxvz.setTitle("Vx vs Vz")
        self.graph_tabpolar_vxvz.showGrid(x=True, y=True, alpha=0.3)
        self.graph_tabpolar_vxvz.setEnabled(True)
        self.graph_tabpolar_timeserie.setBackground("w")
        self.graph_tabpolar_timeserie.setLabel("bottom", "Sample")
        self.graph_tabpolar_timeserie.addLegend()
        self.graph_tabpolar_timeserie.showGrid(x=True, y=True, alpha=0.3)
        self.graph_tabpolar_timeserie.setEnabled(True)
        self.comboBox_flight_select_polartab.currentTextChanged.connect(lambda choice: self.populate_combobox_polar_variable(self.flight, self.comboBox_variable_select_polartab, choice))
        self.comboBox_flight_select_polartab.currentTextChanged.connect(lambda: plot.clear_plots_1D(self.graph_tabpolar_timeserie, None))
        self.comboBox_flight_select_polartab.currentTextChanged.connect(lambda:plot.update_polartab_timeserie_plot(self.flight, self.comboBox_flight_select_polartab, self.comboBox_variable_select_polartab, self.graph_tabpolar_timeserie))
        self.comboBox_variable_select_polartab.currentTextChanged.connect(lambda : plot.update_polartab_timeserie_plot(self.flight, self.comboBox_flight_select_polartab, self.comboBox_variable_select_polartab, self.graph_tabpolar_timeserie))
        self.comboBox_variable_select_polartab.currentTextChanged.connect(lambda : plot.display_rois(self.flight, self.graph_tabpolar_timeserie, self.comboBox_flight_select_polartab))
        self.comboBox_flight_select_polartab.currentTextChanged.connect(lambda : plot.display_rois(self.flight, self.graph_tabpolar_timeserie, self.comboBox_flight_select_polartab))
        self.comboBox_flight_select_polartab.currentTextChanged.connect(lambda : plot.reset_highlights(self.flight, self.graph_tabpolar_vxvz ))
        self.comboBox_flight_select_polartab.currentTextChanged.connect(lambda :create_polar_table(self.flight, self.tableView_polar_points, self.comboBox_flight_select_polartab))
        self.pushButton_add_polar_point.clicked.connect(lambda : plot.create_roi(self.flight,self.graph_tabpolar_timeserie, self.graph_tabpolar_vxvz, self.tableView_polar_points, self.comboBox_flight_select_polartab))
        self.pushButton_add_polar_point.clicked.connect(lambda : create_polar_table(self.flight, self.tableView_polar_points, self.comboBox_flight_select_polartab))
        

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
    def write_settings_main(self):
        """
        This function will be called when the main window is closed. 
        It will record every parameters (geometry) as QSettings to be retrieved 
        at every starts

        """
        self.settings.beginGroup("geometry")
        self.settings.setValue("pos", self.pos())
        self.settings.setValue("size", self.size())
        self.settings.endGroup()
        
    def read_settings_main(self):
 
        self.settings.beginGroup("geometry")
        self.move(self.settings.value("pos", defaultValue=QPoint(50, 50)))
        self.resize(self.settings.value("size" , defaultValue=QSize(400, 200)))
        self.settings.endGroup()
        
    def closeEvent(self, event):
        self.write_settings_main()
        super().closeEvent(event)
        event.accept()
        
        
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
        

    def on_button_generate_vva(self, widget_):
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
        update_table_button_state(self.tableWidget_database,self.flight, self.pushButton_export_entry_csv, self.pushButton_delete_entry, self.pushButton_analyze_entry, self.pushButton_export_entry_ge, self.tab_list, self.tabWidget)
        self.populate_combobox_flight(self.flight, self.comboBox_flight_tab1D)
        self.populate_combobox_flight(self.flight, self.comboBox_flight_select_polartab)
        self.populate_flight_list_tab_2D(self.flight, self.listWidget_flights_plot2D)
        
        self.lineEdit_file_path.clear()
        self.lineEdit_comment.clear()
        
        
        
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
        update_table_button_state(self.tableWidget_database,self.flight, self.pushButton_export_entry_csv, self.pushButton_delete_entry, self.pushButton_analyze_entry, self.pushButton_export_entry_ge, self.tab_list, self.tabWidget)
        self.populate_combobox_flight(self.flight, self.comboBox_flight_tab1D)
        self.populate_combobox_flight(self.flight, self.comboBox_flight_select_polartab)
        self.populate_flight_list_tab_2D(self.flight, self.listWidget_flights_plot2D)
        return
    
    def on_button_analyze_entries(self):
        """
        This function can handle multiple analysis through threads . It waits for the previous analysis to finish before 
        starting the next one
        """
        row_to_analyze = return_selected_row(self.flight, self.tableWidget_database)
        if not row_to_analyze:
            return 
        self.analyze_queue = row_to_analyze.copy()
        
        if not self.analyze_running: #If the analyze hasn't started yet
            self.start_next_analysis_thread(self.pushButton_analyze_entry)
            
        
    
    def start_next_analysis_thread(self, button_analyse):
        
        if not self.analyze_queue: #if the queue is empty
            self.analyze_running = False 
            logger.info("Analysis done")
            button_analyse.setEnabled(True)
            self.populate_combobox_flight(self.flight, self.comboBox_flight_tab1D)
            self.populate_combobox_flight(self.flight, self.comboBox_flight_select_polartab)
            self.populate_flight_list_tab_2D(self.flight, self.listWidget_flights_plot2D)
            return
        

        self.analyze_running = True #Starting analysis 
        button_analyse.setEnabled(False)
        row = self.analyze_queue.pop(0)
        
        worker = MoulinetteWorker(self.flight[row])

        worker.signals.progress.connect(self.update_progress_bar)
        worker.signals.finished.connect(self.analysis_finished)
        worker.signals.error.connect(self.analysis_error)

        self.threadpool.start(worker)
    
    def update_progress_bar(self, value):
        self.progressBar.setValue(value)
       
    def analysis_finished(self, flight_dic):
        logger.info(f"Finished {flight_dic['file_name']}")
        flight_dic["is_data_processed"] = True 
        update_table_button_state(self.tableWidget_database,self.flight, self.pushButton_export_entry_csv, self.pushButton_delete_entry, self.pushButton_analyze_entry, self.pushButton_export_entry_ge, self.tab_list, self.tabWidget)
        self.start_next_analysis_thread(self.pushButton_analyze_entry)
       
        
    def analysis_error(self, msg):
        logger.error(f"Error while analyzing data : {msg}")
        
        
    def on_button_export_entries_csv(self):
        
        row_to_export = return_selected_row(self.flight, self.tableWidget_database)
        for row in row_to_export:
            export_file_csv(self.flight[row])
            
    def populate_combobox_flight(self, data, combo_box_flight):
        """
        Set the flights that has been analyzed into the specified combobox. Used in 1D plot and Polar tab

        """
        #first we remove all the items in the combobox 
        combo_box_flight.clear()
        self.set_colors_to_flights(data) # We set a color to each flight here because the analyze has to be finished before setting new color trust me

        for row, flight in enumerate(data):
            original_filename = Path(flight['file_name'])
            original_filename_wo_extension = original_filename.with_suffix("")
            original_filename_wo_extension = str(original_filename_wo_extension.with_suffix(""))
            if combo_box_flight.findText(original_filename_wo_extension) >= 0 and not flight['is_data_processed'] :
                combo_box_flight.removeItem(combo_box_flight.findText(original_filename_wo_extension))
            elif flight['is_data_processed'] and combo_box_flight.findText(original_filename_wo_extension) < 0:
                combo_box_flight.addItem(f"{original_filename_wo_extension}")
                
    def populate_combobox_1D_variable(self, flight_dic, list1, list2, choice):
        # list1.blockSignals(True)
        # list2.blockSignals(True)
        list1.clear()
        list2.clear()
        for row, flight in enumerate(flight_dic):
            if flight['file_name'].split(".")[0] == choice:
                if flight['is_data_processed'] and flight['data']:
                    for index, variable in enumerate(flight['data']):
                        if variable != 'GNSS_time':                       
                            if len(flight['data'][variable]) > 0 and not np.all(np.isnan(flight['data'][variable])):
                                item1 = QListWidgetItem(variable)
                                item1.setFlags(
                                    item1.flags() | Qt.ItemFlag.ItemIsUserCheckable
                                )
                            
                                item1.setCheckState(Qt.CheckState.Unchecked)
                                
                                item2 = QListWidgetItem(variable)
                                item2.setFlags(
                                    item2.flags() | Qt.ItemFlag.ItemIsUserCheckable
                                )
                            
                                item2.setCheckState(Qt.CheckState.Unchecked)
                            
                                list1.addItem(item1)
                                list2.addItem(item2)
                            
            
        # list1.blockSignals(False)
        # list2.blockSignals(False)
        
    def handle_checkboxes_on_widgetlist_1D(self, list_widget):
        """
        This function handles what variables can be displayed on the same graph
        relative to their scale (same group only, max 2 variables)
        """
    
        var_to_unit_group_dic = {
            "heading": ["compass_head", "GNSS_head", "wind_origin"],
            "speed": ["GNSS_speed", "vario", "wind_vel", "IAS", "VarioIAS", "TAS", "netto"],
            "altitude": ["GNSS_alt", "QNS_alt", "LCL"],
            "temperature": ["T_sensor", "air_T", "AirTheta", "AirTd"],
            "angle": ["pitch", "roll"],
            "pressure": ["DP", "P_stat", "AirES", "AirE"]
        }
    

        var_to_group = {
            var: group
            for group, variables in var_to_unit_group_dic.items()
            for var in variables
        }
    
        max_number_plot = 2
    
        list_widget.blockSignals(True)
    
        item_checked = []
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                item_checked.append(item)
    
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setBackground(QBrush(QColor("white")))
    
        if len(item_checked) == 0:
            list_widget.blockSignals(False)
            return
    
        first_var = item_checked[0].text()
        first_group = var_to_group.get(first_var)
        
        
        if first_group is None:
            for i in range(list_widget.count()):
                item = list_widget.item(i)
    
                if item.checkState() != Qt.CheckState.Checked:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                    item.setBackground(QBrush(QColor(240, 240, 240)))
                    item.setToolTip("Variable without unit group → single selection only")
    
            list_widget.blockSignals(False)
            return
    
        if len(item_checked) == 1:
    
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                var = item.text()
    
                if var_to_group.get(var) != first_group: #If the item
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                    item.setBackground(QBrush(QColor(240, 240, 240)))
    
        elif len(item_checked) >= max_number_plot:
    
            for i in range(list_widget.count()):
                item = list_widget.item(i)
    
                if item.checkState() != Qt.CheckState.Checked:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                    item.setBackground(QBrush(QColor(240, 240, 240)))
    
        list_widget.blockSignals(False)
    
    def populate_flight_list_tab_2D(self, flight_dic, widget_list):
        """
        Populating the flight list according to flight that has been already processed

        """
        widget_list.clear()
        for row, flight in enumerate(flight_dic):
            if flight['is_data_processed'] and flight['data']:
                flight_name = str(Path(flight['file_name']).with_suffix("").with_suffix(""))
                item = QListWidgetItem(flight_name)
                item.setFlags(
                    item.flags() | Qt.ItemFlag.ItemIsUserCheckable
                )
                item.setCheckState(Qt.CheckState.Unchecked)
                widget_list.addItem(item)
                
    def handle_checkboxes_color_variable(self, checkbox_list, checkbox_wind, flight_list):
        """
        This function prevent the user to select multiple variables to color the plot, limiting it 
        at one variable.

        """
        sender = self.sender()  # checkbox qui a déclenché le signal
        flight_selected = False
        for i in range(flight_list.count()):
            item = flight_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                flight_selected = True
                break
    
        if not flight_selected:
            checkbox_wind.setChecked(False)
            checkbox_wind.setEnabled(False)
            for checkbox in checkbox_list:
                checkbox.blockSignals(True)
                checkbox.setChecked(False)
                checkbox.setEnabled(False)
                checkbox.blockSignals(False)
            return
    
        for checkbox in checkbox_list:
            checkbox.setEnabled(True)

        if sender.isChecked():
            checkbox_wind.setEnabled(True)
            for checkbox in checkbox_list:
                if checkbox != sender:
                    checkbox.blockSignals(True)
                    checkbox.setChecked(False)
                    checkbox.blockSignals(False)
                    
    def reset_checkboxes_color_variable(self, checkbox_list, checkbox_wind,  colorbar):
        """
        This function enable the checkboxes color variable when a flight is selected in the 
        flight widget list, or disable it when no flight is selected. 

        """
        sender = self.sender()
        flight_selected = False
        for i in range(sender.count()):
            item = sender.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                flight_selected = True
                break
    
        if flight_selected:
            checkbox_wind.setEnabled(True)
            for checkbox in checkbox_list:
                checkbox.blockSignals(True)
                checkbox.setEnabled(True)
                checkbox.blockSignals(False)
        else:
            checkbox_wind.setEnabled(False)
            checkbox_wind.setChecked(False)
            for checkbox in checkbox_list:
                checkbox.blockSignals(True)
                checkbox.setEnabled(False)
                checkbox.setChecked(False)
                checkbox.blockSignals(False)
    
            colorbar.setOpacity(0)
              
  
    def populate_combobox_polar_variable(self, flight_dic, combobox_var, choice):
        
        combobox_var.clear()
        for row, flight in enumerate(flight_dic):
            if flight['file_name'].split(".")[0] == choice:
                if flight['is_data_processed'] and flight['data']:
                    for index, variable in enumerate(flight['data']):
                        if variable == 'IAS' or variable == 'GNSS_alt' :                       
                            if len(flight['data'][variable]) > 0 and not np.all(np.isnan(flight['data'][variable])):
                                combobox_var.addItem(variable)
                                

    def set_colors_to_flights(self, flight_dic):
        for row, flight in enumerate(flight_dic):
            if flight['is_data_processed']: 
                flight['plot']['plot_color'] = plot.colors[row % len(plot.colors)]
        
        
    def display_unit_window(self): #Call the unit window
        
        if self.unit_dialog.isVisible():
            self.unit_dialog.hide()
        else:
            self.unit_dialog.show()

if __name__ == "__main__":
   #try:
    if not QtWidgets.QApplication.instance():
        app = QtWidgets.QApplication(sys.argv)
    else : 
        app = QtWidgets.QApplication.instance() 
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
    # except Exception as e:
    #     print(f"Fatal error {e}")
    #     # logger.exception(f"Fatal error occurred during startup {e}")