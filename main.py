import customtkinter as ctk
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import ticker  # This is necessary to turn off scientific notation on graphs
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkintermapview import TkinterMapView
import seaborn as sns
import sqlite3

from H2AppFunctions import P_wind, P_solar, H2Prod, KirmaniEff


# <editor-fold desc="-- Prepare all data + containers (Pandas + Numpy) --">

weather_database = "Datasets/weather.sqlite"
conn = sqlite3.connect(weather_database)
city_latlong = pd.read_sql_query("SELECT * FROM latlong", conn)
city_windspeed = pd.read_sql_query("SELECT * FROM windspeed", conn)
city_temperature = pd.read_sql_query("SELECT * FROM temperature", conn)
city_humidity = pd.read_sql_query("SELECT * FROM humidity", conn)

windspeed_byYear = city_windspeed.groupby(city_windspeed.Year)
# Convert to numpy for more customizable matplotlib + function calls
WindspeedData = np.zeros([8784, 34, 4]) #First index is hours/leap year, Middle index is 4 datetime columns + 30 cities, Last index is year 0 = 2013, etc
WindspeedData[:8760,:, 0] = windspeed_byYear.get_group(2013).to_numpy()
WindspeedData[:8760,:, 1] = windspeed_byYear.get_group(2014).to_numpy()
WindspeedData[:8760,:, 2] = windspeed_byYear.get_group(2015).to_numpy()
WindspeedData[:,:, 3] = windspeed_byYear.get_group(2016).to_numpy()
Windpower = np.zeros([WindspeedData.shape[0], 4])
WindH2 = np.zeros([WindspeedData.shape[0], 4])
WindH2Avg = np.zeros(WindspeedData.shape[0])
WindH2StdDev = np.zeros(WindspeedData.shape[0])
Solarpower = np.zeros([WindspeedData.shape[0], 4])
SolarH2 = np.zeros([WindspeedData.shape[0], 4])
SolarH2Avg = np.zeros(WindspeedData.shape[0])
SolarH2StdDev = np.zeros(WindspeedData.shape[0])
SolarIrradianceSolstice = np.zeros(24) #This container is used to generate the daily solar trend graph
SolarIrradianceWithWeather = np.zeros(24) #This includes Kirmani 2015 Weather correction correlation
temperature_byYear = city_windspeed.groupby(city_temperature.Year)
TemperatureData = np.zeros([WindspeedData.shape[0], 34, 4]) #Middle index is 4 datetime columns + 30 cities, Last index is year 0 = 2013, etc
TemperatureData[:8760,:, 0] = temperature_byYear.get_group(2013).to_numpy()
TemperatureData[:8760,:, 1] = temperature_byYear.get_group(2014).to_numpy()
TemperatureData[:8760,:, 2] = temperature_byYear.get_group(2015).to_numpy()
TemperatureData[:,:, 3] = temperature_byYear.get_group(2016).to_numpy()
humidity_byYear = city_windspeed.groupby(city_humidity.Year)
HumidityData = np.zeros([WindspeedData.shape[0], 34, 4])
HumidityData[:8760,:, 0] = humidity_byYear.get_group(2013).to_numpy()
HumidityData[:8760,:, 1] = humidity_byYear.get_group(2014).to_numpy()
HumidityData[:8760,:, 2] = humidity_byYear.get_group(2015).to_numpy()
HumidityData[:,:, 3] = humidity_byYear.get_group(2016).to_numpy()
# </editor-fold>


FONT = ("Helvetica", 14)
APP_NAME = "Green Hydrogen Calculator"
WIDTH = 1200
HEIGHT = 750


