import pyqtgraph as pg
import numpy as np
from PyQt6 import QtCore , QtGui
from units import convert_array_to_unit
from scipy.optimize import brentq 
from utils import mapping
from windbarbs import WindBarbs
from sklearn.linear_model import LinearRegression

L = 2.501e6 # J/kg : latent heat of vaporization at 0°C (2.257 J/kg at 100°C)
Ra = 287.04  # J/kg : gas constant for dry air
Rv = 461.5  # J/kg : gas constant for water vapor
eps = Ra/Rv # =Mv/Ma = 0.622
cp = 1005. #J/kg/K
cv = 718. #J/kg/K
kappa = (cp-cv)/cp # kappa = (gamma-1)/gamma = 0.4/1.4 = 2/7 = 0.286
ezero = 6.112# hPa




class SkewTWidget:
    def __init__(self, plot_widget, label_gradient_1000, label_gradient_P, P_bot=1013.25, P_b=1013.25, P_t=300., dp=1):
        
        self.plot_widget = plot_widget
        self.gradient_label_1000 = label_gradient_1000
        self.gradient_label_P = label_gradient_P
        pg.setConfigOptions(antialias=True)
        self.P_bot = P_bot
        self.P_b = P_b
        self.P_t = P_t
        self.dp = dp
        self.plevs = np.arange(self.P_b, self.P_t - 1, -self.dp)
        self.cursor_x = 0
        self.cursor_y =1000 #default value for cursor 
        self._P_data_full = None
        
        self._legend = self.plot_widget.addLegend(
        offset=(10, -10),  # position par rapport au coin
        brush=pg.mkBrush(255, 255, 255, 220),  # fond blanc semi-transparent
        pen=pg.mkPen((200, 200, 200), width=1)  # bordure grise
    )
        
        self._current_flight = None #Used to keep track of which flight is being displayed
        
        #Windbarbs
        self.wind_barbs = WindBarbs(plot_widget)
        self.wind_barbs.P_bot = self.P_bot
        
        self.myregP = LinearRegression()
        self.myregT100 = LinearRegression()
        self.myregT1000 = LinearRegression()
        
        self._curves_isotherms = []
        self._curves_isobars = []
        self._curves_dry_adiabats = []
        self._curves_moist_adiabats = []
        self._curves_mixing_ratio = []
        
        self._isotherm_labels = []   
        self._mixing_labels = []
        self._visibility = { #Default visibility
         'isotherms': True,
         'isobars': False,
         'dry_adiabats': False,
         'moist_adiabats': False,
         'mixing_ratio': False,
     }
        
        self._setup_widget()
        self._draw_background()
        

    def _setup_widget(self):
        # self.plot_widget.clear()
        self.plot_widget.setBackground("w")
        self.plot_widget.getViewBox().invertY(True)
        self.plot_widget.setLabel("left", "Pressure (hPa)")
        self.plot_widget.setLabel("bottom", "Temperature (°C)")
        self.plot_widget.showGrid(x=False, y=True, alpha=0.4)
        self.plot_widget.setXRange(-25, 40, padding=0)
        #self.plot_widget.setLogMode(y=True)
    
        #initializing isotherm and isobar curves to empty , used as the skew  cursor
        self._curve_isotherm_cursor = self.plot_widget.plot([], [])
        self._curve_dry_adia_cursor = self.plot_widget.plot([], [])
        self._curve_isobar_cursor = pg.InfiniteLine(
            angle=0,                 # horizontale
            movable=False,
            pen=pg.mkPen((0,0,0,70), width=1)
        )
        
        self.plot_widget.addItem(self._curve_isobar_cursor)
        
        self.label_cursor_therm = pg.TextItem(text="°C", color=(180, 115, 51, 100), anchor=(0.3, 0), fill = pg.mkBrush(255, 255, 255, 180))
        self.plot_widget.addItem(self.label_cursor_therm)
        self.label_cursor_bar = pg.TextItem(text="hPa", color=(0,0,0,100), anchor=(0.5, 0), fill = pg.mkBrush(255, 255, 255, 180))
        self.plot_widget.addItem(self.label_cursor_bar)
        self.label_cursor_alt = pg.TextItem(text="m", color=(0,0,0,100), anchor=(0.5, 1), fill = pg.mkBrush(255, 255, 255, 180))
        self.plot_widget.addItem(self.label_cursor_alt)
        self.label_cursor_adia = pg.TextItem(text="m", color=(0, 180, 0, 100), anchor=(0.5, 1), fill = pg.mkBrush(255, 255, 255, 180))
        self.plot_widget.addItem(self.label_cursor_adia)
        # self.plot_widget.setYRange(self.P_t, self.P_b, padding=0)
        
        #Gradient 
        self._gradient_reg = self.plot_widget.plot([], [], pen=pg.mkPen(color=(212, 28, 163, 100), width=1, style=QtCore.Qt.PenStyle.SolidLine))
        self._gradient_reg.setVisible(False)
        self.gradient_label_1000.setVisible(False)
        self.gradient_label_P.setVisible(False)
        # Points déplaçables
        self._reg_handle_min = pg.TargetItem(
            pos=(0, 0),
            size=12,
            symbol='o',
            pen=pg.mkPen((255, 100, 0), width=2),
            brush=pg.mkBrush(255, 100, 0, 180),
            movable=True
        )
        self._reg_handle_min.setVisible(False)
        self._reg_handle_max = pg.TargetItem(
            pos=(0, 0),
            size=12,
            symbol='o',
            pen=pg.mkPen((255, 100, 0), width=2),
            brush=pg.mkBrush(255, 100, 0, 180),
            movable=True
        )
        self._reg_handle_max.setVisible(False)

        self._reg_point_min = None  # index dans le profil
        self._reg_point_max = None
            
        self.plot_widget.addItem(self._reg_handle_min)
        self.plot_widget.addItem(self._reg_handle_max)
        # Connexion native du drag
        self._reg_handle_min.sigPositionChanged.connect(self._on_handle_moved)
        self._reg_handle_max.sigPositionChanged.connect(self._on_handle_moved)
        self._updating_handles = False  # flag anti-récursion
        
        
        self.plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)
        self.plot_widget.getViewBox().sigRangeChanged.connect(self._update_labels_cursor)
        self.plot_widget.getViewBox().sigRangeChanged.connect(self._update_labels)
        self.plot_widget.getViewBox().sigRangeChanged.connect(self._update_windbarbs_display)
     
    def _draw_background(self):
        
        self._curves_isotherms = []
        # self._curves_isobars = []
        self._curves_dry_adiabats = []
        self._curves_moist_adiabats = []
        self._curves_mixing_ratio = []
    
        self._draw_isotherms(step=10)
        # self._draw_isobars(step=100)
        self._draw_dry_adiabats(step=10)
        self._draw_moist_adiabats(step=5)
        self._draw_mixing_ratio()
        
    def _draw_isotherms(self, step):
        #Remove previous curves and labels
        for c in self._curves_isotherms:
            self.plot_widget.removeItem(c)
        for label in self._isotherm_labels:
            self.plot_widget.removeItem(label)
        self._curves_isotherms = []
        self._isotherm_labels = []
        
        # Isothermes
        for temp in np.arange(-50, 50, step):
            x = temp + self.skewnessTerm(self.plevs, self.P_bot)
            color = (180, 115, 51, 70)
            style = QtCore.Qt.PenStyle.SolidLine
            c = self.plot_widget.plot(x, self.plevs, pen=pg.mkPen(color=color, width=1, style=style))
            self._curves_isotherms.append(c)
            
            label = pg.TextItem(text=f"{temp}°C", color=color, anchor=(0.5, 0), fill = pg.mkBrush(255, 255, 255, 180))
            label._temp_value = temp  # on stocke la valeur pour recalculer la position
            self.plot_widget.addItem(label)
            self._isotherm_labels.append(label)
        
        self._update_labels()
    
    # def _draw_isobars(self, step):
    #     for c in self._curves_isobars:
    #         self.plot_widget.removeItem(c)
    #     self._curves_isobars = []
    #     # # Isobares
    #     for n in np.arange(self.P_bot, self.P_t - 1, -step):
    #         c = self.plot_widget.plot([-40, 50], [n, n], pen=pg.mkPen(color=(0, 0, 0), width=0.5))
    #         self._curves_isobars.append(c)
            
    def _draw_dry_adiabats(self, step):
        for c in self._curves_dry_adiabats:
            self.plot_widget.removeItem(c)
        self._curves_dry_adiabats = []
        # # Adiabatiques sèches
        for tk in 273.15 + np.arange(-30, 60, step):
            dry = tk * (self.plevs / self.P_bot) ** kappa - 273.15 + self.skewnessTerm(self.plevs, self.P_bot)
            c = self.plot_widget.plot(dry, self.plevs, pen=pg.mkPen(color=(0, 180, 0, 70), width=0.75,
                                                            style=QtCore.Qt.PenStyle.SolidLine))
            self._curves_dry_adiabats.append(c)
            
    def _draw_moist_adiabats(self, step):
        for  c in self._curves_moist_adiabats:
            self.plot_widget.removeItem(c)
        self._curves_moist_adiabats = []   
        # # Adiabatiques saturées
        pen = QtGui.QPen(QtGui.QColor(52, 180, 235, 70))
        pen.setWidth(10)
        pen.setStyle(QtCore.Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        pen.setWidthF(0.5)              # plus épais
        pen.setDashPattern([8, 4])      # tirets plus longs
        ps = [p for p in self.plevs if p <= self.P_bot]
        for temp0 in np.arange(-30, 40, step):
            moist = []
            temp = temp0
        
            for p in ps:
                temp -= self.dp * self.gamma_s(temp, p * 100) * 100
                moist.append(temp + self.skewnessTerm(p, self.P_bot))
            
            c = self.plot_widget.plot(moist, ps, pen=pen)
            self._curves_moist_adiabats.append(c)
            
    def _draw_mixing_ratio(self):
        # # Rapport de mélange
        for ws in np.array([0.1,0.2,0.5,1,1.5,2,3,4,6,8,10,12,15,20,25,30,35,40,45]):#g/kg
            temp = self.ws_to_T(ws, self.plevs) + self.skewnessTerm(self.plevs, self.P_bot)
            c = self.plot_widget.plot(temp, self.plevs, pen=pg.mkPen(color=(255, 0, 255, 70), width=0.5,
                                                             style=QtCore.Qt.PenStyle.DashLine))
            self._curves_mixing_ratio.append(c)
            label = pg.TextItem(text=f"{ws} g/kg", color=(255, 0, 255, 70), anchor=(0.5, 0), fill = pg.mkBrush(255, 255, 255, 180))
            label._ws_value = ws  # on stocke la valeur pour recalculer la position
            self.plot_widget.addItem(label)
            self._mixing_labels.append(label)
        
        self._update_labels()

    def update(self, flight):
        """
        Update the sounding profiles dynamically.
        P_min / P_max : pressure bounds in hPa (P_min < P_max, ex: 800, 1050)
        """
        if self._current_flight is not None and self._current_flight is not flight:
            self._clear_flight_plots()
        self._current_flight = flight
        
        x_min =  int(flight['plot']['roi_emagram'].getRegion()[0])
        x_max =  int(flight['plot']['roi_emagram'].getRegion()[1])
        if x_min == x_max: 
            return
        #Formula to confirm the SkewT diagram is working
        # Tdry = np.subtract(np.add(np.subtract(300.4222, np.divide(np.multiply(6.3533, flight["data"]["GNSS_alt"][x_min : x_max] ),1000)), (np.multiply(0.005886, np.square(np.divide(flight["data"]["GNSS_alt"][x_min : x_max],1000 ))))), 273.15)
        # Tdew = np.full((x_max - x_min), 10)
        Tdry = flight["data"]["air_T"][x_min : x_max]
        Tdew = flight["data"]["AirTd"][x_min : x_max]
        P = np.multiply(flight["data"]["P_stat"][x_min : x_max], 0.01) #converting Pa to hPa
        P_full = np.multiply(flight["data"]["P_stat"], 0.01)
        Tdry_skewed = Tdry + self.skewnessTerm(P, self.P_bot)
        Tdew_skewed = Tdew + self.skewnessTerm(P, self.P_bot)
        #updating the range
        x_range_max = int(max(np.max(Tdry_skewed), np.max(Tdew_skewed))) + 3
        x_range_min = int(min(np.min(Tdry_skewed), np.min(Tdew_skewed))) -3
        y_range_max = int(np.max(P)) + 5
        y_range_min = int(np.min(P)) - 5
        
        self.plot_widget.setYRange(y_range_max, y_range_min)
        self.plot_widget.setXRange(x_range_min, x_range_max)   
        self.plot_widget.setLimits(
            xMin=x_range_min - (x_range_max - x_range_min)*0.5,
            xMax=x_range_max + (x_range_max - x_range_min)*0.5,
            yMin=y_range_min - (y_range_max - y_range_min)*0.2,
            yMax=y_range_max + (y_range_max - y_range_min)*0.2
        )
        
        if flight['plot']['scatter_emagram'][0] and flight['plot']['scatter_emagram'][1]: #if the scatters Tdew and Tdry item already exists
        
            flight['plot']['scatter_emagram'][0].setData(Tdry + self.skewnessTerm(P, self.P_bot), P)
            flight['plot']['scatter_emagram'][1].setData(Tdew + self.skewnessTerm(P, self.P_bot), P)
        else:
            # Create Curve temperature 
            flight['plot']['scatter_emagram'][0] = self.plot_widget.plot(
                Tdry + self.skewnessTerm(P, self.P_bot),
                P,
                pen=pg.mkPen(color=(255, 0, 0), width=1.5),
                name="T dry",
            )
            # Create Curve dew point
            flight['plot']['scatter_emagram'][1] = self.plot_widget.plot(
                Tdew + self.skewnessTerm(P, self.P_bot),
                P,
                pen=pg.mkPen(color=(0, 0, 0), width=1.5),
                name="T dew"
            )
            
            
        #Create windbarbs
        vb = self.plot_widget.getViewBox()
        x_range, y_range = vb.viewRange()
        x_min_range, x_max_range = x_range
        P = flight['data']['P_stat'][x_min : x_max]
        speed = flight['data']['wind_vel'][x_min : x_max]
        angle = flight['data']['wind_origin'][x_min : x_max]
        Xgraph = x_max_range - (x_max_range - x_min_range)*0.1 
        self.wind_barbs.update(P/100, speed, angle, Xgraph)
        self._update_windbarbs_display()
        self._P_data = P / 100 #converting from Pa to hPa
        self._P_data_full = P_full  #converting from Pa to hPa
        self._Tdry_data = Tdry
        self._calculate_linreg(self._P_data, self._Tdry_data)
    
    def _update_windbarbs_display(self):
        vb = self.plot_widget.getViewBox()
        x_range, y_range = vb.viewRange()
        x_min_range, x_max_range = x_range
        Xgraph = x_max_range - (x_max_range - x_min_range)*0.1 
        self.wind_barbs.update_pos(Xgraph)
    
    def _on_mouse_moved(self, pos):
        """
        This function calculates the initial condition for isotherm, isobar and dry adiabatique 
        for where the mouse is (pos)
        """
        vb = self.plot_widget.getViewBox()
        if not self.plot_widget.sceneBoundingRect().contains(pos):
            return
    
        mouse_point = vb.mapSceneToView(pos)
        T_mouse_unskewed = mouse_point.x()   
        P_mouse = mouse_point.y()
        if P_mouse > 0:
            P_mouse == 0.1 #Keeping the P positive 
        T_mouse_skewed = T_mouse_unskewed - self.skewnessTerm(P_mouse, self.P_bot)
        self.cursor_x = T_mouse_skewed
        self.cursor_y = P_mouse
        
        x = T_mouse_skewed + self.skewnessTerm(self.plevs, self.P_bot)
        color_therm = (180, 115, 51, 90)
        style_therm = QtCore.Qt.PenStyle.DashLine 

        self._curve_isotherm_cursor.setData(x, self.plevs, pen=pg.mkPen(color=color_therm, width=1, style=style_therm))
        self._curve_isobar_cursor.setValue(self.cursor_y)
        self._update_labels_cursor()
        
        Tk = (T_mouse_unskewed - self.skewnessTerm(P_mouse, self.P_bot) + 273.15) * (self.P_bot / P_mouse) ** kappa - 273.15
        # # Adiabatique sèche depuis T_mouse, P_mouse
        dry = (Tk + 273.15) * (self.plevs / self.P_bot) ** kappa - 273.15 + self.skewnessTerm(self.plevs, self.P_bot)
        self._curve_dry_adia_cursor.setData(dry, self.plevs , pen=pg.mkPen(color=(0, 180, 0, 90), width=0.5, style=QtCore.Qt.PenStyle.SolidLine))

        # # # Adiabatique saturée depuis T_mouse, P_mouse
        # T_init = self._find_moist_adiabat_T(T_mouse_unskewed, P_mouse) #We use a numerical inversion as gamma_s is non linear so non invertible
        # if T_init is not None:
        #     temp = T_init  
        #     moist_skewed = []
        #     ps = [p for p in self.plevs if p <= self.P_bot]
            
        #     for p in ps:
        #         temp -= self.dp * self.gamma_s(temp, p * 100) * 100  # ← temp mis à jour
        #         moist_skewed.append(temp + self.skewnessTerm(p, self.P_bot))
            
        #     self._curve_moist_adiabat.setData(moist_skewed, ps) 
    
    def skewnessTerm(self, P,P_bot):
        return 45 * (P_bot - P) / P_bot 
        # return 45 * np.log(P_bot/P)
    
    def gamma_s(self, T,p):
        """
        Calculates moist adiabatic lapse rate dT/dp for T (Celsius) and p (Pa)
        """
        a = 2./7.
        b = eps*L*L/(Ra*cp)
        c = a*L/Ra
        esat = ezero*100*np.exp(17.67*T/(T+243.5))
        wsat = eps*esat/(p-esat) # Rogers&Yau 2.18
        numer = a*(T+273.15) + c*wsat
        denom = p * (1 + b*wsat/((T+273.15)**2))
        return numer/denom # Rogers&Yau 3.16
    
    def ws_to_T(self, ws,P):
        """ Find T (°C) associated to a couple ws (g/kg), P (hPa) """
        esat = P*ws*1e-3/(eps+ws*1e-3)
        return 243.5 * np.log(esat/ezero)/(17.67-np.log(esat/ezero))


    def _find_moist_adiabat_T(self, T_mouse_unskewed, P_mouse):
        """
        Trouve T_init tel que l'adiabatique humide partant de (T_init, P_bot)
        passe par T_mouse_unskewed à P_mouse
        """
        def residual(T_init):
            # Intègre l'adiabatique humide de P_bot jusqu'à P_mouse
            temp = T_init
            plevs_integration = np.arange(self.P_bot, P_mouse - 1, -self.dp)
            for p in plevs_integration:
                temp -= self.dp * self.gamma_s(temp, p * 100) * 100
            # La valeur skewée à P_mouse
            T_skewed_at_P = temp + self.skewnessTerm(P_mouse, self.P_bot)
            return T_skewed_at_P - T_mouse_unskewed
    
        # Cherche T_init dans une plage raisonnable
        try:
            T_init = brentq(residual, -60, 50, xtol=0.01)
            return T_init
        except ValueError:
            return None
        
    def _update_labels_cursor(self):
        
        
        vb = self.plot_widget.getViewBox()
        x_range, y_range = vb.viewRange()
        x_min, x_max = x_range
        y_min, y_max = y_range  # y_min = P_t (haut), y_max = P_b (bas) car invertY
    
        P_bottom = max(y_min, y_max) - (0.1 * (y_max - y_min))
        T_left = min(x_min, x_max)  + (0.05 * (x_max - x_min))
        pressure_altitude = 44109.12 * (1 - ((self.cursor_y/1013.25)**(1/5.255)))
        
        
        #updating labels from cursor
        self.label_cursor_therm.setText(f"{round(self.cursor_x,2)} °C")
        Tk = self.cursor_x + self.skewnessTerm(P_bottom, self.P_bot)
        B = self.P_bot * (1 - ((x_min - self.cursor_x)/45))
        #B = self.P_bot / (np.exp((x_min - self.cursor_x)/45))
        temp_adia_zero = (self.cursor_x + 273.15) * (self.P_bot / self.cursor_y) ** kappa - 273.15

        if B < P_bottom:
            pos_curs_x = x_min + (0.02 * (x_max - x_min))
            pos_curs_y = B
        else :
            pos_curs_x = Tk
            pos_curs_y =  P_bottom

        self.label_cursor_therm.setPos(pos_curs_x, pos_curs_y)
        
        self.label_cursor_bar.setText(f"{round(self.cursor_y,2)} hPa")
        self.label_cursor_bar.setPos(T_left, self.cursor_y)
        
        self.label_cursor_alt.setText(f"{round(pressure_altitude)} m")
        self.label_cursor_alt.setPos(T_left, self.cursor_y)
        
        temp_at_P_bottom = (self.cursor_x + 273.15) * (P_bottom / self.cursor_y) ** kappa - 273.15
        
        #Approximation of dry adiabatic taking 0.104 as the slope rate (wich is enough precise for graphic use)
        # P_at_xmax = (x_max - temp_adia_zero + 45  )/ (0.104  - 45/self.P_bot) 
        # temp_at_P_top = temp_adia_zero - 0.104 * self.P_bot
        # P_at_xmax = (x_max - temp_at_P_top) / 0.104
        x_pos_lab_adia = temp_at_P_bottom + self.skewnessTerm(P_bottom, self.P_bot)
        self.label_cursor_adia.setText(f"{round(temp_adia_zero,2)} °C")
        # print(f"PBOT {P_bottom}")
        # print(f"Pxmax {P_at_xmax}")
        # print(f"xmax = {x_max}")
        # if P_at_xmax > P_bottom:
        #     pos_label_adia_x = x_max - (0.02 * (x_max - x_min))
        #     pos_label_adia_y = P_at_xmax
        # else :
            
        pos_label_adia_x = x_pos_lab_adia
        pos_label_adia_y =  P_bottom
            
        self.label_cursor_adia.setPos(pos_label_adia_x, pos_label_adia_y)
        
    def _update_labels(self):
        
        vb = self.plot_widget.getViewBox()
        x_range, y_range = vb.viewRange()
        x_min, x_max = x_range
        y_min, y_max = y_range 
        P_bottom_therm = max(y_min, y_max) - (0.2 * (y_max - y_min))
        P_bottom_ws = max(y_min, y_max) - (0.1 * (y_max - y_min))
        for label in self._isotherm_labels: #Updating labels from grid
            if not self._visibility['isotherms']:  # ← on vérifie l'état
                label.setVisible(False)
                continue
            temp = label._temp_value
            # Position X de l'isotherme à la pression du bas de la viewbox
            x_pos_temp = temp + self.skewnessTerm(P_bottom_therm, self.P_bot)
            # N'affiche le label que s'il est dans la viewbox
            if x_min <= x_pos_temp <= x_max:
                label.setPos(x_pos_temp, P_bottom_therm)
                label.setVisible(True)
            else:
                label.setVisible(False)
                
        
        for label in self._mixing_labels:
            if not self._visibility['mixing_ratio']:
                label.setVisible(False)
                continue
            ws = label._ws_value
            # Position X de l'isotherme à la pression du bas de la viewbox
            x_pos_ws = self.ws_to_T(ws, P_bottom_ws) + self.skewnessTerm(P_bottom_ws, self.P_bot)
            # N'affiche le label que s'il est dans la viewbox
            if x_min <= x_pos_ws <= x_max:
                label.setPos(x_pos_ws, P_bottom_ws)
                label.setVisible(True)
            else:
                label.setVisible(False)
                
    def _calculate_linreg(self, dataX, dataY):
        """
        Appelé depuis update() — initialise les handles ET calcule la régression
        """
        if self._P_data is None or self._Tdry_data is None:
            return
    
        P    = self._P_data
        Tdry = self._Tdry_data
    
        if self._reg_point_min is None or self._reg_point_max is None:
            self._reg_point_min = 0
            self._reg_point_max = len(P) - 1
    
        self._reg_point_min = int(np.clip(self._reg_point_min, 0, len(P) - 1))
        self._reg_point_max = int(np.clip(self._reg_point_max, 0, len(P) - 1))
    
        idx_min = min(self._reg_point_min, self._reg_point_max)
        idx_max = max(self._reg_point_min, self._reg_point_max)
    
        # Repositionne les handles sur la courbe
        self._updating_handles = True
        x_min = float(Tdry[idx_min]) + self.skewnessTerm(float(P[idx_min]), self.P_bot)
        x_max = float(Tdry[idx_max]) + self.skewnessTerm(float(P[idx_max]), self.P_bot)
        self._reg_handle_min.setPos(x_min, float(P[idx_min]))
        self._reg_handle_max.setPos(x_max, float(P[idx_max]))
        self._updating_handles = False
    
        # Calcule la régression
        self._calculate_linreg_update_only()
    
    def _calculate_linreg_update_only(self):
        """
        Recalcule uniquement la courbe de régression sans repositionner les handles.
        We also calculate the linear regression of the adiabatic dry in the same interval to compare coefficient
        It will help us to tell is the atmosphere is stable or instable in the aera
        """
        if self._P_data is None:
            return
    
        idx_min = min(self._reg_point_min, self._reg_point_max)
        idx_max = max(self._reg_point_min, self._reg_point_max)
    
        P_slice    = self._P_data[idx_min:idx_max + 1]
        Alt_slice = 44109.12 * (1 - ((P_slice/1013.25)**(1/5.255))) #Pressure altitude in meter
        Alt_slice_100 = Alt_slice / 100 #Pressure altitude in 100meter
        Alt_slice_1000 =  Alt_slice / 1000 #Pressure altitude in kilometer


        Tdry_slice = self._Tdry_data[idx_min:idx_max + 1]
    
        if len(P_slice) < 2:
            return
        
        # #Regression on Tdry (state curve) and P
        dataX = P_slice.reshape(-1, 1)
        reg_t  = self.myregP.fit(dataX, Tdry_slice)
        curve_reg_tdry = reg_t.coef_[0] * P_slice + reg_t.intercept_
        curve_reg_tdry_skewed = curve_reg_tdry + self.skewnessTerm(P_slice, self.P_bot)
        self._gradient_reg.setData(curve_reg_tdry_skewed, P_slice)
        
        # #Regression on Tdry (state curve) and Alt_slice_100
        dataX100 = Alt_slice_100.reshape(-1, 1)
        reg_t_100  = self.myregT100.fit(dataX100, Tdry_slice)
        thermal_gradient_100 = reg_t_100.coef_[0] 
        
        # #Regression on Tdry (state curve) and Alt_slice_1000
        dataX1000 = Alt_slice_1000.reshape(-1, 1)
        reg_t_1000  = self.myregT1000.fit(dataX1000, Tdry_slice)
        thermal_gradient_1000 = reg_t_1000.coef_[0] 
        
        # # Régression sur Tdry skewé
        # Tdry_skewed_slice = Tdry_slice + self.skewnessTerm(P_slice, self.P_bot)
        
        # dataX  = P_slice.reshape(-1, 1)
        # reg_t  = self.myreg.fit(dataX, Tdry_skewed_slice)
        
        # # La courbe est maintenant linéaire dans l'espace skewé
        # curve_reg_tdry_skewed = reg_t.coef_[0] * P_slice + reg_t.intercept_
        # self._gradient_reg.setData(curve_reg_tdry_skewed, P_slice)
        # self.gradient_label.setText(f"{round(reg_t.coef_[0], 3)} °C/hPa")

        
        
        # Gradient adiabatique sec analytique : d/dP [Tk*(P/P_bot)^kappa] = kappa*Tk/P_bot*(P/P_bot)^(kappa-1)
        # Evalué au milieu de l'intervalle
        P_mid = np.mean(P_slice)
        T_mid_K = np.mean(Tdry_slice) + 273.15
        dry_adiabat_coef = kappa * T_mid_K / P_mid  # dT/dP analytique en °C/hPa
        dz_dP = 44109.12 * (-1/5.255) * (1/1013.25) * (P_mid/1013.25) ** (1/5.255 - 1)  # m/hPa

        dry_adiabat_thermal_gradient_100 = dry_adiabat_coef / dz_dP * 100 
        if thermal_gradient_100 >= -0.65: #Atmosphere stable, set black color to the gradient curve
            color = (0, 0, 0)   # black

        elif  (thermal_gradient_100 < -0.65)  and (thermal_gradient_100 >= dry_adiabat_thermal_gradient_100 ): #Atmosphere neutral
            color = (19, 242, 79)  # green
            
        elif thermal_gradient_100 < dry_adiabat_thermal_gradient_100 :
            color = (12, 140, 245)  # blue

        
        font = self.gradient_label_1000.font()
        font.setBold(True)
        self.gradient_label_1000.setFont(font)

        self.gradient_label_1000.setText(f"{round(thermal_gradient_1000,2)} °C/km")
        self.gradient_label_P.setText(f"{round(reg_t.coef_[0],3)} °C/hPa")
        self._gradient_reg.setPen(pg.mkPen(color=color, width=2,
                                            style=QtCore.Qt.PenStyle.DashLine))
                
    def _on_handle_moved(self):
        if self._P_data is None or self._updating_handles:
            return
    
        self._updating_handles = True
    
        # Trouve l'index le plus proche pour chaque handle
        for handle, attr in [
            (self._reg_handle_min, '_reg_point_min'),
            (self._reg_handle_max, '_reg_point_max'),
        ]:
            P_mouse = handle.pos().y()
            idx = int(np.argmin(np.abs(self._P_data - P_mouse)))
            setattr(self, attr, idx)
    
            # Snap immédiat sur la courbe Tdry
            x_snap = float(self._Tdry_data[idx]) + self.skewnessTerm(float(self._P_data[idx]), self.P_bot)
            y_snap = float(self._P_data[idx])
            handle.setPos(x_snap, y_snap)
    
        self._updating_handles = False
    
        # Recalcul APRÈS avoir mis à jour les index et snappé
        self._calculate_linreg_update_only()
      
        
    def set_background_visibility(self, isotherms=None, isobars=None,
                               dry_adiabats=None, moist_adiabats=None,
                               mixing_ratio=None, windbarbs = None):
        """
        Change visibility of curves only. 
        Labels visibility are changed trhough _update_labels
        """
        mapping = {
        'isotherms':      (isotherms,      self._curves_isotherms,     self._isotherm_labels),
        'isobars':        (isobars,         self._curves_isobars,       []),
        'dry_adiabats':   (dry_adiabats,    self._curves_dry_adiabats,  []),
        'moist_adiabats': (moist_adiabats,  self._curves_moist_adiabats,[]),
        'mixing_ratio':   (mixing_ratio,    self._curves_mixing_ratio,  self._mixing_labels),
        }
        for key, (visible, curves, labels) in mapping.items():
            if visible is not None:
                self._visibility[key] = visible  # ← on mémorise l'état
                for c in curves:
                    c.setVisible(visible)  
        self._update_labels()
        
        if windbarbs is not None:
            self.wind_barbs.show(windbarbs)
    
            
    def set_gradient_visibility(self, state):
        self._gradient_reg.setVisible(state)
        self._reg_handle_min.setVisible(state)
        self._reg_handle_max.setVisible(state)
        self.gradient_label_1000.setVisible(state)
        self.gradient_label_P.setVisible(state)
        

                
    def set_isotherm_step(self, step, enabled=True):
        step_mapped = round(2 * mapping(step,1,100,10,0.5),0) / 2
        if enabled:
            self._draw_isotherms(step_mapped)
        else:
            for _, c in self._curves_isotherms:
                self.plot_widget.removeItem(c)
            self._curves_isotherms = []
    
    # def set_isobar_step(self, step, enabled=True):
    #     step_mapped = mapping(step,1,100,100,10)
    #     if enabled:
    #         self._draw_isobars(step_mapped)
    #     else:
    #         for _, c in self._curves_isobars:
    #             self.plot_widget.removeItem(c)
    #         self._curves_isobars = []
    
    def set_dry_adiabat_step(self, step, enabled=True):
        step_mapped = round(2 * mapping(step,1,100,10,0.5),0) / 2
        if enabled:
            self._draw_dry_adiabats(step_mapped)
        else:
            for _, c in self._curves_dry_adiabats:
                self.plot_widget.removeItem(c)
            self._curves_dry_adiabats = []
    
    def set_moist_adiabat_step(self, step, enabled=True):
        step_mapped = round(2 * mapping(step,1,100,10,0.5),0) / 2
        if enabled:
            self._draw_moist_adiabats(step_mapped)
        else:
            for _, c in self._curves_moist_adiabats:
                self.plot_widget.removeItem(c)
            self._curves_moist_adiabats = []
    
    def set_windbarbs_step(self, step):
        self.wind_barbs.update_density_barb(step)
        
        
    # def set_mixing_ratio_step(self, step, enabled=True):
    #     step_mapped = mapping(step,1,100,10,1)
    #     if enabled:
    #         self._draw_mixing_ratio(step_mapped)
    #     else:
    #         for _, c in self._curves_mixing_ratio:
    #             self.plot_widget.removeItem(c)
    #         self._curves_mixing_ratio = []

    
    
    def _clear_flight_plots(self):
        """Supprime les courbes de l'ancien vol"""
        flight = self._current_flight
        
        # Supprime les courbes Tdry / Tdew
        if flight['plot']['scatter_emagram'][0]:
            self.plot_widget.removeItem(flight['plot']['scatter_emagram'][0])
            flight['plot']['scatter_emagram'][0] = None
        if flight['plot']['scatter_emagram'][1]:
            self.plot_widget.removeItem(flight['plot']['scatter_emagram'][1])
            flight['plot']['scatter_emagram'][1] = None
    
        # Supprime la régression
        self._gradient_reg.setData([], [])
        self._reg_handle_min.setPos(0, 0)
        self._reg_handle_max.setPos(0, 0)
        self._reg_point_min = None
        self._reg_point_max = None
    
        # Vide les windbarbs
        self.wind_barbs.clear()
    
        # Reset des données
        self._P_data = None
        self._Tdry_data = None
        self.plot_widget.autoRange()