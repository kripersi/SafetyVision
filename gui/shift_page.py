from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton
)


class ShiftPage(QWidget):

    def __init__(self, main_window):
        super().__init__()

        self.main_window = main_window

        layout = QVBoxLayout()

        title = QLabel("👷 Смена")

        title.setStyleSheet(
            "font-size: 30px; font-weight: bold;"
        )

        info = QLabel(
            "Раздел управления сменой\n\n"
            "Здесь позже появятся:\n"
            "• работники\n"
            "• время прихода\n"
            "• нарушения\n"
            "• Telegram\n"
            "• допуск к смене"
        )

        back_button = QPushButton(
            "← Назад"
        )

        back_button.clicked.connect(
            self.main_window.show_main_menu
        )

        layout.addWidget(title)
        layout.addWidget(info)
        layout.addStretch()
        layout.addWidget(back_button)

        self.setLayout(layout)
