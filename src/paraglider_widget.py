from PyQt6 import QtGui
import numpy as np
import pyqtgraph.opengl as gl
from PyQt6.QtCore import QSettings, QTimer
from pyqtgraph.Qt import QtCore
from PyQt6.QtGui import QColor, QVector3D
from utils import mapping
import trimesh

import numpy as np
import pyqtgraph.opengl as gl


def create_green_dome(
    radius,
    color,
    stacks=32,
    slices=64
):
    """
    Demi-sphère inversée :
    
    - ouverte vers le haut
    - creuse
    - section circulaire à z = 0
    - point le plus bas à z = -radius
    """

    phi = np.linspace(np.pi / 2, np.pi, stacks)
    theta = np.linspace(0, 2 * np.pi, slices)

    phi, theta = np.meshgrid(phi, theta, indexing='ij')

    # coordonnées sphériques
    x = radius * np.sin(phi) * np.cos(theta)
    y = radius * np.sin(phi) * np.sin(theta)
    z = radius * np.cos(phi)

    verts = np.stack((x, y, z), axis=-1).reshape(-1, 3)

    faces = []

    for i in range(stacks - 1):
        for j in range(slices - 1):

            a = i * slices + j
            b = (i + 1) * slices + j
            c = (i + 1) * slices + (j + 1)
            d = i * slices + (j + 1)

            # orientation vers l'intérieur
            faces.append([a, c, b])
            faces.append([a, d, c])

    faces = np.array(faces, dtype=np.int32)

    colors = np.ones((len(faces), 4), dtype=np.float32)
    colors[:] = color

    dome = gl.GLMeshItem(
        vertexes=verts,
        faces=faces,
        faceColors=colors,
        smooth=True,
        drawEdges=False,
        shader='balloon'
    )

    dome.setGLOptions('opaque')

    return dome

def create_ground(
    size=50000,
    color=(1.0, 0.0, 0.0, 0.0)
):

    import numpy as np
    import pyqtgraph.opengl as gl

    verts = np.array([
        [-size, -size, 0],
        [ size, -size, 0],
        [ size,  size, 0],
        [-size,  size, 0],
    ], dtype=np.float32)

    faces = np.array([
        [0, 1, 2],
        [0, 2, 3]
    ], dtype=np.uint32)

    colors = np.array([
        color,
        color
    ], dtype=np.float32)

    ground = gl.GLMeshItem(
        vertexes=verts,
        faces=faces,
        faceColors=colors,
        smooth=False,
        drawEdges=False,
        shader="balloon"
    )

    return ground

def load_obj_mesh(obj_path: str) -> gl.GLMeshItem:
    from pathlib import Path

    mesh = trimesh.load(Path(obj_path), force='mesh')
    verts = np.array(mesh.vertices, dtype=float)
    faces = np.array(mesh.faces, dtype=int)

    colors = np.full((len(faces), 4),
                     [0.15, 0.15, 0.15, 1.0],
                     dtype=float)

    return gl.GLMeshItem(
        vertexes=verts,
        faces=faces,
        smooth=True,
        drawEdges=False,
        shader='shaded'
    )


def load_arrow_mesh(
    obj_path: str,
    color=(0.0, 0.0, 1.0, 1.0)
) -> gl.GLMeshItem:

    from pathlib import Path

    mesh = trimesh.load(Path(obj_path), force='mesh')

    verts = np.array(mesh.vertices, dtype=float)
    faces = np.array(mesh.faces, dtype=int)

    item = gl.GLMeshItem(
        vertexes=verts,
        faces=faces,
        color=color,
        smooth=True,
        drawEdges=False,
        shader='balloon'
    )

    return item

def load_stl_mesh(
    stl_path: str,
    color=(0.0, 0.0, 1.0, 1.0)
) -> gl.GLMeshItem:
    from pathlib import Path
    mesh = trimesh.load(Path(stl_path), force='mesh')
    verts = np.array(mesh.vertices, dtype=float)
    faces = np.array(mesh.faces,    dtype=int)
    item = gl.GLMeshItem(
        vertexes=verts,
        faces=faces,
        color=color,
        smooth=True,
        drawEdges=False,
        shader='balloon'
    )
    return item


