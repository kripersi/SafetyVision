import json
import os

from config import (
    CAMERA_MODE,
    CAMERA_SOURCE,
    CAMERAS_FILE,
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_DETECT_INTERVAL,
    DEFAULT_DISPLAY_CONFIDENCE_THRESHOLD,
    DEFAULT_MONITORING_RULES,
    LOCAL_CAMERA_INDEX,
    LOCAL_CAMERA_URL,
    MONITORING_RULES_FILE,
    MONITORING_SETTINGS_FILE,
)


def _read_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if data is not None else default
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _write_json(path: str, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def load_cameras() -> list[dict]:
    """Load camera definitions; an empty list is a valid saved value."""
    if not os.path.exists(CAMERAS_FILE):
        return []

    cameras = _read_json(CAMERAS_FILE, [])
    if not isinstance(cameras, list):
        return []

    cleaned = []
    for camera in cameras:
        if not isinstance(camera, dict):
            continue
        name = str(camera.get("name") or "Камера").strip()
        url = str(camera.get("url") or "").strip()
        if url:
            cleaned.append({"name": name or "Камера", "url": url})

    return cleaned


def save_cameras(cameras: list[dict]):
    _write_json(CAMERAS_FILE, cameras)


def load_monitoring_rules() -> dict:
    rules = _read_json(MONITORING_RULES_FILE, DEFAULT_MONITORING_RULES)
    if not isinstance(rules, dict):
        return DEFAULT_MONITORING_RULES.copy()
    merged = DEFAULT_MONITORING_RULES.copy()
    merged.update({key: bool(value) for key, value in rules.items()})
    return merged


def save_monitoring_rules(rules: dict):
    _write_json(MONITORING_RULES_FILE, rules)


def load_detect_interval() -> float:
    settings = _read_json(MONITORING_SETTINGS_FILE, {})
    try:
        interval = float(settings.get("detect_interval", DEFAULT_DETECT_INTERVAL))
    except (TypeError, ValueError):
        return DEFAULT_DETECT_INTERVAL
    return interval if interval >= 0 else DEFAULT_DETECT_INTERVAL


def save_detect_interval(interval: float):
    value = float(interval)
    if value < 0:
        raise ValueError("Интервал не может быть отрицательным")
    settings = _read_json(MONITORING_SETTINGS_FILE, {})
    if not isinstance(settings, dict):
        settings = {}
    settings["detect_interval"] = value
    _write_json(MONITORING_SETTINGS_FILE, settings)


def load_confidence_threshold() -> float:
    settings = _read_json(MONITORING_SETTINGS_FILE, {})
    try:
        threshold = float(settings.get("confidence_threshold", DEFAULT_CONFIDENCE_THRESHOLD))
    except (TypeError, ValueError):
        return DEFAULT_CONFIDENCE_THRESHOLD
    return min(max(threshold, 0.0), 1.0)


def save_confidence_threshold(threshold: float):
    value = float(threshold)
    if not 0.0 <= value <= 1.0:
        raise ValueError("Порог уверенности должен быть от 0 до 1")
    settings = _read_json(MONITORING_SETTINGS_FILE, {})
    if not isinstance(settings, dict):
        settings = {}
    settings["confidence_threshold"] = value
    _write_json(MONITORING_SETTINGS_FILE, settings)


def load_display_confidence_threshold() -> float:
    settings = _read_json(MONITORING_SETTINGS_FILE, {})
    try:
        threshold = float(settings.get("display_confidence_threshold", DEFAULT_DISPLAY_CONFIDENCE_THRESHOLD))
    except (TypeError, ValueError):
        return DEFAULT_DISPLAY_CONFIDENCE_THRESHOLD
    return min(max(threshold, 0.0), 1.0)


def save_display_confidence_threshold(threshold: float):
    value = float(threshold)
    if not 0.0 <= value <= 1.0:
        raise ValueError("Порог отображения должен быть от 0 до 1")
    settings = _read_json(MONITORING_SETTINGS_FILE, {})
    if not isinstance(settings, dict):
        settings = {}
    settings["display_confidence_threshold"] = value
    _write_json(MONITORING_SETTINGS_FILE, settings)


def get_camera_sources() -> list[dict]:
    if CAMERA_MODE == "rtsp":
        return load_cameras()
    return []


def get_camera_source(camera_index: int = 0) -> str:
    camera_sources = get_camera_sources()
    if not camera_sources:
        return CAMERA_SOURCE

    index = max(0, min(int(camera_index), len(camera_sources) - 1))
    return camera_sources[index]["url"]


def is_local_camera_source(source: str) -> bool:
    return isinstance(source, str) and source.strip().lower() == LOCAL_CAMERA_URL.lower()


def get_opencv_camera_source(source: str):
    return LOCAL_CAMERA_INDEX if is_local_camera_source(source) else source
