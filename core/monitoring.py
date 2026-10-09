from config import (
    DEFAULT_DISPLAY_CONFIDENCE_THRESHOLD,
    DEFAULT_MONITORING_RULES,
)
from core.settings_store import load_monitoring_rules


def normalize_monitoring_rule_key(class_name):
    """Normalize a YOLO or Russian class label to its monitoring-rule key."""
    if not isinstance(class_name, str):
        return ""

    raw = class_name.strip()
    if not raw:
        return ""

    if raw in DEFAULT_MONITORING_RULES:
        return raw

    lowered = raw.lower()
    if lowered in {key.lower() for key in DEFAULT_MONITORING_RULES}:
        for key in DEFAULT_MONITORING_RULES:
            if key.lower() == lowered:
                return key

    alias_map = {
        "Без жилета": "NO-Safety Vest",
        "Без каски": "NO-Hardhat",
        "Без маски": "NO-Mask",
        "Жилет": "Safety Vest",
        "Защитный жилет": "Safety Vest",
        "Каска": "Hardhat",
        "Конус безопасности": "Safety Cone",
        "Маска": "Mask",
        "Машины": "machinery",
        "Машины и механизмы": "machinery",
        "Механизмы": "machinery",
        "Транспорт": "vehicle",
        "Человек": "Person",
    }
    return alias_map.get(raw.lower(), raw)


def is_monitoring_rule_enabled(class_name, rules=None):
    if rules is None:
        rules = load_monitoring_rules()

    if not isinstance(class_name, str):
        return True

    normalized = normalize_monitoring_rule_key(class_name)
    if not normalized:
        return True

    if normalized in rules:
        return bool(rules.get(normalized, True))

    raw = class_name.strip()
    if raw in rules:
        return bool(rules.get(raw, True))

    return bool(rules.get(raw.lower(), True))


def should_run_detection(now: float, last_detect_time: float, interval: float) -> bool:
    return interval <= 0 or now - last_detect_time >= interval


def filter_detections_for_display(
        detections,
        rules=None,
        confidence_threshold=DEFAULT_DISPLAY_CONFIDENCE_THRESHOLD,
):
    if not isinstance(detections, list):
        return []

    filtered = []
    for detection in detections:
        class_name = detection.get("class_name")
        confidence = float(detection.get("confidence", 0.0))
        if not isinstance(class_name, str):
            continue
        if not is_monitoring_rule_enabled(class_name, rules):
            continue
        if confidence < confidence_threshold:
            continue
        filtered.append(detection)
    return filtered
