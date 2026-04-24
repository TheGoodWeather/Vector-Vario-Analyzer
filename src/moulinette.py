import numpy as np
from datetime import datetime
import re
from gps_calculation import calculateDistance, calculateHeading
import copy
from units import convert_gps_coords_DDM_to_DD
from utils import sma_filter, min_res


raw_data_model = {  #available for both csv and igc file 
    "GNSS_time" : [],
    "GNSS_lat" : [],
    "GNSS_lon" : [],
    "GNSS_alt" : [],
    "QNS_alt": [],
    "GNSS_speed" : [], #native to LOGPRO
    "GNSS_head" : [],#native to LOGPRO
    "GNSS_velD" : [], #native to LOGPRO
    "compass_head" : [],
    "pitch" : [],
    "roll" : [],
    "G_force" : [], 
    "vario" : [],#native to LOGPRO
    "DP" : [],#native to LOGPRO
    "T_sensor" : [],#native to LOGPRO
    "A0_cor_DP" : [],#native to LOGPRO
    "A1_cor_DP" : [],#native to LOGPRO
    "P_stat" : [],#native to LOGPRO
    "air_T" : [], 
    "air_RH" : [],
    "wind_origin" : [],
    "wind_vel" : [],
    "netto" : [],
    "IAS" : []
    }
    

def fetch_raw_csv(flight_dic , progress_callback):
    """
    
    Parameters
    ----------
    flight_dic : dic
    
    This function returns all the raw data from a csv files, and compute additionnaly the IAS value.
    It also sets all the netto and QNS_alt values to NaN because it has not been integrated yet

    Returns
    -------
    None.

    """
    total_lines = 0 
    
    raw_data = copy.deepcopy(raw_data_model) #initializing the dic that will be returned
    #Remove spaces and blank lines
    with open(flight_dic["origin_file_path"], 'r') as file:
           lines = file.readlines()
           lines = [line for line in lines if line.strip()]
           total_lines = len(lines)
    with open(flight_dic["origin_file_path"], 'w') as file:
        file.writelines(lines)
    
    header_line_pattern = re.compile(r'^\s*t;GNSS_fix')
    data_line_pattern = re.compile(r'^\s*[-+]?\d')  # line starts with a number (could be negative or positive)
    
    with open(flight_dic["origin_file_path"], 'r') as txtfile:
        for line in txtfile:
            if header_line_pattern.match(line):
            #Read the column names from the metadata line of the file
                columns = line.rstrip().split(';')
                break
            
        raw_data_from_csv = {} # Create a dictionary of lists to hold the column values from the csv files
        for colname in columns:
            raw_data_from_csv[colname] = np.array([])  # On créé des np.array pour pouvoir y faire des opérations arithmétiques
            # Read the remaining lines of the file and add the values to the dictionary
        
        for line in txtfile:
            if data_line_pattern.match(line) and int(line.split(";")[1]) == 1 :  #If the line is data and the GPS is fixed
                values = line.rstrip().split(';')  # On récupère chaque valeur par lignes en sachant qu'elles sont séparées d'un point virgule
                for i in range(len(columns)):
                    raw_data_from_csv[columns[i]] = np.append(raw_data_from_csv[columns[i]], values[i])  # On ajoute les valeurs dans les arrays en les convertissant en float pour pouvoir les traiter
        
        for i, (parameter_from_csv, value_from_csv) in enumerate(raw_data_from_csv.items()):
            if i % 200 == 0:
                emit_progress(progress_callback, 0, 40, i, total_lines)
            for j, (parameter_from_model, value_from_model) in enumerate(raw_data.items()):
                if parameter_from_csv == parameter_from_model:
                    if parameter_from_csv == "GNSS_time": #Converting the string into float, int or datetime for the GNSS time
                        raw_data[parameter_from_model] = np.array([datetime.strptime(t, "%Y-%m-%d %H:%M:%S.%f")for t in raw_data_from_csv[parameter_from_csv]])    
                    #raw_data[parameter_from_model] = datetime.strptime(str(raw_data_from_csv[parameter_from_csv]),"%Y-%m-%d %H:%M:%S.%f" ) 
                    elif parameter_from_csv in {"GNSS_fix", "GNSS_head" , "compass_head" , "pitch" , "roll" , "P_stat" , "wind_origin"}:
                        raw_data[parameter_from_model] = raw_data_from_csv[parameter_from_csv].astype(int)
                    elif parameter_from_csv == "GNSS_velD":
                        raw_data[parameter_from_model] = raw_data_from_csv[parameter_from_csv].astype(float)
                    else:
                        raw_data[parameter_from_model] = raw_data_from_csv[parameter_from_csv].astype(float)
        
        
        with np.errstate(divide='ignore', invalid='ignore'):
            #calculating IAS as it is not natively recorded into LOGPRO
            raw_data["IAS"] = np.round(np.divide(np.sqrt(np.abs(np.multiply(2.0 / 1.225, np.add(raw_data["DP"], np.add(raw_data["A0_cor_DP"][-1], np.multiply(raw_data["A1_cor_DP"][-1], raw_data["T_sensor"])))))), flight_dic['metadata']['calib']),2)
        
        #raw_data["P_stat"] = np.divide(raw_data["P_stat"],10)
        
        raw_data["QNS_alt"] = np.full(len(raw_data["GNSS_time"]),np.nan)
        raw_data["netto"] = np.full(len(raw_data["GNSS_time"]),np.nan)
        
        raw_data["AirES"],raw_data["AirE"],raw_data["AirW"], raw_data["AirTd"], raw_data["LCL"], raw_data["AirTheta"], raw_data["AirRho"], raw_data["VarioIAS"], raw_data["TAS"] = additional_data_process(raw_data , progress_callback)
        flight_dic["data"] = raw_data
        
        return flight_dic["data"]
        
