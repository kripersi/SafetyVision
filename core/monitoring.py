from config import (
    DEFAULT_DISPLAY_CONFIDENCE_THRESHOLD,
    DEFAULT_MONITORING_RULES,
)
from core.settings_store import load_monitoring_rules


# Строится один раз при загрузке модуля, а не при каждом вызове
_RULE_KEYS_LOWER = {key.lower(): key for key in DEFAULT_MONITORING_RULES}

_ALIASES = {
    "без жилета": "NO-Safety Vest",
    "без каски": "NO-Hardhat",
    "без маски": "NO-Mask",
    "жилет": "Safety Vest",
    "защитный жилет": "Safety Vest",
    "каска": "Hardhat",
    "конус безопасности": "Safety Cone",
    "маска": "Mask",
    "машины": "machinery",
    "машины и механизмы": "machinery",
    "механизмы": "machinery",
    "транспорт": "vehicle",
    "человек": "Person",
}


def normalize_monitoring_rule_key(class_name):
    """Приводит название класса (YOLO или русское) к ключу правила мониторинга."""
    if not isinstance(class_name, str):
        return ""

    raw = class_name.strip()
    if not raw:
        return ""

    low = raw.lower()
    return _RULE_KEYS_LOWER.get(low) or _ALIASES.get(low, raw)


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
        if not isinstance(detection, dict):
            continue

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
