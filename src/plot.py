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

    variables = get_checked_variables(list_widget)
    if len(variables) == 0:
        plot_widget.clear()
        return
    
    
    plot_widget.clear()
    for row, flight in enumerate(flight_dic):
        if flight['file_name'].split(".")[0] == comboBox_flight.currentText():
            x = np.array([t.timestamp() for t in flight['data']['GNSS_time']])
            plot_widget.setLabel("left", variables[0])
            plot_widget.addLegend()
            pen1 = pg.mkPen(colors[0], width=2)
            plot_widget.plot(x, flight['data'][variables[0]] , pen=pen1,  name=variables[0])
            
            if len(variables) > 1:
                
            


                plot_widget.setTitle("")
                plot_widget.showAxis('right')
                plot_widget.getAxis('right').setLabel("right", variables[1])
                p2 = pg.ViewBox()
                plot_widget.scene().addItem(p2)
                plot_widget.getAxis('right').linkToView(p2)
                p2.setXLink(plot_widget)
                def updateViews():
                    p2.setGeometry(plot_widget.getViewBox().sceneBoundingRect())
                    p2.linkedViewChanged(plot_widget.getViewBox(), p2.XAxis)
                
                updateViews()
                plot_widget.getViewBox().sigResized.connect(updateViews)
                pen2 = pg.mkPen(colors[1], width=2)
                curve2 = pg.PlotCurveItem(x, flight['data'][variables[1]], pen=pen2, name=variables[1] )
                p2.addItem(curve2)
            break
            
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
