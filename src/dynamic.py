import pyqtgraph as pg
import numpy as np
from PyQt6 import QtCore , QtGui
from utils import mapping
from paraglider_widget import ParaGliderWidget
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QStackedLayout
from units import convert_array_to_unit, get_unit, convert_gps_to_local_xy
from utils import get_label, get_variable
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtCore import Qt

fps = 30

class DynamicTab(QtCore.QObject):


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
                 radioButton_free_view,
                 radioButton_front_view,
                 radioButton_behind_view,
                 radioButton_top_view,
                 radioButton_left_view,
                 radioButton_right_view,
                 label_unit_var1_dyna,
                 label_unit_var2_dyna,
                 label_unit_var3_dyna,
                 checkbox_wind_vector_dyna,
                 checkbox_north_vector_dyna,
                 checkbox_tas_vector_dyna,
                 checkbox_bearing_vector_dyna,
                 obj_path: str = None):
        
        super().__init__()

        self.radioButton_free_view = radioButton_free_view
        self.radioButton_front_view = radioButton_front_view
        self.radioButton_behind_view = radioButton_behind_view
        self.radioButton_top_view = radioButton_top_view
        self.radioButton_left_view= radioButton_left_view
        self.radioButton_right_view = radioButton_right_view
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
        self.label_unit_var1_dyna = label_unit_var1_dyna
        self.label_unit_var2_dyna = label_unit_var2_dyna
        self.label_unit_var3_dyna = label_unit_var3_dyna
        self.checkbox_wind_vector_dyna = checkbox_wind_vector_dyna
        self.checkbox_north_vector_dyna = checkbox_north_vector_dyna
        self.checkbox_tas_vector_dyna =checkbox_tas_vector_dyna
        self.checkbox_bearing_vector_dyna = checkbox_bearing_vector_dyna

    
        self._cursor_lines = []
        self._current_time = 0.0 #second
        self._interp_index = 0
        self._raw_index = 0

        self._flight = None

        self._pitch_interp = None
        self._roll_interp = None
        self._yaw_interp = None
        self._time_interp = None
        self._x_interp = None
        self._y_interp = None
        self._z_interp = None
        self._speed_interp = None
        self._netto_interp = None
        self._alt_interp = None
        self._wind_dir_interp = None
        self._wind_tilt_interp = None
        self._wind_tilt = None
        self._wind_speed_interp = None

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
        self.comboBox_var_1_dyntab.currentIndexChanged.connect(lambda: self._update_plot(self.plotwidget_1_dyntab, self._curve1 , self.comboBox_var_1_dyntab, self.label_unit_var1_dyna ))
        self.comboBox_var_2_dyntab.currentIndexChanged.connect(lambda: self._update_plot(self.plotwidget_2_dyntab,self._curve2 , self.comboBox_var_2_dyntab, self.label_unit_var2_dyna))
        self.comboBox_var_3_dyntab.currentIndexChanged.connect(lambda: self._update_plot(self.plotwidget_3_dyntab, self._curve3 , self.comboBox_var_3_dyntab ,self.label_unit_var3_dyna))
        
        self.pushButton_play.clicked.connect(self.play)
        self.pushButton_pause.clicked.connect(self.pause)
        self.pushButton_next.clicked.connect(self.next_frame)
        self.pushButton_previous.clicked.connect(self.previous_frame)
        self.pushButton_speed.clicked.connect(self.change_speed)
        
        self.radioButton_free_view.toggled.connect(self.model_widget.set_view_free)
        self.radioButton_front_view.toggled.connect(self.model_widget.set_view_front)
        self.radioButton_behind_view.toggled.connect(self.model_widget.set_view_behind)
        self.radioButton_top_view.toggled.connect(self.model_widget.set_view_top) 
        self.radioButton_left_view.toggled.connect(self.model_widget.set_view_left)
        self.radioButton_right_view.toggled.connect(self.model_widget.set_view_right) 

        self.checkbox_wind_vector_dyna.stateChanged.connect(lambda state: self.model_widget.set_visibility_wind_vector(state))
        self.checkbox_wind_vector_dyna.setChecked(True)
        self.checkbox_north_vector_dyna.stateChanged.connect(lambda state: self.model_widget.set_visibility_north_vector(state))
        self.checkbox_north_vector_dyna.setChecked(False)
        self.checkbox_tas_vector_dyna.stateChanged.connect(lambda state: self.model_widget.set_visibility_tas_vector(state))
        self.checkbox_tas_vector_dyna.setChecked(False)
        self.checkbox_bearing_vector_dyna.stateChanged.connect(lambda state: self.model_widget.set_visibility_bearing_vector(state))
        self.checkbox_bearing_vector_dyna.setChecked(False)

        self._play_timer = QtCore.QTimer()
        self._play_timer.timeout.connect(self._play_step)
        self._elapsed_timer = QtCore.QElapsedTimer()
        
        self._playback_speed = 1.0   # 0.5 / 1 / 2
        self._play_elapsed = 0.0     # temps simulé écoulé

        # Keyboard events management
        self.gl_container.installEventFilter(self)
        self.gl_container.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.gl_container.setFocus()

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
       

        self.label_unit_var1_dyna.setText("")
        self.label_unit_var2_dyna.setText("")
        self.label_unit_var3_dyna.setText("")

        for plot in [
            self.plotwidget_1_dyntab,
            self.plotwidget_2_dyntab,
            self.plotwidget_3_dyntab
        ]:
        
            line = pg.InfiniteLine(
                angle=90,
                movable=True,
                pos = self._raw_index,
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
            self._interpolate_data()
            self._set_time(0.0)


            self.comboBox_var_1_dyntab.setCurrentIndex(self.comboBox_var_1_dyntab.findData("compass_head"))
            self.comboBox_var_2_dyntab.setCurrentIndex(self.comboBox_var_1_dyntab.findData("pitch"))
            self.comboBox_var_3_dyntab.setCurrentIndex(self.comboBox_var_1_dyntab.findData("roll"))



    def _interpolate_data(self):

        times = self._flight['data']['GNSS_time']

        t0 = times[0]

        t_seconds = np.array([
            (t - t0).total_seconds()
            for t in times
        ], dtype=np.float64)

        self._time_raw = t_seconds

        self._time_interp = np.arange(
            0,
            t_seconds[-1],
            1/fps
        )


        self._pitch_interp = np.interp(
            self._time_interp,
            t_seconds,
            self._flight['data']['pitch']
        )

        self._roll_interp = np.interp(
            self._time_interp,
            t_seconds,
            self._flight['data']['roll']
        )

        yaw = np.unwrap(
            np.radians(
                self._flight['data']['compass_head']
            )
        )
        yaw_interp = np.interp(
            self._time_interp,
            t_seconds,
            yaw
        )
        self._yaw_interp = np.degrees(yaw_interp)

        _x_local, _y_local = convert_gps_to_local_xy(self._flight['data']['GNSS_lon'], self._flight['data']['GNSS_lat'])

        self._x_interp = np.interp(
            self._time_interp,
            t_seconds,
            _x_local
        )

        self._y_interp = np.interp(
            self._time_interp,
            t_seconds,
            _y_local
        )

        self._z_interp = np.interp(
            self._time_interp,
            t_seconds,
            self._flight['data']['GNSS_alt']
        )

        self.model_widget.set_trajectory(
            self._x_interp ,
            self._y_interp ,
            self._z_interp,
        )

        self._netto_interp = np.interp(
            self._time_interp,
            t_seconds,
            self._flight['data']['netto']
        )

        self._alt_interp = np.interp(
            self._time_interp,
            t_seconds,
            self._flight['data']['GNSS_alt']
        )

        self._speed_interp = np.interp(
            self._time_interp,
            t_seconds,
            self._flight['data']['GNSS_speed']
        )

        wind_vel = np.asarray(
            self._flight['data']['wind_vel'],
            dtype=float
        )

        netto = np.asarray(
            self._flight['data']['netto'],
            dtype=float
        )

        ratio = np.divide(
            netto,
            wind_vel,
            out=np.zeros_like(netto),
            where=np.abs(wind_vel) > 1e-6
        )

        self._wind_tilt = np.rad2deg(
            np.arctan(ratio)
        )


        wind_dir = np.unwrap(
            np.radians(
                self._flight['data']['wind_origin']
            )
        )
        wind_dir_interp = np.interp(
            self._time_interp,
            t_seconds,
            wind_dir
        )
        self._wind_dir_interp = np.degrees(wind_dir_interp)


        self._wind_tilt_interp = np.interp(
            self._time_interp,
            t_seconds,
            self._wind_tilt)
        
        self._wind_speed_interp = np.interp(
            self._time_interp,
            t_seconds,
            self._flight['data']['wind_vel']
        )

        self._tas_interp = np.interp(
            self._time_interp,
            t_seconds,
            self._flight['data']['TAS']
        )

        self._vario_interp = np.interp(
            self._time_interp,
            t_seconds,
            self._flight['data']['vario']
        )

        gnss_heading = np.unwrap(
            np.radians(
                self._flight['data']['GNSS_head']
            )
        )
        gnss_heading_interp = np.interp(
            self._time_interp,
            t_seconds,
            gnss_heading
        )
        self._gnss_heading_interp = np.degrees(gnss_heading_interp)


    


    
    def _populate_var_combobox(self):
        for combobox in [self.comboBox_var_1_dyntab, self.comboBox_var_2_dyntab, self.comboBox_var_3_dyntab ]:
            variable_to_sort = []
            combobox.clear()
            combobox.addItem("None", userData = None)
            for variable in self._flight['data']:
                if variable == 'GNSS_time':  
                    continue
                if len(self._flight['data'][variable]) > 0 and not np.all(np.isnan(self._flight['data'][variable])):
                    variable_to_sort.append(get_label(variable))
            for variable in sorted(variable_to_sort):
                combobox.addItem(variable, userData=get_variable(variable))

    def _update_plot(self, plot_widget, curve, combobox_var, label_widget_unit):
        
        
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

        label_widget_unit.setText(str(get_unit(variable)))

    
    def _cursor_moved(self, line):

        self._raw_index = int(line.value())

        # sécurité
        self._raw_index = np.clip(
            self._raw_index,
            0,
            len(self._time_raw) - 1
        )

        # 1) convertir raw index → temps
        self._current_time = self._time_raw[self._raw_index]

        # 2) convertir temps → index interpolé
        self._interp_index = int(self._current_time * fps)

        self._interp_index = np.clip(
            self._interp_index,
            0,
            len(self._time_interp) - 1
        )

        # 3) sync UI
        self._update_model()
        self._update_lcds()
        self._update_hud()

    
    def _set_time(self, current_time):

        if self._flight is None:
            return

        self._current_time = np.clip(
            current_time,
            0,
            self._time_interp[-1]
        )

        # -------------------------
        # index interpolation 30 fps
        # -------------------------

        self._interp_index = int(
            self._current_time * fps
        )

        self._interp_index = min(
            self._interp_index,
            len(self._time_interp) - 1
        )

        # -------------------------
        # index données brutes
        # -------------------------

        self._raw_index = np.searchsorted(
            self._time_raw,
            self._current_time
        )

        self._raw_index = min(
            self._raw_index,
            len(self._time_raw) - 1
        )

        # -------------------------
        # update UI
        # -------------------------

        self._update_cursor()
        self._update_model()
        self._update_lcds()
        self._update_hud()
    
    def _update_cursor(self):

        for line in self._cursor_lines:
            line.blockSignals(True)
            line.setValue(self._raw_index)
            line.blockSignals(False)

    def _update_model(self):

        i = self._interp_index
        pitch= self._pitch_interp[i]
        roll= self._roll_interp[i]
        yaw= self._yaw_interp[i]
        x = self._x_interp[i]
        y = self._y_interp[i]
        z = self._z_interp[i]
        wind_azimut = self._wind_dir_interp[i]
        wind_tilt = self._wind_tilt_interp[i]
        wind_speed = self._wind_speed_interp[i]
        tas = self._tas_interp[i]
        gnss_speed = self._speed_interp[i]
        bearing = self._gnss_heading_interp[i]
        


        self.model_widget.set_attitude(pitch =pitch, roll = roll, yaw= yaw)
        self.model_widget.set_position(x,y,z)
        self.model_widget.set_wind_vector(wind_azimut,wind_tilt, wind_speed)
        self.model_widget.set_tas_vector(yaw, tas)
        self.model_widget.set_bearing_vector(bearing,gnss_speed)


    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.KeyPress:
            key = event.key()
            # SPACE -> play/pause
            if key == Qt.Key.Key_Space:
                if self._play_timer.isActive():
                    self.pause()
                else:
                    self.play()
                event.accept()
                return True
            # RIGHT -> frame suivante
            elif key == Qt.Key.Key_Right:
                self.next_frame()
                event.accept()
                return True
            # LEFT -> frame précédente
            elif key == Qt.Key.Key_Left:
                self.previous_frame()
                event.accept()                
                return True
            # UP -> vitesse +
            elif key == Qt.Key.Key_Up:
                self._playback_speed *= 2
                return True
            # DOWN -> vitesse -
            elif key == Qt.Key.Key_Down:
                self._playback_speed /= 2
                return True
            # vues caméra
            elif key == Qt.Key.Key_F:
                self.model_widget.set_view_front()
                return True
            elif key == Qt.Key.Key_B:
                self.model_widget.set_view_behind()
                return True
            elif key == Qt.Key.Key_T:
                self.model_widget.set_view_top()
                return True
            elif key == Qt.Key.Key_G:
                self.model_widget.set_view_free()
                return True
        return super().eventFilter(obj, event)
        

    def next_frame(self):
        dt = 1 / fps    
        self._set_time(min(
        self._current_time + dt,
        self._time_interp[-1]
    ))
        
    def previous_frame(self):
        dt = 1 / fps
        self._set_time(max(0, self._current_time - dt))
        
    def play(self):
        self._elapsed_timer.restart()
        self._play_timer.start(16)   # vise 60 Hz, on régule nous-mêmes
        # self._play_timer.start(int(1000 / fps))
        
    def pause(self):

        self._play_timer.stop()
    
    def change_speed(self):
        

        speeds = [0.5, 1, 2, 5, 10]
        current_index = speeds.index(self._playback_speed)
        current_index = (current_index + 1) % len(speeds)
        self._playback_speed = speeds[current_index]
        self.pushButton_speed.setText(f"x{self._playback_speed}")
        
        
    def _play_step(self):
        dt = 1 / fps
        dt_real = self._elapsed_timer.elapsed() / 1000.0
        self._elapsed_timer.restart()

        dt_sim = dt_real * self._playback_speed

        if self._current_time >= self._time_interp[-1]:
            self.pause()
            return

        # self._current_time += dt * self._playback_speed
        self._current_time = min(
            self._current_time + dt_sim,
            self._time_interp[-1]
        )

        self._set_time(self._current_time)
        
       
    

    
    def _update_hud(self):
        
        i = self._raw_index
        y = self._interp_index
        vario = convert_array_to_unit(self._vario_interp[y], "vario")
        altitude = convert_array_to_unit(self._alt_interp[y], "GNSS_alt")
        time = self._flight['data']['GNSS_time'][i]
        formatted_time = time.strftime("%H:%M")
        ground_speed = convert_array_to_unit(self._speed_interp[y], "GNSS_speed")
        duration = self._flight['data']['GNSS_time'][i] - self._flight['data']['GNSS_time'][0]
        total_seconds = int(duration.total_seconds())

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        formatted_duration = (
            f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        )
        
        self.hud_widget.set_netto(round(vario,2))
        self.hud_widget.set_altitude(round(altitude,2))
        self.hud_widget.set_ground_speed(round(ground_speed,2))
        self.hud_widget.set_time(formatted_time)
        self.hud_widget.set_duration(formatted_duration)
        
    def _update_lcds(self):
        i = self._raw_index
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

        label = [
            self.label_unit_var1_dyna,
            self.label_unit_var2_dyna,
            self.label_unit_var3_dyna,
        ]
        
        for combo, lcd, label in zip(combos, lcds, label):
        
            variable = combo.currentData()
            
            if not variable:
                lcd.display("---")
                label.setText("")
                continue
            
            data = convert_array_to_unit(
            self._flight['data'][variable],
            variable
            )
            
            if i >= len(data):
                continue
            
            value = data[i]
            
            if np.isnan(value):
                lcd.display("---")
            else:
                lcd.display(round(float(value), 2))
                        
    
    def cleanup(self):
        """
        Close correctly the GL widget
        """
        self.model_widget.cleanup()
        
    

    def update_units(self):
        self._update_plot(self.plotwidget_1_dyntab, self._curve1 , self.comboBox_var_1_dyntab, self.label_unit_var1_dyna )
        self._update_plot(self.plotwidget_2_dyntab,self._curve2 , self.comboBox_var_2_dyntab, self.label_unit_var2_dyna)
        self._update_plot(self.plotwidget_3_dyntab, self._curve3 , self.comboBox_var_3_dyntab ,self.label_unit_var3_dyna)
        self.hud_widget.update_units()






class HUDWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.netto = 0.0
        self.ground_speed = 0
        self.time = 0
        self.duration = 0
        self.altitude = 0
        
        self._unit_netto = get_unit("netto")
        self._unit_alt = get_unit("GNSS_alt")
        self._unit_ground_speed = get_unit("GNSS_speed")

        # Transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Le HUD ne bloque pas la souris
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
   
    
    def set_netto(self, value):
        self.netto = round(value,1)
        self.update()
    
    def set_altitude(self, value):
        self.altitude = round(value)
        self.update()
    
    def set_time(self, value):
        self.time = value
        self.update()
    
    def set_duration(self, value):
        self.duration = value
        self.update()
        
    def set_ground_speed(self, value):
        self.ground_speed = round(value,1)
        self.update()


    def update_units(self):
        self._unit_netto = get_unit("netto")
        self._unit_alt = get_unit("GNSS_alt")
        self._unit_ground_speed = get_unit("GNSS_speed")

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
            f"Altitude ({self._unit_alt}) : {self.altitude} "
        )
        
        painter.drawText(
            20,
            80,
            f"Ground Speed ({self._unit_ground_speed}) : {self.ground_speed} "
        )
        
    
        
        if self.netto > 0 :
            painter.drawText(
                self.width() - 80 - 20,
                40,
                f"+{self.netto} {self._unit_netto} "
            )
        else:
            painter.drawText(
                self.width() - 80 - 20,
                40,
                f"{self.netto} {self._unit_netto} "
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
        value = max(-6, min(6, convert_array_to_unit(self.netto, "netto")))

        #normalized = (value + 5) / 10.0

        fill_h = int(mapping(value, -6, 6,0, gauge_h))
        
        x = gauge_x
        y = int(gauge_y + gauge_h - fill_h)
        w = gauge_w
        h = fill_h
        painter.setBrush(QColor(0, 255, 0, 200))
        painter.drawRect(x, y, w, h)

        painter.end()
     