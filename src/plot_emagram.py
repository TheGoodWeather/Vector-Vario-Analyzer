import pyqtgraph as pg
import numpy as np
from PyQt6 import QtCore 
from units import convert_array_to_unit

L = 2.501e6 # J/kg : latent heat of vaporization at 0°C (2.257 J/kg at 100°C)
Ra = 287.04  # J/kg : gas constant for dry air
Rv = 461.5  # J/kg : gas constant for water vapor
eps = Ra/Rv # =Mv/Ma = 0.622
cp = 1005. #J/kg/K
cv = 718. #J/kg/K
kappa = (cp-cv)/cp # kappa = (gamma-1)/gamma = 0.4/1.4 = 2/7 = 0.286
ezero = 6.112# hPa




class SkewTWidget:
    def __init__(self, plot_widget, P_bot=1000., P_b=1000., P_t=300., dp=1):
        
        self.plot_widget = plot_widget
        self.P_bot = P_bot
        self.P_b = P_b
        self.P_t = P_t
        self.dp = dp

        self._setup_widget()
        self._draw_background()

    def _setup_widget(self):
        self.plot_widget.clear()
        self.plot_widget.setBackground("w")
        self.plot_widget.getViewBox().invertY(True)
        self.plot_widget.setLabel("left", "Pressure (hPa)")
        self.plot_widget.setLabel("bottom", "Temperature (°C)")
        self.plot_widget.showGrid(x=False, y=True, alpha=0.3)
        self.plot_widget.setXRange(-25, 40, padding=0)
        # self.plot_widget.setYRange(self.P_t, self.P_b, padding=0)

    def _draw_background(self):
        """Draws static background lines : isotherms, isobars, adiabats, mixing ratio lines"""
        plevs = np.arange(self.P_b, self.P_t - 1, -self.dp)

        # Isothermes
        for temp in np.arange(-50, 50, 2):
            x = temp + self.skewnessTerm(plevs, self.P_bot)
            color = (0, 0, 255, 50) if temp <= 0 else (255, 0, 0, 50)
            style = QtCore.Qt.PenStyle.SolidLine if temp == 0 else QtCore.Qt.PenStyle.DashLine
            self.plot_widget.plot(x, plevs, pen=pg.mkPen(color=color, width=1, style=style))

        # # Isobares
        # for n in np.arange(self.P_bot, self.P_t - 1, -100):
        #     self.plot_widget.plot([-40, 50], [n, n], pen=pg.mkPen(color=(0, 0, 0), width=0.5))

        # # Adiabatiques sèches
        # for tk in 273.15 + np.arange(-30, 210, 10):
        #     dry = tk * (plevs / self.P_bot) ** kappa - 273.15 + skewnessTerm(plevs, self.P_bot)
        #     self.plot_widget.plot(dry, plevs, pen=pg.mkPen(color=(139, 69, 19), width=0.5,
        #                                                     style=QtCore.Qt.PenStyle.DashLine))

        # # Adiabatiques saturées
        # ps = [p for p in plevs if p <= self.P_bot]
        # for temp in np.concatenate((np.arange(-40., 10.1, 5.), np.arange(12.5, 45.1, 2.5))):
        #     moist = []
        #     for p in ps:
        #         temp -= self.dp * gamma_s(temp, p * 100) * 100
        #         moist.append(temp + skewnessTerm(p, self.P_bot))
        #     self.plot_widget.plot(moist, ps, pen=pg.mkPen(color=(0, 180, 0), width=0.5,
        #                                                    style=QtCore.Qt.PenStyle.DotLine))

        # # Rapport de mélange
        # for ws in np.array([0.1, 0.2, 0.5, 1, 1.5, 2, 3, 4, 6, 8, 10, 12, 15, 20, 25, 30]):
        #     temp = ws_to_T(ws, plevs) + skewnessTerm(plevs, self.P_bot)
        #     self.plot_widget.plot(temp, plevs, pen=pg.mkPen(color=(255, 0, 255), width=0.5,
        #                                                      style=QtCore.Qt.PenStyle.DotLine))

    def update(self, flight):
        """
        Update the sounding profiles dynamically.
        P_min / P_max : pressure bounds in hPa (P_min < P_max, ex: 800, 1050)
        """

        x_min =  int(flight['plot']['roi_emagram'].getRegion()[0])
        x_max =  int(flight['plot']['roi_emagram'].getRegion()[1])
        if x_min == x_max: 
            return
        Tdry = flight["data"]["air_T"][x_min : x_max]
        Tdew = flight["data"]["AirTd"][x_min : x_max]
        P = np.multiply(flight["data"]["P_stat"][x_min : x_max], 0.01) #converting Pa to hPa
        
        #updating the range
        # x_range_max = int(max(np.max(Tdry), np.max(Tdew))) + 5
        # x_range_min = int(max(np.min(Tdry), np.min(Tdew))) -5
        y_range_max = int(np.max(P)) + 5
        y_range_min = int(np.min(P)) - 5
        
        self.plot_widget.setYRange(y_range_max, y_range_min)
           
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
            
    def skewnessTerm(self, P,P_bot):
        return 45 * np.log(P_bot/P)