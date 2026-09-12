from ultralytics import YOLO


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
