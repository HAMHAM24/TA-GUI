from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtCore import Qt
from widgets.lamp_button import LampButton


class LampSetup:
    @staticmethod
    def setup(ui, main_window):
        frames = [
            ui.framebtnlamp1,
            ui.framebtnlamp2,
            ui.framebtnlamp3,
            ui.framebtnlamp4,
            ui.framebtnlamp5,
        ]

        lamp_locations = {
            1: "Lampu Atas Tengah",
            2: "Lampu Atas Utara dan Selatan",
            3: "Lampu Belakang TV",
            4: "Tidak Terpakai",
            5: "Lampu Depan Pintu",
        }

        main_window.lamps = []

        for i, frame in enumerate(frames, start=1):
            layout = QVBoxLayout(frame)
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            lamp = LampButton(size=100)

            # ✅ TOOLTIP DI TEMPAT YANG BENAR
            lamp.setToolTip(
                f"Lampu {i}\n"
                f"Lokasi: {lamp_locations.get(i, '-')}"
            )
            
            # 🔒 Disable Lamp Button 4
            if i == 4:
                lamp.setEnabled(False)

            layout.addWidget(lamp)
            main_window.lamps.append(lamp)

            lamp.toggled.connect(
                lambda state, idx=i: main_window.publish_lamp(idx, state)
            )
