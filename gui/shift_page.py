from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ShiftPage(QWidget):

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setStyleSheet(
            """
            QWidget {
                background: #0f1419;
                color: #edf3fb;
            }
            QLabel { color: #edf3fb; }
            QPushButton {
                background: #171d24;
                color: #edf3fb;
                border: 1px solid #2a313a;
                border-radius: 12px;
                padding: 10px 14px;
            }
            QFrame.card {
                background: #151b20;
                border: 1px solid #212b34;
                border-radius: 16px;
            }
            QProgressBar {
                border: 1px solid #2d3742;
                border-radius: 8px;
                background: #0d1318;
            }
            QProgressBar::chunk {
                background: #2ecc71;
                border-radius: 7px;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(18)

        header = QHBoxLayout()
        title = QLabel("📊 Отчеты / Статистика")
        title.setStyleSheet("font-size: 28px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch()

        back_button = QPushButton("← Назад")
        back_button.clicked.connect(self.main_window.show_main_menu)
        header.addWidget(back_button)
        layout.addLayout(header)

        metrics = QHBoxLayout()
        metrics.setSpacing(16)
        for value, label, color in [
            ("96%", "Сводка по смене", "#2ecc71"),
            ("28", "Проверок PPE", "#ff6b00"),
            ("03", "Небезопасных зон", "#ff4d4d"),
            ("2.4h", "Среднее время реакции", "#f1c40f"),
        ]:
            card = QFrame()
            card.setObjectName("card")
            card.setMinimumHeight(100)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)
            val = QLabel(value)
            val.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {color};")
            lab = QLabel(label)
            lab.setStyleSheet("font-size: 12px; color: #adb8c5;")
            card_layout.addWidget(val)
            card_layout.addWidget(lab)
            metrics.addWidget(card)
        layout.addLayout(metrics)

        main_row = QHBoxLayout()
        main_row.setSpacing(18)

        chart = QFrame()
        chart.setObjectName("card")
        chart.setMinimumHeight(360)
        chart_layout = QVBoxLayout(chart)
        chart_layout.setContentsMargins(18, 18, 18, 18)
        chart_title = QLabel("Распределение рисков по участкам")
        chart_title.setStyleSheet("font-size: 18px; font-weight: 700;")
        chart_layout.addWidget(chart_title)

        bars = QHBoxLayout()
        bars.setSpacing(12)
        zones = [("Зона 1", 72), ("Зона 2", 48), ("Зона 3", 84), ("Зона 4", 33), ("Зона 5", 59)]
        for name, level in zones:
            col = QVBoxLayout()
            bar = QProgressBar()
            bar.setValue(level)
            bar.setMinimumHeight(180)
            bar.setOrientation(1)
            label = QLabel(name)
            label.setAlignment(0x0004)
            col.addWidget(bar)
            col.addWidget(label)
            bars.addLayout(col)
        chart_layout.addLayout(bars)
        main_row.addWidget(chart, 2)

        summary = QFrame()
        summary.setObjectName("card")
        summary.setMinimumWidth(330)
        summary.setMaximumWidth(330)
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(16, 16, 16, 16)

        summary_title = QLabel("Краткая сводка")
        summary_title.setStyleSheet("font-size: 18px; font-weight: 700;")
        summary_layout.addWidget(summary_title)
        tasks = [
            "Усилить наблюдение у входа №2",
            "Проверить 3 бригады по PPE",
            "Выполнить инструктаж первой смены",
            "Подтвердить отметку в зоне 4",
        ]
        for task in tasks:
            task_label = QLabel(f"• {task}")
            task_label.setStyleSheet("font-size: 12px; color: #cbd6e6; margin-top: 8px;")
            summary_layout.addWidget(task_label)
        summary_layout.addStretch()
        main_row.addWidget(summary, 1)
        layout.addLayout(main_row)

        footer = QHBoxLayout()
        footer.addStretch()
        export_btn = QPushButton("📤 Экспорт в PDF")
        export_btn.setObjectName("ghostButton")
        footer.addWidget(export_btn)
        layout.addLayout(footer)
