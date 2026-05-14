import pyqtgraph as pg
import numpy as np
from PyQt6 import QtCore , QtGui
from utils import mapping
from paraglider_widget import ParaGliderWidget
from PyQt6.QtWidgets import QVBoxLayout

class DynamicTab:
    def __init__(self, yaw_plotwidget, roll_plotwidget, pitch_plotwidget, model_container, obj_path: str = None):
        
        self.yaw_plotwidget = yaw_plotwidget
        self.roll_plotwidget = roll_plotwidget
        self.pitch_plotwidget = pitch_plotwidget
        self.model_widget = ParaGliderWidget(obj_path=obj_path)
        layout = QVBoxLayout(model_container)
        layout.setContentsMargins(0,0,0,0)

        layout.addWidget(self.model_widget)
   
        self._setup_widget()
        

    def _setup_widget(self):
        
    
        
        self.yaw_plotwidget.setBackground("w")
        self.yaw_plotwidget.setLabel("left", "Angle")
        self.yaw_plotwidget.setLabel("bottom", "Sample")
        self.yaw_plotwidget.showGrid(x=True, y=True, alpha=0.4)
        
        self.roll_plotwidget.setBackground("w")
        self.roll_plotwidget.setLabel("left", "Angle")
        self.roll_plotwidget.setLabel("bottom", "Sample")
        self.roll_plotwidget.showGrid(x=True, y=True, alpha=0.4)
        
        self.pitch_plotwidget.setBackground("w")
        self.pitch_plotwidget.setLabel("left", "Angle")
        self.pitch_plotwidget.setLabel("bottom", "Sample")
        self.pitch_plotwidget.showGrid(x=True, y=True, alpha=0.4)
        
        
    def cleanup(self):
        """
        Close correctly the GL widget
        """
        self.model_widget.cleanup()
        
      
     