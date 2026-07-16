import sys
import tensorflow as tf
from dotenv import load_dotenv
from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QListWidgetItem, QFileDialog
from tmdb_client import TMDbClient
from PyQt6.QtCore import Qt
import os

load_dotenv()

class Generador(QMainWindow):

    def __init__(self):
        super().__init__()
        self.tmdb = TMDbClient()
        os.getenv("TMDB_BEARER_TOKEN")
        uic.loadUi("X_Ray_ui.ui", self)

        # Eventos
        self.btnBuscarPelicula.clicked.connect(self.buscar_pelicula)
        self.btnSeleccionarPelicula.clicked.connect(self.seleccionar_video)
        self.BtnGenerar.clicked.connect(self.generar_json)

        self.listPeliculas.itemClicked.connect(self.pelicula_seleccionada)

    def buscar_pelicula(self):

        texto = self.LineBuscarPelicula.text().strip()

        if not texto:
            return

        peliculas = self.tmdb.buscar_peliculas(texto)

        self.listPeliculas.clear()

        for pelicula in peliculas:

            item = QListWidgetItem(
                f"{pelicula['title']} ({pelicula['year']})"
            )

            item.setData(Qt.ItemDataRole.UserRole, pelicula)

            self.listPeliculas.addItem(item)

    def seleccionar_video(self):

        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Selecciona una película",
            "",
            "Vídeos (*.mp4 *.mkv *.avi *.mov *.wmv);;Todos los archivos (*)"
        )

        if ruta:
            self.lblSeleccionarVideo.setText(ruta)
            self.ruta_video = ruta

    def generar_json(self):


        from deepface import DeepFace
        print("DeepFace cargado")
        from modelo_entrenado import generar_xray

        if not hasattr(self, "ruta_video"):
            print("Selecciona un vídeo")
            return

        item = self.listPeliculas.currentItem()

        if item is None:
            print("Selecciona una película")
            return

        pelicula = item.data(Qt.ItemDataRole.UserRole)

        generar_xray(
            video_path=self.ruta_video,
            movie_query=pelicula["title"],
            movie_id=pelicula["tmdb_id"],
            progress_callback=self.actualizar_progreso
        )

        print("JSON generado")

    def pelicula_seleccionada(self, item):

        pelicula = item.data(Qt.ItemDataRole.UserRole)

        print(pelicula)

    def actualizar_progreso(self, porcentaje):

        if self.progress_callback:
            self.progress_callback(porcentaje)
    def actualizar_progreso(self, porcentaje):
        self.progressBar.setValue(porcentaje)
        QApplication.processEvents()
        
app = QApplication(sys.argv)

ventana = Generador()
ventana.show()

sys.exit(app.exec())