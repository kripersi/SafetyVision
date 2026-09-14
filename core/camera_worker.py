import time
import cv2
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker


class CameraWorker(QThread):
    """Один воркер = одно RTSP-подключение к одной камере.
    Живёт всё время работы приложения, не пересоздаётся при открытии вкладок."""

    frame_ready = Signal(str, object)      # camera_name, frame (np.ndarray BGR)
    violation_found = Signal(str, list)    # camera_name, detections (raw list из detector.detect)
    status_changed = Signal(str, str)      # camera_name, "connected"/"error"/...

    def __init__(self, camera, detector, detector_lock, detect_interval=5.0, parent=None):
        super().__init__(parent)
        self.camera_name = camera["name"]
        self.url = camera["url"]
        self.detector = detector           # ОБЩИЙ детектор, передаём снаружи, не создаём свой
        self.detector_lock = detector_lock # ОБЩИЙ мьютекс, чтобы 2 камеры не дёргали detect() одновременно
        self.detect_interval = detect_interval
        self._running = True

    def stop(self):
        self._running = False
        self.wait(3000)

    def run(self):
        cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            self.status_changed.emit(self.camera_name, "error")
            return

        self.status_changed.emit(self.camera_name, "connected")
        last_detect_time = 0.0

        while self._running:
            ok, frame = cap.read()
            if not ok or frame is None:
                self.msleep(200)
                continue

            # 1. Отдаём кадр для показа (если кто-то подписан — VideoPage)
            self.frame_ready.emit(self.camera_name, frame)

            # 2. Раз в detect_interval секунд гоняем YOLO — ОДИН раз, а не два потока
            now = time.time()
            if now - last_detect_time >= self.detect_interval:
                last_detect_time = now
                try:
                    with QMutexLocker(self.detector_lock):
                        detections = self.detector.detect(frame)
                except Exception:
                    detections = []
                if detections:
                    self.violation_found.emit(self.camera_name, detections)

            self.msleep(30)  # не душим CPU чтением на пределе

        cap.release()