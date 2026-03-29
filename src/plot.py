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



def update_1D_plot(flight_dic, comboBox_flight , list_widget, plot_widget):
    """
    This function was initially written in order to handle multiple plot on the same graph. 
    For now it only plot one as it is to complex to add several scales with pyqtgraph.
    """

    variables = get_checked_variables(list_widget)
    if len(variables) == 0:
        plot_widget.clear()
        
        return
    
    
    plot_widget.clear()
    for row, flight in enumerate(flight_dic):
        if flight['file_name'].split(".")[0] == comboBox_flight.currentText():
            
            x = np.array([t.timestamp() for t in flight['data']['GNSS_time']])
           
            y = convert_array_to_unit(flight['data'][variables[0]], variables[0])
            plot_widget.setLabel("left", f"{variables[0]} {get_unit(variables[0])}")
            plot_widget.setTitle(f"{variables[0]} vs time")
            plot_widget.addLegend()
            plot_widget.enableAutoRange(True)
            pen1 = pg.mkPen(flight['plot']['plot_color'], width=1)
            date_axis = pg.graphicsItems.DateAxisItem.DateAxisItem(orientation='bottom')
            plot_widget.setAxisItems({'bottom': date_axis})
            plot_widget.plot(x, y, pen=pen1,  name=variables[0])
            
            if len(variables) > 1:
                y2 = convert_array_to_unit(flight['data'][variables[1]], variables[1])
                plot_widget.setLabel("left", f"{variables[0]} {get_unit(variables[0])} / {variables[1]} {get_unit(variables[1])}")
                plot_widget.setTitle(f"{variables[0]} and {variables[1]} vs time")
                plot_widget.addLegend()
                pen2 = pg.mkPen(flight['plot']['plot_color'].darker(), width=1)
                plot_widget.plot(x, y2, pen=pen2,  name=variables[1])
                
            plot_widget.autoRange()
        
            
def get_checked_variables(list_widget):

    checked_vars = []

    for i in range(list_widget.count()):

        item = list_widget.item(i)

        if item.checkState() == Qt.CheckState.Checked:
            checked_vars.append(item.text())

    return checked_vars

def save_checked_variables_1D(flight_dic, comboBox_flight, list_widget1, list_widget2):
    """
    Save the variables that has been checked to display in graph 1D
    each time we tick a new variable
    """

    current_flight_name = comboBox_flight.currentText()

    for flight in flight_dic:
        if flight['file_name'].split(".")[0] == current_flight_name:

            flight['plot']['variables_1D'] = [[],[]]

            for i in range(list_widget1.count()):
                item1 = list_widget1.item(i)
                if item1.checkState() == Qt.CheckState.Checked:
                    flight['plot']['variables_1D'][0].append(item1.text())
            for i in range(list_widget2.count()):
                item2 = list_widget2.item(i)
                if item2.checkState() == Qt.CheckState.Checked:
                    flight['plot']['variables_1D'][1].append(item2.text())
                    

def restore_checked_variables_1D(flight_dic, comboBox_flight, list_widget1, list_widget2):
    """
    Restore the variables that has been previously checked to display in graph 1D
    """

    current_flight_name = comboBox_flight.currentText()

    for flight in flight_dic:
        if flight['file_name'].split(".")[0] == current_flight_name:

            selected = flight['plot']['variables_1D']

            for i in range(list_widget1.count()):
                item1 = list_widget1.item(i)
            
                if item1.text() in selected[0]:
                    item1.setCheckState(Qt.CheckState.Checked)
                else:
                    item1.setCheckState(Qt.CheckState.Unchecked)
                    
            for i in range(list_widget2.count()):
                item2 = list_widget2.item(i)
            
                if item2.text() in selected[1]:
                    item2.setCheckState(Qt.CheckState.Checked)
                else:
                    item2.setCheckState(Qt.CheckState.Unchecked)


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


