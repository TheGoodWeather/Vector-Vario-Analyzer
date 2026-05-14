import pyqtgraph as pg
import numpy as np
from PyQt6 import QtCore , QtGui
from utils import mapping
from paraglider_widget import ParaGliderWidget
from PyQt6.QtWidgets import QVBoxLayout
from units import convert_array_to_unit, get_unit
from utils import get_label

class DynamicTab:
    def __init__(self, 
                 flight_data_set,
                 comboBox_select_flight_dyntab,
                 plotwidget_1_dyntab,
                 plotwidget_2_dyntab,
                 plotwidget_3_dyntab,
                 comboBox_var_1_dyntab,
                 comboBox_var_2_dyntab,
                 comboBox_var_3_dyntab,
                 lcdNumber_var_1,
                 lcdNumber_var_2,
                 lcdNumber_var_3,
                 model_container,
                 pushButton_previous,
                 pushButton_pause,
                 pushButton_play,
                 pushButton_next,
                 obj_path: str = None):
        
        self.flight_data_set = flight_data_set
        self.comboBox_select_flight_dyntab = comboBox_select_flight_dyntab
        self.plotwidget_1_dyntab = plotwidget_1_dyntab
        self.plotwidget_2_dyntab = plotwidget_2_dyntab
        self.plotwidget_3_dyntab = plotwidget_3_dyntab
        self.comboBox_var_1_dyntab = comboBox_var_1_dyntab
        self.comboBox_var_2_dyntab = comboBox_var_2_dyntab
        self.comboBox_var_3_dyntab = comboBox_var_3_dyntab
        self.lcdNumber_var_1 = lcdNumber_var_1
        self.lcdNumber_var_2 = lcdNumber_var_2
        self.lcdNumber_var_3 = lcdNumber_var_3
        self.model_container = model_container
        self.pushButton_previous = pushButton_previous
        self.pushButton_pause = pushButton_pause
        self.pushButton_play = pushButton_play
        self.pushButton_next = pushButton_next
        
        
        self._cursor_lines = []
        self._index = 400 
        self._flight = None
        
        self.model_widget = ParaGliderWidget(obj_path=obj_path)
        layout = QVBoxLayout(model_container)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.model_widget)
   
        self._setup_widget()
        
        self.comboBox_select_flight_dyntab.currentTextChanged.connect(lambda flight_text : self._fetch_flight(flight_text))
        self.comboBox_var_1_dyntab.currentIndexChanged.connect(lambda: self._update_plot(self.plotwidget_1_dyntab, self._curve1 , self.comboBox_var_1_dyntab ))
        self.comboBox_var_2_dyntab.currentIndexChanged.connect(lambda: self._update_plot(self.plotwidget_2_dyntab,self._curve2 , self.comboBox_var_2_dyntab ))
        self.comboBox_var_3_dyntab.currentIndexChanged.connect(lambda: self._update_plot(self.plotwidget_3_dyntab, self._curve3 , self.comboBox_var_3_dyntab ))
        
        self.pushButton_play.clicked.connect(self.play)
        self.pushButton_pause.clicked.connect(self.pause)
        self.pushButton_next.clicked.connect(self.next_frame)
        self.pushButton_previous.clicked.connect(self.previous_frame)
        
        
        self._play_timer = QtCore.QTimer()
        self._play_timer.timeout.connect(self._play_step)

    def _setup_widget(self):
        
        self.plotwidget_1_dyntab.setBackground("w")
        self.plotwidget_1_dyntab.showGrid(x=True, y=True, alpha=0.4)
        self._curve1 = self.plotwidget_1_dyntab.plot([],[])

        self.plotwidget_2_dyntab.setBackground("w")
        self.plotwidget_2_dyntab.showGrid(x=True, y=True, alpha=0.4)
        self._curve2 = self.plotwidget_2_dyntab.plot([],[])

        self.plotwidget_3_dyntab.setBackground("w")
        self.plotwidget_3_dyntab.showGrid(x=True, y=True, alpha=0.4)
        self._curve3 = self.plotwidget_3_dyntab.plot([],[])

        self.plotwidget_3_dyntab.setXLink(self.plotwidget_1_dyntab)
        self.plotwidget_1_dyntab.setXLink(self.plotwidget_2_dyntab)
       

        for plot in [
            self.plotwidget_1_dyntab,
            self.plotwidget_2_dyntab,
            self.plotwidget_3_dyntab
        ]:
        
            line = pg.InfiniteLine(
                angle=90,
                movable=True,
                pos = self._index,
                pen=pg.mkPen('r', width=2)
            )
            line.sigPositionChanged.connect(lambda line: self._cursor_moved(line))
            plot.addItem(line)
        
            self._cursor_lines.append(line)
        
    def _fetch_flight(self, flight_text):
        
        for flight in self.flight_data_set:
            if flight['file_name'].split(".")[0] == flight_text or (flight['metadata']['alias'] == flight_text):
                if flight['is_data_processed'] and flight['data'] and flight['is_flight_selected']:
                    self._flight = flight
                    break 
        
        if self._flight:
            self._populate_var_combobox()
    
    def _populate_var_combobox(self):

        for combobox in [self.comboBox_var_1_dyntab, self.comboBox_var_2_dyntab, self.comboBox_var_3_dyntab ]:
            combobox.clear()
            combobox.addItem("None", userData = None)
            for variable in self._flight['data']:
                if variable == 'GNSS_time':  
                    continue
                if len(self._flight['data'][variable]) > 0 and not np.all(np.isnan(self._flight['data'][variable])):
                    combobox.addItem(get_label(variable), userData=variable)
                    
    
    def _update_plot(self, plot_widget, curve, combobox_var):
        
        
        variable = combobox_var.currentData() 
        if not variable:
            curve.clear()
            plot_widget.setTitle("Select a variable")
            return
        y = convert_array_to_unit(self._flight['data'][variable], variable)
        if y is None or len(y) == 0:
            return

        x = np.arange(len(y))

        plot_widget.setLimits(
            xMin=np.min(x), xMax=np.max(x),
            yMin=np.min(y), yMax=np.max(y)
        )

        plot_widget.setTitle(f"{get_label(variable)}")
        plot_widget.setLimits(
            xMin=np.min(x),
            xMax=np.max(x),
            yMin=np.min(y),
            yMax=np.max(y)
        )
        pen = pg.mkPen(self._flight['plot']['plot_color'], width=1)
        
        curve.setPen(pen)

        curve.setData(x,y)

        plot_widget.autoRange()   
    
    def _cursor_moved(self, line):

        index = int(line.value())
        self._set_index(index)
    
    def _set_index(self, index):

        if self._flight is None:
            return
    
        n = len(next(iter(self._flight['data'].values())))
    
        self._index = max(0, min(index, n - 1))
        
        if self._index == n -1 :
            self._index = 10
        
        for line in self._cursor_lines:
    
            line.blockSignals(True)
            line.setValue(self._index)
            line.blockSignals(False)
    
        self._update_lcds()
    
    
    def next_frame(self):

        self._set_index(self._index + 1)
        
    def previous_frame(self):

        self._set_index(self._index - 1)
        
    def play(self):

        self._play_timer.start(30)
        
    def pause(self):

        self._play_timer.stop()
        
    def _play_step(self):

        if self._flight is None:
            return
    
        n = len(next(iter(self._flight['data'].values())))
    
        if self._index >= n - 1:
            self.pause()
            return
    
        self._set_index(self._index + 1)
    

            
    def _update_lcds(self):

        combos = [
        self.comboBox_var_1_dyntab,
        self.comboBox_var_2_dyntab,
        self.comboBox_var_3_dyntab,
        ]
        
        lcds = [
        self.lcdNumber_var_1,
        self.lcdNumber_var_2,
        self.lcdNumber_var_3,
        ]
        
        for combo, lcd in zip(combos, lcds):
        
            variable = combo.currentData()
            
            if not variable:
                lcd.display("---")
                continue
            
            data = convert_array_to_unit(
            self._flight['data'][variable],
            variable
            )
            
            if self._index >= len(data):
                continue
            
            value = data[self._index]
            
            if np.isnan(value):
                lcd.display("---")
            else:
                lcd.display(round(float(value), 2))
                        
    
    def cleanup(self):
        """
        Close correctly the GL widget
        """
        self.model_widget.cleanup()
        
      
     