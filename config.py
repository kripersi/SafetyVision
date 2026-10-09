"""Настройки источника видео для live-режима.

Как подключить камеру:
1. Укажите CAMERA_MODE = "rtsp".
2. В файле cameras.json добавьте камеры или используйте интерфейс настроек.
3. Если камера недоступна, приложение автоматически использует локальный файл.
"""

import os

CAMERA_MODE = "rtsp"  # "file" или "rtsp"
CAMERA_SOURCE = r"C:\Users\user\PycharmProjects\BIM_model\videos\video.avi"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMERAS_FILE = os.path.join(BASE_DIR, "cameras.json")
MONITORING_RULES_FILE = os.path.join(BASE_DIR, "monitoring_rules.json")
MONITORING_SETTINGS_FILE = os.path.join(BASE_DIR, "monitoring_settings.json")
TELEGRAM_BOT_TOKEN = "8620870036:AAGcmEgiB3MTGnMz9GuOCxI4l1kXpbMIdBg"
TELEGRAM_CHAT_ID = "5381172828"
DEFAULT_DETECT_INTERVAL = 5.0
DEFAULT_CONFIDENCE_THRESHOLD = 0.4
DEFAULT_DISPLAY_CONFIDENCE_THRESHOLD = 0.4
VIOLATION_CLASS_NAMES = {
    "NO-Hardhat": "Без каски",
    "NO-Mask": "Без маски",
    "NO-Safety Vest": "Без защитного жилета",
}

DISPLAY_CLASS_NAMES = {
    "Hardhat": "Каска",
    "Mask": "Маска",
    "NO-Hardhat": "Без каски",
    "NO-Mask": "Без маски",
    "NO-Safety Vest": "Без защитного жилета",
    "Person": "Человек",
    "person": "Человек",
    "Safety Cone": "Конус безопасности",
    "Safety Vest": "Защитный жилет",
    "machinery": "Машины и механизмы",
    "vehicle": "Транспорт",
    "Vehicle": "Транспорт",
}

DEFAULT_CAMERAS = [
    {"name": "Камера 1", "url": "rtsp://admin:admin12345@192.168.1.27:554/Streaming/channels/201"},
    {"name": "Камера 2", "url": "rtsp://admin:admin12345@192.168.1.27:554/Streaming/channels/101"},
]

LOCAL_CAMERA_URL = "тест"
LOCAL_CAMERA_INDEX = 0

DEFAULT_MONITORING_RULES = {
    "Hardhat": True,
    "Mask": True,
    "NO-Hardhat": True,
    "NO-Mask": True,
    "NO-Safety Vest": True,
    "Person": False,
    "Safety Cone": True,
    "Safety Vest": True,
    "machinery": True,
    "vehicle": True,
}


