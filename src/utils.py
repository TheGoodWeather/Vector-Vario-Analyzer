import numpy as np
from scipy.interpolate import CubicSpline , interp1d



VARIABLE_LABELS = {
    "GNSS_time"    : "Time",
    "GNSS_lat"     : "Latitude",
    "GNSS_lon"     : "Longitude",
    "GNSS_alt"     : "GNSS Altitude",
    "QNS_alt"      : "Pressure Altitude",
    "GNSS_speed"   : "GNSS Speed",
    "GNSS_head"    : "GNSS Heading",
    "GNSS_velD"    : "GNSS Vario",
    "compass_head" : "Compass Heading",
    "pitch"        : "Pitch",
    "roll"         : "Roll",
    "G_force"      : "G Force",
    "vario"        : "Vario",
    "DP"           : "Dynamic Pressure",
    "T_sensor"     : "Sensor Temperature",
    "A0_cor_DP"    : "A0 Corrected DP",
    "A1_cor_DP"    : "A1 Corrected DP",
    "P_stat"       : "Static Pressure",
    "air_T"        : "Air Temperature",
    "air_RH"       : "Relative Humidity",
    "wind_origin"  : "Wind Direction",
    "wind_vel"     : "Wind Speed",
    "netto"        : "Netto",
    "IAS"          : "Indicated Airspeed",
    "AirES"        : "Saturation Vapor",
    "AirE"        : "Vapor Pressure",
    "AirW"        : "Mixing Ratio",
    "AirTd"        : "Dew Point",
    "LCL"        : "Cloud Base",
    "AirTheta"        : "Potential Temperature",
    "AirRho"        : "Air Density",
    "VarioIAS"        : "Vario IAS ",
    "TAS"        : "True Air Speed",
    
}

VARIABLE_KEYS = {v: k for k, v in VARIABLE_LABELS.items()}

def mapping(value, fromLow, fromHigh, toLow, toHigh):
    return (value - fromLow) * (toHigh - toLow) / (fromHigh - fromLow) + toLow
    

def min_res(data):

    diff_min = 9999
    for i in range(1,len(data)-1):
        diff = data[i] - data[i-1]
        if abs(diff) < diff_min and diff !=0:
            diff_min = abs(diff)
    return diff_min


def sma_filter(data, window_size_sma):
    """
    Apply a Simple Moving Average filter to data.
    Replaces the first and last window_size values with the original raw values
    to avoid edge effects from convolution.
    """
    if window_size_sma <= 1 or len(data) == 0:
        return data  # pas de filtrage nécessaire
    
    if window_size_sma > len(data):
        window_size_sma = len(data) 
    kernel_sma = np.ones(window_size_sma) / window_size_sma
    filtered = np.convolve(data, kernel_sma, mode='same')
    # Remplace les bords par les valeurs brutes
    filtered[:window_size_sma] = data[:window_size_sma]
    filtered[-window_size_sma:] = data[-window_size_sma:]
    return filtered



def get_label(variable: str) -> str:
    """
    Return a more comprehensive label from the VARIABLE_LEVELS list
    """
    return VARIABLE_LABELS.get(variable, variable)



def is_all_nan(data):

    arr = np.asarray(data)

    # types numériques seulement
    if np.issubdtype(arr.dtype, np.number):
        return np.all(np.isnan(arr))

    return False


def sort_combobox_alphabetically(combobox):
    """
    Trie un QComboBox par ordre alphabétique
    tout en conservant les userData.
    """

    items = []

    for i in range(combobox.count()):

        text = combobox.itemText(i)
        data = combobox.itemData(i)

        items.append((text, data))

    # tri alphabétique insensible à la casse
    items.sort(key=lambda x: x[0].lower())

    combobox.clear()

    for text, data in items:
        combobox.addItem(text, userData=data)

def get_variable(label: str) -> str:
    """
    Return the internal variable name from a user-friendly label.
    """
    return VARIABLE_KEYS.get(label, label)

def interp_spline(t_new, t, values):
    
    values = np.asarray(values, dtype=float)

    # supprime NaN
    mask = ~np.isnan(values)

    t_clean = t[mask]
    v_clean = values[mask]

    # fallback sécurité
    if len(v_clean) < 2:
        return np.full_like(t_new, np.nan)

    spline = CubicSpline(
        t_clean,
        v_clean,
        bc_type='natural'
    )

    return spline(t_new)


def interp_nearest(t_new, t, values):

    values = np.asarray(values, dtype=float)

    # suppression NaN
    mask = ~np.isnan(values)

    t_clean = t[mask]
    v_clean = values[mask]

    # sécurité
    if len(v_clean) < 2:
        return np.full_like(t_new, np.nan)

    f = interp1d(
        t_clean,
        v_clean,
        kind='nearest',
        bounds_error=False,
        fill_value=np.nan
    )

    return f(t_new)
