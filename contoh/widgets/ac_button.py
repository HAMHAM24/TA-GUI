from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, Property, Signal
from PySide6.QtGui import QPainter, QColor, QBrush, QPen


def blend_color(c1: QColor, c2: QColor, t: float) -> QColor:
    r = c1.red() + (c2.red() - c1.red()) * t
    g = c1.green() + (c2.green() - c1.green()) * t
    b = c1.blue() + (c2.blue() - c1.blue()) * t
    return QColor(int(r), int(g), int(b))


class ACButton(QWidget):
    """
    Animated AC Switch Button
    Signal:
        toggled(bool)
    """
    toggled = Signal(bool)

    def __init__(self, parent=None, width=90, height=42):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.setCursor(Qt.PointingHandCursor)
        
        # Warna pastel
        self.off_color = QColor("#DCE9F5")
        self.on_color = QColor("#A5E8FF")

        self._bg_color = self.off_color
        self._is_on = False
        self._radius = height // 2
        self._handle_pos = 3

        # Animasi handle
        self._anim_pos = QPropertyAnimation(self, b"handle_pos", self)
        self._anim_pos.setDuration(260)
        self._anim_pos.setEasingCurve(QEasingCurve.OutCubic)

        # Animasi warna
        self._anim_progress = 0.0
        self._color_timer = QTimer(self)
        self._color_timer.setInterval(15)
        self._color_timer.timeout.connect(self._update_color)

    # ===== handle property =====
    def get_handle_pos(self):
        return self._handle_pos

    def set_handle_pos(self, pos):
        self._handle_pos = pos
        self.update()

    handle_pos = Property(float, get_handle_pos, set_handle_pos)

    # ===== interaction =====
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle()

    def toggle(self):
        self._is_on = not self._is_on
        self._anim_progress = 0.0
        self._color_timer.start()
        self._animate_switch()
        self.toggled.emit(self._is_on)

    def isOn(self):
        return self._is_on

    def setOn(self, state: bool):
        if self._is_on == state:
            return
        self._is_on = state
        self._animate_switch()
        self._color_timer.start()
        self.toggled.emit(state)

    # ===== animation =====
    def _animate_switch(self):
        start = self._handle_pos
        end = self.width() - self.height() + 3 if self._is_on else 3

        self._anim_pos.stop()
        self._anim_pos.setStartValue(start)
        self._anim_pos.setEndValue(end)
        self._anim_pos.start()

    def _update_color(self):
        self._anim_progress += 0.06
        if self._anim_progress >= 1.0:
            self._anim_progress = 1.0
            self._color_timer.stop()

        if self._is_on:
            self._bg_color = blend_color(self.off_color, self.on_color, self._anim_progress)
        else:
            self._bg_color = blend_color(self.on_color, self.off_color, self._anim_progress)

        self.update()

    # ===== paint =====
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Background
        p.setBrush(QBrush(self._bg_color))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(self.rect(), self._radius, self._radius)

        # Handle
        d = self.height() - 6
        p.setBrush(Qt.white)
        p.setPen(QPen(QColor(200, 200, 200), 1))
        p.drawEllipse(self._handle_pos, 3, d, d)
        

    # def setChecked(self, state: bool):
    #     """
    #     Sinkron state dari MQTT / aplikasi lain
    #     TANPA emit toggled (biar tidak loop)
    #     """
    #     if self._is_on == state:
    #         return

    #     self._is_on = state
    #     self._animate_switch()
    #     self._color_timer.start()


    def setChecked(self, state: bool):
        """
        Sinkron state AC dari MQTT / restore state
        TANPA emit signal toggled
        """
        if self._is_on == state:
            return

        self._is_on = state

        # 🔥 PAKSA update tampilan AC
        self._animate_switch()     # posisi toggle
        self._color_timer.start()  # trigger warna ON/OFF
        self.update()              # repaint widget
