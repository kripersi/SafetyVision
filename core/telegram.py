import urllib.error
import urllib.parse
import urllib.request

from core.settings_store import load_telegram_settings


def send_telegram_message(message: str) -> bool:
    """Send a text message to Telegram; return whether the request succeeded."""
    settings = load_telegram_settings()
    bot_token = settings["bot_token"]
    chat_id = settings["chat_id"]
    if not bot_token or not chat_id:
        print("Telegram не настроен: отсутствует бот-токен или chat ID")
        return False

    payload = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": True,
    }).encode("utf-8")

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    try:
        request = urllib.request.Request(url, data=payload, method="POST")
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
        return True
    except urllib.error.URLError as exc:
        reason = exc.reason
        network_reason = isinstance(reason, (TimeoutError, OSError)) or any(
            text in str(reason).lower()
            for text in ("no route", "network", "timeout", "connection", "internet")
        )
        if network_reason:
            print("Telegram не отправлен: нет доступа к интернету")
        else:
            print(f"Telegram не отправлен: {reason}")
        return False
    except (TimeoutError, OSError) as exc:
        print(f"Telegram не отправлен: {exc}")
        return False
    except Exception as exc:
        print(f"Telegram не отправлен: ошибка HTTP/сети: {exc}")
        return False