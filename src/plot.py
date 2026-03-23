from pyqtgraph import ErrorBarItem 
import pyqtgraph as pg
from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtWidgets import QListWidgetItem, QApplication, QLineEdit, QWidget, QVBoxLayout,QTableWidgetItem ,QButtonGroup , QPushButton, QHBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from PyQt6.QtGui import QColor, QPen, QBrush
import numpy as np
from units import convert_array_to_unit , get_unit
import math
pg.setConfigOptions(useOpenGL=True)
pg.setConfigOptions(antialias=True)

colors = [
   QColor(253, 50, 22),     
   QColor(128, 204, 0)
   ]



def update_1D_plot(flight_dic, comboBox_flight , list_widget, plot_widget):
    """
    This function was initially written in order to handle multiple plot on the same graph. 
    For now it only plot one as it is to complex to add several scales with pyqtgraph
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
            pen1 = pg.mkPen(colors[0], width=2)
            date_axis = pg.graphicsItems.DateAxisItem.DateAxisItem(orientation='bottom')
            plot_widget.setAxisItems({'bottom': date_axis})
            plot_widget.plot(x, y, pen=pen1,  name=variables[0])
            
            if len(variables) > 1:
                y2 = convert_array_to_unit(flight['data'][variables[1]], variables[1])
                plot_widget.setLabel("left", f"{variables[0]} {get_unit(variables[0])} / {variables[1]} {get_unit(variables[1])}")
                plot_widget.setTitle(f"{variables[0]} and {variables[1]} vs time")
                plot_widget.addLegend()
                pen2 = pg.mkPen(colors[1], width=2)
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
    plot1.clear()
    plot2.clear()
    


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
                color = colors[row % len(colors)]
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
                    color = colors[row % len(colors)]
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
                size=3,
                pen=pen
            )
            plot_widget.setTitle(f"{flight['file_name'].split('.')[0]} flight trajectory")
            
            
            #scatter start
            start = pg.ScatterPlotItem(
            x=[x[0]], y=[y[0]],
            brush=pg.mkBrush('black'),
            size=5,
            symbol='o'
            )
        
            # scatter finish 
            end = pg.ScatterPlotItem(
                x=[x[-1]], y=[y[-1]],
                brush=pg.mkBrush('black'),
                size=5,
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

                        