def fetch_raw_igc(flight_dic, progress_callback):
    """
    

    Parameters
    ----------
    flight_dic : TYPE
    
    This function returns all the raw data from a igc files, and compute additionnaly the Vario, Pstat, heading GPS and speed_Gps values.
    It detects if its an IGC or an IGC+ 
.

    Returns
    -------
    None.

    """

    total_lines = 0 
    raw_data = copy.deepcopy(raw_data_model) #initializing the dic that will be returned
    #Remove spaces and blank lines
    with open(flight_dic["origin_file_path"], 'r') as file:
           lines = file.readlines()
           lines = [line for line in lines if line.strip()]
           total_lines = len(lines)

    with open(flight_dic["origin_file_path"], 'w') as file:
        file.writelines(lines)

    
    with open(flight_dic["origin_file_path"], "r", encoding="utf-8") as file:
        
        for i, line in enumerate(file):
            line = line.strip()
            
            if i % 200 == 0:
                emit_progress(progress_callback, 0, 40, i, total_lines)
                
            if line.startswith("HFDTEDATE"):
                line= line.split(":")[1]   
                date_wo_hour = line.split(",")[0]

            if line.startswith("B"):
                nord_index = line.index("N")
                east_index = line.index("E")
                alti_index = line.index("A")
                time_index = line.index("B")
                raw_data["GNSS_time"].append(datetime.strptime(date_wo_hour + line[time_index+1 : time_index+7],"%d%m%y%H%M%S" ))
                
                lat_DMD = float(line[nord_index-7 : nord_index])/100000
                lon_DMD = float(line[east_index-8 : east_index])/100000
                lat_DD, lon_DD = convert_gps_coords_DDM_to_DD(lat_DMD, lon_DMD )
                raw_data["GNSS_lat"].append(lat_DD) # decimal degrees 
                raw_data["GNSS_lon"].append(lon_DD) # decimal degrees
                #With IGC , GPS coordinates are in degrees minutes decimals
                raw_data["QNS_alt"].append(int(line[alti_index+1 : alti_index+6]))
                raw_data["GNSS_alt"].append(int(line[alti_index+7 : alti_index+11]))
                
                
                lxvv_line = next(file, None)
                temp_index = lxvv_line.index("T")
                hum_index = lxvv_line.index("H")
                ias_index = lxvv_line.index("I")
                netto_index = lxvv_line.index("N")
                wind_index = lxvv_line.index('W')
                atti_index = lxvv_line.index('D')
                g_index = lxvv_line.index('G')
           
                raw_data["air_T"].append(float(str(lxvv_line[temp_index+1 : temp_index+5]))/10)
                raw_data["air_RH"].append(float(str(lxvv_line[hum_index+1 : hum_index+4]))/10)
                raw_data["IAS"].append(float(str(lxvv_line[ias_index+1 : ias_index+4]))/10)
                raw_data["netto"].append(float(str(lxvv_line[netto_index+1 : netto_index+5]))/10)
                raw_data["wind_vel"].append(float(str(lxvv_line[wind_index+4 : wind_index+7]))/10)
                raw_data["wind_origin"].append(int(str(lxvv_line[wind_index+1 : wind_index+4])))
                raw_data["compass_head"].append(int(str(lxvv_line[atti_index+1 : atti_index+4])))
                raw_data["pitch"].append(int(str(lxvv_line[atti_index+4 : atti_index+8])))
                raw_data["roll"].append(int(str(lxvv_line[atti_index+8 : atti_index+12])))
                raw_data["G_force"].append(float(str(lxvv_line[g_index+1 : g_index+4]))/10)

        timestamps = np.array([t.timestamp() for t in raw_data["GNSS_time"]])
        dt = np.mean(np.diff(timestamps))
        # computing heading
        raw_data["GNSS_head"] = []
        for i in range(len(raw_data["GNSS_lat"]) - 1):
            head = calculateHeading(
                raw_data["GNSS_lat"][i], raw_data["GNSS_lon"][i],
                raw_data["GNSS_lat"][i+1], raw_data["GNSS_lon"][i+1]
            )
            raw_data["GNSS_head"].append(round(head))
        raw_data["GNSS_head"].append(np.nan)  #To complete the array
        
        # computing speed 
        GNSS_speed = []
        for i in range(len(raw_data["GNSS_lat"]) - 1):
            distance = calculateDistance(
                raw_data["GNSS_lat"][i], raw_data["GNSS_lon"][i],
                raw_data["GNSS_lat"][i+1], raw_data["GNSS_lon"][i+1]
            )
            speed = distance / dt  #speed is in m/s
         
            GNSS_speed.append(round(speed,2))
        
        # Simple Moving Average (SMA) for filtering data
        
        raw_data["GNSS_speed"] = sma_filter(GNSS_speed, 4)
        raw_data["GNSS_speed"] = np.append(raw_data["GNSS_speed"], np.nan) #to complete the array
        
        raw_data["DP"] = np.full(len(raw_data["GNSS_time"]),np.nan)
        raw_data["T_sensor"] = np.full(len(raw_data["GNSS_time"]),np.nan)
        
        #computing P_stat with QNS_alt
        raw_data["P_stat"] = np.round(np.multiply(101325, np.power(np.subtract(1, np.divide(raw_data["QNS_alt"],44109.12)),5.255)))
        
        
        # Simple Moving Average (SMA) for filtering data
        raw_data["QNS_alt"] = sma_filter(raw_data["QNS_alt"], 7)
        raw_data["GNSS_alt"] = sma_filter(raw_data["GNSS_alt"], 7)
        
        #Computing vario with only GNSS_alt to prevent atmoshpere effect
        raw_data["vario"] = np.multiply(
            (
                np.diff(raw_data["GNSS_alt"], append=raw_data["GNSS_alt"][-1])
            ),
            dt
        )
    
        
        
        raw_data["AirES"],raw_data["AirE"],raw_data["AirW"], raw_data["AirTd"], raw_data["LCL"], raw_data["AirTheta"], raw_data["AirRho"], raw_data["VarioIAS"], raw_data["TAS"] = additional_data_process(raw_data,progress_callback )
        flight_dic["data"] = raw_data    
       

        return flight_dic["data"]


