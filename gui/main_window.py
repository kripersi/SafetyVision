import json
import os
from datetime import datetime

from PySide6.QtCore import QDateTime, QTimer, QMutex
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
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

from config import (
    get_camera_sources,
    load_cameras,
    load_confidence_threshold,
    load_detect_interval,
    load_monitoring_rules,
    DISPLAY_CLASS_NAMES,
    VIOLATION_CLASS_NAMES,
    save_cameras,
    save_confidence_threshold,
    save_detect_interval,
    save_monitoring_rules,
)
from core.detector import PPEDetector
from gui.shift_page import ShiftPage
from gui.video_page import UploadVideoPage, VideoPage
from core.camera_worker import CameraWorker


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
        self.detector_lock = QMutex()
        self.json_path = os.path.join("results", "violations.json")
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
        self.shift_started_at = datetime.now()
        self.camera_statuses = {camera["name"]: "connecting" for camera in self.camera_sources}
        self.clock_label = None
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

        self.camera_workers = {}  # camera_name -> CameraWorker
        self.start_camera_workers()

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
        self.dashboard_stat_labels = {}
        self.dashboard_log_list = None
        self.camera_status_list = None
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
        return DISPLAY_CLASS_NAMES.get(class_name, class_name)

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

    def start_camera_workers(self):
        """Запускает по одному воркеру на камеру. Вызывается один раз при старте."""
        detect_interval = load_detect_interval()
        self.camera_statuses = {camera["name"]: "connecting" for camera in self.camera_sources}
        for camera in self.camera_sources:
            worker = CameraWorker(
                camera,
                self.detector,
                self.detector_lock,
                detect_interval=detect_interval,
            )
            worker.violation_found.connect(self.on_violation_found)
            worker.status_changed.connect(self.on_camera_status_changed)
            worker.start()
            self.camera_workers[camera["name"]] = worker

    def on_camera_status_changed(self, camera_name, status):
        self.camera_statuses[camera_name] = status
        if self.camera_status_list is None:
            return
        for index in range(self.camera_status_list.count()):
            item = self.camera_status_list.item(index)
            if item.data(256) != camera_name:
                continue
            label = "онлайн" if status == "connected" else "ошибка подключения"
            item.setText(f"{camera_name} • {label}")
            break
        self.refresh_dashboard_stats()

    def on_violation_found(self, camera_name, detections):
        """Заменяет старую логику из run_background_monitor —
        получает уже готовые detections от воркера и пишет в лог."""
        rules = self.get_active_monitoring_rules()
        today = datetime.now().strftime("%Y-%m-%d")
        now_text = datetime.now().strftime("%H:%M:%S")
        log_data = self.load_activity_log()

        events = []
        confidence_threshold = load_confidence_threshold()
        for detection in detections:
            class_name = detection.get("class_name", "")
            if class_name not in VIOLATION_CLASS_NAMES:
                continue
            confidence = float(detection.get("confidence", 0.0))
            if confidence < confidence_threshold:
                continue
            normalized = self.normalize_violation_name(class_name)
            key = class_name if isinstance(normalized, str) else class_name
            if not rules.get(key, True):
                continue
            if normalized in {"Person", "person"}:
                continue
            confidence_pct = int(confidence * 100)
            events.append((normalized, confidence_pct))

        if not events:
            return

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

        self.refresh_dashboard_stats()

    def closeEvent(self, event):
        for worker in self.camera_workers.values():
            worker.stop()
        super().closeEvent(event)

    def restart_camera_workers(self):
        for worker in self.camera_workers.values():
            worker.stop()
        self.camera_workers = {}
        self.start_camera_workers()

    def iter_violation_entries(self):
        violation_labels = set(VIOLATION_CLASS_NAMES.values()) | {"Без жилета"}
        logs = self.load_activity_log()
        for day, day_events in logs.items():
            if not isinstance(day_events, dict):
                continue
            for time_label, event in day_events.items():
                if not isinstance(event, str):
                    continue
                count = sum(event.count(label) for label in violation_labels)
                if count == 0:
                    continue
                try:
                    event_time = datetime.strptime(
                        f"{day} {time_label[:8]}", "%Y-%m-%d %H:%M:%S"
                    )
                except ValueError:
                    continue
                yield event_time, count

    def get_dashboard_summary(self):
        now = datetime.now()
        monthly = 0
        shift = 0
        for event_time, count in self.iter_violation_entries():
            if event_time.year == now.year and event_time.month == now.month:
                monthly += count
            if event_time >= self.shift_started_at:
                shift += count

        return {
            "monthly": monthly,
            "shift": shift,
            "cameras": sum(status == "connected" for status in self.camera_statuses.values()),
        }

    def refresh_dashboard_stats(self):
        if not hasattr(self, "dashboard_stat_labels") or not self.dashboard_stat_labels:
            return
        if self.dashboard_log_list is None:
            return

        summary = self.get_dashboard_summary()
        try:
            self.dashboard_stat_labels["monthly"].setText(str(summary["monthly"]))
            self.dashboard_stat_labels["shift"].setText(str(summary["shift"]))
            self.dashboard_stat_labels["cameras"].setText(str(summary["cameras"]))
        except RuntimeError:
            self.dashboard_stat_labels = {}
            return

        log_entries = []
        logs = self.load_activity_log()
        violation_labels = set(VIOLATION_CLASS_NAMES.values()) | {"Без жилета"}
        for day in sorted(logs.keys(), reverse=True):
            entries = logs.get(day, {})
            for time_label, event in sorted(entries.items(), reverse=True):
                if not isinstance(event, str) or not any(label in event for label in violation_labels):
                    continue
                log_entries.append(f"{day}  {time_label} — {event}")

        try:
            self.dashboard_log_list.clear()
        except RuntimeError:
            self.dashboard_log_list = None
            return

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
            ("Нарушений за месяц", "monthly", "#ff4d4d"),
            ("Нарушений за смену", "shift", "#ff9f43"),
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
            status = self.camera_statuses.get(camera["name"], "connecting")
            status_label = "онлайн" if status == "connected" else "ошибка подключения" if status == "error" else "подключение"
            item = QListWidgetItem(f"{camera['name']} • {status_label}")
            item.setData(256, camera["name"])
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
            ("Hardhat", "Каска"),
            ("Mask", "Маска"),
            ("NO-Hardhat", "Без каски"),
            ("NO-Mask", "Без маски"),
            ("NO-Safety Vest", "Без защитного жилета"),
            ("Person", "Человек"),
            ("Safety Cone", "Конус безопасности"),
            ("Safety Vest", "Защитный жилет"),
            ("machinery", "Машины и механизмы"),
            ("vehicle", "Транспорт"),
        ]
        rules = self.get_active_monitoring_rules()

        interval_group = QWidget()
        interval_layout = QHBoxLayout(interval_group)
        interval_layout.setContentsMargins(0, 0, 0, 0)
        interval_layout.setSpacing(10)
        interval_layout.addWidget(QLabel("Проверять нарушения каждые"))

        interval_spin = QDoubleSpinBox()
        interval_spin.setRange(0.1, 3600.0)
        interval_spin.setSingleStep(0.5)
        interval_spin.setDecimals(1)
        interval_spin.setSuffix(" сек.")
        interval_spin.setValue(load_detect_interval())
        interval_layout.addWidget(interval_spin)

        save_interval_button = QPushButton("Сохранить")
        save_interval_button.clicked.connect(
            lambda: self._save_detect_interval(interval_spin.value())
        )
        interval_layout.addWidget(save_interval_button)
        interval_layout.addStretch()
        layout.addWidget(interval_group)

        confidence_group = QWidget()
        confidence_layout = QHBoxLayout(confidence_group)
        confidence_layout.setContentsMargins(0, 0, 0, 0)
        confidence_layout.setSpacing(10)
        confidence_layout.addWidget(QLabel("Уведомлять при уверенности от"))

        confidence_spin = QDoubleSpinBox()
        confidence_spin.setRange(0.0, 100.0)
        confidence_spin.setSingleStep(5.0)
        confidence_spin.setDecimals(0)
        confidence_spin.setSuffix(" %")
        confidence_spin.setValue(load_confidence_threshold() * 100)
        confidence_layout.addWidget(confidence_spin)

        save_confidence_button = QPushButton("Сохранить")
        save_confidence_button.clicked.connect(
            lambda: self._save_confidence_threshold(confidence_spin.value())
        )
        confidence_layout.addWidget(save_confidence_button)
        confidence_layout.addStretch()
        layout.addWidget(confidence_group)

        toggle_group = QWidget()
        toggle_layout = QVBoxLayout(toggle_group)
        toggle_layout.setSpacing(10)
        toggle_layout.addWidget(QLabel("Следить за классами"))
        for key, label in options:
            checkbox = QCheckBox(label)
            checkbox.setChecked(bool(rules.get(key, True)))
            checkbox.stateChanged.connect(lambda state, key=key: self._save_monitoring_rule(key, state == 2))
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

    def _save_detect_interval(self, interval: float):
        save_detect_interval(interval)
        for worker in self.camera_workers.values():
            worker.set_detect_interval(interval)

    def _save_confidence_threshold(self, percentage: float):
        save_confidence_threshold(percentage / 100.0)

    def _add_camera_from_config(self, name: str, url: str):
        text_name = (name or "").strip()
        text_url = (url or "").strip()
        if not text_url:
            return

        cameras = load_cameras()
        cameras.append({"name": text_name or f"Камера {len(cameras) + 1}", "url": text_url})
        save_cameras(cameras)
        self.camera_sources = get_camera_sources()
        self.restart_camera_workers()
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
        self.restart_camera_workers()

    def _delete_camera(self, index: int):
        cameras = load_cameras()
        if index < 0 or index >= len(cameras):
            return
        del cameras[index]
        save_cameras(cameras)
        self.camera_sources = get_camera_sources()
        self.restart_camera_workers()
        self.show_settings_page()
