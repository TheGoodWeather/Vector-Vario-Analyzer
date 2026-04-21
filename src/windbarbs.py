import numpy as np
import pyqtgraph as pg
from utils import mapping
from PyQt6 import QtCore

class WindBarbs:
    def __init__(self, plot_widget):
        self._n_barbs = 10  # nombre fixe de barbules affichées
        self.plot_widget = plot_widget
        self._items = []
        self._P = None
        self._wind_vel = None
        self._wind_origin = None
        self._Xgraph = None
        self.P_bot = None         # sera assigné depuis SkewTWidget

        self._hampes  = []
        self._barbes  = [] 
        self._build_barb()
        
        self.plot_widget.getViewBox().sigRangeChanged.connect(self._on_range_changed)
        
        QtCore.QTimer.singleShot(0, self._redraw)
        
        self.poutre = pg.InfiniteLine( #The line where the windbarbs will be fixed 
            angle = 90,                 # horizontale
            movable=False,
            pen=pg.mkPen((0,0,0,50), width=1)
        )
        self.plot_widget.addItem(self.poutre)
    
    def _build_barb(self):
        
        #Clear previous barbs
        
        for barbs in self._barbes:
            for seg in barbs:  # 
                self.plot_widget.removeItem(seg)
    
        for hamps in self._hampes:
            self.plot_widget.removeItem(hamps)
        self._hampes  = []
        self._barbes  = [] 
        
        pen = pg.mkPen(color=(0, 0, 0), width=1)

        for _ in range(self._n_barbs):
            hampe = self.plot_widget.plot([], [], pen=pen)
            self._hampes.append(hampe)

            barbes_i = []
            for _ in range(7):  # max 7 segments par barbule (flags + full + half)
                seg = self.plot_widget.plot([], [], pen=pen)
                barbes_i.append(seg)
            self._barbes.append(barbes_i)
            
  
        self._redraw()
    
    def _get_barb_length(self):
        """Calcule la longueur de la hampe en unités de la viewbox"""
        # vb = self.plot_widget.getViewBox()
        # x_range, y_range = vb.viewRange()
        # return (x_range[1] - x_range[0]) * 0.04  # 4% de la largeur
        vb = self.plot_widget.getViewBox()
        # Guard : valeurs aberrantes si widget pas encore rendu
        px_size_x, px_size_y = vb.viewPixelSize()
        if px_size_x == 0 or px_size_y == 0 or px_size_x > 1e6:
            return 1.0, 1.0
        desired_pixels = 40
    
        return desired_pixels * px_size_x , desired_pixels * px_size_y

    def _update_barb(self, idx, x, y, speed, angle, barb_length_x, barb_length_y):
        """Dessine une barbule et retourne la liste des items créés"""
        speed = speed * 1.94384  # m/s → noeuds
        angle = np.deg2rad(180 - angle) 
        hampe = self._hampes[idx]
        barbes = self._barbes[idx]
        
        for seg in barbes: #reset barbs
            seg.setData([], [])
            
            
        # if speed < 2.5:  # vent calme : cercle
        #     circle = pg.ScatterPlotItem(
        #         [x], [y],
        #         symbol='o', size=6,
        #         pen=pg.mkPen((0, 0, 0), width=1),
        #         brush=pg.mkBrush(None)
        #     )
        #     self.plot_widget.addItem(circle)
        #     items.append(circle)
        #     return items

        
        perp = angle + np.pi / 2
        barb_step_x = barb_length_x / 8
        barb_step_y = barb_length_y / 8

        # Hampe principale
        x_end = x + barb_length_x * np.sin(angle)
        y_end = y + barb_length_y * np.cos(angle)

        hampe.setData([x, x_end], [y, y_end])
        
        n_flags = int(speed // 50)
        n_full  = int((speed % 50) // 10)
        n_half  = int((speed % 10) // 5)

        pos_x = barb_length_x
        pos_y = barb_length_y
        seg_idx = 0

        # Fanions (50 noeuds)
        for _ in range(n_flags):
            if seg_idx >= len(barbes):
                break
            x1 = x + pos_x * np.sin(angle)
            y1 = y + pos_y * np.cos(angle)
            x2 = x + (pos_x - barb_step_x) * np.sin(angle) + barb_length_x * 0.4 * np.sin(perp)
            y2 = y + (pos_y - barb_step_y) * np.cos(angle) + barb_length_y * 0.4 * np.cos(perp)
            x3 = x + (pos_x - barb_step_x) * np.sin(angle)
            y3 = y + (pos_y - barb_step_y) * np.cos(angle)
            barbes[seg_idx].setData([x1, x2, x3, x1], [y1, y2, y3, y1])
            seg_idx += 1
            pos_x -= barb_step_x * 1.5
            pos_y -= barb_step_y * 1.5

        for _ in range(n_full):
            if seg_idx >= len(barbes):
                break
            x1 = x + pos_x * np.sin(angle)
            y1 = y + pos_y * np.cos(angle)
            x2 = x1 + barb_length_x * 0.35 * np.sin(perp)
            y2 = y1 + barb_length_y * 0.35 * np.cos(perp)
            barbes[seg_idx].setData([x1, x2], [y1, y2])
            seg_idx += 1
            pos_x -= barb_step_x
            pos_y -= barb_step_y

        if n_half and seg_idx < len(barbes):
            x1 = x + pos_x * np.sin(angle)
            y1 = y + pos_y * np.cos(angle)
            x2 = x1 + barb_length_x * 0.175 * np.sin(perp)
            y2 = y1 + barb_length_y * 0.175 * np.cos(perp)
            barbes[seg_idx].setData([x1, x2], [y1, y2])

        self.poutre.setValue(self._Xgraph)
        
    def _clear(self):
        for item in self._items:
            self.plot_widget.removeItem(item)
        self._items = []

    def _redraw(self):
        """Redessine toutes les barbules avec la taille courante de la viewbox"""
        if self._P is None:
            return
        barb_length_x, barb_length_y = self._get_barb_length()
        
        indices = np.linspace(0, len(self._P) - 1, self._n_barbs, dtype=int)
        
        for i, idx in enumerate(indices):
            x = self._Xgraph
            self._update_barb(i, x, self._P[idx], self._wind_vel[idx], self._wind_origin[idx], barb_length_x, barb_length_y)

    def _on_range_changed(self):
        """Redessine quand le zoom/pan change pour adapter la taille des barbules"""
        self._redraw()

    def update(self, P, speed, angle, X_graph):
        """
        Met à jour les barbules avec de nouvelles données.
        delta : un niveau sur N
        """
        self._P = P
        self._wind_origin = angle
        self._wind_vel = speed
        self._Xgraph = X_graph
        
        # Diffère si le widget n'est pas encore rendu
        if self.plot_widget.width() == 0:
            QtCore.QTimer.singleShot(100, self._redraw)
        else:
            self._redraw()
        
    def update_pos(self, Xpos):
        self._Xgraph = Xpos
        self._redraw()

    def clear(self):
        self._clear()
        self._P =self._wind_vel = self._wind_origin = self._Xgraph = None
        
    def update_density_barb(self, density):
        self._n_barbs = int(mapping(density, 1 , 100 , 1 ,30 ))
        
        self._build_barb()
    
    def show(self, state):
        for barbs in self._barbes:
            for seg in barbs:  # 
                seg.setVisible(state)
    
        for hamps in self._hampes:
            hamps.setVisible(state)
            
        self.poutre.setVisible(state)