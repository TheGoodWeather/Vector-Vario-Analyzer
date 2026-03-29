import numpy as np
import pyqtgraph as pg
from units import convert_array_to_unit
from PyQt6.QtWidgets import QRadioButton
#constants


A0P =  0.0264191                   
A1P =  0.0253048                   
A2P =  0.2781714                  
KAR =  0.0030313                   
OPEN = 0.0389250                   
POD =  0.0296384                   
SUB =  0.0247878                   
increment_ci = 0.01



def update_polar_generator_values(auw, ar, sproj, widget_harness, curve, plot_widget_vxvz):
    
    for radiobutton in widget_harness.findChildren(QRadioButton):
        if radiobutton.isChecked():
            
            text = radiobutton.text().upper()
            
            if text == "OPEN":
                harness = OPEN
            elif text == "POD":
                harness = POD
            elif text == "SUB":
                harness = SUB
         
    Cl0 =  0.0899 * (ar/100) + 0.3391
    scatter_vx = []
    scatter_vz = []
    for CI in np.arange(0.3, Cl0, increment_ci):
        Cd = harness + A0P - (KAR * (ar/100)) + A1P * CI + A2P *np.square(CI) / (ar/100)
        Vx = np.sqrt((2*auw * 9.81)/(1.225 * CI *sproj))
        Vz = - np.sqrt((2*auw * 9.81)/(1.225 * Cd *sproj))
        scatter_vx.append(Vx)
        scatter_vz.append(Vz)
    
    scatter_vx =  convert_array_to_unit(scatter_vx, 'GNSS_speed')
    scatter_vz = convert_array_to_unit(scatter_vz, 'GNSS_speed' )


    curve.setData(scatter_vx, scatter_vz)
    plot_widget_vxvz.autoRange()
    
