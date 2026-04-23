import pyqtgraph as pg
from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtWidgets import QListWidgetItem, QApplication, QLineEdit, QWidget, QVBoxLayout,QTableWidgetItem ,QButtonGroup , QPushButton, QHBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from PyQt6.QtGui import QColor, QPen, QBrush
import numpy as np
import datetime
from units import convert_array_to_unit , get_unit
from table_handler import create_polar_table
import math
import pprint
from utils import get_label

settings = QSettings("Vector Vario", "VVA") #Initialize settings
pg.setConfigOptions(useOpenGL=True)
pg.setConfigOptions(antialias=True)

colors = [
   QColor(253, 50, 22),     
   QColor(128, 204, 0),
   QColor(156, 85, 31),
   QColor(4, 128, 184),     
   QColor(156, 39, 176),
   QColor(194, 23, 154)
   
   ]



def update_1D_plot(flight_dic, comboBox_flight , table_widget, plot_widget, curve1, curve2):
    """
    This function was initially written in order to handle multiple plot on the same graph. 
    For now it only plot twos as it is to complex to add several scales with pyqtgraph.
    """
    

    crosshair_id = plot_widget.crosshair_id
    plot_widget.enableAutoRange()
    variables = get_checked_variables(table_widget)
    legend = plot_widget.addLegend()
    legend.clear()
    
    remove_crosshair(flight_dic, plot_widget, f"time_{crosshair_id}")

    if not comboBox_flight.currentText(): #Fix to prevent load an empty file . Happens when the combobox takes too long to change
        return

    if len(variables) == 0:
        curve1.setData([], [])
        curve2.setData([], [])
        legend.clear()
        remove_crosshair(flight_dic, plot_widget, f"time_{crosshair_id}")
        return
    
    
    for flight in flight_dic:
        if flight['plot']['crosshair_v_time_1']: #Removing crosshairs
            plot_widget.removeItem(flight['plot']['crosshair_v_time_1'])
            plot_widget.removeItem(flight['plot']['crosshair_h_time_1'])
            flight['plot']['crosshair_v_time_1'] = None
            flight['plot']['crosshair_h_time_1'] = None
            
        if flight['file_name'].split(".")[0] == comboBox_flight.currentText() or  flight['metadata']['alias'] == comboBox_flight.currentText() :
            
    
            x = np.array([t.timestamp() for t in flight['data']['GNSS_time']])
            y1 = convert_array_to_unit(flight['data'][variables[0]], variables[0])
            x_min_limit= np.min(x) - 10
            x_max_limit= np.max(x) + 10 
            # y1_min_limit= int(np.min(y1) - (0.1 * (np.max(y1) - np.min(y1))))
            # y1_max_limit= int(np.max(y1) + (0.1 * (np.max(y1) - np.min(y1)))) 
            y1_min_limit= np.min(y1) - (0.1 * (np.max(y1) - np.min(y1)))
            y1_max_limit= np.max(y1) + (0.1 * (np.max(y1) - np.min(y1)))

            plot_widget.setLabel("left", f"{variables[0]} {get_unit(variables[0])}")
            plot_widget.setTitle(f"{variables[0]} vs time")
            plot_widget.setLimits(
                xMin=x_min_limit,
                xMax=x_max_limit,
                yMin=y1_min_limit,
                yMax=y1_max_limit
            )
            
            pen1 = pg.mkPen(flight['plot']['plot_color'], width=1)
            legend.addItem(curve1, variables[0])
            curve1.setPen(pen1)
            curve1.setData(x, y1,
                pen=pen1,
                symbol='o',
                symbolSize=5,
                symbolBrush=(0, 0, 0, 0),  # invisible
                symbolPen=None
            )
            
            
            if len(variables) > 1:
                
                y2 = convert_array_to_unit(flight['data'][variables[1]], variables[1])
                y2_min_limit= np.min(y2) - (0.1 * (np.max(y2) - np.min(y2)))
                y2_max_limit= np.max(y2) + (0.1 * (np.max(y2) - np.min(y2)))
                y_min_limit= min(y2_min_limit, y1_min_limit)
                y_max_limit= max(y2_max_limit, y1_max_limit)
                
                plot_widget.setLabel("left", f"{variables[0]} {get_unit(variables[0])} / {variables[1]} {get_unit(variables[1])}")
                plot_widget.setTitle(f"{variables[0]} and {variables[1]} vs time")
                plot_widget.setLimits(
                    xMin=x_min_limit,
                    xMax=x_max_limit,
                    yMin=y_min_limit,
                    yMax=y_max_limit
                )
                pen2 = pg.mkPen(flight['plot']['plot_color'].darker(), width=1)
                legend.addItem(curve2, variables[1])
                curve2.setPen(pen2)
                curve2.setData(x, y2, pen=pen2,
                symbol='o',
                symbolSize=5,
                symbolBrush=(0, 0, 0, 0),  # invisible
                symbolPen=None
                )
            else:
                curve2.setData([], [])

            plot_widget.autoRange()
        
            
