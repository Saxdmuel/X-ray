import json
import sys
from pathlib import Path

import requests
import vlc
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


BASE_DIR = Path(__file__).resolve().parent.parent
VIDEO_PATH = BASE_DIR / "reproductor" / "malditos-baja.mp4"
XRAY_JSON_PATH = BASE_DIR / "resultado.json"


class Reproductor(QWidget):
    def __init__(self, video_path=VIDEO_PATH, json_path=XRAY_JSON_PATH):
        super().__init__()
        self.setWindowTitle("Reproductor VLC X-Ray")
        self.setGeometry(300, 200, 1100, 620)

        self.video_path = Path(video_path)
        self.json_path = Path(json_path)

        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()

        self.xray_data = self.cargar_xray(self.json_path)
        self.timeline = self.xray_data.get("timeline", [])
        self.pixmap_cache = {}
        self.current_actor_key = None
        self.media_loaded = False
        self.controls_visible = True

        self.video_frame = QFrame(self)
        self.video_frame.setStyleSheet("background-color: black;")
        self.setMouseTracking(True)
        self.video_frame.setMouseTracking(True)

        self.xray_panel = QWidget()
        self.xray_panel.setFixedWidth(280)
        self.xray_layout = QVBoxLayout()
        self.xray_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.xray_panel.setLayout(self.xray_layout)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.xray_panel)
        self.scroll.setStyleSheet("""
            QScrollArea {
                background-color: #151515;
                border: none;
            }
        """)

        self.btn_play = QPushButton("Reproducir")
        self.btn_pause = QPushButton("Pausar")
        self.btn_stop = QPushButton("Detener")
        self.btn_back = QPushButton("-10s")
        self.btn_forward = QPushButton("+10s")
        self.btn_xray = QPushButton("Ocultar X-Ray")
        self.btn_full = QPushButton("Pantalla completa")

        self.controls_widget = QWidget()
        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.addWidget(self.btn_play)
        controls.addWidget(self.btn_pause)
        controls.addWidget(self.btn_stop)
        controls.addWidget(self.btn_back)
        controls.addWidget(self.btn_forward)
        controls.addWidget(self.btn_xray)
        controls.addWidget(self.btn_full)
        self.controls_widget.setLayout(controls)

        main_area = QHBoxLayout()
        main_area.addWidget(self.video_frame, 1)
        main_area.addWidget(self.scroll)

        layout = QVBoxLayout()
        layout.addLayout(main_area, 1)
        layout.addWidget(self.controls_widget)
        self.setLayout(layout)

        self.btn_play.clicked.connect(self.play_video)
        self.btn_pause.clicked.connect(self.pause_video)
        self.btn_stop.clicked.connect(self.stop_video)
        self.btn_back.clicked.connect(lambda: self.saltar_segundos(-10))
        self.btn_forward.clicked.connect(lambda: self.saltar_segundos(10))
        self.btn_xray.clicked.connect(self.toggle_xray)
        self.btn_full.clicked.connect(self.full_screen)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.actualizar_xray)
        self.timer.start(500)

        self.hide_controls_timer = QTimer(self)
        self.hide_controls_timer.setSingleShot(True)
        self.hide_controls_timer.timeout.connect(self.ocultar_controles)

        self.mostrar_actores([])

    def cargar_xray(self, json_path):
        if not json_path.exists():
            return {"timeline": []}

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return {"timeline": data}

        return data

    def play_video(self):
        if not self.media_loaded:
            media = self.instance.media_new(str(self.video_path))
            self.player.set_media(media)

            if sys.platform.startswith("win"):
                self.player.set_hwnd(int(self.video_frame.winId()))
            else:
                self.player.set_xwindow(int(self.video_frame.winId()))

            self.media_loaded = True

        self.player.play()

    def pause_video(self):
        self.player.pause()

    def stop_video(self):
        self.player.stop()
        self.current_actor_key = None
        self.mostrar_actores([])

    def saltar_segundos(self, segundos):
        current_ms = self.player.get_time()
        if current_ms < 0:
            current_ms = 0

        target_ms = max(0, current_ms + segundos * 1000)
        duration_ms = self.player.get_length()

        if duration_ms > 0:
            target_ms = min(target_ms, duration_ms)

        self.player.set_time(int(target_ms))
        self.current_actor_key = None
        self.actualizar_xray()

    def toggle_xray(self):
        if self.scroll.isVisible():
            self.scroll.hide()
            self.btn_xray.setText("Mostrar X-Ray")
        else:
            self.scroll.show()
            self.btn_xray.setText("Ocultar X-Ray")

    def full_screen(self):
        if self.isFullScreen():
            self.showNormal()
            self.btn_full.setText("Pantalla completa")
            self.mostrar_controles()
        else:
            self.showFullScreen()
            self.btn_full.setText("Salir")
            self.mostrar_controles()

    def mostrar_controles(self):
        self.controls_visible = True
        self.controls_widget.show()
        self.hide_controls_timer.start(2500)

    def ocultar_controles(self):
        if self.underMouse():
            self.hide_controls_timer.start(1200)
            return

        self.controls_visible = False
        self.controls_widget.hide()

    def mouseMoveEvent(self, event):
        self.mostrar_controles()
        super().mouseMoveEvent(event)

    def enterEvent(self, event):
        self.mostrar_controles()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hide_controls_timer.start(700)
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        key = event.key()

        if key == Qt.Key.Key_Right:
            self.saltar_segundos(10)
        elif key == Qt.Key.Key_Left:
            self.saltar_segundos(-10)
        elif key == Qt.Key.Key_Space:
            self.pause_video()
        elif key == Qt.Key.Key_F:
            self.full_screen()
        elif key == Qt.Key.Key_Escape and self.isFullScreen():
            self.full_screen()
        else:
            super().keyPressEvent(event)

    def actores_en_segundo(self, segundo):
        for item in self.timeline:
            if item["start"] <= segundo < item["end"]:
                return item.get("actors", [])

        return []

    def actualizar_xray(self):
        current_ms = self.player.get_time()
        if current_ms < 0:
            return

        segundo = current_ms / 1000
        actors = self.actores_en_segundo(segundo)
        actor_key = tuple(
            (actor.get("tmdb_id"), actor.get("name"), actor.get("score"))
            for actor in actors
        )

        if actor_key == self.current_actor_key:
            return

        self.current_actor_key = actor_key
        self.mostrar_actores(actors)

    def limpiar_xray(self):
        while self.xray_layout.count():
            item = self.xray_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def mostrar_actores(self, actors):
        self.limpiar_xray()

        movie = self.xray_data.get("movie", {})
        movie_title = movie.get("title") or "X-Ray"
        title = QLabel(movie_title)
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
                padding: 12px 10px 8px 10px;
            }
        """)
        self.xray_layout.addWidget(title)

        subtitle = QLabel("X-Ray de actores")
        subtitle.setStyleSheet("""
            QLabel {
                color: #9a9a9a;
                font-size: 12px;
                padding: 0 10px 10px 10px;
            }
        """)
        self.xray_layout.addWidget(subtitle)

        if not actors:
            empty = QLabel("Sin actores detectados")
            empty.setWordWrap(True)
            empty.setStyleSheet("""
                QLabel {
                    color: #a0a0a0;
                    font-size: 13px;
                    padding: 0 10px;
                }
            """)
            self.xray_layout.addWidget(empty)
            self.xray_layout.addStretch()
            return

        for actor in actors:
            self.xray_layout.addWidget(self.crear_actor_card(actor))

        self.xray_layout.addStretch()

    def crear_actor_card(self, actor):
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: #222;
                border-radius: 6px;
            }
        """)

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        card.setLayout(layout)

        image = QLabel()
        image.setFixedSize(72, 96)
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image.setStyleSheet("background-color: #333; color: #aaa;")

        pixmap = self.obtener_pixmap(actor.get("image_url"))
        if pixmap is not None:
            image.setPixmap(
                pixmap.scaled(
                    72,
                    96,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
        else:
            image.setText("Sin imagen")

        text_layout = QVBoxLayout()

        name = QLabel(actor.get("name") or "Actor")
        name.setWordWrap(True)
        name.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")

        character = QLabel(actor.get("character") or "")
        character.setWordWrap(True)
        character.setStyleSheet("color: #c9c9c9; font-size: 12px;")

        score = actor.get("score")
        detections = actor.get("detections")
        meta_text = []
        if score is not None:
            meta_text.append(f"{score:.2f}")
        if detections is not None:
            meta_text.append(f"{detections} det.")

        meta = QLabel(" | ".join(meta_text))
        meta.setStyleSheet("color: #8f8f8f; font-size: 11px;")

        text_layout.addWidget(name)
        text_layout.addWidget(character)
        text_layout.addStretch()
        text_layout.addWidget(meta)

        layout.addWidget(image)
        layout.addLayout(text_layout, 1)

        return card

    def obtener_pixmap(self, image_url):
        if not image_url:
            return None

        if image_url in self.pixmap_cache:
            return self.pixmap_cache[image_url]

        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            return None

        pixmap = QPixmap()
        if not pixmap.loadFromData(response.content):
            return None

        self.pixmap_cache[image_url] = pixmap
        return pixmap


if __name__ == "__main__":
    video_path = Path(sys.argv[1]) if len(sys.argv) > 1 else VIDEO_PATH
    json_path = Path(sys.argv[2]) if len(sys.argv) > 2 else XRAY_JSON_PATH

    app = QApplication(sys.argv)
    ventana = Reproductor(video_path=video_path, json_path=json_path)
    ventana.show()
    sys.exit(app.exec())
