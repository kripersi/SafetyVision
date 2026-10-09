class ViolationTracker:
    """
    Превращает поток детекций в события-эпизоды.
    Вызывается из одного потока (AI-потока камеры) — блокировки не нужны.
    """

    def __init__(self, confirm_hits=2, confirm_seconds=1.5, repeat_after=300.0):
        self.confirm_hits = confirm_hits
        self.confirm_seconds = confirm_seconds
        self.repeat_after = repeat_after
        self._tracks = {}  # class_name -> dict

    def update(self, violations, now, clear_after):
        """
        violations  — детекции-нарушения текущего прогона AI (может быть пустым!)
        clear_after — сколько секунд без нарушения закрывает эпизод
        Возвращает список событий для лога/Telegram.
        """
        by_class = {}
        for det in violations:
            by_class.setdefault(det["class_name"], []).append(det)

        events = []

        for class_name, dets in by_class.items():
            track = self._tracks.get(class_name)
            if track is None:
                track = self._tracks[class_name] = {
                    "first": now,
                    "hits": 0,
                    "max_conf": 0.0,
                    "max_count": 0,
                    "reported_at": None,
                }

            track["last"] = now
            track["hits"] += 1
            track["max_conf"] = max(track["max_conf"], max(d["confidence"] for d in dets))
            track["max_count"] = max(track["max_count"], len(dets))

            if track["reported_at"] is None:
                confirmed = (
                        track["hits"] >= self.confirm_hits
                        and now - track["first"] >= self.confirm_seconds
                )
                if confirmed:
                    track["reported_at"] = now
                    events.append(self._event(class_name, track, repeat=False))
            elif now - track["reported_at"] >= self.repeat_after:
                track["reported_at"] = now
                events.append(self._event(class_name, track, repeat=True))

        # Закрываем эпизоды, где нарушения давно нет
        for class_name in list(self._tracks):
            if class_name in by_class:
                continue
            if now - self._tracks[class_name]["last"] >= clear_after:
                del self._tracks[class_name]

        return events

    @staticmethod
    def _event(class_name, track, repeat):
        return {
            "class_name": class_name,
            "confidence": track["max_conf"],
            "count": track["max_count"],
            "repeat": repeat,
        }
