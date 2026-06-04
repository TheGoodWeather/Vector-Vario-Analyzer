import math

from PyQt6 import QtWidgets
import numpy as np
import pyqtgraph as pg


class VerticalWindDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Hodograph")
        self.resize(350, 350)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("w")
        self.plot_widget.setAspectLocked(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.plot_widget)

        self.curve = self.plot_widget.plot(
            [],
            [],
            pen=pg.mkPen((0, 100, 255), width=2)
        )
        self._line_angle_list = [] #the list that contains all the drawed lined
        self._circle_list = []
        self.wind_speed_max = 30 # m/s
        self.wind_speed_min = 0 # m/s

        self.draw_diagram()
    
    def draw_diagram(self):

        max_wind_speed =  math.ceil(self.wind_speed_max / 3) * 3
        amplitude = max((max_wind_speed - self.wind_speed_min), 3)
        
        for radius in range(0, max_wind_speed, int(amplitude/3)):
            circle = self._make_circle(radius)
            self.plot_widget.addItem(circle)
            self._circle_list.append(circle)

        for theta in range(0, 360, 30):
            line = self._make_line(max_wind_speed, theta)
            self.plot_widget.addItem(line)
            self._line_angle_list.append(line)

    def _make_circle(self, r: float) -> pg.PlotCurveItem:
        
        theta = np.linspace(0, 2 * np.pi, 1000, endpoint=True)
        cx = r * np.cos(theta)
        cy = r * np.sin(theta)
        return pg.PlotCurveItem(cx, cy, pen=pg.mkPen('b', width=1))
    

    def _make_line(self, length: float, theta_deg: float) -> pg.PlotCurveItem:
  
        theta = np.radians(theta_deg)
        x_end = length * np.cos(theta)
        y_end = length * np.sin(theta)
        return pg.PlotCurveItem(
            [0, x_end],
            [0, y_end],
            pen=pg.mkPen('b', width=1)
        )

    def _update_circle(self):
        max_wind_speed =  math.ceil(self.wind_speed_max / 3) * 3
        amplitude = max((max_wind_speed - self.wind_speed_min), 3)
        theta = np.linspace(0, 2 * np.pi, 1000, endpoint=True)
        for circle, radius in zip(self._circle_list, range(0, max_wind_speed,  int(amplitude/3))):
            circle.setData(
                radius * np.cos(theta),
                radius * np.sin(theta)
            )

    def _update_lines(self):

        length =  math.ceil(self.wind_speed_max / 3) * 3
        for lines, theta_deg in zip(self._line_angle_list, range(0, 360,30)):
            theta = np.radians(theta_deg)
            x_end = length * np.cos(theta)
            y_end = length * np.sin(theta)
            lines.setData([0, x_end],
            [0, y_end])


    def _convert_data_to_hodo(self, r, theta_deg):
        theta = np.radians(theta_deg)
        return r * np.cos(theta), r * np.sin(theta)

    # API 

    def update_hodograph(self, data_windspeed, data_wind_dir):
        self.wind_speed_max = np.max(data_windspeed)
        self._update_circle()
        self._update_lines()
        x, y = self._convert_data_to_hodo(data_windspeed, data_wind_dir)
        self.curve.setData(x,y)
        self.plot_widget.autoRange()






    

    