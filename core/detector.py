from ultralytics import YOLO
import cv2


class PPEDetector:

    def __init__(self, model_path):
        print("Загрузка модели...")

        self.model = YOLO(model_path)

        print("Модель загружена!\n")
        print("Классы модели:")

        for class_id, class_name in self.model.names.items():
            print(f"{class_id}: {class_name}")

    def detect(self, frame):

        results = self.model(
            frame,
            verbose=False
        )

        detections = []

        for result in results:

            if result.boxes is None:
                continue

            for box in result.boxes:

                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                class_name = self.model.names[class_id]

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0].tolist()
                )

                detections.append({
                    "class_id": class_id,
                    "class_name": class_name,
                    "confidence": confidence,
                    "bbox": [x1, y1, x2, y2]
                })

        return detections

    def draw_detections(self, frame, detections):
        """
        Рисует результаты AI на кадре.

        Возвращает НОВУЮ копию кадра.
        Исходный frame не изменяется.
        """

        result_frame = frame.copy()

        for detection in detections:

            class_name = detection["class_name"]
            confidence = detection["confidence"]

            x1, y1, x2, y2 = detection["bbox"]

            # ------------------------------------------------------
            # Bounding box
            # ------------------------------------------------------

            cv2.rectangle(
                result_frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            # ------------------------------------------------------
            # Текст
            # ------------------------------------------------------

            label = f"{class_name} {confidence:.2f}"

            # Размер текста
            (text_width, text_height), baseline = cv2.getTextSize(
                label,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                2
            )

            # Фон под текст
            cv2.rectangle(
                result_frame,
                (x1, y1 - text_height - baseline - 5),
                (x1 + text_width + 5, y1),
                (0, 255, 0),
                -1
            )

            # Сам текст
            cv2.putText(
                result_frame,
                label,
                (x1 + 2, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2,
                cv2.LINE_AA
            )

        return result_frame