from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class ShiftPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setStyleSheet(
            """
            QWidget { background: #0f1419; color: #edf3fb; }
            QLabel { color: #edf3fb; }
            QPushButton {
                background: #171d24; color: #edf3fb;
                border: 1px solid #2a313a; border-radius: 12px; padding: 10px 14px;
            }
            QFrame.card { background: #151b20; border: 1px solid #212b34; border-radius: 16px; }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)

        header = QHBoxLayout()
        title = QLabel("Отчеты")
        title.setStyleSheet("font-size: 28px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch()
        back_button = QPushButton("Назад")
        back_button.clicked.connect(main_window.show_main_menu)
        header.addWidget(back_button)
        layout.addLayout(header)

        description = QLabel("Статистика нарушений экипировки по данным мониторинга")
        description.setStyleSheet("color: #96a3b7; font-size: 13px;")
        layout.addWidget(description)

        summary = main_window.get_report_summary()
        metrics = [
            ("Всего нарушений", summary["all_time"], "#ff4d4d"),
            ("За текущий месяц", summary["month"], "#ff9f43"),
            ("За текущую смену", summary["shift"], "#f1c40f"),
            ("За последние 2 часа", summary["last_two_hours"], "#e67e22"),
            ("Процент нарушений за смену", f"{summary['shift_percent']:.1f}%", "#2ecc71"),
        ]

        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(16)
        for index, (label, value, color) in enumerate(metrics):
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(18, 16, 18, 16)
            value_label = QLabel(str(value))
            value_label.setStyleSheet(f"font-size: 30px; font-weight: 700; color: {color};")
            title_label = QLabel(label)
            title_label.setWordWrap(True)
            title_label.setStyleSheet("font-size: 12px; color: #adb8c5;")
            card_layout.addWidget(value_label)
            card_layout.addWidget(title_label)
            metrics_grid.addWidget(card, index // 3, index % 3)
        layout.addLayout(metrics_grid)

        note = QLabel(
            f"Всего смен с записями: {summary['total_shifts']}. "
            "В расчет входят только: без каски, без маски и без защитного жилета."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #96a3b7; font-size: 12px;")
        layout.addWidget(note)
        layout.addStretch()
