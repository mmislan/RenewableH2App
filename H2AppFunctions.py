import numpy as np
import math

#---- Function for calculating Wind Power from Velocity (m/s) ----
def P_wind(radius, height, velocity):
    z0 = 1.0  # Adjust windspeed from Surface (10m) to avg windmill height (e.g. 80m) assuming Roughness length z0 = 1m
    velocity = velocity * (math.log(height / z0) / math.log(10 / z0))

    #Assumes a 2MW windmill, average 80m tall has rotor radius (e.g. 60m)
    if ((velocity >= 3) or (velocity <= 25)):  # Assumes windmill unable to produce power below 3m/s or above 25m/s (90 km/hr)
        Pw = (3.14/2)*1.225*(radius**2)*0.4*0.75*0.9*velocity**3 #Pw = (pi/2)*rho_air*R^2*Cp*Ng*Nb*u^3 = (pi/2)*1.225*3^2*0.4*0.75*0.9*u^3
    else:
        Pw = 0 #W
    return Pw #Units of Watts

#--- Function for calculating Solar Power (W/m2) ----
def P_solar(Latitude_degree, DOY, Hour):
    Lat_rad = math.radians(Latitude_degree) #Convert latitude from degrees to radians
    dr = 1+0.33*math.cos((2*3.14/365)*DOY)#This is distance from sun to earth as function of Day of Year (1-365)
    delta = 0.409*math.sin((2*3.14/365)*DOY-1.39)
    omega_s = math.radians(15*(Hour-12))
    E0 = 1353 #W/m2 -> Max solar radiance hitting top of Earths atmosphere
    Sunrise = 12 - math.degrees(np.arccos((-1*np.sin(Lat_rad)*np.sin(delta))/(np.cos(Lat_rad)*np.cos(delta))))/15
    Sunset = 12 + math.degrees(np.arccos((-1*np.sin(Lat_rad)*np.sin(delta))/(np.cos(Lat_rad)*np.cos(delta))))/15

    if (Hour > Sunrise) and (Hour < Sunset):
        Ps = (1.2*E0*dr)*(math.sin(Lat_rad)*math.sin(delta) + math.cos(Lat_rad)*math.cos(delta)*math.cos(omega_s))
    else:
        Ps = 0

    return Ps #Units of W/m2

#-- Function for calculating H2 Electrolysis generation (kg/hr) --
def H2Prod(Power_MWh):
    #An electrolyzer produces approximately 0.162kg H2/kWh
    H2_kgperhr = Power_MWh*16.4 #Power is coming in as MWh so needs 1000 to convert
    H2_tonperhr = H2_kgperhr/1000
    return H2_tonperhr

#-- Kirmani 2015 Correlation for Weather effects on Solar Irradiance --
def KirmaniEff(WindSpeed_kmperhr, Temp_C, RH_Percent):
    K = 1- 0.02914*WindSpeed_kmperhr -0.0076*Temp_C - 0.00705*RH_Percent
    return K