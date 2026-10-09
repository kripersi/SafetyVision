import urllib.error
import urllib.parse
import urllib.request

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_telegram_message(message: str) -> bool:
    """Send a text message to Telegram; return whether the request succeeded."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram не настроен: отсутствует бот-токен или chat ID")
        return False

    payload = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": True,
    }).encode("utf-8")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

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