import os
import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
import pywavefront
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGraphicsView, QGraphicsScene, QComboBox
)
from PyQt5.QtCore import QTimer, Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter
from PyQt5.QtWidgets import QGraphicsObject


class DraggableGridItem(QGraphicsObject):
    toggled = pyqtSignal(int, int)  # row, col

    def __init__(self, row, col, size):
        super().__init__()
        self.row = row
        self.col = col
        self.size = size
        self.rect = QRectF(0, 0, size, size)
        self.is_obstacle = False

    def boundingRect(self):
        return self.rect

    def paint(self, painter: QPainter, option, widget=None):
        color = QColor("#444") if self.is_obstacle else QColor("#fff")
        painter.setBrush(QBrush(color))
        painter.drawRect(self.rect)

    def mousePressEvent(self, event):
        self.is_obstacle = not self.is_obstacle
        self.update()
        self.toggled.emit(self.row, self.col)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI-Driven Drone GUI App")
        self.setGeometry(200, 100, 1200, 700)

        self.grid_size = 10
        self.cell_size = 30
        self.grid = [[0 for _ in range(self.grid_size)] for _ in range(self.grid_size)]

        self.drone_pos = [0, 0]
        self.drone_angle = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout()
        main_widget.setLayout(layout)

        # Sol panel
        control_panel = QVBoxLayout()

        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["Dijkstra", "Greedy", "A*"])
        self.info_label = QLabel("Battery: 100%\nPosition: (0,0)")

        for w in [self.start_btn, self.stop_btn, self.algo_combo, self.info_label]:
            w.setFont(QFont("Arial", 12))
            w.setFixedHeight(40 if isinstance(w, QPushButton) else 60)
            control_panel.addWidget(w)

        self.start_btn.clicked.connect(self.start_simulation)
        self.stop_btn.clicked.connect(self.stop_simulation)

        layout.addLayout(control_panel, 1)

        # Orta panel – 2D harita
        self.scene = QGraphicsScene()
        self.graphics_view = QGraphicsView(self.scene)
        self.graphics_view.setFixedSize(
            self.grid_size * self.cell_size + 2,
            self.grid_size * self.cell_size + 2
        )
        layout.addWidget(self.graphics_view, 2)

        # Sağ panel – 3D simülasyon
        self.gl_widget = gl.GLViewWidget()
        self.gl_widget.setCameraPosition(distance=30)
        layout.addWidget(self.gl_widget, 3)

        self.grid_items = []
        self.draw_2d_grid()
        self.setup_3d_scene()
        self.load_drone_model()
        self.update_3d_scene()

    def draw_2d_grid(self):
        self.scene.clear()
        self.grid_items = []

        for r in range(self.grid_size):
            row_items = []
            for c in range(self.grid_size):
                cell = DraggableGridItem(r, c, self.cell_size)
                cell.setPos(c * self.cell_size, r * self.cell_size)
                cell.toggled.connect(self.toggle_obstacle)
                self.scene.addItem(cell)
                row_items.append(cell)
            self.grid_items.append(row_items)

    def toggle_obstacle(self, row, col):
        self.grid[row][col] = 1 - self.grid[row][col]
        self.update_3d_scene()

    def setup_3d_scene(self):
        self.gl_widget.clear()
        grid = gl.GLGridItem()
        grid.setSize(10, 10)
        grid.setSpacing(1, 1)
        self.gl_widget.addItem(grid)

    def create_cube_mesh(self):
        verts = np.array([
            [1, 1, 1],
            [-1, 1, 1],
            [-1, -1, 1],
            [1, -1, 1],
            [1, 1, -1],
            [-1, 1, -1],
            [-1, -1, -1],
            [1, -1, -1]
        ])
        faces = np.array([
            [0, 1, 2], [0, 2, 3],  # front
            [4, 0, 3], [4, 3, 7],  # right
            [5, 4, 7], [5, 7, 6],  # back
            [1, 5, 6], [1, 6, 2],  # left
            [4, 5, 1], [4, 1, 0],  # top
            [2, 6, 7], [2, 7, 3],  # bottom
        ])
        return gl.MeshData(vertexes=verts, faces=faces)

    def create_obstacle(self, x, y, z):
        mesh_data = self.create_cube_mesh()
        cube = gl.GLMeshItem(meshdata=mesh_data, smooth=False, color=(1, 0.3, 0.3, 1), shader='shaded')
        cube.scale(0.5, 0.5, 0.5)
        cube.translate(x, y, z)
        return cube

    def update_3d_scene(self):
        self.setup_3d_scene()
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if self.grid[r][c] == 1:
                    obs = self.create_obstacle(c - self.grid_size / 2, -(r - self.grid_size / 2), 0)
                    self.gl_widget.addItem(obs)

    def load_drone_model(self):
        try:
            model_path = os.path.join("assets", "models", "sci_fi_surveillance_drone.obj")
            if not os.path.exists(model_path):
                raise FileNotFoundError("Model bulunamadı: sci_fi_surveillance_drone.obj")

            self.drone_obj = pywavefront.Wavefront(model_path, collect_faces=True)

            vertices = []
            faces = []
            offset = 0

            for name, mesh in self.drone_obj.meshes.items():
                vertices.extend(mesh.vertices)
                faces.extend([[i + offset for i in face] for face in mesh.faces])
                offset += len(mesh.vertices)

            vertices = np.array(vertices)
            faces = np.array(faces)

            mesh_data = gl.MeshData(vertexes=vertices, faces=faces)
            mesh_item = gl.GLMeshItem(
                meshdata=mesh_data,
                smooth=True,
                color=(0.2, 0.7, 1, 1),  # Açık mavi
                shader='shaded'
            )
            mesh_item.scale(0.01, 0.01, 0.01)  # Modeli ölçeklendir
            mesh_item.translate(0, 0, 1)       # Biraz yukarı taşı

            self.gl_widget.addItem(mesh_item)
            self.mesh_items = [mesh_item]

            self.gl_widget.setCameraPosition(distance=30)

        except Exception as e:
            print("Model yüklenemedi:", e)
            mesh_data = gl.MeshData.sphere(rows=10, cols=10)
            cube = gl.GLMeshItem(meshdata=mesh_data, smooth=True, color=(1, 0, 0, 1), shader='ball')
            cube.translate(0, 0, 0.5)
            self.gl_widget.addItem(cube)
            self.mesh_items = [cube]

    def start_simulation(self):
        self.timer.start(200)

    def stop_simulation(self):
        self.timer.stop()

    def update_simulation(self):
        self.drone_angle += 5
        self.drone_pos[0] = (self.drone_pos[0] + 1) % self.grid_size
        self.drone_pos[1] = (self.drone_pos[1] + 1) % self.grid_size
        self.info_label.setText(f"Battery: 100%\nPosition: {tuple(self.drone_pos)}")

        for mesh in self.mesh_items:
            mesh.resetTransform()
            mesh.rotate(self.drone_angle, 0, 0, 1)
            mesh.translate(*self.drone_pos, 0.5)

