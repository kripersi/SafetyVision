import json
import os
import threading

import cv2

from core.monitoring import filter_detections_for_display
from core.settings_store import (
    load_confidence_threshold,
    load_display_confidence_threshold,
    load_monitoring_rules,
)
from core.utils import format_time


class VideoAnalyzer:

    @staticmethod
    def _merge_consecutive_violations(raw_violations):
        if not raw_violations:
            return []

        merged = []
        current = None

        for event in raw_violations:
            event_types = sorted(set(event.get("types", [])))

            if current is not None and event_types == current["types"]:
                current["time_end"] = float(event["time"])
                current["average_confidences"].append(float(event.get("average_confidence", 0.0)))
                current["violation_count"] += int(event.get("violation_count", 0))
                continue

            if current is not None:
                merged.append(current)

            current = {
                "time_start": float(event["time"]),
                "time_end": float(event["time"]),
                "types": event_types,
                "average_confidences": [float(event.get("average_confidence", 0.0))],
                "violation_count": int(event.get("violation_count", 0)),
            }

        if current is not None:
            merged.append(current)

        result = []
        for item in merged:
            start_time = item["time_start"]
            end_time = item["time_end"]
            start_formatted = format_time(start_time)
            end_formatted = format_time(end_time)
            if start_time == end_time:
                time_formatted = start_formatted
            else:
                time_formatted = f"{start_formatted}-{end_formatted}"

            average_conf = sum(item["average_confidences"]) / len(item["average_confidences"])
            result.append({
                "time": round(start_time, 2),
                "time_formatted": time_formatted,
                "types": item["types"],
                "average_confidence": round(average_conf, 4),
                "violation_count": item["violation_count"],
            })

        return result

    def __init__(self, detector, detector_lock=None):
        self.detector = detector
        self.detector_lock = detector_lock or threading.Lock()

        self.violation_classes = {
            "NO-Hardhat": "Отсутствие каски",
            "NO-Mask": "Отсутствие маски",
            "NO-Safety Vest": "Отсутствие жилета",
        }

        # Проверять видео каждые X секунд (VideoWorker может переопределить)
        self.check_interval = 5
        # Порог уверенности для записи нарушения (VideoWorker может переопределить)
        self.confidence_threshold = load_confidence_threshold()

    def analyze(self, video_path, output_path, json_path, progress_callback=None):
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise RuntimeError("Не удалось открыть видео")

        out = None

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 25

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if total_frames > 0 else 0.0

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            print(
                f"Видео: {width}x{height}, FPS {fps:.2f}, "
                f"{total_frames} кадров, {duration:.2f} сек\n"
            )
            print(f"Проверка каждые {self.check_interval} секунд\n")

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            if not out.isOpened():
                raise RuntimeError("Не удалось создать выходной видеофайл")

            violations = []
            next_check_time = 0.0
            frame_number = 0
            last_display = []  # последние рамки, держатся до следующей проверки

            rules = load_monitoring_rules()
            display_threshold = load_display_confidence_threshold()

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                current_time = frame_number / fps

                if current_time >= next_check_time:
                    next_check_time = current_time + self.check_interval

                    with self.detector_lock:
                        detections = self.detector.detect(frame)

                    last_display = filter_detections_for_display(
                        detections,
                        rules=rules,
                        confidence_threshold=display_threshold,
                    )

                    detected_violations = []
                    for detection in last_display:
                        class_name = detection["class_name"]
                        if detection["confidence"] < self.confidence_threshold:
                            continue
                        if class_name not in self.violation_classes:
                            continue
                        detected_violations.append({
                            "type": self.violation_classes[class_name],
                            "confidence": detection["confidence"],
                        })

                    if detected_violations:
                        violation_types = list(
                            dict.fromkeys(v["type"] for v in detected_violations)
                        )
                        average_confidence = (
                                sum(v["confidence"] for v in detected_violations)
                                / len(detected_violations)
                        )
                        violations.append({
                            "time": round(current_time, 2),
                            "time_formatted": format_time(current_time),
                            "types": violation_types,
                            "average_confidence": round(average_confidence, 4),
                            "violation_count": len(detected_violations),
                        })

                # Рамки рисуем на каждом кадре, пока не придёт новая проверка
                if last_display:
                    annotated_frame = self.detector.draw_detections(
                        frame, last_display, copy=False
                    )
                else:
                    annotated_frame = frame

                out.write(annotated_frame)
                frame_number += 1

                if progress_callback and total_frames > 0:
                    progress_callback(min(100.0, frame_number / total_frames * 100))

        finally:
            cap.release()
            if out is not None:
                out.release()

        merged_violations = self._merge_consecutive_violations(violations)

        for violation in merged_violations:
            types_text = ", ".join(violation["types"])
            print(
                f"НАРУШЕНИЕ: {violation['time_formatted']} | "
                f"{types_text} | "
                f"средний процент {violation['average_confidence'] * 100:.1f}% | "
                f"нарушений: {violation['violation_count']} \n"
            )

        os.makedirs(os.path.dirname(json_path) or ".", exist_ok=True)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(merged_violations, f, ensure_ascii=False, indent=4)

        print("\n\nАнализ завершён.")
        print(f"Найдено событий: {len(merged_violations)}")

        return merged_violations
