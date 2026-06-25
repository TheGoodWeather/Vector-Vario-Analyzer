from PyQt6 import QtWidgets
import pyqtgraph as pg
import numpy as np
from PyQt6 import QtCore , QtGui
from utils import mapping, rgba_to_hex, hex_to_rgba
from paraglider_widget import ParaGliderWidget
from PyQt6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QMenu, QPushButton, QVBoxLayout, QWidget, QStackedLayout
from units import convert_array_to_unit, get_unit, convert_gps_to_local_xy
from utils import get_label, get_variable, interp_spline, interp_nearest
from PyQt6.QtGui import QAction, QFontMetrics, QPainter, QColor, QPen, QFont
from PyQt6.QtCore import QSettings, Qt

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
                #  checkbox_bearing_vector_dyna,
                 checkbox_vertical_vector_dyna,
                 radioButton_interpolated_dyna,
                 radioButton_raw_dyna,
                 checkBox_show_grid,
                 comboBox_colormap_dyna,
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
        # self.checkbox_bearing_vector_dyna = checkbox_bearing_vector_dyna
        self.checkbox_vertical_vector_dyna = checkbox_vertical_vector_dyna
        self.radioButton_interpolated_dyna = radioButton_interpolated_dyna
        self.radioButton_raw_dyna = radioButton_raw_dyna
        self.checkBox_show_grid = checkBox_show_grid
        self.comboBox_colormap_dyna = comboBox_colormap_dyna
        self.settings = QSettings("Vector Vario", "VVA")

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
        self._vario_interp = None
        self._netto_interp = None
        self._alt_interp = None
        self._wind_dir_interp = None
        self._wind_tilt_interp = None
        self._wind_tilt = None
        self._wind_speed_interp = None

        self.gnss_offset = 0

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


        #COLOR BAR DIALOG

        self.model_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.model_widget.customContextMenuRequested.connect(self._show_context_menu)

        # self.dlg = ColorMapLimits(
        #     np.nanmin(0),
        #     np.nanmax(0),
        #     cmap_name="turbo",
        #     parent=self,
        # )


      
        
        self.comboBox_select_flight_dyntab.currentTextChanged.connect(lambda flight_text : self._fetch_flight(flight_text))
        self.comboBox_var_1_dyntab.currentIndexChanged.connect(lambda: self._update_plot(self.plotwidget_1_dyntab, self._curve1 , self.comboBox_var_1_dyntab, self.label_unit_var1_dyna ))
        self.comboBox_var_2_dyntab.currentIndexChanged.connect(lambda: self._update_plot(self.plotwidget_2_dyntab,self._curve2 , self.comboBox_var_2_dyntab, self.label_unit_var2_dyna))
        self.comboBox_var_3_dyntab.currentIndexChanged.connect(lambda: self._update_plot(self.plotwidget_3_dyntab, self._curve3 , self.comboBox_var_3_dyntab ,self.label_unit_var3_dyna))
        self.comboBox_colormap_dyna.currentIndexChanged.connect(lambda: self._set_color_trajectory())

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
        self.checkbox_wind_vector_dyna.stateChanged.connect(lambda state: self._change_checkbox_color(state, checkbox_wind_vector_dyna, rgba_to_hex(0.3, 0.6, 1.0, 0.8)))
        self.checkbox_wind_vector_dyna.setChecked(True)
        self.checkbox_north_vector_dyna.stateChanged.connect(lambda state: self.model_widget.set_visibility_north_vector(state))
        self.checkbox_north_vector_dyna.stateChanged.connect(lambda state: self._change_checkbox_color(state, checkbox_north_vector_dyna, rgba_to_hex(1.0, 0.2, 0.2, 0.8)))
        self.checkbox_north_vector_dyna.setChecked(False)
        self.checkbox_tas_vector_dyna.stateChanged.connect(lambda state: self.model_widget.set_visibility_tas_vector(state))
        self.checkbox_tas_vector_dyna.stateChanged.connect(lambda state: self._change_checkbox_color(state, checkbox_tas_vector_dyna, rgba_to_hex(0.3, 1.0, 0.5, 0.8)))
        self.checkbox_tas_vector_dyna.setChecked(False)
        # self.checkbox_bearing_vector_dyna.stateChanged.connect(lambda state: self.model_widget.set_visibility_bearing_vector(state))
        # self.checkbox_bearing_vector_dyna.stateChanged.connect(lambda state: self._change_checkbox_color(state, checkbox_bearing_vector_dyna, rgba_to_hex(0.3, 1.0, 0.5, 0.8)))
        # self.checkbox_bearing_vector_dyna.setChecked(False)
        self.checkbox_vertical_vector_dyna.stateChanged.connect(lambda state: self.model_widget.set_visibility_vertical_vector(state))
        self.checkbox_vertical_vector_dyna.stateChanged.connect(lambda state: self._change_checkbox_color(state, checkbox_vertical_vector_dyna, rgba_to_hex(0.3,0.4, 0.5, 0.8)))
        self.checkbox_vertical_vector_dyna.setChecked(False)

        self.checkBox_show_grid.stateChanged.connect(lambda state: self.model_widget.show_grid(state))
        self.checkBox_show_grid.setChecked(True)

        self.radioButton_interpolated_dyna.toggled.connect(lambda state : self.change_interpolation(state))
        #self.radioButton_interpolated_dyna.setChecked(True)

        self._play_timer = QtCore.QTimer()
        self._play_timer.timeout.connect(self._play_step)
        self._elapsed_timer = QtCore.QElapsedTimer()
        
        self._playback_speed = 1.0   # 0.5 / 1 / 2
        self._play_elapsed = 0.0     # temps simulé écoulé
        
        self._setup_keyboard_shortcuts()

    def _setup_keyboard_shortcuts(self):
        # Keyboard events management
        app = QtCore.QCoreApplication.instance()
        app.installEventFilter(self)
        # app.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # app.setFocus()

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Space:
                self._on_space_pressed()
                return True   # événement consommé, ne se propage pas
        return super().eventFilter(obj, event)

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
       
        self.plotwidget_1_dyntab.scene().sigMouseClicked.connect(lambda event: self._on_graph_clicked(event,self.plotwidget_1_dyntab))
        self.plotwidget_2_dyntab.scene().sigMouseClicked.connect(lambda event: self._on_graph_clicked(event,self.plotwidget_2_dyntab))
        self.plotwidget_3_dyntab.scene().sigMouseClicked.connect(lambda event: self._on_graph_clicked(event,self.plotwidget_3_dyntab ))
                                                         
                                                                 
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
                pen=pg.mkPen(QColor(0,0,0), width=3)
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
            self._return_min_radius()
            self._set_time(0.0)


            self.comboBox_var_1_dyntab.setCurrentIndex(self.comboBox_var_1_dyntab.findData("compass_head"))
            self.comboBox_var_2_dyntab.setCurrentIndex(self.comboBox_var_1_dyntab.findData("pitch"))
            self.comboBox_var_3_dyntab.setCurrentIndex(self.comboBox_var_1_dyntab.findData("roll"))

            #set by default the color mapping with g_force
            index = self.comboBox_colormap_dyna.findData("G_force")
            if index >= 0:
                self.comboBox_colormap_dyna.setCurrentIndex(index)
            
            # self.model_widget.set_color_trajectory(self._alt_interp)

    def set_color_trajectory(self, v_min : float = None, v_max : float = None):
        """
        Choose a variable and send it to paraglider_widget to plot it colormapped
        """
        variable = self.comboBox_colormap_dyna.currentData()
        if variable is not None:
            z = self._flight['data'][variable]
            if self.radioButton_interpolated_dyna.isChecked():
                z_interp = interp_spline(self._time_interp, self._time_raw, z) 
            else :
                z_interp = interp_nearest(self._time_interp,self._time_raw,  z) 
            to_mapped = True
        else:
            z_interp = None
            to_mapped = False
        self.model_widget.set_color_trajectory(z_interp, to_mapped, v_min, v_max)

    def _interpolate_data(self, method = 'spline'):
        """
        This function interpolate the data accordingly to fps (30 by default).
        The interpolation can be spline (cubic) or nearest to preserve the "raw" data.
        Moreover, we are applying a GNSS offset to IGC file that can be changed. 
        """
        if method == 'spline':
            def interp(time_origine, time_interp, variable_to_interp):
                return interp_spline(time_origine, time_interp, variable_to_interp)
        else :
            def interp(time_origine, time_interp, variable_to_interp):
                return interp_nearest(time_origine, time_interp, variable_to_interp)


        def interp_and_shift(arr):
            result = interp(self._time_interp, t_seconds, arr)
            if gnss_shift == 0:
                return result
            shifted = np.roll(result, -gnss_shift)
            if gnss_shift > 0:
                shifted[-gnss_shift:] = result[-1]
            else:
                shifted[:-gnss_shift] = result[0]
            return shifted

    
        if self._flight['file_name'].split('.')[1] == "igc" or self._flight['file_name'].split('.')[1] == "IGC":
            self.gnss_offset = 0.8 # At 0 for the moment, can be modified in the future when we will know more about gnss_lag
            z_data = self._flight['data']['QNS_alt']
        else: 
            self.gnss_offset = 0 
            z_data = self._flight['data']['GNSS_alt']   

        times = self._flight['data']['GNSS_time']

        # Number of iterations to offset according to a lag in seconds 
        gnss_shift = int(round(self.gnss_offset * fps))

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

        

        self._pitch_interp =  interp(
            self._time_interp,
            t_seconds,
            self._flight['data']['pitch']
        )

        self._roll_interp =  interp(
            self._time_interp,
            t_seconds,
            self._flight['data']['roll']
        )

        yaw = np.unwrap(
            np.radians(
                self._flight['data']['compass_head']
            )
        )
        yaw_interp =  interp(
            self._time_interp,
            t_seconds,
            yaw
        )
        self._yaw_interp = np.degrees(yaw_interp)

        _x_local, _y_local = convert_gps_to_local_xy(self._flight['data']['GNSS_lon'], self._flight['data']['GNSS_lat'])

        self._x_interp     = interp_and_shift(_x_local)
        self._y_interp     = interp_and_shift(_y_local)

        self._z_interp =  interp(
            self._time_interp,
            t_seconds,
            z_data,
        ) 

        self.model_widget.set_trajectory(
            self._x_interp ,
            self._y_interp ,
            self._z_interp,
        )

        self._netto_interp =  interp(
            self._time_interp,
            t_seconds,
            self._flight['data']['netto']
        )

        self._alt_interp   = interp_and_shift(self._flight['data']['GNSS_alt'])

        self._speed_interp = interp_and_shift(self._flight['data']['GNSS_speed'])

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
        wind_dir_interp =  interp(
            self._time_interp,
            t_seconds,
            wind_dir
        )
        self._wind_dir_interp = np.degrees(wind_dir_interp)


        self._wind_tilt_interp =  interp(
            self._time_interp,
            t_seconds,
            self._wind_tilt)
        
        self._wind_speed_interp =  interp(
            self._time_interp,
            t_seconds,
            self._flight['data']['wind_vel']
        )

        self._tas_interp =  interp(
            self._time_interp,
            t_seconds,
            self._flight['data']['TAS']
        )

        self._vario_interp =  interp(
            self._time_interp,
            t_seconds,
            self._flight['data']['vario']
        )
        self._G_force_interp =  interp(
            self._time_interp,
            t_seconds,
            self._flight['data']['G_force']
        )

        # REMOVED FOR V0.03 BECAUSE NOT WORKING WHEN GNSS IS NAN 

        # gnss_heading = np.unwrap(
        #     np.radians(
        #         self._flight['data']['GNSS_head']
        #     )
        # )
        # gnss_heading_interp = interp_and_shift(gnss_heading)
        # self._gnss_heading_interp = np.degrees(gnss_heading_interp)

      

    

    
    def _populate_var_combobox(self):
        for combobox in [self.comboBox_var_1_dyntab, self.comboBox_var_2_dyntab, self.comboBox_var_3_dyntab, self.comboBox_colormap_dyna]:
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
        
        self._update_lcds()

    
    def _cursor_moved(self, line):

        self._raw_index = int(line.value())

        # sécurité
        self._raw_index = np.clip(
            self._raw_index,
            0,
            len(self._time_raw) - 1
        )

        # convertir raw index → temps
        self._current_time = self._time_raw[self._raw_index]

        # convertir temps → index interpolé
        self._interp_index = int(self._current_time * fps)

        self._interp_index = np.clip(
            self._interp_index,
            0,
            len(self._time_interp) - 1
        )
        # sync UI
        self._update_cursor()
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
        # bearing = self._gnss_heading_interp[i]
        


        self.model_widget.set_attitude(pitch =pitch, roll = roll, yaw= yaw)
        self.model_widget.set_position(x,y,z)
        self.model_widget.set_wind_vector(wind_azimut,wind_tilt, wind_speed)
        self.model_widget.set_tas_vector(yaw, tas)
        # self.model_widget.set_bearing_vector(bearing,gnss_speed)
        
        

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
        if not self._play_timer.isActive():
            self.pushButton_pause.setChecked(False)
            self.pushButton_play.setChecked(True)
            self._elapsed_timer.restart()
            self._play_timer.start(16)   # vise 60 Hz, on régule nous-mêmes
            # self._play_timer.start(int(1000 / fps))
        
    def pause(self):
        if self._play_timer.isActive():
            self._play_timer.stop()
            self.pushButton_pause.setChecked(True)
            self.pushButton_play.setChecked(False)
    
    def change_speed(self):
        

        speeds = [0.5, 1, 2, 5, 10]
        current_index = speeds.index(self._playback_speed)
        current_index = (current_index + 1) % len(speeds)
        self._playback_speed = speeds[current_index]
        self.pushButton_speed.setText(f"x{self._playback_speed}")

    def update_data_set(self, dataset):
        self.flight_data_set = dataset
        self._fetch_flight(self.comboBox_select_flight_dyntab.currentText())
        
        
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
        
       
    def _on_space_pressed(self):
        if self._flight is None:
            return
        if self._play_timer.isActive():
            self.pause()
        else:
            self.play()

    
    def _update_hud(self):
        
        i = self._raw_index
        y = self._interp_index
        vario = convert_array_to_unit(self._vario_interp[y], "vario")
        altitude = convert_array_to_unit(self._alt_interp[y], "GNSS_alt")
        roll = convert_array_to_unit(self._roll_interp[y], "roll")
        pitch = convert_array_to_unit(self._pitch_interp[y], "pitch")
        time = self._flight['data']['GNSS_time'][i]
        formatted_time = time.strftime("%d-%m-%Y %H:%M")
        ground_speed = convert_array_to_unit(self._speed_interp[y], "GNSS_speed")
        duration = self._flight['data']['GNSS_time'][i] - self._flight['data']['GNSS_time'][0]
        total_seconds = int(duration.total_seconds())
        G_force = self._G_force_interp[y];

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        formatted_duration = (
            f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        )
        
        self.hud_widget.set_vario(round(vario,2))
        self.hud_widget.set_G_force(round(G_force,1))
        self.hud_widget.set_altitude(round(altitude,2))
        self.hud_widget.set_ground_speed(round(ground_speed,2))
        self.hud_widget.set_time(formatted_time)
        self.hud_widget.set_duration(formatted_duration)
        self.hud_widget.set_pitch(round(pitch,0))
        self.hud_widget.set_roll(round(roll,0))
        
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
                if variable == 'G_force':
                    lcd.display(round(float(value), 3))
                else:
                    lcd.display(round(float(value), 2))

    def _on_graph_clicked(self, event, plot_widget):

        pos = event.scenePos()
        vb = plot_widget.getViewBox()
        
        mouse_point = vb.mapSceneToView(pos)
        self._raw_index = int(mouse_point.x())
        # sécurité

        self._raw_index = np.clip(
            self._raw_index,
            0,
            len(self._time_raw) - 1
        )

        # convertir raw index → temps
        self._current_time = self._time_raw[self._raw_index]

        # convertir temps → index interpolé
        self._interp_index = int(self._current_time * fps)

        self._interp_index = np.clip(
            self._interp_index,
            0,
            len(self._time_interp) - 1
        )
        # sync UI
        self._update_cursor()
        self._update_model()
        self._update_lcds()
        self._update_hud()
        
    

    def _return_min_radius(self, step: int = 10) -> float:
        """
        Returns the size of the flight in order to create a grid model that suits bests
        """
        rad_x = abs(np.max(self._x_interp) - np.min(self._x_interp))
        rad_y = abs(np.max(self._y_interp) - np.min(self._y_interp))
        rad_z = abs(np.max(self._z_interp) - np.min(self._z_interp))

        coeff_z = mapping(np.max(self._z_interp),0, 6000, 1, 3)
        # coeff_z = 1
        origin_x = np.min(self._x_interp) + rad_x / 2
        origin_y = np.min(self._y_interp) + rad_y / 2
        len_x = rad_x * coeff_z
        len_y = rad_y * coeff_z 
        self.model_widget.set_len_grid(origin_x, origin_y, len_x, len_y)

    def _change_checkbox_color(self, state, checkbox, color: str):
        if state :
            r, g, b, _ = hex_to_rgba(color)
            bg = f'rgba({int(r*255)}, {int(g*255)}, {int(b*255)}, 0.35)'
        else :
            bg = 'white'

        checkbox.setStyleSheet(f"""
        QCheckBox {{
            background-color: {bg};
            border-radius: 4px;
            padding: 2px 6px;
        }}
        """)

    def _show_context_menu(self, pos):

        menu = QMenu(self.model_widget)
        print('here')
        # --- Action : set color map limit ---
        action_all = QAction("Set color mapping limits",self.model_widget )
        action_all.setEnabled(True)
        action_all.triggered.connect(self._show_color_limits_dialog)
        
        menu.addAction(action_all)
        menu.exec(self.model_widget.mapToGlobal(pos))

    def _show_color_limits_dialog(self):
        self.dlg.exec()

        vmin, vmax = self.dlg.limits()
        self._update_colorbar_3d
        
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
        


    def change_interpolation(self, state):
        if state: #by default we set the interpolation to spline
            self._interpolate_data('spline')
        else:
            self._interpolate_data('nearest')

    def apply_color_change(self):
        self.model_widget.apply_color_changes()
        # We reset the combobox color mapping 
        self.comboBox_colormap_dyna.setCurrentIndex(0)




class HUDWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.vario = 0.0
        self.ground_speed = 0
        self.time = 0
        self.duration = 0
        self.altitude = 0
        self.roll = 0.0
        self.pitch = 0.0 
        self.G_force = 0.0        
        self._unit_vario = get_unit("vario")
        self._unit_alt = get_unit("GNSS_alt")
        self._unit_ground_speed = get_unit("GNSS_speed")
        self._unit_angle = get_unit("roll")

        # Transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Le HUD ne bloque pas la souris
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
   
    def set_G_force(self, value):
            self.G_force = round(value,1)
            self.update()    
    def set_vario(self, value):
        self.vario = round(value,1)
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
        self.ground_speed = round(value,0)
        self.update()

    def set_roll(self, value):
        self.roll = round(value,0)
        self.update()

    def set_pitch(self, value):
        self.pitch = round(value,0)
        self.update()


    def update_units(self):
        self._unit_vario = get_unit("vario")
        self._unit_alt = get_unit("GNSS_alt")
        self._unit_ground_speed = get_unit("GNSS_speed")
        self._unit_angle = get_unit("roll")



    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        
        fm = QFontMetrics(font)

        # -------------------------------------------------
        # DONNÉES
        # -------------------------------------------------

        sign = "+" if self.vario > 0 else ""
        fields = [
            ("Altitude",     f"{self.altitude} {self._unit_alt}"),
            ("Ground Speed", f"{self.ground_speed} {self._unit_ground_speed}"),
            ("Roll",         f"{self.roll} {self._unit_angle}"),
            ("Pitch",        f"{self.pitch} {self._unit_angle}"),
            ("G_force",      f"{self.G_force}"),
            ("Time",         f"{self.time}"),
            ("Duration",     f"{self.duration}"),
        ]
        texts = [f"{label} : {value}" for label, value in fields]

        # -------------------------------------------------
        # SEUIL : largeur minimale pour tenir en 3 colonnes
        # -------------------------------------------------

        col_width   = max(fm.horizontalAdvance(t) for t in texts) + 20
        gauge_space = 100   # réservé pour la jauge à droite
        needed_3col = col_width * 3 + gauge_space

        w = self.width()
        margin_x = 20
        margin_y = 30
        line_h   = fm.height() + 10

        # -------------------------------------------------
        # LAYOUT : 3 colonnes × 2 lignes  ou  1 colonne × N lignes
        # -------------------------------------------------

        if w >= needed_3col:
            # 3 colonnes, 2 lignes — disposition originale
            positions = [
                (margin_x,           margin_y),           # Altitude
                (margin_x,           margin_y + line_h),  # Ground Speed
                (margin_x + col_width,     margin_y),     # Roll
                (margin_x + col_width,     margin_y + line_h),  # Pitch
                (margin_x + col_width * 2, margin_y),     # Time
                (margin_x + col_width * 2, margin_y + line_h),  # Duration
            ]
        else:
            # 1 colonne, N lignes
            positions = [
                (margin_x, margin_y + i * line_h)
                for i in range(len(texts))
            ]

        # -------------------------------------------------
        # TEXT
        # -------------------------------------------------

        for text, (x, y) in zip(texts, positions):
            # ombre
            painter.setPen(QPen(QColor(0, 0, 0, 180)))
            painter.drawText(x + 1, y , text)
            # texte blanc par-dessus
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(x, y, text)

        # -------------------------------------------------
        # VARIO GAUGE
        # -------------------------------------------------

        gauge_x = self.width() - 80
        gauge_y = 50
        gauge_h = 200
        gauge_w = 20

        # fond
        painter.setBrush(QColor(40, 40, 40, 180))
        painter.drawRect(gauge_x, gauge_y, gauge_w, gauge_h)

        # valeur
        value = max(-10, min(10, convert_array_to_unit(self.vario, "vario")))

        #normalized = (value + 5) / 10.0

        fill_h = int(mapping(value, -10, 10,0, gauge_h))
        
        x = gauge_x
        y = int(gauge_y + gauge_h - fill_h)
        w = gauge_w
        h = fill_h
        if self.vario >= 0 :
            painter.setBrush(QColor(0, 255, 0, 200))
        else :
            painter.setBrush(QColor(255, 0, 0, 200))
        painter.drawRect(x, y, w, h)

        # Label Vario — ombre + blanc
        sign = "+" if self.vario > 0 else ""
        vario_text = f"{sign}{self.vario} {self._unit_vario}"

        for label, tx, ty in [("Vario", gauge_x - 7, gauge_y - 25),
                            (vario_text, gauge_x - 9, gauge_y - 10)]:
            painter.setPen(QPen(QColor(0, 0, 0, 180)))
            painter.drawText(tx + 1, ty + 1, label)
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(tx, ty, label)

        painter.end()


