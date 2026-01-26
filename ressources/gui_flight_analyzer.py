#import time
import os
from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtWidgets import QApplication, QLineEdit, QWidget, QVBoxLayout,QTableWidgetItem ,QButtonGroup , QPushButton, QHBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPen, QBrush
#from database_handler import get_db, DB_PATH
from tinydb import Query
from logging_handler import QTextEditLogger, logger
 
import re
import numpy as np
import sys
from moulinette import Moulinette  
from datetime import datetime
from pathlib  import Path 
from pyqtgraph import ErrorBarItem 
import pyqtgraph as pg
import csv
import json
from scipy.interpolate import interp1d
from scipy.signal import correlate


class App(QtWidgets.QMainWindow):
    
    
    export_update_signal = QtCore.pyqtSignal(str, bool)  # (message: str, enable_export: bool)
    
    

    def __init__(self):
        super(App, self).__init__()

        uic.loadUi(self.resource_path("mainwindow.ui"), self)  # Load the .ui file directly
 
        
        self.flight_dic = {  #this dictionnary will store every detail of a flight file
            "A": {
                "raw_path": None,
                "config_path": None,
                "has_gps": False, #by default
                "flight_date" : None,
                "config_version" : None,
                "probe_number" : None,
                "processed_data" : {
                    "time": None,
                    "date" : None,
                    "ias": None,
                    "glide": None,
                    "alpha": None,
                    "theta": None,
                    "dtheta" : None,
                    "roulis": None,
                    "rho" : None,
                    "lacet": None,
                    "glide_ratio": None
                    },
                "ready_to_be_analyzed" : False,
                "to_analyze" : False,
                "plot_item": None #used to keep tracks of the plot 
            },
            "B": {
                "raw_path": None,
                "config_path": None,
                "has_gps": False, #by default
                "flight_date" : None,
                "config_version" : None,
                "probe_number" : None,
                "processed_data" : {
                    "time": None,
                    "date" : None,
                    "ias": None,
                    "glide": None,
                    "alpha": None,
                    "theta": None,
                    "dtheta" : None,
                    "roulis": None,
                    "rho" : None,
                    "lacet": None,
                    "glide_ratio": None
                    },
                "ready_to_be_analyzed": False,
                "to_analyze" : False, #by default we set the second flight non-analyzable 
                "plot_item": None #used to keep tracks of the plot 
            }
        }
        
        
        self.db = get_db()  # Load or create DB once
        


        self.reference_polar_data = {}  #this dictionnary will store the reference polar points 
        
        self.polar_data = {   #this dictionnary will store the polar point 
            }
        
        
        """
        Tab analyse
        """

        self.export_dialog = ExportDialog(db = self.db, parent = self)  
        self.export_update_signal.connect(self.export_dialog.handle_update)
        
        self.reference_dialog = ReferenceDialog(db = self.db, parent = self)
        
        self.setFocus()  #allow the main windows to receive key press event 

        self.is_editing = False #This variable tracks when the user is editing or not
        self.current_edit_point = 0  # ID of the polar point being edited or removed when clicked
        self.id_point_newly_created = 0 # ID of the polar point being newly created 
        self.load_flight_file_A.clicked.connect(lambda: self.load_file('A'))
        self.load_flight_file_B.clicked.connect(lambda: self.load_file('B'))
        

        self.load_flight_file_B.setEnabled(False)
        self.lineFlightDateB.setEnabled(False)
        self.lineProbeB.setEnabled(False)
        self.lineConfVersionB.setEnabled(False)
        
        self.lineProbeA.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lineProbeB.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lineConfVersionB.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lineConfVersionA.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lineFlightDateB.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lineFlightDateA.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.graph_ias_time.setBackground("w")
        self.graph_ias_time.setLabel('left', 'IAS_COR (Speed)')
        self.graph_ias_time.setLabel('bottom', 'Time (s)')
        self.graph_ias_time.setTitle("IAS_COR vs Time")
        self.graph_ias_time.showGrid(x=True, y=True, alpha=0.3)
        self.graph_ias_time.setEnabled(False)
        


        self.checkBox_showA.toggled.connect(lambda : self.toggle_show("A"))
        self.checkBox_showB.toggled.connect(lambda : self.toggle_show("B"))
        self.checkBox_showB.setEnabled(False)
        self.radioButton_probe_B.setEnabled(False)
        
        self.unit_mode = "glide" #The unit preset for polar graph (can be fineness = Glide ratio or glide = glide in degrees)
        
        self.graph_glide_ias.setBackground("w")
        self.graph_glide_ias.setLabel('left', 'Glide (°)')
        self.graph_glide_ias.setLabel('bottom', 'IAS (m/s)')
        self.graph_glide_ias.setTitle("Glide vs IAS")
        self.graph_glide_ias.setXRange(0,20)
        self.graph_glide_ias.setYRange(-15,5)
        #self.graph_glide_ias.setLimits(xMin=0, xMax=20, yMin=-15, yMax=5)
        self.graph_glide_ias.showGrid(x=True, y=True, alpha=0.3)
        self.graph_glide_ias.setEnabled(True)   
        # Create crosshair lines (invisible by default)
        self.crosshair_v = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('r', width=1, style=QtCore.Qt.PenStyle.DashLine))
        self.crosshair_h = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('r', width=1, style=QtCore.Qt.PenStyle.DashLine))
        self.graph_glide_ias.addItem(self.crosshair_v)
        self.graph_glide_ias.addItem(self.crosshair_h)
        self.crosshair_v.hide()
        self.crosshair_h.hide()
        
        # Plot A (blue) in polar graph -> live data
        self.scatter_a = pg.ScatterPlotItem(brush=pg.mkBrush('b'), pen=pg.mkPen(None), size=10)
        # Plot B (red) in polar graph -> live data
        self.scatter_b = pg.ScatterPlotItem(brush=pg.mkBrush('r'), pen=pg.mkPen(None), size=10)
        # Plot average (purple) -> live data
        self.scatter_avg = pg.ScatterPlotItem(brush=pg.mkBrush(128, 0, 128), pen=pg.mkPen(None), size=10)
        
        # Plot A (blue) in polar graph -> ref data from database 
        self.scatter_ref_a = pg.ScatterPlotItem(brush=pg.mkBrush(66, 81, 245), pen=pg.mkPen(None), size=6)
        # Plot B (red) in polar graph -> ref data from database 
        self.scatter_ref_b = pg.ScatterPlotItem(brush=pg.mkBrush(245, 61, 5), pen=pg.mkPen(None), size=6)
        
        
        self.graph_glide_ias.addItem(self.scatter_a)
        self.graph_glide_ias.addItem(self.scatter_b)
        self.graph_glide_ias.addItem(self.scatter_avg)
        self.graph_glide_ias.addItem(self.scatter_ref_a)
        self.graph_glide_ias.addItem(self.scatter_ref_b)
        # Manually add legend entries (name and corresponding item)
        
        self.graph_glide_ias.addLegend()

        
        
        #SPIN WIDGETS
        for spin in [self.spin_ymin, self.spin_ymax, self.spin_xmin, self.spin_xmax]:
            spin.setDecimals(2)
            spin.setRange(-20, 20)  # Wide enough for typical data
            spin.setSingleStep(1.0)
        
        
        self.spin_ymin.valueChanged.connect(lambda: self.update_view_from_spinboxes(self.graph_glide_ias ,self.spin_xmin,self.spin_xmax, self.spin_ymin, self.spin_ymax))
        self.spin_ymax.valueChanged.connect(lambda: self.update_view_from_spinboxes(self.graph_glide_ias ,self.spin_xmin,self.spin_xmax, self.spin_ymin, self.spin_ymax))
        self.spin_xmin.valueChanged.connect(lambda: self.update_view_from_spinboxes(self.graph_glide_ias ,self.spin_xmin,self.spin_xmax, self.spin_ymin, self.spin_ymax))
        self.spin_xmax.valueChanged.connect(lambda: self.update_view_from_spinboxes(self.graph_glide_ias ,self.spin_xmin,self.spin_xmax, self.spin_ymin, self.spin_ymax))
        
        # Update spinboxes when user zooms/pans
        self.graph_glide_ias.getViewBox().sigXRangeChanged.connect(lambda: self.update_spinboxes_from_view(self.graph_glide_ias ,self.spin_xmin,self.spin_xmax, self.spin_ymin, self.spin_ymax))
        self.graph_glide_ias.getViewBox().sigYRangeChanged.connect(lambda: self.update_spinboxes_from_view(self.graph_glide_ias ,self.spin_xmin,self.spin_xmax, self.spin_ymin, self.spin_ymax))
        self.graph_glide_ias.setXRange(8, 18, padding=0)
        self.graph_glide_ias.setYRange(-3, -8, padding=0)
        self.update_spinboxes_from_view(self.graph_glide_ias ,self.spin_xmin,self.spin_xmax, self.spin_ymin, self.spin_ymax)



        self.buttonClearAll.clicked.connect(self.clear_all)
        
        
        self.button_analyse.clicked.connect(self.analyse_data)
        self.pushButton_addPoint.clicked.connect(self.add_polar_point)
                
        self.clearButton.clicked.connect(self.clear_log)
        
        
        self.buttonRemovePoint.clicked.connect(self.remove_polar_point)
        self.buttonRemovePoint.setEnabled(self.current_edit_point is not None)       
        
        
        self.buttonCompare.toggled.connect(self.toggle_compare_flight)
        
        self.points_glide_table.cellClicked.connect(self.raw_table_clicked)
        self.points_glide_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.points_glide_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        
        self.pushButton_export.clicked.connect(self.display_export_window)
        
        self.radioButton_probe_A.toggled.connect(lambda: self.update_polar_graph(
            self.polar_data,
            reference=False,
            y_axis_mode=self.unit_mode,
            graph_widget=self.graph_glide_ias,
            scatter_items={
            "a": self.scatter_a,
            "b": self.scatter_b,
            "ref_a": self.scatter_ref_a,
            "ref_b": self.scatter_ref_b},
            dynamic = False
        ))

        self.radioButton_probe_B.toggled.connect(lambda: self.update_polar_graph(
            self.polar_data,
            reference=False,
            y_axis_mode=self.unit_mode,
            graph_widget=self.graph_glide_ias,
            scatter_items={
            "a": self.scatter_a,
            "b": self.scatter_b,
            "ref_a": self.scatter_ref_a,
            "ref_b": self.scatter_ref_b},
            dynamic = False
        ))
        
        self.radioButton_ref_probe_A.toggled.connect(lambda: self.update_polar_graph(
            self.reference_polar_data["polar_data"],
            reference=True,
            y_axis_mode=self.unit_mode,
            graph_widget=self.graph_glide_ias,
            scatter_items={
            "a": self.scatter_a,
            "b": self.scatter_b,
            "ref_a": self.scatter_ref_a,
            "ref_b": self.scatter_ref_b},
            dynamic = False
        ))

        self.radioButton_ref_probe_B.toggled.connect(lambda: self.update_polar_graph(
            self.reference_polar_data["polar_data"],
            reference=True,
            y_axis_mode=self.unit_mode,
            graph_widget=self.graph_glide_ias,
            scatter_items={
            "a": self.scatter_a,
            "b": self.scatter_b,
            "ref_a": self.scatter_ref_a,
            "ref_b": self.scatter_ref_b},
            dynamic = False
        ))
        


        self.radioButton_ref_probe_A.setEnabled(False)
        self.radioButton_ref_probe_B.setEnabled(False)


        self.radio_button_toggle_angle.toggled.connect(self.change_polar_unit)
        self.radio_button_toggle_fineness.toggled.connect(self.change_polar_unit)
        self.radio_button_toggle_angle.toggled.connect(
            lambda checked: self.radio_button_toggle_angle_compare.setChecked(checked)
        )
        self.radio_button_toggle_fineness.toggled.connect(
            lambda checked: self.radio_button_toggle_fineness_compare.setChecked(checked)
        )


        #self.radioButton_AVG.toggled.connect(lambda: self.update_polar_graph(self.polar_data))
        
        self.exit_button.clicked.connect(QtWidgets.QApplication.quit)  # Clean exit
        
        self.button_load_reference.clicked.connect(self.display_reference_window)
        
        
        icon_path = self.external_path("logo_inv.ico")  # or "icon.png"
        self.setWindowIcon(QtGui.QIcon(str(icon_path)))
        
        self.logbox_handler = QTextEditLogger(self.logBox)
        self.logBox.verticalScrollBar().setValue(self.logBox.verticalScrollBar().maximum())
        
        logger.addHandler(self.logbox_handler) 
        
        """
        Tab compare
        """
        self.search_button_compare.clicked.connect(lambda : self.search("compare", self.table_returned_results_compare))
        
        self.table_returned_results_compare.horizontalHeader().setStretchLastSection(True)
        #self.table_returned_results.cellClicked.connect(self.parent.raw_table_clicked)
        self.table_returned_results_compare.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_returned_results_compare.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        
        self.graph_glide_ias_compare.setBackground("w")
        self.graph_glide_ias_compare.setLabel('left', 'Glide (°)')
        self.graph_glide_ias_compare.setLabel('bottom', 'IAS (m/s)')
        self.graph_glide_ias_compare.setTitle("Glide vs IAS")
        self.graph_glide_ias_compare.setXRange(0,20)
        self.graph_glide_ias_compare.showGrid(x=True, y=True, alpha=0.3)
        self.graph_glide_ias_compare.setEnabled(True)   
        
        self.graph_vxvz.setBackground("w")
        self.graph_vxvz.setLabel('left', 'Vz (m/s)')
        self.graph_vxvz.setLabel('bottom', 'Vx (m/s)')
        self.graph_vxvz.setTitle("Vx vs Vz")
        # self.graph_vxvz.setXRange(-3,15)
        # self.graph_vxvz.setXRange(-3,15)
        self.graph_vxvz.showGrid(x=True, y=True, alpha=0.3)
        self.graph_vxvz.setEnabled(True)
        
        

        # Plot A (blue) in polar graph compare 
        self.scatter_a_compare = pg.ScatterPlotItem(brush=pg.mkBrush('b'), pen=pg.mkPen(None), size=10)
        # Plot B (red) in polar graph compare
        self.scatter_b_compare = pg.ScatterPlotItem(brush=pg.mkBrush('r'), pen=pg.mkPen(None), size=10)
        # Plot average (purple) 
        #self.scatter_avg = pg.ScatterPlotItem(brush=pg.mkBrush(128, 0, 128), pen=pg.mkPen(None), size=10)
        # Plot A (blue) in polar graph compare 
        self.scatter_a_vxvz = pg.ScatterPlotItem(brush=pg.mkBrush('b'), pen=pg.mkPen(None), size=10)
        # Plot B (red) in polar graph compare
        self.scatter_b_vxvz = pg.ScatterPlotItem(brush=pg.mkBrush('r'), pen=pg.mkPen(None), size=10)
        # Plot average (purple) 
        #self.scatter_avg = pg.ScatterPlotItem(brush=pg.mkBrush(128, 0, 128), pen=pg.mkPen(None), size=10)
        
        self.graph_glide_ias_compare.addItem(self.scatter_a_compare)
        self.graph_glide_ias_compare.addItem(self.scatter_b_compare)
        self.graph_vxvz.addItem(self.scatter_a_vxvz)
        self.graph_vxvz.addItem(self.scatter_b_vxvz)
        
        #SPIN WIDGETS GRAPH COMPARE 
        for spin in [self.spin_ymin_compare, self.spin_ymax_compare, self.spin_xmin_compare, self.spin_xmax_compare]:
            spin.setDecimals(2)
            spin.setRange(-20, 20)  # Wide enough for typical data
            spin.setSingleStep(1.0)
        
        
        self.spin_ymin_compare.valueChanged.connect(lambda: self.update_view_from_spinboxes(self.graph_glide_ias_compare ,self.spin_xmin_compare,self.spin_xmax_compare, self.spin_ymin_compare, self.spin_ymax_compare))
        self.spin_ymax_compare.valueChanged.connect(lambda: self.update_view_from_spinboxes(self.graph_glide_ias_compare ,self.spin_xmin_compare,self.spin_xmax_compare, self.spin_ymin_compare, self.spin_ymax_compare))
        self.spin_xmin_compare.valueChanged.connect(lambda: self.update_view_from_spinboxes(self.graph_glide_ias_compare ,self.spin_xmin_compare,self.spin_xmax_compare, self.spin_ymin_compare, self.spin_ymax_compare))
        self.spin_xmax_compare.valueChanged.connect(lambda: self.update_view_from_spinboxes(self.graph_glide_ias_compare ,self.spin_xmin_compare,self.spin_xmax_compare, self.spin_ymin_compare, self.spin_ymax_compare))
        
        # Update spinboxes when user zooms/pans
        self.graph_glide_ias_compare.getViewBox().sigXRangeChanged.connect(lambda: self.update_spinboxes_from_view(self.graph_glide_ias_compare ,self.spin_xmin_compare,self.spin_xmax_compare, self.spin_ymin_compare, self.spin_ymax_compare))
        self.graph_glide_ias_compare.getViewBox().sigYRangeChanged.connect(lambda: self.update_spinboxes_from_view(self.graph_glide_ias_compare ,self.spin_xmin_compare,self.spin_xmax_compare, self.spin_ymin_compare, self.spin_ymax_compare))
        self.graph_glide_ias_compare.setXRange(8, 16, padding=0)
        self.graph_glide_ias_compare.setYRange(-16, 6, padding=0)
        self.update_spinboxes_from_view(self.graph_glide_ias_compare ,self.spin_xmin_compare,self.spin_xmax_compare, self.spin_ymin_compare, self.spin_ymax_compare)
        
        #SPIN WIDGETS GRAPH VXVZ
        for spin in [self.spin_ymin_vxvz, self.spin_ymax_vxvz, self.spin_xmin_vxvz, self.spin_xmax_vxvz]:
            spin.setDecimals(2)
            spin.setRange(-20, 20)  # Wide enough for typical data
            spin.setSingleStep(1.0)
        
        
        self.spin_ymin_vxvz.valueChanged.connect(lambda: self.update_view_from_spinboxes(self.graph_vxvz ,self.spin_xmin_vxvz,self.spin_xmax_vxvz, self.spin_ymin_vxvz, self.spin_ymax_vxvz))
        self.spin_ymax_vxvz.valueChanged.connect(lambda: self.update_view_from_spinboxes(self.graph_vxvz ,self.spin_xmin_vxvz,self.spin_xmax_vxvz, self.spin_ymin_vxvz, self.spin_ymax_vxvz))
        self.spin_xmin_vxvz.valueChanged.connect(lambda: self.update_view_from_spinboxes(self.graph_vxvz ,self.spin_xmin_vxvz,self.spin_xmax_vxvz, self.spin_ymin_vxvz, self.spin_ymax_vxvz))
        self.spin_xmax_vxvz.valueChanged.connect(lambda: self.update_view_from_spinboxes(self.graph_vxvz ,self.spin_xmin_vxvz,self.spin_xmax_vxvz, self.spin_ymin_vxvz, self.spin_ymax_vxvz))
        
        # Update spinboxes when user zooms/pans
        self.graph_vxvz.getViewBox().sigXRangeChanged.connect(lambda: self.update_spinboxes_from_view(self.graph_vxvz ,self.spin_xmin_vxvz,self.spin_xmax_vxvz, self.spin_ymin_vxvz, self.spin_ymax_vxvz))
        self.graph_vxvz.getViewBox().sigYRangeChanged.connect(lambda: self.update_spinboxes_from_view(self.graph_vxvz ,self.spin_xmin_vxvz,self.spin_xmax_vxvz, self.spin_ymin_vxvz, self.spin_ymax_vxvz))
        self.graph_vxvz.setXRange(9, 15, padding=0)
        self.graph_vxvz.setYRange(-3, 1, padding=0)
        self.update_spinboxes_from_view(self.graph_vxvz ,self.spin_xmin_vxvz,self.spin_xmax_vxvz, self.spin_ymin_vxvz, self.spin_ymax_vxvz)        
        
        
        self.table_returned_results_compare.cellClicked.connect(self.display_selected_polar_data_compare)
        
        self.radioButton_probe_A_compare.toggled.connect(lambda: self.change_visibility_compare_tab("A"))
        self.radioButton_probe_B_compare.toggled.connect(lambda: self.change_visibility_compare_tab("B"))
        
        
        self.legend_compare = pg.LegendItem()
        self.legend_compare.setParentItem(self.graph_glide_ias_compare.getPlotItem())
        self.legend_compare.anchor(itemPos=(1, 0), parentPos=(1, 0), offset=(-10, 10))
        
        self.legend_vxvz = pg.LegendItem()
        self.legend_vxvz.setParentItem(self.graph_vxvz.getPlotItem())
        self.legend_vxvz.anchor(itemPos=(1, 0), parentPos=(1, 0), offset=(-10, 10))
        
        self.radio_button_toggle_angle_compare.toggled.connect(self.change_polar_unit)
        self.radio_button_toggle_fineness_compare.toggled.connect(self.change_polar_unit)
        self.radio_button_toggle_angle_compare.toggled.connect(
            lambda checked: self.radio_button_toggle_angle.setChecked(checked)
        )
        self.radio_button_toggle_fineness_compare.toggled.connect(
            lambda checked: self.radio_button_toggle_fineness.setChecked(checked)

        )
        
        """
        Tab manage
        """
        self.search_button_manage.clicked.connect(lambda : self.search("manage", self.table_returned_results_manage))
        
        self.table_returned_results_manage.horizontalHeader().setStretchLastSection(True)
        self.table_returned_results_manage.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_returned_results_manage.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        
        self.pushButton_edit_entry.setCheckable(True)  # Permet de l'utiliser en mode ON/OFF
        self.pushButton_edit_entry.clicked.connect(self.toggle_edit_database_manage)
        self.pushButton_edit_entry.toggled.connect(self.on_edit_manage_toggled)
        
        self.pushButton_delete_entry.clicked.connect(self.delete_selected_entry_manage)
        
        self.pushButton_export_entry.clicked.connect(self.export_selected_entry_manage)
        
        self.edit_mode_manage = False
        
        #We store each error bar items to manage them easily 
        self.error_bar_items = {
            "A": {"glide_ias": {"Glide_ratio": None, "Glide": None},
                  "glide_ias_compare": {"Glide_ratio": None, "Glide": None},
                  "vxvz": None},
            "B": {"glide_ias": {"Glide_ratio": None, "Glide": None},
                  "glide_ias_compare": {"Glide_ratio": None, "Glide": None},
                  "vxvz": None}}
        
    def resource_path(self, relative_path):
        #Get absolute path to resource (for PyInstaller and development) , I don't really understand but it seems useful for lauching as exe maybe for database folder
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
    
    
    def print_database(self):
 
        records = self.db.all()
        for record in records:
            print(record)
            
    def clear_database(self):
        self.db.truncate()
        
    def load_file(self, file_type):
        
        logger.detail("STATE LOAD FILE")
        
        # Préfixes de commentaires possibles
        comment_prefixes = [r"\$", r"//"]
        
        # Types de métadonnées à détecter
        version_keywords = ["Version", "version"]
        probe_keywords = ["Probe", "probe", "Sonde", "sonde"]
        firmware_keywords =["Firmware", "firmware"]
        
        
        def build_pattern(prefixes, keywords):
            patterns = []
            for prefix in prefixes:  # ✅ il faut boucler ici aussi
                for keyword in keywords:
                    pattern = rf"^\s*{prefix}\s*{keyword}\s*[:=]?\s*(?P<value>.+)?$"
                    patterns.append(pattern)
            return patterns
            
        
        version_patterns = build_pattern(comment_prefixes, version_keywords)
        probe_patterns = build_pattern(comment_prefixes, probe_keywords)
        firmware_patterns = build_pattern(comment_prefixes, firmware_keywords)
        version_is_checked = False
        probe_is_checked = False
        self.clear_flight(file_type) #clearing the previous data
        self.flight_dic[file_type]['raw_path'] = QtWidgets.QFileDialog.getOpenFileName(self, "Open raw data file", "", ".TXT Files (*.txt);;All Files (*)")
        if self.flight_dic[file_type]['raw_path']:
            self.flight_dic[file_type]['raw_path'] = Path(self.flight_dic[file_type]['raw_path'][0]) 
     
            if (self.flight_dic[file_type]['raw_path'].suffix == '.txt' or self.flight_dic[file_type]['raw_path'].suffix == '.csv'):
                logger.info(f"File chosen for flight {file_type} : {self.flight_dic[file_type]['raw_path']}")
                #self.add_log(f"File chosen for flight {file_type} : {self.flight_dic[file_type]['raw_path']}")
                                   
                
                #Opening the config file associated with the raw data
                try:
                    found = False
                    with open(self.flight_dic[file_type]["raw_path"], "r", encoding="utf-8") as file:
                        
                        #Fetching probe number in raw file
                        for line in file:
                            for pattern in probe_patterns:
                                match = re.match(pattern, line, re.IGNORECASE)
                                if match:
                                    logger.info(f"Probe {match.group('value').strip()}")
                                    self.flight_dic[file_type]['probe_number'] = line.split(":")[1].strip()  # Extraire le numéro de la sonde
                                    found = True
                                    break  # Sortie une fois trouvé
                            if found:
                                break
                        if not found:   
                            self.flight_dic[file_type]['ready_to_be_analyzed'] = False
                            logger.error(f"no probe number found for file {self.flight_dic[file_type]['raw_path']}")
                            
                            return None
                        
                                
                        if file_type == 'A':
                            self.lineProbeA.setText(self.flight_dic[file_type]['probe_number'])
                        elif file_type == 'B':
                            self.lineProbeB.setText(self.flight_dic[file_type]['probe_number'])
                                
                        config_filename = f"config_{self.flight_dic[file_type]['probe_number']}.txt"
                        config_directory = self.external_path("config")
                        
                        self.flight_dic[file_type]['config_path'] = config_directory / config_filename #converting with ressource_path for portability in .exe 
                        #self.add_log(self.flight_dic[file_type]['config_path'])
                        logger.info(f"config file path : {self.flight_dic[file_type]['config_path']}")
                        
                       
                        number_line_pattern = re.compile(r'^\s*[-+]?\d')  # line starts with a number (could be negative or positive)
                        for line in file:
                            if number_line_pattern.match(line):
                                values = line.rstrip().split(' ')  # On récupère chaque valeur par lignes en sachant qu'elles sont séparées par un espace
    
                                if int(values[26]) != 0: #if we found a year that is consistent (year is at the 26th colomns in the raw data, may be due to change) 
                                    self.flight_dic[file_type]["has_gps"] = True
                                    self.flight_dic[file_type]['flight_date']= datetime(int(values[26]),int(values[27]),int(values[28])).strftime("%Y-%m-%d")
                                    if file_type == 'A':
                                        self.lineFlightDateA.setText(self.flight_dic[file_type]['flight_date'])  #displaying the date with the format YYYY-MM-DD
                                    elif file_type == 'B':
                                        self.lineFlightDateB.setText(self.flight_dic[file_type]['flight_date'])
                                    break
                            
                        if not self.flight_dic[file_type]["has_gps"]:
                            logger.warning("No GPS time data available for this flight")
                            #self.add_log("No GPS time data available for this flight")
                        
                            if file_type == 'A':
                                self.lineFlightDateA.setText('NO GPS')
                            elif file_type == 'B':
                                self.lineFlightDateB.setText('NO GPS')

                except FileNotFoundError as e:
                    logger.error(f"error trying to open the raw file: {e}")
                    #self.add_log('error trying to open the config file')
                    return None
                
                
                if self.flight_dic[file_type]['config_path'].exists():
                    logger.detail("config path exists")
                    try: 

                        # we check if the config file provided is suited for the raw data 
                        with open(self.flight_dic[file_type]['config_path'], 'r') as f:

                            found = False
                            for line in f:
                                line = line.strip()  # Remove leading/trailing spaces
                                
                                for pattern in probe_patterns:
                                    match = re.match(pattern, line, re.IGNORECASE)
                                    if match:
                                        key, value = line.split("=", 1)  # Split at first '=' to handle unexpected formats
                                        key = key.strip()
                                        value = value.strip().rstrip(";")  # Remove trailing ';'
                                        found = True
                                        
                                        if value == self.flight_dic[file_type]['probe_number']:
                                            logger.info(f"Right config found at {self.flight_dic[file_type]['config_path']}")
                                            #self.add_log(f"Right config found at {self.flight_dic[file_type]['config_path']}")
                                            probe_is_checked = True
                                            
                                            break

                                        else : 
                                            probe_is_checked = False
                                            logger.error(f"config file provided does not match with the probe used. Probe used : {self.flight_dic[file_type]['probe_number']} and config is for probe : {value}")
                                            #self.add_log(f"Error : config file provided does not match with the probe used. Probe used : {self.flight_dic[file_type]['probe_number']} and config is for probe : {value}")
                                            return 
                                    if found:
                                        break
                            if not found :        
                                self.flight_dic[file_type]['ready_to_be_analyzed'] = False                            
                                logger.error(f"no probe number found in file {self.flight_dic[file_type]['config_path']}")
                                return None
                            
                            #Fetching config version in config file
                            found = False
                            f.seek(0)
                            for line in f:
                                for pattern in version_patterns:
                                    match = re.match(pattern, line.strip(), re.IGNORECASE)
                                    if match:                        
                                        found = True
                                        key, value = line.split("=", 1)  # Split at first '=' to handle unexpected formats
                                        key = key.strip()
                                        value = value.strip().rstrip(";")  # Remove trailing ';'
                                        version_is_checked = True
                                        self.flight_dic[file_type]['config_version'] = value
                                        
                                        if file_type == 'A':
                                            self.lineConfVersionA.setText(self.flight_dic[file_type]['config_version'])
                                        elif file_type == 'B':
                                            self.lineConfVersionB.setText(self.flight_dic[file_type]['config_version'])
                                        break
                                if found:
                                    break
                                    
                            if not found : 
                                self.flight_dic[file_type]['ready_to_be_analyzed'] = False                            
                                logger.error(f"config version has not been found in file {self.flight_dic[file_type]['config_path']}")
                                return None
                            
                    except FileNotFoundError as e:
                        logger.error(f"error trying to open the config file: {e}")
                        #self.add_log('error trying to open the config file')
                        return None          
                else : 
                    logger.error(f"config not found for {self.flight_dic[file_type]['probe_number']} probe")
                    self.flight_dic[file_type]['ready_to_be_analyzed'] = False
            else :
                logger.error('Wrong type of file, please select a flight file in .csv or .txt')
                #self.add_log('Wrong type of file, please select a flight file in .csv or .txt')
            
            if probe_is_checked and version_is_checked:
                self.flight_dic[file_type]['ready_to_be_analyzed'] = True
                self.flight_dic[file_type]['to_analyze'] = True
                logger.info(f"Flight {file_type} is ready to be analyzed :")
                #self.add_log(f"Flight {file_type} ready to be analyzed :")



    def add_log(self, log):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logBox.append(f'<span style="color: blue;">[{timestamp}]</span> {log}')
        self.logBox.verticalScrollBar().setValue(self.logBox.verticalScrollBar().maximum())
    
    def clear_log(self):
        logger.detail("STATE CLEAR LOG")
        self.logBox.clear()
    
    
    def toggle_show(self, flight):
        #Show or not the plot on the ias vs time graph 
        if flight == "A":
            if self.checkBox_showA.isChecked():
                self.graph_ias_time.addItem(self.flight_dic[flight]["plot_item"])
            else:
                self.graph_ias_time.removeItem(self.flight_dic[flight]["plot_item"])
        if flight == "B":
            if self.checkBox_showB.isChecked():
                self.graph_ias_time.addItem(self.flight_dic[flight]["plot_item"])
            else:
                self.graph_ias_time.removeItem(self.flight_dic[flight]["plot_item"])
        
    
    def toggle_compare_flight(self):
        """Enables or disables buttons based for the second flight"""
        logger.detail("STATE TOGGLE COMPARE FLIGHT")
        if self.buttonCompare.isChecked():
            self.flight_dic["B"]["to_analyze"]= True
            
            #self.add_log("Dual analysis enabled : provide two raw files")
            logger.info("Dual analysis enabled : provide two raw files")
            self.export_update_signal.emit("Dual analysis enabled", True)
            
            self.export_update_signal.emit("Dual analysis enabled", True)
            self.load_flight_file_B.F(True)  # Enable the button if the radio is checked
            self.checkBox_showB.setEnabled(True)
            self.radioButton_probe_B.setEnabled(True)
            self.lineFlightDateB.setEnabled(True)
            self.lineProbeB.setEnabled(True)
            self.lineConfVersionB.setEnabled(True) 
            
            # self.export_dialog.button_export_flight_file_B.setEnabled(True)
        else:
            #self.add_log("Dual analysis disabled")
            logger.info("Dual analysis disabled")
            self.flight_dic["B"]["to_analyze"]= False
            self.clear_all()
            #Remove all polar data -> Not efficient but easier to implement 
        
            self.export_update_signal.emit("Dual analysis enabled", False)
            self.load_flight_file_B.setEnabled(False)  # Disable the button if the radio is unchecked
            self.checkBox_showB.setEnabled(False)
            self.radioButton_probe_B.setEnabled(False)
            self.lineFlightDateB.setEnabled(False)
            self.lineProbeB.setEnabled(False)
            self.lineConfVersionB.setEnabled(False)
            # self.export_dialog.button_export_flight_file_B.setEnabled(False)



    def datetime_resampling(self, time_array, date_array, target_interval=100): #This function is used for interpolating datetime objects, which can't do the np.interp()
        """
        Interpolates a list of datetime objects based on original_time, returns datetime objects.
        """
        logger.detail("STATE DATETIME RESAMPLING")
        # Ensure arrays are numpy arrays
        time_array = np.array(time_array)
        date_array = np.array([dt.timestamp() for dt in date_array])

        # Create regular time points
        new_time_array = np.arange(time_array[0], time_array[-1], target_interval) #Recreating the time serie at a fixed interval
        

        # Interpolate the timestamps
        interpolator = interp1d(time_array, date_array, kind='cubic', bounds_error=False, fill_value="extrapolate")    
        interpolated_timestamps = interpolator(new_time_array)
        
        # Convert back to datetime
        interpolated_dates = [datetime.fromtimestamp(ts) for ts in interpolated_timestamps]
        
        
        
        return interpolated_dates


    def resampling(self, time_array, data_array, target_interval=100):
        logger.detail("STATE RESAMPLING")
        # Ensure arrays are numpy arrays
        time_array = np.array(time_array)
        data_array = np.array(data_array)

        # Create regular time points
        new_time_array = np.arange(time_array[0], time_array[-1], target_interval) #Recreating the time serie at a fixed interval 
        
        # Create the interpolation function (linear interpolation by default)
        interpolator = interp1d(time_array, data_array, kind='cubic', bounds_error=False, fill_value="extrapolate")
        
        # Apply interpolation
        new_data_array = interpolator(new_time_array)
        
        
        return new_time_array, new_data_array

            
    def analyse_data(self):
        
        logger.detail("STATE ANALYSE")
  
        color_map = {
            "A" : 'b',  #Flight A in blue
            "B" : 'r'}  #Flight B in red
        
        #calculating
        original_time = None

        for flight_id, flight_data in self.flight_dic.items():
            if self.flight_dic[flight_id]["to_analyze"]  and  self.flight_dic[flight_id]["ready_to_be_analyzed"]:
                logger.info(f'analyzing flight {flight_id}, this can take a few seconds')
                #self.add_log(f'analyzing flight {flight_id}, this can take a few seconds')
                if flight_data.get("raw_path").exists():
                    self.flight_dic[flight_id]["processed_data"]['time'], self.flight_dic[flight_id]["processed_data"]['date'], self.flight_dic[flight_id]["processed_data"]['ias'], self.flight_dic[flight_id]["processed_data"]['glide'], self.flight_dic[flight_id]["processed_data"]['alpha'],self.flight_dic[flight_id]["processed_data"]['theta'],self.flight_dic[flight_id]["processed_data"]['dtheta'],self.flight_dic[flight_id]["processed_data"]['roulis'],self.flight_dic[flight_id]["processed_data"]['rho'],self.flight_dic[flight_id]["processed_data"]['lacet'] = Moulinette(self.flight_dic[flight_id]["raw_path"], self.flight_dic[flight_id]["config_path"])
                    original_time = self.flight_dic[flight_id]["processed_data"]['time']
                    for key, values in self.flight_dic[flight_id]["processed_data"].items():
                        if key == "time": #No need to interpolate "time" because it will be synthetized with resampling()
                            continue
                        elif key == "date":
                            #self.flight_dic[flight_id]["processed_data"]['date'] = np.nan_to_num(self.flight_dic[flight_id]["processed_data"]['date'], nan=0.0) #replacing NaN to 0 otherwise it will cause error in resampling
                            # self.flight_dic[flight_id]["processed_data"]['date'] = self.datetime_resampling(original_time, self.flight_dic[flight_id]["processed_data"]["date"],100) #RESAMPLING
                            continue  #We don't manage the date for the moment
                        else :
                            self.flight_dic[flight_id]["processed_data"][key] = np.nan_to_num(self.flight_dic[flight_id]["processed_data"][key], nan=0.0) #replacing NaN to 0 otherwise it will cause error in resampling
                            logger.detail(f"Resampling {key}")
                            # self.add_log(f"Resampling {key}")
                            self.flight_dic[flight_id]["processed_data"]['time'] , self.flight_dic[flight_id]["processed_data"][key] = self.resampling(original_time, self.flight_dic[flight_id]["processed_data"][key],100) #RESAMPLING
                            
                    #Once the resampling of all data is done, we shift the time serie so that it starts at 0 and can be compared with other flights (each raw flights starts at a different time)
    
                    self.flight_dic[flight_id]["processed_data"]['time'] = self.flight_dic[flight_id]["processed_data"]['time'] - self.flight_dic[flight_id]["processed_data"]['time'][0]
 

        
       
        if self.buttonCompare.isChecked(): #If we compare two flights, we sync them in time
            for flight_id, flight_data in self.flight_dic.items():
                if self.flight_dic[flight_id]["to_analyze"]  and  self.flight_dic[flight_id]["ready_to_be_analyzed"]:
                    #Adjust B according to A 
                    self.sync(self.flight_dic["A"], self.flight_dic["B"])




        
        
        #plotting
                    
        for flight_id, flight_data in self.flight_dic.items():
            if self.flight_dic[flight_id]["to_analyze"]  and  self.flight_dic[flight_id]["ready_to_be_analyzed"]:
                if flight_data.get("raw_path").exists():
                    color = color_map.get(flight_id, 'k')
                    if self.flight_dic[flight_id]["plot_item"] is None: #we have to check this otherwise it will be impossible to clear the previous plot item 
                        self.flight_dic[flight_id]["plot_item"] = self.plot(self.flight_dic[flight_id]["processed_data"]['time'], self.flight_dic[flight_id]["processed_data"]['ias'], self.graph_ias_time,color)
            
                    
                    self.flight_dic[flight_id]["to_analyze"] = False #Once it is analyzed we don't need to do it again later, unless we load a new file 
                    
        self.pushButton_addPoint.setEnabled(True) 
        self.buttonRemovePoint.setEnabled(True)
        


            
    def plot(self, x, y, graph, color):
        logger.detail(f"STATE PLOT x={x} y={y} graph={graph}")
        graph.setEnabled(True)
        plot = graph.plot(x, y, pen=color)
        graph.setBackground("w")      
        return plot
        

    
    def sync(self, flight_a, flight_b):
        
        logger.detail("STATE SYNC")
        ias_a = np.array(flight_a["processed_data"]["ias"])    #We use the IAS to detect the lag because the shape is better for correlation
        ias_b = np.array(flight_b["processed_data"]["ias"])

        
        min_len = min(len(ias_a), len(ias_b))
        ias_a = ias_a[:min_len] #sizing to both length the two output otherwise calculation became unaccurate
        ias_b = ias_b[:min_len]
    
        # Normalize both signals: remove mean and scale by std
        ias_a = (ias_a - np.mean(ias_a)) / np.std(ias_a)
        ias_b = (ias_b - np.mean(ias_b)) / np.std(ias_b)
    
   
      
        
    
        # Compute full cross-correlation
        correlation = correlate(ias_a, ias_b, mode="full")
        lags = np.arange(-len(ias_b)+1, len(ias_a))
        lag = lags[np.argmax(correlation)]
        
        #flight_b["processed_data"]["date"]=np.roll(flight_b["processed_data"]["date"],  lag)
        flight_b["processed_data"]["ias"]=np.roll(flight_b["processed_data"]["ias"], lag)
        flight_b["processed_data"]["glide"]=np.roll(flight_b["processed_data"]["glide"], lag)
        flight_b["processed_data"]["alpha"]=np.roll(flight_b["processed_data"]["alpha"], lag)
        flight_b["processed_data"]["theta"]= np.roll(flight_b["processed_data"]["theta"], lag)
        flight_b["processed_data"]["dtheta"]= np.roll(flight_b["processed_data"]["dtheta"], lag)
        flight_b["processed_data"]["roulis"]= np.roll(flight_b["processed_data"]["roulis"], lag)
        flight_b["processed_data"]["rho"]= np.roll(flight_b["processed_data"]["rho"], lag)
        flight_b["processed_data"]["lacet"]= np.roll(flight_b["processed_data"]["lacet"], lag)
        #flight_b["processed_data"]["glide_ratio"]= np.roll(flight_b["processed_data"]["glide_ratio"], lag)
        #flight_b["processed_data"]["time"] = np.roll(flight_b["processed_data"]["time"], lag)

        
        
 
        
  
 
    def add_polar_point(self):
        logger.detail("STATE ADD POLAR POINT")
        self.polar_data[self.id_point_newly_created]= {
        "ID" : None,
        "Xmin_second" : 400000,  #  by default
        "Xmax_second" : 500000, #  by default
        "Xmin_date" : None,  #  
        "Xmax_date" : None, #  
        "IAS_a": None,
        "Glide_a": None,
        "Error_glide_a": None,
        "Alpha_a": None,
        "Theta_a" : None,
        "DTheta_a" : None,
        "Lacet_a" : None,
        "Roulis_a": None,
        "Rho_a" : None,
        "Glide_ratio_a": None,
        "Error_glide_ratio_a": None,
        "IAS_b": None,
        "Glide_b": None,
        "Error_glide_b": None,
        "Alpha_b": None,
        "Theta_b" : None,
        "DTheta_b" : None,
        "Lacet_b" : None,
        "Roulis_b": None,
        "Rho_b" : None,
        "Glide_ratio_b": None,
        "Error_glide_ratio_b": None,
        "Label": None,
        "ROI": None}
         
        
        
        
    
        self.update_polar_table(self.points_glide_table,self.polar_data)   
        self.update_values()
        #self.add_log(f'New point created {self.polar_data[self.id_point_newly_created]["ID"]}')
        self.id_point_newly_created += 1  #This variable is only required to create a new point but is never used. To keep tracks of point we instead use its key 'ID'
        
        self.current_edit_point = (len(self.polar_data) - 1) #We set the new point to edit as the last one created 
        
        self.edit_point()
        self.update_values()
        
    def clear_polar_data(self):
        
        logger.detail("STATE CLEAR POLAR DATA")
        for point in self.polar_data.values():
            roi = point.get("ROI")
            if roi is not None:
                try:
                    self.graph_ias_time.removeItem(roi)  # or self.plot_widget.removeItem(roi), depending on your naming
                except Exception as e:
                    logger.error(f"Failed to remove ROI: {e}")
                    #self.add_log(f"Failed to remove ROI: {e}")
        
        self.polar_data = {}
  
        self.id_point_newly_created = 0  # Reset the point counter as well, if needed
        self.update_polar_table(self.points_glide_table,self.polar_data)
        
 
        self.crosshair_v.hide()
        self.crosshair_h.hide()
        

        self.update_polar_graph(#Used to delete the point on the glide ias graph
            self.polar_data,
            reference=False,
            y_axis_mode=self.unit_mode,
            graph_widget=self.graph_glide_ias,
            scatter_items={
            "a": self.scatter_a,
            "b": self.scatter_b,
            "ref_a": self.scatter_ref_a,
            "ref_b": self.scatter_ref_b},
            dynamic = True
        )
        
        for item in [self.scatter_ref_a, self.scatter_ref_b]:
            try:
                self.graph_glide_ias.removeItem(item)
            except Exception as e:
                logger.warning(f"Couldn't remove reference scatter item: {e}")
                
        self.scatter_ref_a.setData([], [])
        self.scatter_ref_b.setData([], [])
        self.update_polar_table(self.points_glide_table,self.polar_data) #Used to delete on the table
       
        self.update_values()
        self.current_edit_point = None #Prevent crashes when deleting too much points

    def remove_polar_point(self):
        logger.detail("STATE CLEAR POLAR POINT")
        self.exit_edit()
        
        if self.current_edit_point == None :
            logger.warning("No point selected to be removed")
            #self.add_log("No point selected to be removed")
            return
        
        key_to_delete = None

        for key, point in self.polar_data.items():
            if point["ID"] == self.current_edit_point:
                key_to_delete = key
                if point['ROI'] is not None:
                    self.graph_ias_time.removeItem(point['ROI']) #We have to remove it from the graph before deleting the point
                break  # Stop after finding the first match
        
        if key_to_delete is not None:
            del self.polar_data[key_to_delete]
            logger.info(f'Delete point {self.current_edit_point}')
            #self.add_log(f'Delete point {self.current_edit_point}')
        
        
        # if hasattr(self, 'error_bar_a'): 
        #     self.graph_glide_ias.removeItem(self.error_bar_a)   #Remove previous bar item
            
        # if hasattr(self, 'error_bar_b'):
        #     self.graph_glide_ias.removeItem(self.error_bar_b)   #Remove previous bar item
        
        self.crosshair_v.hide()
        self.crosshair_h.hide()
        

        self.update_polar_graph(#Used to delete the point on the glide ias graph
            self.polar_data,
            reference=False,
            y_axis_mode=self.unit_mode,
            graph_widget=self.graph_glide_ias,
            scatter_items={
            "a": self.scatter_a,
            "b": self.scatter_b,
            "ref_a": self.scatter_ref_a,
            "ref_b": self.scatter_ref_b},
            dynamic = True
        )
        # if self.reference_polar_data["polar_data"]:
        #     self.update_polar_graph(#Used to delete the point on the glide ias graph
        #         self.reference_polar_data["polar_data"],
        #         reference=True,
        #         y_axis_mode=self.unit_mode,
        #         graph_widget=self.graph_glide_ias,
        #         scatter_items={
        #         "a": self.scatter_a,
        #         "b": self.scatter_b,
        #         "ref_a": self.scatter_ref_a,
        #         "ref_b": self.scatter_ref_b},
        #         dynamic = True
        #     )
        self.update_polar_table(self.points_glide_table,self.polar_data) #Used to delete on the table
       
        self.update_values()
        self.current_edit_point = None #Prevent crashes when deleting too much points
        

    def update_polar_table(self, table_widget, polar_data): #Each time we create or remove a new polar point, we build again the table 
        logger.detail("STATE UPDATE POLAR TABLE")
        table_widget.blockSignals(True) # on bloque les signaux pour éviter d'engendrer des problèmes lorsqu'on édite le label
        table_widget.setRowCount(0)  # Clear the table
        
        for i, (point_id, point_data) in enumerate(polar_data.items()):
      
            row_base = i * 2  # 2 rows per point
            table_widget.insertRow(row_base)
            table_widget.insertRow(row_base +1 )


            point_data["ID"]= i
            
            table_widget.setSpan(row_base, 0, 2, 1)  # Span 2 rows for the ID
            id_item = QTableWidgetItem(str(point_data["ID"]))
            id_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base, 0, id_item)
            
            

            
            #*************A DATA*********************
    
            # IAS A (read-only)

            ias_item_a = QTableWidgetItem(str(point_data["IAS_a"]))
            ias_item_a.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled) #makes the cell uneditable
            table_widget.setItem(row_base, 1, ias_item_a)
     
            # Glide A (read-only)
  
            glide_item_a = QTableWidgetItem(str(point_data["Glide_a"]))
            glide_item_a.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base, 2, glide_item_a)
            
            # Error glide A (read-only)
            error_a_item = QTableWidgetItem(str(point_data["Error_glide_a"]))
            error_a_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base, 3, error_a_item)
            
            # Theta A (read-only)
            theta_a_item = QTableWidgetItem(str(point_data["Theta_a"]))
            theta_a_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base, 4, theta_a_item)
            
            # Dtheta A (read-only)
            dtheta_a_item = QTableWidgetItem(str(point_data["DTheta_a"]))
            dtheta_a_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base, 5, dtheta_a_item)
            
            # Lacet A (read-only)
            lacet_a_item = QTableWidgetItem(str(point_data["Lacet_a"]))
            lacet_a_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base, 6, lacet_a_item)
            
            
            # roulis A (read-only)
            roulis_a_item = QTableWidgetItem(str(point_data["Roulis_a"]))
            roulis_a_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base, 7, roulis_a_item)
            
            
            # alpha a (read-only)
            alpha_a_item = QTableWidgetItem(str(point_data["Alpha_a"]))
            alpha_a_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base, 8, alpha_a_item)
            
            #*************B DATA*********************
    
            # IAS B (read-only)

            ias_item_b = QTableWidgetItem(str(point_data["IAS_b"]))
            ias_item_b.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled) #makes the cell uneditable
            table_widget.setItem(row_base+1, 1, ias_item_b)
     
            # Glide B (read-only)
  
            glide_item_b = QTableWidgetItem(str(point_data["Glide_b"]))
            glide_item_b.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base +1, 2, glide_item_b)
            
            # Error glide B (read-only)
            error_b_item = QTableWidgetItem(str(point_data["Error_glide_b"]))
            error_b_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base +1, 3, error_b_item)
            
            # Theta B (read-only)
            theta_b_item = QTableWidgetItem(str(point_data["Theta_b"]))
            theta_b_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base +1, 4, theta_b_item)
            
            # Dtheta B (read-only)
            dtheta_b_item = QTableWidgetItem(str(point_data["DTheta_b"]))
            dtheta_b_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base + 1, 5, dtheta_b_item)
            
            # Lacet B (read-only)
            lacet_b_item = QTableWidgetItem(str(point_data["Lacet_b"]))
            lacet_b_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base + 1, 6, lacet_b_item)
            
            
            # roulis B (read-only)
            roulis_b_item = QTableWidgetItem(str(point_data["Roulis_b"]))
            roulis_b_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base +1, 7, roulis_b_item)
            
            # alpha B (read-only)
            alpha_b_item = QTableWidgetItem(str(point_data["Alpha_b"]))
            alpha_b_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base +1, 8, alpha_b_item)
            
            
            # # Xmin date (read-only)
            # if point_data["Xmin_date"] is None: 
            #     xmindate_item = QTableWidgetItem(str(point_data["Xmin"])) #By default, it is the A flight date
            # else : 
            #     xmindate_item = QTableWidgetItem(point_data["Xmin_date"].strftime("%H:%M:%S"))
            # xmindate_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            # self.points_glide_table.setItem(row_position, 4, xmindate_item)
            
            flight_a_label = QTableWidgetItem("A")
            flight_a_label.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base, 9,flight_a_label)
            flight_b_label = QTableWidgetItem("B")
            flight_b_label.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base +1, 9, flight_b_label)
            
            
            
            
            
            # Xmin second (read-only)
            xminsec_item = QTableWidgetItem(str(point_data["Xmin_second"])) #By default, it is the A flight date
            table_widget.setSpan(row_base, 10, 2, 1)  # Span 2 rows for the label
            xminsec_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base, 10, xminsec_item)
            
            # # Xmax date (read-only)
            # if point_data["Xmax_date"] is None: 
            #     xmaxdate_item = QTableWidgetItem(str(point_data["Xmax_date"]))
            # else : 
            #     xmaxdate_item = QTableWidgetItem(point_data["Xmax_date"].strftime("%H:%M:%S"))
            # xmaxdate_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            # self.points_glide_table.setItem(row_position, 5, xmaxdate_item)
            
            
            # Xmax second (read-only)
            xmaxsec_item = QTableWidgetItem(str(point_data["Xmax_second"])) #By default, it is the A flight date
            table_widget.setSpan(row_base, 11, 2, 1)  # Span 2 rows for the label
            xmaxsec_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table_widget.setItem(row_base, 11, xmaxsec_item)
            
            # Label (read and write)
            labelitem = QTableWidgetItem(str(point_data["Label"]))
            table_widget.setSpan(row_base, 12, 2, 1)  # Span 2 rows for the label
            table_widget.setItem(row_base, 12, labelitem)  
            

            self.current_edit_point = None 
        
        table_widget.blockSignals(False)
    
    

    def update_row(self, current_point): # only update the display on the table
        logger.detail("STATE UPDATE ROW")
        # Find the row corresponding to the current_edit_point in the table
        for point in self.polar_data.values():
            if point["ID"] == current_point: #Dividing by two for two rows handling
                row = current_point * 2 
                # Update the IAS and glide columns
                # if self.buttonCompare.isChecked():
                #     self.points_glide_table.setItem(row, 0, QTableWidgetItem(str(point["IAS_avg"])))
                #     self.points_glide_table.setItem(row, 1 , QTableWidgetItem(str(point["Glide_avg"])))
                # else :
                #     self.points_glide_table.setItem(row, 0, QTableWidgetItem(str(point["IAS_a"])))
                #     self.points_glide_table.setItem(row, 1 , QTableWidgetItem(str(point["Glide_a"])))
                
                self.points_glide_table.setItem(row, 0 , QTableWidgetItem(str(point["ID"])))
                
                # Update A row
                self.points_glide_table.setItem(row, 1 , QTableWidgetItem(str(point["IAS_a"])))
                self.points_glide_table.setItem(row, 2 , QTableWidgetItem(str(point["Glide_a"])))
                self.points_glide_table.setItem(row, 3, QTableWidgetItem(str(point["Error_glide_a"])))
                self.points_glide_table.setItem(row, 4, QTableWidgetItem(str(point["Theta_a"])))
                self.points_glide_table.setItem(row, 5, QTableWidgetItem(str(point["DTheta_a"])))
                self.points_glide_table.setItem(row, 6 , QTableWidgetItem(str(point["Lacet_a"])))
                self.points_glide_table.setItem(row, 7 , QTableWidgetItem(str(point["Roulis_a"])))
                self.points_glide_table.setItem(row, 8 , QTableWidgetItem(str(point["Alpha_a"]))) 
                self.points_glide_table.setItem(row, 9 , QTableWidgetItem(str("A")))
 
                # Update B row
                self.points_glide_table.setItem(row+1, 1 , QTableWidgetItem(str(point["IAS_b"])))
                self.points_glide_table.setItem(row+1, 2 , QTableWidgetItem(str(point["Glide_b"])))
                self.points_glide_table.setItem(row+1, 3, QTableWidgetItem(str(point["Error_glide_b"])))
                self.points_glide_table.setItem(row+1, 4, QTableWidgetItem(str(point["Theta_b"])))
                self.points_glide_table.setItem(row+1, 5, QTableWidgetItem(str(point["DTheta_b"])))
                self.points_glide_table.setItem(row+1, 6 , QTableWidgetItem(str(point["Lacet_b"])))
                self.points_glide_table.setItem(row+1, 7 , QTableWidgetItem(str(point["Roulis_b"])))   
                self.points_glide_table.setItem(row+1, 8 , QTableWidgetItem(str(point["Alpha_b"]))) 
                self.points_glide_table.setItem(row+1, 9 , QTableWidgetItem(str("B")))
                
                self.points_glide_table.setItem(row, 10, QTableWidgetItem(str(point["Xmin_second"])))
                self.points_glide_table.setItem(row, 11, QTableWidgetItem(str(point["Xmax_second"])))
                self.points_glide_table.setItem(row, 12, QTableWidgetItem(str(point["Label"])))
                
                item_dtheta_a = self.points_glide_table.item(row, 5) 
                item_dtheta_b = self.points_glide_table.item(row+1, 5) 
                item_alpha_a = self.points_glide_table.item(row, 8) 
                item_alpha_b = self.points_glide_table.item(row+1, 8) 
                item_lacet_a = self.points_glide_table.item(row, 6) 
                item_lacet_b = self.points_glide_table.item(row+1, 6) 
                
                if point["DTheta_a"] is not None and  abs(point["DTheta_a"]) > 0.1:
                    item_dtheta_a.setForeground(QBrush(QColor("red")))
                else :
                    item_dtheta_a.setForeground(QBrush(QColor("black")))
                    
                if point["DTheta_b"] is not None and  abs(point["DTheta_b"]) > 0.1:
                    item_dtheta_b.setForeground(QBrush(QColor("red")))
                else :
                    item_dtheta_b.setForeground(QBrush(QColor("black")))
                    
                if point["Lacet_a"] is not None and  abs(point["Lacet_a"]) < 1:
                    item_lacet_a.setForeground(QBrush(QColor("green")))
                elif point["Lacet_a"] is not None and  abs(point["Lacet_a"]) > 2:
                    item_lacet_a.setForeground(QBrush(QColor("red")))
                elif point["Lacet_a"] is not None :
                    item_lacet_a.setForeground(QBrush(QColor("orange")))
                else : 
                    item_lacet_a.setForeground(QBrush(QColor("black")))
                    
                if point["Lacet_b"] is not None  and abs(point["Lacet_b"]) < 1 :
                    item_lacet_b.setForeground(QBrush(QColor("green")))
                elif point["Lacet_b"] is not None and  abs(point["Lacet_b"]) > 2 :
                    item_lacet_b.setForeground(QBrush(QColor("red")))
                elif point["Lacet_b"] is not None:
                    item_lacet_b.setForeground(QBrush(QColor("orange")))  
                else:  
                    item_lacet_b.setForeground(QBrush(QColor("black")))  

                if point["Alpha_a"] is not None and abs(point["Alpha_a"]) < 2  :
                    item_alpha_a.setForeground(QBrush(QColor("green")))
                elif point["Alpha_a"] is not None  and  abs(point["Alpha_a"]) > 5:
                    item_alpha_a.setForeground(QBrush(QColor("red")))
                elif  point["Alpha_a"] is not None:
                    item_alpha_a.setForeground(QBrush(QColor("orange")))
                else : 
                    item_alpha_a.setForeground(QBrush(QColor("black")))


                if point["Alpha_b"] is not None and  abs(point["Alpha_b"]) < 2 :
                    item_alpha_b.setForeground(QBrush(QColor("green")))
                elif point["Alpha_b"] is not None and  abs(point["Alpha_b"]) > 5 :
                    item_alpha_b.setForeground(QBrush(QColor("red")))
                elif  point["Alpha_b"] is not None :
                    item_alpha_b.setForeground(QBrush(QColor("orange")))
                else : 
                    item_alpha_b.setForeground(QBrush(QColor("black")))
    

                    
        self.apply_alternate_row_colors(self.points_glide_table, 2)

    def raw_table_clicked(self, row):
        
        
        self.current_edit_point = row  // 2  #update the point we want to edit    //2 because of the two rwos handling
        self.edit_point()  #automaticaly entering editing mode

    
    def edit_point(self):
        logger.detail("STATE EDIT POINT")
        self.exit_edit() #Remove previous edit mode
        self.is_editing = True
        logger.detail(f"Entering edit mode for point {self.current_edit_point}")

        if self.current_edit_point is None:
            #self.add_log("No point selected to be edited")
            return
        
        # Create ROI and display it on the graph (you can adjust it)
        for point in self.polar_data.values():
            if point["ID"] == self.current_edit_point: 
                if point["ROI"] is None: #If no ROI (meaning a newly point), we create a new ROI this the default values
                    roi = pg.LinearRegionItem(values=(self.calculate_roi("min"), self.calculate_roi("max")),brush=(10, 10, 255, 60))
                    roi.setMovable(True)
                    roi.setZValue(10)  # Stay on top
                    self.graph_ias_time.addItem(roi)
                    point["ROI"] = roi #And we add the ROI to the dic
                else: #If the point was already created with a already set ROI, we just change its color and make it movable
                    roi = point["ROI"]
                    roi.setBrush(QColor(10, 10, 255, 60))
                    roi.setRegion((point["Xmin_second"], point["Xmax_second"]),)
                    roi.setMovable(True)
       
                    if point['IAS_a'] is not None:
                        if self.unit_mode == "Glide":
                            self.crosshair_h.setValue(point['Glide_a'])
                        else:
                            self.crosshair_h.setValue(point['Glide_ratio_a'])
                            
                        self.crosshair_v.setValue(point['IAS_a'])
                        self.crosshair_v.show()
                        self.crosshair_h.show() 


                # Live update the polar_data when ROI is moved
                point['ROI'].sigRegionChanged.connect(self.update_values)  
                
    def calculate_roi(self, edge):
        """
        edge : 'min' ou 'max'
        Retourne la valeur correspondante pour la ROI à créer
        """
        total_time = self.flight_dic["A"]["processed_data"]["time"][-1]
        existing_rois = []
    
        # Récupère toutes les plages existantes
        for point in self.polar_data.values():
            if point.get("ROI") is not None:
                roi = point["ROI"].getRegion()
                existing_rois.append((roi[0], roi[1]))
    
        # Trier par Xmin pour savoir le dernier
        existing_rois.sort(key=lambda x: x[0])
    
        if not existing_rois:
            #Premier point : intervalle 100000 centré
            start = (total_time / 2) - 50000
            end = (total_time / 2) + 50000
        else:
            #Autres points
            last_xmin, last_xmax = existing_rois[-1]
            remaining = max(total_time - last_xmax, 0)
    
            if remaining > 0:
                interval = max(int(remaining * 0.1), 50000)  # minimum sécurité de 50000
                start = last_xmax + 5000
                end = min(start + interval, total_time)
            else:
                # Plus de place → dernière portion
                start = last_xmax + 50
                end = total_time
                
        return start if edge == "min" else end            
      
    def exit_edit(self):
        logger.detail("STATE EXIT EDIT")
        self.is_editing = False
        #self.add_log("Exit edit mode")        
        #Draw the previous ROI as transparent
        if self.polar_data:
            for point in self.polar_data.values():
                if point["ROI"]:
                    point["ROI"].setBrush(QColor(10, 255, 10, 25))  # quart-transparent green
                    point["ROI"].setMovable(False)  # prevent dragging if needed
                    
            self.graph_ias_time.viewport().update() #updating the graph so that we can lively see the change when exiting edit mode
            
            self.crosshair_v.hide()
            self.crosshair_h.hide()
            
        
    def update_values(self): #This function calculate the ias and glide in real time accordingly to the ROI 
        logger.detail("STATE UPDATE VALUES")
        if self.current_edit_point is not None : 
            for point in self.polar_data.values():
                if point["ID"] == self.current_edit_point:
                    
                    xmin, xmax = point["ROI"].getRegion()
                    point["Xmin_second"] = round(xmin, 2)
                    point["Xmax_second"] = round(xmax, 2)
                    
                    # By default we fetch the time and data from the flight A , but it's supposed to be the same than B anyway
                    # idx_min = np.where(self.flight_dic["A"]["processed_data"]["time"] == xmin)[0]
                    # if idx_min.size > 0:
                    #     point["Xmin_date"] = self.flight_dic["A"]["processed_data"]["date"][idx_min[0]]
                    # else:
                    #     # Fallback in case there's no exact match, use closest value
                    #     closest_idx = (np.abs(self.flight_dic["A"]["processed_data"]["time"] - xmin)).argmin()
                    #     point["Xmin_date"] = self.flight_dic["A"]["processed_data"]["date"][closest_idx]
                    
                    # idx_max = np.where(self.flight_dic["A"]["processed_data"]["time"] == xmax)[0]
                    # if idx_max.size > 0:
                    #     point["Xmax_date"] =self.flight_dic["A"]["processed_data"]["date"][idx_max[0]]
                    # else:
                    #     # Fallback in case there's no exact match, use closest value
                    #     closest_idx = (np.abs(self.flight_dic["A"]["processed_data"]["time"] - xmax)).argmin()
                    #     point["Xmax_date"] = self.flight_dic["A"]["processed_data"]["date"][closest_idx]
            
                    for flight_id, flight_data in self.flight_dic.items():
                        if self.flight_dic[flight_id]["ready_to_be_analyzed"]:
                            # calculating average for each flight
                            # creating mask for the specified region 
                            mask = (self.flight_dic[flight_id]["processed_data"]["time"] >= xmin) & (self.flight_dic[flight_id]["processed_data"]["time"] <= xmax)
                            # calculating ias average
                            ias_avg = np.mean(self.flight_dic[flight_id]["processed_data"]['ias'][mask])
                            # calculating glide average
                            glide_avg = np.mean(self.flight_dic[flight_id]["processed_data"]['glide'][mask])
                            # calculating alpha average
                            alpha_avg = np.mean(self.flight_dic[flight_id]["processed_data"]['alpha'][mask])
                            # calculating theta average
                            theta_avg = np.mean(self.flight_dic[flight_id]["processed_data"]['theta'][mask])
                            # calculating dtheta average
                            dtheta_avg = np.mean(self.flight_dic[flight_id]["processed_data"]['dtheta'][mask])
                            # calculating roulis average
                            roulis_avg = np.mean(self.flight_dic[flight_id]["processed_data"]['roulis'][mask])
                            # calculating roh average
                            rho_avg = np.mean(self.flight_dic[flight_id]["processed_data"]['rho'][mask])
                            # calculating lacet average
                            lacet_avg = np.mean(self.flight_dic[flight_id]["processed_data"]['lacet'][mask])
                            
                            
                            # calculating fineness average
                            
                            glide_ratio_avg = -1 / np.tan(np.deg2rad(glide_avg ))
                            self.flight_dic[flight_id]["processed_data"]['glide_ratio'] = glide_ratio_avg
                            # Calculating glide error 
                            error_glide = self.cumulative_error_analysis(self.flight_dic[flight_id]["processed_data"]['glide'][mask])
                           
                            # Calculating fineness  error 
                            glide_ratio_and_error = -1 / np.tan(np.deg2rad(glide_avg + error_glide))
                            error_glide_ratio = glide_ratio_and_error - glide_ratio_avg
                            
    
                            if not np.isnan(glide_avg) and not np.isnan(ias_avg):
                
                                suffix = f"_{flight_id.lower()}"  # results in "_a" or "_b"
                    
                                point[f'Glide{suffix}'] = round(glide_avg, 3)
                                point[f'IAS{suffix}'] = round(ias_avg, 3)
                                point[f'Error_glide{suffix}'] = round(error_glide, 3)
                                point[f'Error_glide_ratio{suffix}'] = round(error_glide_ratio, 3)
                                point[f'Alpha{suffix}'] = round(alpha_avg, 3)
                                point[f'Theta{suffix}'] = round(theta_avg, 3)
                                point[f'DTheta{suffix}'] = round(dtheta_avg, 3)
                                point[f'Lacet{suffix}'] = round(lacet_avg, 3)
                                point[f'Roulis{suffix}'] = round(roulis_avg, 3)
                                point[f'Rho{suffix}'] = round(rho_avg, 3)
                                point[f'Glide_ratio{suffix}'] = round(glide_ratio_avg, 3)
        
                            else :
                                continue 
                            
                            
                    # if self.buttonCompare.isChecked(): #If we are comparing two flights , we calculate the mean polar data
                    #     point['IAS_avg'] = round(((point['IAS_a'] + point['IAS_b']) / 2),3)
                    #     point['Glide_avg'] = round(((point['Glide_a'] + point['Glide_b']) / 2),3)
                    #     self.crosshair_v.setValue(point['IAS_avg'])
                    # #     self.crosshair_h.setValue(point['Glide_avg'])
                    # else :  #otherwise, only flight A gets its values assigned
                    
                    self.crosshair_v.setValue(point['IAS_a'])
                    if self.unit_mode == "glide_ratio":
                        self.crosshair_h.setValue(point['Glide_ratio_a'])
                    else:
                        self.crosshair_h.setValue(point['Glide_a'])
                                                        
      
                            
                    
                    self.update_polar_graph(
                        self.polar_data,
                        reference=False,
                        y_axis_mode=self.unit_mode,
                        graph_widget=self.graph_glide_ias,
                        scatter_items={
                        "a": self.scatter_a,
                        "b": self.scatter_b,
                        "ref_a": self.scatter_ref_a,
                        "ref_b": self.scatter_ref_b},
                        dynamic = True
                    )
                    self.crosshair_v.show()
                    self.crosshair_h.show() 
                    self.update_row(self.current_edit_point) #live updating row
                            
    
    def set_error_bars(self, point, graph, mode="polar", probe="A", y_axis_mode="glide", dynamic="False"):
        """
        Create and add error bars to the given graph based on mode ('polar' or 'vxvz') and probe ('A' or 'B'). When dynamic is set True, it will delete previous bar to create a live update
        """
        logger.detail("STATE SET ERROR BARS")
        if mode == "polar":
            y_field = "Glide_ratio" if y_axis_mode == "glide_ratio" else "Glide"
            error_field = "Error_glide_ratio" if y_axis_mode == "glide_ratio" else "Error_glide"
    
            x = point[f"IAS_{probe.lower()}"]
            y = point[f"{y_field}_{probe.lower()}"]
            error = point[f"{error_field}_{probe.lower()}"]
    
        elif mode == "vxvz":
            vx = point[f"IAS_{probe.lower()}"] * np.cos(np.deg2rad(point[f"Glide_{probe.lower()}"]))
            vz = point[f"IAS_{probe.lower()}"] * np.sin(np.deg2rad(point[f"Glide_{probe.lower()}"]))
            x = vx
            y = vz
            error = vz - (point[f"IAS_{probe.lower()}"] * np.sin(np.deg2rad(point[f"Glide_{probe.lower()}"] + point[f"Error_glide_{probe.lower()}"])))
    
        else:
            raise ValueError("Invalid mode. Must be 'polar' or 'vxvz'.")
    
    
    
    
                
        #Delete the previous errors bars if they exists 
        if dynamic: 
            if graph== self.graph_glide_ias:
                if self.error_bar_items[probe]["glide_ias"][y_field]:
                    graph.removeItem(self.error_bar_items[probe]["glide_ias"][y_field])
            elif graph== self.graph_glide_ias_compare:
                if self.error_bar_items[probe]["glide_ias_compare"][y_field]:
                   graph.removeItem(self.error_bar_items[probe]["glide_ias_compare"][y_field]) 
            else:
                if self.error_bar_items[probe]["vxvz"]:
                    graph.removeItem(self.error_bar_items[probe]["vxvz"])
            
        error_bar = pg.ErrorBarItem(
            x=np.array([x]),
            y=np.array([y]),
            height=2 * error,
            beam=error / 5
        )
        graph.addItem(error_bar)
        
        
        #Recording the error bar items 
        if graph== self.graph_glide_ias:
            self.error_bar_items[probe]["glide_ias"][y_field] =error_bar
        elif graph== self.graph_glide_ias_compare:
            self.error_bar_items[probe]["glide_ias_compare"][y_field] =error_bar
        else:
            self.error_bar_items[probe]["vxvz"]=error_bar
            
    def remove_error_bars(self, graph, probe="A", y_axis_mode="glide"):
        """
        Remove error bars to the given graph if they exist based on mode ('polar' or 'vxvz') and probe ('A' or 'B').
        """

        logger.detail("STATE REMOVE ERROR BARS")
        y_field = "Glide_ratio" if y_axis_mode == "glide_ratio" else "Glide"

        if graph== self.graph_glide_ias:
            if self.error_bar_items[probe]["glide_ias"][y_field]:
                graph.removeItem(self.error_bar_items[probe]["glide_ias"][y_field])
                self.error_bar_items[probe]["glide_ias"][y_field] = None 
        elif graph== self.graph_glide_ias_compare:
            if self.error_bar_items[probe]["glide_ias_compare"][y_field]:
               graph.removeItem(self.error_bar_items[probe]["glide_ias_compare"][y_field]) 
               self.error_bar_items[probe]["glide_ias_compare"][y_field] = None
        else:
            if self.error_bar_items[probe]["vxvz"]:
                graph.removeItem(self.error_bar_items[probe]["vxvz"])
                self.error_bar_items[probe]["vxvz"] = None
        graph.repaint() 

                
    def hide_error_bars(self, graph, probe="A", y_axis_mode="glide", hide = True):
        """
        hide or show error bars to the given graph if they exist based on mode ('polar' or 'vxvz') and probe ('A' or 'B').
        """

        logger.detail("STATE HIDE ERROR BARS")
        y_field = "Glide_ratio" if y_axis_mode == "glide_ratio" else "Glide"
        
        if hide == True:
            transparency = 0
        else:
            transparency = 255
        #hide or show the errors bars if they exists  
        if graph== self.graph_glide_ias:
            if self.error_bar_items[probe]["glide_ias"][y_field]:
                self.error_bar_items[probe]["glide_ias"][y_field].opts["pen"] = pg.mkPen((120, 120, 120, transparency))
                self.error_bar_items[probe]["glide_ias"][y_field].update()
        elif graph== self.graph_glide_ias_compare:
            if self.error_bar_items[probe]["glide_ias_compare"][y_field]:
                self.error_bar_items[probe]["glide_ias_compare"][y_field].opts["pen"] = pg.mkPen((120, 120,120, transparency))
                self.error_bar_items[probe]["glide_ias_compare"][y_field].update()
        else:
            if self.error_bar_items[probe]["vxvz"]:
                self.error_bar_items[probe]["vxvz"].opts["pen"] = pg.mkPen((120, 120, 120, transparency))
                self.error_bar_items[probe]["vxvz"].update() 

    def update_polar_graph(
        self,
        dic,
        reference,
        y_axis_mode="glide",
        graph_widget=None,
        scatter_items=None,
        dynamic = False
    ):
        logger.detail(f"STATE UPDATE POLAR GRAPH reference={reference} y_axis_mode={y_axis_mode}")
    
        # Use the provided graph widget or fallback to the default
        graph = graph_widget or self.graph_glide_ias
    
        # Use the provided scatter plot items
        scatter_a = scatter_items.get("a")
        scatter_b = scatter_items.get("b")
        scatter_ref_a = scatter_items.get("ref_a")
        scatter_ref_b = scatter_items.get("ref_b")
    

    
        # Prepare new data
        data = {
            "ias_a": [], "ias_b": [], "ias_ref_a": [], "ias_ref_b": [],
            "glide_a": [], "glide_b": [], "glide_ref_a": [], "glide_ref_b": [],
            "glide_ratio_a": [], "glide_ratio_b": [], "glide_ratio_ref_a": [], "glide_ratio_ref_b": []
        }
    
        y_field = "Glide_ratio" if y_axis_mode == "glide_ratio" else "Glide"
        error_field = "Error_glide_ratio" if y_axis_mode == "glide_ratio" else "Error_glide"
    
        # Populate and plot
        for point in dic.values():
            is_dual = point.get("IAS_b") is not None
    
            # Reference
            if reference:
                data["ias_ref_a"].append(point["IAS_a"])
                data[f"{y_axis_mode.lower()}_ref_a"].append(point[f"{y_field}_a"])
                #self.set_error_bars(point, graph, mode="polar", probe="A", y_axis_mode=y_axis_mode , dynamic = dynamic)
    
                if is_dual:
                    data["ias_ref_b"].append(point["IAS_b"])
                    data[f"{y_axis_mode.lower()}_ref_b"].append(point[f"{y_field}_b"])
                    #self.set_error_bars(point, graph, mode="polar", probe="B", y_axis_mode=y_axis_mode , dynamic = dynamic)
            else:
                data["ias_a"].append(point["IAS_a"])
                data[f"{y_axis_mode.lower()}_a"].append(point[f"{y_field}_a"])
                #self.set_error_bars(point, graph, mode="polar", probe="A", y_axis_mode=y_axis_mode, dynamic = dynamic)
    
                if is_dual:
                    data["ias_b"].append(point["IAS_b"])
                    data[f"{y_axis_mode.lower()}_b"].append(point[f"{y_field}_b"])
                    #self.set_error_bars(point, graph, mode="polar", probe="B", y_axis_mode=y_axis_mode, dynamic = dynamic)
    
        # Set scatter data and visibility
        if reference:
            if scatter_ref_a:
                scatter_ref_a.setData(x=data["ias_ref_a"], y=data[f"{y_axis_mode.lower()}_ref_a"])
                scatter_ref_a.setVisible(self.radioButton_ref_probe_A.isChecked())
            if scatter_ref_b:
                scatter_ref_b.setData(x=data["ias_ref_b"], y=data[f"{y_axis_mode.lower()}_ref_b"])
                scatter_ref_b.setVisible(self.radioButton_ref_probe_B.isChecked())
        else:
            if scatter_a:
                scatter_a.setData(x=data["ias_a"], y=data[f"{y_axis_mode.lower()}_a"])
                if graph == self.graph_glide_ias:
                    scatter_a.setVisible(self.radioButton_probe_A.isChecked())
                else :
                    scatter_a.setVisible(self.radioButton_probe_A_compare.isChecked())
            if scatter_b:
                scatter_b.setData(x=data["ias_b"], y=data[f"{y_axis_mode.lower()}_b"])
                if graph == self.graph_glide_ias:
                    scatter_b.setVisible(self.radioButton_probe_B.isChecked())
                else :
                    scatter_b.setVisible(self.radioButton_probe_B_compare.isChecked())

    
        # Set Y-axis range
        if y_axis_mode == "glide_ratio":
            graph.setYRange(5, 15)
        else:
            graph.setYRange(-15, 5)
            
            
    def update_vxvz_graph(
        self,
        dic,
        graph_widget=None,
        scatter_a= None,
        scatter_b=None,
        dynamic = False):
        
        logger.detail("STATE UPDATE VXVZ GRAPH")
        
        # Prepare the data to plot
        data = {"Vx_a": [], "Vx_b": [],"Vz_a": [], "Vz_b": []}
        
        for point in dic.values():

            is_dual = point.get("IAS_b") is not None
            
            vx_a = point["IAS_a"] * np.cos(np.deg2rad(point["Glide_a"]))
            vz_a = point["IAS_a"] * np.sin(np.deg2rad(point["Glide_a"]))
            
            
            
            #self.set_error_bars(point, graph_widget, mode="vxvz", probe="A" , dynamic = dynamic)
            
            data["Vx_a"].append(vx_a)
            data["Vz_a"].append(vz_a)
         
            if is_dual:
                vx_b = point["IAS_b"] * np.cos(np.deg2rad(point["Glide_b"]))
                vz_b = point["IAS_b"] * np.sin(np.deg2rad(point["Glide_b"]))
                
                
                #self.set_error_bars(point, graph_widget, mode="vxvz", probe="B", dynamic = dynamic)
                
                data["Vx_b"].append(vx_b)
                data["Vz_b"].append(vz_b)
            
            
            
        if scatter_a:
            scatter_a.setData(x=data["Vx_a"], y=data["Vz_a"])
            scatter_a.setVisible(self.radioButton_probe_A_compare.isChecked())
        if scatter_b:
            scatter_b.setData(x=data["Vx_b"], y=data["Vz_b"])
            scatter_b.setVisible(self.radioButton_probe_B_compare.isChecked())

    
        
    def change_visibility_compare_tab(self, probe):
        if not hasattr(self, "active_displayed_rows"):
            return
        for row_data in self.active_displayed_rows.values():
            
            if probe=="A":
                scatter_compare = row_data[0]  # A is the first item in the compare graph
                scatter_vxvz = row_data[3]  # A is the first item in the vxvz graph
                scatter_compare.setVisible(self.radioButton_probe_A_compare.isChecked())
                scatter_vxvz.setVisible(self.radioButton_probe_A_compare.isChecked())
                # if not self.radioButton_probe_A_compare.isChecked():
                #     self.hide_error_bars( self.graph_glide_ias_compare, probe,  self.unit_mode, True)
                #     self.hide_error_bars( self.graph_vxvz, probe,  self.unit_mode, True)
                # else: 
                #     self.hide_error_bars( self.graph_glide_ias_compare, probe,  self.unit_mode, False)
                #     self.hide_error_bars( self.graph_vxvz, probe,  self.unit_mode, False)

                 
            elif probe=="B":
                scatter_compare = row_data[1]  # A is the first item in the compare graph
                scatter_vxvz = row_data[4]  # A is the first item in the compare graph
                scatter_compare.setVisible(self.radioButton_probe_B_compare.isChecked())
                scatter_vxvz.setVisible(self.radioButton_probe_B_compare.isChecked())
                # if not self.radioButton_probe_B_compare.isChecked():
                #     self.hide_error_bars( self.graph_glide_ias_compare, probe,  self.unit_mode, True)
                #     self.hide_error_bars( self.graph_vxvz, probe,  self.unit_mode, True)
                # else: 
                #     self.hide_error_bars( self.graph_glide_ias_compare, probe,  self.unit_mode, False)
                #     self.hide_error_bars( self.graph_vxvz, probe,  self.unit_mode, False)
                
                


            
    def change_polar_unit(self):
        # Determine which button is checked
        if self.radio_button_toggle_fineness.isChecked() or self.radio_button_toggle_fineness_compare.isChecked():
            self.unit_mode = "glide_ratio"
            y_label = "Glide ratio"
            self.update_values()
        elif self.radio_button_toggle_angle.isChecked() or self.radio_button_toggle_angle_compare.isChecked():
            self.unit_mode = "glide"
            y_label = "Glide (°)"
            self.update_values()
        else:
            return
        
        # Update both Y-axis labels
        self.graph_glide_ias.setLabel('left', y_label)
        self.graph_glide_ias_compare.setLabel('left', y_label)
    
        # Update main polar graph
        self.update_polar_graph(
            self.polar_data,
            reference=False,
            y_axis_mode=self.unit_mode,
            graph_widget=self.graph_glide_ias,
            scatter_items={
                "a": self.scatter_a,
                "b": self.scatter_b,
                "ref_a": self.scatter_ref_a,
                "ref_b": self.scatter_ref_b,
                
            },
            dynamic = False
        )
        
        if self.reference_polar_data:
            self.update_polar_graph(
                self.reference_polar_data["polar_data"],
                reference=True,
                y_axis_mode=self.unit_mode,
                graph_widget=self.graph_glide_ias,
                scatter_items={
                "a": self.scatter_a,
                "b": self.scatter_b,
                "ref_a": self.scatter_ref_a,
                "ref_b": self.scatter_ref_b},
                dynamic = False)
    
        # Update comparison graph
        if hasattr(self, "active_displayed_rows"):
            for flight_number, (scatter_a, scatter_b, row_index, *_rest) in self.active_displayed_rows.items():
                print("awwa")
                polar_data = self.results[row_index]["polar_data"]
    
                self.update_polar_graph(
                    polar_data,
                    reference=False,
                    y_axis_mode=self.unit_mode,
                    graph_widget=self.graph_glide_ias_compare,
                    scatter_items={
                        "a": scatter_a,
                        "b": scatter_b
                    },
                    dynamic = False
                )
    
            if self.reference_polar_data:
                print(f"update graph with {self.unit_mode} ")
                self.update_polar_graph(
                    self.reference_polar_data["polar_data"],
                    reference=True,
                    y_axis_mode=self.unit_mode,
                    graph_widget=self.graph_glide_ias,
                    scatter_items={
                    "a": self.scatter_a,
                    "b": self.scatter_b,
                    "ref_a": self.scatter_ref_a,
                    "ref_b": self.scatter_ref_b},
                    dynamic = False
                )
                
        #Update the fittings curves if there is any 
        if hasattr(self, "active_displayed_fit_curves"):
            self.update_fit_curves_on_unit_change()

    def set_cell_background(self, table, row, col, color):
        item = table.item(row, col)
        if item is None:
            item = QTableWidgetItem()
            table.setItem(row, col, item)
        item.setBackground(QBrush(color))    
   

    def apply_alternate_row_colors(self, table, group_size=1):
        for row in range(table.rowCount()):
            color = QColor(240, 240, 240) if (row // group_size) % 2 == 0 else QColor(255, 255, 255)
            for col in range(table.columnCount()):
                self.set_cell_background(table, row, col, color)
                    
     
        

    
    def save_label(self):
        logger.detail("STATE SAVE LABEL")
        item = self.points_glide_table.item(self.current_edit_point, 11)
        label = item.text()
        for point in self.polar_data.values():
            if point["ID"] == self.current_edit_point:
                point["Label"] = label
    
    
    def clear_flight(self, flight):
        logger.detail("STATE CLEAR FLIGHT")
        self.graph_ias_time.removeItem(self.flight_dic[flight]["plot_item"]) #removing the graph
        
        # Clear data without removing the keys
        for key in self.flight_dic[flight]:
            if isinstance(self.flight_dic[flight][key], dict):
                self.flight_dic[flight][key].clear()
            else:
                self.flight_dic[flight][key] = None
        
        # Restore booleans to default 
        self.flight_dic[flight]["has_gps"] = False
        self.flight_dic[flight]["to_analyze"] = False
        self.flight_dic[flight]["plot_item"] = None
        
      # clear IAS_vs_glide graph
      
        
       
        self.crosshair_v.hide()
        self.crosshair_h.hide()
        
        
        self.update_polar_graph(
            self.polar_data,
            reference=False,
            y_axis_mode=self.unit_mode,
            graph_widget=self.graph_glide_ias,
            scatter_items={
            "a": self.scatter_a,
            "b": self.scatter_b,
            "ref_a": self.scatter_ref_a,
            "ref_b": self.scatter_ref_b},
            dynamic = True
        )
        #self.update_polar_graph(self.reference_polar_data["polar_data"], True, y_axis_mode=self.unit_mode)
        self.update_polar_table(self.points_glide_table,self.polar_data) #Used to delete on the table
           
        self.update_values()
          

        
        # reset UI elements
        if flight == "A":
            self.lineFlightDateA.setText("")
            self.lineProbeA.setText("")
            self.lineConfVersionA.setText("")
        if flight == "B":
            self.lineFlightDateB.setText("")
            self.lineProbeB.setText("")
            self.lineConfVersionB.setText("")
            
        #self.add_log(f"Flight {flight} data has been cleared.")
        logger.info(f"Flight {flight} data has been cleared.")
     
        
    
    def keyPressEvent(self, event): #This function handle the keys event 
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Escape) and self.is_editing: 
            self.exit_edit()
        else:
            super().keyPressEvent(event)
                
    def display_export_window(self): #Call the export window
        logger.detail("STATE DISPLAY EXPORT WINDOW")
        # self.export_dialog.exec()  
        if self.export_dialog.isVisible():
            self.export_dialog.hide()
        
        else:
            self.export_dialog.show()
                
        
    def display_reference_window(self): #Call the reference window
        logger.detail("STATE DISPLAY REFERENCE WINDOW")
        self.reference_dialog.reference_loaded.connect(self.on_reference_loaded)  # connect the signal
        if self.reference_dialog.isVisible():
            self.reference_dialog.hide()
        
        else:
            self.reference_dialog.show()
                      
        
        
    def clear_all(self):
        logger.detail("STATE CLEAR ALL")
        for flight_id, flight_data in self.flight_dic.items():
            self.clear_flight(flight_id)
            
            
        self.clear_polar_data()
        self.clear_log()
        self.crosshair_v.hide()
        self.crosshair_h.hide() 
        # self.remove_error_bars(self.graph_glide_ias,"A", self.unit_mode)
        # self.remove_error_bars(self.graph_glide_ias,"B", self.unit_mode)
   
        
        logger.info("Everything has been cleared")
        #self.add_log("Everything has been cleared")
    def cumulative_error_analysis(self, data):
        """
        Calcule la moyenne cumulative, la moyenne finale (valeur retenue),
        et la barre d'erreur maximale sur la seconde moitié du vecteur.
        
        Parameters:
            data (array-like): Liste ou tableau de valeurs numériques.
            
        Returns:
            dict: {
                "error_bar": écart max absolu sur la seconde moitié
            }
        """
        data = np.asarray(data)
        if len(data) == 0:
            raise ValueError("Le vecteur de données est vide.")
        
        cumulative_mean = np.cumsum(data) / np.arange(1, len(data)+1)
        final_value = cumulative_mean[-1]
        second_half = cumulative_mean[len(data)//2:]
        # Compute deviations from final value (keep sign)
        deviations = second_half - final_value
         
        # Error bar is max absolute deviation (but signed)
        error_bar = np.max(np.abs(deviations))
        
        
        return  error_bar



    def update_spinboxes_from_view(self, graph, spin_xmin, spin_xmax, spin_ymin, spin_ymax):
        vb = graph.getViewBox()
        x_range, y_range = vb.viewRange()
        
        # Block signals to avoid triggering view update again
        spin_xmin.blockSignals(True)
        spin_xmax.blockSignals(True)
        spin_ymin.blockSignals(True)
        spin_ymax.blockSignals(True)
        
        spin_xmin.setValue(x_range[0])
        spin_xmax.setValue(x_range[1])
        spin_ymin.setValue(y_range[0])
        spin_ymax.setValue(y_range[1])
        
        spin_xmin.blockSignals(False)
        spin_xmax.blockSignals(False)
        spin_ymin.blockSignals(False)
        spin_ymax.blockSignals(False)

    def update_view_from_spinboxes(self, graph, spin_xmin, spin_xmax, spin_ymin, spin_ymax):
        xmin = spin_xmin.value()
        xmax = spin_xmax.value()
        ymin = spin_ymin.value()
        ymax = spin_ymax.value()
        
        graph.setXRange(xmin, xmax, padding=0)
        graph.setYRange(ymin, ymax, padding=0)



    def on_reference_loaded(self, loaded: bool):
        # Enable the radio button
        self.radioButton_ref_probe_A.setEnabled(loaded)
        self.radioButton_ref_probe_B.setEnabled(loaded)
        # self.radioButton_ref_probe_avg.setEnabled(loaded)
        

                    
        
    # Utility method to build the query
    def build_query(self, criteria):
        Flight = Query()
        query = None
    
        for key, keyword in criteria.items():
            if keyword != "":
                if key == "Probe":
                    condition_a = Flight.metadata["Probe A"].test(lambda val, k=keyword: k in str(val).lower())
                    condition_b = Flight.metadata["Probe B"].test(lambda val, k=keyword: k in str(val).lower())
                    condition = condition_a | condition_b
                else:
                    condition = Flight.metadata[key].test(lambda val, k=keyword: k in str(val).lower())
                query = condition if query is None else query & condition
    
        return query
    

        
    def search(self, suffix, table):
        """
        suffix : str → 'compare' ou 'manage'
        table : QTableWidget cible pour afficher les résultats
        """
        logger.detail(f"STATE SEARCH IN DATABASE FOR TAB {suffix.upper()}")
        
        table.setRowCount(0)  # Clear previous results
    
        def get_date(widget):
            date_str = widget.date().toString("yyyy")
            return "" if date_str == "2000" else widget.date().toString("yyyy-MM-dd")
    
        # Construire les noms complets des widgets
        fields = ["flight_number", "auw", "wing", "harness", "probe_number"]
        criteria = {}
    
        for field in fields:
            widget = getattr(self, f"search_bar_{field}_{suffix}")
            criteria[field.replace("_", " ").title()] = widget.text().strip().lower()
    
        # Ajouter les dates
        flight_date_widget = getattr(self, f"search_flight_date_{suffix}")
        export_date_widget = getattr(self, f"search_export_date_{suffix}")
        
        criteria["Flight Date"] = get_date(flight_date_widget)
        criteria["Export Date"] = get_date(export_date_widget)
    
        query = self.build_query(criteria)
        self.results = self.db.search(query) if query else self.db.all()
        
        #On trie self.results
        self.results.sort(key=lambda x: int(x["metadata"].get("Flight Number", 0)))
        
    
        logger.info(f"Found {len(self.results)} result(s).")
    
        self.display_results(self.results, table, suffix)
        
    
    
    def display_results(self, results, table, suffix):
        
        if suffix == "compare":
            column_offset = 1
        else:
            column_offset = 0 
        table.setSortingEnabled(False)
        table.setRowCount(len(results))
        lcd_widget = getattr(self, f"results_size_lcd_{suffix}")
        lcd_widget.display(len(results))
        self.displayed_data_checkboxes =  {}  # Track checkboxes to limit display to 4
        self.displayed_fit_checkboxes =  {}
        
        table.blockSignals(True)
        
        if not hasattr(self, "active_displayed_rows"):
            self.active_displayed_rows = {}
        if not hasattr(self, "active_displayed_fit_curves"):
            self.active_displayed_fit_curves = {}

        for row_idx, entry in enumerate(results):
            meta = entry["metadata"]
            flight_number = meta.get("Flight Number", "")
            row_data = [
                meta.get("Flight Number", ""),
                meta.get("AUW", ""),
                meta.get("Wing", ""),
                meta.get("Harness", ""),
                meta.get("Probe A", ""),
                meta.get("Probe B", ""),
                meta.get("Flight Date", ""),
                meta.get("Export Date", "")
            ]
            
            for col_idx, value in enumerate(row_data):
                item = QtWidgets.QTableWidgetItem(value)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                if col_idx == 0: #If it's the flight number
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, value) # specific role for flight number in order to sort it 
                table.setItem(row_idx, col_idx+column_offset, item)
            
            #This part is used to check if the checkbox has already been checked so the data won't be displayed twice         
            # Create two checkboxes: one for "data", one for "fit"
            
                if suffix == "compare": 
                    checkbox_data = QtWidgets.QCheckBox("data")
                    checkbox_data.setChecked(flight_number in self.active_displayed_rows)
                    checkbox_data.stateChanged.connect(lambda state, idx=row_idx: self.handle_result_toggle(idx, state))
                    self.displayed_data_checkboxes[flight_number] = checkbox_data
                    
                    checkbox_fit = QtWidgets.QCheckBox("fit")
                    checkbox_fit.setChecked(flight_number in self.active_displayed_fit_curves)
                    checkbox_fit.stateChanged.connect(lambda state, idx=row_idx: self.handle_fit_toggle(idx, state))  
                    self.displayed_fit_checkboxes[flight_number] = checkbox_fit
                    
                    # Pack them into a QWidget with horizontal layout
                    checkbox_widget = QtWidgets.QWidget()
                    layout = QtWidgets.QHBoxLayout(checkbox_widget)
                    layout.setContentsMargins(0, 0, 0, 0)
                    layout.setSpacing(5)
                    layout.addWidget(checkbox_data)
                    layout.addWidget(checkbox_fit)
                    checkbox_widget.setLayout(layout)
                
                    table.setCellWidget(row_idx, 0, checkbox_widget)
       
        table.blockSignals(False)
        table.setSortingEnabled(True)
        #table.sortItems(0, QtCore.Qt.SortOrder.DescendingOrder)
        #signal for managing edit, delete , or save rows in the table
        table.itemChanged.connect(self.on_item_changed)
        table.itemSelectionChanged.connect(self.set_editable_for_selected_row)
        
        self.apply_alternate_row_colors(table, 1)
        
    def handle_result_toggle(self, row_index, state): #Handle which flight will be displayed in the graph
        scatter_colors = [
        QColor(179, 4, 4),     # Red
        QColor(4, 179, 74),     # Green
        QColor(4, 10, 179),     # Blue
        QColor(237, 28, 206),   # Purple
        # Add more if needed
        ]
        
        entry = self.results[row_index]
        flight_number = entry["metadata"]["Flight Number"]
        
        if state == 2:#Meaning it is checked
            # if hasattr(self, "active_displayed_rows") and len(self.active_displayed_rows) >= 4:
            #     logger.warning("Limit Reached" "You can display up to 4 datasets at a time.")
            #     checkbox = self.displayed_data_checkboxes[flight_number]
            #     checkbox.setChecked(False)
            #     return
    
            self.selected_data_to_compare = self.results[row_index]
            flight_number = self.selected_data_to_compare["metadata"]["Flight Number"]

            

            if not hasattr(self, "active_displayed_rows"):
                self.active_displayed_rows = {}
            
            color = scatter_colors[row_index % len(scatter_colors)]  #Select a color according to the position of the graph displayed 
            
            scatter_a_compare = pg.ScatterPlotItem(brush=pg.mkBrush(color), pen=pg.mkPen(None), size=8)
            scatter_b_compare = pg.ScatterPlotItem(brush=pg.mkBrush(color.lighter(125)), pen=pg.mkPen(None), size=8)
            scatter_a_vxvz = pg.ScatterPlotItem(brush=pg.mkBrush(color), pen=pg.mkPen(None), size=8)
            scatter_b_vxvz = pg.ScatterPlotItem(brush=pg.mkBrush(color.lighter(125)), pen=pg.mkPen(None), size=8)
            
            self.active_displayed_rows[flight_number] = (
            scatter_a_compare, scatter_b_compare, row_index,
            scatter_a_vxvz, scatter_b_vxvz, color
            )
            self.graph_glide_ias_compare.addItem(scatter_a_compare)
            self.graph_glide_ias_compare.addItem(scatter_b_compare)
            self.graph_vxvz.addItem(scatter_a_vxvz)
            self.graph_vxvz.addItem(scatter_b_vxvz)
                
            self.update_polar_graph(
                self.selected_data_to_compare["polar_data"],
                reference=False,
                y_axis_mode=self.unit_mode,
                graph_widget=self.graph_glide_ias_compare,
                scatter_items={
                "a": scatter_a_compare,
                "b": scatter_b_compare},
                dynamic = False
            )
            self.update_vxvz_graph(self.selected_data_to_compare["polar_data"],self.graph_vxvz,scatter_a_vxvz, scatter_b_vxvz, False  )
            
            self.legend_compare.addItem(scatter_a_compare, f"{flight_number}")
            self.legend_vxvz.addItem(scatter_a_vxvz, f"{flight_number}")
        else:
            # Unchecked – remove from graph
            if hasattr(self, "active_displayed_rows") and flight_number in self.active_displayed_rows:

                scatter_a_compare, scatter_b_compare, row_index , scatter_a_vxvz, scatter_b_vxvz, _  = self.active_displayed_rows[flight_number]
                self.graph_glide_ias_compare.removeItem(scatter_a_compare)
                self.graph_glide_ias_compare.removeItem(scatter_b_compare)
                self.graph_vxvz.removeItem(scatter_a_vxvz)
                self.graph_vxvz.removeItem(scatter_b_vxvz)
                self.legend_compare.removeItem(scatter_a_compare)
                self.legend_vxvz.removeItem(scatter_a_vxvz)
                
                if hasattr(self, "displayed_fit_checkboxes"):
                    fit_checkbox = self.displayed_fit_checkboxes[flight_number]  
                    if fit_checkbox and fit_checkbox.isChecked():
                        fit_checkbox.setChecked(False)  # This will call handle_fit_toggle automatically
                del self.active_displayed_rows[flight_number]     #Then we delete
        
                
                
                
    def handle_fit_toggle(self, row_index, state): #Handle which flight will be displayed in the graph

        self.selected_data_to_fit = self.results[row_index]
        flight_number = self.selected_data_to_fit["metadata"]["Flight Number"]

        if state == 2:  # fit checkbox is checked
            if hasattr(self, "displayed_data_checkboxes"):
                data_checkbox = self.displayed_data_checkboxes[str(flight_number)]
                if data_checkbox and not data_checkbox.isChecked():
                    data_checkbox.setChecked(True)

        
        polar_data = self.selected_data_to_fit["polar_data"]

        
                
        _, _, _, _, _, color = self.active_displayed_rows[str(flight_number)]
        

        
        if state == 2:#Meaning it is checked

            # if  len(self.active_displayed_rows) >= 4:
            #     logger.warning("Limit Reached" "You can display up to 4 datasets at a time.")
            #     checkbox = self.displayed_fit_checkboxes[flight_number]
            #     checkbox.setChecked(False)
            #     return

            

            if not hasattr(self, "active_displayed_rows"):
                self.active_displayed_rows = {}
                  
            # ---- Prepare data for fitting ----
            # Extract IAS (x) and Glide (y), and Vx and Vz
            x = []
            y_ratio = []
            y_glide = []
            vx = []
            vz = []
            
            
            for point in polar_data.values():
                    # Probe A
                    if "IAS_a" in point:
                        x.append(point["IAS_a"])
                        y_ratio.append(point["Glide_ratio_a"])
                        y_glide.append(point["Glide_a"])
                        vx.append(point["IAS_a"] * np.cos(np.deg2rad(point["Glide_a"])))
                        vz.append(point["IAS_a"] * np.sin(np.deg2rad(point["Glide_a"])))
                    # Probe B
                    if "IAS_b" in point and point["IAS_b"] is not None:
                        x.append(point["IAS_b"])
                        y_ratio.append(point["Glide_ratio_b"])
                        y_glide.append(point["Glide_b"])
                        vx.append(point["IAS_b"] * np.cos(np.deg2rad(point["Glide_b"])))
                        vz.append(point["IAS_b"] * np.sin(np.deg2rad(point["Glide_b"])))
                        
            x = np.array(x)
            y_glide = np.array(y_glide)
            y_ratio = np.array(y_ratio)
            vx = np.array(vx)
            vz = np.array(vz)
       
 
            # ----Generate fit curve (example: quadratic fit) ----
            if len(x) < 3:  # not enough points for fit
                logger.warning(f"Not enough data to fit for flight {flight_number}")
                return
            
            #Computing the fit curve for IAS vs Glide graph
            y = y_ratio if self.unit_mode == "glide_ratio" else y_glide
            coeffs = np.polyfit(x, y, 2)  # quadratic fit
            fit_fn = np.poly1d(coeffs)
            x_fit = np.linspace(np.min(x)-1, np.max(x)+1, 100)
            y_fit = fit_fn(x_fit)
            fit_curve_compare = pg.PlotDataItem(x_fit, y_fit, pen=pg.mkPen(color, width=1, style=QtCore.Qt.PenStyle.DashLine))
            
            #Computing the fit curve for Vx Vz graph
            coeffs = np.polyfit(vx, vz, 2)  # quadratic fit
            fit_fn = np.poly1d(coeffs)
            x_fit = np.linspace(np.min(vx)-1, np.max(vx)+1, 100)
            y_fit = fit_fn(x_fit)
            fit_curve_vxvz = pg.PlotDataItem(x_fit, y_fit, pen=pg.mkPen(color, width=1, style=QtCore.Qt.PenStyle.DashLine))
            
            # ---- Manage fit curve items ----
            # Store fit curves in a dictionary to remove later
            if not hasattr(self, "active_displayed_fit_curves"):
                self.active_displayed_fit_curves = {} 
            self.active_displayed_fit_curves[flight_number] = {
            "plot_item_compare": fit_curve_compare,
            "plot_item_vxvz" : fit_curve_vxvz,
            "x": x,
            "y_glide": y_glide,
            "y_ratio": y_ratio,
            "vx" : vx,
            "vz" : vz
            }
            
            self.graph_glide_ias_compare.addItem(fit_curve_compare)
            self.graph_vxvz.addItem(fit_curve_vxvz)
    
        # If checkbox is unchecked, remove the fit curve
        else:
            if self.active_displayed_fit_curves[flight_number]:
                self.graph_glide_ias_compare.removeItem(self.active_displayed_fit_curves[flight_number]["plot_item_compare"])
                self.graph_vxvz.removeItem(self.active_displayed_fit_curves[flight_number]["plot_item_vxvz"])
                del self.active_displayed_fit_curves[flight_number]
                logger.info(f"Removed fit curve for flight {flight_number}")   
            else :
                logger.warning("No fit to remove")
  
                

    def update_fit_curves_on_unit_change(self):
        """
        Recompute and redraw all active fit curves when unit_mode changes (concern only the IAS vs Glide graph)
        """
        for flight_number, fit_data in list(self.active_displayed_fit_curves.items()):
            # Remove old curve
            _, _, _, _, _, color = self.active_displayed_rows[str(flight_number)]
            self.graph_glide_ias_compare.removeItem(fit_data["plot_item_compare"])
    
            # Choose correct y values
            y = fit_data["y_ratio"] if self.unit_mode == "glide_ratio" else fit_data["y_glide"]
            x = fit_data["x"]
    
            # Refit
            coeffs = np.polyfit(x, y, 2)
            fit_fn = np.poly1d(coeffs)
            x_fit = np.linspace(0, 16, 100)
            y_fit = fit_fn(x_fit)
    
            # Redraw curve
            new_curve = pg.PlotDataItem(x_fit, y_fit, pen=pg.mkPen(color, width=1, style=QtCore.Qt.PenStyle.DashLine))
            self.graph_glide_ias_compare.addItem(new_curve)
    
            # Update stored curve
            self.active_displayed_fit_curves[flight_number]["plot_item_compare"] = new_curve
    
                
    def get_selected_row_data(self):
        selected_items = self.table_returned_results_compare.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a row first.")
            return
    
        row = selected_items[0].row()
    
        try:
            self.selected_data_to_compare = self.results[row]

            self.update_polar_graph(
                self.selected_data_to_compare["polar_data"],
                reference=False,
                y_axis_mode=self.unit_mode,
                graph_widget=self.graph_glide_ias_compare,
                scatter_items={
                "a": self.scatter_a_compare,
                "b": self.scatter_b_compare},
                dynamic = False
            )
            self.update_vxvz_graph(self.selected_data_to_compare["polar_data"],self.graph_vxvz,self.scatter_a_vxvz, self.scatter_b_vxvz , False )
        

        except IndexError:
            QMessageBox.critical(self, "Data Error", "Selected row does not match result data.")
            
    def display_selected_polar_data_compare(self, row, column):
        entry = self.results[row]
        polar_data = entry.get("polar_data", {})
        
        if not polar_data:
            logger.warning("This entry has no polar_data.")
            return
    
        self.update_polar_table(self.table_display_polar_data_compare, polar_data)
        self.apply_alternate_row_colors(self.table_display_polar_data_compare, 2)
        
        
    def toggle_edit_database_manage(self):
        self.edit_mode_manage = self.pushButton_edit_entry.isChecked()
        
        
        if not self.edit_mode_manage:
            # Désactiver l'édition partout
            for row in range(self.table_returned_results_manage.rowCount()):
                for col in range(self.table_returned_results_manage.columnCount()):
                    item = self.table_returned_results_manage.item(row, col)
                    if item:
                        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            
        else:
          # Activer uniquement pour la ligne sélectionnée
          self.set_editable_for_selected_row()
    
    def on_item_changed(self, item):
        if not self.edit_mode_manage:
            return  # Si pas en mode édition, on ignore
    
        row = item.row()
        col = item.column()
    
        # Récupérer la clé associée à cette colonne
        keys = ["Flight Number", "AUW", "Wing", "Harness", "Probe A", "Probe B", "Flight Date", "Export Date"]
        if col >= len(keys):
            return  # Si hors limites
        key = keys[col]
    
        # Empêcher la modification de Flight Number (au cas où)
        if key == "Flight Number":
            return
    
        new_value = item.text()
        old_value = self.results[row]["metadata"].get(key, "")
    
        if new_value != old_value:
            # Mettre à jour en mémoire
            self.results[row]["metadata"][key] = new_value
    
            # Sauvegarder dans TinyDB
            flight_number = self.results[row]["metadata"]["Flight Number"]
            Q = Query()
            self.db.update({"metadata": self.results[row]["metadata"]}, Q.metadata["Flight Number"] == flight_number)
            logger.info(f"Updated {key} for Flight {flight_number} in DB")
            
    def set_editable_for_selected_row(self):
        if self.edit_mode_manage:
        # Tout désactiver
            for row in range(self.table_returned_results_manage.rowCount()):
                for col in range(self.table_returned_results_manage.columnCount()):
                    item = self.table_returned_results_manage.item(row, col)
                    if item:
                        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        
            # Activer la ligne sélectionnée
            selected_rows = set(idx.row() for idx in self.table_returned_results_manage.selectedIndexes())
            for row in selected_rows:
                for col in range(self.table_returned_results_manage.columnCount()):
                    item = self.table_returned_results_manage.item(row, col)
                    if item:
                        if col != 0:  # Sauf Flight Number
                            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable) 
                            
    def delete_selected_entry_manage(self):
        # Vérifier qu'une ligne est sélectionnée
        selected_rows = set(idx.row() for idx in self.table_returned_results_manage.selectedIndexes())
        if not selected_rows:
            logger.warning("No selection please select a row to delete.")
            return
    
        row = list(selected_rows)[0]  # On prend la première sélectionnée (tu peux gérer multi-sélection plus tard)
        flight_number_item = self.table_returned_results_manage.item(row, 0)
        if not flight_number_item:
            logger.error("No flight number found in the list to delete")
            return
    
        flight_number = flight_number_item.text()
    
        # Demander confirmation
        reply = QMessageBox.question(
            self,
            "Delete Confirmation",
            f"Are you sure you want to delete the flight '{flight_number}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
    
        if reply == QMessageBox.StandardButton.Yes:
            # Supprimer de TinyDB
            Q = Query()
            self.db.remove(Q.metadata["Flight Number"] == flight_number)
    
            # Supprimer de self.results
            self.results = [entry for entry in self.results if entry["metadata"]["Flight Number"] != flight_number]
    
            # Supprimer de l'UI
            self.table_returned_results_manage.removeRow(row)
            
            self.search("manage", self.table_returned_results_manage)
            logger.info(f"Deleted entry with Flight Number {flight_number}")
            
    def export_selected_entry_manage(self):
        
        selected_rows = set(idx.row() for idx in self.table_returned_results_manage.selectedIndexes())
        if not selected_rows:
            logger.warning("No selection please select a row to export.")
            return
    
        row = list(selected_rows)[0]
        entry = self.results[row]  # L'entrée TinyDB correspondante
    
        flight_number = entry["metadata"].get("Flight Number")
        filename = self.create_file_name(flight_number, datetime.now(), 'csv')
    
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save file as .csv", filename, "CSV Files (*.csv);;All Files (*)"
        )
    
        if not filepath:
            return  # Annulé par l'utilisateur
    
        try:
            with open(filepath, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
    
                # ✅ Metadata
                metadata = entry.get("metadata", {})
                writer.writerow(['Export Date', metadata.get("Export Date", "")])
                writer.writerow(['Flight Number', metadata.get("Flight Number", "")])
                writer.writerow(['AUW', metadata.get("AUW", "")])
                writer.writerow(['Harness', metadata.get("Harness", "")])
                writer.writerow(['Wing', metadata.get("Wing", "")])
                writer.writerow(['Comment', metadata.get("Comment", "")])
                writer.writerow(['Flight Date', metadata.get("Flight Date", "")])
                writer.writerow(['Probe A', metadata.get("Probe A", "")])
                writer.writerow(['Probe B', metadata.get("Probe B", "")])
                writer.writerow(['Config version A', metadata.get("Config version A", "")])
                writer.writerow(['Config version B', metadata.get("Config version B", "")])
    
                writer.writerow([])  # Ligne vide
    
                # ✅ Header pour polar_data
                writer.writerow([
                    "IAS A", "IAS B", "Glide A", "Glide B", "Error Glide A", "Error Glide B",
                    "Alpha A", "Alpha B", "Theta A", "Theta B", "DTheta A", "DTheta B",
                    "Lacet A", "Lacet B", "Roulis A", "Roulis B", "Rho A", "Rho B",
                    "Glide Ratio A", "Glide Ratio B", "Error glide Ratio A", "Error glide Ratio B",
                    "Xmin_second", "Xmax_second", "Label"
                ])
    
                # ✅ Données polar_data
                for point in entry.get("polar_data", {}).values():
                    writer.writerow([
                        point.get("IAS_a", ""),
                        point.get("IAS_b", ""),
                        point.get("Glide_a", ""),
                        point.get("Glide_b", ""),
                        point.get("Error_glide_a", ""),
                        point.get("Error_glide_b", ""),
                        point.get("Alpha_a", ""),
                        point.get("Alpha_b", ""),
                        point.get("Theta_a", ""),
                        point.get("Theta_b", ""),
                        point.get("DTheta_a", ""),
                        point.get("DTheta_b", ""),
                        point.get("Lacet_a", ""),
                        point.get("Lacet_b", ""),
                        point.get("Roulis_a", ""),
                        point.get("Roulis_b", ""),
                        point.get("Rho_a", ""),
                        point.get("Rho_b", ""),
                        point.get("Glide_ratio_a", ""),
                        point.get("Glide_ratio_b", ""),
                        point.get("Error_glide_ratio_a", ""),
                        point.get("Error_glide_ratio_b", ""),
                        point.get("Xmin_second", ""),
                        point.get("Xmax_second", ""),
                        point.get("Label", "")
                    ])
    
            logger.info(f"Export successful: {filepath}")
    
        except Exception as e:
            logger.error(f"Failed to export: {e}")
            
    def on_edit_manage_toggled(self, checked):
        """
        Désactive Delete et Export si Edit est actif.
        """
        if checked:
            # Mode édition activé → désactiver delete/export
            self.pushButton_delete_entry.setDisabled(True)
            self.pushButton_export_entry.setDisabled(True)
        else:
            # Mode édition désactivé → réactiver
            self.pushButton_delete_entry.setDisabled(False)
            self.pushButton_export_entry.setDisabled(False)
            
    def create_file_name(self, flight: str, date, filetype: str): #Little function to create a path file for export
        file_name =  'polar_' + flight + '_' +  date.strftime("%Y%m%d%H%M%S") +'.' + filetype
        return file_name
                
class ExportDialog(QtWidgets.QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.db = db
        def resource_path(relative_path):
            #Get absolute path to resource (for PyInstaller and development) , I don't really understand but it seems useful for lauching as a onefile exe
            if hasattr(sys, '_MEIPASS'):
                return Path(sys._MEIPASS) / relative_path
            return Path(__file__).parent / relative_path


        uic.loadUi(resource_path("export.ui"), self)  # Load the .ui file directly
        
        
        self.setWindowTitle("Export")
        self.parent = parent
    
        self.pushButton_export_analysis.clicked.connect(self.save_file_csv)
        self.pushButton_save_analysis.clicked.connect(self.save_to_database)
        self.button_export_flight_file_A.clicked.connect(lambda : self.save_flight_csv("A"))
        self.button_export_flight_file_B.clicked.connect(lambda : self.save_flight_csv("B"))

        
        self.button_export_flight_file_B.setEnabled(False)
        
                    

                
        
    def save_file_csv(self):
        logger.detail("STATE SAVE FILE CSV")
        if len(self.parent.polar_data) == 0: #If there is nothing to save
            logger.warning("There is nothing to save")    
        #self.parent.add_log("There is nothing to save")
            return 
        
        if not self.input_flight_number.text().strip():#if the user forgot to write the flight number
            logger.error("Please provide a correct flight number in order to save the file")  
            #self.parent.add_log("Please provide a correct flight number in order to save the file")
            return
        
        filename = self.parent.create_file_name(self.input_flight_number.text(), datetime.now(), 'csv')
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save file as .csv", filename, "CSV Files (*.csv);;All Files (*)")
        
        if self.parent.flight_dic["A"]["flight_date"] == self.parent.flight_dic["B"]["flight_date"]:
            flight_date = self.parent.flight_dic["A"]["flight_date"]
        elif self.parent.flight_dic["A"]["flight_date"] is not None:
            flight_date = self.parent.flight_dic["A"]["flight_date"]
        elif self.parent.flight_dic["B"]["flight_date"] is not None:
            flight_date = self.parent.flight_dic["B"]["flight_date"]
        else:
            flight_date = ""
        
        if filepath:
            try:
                with open(filepath, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
        
                    # Metadata
                    writer.writerow(['Export Date' , datetime.now().isoformat()])
                    writer.writerow(['Flight Number',self.input_flight_number.text()])
                    writer.writerow(['AUW',self.input_auw.text()])
                    writer.writerow(['Harness',self.input_harness.text()])
                    writer.writerow(['Wing',self.input_wing.text()])
                    writer.writerow(['Comment', self.input_comment.text()])
                    writer.writerow(['Flight Date' , flight_date])
                    writer.writerow(['Probe A',self.parent.flight_dic["A"]["probe_number"]])
                    writer.writerow(['Probe B',self.parent.flight_dic["B"]["probe_number"]])
                    writer.writerow(['Config version A',self.parent.flight_dic["A"]["config_version"]])
                    writer.writerow(['Config version B',self.parent.flight_dic["B"]["config_version"]])
                
                    writer.writerow([])  # Empty line
        
                    # Header
                    writer.writerow([
                        "IAS A", "IAS B", "Glide A" , "Glide B", "Error Glide A",  "Error Glide B", "Alpha A", "Alpha B", "Theta A", "Theta B" , "DTheta A", "DTheta B", "Lacet A", "Lacet B", "Roulis A" , "Roulis B", "Rho A", "Rho B", "Glide Ratio A", "Glide Ratio B","Error glide Ratio A", "Error glide Ratio B", "Xmin_second", "Xmax_second", "Label"
                    ])
        
                    # Write data
                    for point in self.parent.polar_data.values():
                        writer.writerow([
                            point["IAS_a"],
                            point["IAS_b"],
                            point["Glide_a"],
                            point["Glide_b"],
                            point["Error_glide_a"],
                            point["Error_glide_b"],
                            point["Alpha_a"],
                            point["Alpha_b"],
                            point["Theta_a"],
                            point["Theta_b"],
                            point["DTheta_a"],
                            point["DTheta_b"],
                            point["Lacet_a"],
                            point["Lacet_b"],
                            point["Roulis_a"],
                            point["Roulis_b"],
                            point["Rho_a"],
                            point["Rho_b"],
                            point["Glide_ratio_a"],
                            point["Glide_ratio_b"],
                            point["Error_glide_ratio_a"],
                            point["Error_glide_ratio_b"],
                            point["Xmin_second"],
                            point["Xmax_second"],
                            point["Label"]
                        ])
                #self.parent.add_log(f"Save succesful : {filepath} ")
                logger.info(f"Save succesful : {filepath} ")
                self.accept()
        
            except Exception as e:
                logger.error(f"Failed to export: {e}")
                #self.parent.add_log("Error", f"Failed to export: {e}")
                
                
   

    def save_to_database(self):
        logger.detail("STATE SAVE FILE TO DATABASE")
        Q = Query()
        if len(self.parent.polar_data) == 0: #If there is nothing to save
            logger.warning("There is nothing to save")
            return 
        
        if not self.input_flight_number.text().strip(): #if the user forgot to write the flight number
            logger.error("Please provide a correct flight number in order to save the file")
            return  
        
        elif self.db.search(Q.metadata["Flight Number"] == self.input_flight_number.text().strip()):
        
            reply = QMessageBox.question(
                self,
                "Caution !",
                f"The flight number '{self.input_flight_number.text().strip()}' already exists in the database.\nDo you want to overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return  # Stop saving process
            else:
                # Overwrite existing data
                self.db.remove(Q.metadata["Flight Number"] == self.input_flight_number.text().strip())
    
        else:
            # No conflict, insert as new
            logger.info("Writing in database")
   
            
        
        if self.parent.flight_dic["A"]["flight_date"] == self.parent.flight_dic["B"]["flight_date"]:
            flight_date = self.parent.flight_dic["A"]["flight_date"]
        elif self.parent.flight_dic["A"]["flight_date"] is not None:
            flight_date = self.parent.flight_dic["A"]["flight_date"]
        elif self.parent.flight_dic["B"]["flight_date"] is not None:
            flight_date = self.parent.flight_dic["B"]["flight_date"]
        else:
            flight_date = ""
        
        
        
        export_data = {
            "metadata": {
                "Export Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Flight Number": self.input_flight_number.text(),
                "Flight Date" : flight_date,
                "Probe A" : self.parent.flight_dic["A"]["probe_number"],
                "Probe B" : self.parent.flight_dic["B"]["probe_number"],
                "Config version A" : self.parent.flight_dic["A"]["config_version"],
                "Config version B" : self.parent.flight_dic["B"]["config_version"],
                "AUW" : self.input_auw.text(),
                "Harness": self.input_harness.text(),
                "Wing" : self.input_wing.text() ,
                "Comment": self.input_comment.text()
                },
            "polar_data": {}
        }
        for point_id, point in self.parent.polar_data.items():
            desirable_data = {
              "Label": point.get("Label"),
              "Xmin_second": point.get("Xmin_second"),
              "Xmax_second": point.get("Xmax_second"),
              "IAS_a": point.get("IAS_a"),
              "IAS_b": point.get("IAS_b"),
              "Glide_a": point.get("Glide_a"),
              "Glide_b": point.get("Glide_b"),
              "Error_glide_a": point.get("Error_glide_a"),
              "Error_glide_b": point.get("Error_glide_b"),
              "error_bar_a": None,
              "error_bar_b": None,
              "Alpha_a": point.get("Alpha_a"),
              "Alpha_b": point.get("Alpha_b"),
              "Theta_a": point.get("Theta_a"),
              "Theta_b": point.get("Theta_b"),
              "DTheta_a": point.get("DTheta_a"),
              "DTheta_b": point.get("DTheta_b"),
              "Lacet_a": point.get("Lacet_a"),
              "Lacet_b": point.get("Lacet_b"),
              "Roulis_a": point.get("Roulis_a"),
              "Roulis_b": point.get("Roulis_b"),
              "Rho_a": point.get("Rho_a"),
              "Rho_b": point.get("Rho_b"),
              "Glide_ratio_a": point.get("Glide_ratio_a"),
              "Glide_ratio_b": point.get("Glide_ratio_b"),
              "Error_glide_ratio_a": point.get("Error_glide_ratio_a"),
              "Error_glide_ratio_b": point.get("Error_glide_ratio_b"),
              }
            export_data["polar_data"][point_id] = desirable_data
        
        self.db.insert(export_data)
        logger.info("Done")
        #self.parent.add_log("Done")

    def save_flight_csv(self, flight):
        logger.detail("STATE SAVE FLIGHT CSV")
        if flight == "A":
            if not self.input_flight_number.text().strip(): #if the user forgot to write the flight number
                #self.parent.add_log("Please provide a correct flight A number in order to save the file")
                logger.error("Please provide a correct flight A number in order to save the file")
                return  

        filename = self.parent.flight_dic[flight]['raw_path'].stem + '_analyzed.csv'  #we just add "analyzed" in the name of the file
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save file as .csv", filename, "CSV Files (*.csv);;All Files (*)")
        
        if filepath:
            try:
                with open(filepath, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
        
                    # Metadata
                    writer.writerow(['Export Date' , datetime.now().isoformat()])
                    writer.writerow(['Raw file path',self.parent.flight_dic[flight]['raw_path']])
                    writer.writerow(['Config file path',self.parent.flight_dic[flight]['config_path']])
                    writer.writerow(['Has GPS ',self.parent.flight_dic[flight]['has_gps']])
                    writer.writerow(['Flight Date',self.parent.flight_dic[flight]['flight_date']])
                    writer.writerow(['Config version', self.parent.flight_dic[flight]['config_version']])
                    writer.writerow(['Probe', self.parent.flight_dic[flight]['probe_number']])
                    writer.writerow([])  # Empty line

                    writer.writerow(['Flight Number',self.input_flight_number.text()])
                    writer.writerow(['AUW',self.input_auw.text()])
                    writer.writerow(['Harness',self.input_harness.text()])
                    writer.writerow(['Wing',self.input_wing.text()])
                    writer.writerow(['Comment', self.input_comment.text()])
                    writer.writerow([])  # Empty line
        
                    # Header
                    writer.writerow([
                        "Time", "IAS", "Glide" , "Alpha" , "Theta", "DTheta", "Roulis", "Rho", "Lacet"
                    ])
        
                    # Write datas

                    
                    for i in range(len(self.parent.flight_dic[flight]['processed_data']["time"])):
                        writer.writerow([
                            self.parent.flight_dic[flight]['processed_data']["time"][i],
                            #self.parent.flight_dic[flight]['processed_data']["date"][i],
                            self.parent.flight_dic[flight]['processed_data']["ias"][i],
                            self.parent.flight_dic[flight]['processed_data']["glide"][i],
                            self.parent.flight_dic[flight]['processed_data']["alpha"][i],
                            self.parent.flight_dic[flight]['processed_data']["theta"][i],
                            self.parent.flight_dic[flight]['processed_data']["dtheta"][i],
                            self.parent.flight_dic[flight]['processed_data']["roulis"][i],
                            self.parent.flight_dic[flight]['processed_data']["rho"][i],
                            self.parent.flight_dic[flight]['processed_data']["lacet"][i],
                            
                   
    ])

                #self.parent.add_log(f"Save succesful : {filepath} ")
                logger.info(f"Save succesful : {filepath} ")
                self.accept()
        
            except Exception as e:
                logger.error(f"Failed to export: {e}")
                #self.parent.add_log(f"Error : Failed to export: {e}")



                    
    @QtCore.pyqtSlot(str, bool)
    def handle_update(self, action, status):  #This function handle the signals sent from the main window

        if action == "Dual analysis enabled":
            self.button_export_flight_file_B.setEnabled(status)



class ReferenceDialog(QtWidgets.QDialog):
    
    reference_loaded = pyqtSignal(bool)   # This will emit the reference polar data
    
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.db = db
        def resource_path(relative_path):
            #Get absolute path to resource (for PyInstaller and development) , I don't really understand but it seems useful for lauching as a onefile exe
            if hasattr(sys, '_MEIPASS'):
                return Path(sys._MEIPASS) / relative_path
            return Path(__file__).parent / relative_path


        uic.loadUi(resource_path("reference.ui"), self)  # Load the .ui file directly
        
        self.search_button_reference.clicked.connect(self.search)
        
        self.table_returned_results_reference.horizontalHeader().setStretchLastSection(True)
        #self.table_returned_results.cellClicked.connect(self.parent.raw_table_clicked)
        self.table_returned_results_reference.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_returned_results_reference.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        
        
        self.select_button_reference.clicked.connect(self.get_selected_row_data)
        
        self.parent = parent
        self.results = []
        
        
        
    def apply_alternate_row_colors(self, table):
        for row in range(table.rowCount()):
            color = QColor(240, 240, 240) if row % 2 == 0 else QColor(255, 255, 255)
            for col in range(table.columnCount()):
                self.parent.set_cell_background(table, row, col, color)
                    
        
    def search(self):
        #Cette fonction est une copie de celle qu'on retrouve dans la classe main : c'est normal et plus facile à gérer entre 2 classes pour les widgets
        
        logger.detail("STATE SEARCH IN DATABASE REFERENCE")
        self.table_returned_results_reference.setRowCount(0)  # Clear previous results

        if self.search_flight_date_reference.date().toString("yyyy") == "2000": #This means the user didn't choose a date as criteria
            flight_date = ""
        else:
            flight_date = self.search_flight_date_reference.date().toString("yyyy-MM-dd")
    
            
        if self.search_export_date_reference.date().toString("yyyy") == "2000": #This means the user didn't choose a date as criteria
            export_date = ""
        else:
            export_date = self.search_export_date_reference.date().toString("yyyy-MM-dd")

        # Read all search keywords and lowercase them
        criteria = {
            "Flight Number": self.search_bar_flight_number_reference.text().strip().lower(),
            "AUW": self.search_bar_auw_reference.text().strip().lower(),
            "Wing": self.search_bar_wing_reference.text().strip().lower(),
            "Harness": self.search_bar_harness_reference.text().strip().lower(),
            "Probe": self.search_bar_probe_number_reference.text().strip().lower(),

            "Flight Date": flight_date,
            "Export Date":  export_date
        }
    
        # Build the TinyDB query dynamically
        Flight = Query()
        query = None
        if all(value == "" for value in criteria.values()):
            self.results = self.db.all()  # Show all records
        else:
            for key, keyword in criteria.items():
                if keyword != "": #We select all the relevant criteria : those where the user input
                    if key == "Probe":  # handle Probe A & B together
                        condition_a = Flight.metadata["Probe A"].test(lambda val, k=keyword: k in str(val).lower())
                        condition_b = Flight.metadata["Probe B"].test(lambda val, k=keyword: k in str(val).lower())
                        condition = condition_a | condition_b  # Match if A or B contains the keyword
                    else:
                        condition = Flight.metadata[key].test(lambda val, k=keyword: k in str(val).lower())
                    query = condition if query is None else query & condition
            # Perform query
            if query:
                self.results = self.db.search(query) 

            else:
                logger.info("No results")
                self.results = []
        
        self.results.sort(key=lambda x: int(x["metadata"].get("Flight Number", 0)))
        self.table_returned_results_reference.setRowCount(len(self.results))
        self.results_size_lcd_reference.display(len(self.results))
        

        
        for row_idx, entry in enumerate(self.results):
            meta = entry["metadata"]
            row_data = [
                meta.get("Flight Number", ""),
                meta.get("AUW", ""),
                meta.get("Wing", ""),
                meta.get("Harness", ""),
                meta.get("Probe A", ""),
                meta.get("Probe B", ""),
                meta.get("Flight Date", ""),
                meta.get("Export Date", "")
            ]

            for col_idx, value in enumerate(row_data):
                item = QtWidgets.QTableWidgetItem(value)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                if col_idx == 0: #If it's the flight number
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, value) # specific role for flight number in order to sort it 
                self.table_returned_results_reference.setItem(row_idx, col_idx, item)
            
            self.apply_alternate_row_colors(self.table_returned_results_reference)
            
          
    
    
    def get_selected_row_data(self):
        
        #Getting the row number
        selected_items = self.table_returned_results_reference.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a row first.")
            return
        row = selected_items[0].row()
        
        self.parent.reference_polar_data = self.results[row]

        #row_data = [self.table_returned_results.item(row, col).text() for col in range(self.table_returned_results.columnCount())]
        
        self.parent.update_polar_graph(
            self.parent.reference_polar_data["polar_data"],
            reference=True,
            y_axis_mode=self.parent.unit_mode,
            graph_widget=self.parent.graph_glide_ias,
            scatter_items={
            "ref_a": self.parent.scatter_ref_a,
            "ref_b": self.parent.scatter_ref_b},
            dynamic = False
        ) 
        if self.parent.reference_polar_data["polar_data"]:
            self.reference_loaded.emit(True)
            self.parent.actual_reference_displayed.setText(self.parent.reference_polar_data["metadata"]["Flight Number"]) 
        else : 
            self.reference_loaded.emit(False)

        
        self.accept() 
        

    