def load_glb_mesh(
    glb_path: str,
    color=(0.0, 0.0, 1.0, 1.0)
) -> gl.GLMeshItem:

    from pathlib import Path

    # Chargement de la scène GLB
    scene = trimesh.load(
        Path(glb_path),
        force='scene'
    )

    # Fusion de tous les meshes
    meshes = []

    for geom in scene.geometry.values():

        if isinstance(geom, trimesh.Trimesh):
            meshes.append(geom)

    if len(meshes) == 0:
        raise ValueError("No mesh found in GLB file")

    mesh = trimesh.util.concatenate(meshes)

    verts = np.array(
        mesh.vertices,
        dtype=np.float32
    )

    faces = np.array(
        mesh.faces,
        dtype=np.uint32
    )

    item = gl.GLMeshItem(
        vertexes=verts,
        faces=faces,
        color=color,
        smooth=True,
        drawEdges=False,
        shader='balloon'
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

        self.settings = QSettings("Vector Vario", "VVA")

        self.setBackgroundColor(QColor(self.settings.value("colors/background" , "#b5b5b5")))   
        self.setCameraPosition(distance=14, elevation=20, azimuth=45)
        self._view = "free"
        self._cam_azimuth = 45
        self._cam_elevation = 20

        self._items = []
        # Ground
        # radius = 200
        # self._dome_ground = create_green_dome(
        #     radius=radius,
        #     color=(0.184, 0.62, 0.345, 1.0)
        # )
        # # self._dome_ground.setGLOptions('additive')
        # self.addItem(self._dome_ground)
        # self._items.append(self._dome_ground)
         # Grille de référence au sol

        self._grid = gl.GLGridItem()
        self._grid.setSize(200, 200)
        self._grid.setSpacing(20, 20)
        self._grid.setColor(QColor(self.settings.value("colors/grid" , "#FFFFFF")))
        self._grid.translate(0, 0, -4)
        self.addItem(self._grid)
        self._items.append(self._grid)

        # Axe de référence (debug, optionnel)
        self._axis = gl.GLAxisItem()
        self._axis.setSize(3, 3, 3)
        self.addItem(self._axis)
        self._items.append(self._axis)
        # Construction du modèle
        # self._model = load_glb_mesh("gui/models/para2.glb")
        self._model = load_obj_mesh("gui/models/para_v4.obj")
        self.addItem(self._model)
        self._model.setColor(QColor("#FF1717"))
        self._items.append(self._model)
        # Building arrow 
        self._wind_arrow = load_arrow_mesh("gui/models/arrow1.obj", (0.3, 0.6, 1.0, 0.8))
        self.addItem(self._wind_arrow)
        self._items.append(self._wind_arrow)

        self._north_arrow = load_arrow_mesh("gui/models/arrow1.obj", (1.0, 0.2, 0.2, 0.8))
        self.addItem(self._north_arrow)
        self._items.append(self._north_arrow)

        self._tas_arrow = load_arrow_mesh("gui/models/arrow1.obj", (0.2, 0.8, 1.0, 0.8))
        self.addItem(self._tas_arrow)
        self._items.append(self._tas_arrow)

        self._bearing_arrow = load_arrow_mesh("gui/models/arrow1.obj", (0.3, 1.0, 0.5, 0.8))
        self.addItem(self._bearing_arrow)
        self._items.append(self._bearing_arrow)

        self._vertical_arrow = load_arrow_mesh("gui/models/arrow1.obj", (0.3,0.4, 0.5, 0.8))
        self.addItem(self._vertical_arrow)
        self._items.append(self._vertical_arrow)


        # Trajectoire du parapente 
        qcolor_trajectory = QColor(self.settings.value("colors/plot" , "#ff0000"))
        r, g, b, a = qcolor_trajectory.getRgbF()
        gl_color = (r, g, b, a)
        self._trajectory = gl.GLLinePlotItem(
            pos=np.zeros((1,3)),
            color= gl_color,
            width=2,
            antialias=False,
            mode='line_strip'
        )
        self._trajectory.setGLOptions('opaque')  # ← respecte le depth buffer
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
        self._wind_azimut = 0.0
        self._wind_speed = 0.0
        self._wind_tilt = 0.0
        self._tas = 0.0
        self._gnss_speed = 0.0
        self._bearing = 0.0

        self._min_radius_skybox = 0.0
        
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
        self._update_clipping_planes()
        self._smooth_camera(target_azimuth, target_elevation)
        
    def _smooth_camera(self, target_azimuth, target_elevation ):

     
        alpha = 0.1
        
        self._cam_azimuth = self._angle_lerp(
            self.opts['azimuth'],
            target_azimuth,
            alpha
        )
      
        self._cam_elevation = self._angle_lerp(
            self.opts['elevation'],
            target_elevation,
            alpha
            )

        self.setCameraPosition(
            azimuth=self._cam_azimuth,
            elevation=self._cam_elevation
            )

    def _angle_lerp(self, current, target, alpha):

        delta = (target - current + 180) % 360 - 180

        return current + delta * alpha
        

    # ------------------------------------------------------------------
    # Models translation and rotation
    # ------------------------------------------------------------------
    

    def _update_transform(self):

        #TRANSLATION
        # Paraglider
        item = self._model
        item.resetTransform()
        item.translate(
            self._x,
            self._y,
            self._z
        )
        # ROTATION
        item.rotate(-self._yaw + 90, 0, 0, 1, True)
        item.rotate(- self._pitch, 0, 1,0 , True)  
        item.rotate(self._roll - 90, 1, 0, 0, True)
   
        # Wind vector 
        self._wind_arrow.resetTransform()
        self._wind_arrow.rotate(- self._wind_azimut - 90, 0 , 0 , 1, True)
        self._wind_arrow.rotate(- self._wind_tilt , 0 , 1 , 0, True)
        self._wind_arrow.translate(
            self._x,
            self._y,
            self._z
        )


         # North vector 

        self._north_arrow.resetTransform()
        self._north_arrow.rotate(90, 0 , 0 , 1, True)
        self._north_arrow.translate(
            self._x,
            self._y,
            self._z
        )
          # TAS vector 
        self._tas_arrow.resetTransform()
        self._tas_arrow.rotate(-self._yaw + 90, 0 , 0 , 1, True)
        self._tas_arrow.translate(
            self._x,
            self._y,
            self._z
        )
         # Bearing vector 
        self._bearing_arrow.resetTransform()
        self._bearing_arrow.rotate(-self._bearing + 90, 0 , 0 , 1, True)
        self._bearing_arrow.translate(
            self._x,
            self._y,
            self._z
        )
         # Vertical vector 
        self._vertical_arrow.resetTransform()
        self._vertical_arrow.rotate(-90, 0 , 1 , 0, True)
        self._vertical_arrow.translate(
            self._x,
            self._y,
            self._z
        )
    
        #SCALING
        self._wind_arrow.scale(mapping(self._wind_speed,0,30,0.1,3), 1, 1)
        self._tas_arrow.scale(mapping(self._tas,0,30,0.1,3), 1, 1)
        self._bearing_arrow.scale(mapping(self._gnss_speed,0,30,0.1,3), 1, 1)

        self._camera_follow()


        #SKYBOX
        # cam_dist = self.opts['distance']
        # cam_center = self._get_camera_pos()
        # if cam_dist + self._min_radius_skybox <= self._min_radius_skybox:
        #     dome_radius = self._min_radius_skybox
        # else :
        #     dome_radius = cam_dist * 1.2 + self._min_radius_skybox
       

        # self._dome_ground.resetTransform()
        # self._dome_ground.translate(
        #     cam_center[0],
        #     cam_center[1],
        #     cam_center[2]
        # )
        # self._dome_ground.scale(dome_radius, dome_radius, dome_radius)
           
    def _get_camera_pos(self) -> np.ndarray:
        """Retourne la position XYZ de la caméra dans le repère monde."""
        dist = self.opts['distance']
        elev = np.radians(self.opts['elevation'])
        azim = np.radians(self.opts['azimuth'])
        center = self.opts['center']  # QVector3D

        x = center.x() + dist * np.cos(elev) * np.cos(azim)
        y = center.y() + dist * np.cos(elev) * np.sin(azim)
        z = center.z() + dist * np.sin(elev)

        return np.array([x, y, z], dtype=float)
    
    def _update_clipping_planes(self):
        cam_dist = self.opts['distance']
        # near = 0.1% de la distance caméra, far = 10× la distance caméra
        self.opts['near'] = max(0.01, cam_dist * 0.001)
        self.opts['far']  = cam_dist * 10.0
        self.update()
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

    def set_wind_vector(self, azimut, tilt, velocity):
        self._wind_azimut = azimut
        self._wind_speed = velocity
        self._wind_tilt = tilt
    

    def set_tas_vector(self, yaw, tas):
        self._tas = tas
        self._yaw = yaw
    
    def set_bearing_vector(self, bearing, speed):
        self._gnss_speed = speed
        self._bearing = bearing

    

    def set_visibility_wind_vector(self, visible):
        self._wind_arrow.setVisible(visible)

    def set_visibility_north_vector(self, visible):
        self._north_arrow.setVisible(visible)
    
    def set_visibility_tas_vector(self, visible):
        self._tas_arrow.setVisible(visible)
    
    def set_visibility_bearing_vector(self, visible):
        self._bearing_arrow.setVisible(visible)

    def set_visibility_vertical_vector(self, visible):
        self._vertical_arrow.setVisible(visible)

    def set_min_radius(self, radius):
        self._min_radius_skybox = radius 

    def set_len_grid(self, origin_x, origin_y, len_x, len_y):
        self._grid.resetTransform()
        self._grid.translate(origin_x, origin_y, -4)
        self._grid.setSize(len_x* 4, len_y* 4)
        spacing = max(len_x,len_y) / 50
        self._grid.setSpacing(spacing, spacing)

    def apply_color_changes(self):
        self.settings.beginGroup("colors")
        self._grid.setColor(QColor(self.settings.value("grid" , "#FFFFFF")))
        self.setBackgroundColor(QColor(self.settings.value("background" , "#908989")))
        qcolor_trajectory = QColor(self.settings.value("dynaplot" , "#ff0000"))
        r, g, b, a = qcolor_trajectory.getRgbF()
        gl_color = (r, g, b, a)
        self._trajectory.setData(color = gl_color)
        self._model.setColor(QColor(self.settings.value("model" , "#322D2D")))
        self.settings.endGroup()

 
    


