from PySide6.QtCore import Qt, QEvent, QTimer, QEasingCurve, QPropertyAnimation
from PySide6.QtGui import QIcon


class UIFunctions:
    def __init__(self, main_window):
        self.main_window = main_window
        self.drag_pos = None
        self.is_maximized = False
        self.menu_expanded = False
        

    # TOGGLE MAXIMIZE / RESTORE
    def toggle_max_restore(self):
        if self.is_maximized:
            self.main_window.showNormal()
            self.is_maximized = False
        else:
            self.main_window.showMaximized()
            self.is_maximized = True

    # MOUSE PRESS (dipanggil dari MainWindow)
    def mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()

    # MOUSE MOVE (drag window)
    def mouse_move(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos:
            # Jika sedang maximize, kembalikan normal dulu
            if self.is_maximized:
                self.toggle_max_restore()

            self.main_window.move(
                self.main_window.pos()
                + event.globalPosition().toPoint()
                - self.drag_pos
            )
            self.drag_pos = event.globalPosition().toPoint()
            event.accept()

    # DOUBLE CLICK TITLE BAR → MAX / RESTORE
    def mouse_double_click(self, event):
        if event.type() == QEvent.MouseButtonDblClick:
            QTimer.singleShot(100, self.toggle_max_restore)
            
            
    def toggle_left_menu(self, menu):
        collapsed_width = 60
        expanded_width = 240

        current_width = menu.width()

        if self.menu_expanded:
            # COLLAPSE
            menu.setMinimumWidth(0)

            self.animation = QPropertyAnimation(menu, b"maximumWidth")
            self.animation.setDuration(300)
            self.animation.setStartValue(current_width)
            self.animation.setEndValue(collapsed_width)
            self.animation.setEasingCurve(QEasingCurve.InOutQuart)

            self.menu_expanded = False

        else:
            # EXPAND (ANIMASI DULU)
            menu.setMaximumWidth(expanded_width)

            self.animation = QPropertyAnimation(menu, b"maximumWidth")
            self.animation.setDuration(300)
            self.animation.setStartValue(current_width)
            self.animation.setEndValue(expanded_width)
            self.animation.setEasingCurve(QEasingCurve.InOutQuart)

            # SET MIN WIDTH SETELAH ANIMASI SELESAI
            self.animation.finished.connect(
                lambda: menu.setMinimumWidth(expanded_width)
            )

            self.menu_expanded = True

        self.animation.start()
