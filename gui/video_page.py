import os

from PySide6.QtCore import Signal, QThread
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
        video_panel_layout.setContentsMargins(18, 18, 18, 18)

        live_header = QLabel("LIVE • Камера 4 • Зона 4")
        live_header.setStyleSheet("font-size: 18px; font-weight: 700;")
        video_panel_layout.addWidget(live_header)
        video_panel_layout.addStretch()

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

        violations_list = QListWidget()
        for item in [
            "11:34:19 • Без каски • ID #089",
            "11:47:10 • Без жилета • ID #104",
            "11:52:06 • Опасная зона • Камера 03",
            "12:08:32 • Требуется проверка • ID #201",
        ]:
            violations_list.addItem(item)
        alert_layout.addWidget(violations_list)
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
