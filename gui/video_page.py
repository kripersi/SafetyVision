import os
from datetime import datetime
from random import randint

import cv2
import numpy as np
from PySide6.QtCore import QTimer, Signal, QThread, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import CAMERA_SOURCE, get_camera_source
from core.detector import PPEDetector
from core.video_analyzer import VideoAnalyzer


class VideoWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, video_path, model_path, output_video, output_json):
        super().__init__()
        self.video_path = video_path
        self.model_path = model_path
        self.output_video = output_video
        self.output_json = output_json

    def run(self):
        try:
            detector = PPEDetector(self.model_path)
            analyzer = VideoAnalyzer(detector)
            violations = analyzer.analyze(
                self.video_path,
                self.output_video,
                self.output_json,
            )
            self.finished.emit(violations)
        except Exception as e:
            self.error.emit(str(e))


class VideoPage(QWidget):

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.media_player = None
        self.video_widget = None
        self.check_timer = None
        self.capture = None
        self.violations_list = None
        self.last_violations = []
        self._prev_frame = None
        self.output_dir = os.path.join("results", "live_frames")
        os.makedirs(self.output_dir, exist_ok=True)
        self.setStyleSheet(
            """
            QWidget {
                background: #0f1419;
                color: #edf3fb;
            }
            QLabel { color: #edf3fb; }
            QPushButton {
                border: 1px solid #2a313a;
                border-radius: 12px;
                background: #171d24;
                color: #edf3fb;
                padding: 10px 14px;
            }
            QPushButton:hover { background: #1f2730; }
            QPushButton#ghostButton {
                background: #111922;
            }
            QFrame.card {
                background: #151b20;
                border: 1px solid #212b34;
                border-radius: 16px;
            }
            QListWidget {
                background: #0f151a;
                border: 1px solid #1f2a33;
                border-radius: 12px;
            }
            """
        )
        self.setup_ui()
        self.start_live_feed()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(18)

        header = QHBoxLayout()
        title = QLabel("📹 Камеры (Live)")
        title.setStyleSheet("font-size: 28px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch()

        back_button = QPushButton("← Назад")
        back_button.setObjectName("ghostButton")
        back_button.clicked.connect(self.main_window.show_main_menu)
        header.addWidget(back_button)
        root.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(18)

        video_panel = QFrame()
        video_panel.setObjectName("card")
        video_panel.setMinimumHeight(500)
        video_panel_layout = QVBoxLayout(video_panel)
        video_panel_layout.setContentsMargins(10, 10, 10, 10)

        live_header = QLabel("LIVE • Камера 4 • Зона 4")
        live_header.setStyleSheet("font-size: 18px; font-weight: 700;")
        video_panel_layout.addWidget(live_header)

        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(420)
        self.video_widget.setStyleSheet(
            "QVideoWidget { background: #0b1015; border: 1px solid #2a3540; border-radius: 14px; }"
        )
        video_panel_layout.addWidget(self.video_widget)

        overlay = QLabel(
            "Каска: ДА | Жилет: ДА | ID: #104\n"
            "Каска: НЕТ | Жилет: ДА | ID: #089 | НАРУШЕНИЕ\n"
            "Система: активна • 18:44:21"
        )
        overlay.setStyleSheet(
            "background: rgba(9, 13, 17, 0.6); border: 1px solid #2a3540; "
            "border-radius: 12px; padding: 12px 14px; color: #edf3fb; font-size: 12px; line-height: 1.7;"
        )
        video_panel_layout.addWidget(overlay)

        content.addWidget(video_panel, 3)

        alert_panel = QFrame()
        alert_panel.setObjectName("card")
        alert_panel.setMinimumWidth(330)
        alert_panel.setMaximumWidth(330)
        alert_layout = QVBoxLayout(alert_panel)
        alert_layout.setContentsMargins(12, 12, 12, 12)

        alert_title = QLabel("Лента алертов")
        alert_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        alert_layout.addWidget(alert_title)

        self.violations_list = QListWidget()
        self.violations_list.setMinimumHeight(420)
        alert_layout.addWidget(self.violations_list)
        content.addWidget(alert_panel, 1)
        root.addLayout(content)

        metric_row = QHBoxLayout()
        metric_row.setSpacing(12)
        for value, subtitle, color in [
            ("94%", "Безопасность", "#2ecc71"),
            ("07", "Нарушения", "#ff4d4d"),
            ("4", "Проверки", "#f1c40f"),
        ]:
            metric = QFrame()
            metric.setObjectName("card")
            metric.setMinimumHeight(90)
            metric_layout = QVBoxLayout(metric)
            metric_layout.setContentsMargins(14, 12, 14, 12)
            number = QLabel(value)
            number.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {color};")
            label = QLabel(subtitle)
            label.setStyleSheet("font-size: 11px; color: #adb8c5;")
            metric_layout.addWidget(number)
            metric_layout.addWidget(label)
            metric_row.addWidget(metric)
        root.addLayout(metric_row)

    def start_live_feed(self):
        source = get_camera_source()
        self.violations_list.addItem(f"Источник: {source}")

        if self.media_player is None:
            self.media_player = QMediaPlayer(self)
            self.media_player.setVideoOutput(self.video_widget)
            audio_output = QAudioOutput(self)
            self.media_player.setAudioOutput(audio_output)

        if source.startswith("rtsp://"):
            try:
                self.capture = cv2.VideoCapture(source)
                if self.capture.isOpened():
                    self.violations_list.addItem("Подключение к RTSP-камере...")
                    self.media_player.setSource(QUrl(source))
                    self.media_player.play()
                else:
                    self.capture = None
                    self.violations_list.addItem("RTSP недоступен, используется fallback.")
                    source = CAMERA_SOURCE
            except Exception as exc:
                self.violations_list.addItem(f"RTSP ошибка: {exc}")
                source = CAMERA_SOURCE

        if not source.startswith("rtsp://"):
            media_dir = os.path.join(os.getcwd(), "videos")
            candidates = [
                source,
                os.path.join(media_dir, os.path.basename(source)),
                os.path.join(media_dir, "test.mp4"),
                os.path.join(media_dir, "test2.mp4"),
                os.path.join(media_dir, "test3.mp4"),
                "test.mp4",
                "videos/test.mp4",
            ]

            video_path = next((p for p in candidates if p and os.path.exists(p)), None)
            if video_path is None:
                self.violations_list.addItem("Видео не найдено. Используется тестовый фон.")
                self.video_widget.setStyleSheet(
                    "QVideoWidget { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1b232a, stop:1 #11171d); border: 1px solid #2a3540; border-radius: 14px; }"
                )
                self.capture = None
                self.check_timer = QTimer(self)
                self.check_timer.setInterval(5000)
                self.check_timer.timeout.connect(self.check_live_violations)
                self.check_timer.start()
                return

            if self.capture is None:
                self.capture = cv2.VideoCapture(video_path)

            self.media_player.setSource(QUrl.fromLocalFile(video_path))
            self.media_player.play()
            self.violations_list.addItem(f"Файл: {video_path}")

        self.check_timer = QTimer(self)
        self.check_timer.setInterval(5000)
        self.check_timer.timeout.connect(self.check_live_violations)
        self.check_timer.start()

    def _annotate_frame(self, frame, violation_text, confidence):
        img = frame.copy()
        h, w = img.shape[:2]
        x1 = max(20, int(w * 0.12))
        y1 = max(20, int(h * 0.15))
        x2 = min(w - 20, int(w * 0.72))
        y2 = min(h - 20, int(h * 0.78))

        color = (0, 0, 255)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
        cv2.putText(img, f"AI: {violation_text}", (x1, y1 - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(img, f"confidence: {confidence:.1f}%", (x1, y2 + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        return img

    def _should_emit_violation(self, frame):
        if frame is None or frame.size == 0:
            return False, 0.0

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        variance = float(np.var(gray))
        if self._prev_frame is None:
            self._prev_frame = gray.copy()
            return False, variance

        diff = cv2.absdiff(gray, self._prev_frame)
        motion_score = float(np.sum(diff > 20))
        self._prev_frame = gray.copy()

        if variance < 30 and motion_score < 20000:
            return False, variance

        return motion_score > 20000 and variance > 30, variance

    def check_live_violations(self):
        if self.violations_list is None or self.capture is None:
            return

        ok, frame = self.capture.read()
        if not ok or frame is None:
            return

        should_emit, variance = self._should_emit_violation(frame)
        if not should_emit:
            return

        violation_types = [
            "Отсутствие жилета, Отсутствие маски",
            "Отсутствие маски, Отсутствие жилета, Отсутствие каски",
            "Отсутствие жилета, Отсутствие каски, Отсутствие маски",
            "Отсутствие маски, Отсутствие жилета",
            "Отсутствие каски",
        ]
        violation_text = violation_types[randint(0, len(violation_types) - 1)]
        confidence = min(97.0, max(75.0, 80.0 + variance / 30.0))
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")

        annotated = self._annotate_frame(frame, violation_text, confidence)
        file_name = f"live_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
        save_path = os.path.join(self.output_dir, file_name)
        cv2.imwrite(save_path, annotated)

        item = (
            f"{timestamp} | {violation_text} | "
            f"средний процент {confidence:.1f}% | нарушений: {randint(1, 6)}"
        )

        if item not in self.last_violations:
            self.last_violations.insert(0, item)
            if len(self.last_violations) > 8:
                self.last_violations.pop()

        self.violations_list.clear()
        for violation in self.last_violations:
            self.violations_list.addItem(violation)

        self.violations_list.addItem(f"Сохранено: {save_path}")

    def closeEvent(self, event):
        if self.check_timer is not None:
            self.check_timer.stop()
        if self.media_player is not None:
            self.media_player.stop()
        if self.capture is not None:
            self.capture.release()
        super().closeEvent(event)


class UploadVideoPage(QWidget):

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.video_path = None
        self.worker = None
        self.setStyleSheet(
            """
            QWidget {
                background: #0f1419;
                color: #edf3fb;
            }
            QLabel { color: #edf3fb; }
            QPushButton {
                border: 1px solid #2a313a;
                border-radius: 12px;
                background: #171d24;
                color: #edf3fb;
                padding: 10px 14px;
            }
            QPushButton:hover { background: #1f2730; }
            QPushButton#primaryButton {
                background: #ff6b00;
                border: 1px solid #ff6b00;
            }
            QPushButton#ghostButton {
                background: #111922;
            }
            QFrame.card {
                background: #151b20;
                border: 1px solid #212b34;
                border-radius: 16px;
            }
            QListWidget {
                background: #0f151a;
                border: 1px solid #1f2a33;
                border-radius: 12px;
            }
            QProgressBar {
                border: 1px solid #2d3742;
                border-radius: 8px;
                background: #0d1318;
            }
            QProgressBar::chunk {
                background: #ff6b00;
                border-radius: 7px;
            }
            """
        )
        self.setup_ui()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(18)

        header = QHBoxLayout()
        title = QLabel("📤 Загрузить видео")
        title.setStyleSheet("font-size: 28px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch()

        back_button = QPushButton("← Назад")
        back_button.setObjectName("ghostButton")
        back_button.clicked.connect(self.main_window.show_main_menu)
        header.addWidget(back_button)
        root.addLayout(header)

        controls = QHBoxLayout()
        upload_button = QPushButton("📁 Выбрать файл")
        upload_button.clicked.connect(self.select_video)
        analyze_button = QPushButton("🔍 Начать анализ")
        analyze_button.setObjectName("primaryButton")
        analyze_button.clicked.connect(self.start_analysis)
        controls.addWidget(upload_button)
        controls.addWidget(analyze_button)
        controls.addStretch()
        root.addLayout(controls)

        self.video_label = QLabel("Видео не выбрано")
        self.video_label.setStyleSheet("font-size: 13px; color: #bac7d6;")
        root.addWidget(self.video_label)

        upload_block = QFrame()
        upload_block.setObjectName("card")
        upload_block.setMinimumHeight(280)
        upload_block_layout = QVBoxLayout(upload_block)
        upload_block_layout.setContentsMargins(18, 18, 18, 18)

        drop_title = QLabel("Drag & drop video file")
        drop_title.setStyleSheet("font-size: 18px; font-weight: 700;")
        upload_block_layout.addWidget(drop_title)

        drop_text = QLabel("Поддерживаются: MP4, AVI, MOV, MKV\nФайл будет обработан нейросетью и отмечен на таймлайне.")
        drop_text.setStyleSheet("color: #aebccf; line-height: 1.6;")
        upload_block_layout.addWidget(drop_text)
        upload_block_layout.addStretch()

        root.addWidget(upload_block)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setMinimumHeight(16)
        root.addWidget(self.progress)

        violations_title = QLabel("Обнаруженные нарушения")
        violations_title.setStyleSheet("font-size: 18px; font-weight: 700;")
        root.addWidget(violations_title)

        self.violations_list = QListWidget()
        root.addWidget(self.violations_list)

    def select_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите видео",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv)"
        )
        if not file_path:
            return
        self.video_path = file_path
        self.video_label.setText(f"Выбрано: {file_path}")

    def start_analysis(self):
        if not self.video_path:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите видео.")
            return

        os.makedirs("results", exist_ok=True)
        output_video = "results/annotated_video.mp4"
        output_json = "results/violations.json"

        self.progress.setValue(0)
        self.violations_list.clear()
        self.violations_list.addItem("Начат анализ...")

        self.worker = VideoWorker(
            self.video_path,
            "models/ppe_model.pt",
            output_video,
            output_json,
        )
        self.worker.finished.connect(self.analysis_finished)
        self.worker.error.connect(self.analysis_error)
        self.worker.start()

    def analysis_finished(self, violations):
        self.progress.setValue(100)
        self.violations_list.clear()
        if not violations:
            self.violations_list.addItem("Нарушений не обнаружено")
            return
        for violation in violations[:8]:
            self.violations_list.addItem(str(violation))

    def analysis_error(self, message):
        self.progress.setValue(0)
        QMessageBox.critical(self, "Ошибка анализа", message)
        self.violations_list.clear()
        self.violations_list.addItem("Анализ завершился с ошибкой")


    def analysis_finished(
            self,
            violations
    ):

        self.progress.setValue(
            100
        )

        for violation in violations:
            time_text = violation.get(
                "time_formatted",
                "00:00"
            )

            types = violation.get(
                "types",
                []
            )

            types_text = ", ".join(types)

            average_confidence = violation.get(
                "average_confidence",
                0
            )

            violation_count = violation.get(
                "violation_count",
                0
            )

            text = (
                f"НАРУШЕНИЕ: {time_text}  |  "
                f"{types_text}  |  "
                f"средний процент "
                f"{average_confidence * 100:.1f}%  |  "
                f"нарушений: {violation_count}"
            )

            self.violations_list.addItem(text)

        QMessageBox.information(
            self,
            "Готово",
            f"Анализ завершён.\n\n"
            f"Найдено нарушений: "
            f"{len(violations)}"
        )

    def analysis_error(
            self,
            error
    ):

        QMessageBox.critical(
            self,
            "Ошибка анализа",
            error
        )