class ColorMapLimits(QtWidgets.QDialog):
    def __init__(
        self,
        vmin,
        vmax,
        cmap_name="turbo",
        parent=None,
    ):
        super().__init__()

        self.setWindowTitle("Color mapping limits")
        self.resize(450, 220)

        layout = QVBoxLayout(self)

        # --------------------------
        # Color bar
        # --------------------------

        self.graphics = pg.GraphicsLayoutWidget()

        self.cmap = pg.colormap.get(cmap_name)

        self.colorbar = pg.ColorBarItem(
            values=(vmin, vmax),
            colorMap=self.cmap,
            interactive=False,
            orientation="horizontal",
        )

        self.colorbar.setImageItem(None)

        self.graphics.addItem(self.colorbar)

        layout.addWidget(self.graphics)

        # --------------------------
        # Spinboxes
        # --------------------------

        spin_layout = QHBoxLayout()

        spin_layout.addWidget(QLabel("Min"))

        self.spin_min = QDoubleSpinBox()
        self.spin_min.setDecimals(2)
        self.spin_min.setRange(-1e9, 1e9)
        self.spin_min.setValue(vmin)

        spin_layout.addWidget(self.spin_min)

        spin_layout.addSpacing(20)

        spin_layout.addWidget(QLabel("Max"))

        self.spin_max = QDoubleSpinBox()
        self.spin_max.setDecimals(2)
        self.spin_max.setRange(-1e9, 1e9)
        self.spin_max.setValue(vmax)

        spin_layout.addWidget(self.spin_max)

        layout.addLayout(spin_layout)


        # --------------------------
        # Connections
        # --------------------------

        self.spin_min.valueChanged.connect(self._update_colorbar)
        self.spin_max.valueChanged.connect(self._update_colorbar)

    def _update_colorbar(self):

        vmin = self.spin_min.value()
        vmax = self.spin_max.value()

        if vmin >= vmax:
            return

        self.colorbar.setLevels((vmin, vmax))

    def limits(self):
        return (
            self.spin_min.value(),
            self.spin_max.value(),
        )