def get_checked_variables(table_widget):
    """
    Returns the variables checked to be displayed in the 1D Tab
    """
    checked_vars = []
    
    for row in range(table_widget.rowCount()):
        item = table_widget.item(row, 0)

        if item and item.checkState() == Qt.CheckState.Checked:
            checked_vars.append(item.text())
            
    return checked_vars

def get_flight_variable_2D(table_widget):
    """
    Returns which flights is selected to be displayed in the 2D map 
    """
    flights_selected = []
    for row in range(table_widget.rowCount()):
        checkbox_item = table_widget.item(row, 0)
        if checkbox_item.checkState() == Qt.CheckState.Checked:
            flight_name = checkbox_item.text()
            if table_widget.cellWidget(row, 1).currentText() != 'None':
                variable = table_widget.cellWidget(row, 1).currentText() #fetch the associated variable
            else:
                variable = None
            flights_selected.append((flight_name,variable))
    return flights_selected

def save_checked_variables_1D(flight_dic, comboBox_flight, table_widget1, table_widget2):
    """
    Save the variables that has been checked to display in graph 1D
    each time we tick a new variable
    """
    current_flight_name = comboBox_flight.currentText()

    for flight in flight_dic:
        if flight['file_name'].split(".")[0] == current_flight_name or flight['metadata']['alias'] == current_flight_name :

            flight['plot']['variables_1D'] = [[],[]]

            for row in range(table_widget1.rowCount()):
                item_check_1 = table_widget1.item(row, 0)
                if item_check_1 and item_check_1.checkState() == Qt.CheckState.Checked:
                        flight['plot']['variables_1D'][0].append(item_check_1.text())
            
            
            for row in range(table_widget2.rowCount()):
                item_check_2 = table_widget2.item(row, 0)            
                if item_check_2 and item_check_2.checkState() == Qt.CheckState.Checked:
                    flight['plot']['variables_1D'][1].append(item_check_2.text())
            

def restore_checked_variables_1D(flight_dic, comboBox_flight, table_widget1, table_widget2):
    """
    Restore the variables that have been previously checked to display in graph 1D
    """
    current_flight_name = comboBox_flight.currentText()

    for flight in flight_dic:
        if (flight['file_name'].split(".")[0] == current_flight_name or 
            flight['metadata']['alias'] == current_flight_name):
            
            selected = flight['plot']['variables_1D']
            #  TABLE 1
            for row in range(table_widget1.rowCount()):
                item_check = table_widget1.item(row, 0)
                if item_check:
                    if item_check.text() in selected[0]:
                        item_check.setCheckState(Qt.CheckState.Checked)
                    else:
                        item_check.setCheckState(Qt.CheckState.Unchecked)

            #  TABLE 2
            for row in range(table_widget2.rowCount()):
                item_check = table_widget2.item(row, 0)
                if item_check:
                    if item_check.text() in selected[1]:
                        item_check.setCheckState(Qt.CheckState.Checked)
                    else:
                        item_check.setCheckState(Qt.CheckState.Unchecked)


def clear_plots_1D(plot1, plot2):
    if plot1:
        plot1.clear()
    else:
        return
    if plot2:
        plot2.clear()
    else:
        return


