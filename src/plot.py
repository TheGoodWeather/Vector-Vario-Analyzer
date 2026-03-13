from pyqtgraph import ErrorBarItem 
import pyqtgraph as pg
from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtWidgets import QListWidgetItem, QApplication, QLineEdit, QWidget, QVBoxLayout,QTableWidgetItem ,QButtonGroup , QPushButton, QHBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPen, QBrush
import numpy as np

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
  
            plot_widget.setLabel("left", variables[0])
            plot_widget.setTitle(f"{variables[0]} vs time")
            plot_widget.addLegend()
            plot_widget.enableAutoRange(True)
            pen1 = pg.mkPen(colors[0], width=2)
            date_axis = pg.graphicsItems.DateAxisItem.DateAxisItem(orientation='bottom')
            plot_widget.setAxisItems({'bottom': date_axis})
            plot_widget.plot(x, flight['data'][variables[0]] , pen=pen1,  name=variables[0])
            
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
