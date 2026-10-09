import os
import threading
import time
from datetime import datetime

# Низкая задержка RTSP. Нужно задать ДО создания VideoCapture.
os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS",
    "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay",
)

import cv2
from PySide6.QtCore import QThread, Signal, QMutexLocker

from config import (
    DISPLAY_CLASS_NAMES,
    LOCAL_CAMERA_INDEX,
)
from core.monitoring import (
    filter_detections_for_display,
    is_monitoring_rule_enabled,
    should_run_detection,
)
from core.settings_store import (
    get_opencv_camera_source,
    load_confidence_threshold,
    load_display_confidence_threshold,
    load_monitoring_rules,
)
from core.telegram import send_telegram_message
from core.violation_tracker import ViolationTracker

VIOLATION_CLASSES = {"NO-Hardhat", "NO-Mask", "NO-Safety Vest"}

MAX_UI_FPS = 30
TELEGRAM_COOLDOWN = 30.0     # сек. между сообщениями об одном нарушении на одной камере
RECONNECT_AFTER_FAILS = 25   # ~5 сек без кадров -> переподключение


class CameraWorker(QThread):
    """
    Два потока на камеру:

    1. run()          — читает RTSP и отдаёт в GUI КАЖДЫЙ кадр
                        (с нарисованными последними детекциями).
    2. _infer_loop()  — отдельный поток, гоняет AI по последнему кадру
                        и обновляет список детекций.

    Чтение никогда не ждёт AI, поэтому видео не лагает.
    """

    frame_ready = Signal(str, object)
    violation_found = Signal(str, list)
    status_changed = Signal(str, str)

    def __init__(self, camera, detector, detector_lock, detect_interval=5.0, parent=None):
        super().__init__(parent)

        self.camera_name = camera["name"]
        self.url = camera["url"]
        self.detector = detector
        self.detector_lock = detector_lock
        self.detect_interval = detect_interval

        self._running = True

        # Общее состояние между потоками
        self._state_lock = threading.Lock()
        self._latest_frame = None      # оригинальный кадр (его никто не рисует поверх)
        self._latest_frame_id = 0
        self._detections = []          # последние детекции
        self._detections_time = 0.0

        self._tracker = ViolationTracker()

    # ==========================================================

    def set_detect_interval(self, interval):
        self.detect_interval = max(0.0, float(interval))

    def stop(self):
        self._running = False
        self.wait(5000)

    # ==========================================================

    def _hold_time(self):
        """Сколько секунд держать старые рамки, если AI не обновил результат."""
        return max(1.5, self.detect_interval * 1.5 + 1.0)

    def _open_capture(self):
        source = get_opencv_camera_source(self.url)
        backend = cv2.CAP_FFMPEG if source != LOCAL_CAMERA_INDEX else cv2.CAP_ANY
        cap = cv2.VideoCapture(source, backend)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    # ==========================================================
    # ПОТОК ЧТЕНИЯ + ОТОБРАЖЕНИЯ
    # ==========================================================

    def run(self):
        cap = None
        infer_thread = None

        try:
            cap = self._open_capture()
            if not cap.isOpened():
                self.status_changed.emit(self.camera_name, "error")
                return

            self.status_changed.emit(self.camera_name, "connected")

            infer_thread = threading.Thread(
                target=self._infer_loop,
                name=f"infer-{self.camera_name}",
                daemon=True,
            )
            infer_thread.start()

            fails = 0
            last_emit = 0.0
            min_emit_dt = 1.0 / MAX_UI_FPS

            while self._running:
                ok, frame = cap.read()

                if not ok or frame is None:
                    fails += 1
                    if fails >= RECONNECT_AFTER_FAILS:
                        self.status_changed.emit(self.camera_name, "error")
                        cap.release()
                        self.msleep(1000)
                        cap = self._open_capture()
                        if cap.isOpened():
                            self.status_changed.emit(self.camera_name, "connected")
                            fails = 0
                    else:
                        self.msleep(200)
                    continue

                fails = 0

                # Отдаём последний кадр AI-потоку (ссылка, без копии;
                # сами мы этот массив больше не меняем).
                with self._state_lock:
                    self._latest_frame = frame
                    self._latest_frame_id += 1
                    detections = list(self._detections)
                    det_age = time.time() - self._detections_time

                # Не заваливаем GUI лишними кадрами
                now = time.time()
                if now - last_emit < min_emit_dt:
                    continue
                last_emit = now

                # Рисуем только разрешённые классами и уверенные детекции.
                # Старые детекции остаются на кадре до истечения времени их хранения.
                if detections and det_age <= self._hold_time():
                    display_detections = filter_detections_for_display(
                        detections,
                        rules=load_monitoring_rules(),
                        confidence_threshold=load_display_confidence_threshold(),
                    )
                    out = self.detector.draw_detections(frame, display_detections, copy=True)
                else:
                    out = frame

                self.frame_ready.emit(self.camera_name, out)

        except Exception as e:
            print(f"[{self.camera_name}] Ошибка CameraWorker: {e}")
            self.status_changed.emit(self.camera_name, "error")

        finally:
            self._running = False
            if infer_thread is not None:
                infer_thread.join(timeout=3)
            if cap is not None:
                cap.release()
            self.status_changed.emit(self.camera_name, "stopped")

    # ==========================================================
    # ПОТОК AI
    # ==========================================================

    def _infer_loop(self):
        last_detect_time = 0.0
        last_frame_id = -1

        while self._running:
            with self._state_lock:
                frame = self._latest_frame
                frame_id = self._latest_frame_id

            now = time.time()

            if (
                frame is None
                or frame_id == last_frame_id
                or not should_run_detection(now, last_detect_time, self.detect_interval)
            ):
                time.sleep(0.01)
                continue

            last_detect_time = now
            last_frame_id = frame_id

            try:
                with QMutexLocker(self.detector_lock):
                    detections = self.detector.detect(frame)
            except Exception as e:
                print(f"[{self.camera_name}] Ошибка AI: {e}")
                time.sleep(0.5)
                continue

            with self._state_lock:
                self._detections = detections
                self._detections_time = time.time()

            self._handle_violations(detections)

    # ==========================================================

    def _handle_violations(self, detections):
        threshold = load_confidence_threshold()

        violations = [
            det for det in detections
            if isinstance(det.get("class_name"), str)
               and det["class_name"] in VIOLATION_CLASSES
               and det.get("confidence", 0.0) >= threshold
               and is_monitoring_rule_enabled(det["class_name"])
        ]

        # ВАЖНО: вызываем и с пустым списком, иначе трекер не поймёт,
        # что нарушение закончилось.
        clear_after = max(5.0, self.detect_interval * 2 + 2.0)
        events = self._tracker.update(violations, time.time(), clear_after)

        if not events:
            return

        for ev in events:
            name = DISPLAY_CLASS_NAMES.get(ev["class_name"], ev["class_name"])
            people = f" ×{ev['count']}" if ev["count"] > 1 else ""
            suffix = " (продолжается)" if ev["repeat"] else ""
            message = (
                f"{datetime.now().strftime('%H:%M:%S')} | {self.camera_name} | "
                f"{name}{people} | {ev['confidence'] * 100:.0f}%{suffix}"
            )
            threading.Thread(
                target=send_telegram_message,
                args=(message,),
                daemon=True,
            ).start()

        self.violation_found.emit(self.camera_name, events)