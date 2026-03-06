# -*- coding: utf-8 -*-
# Calculus copied from the website : https://toptechboy.com/python-program-to-calculate-distance-and-heading-between-two-gps-points-using-haversine-formula/
import math
earthRadius = 6371000

def calculateDistance(lat1,lon1,lat2,lon2):
    lat1=lat1*2*math.pi/360
    lon1=lon1*2*math.pi/360
    lat2=lat2*2*math.pi/360
    lon2=lon2*2*math.pi/360
    theta = 2*math.asin(math.sqrt(
        math.sin((lat2-lat1)/2)**2 +
        math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
        ))
    distance = earthRadius * theta
    return distance


def calculateHeading(lat1,lon1,lat2,lon2):
    lat1=lat1*2*math.pi/360
    lon1=lon1*2*math.pi/360
    lat2=lat2*2*math.pi/360
    lon2=lon2*2*math.pi/360
    deltaLon=lon2-lon1
    xC=math.sin(deltaLon)*math.cos(lat2)
    yC=math.cos(lat1)*math.sin(lat2)-math.sin(lat1)*math.cos(lat2)*math.cos(deltaLon)
    beta = math.atan2(xC,yC)
    betaDeg = (beta*360/2/math.pi) % 360 #return the modulo
    return betaDeg