def toggle_x_link(plot1, plot2, checkbox):
    if checkbox.isChecked():
        plot2.setXLink(plot1)
    else:
        plot2.setXLink(None)



    
def update_2D_plot(flight_dic, tab_widget_flight, plot_widget):
    """
    Big function that creates the 2D graph, and add mapping colors to it according to a selected variable
    """

    settings.beginGroup("colors")
    color = QColor(settings.value("plot", "#ff0000"))   
    settings.endGroup()
    flight_selected = get_flight_variable_2D(tab_widget_flight)

    selected_names = [f for f, v in flight_selected]
    
    
    #Removing all previous highlighted point if they exists
    for flight in flight_dic:
        if flight['plot']['highlight_point_map']: 
            plot_widget.removeItem(flight['plot']['highlight_point_map'])
            flight['plot']['highlight_point_map'] = None
        
    
    for flight in flight_dic:

        flight_name = flight['file_name'].split(".")[0]
        alias = flight['metadata']['alias']

        is_selected = flight_name in selected_names or alias in selected_names

        # récupérer variable
        variable = None
        for f_name, var in flight_selected:
            if f_name == flight_name or f_name == alias:
                variable = var
                break

        if is_selected:

            x = flight['data']['GNSS_lon']
            y = flight['data']['GNSS_lat']

            # REMOVE ancien plot UNE FOIS
            if flight['plot']['scatter_map']:
                plot_widget.removeItem(flight['plot']['scatter_map'])
                flight['plot']['scatter_map'] = None
            
            # Suppression ancienne courbe de liaison si elle existe
            if flight['plot'].get('link_curve_map'):
                plot_widget.removeItem(flight['plot']['link_curve_map'])
                flight['plot']['link_curve_map'] = None

            
            # --- Interpolation x1 . Set to anticipate future improvements---
            t_orig = np.arange(len(x))
            t_new  = np.linspace(0, len(x) - 1, len(x) *1)
            x_interp = np.interp(t_new, t_orig, x)
            y_interp = np.interp(t_new, t_orig, y)
            
            
            if not variable:
                pen = pg.mkPen(color, width=2)

                flight['plot']['scatter_map'] = plot_widget.plot(
                    x=x,
                    y=y,
                    pen=pen
                )

            else:
                
       
                
                cmap = pg.colormap.get('turbo')
                z = flight['data'][variable]
            
                # Interpolation de z également
                z_interp = np.interp(t_new, t_orig, z)
             
                z_min, z_max = np.nanmin(z_interp), np.nanmax(z_interp)            
            
                #z_min, z_max = np.nanmin(z), np.nanmax(z)
                
                if z_max - z_min == 0:
                    norm = np.zeros_like(z_interp)
                else:
                    norm = (z_interp - z_min) / (z_max - z_min)
                
           
                brush = cmap.map(norm, mode='qcolor')
                pen = None
                
                link_pen = pg.mkPen(QColor(180, 180, 180, 150), width=1)
                link_curve = pg.PlotCurveItem(x=x_interp, y=y_interp, pen=link_pen)
                link_curve.setZValue(-1)
                plot_widget.addItem(link_curve)
                flight['plot']['link_curve_map'] = link_curve
             
                flight['plot']['scatter_map'] = pg.ScatterPlotItem(
                    x=x_interp,
                    y=y_interp,
                    brush=brush,
                    size=6,
                    pen=None
                )
                plot_widget.addItem(flight['plot']['scatter_map'])
                # if flight['plot']['scatter_map']:
                #     plot_widget.removeItem(flight['plot']['scatter_map'])
                # flight['plot']['scatter_map'] = pg.ScatterPlotItem(
                #     x=x,
                #     y=y,
                #     brush=brush,
                #     size=10,
                #     pen=pen
                # )
                # plot_widget.addItem(flight['plot']['scatter_map'])
              

            # START / END
            if not flight['plot']['text_map_start']:
                start = pg.TextItem("Start", color='black')
                plot_widget.addItem(start)
                flight['plot']['text_map_start'] = start
               
            if not flight['plot']['text_map_end']:
                end = pg.TextItem("End", color='black')
                plot_widget.addItem(end)
                flight['plot']['text_map_end'] = end
                
            flight['plot']['text_map_start'].setPos(x[0], y[0])
            flight['plot']['text_map_start'].show()
            flight['plot']['text_map_end'].setPos(x[-1], y[-1])
            flight['plot']['text_map_end'].show()
        else:
            
            if flight['plot']['scatter_map']:
                plot_widget.removeItem(flight['plot']['scatter_map'])
                flight['plot']['scatter_map'] = None
                
            if flight['plot'].get('link_curve_map'):
                plot_widget.removeItem(flight['plot']['link_curve_map'])
                flight['plot']['link_curve_map'] = None
                

            if flight['plot']['text_map_start']:
                flight['plot']['text_map_start'].hide()


            if flight['plot']['text_map_end']:
                flight['plot']['text_map_end'].hide()
        
    plot_widget.autoRange()   
        


  
