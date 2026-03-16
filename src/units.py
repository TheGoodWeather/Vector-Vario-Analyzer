from pyqtgraph import ErrorBarItem 
import pyqtgraph as pg
from PyQt6 import QtWidgets, uic, QtCore, QtGui
from PyQt6.QtWidgets import QListWidgetItem, QApplication, QLineEdit, QWidget, QVBoxLayout,QTableWidgetItem ,QButtonGroup , QPushButton, QHBoxLayout, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from PyQt6.QtGui import QColor, QPen, QBrush
import numpy as np

units_coeff_dic = {
    "radian" : 0.0174533, #deg to rad
    "degree" : 1.0, #deg to deg
    "m/s" : 1.0, #m/s to m/s
    "knot" : 1.94384, #m/s to knot
    "km/h" : 3.6 , #m/s to km/h
    "mph" : 2.23694, #m/s to mph
    "meters" : 1.0, #meters to meters
    "feet" : 3.28084, #meters to feet
    "Pa" : 1.0, #Pa to Pa
    "hPa" : 0.01, #Pa to hPa
    "atm" : 9.86923e-6, #Pa to atm
    "mbar" : 0.01, #Pa to mbar
    }

var_to_unit_group_dic = {
    "heading" : ["compass_head", "GNSS_head" , "wind_origin"],
    "speed" : ["GNSS_speed", "vario" , "wind_vel", "IAS" , "VarioIAS" , "TAS" , "netto"],
    "coordinates" : ["GNSS_lat","GNSS_lon" ],
    "altitude" : ["GNSS_alt", "QNS_alt" , "LCL"], 
    "temperature" : ["T_sensor", "air_T", "AirTheta" , "AirTd"],
    "angle" : ["pitch" , "roll"],
    "pressure" : ["DP" , "P_stat" , "AirES" , "AirE"]}

unit_group = {
    "heading" : ["degree", "radian"],
    "speed" : ["m/s", "knot", "km/h", "mph"],
    "altitude": ["meters", "feet"],
    "temperature": ["°C", "°K", "°F"],
    "angle": ["degree", "radian"],
    "pressure": ["Pa", "hPa", "atm", "mbar"]}

def get_unit(variable):
    
    settings = QSettings("Vector Vario", "VVA")
    settings.beginGroup("units")
    for group, variables in var_to_unit_group_dic.items():
        if variable in variables:
            unit = settings.value(group)    

    
    settings.endGroup()
    return unit


def convert_array_to_unit(array, variable):
    unit = get_unit(variable)
    if variable in ["GNSS_lat", "GNSS_lon"]: #no need to convert for GNSS coordinates
        array_converted = array 
    elif variable in ["T_sensor", "air_T"]:
        if unit == "°K":
            array_converted = np.add(array,273.15) 
        elif unit == "°F":
            array_converted = np.add(np.multiply(array,9/5), 32)
        elif unit == "°C":
            array_converted = array
    elif variable == "AirTheta":
        if unit == "°K":
            array_converted = array 
        elif unit == "°F":
            array_converted = np.add(np.multiply(np.subtract(array,273.15), 9/5),32)  
        elif unit == "°C":
            array_converted = np.subtract(array , 273.15)
    else:
        array_converted = np.multiply(array, units_coeff_dic[unit])
        

    return array_converted