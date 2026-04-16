#import time
import os
import shutil
from pyqtgraph_gis import MapWidget
from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtWidgets import QListWidgetItem,QComboBox, QHeaderView, QRadioButton, QApplication, QLineEdit, QWidget, QVBoxLayout,QTableWidgetItem ,QButtonGroup , QPushButton, QHBoxLayout, QFileDialog, QMessageBox, QMainWindow
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize
from PyQt6.QtGui import QColor, QPen, QBrush
from logging_handler import QTextEditLogger, logger
from file_handler import igc2vva, csv2vva, generate_vva, load_vva_files, save_section_to_vva
from table_handler import update_vva_table, delete_table_entries, update_table_button_state, return_selected_row, create_polar_table, save_comment_alias, populate_table_1D_variable
from PyQt6.QtCore import QThread, QThreadPool, QSettings
from moulinette_worker import MoulinetteWorker
from pyqtgraph import ErrorBarItem 
import pyqtgraph as pg
from export import export_file_csv, export_file_kml
from plot_emagram import SkewTWidget
import sys
from units import get_unit, convert_array_to_unit
from overlay_map import OSMTileOverlay
from dropzone import DropZone
from polar_generator import update_polar_generator_values
from pathlib  import Path 
import pprint
import numpy as np
from preference_windows import UnitDialog, ColorDialog
import plot 


SOFTWARE_VERSION = "1.0.0"
OPEN = 0.0389250
POD =  0.0296384
SUB =  0.0247878

