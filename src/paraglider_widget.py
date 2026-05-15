import numpy as np
import pyqtgraph.opengl as gl
from PyQt6.QtCore import QTimer
from pyqtgraph.Qt import QtCore
from PyQt6.QtGui import QColor
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
        
        # État courant
        self._pitch = 0.0
        self._roll  = 0.0
        self._yaw   = 0.0
        self._x = 0.0
        self._y = 0.0
        self._z = 0.0


    # ------------------------------------------------------------------
    # Rotation du modèle
    # ------------------------------------------------------------------

    def _apply_rotation(self):
        """Applique pitch / roll / yaw à tous les éléments du modèle."""
        for item in [self._model]:
            item.resetTransform()
            item.rotate(self._yaw,   0, 0, 1)   # lacet  (Z)
            item.rotate(self._pitch, 1, 0, 0)   # tangage (X)
            item.rotate(self._roll + 90,  0, 1, 0)   # roulis  (Y)


    def _apply_translation(self):
        """Applique x/y/z à tous les éléments du modèle."""
        for item in [self._model]:
            item.resetTransform()
            item.translate(self._x,self._y, self._z)  
           

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------
    def cleanup(self):
        
        self.clear()
    
      
        
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
        self._apply_rotation()

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
        self._apply_translation()

    def reset_position(self):
        """Remet le modèle en position neutre."""
        self.set_position(0.0, 0.0, 0.0)

 
    
