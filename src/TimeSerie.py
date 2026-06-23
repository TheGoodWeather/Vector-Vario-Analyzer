
from PyQt6 import QtWidgets
import pyqtgraph as pg
import numpy as np
from PyQt6 import QtCore
from PyQt6.QtWidgets import QHeaderView, QTableWidgetItem
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtCore import Qt

from units import convert_array_to_unit, get_unit
from utils import get_label


class TimeSerie:
    """Gère les deux graphiques 1D (graph1_tab1D / graph2_tab1D) et leurs
    tables de variables associées."""

    MAX_CHECKED_VARIABLES = 2
    CLICK_TOLERANCE_PX = 20

    def __init__(self,
                 flight,
                 graph1_tab1D,
                 graph2_tab1D,
                 comboBox_flight_tab1D,
                 tableWidget_variable_plot1,
                 tableWidget_variable_plot2,
                 checkBox_x_axis_link,
                 ):
        self.flight = flight
        self.graph1_tab1D = graph1_tab1D
        self.graph2_tab1D = graph2_tab1D
        self.comboBox_flight_tab1D = comboBox_flight_tab1D
        self.tableWidget_variable_plot1 = tableWidget_variable_plot1
        self.tableWidget_variable_plot2 = tableWidget_variable_plot2
        self.checkBox_x_axis_link = checkBox_x_axis_link

        self._gnss_ts_cache = {}

        self._setup_widgets()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------
    def _setup_widgets(self):
        self._init_plot(self.graph1_tab1D, crosshair_id="1")
        self._init_plot(self.graph2_tab1D, crosshair_id="2")

        self.curve_1D_11 = self.graph1_tab1D.plot([], [])
        self.curve_1D_12 = self.graph1_tab1D.plot([], [])
        self.curve_1D_21 = self.graph2_tab1D.plot([], [])
        self.curve_1D_22 = self.graph2_tab1D.plot([], [])

        self.comboBox_flight_tab1D.currentTextChanged.connect(self._populate_table_1D_variable)
        self.comboBox_flight_tab1D.currentTextChanged.connect(self._restore_checked_variables_1D)
        self.comboBox_flight_tab1D.currentTextChanged.connect(
            lambda: self._update_1D_plot(self.tableWidget_variable_plot1, self.graph1_tab1D,
                                          self.curve_1D_11, self.curve_1D_12)
        )
        self.comboBox_flight_tab1D.currentTextChanged.connect(
            lambda: self._update_1D_plot(self.tableWidget_variable_plot2, self.graph2_tab1D,
                                          self.curve_1D_21, self.curve_1D_22)
        )

        self.tableWidget_variable_plot1.itemChanged.connect(self._on_item_table_1D_changed)
        self.tableWidget_variable_plot2.itemChanged.connect(self._on_item_table_1D_changed)

        self.checkBox_x_axis_link.stateChanged.connect(self._toggle_x_link)

        self._setup_table(self.tableWidget_variable_plot1)
        self._setup_table(self.tableWidget_variable_plot2)

        self.graph1_tab1D.scene().sigMouseClicked.connect(
            lambda event: self._on_1D_point_clicked(event, self.graph1_tab1D, self.tableWidget_variable_plot1)
        )
        self.graph2_tab1D.scene().sigMouseClicked.connect(
            lambda event: self._on_1D_point_clicked(event, self.graph2_tab1D, self.tableWidget_variable_plot2)
        )

        self.graph1_tab1D.getViewBox().sigRangeChanged.connect(
        lambda: self._reposition_crosshair_edge_labels(self.graph1_tab1D)
        )
        self.graph2_tab1D.getViewBox().sigRangeChanged.connect(
            lambda: self._reposition_crosshair_edge_labels(self.graph2_tab1D)
        )

    def _init_plot(self, plot_widget, crosshair_id):
        """Initialisation commune aux deux graphiques 1D."""
        plot_widget.setBackground("w")
        plot_widget.setLabel('left', 'No variable selected')
        plot_widget.setLabel('bottom', 'GNSS Time (s)')
        plot_widget.setTitle("Select a variable to plot in time")
        plot_widget.showGrid(x=True, y=True, alpha=0.3)
        plot_widget.setEnabled(True)
        plot_widget.crosshair_id = crosshair_id
        plot_widget.enableAutoRange(True)
        plot_widget.setAxisItems({'bottom': pg.graphicsItems.DateAxisItem.DateAxisItem(orientation='bottom')})

    def _setup_table(self, table_widget):
        """Initialisation commune aux deux tables de variables."""
        headers = ["Variable", "Value", "Unit"]
        table_widget.setColumnCount(len(headers))
        table_widget.setHorizontalHeaderLabels(headers)
        table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        table_widget.resizeColumnsToContents()

    # ------------------------------------------------------------------
    # Helpers de recherche de vol
    # ------------------------------------------------------------------
    def _find_flight(self, name):
        """Retourne le dict du vol correspondant à `name` (nom de fichier ou
        alias), ou None si aucun vol ne correspond."""
        for flight in self.flight:
            if flight['file_name'].split(".")[0] == name or flight['metadata']['alias'] == name:
                return flight
        return None

    def _get_gnss_timestamps(self, flight):
        """Retourne (et met en cache) le GNSS_time de `flight` sous forme de
        tableau numpy de timestamps POSIX."""
        key = id(flight)
        cached = self._gnss_ts_cache.get(key)
        if cached is None or len(cached) != len(flight['data']['GNSS_time']):
            cached = np.array([t.timestamp() for t in flight['data']['GNSS_time']])
            self._gnss_ts_cache[key] = cached
        return cached

    # ------------------------------------------------------------------
    # Gestion du clic / crosshair
    # ------------------------------------------------------------------
    def _on_1D_point_clicked(self, event, plot_widget, table_data):
        """
        Affiche un crosshair au point le plus proche du clic, et met à jour
        la table avec les valeurs correspondantes. Retire le crosshair si le
        clic est trop loin de tout point.
        """
        flight_selected = self.comboBox_flight_tab1D.currentText()
        variables_checked = self._get_checked_variables(table_data)
        if not variables_checked:
            return

        flight_selected_dic = self._find_flight(flight_selected)
        if flight_selected_dic is None:
            return

        crosshair_id = plot_widget.crosshair_id
        vb = plot_widget.getViewBox()
        pos = event.scenePos()
        mouse_point = vb.mapSceneToView(pos)
        x_click = mouse_point.x()

        gnss_ts = self._get_gnss_timestamps(flight_selected_dic)
        idx = int(np.clip(np.searchsorted(gnss_ts, x_click), 0, len(gnss_ts) - 1))

        dist = []
        for variable in variables_checked:
            x_val = gnss_ts[idx]
            y_val = convert_array_to_unit(flight_selected_dic['data'][variable], variable)[idx]
            point_scene = vb.mapViewToScene(QtCore.QPointF(x_val, y_val))
            d = np.hypot(pos.x() - point_scene.x(), pos.y() - point_scene.y())  # distance euclidienne en pixels
            dist.append((d, variable))

        closest_distance, closest_variable = min(dist, key=lambda x: x[0])

        if closest_distance < self.CLICK_TOLERANCE_PX:  # clic à moins de 20 pixels d'un point
            self._show_crosshair(flight_selected_dic, plot_widget, crosshair_id, idx, closest_variable, gnss_ts)
            self._fill_table_values(table_data, flight_selected_dic, idx)
        else:
            self._clear_table_values(table_data)
            self._remove_crosshair_for_flight(flight_selected_dic, plot_widget, f"time_{crosshair_id}")

    def _show_crosshair(self, flight, plot_widget, crosshair_id, idx, closest_variable, gnss_ts):
            """
            Affiche/déplace le crosshair (lignes verticale + horizontale) ainsi
            que 2 étiquettes texte au point cliqué :
            - une étiquette "date" (GNSS time formaté), ancrée juste au-dessus
                du point ;
            - une étiquette "valeur" (variable + valeur + unité), ancrée juste
                en dessous du point.
            Les étiquettes sont positionnées en coordonnées de données (pas en
            pixels), donc elles restent correctement alignées sur le point même
            après un zoom/pan.
            """
            v_key = f'crosshair_v_time_{crosshair_id}'
            h_key = f'crosshair_h_time_{crosshair_id}'
            date_label_key = f'crosshair_label_date_time_{crosshair_id}'
            value_label_key = f'crosshair_label_value_time_{crosshair_id}'
    
            # Conversion d'unité faite sur le tableau complet puis indexée, pour
            # rester cohérent avec le reste du fichier (convert_array_to_unit
            # attend un tableau, pas un float isolé).
            y_val = float(convert_array_to_unit(flight['data'][closest_variable], closest_variable)[idx])
            x_val = float(gnss_ts[idx])
    
            date_str = flight['data']['GNSS_time'][idx].strftime("%Y-%m-%d %H:%M:%S")
            value_str = f"{get_label(closest_variable)} : {round(y_val, 2)} {get_unit(closest_variable)}"
    
            (x_min, x_max), (y_min, y_max) = plot_widget.getViewBox().viewRange()
    
            if flight['plot'].get(v_key) is None:
                pen = pg.mkPen(QColor(0, 0, 0), width=1, style=QtCore.Qt.PenStyle.DashLine)
                crosshair_v = pg.InfiniteLine(angle=90, movable=False, pen=pen)
                crosshair_h = pg.InfiniteLine(angle=0, movable=False, pen=pen)
                plot_widget.addItem(crosshair_v, ignoreBounds=True)
                plot_widget.addItem(crosshair_h, ignoreBounds=True)
                flight['plot'][v_key] = crosshair_v
                flight['plot'][h_key] = crosshair_h
    
                label_border = pg.mkPen(QColor(0, 0, 0))
                label_fill = pg.mkBrush(255, 255, 255, 200)
                # anchor=(0.5, 1) : le bas du texte est calé sur y_min -> le
                # texte reste visible juste au-dessus du bord bas.
                date_label = pg.TextItem(text=date_str, color=(0, 0, 0), anchor=(0.5, 1),
                                        border=label_border, fill=label_fill)
                # anchor=(0, 0.5) : le bord gauche du texte est calé sur x_min ->
                # le texte reste visible juste à droite du bord gauche.
                value_label = pg.TextItem(text=value_str, color=(0, 0, 0), anchor=(0, 0.5),
                                        border=label_border, fill=label_fill)
                plot_widget.addItem(date_label, ignoreBounds=True)
                plot_widget.addItem(value_label, ignoreBounds=True)
                flight['plot'][date_label_key] = date_label
                flight['plot'][value_label_key] = value_label
    
            flight['plot'][v_key].setValue(x_val)
            flight['plot'][h_key].setValue(y_val)
    
            flight['plot'][date_label_key].setText(date_str)
            flight['plot'][date_label_key].setPos(x_val, y_min)  # aligné en X sur le point, collé en bas
    
            flight['plot'][value_label_key].setText(value_str)
            flight['plot'][value_label_key].setPos(x_min, y_val)  # aligné en Y sur le point, collé à gauche


    def _reposition_crosshair_edge_labels(self, plot_widget):
        """
        Recolle les étiquettes date/valeur du crosshair (s'il y en a un)
        respectivement au bord bas et au bord gauche de `plot_widget` quand
        la vue change (zoom, pan, autoRange). L'alignement X (date) / Y
        (valeur) sur le point cliqué est préservé : seule la coordonnée
        "bord" est mise à jour.
        """
        crosshair_id = plot_widget.crosshair_id
        (x_min, x_max), (y_min, y_max) = plot_widget.getViewBox().viewRange()
        date_label_key = f'crosshair_label_date_time_{crosshair_id}'
        value_label_key = f'crosshair_label_value_time_{crosshair_id}'
 
        for flight in self.flight:
            date_label = flight['plot'].get(date_label_key)
            if date_label is not None:
                date_label.setPos(date_label.pos().x(), y_min)
 
            value_label = flight['plot'].get(value_label_key)
            if value_label is not None:
                value_label.setPos(x_min, value_label.pos().y())

    def _fill_table_values(self, table_data, flight, idx):
        for row in range(table_data.rowCount()):
            variable = table_data.item(row, 0).data(Qt.ItemDataRole.UserRole)
            value = convert_array_to_unit(flight['data'][variable], variable)[idx]

            text = str(round(value, 2)) if isinstance(value, float) else str(value)
            item_value = QTableWidgetItem(text)
            item_value.setFlags(item_value.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table_data.setItem(row, 1, item_value)

            item_unit = QTableWidgetItem(get_unit(variable))
            item_unit.setFlags(item_unit.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table_data.setItem(row, 2, item_unit)

    def _clear_table_values(self, table_data):
        for row in range(table_data.rowCount()):
            table_data.setItem(row, 1, QTableWidgetItem(""))
            table_data.setItem(row, 2, QTableWidgetItem(""))

    def _remove_crosshair_for_flight(self, flight, plot_widget, crosshair):
        keys = (
            f"crosshair_v_{crosshair}",
            f"crosshair_h_{crosshair}",
            f"crosshair_label_date_{crosshair}",
            f"crosshair_label_value_{crosshair}",
        )
        if flight['plot'].get(keys[0]) is not None:
            for key in keys:
                item = flight['plot'].get(key)
                if item is not None:
                    plot_widget.removeItem(item)
                    flight['plot'][key] = None

    def _remove_crosshair(self, plot_widget, crosshair):
        """Retire le crosshair `crosshair` (ex: "time_1") de `plot_widget`,
        pour tous les vols (sécurité en cas de changement de vol affiché)."""
        for flight in self.flight:
            self._remove_crosshair_for_flight(flight, plot_widget, crosshair)


    # ------------------------------------------------------------------
    # Tables de variables
    # ------------------------------------------------------------------
    def _get_checked_variables(self, table_widget):
        """Retourne la liste des variables cochées dans `table_widget`."""
        checked_vars = []
        for row in range(table_widget.rowCount()):
            item = table_widget.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                checked_vars.append(item.data(Qt.ItemDataRole.UserRole))
        return checked_vars

    def _toggle_x_link(self):
        if self.checkBox_x_axis_link.isChecked():
            self.graph2_tab1D.setXLink(self.graph1_tab1D)
        else:
            self.graph2_tab1D.setXLink(None)

    def _populate_table_1D_variable(self, choice):
        """Reconstruit les deux tables de variables pour le vol `choice`."""
        self.tableWidget_variable_plot1.blockSignals(True)
        self.tableWidget_variable_plot2.blockSignals(True)
        self.tableWidget_variable_plot1.setRowCount(0)
        self.tableWidget_variable_plot2.setRowCount(0)

        flight = self._find_flight(choice)
        if not flight:
            return
        if flight['is_data_processed'] and flight['data']:
            row = 0
            for variable, data in flight['data'].items():
                if variable == 'GNSS_time':
                    continue
                if len(data) == 0 or np.all(np.isnan(data)):
                    continue

                self.tableWidget_variable_plot1.insertRow(row)
                self.tableWidget_variable_plot2.insertRow(row)

                for table in (self.tableWidget_variable_plot1, self.tableWidget_variable_plot2):
                    item = QTableWidgetItem(get_label(variable))
                    item.setData(Qt.ItemDataRole.UserRole, variable)
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    item.setCheckState(Qt.CheckState.Unchecked)
                    table.setItem(row, 0, item)

                row += 1
        else:
            return
        
        self.tableWidget_variable_plot1.sortItems(0, Qt.SortOrder.AscendingOrder)
        self.tableWidget_variable_plot2.sortItems(0, Qt.SortOrder.AscendingOrder)

        self.tableWidget_variable_plot1.blockSignals(False)
        self.tableWidget_variable_plot2.blockSignals(False)

    def _update_unit_table_variable(self, choice):
        """"Only update values and units"""""
        flight = self._find_flight(choice)
        if flight is None:
            return
 
        for table_widget, crosshair_id in (
            (self.tableWidget_variable_plot1, "1"),
            (self.tableWidget_variable_plot2, "2"),
        ):
            table_widget.blockSignals(True)
 
            crosshair_v = flight['plot'].get(f'crosshair_v_time_{crosshair_id}')
            idx = None
            if crosshair_v is not None:
                gnss_ts = self._get_gnss_timestamps(flight)
                idx = int(np.clip(np.searchsorted(gnss_ts, crosshair_v.value()), 0, len(gnss_ts) - 1))
 
            for row in range(table_widget.rowCount()):
                item = table_widget.item(row, 0)
                if item is None:
                    continue
                variable = item.data(Qt.ItemDataRole.UserRole)
 
                item_unit = QTableWidgetItem(get_unit(variable))
                item_unit.setFlags(item_unit.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table_widget.setItem(row, 2, item_unit)
 
                if idx is not None:
                    value = convert_array_to_unit(flight['data'][variable], variable)[idx]
                    text = str(round(value, 2)) if isinstance(value, float) else str(value)
                    item_value = QTableWidgetItem(text)
                    item_value.setFlags(item_value.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    table_widget.setItem(row, 1, item_value)
 
            table_widget.blockSignals(False)


    def _restore_checked_variables_1D(self):
        """Restaure les variables précédemment cochées pour le vol sélectionné."""
        flight = self._find_flight(self.comboBox_flight_tab1D.currentText())
        if flight is None:
            return

        selected = flight['plot']['variables_1D']
        tables_and_selection = (
            (self.tableWidget_variable_plot1, selected[0]),
            (self.tableWidget_variable_plot2, selected[1]),
        )
        for table, selected_vars in tables_and_selection:
            for row in range(table.rowCount()):
                item = table.item(row, 0)
                if item:
                    state = (Qt.CheckState.Checked if item.data(Qt.ItemDataRole.UserRole) in selected_vars
                              else Qt.CheckState.Unchecked)
                    item.setCheckState(state)

    def _save_checked_variables_1D(self):
        """Sauvegarde les variables actuellement cochées pour le vol sélectionné."""
        flight = self._find_flight(self.comboBox_flight_tab1D.currentText())
        if flight is None:
            return

        flight['plot']['variables_1D'] = [
            self._get_checked_variables(self.tableWidget_variable_plot1),
            self._get_checked_variables(self.tableWidget_variable_plot2),
        ]

    def _handle_checkboxes_on_table_1D(self, table_widget):
        """
        This function handles what variables can be displayed on the same graph
        relative to their scale (same group only, max 2 variables)
        """
        var_to_unit_group_dic = {
            "heading": ["compass_head", "GNSS_head", "wind_origin"],
            "speed": ["GNSS_speed", "wind_vel", "IAS", "TAS",'GNSS_velD'],
            "vertical_speed": ["vario", "VarioIAS", "netto"],
            "altitude": ["GNSS_alt", "QNS_alt", "LCL"],
            "temperature": ["T_sensor", "air_T", "AirTheta", "AirTd"],
            "angle": ["pitch", "roll"],
            "pressure": ["DP", "P_stat", "AirES", "AirE"]
        }
    
        var_to_group = {
            var: group
            for group, variables in var_to_unit_group_dic.items()
            for var in variables
        }
        
        table_widget.blockSignals(True)
    
        #  récupérer les items cochés
        items_checked = []
        for row in range(table_widget.rowCount()):
            item = table_widget.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                items_checked.append(item)
    
        #  reset état de tous les items
        for row in range(table_widget.rowCount()):
            item = table_widget.item(row, 0)
            if item:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setBackground(QBrush(QColor("white")))
                item.setToolTip("")
    
        if len(items_checked) == 0:
            table_widget.blockSignals(False)
            return
    
        first_var = items_checked[0].data(Qt.ItemDataRole.UserRole)
        first_group = var_to_group.get(first_var)
    
        # variable sans groupe
        if first_group is None:
            for row in range(table_widget.rowCount()):
                item = table_widget.item(row, 0)
                if item and item.checkState() != Qt.CheckState.Checked:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                    item.setBackground(QBrush(QColor(240, 240, 240)))
                    item.setToolTip("Variable without unit group → single selection only")
    
            table_widget.blockSignals(False)
            return
    
        #  1 seule variable cochée
        if len(items_checked) == 1:
            for row in range(table_widget.rowCount()):
                item = table_widget.item(row, 0)
                if item:
                    var = item.data(Qt.ItemDataRole.UserRole)
                    if var_to_group.get(var) != first_group:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                        item.setBackground(QBrush(QColor(240, 240, 240)))
    
        #  max atteint
        elif len(items_checked) >= self.MAX_CHECKED_VARIABLES:
            for row in range(table_widget.rowCount()):
                item = table_widget.item(row, 0)
                if item and item.checkState() != Qt.CheckState.Checked:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                    item.setBackground(QBrush(QColor(240, 240, 240)))
    
        table_widget.blockSignals(False)

    def _on_item_table_1D_changed(self, item):
        """
        Réagit au changement d'une case à cocher dans l'une des deux tables :
        applique la limite à 2 variables, met à jour les deux graphiques,
        puis sauvegarde la sélection. Les modifications sur les autres
        colonnes (valeur/unité, en lecture seule) sont ignorées.
        """
        if item.column() != 0 or not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
            return

        self._handle_checkboxes_on_table_1D(self.tableWidget_variable_plot1)
        self._handle_checkboxes_on_table_1D(self.tableWidget_variable_plot2)

        self._update_1D_plot(self.tableWidget_variable_plot1, self.graph1_tab1D,
                              self.curve_1D_11, self.curve_1D_12)
        self._update_1D_plot(self.tableWidget_variable_plot2, self.graph2_tab1D,
                              self.curve_1D_21, self.curve_1D_22)
        self._save_checked_variables_1D()

    # ------------------------------------------------------------------
    # Tracé
    # ------------------------------------------------------------------
    def _update_1D_plot(self, table_widget, plot_widget, curve1, curve2):
        """
        Trace jusqu'à deux variables (curve1 / curve2) sur `plot_widget` pour
        le vol sélectionné, selon ce qui est coché dans `table_widget`.

        Initialement pensée pour gérer plusieurs courbes sur un même
        graphique, cette méthode se limite pour l'instant à deux courbes, car
        gérer plusieurs échelles avec pyqtgraph est trop complexe.
        """
        crosshair_id = plot_widget.crosshair_id
        plot_widget.enableAutoRange()

        legend = plot_widget.addLegend()
        legend.clear()

        self._remove_crosshair(plot_widget, f"time_{crosshair_id}")

        current_flight_name = self.comboBox_flight_tab1D.currentText()
        if not current_flight_name:  # Évite de tracer un graphique vide quand la combobox met du temps à changer
            return

        variables = self._get_checked_variables(table_widget)
        if not variables:
            curve1.setData([], [])
            curve2.setData([], [])
            return

        flight = self._find_flight(current_flight_name)
        if flight is None:
            return

        x = self._get_gnss_timestamps(flight)
        x_min_limit = np.min(x) - 10
        x_max_limit = np.max(x) + 10

        y1 = convert_array_to_unit(flight['data'][variables[0]], variables[0])
        y1_min_limit = np.min(y1) - (0.1 * (np.max(y1) - np.min(y1)))
        y1_max_limit = np.max(y1) + (0.1 * (np.max(y1) - np.min(y1)))

        plot_widget.setLabel("left", f"{get_label(variables[0])} {get_unit(variables[0])}")
        plot_widget.setTitle(f"{get_label(variables[0])} vs time")
        plot_widget.setLimits(xMin=x_min_limit, xMax=x_max_limit, yMin=y1_min_limit, yMax=y1_max_limit)

        pen1 = pg.mkPen(flight['plot']['plot_color'], width=1)
        legend.addItem(curve1, get_label(variables[0]))
        curve1.setData(x, y1,
                        pen=pen1,
                        symbol='o',
                        symbolSize=5,
                        symbolBrush=(0, 0, 0, 0),  # invisible
                        symbolPen=None)

        if len(variables) > 1:
            y2 = convert_array_to_unit(flight['data'][variables[1]], variables[1])
            y2_min_limit = np.min(y2) - (0.1 * (np.max(y2) - np.min(y2)))
            y2_max_limit = np.max(y2) + (0.1 * (np.max(y2) - np.min(y2)))
            y_min_limit = min(y2_min_limit, y1_min_limit)
            y_max_limit = max(y2_max_limit, y1_max_limit)

            plot_widget.setLabel(
                "left",
                f"{get_label(variables[0])} {get_unit(variables[0])} / {get_label(variables[1])} {get_unit(variables[1])}"
            )
            plot_widget.setTitle(f"{get_label(variables[0])} and {get_label(variables[1])} vs time")
            plot_widget.setLimits(xMin=x_min_limit, xMax=x_max_limit, yMin=y_min_limit, yMax=y_max_limit)

            pen2 = pg.mkPen(flight['plot']['plot_color'].darker(), width=1)
            legend.addItem(curve2, get_label(variables[1]))
            curve2.setData(x, y2,
                            pen=pen2,
                            symbol='o',
                            symbolSize=5,
                            symbolBrush=(0, 0, 0, 0),  # invisible
                            symbolPen=None)
        else:
            curve2.setData([], [])

        plot_widget.autoRange()


    
    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def update_unit_timeserie(self):
        """
        Update the plots when a new unit is selected, as well as the table
        """
        self._update_1D_plot(self.tableWidget_variable_plot1, self.graph1_tab1D,
                              self.curve_1D_11, self.curve_1D_12)
        self._update_1D_plot(self.tableWidget_variable_plot2, self.graph2_tab1D,
                              self.curve_1D_21, self.curve_1D_22)
        
        self._update_unit_table_variable(self.comboBox_flight_tab1D.currentText())

    def update_flight_list(self, flight):
        """
        Met à jour la référence à la liste des vols.
 
        À appeler depuis main.py à chaque fois que self.flight est réassigné
        (i.e. après chaque `self.flight = load_vva_files()`), sinon TimeSerie
        continue de chercher dans l'ancienne liste → _find_flight ne trouve
        rien → les tables restent vides après un import.
        """
        self.flight = flight
        self._gnss_ts_cache.clear()
        