class MainWindow(QtWidgets.QMainWindow):

    
    def __init__(self):
        super(MainWindow, self).__init__()
    
        uic.loadUi(self.resource_path("gui/mainwindow.ui"), self)  # Load the .ui file directly
        self.unit_dialog = UnitDialog(parent = self)  
        self.unit_dialog.unitsChanged.connect(lambda: plot.update_1D_plot(self.flight, self.comboBox_flight_tab1D, self.tableWidget_variable_plot1, self.graph1_tab1D, self.curve_1D_11,self.curve_1D_12))
        self.unit_dialog.unitsChanged.connect(lambda: plot.update_1D_plot(self.flight, self.comboBox_flight_tab1D, self.tableWidget_variable_plot2, self.graph2_tab1D, self.curve_1D_21, self.curve_1D_22))
        self.unit_dialog.unitsChanged.connect(lambda : plot.update_sample_serie_plot(self.flight, self.comboBox_flight_select_polartab, self.comboBox_variable_select_polartab, self.graph_tabpolar_timeserie))
        self.unit_dialog.unitsChanged.connect(lambda : create_polar_table(self.flight, self.tableView_polar_points, self.comboBox_flight_select_polartab))
        self.unit_dialog.unitsChanged.connect(lambda : plot.update_polar_values(self.flight, self.graph_tabpolar_vxvz, self.tableView_polar_points, self.comboBox_flight_select_polartab, self.graph_tabpolar_legend_vxvz, self.horizontalSlider_ias_comp.value() ))
        self.unit_dialog.unitsChanged.connect(lambda : plot.update_sample_serie_plot(self.flight, self.comboBox_flight_select_atmtab, self.comboBox_variable_select_atmtab, self.graph_atmtab_timeserie))
        self.unit_dialog.unitsChanged.connect(lambda : update_polar_generator_values(self.horizontalSlider_auw.value(), self.horizontalSlider_ar.value(), self.horizontalSlider_sproj.value(),  self.widget_harness_polar , self.polar_generated_curve, self.crosshair_trim_speed, self.graph_tabpolar_vxvz))
        # self.unit_dialog.unitsChanged.connect(lambda event: self.on_2D_point_clicked(event, self.flight, self.graph_tab2D, self.tableWidget_flights_plot2D, self.tableWidget_data_point_tab2D, self.label_table_data))
        # self.unit_dialog.unitsChanged.connect(lambda event: self.on_1D_point_clicked(event, self.flight, self.graph1_tab1D, self.comboBox_flight_tab1D, self.tableWidget_variable_plot1))
        # self.unit_dialog.unitsChanged.connect(lambda event: self.on_1D_point_clicked(event, self.flight, self.graph2_tab1D, self.comboBox_flight_tab1D, self.tableWidget_variable_plot2))
        
        self.color_dialog = ColorDialog(parent = self)  
        self.color_dialog.colorWindBarbsChanged.connect(lambda: plot.update_wind_barbs_2D(self.flight, self.tableWidget_flights_plot2D, self.graph_tab2D, self.radioButton_windbarbs, self.horizontalSlider_density_barbs, self.horizontalSlider_size_barbs))
        
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
        self.actionColors.triggered.connect(self.display_color_window)
        self.actionImport_file.triggered.connect(self.on_button_load_file)
        """
        Widgets tab import  / export
        """
        
        
        self.pushButton_clear_log.clicked.connect(self.on_button_clear_log)
        self.pushButton_delete_entry.clicked.connect(self.on_button_delete_entries)
        self.pushButton_analyze_entry.clicked.connect(self.on_button_analyze_entries)
        self.pushButton_export_entry_csv.clicked.connect(self.on_button_export_entries_csv)
        self.pushButton_export_entry_kml.clicked.connect(self.on_button_export_entries_kml)
        self.logbox_handler = QTextEditLogger(self.textEdit_log)
        self.textEdit_log.verticalScrollBar().setValue(self.textEdit_log.verticalScrollBar().maximum())
        logger.addHandler(self.logbox_handler) 
        
        #initialize progress bar to 0
        self.progressBar.setValue(0)
        
        #Table ------------------------------------
        headers = ["","Flight Name", "Flight date", "Start altitude","Max altitude", "Pilot", "Comment", "Alias"]
        self.tab_list = [self.oneDplotter_tab,self.twoDplotter_tab,self.polar_tab,self.atmo_tab, self.dynamic_tab]
        for tab in self.tab_list:
            index = self.tabWidget.indexOf(tab)
            self.tabWidget.setTabEnabled(index, False)
            
        self.tableWidget_database.setColumnCount(len(headers))
        self.tableWidget_database.setHorizontalHeaderLabels(headers)
        header = self.tableWidget_database.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tableWidget_database.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        #self.tableWidget_database.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
  
        self.tableWidget_database.resizeColumnsToContents()
        self.tableWidget_database.itemChanged.connect(lambda : update_table_button_state(self.tableWidget_database,self.flight, self.pushButton_export_entry_csv, self.pushButton_delete_entry, self.pushButton_analyze_entry, self.pushButton_export_entry_kml, self.tab_list, self.tabWidget))
        self.tableWidget_database.itemChanged.connect(lambda item: save_comment_alias(item, self.flight, self.tableWidget_database))
        
        self.flight = load_vva_files()  #scan and load data from flight dir  # This variable contains all the data and metadata from flights 
        update_vva_table(self.flight, self.tableWidget_database)
        
        self.drop_zone = DropZone()
        self.drag_and_drop_layout.layout().insertWidget(0, self.drop_zone)
        self.drop_zone.fileDropped.connect(lambda filepath : self.on_drop_load_file(filepath))
        
        """
        Widgets tab 1D plot
        """
        #Initializing curves
        self.graph1_tab1D.setBackground("w")
        self.graph1_tab1D.setLabel('left', 'No variable selected')
        self.graph1_tab1D.setLabel('bottom', 'GNSS Time (s)')
        self.graph1_tab1D.setTitle("Select a variable to plot in time")
        self.graph1_tab1D.showGrid(x=True, y=True, alpha=0.3)
        self.graph1_tab1D.setEnabled(True)
        self.graph1_tab1D.crosshair_id = "1"
        
        self.graph2_tab1D.setBackground("w")
        self.graph2_tab1D.setLabel('left', 'No variable selected')
        self.graph2_tab1D.setLabel('bottom', 'GNSS Time (s)')
        self.graph2_tab1D.setTitle("Select a variable to plot in time")
        self.graph2_tab1D.showGrid(x=True, y=True, alpha=0.3)
        self.graph2_tab1D.setEnabled(True)
        self.graph2_tab1D.crosshair_id = "2"
        
        self.graph1_tab1D.enableAutoRange(True)
        self.graph2_tab1D.enableAutoRange(True)
        
        date_axis_1 = pg.graphicsItems.DateAxisItem.DateAxisItem(orientation='bottom')
        date_axis_2 = pg.graphicsItems.DateAxisItem.DateAxisItem(orientation='bottom')
        
        self.graph1_tab1D.setAxisItems({'bottom': date_axis_1})
        self.graph2_tab1D.setAxisItems({'bottom': date_axis_2})
        
        self.curve_1D_11 = self.graph1_tab1D.plot([], [])
        self.curve_1D_12 = self.graph1_tab1D.plot([], [])
        self.curve_1D_21 = self.graph2_tab1D.plot([], [])
        self.curve_1D_22 = self.graph2_tab1D.plot([], [])
        

        self.comboBox_flight_tab1D.currentTextChanged.connect(lambda choice: populate_table_1D_variable(self.flight, self.tableWidget_variable_plot1, self.tableWidget_variable_plot2, choice))
        self.comboBox_flight_tab1D.currentTextChanged.connect(lambda: plot.restore_checked_variables_1D(self.flight, self.comboBox_flight_tab1D, self.tableWidget_variable_plot1, self.tableWidget_variable_plot2))
        self.comboBox_flight_tab1D.currentTextChanged.connect(lambda: plot.update_1D_plot(self.flight, self.comboBox_flight_tab1D, self.tableWidget_variable_plot1, self.graph1_tab1D, self.curve_1D_11,self.curve_1D_12))
        self.comboBox_flight_tab1D.currentTextChanged.connect(lambda: plot.update_1D_plot(self.flight, self.comboBox_flight_tab1D, self.tableWidget_variable_plot2, self.graph2_tab1D, self.curve_1D_21,self.curve_1D_22))

        
 
        self.tableWidget_variable_plot1.itemChanged.connect(lambda item: self.on_item_table_1D_changed(item))
        self.tableWidget_variable_plot2.itemChanged.connect(lambda item: self.on_item_table_1D_changed(item))
        
        self.checkBox_x_axis_link.stateChanged.connect(lambda: plot.toggle_x_link(self.graph1_tab1D, self.graph2_tab1D, self.checkBox_x_axis_link))
        
        #Table ------------------------------------
        header_table_1D2 = ["Variable", "Value", "Unit"]
        self.tableWidget_variable_plot2.setColumnCount(len(header_table_1D2))
        self.tableWidget_variable_plot2.setHorizontalHeaderLabels(header_table_1D2)
        header_table_1D2 = self.tableWidget_variable_plot2.horizontalHeader()
        header_table_1D2.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tableWidget_variable_plot2.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidget_variable_plot2.resizeColumnsToContents()
        
        header_table_1D1 = ["Variable", "Value", "Unit"]
        self.tableWidget_variable_plot1.setColumnCount(len(header_table_1D1))
        self.tableWidget_variable_plot1.setHorizontalHeaderLabels(header_table_1D1)
        header_table_1D1 = self.tableWidget_variable_plot1.horizontalHeader()
        header_table_1D1.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tableWidget_variable_plot1.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidget_variable_plot1.resizeColumnsToContents()
        
        self.graph1_tab1D.scene().sigMouseClicked.connect(lambda event: self.on_1D_point_clicked(event, self.flight, self.graph1_tab1D, self.comboBox_flight_tab1D, self.tableWidget_variable_plot1))
        self.graph2_tab1D.scene().sigMouseClicked.connect(lambda event: self.on_1D_point_clicked(event, self.flight, self.graph2_tab1D, self.comboBox_flight_tab1D, self.tableWidget_variable_plot2))
        """
        Widgets tab 2D plot
        """
        
        self.graph_tab2D.setBackground("w")
        self.graph_tab2D.setLabel("left", "Latitudes")
        self.graph_tab2D.setLabel("bottom", "Longitudes")
        self.graph_tab2D.addLegend()
        self.graph_tab2D.showGrid(x=True, y=True, alpha=0.3)
        self.graph_tab2D.setEnabled(True)
        self.graph_tab2D.setAspectLocked(True)

        
        # self.colorbar = pg.ColorBarItem(values=(0, 1),width=10,colorMap=pg.colormap.get('turbo'), interactive=False, orientation='horizontal')
        # self.color_gradient_bar_widget.addItem(self.colorbar)
        # self.color_gradient_bar_widget.setBackground("w")
        # self.colorbar.setOpacity(0) 
        
        
        #Table ------------------------------------
        headers_table_map = ["Flight", "Variable"]
        self.tableWidget_flights_plot2D.setColumnCount(len(headers_table_map))
        self.tableWidget_flights_plot2D.setHorizontalHeaderLabels(headers_table_map)
        header_table_map = self.tableWidget_flights_plot2D.horizontalHeader()
        header_table_map.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tableWidget_flights_plot2D.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidget_flights_plot2D.resizeColumnsToContents()
        
        headers_table_map_variable = ["Variable","Value", "Unit"]
        self.tableWidget_data_point_tab2D.setColumnCount(len(headers_table_map_variable))
        self.tableWidget_data_point_tab2D.setHorizontalHeaderLabels(headers_table_map_variable)
        header_table_map_variable = self.tableWidget_data_point_tab2D.horizontalHeader()
        header_table_map_variable.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tableWidget_data_point_tab2D.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidget_data_point_tab2D.resizeColumnsToContents()
        
        #signals
        self.tableWidget_flights_plot2D.itemChanged.connect(lambda: plot.update_2D_plot(self.flight, self.tableWidget_flights_plot2D , self.graph_tab2D ))
        self.tableWidget_flights_plot2D.itemChanged.connect(lambda: plot.update_wind_barbs_2D(self.flight, self.tableWidget_flights_plot2D, self.graph_tab2D, self.radioButton_windbarbs, self.horizontalSlider_density_barbs, self.horizontalSlider_size_barbs))
        
        
        self.horizontalSlider_density_barbs.setRange(1,100)
        self.horizontalSlider_density_barbs.setSingleStep(1)
        self.horizontalSlider_density_barbs.setSliderPosition(50) 
        self.horizontalSlider_size_barbs.setRange(1,100)
        self.horizontalSlider_size_barbs.setSingleStep(1)
        self.horizontalSlider_size_barbs.setSliderPosition(50) 
        
        self.radioButton_windbarbs.toggled.connect(lambda toggle : self.on_button_windbarbs(toggle, self.widget_22))
        self.radioButton_windbarbs.toggled.connect(lambda: plot.update_wind_barbs_2D(self.flight, self.tableWidget_flights_plot2D, self.graph_tab2D, self.radioButton_windbarbs, self.horizontalSlider_density_barbs, self.horizontalSlider_size_barbs))
        self.horizontalSlider_density_barbs.valueChanged.connect(lambda: plot.update_wind_barbs_2D(self.flight, self.tableWidget_flights_plot2D, self.graph_tab2D, self.radioButton_windbarbs, self.horizontalSlider_density_barbs, self.horizontalSlider_size_barbs))
        self.horizontalSlider_size_barbs.valueChanged.connect(lambda: plot.update_wind_barbs_2D(self.flight, self.tableWidget_flights_plot2D, self.graph_tab2D, self.radioButton_windbarbs, self.horizontalSlider_density_barbs, self.horizontalSlider_size_barbs))
        
        self.graph_tab2D.scene().sigMouseClicked.connect(lambda event: self.on_2D_point_clicked(event, self.flight, self.graph_tab2D, self.tableWidget_flights_plot2D, self.tableWidget_data_point_tab2D, self.label_table_data))

        # Map
    
        map_overlay = OSMTileOverlay(
        self.graph_tab2D,
        tile_url="https://tile.opentopomap.org/{z}/{x}/{y}.png",
        user_agent="VVA User (felixaubourg@gmail.com)",
        )
        
        self.horizontalSlider_set_opacity.setSliderPosition(50)

        self.radioButton_background_map.toggled.connect(lambda toggle: map_overlay.display_tiles(toggle))
        self.radioButton_background_map.toggled.connect(lambda toggle: self.widget_opacity.setEnabled(toggle))
        self.radioButton_background_map.toggled.connect(lambda : map_overlay.set_opacity(self.horizontalSlider_set_opacity.value() / 100.0))
        self.horizontalSlider_set_opacity.valueChanged.connect(lambda v: map_overlay.set_opacity(v / 100.0))

        """
        Widgets tab POLAR
        """
        
        #Table ------------------------------------
        headers_table_polar = ["Vx", "Vz", "Glide Ratio"]
        self.tableView_polar_points.setColumnCount(len(headers_table_polar))
        self.tableView_polar_points.setHorizontalHeaderLabels(headers_table_map)
        header_table_polar = self.tableView_polar_points.horizontalHeader()
        header_table_polar.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tableView_polar_points.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableView_polar_points.resizeColumnsToContents()
        self.tableView_polar_points.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tableView_polar_points.cellClicked.connect(lambda row, column: self.on_table_cell_clicked(row, self.flight, self.comboBox_flight_select_polartab, self.tableView_polar_points, self.graph_tabpolar_timeserie, self.graph_tabpolar_vxvz, self.pushButton_remove_polar_point))
        
        self.graph_tabpolar_vxvz.setBackground("w")
        self.graph_tabpolar_vxvz.setXRange(0, 30, padding=0)
        self.graph_tabpolar_vxvz.setYRange(-10, 2, padding=0)
        self.graph_tabpolar_vxvz.setTitle("Vx vs Vz")
        self.graph_tabpolar_vxvz.showGrid(x=True, y=True, alpha=0.3)
        self.graph_tabpolar_vxvz.setEnabled(True)

        self.graph_tabpolar_legend_vxvz = pg.LegendItem()
        self.graph_tabpolar_legend_vxvz.setParentItem(self.graph_tabpolar_vxvz.getPlotItem())
        self.graph_tabpolar_legend_vxvz.anchor(itemPos=(1, 0), parentPos=(1, 0), offset=(-10, 10))
        
        self.graph_tabpolar_timeserie.setBackground("w")
        self.graph_tabpolar_timeserie.setLabel("bottom", "Sample")
        self.graph_tabpolar_timeserie.addLegend()
        self.graph_tabpolar_timeserie.showGrid(x=True, y=True, alpha=0.3)
        self.graph_tabpolar_timeserie.setEnabled(True)
        
        self.comboBox_flight_select_polartab.currentTextChanged.connect(lambda choice: self.populate_combobox_variable(self.flight, self.comboBox_variable_select_polartab, choice, 'polar'))
        self.comboBox_flight_select_polartab.currentTextChanged.connect(lambda: plot.clear_plots_1D(self.graph_tabpolar_timeserie, None))
        self.comboBox_flight_select_polartab.currentTextChanged.connect(lambda : plot.load_polar_roi(self.flight, self.graph_tabpolar_timeserie, self.graph_tabpolar_vxvz,  self.tableView_polar_points,  self.comboBox_flight_select_polartab, self.graph_tabpolar_legend_vxvz,  self.horizontalSlider_ias_comp.value() ))
        self.comboBox_flight_select_polartab.currentTextChanged.connect(lambda:plot.update_sample_serie_plot(self.flight, self.comboBox_flight_select_polartab, self.comboBox_variable_select_polartab, self.graph_tabpolar_timeserie))
        self.comboBox_variable_select_polartab.currentTextChanged.connect(lambda : plot.update_sample_serie_plot(self.flight, self.comboBox_flight_select_polartab, self.comboBox_variable_select_polartab, self.graph_tabpolar_timeserie))
        self.comboBox_variable_select_polartab.currentTextChanged.connect(lambda : plot.display_rois(self.flight, self.graph_tabpolar_timeserie, self.comboBox_flight_select_polartab , 'roi_polar'))
        self.comboBox_flight_select_polartab.currentTextChanged.connect(lambda : plot.display_rois(self.flight, self.graph_tabpolar_timeserie, self.comboBox_flight_select_polartab, 'roi_polar'))
        self.comboBox_flight_select_polartab.currentTextChanged.connect(lambda : plot.reset_highlights(self.flight, self.graph_tabpolar_vxvz ))
        self.comboBox_flight_select_polartab.currentTextChanged.connect(lambda :create_polar_table(self.flight, self.tableView_polar_points, self.comboBox_flight_select_polartab))
        self.pushButton_add_polar_point.clicked.connect(lambda : plot.create_roi(self.flight,self.graph_tabpolar_timeserie, self.graph_tabpolar_vxvz, self.tableView_polar_points, self.comboBox_flight_select_polartab, self.graph_tabpolar_legend_vxvz,  self.horizontalSlider_ias_comp.value()))
        self.pushButton_add_polar_point.clicked.connect(lambda : create_polar_table(self.flight, self.tableView_polar_points, self.comboBox_flight_select_polartab))
        self.pushButton_remove_polar_point.clicked.connect(lambda : plot.remove_roi(self.flight,self.graph_tabpolar_timeserie, self.graph_tabpolar_vxvz, self.tableView_polar_points, self.comboBox_flight_select_polartab, self.graph_tabpolar_legend_vxvz,  self.horizontalSlider_ias_comp.value()))
        self.pushButton_save_polar.clicked.connect(lambda : save_section_to_vva(self.flight, 'roi_polar'))
        
        #Polar Generator
        #initializing the generated polar curve
        self.polar_generated_curve = self.graph_tabpolar_vxvz.plot(
            [],
            [],
            pen=pg.mkPen(QColor(116, 97, 194), width=2),
            symbol=None
        )
        
        self.crosshair_trim_speed = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen(QColor(116, 97, 194), width=1, style=QtCore.Qt.PenStyle.DashLine),
            label='TrimSpeed = {value:.2f}',
            markers= '>|',
            labelOpts={
            'position':  0.1,          
            'color': (150, 150, 150), 
            'fill': None,             
            'border': None,           
            'anchor': (1, -0.5)        
            })
        
        self.graph_tabpolar_vxvz.addItem(self.crosshair_trim_speed)
        self.crosshair_trim_speed.hide()
        
        self.checkBox_display_generated_polar.stateChanged.connect(lambda state: self.on_radiobutton_dis_gen_pol(state,self.polar_generated_curve, self.graph_tabpolar_vxvz , self.crosshair_trim_speed))
        self.checkBox_ias_offset.stateChanged.connect(lambda state: self.on_radiobutton_comp_ias(state, self.widget_ias_compensation, self.horizontalSlider_ias_comp, self.graph_tabpolar_vxvz))
        self.horizontalSlider_sproj.valueChanged.connect(self.spinBox_sproj.setValue)
        self.spinBox_sproj.valueChanged.connect(self.horizontalSlider_sproj.setValue)
        self.horizontalSlider_auw.valueChanged.connect(self.spinBox_auw.setValue)
        self.spinBox_auw.valueChanged.connect(self.horizontalSlider_auw.setValue)
        self.horizontalSlider_ar.valueChanged.connect(lambda v: self.spinBox_ar.setValue(v / 10))
        self.spinBox_ar.valueChanged.connect(lambda v: self.horizontalSlider_ar.setValue(int(v * 10)))
        self.horizontalSlider_ias_comp.valueChanged.connect(self.spinBox_ias_comp.setValue)
        self.spinBox_ias_comp.valueChanged.connect(self.horizontalSlider_ias_comp.setValue)
        
        self.horizontalSlider_sproj.setRange(8,45)
        self.spinBox_sproj.setRange(8,45)
        self.horizontalSlider_auw.setRange(40, 250)
        self.spinBox_auw.setRange(40, 250)
        self.horizontalSlider_ar.setRange(30,80)
        self.spinBox_ar.setRange(3,8)
        self.horizontalSlider_ias_comp.setRange(-15,15)
        self.spinBox_ias_comp.setRange(-15,15)
        
        self.horizontalSlider_sproj.setSingleStep(1)
        self.horizontalSlider_auw.setSingleStep(1)
        self.horizontalSlider_ar.setSingleStep(1)
        self.spinBox_ar.setSingleStep(0.1)
        self.horizontalSlider_sproj.setSliderPosition(20) 
        self.horizontalSlider_auw.setSliderPosition(90) 
        self.horizontalSlider_ar.setSliderPosition(60) 
        self.horizontalSlider_ias_comp.setSliderPosition(0)
        
        
        self.horizontalSlider_sproj.valueChanged.connect(lambda sproj: update_polar_generator_values(self.horizontalSlider_auw.value(), self.horizontalSlider_ar.value(), sproj, self.widget_harness_polar , self.polar_generated_curve, self.crosshair_trim_speed, self.graph_tabpolar_vxvz))
        self.horizontalSlider_auw.valueChanged.connect(lambda auw: update_polar_generator_values(auw, self.horizontalSlider_ar.value(), self.horizontalSlider_sproj.value(),  self.widget_harness_polar , self.polar_generated_curve,self.crosshair_trim_speed, self.graph_tabpolar_vxvz))
        self.horizontalSlider_ar.valueChanged.connect(lambda ar: update_polar_generator_values(self.horizontalSlider_auw.value(), ar, self.horizontalSlider_sproj.value(),  self.widget_harness_polar , self.polar_generated_curve,self.crosshair_trim_speed, self.graph_tabpolar_vxvz))
        self.horizontalSlider_ias_comp.valueChanged.connect(lambda : plot.update_polar_values(self.flight, self.graph_tabpolar_vxvz, self.tableView_polar_points, self.comboBox_flight_select_polartab, self.graph_tabpolar_legend_vxvz, self.horizontalSlider_ias_comp.value() ))

        self.checkBox_display_generated_polar.stateChanged.connect(lambda: update_polar_generator_values(self.horizontalSlider_auw.value(), self.horizontalSlider_ar.value(), self.horizontalSlider_sproj.value(),  self.widget_harness_polar , self.polar_generated_curve,self.crosshair_trim_speed, self.graph_tabpolar_vxvz))
        for button in self.widget_harness_polar.findChildren(QRadioButton):
            button.toggled.connect(lambda: update_polar_generator_values(self.horizontalSlider_auw.value(), self.horizontalSlider_ar.value(), self.horizontalSlider_sproj.value(),  self.widget_harness_polar , self.polar_generated_curve , self.crosshair_trim_speed, self.graph_tabpolar_vxvz))
        
        self.checkBox_display_generated_polar.stateChanged.connect(lambda : plot.update_polar_values(self.flight, self.graph_tabpolar_vxvz, self.tableView_polar_points, self.comboBox_flight_select_polartab, self.graph_tabpolar_legend_vxvz, self.horizontalSlider_ias_comp.value() ))
        
        self.graph_tabpolar_timeserie.scene().sigMouseClicked.connect(
        lambda pos: self.on_roi_clicked(pos, self.flight, self.graph_tabpolar_timeserie, self.tableView_polar_points, self.graph_tabpolar_vxvz)
        )
        self.graph_tabpolar_vxvz.scene().sigMouseClicked.connect(lambda event: self.on_polar_point_clicked(event, self.flight, self.graph_tabpolar_timeserie, self.tableView_polar_points, self.graph_tabpolar_vxvz, self.comboBox_flight_select_polartab))
        
        """
        Widgets tab EMAGRAM
        """
        
        self.skewt = SkewTWidget(self.graph_skewt)
        
        
        self.graph_atmtab_timeserie.setBackground("w")
        self.graph_atmtab_timeserie.setLabel("bottom", "Sample")
        self.graph_atmtab_timeserie.addLegend()
        self.graph_atmtab_timeserie.showGrid(x=True, y=True, alpha=0.3)
        self.graph_atmtab_timeserie.setEnabled(True)

        self.comboBox_flight_select_atmtab.currentTextChanged.connect(lambda choice: self.populate_combobox_variable(self.flight, self.comboBox_variable_select_atmtab, choice, 'emagram'))
        
        self.comboBox_flight_select_atmtab.currentTextChanged.connect(lambda: plot.clear_plots_1D(self.graph_atmtab_timeserie, None))
        self.comboBox_flight_select_atmtab.currentTextChanged.connect(lambda : plot.load_emagram_roi(self.flight, self.graph_atmtab_timeserie, self.skewt, self.comboBox_flight_select_atmtab ))
        
        self.comboBox_flight_select_atmtab.currentTextChanged.connect(lambda: plot.update_sample_serie_plot(self.flight, self.comboBox_flight_select_atmtab, self.comboBox_variable_select_atmtab, self.graph_atmtab_timeserie))
        self.comboBox_variable_select_atmtab.currentTextChanged.connect(lambda : plot.update_sample_serie_plot(self.flight, self.comboBox_flight_select_atmtab, self.comboBox_variable_select_atmtab, self.graph_atmtab_timeserie))
        #self.comboBox_flight_select_atmtab.currentTextChanged.connect(lambda : plot.display_rois(self.flight, self.graph_atmtab_timeserie, self.comboBox_flight_select_atmtab, 'roi_emagram'))
        
        self.checkBox_isotherm.stateChanged.connect(lambda state: self.horizontalSlider_isotherm.setEnabled(state))
        self.checkBox_dryadia.stateChanged.connect(lambda state: self.horizontalSlider_dry_adia.setEnabled(state))
        self.checkBox_moist_adia.stateChanged.connect(lambda state: self.horizontalSlider_moist_adia.setEnabled(state))
        self.checkBox_windbarbs_atm.stateChanged.connect(lambda state: self.horizontalSlider_windbarbs_atm.setEnabled(state))
        
        

        self.checkBox_isotherm.stateChanged.connect(
            lambda state: self.skewt.set_background_visibility(isotherms=bool(state)))  
        
        self.checkBox_dryadia.stateChanged.connect(
            lambda state: self.skewt.set_background_visibility(dry_adiabats=bool(state)))
        
        self.checkBox_moist_adia.stateChanged.connect(
            lambda state: self.skewt.set_background_visibility(moist_adiabats=bool(state)))
        
        self.checkBox_mixing_ratio.stateChanged.connect(
            lambda state: self.skewt.set_background_visibility(mixing_ratio=bool(state)))   
        
        self.checkBox_windbarbs_atm.stateChanged.connect(
            lambda state: self.skewt.set_background_visibility(windbarbs=bool(state)))   
        
        self.horizontalSlider_isotherm.valueChanged.connect(lambda v: self.skewt.set_isotherm_step(v, self.checkBox_isotherm.isChecked()))
        self.horizontalSlider_dry_adia.valueChanged.connect(lambda v: self.skewt.set_dry_adiabat_step(v, self.checkBox_dryadia.isChecked()))
        self.horizontalSlider_moist_adia.valueChanged.connect(lambda v: self.skewt.set_moist_adiabat_step(v, self.checkBox_moist_adia.isChecked()))
        self.horizontalSlider_windbarbs_atm.valueChanged.connect(lambda v: self.skewt.set_windbarbs_step(v))

        
        self.checkBox_isotherm.setCheckState(Qt.CheckState.Checked)
        self.checkBox_dryadia.setCheckState(Qt.CheckState.Unchecked)
        self.checkBox_moist_adia.setCheckState(Qt.CheckState.Unchecked)
        self.checkBox_mixing_ratio.setCheckState(Qt.CheckState.Unchecked)
        self.checkBox_windbarbs_atm.setCheckState(Qt.CheckState.Unchecked)



        
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
        Triggered from the menu bar
        """

        self.new_file_path = QtWidgets.QFileDialog.getOpenFileName(self, "Open flight file", "", ".CSV .IGC Files (*.csv *.igc)")
        if self.new_file_path[0]:
            self.new_file_path = Path(self.new_file_path[0]) 
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
         
                return  
        
        try:
            shutil.copy2(self.new_file_path, new_file_path_copy)
            logger.info("File copied")
            self.new_file_path = new_file_path_copy

        except shutil.SameFileError:
            logger.info("Source and destination represent the same file.")
        except PermissionError:
            logger.info("Permission denied.")
        except FileNotFoundError:
            logger.info("Source file not found.")
        except Exception as e:
            logger.info(f"An error occurred: {e}")
        
        if self.new_file_path.suffix == ".csv":
            generate_vva(self.new_file_path, csv2vva(self.new_file_path))
            logger.info("Converting .csv file to .vva")
        elif self.new_file_path.suffix == ".IGC" or self.new_file_path.suffix == ".igc":
            generate_vva(self.new_file_path, igc2vva(self.new_file_path))
            logger.info("Converting .igc file to .vva")
        else:
            logger.info(f"{self.new_file_path.suffix} files are not supported on version {SOFTWARE_VERSION}")
            return
        
        self.flight = load_vva_files()
        update_vva_table(self.flight, self.tableWidget_database)
        update_table_button_state(self.tableWidget_database,self.flight, self.pushButton_export_entry_csv, self.pushButton_delete_entry, self.pushButton_analyze_entry, self.pushButton_export_entry_kml, self.tab_list, self.tabWidget)
        self.populate_combobox_flight(self.flight, self.comboBox_flight_tab1D)
        self.populate_combobox_flight(self.flight, self.comboBox_flight_select_polartab)
        self.populate_combobox_flight(self.flight, self.comboBox_flight_select_atmtab)
        self.populate_flight_table_tab_2D(self.flight, self.tableWidget_flights_plot2D,self.graph_tab2D )
            
    def on_drop_load_file(self, filepath):
        """
        Fetching new file path and copying it into flight folder
        Used when user drops the new file
        """

        
    
        new_file_path = Path(filepath) 
        new_file_path_copy_name = Path(new_file_path).name
        new_file_path_copy = Path(os.path.join('./flight/',new_file_path_copy_name))
      
        
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
                return  
        
        try:
            shutil.copy2(new_file_path, new_file_path_copy)
            logger.info("File copied")
            new_file_path = new_file_path_copy
            
        except shutil.SameFileError:
            logger.info("Source and destination represent the same file.")
        except PermissionError:
            logger.info("Permission denied.")
        except FileNotFoundError:
            logger.info("Source file not found.")
        except Exception as e:
            logger.info(f"An error occurred: {e}")
        
        
        if new_file_path.suffix == ".csv":
            generate_vva(new_file_path, csv2vva(new_file_path))
            logger.info("Converting .csv file to .vva")
        elif new_file_path.suffix == ".IGC" or new_file_path.suffix == ".igc":
            generate_vva(new_file_path, igc2vva(new_file_path))
            logger.info("Converting .igc file to .vva")
        else:
            logger.info(f"{new_file_path.suffix} files are not supported on version {SOFTWARE_VERSION}")
            return
        
        self.flight = load_vva_files()
        update_vva_table(self.flight, self.tableWidget_database)
        update_table_button_state(self.tableWidget_database,self.flight, self.pushButton_export_entry_csv, self.pushButton_delete_entry, self.pushButton_analyze_entry, self.pushButton_export_entry_kml, self.tab_list, self.tabWidget)
        self.populate_combobox_flight(self.flight, self.comboBox_flight_tab1D)
        self.populate_combobox_flight(self.flight, self.comboBox_flight_select_polartab)
        self.populate_combobox_flight(self.flight, self.comboBox_flight_select_atmtab)
        self.populate_flight_table_tab_2D(self.flight, self.tableWidget_flights_plot2D,self.graph_tab2D )


        
        
        
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
        update_table_button_state(self.tableWidget_database,self.flight, self.pushButton_export_entry_csv, self.pushButton_delete_entry, self.pushButton_analyze_entry, self.pushButton_export_entry_kml, self.tab_list, self.tabWidget)
        self.populate_combobox_flight(self.flight, self.comboBox_flight_tab1D)
        self.populate_combobox_flight(self.flight, self.comboBox_flight_select_polartab)
        self.populate_combobox_flight(self.flight, self.comboBox_flight_select_atmtab)
        self.populate_flight_table_tab_2D(self.flight, self.tableWidget_flights_plot2D,self.graph_tab2D )
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
            self.populate_combobox_flight(self.flight, self.comboBox_flight_select_atmtab)
            self.populate_flight_table_tab_2D(self.flight, self.tableWidget_flights_plot2D,self.graph_tab2D )
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
        update_table_button_state(self.tableWidget_database,self.flight, self.pushButton_export_entry_csv, self.pushButton_delete_entry, self.pushButton_analyze_entry, self.pushButton_export_entry_kml, self.tab_list, self.tabWidget)
        self.start_next_analysis_thread(self.pushButton_analyze_entry)
       
        
    def analysis_error(self, msg):
        logger.error(f"Error while analyzing data : {msg}")
        
        
    def on_button_export_entries_csv(self):
        
        row_to_export = return_selected_row(self.flight, self.tableWidget_database)
        for row in row_to_export:
            export_file_csv(self.flight[row], self)
            
    def on_button_export_entries_kml(self):
        
        row_to_export = return_selected_row(self.flight, self.tableWidget_database)
        for row in row_to_export:
            export_file_kml(self.flight[row], self)
            
    def populate_combobox_flight(self, data, combo_box_flight):
        """
        Set the flights that has been analyzed into the specified combobox. Used in 1D plot, polar and emagram

        """
        #first we remove all the items in the combobox 
        combo_box_flight.clear()
        self.set_colors_to_flights(data) # We set a color to each flight here because the analyze has to be finished before setting new color trust me

        for row, flight in enumerate(data):
            original_filename = Path(flight['file_name'])
            original_filename_wo_extension = original_filename.with_suffix("")
            original_filename_wo_extension = str(original_filename_wo_extension.with_suffix(""))
            alias = self.get_alias(original_filename_wo_extension)
            if combo_box_flight.findText(alias) >= 0 and not flight['is_data_processed'] :
                combo_box_flight.removeItem(combo_box_flight.findText(alias))
            elif flight['is_data_processed'] and combo_box_flight.findText(alias) < 0:
                combo_box_flight.addItem(f"{alias}")
                
    
            
   
        
    def handle_checkboxes_on_table_1D(self, table_widget):
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
    
        table_widget.blockSignals(True)
    
        #  récupérer les items cochés
        items_checked = []
        for row in range(table_widget.rowCount()):
            item = table_widget.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                items_checked.append(item)
    
        #  reset état de tous les items
        for row in range(table_widget.rowCount()):
            item = table_widget.item(row, 0)
            if item:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setBackground(QBrush(QColor("white")))
                item.setToolTip("")
    
        if len(items_checked) == 0:
            table_widget.blockSignals(False)
            return
    
        first_var = items_checked[0].text()
        first_group = var_to_group.get(first_var)
    
        # variable sans groupe
        if first_group is None:
            for row in range(table_widget.rowCount()):
                item = table_widget.item(row, 0)
                if item and item.checkState() != Qt.CheckState.Checked:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                    item.setBackground(QBrush(QColor(240, 240, 240)))
                    item.setToolTip("Variable without unit group → single selection only")
    
            table_widget.blockSignals(False)
            return
    
        #  1 seule variable cochée
        if len(items_checked) == 1:
            for row in range(table_widget.rowCount()):
                item = table_widget.item(row, 0)
                if item:
                    var = item.text()
                    if var_to_group.get(var) != first_group:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                        item.setBackground(QBrush(QColor(240, 240, 240)))
    
        #  max atteint
        elif len(items_checked) >= max_number_plot:
            for row in range(table_widget.rowCount()):
                item = table_widget.item(row, 0)
                if item and item.checkState() != Qt.CheckState.Checked:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                    item.setBackground(QBrush(QColor(240, 240, 240)))
    
        table_widget.blockSignals(False)
        
        
    def populate_flight_table_tab_2D(self, flight_dic, table_widget, plot_widget):
        """
        Populating the flight table according to flights that are processed

        """

        table_widget.setRowCount(0)        
        row = 0
    
        for flight in flight_dic:
            if flight['is_data_processed'] and flight['data']:
    
                table_widget.insertRow(row)
                flight_name = self.get_alias(str(Path(flight['file_name']).with_suffix("").with_suffix("")))
    
                item = QTableWidgetItem(flight_name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    
                item.setCheckState(Qt.CheckState.Unchecked)
    
                table_widget.setItem(row, 0, item)
    
                combobox_var = QComboBox()
                combobox_var.currentTextChanged.connect(lambda: plot.update_2D_plot(flight_dic, table_widget , plot_widget ))
                combobox_var.currentTextChanged.connect(lambda: plot.update_wind_barbs_2D(self.flight, self.tableWidget_flights_plot2D, self.graph_tab2D, self.radioButton_windbarbs, self.horizontalSlider_density_barbs, self.horizontalSlider_size_barbs))
                combobox_var.addItem('None')
                for variable in flight['data']:
                    if variable != 'GNSS_time':
                        if len(flight['data'][variable]) > 0 and not np.all(np.isnan(flight['data'][variable])):
                            combobox_var.addItem(variable)
                table_widget.setCellWidget(row, 1, combobox_var)
    
                row += 1
                
              
  
    def populate_combobox_variable(self, flight_dic, combobox_var, choice, tab):
        """
        This function populate the variable according to the flight selected in the combobox in selected tab
        It also set a prioritarization of the variable IAS in the polar tab
        """
        combobox_var.clear()
        
        for flight in flight_dic:
            if flight['file_name'].split(".")[0] == choice or (flight['metadata']['alias'] == choice):
                if flight['is_data_processed'] and flight['data']:
                    if tab == 'polar':
                        priority_vars = ['IAS', 'GNSS_alt']
                        for variable in priority_vars:
                            if variable in flight['data']:
                                if len(flight['data'][variable]) > 0 and not np.all(np.isnan(flight['data'][variable])):
                                    combobox_var.addItem(variable)
                    elif tab == 'emagram':
                        for variable in flight['data']:
                            if variable != 'GNSS_time':
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
    
    def display_color_window(self): #Call the color window
        
        if self.color_dialog.isVisible():
            self.color_dialog.hide()
        else:
            self.color_dialog.show()
            
    def on_radiobutton_dis_gen_pol(self, state, scatter_polar, plot_widget_vxvz, line): 
        """
        Display or not the polar generated and the widgets associated
        """
        self.widget_harness_polar.setEnabled(state)
        self.widget_sliders_polar.setEnabled(state)
        if state:
            scatter_polar.show()
            line.show()
        else:
            scatter_polar.hide()
            line.hide()

        
        plot_widget_vxvz.autoRange()
        
    def on_radiobutton_comp_ias(self, state, widget, slider, plot_widget_vxvz):
        widget.setEnabled(state)
        if not state:
            slider.setValue(0)
        plot_widget_vxvz.autoRange()
    
    def on_table_cell_clicked(self, row, flight_dic, combobox_flight, table_widget, plot_time_widget, plot_vxvz_widget, button_remove):
        """
        When a table cell is clicked, it will display a cross in the vx vz graph pointing the current point, and highlight the matching ROI 
        """
        for i, flight in enumerate(flight_dic):
            if (flight['file_name'].split(".")[0] == combobox_flight.currentText()) or (flight['metadata']['alias'] == combobox_flight.currentText()):
                if row >= len(flight['plot']['roi_polar']):
                    return
                for i, roi_data in enumerate(flight['plot']['roi_polar']):
                    if i == row:
                        plot.highlights_polar_tab(i, flight, table_widget, plot_vxvz_widget)
                    
                    button_remove.setEnabled(True)

        
    def on_roi_clicked(self, event, flight_dic, plot_widget_timeserie, table_polar_points, plot_widget_vxvz):
        """
        Just like 'on_table_cell_clicked'. This function detects the position of the click
        and retrieves the roi associated, highlights it and create if necessary the crosshair 
        """ 
        vb = plot_widget_timeserie.getViewBox()
        click_pos = vb.mapSceneToView(event.scenePos())
        x = click_pos.x()
     
        for flight in flight_dic:
            if not flight['is_data_processed']:
                continue
     
            for i, roi_data in enumerate(flight['plot']['roi_polar']):
                x_min, x_max = roi_data[0].getRegion()
     
                if x_min <= x <= x_max:
                    plot.highlights_polar_tab(i, flight, table_polar_points, plot_widget_vxvz)
                    return
    
    
    def on_polar_point_clicked(self, event, flight_dic, plot_widget_timeserie, table_polar_points, plot_widget_vxvz, combobox_flight):
        """
        Just like 'on_table_cell_clicked'. This function detects the position of the click
        and retrieves the polar point associated, highlights its roi and create if necessary the crosshair 
        """ 
        vb = plot_widget_vxvz.getViewBox()
        click_pos = vb.mapSceneToView(event.scenePos())


        distances = []
        for i, flight in enumerate(flight_dic):
            if (flight['file_name'].split(".")[0] == combobox_flight.currentText()) or (flight['metadata']['alias'] == combobox_flight.currentText()):
                if flight['plot']['roi_polar']:
                    for index, roi_data in enumerate(flight['plot']['roi_polar']):
                        x_click = click_pos.x()
                        y_click = click_pos.y()
                        x_point = roi_data[2]
                        y_point = roi_data[3]
                        d = np.absolute(np.sqrt(np.add((np.square(np.subtract(x_click, x_point))), np.square(np.subtract(y_click, y_point)))))
                        distances.append(d)
                    
                    distance_closer = min(distances)
                    if distance_closer <= 0.5:
                        index_closer = distances.index(min(distances))
                        plot.highlights_polar_tab(index_closer, flight, table_polar_points, plot_widget_vxvz)
                    else:
                        return
                else:
                    return
                
    def on_2D_point_clicked(self, event, flight_dic, plot_widget, table_flight, table_data, label_table_data):
        """
        This function displays crosshair to the closest point where the user clicked
        It also retrieves the corresponding flight and displays its value on the data table
        Remove previous crosshair from other flights aswell 
        """
        table_data.setRowCount(0)        
        
        vb = plot_widget.getViewBox()
        click_pos = event.scenePos()
        flight_selected = plot.get_flight_variable_2D(table_flight)
        plausible_flight = []
        if len(flight_selected) == 0:
            return
        
        for row, flight in enumerate(flight_dic):
            for flight_to_plot, variable in flight_selected:
                if (flight['file_name'].split(".")[0] == flight_to_plot) or (flight['metadata']['alias'] == flight_to_plot):
                    x_click = click_pos.x()
                    y_click = click_pos.y()
                    best_dist = float('inf')
                    best_index = None
                    best_flight = None
                    for index in range(len(flight['data']['GNSS_lat'])):
                        
                        x_point = flight['data']['GNSS_lon'][index]
                        y_point = flight['data']['GNSS_lat'][index]
                        point_scene = vb.mapViewToScene(QtCore.QPointF(x_point, y_point))

                        dist = np.sqrt((x_click - point_scene.x())**2 + (y_click - point_scene.y())**2)

                        if dist < best_dist:
                            best_dist = dist
                            best_index = index
                            best_flight = flight['file_name'].split(".")[0]
                            
                    plausible_flight.append([best_dist, best_index, best_flight])
      
        
        if plausible_flight:
            best = min(plausible_flight, key=lambda x: x[0])
            best_dist, best_index, best_flight = best
            
            if best_dist < 20: #if the distance clicked is beyond 20 pixels
                for flight in flight_dic:
                    if (flight['file_name'].split(".")[0] == best_flight) or (flight['metadata']['alias'] == best_flight):
                        label_table_data.setText(f"Data from flight : {self.get_alias(flight['file_name'].split('.')[0])}")
                        row = 0
                        for variable in flight['data']: #creating table
                            if isinstance(flight['data'][variable], np.ndarray) and len(flight['data'][variable]) > 0 :
                                table_data.insertRow(row)
                                            
                                item_variable = QTableWidgetItem(variable)
                                item_variable.setFlags(item_variable.flags() & ~Qt.ItemFlag.ItemIsEditable)
                                table_data.setItem(row, 0, item_variable)
                                
                                data = convert_array_to_unit(flight['data'][variable], variable)
                                if isinstance(data[best_index], float):
                                    item_value = QTableWidgetItem(str(round(data[best_index],2)))
                                else:
                                    item_value = QTableWidgetItem(str(data[best_index]))
    
                                item_value.setFlags(item_value.flags() & ~Qt.ItemFlag.ItemIsEditable)
                                table_data.setItem(row, 1, item_value)
                                
                                item_unit = QTableWidgetItem(get_unit(variable))
                                item_unit.setFlags(item_unit.flags() & ~Qt.ItemFlag.ItemIsEditable)
                                table_data.setItem(row, 2, item_unit)
                                
                                row += 1
                        #setting the point to Highlight 
                        if flight['plot'].get('highlight_point_map'):
                            # Déjà existant → on met à jour
                            flight['plot']['highlight_point_map'].setData([float(flight['data']['GNSS_lon'][best_index])], [float(flight['data']['GNSS_lat'][best_index])])
                        else:
                            # Création du point highlight
                            scatter = pg.ScatterPlotItem(
                                x=[float(flight['data']['GNSS_lon'][best_index])],
                                y=[float(flight['data']['GNSS_lat'][best_index])],
                                size=6,  
                                pen=pg.mkPen('black', width=2),   # contour
                                brush=pg.mkBrush(255, 0, 0, 180), # rouge semi-transparent
                                symbol='o'
                            )
                        
                            plot_widget.addItem(scatter)
                            flight['plot']['highlight_point_map'] = scatter
            else:
                for flight in flight_dic:
                    if flight['file_name'].split(".")[0] == best_flight:
                        table_data.clearContents()
                        label_table_data.setText("Data from flight :")
                        if flight['plot'].get('highlight_point_map'):
                            plot_widget.removeItem(flight['plot']['highlight_point_map'])
                            flight['plot']['highlight_point_map'] = None
    

            
        
    def on_1D_point_clicked(self, event, flight_dic, plot_widget, combobox_flight, table_data):
        """
        This function displays crosshair to the closest point where the user clicked
        It also retrieves the corresponding flight and displays its value on the data table
        Remove previous crosshair from other flights aswell 
        """

            
        crosshair_id = plot_widget.crosshair_id
        vb = plot_widget.getViewBox()
        
        click_pos = event.scenePos()
        flight_selected = combobox_flight.currentText()
        variables_checked = plot.get_checked_variables(table_data)

        for flight in flight_dic:
            if (flight['file_name'].split(".")[0] == flight_selected) or (flight['metadata']['alias'] == flight_selected):
                x_click = click_pos.x()
                y_click = click_pos.y()
                
                best_dist = float('inf')
                best_index = None
                best_variable = None
                
                closest_variable = [] 
                for variable in variables_checked:
             
                    for index in range(len(flight['data'][variable])):
                        x_point = flight['data']['GNSS_time'][index].timestamp()
                        y_point = convert_array_to_unit(flight['data'][variable][index], variable)
                        point_scene = vb.mapViewToScene(QtCore.QPointF(x_point, y_point))
                        
                        #Computing virtual distance between click and the curve displayed . Get the relative distance in pixel
                        dist = np.sqrt((x_click - point_scene.x())**2 + (y_click - point_scene.y())**2)
              
                        if dist < best_dist:
                            best_dist = dist
                            best_index = index
                
                    closest_variable.append([best_dist, best_index, variable])
                
                # if flight['plot']['crosshair_v_map']:
                #     plot_widget.removeItem(flight['plot']['crosshair_v_map'])
                #     plot_widget.removeItem(flight['plot']['crosshair_h_map'])
        
                if closest_variable:
                    best = min(closest_variable, key=lambda x: x[0])
                    best_dist, best_index, best_variable = best
                    

                    if best_dist < 10: #if the distance clicked is beyond 30 pixels
                        for f in flight_dic:
                            if (f['file_name'].split(".")[0] == flight_selected) or (f['metadata']['alias'] == flight_selected):
                                for row in range(table_data.rowCount()): #Updating table content
                                    variable_already_set = table_data.item(row, 0).text()  
                                    data = convert_array_to_unit(f['data'][variable_already_set], variable_already_set)
                                    if isinstance(data[best_index], float):
                                        item_value = QTableWidgetItem(str(round(data[best_index],2)))
                                    else:
                                        item_value = QTableWidgetItem(str(data[best_index]))
                                    item_value.setFlags(item_value.flags() & ~Qt.ItemFlag.ItemIsEditable)
                                    table_data.setItem(row, 1, item_value)
                                    
                                    item_unit = QTableWidgetItem(get_unit(variable_already_set))
                                    item_unit.setFlags(item_unit.flags() & ~Qt.ItemFlag.ItemIsEditable)
                                    table_data.setItem(row, 2, item_unit)
                                    
                                #setting the crosshair
                                if f['plot'][f'crosshair_v_time_{crosshair_id}']:
                                    f['plot'][f'crosshair_v_time_{crosshair_id}'].setValue(float(f['data']['GNSS_time'][best_index].timestamp()))
                                    f['plot'][f'crosshair_h_time_{crosshair_id}'].setValue(convert_array_to_unit(float(f['data'][best_variable][best_index]),best_variable))
                                    
                                else:
                                    
                                    pen = pg.mkPen(QColor(0,0,0), width=1, style=QtCore.Qt.PenStyle.DashLine)
                                
                                    crosshair_v = pg.InfiniteLine(
                                        angle=90,
                                        movable=False,
                                        pen = pen
                                     
                                    )
                                    
                                    crosshair_h = pg.InfiniteLine(
                                        angle=0,
                                        movable=False,
                                        pen = pen
                                      
                                    )
                                
                                    plot_widget.addItem(crosshair_v, ignoreBounds=True)
                                    plot_widget.addItem(crosshair_h, ignoreBounds=True)
                                    f['plot'][f'crosshair_v_time_{crosshair_id}'] = crosshair_v
                                    f['plot'][f'crosshair_h_time_{crosshair_id}'] = crosshair_h
                                    f['plot'][f'crosshair_v_time_{crosshair_id}'].setValue(float(f['data']['GNSS_time'][best_index].timestamp()))
                                    f['plot'][f'crosshair_h_time_{crosshair_id}'].setValue(convert_array_to_unit(float(f['data'][best_variable][best_index]),best_variable))
                    else:
                        for row in range(table_data.rowCount()): # Clearing the table contents
                            
                            table_data.setItem(row, 1, QTableWidgetItem(""))
                            table_data.setItem(row, 2, QTableWidgetItem(""))
                       
                        if flight['plot'][f'crosshair_v_time_{crosshair_id}']:
                            plot_widget.removeItem(flight['plot'][f'crosshair_v_time_{crosshair_id}'])
                            plot_widget.removeItem(flight['plot'][f'crosshair_h_time_{crosshair_id}'])
                            flight['plot'][f'crosshair_v_time_{crosshair_id}'] = None
                            flight['plot'][f'crosshair_h_time_{crosshair_id}'] = None
                        
    def on_item_table_1D_changed(self, item):
        """
        This function is here to filter which item has been changed from the table 1D 
        if it is a checkbox, then there will be an update of the graph
        otherwise, we do nothing to minimize computing each time a cell is changed
        """
        if item.column() != 0:
            return
    
        if not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
            return
        
        plot.update_1D_plot(self.flight, self.comboBox_flight_tab1D, self.tableWidget_variable_plot1, self.graph1_tab1D, self.curve_1D_11,self.curve_1D_12)
        plot.update_1D_plot(self.flight, self.comboBox_flight_tab1D, self.tableWidget_variable_plot2, self.graph2_tab1D, self.curve_1D_21,self.curve_1D_22)
        plot.save_checked_variables_1D(self.flight, self.comboBox_flight_tab1D, self.tableWidget_variable_plot1, self.tableWidget_variable_plot2)
        self.handle_checkboxes_on_table_1D(self.tableWidget_variable_plot2)
        self.handle_checkboxes_on_table_1D(self.tableWidget_variable_plot1)
        
    def get_alias(self, flight_name):
        for flight in self.flight:
      
            if flight['file_name'].split(".")[0] == flight_name:
                if flight['metadata']['alias'] != "":
                    return flight['metadata']['alias']
                else:
                    return flight['file_name'].split(".")[0]
                    
                
    def on_button_windbarbs(self, toggle, widget_wind):
        widget_wind.setEnabled(toggle)
        
        
    def on_mouse_hovering(self, point_list):
        print(point_list)
        
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