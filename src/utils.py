import numpy as np


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