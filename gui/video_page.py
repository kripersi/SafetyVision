import os

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QProgressBar,
    QMessageBox,
    QListWidget
)

from PySide6.QtCore import QThread, Signal

from core.detector import PPEDetector
from core.video_analyzer import VideoAnalyzer


class VideoWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(
            self,
            video_path,
            model_path,
            output_video,
            output_json
    ):

        super().__init__()

        self.video_path = video_path
        self.model_path = model_path
        self.output_video = output_video
        self.output_json = output_json

    def run(self):

        try:

            detector = PPEDetector(
                self.model_path
            )

            analyzer = VideoAnalyzer(
                detector
            )

            violations = analyzer.analyze(
                self.video_path,
                self.output_video,
                self.output_json
            )

            self.finished.emit(
                violations
            )

        except Exception as e:

            self.error.emit(
                str(e)
            )


class VideoPage(QWidget):

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.video_path = None
        self.worker = None
        self.setup_ui()

    def setup_ui(self):

        layout = QVBoxLayout()

        title = QLabel(
            "🎥 Анализ видео"
        )

        title.setStyleSheet(
            "font-size: 30px; font-weight: bold;"
        )

        # Кнопки
        buttons = QHBoxLayout()
        upload_button = QPushButton(
            "📁 Загрузить видео"
        )

        analyze_button = QPushButton(
            "🔍 Начать анализ"
        )

        back_button = QPushButton(
            "← Назад"
        )

        upload_button.clicked.connect(
            self.select_video
        )

        analyze_button.clicked.connect(
            self.start_analysis
        )

        back_button.clicked.connect(
            self.main_window.show_main_menu
        )

        buttons.addWidget(
            upload_button
        )

        buttons.addWidget(
            analyze_button
        )

        buttons.addStretch()

        buttons.addWidget(
            back_button
        )

        # Информация

        self.video_label = QLabel(
            "Видео не выбрано"
        )

        self.video_label.setStyleSheet(
            "font-size: 16px;"
        )

        # Прогресс

        self.progress = QProgressBar()

        self.progress.setRange(
            0,
            100
        )

        self.progress.setValue(
            0
        )

        # Нарушения

        violations_title = QLabel(
            "Обнаруженные нарушения"
        )

        violations_title.setStyleSheet(
            "font-size: 20px; font-weight: bold;"
        )

        self.violations_list = QListWidget()

        layout.addWidget(
            title
        )

        layout.addLayout(
            buttons
        )

        layout.addSpacing(20)

        layout.addWidget(
            self.video_label
        )

        layout.addWidget(
            self.progress
        )

        layout.addSpacing(20)

        layout.addWidget(
            violations_title
        )

        layout.addWidget(
            self.violations_list
        )

        self.setLayout(
            layout
        )

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

        self.video_label.setText(
            f"Выбрано:\n{file_path}"
        )

    def start_analysis(self):

        if not self.video_path:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Сначала выберите видео."
            )

            return

        os.makedirs(
            "results",
            exist_ok=True
        )

        output_video = (
            "results/annotated_video.mp4"
        )

        output_json = (
            "results/violations.json"
        )

        self.progress.setValue(
            0
        )

        self.violations_list.clear()

        self.worker = VideoWorker(
            self.video_path,
            "models/ppe_model.pt",
            output_video,
            output_json
        )

        self.worker.finished.connect(
            self.analysis_finished
        )

        self.worker.error.connect(
            self.analysis_error
        )

        self.worker.start()

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
