from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout
)

from gui.video_page import VideoPage
from gui.shift_page import ShiftPage


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("BIM-Safety")

        self.setMinimumSize(1000, 650)

        self.show_main_menu()

    def clear_window(self):
        old_widget = self.centralWidget()

        if old_widget:
            old_widget.deleteLater()

    def show_main_menu(self):
        self.clear_window()

        widget = QWidget()
        layout = QVBoxLayout()

        title = QLabel("BIM-Safety")
        title.setStyleSheet(
            "font-size: 36px; font-weight: bold;"
        )

        subtitle = QLabel(
            "Система контроля безопасности "
            "на строительной площадке"
        )

        subtitle.setStyleSheet(
            "font-size: 16px;"
        )

        video_button = QPushButton(
            "🎥  ВИДЕО"
        )

        shift_button = QPushButton(
            "👷  СМЕНА"
        )

        video_button.setMinimumHeight(100)
        shift_button.setMinimumHeight(100)

        video_button.clicked.connect(
            self.show_video_page
        )

        shift_button.clicked.connect(
            self.show_shift_page
        )

        buttons = QHBoxLayout()

        buttons.addWidget(video_button)
        buttons.addWidget(shift_button)

        layout.addStretch()

        layout.addWidget(
            title
        )

        layout.addWidget(
            subtitle
        )

        layout.addSpacing(40)

        layout.addLayout(
            buttons
        )

        layout.addStretch()

        widget.setLayout(layout)

        self.setCentralWidget(widget)

    def show_video_page(self):
        self.clear_window()

        self.setCentralWidget(
            VideoPage(self)
        )

    def show_shift_page(self):
        self.clear_window()

        self.setCentralWidget(
            ShiftPage(self)
        )
