import pyqtgraph as pg
import numpy as np
from PyQt6 import QtCore 
from units import convert_array_to_unit
from scipy.optimize import brentq 

L = 2.501e6 # J/kg : latent heat of vaporization at 0°C (2.257 J/kg at 100°C)
Ra = 287.04  # J/kg : gas constant for dry air
Rv = 461.5  # J/kg : gas constant for water vapor
eps = Ra/Rv # =Mv/Ma = 0.622
cp = 1005. #J/kg/K
cv = 718. #J/kg/K
kappa = (cp-cv)/cp # kappa = (gamma-1)/gamma = 0.4/1.4 = 2/7 = 0.286
ezero = 6.112# hPa




class SkewTWidget:
    def __init__(self, plot_widget, P_bot=1013.25, P_b=1013.25, P_t=300., dp=1):
        
        self.plot_widget = plot_widget
        
        self.P_bot = P_bot
        self.P_b = P_b
        self.P_t = P_t
        self.dp = dp
        self.plevs = np.arange(self.P_b, self.P_t - 1, -self.dp)
        self.cursor_x = 0
        self.cursor_y =1000 #default value for cursor 
        self._curves_isotherms = []
        self._curves_isobars = []
        self._curves_dry_adiabats = []
        self._curves_moist_adiabats = []
        self._curves_mixing_ratio = []
        self._setup_widget()
        self._draw_background()
        

    def _setup_widget(self):
        self.plot_widget.clear()
        self.plot_widget.setBackground("w")
        self.plot_widget.getViewBox().invertY(True)
        self.plot_widget.setLabel("left", "Pressure (hPa)")
        self.plot_widget.setLabel("bottom", "Temperature (°C)")
        self.plot_widget.showGrid(x=False, y=True, alpha=0.1)
        self.plot_widget.setXRange(-25, 40, padding=0)
        #initializing adiabatic curves to empty 
        # self._curve_dry_adiabat = self.plot_widget.plot([], [], pen=pg.mkPen(color=(139, 69, 19), width=1.5))
        # self._curve_moist_adiabat = self.plot_widget.plot([], [], pen=pg.mkPen(color=(0, 180, 0), width=1.5))
        #initializing isotherm and isobar curves to empty , used as the skew  cursor
        self._curve_isotherm_cursor = self.plot_widget.plot([], [])
        self._curve_isobar_cursor = pg.InfiniteLine(
            angle=0,                 # horizontale
            movable=False,
            pen=pg.mkPen((0,0,0,70), width=1)
        )
        
        self.plot_widget.addItem(self._curve_isobar_cursor)
        
        self.label_cursor_therm = pg.TextItem(text="°C", color='b', anchor=(0.3, 0))
        self.plot_widget.addItem(self.label_cursor_therm)
        self.label_cursor_bar = pg.TextItem(text="hPa", color=(0,0,0,50), anchor=(0.5, 0))
        self.plot_widget.addItem(self.label_cursor_bar)
        self.label_cursor_alt = pg.TextItem(text="m", color=(0,0,0,50), anchor=(0.5, 1))
        self.plot_widget.addItem(self.label_cursor_alt)
        # self.plot_widget.setYRange(self.P_t, self.P_b, padding=0)
        
        self.plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)
        self.plot_widget.getViewBox().sigRangeChanged.connect(self._update_labels_cursor)
     
    def _draw_background(self):
        
 
        # Isothermes
        for temp in np.arange(-50, 50, 2):
            x = temp + self.skewnessTerm(self.plevs, self.P_bot)
            color = (0, 0, 255, 50) if temp <= 0 else (255, 0, 0, 50)
            style = QtCore.Qt.PenStyle.SolidLine if temp == 0 else QtCore.Qt.PenStyle.DashLine
            c = self.plot_widget.plot(x, self.plevs, pen=pg.mkPen(color=color, width=1, style=style))
            c.setVisible(False)
            self._curves_isotherms.append(c)
    
    
        # # Isobares
        for n in np.arange(self.P_bot, self.P_t - 1, -100):
            c = self.plot_widget.plot([-40, 50], [n, n], pen=pg.mkPen(color=(0, 0, 0), width=0.5))
            self._curves_isobars.append(c)

        # # Adiabatiques sèches
        for tk in 273.15 + np.arange(-30, 210, 10):
            dry = tk * (self.plevs / self.P_bot) ** kappa - 273.15 + self.skewnessTerm(self.plevs, self.P_bot)
            c = self.plot_widget.plot(dry, self.plevs, pen=pg.mkPen(color=(139, 69, 19), width=0.5,
                                                            style=QtCore.Qt.PenStyle.DashLine))
            c.setVisible(False)
            self._curves_dry_adiabats.append(c)
            
       
        # # Adiabatiques saturées
        ps = [p for p in self.plevs if p <= self.P_bot]
        for temp in np.concatenate((np.arange(-40., 10.1, 5.), np.arange(12.5, 45.1, 2.5))):
            moist = []
            for p in ps:
                temp -= self.dp * self.gamma_s(temp, p * 100) * 100
                moist.append(temp + self.skewnessTerm(p, self.P_bot))
            c = self.plot_widget.plot(moist, ps, pen=pg.mkPen(color=(0, 180, 0), width=0.5,
                                                           style=QtCore.Qt.PenStyle.DotLine))
            c.setVisible(False)
            self._curves_moist_adiabats.append(c)
    
        # # Rapport de mélange
        for ws in np.array([0.1, 0.2, 0.5, 1, 1.5, 2, 3, 4, 6, 8, 10, 12, 15, 20, 25, 30]):
            temp = self.ws_to_T(ws, self.plevs) + self.skewnessTerm(self.plevs, self.P_bot)
            c = self.plot_widget.plot(temp, self.plevs, pen=pg.mkPen(color=(255, 0, 255), width=0.5,
                                                             style=QtCore.Qt.PenStyle.DotLine))
            c.setVisible(False)
            self._curves_mixing_ratio.append(c)

    def update(self, flight):
        """
        Update the sounding profiles dynamically.
        P_min / P_max : pressure bounds in hPa (P_min < P_max, ex: 800, 1050)
        """

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
        Tdry_skewed = Tdry + self.skewnessTerm(P, self.P_bot)
        Tdew_skewed = Tdew + self.skewnessTerm(P, self.P_bot)
        #updating the range
        x_range_max = int(max(np.max(Tdry_skewed), np.max(Tdew_skewed))) + 3
        x_range_min = int(min(np.min(Tdry_skewed), np.min(Tdew_skewed))) -3
        y_range_max = int(np.max(P)) + 5
        y_range_min = int(np.min(P)) - 5
        
        self.plot_widget.setYRange(y_range_max, y_range_min)
        self.plot_widget.setXRange(x_range_min, x_range_max)   
        
        if flight['plot']['scatter_emagram'][0] and flight['plot']['scatter_emagram'][1]: #if the scatters Tdew and Tdry item already exists
        
            flight['plot']['scatter_emagram'][0].setData(Tdry + self.skewnessTerm(P, self.P_bot), P)
            flight['plot']['scatter_emagram'][1].setData(Tdew + self.skewnessTerm(P, self.P_bot), P)
        else:
            # Create Curve T Dry 
            flight['plot']['scatter_emagram'][0] = self.plot_widget.plot(
                Tdry + self.skewnessTerm(P, self.P_bot),
                P,
                pen=pg.mkPen(color=(0, 0, 0), width=1.5)
            )
            # Create Curve T moist
            flight['plot']['scatter_emagram'][1] = self.plot_widget.plot(
                Tdew + self.skewnessTerm(P, self.P_bot),
                P,
                pen=pg.mkPen(color=(255, 0, 0), width=1.5)
            )
    
    def _on_mouse_moved(self, pos):
        vb = self.plot_widget.getViewBox()
        if not self.plot_widget.sceneBoundingRect().contains(pos):
            return
    
        mouse_point = vb.mapSceneToView(pos)
        T_mouse_unskewed = mouse_point.x()   
        P_mouse = mouse_point.y()
        T_mouse_skewed = T_mouse_unskewed - self.skewnessTerm(P_mouse, self.P_bot)
        self.cursor_x = T_mouse_skewed
        self.cursor_y = P_mouse
        
        x = T_mouse_skewed + self.skewnessTerm(self.plevs, self.P_bot)
        color_therm = (0, 0, 255, 70) if T_mouse_skewed <= 0 else (255, 0, 0, 70)
        style_therm = QtCore.Qt.PenStyle.SolidLine if T_mouse_skewed == 0 else QtCore.Qt.PenStyle.DashLine
        
        self._curve_isotherm_cursor.setData(x, self.plevs, pen=pg.mkPen(color=color_therm, width=1, style=style_therm))
        self._curve_isobar_cursor.setValue(self.cursor_y)
        self._update_labels_cursor()
        
        # Tk = (T_mouse_unskewed - self.skewnessTerm(P_mouse, self.P_bot) + 273.15) * (self.P_bot / P_mouse) ** kappa - 273.15
        # # # Adiabatique sèche depuis T_mouse, P_mouse
        # dry = (Tk + 273.15) * (self.plevs / self.P_bot) ** kappa - 273.15 + self.skewnessTerm(self.plevs, self.P_bot)
        # self._curve_dry_adiabat.setData(dry, self.plevs)

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
        return 45 * np.log(P_bot/P)
    
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
        color_cursor_therm = (0, 0, 255, 70) if self.cursor_x <= 0 else (255, 0, 0, 70)
        self.label_cursor_therm.setText(f"{round(self.cursor_x,2)} °C")
        self.label_cursor_therm.setColor(color_cursor_therm)
        self.label_cursor_therm.setPos(self.cursor_x + self.skewnessTerm(P_bottom, self.P_bot), P_bottom)
        
        self.label_cursor_bar.setText(f"{round(self.cursor_y,2)} hPa")
        self.label_cursor_bar.setPos(T_left, self.cursor_y)
        
        self.label_cursor_alt.setText(f"{round(pressure_altitude,2)} m")
        self.label_cursor_alt.setPos(T_left, self.cursor_y)
        # for label in self._isotherm_labels: #Updating labels from grid
        #     temp = label._temp_value
        #     # Position X de l'isotherme à la pression du bas de la viewbox
        #     x_pos = temp + self.skewnessTerm(P_bottom, self.P_bot)
        #     # N'affiche le label que s'il est dans la viewbox
        #     if x_min <= x_pos <= x_max:
        #         label.setPos(x_pos, P_bottom)
        #         label.setVisible(True)
        #     else:
        #         label.setVisible(False)
    
        # for label in self._isobar_labels:
        #     n = label._pres_value
        #     # N'affiche le label que si l'isobare est dans la viewbox
        #     if min(y_min, y_max) <= n <= max(y_min, y_max):
        #         label.setPos(x_min, n)
        #         label.setVisible(True)
        #     else:
        #         label.setVisible(False)
        
    def set_background_visibility(self, isotherms=None, isobars=None,
                               dry_adiabats=None, moist_adiabats=None,
                               mixing_ratio=None):
        """
        Chaque argument est un booléen. None = pas de changement.
        Exemple : self.skewt.set_background_visibility(dry_adiabats=True, mixing_ratio=False)
        """
        mapping = {
            isotherms:     self._curves_isotherms,
            isobars:       self._curves_isobars,
            dry_adiabats:  self._curves_dry_adiabats,
            moist_adiabats:self._curves_moist_adiabats,
            mixing_ratio:  self._curves_mixing_ratio,
        }
        for visible, curves in mapping.items():
            if visible is not None:
                for c in curves:
                    c.setVisible(visible)