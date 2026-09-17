import os
from datetime import datetime

import cv2
import numpy as np
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt, QTimer
from PySide6.QtCore import QTimer, Signal, QThread, QUrl, Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
    QGridLayout,
    QSpacerItem,
)

from config import (
    CAMERA_SOURCE,
    DISPLAY_CLASS_NAMES,
    get_camera_source,
    get_camera_sources,
    load_confidence_threshold,
)
from core.detector import PPEDetector
from core.video_analyzer import VideoAnalyzer

# ============================================================
# THEME — сдержанная, промышленная
# ============================================================

BG = "#0f1114"
PANEL = "#161a1f"
PANEL_2 = "#1c2127"
PANEL_3 = "#232932"

LINE = "#2a3138"
LINE_2 = "#343c45"

TEXT = "#e6e9ed"
TEXT_2 = "#9aa3ad"
TEXT_3 = "#5f6873"

ACCENT = "#c8722a"
ACCENT_2 = "#e08a3c"

OK = "#4a9e6a"
ERR = "#b85050"
WARN = "#b08a3c"

VIDEO_BG = "#05070a"

GLOBAL_STYLE = f"""
QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: "Inter", "Segoe UI", "Helvetica Neue", sans-serif;
    font-size: 13px;
}}

QLabel {{
    background: transparent;
    color: {TEXT};
}}

QPushButton {{
    background: {PANEL_2};
    color: {TEXT};
    border: 1px solid {LINE};
    border-radius: 3px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.2px;
}}
QPushButton:hover {{
    background: {PANEL_3};
    border-color: {LINE_2};
}}
QPushButton:pressed {{
    background: {PANEL};
}}
QPushButton:disabled {{
    color: {TEXT_3};
    border-color: {LINE};
}}

QPushButton#primaryButton {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
    color: #16110b;
    font-weight: 600;
}}
QPushButton#primaryButton:hover {{
    background: {ACCENT_2};
    border-color: {ACCENT_2};
}}

QPushButton#ghostButton {{
    background: transparent;
    border: 1px solid {LINE};
    color: {TEXT_2};
    padding: 7px 14px;
}}
QPushButton#ghostButton:hover {{
    border-color: {LINE_2};
    color: {TEXT};
    background: {PANEL};
}}

QPushButton#toolbarButton {{
    background: transparent;
    border: 1px solid {LINE};
    padding: 6px 12px;
    font-size: 11px;
    color: {TEXT_2};
}}
QPushButton#toolbarButton:hover {{
    color: {TEXT};
    border-color: {LINE_2};
}}

QFrame#card {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-radius: 4px;
}}

QFrame#videoCard {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-radius: 4px;
}}

QListWidget {{
    background: transparent;
    border: none;
    outline: none;
    padding: 0;
}}
QListWidget::item {{
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
}}
QListWidget::item:selected {{
    background: transparent;
}}

QProgressBar {{
    background: {PANEL_3};
    border: none;
    border-radius: 2px;
    height: 4px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 2px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {LINE_2};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #4a535e;
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: transparent;
}}
"""


# ============================================================
# TYPOGRAPHY / HELPERS
# ============================================================

def mono_font(size=11, weight=QFont.Medium):
    f = QFont("JetBrains Mono, Consolas, monospace")
    f.setPointSize(size)
    f.setWeight(weight)
    f.setLetterSpacing(QFont.AbsoluteSpacing, 0.4)
    return f


def section_label(text):
    """Мелкая надпись-заголовок секции, в стиле 'надстрочника'."""
    label = QLabel(text.upper())
    label.setFont(mono_font(9, QFont.DemiBold))
    label.setStyleSheet(f"color: {TEXT_3}; letter-spacing: 1.5px;")
    return label


def value_label(text, size=15, color=TEXT, weight=QFont.DemiBold):
    label = QLabel(text)
    label.setStyleSheet(f"color: {color};")
    f = label.font()
    f.setPointSize(size)
    f.setWeight(weight)
    label.setFont(f)
    return label


def hairline():
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet(f"background: {LINE};")
    return line


