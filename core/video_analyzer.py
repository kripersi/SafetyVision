import cv2
import json
import os

from core.utils import format_time


class VideoAnalyzer:

    def __init__(self, detector):

        self.detector = detector

        self.violation_classes = {
            "NO-Hardhat": "Отсутствие каски",
            "NO-Mask": "Отсутствие маски",
            "NO-Safety Vest": "Отсутствие жилета"
        }

        # Проверять видео каждые X секунд
        self.check_interval = 5

    def analyze(self, video_path, output_path, json_path, progress_callback=None):

        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise RuntimeError("Не удалось открыть видео")

        fps = cap.get(cv2.CAP_PROP_FPS)

        if fps <= 0:
            fps = 25

        total_frames = int(
            cap.get(cv2.CAP_PROP_FRAME_COUNT)
        )

        duration = total_frames / fps

        width = int(
            cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        )

        height = int(
            cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        )

        print(
            f"Видео: {width}x{height}, "
            f"FPS {fps:.2f}, "
            f"{total_frames} кадров, "
            f"{duration:.2f} сек\n"
        )

        print(
            f"Проверка каждые {self.check_interval} секунд\n"
        )

        # Видео для результата
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        out = cv2.VideoWriter(
            output_path,
            fourcc,
            fps,
            (width, height)
        )

        violations = []

        # Следующий момент времени, когда нужно проверить кадр
        next_check_time = 0

        frame_number = 0

        while True:

            ret, frame = cap.read()

            if not ret:
                break

            current_time = frame_number / fps

            # По умолчанию просто показываем кадр
            annotated_frame = frame.copy()

            # Проверяем только каждые X секунд
            if current_time >= next_check_time:

                detections = self.detector.detect(frame)

                # Оставляем только нарушения
                detected_violations = []

                for detection in detections:

                    class_name = detection["class_name"]

                    if class_name not in self.violation_classes:
                        continue

                    violation_name = self.violation_classes[class_name]

                    confidence = detection["confidence"]

                    detected_violations.append({
                        "type": violation_name,
                        "confidence": confidence,
                        "bbox": detection["bbox"]
                    })

                # Если нашли нарушения
                if detected_violations:

                    # Группируем по типу нарушения
                    grouped = {}

                    for violation in detected_violations:

                        violation_type = violation["type"]

                        if violation_type not in grouped:
                            grouped[violation_type] = []

                        grouped[violation_type].append(
                            violation["confidence"]
                        )

                    # Все типы нарушений
                    violation_types = list(grouped.keys())

                    # Средний confidence
                    all_confidences = []

                    for violation in detected_violations:
                        all_confidences.append(
                            violation["confidence"]
                        )

                    average_confidence = (
                            sum(all_confidences)
                            / len(all_confidences)
                    )

                    # Общее количество нарушений
                    violation_count = len(
                        detected_violations
                    )

                    time_formatted = format_time(
                        current_time
                    )

                    types_text = ", ".join(
                        violation_types
                    )

                    print(
                        f"НАРУШЕНИЕ: {time_formatted} | "
                        f"{types_text} | "
                        f"средний процент "
                        f"{average_confidence * 100:.1f}% | "
                        f"нарушений: {violation_count} \n"
                    )


                    # Сохраняем событие
                    violations.append({
                        "time": round(current_time, 2),
                        "time_formatted": time_formatted,
                        "types": violation_types,
                        "average_confidence": round(
                            average_confidence,
                            4
                        ),
                        "violation_count": violation_count
                    })

                    # Рисуем найденные нарушения
                    for violation in detected_violations:
                        x1, y1, x2, y2 = violation["bbox"]

                        label = (
                            f"{violation['type']} "
                            f"{violation['confidence'] * 100:.0f}%"
                        )

                        cv2.rectangle(
                            annotated_frame,
                            (x1, y1),
                            (x2, y2),
                            (0, 0, 255),
                            2
                        )

                        cv2.putText(
                            annotated_frame,
                            label,
                            (x1, max(y1 - 10, 20)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0, 0, 255),
                            2
                        )

                # Следующая проверка
                next_check_time += self.check_interval

            # Записываем кадр
            out.write(annotated_frame)

            frame_number += 1

            # Прогресс
            if progress_callback:
                progress = (
                                   frame_number / total_frames
                           ) * 100

                progress_callback(progress)

        cap.release()
        out.release()

        # Создаём папку для JSON
        os.makedirs(
            os.path.dirname(json_path) or ".",
            exist_ok=True
        )

        # Сохраняем результаты
        with open(
                json_path,
                "w",
                encoding="utf-8"
        ) as f:

            json.dump(
                violations,
                f,
                ensure_ascii=False,
                indent=4
            )

        print("\n\nАнализ завершён.")
        print(
            f"Найдено событий: {len(violations)}"
        )

        return violations
