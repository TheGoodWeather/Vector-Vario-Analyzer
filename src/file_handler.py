# -*- coding: utf-8 -*-
from logging_handler import QTextEditLogger, logger
import re
from itertools import islice
from datetime import datetime
from pathlib import Path
 
def generate_vva(filepath, metadata):
    FUNCTION_VERSION = 1.0
    vva_path = filepath.with_suffix(filepath.suffix + ".vva")

    with open(vva_path, "w", encoding="utf-8") as f:
        try :
            f.write(f"VV_VVA:{FUNCTION_VERSION}\n")
            f.write(f"VV_SN:{metadata['vv_sn']}\n")
            f.write(f"VV_HW:{metadata['vv_hw']}\n")
            f.write(f"VV_FW:{metadata['vv_fw']}\n")
            f.write(f"CALIB:{metadata['calib']}\n")
            f.write(f"pilot:{metadata['pilot']}\n")
            f.write(f"date:{metadata['date']}\n")
            f.write(f"altitude_max:{metadata['altitude_max']}\n")
            f.write(f"altitude_min:{metadata['altitude_min']}\n")
            f.write(f"altitude_start:{metadata['altitude_start']}\n")
            f.write(f"avg_windspeed:{metadata['avg_windspeed']}\n")
            f.write(f"avg_winddir:{metadata['avg_winddir']}\n")
            f.write(f"comment:{metadata['comment']}\n")
            
            logger.info(f".vva file created at {vva_path}")
            
        except Exception as e:
             logger.info(f"An error occurred: {e}")

     
