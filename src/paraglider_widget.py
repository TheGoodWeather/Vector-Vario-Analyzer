from PyQt6 import QtGui
import numpy as np
import pyqtgraph.opengl as gl
from PyQt6.QtCore import QTimer
from pyqtgraph.Qt import QtCore
from PyQt6.QtGui import QColor, QVector3D
import trimesh



def load_obj_mesh(obj_path: str) -> gl.GLMeshItem:
    """
    Charge un fichier .obj et retourne un GLMeshItem prêt à ajouter au GLViewWidget.
    """
    from pathlib import Path

    mesh = trimesh.load(Path(obj_path), force='mesh')

    verts  = np.array(mesh.vertices, dtype=float)
    faces  = np.array(mesh.faces,    dtype=int)

    # Couleurs par face (gris neutre par défaut, à adapter)
    colors = np.ones((len(faces), 4), dtype=float)
    
    colors[:, 0] = 1.0   # Rouge
    colors[:, 1] = 0.0   # Vert
    colors[:, 2] = 0.0   # Bleu
    colors[:, 3] = 1.0   # Alpha (opaque)

    item = gl.GLMeshItem(
        vertexes=verts,
        faces=faces,
        faceColors=colors,
        smooth=True,
        drawEdges=False,
        shader = "shaded"
        
    )
    return item



class ParaGliderWidget(gl.GLViewWidget):
    """
    Widget 3D affichant un modèle simplifié de parapente
    et l'animant en temps réel selon pitch / roll / yaw.

    Utilisation :
        widget = ParaGliderWidget()
        widget.show()

        # Mise à jour depuis les données de vol
        widget.set_attitude(pitch=5.0, roll=-10.0, yaw=45.0)

        # Lecture animée d'un tableau de données
        widget.play(pitch_array, roll_array, yaw_array, dt_ms=200)
    """

    def __init__(self, parent=None, obj_path: str = None):
        super().__init__(parent)

        self.setBackgroundColor((200, 200, 200, 200))   # fond sombre
        self.setCameraPosition(distance=14, elevation=20, azimuth=45)
        self._view = "free"
        self._cam_azimuth = 45
        self._cam_elevation = 20

        self._items = []
        # Grille de référence au sol
        self._grid = gl.GLGridItem()
        self._grid.setSize(200, 200)
        self._grid.setSpacing(20, 20)
        self._grid.setColor(QColor(13, 143, 9))
        self._grid.translate(0, 0, -4)
        self.addItem(self._grid)
        self._items.append(self._grid)
        # Axe de référence (debug, optionnel)
        self._axis = gl.GLAxisItem()
        self._axis.setSize(3, 3, 3)
        self.addItem(self._axis)
        self._items.append(self._axis)
        # Construction du modèle
        self._model = load_obj_mesh(obj_path)
        self.addItem(self._model)
        self._items.append(self._model)
        # Trajectoire du parapente 
        self._trajectory = gl.GLLinePlotItem(
            pos=np.zeros((1,3)),
            color=(1, 0, 0, 1),  # rouge RGBA
            width=2,
            antialias=True,
            mode='line_strip'
        )

        self.addItem(self._trajectory)
        
        # debug_points = self.debug_points()
        # self.addItem(debug_points)

        # État courant
        self._pitch = 0.0
        self._roll  = 0.0
        self._yaw   = 0.0
        self._x = 0.0
        self._y = 0.0
        self._z = 0.0
        
        self.set_attitude(0,0,0)
        self.set_position(0,0,0)

    def _camera_follow(self):

        # # offset = QtGui.QVector3D(0, 0, 0)  # derrière + au-dessus
        target_elevation = None
        target_azimuth = None

        self.opts['center'] = QtGui.QVector3D(
            self._x,
            self._y,
            self._z
        )

        match self._view:

            case "top":
                target_elevation = (
                    -self._pitch + 90
                )
                target_azimuth = 0
            case "side_left":
                target_azimuth = (
                    -self._yaw - 180
                )
                target_elevation = 0
            case "side_right":
                target_azimuth = (
                    -self._yaw
                )
                target_elevation = 0
            case "front":
                target_azimuth = (
                    -self._yaw + 90
                )
                target_elevation = 0
            case "behind":
                target_azimuth = (
                    -self._yaw - 90
                )
                target_elevation = 0

            case "free":
                return
        
        self._smooth_camera(target_azimuth, target_elevation)
        
    def _smooth_camera(self, target_azimuth, target_elevation ):

     
        alpha = 0.1

        self._cam_azimuth += (
            target_azimuth - self.opts['azimuth']
            ) * alpha

        self._cam_elevation += (
            target_elevation - self.opts['elevation']
            ) * alpha

        self.setCameraPosition(
            azimuth=self._cam_azimuth,
            elevation=self._cam_elevation
            )

        

    # ------------------------------------------------------------------
    # Rotation du modèle
    # ------------------------------------------------------------------
    

    def _update_transform(self):

        item = self._model

        item.resetTransform()

        # translation monde
        item.translate(
            self._x,
            self._y,
            self._z
        )

        # rotations locales
        item.rotate(-self._yaw + 90, 0, 0, 1, True)
        item.rotate(- self._pitch, 0, 1,0 , True)  
        item.rotate(self._roll - 90, 1, 0, 0, True)

        self._camera_follow()
           

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def set_view_front(self):
        self._view = "front"
    
    def set_view_free(self):
        self._view = "free"

    def set_view_left(self):
        self._view = "side_left"

    def set_view_right(self):
        self._view = "side_right" 

    def set_view_behind(self):
        self._view = "behind" 

    def set_view_top(self):
        self._view = "top" 

    def cleanup(self):
        
        self.clear()
    
    def debug_points(self):
        pts = np.array([
            [1,0,0],   # rouge = X
            [0,1,0],   # vert  = Y
            [0,0,1],   # bleu  = Z
        ])

        colors = np.array([
            [1,0,0,1],
            [0,1,0,1],
            [0,0,1,1],
        ])

        sp = gl.GLScatterPlotItem(pos=pts, color=colors, size=10)
        return sp 
        
    def set_attitude(self, pitch: float = 0.0, roll: float = 0.0, yaw: float = 0.0):
        """
        Met à jour l'attitude du modèle.

        Parameters
        ----------
        pitch : float  Tangage en degrés (positif = nez haut)
        roll  : float  Roulis en degrés  (positif = aile droite basse)
        yaw   : float  Lacet en degrés   (positif = virage à droite)
        """
        self._pitch = pitch
        self._roll  = roll
        self._yaw   = yaw
        self._update_transform()

    def reset_attitude(self):
        """Remet le modèle en position neutre."""
        self.set_attitude(0.0, 0.0, 0.0)

    def set_position(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        """
        Met à jour la position du modèle
        """
        self._x = x
        self._y  = y
        self._z   = z
        self._update_transform()

    def reset_position(self):
        """Remet le modèle en position neutre."""
        self.set_position(0.0, 0.0, 0.0)

    def set_trajectory(self, x, y, z):

        pts = np.column_stack((x, y, z))

        self._trajectory.setData(
            pos=pts
        )

 
    
