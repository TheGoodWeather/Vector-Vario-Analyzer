from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import numpy as np

import metpy.calc as mpcalc
from metpy.plots import  SkewT
from metpy.units import units




def update_emagram_graph(flight_dic, widget_emagram, combobox_flight):

    layout = widget_emagram.layout()
    
    fig = Figure(figsize=(6, 6))
    fig.tight_layout()
    canvas = FigureCanvas(fig)
    canvas.setMaximumHeight(400)
    skew = SkewT(fig, rotation=45, aspect = 'auto')

    for flight in flight_dic:
        if flight['file_name'].split(".")[0] == combobox_flight.currentText():

            u, v = mpcalc.wind_components(
                flight['data']['wind_vel'] * units("m/s"),
                flight['data']['wind_origin'] * units("degrees")
            )
            p = (flight['data']['P_stat'] * units.Pa).to(units.hPa) #converting to hpa
            skew.plot(p, flight['data']['air_T'], 'r')
            skew.plot(p, flight['data']['AirTd'], 'g')
            skew.plot_barbs(
                p[::10],
                u[::10],
                v[::10]
            )

            skew.plot_dry_adiabats()
            skew.plot_moist_adiabats()
            skew.plot_mixing_lines()

            skew.ax.set_ylim(np.max(p),700)
            skew.ax.set_xlim(-20, 30)

    layout.addWidget(canvas)
    canvas.draw()