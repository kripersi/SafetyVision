import json
import os
from datetime import datetime

import cv2
from PySide6.QtCore import QDateTime, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import get_camera_sources, load_cameras, load_monitoring_rules, save_cameras, save_monitoring_rules
from core.detector import PPEDetector
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
        self.camera_sources = get_camera_sources()
        self.detector = PPEDetector("models/ppe_model.pt")
        self.json_path = os.path.join("results", "violations.json")
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
        self.clock_label = None
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.run_background_monitor)
        self.monitor_timer.start(15000)
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.run_background_monitor()
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

    def normalize_violation_name(self, class_name):
        mapping = {
            "Hardhat": "Hardhat",
            "Mask": "Mask",
            "NO-Hardhat": "Без каски",
            "NO-Mask": "Без маски",
            "NO-Safety Vest": "Без жилета",
            "Safety Cone": "Safety Cone",
            "Safety Vest": "Safety Vest",
            "Vehicle": "Vehicle",
            "vehicle": "Vehicle",
            "machinery": "machinery",
            "person": "Person",
        }
        return mapping.get(class_name, class_name)

    def get_active_monitoring_rules(self):
        return load_monitoring_rules()

    def load_activity_log(self):
        if not os.path.exists(self.json_path):
            return {}

        try:
            with open(self.json_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def save_activity_log(self, data):
        try:
            with open(self.json_path, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def run_background_monitor(self):
        if not self.camera_sources:
            return

        rules = self.get_active_monitoring_rules()
        today = datetime.now().strftime("%Y-%m-%d")
        now_text = datetime.now().strftime("%H:%M:%S")
        log_data = self.load_activity_log()

        for camera in self.camera_sources:
            camera_name = camera["name"]
            url = camera["url"]
            try:
                cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                if not cap.isOpened():
                    continue
                ret, frame = cap.read()
                cap.release()
                if not ret or frame is None:
                    continue

                detections = self.detector.detect(frame)
                events = []
                for detection in detections:
                    class_name = detection.get("class_name", "")
                    normalized = self.normalize_violation_name(class_name)
                    key = class_name
                    if isinstance(normalized, str):
                        key = normalized
                    if not rules.get(key, True):
                        continue
                    if normalized in {"Person", "person"}:
                        continue
                    confidence_pct = int(float(detection.get("confidence", 0.0)) * 100)
                    events.append((normalized, confidence_pct))

                if not events:
                    continue

                unique_events = []
                seen = set()
                for label, confidence in events:
                    label_key = str(label)
                    if label_key not in seen:
                        seen.add(label_key)
                        unique_events.append(f"{label} • {confidence}%")

                today_events = log_data.setdefault(today, {})
                today_events[f"{now_text} ({camera_name})"] = f"{camera_name}: {', '.join(unique_events)}"
                self.save_activity_log(log_data)
            except Exception:
                continue

        self.refresh_dashboard_stats()

    def get_dashboard_summary(self):
        logs = self.load_activity_log()
        total = 0
        hardhat = 0
        mask = 0
        vest = 0
        vehicle = 0

        for day_events in logs.values():
            if not isinstance(day_events, dict):
                continue
            for event in day_events.values():
                if not isinstance(event, str):
                    continue
                text = event.lower()
                if not text:
                    continue
                total += 1
                if "без каски" in text:
                    hardhat += 1
                if "без маски" in text:
                    mask += 1
                if "без жилета" in text:
                    vest += 1
                if "vehicle" in text:
                    vehicle += 1

        return {
            "total": total,
            "hardhat": hardhat,
            "mask": mask,
            "vest": vest,
            "vehicle": vehicle,
            "cameras": len(self.camera_sources),
        }

    def refresh_dashboard_stats(self):
        if not hasattr(self, "dashboard_stat_labels"):
            return

        summary = self.get_dashboard_summary()
        self.dashboard_stat_labels["total"].setText(str(summary["total"]))
        self.dashboard_stat_labels["hardhat"].setText(str(summary["hardhat"]))
        self.dashboard_stat_labels["vehicle"].setText(str(summary["vehicle"]))
        self.dashboard_stat_labels["cameras"].setText(str(summary["cameras"]))

        log_entries = []
        logs = self.load_activity_log()
        for day in sorted(logs.keys(), reverse=True):
            entries = logs.get(day, {})
            for time_label, event in sorted(entries.items(), reverse=True):
                log_entries.append(f"{day}  {time_label} — {event}")

        self.dashboard_log_list.clear()

        if not log_entries:
            item = QListWidgetItem("Пока нарушений нет. Фоновый мониторинг работает в фоне.")
            self.dashboard_log_list.addItem(item)
            return

        for entry in log_entries[:80]:
            self.dashboard_log_list.addItem(entry)

    def build_dashboard(self):
        root = QWidget()
        root.setObjectName("main_dashboard")
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

        settings = self.make_nav_button("⚙️ Настройки", self.show_settings_page, False)
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

        status = QLabel("● Система активна / ИИ анализирует все камеры")
        status.setStyleSheet("color: #2ecc71; font-weight: 600; font-size: 13px;")
        topbar_layout.addWidget(status)

        object_box = QPushButton(f"Фон. мониторинг • {len(self.camera_sources)} камер")
        object_box.setObjectName("smallAction")
        topbar_layout.addStretch()
        topbar_layout.addWidget(object_box)

        self.clock_label = QLabel()
        self.clock_label.setObjectName("clockLabel")
        self.clock_label.setStyleSheet("color: #dfe7f3; font-weight: 600; font-size: 13px;")
        self.update_clock()
        topbar_layout.addWidget(self.clock_label)

        content_layout.addWidget(topbar)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)
        stat_cards = [
            ("Всего нарушений", "total", "#ff4d4d"),
            ("Без каски", "hardhat", "#ff9f43"),
            ("Vehicle", "vehicle", "#f1c40f"),
            ("Активных камер", "cameras", "#2ecc71"),
        ]
        self.dashboard_stat_labels = {}

        for title, key, color in stat_cards:
            card = QFrame()
            card.setObjectName("card")
            card.setMinimumHeight(108)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            label_value = QLabel("0")
            label_value.setStyleSheet(f"font-size: 32px; font-weight: 700; color: {color};")
            label_title = QLabel(title)
            label_title.setStyleSheet("font-size: 12px; color: #96a3b7;")
            card_layout.addWidget(label_value)
            card_layout.addWidget(label_title)
            self.dashboard_stat_labels[key] = label_value
            stats_row.addWidget(card)
        content_layout.addLayout(stats_row)

        main_grid = QHBoxLayout()
        main_grid.setSpacing(18)

        left_panel = QFrame()
        left_panel.setObjectName("card")
        left_panel.setMinimumHeight(500)
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel_layout.setContentsMargins(18, 18, 18, 18)

        left_title = QLabel("Состояние камер")
        left_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #f4f7fb;")
        left_panel_layout.addWidget(left_title)

        self.camera_status_list = QListWidget()
        self.camera_status_list.setMinimumHeight(180)
        for camera in self.camera_sources:
            item = QListWidgetItem(f"{camera['name']} • онлайн • {camera['url']}")
            self.camera_status_list.addItem(item)
        left_panel_layout.addWidget(self.camera_status_list)

        left_panel_layout.addSpacing(12)

        left_subtitle = QLabel("Лента событий")
        left_subtitle.setStyleSheet("font-size: 14px; font-weight: 700; color: #f4f7fb;")
        left_panel_layout.addWidget(left_subtitle)

        self.dashboard_log_list = QListWidget()
        self.dashboard_log_list.setMinimumHeight(280)
        left_panel_layout.addWidget(self.dashboard_log_list)

        main_grid.addWidget(left_panel, 1)
        content_layout.addLayout(main_grid)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(content, 1)
        self.setCentralWidget(root)
        self.clock_timer.start(1000)
        self.refresh_dashboard_stats()

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

    def show_settings_page(self):
        self.clear_window()
        self.setCentralWidget(self.build_settings_page())

    def show_shift_page(self):
        self.clear_window()
        self.setCentralWidget(ShiftPage(self))

    def build_settings_page(self):
        page = QWidget()
        page.setStyleSheet(
            "QWidget { background: #0f1115; color: #edf2f7; } "
            "QLabel { color: #edf2f7; } "
            "QPushButton { border: 1px solid #2b3038; border-radius: 10px; background: #1a1e25; color: #edf2f7; padding: 8px 12px; } "
            "QLineEdit { background: #12181d; border: 1px solid #2a3039; border-radius: 8px; color: #edf2f7; padding: 8px 10px; }"
        )
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)

        header_row = QHBoxLayout()
        title = QLabel("Настройки мониторинга")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        header_row.addWidget(title)
        header_row.addStretch()

        back_button = QPushButton("← Назад")
        back_button.clicked.connect(self.show_main_menu)
        header_row.addWidget(back_button)
        layout.addLayout(header_row)

        options = [
            "Hardhat",
            "Mask",
            "NO-Hardhat",
            "NO-Mask",
            "NO-Safety Vest",
            "Person",
            "Safety Cone",
            "Safety Vest",
            "machinery",
            "vehicle",
        ]
        rules = self.get_active_monitoring_rules()

        toggle_group = QWidget()
        toggle_layout = QVBoxLayout(toggle_group)
        toggle_layout.setSpacing(10)
        toggle_layout.addWidget(QLabel("Следить за классами"))
        for name in options:
            checkbox = QCheckBox(name)
            checkbox.setChecked(bool(rules.get(name, True)))
            checkbox.stateChanged.connect(lambda state, key=name: self._save_monitoring_rule(key, state == 2))
            toggle_layout.addWidget(checkbox)
        layout.addWidget(toggle_group)

        cameras_widget = QWidget()
        cameras_layout = QVBoxLayout(cameras_widget)
        cameras_layout.setSpacing(12)
        cameras_layout.addWidget(QLabel("Камеры"))

        current_cameras = load_cameras()
        for index, camera in enumerate(current_cameras):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)

            name_edit = QLineEdit(camera.get("name", f"Камера {index + 1}"))
            url_edit = QLineEdit(camera.get("url", ""))
            name_edit.setPlaceholderText("Имя камеры")
            url_edit.setPlaceholderText("rtsp://...")

            save_button = QPushButton("Сохранить")
            save_button.clicked.connect(
                lambda _, i=index, n=name_edit, u=url_edit: self._update_camera(i, n.text(), u.text())
            )

            delete_button = QPushButton("Удалить")
            delete_button.clicked.connect(
                lambda _, i=index: self._delete_camera(i)
            )

            row_layout.addWidget(name_edit, 2)
            row_layout.addWidget(url_edit, 5)
            row_layout.addWidget(save_button)
            row_layout.addWidget(delete_button)
            cameras_layout.addWidget(row)

        new_camera_row = QWidget()
        new_row_layout = QHBoxLayout(new_camera_row)
        new_row_layout.setContentsMargins(0, 0, 0, 0)
        new_row_layout.setSpacing(10)

        new_name = QLineEdit()
        new_url = QLineEdit()
        new_name.setPlaceholderText("Имя новой камеры")
        new_url.setPlaceholderText("rtsp://admin:.../channel/101")

        add_button = QPushButton("Добавить камеру")
        add_button.clicked.connect(
            lambda: self._add_camera_from_config(new_name.text(), new_url.text())
        )

        new_row_layout.addWidget(new_name, 2)
        new_row_layout.addWidget(new_url, 5)
        new_row_layout.addWidget(add_button)
        cameras_layout.addWidget(new_camera_row)

        layout.addWidget(cameras_widget)
        return page

    def _save_monitoring_rule(self, key, value):
        rules = self.get_active_monitoring_rules()
        rules[key] = value
        save_monitoring_rules(rules)

    def _add_camera_from_config(self, name: str, url: str):
        text_name = (name or "").strip()
        text_url = (url or "").strip()
        if not text_url:
            return

        cameras = load_cameras()
        cameras.append({"name": text_name or f"Камера {len(cameras) + 1}", "url": text_url})
        save_cameras(cameras)
        self.camera_sources = get_camera_sources()
        self.show_settings_page()

    def _update_camera(self, index: int, name: str, url: str):
        cameras = load_cameras()
        if index < 0 or index >= len(cameras):
            return
        text_name = (name or "").strip()
        text_url = (url or "").strip()
        if not text_url:
            return
        cameras[index] = {"name": text_name or f"Камера {index + 1}", "url": text_url}
        save_cameras(cameras)
        self.camera_sources = get_camera_sources()

    def _delete_camera(self, index: int):
        cameras = load_cameras()
        if index < 0 or index >= len(cameras):
            return
        del cameras[index]
        save_cameras(cameras)
        self.camera_sources = get_camera_sources()
        self.show_settings_page()