def metric_cell(value, label, color=TEXT):
    """Метрика в виде пары 'значение / подпись', вертикально."""
    w = QWidget()
    w.setStyleSheet("background: transparent;")
    l = QVBoxLayout(w)
    l.setContentsMargins(0, 0, 0, 0)
    l.setSpacing(4)

    v = QLabel(value)
    v.setFont(mono_font(20, QFont.Bold))
    v.setStyleSheet(f"color: {color};")

    t = QLabel(label.upper())
    t.setFont(mono_font(9, QFont.Medium))
    t.setStyleSheet(f"color: {TEXT_3}; letter-spacing: 1.2px;")

    l.addWidget(v)
    l.addWidget(t)
    return w


def tag(text, color=TEXT_2):
    """Плоский текстовый тег без закруглений и фона."""
    label = QLabel(text.upper())
    label.setFont(mono_font(9, QFont.Bold))
    label.setStyleSheet(
        f"color: {color}; letter-spacing: 1.4px;"
    )
    return label


# ============================================================
# VIDEO WORKER (без изменений)
# ============================================================

class VideoWorker(QThread):
    finished = Signal(list)
    error = Signal(str)
    progress_changed = Signal(float)

    def __init__(self, video_path, detector, detector_lock, output_video, output_json):
        super().__init__()
        self.video_path = video_path
        self.detector = detector
        self.detector_lock = detector_lock
        self.output_video = output_video
        self.output_json = output_json

    def run(self):
        try:
            analyzer = VideoAnalyzer(self.detector, self.detector_lock)
            analyzer.check_interval = 1
            analyzer.confidence_threshold = load_confidence_threshold()
            violations = analyzer.analyze(
                self.video_path,
                self.output_video,
                self.output_json,
                progress_callback=self.progress_changed.emit,
            )
            self.finished.emit(violations)
        except Exception as e:
            self.error.emit(str(e))


# ============================================================
# LIVE CAMERA PAGE
# ============================================================

