from PySide6.QtCore import QDateTime, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.shift_page import ShiftPage
from gui.video_page import UploadVideoPage, VideoPage


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("СтройОко AI")
        self.resize(1480, 920)
        self.setMinimumSize(1200, 780)
        self.setStyleSheet(
            """
            QMainWindow {
                background: #0f1115;
                color: #edf2f7;
            }
            QWidget {
                background: transparent;
                color: #edf2f7;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #edf2f7;
            }
            QPushButton {
                border: 1px solid #2b3038;
                border-radius: 12px;
                background: #1a1e25;
                color: #edf2f7;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #222833;
            }
            QPushButton#navButton {
                background: transparent;
                border: 1px solid transparent;
                text-align: left;
                padding: 12px 14px;
                border-radius: 12px;
                font-size: 13px;
                color: #c7ced9;
            }
            QPushButton#navButton:hover {
                background: #171c22;
                border: 1px solid #2a2f3a;
            }
            QPushButton#navButton.active {
                background: #ff6b00;
                color: #fff;
                border: 1px solid #ff6b00;
            }
            QPushButton#actionPrimary {
                background: #ff6b00;
                border: 1px solid #ff6b00;
                color: #fff;
            }
            QPushButton#smallAction {
                background: #141a20;
                border: 1px solid #2a2f38;
                padding: 8px 12px;
                font-size: 12px;
            }
            QFrame.card {
                background: #171b20;
                border: 1px solid #232a32;
                border-radius: 16px;
            }
            QFrame.cardHeader {
                background: rgba(255,255,255,0.02);
                border: 1px solid #222933;
                border-radius: 12px;
            }
            QListWidget {
                background: #11151a;
                border: 1px solid #202733;
                border-radius: 14px;
                padding: 8px;
            }
            QListWidget::item {
                border-radius: 10px;
                background: #171c23;
                border: 1px solid #202833;
                margin: 6px 0;
            }
            QProgressBar {
                border: 1px solid #2a3039;
                border-radius: 8px;
                background: #10151a;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #ff6b00;
                border-radius: 7px;
            }
            """
        )
        self.clock_label = None
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.show_main_menu()

    def update_clock(self):
        if self.clock_label is None:
            return
        try:
            self.clock_label.setText(
                QDateTime.currentDateTime().toString("dd.MM.yyyy  hh:mm:ss")
            )
        except RuntimeError:
            self.clock_timer.stop()

    def clear_window(self):
        self.clock_timer.stop()
        old_widget = self.centralWidget()
        if old_widget:
            old_widget.deleteLater()
        self.clock_label = None

    def make_nav_button(self, text, callback=None, active=False):
        button = QPushButton(text)
        button.setObjectName("navButton")
        if active:
            button.setObjectName("navButton")
            button.setProperty("active", True)
            button.style().unpolish(button)
            button.style().polish(button)
        if callback:
            button.clicked.connect(callback)
        button.setMinimumHeight(46)
        return button

    def build_dashboard(self):
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(240)
        sidebar.setMaximumWidth(240)
        sidebar_style = """
            QWidget#sidebar {
                background: #12161b;
                border: 1px solid #1d252d;
                border-left: none;
                border-top: none;
                border-bottom: none;
            }
        """
        sidebar.setStyleSheet(sidebar_style)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 18, 18, 18)
        sidebar_layout.setSpacing(14)

        logo = QLabel("🛡️ СтройОко AI")
        logo.setStyleSheet(
            "font-size: 24px; font-weight: 700; color: #f8f9fb; margin-bottom: 18px;"
        )
        sidebar_layout.addWidget(logo)

        nav_buttons = [
            ("🏠 Главная", self.show_main_menu, True),
            ("📹 Камеры (Live)", self.show_live_page, False),
            ("📤 Загрузить видео", self.show_upload_page, False),
            ("🗺️ Карта объекта", self.show_shift_page, False),
            ("📊 Отчеты", self.show_shift_page, False),
        ]

        for text, callback, active in nav_buttons:
            btn = self.make_nav_button(text, callback, active)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        settings = self.make_nav_button("⚙️ Настройки", None, False)
        profile = self.make_nav_button("👤 Профиль прораба", None, False)
        sidebar_layout.addWidget(settings)
        sidebar_layout.addWidget(profile)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(18)

        topbar = QWidget()
        topbar.setObjectName("topbar")
        topbar.setStyleSheet(
            "QWidget#topbar { background: #12181d; border: 1px solid #202932; border-radius: 16px; padding: 10px; }"
        )
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(18, 12, 18, 12)

        status = QLabel("● Система активна / ИИ анализирует")
        status.setStyleSheet("color: #2ecc71; font-weight: 600; font-size: 13px;")
        topbar_layout.addWidget(status)

        object_box = QPushButton("ЖК \"Высоты\", Зона 4")
        object_box.setObjectName("smallAction")
        topbar_layout.addStretch()
        topbar_layout.addWidget(object_box)

        self.clock_label = QLabel()
        self.clock_label.setObjectName("clockLabel")
        self.clock_label.setStyleSheet("color: #dfe7f3; font-weight: 600; font-size: 13px;")
        self.update_clock()
        topbar_layout.addWidget(self.clock_label)

        bell = QPushButton("🔔 2")
        bell.setObjectName("smallAction")
        topbar_layout.addWidget(bell)

        content_layout.addWidget(topbar)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)
        for title, value, color in [
            ("Безопасность объекта", "94%", "#2ecc71"),
            ("Активных камер", "12", "#ff6b00"),
            ("Алертов сегодня", "07", "#ff4d4d"),
            ("Реакция ИИ", "3.1 мин", "#f1c40f"),
        ]:
            card = QFrame()
            card.setObjectName("card")
            card.setMinimumHeight(108)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            label_value = QLabel(value)
            label_value.setStyleSheet(f"font-size: 32px; font-weight: 700; color: {color};")
            label_title = QLabel(title)
            label_title.setStyleSheet("font-size: 12px; color: #96a3b7;")
            card_layout.addWidget(label_value)
            card_layout.addWidget(label_title)
            stats_row.addWidget(card)
        content_layout.addLayout(stats_row)

        main_grid = QHBoxLayout()
        main_grid.setSpacing(18)

        left_panel = QFrame()
        left_panel.setObjectName("card")
        left_panel.setMinimumHeight(500)
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel_layout.setContentsMargins(18, 18, 18, 18)

        left_title = QLabel("Камеры в реальном времени")
        left_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #f4f7fb;")
        left_panel_layout.addWidget(left_title)

        video_mock = QFrame()
        video_mock.setStyleSheet(
            """
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1b232a, stop:1 #11171d);
                border: 1px solid #29323a;
                border-radius: 16px;
            }
            """
        )
        video_mock.setMinimumHeight(320)
        video_mock_layout = QVBoxLayout(video_mock)
        video_mock_layout.setContentsMargins(18, 18, 18, 18)

        mock_label = QLabel("LIVE • Камера 4 • Зона 4")
        mock_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #f5f8ff; margin-top: 12px;")
        video_mock_layout.addWidget(mock_label)
        video_mock_layout.addStretch()

        overlay = QLabel(
            "Каска: ДА | Жилет: ДА | ID: #104\n"
            "Каска: НЕТ | Жилет: ДА | ID: #089 | НАРУШЕНИЕ\n"
            "Площадка: West Gate / 18:44:21"
        )
        overlay.setStyleSheet(
            "background: rgba(10, 13, 17, 0.55); border: 1px solid #2e3740; border-radius: 10px; "
            "padding: 12px 14px; color: #e9edf6; font-size: 12px; line-height: 1.6;"
        )
        video_mock_layout.addWidget(overlay)

        left_panel_layout.addWidget(video_mock)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)
        for text, value, tone in [
            ("Корректно", "11", "#2ecc71"),
            ("Тревоги", "5", "#ff4d4d"),
            ("Проверки", "3", "#f1c40f"),
        ]:
            mini = QFrame()
            mini.setObjectName("card")
            mini.setMinimumHeight(90)
            mini_layout = QVBoxLayout(mini)
            mini_layout.setContentsMargins(14, 10, 14, 10)
            mini_value = QLabel(value)
            mini_value.setStyleSheet(f"font-size: 26px; font-weight: 700; color: {tone};")
            mini_label = QLabel(text)
            mini_label.setStyleSheet("font-size: 11px; color: #adb8c5;")
            mini_layout.addWidget(mini_value)
            mini_layout.addWidget(mini_label)
            bottom_row.addWidget(mini)
        left_panel_layout.addLayout(bottom_row)

        right_panel = QFrame()
        right_panel.setObjectName("card")
        right_panel.setMinimumWidth(360)
        right_panel.setMaximumWidth(360)
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setContentsMargins(14, 14, 14, 14)

        right_title = QLabel("Лента нарушений")
        right_title.setStyleSheet("font-size: 18px; font-weight: 700; margin-bottom: 6px;")
        right_panel_layout.addWidget(right_title)

        events = [
            ("11:34:19", "Без каски", "ID #089", "#FF4D4D"),
            ("11:47:10", "Без жилета", "ID #104", "#FF9F43"),
            ("11:52:06", "Опасная зона", "Камера 03", "#FF4D4D"),
            ("12:08:32", "Проверка PPE", "ID #201", "#F1C40F"),
        ]

        for time_value, kind, identity, color in events:
            event_card = QFrame()
            event_card.setStyleSheet(
                "QFrame { background: #11191f; border: 1px solid #232e39; border-radius: 12px; padding: 8px; }"
            )
            event_layout = QVBoxLayout(event_card)
            event_layout.setContentsMargins(12, 12, 12, 12)

            top = QLabel(f"{time_value}   {kind}")
            top.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {color};")
            bottom = QLabel(identity)
            bottom.setStyleSheet("font-size: 11px; color: #d7dfeb;")
            event_layout.addWidget(top)
            event_layout.addWidget(bottom)
            event_layout.addWidget(QLabel("🧍 cropshot • лицо / грудь"))
            right_panel_layout.addWidget(event_card)

        right_panel_layout.addStretch()
        main_grid.addWidget(left_panel, 3)
        main_grid.addWidget(right_panel, 1)
        content_layout.addLayout(main_grid)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(content, 1)
        self.setCentralWidget(root)
        self.clock_timer.start(1000)

    def show_main_menu(self):
        self.clear_window()
        self.build_dashboard()

    def show_live_page(self):
        self.clear_window()
        self.setCentralWidget(VideoPage(self))

    def show_video_page(self):
        self.show_live_page()

    def show_upload_page(self):
        self.clear_window()
        self.setCentralWidget(UploadVideoPage(self))

    def show_shift_page(self):
        self.clear_window()
        self.setCentralWidget(ShiftPage(self))