def update_2D_plot(flight_dic, checkbox_color, variable_color , list_widget_flight, plot_widget, color_bar):
    """
    Big function that creates the 2D graph, and add mapping colors to it according to a selected variable
    """
   
    plot_widget.enableAutoRange(True)
    plot_widget.setAspectLocked(True)
    
    flights = get_checked_variables(list_widget_flight)
    if len(flights) == 0:
        plot_widget.clear()

        
        return
    
    
    plot_widget.clear()
    
    
    
    
    for row, flight in enumerate(flight_dic):
        if flight['file_name'].split(".")[0] in flights:
            #setting the color mapping 
            if checkbox_color is None:
                color = flight['plot']['plot_color']
                pen = pg.mkPen(color, width=2)
                brush = None
                color_bar.setOpacity(0)
            else:
                if checkbox_color.isChecked():
                    cmap = pg.colormap.get('turbo')
                    z = flight['data'][variable_color]
                
                    z_min, z_max = np.nanmin(z), np.nanmax(z)
                    
                    color_bar.setLevels((z_min, z_max))
                    if z_max - z_min == 0:
                        norm = np.zeros_like(z)
                    else:
                        norm = (z - z_min) / (z_max - z_min)
                    
                    brush = cmap.map(norm, mode='qcolor')
                    pen = None
                    color_bar.setOpacity(1)
                elif not checkbox_color.isChecked():
                    color = flight['plot']['plot_color']
                    pen = pg.mkPen(color, width=2)
                    brush = None
                    color_bar.setOpacity(0)
 
            #main scatter
            
            x = flight['data']['GNSS_lon']
            y = flight['data']['GNSS_lat']
            
            
            scatter = pg.ScatterPlotItem(
                x=x,
                y=y,
                brush=brush,
                size=2,
                pen=pen
            )
            plot_widget.setTitle(f"{flight['file_name'].split('.')[0]} flight trajectory")
            
            
            #scatter start
            start = pg.ScatterPlotItem(
            x=[x[0]], y=[y[0]],
            brush=pg.mkBrush('black'),
            size=3,
            symbol='o'
            )
        
            # scatter finish 
            end = pg.ScatterPlotItem(
                x=[x[-1]], y=[y[-1]],
                brush=pg.mkBrush('black'),
                size=3,
                symbol='x'
            )
            
            
            text_start = pg.TextItem("Start", color='black')
            text_start.setPos(x[0], y[0])
            
            text_end = pg.TextItem("Finish", color='black')
            text_end.setPos(x[-1], y[-1])
            plot_widget.addItem(text_start)
            plot_widget.addItem(text_end)
            plot_widget.addItem(scatter)
            plot_widget.addItem(start)
            plot_widget.addItem(end)
            plot_widget.autoRange()

            


  