def update_wind_barbs_2D(flight_dic, table_widget_flight, plot_widget, radiobutton_wind, slider_density, slider_size):
    """
    This function creates or removes windbarbs on the graph according to the checkbox wind barbs state
    """
    
    settings.beginGroup("colors")
    color = QColor(settings.value("windbarbs", "#000000")) #default color is black  
    settings.endGroup()
    density = slider_density.value()
    size_coeff = slider_size.value()
    increment = int((density - 1) * (20 - 200) // (100 - 1) + 200) #mapping the res of the slider into a increment that goes to a barb every 20 points to every 200 points  
    flight_selected = get_flight_variable_2D(table_widget_flight)
    
    selected_names = {f for f, _ in flight_selected}

    for flight in flight_dic:
        flight_name = flight['file_name'].split(".")[0]
        flight_alias = flight['metadata']['alias']
    
        if (flight_name not in selected_names) and (flight_alias not in selected_names):
            if flight['plot']['windbarbs_2D']:
                for arrow in flight['plot']['windbarbs_2D']:
                    plot_widget.removeItem(arrow)
                flight['plot']['windbarbs_2D'] = []
    
    if len(flight_selected) == 0:
        return
    
    for row, flight in enumerate(flight_dic):
        for flight_to_plot, variable in flight_selected:
            if flight['file_name'].split(".")[0] == flight_to_plot or flight['metadata']['alias'] == flight_to_plot:
                vel_max = np.nanmax(flight['data']['wind_vel'])
                vel_min = np.nanmin(flight['data']['wind_vel'])    
                #slider.setMaximum(int(round(len(flight['data']['GNSS_lon'])/3)))
                if len(flight['plot']['windbarbs_2D']) != round((len(flight['data']['GNSS_lon']) / density)): #If the numbers of windbarbs has changed
                    if radiobutton_wind.isChecked():
                        #First we delete the previous windbarbs
                        if len(flight['plot']['windbarbs_2D']) > 0:
                            for arrow in flight['plot']['windbarbs_2D']:
                                plot_widget.removeItem(arrow)
                            flight['plot']['windbarbs_2D']= [] 
    
    
                        #Then we build again the windbarbs
                        for i in range(0, len(flight['data']['GNSS_lon']), increment):
                        
                            lon = flight['data']['GNSS_lon'][i]
                            lat = flight['data']['GNSS_lat'][i]
                            wind_dir = (flight['data']['wind_origin'][i]  + 90 ) % 360  #+90 because the item arrow is offseted by 90
                            wind_speed = flight['data']['wind_vel'][i]
                            
                    
                            size = 5 + ( size_coeff * ((wind_speed - vel_min) / (vel_max - vel_min)))
                            
                            
                    
                            arrow = pg.ArrowItem(
                                pos=(lon , lat ),
                                angle=wind_dir,
                                headLen=0,
                                headWidth = 0,
                                tipAngle=25,
                                tailLen = size ,
                                tailWidth = 1,
                                brush='black',
                                pen=pg.mkPen(color)
                            )
                        
                            plot_widget.addItem(arrow)
                            flight['plot']['windbarbs_2D'].append(arrow)
    
                    else: #Else we remove every windbarbs
                        if len(flight['plot']['windbarbs_2D']) > 0:
                            for arrow in flight['plot']['windbarbs_2D']:
                                plot_widget.removeItem(arrow)
                            flight['plot']['windbarbs_2D']= [] 
    
                        else:
                            return
                    
                else: 
                    if radiobutton_wind.isChecked(): #If the numbers of windbarbs hasn't changed , we need to rebuild because it may has been previously deleted
                        if len(flight['plot']['windbarbs_2D']) > 0:
                            for arrow in flight['plot']['windbarbs_2D']:
                                # plot_widget.addItem(arrow)
                                pass
                        elif not flight['plot']['windbarbs_2D']:
                            for i in range(0, len(flight['data']['GNSS_lon']), increment):
                            
                                lon = flight['data']['GNSS_lon'][i]
                                lat = flight['data']['GNSS_lat'][i]
                                wind_dir = (flight['data']['wind_origin'][i]  + 90 ) % 360  #+90 because the item arrow is offseted by 90
                                wind_speed = flight['data']['wind_vel'][i]
                                
                        
                                size = 10 + ( 50* ((wind_speed - vel_min) / (vel_max - vel_min)))
                                
                                
                        
                                arrow = pg.ArrowItem(
                                    pos=(lon , lat ),
                                    angle=wind_dir,
                                    headLen=0,
                                    headWidth = 0,
                                    tipAngle=25,
                                    tailLen = size ,
                                    tailWidth = 1,
                                    brush='black',
                                    pen=pg.mkPen(color)
                                )
                            
                                plot_widget.addItem(arrow)
                                flight['plot']['windbarbs_2D'].append(arrow)
                    else: #Or if it's the same number but the windbarbs checkbox is unchecked
                        if len(flight['plot']['windbarbs_2D']) > 0:
                            for arrow in flight['plot']['windbarbs_2D']:
                                plot_widget.removeItem(arrow)
                                
                            flight['plot']['windbarbs_2D']= []

                        
def update_sample_serie_plot(flight_dic, comboBox_flight, combobox_var, plot_widget):
    """
    Same function than 1D plot, but it takes only one var as input. 
    It is also not plotted with time as it is too complicated to handle with the linear region (ROI)
    It also load the existing ROI
    Used both in Polar and Emagram tab
    """
    variable = combobox_var.currentText()
    if not variable:
        plot_widget.clear()
        return

    selected = comboBox_flight.currentText()
    plot_widget.clear()

    for flight in flight_dic:
        name  = flight['file_name'].split(".")[0]
        alias = flight['metadata']['alias']

        if name != selected and alias != selected:
            continue

        data = flight.get('data')
        if not data or variable not in data:
            return

        y = convert_array_to_unit(data[variable], variable)
        if y is None or len(y) == 0:
            return

        x = np.arange(len(y))

        plot_widget.setLimits(
            xMin=np.min(x), xMax=np.max(x),
            yMin=np.min(y), yMax=np.max(y)
        )

        plot_widget.setLabel("left", f"{variable} {get_unit(variable)}")
        plot_widget.setTitle(f"{variable}")
        plot_widget.addLegend()

        pen = pg.mkPen(flight['plot']['plot_color'], width=1)
        plot_widget.plot(x, y, pen=pen, name=variable)
        
        if flight['plot']['roi_emagram']:
            plot_widget.addItem(flight['plot']['roi_emagram'])


        break  

def create_roi(flight_dic, plot_widget_time, plot_widget_vxvz,table_polar_widget, combobox_flight, legend_vxvz, ias_comp):
    """
    Creating a new ROI -> meaning a new polar point
    Used only in polar tab
    """
    for row, flight in enumerate(flight_dic):
        if flight['file_name'].split(".")[0] == combobox_flight.currentText() or flight['metadata']['alias'] == combobox_flight.currentText():
            roi = pg.LinearRegionItem(values=(calculate_roi(flight, "min"), calculate_roi(flight, "max")), bounds=(calculate_roi(flight, "bound_min"), calculate_roi(flight, "bound_max" )))
            roi.setMovable(True)
            roi.setBrush(QColor(100, 100, 100, 25)) 
            roi.setZValue(10)  # Stay on top
            plot_widget_time.addItem(roi)
            flight['plot']['roi_polar'].append([roi, None, None, None, None, None]) #And we add the ROI to the dic,
            update_polar_values(flight_dic, plot_widget_vxvz, table_polar_widget, combobox_flight, legend_vxvz, ias_comp)
            roi.sigRegionChanged.connect(lambda : update_polar_values(flight_dic, plot_widget_vxvz, table_polar_widget, combobox_flight, legend_vxvz, ias_comp))
            
            
            
def calculate_roi(flight, edge):
    """ 
    edge : 'min' ou 'max' 
    Calculate a position that suits well to be displayed for new ROIs 
    """
    #t = np.array([t.timestamp() for t in flight['data']['GNSS_time']])
    t= np.arange(len(flight['data']['GNSS_time']))
    t0 = t[0]
    t_end = t[-1]
    total_duration = t_end - t0

    existing_rois = []

    if flight['plot']['roi_polar']:
        for roi_data in flight['plot']['roi_polar']:
            existing_rois.append((roi_data[0].getRegion()[0], roi_data[0].getRegion()[1]))

    existing_rois.sort(key=lambda x: x[0])

    if not existing_rois:
        # middle flight
        center = t0 + total_duration / 2
        half_width = total_duration * 0.06

        start = center - half_width
        end = center + half_width

    else:
        last_xmin, last_xmax = existing_rois[-1]
        remaining = max(t_end - last_xmax, 0)

        if remaining > 0:
            interval = max(
                remaining * 0.1,
                total_duration * 0.08
            )

            start = last_xmax + total_duration * 0.08
            end = min(start + interval, t_end)

        else:
            start = t_end - total_duration * 0.08
            end = t_end
    if edge == 'min':
        return int(start)
    elif edge == 'max':
        return int(end)
    elif edge == 'bound_min':
        return int(t0)
    else:
        return int(t_end)
    
    
def load_polar_roi(flight_dic, plot_widget_time, plot_widget_vxvz, table_polar_widget, combobox_flight , legend_vxvz, ias_comp):
    plot_widget_time.clear()
    for flight in flight_dic:
        if flight['is_data_processed']:
            if len(flight['plot']['roi_polar']) > 0:
                for roi_data in flight['plot']['roi_polar']:
                    roi = roi_data[0]
                    plot_widget_time.addItem(roi)
                    roi.sigRegionChanged.connect(lambda : update_polar_values(flight_dic, plot_widget_vxvz, table_polar_widget, combobox_flight, legend_vxvz, ias_comp))
        update_polar_values(flight_dic, plot_widget_vxvz, table_polar_widget, combobox_flight, legend_vxvz, ias_comp)

def load_emagram_roi(flight_dic, plot_widget_time, widget_emagram, combobox_flight):
    """
    this function is called when a new emagram is displayed. it retrieves the previous roi if it already exists
    or create a new one , and save it to the dic
    """
    flight_selected = None 
    for flight in flight_dic:
        if flight['file_name'].split(".")[0] == combobox_flight.currentText() or flight['metadata']['alias'] == combobox_flight.currentText():
            flight_selected = flight 
            break 
    if not combobox_flight.currentText():
        return


    if flight_selected['plot']['roi_emagram']: #If there is already a ROI saved, we delete it to create a new one. Correct a bug
        plot_widget_time.removeItem(flight_selected['plot']['roi_emagram'])
        flight_selected['plot']['roi_emagram'] = None
    # else: #if no ROI exists yet, we create a new one by default

    x_min_default = int(len(flight_selected['data']['GNSS_time'])/2 - (0.2 *len(flight_selected['data']['GNSS_time'])))
    x_max_default = int(len(flight_selected['data']['GNSS_time'])/2 + (0.2 *len(flight_selected['data']['GNSS_time'])))
    x_bound_max_default = len(flight_selected['data']['GNSS_time'])
    x_bound_min_default = 1                          
    roi = pg.LinearRegionItem(values=(x_min_default,x_max_default ), bounds=(x_bound_min_default,x_bound_max_default ))
    roi.setMovable(True)
    roi.setBrush(QColor(100, 100, 100, 25)) 
    roi.setZValue(10)  # Stay on top
    plot_widget_time.addItem(roi)
    roi.sigRegionChanged.connect(lambda roi_item, f=flight_selected: widget_emagram.update(f))
    #roi.sigRegionChanged.connect(lambda roi_item: widget_emagram.update(flight_selected))

    flight_selected['plot']['roi_emagram'] = roi
    
    widget_emagram.update(flight_selected)
         

def remove_roi(flight_dic, plot_widget_time, plot_widget_vxvz,table_polar_widget, combobox_flight, legend_vxvz, ias_comp):
    row = table_polar_widget.currentRow() #the row selected 
    for flight in flight_dic:
        if flight['file_name'].split(".")[0] == combobox_flight.currentText() or flight['metadata']['alias'] == combobox_flight.currentText():
            if row >= len(flight['plot']['roi_polar']):
                return
            else:
                for i, roi_data in enumerate(flight['plot']['roi_polar']):
                    if i == row:
                        plot_widget_time.removeItem(roi_data[0])
                        flight['plot']['roi_polar'].pop(i)
                plot_widget_vxvz.removeItem(flight['plot']['crosshair_v_polar'])
                plot_widget_vxvz.removeItem(flight['plot']['crosshair_h_polar'])
                
    update_polar_values(flight_dic, plot_widget_vxvz, table_polar_widget, combobox_flight, legend_vxvz, ias_comp)


def update_polar_values(flight_dic , plot_widget, table_widget, combobox_flight, legend_vxvz, ias_comp_coeff):
 
    for row, flight in enumerate(flight_dic):
        # if flight['file_name'].split(".")[0] == combobox_flight.currentText():
        if flight['is_data_processed']:
            if len(flight['plot']['roi_polar']) > 0:
                for roi_data in flight['plot']['roi_polar']:
                    x_min, x_max = roi_data[0].getRegion()
                    if x_min != x_max:
                        with np.errstate(divide='ignore', invalid='ignore'):
                            # we set the ias compensation 
                     
                            ias_comp = np.multiply(flight['data']['IAS'] , (1+ (ias_comp_coeff/100) ))
                            #Then the array are converted into the desired unit
                            ias_comp = convert_array_to_unit(ias_comp, 'IAS')
                            vario_ias = flight['data']['VarioIAS']
                            vx = np.sqrt(np.subtract(np.square(ias_comp), np.square(vario_ias)))
                            
                            
                            

                            vx_avg = round(np.nanmean(vx[int(x_min):int(x_max)]),2)
                            ias_avg = round(np.nanmean(ias_comp[int(x_min):int(x_max)]),2)
                            vario_avg = round(np.nanmean(vario_ias[int(x_min):int(x_max)]),2)
                            glide_ratio_avg = round(np.divide(vx_avg, vario_avg ), 2)
                            
                            roi_data[1] = ias_avg
                            roi_data[2] = vx_avg
                            roi_data[3] = vario_avg
                            roi_data[4] = glide_ratio_avg
                            
                            if flight['plot']['crosshair_v_polar']:
                                flight['plot']['crosshair_v_polar'].hide()
                                flight['plot']['crosshair_h_polar'].hide()
            
    create_polar_table(flight_dic, table_widget, combobox_flight)
    update_vxvz_graph(flight_dic, plot_widget, legend_vxvz)
        

    
def display_rois(flight_dic, plot_widget, combobox_flight, tab):
    """
    This function keeps the existings rois displayed even though we change the variable or the flight
    Used only in Polar Tab
    """
    for row, flight in enumerate(flight_dic):
        if flight['file_name'].split(".")[0] == combobox_flight.currentText() or flight['metadata']['alias'] == combobox_flight.currentText():
            if flight['plot'][tab]:
                for roi in flight['plot'][tab]:
                    plot_widget.addItem(roi[0])  #roi[0] is the pyqtgraph item 
                    
                    
          
            
def reset_highlights(flight_dic, plot_widget):
    """
    Reset the color of a ROI if it has been changed by a previous selection
    And it also removes the crosshair from the previous selection 
    """
    for row, flight in enumerate(flight_dic):
        if flight['is_data_processed']:
            for roi in flight['plot']['roi_polar']:
                roi[0].setBrush(QColor(100, 100, 100, 25))
            if flight['plot']['crosshair_v_polar']:
                plot_widget.removeItem(flight['plot']['crosshair_v_polar'])
                plot_widget.removeItem(flight['plot']['crosshair_h_polar'])  

def update_vxvz_graph(flight_dic, plot_widget, legend_vxvz):
    
    #plot_widget.clear()
    legend_vxvz.clear()  
    plot_widget.setAspectLocked(True)
    plot_widget.enableAutoRange(True)
    plot_widget.setLabel("top", f"Vx {get_unit('IAS')}")
    plot_widget.setLabel("left","Vz m/s")
    
    for flight in flight_dic:
        if flight['is_data_processed'] and len(flight['plot']['roi_polar']) > 0:
            if not flight['plot']['scatter_vxvz']: #if no scatter exists yet
                scatter_polar_vx = []
                scatter_polar_vz = []
                for roi_data in flight['plot']['roi_polar']:
                    scatter_polar_vx.append(roi_data[2])
                    scatter_polar_vz.append(roi_data[3])
                pen = pg.mkPen(flight['plot']['plot_color'], width=4)
                scatter = pg.ScatterPlotItem(
                    x=scatter_polar_vx,
                    y=scatter_polar_vz,
                    size=6,
                    pen=pen,
                    brush=None
                )
                
                plot_widget.addItem(scatter)
                flight['plot']['scatter_vxvz'] = scatter
            
            else:
                scatter_polar_vx = []
                scatter_polar_vz = []
                for roi_data in flight['plot']['roi_polar']:
                    scatter_polar_vx.append(roi_data[2])
                    scatter_polar_vz.append(roi_data[3])
                scatter = flight['plot']['scatter_vxvz']
                scatter.setData(scatter_polar_vx, scatter_polar_vz)
        
            
            label = flight['file_name'].split(".")[0]
            legend_vxvz.addItem(scatter, label)
            
        elif len(flight['plot']['roi_polar']) == 0:
            if flight['plot']['scatter_vxvz']: 
                plot_widget.removeItem(flight['plot']['scatter_vxvz'])
                flight['plot']['scatter_vxvz'] = None  #delete
                
    plot_widget.autoRange()


def highlights_polar_tab(index, flight, table_polar_points, plot_widget_vxvz):
    """
    This function highlights the ROI, moves or create the crosshair, and highlights the
    correspond table row
    """
    for i, roi_data in enumerate(flight['plot']['roi_polar']):

        if i == index:
            roi_data[0].setBrush(QColor(100, 100, 100, 50)) #Highlight ROI 
            roi_data[0].setZValue(20) 
            
            if flight['plot']['crosshair_v_polar']: #if the crosshair already exists, no need to create them again
                flight['plot']['crosshair_v_polar'].show()
                flight['plot']['crosshair_h_polar'].show()
                flight['plot']['crosshair_v_polar'].setValue(roi_data[2])
                flight['plot']['crosshair_h_polar'].setValue(roi_data[3])
            
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
            
                plot_widget_vxvz.addItem(crosshair_v)
                plot_widget_vxvz.addItem(crosshair_h)
                flight['plot']['crosshair_v_polar'] = crosshair_v
                flight['plot']['crosshair_h_polar'] = crosshair_h
                flight['plot']['crosshair_v_polar'].setValue(roi_data[2])
                flight['plot']['crosshair_h_polar'].setValue(roi_data[3])
            
            table_polar_points.selectRow(i) #highlights the corresponding row
            
        else :
            roi_data[0].setBrush(QColor(100, 100, 100, 25)) 
            roi_data[0].setZValue(10) 

def remove_crosshair(flight_dic, plot_widget, crosshair):
    for flight in flight_dic:
        if flight['plot'][f"crosshair_v_{crosshair}"]:
            plot_widget.removeItem(flight['plot'][f'crosshair_v_{crosshair}'])
            plot_widget.removeItem(flight['plot'][f'crosshair_h_{crosshair}'])
            flight['plot'][f'crosshair_v_{crosshair}'] = None
            flight['plot'][f'crosshair_h_{crosshair}'] = None
                

