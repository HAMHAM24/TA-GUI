import sys
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import QTimer
from ui_main import Ui_MainWindow
from wajah import RobotFace


class MainWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.face = RobotFace()
        self.face.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        
        self.ui.pushButton.clicked.connect(self.tombol_ditekan)

    def tombol_ditekan(self):
        print("Tombol ditekan bro 🔥")


class FaceWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Face - TA")
        self.setFixedSize(1024, 600)
        
        self.face = RobotFace()
        layout = QVBoxLayout(self)
        layout.addWidget(self.face)
        
        self._setup_demo()

    def _setup_demo(self):
        self.demo_timer = QTimer(self)
        self.demo_timer.timeout.connect(self._demo_sequence)
        self.demo_step = 0
        QTimer.singleShot(1000, self._start_demo)

    def _start_demo(self):
        print("\n=== DEMO START ===")
        print("Menggunakan API:")
        print("  face.set_llm_state('senang')  # Set ekspresi dari Qwen")
        print("  face.set_tts_active(True)    # Mulai berbicara (TTS)")
        print("  face.set_tts_active(False)   # Berhenti berbicara")
        print("====================\n")
        self.demo_timer.start(3000)

    def _demo_sequence(self):
        demos = [
            ("senang", True),
            ("senang", False),
            ("sedih", True),
            ("sedih", False),
            ("marah", True),
            ("marah", False),
            ("ketawa", True),
            ("ketawa", False),
        ]
        
        emotion, tts = demos[self.demo_step]
        self.face.set_llm_state(emotion)
        QTimer.singleShot(500, lambda: self.face.set_tts_active(tts))
        
        self.demo_step = (self.demo_step + 1) % len(demos)
        if self.demo_step == 0:
            print("Demo sequence restart...")


if __name__ == "__main__":
    from PySide6.QtCore import Qt
    
    app = QApplication(sys.argv)
    
    face_window = FaceWindow()
    face_window.show()
    
    sys.exit(app.exec())