def igc2vva(igc_filepath, widget_comment):
    
    metadata = {
        "vv_sn" : None,
        "vv_hw" : None,
        "vv_fw" : None,
        "calib" : None,
        "pilot" : None,
        "date" : None,
        "altitude_max" : None,
        "altitude_min" : None, 
        "altitude_start" : None,
        "avg_windspeed" : None,
        "avg_winddir" : None,
        "comment" : ""
        }


    
    with open(igc_filepath, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if line.startswith("AXVV"):
                metadata["vv_sn"] = line[4:]  
            if line.startswith("HFRHWHARDWAREVERSION"):
                metadata["vv_hw"]= line.split(":")[1]
            if line.startswith("HFRFWFIRMWAREVERSION"):
                metadata["vv_fw"]= line.split(":")[1]
            if line.startswith("HFPLTPILOTINCHARGE"):
                metadata["pilot"]= line.split(":")[1]
            if line.startswith("HFDTEDATE"):
                line= line.split(":")[1]   
                date_wo_hour = line.split(",")[0]
            if metadata["vv_sn"] and metadata["vv_hw"] and metadata["vv_fw"] and metadata["pilot"] and date_wo_hour != None :
                break 
            
        file.seek(0)
        gps_altitude = []
        windspeed = []
        winddir = []
        hour = []
        for line in file:
            line = line.strip()
            if line.startswith("B"):
                gps_altitude.append(int(line[-5:]))
                lxvv_line = next(file, None)
                wind_index = lxvv_line.index('W')
                hour.append(str(line[1:6]))
                windspeed.append(int(str(lxvv_line[wind_index+1 : wind_index+3])))
                winddir.append(int(str(lxvv_line[wind_index+4 : wind_index+7])))
        
        altitude_max = max(gps_altitude)
        altitude_min = min(gps_altitude)
        altitude_start = gps_altitude[0]
        avg_winddir = sum(winddir) / len(winddir)
        avg_windspeed = sum(windspeed) / len(windspeed)
        comment = widget_comment.text()
        
        date = datetime.strptime(date_wo_hour + hour[0],"%d%m%y%H%M%S" ).strftime("%Y-%m-%d %H.%M")
        metadata["date"] = date
        metadata["altitude_max"] = altitude_max
        metadata["altitude_min"] = altitude_min
        metadata["altitude_start"] = altitude_start
        metadata["comment"] = comment
        
        if avg_windspeed is not None:
            metadata["avg_windspeed"] = round(avg_windspeed,2)
            
        if avg_winddir is not None:
            metadata["avg_winddir"] = round(avg_winddir,2)
        
        return metadata


def csv2vva(csv_filepath, widget_comment):
    """
    

    Parameters
    ----------
    csv_filepath : string
        the csv filepath to fetch metadata.
    widget_comment : Qwidget
        The widget from which the comment is written.

    Returns
    -------
    metadata : dic
        
    """
    metadata = {
        "vv_sn" : None,
        "vv_hw" : None,
        "vv_fw" : None,
        "calib" : None,
        "pilot" : None,
        "date" : None,
        "altitude_max" : None,
        "altitude_min" : None, 
        "altitude_start" : None,
        "avg_windspeed" : None,
        "avg_winddir" : None,
        "comment" : ""
        }

    
    with open(csv_filepath, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line.startswith("# [VV] "):
                sn_match = re.search(r"SN:([^\s]+)", line)
                hw_match = re.search(r"HW:([^\s]+)", line)
                fw_match = re.search(r"FW:([^\s]+)", line)
               
                if sn_match:
                    metadata["vv_sn"] = sn_match.group(1)
                if hw_match:
                    metadata["vv_hw"] = hw_match.group(1)
                if fw_match:
                    metadata["vv_fw"] = fw_match.group(1)
                
            elif line.startswith("# [PILOTE]"):
                metadata["pilot"] = line.replace("# [PILOTE]", "").strip()
                
            elif line.startswith("# [CALIB]"):
                metadata["calib"] = line.replace("# [CALIB]", "").strip()
            
            elif metadata["calib"] and metadata["vv_sn"] and metadata["vv_hw"] and metadata["vv_fw"] and metadata["pilot"] != None:
                break
    
    gps_altitude = []
    windspeed = []
    winddir = []
    gnss_time = []
    
    with open(csv_filepath, "r", encoding="utf-8") as file:
        for line in islice(file,5, None): #To change if there is more comments added into the file
            if int(line.split(";")[1]) == 1 :  #If the GPS is fixed
                gps_altitude.append(float(line.split(";")[5]))
                windspeed.append(float(line.split(";")[21]))
                winddir.append(int(line.split(";")[20]))
                gnss_time.append(datetime.strptime(str(line.split(";")[2]), "%Y-%m-%d %H:%M:%S.%f"))
        
    altitude_max = max(gps_altitude)
    altitude_min = min(gps_altitude)
    altitude_start = gps_altitude[0]
    avg_winddir = sum(winddir) / len(winddir)
    avg_windspeed = sum(windspeed) / len(windspeed)
    date = gnss_time[0].strftime("%Y-%m-%d %H.%M")
    metadata["date"] = date
    metadata["altitude_max"] = altitude_max
    metadata["altitude_min"] = altitude_min
    metadata["altitude_start"] = altitude_start
    metadata["comment"] = widget_comment.text()
    
    if avg_windspeed is not None:
        metadata["avg_windspeed"] = round(avg_windspeed,2)
        
    if avg_winddir is not None:
        metadata["avg_winddir"] = round(avg_winddir,2)
    file.close()
    
    return metadata

def read_vva_metadata(vva_filepath):
    """
    Read data from a specified vva file, and retrieves it into a dic

    """
    metadata = {
        "vv_vva" : None,
        "vv_sn" : None,
        "vv_hw" : None,
        "vv_fw" : None,
        "calib" : None,
        "pilot" : None,
        "date" : None,
        "altitude_max" : None,
        "altitude_min" : None, 
        "altitude_start" : None,
        "avg_windspeed" : None,
        "avg_winddir" : None,
        "comment" : ""
        }
    
    with open(vva_filepath, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if line.startswith("VV_VVA"):
                metadata["vv_vva"] = line.split(":")[1]  
            if line.startswith("VV_SN"):
                metadata["vv_sn"] = line.split(":")[1]  
            if line.startswith("VV_HW"):
                metadata["vv_hw"] = line.split(":")[1]
            if line.startswith("VV_FW"):
                metadata["vv_fw"] = line.split(":")[1]  
            if line.startswith("CALIB"):
                if line.split(":")[1] != 'None':
                    metadata["calib"] = float(line.split(":")[1])
                else:
                    metadata["calib"] = line.split(":")[1]
            if line.startswith("pilot"):
                metadata["pilot"] = line.split(":")[1]
            if line.startswith("date"):
                metadata["date"] = line.split(":")[1]   
            if line.startswith("altitude_max"):
                metadata["altitude_max"] = line.split(":")[1]  
            if line.startswith("altitude_min"):
                metadata["altitude_min"] = line.split(":")[1]  
            if line.startswith("altitude_start"):
                metadata["altitude_start"] = line.split(":")[1]  
            if line.startswith("avg_windspeed"):
                metadata["avg_windspeed"] = line.split(":")[1]  
            if line.startswith("avg_winddir"):
                metadata["avg_winddir"] = line.split(":")[1]  
            if line.startswith("comment"):
                metadata["comment"] = line.split(":")[1] 
    file.close()
    return metadata

def load_vva_files(flight_dir="flight"):
    vva_files = Path(flight_dir).glob("*.vva")

    data = []  #List of dictionnaries
    for file in vva_files:
        flight = {
           "metadata" : None,
           "data" : None,
           "file_path" : None,
           "file_name" : None,
           "origin_file_path" : None,
           "is_data_processed" : False,
           "plot" : {"variables_1D" : [[],[]],
                     "windbarbs_2D" : []}}
        flight["metadata"] = read_vva_metadata(file)
        flight["file_name"] = file.name
        flight["file_path"] = file
        origin_file = file.with_suffix("")
        if origin_file.exists():
            flight["origin_file_path"] = origin_file
        else:
            logger.info(f"{file} has no origin file")
        data.append(flight)
    return data