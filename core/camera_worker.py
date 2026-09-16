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
        save_live_frames=True,
        save_dir=r"C:\Users\user\PycharmProjects\BIM_model\results\live_frames",
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

        # ----------------------------------------------------------
        # Управление сохранением
        # ----------------------------------------------------------

        self._save_live_frames = bool(save_live_frames)

        self.save_dir = save_dir

        if self._save_live_frames:
            self._ensure_save_dir()

    # ==============================================================
    # SAVE SETTINGS
    # ==============================================================

    def set_save_frames(self, enabled: bool):
        """
        Включить или выключить сохранение обработанных AI кадров.

        Можно вызывать в любой момент:

            worker.set_save_frames(True)

        или:

            worker.set_save_frames(False)
        """

        self._save_live_frames = bool(enabled)

        if self._save_live_frames:
            self._ensure_save_dir()

        print(
            f"[{self.camera_name}] "
            f"Сохранение кадров: "
            f"{'ВКЛ' if self._save_live_frames else 'ВЫКЛ'}"
        )

    def is_save_frames_enabled(self) -> bool:
        """
        Возвращает текущее состояние сохранения.
        """

        return self._save_live_frames

    # ==============================================================
    # SAVE DIRECTORY
    # ==============================================================

    def _ensure_save_dir(self):
        """
        Создаёт папку для сохранения.
        """

        try:

            os.makedirs(
                self.save_dir,
                exist_ok=True
            )

        except Exception as e:

            print(
                f"[{self.camera_name}] "
                f"Ошибка создания папки:\n"
                f"{self.save_dir}\n"
                f"{e}"
            )

    # ==============================================================
    # SAVE PROCESSED FRAME
    # ==============================================================

    def _save_processed_frame(
        self,
        frame
    ):
        """
        Сохраняет уже обработанный AI кадр.

        В этот метод должен приходить frame, на котором
        уже нарисованы bounding boxes / labels.
        """

        if not self._save_live_frames:
            return

        if frame is None:
            return

        try:

            self._ensure_save_dir()

            # ------------------------------------------------------
            # Делаем безопасное имя камеры
            # ------------------------------------------------------

            safe_camera_name = "".join(
                c
                if c.isalnum() or c in ("-", "_")
                else "_"
                for c in self.camera_name
            )

            # ------------------------------------------------------
            # Время с миллисекундами
            # ------------------------------------------------------

            timestamp = datetime.now().strftime(
                "%Y-%m-%d_%H-%M-%S-%f"
            )[:-3]

            # ------------------------------------------------------
            # Имя файла
            # ------------------------------------------------------

            filename = (
                f"{safe_camera_name}_"
                f"{timestamp}.jpg"
            )

            filepath = os.path.join(
                self.save_dir,
                filename
            )

            # ------------------------------------------------------
            # Сохраняем JPEG
            # ------------------------------------------------------

            success = cv2.imwrite(
                filepath,
                frame
            )

            if not success:

                print(
                    f"[{self.camera_name}] "
                    f"Не удалось сохранить:\n"
                    f"{filepath}"
                )

        except Exception as e:

            # Ошибка сохранения НЕ должна останавливать камеру

            print(
                f"[{self.camera_name}] "
                f"Ошибка сохранения кадра: {e}"
            )

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

                        # ==========================================
                        # СОХРАНЯЕМ ИМЕННО ОБРАБОТАННЫЙ КАДР
                        # ==========================================

                        self._save_processed_frame(
                            processed_frame
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

                        self.violation_found.emit(
                            self.camera_name,
                            detections
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