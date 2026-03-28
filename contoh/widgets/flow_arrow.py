from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QPainter, QColor, QPolygon


class FlowArrow(QWidget):
    """
    Flow Arrow Cascade Widget
    direction: 'up', 'down', 'left', 'right'
    """

    def __init__(self, parent=None, direction="right", count=5):
        super().__init__(parent)

        self.direction = direction
        self.count = count
        self.active = False

        self.step = 0
        self.state = "grow"
        self.alpha = 255

        if direction in ("up", "down"):
            self.setFixedSize(40, 140)
        else:
            self.setFixedSize(140, 40)

        self.timer = QTimer(self)
        self.timer.setInterval(120)
        self.timer.timeout.connect(self.animate)

    # ================= CONTROL =================
    def set_active(self, state: bool):
        if self.active == state:
            return

        self.active = state
        self.step = 0
        self.state = "grow"
        self.alpha = 255

        if state:
            self.timer.start()
        else:
            self.timer.stop()
            self.update()

    def animate(self):
        if self.state == "grow":
            self.step += 1
            if self.step >= self.count:
                self.step = self.count
                self.state = "fade"
        else:
            self.alpha -= 35
            if self.alpha <= 0:
                self.step = 0
                self.alpha = 255
                self.state = "grow"

        self.update()

    # ================= PAINT =================
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        active_color = QColor("#032277")     # hijau jelas
        inactive_color = QColor(200, 200, 200)

        w, h = self.width(), self.height()
        size = 6
        spacing = 18

        for i in range(self.count):
            if not self.active or i >= self.step:
                color = inactive_color
                alpha = 255
            else:
                color = active_color
                alpha = self.alpha

            c = QColor(color)
            c.setAlpha(alpha)
            p.setBrush(c)
            p.setPen(Qt.NoPen)

            if self.direction == "right":
                x = 10 + i * spacing
                y = h // 2
            elif self.direction == "left":
                x = w - (10 + i * spacing)
                y = h // 2
            elif self.direction == "down":
                x = w // 2
                y = 10 + i * spacing
            elif self.direction == "up":
                x = w // 2
                y = (self.count - i - 1) * spacing + 8


            p.drawPolygon(self.make_triangle(x, y, size))

    def make_triangle(self, x, y, s):
        if self.direction == "right":
            return QPolygon([
                QPoint(x, y - s),
                QPoint(x, y + s),
                QPoint(x + s + 6, y)
            ])
        if self.direction == "left":
            return QPolygon([
                QPoint(x, y),
                QPoint(x + s + 6, y - s),
                QPoint(x + s + 6, y + s)
            ])
        if self.direction == "up":
            return QPolygon([
                QPoint(x - s, y + s + 6),
                QPoint(x + s, y + s + 6),
                QPoint(x, y)
            ])
        return QPolygon([
            QPoint(x - s, y),
            QPoint(x + s, y),
            QPoint(x, y + s + 6)
        ])

    def set_direction(self, direction: str):
        if direction not in ("up", "down", "left", "right"):
            return

        if self.direction == direction:
            return

        self.direction = direction
        self.step = 0
        self.alpha = 255
        self.state = "grow"
        self.update()
