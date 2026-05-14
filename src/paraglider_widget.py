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
    mesh = trimesh.load(obj_path, force='mesh')

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

        self.items= []
    
        # Grille de référence au sol
        self._grid = gl.GLGridItem()
        self._grid.setSize(200, 200)
        self._grid.setSpacing(20, 20)
        self._grid.setColor(QColor(13, 143, 9))
        self._grid.translate(0, 0, -4)
        self.addItem(self._grid)
        self.items.append(self._grid)
        # Construction du modèle
        self._build_model(obj_path)

        # État courant
        self._pitch = 0.0
        self._roll  = 0.0
        self._yaw   = 0.0

        # # Timer pour la lecture animée
        # self._play_timer   = QTimer(self)
        # self._play_data    = None
        # self._play_index   = 0
        # self._play_timer.timeout.connect(self._play_step)

    # ------------------------------------------------------------------
    # Construction du modèle parapente (maillage simplifié)
    # ------------------------------------------------------------------

    def _build_model(self, obj_path: str = None):
        """Construit la voile et les suspentes."""

        if obj_path:
            self._model = load_obj_mesh(obj_path)
        else:
            return
        self.addItem(self._model)
        self.items.append(self._model)
        # self._canopy = gl.GLMeshItem(
        #     vertexes=verts,
        #     faces=faces,
        #     faceColors=colors,
        #     smooth=True,
        #     drawEdges=False,
        # )
        # self.addItem(self._canopy)

        # --- Suspentes (lignes entre voile et sellette) ---------------
 
        # Axe de référence (debug, optionnel)
        self._axis = gl.GLAxisItem()
        self._axis.setSize(3, 3, 3)
        self.addItem(self._axis)
        self.items.append(self._axis)

    # ------------------------------------------------------------------
    # Rotation du modèle
    # ------------------------------------------------------------------

    def _apply_rotation(self):
        """Applique pitch / roll / yaw à tous les éléments du modèle."""
        for item in self.items:
            item.resetTransform()
            item.rotate(self._yaw,   0, 0, 1)   # lacet  (Z)
            item.rotate(self._pitch, 1, 0, 0)   # tangage (X)
            item.rotate(self._roll,  0, 1, 0)   # roulis  (Y)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------
    def cleanup(self):
        
        print("cleaning")
        self.clear()
    
        for item in self.items:
            self.removeItem(item)
        
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

    # ------------------------------------------------------------------
    # Lecture animée d'un vol
    # ------------------------------------------------------------------

    def play(self, pitch_array, roll_array, yaw_array, dt_ms: int = 200):
        """
        Anime le modèle en lisant les tableaux de données.

        Parameters
        ----------
        pitch_array : array-like
        roll_array  : array-like
        yaw_array   : array-like
        dt_ms       : int  Intervalle entre chaque frame en millisecondes
        """
        self._play_data  = (
            np.array(pitch_array, dtype=float),
            np.array(roll_array,  dtype=float),
            np.array(yaw_array,   dtype=float),
        )
        self._play_index = 0
        self._play_timer.setInterval(dt_ms)
        self._play_timer.start()

    def pause(self):
        self._play_timer.stop()

    def resume(self):
        if self._play_data is not None:
            self._play_timer.start()

    def stop(self):
        self._play_timer.stop()
        self._play_index = 0
        self.reset_attitude()

    def seek(self, index: int):
        """Saute à un index précis dans les données de vol."""
        if self._play_data is None:
            return
        n = len(self._play_data[0])
        self._play_index = max(0, min(index, n - 1))
        p, r, y = (arr[self._play_index] for arr in self._play_data)
        self.set_attitude(
            pitch=0.0 if np.isnan(p) else p,
            roll =0.0 if np.isnan(r) else r,
            yaw  =0.0 if np.isnan(y) else y,
        )

    def _play_step(self):
        if self._play_data is None:
            return
        pitches, rolls, yaws = self._play_data
        n = len(pitches)

        if self._play_index >= n:
            self._play_timer.stop()
            return

        p = pitches[self._play_index]
        r = rolls[self._play_index]
        y = yaws[self._play_index]

        self.set_attitude(
            pitch=0.0 if np.isnan(p) else p,
            roll =0.0 if np.isnan(r) else r,
            yaw  =0.0 if np.isnan(y) else y,
        )
        self._play_index += 1