class VideoPage(QWidget):

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        self.video_widget = None
        self.violations_list = None
        self.last_violations = []

        self.camera_sources = get_camera_sources()
        self.selected_camera_index = 0
        self.camera_selector = None
        self.current_worker = None  # ссылка на CameraWorker, к которому сейчас подписаны
        self.fallback_video_path = self._get_fallback_video_path()
        self.fallback_capture = None
        self.fallback_timer = None

        self.setStyleSheet(GLOBAL_STYLE)

        self.setup_ui()
        self.attach_to_camera(self.selected_camera_index)

    def _get_fallback_video_path(self):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        videos_dir = os.path.join(project_root, "videos")
        candidates = ["test.mp4", "test2.mp4", "test3.mp4"]
        for name in candidates:
            path = os.path.join(videos_dir, name)
            if os.path.exists(path):
                return path
        return None

    def _stop_fallback_video(self):
        if self.fallback_timer is not None:
            self.fallback_timer.stop()
            self.fallback_timer.deleteLater()
            self.fallback_timer = None
        if self.fallback_capture is not None:
            self.fallback_capture.release()
            self.fallback_capture = None

    def _show_fallback_video(self):
        self._stop_fallback_video()
        self.current_worker = None

        if self.camera_name is not None:
            self.camera_name.setText("БАЗОВОЕ ВИДЕО")

        if not self.fallback_video_path:
            self.video_widget.setText("Нет подключённых камер")
            return

        self.fallback_capture = cv2.VideoCapture(self.fallback_video_path)
        if not self.fallback_capture.isOpened():
            self.video_widget.setText("Нет подключённых камер")
            return

        self.fallback_timer = QTimer(self)
        self.fallback_timer.timeout.connect(self._read_fallback_frame)
        self.fallback_timer.start(33)
        self._read_fallback_frame()

    def _read_fallback_frame(self):
        if self.fallback_capture is None or not self.fallback_capture.isOpened():
            return

        ok, frame = self.fallback_capture.read()
        if not ok or frame is None:
            self.fallback_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self.fallback_capture.read()
            if not ok or frame is None:
                return

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        self.video_widget.setPixmap(
            pixmap.scaled(self.video_widget.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def on_camera_selected(self, index):
        if index < 0:
            return
        self.attach_to_camera(index)

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------



    def check_live_violations(self):

        if self.current_frame is None:
            self.add_system_event("Кадр камеры ещё не получен")
            return

        # Берём тот же самый кадр,
        # который сейчас получен от камеры
        frame = self.current_frame.copy()

        try:
            detections = self.detector.detect(frame)
        except Exception as exc:
            self.add_system_event(f"Ошибка YOLO: {exc}")
            return

        # Это самый свежий кадр камеры
        self.current_frame = frame.copy()

        # Показываем именно этот кадр
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        h, w, ch = rgb.shape
        bytes_per_line = ch * w

        image = QImage(
            rgb.data,
            w,
            h,
            bytes_per_line,
            QImage.Format_RGB888,
        )

        pixmap = QPixmap.fromImage(image)

        # Если video_widget у тебя QLabel
        self.video_widget.setPixmap(
            pixmap.scaled(
                self.video_widget.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def setup_ui(self):

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 26, 32, 26)
        root.setSpacing(20)

        # --- HEADER ---
        header = QHBoxLayout()
        header.setSpacing(20)

        title_block = QWidget()
        tb = QVBoxLayout(title_block)
        tb.setContentsMargins(0, 0, 0, 0)
        tb.setSpacing(2)

        title = QLabel("Мониторинг камер")
        f = title.font()
        f.setPointSize(20)
        f.setWeight(QFont.DemiBold)
        title.setFont(f)
        title.setStyleSheet("color: #e6e9ed; background: #000000;")

        subtitle = QLabel("Контроль объекта в реальном времени")
        subtitle.setStyleSheet(f"color: {TEXT_3}; background: #000000; font-size: 12px;")

        tb.addWidget(title)
        tb.addWidget(subtitle)

        header.addWidget(title_block)
        header.addStretch()

        header.addWidget(tag("СИСТЕМА АКТИВНА", OK))

        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background: {LINE};")
        header.addWidget(sep)

        root.addLayout(header)
        root.addWidget(hairline())

        # --- CONTENT ---
        content = QHBoxLayout()
        content.setSpacing(20)

        # --- VIDEO PANEL ---
        video_panel = QFrame()
        video_panel.setObjectName("videoCard")
        video_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        vl = QVBoxLayout(video_panel)
        vl.setContentsMargins(16, 16, 16, 16)
        vl.setSpacing(14)

        # верхняя строка с метаданными камеры
        cam_bar = QHBoxLayout()
        cam_bar.setSpacing(16)

        cam_name = QLabel("КАМЕРА 01")
        cam_name.setFont(mono_font(11, QFont.Bold))
        cam_name.setStyleSheet(f"color: {TEXT}; letter-spacing: 1.6px;")
        self.camera_name = cam_name

        self.camera_selector = QComboBox()
        self.camera_selector.setStyleSheet(
            f"QComboBox {{ background: {PANEL_2}; color: {TEXT}; border: 1px solid {LINE}; padding: 6px 10px; min-width: 150px; }}"
            f"QComboBox QAbstractItemView {{ background: {PANEL_2}; color: {TEXT}; selection-background-color: {ACCENT}; }}"
        )
        for index, camera in enumerate(self.camera_sources):
            self.camera_selector.addItem(camera["name"])
        self.camera_selector.setCurrentIndex(self.selected_camera_index)
        self.camera_selector.currentIndexChanged.connect(self.on_camera_selected)

        cam_bar.addWidget(cam_name)
        cam_bar.addStretch()
        cam_bar.addWidget(self.camera_selector)
        cam_bar.addWidget(tag("LIVE", ERR))

        toolbar_button = QPushButton("Настройки")
        toolbar_button.setObjectName("toolbarButton")
        toolbar_button.clicked.connect(self.main_window.show_settings_page)
        cam_bar.addWidget(toolbar_button)

        vl.addLayout(cam_bar)
        vl.addWidget(hairline())

        # видео
        self.video_widget = QLabel()
        self.video_widget.setAlignment(Qt.AlignCenter)
        self.video_widget.setMinimumHeight(450)
        self.video_widget.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        self.video_widget.setStyleSheet(
            f"""
            QLabel {{
                background: {VIDEO_BG};
                border: 1px solid {LINE};
                border-radius: 2px;
            }}
            """
        )

        vl.addWidget(self.video_widget, 1)

        # нижняя инфо-полоса
        info_bar = QFrame()
        info_bar.setStyleSheet(
            f"QFrame {{ background: transparent; border-top: 1px solid {LINE}; }}"
        )
        info_layout = QHBoxLayout(info_bar)
        info_layout.setContentsMargins(0, 10, 0, 0)
        info_layout.setSpacing(22)

        info_layout.addWidget(tag("ИСТОЧНИК", TEXT_3))
        info_layout.addWidget(value_label("подключено", 11, TEXT_2, QFont.Medium))
        info_layout.addStretch()
        info_layout.addWidget(tag("РАЗРЕШЕНИЕ", TEXT_3))
        info_layout.addWidget(value_label("1920 × 1080", 11, TEXT_2, QFont.Medium))
        info_layout.addSpacing(18)
        info_layout.addWidget(tag("ЧАСТОТА", TEXT_3))
        info_layout.addWidget(value_label("25 fps", 11, TEXT_2, QFont.Medium))

        vl.addWidget(info_bar)

        content.addWidget(video_panel, 3)

        # --- EVENTS PANEL ---
        events_panel = QFrame()
        events_panel.setObjectName("card")
        events_panel.setMinimumWidth(360)
        events_panel.setMaximumWidth(360)

        el = QVBoxLayout(events_panel)
        el.setContentsMargins(18, 18, 18, 18)
        el.setSpacing(14)

        ev_header = QHBoxLayout()
        ev_header.addWidget(section_label("События"))
        ev_header.addStretch()

        self.events_count = QLabel("00")
        self.events_count.setFont(mono_font(13, QFont.Bold))
        self.events_count.setStyleSheet(f"color: {ERR};")
        ev_header.addWidget(self.events_count)

        el.addLayout(ev_header)
        el.addWidget(hairline())

        self.violations_list = QListWidget()
        self.violations_list.setMinimumHeight(450)
        self.violations_list.setSpacing(0)
        el.addWidget(self.violations_list, 1)

        content.addWidget(events_panel, 1)

        root.addLayout(content, 1)


    # --------------------------------------------------------
    # LIVE FEED
    # --------------------------------------------------------

    def attach_to_camera(self, index):
        """Отписывается от предыдущего воркера и подписывается на воркер выбранной камеры.
        НЕ открывает новое RTSP-подключение — использует уже работающий поток из MainWindow."""
        self._stop_fallback_video()

        if not self.camera_sources or not any(
            self.main_window.camera_statuses.get(camera["name"]) == "connected"
            for camera in self.camera_sources
        ):
            self._show_fallback_video()
            return

        if index < 0 or index >= len(self.camera_sources):
            self._show_fallback_video()
            return

        camera_name = self.camera_sources[index]["name"]
        worker = self.main_window.camera_workers.get(camera_name)

        # отписываемся от старого
        if self.current_worker is not None:
            try:
                self.current_worker.frame_ready.disconnect(self.on_frame_ready)
                self.current_worker.violation_found.disconnect(self.on_violation_found)
            except (TypeError, RuntimeError):
                pass

        self.current_worker = worker
        self.selected_camera_index = index

        if self.violations_list is not None:
            self.violations_list.clear()
            self.update_events_count()

        if self.camera_name is not None:
            self.camera_name.setText(camera_name.upper())

        if worker is None:
            self.add_system_event("Камера не найдена")
            return

        worker.frame_ready.connect(self.on_frame_ready)
        worker.violation_found.connect(self.on_violation_found)
        self.add_system_event("Подключено к фоновому потоку камеры")

    def on_frame_ready(self, camera_name, frame):
        if camera_name != self.camera_sources[self.selected_camera_index]["name"]:
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        self.video_widget.setPixmap(
            pixmap.scaled(self.video_widget.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def on_violation_found(self, camera_name, detections):
        if camera_name != self.camera_sources[self.selected_camera_index]["name"]:
            return
        if not detections:
            self.add_system_event("YOLO: объектов не обнаружено")
            return
        objects_text = ", ".join(
            f"{DISPLAY_CLASS_NAMES.get(d['class_name'], d['class_name'])} "
            f"{d['confidence'] * 100:.0f}%" for d in detections
        )
        self.add_system_event(f"YOLO: {objects_text}")

    # --------------------------------------------------------
    # SYSTEM EVENTS
    # --------------------------------------------------------

    def update_events_count(self):
        if self.events_count is not None and self.violations_list is not None:
            self.events_count.setText(f"{self.violations_list.count():02d}")

    def add_system_event(self, text):

        if self.violations_list is None:
            return

        item = QListWidgetItem()
        widget = QFrame()
        widget.setStyleSheet(
            f"""
            QFrame {{
                background: transparent;
                border: none;
                border-bottom: 1px solid {LINE};
            }}
            """
        )

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(10)

        mark = QLabel("·")
        mark.setFont(mono_font(11, QFont.Bold))
        mark.setStyleSheet(f"color: {TEXT_3};")
        mark.setFixedWidth(10)
        layout.addWidget(mark)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {TEXT_3}; font-size: 11px;")
        layout.addWidget(label, 1)

        item.setSizeHint(widget.sizeHint())
        self.violations_list.insertItem(self.violations_list.count(), item)
        self.violations_list.setItemWidget(item, widget)
        self.update_events_count()


    def refresh_violation_list(self):

        if self.violations_list is None:
            return

        self.violations_list.clear()
        self.update_events_count()

        for v in self.last_violations:
            item = QListWidgetItem()

            widget = QFrame()
            widget.setStyleSheet(
                f"""
                QFrame {{
                    background: transparent;
                    border: none;
                    border-bottom: 1px solid {LINE};
                }}
                """
            )

            outer = QHBoxLayout(widget)
            outer.setContentsMargins(0, 10, 0, 10)
            outer.setSpacing(12)

            # левая цветная полоса-индикатор
            bar = QFrame()
            bar.setFixedWidth(2)
            bar.setStyleSheet(f"background: {ERR}; border-radius: 1px;")
            outer.addWidget(bar)

            body = QVBoxLayout()
            body.setContentsMargins(0, 0, 0, 0)
            body.setSpacing(5)

            top = QHBoxLayout()
            top.setSpacing(8)

            time_label = QLabel(v["time"])
            time_label.setFont(mono_font(10, QFont.Medium))
            time_label.setStyleSheet(f"color: {TEXT_3};")
            top.addWidget(time_label)

            top.addStretch()

            kind = QLabel("НАРУШЕНИЕ")
            kind.setFont(mono_font(9, QFont.Bold))
            kind.setStyleSheet(f"color: {ERR}; letter-spacing: 1.3px;")
            top.addWidget(kind)

            body.addLayout(top)

            type_label = QLabel(v["type"])
            type_label.setWordWrap(True)
            type_label.setStyleSheet(
                f"color: {TEXT}; font-size: 12px; font-weight: 500;"
            )
            body.addWidget(type_label)

            meta = QLabel(
                f'Уверенность  {v["confidence"]:.1f}%'
                f'      Объектов  {v["count"]}'
            )
            meta.setFont(mono_font(10, QFont.Normal))
            meta.setStyleSheet(f"color: {TEXT_3};")
            body.addWidget(meta)

            outer.addLayout(body, 1)

            item.setSizeHint(widget.sizeHint())
            self.violations_list.addItem(item)
            self.violations_list.setItemWidget(item, widget)

        self.update_events_count()

    # --------------------------------------------------------
    # CLOSE
    # --------------------------------------------------------

    def closeEvent(self, event):
        self._stop_fallback_video()
        if self.current_worker is not None:
            try:
                self.current_worker.frame_ready.disconnect(self.on_frame_ready)
                self.current_worker.violation_found.disconnect(self.on_violation_found)
            except (TypeError, RuntimeError):
                pass
        super().closeEvent(event)


# ============================================================
# UPLOAD VIDEO PAGE
# ============================================================

class UploadVideoPage(QWidget):

    def __init__(self, main_window):
        super().__init__()

        self.main_window = main_window

        self.media_player = None
        self.audio_output = None
        self.video_widget = None
        self.annotated_video_path = None
        self.check_timer = None
        self.capture = None

        self.violations_list = None
        self.last_violations = []

        self.output_dir = os.path.join(
            "results",
            "live_frames"
        )

        os.makedirs(
            self.output_dir,
            exist_ok=True
        )

        self.setStyleSheet(GLOBAL_STYLE)

        self.setup_ui()

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    def setup_ui(self):

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 26, 32, 26)
        root.setSpacing(20)

        # --- HEADER ---
        header = QHBoxLayout()
        header.setSpacing(20)

        title_block = QWidget()
        tb = QVBoxLayout(title_block)
        tb.setContentsMargins(0, 0, 0, 0)
        tb.setSpacing(2)

        title = QLabel("Анализ видеозаписи")
        f = title.font()
        f.setPointSize(20)
        f.setWeight(QFont.DemiBold)
        title.setFont(f)
        title.setStyleSheet("color: #e6e9ed; background: #000000;")

        subtitle = QLabel(
            "Загрузка архива и автоматическое обнаружение нарушений"
        )
        subtitle.setStyleSheet(f"color: {TEXT_3}; background: #000000; font-size: 12px;")

        tb.addWidget(title)
        tb.addWidget(subtitle)

        header.addWidget(title_block)
        header.addStretch()

        root.addLayout(header)
        root.addWidget(hairline())

        # --- CONTROL BAR ---
        controls_card = QFrame()
        controls_card.setObjectName("card")

        cl = QHBoxLayout(controls_card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(10)

        upload_button = QPushButton("Выбрать видео")
        upload_button.clicked.connect(self.select_video)

        analyze_button = QPushButton("Начать анализ")
        analyze_button.setObjectName("primaryButton")
        analyze_button.clicked.connect(self.start_analysis)

        cl.addWidget(upload_button)
        cl.addWidget(analyze_button)
        cl.addStretch()

        file_box = QVBoxLayout()
        file_box.setContentsMargins(0, 0, 0, 0)
        file_box.setSpacing(3)

        file_caption = QLabel("ФАЙЛ")
        file_caption.setFont(mono_font(9, QFont.Bold))
        file_caption.setStyleSheet(f"color: {TEXT_3}; letter-spacing: 1.4px;")

        self.video_label = QLabel("не выбран")
        self.video_label.setFont(mono_font(11, QFont.Medium))
        self.video_label.setStyleSheet(f"color: {TEXT_2};")

        formats = QLabel("MP4  ·  AVI  ·  MOV  ·  MKV")
        formats.setFont(mono_font(9, QFont.Medium))
        formats.setStyleSheet(f"color: {TEXT_3}; letter-spacing: 1px;")

        file_box.addWidget(file_caption)
        file_box.addWidget(self.video_label)
        file_box.addWidget(formats)

        cl.addLayout(file_box)

        root.addWidget(controls_card)

        # --- PROGRESS ---
        progress_header = QHBoxLayout()

        progress_title = QLabel("ПРОГРЕСС ОБРАБОТКИ")
        progress_title.setFont(mono_font(9, QFont.Bold))
        progress_title.setStyleSheet(
            f"color: {TEXT_3}; letter-spacing: 1.5px;"
        )
        progress_header.addWidget(progress_title)
        progress_header.addStretch()

        self.progress_value = QLabel("0%")
        self.progress_value.setFont(mono_font(11, QFont.DemiBold))
        self.progress_value.setStyleSheet(f"color: {TEXT_2};")
        progress_header.addWidget(self.progress_value)

        root.addLayout(progress_header)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        root.addWidget(self.progress)

        analysis_row = QHBoxLayout()
        analysis_row.setSpacing(16)

        playback_card = QFrame()
        playback_card.setObjectName("card")
        playback_card.setMinimumWidth(520)
        playback_layout = QVBoxLayout(playback_card)
        playback_layout.setContentsMargins(14, 12, 14, 12)
        playback_layout.setSpacing(10)

        playback_header = QHBoxLayout()
        playback_header.addWidget(section_label("Обработанное видео"))
        playback_header.addStretch()
        self.play_processed_button = QPushButton("Воспроизвести")
        self.play_processed_button.setObjectName("primaryButton")
        self.play_processed_button.setEnabled(False)
        self.play_processed_button.clicked.connect(self.play_annotated_video)
        playback_header.addWidget(self.play_processed_button)
        playback_layout.addLayout(playback_header)

        video_stack = QWidget()
        video_stack_layout = QStackedLayout(video_stack)
        video_stack_layout.setContentsMargins(0, 0, 0, 0)

        self.processed_preview = QLabel("Ожидание обработанного видео")
        self.processed_preview.setAlignment(Qt.AlignCenter)
        self.processed_preview.setMinimumHeight(220)
        self.processed_preview.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )
        self.processed_preview.setStyleSheet(
            f"background: {VIDEO_BG}; border: 1px solid {LINE}; color: {TEXT_3};"
        )
        video_stack_layout.addWidget(self.processed_preview)

        self.processed_video_widget = QVideoWidget()
        self.processed_video_widget.setMinimumHeight(220)
        self.processed_video_widget.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )
        self.processed_video_widget.setStyleSheet(
            f"background: {VIDEO_BG}; border: 1px solid {LINE};"
        )
        video_stack_layout.addWidget(self.processed_video_widget)
        self.video_stack_layout = video_stack_layout
        playback_layout.addWidget(video_stack)
        analysis_row.addWidget(playback_card, 2)

        self.audio_output = QAudioOutput(self)
        self.media_player = QMediaPlayer(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.processed_video_widget)

        # --- RESULTS ---
        result_card = QFrame()
        result_card.setObjectName("card")
        result_card.setMinimumWidth(360)

        rl = QVBoxLayout(result_card)
        rl.setContentsMargins(18, 18, 18, 18)
        rl.setSpacing(14)

        rh = QHBoxLayout()
        rh.addWidget(section_label("Результаты анализа"))
        rh.addStretch()
        rl.addLayout(rh)

        rl.addWidget(hairline())

        self.violations_list = QListWidget()
        self.violations_list.setMinimumHeight(220)
        self.violations_list.setSpacing(0)
        rl.addWidget(self.violations_list)

        analysis_row.addWidget(result_card, 1)
        root.addLayout(analysis_row, 1)

    # --------------------------------------------------------
    # SELECT
    # --------------------------------------------------------

    def select_video(self):

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите видео",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv)",
        )

        if not file_path:
            return

        self.video_path = file_path
        self.video_label.setText(os.path.basename(file_path))
        self.video_label.setToolTip(file_path)

    # --------------------------------------------------------
    # ANALYSIS
    # --------------------------------------------------------

    def start_analysis(self):

        if not self.video_path:
            QMessageBox.warning(
                self,
                "Файл не выбран",
                "Сначала выберите видео для анализа.",
            )
            return

        os.makedirs("results", exist_ok=True)

        output_video = "results/annotated_video.mp4"
        output_json = "results/video_analysis_violations.json"

        self.progress.setValue(0)
        self.progress_value.setText("0%")
        self.violations_list.clear()
        self.play_processed_button.setEnabled(False)
        self.media_player.stop()
        self.video_stack_layout.setCurrentWidget(self.processed_preview)

        self.add_result_event(
            "Анализ запущен",
            "Видеофайл передан на обработку",
            ACCENT,
        )

        self.worker = VideoWorker(
            self.video_path,
            self.main_window.detector,
            self.main_window.detector_lock,
            output_video,
            output_json,
        )
        self.worker.finished.connect(self.analysis_finished)
        self.worker.error.connect(self.analysis_error)
        self.worker.progress_changed.connect(self.update_analysis_progress)
        self.worker.start()

    def update_analysis_progress(self, value):
        progress = max(0, min(100, int(value)))
        self.progress.setValue(progress)
        self.progress_value.setText(f"{progress}%")

    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    def add_result_event(self, title, description, color):

        item = QListWidgetItem()

        widget = QFrame()
        widget.setStyleSheet(
            f"""
            QFrame {{
                background: transparent;
                border: none;
                border-bottom: 1px solid {LINE};
            }}
            """
        )

        outer = QHBoxLayout(widget)
        outer.setContentsMargins(0, 10, 0, 10)
        outer.setSpacing(12)

        bar = QFrame()
        bar.setFixedWidth(2)
        bar.setStyleSheet(f"background: {color}; border-radius: 1px;")
        outer.addWidget(bar)

        body = QVBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(3)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {TEXT}; font-size: 12px; font-weight: 600;"
        )
        body.addWidget(title_label)

        description_label = QLabel(description)
        description_label.setWordWrap(True)
        description_label.setStyleSheet(
            f"color: {TEXT_3}; font-size: 11px;"
        )
        body.addWidget(description_label)

        outer.addLayout(body, 1)

        item.setSizeHint(widget.sizeHint())
        self.violations_list.addItem(item)
        self.violations_list.setItemWidget(item, widget)

    def analysis_finished(self, violations):

        self.progress.setValue(100)
        self.progress_value.setText("100%")
        self.violations_list.clear()
        self.annotated_video_path = os.path.abspath("results/annotated_video.mp4")
        if os.path.exists(self.annotated_video_path):
            capture = cv2.VideoCapture(self.annotated_video_path)
            ok, frame = capture.read()
            capture.release()
            if ok and frame is not None:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width, channels = rgb.shape
                image = QImage(
                    rgb.data,
                    width,
                    height,
                    channels * width,
                    QImage.Format_RGB888,
                ).copy()
                self.processed_preview.setPixmap(
                    QPixmap.fromImage(image).scaled(
                        self.processed_preview.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
            self.media_player.setSource(QUrl.fromLocalFile(self.annotated_video_path))
            self.play_processed_button.setEnabled(True)
            self.add_result_event(
                "Видео обработано",
                "Размеченное видео готово к просмотру ниже.",
                OK,
            )

        if not violations:
            self.add_result_event(
                "Нарушений не обнаружено",
                "По результатам анализа нарушений не найдено.",
                OK,
            )
            return

        for violation in violations:

            if isinstance(violation, dict):
                time_text = violation.get("time_formatted", "00:00")
                types = violation.get("types", [])
                types_text = ", ".join(types)
                average_confidence = violation.get("average_confidence", 0)
                violation_count = violation.get("violation_count", 0)

                text = (
                    f"{types_text}   ·   "
                    f"{average_confidence * 100:.1f}%   ·   "
                    f"объектов: {violation_count}"
                )
                self.add_result_event(
                    f"Нарушение · {time_text}",
                    text,
                    ERR,
                )
            else:
                self.add_result_event("Нарушение", str(violation), ERR)

        QMessageBox.information(
            self,
            "Анализ завершён",
            f"Обнаружено событий: {len(violations)}",
        )

    def play_annotated_video(self):
        if not self.annotated_video_path or not os.path.exists(self.annotated_video_path):
            return
        self.video_stack_layout.setCurrentWidget(self.processed_video_widget)
        self.media_player.play()

    def analysis_error(self, error):

        self.progress.setValue(0)
        self.progress_value.setText("ошибка")
        self.violations_list.clear()

        self.add_result_event("Ошибка анализа", str(error), ERR)

        QMessageBox.critical(self, "Ошибка анализа", str(error))
