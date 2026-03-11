from PyQt6 import QtWidgets
from logging_handler import QTextEditLogger, logger
from pathlib  import Path 
import csv


def export_file_csv(flight):
    
    
    filename = create_file_name(flight)
    filepath, _ = QtWidgets.QFileDialog.getSaveFileName(None,"Save file as .csv", filename, "CSV Files (*.csv);;All Files (*)")
    
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



def create_file_name(flight): #Little function to create a path file for export
        original_filename = Path(flight['file_name'])
        original_filename_wo_extension = original_filename.with_suffix("")
        original_filename_wo_extension = original_filename_wo_extension.with_suffix("") #remove both extension .csv / .igc and .vva
        file_name = str(original_filename_wo_extension) + '_processed.csv' 
        return file_name


