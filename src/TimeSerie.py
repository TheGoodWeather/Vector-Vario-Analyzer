from PyQt6 import QtWidgets
import pyqtgraph as pg
import numpy as np
from PyQt6 import QtCore , QtGui
import plot
from table_handler import populate_table_1D_variable
from utils import mapping, rgba_to_hex, hex_to_rgba
from paraglider_widget import ParaGliderWidget
from PyQt6.QtWidgets import QHeaderView, QTableWidgetItem, QVBoxLayout, QWidget, QStackedLayout
from units import convert_array_to_unit, get_unit, convert_gps_to_local_xy
from utils import get_label, get_variable, interp_spline, interp_nearest
from PyQt6.QtGui import QFontMetrics, QPainter, QColor, QPen, QFont
from PyQt6.QtCore import QSettings, Qt

class TimeSerie:
    def __init__(self, 
                flight,
                graph1_tab1D,
                graph1_tab2D,
                comboBox_flight_tab1D,
                tableWidget_variable_plot1,
                tableWidget_variable_plot2,
                checkBox_x_axis_link,
                ):
        

        super().__init__()
        self.flight = flight
        self.graph1_tab1D = graph1_tab1D
        self.graph1_tab2D = graph1_tab2D
        self.comboBox_flight_tab1D = comboBox_flight_tab1D
        self.tableWidget_variable_plot1 = tableWidget_variable_plot1
        self.tableWidget_variable_plot2 = tableWidget_variable_plot2
        self.checkBox_x_axis_link=  checkBox_x_axis_link
        self._setup_widgets()

    def _setup_widgets(self):
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
        
        self.graph1_tab1D.scene().sigMouseClicked.connect(lambda event: self.on_1D_point_clicked(event, self.flight, self.graph1_tab1D, self.tableWidget_variable_plot1))
        self.graph2_tab1D.scene().sigMouseClicked.connect(lambda event: self.on_1D_point_clicked(event, self.flight, self.graph2_tab1D, self.tableWidget_variable_plot2))


    def on_1D_point_clicked(self, event, plot_widget, table_data):
        """
        This function displays crosshair to the closest point where the user clicked
        It also retrieves the corresponding flight and displays its value on the data table
        Remove previous crosshair from other flights aswell 
        """

        
        pos = event.scenePos()
        crosshair_id = plot_widget.crosshair_id
        vb = plot_widget.getViewBox()
        
        flight_selected_dic = None
        mouse_point = vb.mapSceneToView(pos)
        x_click = mouse_point.x()
        y_click = mouse_point.y()
    
        flight_selected = self.comboBox_flight_tab1D.currentText()
        variables_checked = self._get_checked_variables(table_data)
        
        
        if not variables_checked:
            return

        for flight in self.flight:
            if (flight['file_name'].split(".")[0] == flight_selected) or (flight['metadata']['alias'] == flight_selected):
                
                flight_selected_dic = flight
                GNSS_time_timestamped = np.array([t.timestamp() for t in flight_selected_dic['data']['GNSS_time']])
                idx = np.searchsorted(GNSS_time_timestamped, x_click)
                if idx > len(flight_selected_dic['data']['GNSS_time']) -1:
                    idx = len(flight_selected_dic['data']['GNSS_time']) -1
                if idx < 0:
                    idx = 0
            else:
                pass
            
        dist = []
        
        for variable in variables_checked:
            x_val = flight_selected_dic['data']['GNSS_time'][idx].timestamp()
            y_val = convert_array_to_unit(flight_selected_dic['data'][variable], variable)[idx]  # ← unité convertie
        
            point_view = QtCore.QPointF(x_val, y_val)
            point_scene = vb.mapViewToScene(point_view)
        
            dx = abs(pos.x() - point_scene.x())
            dy = abs(pos.y() - point_scene.y())
            d = np.sqrt(dx**2 + dy**2)  # distance euclidienne en pixels
        
            dist.append((d, variable))
           
        closest_variable = min(dist, key=lambda x: x[0])[1] 
        closest_distance = min(dist, key=lambda x: x[0])[0] 
        

        if closest_distance < 20: #if the click is below 20 pixels
             
                    #setting the crosshair
            if flight_selected_dic['plot'][f'crosshair_v_time_{crosshair_id}']:
                flight_selected_dic['plot'][f'crosshair_v_time_{crosshair_id}'].setValue(float(flight_selected_dic['data']['GNSS_time'][idx].timestamp()))
                flight_selected_dic['plot'][f'crosshair_h_time_{crosshair_id}'].setValue(convert_array_to_unit(float(flight_selected_dic['data'][closest_variable][idx]),closest_variable))
                
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
                flight_selected_dic['plot'][f'crosshair_v_time_{crosshair_id}'] = crosshair_v
                flight_selected_dic['plot'][f'crosshair_h_time_{crosshair_id}'] = crosshair_h
                flight_selected_dic['plot'][f'crosshair_v_time_{crosshair_id}'].setValue(float(flight_selected_dic['data']['GNSS_time'][idx].timestamp()))
                flight_selected_dic['plot'][f'crosshair_h_time_{crosshair_id}'].setValue(convert_array_to_unit(float(flight_selected_dic['data'][closest_variable][idx]),closest_variable))
    
             
            for row in range(table_data.rowCount()): #Updating table content
                variable_already_set = table_data.item(row, 0).data(Qt.ItemDataRole.UserRole) 
                data = convert_array_to_unit(flight_selected_dic['data'][variable_already_set], variable_already_set)
                if isinstance(data[idx], float):
                    item_value = QTableWidgetItem(str(round(data[idx],2)))
                else:
                    item_value = QTableWidgetItem(str(data[idx]))
                item_value.setFlags(item_value.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table_data.setItem(row, 1, item_value)
                
                item_unit = QTableWidgetItem(get_unit(variable_already_set))
                item_unit.setFlags(item_unit.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table_data.setItem(row, 2, item_unit)
                    
        else:
            for row in range(table_data.rowCount()): # Clearing the table contents
                
                table_data.setItem(row, 1, QTableWidgetItem(""))
                table_data.setItem(row, 2, QTableWidgetItem(""))
           
            if flight_selected_dic['plot'][f'crosshair_v_time_{crosshair_id}']:
                plot_widget.removeItem(flight_selected_dic['plot'][f'crosshair_v_time_{crosshair_id}'])
                plot_widget.removeItem(flight_selected_dic['plot'][f'crosshair_h_time_{crosshair_id}'])
                flight_selected_dic['plot'][f'crosshair_v_time_{crosshair_id}'] = None
                flight_selected_dic['plot'][f'crosshair_h_time_{crosshair_id}'] = None


    def _get_checked_variables(self, table_widget):
        """
        Returns the variables checked to be displayed in the 1D Tab
        """
        checked_vars = []
        
        for row in range(table_widget.rowCount()):
            item = table_widget.item(row, 0)

            if item and item.checkState() == Qt.CheckState.Checked:
                checked_vars.append(item.data(Qt.ItemDataRole.UserRole))
                
        return checked_vars