def additional_data_process(raw_data, progress_callback):
    """
    
    
    Parameters
    ----------
    raw_data : dic
    
    This function computes addtionnal data that are not initialy written in CSV or IGC files. 
    
    Returns
    -------
    AirES : TYPE
        DESCRIPTION.
    AirE : TYPE
        DESCRIPTION.
    AirW : TYPE
        DESCRIPTION.
    AirTd : TYPE
        DESCRIPTION.
    LCL : TYPE
        DESCRIPTION.
    AirTheta : TYPE
        DESCRIPTION.
    AirRho : TYPE
        DESCRIPTION.
    VarioIAS : TYPE
        DESCRIPTION.
    TAS : TYPE
        DESCRIPTION.

    """
    with np.errstate(divide='ignore', invalid='ignore'):
        
        # pression de vapeur saturante en hPa
        AirES = np.multiply(6.112, np.exp(np.divide(np.multiply(17.67,raw_data["air_T"]), np.add(raw_data["air_T"], 243.5))))
        emit_progress(progress_callback, 40, 60, 1, 9)
        # Pression de vapeur réelle en hPa
        AirE = np.multiply(raw_data["air_RH"],AirES) / 100
        emit_progress(progress_callback, 40, 60, 2, 9)
        #Mixing ratio 
        AirW = np.divide(np.multiply(0.622,AirE * 100 ), np.subtract(raw_data["P_stat"],AirE * 100 ))  #converting AirE from Hpa to Pa
        emit_progress(progress_callback, 40, 60, 3, 9)
        #Dewpoint in °C
        AirTd = 243.5 * np.divide(np.log(np.divide(AirE,6.112)),np.subtract(17.67, np.log(np.divide(AirE,6.112))))
        emit_progress(progress_callback, 40, 60, 4, 9)
        # Cloud base in meters
        LCL = np.add(raw_data["GNSS_alt"] , np.divide(np.subtract(raw_data["air_T"],AirTd), 0.0098))
        emit_progress(progress_callback, 40, 60, 5, 9)
        # Potential temperature in °C
        AirTheta = np.multiply(np.add(raw_data["air_T"], 273.15), np.power(np.divide(100000,raw_data["P_stat"]),0.286))
        emit_progress(progress_callback, 40, 60, 6, 9)
        # Air density kg/m^3
        AirRho = np.multiply(np.multiply(1.1885,np.divide(raw_data["P_stat"],100000)), np.divide(293.15, np.add(273 ,raw_data["air_T"] )))
        emit_progress(progress_callback, 40, 60, 7, 9)
        # Normalized vario m/s
        VarioIAS = np.multiply(raw_data["vario"], np.sqrt(np.divide(AirRho,1.225)))
        emit_progress(progress_callback, 40, 60, 8, 9)
        # True airspeed
        TAS = np.multiply(raw_data["IAS"], np.sqrt(np.divide(1.225, AirRho)))
        emit_progress(progress_callback, 40, 60, 9, 9)
  
    return np.round(AirES,5), np.round(AirE,5) , np.round(AirW,5), np.round(AirTd,2), np.round(LCL,2) , np.round(AirTheta,2), np.round(AirRho,2), np.round(VarioIAS,2), np.round(TAS,2)



def emit_progress(callback, start, span, step, total_steps):
    """
    This function is used to emit progress signal to update the gui progress bar
    """
    progress = start + int(span * step / total_steps)
    callback.emit(progress)