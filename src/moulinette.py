import numpy as np
from datetime import datetime
import re

def moulinette_csv(flight_dic):
    
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
        data = {}  # Create a dictionary of lists to hold the column values
        for colname in columns:
            data[colname] = np.array([])  # On créé des np.array pour pouvoir y faire des opérations arithmétiques
            # Read the remaining lines of the file and add the values to the dictionary
        
        for line in txtfile:
            if data_line_pattern.match(line) and int(line.split(";")[1]) == 1 :  #If the line is data and the GPS is fixed
                values = line.rstrip().split(';')  # On récupère chaque valeur par lignes en sachant qu'elles sont séparées d'un point virgule
                for i in range(len(columns)):
                    data[columns[i]] = np.append(data[columns[i]], values[i])  # On ajoute les valeurs dans les arrays en les convertissant en float pour pouvoir les traiter
        


def moulinette_igc(flight_dic):
    print(flight_dic)
    return