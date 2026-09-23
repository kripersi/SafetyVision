import os
import time
from datetime import datetime

import cv2

from PySide6.QtCore import (
    QThread,
    Signal,
    QMutex,
    QMutexLocker
)

from config import DISPLAY_CLASS_NAMES, is_monitoring_rule_enabled, send_telegram_message


class CameraWorker(QThread):
    """
    Один воркер = одно RTSP-подключение к одной камере.

    Возможности:

    1. Постоянно получает кадры с RTSP.
    2. Передаёт кадры для отображения.
    3. Раз в detect_interval секунд запускает AI.
    4. Получает detections от AI.
    5. Рисует bounding boxes и подписи.
    6. Сохраняет обработанный кадр.
    7. Сохранение можно включать/выключать во время работы.
    """

    # camera_name, frame
    frame_ready = Signal(str, object)

    # camera_name, detections
    violation_found = Signal(str, list)

    # camera_name, status
    status_changed = Signal(str, str)

    def __init__(
        self,
        camera,
        detector,
        detector_lock,
        detect_interval=5.0,
        parent=None
    ):
        super().__init__(parent)

        # ----------------------------------------------------------
        # Камера
        # ----------------------------------------------------------

        self.camera_name = camera["name"]
        self.url = camera["url"]

        # ----------------------------------------------------------
        # Общий AI detector
        # ----------------------------------------------------------

        self.detector = detector

        # ----------------------------------------------------------
        # Общий mutex.
        #
        # Нужен, если несколько камер используют одну модель.
        # ----------------------------------------------------------

        self.detector_lock = detector_lock

        # ----------------------------------------------------------
        # Интервал AI-проверки
        # ----------------------------------------------------------

        self.detect_interval = detect_interval

        # ----------------------------------------------------------
        # Управление потоком
        # ----------------------------------------------------------

        self._running = True

    # ==============================================================
    # DETECTION INTERVAL
    # ==============================================================

    def set_detect_interval(self, interval):
        """Изменить период AI-проверки без перезапуска камеры."""
        self.detect_interval = max(0.1, float(interval))

    # ==============================================================
    # STOP
    # ==============================================================

    def stop(self):
        """
        Остановить поток камеры.
        """

        self._running = False

        self.wait(3000)

    # ==============================================================
    # MAIN THREAD
    # ==============================================================

    def run(self):

        cap = None

        try:

            # ------------------------------------------------------
            # Открываем RTSP
            # ------------------------------------------------------

            cap = cv2.VideoCapture(
                self.url,
                cv2.CAP_FFMPEG
            )

            cap.set(
                cv2.CAP_PROP_BUFFERSIZE,
                1
            )

            # ------------------------------------------------------
            # Проверяем подключение
            # ------------------------------------------------------

            if not cap.isOpened():

                self.status_changed.emit(
                    self.camera_name,
                    "error"
                )

                return

            # ------------------------------------------------------
            # Камера подключена
            # ------------------------------------------------------

            self.status_changed.emit(
                self.camera_name,
                "connected"
            )

            # ------------------------------------------------------
            # Время последнего AI запуска
            # ------------------------------------------------------

            last_detect_time = 0.0

            # ======================================================
            # MAIN LOOP
            # ======================================================

            while self._running:

                # --------------------------------------------------
                # Читаем кадр
                # --------------------------------------------------

                ok, frame = cap.read()

                if not ok or frame is None:

                    self.msleep(200)

                    continue

                # --------------------------------------------------
                # Отдаём оригинальный кадр интерфейсу.
                #
                # Здесь он БЕЗ AI-разметки.
                # --------------------------------------------------

                self.frame_ready.emit(
                    self.camera_name,
                    frame
                )

                # --------------------------------------------------
                # Проверяем интервал AI
                # --------------------------------------------------

                now = time.time()

                if (
                    now - last_detect_time
                    >= self.detect_interval
                ):

                    last_detect_time = now

                    detections = []

                    try:

                        # ==========================================
                        # AI
                        # ==========================================

                        with QMutexLocker(
                            self.detector_lock
                        ):

                            detections = self.detector.detect(
                                frame
                            )

                        # ==========================================
                        # РИСУЕМ AI РЕЗУЛЬТАТ
                        # ==========================================

                        processed_frame = (
                            self.detector.draw_detections(
                                frame,
                                detections
                            )
                        )

                    except Exception as e:

                        print(
                            f"[{self.camera_name}] "
                            f"Ошибка AI: {e}"
                        )

                    # --------------------------------------------------
                    # Передаём найденные нарушения
                    # --------------------------------------------------

                    if detections:
                        filtered_detections = []
                        for detection in detections:
                            class_name = detection.get("class_name")
                            if not isinstance(class_name, str):
                                continue
                            if not is_monitoring_rule_enabled(class_name):
                                continue
                            if class_name not in {"NO-Hardhat", "NO-Mask", "NO-Safety Vest"}:
                                continue
                            confidence = float(detection.get("confidence", 0.0))
                            violation_name = DISPLAY_CLASS_NAMES.get(class_name, class_name)
                            message = (
                                f"{datetime.now().strftime('%H:%M:%S')} | "
                                f"{violation_name} | {confidence * 100:.0f}%"
                            )
                            send_telegram_message(message)
                            filtered_detections.append(detection)

                        if filtered_detections:
                            self.violation_found.emit(
                                self.camera_name,
                                filtered_detections
                            )

                # --------------------------------------------------
                # Небольшая задержка
                # --------------------------------------------------

                self.msleep(30)

        except Exception as e:

            print(
                f"[{self.camera_name}] "
                f"Ошибка CameraWorker: {e}"
            )

            self.status_changed.emit(
                self.camera_name,
                "error"
            )

        finally:

            # ------------------------------------------------------
            # Освобождаем RTSP
            # ------------------------------------------------------

            if cap is not None:
                cap.release()

            self.status_changed.emit(
                self.camera_name,
                "stopped"
            )