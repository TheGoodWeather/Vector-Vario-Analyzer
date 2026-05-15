import pyqtgraph as pg
import numpy as np
from PyQt6 import QtCore , QtGui
from utils import mapping
from paraglider_widget import ParaGliderWidget
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QStackedLayout
from units import convert_array_to_unit, get_unit
from utils import get_label
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtCore import Qt


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
                 pushButton_speed,
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
        self.pushButton_speed = pushButton_speed
        
        self._cursor_lines = []
        self._index = 400 
        self._flight = None
        
        # self.model_widget = ParaGliderWidget(obj_path=obj_path)
        # layout = QVBoxLayout(model_container)
        # layout.setContentsMargins(0,0,0,0)
        # layout.addWidget(self.model_widget)
        
        self.gl_container = QWidget()
        stack = QStackedLayout(self.gl_container)
        stack.setStackingMode(
            QStackedLayout.StackingMode.StackAll
        )
        
        self.model_widget = ParaGliderWidget(
            obj_path=obj_path
        )
        
        self.hud_widget = HUDWidget()
        
        stack.addWidget(self.model_widget)
        stack.addWidget(self.hud_widget)
        self.hud_widget.setStyleSheet("background: transparent;")
        self.hud_widget.raise_()
        
        layout = QVBoxLayout(model_container)
        layout.setContentsMargins(0,0,0,0)
        
        layout.addWidget(self.gl_container)
   
        self._setup_widget()
        
        self.comboBox_select_flight_dyntab.currentTextChanged.connect(lambda flight_text : self._fetch_flight(flight_text))
        self.comboBox_var_1_dyntab.currentIndexChanged.connect(lambda: self._update_plot(self.plotwidget_1_dyntab, self._curve1 , self.comboBox_var_1_dyntab ))
        self.comboBox_var_2_dyntab.currentIndexChanged.connect(lambda: self._update_plot(self.plotwidget_2_dyntab,self._curve2 , self.comboBox_var_2_dyntab ))
        self.comboBox_var_3_dyntab.currentIndexChanged.connect(lambda: self._update_plot(self.plotwidget_3_dyntab, self._curve3 , self.comboBox_var_3_dyntab ))
        
        self.pushButton_play.clicked.connect(self.play)
        self.pushButton_pause.clicked.connect(self.pause)
        self.pushButton_next.clicked.connect(self.next_frame)
        self.pushButton_previous.clicked.connect(self.previous_frame)
        self.pushButton_speed.clicked.connect(self.change_speed)
        
        
        self._play_timer = QtCore.QTimer()
        self._play_timer.timeout.connect(self._play_step)
        
        self._playback_speed = 1.0   # 0.5 / 1 / 2
        self._play_elapsed = 0.0     # temps simulé écoulé

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
            # plot_widget.setTitle("Select a variable")
            return
        y = convert_array_to_unit(self._flight['data'][variable], variable)
        if y is None or len(y) == 0:
            return

        x = np.arange(len(y))

        plot_widget.setLimits(
            xMin=np.min(x), xMax=np.max(x),
            yMin=np.min(y), yMax=np.max(y)
        )

        # plot_widget.setTitle(f"{get_label(variable)}")
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
        self._update_hud()
        self._update_model()
    
    def _update_model(self):
        pitch= self._flight['data']['pitch'][self._index]
        roll= self._flight['data']['roll'][self._index]
        yaw= self._flight['data']['compass_head'][self._index]
        x = self._flight['data']['GNSS_lat'][self._index]
        y = self._flight['data']['GNSS_lon'][self._index]
        z = self._flight['data']['GNSS_alt'][self._index]
        self.model_widget.set_attitude(pitch,roll,yaw)
        self.model_widget.set_position(x,y,z)

    def next_frame(self):

        self._set_index(min(
        self._index + 1,
        len(self._flight['data']['GNSS_time']) - 1
    ))
        
    def previous_frame(self):

        self._set_index(max(0, self._index - 1))
        
    def play(self):

        self._play_timer.start(30)
        
    def pause(self):

        self._play_timer.stop()
    
    def change_speed(self):
        

        speeds = [0.5, 1, 2, 5, 10]
        current_index = speeds.index(self._playback_speed)
        current_index = (current_index + 1) % len(speeds)
        self._playback_speed = speeds[current_index]
        self.pushButton_speed.setText(f"x{self._playback_speed}")
        
        
    def _play_step(self):

        if self._flight is None:
            return
    
        times = self._flight['data']['GNSS_time']
    
        if self._index >= len(times) - 1:
            self.pause()
            return
    
        # temps simulé ajouté à chaque frame
        dt_frame = (1 / 30.0) * self._playback_speed
    
        self._play_elapsed += dt_frame
    
        current_time = times[self._index]
    
        # avance tant que le temps simulé dépasse
        while self._index < len(times) - 1:
    
            next_time = times[self._index + 1]
    
            real_dt = (next_time - current_time).total_seconds()
    
            if self._play_elapsed >= real_dt:
    
                self._play_elapsed -= real_dt
                self._index += 1
    
                current_time = next_time
    
            else:
                break
    
        self._set_index(self._index)
    

    
    def _update_hud(self):
        
        netto = self._flight['data']['netto'][self._index]
        altitude = self._flight['data']['GNSS_alt'][self._index]
        time = self._flight['data']['GNSS_time'][self._index]
        formatted_time = time.strftime("%H:%M")
        ground_speed = self._flight['data']['GNSS_speed'][self._index]
        duration = self._flight['data']['GNSS_time'][self._index] - self._flight['data']['GNSS_time'][0]
        total_seconds = int(duration.total_seconds())

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        formatted_duration = (
            f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        )
        
        self.hud_widget.set_netto(round(netto,2))
        self.hud_widget.set_altitude(round(altitude,2))
        self.hud_widget.set_ground_speed(round(ground_speed,2))
        self.hud_widget.set_time(formatted_time)
        self.hud_widget.set_duration(formatted_duration)
        
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
        
        






class HUDWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.netto = 0.0
        self.ground_speed = 0
        self.time = 0
        self.duration = 0
        self.altitude = 0

        # Transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Le HUD ne bloque pas la souris
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
   
    
    def set_netto(self, value):
        self.netto = value
        self.update()
    
    def set_altitude(self, value):
        self.altitude = value
        self.update()
    
    def set_time(self, value):
        self.time = value
        self.update()
    
    def set_duration(self, value):
        self.duration = value
        self.update()
        
    def set_ground_speed(self, value):
        self.ground_speed = value
        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
        # -------------------------------------------------
        # TEXTE
        # -------------------------------------------------

        painter.setPen(QPen(QColor(255, 255, 255)))

        font = QFont()
        font.setPointSize(10)
        font.setBold(True)

        painter.setFont(font)

        painter.drawText(
            300,
            40,
            f"Time : {self.time}"
        )
        
        painter.drawText(
            300,
            80,
            f"Duration : {self.duration}"
        )
        
        painter.drawText(
            20,
            40,
            f"Altitude (m) : {self.altitude} "
        )
        
        painter.drawText(
            20,
            80,
            f"Ground Speed (m/s) : {self.ground_speed} "
        )
        
    
        
        if self.netto > 0 :
            painter.drawText(
                self.width() - 80 - 20,
                40,
                f"+{self.netto} m/s "
            )
        else:
            painter.drawText(
                self.width() - 80 - 20,
                40,
                f"{self.netto} m/s "
            )
        # -------------------------------------------------
        # JAUGE SIMPLE
        # -------------------------------------------------

        gauge_x = self.width() - 80
        gauge_y = 50
        gauge_h = 200
        gauge_w = 20

        # fond
        painter.setBrush(QColor(40, 40, 40, 180))
        painter.drawRect(gauge_x, gauge_y, gauge_w, gauge_h)

        # valeur
        value = max(-6, min(6, self.netto))

        #normalized = (value + 5) / 10.0

        fill_h = int(mapping(value, -6, 6,0, gauge_h))
        
        x = gauge_x
        y = int(gauge_y + gauge_h - fill_h)
        w = gauge_w
        h = fill_h
        painter.setBrush(QColor(0, 255, 0, 200))
        painter.drawRect(x, y, w, h)

        painter.end()
     