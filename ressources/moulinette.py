import numpy as np
from datetime import datetime
import re

##------------------------------------ Moulinette-----------------------------------
def Moulinette(flight_path, config_path):  # function moulinette


    # On ouvre la config correspondant à la bonne sonde
    config = {}
    with open(config_path, 'r') as f:
        for line in f:
            if line.startswith('//')or line.startswith('$')  or line == '\n':  # On prend pas en compte  les commentaires
                continue
            line = line.split('%')[0]
            key, value = line.strip().rstrip(';').split('=')
            if '/' in value:  # Check if the value is a fraction
                numerator, denominator = value.split('/')
                config[key.strip()] = float(numerator) / float(denominator)
            else:
                config[key.strip()] = float(value.strip())

            # On ouvre le raw flight et on récupère les datas

    # on commence par virer les éventuelles lignes vides
    with open(flight_path, 'r') as file:
        lines = file.readlines()
        lines = [line for line in lines if line.strip()]
    with open(flight_path, 'w') as file:
        file.writelines(lines)
        
    
    
   



    metadata_line_pattern = re.compile(r'^\s*Time')
    data_line_pattern = re.compile(r'^\s*[-+]?\d')  # line starts with a number (could be negative or positive)
    with open(flight_path, 'r') as txtfile:
        for line in txtfile:
            
            if metadata_line_pattern.match(line):
        
           # Read the column names from the metadata line of the file
                columns = line.rstrip().split(' ')
       

                break
        data = {}  # Create a dictionary of lists to hold the column values
        for colname in columns:
            data[colname] = np.array([])  # On créé des np.array pour pouvoir y faire des opérations arithmétiques
            # Read the remaining lines of the file and add the values to the dictionary
        for line in txtfile:
            if data_line_pattern.match(line):

                values = line.rstrip().split(' ')  # On récupère chaque valeur par lignes en sachant qu'elles sont séparées d'un point virgule
                for i in range(len(columns)):
                    data[columns[i]] = np.append(data[columns[i]], float(values[i]))  # On ajoute les valeurs dans les arrays en les convertissant en float pour pouvoir les traiter

            # MOULINETTE TRADUITE EN PYTHON
        with np.errstate(divide='ignore', invalid='ignore'):

            Pabs = data['Patm']
            dtC = np.mean(np.diff(data['Time'][1:])) / 1000  # Periode moyenne seconde
    
            RhoI = np.multiply((np.multiply(1.1885, Pabs)),(293.15 / (273.15 + data['Temp_AoA'])))  # Masse volumique capteur incidence
            RhoK = np.multiply((np.multiply(1.1885, Pabs)),(293.15 / (273.15 + data['Temp_IAS'])))  # Masse volumique Vitesse
            RhoL = np.multiply((np.multiply(1.1885, Pabs)),(293.15 / (273.15 + data['Temp_AoS'])))  # Masse volumique Vitesse
    
            NairI = np.multiply(18.205 + (np.multiply(0.0484, (data['Temp_AoA'] - 20))), 10 ** - 6)
            NairK = np.multiply(18.205 + (np.multiply(0.0484, (data['Temp_IAS'] - 20))), 10 ** - 6)
            NairL = np.multiply(18.205 + (np.multiply(0.0484, (data['Temp_AoS'] - 20))), 10 ** - 6)
    
            EpsI = np.multiply(np.multiply(np.multiply(- 64.0 / np.pi, 1.0240e+09) * NairI / RhoI, (4.79 * 10 ** - 7)) / np.abs(data['DP_AoA']),(np.sqrt(1 + (8.0 * np.abs(data['DP_AoA']) / 101)) - 1))  # ORDRE DE CALCUL A VERIFIER
            EpsK = np.multiply(np.multiply(np.multiply(- 64.0 / np.pi, 1.0240e+09) * NairK / RhoK, (4.79 * 10 ** - 7)) / np.abs(data['DP_IAS']),(np.sqrt(1 + (8.0 * np.abs(data['DP_IAS']) / 101)) - 1))  # ORDRE DE CALCUL A VERIFIER
            EpsL = np.multiply( np.multiply(np.multiply(- 64.0 / np.pi, 1.0240e+09) * NairL / RhoL, (4.79 * 10 ** - 7)) / np.abs(data['DP_AoS']),(np.sqrt(1 + (8.0 * np.abs(data['DP_AoS']) / 101)) - 1))  # ORDRE DE CALCUL A VERIFIER
    
            # creation des vecteurs I/K avec les correction altitude et perte de charge.
    
            If = (np.multiply((data['DP_AoA']) / Pabs, 0.966)) / (1 + EpsI)
            # Kf = ((np.multiply(config['CorKiel'], data['DP_IAS'])) / Pabs * 0.966) / (1 + EpsK) ancienne formule
            Kf = (np.multiply((data['DP_IAS']) / Pabs, 0.966)) / (1 + EpsK)
            # Lf = ((data['DP_AoS']) / Pabs * 0.966) / (1 + EpsL) ancienne formule
            Lf = (np.multiply((data['DP_AoS']) / Pabs, 0.966)) / (1 + EpsL)
    
            I_K = If / Kf
            L_K = Lf / Kf
    
            L_K[np.isnan(L_K)] = 0
            I_K[np.isnan(I_K)] = 0
    
            # correction temperature
            AccxCT = data['Ax1'] - np.multiply((data['Temp_IMU1'] - 20), config['OTempX1'])
            AccyCT = data['Ay1'] - np.multiply((data['Temp_IMU1'] - 20), config['OTempY1'])
            AcczCT = data['Az1'] - np.multiply((data['Temp_IMU1'] - 20), config['OTempZ1'])
            # correction temperature
    
            AccxCT2 = data['Ax2'] - np.multiply((data['Temp_IMU2'] - 20), config['OTempX2'])
            AccyCT2 = data['Ay2'] - np.multiply((data['Temp_IMU2'] - 20), config['OTempY2'])
            AcczCT2 = data['Az2'] - np.multiply((data['Temp_IMU2'] - 20), config['OTempZ2'])
    
            # calcul composantes corrig d'offset/facteur et alignement acclromtre n1
            Accx = (AccxCT - config['Bx']) / (1 + config['Sx'])
            Accy = (AccyCT - config['By']) / (1 + config['Sy']) + (AccxCT - config['Bx']) * config['Mx'] / ((1 + config['Sx']) * (1 + config['Sy']))
            Accz = (AcczCT - config['Bz']) / (1 + config['Sz']) + (AccyCT - config['By']) * - config['Mz'] / ((1 + config['Sz']) * (1 + config['Sy'])) - (AccxCT - config['Bx']) * (config['Sy'] * config['My'] + config['My'] + config['Mx'] * config['Mz']) / ((1 + config['Sx']) * (1 + config['Sz']) * (1 + config['Sy']))
            G = np.sqrt(Accx ** 2 + Accy ** 2 + Accz ** 2)
    
            Gs = G / 9.806
            # assiette et roulis acclromtre n1
            Theta_R = -(np.arctan(Accx / np.sqrt(Accy ** 2 + Accz ** 2)) * 180 / np.pi)
            Phi_R = np.arctan(Accz / Accy) * 180 / np.pi
    
            Theta1 = ((Theta_R + np.multiply(np.cos((Phi_R + config['PhiC']) * np.pi / 180), config['ThetaC'])) - config['ZT']) / config['CTRL_A1']
    
            Roulis1 = (Phi_R - config['ZR'])
    
            # calcul composantes corrig d'offset/facteur et alignement acclromtre n2
            Accx2 = (AccxCT2 - config['Bx2']) / (1 + config['Sx2'])
            Accy2 = (AccyCT2 - config['By2']) / (1 + config['Sy2']) + (AccxCT2 - config['Bx2']) * config['Mx2'] / ((1 + config['Sx2']) * (1 + config['Sy2']))
            Accz2 = (AcczCT2 - config['Bz2']) / (1 + config['Sz2']) + (AccyCT2 - config['By2']) * - config['Mz2'] / ((1 + config['Sz2']) * (1 + config['Sy2'])) - (AccxCT2 - config['Bx2']) * (config['Sy2'] * config['My2'] + config['My2'] + config['Mx2'] * config['Mz2']) / ((1 + config['Sx2']) * (1 + config['Sz2']) * (1 + config['Sy2']))
            G2 = np.sqrt(Accx2 ** 2 + Accy2 ** 2 + Accz2 ** 2)
    
            Gs2 = G2 / 9.806
            # assiette et roulis acclromtre n2
            Theta_R2 = -(np.arctan(Accx2 / np.sqrt(Accy2 ** 2 + Accz2 ** 2)) * 180 / np.pi)
    
            Phi_R2 = np.arctan(Accz2 / Accy2) * 180 / np.pi
    
            Theta2 = ((Theta_R2 + np.multiply(np.cos((Phi_R2 + config['PhiC2']) * np.pi / 180),config['ThetaC2'])) - config['ZT2']) / config['CTRL_A2']
    
            Roulis2 = (Phi_R2 - config['ZR2'])
    
            G = (Gs + Gs2) / 2
            Theta = (Theta1 + Theta2) / 2
            Dtheta = Theta1 - Theta2
            Roulis = (Roulis1 + Roulis2) / 2
    
            # Densit de l'air Rho
            Rho = np.multiply((np.multiply(1.1885, Pabs)), (293.15 / (273.15 + data['Temp_IMU1'])))
            # altitude
            Alt = np.multiply((1 - ((np.multiply(Pabs, 1000)) / 1013.25) ** (1 / 5.255)), 288.15) / 0.0065 - (np.multiply((1 - ((np.multiply(Pabs[3], 1000)) / 1013.25) ** (1 / 5.255)), 288.15) / 0.0065)
            # vario IAS
            VarioIAS = np.zeros(len(Alt))
            VarioIAS[1:] = (np.multiply(np.diff(Alt), np.sqrt(Rho[1:]) / 1.225)) / dtC
            # Vitesse brute (utilise pour corrigig la calibration de l'incidence et du lacet)
            Kiel = np.abs(np.sqrt(np.multiply(2.0 / 1.225, np.abs(Kf))))
            # SKiel=smooth(Kiel,4); # le diff donne la turbulence vers 1Hz  10m/S = chel 10m.
            # DKiel = Kiel-SKiel ;#  wpass [?  rad/sample]
    
            # Angle d'incidence (Alpha) avec correction de non-linéartié + effet  reynolds
            Alpha = np.multiply(np.multiply(I_K**2, (np.multiply((Kiel / config['Vitesse_REF']), config['Eff_Vitesse_NL_S']) + config['Eff_Vitesse_NL_O'])), config['Alpha_NL_REF']) + np.multiply(I_K,np.multiply((np.multiply((Kiel / config['Vitesse_REF']),config['Eff_Vitesse_S'])+config['Eff_Vitesse_O']),config['Alpha_REF'])) - (config['A0_Offset_ALPHA'] + np.multiply(config['A1_Offset_ALPHA'],Kiel)) 
            # Angle de dérapage (Beta)
            Lacet = np.multiply(L_K,config['Lacet']) - config['Offset_Lacet']
            # Angle de plan
            Angle_tot = Theta + Alpha
            # Angle de plan corrig du lacet
            Angle_tot_COR = Angle_tot + np.multiply(np.sin(Roulis * np.pi / 180), Lacet)
            # Vitesse
            IAS = (Kiel ** 2.0 * config['A2V'] + np.multiply(Kiel, config['A1V']) + config['A0V'])
            IAS_COR = np.multiply(IAS, (np.multiply(0.003, Lacet) + 1))
    
            TAS = np.multiply(IAS_COR, np.sqrt(1.225 / Rho)) * 3.6
            
            #Fineness = -1 / np.tan(np.deg2rad(Angle_tot_COR)) #Ajout de la finesse
            
            Time = data['Time'] 
            
            # CREATING DATE VARIABLE
            date_list = []
            
            # Iterate through the data
            for i in range(len(data['Years'])):
                year = int(data['Years'][i])
                month = int(data['Month'][i])
                day = int(data['Day'][i])
                hour = int(data['Hour'][i])
                minute = int(data['Minute'][i])
                second = int(data['Second'][i])
                
                # Create a datetime object
                if (year != 0):  #si l'année est correcte car le gps a fixé
                    date_obj = datetime(year, month, day, hour, minute, second)
                    
                    # Append to the list
                    date_list.append(date_obj)
                else : 
                    date_list.append(None)
            
            # Convert list to numpy array
            Dates = np.array(date_list)
            
            return Time, Dates, IAS_COR, Angle_tot_COR , Alpha , Theta, Dtheta, Roulis, Rho, Lacet 



 

