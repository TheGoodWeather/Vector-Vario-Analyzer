from pyqtgraph import ErrorBarItem 
import pyqtgraph as pg
from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtWidgets import QListWidgetItem, QApplication, QLineEdit, QWidget, QVBoxLayout,QTableWidgetItem ,QButtonGroup , QPushButton, QHBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from PyQt6.QtGui import QColor, QPen, QBrush
import numpy as np
from units import convert_array_to_unit , get_unit

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

def clear_plots_1D(plot1, plot2):
    plot1.clear()
    plot2.clear()
    


def toggle_x_link(plot1, plot2, checkbox):
    if checkbox.isChecked():
        plot2.setXLink(plot1)
    else:
        plot2.setXLink(None)

    

def update_2D_plot(flight_dic, checkboxes_variable, checkbox_wind , list_widget_flight, plot_widget):
    """

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
            color = colors[row % len(colors)]
            pen = pg.mkPen(color, width=2)
            #main scatter
            scatter = pg.ScatterPlotItem(brush=pg.mkBrush('b'), pen=pen, size=1)
            x = flight['data']['GNSS_lon']
            y = flight['data']['GNSS_lat']
            scatter.setData(x, y)
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
            plot_widget.addItem(start)
            plot_widget.addItem(end)
            plot_widget.addItem(scatter)
            plot_widget.autoRange()

  
   