def update_wind_barbs_2D(flight_dic, list_widget_flight, plot_widget, checkbox_wind, slider, res):
    """
    This function creates or removes windbarbs on the graph according to the checkbox wind barbs state
    """
    increment = int((res - 1) * (20 - 200) // (100 - 1) + 200) #mapping the res of the slider into a increment that goes to a barb every 20 points to every 200 points  
    flights = get_checked_variables(list_widget_flight)
    for row, flight in enumerate(flight_dic):
        if flight['file_name'].split(".")[0] in flights:
            vel_max = np.nanmax(flight['data']['wind_vel'])
            vel_min = np.nanmin(flight['data']['wind_vel'])    
            #slider.setMaximum(int(round(len(flight['data']['GNSS_lon'])/3)))
            if len(flight['plot']['windbarbs_2D']) != round((len(flight['data']['GNSS_lon']) / res)): #If the numbers of windbarbs has changed
                if checkbox_wind.isChecked():
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
                            pen=pg.mkPen('black')
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
                if checkbox_wind.isChecked(): #If the numbers of windbarbs hasn't changed , we need to rebuild because it may has been previously deleted
                    if len(flight['plot']['windbarbs_2D']) > 0:
                        for arrow in flight['plot']['windbarbs_2D']:
                            plot_widget.addItem(arrow)
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
                                pen=pg.mkPen('black')
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
    if variable == '':
        plot_widget.clear()
        return
    
    plot_widget.clear()
    for row, flight in enumerate(flight_dic):
        if flight['file_name'].split(".")[0] == comboBox_flight.currentText():
            
            y = convert_array_to_unit(flight['data'][variable], variable)
            x = np.arange(len(y))

            plot_widget.setLimits(xMin=np.min(x), xMax=np.max(x), yMin=np.min(y), yMax=np.max(y))
            plot_widget.setLabel("left", f"{variable} {get_unit(variable)}")
            plot_widget.setTitle(f"{variable}")
            plot_widget.addLegend()
            plot_widget.enableAutoRange(False)
            pen1 = pg.mkPen(flight['plot']['plot_color'], width=1)
            plot_widget.plot(x, y, pen=pen1,  name=variable)
            plot_widget.autoRange()

def create_roi(flight_dic, plot_widget_time, plot_widget_vxvz,table_polar_widget, combobox_flight, legend_vxvz):
    """
    Creating a new ROI -> meaning a new polar point
    """
    for row, flight in enumerate(flight_dic):
        if flight['file_name'].split(".")[0] == combobox_flight.currentText():
            roi = pg.LinearRegionItem(values=(calculate_roi(flight, "min"), calculate_roi(flight, "max")), bounds=(calculate_roi(flight, "bound_min"), calculate_roi(flight, "bound_max" )))
            roi.setMovable(True)
            roi.setBrush(QColor(100, 100, 100, 25)) 
            roi.setZValue(10)  # Stay on top
            plot_widget_time.addItem(roi)
            flight['plot']['roi_polar'].append([roi, None, None, None, None, None]) #And we add the ROI to the dic,
            update_polar_values(flight_dic, plot_widget_vxvz, table_polar_widget, combobox_flight, legend_vxvz)
            roi.sigRegionChanged.connect(lambda : update_polar_values(flight_dic, plot_widget_vxvz, table_polar_widget, combobox_flight, legend_vxvz))

            
            
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
            # Plus de place
            start = last_xmax + 50
            end = t_end
    if edge == 'min':
        return int(start)
    elif edge == 'max':
        return int(end)
    elif edge == 'bound_min':
        return int(t0)
    else:
        return int(t_end)
    
    
def load_polar_roi(flight_dic, plot_widget_time, plot_widget_vxvz, table_polar_widget, combobox_flight , legend_vxvz):
    plot_widget_time.clear()
    for flight in flight_dic:
        if flight['is_data_processed']:
            if len(flight['plot']['roi_polar']) > 0:
                for roi_data in flight['plot']['roi_polar']:
                    roi = roi_data[0]
                    plot_widget_time.addItem(roi)
                    roi.sigRegionChanged.connect(lambda : update_polar_values(flight_dic, plot_widget_vxvz, table_polar_widget, combobox_flight, legend_vxvz))
        update_polar_values(flight_dic, plot_widget_vxvz, table_polar_widget, combobox_flight, legend_vxvz)

def load_emagram_roi(flight_dic, plot_widget_time, plot_widget_emagram, combobox_flight):
    plot_widget_time.clear()
    for flight in flight_dic:
        if flight['is_data_processed']:
            if len(flight['plot']['roi_emagram']) > 0:
                for roi in flight['plot']['roi_emagram']:
                    plot_widget_time.addItem(roi)
                    roi.sigRegionChanged.connect(lambda : update_emagram_values(flight_dic, plot_widget_emagram))
        update_emagram_values(flight_dic, plot_widget_emagram)

def remove_roi(flight_dic, plot_widget_time, plot_widget_vxvz,table_polar_widget, combobox_flight, legend_vxvz):
    row = table_polar_widget.currentRow() #the row selected 
    for flight in flight_dic:
        if flight['file_name'].split(".")[0] == combobox_flight.currentText():
            if row >= len(flight['plot']['roi_polar']):
                return
            else:
                for i, roi_data in enumerate(flight['plot']['roi_polar']):
                    if i == row:
                        plot_widget_time.removeItem(roi_data[0])
                        flight['plot']['roi_polar'].pop(i)
                plot_widget_vxvz.removeItem(flight['plot']['crosshair_v'])
                plot_widget_vxvz.removeItem(flight['plot']['crosshair_h'])
                
    update_polar_values(flight_dic, plot_widget_vxvz, table_polar_widget, combobox_flight, legend_vxvz)


def update_polar_values(flight_dic , plot_widget, table_widget, combobox_flight, legend_vxvz):
    for row, flight in enumerate(flight_dic):
        # if flight['file_name'].split(".")[0] == combobox_flight.currentText():
        if flight['is_data_processed']:
            if len(flight['plot']['roi_polar']) > 0:
                for roi_data in flight['plot']['roi_polar']:
                    x_min, x_max = roi_data[0].getRegion()
                    if x_min != x_max:
                        with np.errstate(divide='ignore', invalid='ignore'):
                            #The array are converted into the desired unit
                            ias = convert_array_to_unit(flight['data']['IAS'], 'IAS')
                            vario_ias = convert_array_to_unit(flight['data']['VarioIAS'], 'VarioIAS')
                            vx = np.sqrt(np.subtract(np.square(ias), np.square(vario_ias)))
                            glide_ratio = np.divide(vx, vario_ias)
                            
                            glide_ratio_avg = round(np.nanmean(glide_ratio[int(x_min):int(x_max)]),2)

                            vx_avg = round(np.nanmean(vx[int(x_min):int(x_max)]),2)
                            ias_avg = round(np.nanmean(ias[int(x_min):int(x_max)]),2)
                            vario_avg = round(np.nanmean(vario_ias[int(x_min):int(x_max)]),2)
                            
                            roi_data[1] = ias_avg
                            roi_data[2] = vx_avg
                            roi_data[3] = vario_avg
                            roi_data[4] = glide_ratio_avg
                            
    create_polar_table(flight_dic, table_widget, combobox_flight)
    update_vxvz_graph(flight_dic, plot_widget, legend_vxvz)
        
def update_emagram_values(flight_dic, plot_widget_emagram):
    for row, flight in enumerate(flight_dic):
        # if flight['file_name'].split(".")[0] == combobox_flight.currentText():
        if flight['is_data_processed']:
            if len(flight['plot']['roi_emagram']) > 0:
                for roi in flight['plot']['roi_emagram']:
                    x_min, x_max = roi.getRegion()
                    if x_min != x_max:
                        with np.errstate(divide='ignore', invalid='ignore'):
                            print(x_min)
                            print(x_max)
                            
    #update_emagram_graph(flight_dic, plot_widget_emagram)
    
    
def display_rois(flight_dic, plot_widget, combobox_flight, tab):
    """
    This function keeps the existings rois displayed even though we change the variable or the flight
    """
    for row, flight in enumerate(flight_dic):
        if flight['file_name'].split(".")[0] == combobox_flight.currentText():
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
            if flight['plot']['crosshair_v']:
                plot_widget.removeItem(flight['plot']['crosshair_v'])
                plot_widget.removeItem(flight['plot']['crosshair_h'])  

def update_vxvz_graph(flight_dic, plot_widget, legend_vxvz):
    
    #plot_widget.clear()
    legend_vxvz.clear()  
    plot_widget.setAspectLocked(True)
    plot_widget.enableAutoRange(True)
    plot_widget.setLabel("top", f"Vx {get_unit('IAS')}")
    plot_widget.setLabel("left", f"Vz {get_unit('IAS')}")
    
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

            
                



        
        
        