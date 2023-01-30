# Renewable Hydrogen Calculator

Uses an hourly SQL weather dataset for North American cities covering 2013-2016 to calculate Wind and Solar power + Hydrogen electrolysis generation potential. 

## Description

Select cities to see estimates of Wind power generation potential for each. The windmill height and rotor radius used in calculations can be changed and must be updated before selecting the city marker. 

![StartMap_WindData](/ReadMeImages/WindMap_Cities.png?raw=true)

Within each city tab, wind power generation potential has been calculated using hourly wind velocities.

![CityTab_WindData](/ReadMeImages/WindData.png?raw=true)

Toggling the map page to Solar switches the city markers to link to Solar power calculations. As with the Wind power map, important parameters including the Total Panel Surface Area and PV Efficiency can be altered and must be updated to change the results for each city. 

![StartMap_SolarData](/ReadMeImages/SolarMap_Cities.png?raw=true)

An estimate of Direct Solar Irradiance (W/m2) is computed for each day based on the latitude of each city, which is then altered using a modified form of the Kirmani 2015 weather correction to estimate the amount of incident solar energy shining on a horizontal solar panel. 

![CityTab_SolarData](/ReadMeImages/SolarData.png?raw=true)
