from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtCore import Qt
from widgets.ac_button import ACButton


class ACSetup:
    @staticmethod
    # def setup(ui, main_window):
    #     layout = QVBoxLayout(ui.frameButtonOnOffAC)
    #     layout.setAlignment(Qt.AlignCenter)
    #     layout.setContentsMargins(0, 0, 0, 0)
    #     layout.setSpacing(6)

    #     main_window.ac_button = ACButton()
    #     layout.addWidget(main_window.ac_button)

    #     # update label status AC
    #     def update_status(state):
    #         ui.statusAC.setText("AC: ON ❄️" if state else "AC: OFF")
    #         ui.statusAC.setProperty("state", "on" if state else "off")
    #         ui.statusAC.style().polish(ui.statusAC)
        
    #     main_window.ac_button.toggled.connect(update_status)
    #     main_window.ac_button.toggled.connect(
    #         lambda state: main_window.publish_ac_power(state)
    #     )

    def setup(ui, main_window):
        layout = QVBoxLayout(ui.frameButtonOnOffAC)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        main_window.ac_button = ACButton()
        layout.addWidget(main_window.ac_button)

        # === UPDATE STATUS AC ===
        def update_ac_status(state):
            ui.statusAC.setText("AC: ON ❄️" if state else "AC: OFF")
            ui.statusAC.setProperty("state", "on" if state else "off")
            ui.statusAC.style().polish(ui.statusAC)

        # expose ke MainWindow (INI PENTING)
        main_window.update_ac_status = update_ac_status

        # saat klik user
        main_window.ac_button.toggled.connect(update_ac_status)
        main_window.ac_button.toggled.connect(
            lambda state: main_window.publish_ac_power(state)
        )

