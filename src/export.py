from PyQt6 import QtWidgets
from logging_handler import QTextEditLogger, logger
from pathlib  import Path 
import csv
import simplekml
import math
import numpy as np

def export_file_csv(flight, parent):
    
    
    filename = create_file_name(flight , '_processed.csv' )

    filepath, _ = QtWidgets.QFileDialog.getSaveFileName(parent,"Save file as .csv", filename, "CSV Files (*.csv);;All Files (*)")
    
    if filepath:
        try:
            with open(filepath, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
    
                # Metadata
                writer.writerow(['vv_vva' , flight['metadata']['vv_vva']])
                writer.writerow(['vv_sn', flight['metadata']['vv_sn']])
                writer.writerow(['vv_hw', flight['metadata']['vv_hw']])
                writer.writerow(['vv_fw', flight['metadata']['vv_fw']])
                writer.writerow(['calib', flight['metadata']['calib']])
                writer.writerow(['pilot',  flight['metadata']['pilot']])
                writer.writerow(['date' ,  flight['metadata']['date']])
                writer.writerow(['comment',  flight['metadata']['comment']])
    
                writer.writerow([])  # Empty line
    
                # Header
                writer.writerow([
                    "GNSS_time", "GNSS_lat (dec degrees)", "GNSS_lon (dec degrees)" , "GNSS_alt (m)", "GNSS_speed (m/s)",  "GNSS_head (deg)", "QNS_alt (m)", "compass_head (deg)", 
                    "pitch (deg)", "roll (deg) ", "G_force" , "vario (m/s)", "DP (Pa)", "T_sensor (degC)", 
                    "P_stat (Pa)", "air_T (degC)" , "air_RH (%)", "wind_origin (deg)", "wind_vel (m/s)", "netto (m/s)", "IAS (m/s)","AirES (hPa)", 
                    "AirE (hPa)", "AirW","AirTd (degC)", "LCL (m)" , "AirTheta (degK)", "AirRho (kg/m^3)", "VarioIAS (m/s)" , "TAS (m/s)"
                ])
                
                # Write data   
                for i in range(len(flight["data"]["GNSS_time"])):
                    writer.writerow([
                        flight["data"]["GNSS_time"][i].strftime("%Y-%m-%d %H:%M:%S"),
                        flight["data"]["GNSS_lat"][i],
                        flight["data"]["GNSS_lon"][i],
                        flight["data"]["GNSS_alt"][i],
                        flight["data"]["GNSS_speed"][i],
                        flight["data"]["GNSS_head"][i],
                        flight["data"]["QNS_alt"][i],
                        flight["data"]["compass_head"][i],
                        flight["data"]["pitch"][i],
                        flight["data"]["roll"][i],
                        flight["data"]["G_force"][i],
                        flight["data"]["vario"][i],
                        flight["data"]["DP"][i],
                        flight["data"]["T_sensor"][i],
                        flight["data"]["P_stat"][i],
                        flight["data"]["air_T"][i],
                        flight["data"]["air_RH"][i],
                        flight["data"]["wind_origin"][i],
                        flight["data"]["wind_vel"][i],
                        flight["data"]["netto"][i],
                        flight["data"]["IAS"][i],
                        flight["data"]["AirES"][i],
                        flight["data"]["AirE"][i],
                        flight["data"]["AirW"][i],
                        flight["data"]["AirTd"][i],
                        flight["data"]["LCL"][i],
                        flight["data"]["AirTheta"][i],
                        flight["data"]["AirRho"][i],
                        flight["data"]["VarioIAS"][i],
                        flight["data"]["TAS"][i], 
                    ])
                    
            logger.info(f"Save succesful : {filepath} ")
            
            file.close()

        except Exception as e:
            logger.error(f"Failed to export: {e}")



def create_file_name(flight , end): #Little function to create a path file for export
        original_filename = Path(flight['file_name'])
        original_filename_wo_extension = original_filename.with_suffix("")
        original_filename_wo_extension = original_filename_wo_extension.with_suffix("") #remove both extension .csv / .igc and .vva
        file_name = str(original_filename_wo_extension) + end
        return file_name


def export_file_kml(flight, parent):
    
    
    kml = simplekml.Kml() 
    R = 6371000
    scale = 50
    minLat, maxLat = 90, -90
    minLon, maxLon = 180, -180
    minAlt, maxAlt = 1e9, -1e9

    def delta_lat(dy):
        return (dy / R) * (180 / math.pi)

    def delta_lon(dx, lat):
        return (dx / (R * math.cos(math.radians(lat)))) * (180 / math.pi)

    filename = create_file_name(flight , '_track.kml')
    filepath, _ = QtWidgets.QFileDialog.getSaveFileName(parent,"Save file as .kml", filename, "KML Files (*.kml);;All Files (*)")
    coords = []
    if not filepath:
        return 
    
    data = flight['data']

    for i in range(len(flight['data']['GNSS_lat'])): #sample every seconds
        lat = data['GNSS_lat'][i]
        lon = data['GNSS_lon'][i]
        alt = data['GNSS_alt'][i]
        coords.append((lon,lat,alt))   
        
        minLat = min(minLat, lat)
        maxLat = max(maxLat, lat)
        minLon = min(minLon, lon)
        maxLon = max(maxLon, lon)
        minAlt = min(minAlt, alt)
        maxAlt = max(maxAlt, alt)

    line = kml.newlinestring(
        name=f"{flight['file_name'].split('.')[0]}",
        coords=coords
    )
    
    line.altitudemode = simplekml.AltitudeMode.absolute
    line.extrude = 0 # ligne vers le sol (optionnel)
    line.style.linestyle.width = 2
    line.style.linestyle.color = simplekml.Color.red


   

    for l in range(0, len(flight['data']['GNSS_lat']) -1 ,10): #wind vectors every 10 seconds (only for IGC+ with netto)
        
        lat0 = data['GNSS_lat'][l]
        lon0 = data['GNSS_lon'][l]
        alt0 = data['GNSS_alt'][l]
        wind_speed = data['wind_vel'][l]
        wind_dir = data['wind_origin'][l]
        netto = data['netto'][l]
    
        L = scale * wind_speed
        dir_vent = (wind_dir + 180) % 360
    
        dx = L * math.sin(math.radians(dir_vent))
        dy = L * math.cos(math.radians(dir_vent))
    
        lat1 = lat0 + delta_lat(dy)
        lon1 = lon0 + delta_lon(dx, lat0)
    
        alt1 = alt0
        
        if not np.isnan(netto): #If netto exists (does not exist on VPRO)
            alt1 = alt0 + scale * netto
    
        ls = kml.newlinestring(
            name=f"W {wind_speed:.1f} m/s",
            coords=[(lon0, lat0, alt0), (lon1, lat1, alt1)]
        )
    
        ls.altitudemode = simplekml.AltitudeMode.absolute
        ls.style.linestyle.width = 2
    
        if not np.isnan(netto):
            ls.style.linestyle.color = simplekml.Color.cyan
        else:
            ls.style.linestyle.color = simplekml.Color.green

    # ------------------------
    # # 3. LOOKAT (ZOOM GOOGLE EARTH)
    # # ------------------------
    centerLat = (minLat + maxLat) / 2
    centerLon = (minLon + maxLon) / 2
    centerAlt = (minAlt + maxAlt) / 2

    spanLat = maxLat - minLat
    spanLon = maxLon - minLon
    spanAlt = maxAlt - minAlt

    spanDeg = max(spanLat, spanLon)
    approxRange = max(100, R * spanDeg * math.pi/180 * 1.5 + spanAlt)

    kml.document.lookat = simplekml.LookAt(
        latitude=centerLat,
        longitude=centerLon,
        altitude=centerAlt,
        range=approxRange,
        tilt=60
    )
    
    kml.save(filepath)

   
        
        
        
        
        
        
        