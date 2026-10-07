import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

from config import DISPLAY_CLASS_NAMES

VIOLATION_CLASSES = {"NO-Hardhat", "NO-Mask", "NO-Safety Vest"}

COLOR_VIOLATION = (0, 0, 255)   # BGR, красный
COLOR_OK = (0, 200, 0)          # BGR, зелёный

_FONT_CANDIDATES = [
    "arial.ttf",
    "segoeui.ttf",
    "DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]


def _load_font(size=18):
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


class PPEDetector:

    def __init__(self, model_path, imgsz=640, conf=0.25):
        print("Загрузка модели...")
        self.model = YOLO(model_path)
        self.imgsz = imgsz
        self.conf = conf
        self._font = _load_font(18)
        self._label_cache = {}

        print("Модель загружена!\n")
        print("Классы модели:")
        for class_id, class_name in self.model.names.items():
            print(f"{class_id}: {class_name}")

    @staticmethod
    def is_violation(class_name):
        return class_name in VIOLATION_CLASSES

    def detect(self, frame):
        results = self.model(
            frame,
            imgsz=self.imgsz,
            conf=self.conf,
            verbose=False,
        )

        detections = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                class_id = int(box.cls[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                detections.append({
                    "class_id": class_id,
                    "class_name": self.model.names[class_id],
                    "confidence": float(box.conf[0]),
                    "bbox": [x1, y1, x2, y2],
                })
        return detections

    # ----------------------------------------------------------
    # Подпись с поддержкой кириллицы (cv2.putText её не умеет).
    # Рендерим только маленький прямоугольник и кэшируем.
    # ----------------------------------------------------------
    def _label_image(self, text, color_bgr):
        key = (text, color_bgr)
        cached = self._label_cache.get(key)
        if cached is not None:
            return cached

        left, top, right, bottom = self._font.getbbox(text)
        w, h = right - left + 10, bottom - top + 8
        rgb = (color_bgr[2], color_bgr[1], color_bgr[0])

        img = Image.new("RGB", (w, h), rgb)
        ImageDraw.Draw(img).text((5, 3 - top), text, font=self._font, fill=(255, 255, 255))
        arr = np.array(img)[:, :, ::-1].copy()  # RGB -> BGR

        if len(self._label_cache) > 200:
            self._label_cache.clear()
        self._label_cache[key] = arr
        return arr

    def draw_detections(self, frame, detections, copy=True):
        """
        Красный бокс — нарушение (NO-Hardhat / NO-Mask / NO-Safety Vest),
        зелёный — всё остальное.
        copy=False — рисовать прямо на frame (быстрее).
        """
        out = frame.copy() if copy else frame
        fh, fw = out.shape[:2]

        # Нарушения рисуем последними, чтобы были поверх
        ordered = sorted(
            detections,
            key=lambda d: d["class_name"] in VIOLATION_CLASSES,
        )

        for det in ordered:
            class_name = det["class_name"]
            x1, y1, x2, y2 = det["bbox"]
            violation = class_name in VIOLATION_CLASSES
            color = COLOR_VIOLATION if violation else COLOR_OK

            cv2.rectangle(out, (x1, y1), (x2, y2), color, 3 if violation else 2)

            text = f"{DISPLAY_CLASS_NAMES.get(class_name, class_name)} {det['confidence']:.2f}"
            label = self._label_image(text, color)
            lh, lw = label.shape[:2]

            ly = y1 - lh
            if ly < 0:
                ly = y1  # не помещается сверху — кладём внутрь бокса
            lx = max(0, min(x1, fw - lw))
            ly = max(0, min(ly, fh - lh))

            out[ly:ly + lh, lx:lx + lw] = label[: fh - ly, : fw - lx][: lh, : lw]

        return out