class App:
    def __init__(self, master):
        ctk.set_appearance_mode("dark")
        self.master = master

        self.master.title(APP_NAME)
        self.master.geometry(str(WIDTH) + "x" + str(HEIGHT))
        self.master.minsize(WIDTH, HEIGHT)

        self.WindStartMap()

    def WindStartMap(self):
        for i in self.master.winfo_children():
            i.destroy()
        self.marker_list = []

        try: #This checks if height has been defined at all
            self.height = self.height #This allows app to keep values once changed by user
        except Exception as ex:
            self.Set_WindmillHeight(80) # If not, initialize parameter values
        try:
            self.radius = self.radius
        except Exception as ex:
            self.Set_WindmillRadius(60)  # Initialize parameter values

        # ----- Create Two CTkFrames -----

        self.master.grid_columnconfigure(0, weight=0)
        self.master.grid_columnconfigure(1, weight=1)
        self.master.grid_rowconfigure(0, weight=1)

        self.frame_left = ctk.CTkFrame(master=self.master, width=150, corner_radius=0, fg_color=None)
        self.frame_left.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

        self.frame_right = ctk.CTkFrame(master=self.master, corner_radius=0)
        self.frame_right.grid(row=0, column=1, rowspan=1, pady=0, padx=0, sticky="nsew")

        # ----- Left side of Frame -----

        self.frame_left.grid_rowconfigure(20, weight=1)

        self.button_1 = ctk.CTkSegmentedButton(master=self.frame_left,
                                               values=["Wind", "Solar"],
                                               command=self.ChangeRenewableMap,
                                               font = FONT)
        self.button_1.set("Wind")  # Set Wind as the initially selected value
        self.button_1.pack(padx=20, pady=10)
        self.button_1.grid(pady=(20, 0), padx=(20, 20), row=0, column=0)

        self.heightheader = ctk.CTkLabel(self.frame_left, text="Windmill Height (m)", font = FONT, text_color = '#FFFFFF')
        self.heightheader.grid(row=1, column=0, padx=20, pady=(10,0))

        self.heightinput = ctk.CTkEntry(master=self.frame_left, placeholder_text=self.height,justify='center', font = FONT, fg_color="#1F6AA5")
        self.heightinput.grid(row=2, column=0, padx=20, pady=10)

        self.radiusheader = ctk.CTkLabel(self.frame_left, text="Rotor Radius (m)", font = FONT, text_color = '#FFFFFF')
        self.radiusheader.grid(row=3, column=0, padx=20, pady=(10,0))

        self.radiusinput = ctk.CTkEntry(master=self.frame_left, placeholder_text=self.radius,justify='center', font = FONT, fg_color="#1F6AA5")
        self.radiusinput.grid(row=4, column=0, padx=20, pady=10)

        self.WindMapUpdate = ctk.CTkButton(master=self.frame_left,text="Update Parameters", command = self.UpdateWindmillParams)
        self.WindMapUpdate.grid(row=5, column=0, padx=20, pady=10)
        # ----- Right side of Frame -----

        self.frame_right.grid_rowconfigure(1, weight=1)
        self.frame_right.grid_rowconfigure(0, weight=0)
        self.frame_right.grid_columnconfigure(0, weight=1)
        self.frame_right.grid_columnconfigure(1, weight=0)
        self.frame_right.grid_columnconfigure(2, weight=1)

        self.map_widget = TkinterMapView(self.frame_right, corner_radius=0)
        self.map_widget.grid(row=1, rowspan=1, column=0, columnspan=3, sticky="nswe", padx=(0, 0), pady=(0, 0))

        # Initialize default values -> Using Lebanon, Kansas centers the map to USA
        self.map_widget.set_address("Lebanon, Kansas")
        self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=5)

        self.InitializeWindMarkers()

        def on_closing(self, event=0):
            self.destroy()

    def Set_WindmillHeight(self,value):
        self.height = value

    def Set_WindmillRadius(self, value):
        self.radius = value

    def UpdateWindmillParams(self):
        heightinputText = self.heightinput.get()
        radiusinputText = self.radiusinput.get()
        print('Button pressed')
        try:
            self.height = float(heightinputText)
            print(self.height)
        except Exception as ex:
            print('Trying to execute before value is set')
        try:
            self.radius = float(radiusinputText)
            print(self.radius)
        except Exception as ex:
            print('Trying to execute before value is set')

    def SolarStartMap(self):
        for i in self.master.winfo_children():
            i.destroy()
        self.marker_list = []

        try: #This checks if parameters has been defined at all
            self.Area = self.Area #This allows app to keep values once changed by user
        except Exception as ex:
            self.Set_PanelArea(1) # If not, initialize parameter values
        try:
            self.Efficiency = self.Efficiency
        except Exception as ex:
            self.Set_PVEfficiency(0.2)  # Initialize parameter values

        # ----- Create Two CTkFrames -----

        self.master.grid_columnconfigure(0, weight=0)
        self.master.grid_columnconfigure(1, weight=1)
        self.master.grid_rowconfigure(0, weight=1)

        self.frame_left = ctk.CTkFrame(master=self.master, width=150, corner_radius=0, fg_color=None)
        self.frame_left.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

        self.frame_right = ctk.CTkFrame(master=self.master, corner_radius=0)
        self.frame_right.grid(row=0, column=1, rowspan=1, pady=0, padx=0, sticky="nsew")

        # ----- Left banner of Frame ----

        self.frame_left.grid_rowconfigure(20, weight=1)

        self.button_1 = ctk.CTkSegmentedButton(master=self.frame_left,
                                               values=["Wind", "Solar"],
                                               command=self.ChangeRenewableMap)
        self.button_1.set("Solar")  # Set Wind as the initially selected value
        self.button_1.pack(padx=20, pady=10)
        self.button_1.grid(pady=(20, 0), padx=(20, 20), row=0, column=0)

        self.heightheader = ctk.CTkLabel(self.frame_left, text="Panel Area (m2)", font=FONT, text_color='#FFFFFF')
        self.heightheader.grid(row=1, column=0, padx=20, pady=(10, 0))

        self.areainput = ctk.CTkEntry(master=self.frame_left, placeholder_text=self.Area, justify='center', font=FONT,fg_color="#1F6AA5")
        self.areainput.grid(row=2, column=0, padx=20, pady=10)

        self.efficiencyheader = ctk.CTkLabel(self.frame_left, text="PV Efficiency (%)", font=FONT, text_color='#FFFFFF')
        self.efficiencyheader.grid(row=3, column=0, padx=20, pady=(10, 0))

        self.efficiencyinput = ctk.CTkSlider(master=self.frame_left, from_ = 15, to = 25, number_of_steps=100,fg_color="#1F6AA5")
        self.efficiencyinput.grid(row=4, column=0, padx=20, pady=10)

        self.SolarMapUpdate = ctk.CTkButton(master=self.frame_left,text="Update Parameters", command = self.UpdateSolarParams)
        self.SolarMapUpdate.grid(row=5, column=0, padx=20, pady=10)
        # ----- Right side of Frame -----

        self.frame_right.grid_rowconfigure(1, weight=1)
        self.frame_right.grid_rowconfigure(0, weight=0)
        self.frame_right.grid_columnconfigure(0, weight=1)
        self.frame_right.grid_columnconfigure(1, weight=0)
        self.frame_right.grid_columnconfigure(2, weight=1)

        self.map_widget = TkinterMapView(self.frame_right, corner_radius=0)
        self.map_widget.grid(row=1, rowspan=1, column=0, columnspan=3, sticky="nswe", padx=(0, 0), pady=(0, 0))

        # Initialize default values
        self.map_widget.set_address("Lebanon, Kansas")
        self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=5)
        self.InitializeSolarMarkers()


        def on_closing(self, event=0):
            self.destroy()

    def ChangeRenewableMap(self, Value):
        if Value == "Solar":
            self.SolarStartMap()
        else:
            self.WindStartMap()

    def InitializeWindMarkers(self):
        self.clear_marker_event() #Reset the markers every time this is called
        self.UpdateWindmillParams()
        for i in range(0, city_latlong.shape[0]):
            self.marker_list.append(
                self.map_widget.set_marker(city_latlong.at[i, "Latitude"], city_latlong.at[i, "Longitude"],
                                           text=city_latlong.at[i, "City"], text_color="#FFFFFF", font=FONT, marker_color_outside = "#8396A8", marker_color_circle = "#00144A"))
            self.Set_WindMarker_Command(i)  # For some reason, turning this into a separate function helps avoid Lambda/functional programming from making all cities = Last city (Boston)

    def Set_WindMarker_Command(self, int):
        self.marker_list[int].command = lambda x: self.WindPowerPage(int)
        # self.marker_list[int].command = lambda x: self.WindPowerPage(city_latlong.at[int, "City"])

    def Set_PanelArea(self,value):
        self.Area = value

    def Set_PVEfficiency(self, value):
        self.Efficiency = value

    def UpdateSolarParams(self):
        areainputText = self.areainput.get()
        efficiencyinputText = self.efficiencyinput.get()
        print('Button pressed')
        try:
            self.Area = float(areainputText)
            print(self.Area)
        except Exception as ex:
            print('Trying to execute before value is set')
        try:
            self.Efficiency = float(efficiencyinputText)
            print(self.Efficiency)
        except Exception as ex:
            print('Trying to execute before value is set')

    def InitializeSolarMarkers(self):
        for i in range(0, city_latlong.shape[0]):
            self.UpdateSolarParams()
            self.marker_list.append(
                self.map_widget.set_marker(city_latlong.at[i, "Latitude"], city_latlong.at[i, "Longitude"],
                                           text=city_latlong.at[i, "City"], text_color="#FFFFFF", font=FONT, marker_color_outside = "#FFB300", marker_color_circle = "#A93E00"))
            self.Set_SolarMarker_Command(i)  # For some reason, turning this into a separate function helps avoid Lambda/functional programming from making all cities = Last city (Boston)

    def Set_SolarMarker_Command(self, int):
        self.marker_list[int].command = lambda x: self.SolarPowerPage(int)
        #self.marker_list[int].command = lambda x: self.SolarPowerPage(city_latlong.at[int, "City"])

    def clear_marker_event(self):
        for marker in self.marker_list:
            marker.delete()

    def on_closing(self, event=0):
        self.destroy()

    def WindPowerPage(self, cityNum):
        for i in self.master.winfo_children():
            i.destroy()

        height = self.height
        radius = self.radius

        cityName = city_latlong.iat[cityNum, 0]

        for i in range(1, WindspeedData.shape[0]):  # Perform calculations for Windpower and H2 evolution
            if i < 8760:  # 2016 is a leap year so need to check if loop has extended past end of other arrays
                Windpower[i,0] = Windpower[i - 1,0] + P_wind(radius, height, WindspeedData[i, (cityNum + 4),0]) / 1000000  # Convert to MWh
                Windpower[i,1] = Windpower[i - 1,1] + P_wind(radius, height,WindspeedData[i, (cityNum + 4),1]) / 1000000
                Windpower[i,2] = Windpower[i - 1,2] + P_wind(radius, height,WindspeedData[i, (cityNum + 4),2]) / 1000000
                WindH2[i,0] = WindH2[i - 1,0] + H2Prod((Windpower[i,0] - Windpower[i-1,0]))  # ton/hr H2 production by Electrolysis
                WindH2[i,1] = WindH2[i - 1,1] + H2Prod((Windpower[i,1] - Windpower[i - 1,1]))
                WindH2[i,2] = WindH2[i - 1,2] + H2Prod((Windpower[i,2] - Windpower[i - 1,2]))
            else: #Need to pass non leapyear values forward to avoid graph dropping to zero
                Windpower[i, 0] = Windpower[i-1,0]
                Windpower[i, 1] = Windpower[i - 1, 1]
                Windpower[i, 2] = Windpower[i - 1, 2]
            Windpower[i,3] = Windpower[i - 1,3] + P_wind(radius, height, WindspeedData[i, (cityNum + 4),3]) / 1000000
            WindH2[i,3] = WindH2[i - 1,3] + H2Prod((Windpower[i,3] - Windpower[i - 1,3]))
            if i < 8760:
                WindH2Avg[i] = (WindH2[i,0] + WindH2[i,1] + WindH2[i,2] + WindH2[i,3]) / 4
                WindH2StdDev[i] = np.sqrt(((WindH2[i,0]-WindH2Avg[i])**2 + (WindH2[i,1]-WindH2Avg[i])**2 + (WindH2[i,2]-WindH2Avg[i])**2 + (WindH2[i,3]-WindH2Avg[i])**2) /4)
            else:
                WindH2Avg[i] = WindH2Avg[i - 1]  # Continue the last leap day
                WindH2StdDev[i] = WindH2StdDev[i-1]

        # ------ Create Two CTkFrames -------
        self.master.grid_columnconfigure(0, weight=0)
        self.master.grid_columnconfigure(1, weight=1)
        self.master.grid_rowconfigure(0, weight=1)

        self.frame_left = ctk.CTkFrame(master=self.master, width=150, corner_radius=0, fg_color=None)
        self.frame_left.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

        self.frame_right = ctk.CTkFrame(master=self.master, corner_radius=0)
        self.frame_right.grid(row=0, column=1, rowspan=1, pady=0, padx=0, sticky="nsew")

        # ----- Left banner of Frame --------

        self.frame_left.grid_rowconfigure(20, weight=1)

        self.header = ctk.CTkLabel(self.frame_left, text="Parameters", font = ('Helvetica', 16, 'bold', 'underline'), text_color = '#FFFFFF')
        self.header.grid(row=1, column=1, padx=20, pady=(10,0))

        self.reg_txt = ctk.CTkLabel(self.frame_left, text= "Windmill height = " + str(height) + "m", font=('Helvetica', 14))
        self.reg_txt.grid(row=2, column=1, padx=20, pady=0)

        self.reg_txt = ctk.CTkLabel(self.frame_left, text= "Rotor radius = " + str(radius) + "m", font=('Helvetica', 14))
        self.reg_txt.grid(row=3, column=1, padx=20, pady=0)

        self.button_1 = ctk.CTkButton(master=self.frame_left,
                                      text="Return to Map",
                                      command=self.WindStartMap)
        #Moving this button to Row 25 while making rowconfigure=20 seems necessary to move this button to very bottom
        self.button_1.grid(row=25, column=1, padx=20, pady=10)

        # ------ Right side of Frame ------

        fig, ax = plt.subplots(nrows=2, ncols=2, figsize=(11, 7.75), dpi=144, facecolor='#000000')
        fig.suptitle(cityName + " - Wind Power Data", fontsize=18, color='white')
        fig.tight_layout()  # This prevents subplot titles from overlapping with xlabel
        plt.subplots_adjust(top=0.9, wspace = 0.2, hspace=0.25, left = 0.075, bottom = 0.1, right = 0.95) #This helps separate subplots from supertitle
        plt.subplot(221)
        plt.title('Raw Time Series - Wind Velocity', color='white')
        ax[0, 0].plot(WindspeedData[:, (cityNum + 4),0], 'o', color='#2CBDFE', label='2013')
        ax[0, 0].plot(WindspeedData[:, (cityNum + 4),1], 'H', color='#5986E4', label='2014')
        ax[0, 0].plot(WindspeedData[:, (cityNum + 4),2], 'h', color='#8D46C7', label='2015')
        ax[0, 0].plot(WindspeedData[:, (cityNum + 4),3], '.', color='#B317B1', label='2016')
        ax[0, 0].set_xlabel("Hours in Year", color='white')
        ax[0, 0].set_ylabel("Wind Velocity (m/s)", color='white')
        ax[0, 0].grid(color='white', alpha=0.4, linestyle='--')
        plt.xticks(color='white')
        plt.yticks(color='white')
        ax[0, 0].set_facecolor('#121212')
        plt.gca().legend(loc='upper right')
        plt.subplot(222)  # Violin plot showing Wind speed distribution per year
        plt.title('Wind Speed Distributions', color='white')
        xpos = [2013, 2014, 2015, 2016]  # X-axis positions
        ViolinDataCol = [WindspeedData[:, (cityNum + 4),0], WindspeedData[:, (cityNum + 4),1],
                         WindspeedData[:, (cityNum + 4),2], WindspeedData[:, (cityNum + 4),3]]
        violin_parts = ax[0, 1].violinplot(ViolinDataCol, xpos, widths=0.75, showmeans=True)
        temp = 0
        for vp in violin_parts['bodies']:  # This is necessary to change the violin colours to darkmode colour scheme
            vp.set_edgecolor('#FFFFFF')
            vp.set_alpha(0.5)
            if temp == 0:
                vp.set_facecolor('#2CBDFE')
            elif temp == 1:
                vp.set_facecolor('#5986E4')
            elif temp == 2:
                vp.set_facecolor('#8D46C7')
            elif temp == 3:
                vp.set_facecolor('#B317B1')
            temp = temp + 1;  # Create a dummy variable to iterate through violin parts
        ax[0, 1].set_ylabel("Wind Velocity (m/s)", color='white')
        ax[0, 1].set_ylim(0, 15)
        plt.xticks([2013, 2014, 2015, 2016], color='white')
        plt.yticks(color='white')
        ax[0, 1].grid(color='white', alpha=0.15, linestyle='--')
        ax[0, 1].set_facecolor('#121212')
        plt.subplot(223)  # Cumulative Wind power produced per year
        plt.title('Cumulative Wind Power Produced', color='white')
        ax[1, 0].plot(Windpower[:,0], color='#2CBDFE', label='2013')
        ax[1, 0].plot(Windpower[:,1], color='#5986E4', label='2014')
        ax[1, 0].plot(Windpower[:,2], color='#8D46C7', label='2015')
        ax[1, 0].plot(Windpower[:,3], color='#B317B1', label='2016')
        ax[1, 0].set_xlabel("Hours in Year", color='white')
        ax[1, 0].set_ylabel("Cumulative Wind Power Generated (MWh)", color='white')
        #plt.gca().yaxis.set_major_formatter(ticker.ScalarFormatter())
        #plt.gca().yaxis.set_major_formatter(ticker.StrMethodFormatter("{x}"))
        #ax[1, 0].set_yticklabels(plt.yticks()[0].astype(int))  # Removes decimal from number
        ax[1, 0].grid(color='white', alpha=0.15, linestyle='--')
        plt.xticks(color='white')
        plt.yticks(color='white')
        plt.gca().legend(loc='upper left')
        ax[1, 0].set_facecolor('#121212')
        plt.subplot(224)  # Cumulative Wind power produced per year
        plt.title('Cumulative Hydrogen Electrolyzed', color='white')
        ax[1, 1].plot(WindH2Avg, color='#018786')
        plt.fill_between(np.arange(0, WindH2Avg.shape[0]), WindH2Avg - 2*WindH2StdDev, WindH2Avg + 2*WindH2StdDev, color="#03DAC6", alpha = 0.15) #This creates std dev
        ax[1, 1].set_xlabel("Hours in Year", color='white')
        ax[1, 1].set_ylabel("Cumulative Hydrogen Generated (tonnes)", color='white')
        #plt.gca().yaxis.set_major_formatter(ticker.ScalarFormatter())
        #plt.gca().yaxis.set_major_formatter(ticker.StrMethodFormatter("{x}"))
        #ax[1, 1].set_yticklabels(plt.yticks()[0].astype(int))  # Removes decimal from number
        ax[1, 1].grid(color='white', alpha=0.15, linestyle='--')
        plt.xticks(color='white')
        plt.yticks(color='white')
        ax[1, 1].set_facecolor('#121212')

        canvas = FigureCanvasTkAgg(fig, master=root) #These are necessary to actually render Matplotlib graphs
        canvas.draw()
        canvas.get_tk_widget().place(relx=0.15, rely=0.0)

    def SolarPowerPage(self, cityNum):
        for i in self.master.winfo_children():
            i.destroy()
        cityName = city_latlong.iat[cityNum, 0]

        Efficiency = self.Efficiency/100
        PanelArea = self.Area

        for i in range(1, WindspeedData.shape[0]):  # Perform calculations for Windpower and H2 evolution
            if i < 8760:  # 2016 is a leap year so need to check if loop has extended past end of other arrays
                #Using the Day/Hour from Windpower dataset, divide by 1000 to get kWh
                #Convert wind speed in Kirmani 2015 weather correlation from m/s to km/hr
                Solarpower[i,0] = Solarpower[i-1,0] + (Efficiency*PanelArea*P_solar(city_latlong.iat[cityNum, 2], int(i/24)+1, WindspeedData[i,3,0])/1000)*KirmaniEff(WindspeedData[i, (cityNum + 4),0]*3.6,TemperatureData[i,(cityNum + 4),0],HumidityData[i,(cityNum + 4),0])
                Solarpower[i,1] = Solarpower[i-1,1] + (Efficiency*PanelArea*P_solar(city_latlong.iat[cityNum, 2],int(i/24)+1, WindspeedData[i,3,1])/1000)*KirmaniEff(WindspeedData[i, (cityNum + 4),1]*3.6,TemperatureData[i,(cityNum + 4),1],HumidityData[i,(cityNum + 4),1])
                Solarpower[i,2] = Solarpower[i-1,2] + (Efficiency*PanelArea*P_solar(city_latlong.iat[cityNum, 2],int(i/24)+1, WindspeedData[i,3,2])/1000)*KirmaniEff(WindspeedData[i, (cityNum + 4),2]*3.6,TemperatureData[i,(cityNum + 4),2],HumidityData[i,(cityNum + 4),2])
                SolarH2[i,0] = SolarH2[i - 1,0] + H2Prod((Solarpower[i,0] - Solarpower[i - 1,0]))
                SolarH2[i,1] = SolarH2[i - 1,1] + H2Prod((Solarpower[i,1] - Solarpower[i - 1,1]))
                SolarH2[i,2] = SolarH2[i - 1,2] + H2Prod((Solarpower[i,2] - Solarpower[i - 1,2]))
                if (i >= 4105) and (i <= 4128): #This generates the daily solar irradiance trend for summer solstice = Day 172 June 21st
                    SolarIrradianceSolstice[i-4105] = P_solar(city_latlong.iat[cityNum, 2],172, WindspeedData[i,3,2])
                    SolarIrradianceWithWeather[i - 4105] = P_solar(city_latlong.iat[cityNum, 2], 172,WindspeedData[i, 3,2])*KirmaniEff(WindspeedData[i, (cityNum + 4),2]*3.6,TemperatureData[i,(cityNum + 4),3],HumidityData[i,(cityNum + 4),3])
            else: #Need to pass non-leap year values forward to avoid graphs dropping to zero
                Solarpower[i, 0] = Solarpower[i-1, 0]
                Solarpower[i, 1] = Solarpower[i - 1, 1]
                Solarpower[i, 2] = Solarpower[i - 1, 2]
            Solarpower[i,3] = Solarpower[i-1,3] + (Efficiency*PanelArea*P_solar(city_latlong.iat[cityNum, 2],int(i/24)+1, WindspeedData[i,3,3])/1000)*KirmaniEff(WindspeedData[i, (cityNum + 4),3]*3.6,TemperatureData[i,(cityNum + 4),3],HumidityData[i,(cityNum + 4),3])
            SolarH2[i,3] = SolarH2[i - 1,3] + H2Prod((Solarpower[i,3] - Solarpower[i - 1,3]))
            if i < 8760:
                SolarH2Avg[i] = (SolarH2[i,0] + SolarH2[i,1] + SolarH2[i,2] + SolarH2[i,3]) / 4
                SolarH2StdDev[i] = np.sqrt(((SolarH2[i,0]-SolarH2Avg[i])**2 + (SolarH2[i,1]-SolarH2Avg[i])**2 + (SolarH2[i,2]-SolarH2Avg[i])**2 + (SolarH2[i,3]-SolarH2Avg[i])**2) /4)
            else:
                SolarH2Avg[i] = SolarH2Avg[i - 1]  # Continue the last leap day
                SolarH2StdDev[i] = SolarH2StdDev[i-1]

        # ----- Create Two CTKFrames -----
        self.master.grid_columnconfigure(0, weight=0)
        self.master.grid_columnconfigure(1, weight=1)
        self.master.grid_rowconfigure(0, weight=1)

        self.frame_left = ctk.CTkFrame(master=self.master, width=150, corner_radius=0, fg_color=None)
        self.frame_left.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

        self.frame_right = ctk.CTkFrame(master=self.master, corner_radius=0)
        self.frame_right.grid(row=0, column=1, rowspan=1, pady=0, padx=0, sticky="nsew")

        # ------ Left banner of Frame -----
        self.frame_left.grid_rowconfigure(20, weight=1)

        self.header = ctk.CTkLabel(self.frame_left, text="Parameters", font = ('Helvetica', 16, 'bold', 'underline'), text_color = '#FFFFFF')
        self.header.grid(row=1, column=1, padx=20, pady=(10,0))

        self.reg_txt = ctk.CTkLabel(self.frame_left, text= "Panel Area = " + str(PanelArea) + "m2", font = ('Helvetica', 14))
        self.reg_txt.grid(row=2, column=1, padx=20, pady=0)

        self.reg_txt = ctk.CTkLabel(self.frame_left, text= "PV Efficiency = " + str(100*Efficiency) + "%", font= ('Helvetica', 14))
        self.reg_txt.grid(row=3, column=1, padx=20, pady=0)

        self.button_1 = ctk.CTkButton(master=self.frame_left,
                                      text="Return to Map",
                                      command=self.SolarStartMap)
        self.button_1.grid(row=25, column=1, padx=20, pady=10)

        # ------ Right panel of Frame -----
        fig, ax = plt.subplots(nrows=2, ncols=2, figsize=(11, 7.75), dpi=144, facecolor='#000000')
        fig.suptitle(cityName + " - Solar Power Data", fontsize=18, color='white')
        fig.tight_layout()  # This prevents subplot titles from overlapping with xlabel
        plt.subplots_adjust(top=0.9, wspace = 0.2, hspace=0.25, left = 0.075, bottom = 0.1, right = 0.95) #This helps separate subplots from supertitle
        plt.subplot(221)
        ax[0,0].plot(SolarIrradianceSolstice, color='#FF5700', label='No Weather Correction')
        ax[0, 0].plot(SolarIrradianceWithWeather, color='#FFD700', label='Kirmani 2015 Weather Correction')
        ax[0, 0].grid(color='white', alpha=0.4, linestyle='--')
        plt.xticks(color='white')
        plt.yticks(color='white')
        ax[0, 0].set_facecolor('#121212')
        plt.gca().legend(loc='lower left')
        ax[0, 0].set_ylabel("Irradiance (W/m2)", color='white')
        ax[0, 0].set_xlabel("Hours", color='white')
        plt.title('Summer Solstice Solar Irradiance', color='white')
        plt.subplot(222)
        plt.title('Relative Humidity Distribution', color='white')
        sns.kdeplot(HumidityData[:,(cityNum+4), 0], color='#2CBDFE', fill=True,alpha = 0.3, linewidth = 0, label='2013')
        sns.kdeplot(HumidityData[:, (cityNum + 4), 1], color='#5986E4', fill=True, alpha=0.3, linewidth=0, label='2014')
        sns.kdeplot(HumidityData[:, (cityNum + 4), 2], color='#8D46C7', fill=True, alpha=0.3, linewidth=0, label='2015')
        sns.kdeplot(HumidityData[:, (cityNum + 4), 3], color='#B317B1', fill=True, alpha=0.3, linewidth=0, label='2016')
        ax[0, 1].set_xlabel("Relative Humidity (%)", color='white')
        ax[0, 1].set_ylabel("Frequency Density", color='white')
        ax[0, 1].grid(color='white', alpha=0.4, linestyle='--')
        ax[0,1].set_xticklabels([0,20,40,60,80,100])
        ax[0,1].set_xlim(0,10)
        plt.xticks(color='white')
        plt.yticks(color='white')
        ax[0, 1].set_facecolor('#121212')
        plt.gca().legend(loc='upper right')
        plt.subplot(223)  # Cumulative Wind power produced per year
        plt.title('Cumulative Solar Power Produced', color='white')
        ax[1, 0].plot(Solarpower[:,0], color='#2CBDFE', label='2013')
        ax[1, 0].plot(Solarpower[:,1], color='#5986E4', label='2014')
        ax[1, 0].plot(Solarpower[:,2], color='#8D46C7', label='2015')
        ax[1, 0].plot(Solarpower[:,3], color='#B317B1', label='2016')
        ax[1, 0].set_xlabel("Hours in Year", color='white')
        ax[1, 0].set_ylabel("Cumulative Wind Power Generated (MWh)", color='white')
        #plt.gca().yaxis.set_major_formatter(ticker.ScalarFormatter())
        #plt.gca().yaxis.set_major_formatter(ticker.StrMethodFormatter("{x}"))
        #ax[1, 0].set_yticklabels(plt.yticks()[0].astype(int))  # Removes decimal from number
        ax[1, 0].grid(color='white', alpha=0.15, linestyle='--')
        plt.xticks(color='white')
        plt.yticks(color='white')
        plt.gca().legend(loc='upper left')
        ax[1, 0].set_facecolor('#121212')
        plt.subplot(224)  # Cumulative Wind power produced per year
        plt.title('Cumulative Hydrogen Electrolyzed', color='white')
        ax[1, 1].plot(SolarH2Avg, color='#018786')
        plt.fill_between(np.arange(0, SolarH2Avg.shape[0]), SolarH2Avg - 2*SolarH2StdDev, SolarH2Avg + 2*SolarH2StdDev, color="#03DAC6", alpha = 0.15) #This creates std dev
        ax[1, 1].set_xlabel("Hours in Year", color='white')
        ax[1, 1].set_ylabel("Cumulative Hydrogen Generated (tonnes)", color='white')
        #plt.gca().yaxis.set_major_formatter(ticker.ScalarFormatter())
        #plt.gca().yaxis.set_major_formatter(ticker.StrMethodFormatter("{x}"))
        #ax[1, 1].set_yticklabels(plt.yticks()[0].astype(int))  # Removes decimal from number
        ax[1, 1].grid(color='white', alpha=0.15, linestyle='--')
        plt.xticks(color='white')
        plt.yticks(color='white')
        ax[1, 1].set_facecolor('#121212')

        canvas = FigureCanvasTkAgg(fig, master=root) #These are necessary to actually render Matplotlib graphs
        canvas.draw()
        canvas.get_tk_widget().place(relx=0.15, rely=0.0)

# Driver Code
root = ctk.CTk()
app = App(root)
root.mainloop()