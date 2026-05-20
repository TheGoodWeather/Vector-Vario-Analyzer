from PyQt6.QtCore import QSettings
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

default_unit = {
    "heading": "degree",
    "speed": "km/h",
    "altitude": "meters",
    "temperature": "°C",
    "angle": "degree",
    "pressure": "hPa",
    "coordinates": "Decimal degrees"
}

var_to_unit_group_dic = {
    "heading" : ["compass_head", "GNSS_head" , "wind_origin"],
    "speed" : ["GNSS_speed", "vario" , "wind_vel", "IAS" , "VarioIAS" , "TAS" , "netto" ,"GNSS_velD"],
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
    "pressure": ["Pa", "hPa", "atm", "mbar"],
    "coordinates": ["Decimal degrees", "Degrees decimal minutes", "Degrees minutes seconds"]}

def get_unit(variable):
    
    settings = QSettings("Vector Vario", "VVA")
    settings.beginGroup("units")
    unit = None
    for group, variables in var_to_unit_group_dic.items():
        if variable in variables:
            default = default_unit[group]
            unit = settings.value(group, defaultValue=default)
        
    settings.endGroup()
    return unit


def convert_array_to_unit(array, variable):
    unit = get_unit(variable)

    if variable in ["GNSS_lat", "GNSS_lon"]: #no need to convert for GNSS coordinates
        array_converted = array 
    elif variable in ["T_sensor", "air_T", "AirTd"]:

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
    elif unit not in units_coeff_dic:
        array_converted = array
    else:
        array_converted = np.multiply(array, units_coeff_dic[unit])
        
        
    return array_converted


def convert_gps_coords_DDM_to_DD(lat_DDM, lon_DDM):
    lat_degrees = int(lat_DDM)
    lat_minutes_dec = (lat_DDM - lat_degrees)*100
    lat_secondes = (lat_minutes_dec - int(lat_minutes_dec)) *60
                                
    lat_DD = lat_degrees + int(lat_minutes_dec)/60 + (lat_secondes/3600)
    
    lon_degrees = int(lon_DDM)
    lon_minutes_dec = (lon_DDM - lon_degrees)*100
    lon_secondes = (lon_minutes_dec - int(lon_minutes_dec)) *60
                                
    lon_DD = lon_degrees + int(lon_minutes_dec)/60 + (lon_secondes/3600)

    
    return lat_DD, lon_DD