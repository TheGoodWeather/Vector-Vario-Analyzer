import numpy as np
from datetime import datetime
import re
from gps_calculation import calculateDistance, calculateHeading

raw_data_model = {  #available for both csv and igc file 
    "GNSS_time" : [],
    "GNSS_lat" : [],
    "GNSS_lon" : [],
    "GNSS_alt" : [],
    "QNS_alt": [],
    "GNSS_speed" : [], #native to LOGPRO
    "GNSS_head" : [],#native to LOGPRO
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
    

def fetch_raw_csv(flight_dic):
    """
    
    Parameters
    ----------
    flight_dic : dic
    
    This function returns all the raw data from a csv files, and compute additionnaly the IAS value.

    Returns
    -------
    None.

    """
    raw_data = raw_data_model #initializing the dic that will be returned
    #Remove spaces and blank lines
    with open(flight_dic["origin_file_path"], 'r') as file:
           lines = file.readlines()
           lines = [line for line in lines if line.strip()]
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
            for j, (parameter_from_model, value_from_model) in enumerate(raw_data.items()):
                if parameter_from_csv == parameter_from_model:
                    if parameter_from_csv == "GNSS_time": #Converting the string into float or datetime for the GNSS time
                        raw_data[parameter_from_model] = raw_data_from_csv[parameter_from_csv] #TO DO : COnvert into datetime variable 
                    else:
                        raw_data[parameter_from_model] = raw_data_from_csv[parameter_from_csv].astype(float)
        
        with np.errstate(divide='ignore', invalid='ignore'):
            #calculating IAS as it is not natively recorded into LOGPRO
            raw_data["IAS"] = np.sqrt(np.multiply(2.0 / 1.225, np.add(raw_data["DP"], raw_data["A0_cor_DP"][-1], np.multiply(raw_data["A1_cor_DP"][-1], raw_data["T_sensor"]))))
            
        
        raw_data["AirES"],raw_data["AirE"],raw_data["AirW"], raw_data["AirTd"], raw_data["LCL"], raw_data["AirTheta"], raw_data["AirRho"], raw_data["VarioIAS"], raw_data["TAS"] = additional_data_process(raw_data)
        flight_dic["data"] = raw_data
        
def fetch_raw_igc(flight_dic):
    """
    

    Parameters
    ----------
    flight_dic : TYPE
    
    This function returns all the raw data from a igc files, and compute additionnaly the Vario, Pstat, heading GPS and speed_Gps values.
.

    Returns
    -------
    None.

    """
    raw_data = raw_data_model #initializing the dic that will be returned
    #Remove spaces and blank lines
    with open(flight_dic["origin_file_path"], 'r') as file:
           lines = file.readlines()
           lines = [line for line in lines if line.strip()]
    with open(flight_dic["origin_file_path"], 'w') as file:
        file.writelines(lines)


    with open(flight_dic["origin_file_path"], "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            
            if line.startswith("HFDTEDATE"):
                line= line.split(":")[1]   
                date_wo_hour = line.split(",")[0]

            if line.startswith("B"):
                nord_index = line.index("N")
                east_index = line.index("E")
                alti_index = line.index("A")
                time_index = line.index("B")
                raw_data["GNSS_time"].append(datetime.strptime(date_wo_hour + line[time_index+1 : time_index+7],"%d%m%y%H%M%S" ))
                raw_data["GNSS_lat"].append(float(line[nord_index-7 : nord_index])/100000) # decimal degrees 
                raw_data["GNSS_lon"].append(float(line[east_index-8 : east_index])/100000) # decimal degrees
                raw_data["QNS_alt"].append(int(line[alti_index+1 : alti_index+5]))
                raw_data["GNSS_alt"].append(int(line[alti_index+6 : alti_index+10]))
                
                
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
        
        
        # computing speed 
        raw_data["GNSS_speed"] = []
        for i in range(len(raw_data["GNSS_lat"]) - 1):
            distance = calculateDistance(
                raw_data["GNSS_lat"][i], raw_data["GNSS_lon"][i],
                raw_data["GNSS_lat"][i+1], raw_data["GNSS_lon"][i+1]
            )
            speed = distance / dt  #speed is in m/s
         
            raw_data["GNSS_speed"].append(round(speed,1))

        raw_data["P_stat"] = np.multiply(101325, np.power(np.subtract(1, np.divide(raw_data["QNS_alt"],44109.12)),5.255))
        raw_data["vario"] = np.multiply(np.divide(np.add(np.diff(raw_data["QNS_alt"],append=0), np.diff(raw_data["GNSS_alt"], append=0)),2), dt)
                
        raw_data["AirES"],raw_data["AirE"],raw_data["AirW"], raw_data["AirTd"], raw_data["LCL"], raw_data["AirTheta"], raw_data["AirRho"], raw_data["VarioIAS"], raw_data["TAS"] = additional_data_process(raw_data)
        flight_dic["data"] = raw_data       
        
       
        # # print("P_stat_____________")
        # # print(raw_data["P_stat"][1000:1010])
        # print("AirES___________")
        # print(raw_data["AirES"][11110:11120])
        # print("AirE___________")
        # print(raw_data["AirE"][11110:11120])
        # print("AirW___________")
        # print(raw_data["AirW"][11110:11120])
        # print("AirTd___________")
        # print(raw_data["AirTd"][11110:11120])
        # print("LCLl___________")
        # print(raw_data["LCL"][11110:11120])
        # print("AirTheta___________")
        # print(raw_data["AirTheta"][11110:11120])
        # print("AirRho___________")
        # print(raw_data["AirRho"][11110:11120])
        # print("TAS___________")
        # print(raw_data["TAS"][11110:11120])
        
    
        
    return

def additional_data_process(raw_data):
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
        # Pression de vapeur réelle en hPa
        AirE = np.multiply(raw_data["air_RH"],AirES) / 100
        #Mixing ratio 
        AirW = np.divide(np.multiply(0.622,AirE ), np.subtract(raw_data["P_stat"],AirE ))
        #Dewpoint in °C
        AirTd = 243.5 * np.divide(np.log(np.divide(AirE,6.112)),np.subtract(17.67, np.log(np.divide(AirE,6.112))))
        # Cloud base in meters
        LCL = np.add(raw_data["GNSS_alt"] , np.divide(np.subtract(raw_data["air_T"],AirTd), 0.0098))
        # Potential temperature in °C
        AirTheta = np.multiply(np.add(raw_data["air_T"], 273.15), np.power(np.divide(100000,raw_data["P_stat"]),0.286))
        # Air density kg/m^3
        AirRho = np.multiply(np.multiply(1.1885,np.divide(raw_data["P_stat"],100000)), np.divide(293.15, np.add(273 ,raw_data["air_T"] )))
        # Normalized vario m/s
        VarioIAS = np.multiply(raw_data["vario"], np.sqrt(np.divide(AirRho,1.225)))
        # True airspeed
        TAS = np.multiply(raw_data["IAS"], np.sqrt(np.divide(AirRho,1.225)))
        
    
    #     Pabs = data['Patm']
    #     dtC = np.mean(np.diff(data['Time'][1:])) / 1000  # Periode moyenne seconde
    
    #     RhoI = np.multiply((np.multiply(1.1885, Pabs)),(293.15 / (273.15 + data['Temp_AoA'])))  # Masse volumique capteur incidence
    #     RhoK = np.multiply((np.multiply(1.1885, Pabs)),(293.15 / (273.15 + data['Temp_IAS'])))  # Masse volumique Vitesse
    #     RhoL = np.multiply((np.multiply(1.1885, Pabs)),(293.15 / (273.15 + data['Temp_AoS'])))  # Masse volumique Vitesse*
    
    
    return AirES, AirE, AirW, AirTd, LCL , AirTheta, AirRho, VarioIAS, TAS