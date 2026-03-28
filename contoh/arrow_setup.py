from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtCore import Qt
from widgets.flow_arrow import FlowArrow


class ArrowSetup:
    @staticmethod
    def setup(ui, main_window):

        # DOWN FRAME → PANAH KE BAWAH (SOC LOW)
        ui.arrow_pv = FlowArrow(direction="down")
        ArrowSetup._add(ui.downArrowFrame, ui.arrow_pv)

        # RIGHT FRAME → GRID IMPORT
        ui.arrow_grid = FlowArrow(direction="right")
        ArrowSetup._add(ui.rightArrowFrame, ui.arrow_grid)

        # LEFT FRAME → LOAD CONSUMPTION
        ui.arrow_load = FlowArrow(direction="right")
        ArrowSetup._add(ui.leftArrowFrame, ui.arrow_load)

        # UP FRAME → SOC DYNAMIC (UP / DOWN)
        ui.arrow_soc_dynamic = FlowArrow(direction="up")
        ArrowSetup._add(ui.upArrowFrame, ui.arrow_soc_dynamic)

        # simpan referensi
        main_window.arrows = {
            "pv": ui.arrow_pv,
            "soc_dynamic": ui.arrow_soc_dynamic,
            "grid": ui.arrow_grid,
            "load": ui.arrow_load,
        }
        
        

    @staticmethod
    def _add(frame, widget):
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(widget)
