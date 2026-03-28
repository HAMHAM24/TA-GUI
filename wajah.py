from PySide6.QtWidgets import QApplication, QWidget, QPushButton
from PySide6.QtGui import (QPainter, QColor, QBrush, QPen, QPolygonF,
                            QLinearGradient, QRadialGradient, QFont, QPainterPath)
from PySide6.QtCore import QTimer, Qt, Signal, QObject, QPointF, QRectF
import random
import threading
import math


# ─────────────────────────────────────────────
#  WARNA PER EKSPRESI
# ─────────────────────────────────────────────
EXPR_COLORS = {
    "happy":  {"bg": QColor(30, 30, 60),   "glow": QColor(255, 220, 60),  "eye": QColor(255, 230, 80),  "mouth": QColor(255, 200, 60)},
    "sad":    {"bg": QColor(10, 20, 50),   "glow": QColor(80, 120, 220),  "eye": QColor(100, 150, 255), "mouth": QColor(80, 140, 220)},
    "laugh":  {"bg": QColor(40, 20, 10),   "glow": QColor(255, 140, 20),  "eye": QColor(255, 180, 40),  "mouth": QColor(255, 120, 20)},
    "angry":  {"bg": QColor(40, 5, 5),     "glow": QColor(255, 40, 20),   "eye": QColor(255, 60, 30),   "mouth": QColor(220, 30, 10)},
    "talk":   {"bg": QColor(10, 35, 30),   "glow": QColor(60, 220, 150),  "eye": QColor(80, 255, 170),  "mouth": QColor(50, 200, 130)},
    "sleep":  {"bg": QColor(15, 10, 40),   "glow": QColor(130, 80, 220),  "eye": QColor(160, 120, 240), "mouth": QColor(120, 90, 200)},
    "gabut":  {"bg": QColor(25, 15, 45),   "glow": QColor(120, 180, 255), "eye": QColor(180, 220, 255), "mouth": QColor(150, 200, 255)},
    "standby":{"bg": QColor(20, 20, 40),   "glow": QColor(200, 200, 200), "eye": QColor(220, 220, 220), "mouth": QColor(180, 180, 180)},
    "pukpuk": {"bg": QColor(50, 70, 100),  "glow": QColor(180, 200, 255), "eye": QColor(200, 220, 255), "mouth": QColor(255, 200, 180)},
}


class InputHandler(QObject):
    input_signal = Signal(str)
    stop_signal  = Signal()

    def __init__(self):
        super().__init__()
        self.running = True

    def listen(self):
        print("\n=== KONTROL WAJAH ROBOT ===")
        print("State & Perintah:")
        print("  voka    -> Wake word terdeteksi (interrupt ke Standby)")
        print("  senang  -> LLM state: Senang")
        print("  sedih   -> LLM state: Sedih")
        print("  marah   -> LLM state: Marah")
        print("  bicara  -> TTS ON  (mulut bergerak bicara)")
        print("  henti   -> TTS OFF (kembali ke ekspresi terakhir)")
        print("  sleep   -> Ekspresi tidur")
        print("  gabut   -> Ekspresi gabut/acak")
        print("  pukpuk  -> Ekspresi diusap kepala")
        print("  quit    -> Keluar")
        print("===========================\n")
        while self.running:
            try:
                user_input = input("Masukkan perintah: ").strip().lower()
                if user_input:
                    self.input_signal.emit(user_input)
            except (EOFError, KeyboardInterrupt):
                break
        self.stop_signal.emit()


# ─────────────────────────────────────────────
#  PARTIKEL
# ─────────────────────────────────────────────
PARTICLE_POOL = {
    "happy":  ["heart", "star", "sparkle", "music", "rainbow_dot"],
    "sad":    ["tear_drop", "cloud", "rain", "sleepy"],
    "laugh":  ["star", "exclaim", "sparkle", "lol", "music"],
    "angry":  ["angry_vein", "fire", "exclaim", "skull"],
    "talk":   ["speech", "music", "sparkle", "note"],
    "sleep":  ["zzz_p", "moon", "star", "cloud"],
    "gabut":  ["sparkle", "star", "question", "speech", "music", "note",
               "exclaim", "heart", "sleepy", "cloud"],
    "standby": ["sparkle"],  # Sedikit partikel untuk standby
    "pukpuk":  ["heart", "heart", "star", "sparkle"],  # Partikel hati untuk ekspresi diusap
}

def _make_particle(w, h, expr):
    pool = PARTICLE_POOL.get(expr, PARTICLE_POOL["gabut"])
    return {
        "x":         random.randint(50, w - 50),
        "y":         h + 20,
        "type":      random.choice(pool),
        "vx":        random.uniform(-2.5, 2.5),
        "vy":        random.uniform(-4, -0.8),
        "life":      random.randint(70, 140),
        "max_life":  140,
        "size":      random.randint(16, 30),
        "rot":       random.uniform(0, 360),
        "rot_speed": random.uniform(-5, 5),
    }


# ─────────────────────────────────────────────
#  WIDGET UTAMA
# ─────────────────────────────────────────────
# Kelas utama untuk Robot Face - wajah robot animasi dengan ekspresi
class RobotFace(QWidget):
    def __init__(self):
        # Inisialisasi widget utama dengan jendela tanpa frame dan transparan
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setFixedSize(1024, 600)

        # Tombol close di kanan atas
        self.close_button = QPushButton("✕", self)
        self.close_button.setFlat(True)
        self.close_button.setStyleSheet(
            "color: rgba(255,255,255,120); font-size: 16px; background: transparent;")
        self.close_button.clicked.connect(self.close)
        self._reposition_close_button()

        # ── State dasar ekspresi dan animasi ──
        self.blink          = False  # Mata berkedip
        self.expression     = "standby"  # Ekspresi saat ini
        self.prev_expression= "standby"  # Ekspresi sebelumnya
        self.talk_open      = False  # Mulut terbuka untuk bicara
        self.manual_mode    = False  # Mode manual (dari input user)
        self.gabut_noise_counter = 0  # Counter untuk animasi gabut

        # ── State untuk integrasi LLM dan TTS ──
        self.llm_emotion    = "senang"  # Emosi dari LLM
        self.tts_active     = False     # TTS sedang aktif (Piper bicara)

        # ── Animasi background dan transisi ──
        self.bg_hue         = 0  # Hue untuk background
        self.transition_alpha = 0  # Alpha untuk transisi ekspresi

        # ── Partikel untuk efek visual ──
        w, h = self.width(), self.height()
        self.particles = [_make_particle(w, h, "happy") for _ in range(18)]

        # ── State untuk ekspresi gabut (acak) ──
        self.gabut_state = {
            "eye_x": 0, "eye_y": 0, "eye_x_target": 0, "eye_y_target": 0,
            "pupil_x": 0, "pupil_y": 0, "mouth_type": 0, "tongue_out": False,
            "wink": False, "head_tilt": 0, "head_tilt_target": 0,
            "sweat": False, "sweat_pos": 0, "cheek": False,
            "brow_l": 0, "brow_r": 0, "nose_wiggle": 0, "shake": 0,
            "blink_anim": 0, "eye_size": 1.0, "yawning": False, "yawn_timer": 0,
            "drool": False, "drool_len": 0, "freak_out": 0, "confused": 0,
        }

        # ── EcoLab Status Messages untuk Gabut State ──
        self.gabut_messages = [
            # Format: (text, expression_type, emoji)
            ("Saya ECOLAB assistant, tanya apa saja!", "happy", "🤖"),
            ("Monitoring ruangan, semua normal.", "neutral", "✓"),
            ("Panel surya bekerja dengan baik", "happy", "☀️"),
            ("Suhu ruangan: 24°C - Nyaman!", "neutral", "🌡️"),
            ("Perangkat listrik dalam keadaan aman", "neutral", "⚡"),
            ("Siap menerima perintah!", "happy", "👋"),
            ("Memantau sensor EcoLab...", "thinking", "🔍"),
            ("Energi optimal hari ini", "happy", "🔋"),
            ("Sistem berjalan normal", "neutral", "✅"),
            ("Ada yang bisa saya bantu?", "curious", "🤔"),
            ("Dashboard monitoring aktif", "neutral", "📊"),
            ("Kualitas udara: Baik", "happy", "🌿"),
            ("Menunggu instruksi baru...", "sleepy", "😴"),
            ("EcoLab siap beraksi!", "excited", "💪"),
            ("Semua sistem online", "neutral", "🟢"),
            ("Kelembaban: 65% - Ideal", "neutral", "💧"),
            ("Halo! Saya robot EcoLab", "happy", "👋"),
            ("Menganalisis data sensor...", "thinking", "📈"),
            ("Daya masuk: 450W - Stabil", "neutral", "⚡"),
            ("Siap membantu tugas apa saja!", "happy", "🙌"),
            ("EcoLab assistant v2.0", "neutral", "🔧"),
            ("Memeriksa koneksi jaringan...", "thinking", "🌐"),
            ("Jaga kebersihan lingkungan ya!", "happy", "♻️"),
            ("Hemat energi, hemat dunia!", "excited", "🌍"),
            ("Status: Siap dan stand-by", "neutral", "🔄"),
            ("Menyimpan data sensor...", "neutral", "💾"),
            ("Kapasitas baterai: 87%", "happy", "🔋"),
            ("Sensor suhu: Aktif", "neutral", "🌡️"),
            ("Sensor cahaya: Aktif", "neutral", "💡"),
            ("Sensor gerak: Aktif", "neutral", "🎯"),
        ]

        # ── State untuk pesan gabut ──
        self.gabut_message_state = {
            "current_message": None,
            "current_expression": "neutral",
            "current_emoji": "",
            "message_alpha": 0,  # Untuk fade in/out
            "message_timer": 0,
            "next_message_time": 0,
            "display_duration": 0,
        }

        # ── State untuk animasi halus ekspresi ──
        self.expr_state = {
            # Mata
            "eye_x": 0.0, "eye_y": 0.0,
            "eye_size": 1.0,
            # Alis
            "brow_l": 0.0, "brow_r": 0.0,
            "brow_angle_l": 0.0, "brow_angle_r": 0.0,
            # Pipi
            "cheek_l": 0.0, "cheek_r": 0.0,
            # Mulut
            "mouth_open": 0.0,
            # Kepala
            "head_tilt": 0.0, "head_bob": 0.0,
            # Efek
            "glow_intensity": 0.0,
            "tear": False, "tear_len": 0.0,
            "blush": 0.0,
            "pulse": 1.0,
            "wink": False, "wink_eye": 0,
            "shake": 0.0, "squish": 1.0,
            # Counter
            "time": 0,
        }

        # ── Inisialisasi timer untuk animasi ──
        self._init_timers()

        # ── Thread untuk input keyboard ──
        self.input_handler = InputHandler()
        self.input_handler.input_signal.connect(self._handle_input)
        self.input_handler.stop_signal.connect(self._cleanup)
        self._input_thread = threading.Thread(
            target=self.input_handler.listen, daemon=True)
        self._input_thread.start()

        self._schedule_blink()

    # ─────────────────────────────────────────
    def _init_timers(self):
        # Timer untuk animasi background pulse
        self.bg_timer = QTimer(self)
        self.bg_timer.timeout.connect(self._update_bg)
        self.bg_timer.start(40)

        # Timer untuk berkedip mata
        self.blink_timer = None

        # Timer ekspresi random (tidak dipakai, logika diganti flowchart)
        self.expression_timer = QTimer(self)
        self.expression_timer.timeout.connect(self._random_expression)

        # ── FLOWCHART: Timer Standby (30 detik idle -> Gabut) ──
        # Dimulai saat masuk state Standby
        self.standby_idle_timer = QTimer(self)
        self.standby_idle_timer.setSingleShot(True)
        self.standby_idle_timer.timeout.connect(self._on_standby_timeout)
        self.standby_idle_timer.start(30000)  # Mulai dari awal (state awal = Standby)

        # ── FLOWCHART: Timer Gabut (30 detik di Gabut -> Sleep) ──
        self.gabut_idle_timer = QTimer(self)
        self.gabut_idle_timer.setSingleShot(True)
        self.gabut_idle_timer.timeout.connect(self._on_gabut_timeout)

        # ── FLOWCHART: Timer Bicara (10 detik tidak bicara -> kembali ke Standby) ──
        self.bicara_idle_timer = QTimer(self)
        self.bicara_idle_timer.setSingleShot(True)
        self.bicara_idle_timer.timeout.connect(self._on_bicara_timeout)

        # Timer untuk animasi mulut bicara
        self.talk_timer = QTimer(self)
        self.talk_timer.timeout.connect(self._toggle_talk)

        # Timer untuk animasi ketawa
        self.laugh_timer = QTimer(self)
        self.laugh_timer.timeout.connect(self._toggle_laugh)

        # Timer untuk animasi ZZZ saat tidur
        self.zzz_timer = QTimer(self)
        self.zzz_timer.timeout.connect(self._update_zzz)
        self.zzz_offset  = 0
        self.zzz_visible = True

        # Timer untuk animasi gabut (animasi acak visual)
        self.gabut_timer = QTimer(self)
        self.gabut_timer.timeout.connect(self._update_gabut)

        # Timer untuk update state animasi halus semua ekspresi
        self.expr_timer = QTimer(self)
        self.expr_timer.timeout.connect(self._update_expression_state)
        self.expr_timer.start(30)

        # Timer untuk animasi partikel
        self.particle_timer = QTimer(self)
        self.particle_timer.timeout.connect(self._update_particles)
        self.particle_timer.start(30)

    # ─────────────────────────────────────────
    #  FLOWCHART: Callback timer idle
    # ─────────────────────────────────────────
    def _on_standby_timeout(self):
        """Flowchart: Timer standby > 30 detik -> pindah ke Gabut (B)."""
        if self.expression == "standby":
            print("[AUTO] Standby timeout -> masuk state Gabut")
            self._switch_expression("gabut")
            self.gabut_idle_timer.start(30000)

    def _on_gabut_timeout(self):
        """Flowchart: Timer gabut > 30 detik -> mengantuk 10 detik -> sleep."""
        if self.expression == "gabut":
            print("[AUTO] Gabut timeout -> mengantuk sebentar -> Sleep")
            # Tampilkan state mengantuk (pakai ekspresi sleep dengan eyes setengah)
            # lalu langsung sleep setelah 10 detik
            self._switch_expression("sleep")
            QTimer.singleShot(10000, lambda: self._go_deep_sleep())

    def _go_deep_sleep(self):
        """Flowchart: Selesai setelah sleep (program tidak tutup, tetap sleep sampai voka)."""
        # State tetap sleep; program menunggu wake word 'voka'
        print("[AUTO] Masuk deep sleep. Ketik 'voka' untuk bangun.")

    def _on_bicara_timeout(self):
        """Flowchart: 10 detik tidak ada aktivitas bicara -> kembali ke Standby."""
        if self.tts_active:
            self.bicara_idle_timer.start(10000)
            return
        # Reset llm_emotion lalu ke Standby
        print("[AUTO] Bicara timeout -> reset LLM state -> kembali ke Standby")
        self.llm_emotion = "senang"  # reset ke default
        self._go_to_standby()

    # ─────────────────────────────────────────
    def _stop_all_expr_timers(self):
        self.talk_timer.stop()
        self.laugh_timer.stop()
        self.zzz_timer.stop()
        self.gabut_timer.stop()
        self.expression_timer.stop()

    def _stop_all_idle_timers(self):
        """Stop semua timer idle flowchart."""
        self.standby_idle_timer.stop()
        self.gabut_idle_timer.stop()
        self.bicara_idle_timer.stop()

    def _go_to_standby(self):
        """Kembali ke Standby dan mulai timer standby 30 detik."""
        self._stop_all_idle_timers()
        self._switch_expression("standby")
        self.standby_idle_timer.start(30000)
        print("[STATE] -> Standby (timer 30 detik dimulai)")

    # ─────────────────────────────────────────
    def _update_bg(self):
        self.bg_hue = (self.bg_hue + 1) % 360
        if self.transition_alpha < 255:
            self.transition_alpha = min(255, self.transition_alpha + 12)
        self.update()

    # ─────────────────────────────────────────
    def _update_particles(self):
        w, h = self.width(), self.height()
        expr = self.expression
        for p in self.particles:
            p["x"]   += p["vx"]
            p["y"]   += p["vy"]
            p["rot"] += p["rot_speed"]
            p["life"] -= 1
            if p["life"] <= 0 or p["y"] < -60 or p["x"] < -60 or p["x"] > w + 60:
                p.update(_make_particle(w, h, expr))
        self.update()

    # ─────────────────────────────────────────
    def _update_expression_state(self):
        es = self.expr_state
        r  = random.random
        es["time"] = (es["time"] + 1) % 10000

        # ── mata goyang halus ──
        if self.manual_mode:
            es["eye_x"] *= 0.85
            es["eye_y"] *= 0.85
        else:
            if r() < 0.08:
                es["eye_x"] += random.uniform(-4, 4)
                es["eye_y"] += random.uniform(-3, 3)
            es["eye_x"] *= 0.88
            es["eye_y"] *= 0.88

        # ── ukuran mata ── (sama untuk kiri dan kanan)
        if self.manual_mode:
            es["eye_size"] += (1.0 - es["eye_size"]) * 0.12
        else:
            if r() < 0.025:
                es["eye_size"] = random.uniform(0.85, 1.15)
            es["eye_size"] += (1.0 - es["eye_size"]) * 0.12

        # ── alis ──
        if r() < 0.04:
            es["brow_l"] = random.uniform(-10, 10)
            es["brow_r"] = random.uniform(-10, 10)
            es["brow_angle_l"] = random.uniform(-25, 25)
            es["brow_angle_r"] = random.uniform(-25, 25)

        # ── pipi blushing ──
        if r() < 0.04:
            es["cheek_l"] = random.uniform(0, 1)
            es["cheek_r"] = random.uniform(0, 1)
        es["cheek_l"] += (0 - es["cheek_l"]) * 0.04
        es["cheek_r"] += (0 - es["cheek_r"]) * 0.04

        # ── tilt kepala ──
        fixed_head = self.expression in ("happy", "sad", "angry", "sleep", "standby", "pukpuk")
        if fixed_head or self.manual_mode:
            es["head_tilt"] *= 0.85  # smooth ke 0
        else:
            if r() < 0.03:
                es["head_tilt"] = random.uniform(-8, 8)
            es["head_tilt"] *= 0.93

        # ── bob kepala ──
        if fixed_head or self.manual_mode:
            es["head_bob"] = 0
        else:
            es["head_bob"] = math.sin(es["time"] * 0.08) * 2.5

        # ── glow ──
        if r() < 0.03:
            es["glow_intensity"] = random.uniform(0.3, 1.0)
        es["glow_intensity"] *= 0.96

        # ── pulse ──
        es["pulse"] = 1.0 + math.sin(es["time"] * 0.12) * 0.03

        # ── shake ringan ──
        if fixed_head or self.manual_mode:
            es["shake"] *= 0.85
        else:
            if r() < 0.03:
                es["shake"] = random.uniform(-2.5, 2.5)
            es["shake"] *= 0.88

        # ── squish ──
        if fixed_head or self.manual_mode:
            es["squish"] += (1.0 - es["squish"]) * 0.15
        else:
            if r() < 0.02:
                es["squish"] = random.uniform(0.93, 1.07)
            es["squish"] += (1.0 - es["squish"]) * 0.1

        # ── wink kadang ──
        if not self.manual_mode:
            if r() < 0.015:
                es["wink"]     = not es["wink"]
                es["wink_eye"] = random.randint(0, 1)
        else:
            es["wink"] = False

        # ── blush ──
        if r() < 0.025:
            es["blush"] = random.uniform(0, 1)
        es["blush"] *= 0.96

        # ── air mata ──
        if r() < 0.02:
            es["tear"] = not es["tear"]
        if es["tear"]:
            es["tear_len"] = min(70, es["tear_len"] + 2.5)
        else:
            es["tear_len"] = max(0, es["tear_len"] - 3)

        # ── mouth open ──
        if r() < 0.03:
            es["mouth_open"] = random.uniform(0, 1)
        es["mouth_open"] *= 0.9

    # ═══════════════════════════════════════════════════
    #  PUBLIC API UNTUK INTEGRASI LLM & TTS
    # ═══════════════════════════════════════════════════
    # Mapping emosi dari LLM ke ekspresi internal
    LLM_EXPR_MAP = {
        "senang": "happy", "happy": "happy", "joy": "happy", "excited": "happy",
        "sedih": "sad", "sad": "sad", "sadness": "sad", "crying": "sad",
        "marah": "angry", "angry": "angry", "anger": "angry", "furious": "angry",
        "ketawa": "laugh", "laugh": "laugh", "laughing": "laugh", "funny": "laugh",
        "bicara": "talk", "talk": "talk", "speaking": "talk",
        "tidur": "sleep", "sleep": "sleep", "sleepy": "sleep",
        "gabut": "gabut", "bored": "gabut", "idle": "gabut",
        "netral": "happy", "neutral": "happy",
        "bingung": "gabut", "confused": "gabut",
        "takut": "sad", "fear": "sad", "scared": "sad",
        "jijik": "angry", "disgust": "angry",
    }

    def set_llm_state(self, emotion: str):
        # Set emosi dari LLM (Qwen), menerima kata seperti senang, sedih, marah, dll
        emotion_lower = emotion.lower().strip()
        
        if emotion_lower not in self.LLM_EXPR_MAP:
            print(f"Warning: emotion '{emotion}' tidak valid. Menggunakan 'netral'.")
            emotion_lower = "netral"
        
        self.manual_mode = True
        self.expression_timer.stop()
        self.llm_emotion = emotion_lower
        
        expr = self.LLM_EXPR_MAP[emotion_lower]
        self._switch_expression(expr)
        print(f"[OK] LLM State: {emotion} -> Expression: {expr}")

    def set_emotion(self, emotion: str):
        # Alias untuk set_llm_state() untuk kompatibilitas
        self.set_llm_state(emotion)

    def set_tts_active(self, active: bool):
        """Flowchart TTS ON/OFF:
        TTS ON  -> state 'bicara', mulut bergerak, Timer Bicara ON
        TTS OFF -> mulut berhenti, Timer Bicara OFF, cek state 'henti',
                   lalu kembali ke Standby (A) setelah mulut berhenti bergerak.
        """
        self.tts_active = active
        if active:
            # ── TTS ON: masuk state Bicara, mulut gerak ──
            self._stop_all_idle_timers()
            # Pastikan ekspresi sesuai emosi LLM yang sedang aktif
            llm_expr = self.LLM_EXPR_MAP.get(self.llm_emotion, "happy")
            if self.expression not in [llm_expr]:
                self._switch_expression(llm_expr)
            if not self.talk_timer.isActive():
                self.talk_open = False
                self.talk_timer.start(140)
            # Timer Bicara ON: mulai countdown 10 detik tidak bicara
            self.bicara_idle_timer.start(10000)
        else:
            # ── TTS OFF: mulut berhenti, Timer Bicara OFF ──
            if self.talk_timer.isActive():
                self.talk_timer.stop()
                self.talk_open = False
            self.bicara_idle_timer.stop()
            # Jika ada LLM emotion aktif (senang/sedih/marah), kembali ke ekspresi itu
            llm_emotions = {"senang", "sedih", "marah"}
            if self.llm_emotion in llm_emotions:
                llm_expr = self.LLM_EXPR_MAP.get(self.llm_emotion, "happy")
                self._stop_all_idle_timers()
                self._switch_expression(llm_expr)
                print(f"[STATE] TTS OFF -> Henti -> kembali ke ekspresi '{llm_expr}' ({self.llm_emotion})")
                # Timer bicara: jika 10 detik tidak ada aktivitas, baru ke Standby
                self.bicara_idle_timer.start(10000)
            else:
                # Tidak ada LLM state aktif -> kembali ke Standby
                print("[STATE] TTS OFF -> Henti -> kembali ke Standby")
                self._go_to_standby()
        print(f"[OK] TTS: {'ON (Bicara)' if active else 'OFF (Henti)'}")
        self.update()

    def get_tts_active(self) -> bool:
        # Return status TTS saat ini
        return self.tts_active

    def get_current_expression(self) -> str:
        # Return nama ekspresi saat ini
        return self.expression

    def get_current_emotion(self) -> str:
        # Return emosi LLM saat ini
        return self.llm_emotion

    def start_talking(self):
        # Mulai animasi mulut (untuk integrasi dengan Whisper STT)
        self.set_tts_active(True)

    def stop_talking(self):
        # Hentikan animasi mulut
        self.set_tts_active(False)

    # ─────────────────────────────────────────
    def _handle_input(self, command):
        """
        Flowchart input handler:
        - 'voka'          : INTERRUPT STATE - dari state apapun (termasuk sleep/gabut/bicara),
                            langsung masuk Standby, reset semua timer ke 0
        - 'senang'        : Set LLM state Senang
        - 'sedih'         : Set LLM state Sedih
        - 'marah'         : Set LLM state Marah
        - 'bicara'        : TTS ON -> mulut gerak, ekspresi sesuai state LLM
        - 'henti'/'stop'  : TTS OFF -> mulut berhenti -> kembali Standby
        - 'quit'/'exit'   : Keluar (selesai)
        """

        # ── INTERRUPT STATE: 'voka' dari state manapun ──────────────────
        if command == "voka":
            print("[INTERRUPT] Wake word 'voka' terdeteksi! -> Standby (semua timer reset)")
            self._stop_all_expr_timers()
            self._stop_all_idle_timers()
            self.tts_active = False
            self.talk_open = False
            self._switch_expression("standby")
            self.standby_idle_timer.start(30000)
            return

        # ── LLM STATES: Senang / Sedih / Marah ──────────────────────────
        llm_state_map = {
            "senang": "senang",
            "sedih":  "sedih",
            "marah":  "marah",
        }

        if command in llm_state_map:
            emotion = llm_state_map[command]
            self.llm_emotion = emotion
            expr = self.LLM_EXPR_MAP[emotion]
            # Hanya ubah ekspresi visual, jangan masuk bicara dulu
            # Jika sedang bicara, langsung terapkan; jika standby, terapkan dan tunggu TTS
            self._stop_all_idle_timers()
            self._switch_expression(expr)
            print(f"[STATE] LLM State: {emotion} -> Ekspresi: {expr}")
            # Mulai timer bicara: jika 10 detik tidak ada TTS ON, kembali standby
            self.bicara_idle_timer.start(10000)
            return

        # ── TTS ON: bicara ───────────────────────────────────────────────
        if command in ("bicara", "talk", "berbicara"):
            self.set_tts_active(True)
            return

        # ── TTS OFF: henti / stop ────────────────────────────────────────
        if command in ("henti", "berhenti", "stop", "diam", "quiet"):
            self.set_tts_active(False)
            return

        # ── PUPUK: ekspresi diusap kepala ──────────────────────────────
        if command in ("pukpuk", "patpat", "peluk"):
            self._stop_all_idle_timers()
            self._switch_expression("pukpuk")
            print("[OK] Pukpuk: Mata memejam senang")
            return

        # ── Sleep / Tidur ───────────────────────────────────────────────
        if command in ("sleep", "tidur"):
            self._stop_all_idle_timers()
            self._switch_expression("sleep")
            print("[OK] Tidur...")
            return

        # ── Gabut / Bosen ───────────────────────────────────────────────
        if command in ("gabut", "bosen", "bored"):
            self._stop_all_idle_timers()
            self._switch_expression("gabut")
            print("[OK] Gabut: ekspresi acak...")
            return

        # ── Keluar ───────────────────────────────────────────────────────
        if command in ("quit", "exit"):
            print("Keluar...")
            self.close()
            QApplication.quit()
            return

        print(f"Perintah tidak dikenal: '{command}'")
        print("Gunakan: voka | senang | sedih | marah | bicara | henti | sleep | gabut | pukpuk | quit")

    def _switch_expression(self, new_expr):
        # Ganti ekspresi wajah, stop semua timer ekspresi lama, reset state
        self._stop_all_expr_timers()
        self.prev_expression = self.expression
        self.expression      = new_expr
        self.transition_alpha = 0
        self._reset_expr_state()

        # Refresh partikel sesuai ekspresi baru
        w, h = self.width(), self.height()
        self.particles = [_make_particle(w, h, new_expr) for _ in range(18)]

        if new_expr == "talk":
            self.talk_open = False
            self.talk_timer.start(140)
            QTimer.singleShot(2000, self._stop_talk)
        elif new_expr == "laugh":
            self.talk_open = False
            self.laugh_timer.start(90)
            QTimer.singleShot(3000, self._stop_laugh_auto)
        elif new_expr == "sleep":
            self.zzz_offset  = 0
            self.zzz_visible = True
            self.zzz_timer.start(80)
        elif new_expr == "gabut":
            self._reset_gabut_state()
            self.gabut_timer.start(28)

        elif new_expr == "pukpuk":
            # Mata memejam selama 3 detik, lalu happy, lalu 10 detik lagi standby
            QTimer.singleShot(3000, lambda: [
                self._switch_expression("happy"),
                self.bicara_idle_timer.start(10000)
            ])

        self.update()

    def _reset_expr_state(self):
        es = self.expr_state
        for k in es:
            if isinstance(es[k], bool):
                es[k] = False
            elif isinstance(es[k], float):
                es[k] = 1.0 if k in ("eye_size", "pulse", "squish") else 0.0
            elif isinstance(es[k], int):
                es[k] = 0

    # ─────────────────────────────────────────
    def _schedule_blink(self):
        QTimer.singleShot(random.randint(1800, 4800), self._do_blink)

    def _do_blink(self):
        if self.expression in ("sleep", "gabut"):
            self._schedule_blink(); return
        self.blink = True
        self.update()
        QTimer.singleShot(110, self._end_blink)

    def _end_blink(self):
        self.blink = False
        self.update()
        self._schedule_blink()

    # ─────────────────────────────────────────
    def _random_expression(self):
        self._switch_expression(random.choice(["happy", "sad", "angry", "talk", "laugh"]))

    def _toggle_talk(self):
        self.talk_open = not self.talk_open
        self.update()

    def _stop_talk(self):
        self.talk_timer.stop()
        self.talk_open = False
        self.update()

    def _toggle_laugh(self):
        self.talk_open = not self.talk_open
        self.update()

    def _stop_laugh_auto(self):
        self.laugh_timer.stop()
        self.talk_open = False
        self.update()

    def _update_zzz(self):
        self.zzz_offset = (self.zzz_offset + 2) % 40
        self.zzz_visible = True
        self.update()

    # ─────────────────────────────────────────
    def _reset_gabut_state(self):
        s = self.gabut_state
        for k, v in s.items():
            if isinstance(v, bool):  s[k] = False
            elif isinstance(v, float): s[k] = 1.0 if "size" in k else 0.0
            elif isinstance(v, int):   s[k] = 0
        s["yawning"] = False
        s["yawn_timer"] = 0

        # Reset dan mulai pesan gabut
        self._reset_gabut_message_state()

    # ─────────────────────────────────────────
    def _reset_gabut_message_state(self):
        """Reset state pesan gabut dan jadwalkan pesan pertama"""
        ms = self.gabut_message_state
        ms["current_message"] = None
        ms["current_expression"] = "neutral"
        ms["current_emoji"] = ""
        ms["message_alpha"] = 0
        ms["message_timer"] = 0
        # Random waktu tunggu sebelum pesan pertama (3-8 detik)
        import random
        ms["next_message_time"] = random.randint(100, 280)
        ms["display_duration"] = 0

    # ─────────────────────────────────────────
    def _update_gabut_messages(self):
        """Update pesan EcoLab saat state gabut"""
        ms = self.gabut_message_state
        ms["message_timer"] += 1

        # Cek saatnya untuk menampilkan pesan baru
        if ms["message_timer"] >= ms["next_message_time"] and ms["current_message"] is None:
            # Pilih pesan random
            import random
            msg_data = random.choice(self.gabut_messages)
            ms["current_message"] = msg_data[0]
            ms["current_expression"] = msg_data[1]
            ms["current_emoji"] = msg_data[2]
            ms["display_duration"] = random.randint(180, 300)  # 6-10 detik (60fps)
            ms["message_alpha"] = 0
            ms["next_message_time"] = 0

            # Update ekspresi sesuai jenis pesan
            expr_mapping = {
                "neutral": "standby",
                "happy": "happy",
                "thinking": "gabut",  # Tetap gabut tapi dengan ekspresi thinking
                "curious": "gabut",
                "excited": "happy",
                "sleepy": "sleep"
            }
            # Untuk thinking/curious, kita tetap di gabut tapi ubah gaya animasi

        # Update fade in/out
        if ms["current_message"] is not None:
            if ms["message_alpha"] < 255:
                # Fade in
                ms["message_alpha"] = min(255, ms["message_alpha"] + 8)

            ms["display_duration"] -= 1
            if ms["display_duration"] <= 0:
                # Mulai fade out
                ms["message_alpha"] -= 8
                if ms["message_alpha"] <= 0:
                    # Pesan selesai, reset
                    ms["current_message"] = None
                    ms["current_emoji"] = ""
                    # Jadwalkan pesan berikutnya (4-10 detik)
                    import random
                    ms["next_message_time"] = random.randint(240, 600)
                    ms["message_timer"] = 0

    def _update_gabut(self):
        # Update pesan EcoLab
        self._update_gabut_messages()

        s = self.gabut_state
        self.gabut_noise_counter += 1

        # ── STATE GABUT: 3 Mode yang berbeda ────────────────────────────────
        # 0 = SAYU (mata sayu, sedih, tenang)
        # 1 = MENGANTUK (mata hampir tertutup, head tilt)
        # 2 = MENGUAP (mulut terbuka lebar, mata tertutup)

        if "gabut_mode" not in s:
            s["gabut_mode"] = 0
            s["gabut_mode_timer"] = 0

        s["gabut_mode_timer"] += 1

        # Ganti mode setiap 8-12 detik (28ms per tick * ~300-400 ticks)
        if s["gabut_mode_timer"] > random.randint(280, 430):
            s["gabut_mode"] = (s["gabut_mode"] + 1) % 3
            s["gabut_mode_timer"] = 0
            # Reset state saat ganti mode
            s["yawning"] = False
            s["eye_size"] = 1.0
            s["mouth_type"] = 0

        mode = s["gabut_mode"]

        # ── MODE 0: SAYU (tenang, sedih, mata sayu) ─────────────────────────
        if mode == 0:
            # Mata sayu (sedikit lebih kecil)
            target_eye_size = 0.88
            s["eye_size"] += (target_eye_size - s["eye_size"]) * 0.08

            # Mulut sedikit turun (sedih)
            s["mouth_type"] = 2

            # Head sedikit miring ke samping - SMOOTH, tidak sering berubah
            if "tilt_target" not in s:
                s["tilt_target"] = 0
            if random.random() < 0.005:  # Sangat jarang berubah
                s["tilt_target"] = random.uniform(-5, 5)  # Dikurangi dari 8 ke 5
            s["head_tilt"] += (s["tilt_target"] - s["head_tilt"]) * 0.03  # Lebih lambat

            # Alis sedikit naik (ekspresi sedih)
            s["brow_l"] = -8
            s["brow_r"] = -8

            # Pupil bergerak lambat dan tenang
            if random.random() < 0.03:
                s["pupil_x"] = random.uniform(-3, 3)
                s["pupil_y"] = random.uniform(-2, 2)
            s["pupil_x"] *= 0.92
            s["pupil_y"] *= 0.92

            # Kadang-kadang berkedip lama
            if random.random() < 0.008:
                s["blink_anim"] = 20

        # ── MODE 1: MENGANTUK (mata hampir tertutup, mengantuk banget) ────────
        elif mode == 1:
            # Mata hampir tertutup (mengantuk)
            target_eye_size = 0.55
            s["eye_size"] += (target_eye_size - s["eye_size"]) * 0.06

            # Mulut kecil (ngantuk)
            s["mouth_type"] = 0

            # Head tilt yang smooth - TIDAK SERING berubah
            # Hanya update target tilt jarang sekali
            if "tilt_target" not in s:
                s["tilt_target"] = 0
            if random.random() < 0.005:  # Sangat jarang (0.5% per frame)
                s["tilt_target"] = random.uniform(-10, 10)  # Dikurangi dari 15 ke 10
            s["head_tilt"] += (s["tilt_target"] - s["head_tilt"]) * 0.02  # Lebih lambat

            # Alis turun (mengantuk)
            s["brow_l"] = 5
            s["brow_r"] = 5

            # Pupil hampir tidak bergerak (lemas)
            s["pupil_x"] *= 0.95
            s["pupil_y"] *= 0.95

            # Blink sering dan lama (mengantuk = kelopatan mata berat)
            if random.random() < 0.03:
                s["blink_anim"] = 25

            # NO SHAKE - smooth saja, tidak ada mengangguk
            s["shake"] = 0

        # ── MODE 2: MENGUAP (mulut terbuka lebar, mata tertutup) ────────────────
        elif mode == 2:
            # Yawning state
            if not s.get("yawning", False):
                s["yawning"] = True
                s["yawn_timer"] = 0
                s["yawn_phase"] = 0  # 0=mulai, 1=peak, 2=selesai

            s["yawn_timer"] += 1

            # Phase menguap
            yawn_phase = s.get("yawn_phase", 0)
            yawn_progress = min(1.0, s["yawn_timer"] / 180.0)  # 5 detik untuk menguap

            if yawn_progress < 0.3:
                # MULAI: Mata mulai menutup
                s["eye_size"] = 1.0 - (yawn_progress / 0.3) * 0.5
                s["mouth_type"] = 0
            elif yawn_progress < 0.7:
                # PEAK: Mata tertutup total, mulut terbuka lebar
                s["eye_size"] = 0.5
                s["mouth_type"] = 9
                s["yawn_phase"] = 1
            else:
                # SELESAI: Mata mulai terbuka lagi
                open_progress = (yawn_progress - 0.7) / 0.3
                s["eye_size"] = 0.5 + open_progress * 0.5
                s["mouth_type"] = 9 if open_progress < 0.5 else 0
                s["yawn_phase"] = 2

            # Head sedikit backwards saat menguap
            s["head_tilt"] = 0

            # Alis naik (saat menguap)
            s["brow_l"] = -12
            s["brow_r"] = -12

            # Pupil diam total saat menguap
            s["pupil_x"] *= 0.98
            s["pupil_y"] *= 0.98

            # Selesaikan yawning setelah 5 detik
            if s["yawn_timer"] > 180:
                s["yawning"] = False
                s["yawn_phase"] = 0
                s["gabut_mode_timer"] = 0  # Reset untuk ganti mode

        # ── Common updates untuk semua mode ───────────────────────────────────
        # Smooth eye movement - LEBIH LAMBAT biar tidak getar
        if random.random() < 0.02 and mode != 2:  # Dikurangi dari 0.05 ke 0.02
            s["eye_x_target"] = random.uniform(-15, 15)  # Dikurangi dari 20 ke 15
            s["eye_y_target"] = random.uniform(-10, 10)  # Dikurangi dari 12 ke 10
        s["eye_x"] += (s["eye_x_target"] - s["eye_x"]) * 0.08  # Dikurangi dari 0.12 ke 0.08
        s["eye_y"] += (s["eye_y_target"] - s["eye_y"]) * 0.08  # Dikurangi dari 0.12 ke 0.08

        # NO SHAKE/NOSE WIGGLE untuk state gabut - smooth saja!
        s["shake"] = 0
        s["nose_wiggle"] = 0

        # Sweat drop (kadang-kadang saat sayu/mengantuk)
        if mode in [0, 1] and random.random() < 0.02:  # Dikurangi dari 0.04 ke 0.02
            s["sweat"] = not s["sweat"]
        if random.random() < 0.01:  # Dikurangi dari 0.03 ke 0.01
            s["sweat_pos"] = random.randint(0, 3)

        # Cheek blush (kadang-kadang)
        if random.random() < 0.01:  # Dikurangi dari 0.03 ke 0.01
            s["cheek"] = not s["cheek"]

        # Drool (saat mengantuk banget)
        if mode == 1 and random.random() < 0.01:  # Dikurangi dari 0.02 ke 0.01
            s["drool"] = not s["drool"]
        if s.get("drool", False):
            s["drool_len"] = min(40, s.get("drool_len", 0) + 1)
        else:
            s["drool_len"] = max(0, s.get("drool_len", 0) - 2)

        # Blink animation
        s["blink_anim"] = max(0, s.get("blink_anim", 0) - 1)

        self.update()

    # ─────────────────────────────────────────
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_close_button()

    def _reposition_close_button(self):
        self.close_button.setGeometry(self.width() - 36, 8, 28, 28)

    # ═════════════════════════════════════════
    #  PAINT - Fungsi utama untuk menggambar wajah
    # ═════════════════════════════════════════
    def paintEvent(self, event):
        # Event paint utama, gambar semua elemen wajah
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        expr  = self.expression
        cols  = EXPR_COLORS.get(expr, EXPR_COLORS["happy"])
        es    = self.expr_state
        s     = self.gabut_state

        # ── Background gradient sesuai ekspresi ──────────────────────────────────
        if expr == "gabut":
            # Background gradient yang smooth dan elegan untuk gabut
            # Menggunakan warna biru-ungu yang lembut dengan shifting halus
            shift = math.sin(es["time"] * 0.02) * 0.5 + 0.5  # 0-1 smooth oscillation

            # Warna base: deep blue ke soft purple
            r1, g1, b1 = 25, 15, 45
            r2, g2, b2 = 40, 30, 70

            # Smooth color shifting
            r1_shift = int(r1 + 10 * shift)
            g1_shift = int(g1 + 15 * shift)
            b1_shift = int(b1 + 20 * shift)
            r2_shift = int(r2 + 15 * shift)
            g2_shift = int(g2 + 20 * shift)
            b2_shift = int(b2 + 25 * shift)

            bg1 = QColor(r1_shift, g1_shift, b1_shift)
            bg2 = QColor(r2_shift, g2_shift, b2_shift)
        else:
            bg_base = cols["bg"]
            pulse   = 0.5 + 0.5 * math.sin(es["time"] * 0.05)
            lighter = bg_base.lighter(int(100 + 15 * pulse))
            bg1, bg2 = bg_base, lighter

        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, bg1)
        grad.setColorAt(1, bg2)
        painter.fillRect(self.rect(), grad)

        # ── Glow lingkaran tengah ─────────────────────────────────────
        glow_col = cols["glow"]
        glow_rad = QRadialGradient(w / 2, h / 2, w * 0.45)
        alpha_g  = int(40 + 30 * math.sin(es["time"] * 0.07))
        glow_col_a = QColor(glow_col.red(), glow_col.green(), glow_col.blue(), alpha_g)
        glow_rad.setColorAt(0, glow_col_a)
        glow_rad.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), glow_rad)

        # ── Partikel efek ─────────────────────────────────────────────────
        for p in self.particles:
            alpha = min(255, int(p["life"] / p["max_life"] * 255))
            self._draw_particle(painter, p["x"], p["y"],
                                p["type"], p["size"], p["rot"], alpha)

        # ── Transformasi kepala (shake, tilt, squish) ─────────────────────────────────────────
        painter.save()
        cx, cy = w / 2, h / 2

        if expr == "gabut":
            shake_x = 0  # NO SHAKE untuk gabut - smooth!
            shake_y = 0  # NO SHAKE untuk gabut - smooth!
            tilt    = s["head_tilt"]
        else:
            shake_x = es["shake"]
            shake_y = es["head_bob"]
            tilt    = es["head_tilt"]

        painter.translate(cx + shake_x, cy + shake_y)
        painter.rotate(tilt)
        sc = es["squish"] if expr != "gabut" else 1.0
        painter.scale(sc, 2.0 - sc)  # Squish vertikal
        painter.translate(-cx, -cy)

        # ── Dimensi mata dan mulut ──────────────────────────────────────
        eye_w   = w // 6
        eye_h   = h // 4
        ey      = h // 3 - eye_h // 2
        left_x  = w // 4 - eye_w // 2
        right_x = 3 * w // 4 - eye_w // 2
        radius  = eye_h // 5

        mouth_w = w // 4
        mouth_h = h // 8
        mouth_x = w // 2 - mouth_w // 2
        mouth_y = h * 2 // 3 - 10

        # ── Warna mata dan mulut ────────────────────────────────────────────────
        eye_col   = cols["eye"]
        mouth_col = cols["mouth"]

        if expr == "gabut":
            # Eye color yang smooth dan elegan, bukan rainbow
            shift = math.sin(es["time"] * 0.03) * 0.5 + 0.5
            r = int(180 + 40 * shift)
            g = int(220 + 35 * shift)
            b = 255
            eye_col = QColor(r, g, b)

        # ── Glow di belakang mata ─────────────────────────────────────
        self._draw_eye_glow(painter, left_x,  ey, eye_w, eye_h, eye_col, es)
        self._draw_eye_glow(painter, right_x, ey, eye_w, eye_h, eye_col, es)

        # ── Gambar mata ───────────────────────────────────────────────
        eye_off_x = s["eye_x"] if expr == "gabut" else es["eye_x"]
        eye_off_y = s["eye_y"] if expr == "gabut" else es["eye_y"]
        eye_sz = s["eye_size"] if expr == "gabut" else es["eye_size"]

        self._draw_eyes(painter, expr, s, es,
                        left_x, right_x, ey, eye_w, eye_h,
                        radius, eye_col,
                        eye_off_x, eye_off_y, eye_sz)

        # ── Alis ───────────────────────────────────────────────────────
        self._draw_eyebrows(painter, expr, s, es,
                            left_x, right_x, ey, eye_w, eye_h, mouth_col)

        # ── Pipi / blush ──────────────────────────────────────────────
        self._draw_cheeks(painter, expr, s, es,
                          left_x, right_x, ey, eye_w, eye_h)

        # ── Mulut ─────────────────────────────────────────────────────
        self._draw_mouth(painter, expr, s, es,
                         mouth_x, mouth_y, mouth_w, mouth_h, mouth_col, w)

        # ── Air mata (sedih) ──────────────────────────────────────────
        if expr == "sad" and es["tear_len"] > 0:
            self._draw_tears(painter, left_x, right_x, ey, eye_w, eye_h, es)

        # ── Sweat drop (gabut) ────────────────────────────────────────
        if expr == "gabut" and s["sweat"]:
            self._draw_sweat(painter, s, left_x, right_x, ey, eye_w)

        painter.restore()

        # ── ZZZ (sleep) ───────────────────────────────────────────────
        if expr == "sleep":
            self._draw_zzz(painter, w, h)

        # ── Efek kilat (angry) ────────────────────────────────────────
        if expr == "angry":
            self._draw_angry_fx(painter, w, h, es)

        # ── Sparkle (happy / laugh) ───────────────────────────────────
        if expr in ("happy", "laugh"):
            self._draw_sparkles(painter, w, h, es)

        # ── EcoLab Status Messages (gabut) ───────────────────────────────
        if expr == "gabut":
            # Elegant background effects untuk gabut
            self._draw_gabut_bg_effects(painter, w, h, es)
            self._draw_gabut_message(painter, w, h)

    # ─────────────────────────────────────────
    def _draw_eye_glow(self, painter, ex, ey, ew, eh, col, es):
        gx = ex + ew / 2
        gy = ey + eh / 2
        r  = max(ew, eh) * 0.9
        g  = QRadialGradient(gx, gy, r)
        a  = int(60 + 40 * math.sin(es["time"] * 0.1))
        g.setColorAt(0, QColor(col.red(), col.green(), col.blue(), a))
        g.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(g)
        painter.drawEllipse(QRectF(gx - r, gy - r, r * 2, r * 2))

    # ─────────────────────────────────────────
    def _draw_eyes(self, painter, expr, s, es,
                   left_x, right_x, ey, eye_w, eye_h, radius,
                   eye_col, ox, oy, eye_sz):
        w = self.width()
        t = es["time"]

        def eye_rect_l():
            return QRectF(left_x + ox, ey + oy,
                          eye_w * eye_sz, eye_h * eye_sz)

        def eye_rect_r():
            return QRectF(right_x + ox, ey + oy,
                          eye_w * eye_sz, eye_h * eye_sz)

        # ── SLEEP: Mata tertutup lengkap dengan efek ──
        if expr == "sleep":
            self._draw_sleep_eyes(painter, left_x, right_x, ey, eye_w, eye_h, eye_col, t)
            return

        # ── LAUGH: Mata tertawa (happy arc) ──
        if expr == "laugh":
            self._draw_laugh_eyes(painter, left_x, right_x, ey, eye_w, eye_h, eye_col, ox, oy, t)
            return

        # ── PUKPUK: Mata senyum (diusap) ──
        if expr == "pukpuk":
            self._draw_happy_closed_eyes(painter, left_x, right_x, ey, eye_w, eye_h, eye_col, ox, oy, t)
            return

        # ── BLINK: Berkedip ──
        if self.blink or (expr == "gabut" and s["blink_anim"] > 0):
            self._draw_blink_eyes(painter, left_x, right_x, ey, eye_w, eye_h, eye_col, ox, oy)
            return

        # ── EYES UTAMA dengan berbagai gaya ekspresi ──
        if expr == "sad":
            self._draw_sad_eyes(painter, left_x, right_x, ey, eye_w, eye_h, radius, eye_col, ox, oy, eye_sz, s, es)
        elif expr == "angry":
            self._draw_angry_eyes(painter, left_x, right_x, ey, eye_w, eye_h, radius, eye_col, ox, oy, eye_sz, s, es, t)
        elif expr == "happy":
            self._draw_happy_eyes(painter, left_x, right_x, ey, eye_w, eye_h, radius, eye_col, ox, oy, eye_sz, s, es, t)
        elif expr == "talk":
            self._draw_talk_eyes(painter, left_x, right_x, ey, eye_w, eye_h, radius, eye_col, ox, oy, eye_sz, s, es, t)
        elif expr == "gabut":
            self._draw_gabut_eyes(painter, left_x, right_x, ey, eye_w, eye_h, radius, eye_col, ox, oy, eye_sz, s, es, t)
        elif expr == "standby":
            self._draw_standby_eyes(painter, left_x, right_x, ey, eye_w, eye_h, radius, eye_col, ox, oy, eye_sz, s, es, t)
        else:
            self._draw_normal_eyes(painter, left_x, right_x, ey, eye_w, eye_h, radius, eye_col, ox, oy, eye_sz, s, es)

    # ─────────────────────────────────────────
    #  HELPER FUNCTIONS UNTUK SETIAP EKSPRESI MATA
    # ─────────────────────────────────────────

    def _draw_sleep_eyes(self, painter, left_x, right_x, ey, eye_w, eye_h, eye_col, t):
        """Mata tidur - SAMA dengan gabut saat menguap (garis lurus tertutup)"""
        # Sama persis dengan gabut mode menguap - mata tertutup total
        for bx in (left_x, right_x):
            painter.setPen(Qt.NoPen)

            # Gradient untuk mata tidur
            gradient = QRadialGradient(bx + eye_w/2, ey + eye_h/2, eye_w * 0.6)
            gradient.setColorAt(0, QColor(140, 170, 200, 200))
            gradient.setColorAt(0.7, eye_col)
            gradient.setColorAt(1, QColor(60, 100, 150, 150))

            painter.setBrush(QBrush(gradient))

            # Bentuk mata tertutup total (garis lurus) - SAMA dengan gabut menguap
            pts = [
                QPointF(bx + eye_w * 0.20, ey + eye_h * 0.50),
                QPointF(bx + eye_w * 0.80, ey + eye_h * 0.50),
                QPointF(bx + eye_w * 0.80, ey + eye_h * 0.52),
                QPointF(bx + eye_w * 0.20, ey + eye_h * 0.52),
            ]

            painter.drawPolygon(QPolygonF(pts))

            # Soft glow (redup seperti saat menguap)
            glow_gradient = QRadialGradient(bx + eye_w/2, ey + eye_h/2, eye_w * 0.8)
            glow_gradient.setColorAt(0, QColor(150, 200, 255, 15))
            glow_gradient.setColorAt(1, QColor(150, 200, 255, 0))
            painter.setBrush(QBrush(glow_gradient))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(
                int(bx - eye_w * 0.1),
                int(ey - eye_h * 0.1),
                int(eye_w * 1.2),
                int(eye_h * 1.3)
            )

    def _draw_laugh_eyes(self, painter, left_x, right_x, ey, eye_w, eye_h, eye_col, ox, oy, t):
        """Mata tertawa dengan arc bahagia dan efek berkilau"""
        pen = QPen(eye_col)
        pen.setWidth(max(5, eye_w // 12))
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        # Animasi mata tertawa
        bounce = int(5 * math.sin(t * 0.2))

        for bx in (left_x, right_x):
            cy = ey + eye_h // 2 + oy + bounce
            # Arc bahagia yang lebih tebal
            painter.drawArc(int(bx + ox + eye_w // 6), int(cy - eye_h // 6),
                           eye_w * 2 // 3, eye_h // 2.5, 0, 180 * 16)

        # Sparkle kecil di mata kiri
        sparkle_alpha = int(150 + 100 * math.sin(t * 0.15))
        painter.setBrush(QBrush(QColor(255, 255, 200, sparkle_alpha)))
        painter.setPen(Qt.NoPen)
        sx = left_x + ox + eye_w // 6
        sy = ey + eye_h // 2 + oy + bounce - eye_h // 4
        painter.drawEllipse(int(sx), int(sy), 6, 6)

    def _draw_happy_closed_eyes(self, painter, left_x, right_x, ey, eye_w, eye_h, eye_col, ox, oy, t):
        """Mata senyum untuk ekspresi pukpuk"""
        pen = QPen(eye_col)
        pen.setWidth(max(4, eye_w // 15))
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        # Kurva senyum lembut
        for bx in (left_x, right_x):
            cy = ey + eye_h // 2 + oy
            painter.drawArc(int(bx + ox + eye_w // 6), int(cy - eye_h // 8),
                           eye_w * 2 // 3, eye_h // 3, 0, 180 * 16)

    def _draw_blink_eyes(self, painter, left_x, right_x, ey, eye_w, eye_h, eye_col, ox, oy):
        """Mata berkedip"""
        painter.setBrush(QBrush(eye_col))
        painter.setPen(Qt.NoPen)
        th = max(5, eye_h // 6)
        painter.drawRoundedRect(int(left_x + ox),  int(ey + oy + eye_h // 2 - th // 2), eye_w, th, th // 2, th // 2)
        painter.drawRoundedRect(int(right_x + ox), int(ey + oy + eye_h // 2 - th // 2), eye_w, th, th // 2, th // 2)

    def _draw_sad_eyes(self, painter, left_x, right_x, ey, eye_w, eye_h, radius, eye_col, ox, oy, eye_sz, s, es):
        """Mata sedih dengan bentuk tetesan air mata"""
        t = es["time"]

        # Bentuk mata sedih (sedikit miring ke bawah di luar)
        for bx in (left_x, right_x):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(eye_col))

            # Mata dengan sudut lebih bulat di atas, lebih runcing di bawah
            pts = [
                QPointF(bx + ox + eye_w * 0.1, ey + oy + eye_h * 0.3),
                QPointF(bx + ox + eye_w * 0.9, ey + oy + eye_h * 0.3),
                QPointF(bx + ox + eye_w * 0.95, ey + oy + eye_h * 0.7),
                QPointF(bx + ox + eye_w * 0.5, ey + oy + eye_h * 0.85),
                QPointF(bx + ox + eye_w * 0.05, ey + oy + eye_h * 0.7),
            ]
            painter.drawPolygon(QPolygonF(pts))

        # Pupil dengan posisi sedikit lebih ke atas (melihat ke atas)
        pupil_size = eye_h // 5
        pupil_offset_y = -eye_h // 10

        painter.setBrush(QBrush(QColor(0, 0, 0)))
        for bx in (left_x, right_x):
            painter.drawEllipse(
                int(bx + eye_w // 2 + ox - pupil_size // 2),
                int(ey + eye_h // 2 + oy + pupil_offset_y - pupil_size // 2),
                pupil_size, pupil_size)

        # Highlight tunggal yang lebih kecil (mata sedih kurang berkilau)
        painter.setBrush(QBrush(QColor(255, 255, 255, 150)))
        hs = max(3, pupil_size // 3)
        for bx in (left_x, right_x):
            painter.drawEllipse(
                int(bx + eye_w // 2 + ox - pupil_size // 2 + pupil_size // 3),
                int(ey + eye_h // 2 + oy + pupil_offset_y - pupil_size // 2),
                hs, hs)

    def _draw_angry_eyes(self, painter, left_x, right_x, ey, eye_w, eye_h, radius, eye_col, ox, oy, eye_sz, s, es, t):
        """Mata marah dengan efek intens dan glow merah"""
        # Glow merah di belakang mata
        glow_alpha = int(40 + 20 * math.sin(t * 0.1))
        glow = QColor(255, 50, 50, glow_alpha)

        for bx in (left_x, right_x):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(
                int(bx + ox - eye_w // 4),
                int(ey + oy - eye_h // 4),
                int(eye_w * 1.5), int(eye_h * 1.5))

        # Mata dengan sudut lebih tajam
        for bx in (left_x, right_x):
            painter.setBrush(QBrush(eye_col))
            painter.setPen(Qt.NoPen)

            # Bentuk mata marah (lebih runcing)
            pts = [
                QPointF(bx + ox + eye_w * 0.15, ey + oy + eye_h * 0.25),
                QPointF(bx + ox + eye_w * 0.85, ey + oy + eye_h * 0.25),
                QPointF(bx + ox + eye_w * 0.92, ey + oy + eye_h * 0.6),
                QPointF(bx + ox + eye_w * 0.5, ey + oy + eye_h * 0.75),
                QPointF(bx + ox + eye_w * 0.08, ey + oy + eye_h * 0.6),
            ]
            painter.drawPolygon(QPolygonF(pts))

        # Pupil lebih kecil dan tajam
        pupil_size = eye_h // 6

        # Pupil bergetar sedikit (efek marah)
        shake = int(2 * math.sin(t * 0.3))

        painter.setBrush(QBrush(QColor(0, 0, 0)))
        for bx in (left_x, right_x):
            px = bx + eye_w // 2 + ox - pupil_size // 2 + shake
            py = ey + eye_h // 2 + oy - pupil_size // 2
            painter.drawEllipse(int(px), int(py), pupil_size, pupil_size)

        # Highlight tajam
        painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
        hs = max(4, pupil_size // 2)
        for bx in (left_x, right_x):
            painter.drawEllipse(
                int(bx + eye_w // 2 + ox - pupil_size // 2 + pupil_size // 4),
                int(ey + eye_h // 2 + oy - pupil_size // 2 - 2),
                hs, hs)

        # Vein marah di pelipis
        vein_alpha = int(100 + 50 * math.sin(t * 0.15))
        vein_col = QColor(255, 80, 80, vein_alpha)
        painter.setPen(QPen(vein_col, max(2, eye_w // 30)))
        painter.setBrush(Qt.NoBrush)

        # Cross veins
        for bx in (left_x, right_x):
            vx = bx + ox + eye_w + 5
            vy = ey + oy + eye_h // 3
            # Tanda + marah
            painter.drawLine(int(vx), int(vy - 8), int(vx), int(vy + 8))
            painter.drawLine(int(vx - 8), int(vy), int(vx + 8), int(vy))

    def _draw_happy_eyes(self, painter, left_x, right_x, ey, eye_w, eye_h, radius, eye_col, ox, oy, eye_sz, s, es, t):
        """Mata bahagia dengan iris bercahaya dan bintang"""
        # Mata dasar dengan sedikit rotasi upward
        for bx in (left_x, right_x):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(eye_col))

            # Bentuk mata happy (lebih bulat)
            pts = [
                QPointF(bx + ox + eye_w * 0.1, ey + oy + eye_h * 0.35),
                QPointF(bx + ox + eye_w * 0.9, ey + oy + eye_h * 0.35),
                QPointF(bx + ox + eye_w * 0.88, ey + oy + eye_h * 0.65),
                QPointF(bx + ox + eye_w * 0.5, ey + oy + eye_h * 0.75),
                QPointF(bx + ox + eye_w * 0.12, ey + oy + eye_h * 0.65),
            ]
            painter.drawPolygon(QPolygonF(pts))

        # Iris dengan gradient berwarna-warni
        iris_size = eye_h // 3
        hue_shift = int(t * 2) % 360

        for bx in (left_x, right_x):
            # Radial gradient untuk iris
            iris_grad = QRadialGradient(
                bx + eye_w // 2 + ox,
                ey + eye_h // 2 + oy,
                iris_size
            )
            iris_grad.setColorAt(0, QColor(255, 255, 200))
            iris_grad.setColorAt(0.5, QColor.fromHsv((hue_shift + 45) % 360, 180, 255))
            iris_grad.setColorAt(1, QColor.fromHsv((hue_shift + 30) % 360, 200, 200))

            painter.setBrush(QBrush(iris_grad))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(
                int(bx + eye_w // 2 + ox - iris_size // 2),
                int(ey + eye_h // 2 + oy - iris_size // 2),
                iris_size, iris_size)

        # Pupil hitam
        pupil_size = iris_size // 2
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        for bx in (left_x, right_x):
            painter.drawEllipse(
                int(bx + eye_w // 2 + ox - pupil_size // 2),
                int(ey + eye_h // 2 + oy - pupil_size // 2),
                pupil_size, pupil_size)

        # Multiple highlights (3 highlight untuk efek berkilau)
        highlight_sizes = [(pupil_size // 2, -pupil_size // 4, -pupil_size // 4),
                          (pupil_size // 3, pupil_size // 3, -pupil_size // 3),
                          (pupil_size // 4, -pupil_size // 6, pupil_size // 4)]

        for hs, hox, hoy in highlight_sizes:
            alpha = int(200 - hs * 2)
            painter.setBrush(QBrush(QColor(255, 255, 255, alpha)))
            painter.setPen(Qt.NoPen)
            for bx in (left_x, right_x):
                painter.drawEllipse(
                    int(bx + eye_w // 2 + ox + hox - hs // 2),
                    int(ey + eye_h // 2 + oy + hoy - hs // 2),
                    hs, hs)

        # Bintang kecil di mata (sparkle)
        star_alpha = int(180 + 70 * math.sin(t * 0.15))
        star_col = QColor(255, 255, 180, star_alpha)
        painter.setBrush(QBrush(star_col))
        painter.setPen(Qt.NoPen)

        star_size = pupil_size // 2
        for bx in (left_x, right_x):
            # Bintang 4 titik
            cx = bx + eye_w // 2 + ox
            cy = ey + eye_h // 2 + oy - pupil_size // 3
            self._draw_star_shape(painter, cx, cy, star_size, star_size // 2)

    def _draw_talk_eyes(self, painter, left_x, right_x, ey, eye_w, eye_h, radius, eye_col, ox, oy, eye_sz, s, es, t):
        """Mata bicara dengan animasi fokus dan ekspresi"""
        # Pupil movement untuk bicara (melihat berbicara)
        pupil_offset_x = int(3 * math.sin(t * 0.2))

        for bx in (left_x, right_x):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(eye_col))

            # Bentuk mata fokus (sedikit lebih oval)
            pts = [
                QPointF(bx + ox + eye_w * 0.12, ey + oy + eye_h * 0.3),
                QPointF(bx + ox + eye_w * 0.88, ey + oy + eye_h * 0.3),
                QPointF(bx + ox + eye_w * 0.9, ey + oy + eye_h * 0.65),
                QPointF(bx + ox + eye_w * 0.5, ey + oy + eye_h * 0.72),
                QPointF(bx + ox + eye_w * 0.1, ey + oy + eye_h * 0.65),
            ]
            painter.drawPolygon(QPolygonF(pts))

        # Iris dengan gradient biru-hijau (fokus)
        iris_size = eye_h // 3.5

        for bx in (left_x, right_x):
            iris_grad = QRadialGradient(
                bx + eye_w // 2 + ox + pupil_offset_x,
                ey + eye_h // 2 + oy,
                iris_size
            )
            iris_grad.setColorAt(0, QColor(200, 255, 255))
            iris_grad.setColorAt(0.6, QColor(100, 200, 255))
            iris_grad.setColorAt(1, QColor(80, 150, 220))

            painter.setBrush(QBrush(iris_grad))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(
                int(bx + eye_w // 2 + ox - iris_size // 2),
                int(ey + eye_h // 2 + oy - iris_size // 2),
                iris_size, iris_size)

        # Pupil yang bergerak
        pupil_size = iris_size // 2
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        for bx in (left_x, right_x):
            px = bx + eye_w // 2 + ox + pupil_offset_x - pupil_size // 2
            py = ey + eye_h // 2 + oy - pupil_size // 2
            painter.drawEllipse(int(px), int(py), pupil_size, pupil_size)

        # Highlights
        painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
        hs = max(3, pupil_size // 2)
        for bx in (left_x, right_x):
            painter.drawEllipse(
                int(bx + eye_w // 2 + ox + pupil_offset_x - pupil_size // 2 + pupil_size // 3),
                int(ey + eye_h // 2 + oy - pupil_size // 2),
                hs, hs)

    def _draw_gabut_eyes(self, painter, left_x, right_x, ey, eye_w, eye_h, radius, eye_col, ox, oy, eye_sz, s, es, t):
        """Mata gabut dengan 3 mode: SAYU, MENGANTUK, MENGUAP"""
        # Dapatkan mode gabut
        mode = s.get("gabut_mode", 0)

        # Breathing animation (lebih subtle saat mengantuk)
        breath_intensity = 0.05 if mode == 0 else (0.03 if mode == 1 else 0.02)
        breath = 1.0 + breath_intensity * math.sin(t * 0.06)

        # Floating motion (lebih lambat saat mengantuk)
        float_speed = 0.04 if mode == 0 else (0.02 if mode == 1 else 0.01)
        float_y = 3 * math.sin(t * float_speed)

        # Sway (lebih sedikit saat mengantuk)
        sway = 2 * math.sin(t * 0.03 + 1)
        if mode == 1:
            sway *= 0.5  # Lebih stabil saat mengantuk
        elif mode == 2:
            sway = 0  # Diam saat menguap

        # Eye size dari state
        eye_scale = s.get("eye_size", 1.0)

        for bx in (left_x, right_x):
            painter.setPen(Qt.NoPen)

            # Gradient untuk mata - warna berubah sesuai mode
            if mode == 0:  # SAYU - sedih
                gradient = QRadialGradient(bx + eye_w/2 + sway, ey + eye_h/2 + float_y, eye_w * 0.6)
                gradient.setColorAt(0, QColor(180, 210, 240, 230))
                gradient.setColorAt(0.7, eye_col)
                gradient.setColorAt(1, QColor(100, 140, 190, 180))
            elif mode == 1:  # MENGANTUK - lemas
                gradient = QRadialGradient(bx + eye_w/2 + sway, ey + eye_h/2 + float_y, eye_w * 0.6)
                gradient.setColorAt(0, QColor(160, 190, 220, 210))
                gradient.setColorAt(0.7, eye_col)
                gradient.setColorAt(1, QColor(80, 120, 170, 160))
            else:  # MENGUAP - tertutup
                gradient = QRadialGradient(bx + eye_w/2 + sway, ey + eye_h/2 + float_y, eye_w * 0.6)
                gradient.setColorAt(0, QColor(140, 170, 200, 200))
                gradient.setColorAt(0.7, eye_col)
                gradient.setColorAt(1, QColor(60, 100, 150, 150))

            painter.setBrush(QBrush(gradient))

            # Bentuk mata berubah sesuai mode dan eye_scale
            scaled_ew = eye_w * eye_scale
            scaled_eh = eye_h * eye_scale * breath

            if mode == 0:  # SAYU - mata agak menyipit sedih
                pts = [
                    QPointF(bx + sway + eye_w * 0.15, ey + float_y + scaled_eh * 0.32),
                    QPointF(bx + sway + eye_w * 0.85, ey + float_y + scaled_eh * 0.32),
                    QPointF(bx + sway + eye_w * 0.88, ey + float_y + scaled_eh * 0.60),
                    QPointF(bx + sway + eye_w * 0.50, ey + float_y + scaled_eh * 0.70),
                    QPointF(bx + sway + eye_w * 0.12, ey + float_y + scaled_eh * 0.60),
                ]
            elif mode == 1:  # MENGANTUK - mata sangat kecil dan hampir tertutup
                pts = [
                    QPointF(bx + sway + eye_w * 0.25, ey + float_y + scaled_eh * 0.40),
                    QPointF(bx + sway + eye_w * 0.75, ey + float_y + scaled_eh * 0.40),
                    QPointF(bx + sway + eye_w * 0.78, ey + float_y + scaled_eh * 0.55),
                    QPointF(bx + sway + eye_w * 0.50, ey + float_y + scaled_eh * 0.60),
                    QPointF(bx + sway + eye_w * 0.22, ey + float_y + scaled_eh * 0.55),
                ]
            else:  # MENGUAP - mata tertutup total (garis)
                pts = [
                    QPointF(bx + sway + eye_w * 0.20, ey + float_y + scaled_eh * 0.50),
                    QPointF(bx + sway + eye_w * 0.80, ey + float_y + scaled_eh * 0.50),
                    QPointF(bx + sway + eye_w * 0.80, ey + float_y + scaled_eh * 0.52),
                    QPointF(bx + sway + eye_w * 0.20, ey + float_y + scaled_eh * 0.52),
                ]

            painter.drawPolygon(QPolygonF(pts))

            # Soft glow (lebih redup saat mengantuk/menguap)
            glow_alpha = 40 if mode == 0 else (25 if mode == 1 else 15)
            glow_gradient = QRadialGradient(bx + eye_w/2 + sway, ey + eye_h/2 + float_y, eye_w * 0.8)
            glow_gradient.setColorAt(0, QColor(150, 200, 255, glow_alpha))
            glow_gradient.setColorAt(1, QColor(150, 200, 255, 0))
            painter.setBrush(QBrush(glow_gradient))
            painter.drawEllipse(
                int(bx + sway - eye_w * 0.1),
                int(ey + float_y - eye_h * 0.1),
                int(eye_w * 1.2),
                int(eye_h * 1.3)
            )

        # Pupil - HANYA saat tidak menguap (mode 0 dan 1)
        if mode != 2:
            pupil_size = int((eye_h // 4.5) * breath * eye_scale)

            # Pupil movement berbeda tiap mode
            if mode == 0:  # SAYU - pupil bergerak tenang
                pupil_offset_x = 4 * math.sin(t * 0.05)
                pupil_offset_y = 2 * math.cos(t * 0.07)
            else:  # MENGANTUK - pupil hampir diam
                pupil_offset_x = 1 * math.sin(t * 0.03)
                pupil_offset_y = 0.5 * math.cos(t * 0.04)

            # Tambahkan offset dari state
            pupil_offset_x += s.get("pupil_x", 0)
            pupil_offset_y += s.get("pupil_y", 0)

            # Pupil gradient
            pupil_gradient = QRadialGradient(0, 0, pupil_size)
            if mode == 0:
                pupil_gradient.setColorAt(0, QColor(180, 210, 255))
                pupil_gradient.setColorAt(0.6, QColor(120, 170, 220))
                pupil_gradient.setColorAt(1, QColor(80, 130, 180))
            else:
                pupil_gradient.setColorAt(0, QColor(160, 190, 230))
                pupil_gradient.setColorAt(0.6, QColor(100, 150, 200))
                pupil_gradient.setColorAt(1, QColor(60, 110, 160))

            painter.setBrush(QBrush(pupil_gradient))
            for bx in (left_x, right_x):
                cx = bx + eye_w // 2 + sway + pupil_offset_x
                cy = ey + eye_h // 2 + float_y + pupil_offset_y
                painter.drawEllipse(
                    int(cx - pupil_size // 2),
                    int(cy - pupil_size // 2),
                    pupil_size, pupil_size)

            # Inner pupil
            inner_size = pupil_size // 2
            painter.setBrush(QBrush(QColor(40, 80, 130)))
            for bx in (left_x, right_x):
                cx = bx + eye_w // 2 + sway + pupil_offset_x
                cy = ey + eye_h // 2 + float_y + pupil_offset_y
                painter.drawEllipse(
                    int(cx - inner_size // 2),
                    int(cy - inner_size // 2),
                    inner_size, inner_size)

            # Highlight
            highlight_alpha = int(180 + 75 * math.sin(t * 0.08))
            painter.setBrush(QBrush(QColor(255, 255, 255, highlight_alpha)))
            hs = max(4, inner_size // 2)
            highlight_offset_x = 2 * math.sin(t * 0.06)
            highlight_offset_y = 2 * math.cos(t * 0.06)

            for bx in (left_x, right_x):
                cx = bx + eye_w // 2 + sway + pupil_offset_x - inner_size // 3 + highlight_offset_x
                cy = ey + eye_h // 2 + float_y + pupil_offset_y - inner_size // 3 + highlight_offset_y
                painter.drawEllipse(int(cx), int(cy), hs, hs)

            # Secondary highlight
            painter.setBrush(QBrush(QColor(200, 230, 255, int(highlight_alpha * 0.5))))
            hs2 = hs // 2
            for bx in (left_x, right_x):
                cx = bx + eye_w // 2 + sway + pupil_offset_x + inner_size // 4 + highlight_offset_x * 0.5
                cy = ey + eye_h // 2 + float_y + pupil_offset_y + inner_size // 4 + highlight_offset_y * 0.5
                painter.drawEllipse(int(cx), int(cy), hs2, hs2)

        # Sweat drop (mode SAYU dan MENGANTUK)
        if mode in [0, 1] and s.get("sweat", False):
            sweat_pos = s.get("sweat_pos", 0)
            sweat_x = right_x + eye_w * 0.3
            sweat_y = ey - eye_h * 0.2 + sweat_pos * 10

            # Gambar sweat drop
            sweat_gradient = QRadialGradient(sweat_x, sweat_y, 15)
            sweat_gradient.setColorAt(0, QColor(150, 200, 255, 200))
            sweat_gradient.setColorAt(1, QColor(150, 200, 255, 0))
            painter.setBrush(QBrush(sweat_gradient))
            painter.setPen(Qt.NoPen)

            # Bentuk air mata
            sweat_pts = [
                QPointF(sweat_x, sweat_y - 12),
                QPointF(sweat_x + 8, sweat_y),
                QPointF(sweat_x + 5, sweat_y + 10),
                QPointF(sweat_x - 5, sweat_y + 10),
                QPointF(sweat_x - 8, sweat_y),
            ]
            painter.drawPolygon(QPolygonF(sweat_pts))

    def _draw_standby_eyes(self, painter, left_x, right_x, ey, eye_w, eye_h, radius, eye_col, ox, oy, eye_sz, s, es, t):
        """Mata standby dengan breathing effect dan lembut"""
        # Breathing animation untuk mata
        breath = 1.0 + 0.03 * math.sin(t * 0.08)

        for bx in (left_x, right_x):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(eye_col))

            # Bentuk mata standby (tenang dan bulat)
            pts = [
                QPointF(bx + ox + eye_w * 0.1, ey + oy + eye_h * 0.32 * breath),
                QPointF(bx + ox + eye_w * 0.9, ey + oy + eye_h * 0.32 * breath),
                QPointF(bx + ox + eye_w * 0.88, ey + oy + eye_h * 0.65 * breath),
                QPointF(bx + ox + eye_w * 0.5, ey + oy + eye_h * 0.74 * breath),
                QPointF(bx + ox + eye_w * 0.12, ey + oy + eye_h * 0.65 * breath),
            ]
            painter.drawPolygon(QPolygonF(pts))

        # Iris dengan lembut
        iris_size = int(eye_h // 3.5 * breath)

        for bx in (left_x, right_x):
            iris_grad = QRadialGradient(
                bx + eye_w // 2 + ox,
                ey + eye_h // 2 + oy,
                iris_size
            )
            iris_grad.setColorAt(0, QColor(220, 220, 230))
            iris_grad.setColorAt(0.7, QColor(180, 180, 200))
            iris_grad.setColorAt(1, QColor(150, 150, 170))

            painter.setBrush(QBrush(iris_grad))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(
                int(bx + eye_w // 2 + ox - iris_size // 2),
                int(ey + eye_h // 2 + oy - iris_size // 2),
                iris_size, iris_size)

        # Pupil tenang
        pupil_size = iris_size // 2

        # Pupil sedikit bergerak (looking around)
        look_x = int(2 * math.sin(t * 0.05))
        look_y = int(1.5 * math.cos(t * 0.07))

        painter.setBrush(QBrush(QColor(0, 0, 0)))
        for bx in (left_x, right_x):
            painter.drawEllipse(
                int(bx + eye_w // 2 + ox + look_x - pupil_size // 2),
                int(ey + eye_h // 2 + oy + look_y - pupil_size // 2),
                pupil_size, pupil_size)

        # Highlight lembut
        painter.setBrush(QBrush(QColor(255, 255, 255, 180)))
        hs = max(3, pupil_size // 2)
        for bx in (left_x, right_x):
            painter.drawEllipse(
                int(bx + eye_w // 2 + ox + look_x - pupil_size // 2 + pupil_size // 3),
                int(ey + eye_h // 2 + oy + look_y - pupil_size // 2),
                hs, hs)

        # Highlight kedua lebih kecil
        painter.setBrush(QBrush(QColor(255, 255, 255, 120)))
        hs2 = max(2, pupil_size // 3)
        for bx in (left_x, right_x):
            painter.drawEllipse(
                int(bx + eye_w // 2 + ox + look_x - pupil_size // 2 - pupil_size // 4),
                int(ey + eye_h // 2 + oy + look_y + pupil_size // 4),
                hs2, hs2)

    def _draw_normal_eyes(self, painter, left_x, right_x, ey, eye_w, eye_h, radius, eye_col, ox, oy, eye_sz, s, es):
        """Mata normal (fallback)"""
        w = self.width()

        def eye_rect_l():
            return QRectF(left_x + ox, ey + oy,
                          eye_w * eye_sz, eye_h * eye_sz)

        def eye_rect_r():
            return QRectF(right_x + ox, ey + oy,
                          eye_w * eye_sz, eye_h * eye_sz)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(eye_col))
        painter.drawRoundedRect(eye_rect_l(), radius, radius)
        painter.drawRoundedRect(eye_rect_r(), radius, radius)

        # pupil (default position)
        puc = QColor(0, 0, 0)
        ps = eye_h // 4
        px, py = ox, oy

        painter.setBrush(QBrush(puc))
        for bx in (left_x, right_x):
            painter.drawEllipse(
                int(bx + eye_w // 2 + px - ps // 2),
                int(ey + eye_h // 2 + py - ps // 2),
                ps, ps)

        # specular highlight
        painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
        hs = max(4, ps // 2)
        for bx in (left_x, right_x):
            painter.drawEllipse(
                int(bx + eye_w // 2 + px - ps // 2 + ps // 4),
                int(ey + eye_h // 2 + py - ps // 2),
                hs, hs)

    def _draw_spiral(self, painter, cx, cy, radius, turns):
        """Gambar spiral untuk efek pusing"""
        points = []
        steps = turns * 20
        for i in range(steps):
            angle = i * 0.3
            r = radius * (i / steps)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            points.append(QPointF(x, y))

        if len(points) > 1:
            painter.drawPolyline(QPolygonF(points))

    # ─────────────────────────────────────────
    def _draw_eyebrows(self, painter, expr, s, es,
                       left_x, right_x, ey, eye_w, eye_h, col):
        w = self.width()
        pen = QPen(col)
        pen.setWidth(max(3, w // 80))
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        brow_y = ey - eye_h // 5

        if expr == "gabut":
            bl, br = s["brow_l"], s["brow_r"]
        else:
            bl, br = es["brow_l"], es["brow_r"]

        if expr == "angry":
            # alis melengkung sedih (inner corners raised)
            painter.drawLine(int(left_x + bl),          int(brow_y - 8),
                             int(left_x + eye_w + bl),  int(brow_y + 10))
            painter.drawLine(int(right_x + br),         int(brow_y + 10),
                             int(right_x + eye_w + br), int(brow_y - 8))
        elif expr == "sad":
            # alis miring garang
            painter.drawLine(int(left_x + bl),          int(brow_y + 12),
                             int(left_x + eye_w + bl),  int(brow_y - 8))
            painter.drawLine(int(right_x + br),         int(brow_y - 8),
                             int(right_x + eye_w + br), int(brow_y + 12))
        else:
            # alis default / happy - normal horizontal
            painter.drawLine(int(left_x + bl),          int(brow_y),
                             int(left_x + eye_w + bl),  int(brow_y))
            painter.drawLine(int(right_x + br),         int(brow_y),
                             int(right_x + eye_w + br), int(brow_y))

    # ─────────────────────────────────────────
    def _draw_cheeks(self, painter, expr, s, es,
                     left_x, right_x, ey, eye_w, eye_h):
        if expr in ("happy", "laugh", "talk", "pukpuk") or \
           (expr == "gabut" and s["cheek"]) or \
           es["cheek_l"] > 0.1:
            if expr == "gabut":
                cl, cr = (1, 1) if s["cheek"] else (0, 0)
            else:
                base_blush = 0.5 if expr == "pukpuk" else 0.15
                cl = max(es["cheek_l"], base_blush if expr in ("happy","laugh","talk","pukpuk") else 0)
                cr = max(es["cheek_r"], base_blush if expr in ("happy","laugh","talk","pukpuk") else 0)

            cw = eye_w * 2 // 3
            ch = eye_h // 3
            cy = ey + eye_h + 5
            lx = left_x - cw // 3
            rx = right_x + eye_w - cw * 2 // 3

            for x, intensity in ((lx, cl), (rx, cr)):
                if intensity > 0.05:
                    a = int(intensity * 90)
                    painter.setBrush(QBrush(QColor(255, 110, 110, a)))
                    painter.setPen(Qt.NoPen)
                    painter.drawEllipse(int(x), int(cy), cw, ch)

    # ─────────────────────────────────────────
    def _draw_mouth(self, painter, expr, s, es,
                    mx, my, mw, mh, col, w):
        # Gambar mulut sesuai ekspresi atau TTS
        pen = QPen(col)
        pen.setWidth(max(4, w // 28))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        if self.tts_active:
            # Jika TTS aktif, gunakan animasi mulut bicara (talk style)
            if self.talk_open:
                painter.setBrush(QBrush(col))
                painter.drawRoundedRect(int(mx + mw // 10), int(my),
                                        mw - mw // 5, mh, 14, 14)
            else:
                painter.drawArc(int(mx), int(my), mw, mh, 200 * 16, 140 * 16)
        else:
            # Jika tidak TTS, gambar mulut sesuai ekspresi normal
            if expr == "happy":
                painter.drawArc(int(mx), int(my), mw, mh, 200 * 16, 140 * 16)
                painter.setBrush(QBrush(col))
                tooth_w = mw // 6
                for i in range(3):
                    tx = mx + mw // 5 + i * (mw * 2 // 7)
                    painter.drawRoundedRect(int(tx), int(my + mh * 2 // 5), tooth_w, mh // 4, 3, 3)

            elif expr == "sad":
                pen2 = QPen(col)
                pen2.setWidth(max(4, w // 28))
                pen2.setCapStyle(Qt.RoundCap)
                painter.setPen(pen2)
                zig_y = my + mh // 2
                pts = []
                n = 6
                for i in range(n + 1):
                    x = mx + int(mw * i / n)
                    y = zig_y + ((-1) ** i) * (mh // 5)
                    pts.append(QPointF(x, y))
                painter.drawPolyline(QPolygonF(pts))

            elif expr == "pukpuk":
                # Mulut senang seperti happy, tapi dengan blushing ekstra untuk efek diusap kepala
                painter.drawArc(int(mx), int(my), mw, mh, 200 * 16, 140 * 16)
                painter.setBrush(QBrush(col))
                tooth_w = mw // 6
                for i in range(3):
                    tx = mx + mw // 5 + i * (mw * 2 // 7)
                    painter.drawRoundedRect(int(tx), int(my + mh * 2 // 5), tooth_w, mh // 4, 3, 3)

            elif expr == "standby":
                # Mulut datar untuk standby
                painter.drawLine(int(mx + mw // 5), int(my + mh // 2), int(mx + mw * 4 // 5), int(my + mh // 2))

            elif expr == "angry":
                # Mulut marah: busur melengkung ke bawah
                painter.drawArc(int(mx), int(my + 20), mw, mh, 20 * 16, 140 * 16)

            elif expr == "talk":
                if self.talk_open:
                    painter.setBrush(QBrush(col))
                    painter.drawRoundedRect(int(mx + mw // 10), int(my),
                                            mw - mw // 5, mh, 14, 14)
                else:
                    painter.drawArc(int(mx), int(my), mw, mh, 200 * 16, 140 * 16)

            elif expr == "laugh":
                if self.talk_open:
                    painter.setBrush(QBrush(col))
                    painter.drawRoundedRect(int(mx), int(my - mh // 5),
                                            mw, mh + mh // 2, 20, 20)
                    painter.setBrush(QBrush(QColor(255, 120, 150)))
                    painter.setPen(Qt.NoPen)
                    tongue_w = mw // 2
                    tongue_h = mh // 2
                    painter.drawEllipse(int(mx + mw // 2 - tongue_w // 2),
                                        int(my + mh * 3 // 4),
                                        tongue_w, tongue_h)
                else:
                    painter.drawArc(int(mx), int(my), mw, mh, 200 * 16, 140 * 16)

            elif expr == "sleep":
                # Mulut tidur - SAMA dengan gabut mode mengantuk (sangat kecil)
                # Gradient untuk mulut tidur
                gradient = QLinearGradient(mx, my, mx + mw, my + mh)
                gradient.setColorAt(0, QColor(140, 180, 220))
                gradient.setColorAt(0.5, QColor(110, 160, 210))
                gradient.setColorAt(1, QColor(80, 140, 200))

                painter.setBrush(QBrush(gradient))
                painter.setPen(Qt.NoPen)

                # Mulut sangat kecil - SAMA persis dengan gabut mengantuk
                actual_mw = mw * 0.4
                actual_mh = mh * 0.2
                offset_x = (mw - actual_mw) / 2
                offset_y = (mh - actual_mh) / 2 + mh * 0.4

                # Tiny oval dengan rounded corners
                painter.drawRoundedRect(
                    int(mx + offset_x),
                    int(my + offset_y),
                    int(actual_mw),
                    int(actual_mh),
                    10, 10
                )

                # Soft glow di sekitar mulut tidur
                glow_gradient = QRadialGradient(mx + mw/2, my + mh/2, mw * 0.7)
                glow_gradient.setColorAt(0, QColor(150, 200, 255, 25))
                glow_gradient.setColorAt(1, QColor(150, 200, 255, 0))
                painter.setBrush(QBrush(glow_gradient))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(
                    int(mx - mw * 0.1),
                    int(my - mh * 0.2),
                    int(mw * 1.2),
                    int(mh * 1.5)
                )

            elif expr == "gabut":
                self._draw_gabut_mouth(painter, s, mx, my, mw, mh, col, w)

    # ─────────────────────────────────────────
    def _draw_gabut_mouth(self, painter, s, mx, my, mw, mh, col, w):
        """Mulut gabut dengan 3 mode: SAYU, MENGANTUK, MENGUAP"""
        import time
        t = time.time() * 1000

        # Dapatkan mode gabut
        mode = s.get("gabut_mode", 0)
        mouth_type = s.get("mouth_type", 0)

        # Breathing animation (berbeda tiap mode)
        if mode == 0:  # SAYU
            breath = 1.0 + 0.06 * math.sin(t * 0.005)
        elif mode == 1:  # MENGANTUK
            breath = 1.0 + 0.03 * math.sin(t * 0.004)
        else:  # MENGUAP
            # Yawning animation
            yawn_phase = s.get("yawn_phase", 0)
            if yawn_phase == 0:  # Mulai menguap
                breath = 1.0
            elif yawn_phase == 1:  # Peak menguap
                breath = 1.35  # Tidak terlalu besar, realistic
            else:  # Selesai menguap
                breath = 1.0

        # Gradient untuk mulut - warna berubah sesuai mode
        if mode == 0:  # SAYU - sedih
            gradient = QLinearGradient(mx, my, mx + mw, my + mh)
            gradient.setColorAt(0, QColor(150, 190, 230))
            gradient.setColorAt(0.5, QColor(120, 170, 220))
            gradient.setColorAt(1, QColor(90, 150, 210))
        elif mode == 1:  # MENGANTUK - lemas
            gradient = QLinearGradient(mx, my, mx + mw, my + mh)
            gradient.setColorAt(0, QColor(140, 180, 220))
            gradient.setColorAt(0.5, QColor(110, 160, 210))
            gradient.setColorAt(1, QColor(80, 140, 200))
        else:  # MENGUAP - terbuka lebar
            gradient = QLinearGradient(mx, my, mx + mw, my + mh)
            gradient.setColorAt(0, QColor(170, 210, 250))
            gradient.setColorAt(0.5, QColor(140, 190, 240))
            gradient.setColorAt(1, QColor(110, 170, 230))

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)

        # Bentuk mulut berbeda tiap mode
        if mode == 0:  # SAYU - mulut kecil sedih (garis lurus atau sedikit turun)
            actual_mw = mw * 0.7
            actual_mh = mh * 0.3 * breath
            offset_x = (mw - actual_mw) / 2
            offset_y = (mh - actual_mh) / 2 + mh * 0.35

            # Small rounded rectangle
            painter.drawRoundedRect(
                int(mx + offset_x),
                int(my + offset_y),
                int(actual_mw),
                int(actual_mh),
                15, 15
            )

        elif mode == 1:  # MENGANTUK - mulut sangat kecil (hampir tertutup)
            actual_mw = mw * 0.4
            actual_mh = mh * 0.2 * breath
            offset_x = (mw - actual_mw) / 2
            offset_y = (mh - actual_mh) / 2 + mh * 0.4

            # Tiny oval
            painter.drawRoundedRect(
                int(mx + offset_x),
                int(my + offset_y),
                int(actual_mw),
                int(actual_mh),
                10, 10
            )

            # Drool (saat MENGANTUK)
            if s.get("drool", False):
                drool_len = s.get("drool_len", 0)
                if drool_len > 0:
                    drool_x = mx + mw * 0.5
                    drool_y = my + offset_y + actual_mh

                    # Gambar drool
                    drool_gradient = QLinearGradient(drool_x, drool_y, drool_x, drool_y + drool_len)
                    drool_gradient.setColorAt(0, QColor(180, 220, 255, 180))
                    drool_gradient.setColorAt(1, QColor(180, 220, 255, 50))
                    painter.setBrush(QBrush(drool_gradient))
                    painter.setPen(Qt.NoPen)

                    # Bentuk air liur (tear-drop shape)
                    drool_w = 8
                    drool_pts = [
                        QPointF(drool_x - drool_w/2, drool_y),
                        QPointF(drool_x + drool_w/2, drool_y),
                        QPointF(drool_x, drool_y + drool_len),
                    ]
                    painter.drawPolygon(QPolygonF(drool_pts))

        else:  # MENGUAP - mulut terbuka tapi tidak terlalu besar
            if mouth_type == 9:  # Yawning pose
                actual_mw = mw * 1.0 * breath  # Dari 1.3 ke 1.0
                actual_mh = mh * 1.3 * breath  # Dari 2.0 ke 1.3
                offset_x = (mw - actual_mw) / 2
                offset_y = (mh - actual_mh) / 2 - mh * 0.2  # Dari 0.3 ke 0.2

                # Large oval untuk mulut menguap
                painter.drawEllipse(
                    int(mx + offset_x),
                    int(my + offset_y),
                    int(actual_mw),
                    int(actual_mh)
                )

                # Tambahkan dark inner untuk depth (seperti tenggorakan)
                inner_gradient = QRadialGradient(
                    mx + mw/2 + offset_x + actual_mw * 0.3,
                    my + mh/2 + offset_y + actual_mh * 0.4,
                    actual_mh * 0.5  # Dari 0.6 ke 0.5
                )
                inner_gradient.setColorAt(0, QColor(60, 100, 150, 180))
                inner_gradient.setColorAt(1, QColor(40, 80, 130, 100))
                painter.setBrush(QBrush(inner_gradient))
                painter.drawEllipse(
                    int(mx + offset_x + actual_mw * 0.25),  # Dari 0.2 ke 0.25
                    int(my + offset_y + actual_mh * 0.45),  # Dari 0.4 ke 0.45
                    int(actual_mw * 0.5),  # Dari 0.6 ke 0.5
                    int(actual_mh * 0.4)  # Dari 0.5 ke 0.4
                )

                # Lidah (kadang-kadang visible saat menguap)
                if random.random() < 0.3:
                    tongue_gradient = QLinearGradient(
                        mx + mw/2,
                        my + offset_y + actual_mh * 0.7,
                        mx + mw/2,
                        my + offset_y + actual_mh * 0.95
                    )
                    tongue_gradient.setColorAt(0, QColor(220, 120, 150))
                    tongue_gradient.setColorAt(1, QColor(180, 90, 130))
                    painter.setBrush(QBrush(tongue_gradient))

                    tongue_w = actual_mw * 0.4
                    tongue_h = actual_mh * 0.25
                    tongue_x = mx + mw/2 + offset_x - tongue_w/2
                    tongue_y = my + offset_y + actual_mh * 0.7

                    # Bentuk lidah (oval dengan rounded bottom)
                    painter.drawEllipse(
                        int(tongue_x),
                        int(tongue_y),
                        int(tongue_w),
                        int(tongue_h)
                    )
            else:
                # Normal saat tidak sedang menguap penuh
                actual_mw = mw * 0.6
                actual_mh = mh * 0.4 * breath
                offset_x = (mw - actual_mw) / 2
                offset_y = (mh - actual_mh) / 2 + mh * 0.3

                painter.drawRoundedRect(
                    int(mx + offset_x),
                    int(my + offset_y),
                    int(actual_mw),
                    int(actual_mh),
                    15, 15
                )

        # Soft glow di sekitar mulut
        glow_alpha = 30 if mode != 2 else 50  # Lebih bright saat menguap
        glow_gradient = QRadialGradient(mx + mw/2, my + mh/2, mw * 0.7)
        glow_gradient.setColorAt(0, QColor(150, 200, 255, glow_alpha))
        glow_gradient.setColorAt(1, QColor(150, 200, 255, 0))
        painter.setBrush(QBrush(glow_gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            int(mx - mw * 0.1),
            int(my - mh * 0.2),
            int(mw * 1.2),
            int(mh * 1.5)
        )

    # ─────────────────────────────────────────
    def _draw_tears(self, painter, left_x, right_x, ey, eye_w, eye_h, es):
        tear_col = QColor(120, 180, 255, 200)
        painter.setBrush(QBrush(tear_col))
        painter.setPen(Qt.NoPen)
        tl = int(es["tear_len"])
        tw = 8
        for bx in (left_x, right_x):
            tx = bx + eye_w // 2 - tw // 2
            ty = ey + eye_h
            painter.drawRoundedRect(tx, ty, tw, tl, tw // 2, tw // 2)
            # tetes ujung
            painter.drawEllipse(tx - tw // 4, ty + tl - tw // 2,
                                tw + tw // 2, tw + tw // 2)

    # ─────────────────────────────────────────
    def _draw_sweat(self, painter, s, left_x, right_x, ey, eye_w):
        sweat_spots = [
            (left_x + eye_w + 8,  ey - 20),
            (right_x - 20,        ey - 15),
            (left_x + eye_w // 2, ey - 32),
            (right_x + eye_w // 2,ey - 28),
        ]
        sx, sy = sweat_spots[s["sweat_pos"] % len(sweat_spots)]
        g = QRadialGradient(sx + 8, sy + 10, 16)
        g.setColorAt(0, QColor(120, 210, 255, 220))
        g.setColorAt(1, QColor(80, 180, 255, 0))
        painter.setBrush(g)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(sx), int(sy), 16, 22)

    # ─────────────────────────────────────────
    def _draw_zzz(self, painter, w, h):
        es = self.expr_state
        base_size = w // 38
        for i, (dx, dy, sz_mult) in enumerate([
            (w * 0.62, h * 0.28, 1.0),
            (w * 0.70, h * 0.22, 1.25),
            (w * 0.79, h * 0.16, 1.5),
        ]):
            alpha = int(180 + 70 * math.sin(es["time"] * 0.1 + i))
            col   = QColor.fromHsv(260, 150, 240, alpha)
            font  = QFont()
            font.setPointSize(int(base_size * sz_mult))
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(col)
            x = dx + self.zzz_offset * (0.4 * (i + 1))
            y = dy - self.zzz_offset * (0.3 * (i + 1))
            painter.drawText(int(x % w), int(max(20, y)), "Z")

    # ─────────────────────────────────────────
    def _draw_angry_fx(self, painter, w, h, es):
        if random.random() < 0.3:
            for _ in range(2):
                lx1 = random.randint(0, w)
                ly1 = random.randint(0, h // 2)
                lx2 = lx1 + random.randint(-60, 60)
                ly2 = ly1 + random.randint(20, 80)
                alpha = random.randint(60, 160)
                pen = QPen(QColor(255, 80, 30, alpha))
                pen.setWidth(random.randint(1, 3))
                painter.setPen(pen)
                painter.drawLine(lx1, ly1, lx2, ly2)

    # ─────────────────────────────────────────
    def _draw_sparkles(self, painter, w, h, es):
        n = 5
        t = es["time"]
        for i in range(n):
            ang   = (t * 0.04 + i * 2 * math.pi / n)
            rx    = w * 0.15 + w * 0.7 * (0.5 + 0.5 * math.cos(ang * 1.3 + i))
            ry    = h * 0.15 + h * 0.7 * (0.5 + 0.5 * math.sin(ang * 0.9 + i))
            alpha = int(120 + 100 * math.sin(t * 0.1 + i * 1.3))
            sz    = int(8 + 6 * math.sin(t * 0.08 + i * 0.7))
            hue   = (t * 3 + i * 60) % 360
            col   = QColor.fromHsv(hue, 200, 255, alpha)
            painter.setBrush(QBrush(col))
            painter.setPen(Qt.NoPen)
            self._draw_star_shape(painter, rx, ry, sz, sz // 2)

    # ─────────────────────────────────────────
    def _draw_star_shape(self, painter, cx, cy, outer_r, inner_r):
        """Bintang 5 sudut yang benar."""
        pts = []
        for i in range(10):
            r     = outer_r if i % 2 == 0 else inner_r
            angle = math.radians(i * 36 - 90)
            pts.append(QPointF(cx + r * math.cos(angle),
                               cy + r * math.sin(angle)))
        painter.drawPolygon(QPolygonF(pts))

    # ─────────────────────────────────────────
    def _draw_gabut_bg_effects(self, painter, w, h, es):
        """Efek background yang elegan untuk state gabut"""
        t = es["time"]

        # Soft floating orbs di background
        num_orbs = 4
        for i in range(num_orbs):
            # Smooth orbital motion
            angle = (t * 0.01 + i * 2 * math.pi / num_orbs)
            radius_x = w * 0.35 + w * 0.05 * math.sin(t * 0.02 + i)
            radius_y = h * 0.30 + h * 0.05 * math.cos(t * 0.025 + i)

            ox = w // 2 + radius_x * math.cos(angle)
            oy = h // 2 + radius_y * math.sin(angle) * 0.6

            # Pulsating size
            size = (w // 15) * (1 + 0.3 * math.sin(t * 0.03 + i * 1.5))

            # Gradient untuk orb
            orb_gradient = QRadialGradient(ox, oy, size)
            alpha = int(30 + 20 * math.sin(t * 0.04 + i))

            # Warna yang soft dan matching dengan theme
            hue_shift = (i * 40) % 360
            orb_color = QColor.fromHsv((200 + hue_shift) % 360, 120, 255, alpha)

            orb_gradient.setColorAt(0, orb_color)
            orb_gradient.setColorAt(0.5, QColor(orb_color.red(), orb_color.green(), orb_color.blue(), int(alpha * 0.5)))
            orb_gradient.setColorAt(1, QColor(orb_color.red(), orb_color.green(), orb_color.blue(), 0))

            painter.setBrush(QBrush(orb_gradient))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(
                int(ox - size),
                int(oy - size),
                int(size * 2),
                int(size * 2)
            )

        # Subtle wave lines di background
        num_waves = 3
        for i in range(num_waves):
            wave_y = h * 0.3 + i * h * 0.15
            wave_offset = (t * 0.5 + i * 100) % (w + 200) - 100

            wave_alpha = int(15 + 10 * math.sin(t * 0.02 + i))
            wave_color = QColor(150, 200, 255, wave_alpha)

            painter.setPen(QPen(wave_color, 2))
            painter.setBrush(Qt.NoBrush)

            # Draw wave
            path = QPainterPath()
            path.moveTo(wave_offset, wave_y)

            for x in range(int(wave_offset), int(wave_offset + w + 100), 20):
                wave_height = 10 * math.sin((x - wave_offset) * 0.02 + t * 0.05 + i)
                path.lineTo(x, wave_y + wave_height)

            painter.drawPath(path)

        # Gentle floating particles
        num_particles = 8
        for i in range(num_particles):
            # Floating motion
            px = (w * 0.1 + i * w * 0.1 + t * 0.3) % (w + 40) - 20
            py = (h * 0.2 + i * h * 0.08 + 20 * math.sin(t * 0.02 + i * 2)) % (h * 0.6) + h * 0.1

            particle_size = 3 + 2 * math.sin(t * 0.03 + i)
            particle_alpha = int(40 + 30 * math.sin(t * 0.04 + i * 0.5))

            particle_gradient = QRadialGradient(px, py, particle_size * 2)
            particle_gradient.setColorAt(0, QColor(180, 220, 255, particle_alpha))
            particle_gradient.setColorAt(1, QColor(180, 220, 255, 0))

            painter.setBrush(QBrush(particle_gradient))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(
                int(px - particle_size),
                int(py - particle_size),
                int(particle_size * 2),
                int(particle_size * 2)
            )

    # ─────────────────────────────────────────
    def _draw_gabut_message(self, painter, w, h):
        """Gambar pesan status EcoLab saat state gabut dengan desain elegan"""
        ms = self.gabut_message_state

        # Jika tidak ada pesan atau alpha 0, tidak perlu menggambar
        if ms["current_message"] is None or ms["message_alpha"] <= 0:
            return

        alpha = int(ms["message_alpha"])

        # Import time untuk smooth animation
        import time
        t = time.time() * 1000

        # Setup font
        font = QFont()
        font.setFamily("Segoe UI, Arial, sans-serif")
        font.setPointSize(int(w // 42))
        font.setBold(True)
        painter.setFont(font)

        # Ukuran teks
        text = ms["current_message"]
        emoji = ms["current_emoji"]

        # Hitung ukuran text box
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(text)
        emoji_width = metrics.horizontalAdvance(emoji)
        total_width = text_width + emoji_width + 25

        # Posisi text box dengan subtle floating animation
        float_offset = 3 * math.sin(t * 0.003)
        box_x = w // 2 - total_width // 2 - 25
        box_y = h * 0.70 + float_offset
        box_width = total_width + 50
        box_height = int(h * 0.13)

        # Gradient background yang smooth dan modern
        bg_gradient = QLinearGradient(box_x, box_y, box_x, box_y + box_height)
        bg_gradient.setColorAt(0, QColor(35, 45, 75, int(alpha * 0.92)))
        bg_gradient.setColorAt(1, QColor(25, 35, 60, int(alpha * 0.88)))

        # Border dengan gradient
        border_gradient = QLinearGradient(box_x, box_y, box_x + box_width, box_y)
        border_gradient.setColorAt(0, QColor(100, 180, 255, int(alpha * 0.7)))
        border_gradient.setColorAt(0.5, QColor(150, 200, 255, int(alpha * 0.8)))
        border_gradient.setColorAt(1, QColor(100, 180, 255, int(alpha * 0.7)))

        painter.setPen(QPen(border_gradient, max(2, w // 350)))
        painter.setBrush(QBrush(bg_gradient))
        painter.drawRoundedRect(
            int(box_x), int(box_y),
            box_width, box_height,
            20, 20
        )

        # Inner glow effect
        inner_glow = QRadialGradient(box_x + box_width/2, box_y + box_height/2, box_width * 0.6)
        inner_glow.setColorAt(0, QColor(150, 200, 255, int(alpha * 0.15)))
        inner_glow.setColorAt(1, QColor(150, 200, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(inner_glow))
        painter.drawRoundedRect(
            int(box_x + 3), int(box_y + 3),
            box_width - 6, box_height - 6,
            18, 18
        )

        # Gambar emoji di kiri dengan subtle pulse
        emoji_scale = 1.0 + 0.05 * math.sin(t * 0.006)
        emoji_font = QFont()
        emoji_font.setFamily("Segoe UI Emoji")
        emoji_font.setPointSize(int(w // 32 * emoji_scale))
        painter.setFont(emoji_font)

        # Emoji glow
        emoji_glow = QColor(180, 220, 255, int(alpha * 0.3))
        painter.setPen(emoji_glow)
        for offset in [2, 4, 6]:
            painter.drawText(
                int(box_x + 25 + offset),
                int(box_y + box_height // 2 + metrics.height() // 4 + offset),
                emoji
            )

        # Main emoji
        painter.setPen(QColor(255, 255, 255, alpha))
        painter.drawText(
            int(box_x + 25),
            int(box_y + box_height // 2 + metrics.height() // 4),
            emoji
        )

        # Gambar teks dengan efek yang lebih elegan
        text_font = QFont()
        text_font.setFamily("Segoe UI, Arial, sans-serif")
        text_font.setPointSize(int(w // 48))
        text_font.setBold(True)
        painter.setFont(text_font)

        # Warna teks dengan gradient yang smooth
        text_color_map = {
            "neutral": QColor(210, 230, 255, alpha),
            "happy": QColor(255, 250, 200, alpha),
            "thinking": QColor(180, 220, 255, alpha),
            "curious": QColor(255, 230, 200, alpha),
            "excited": QColor(255, 200, 230, alpha),
            "sleepy": QColor(220, 200, 255, alpha),
        }
        text_color = text_color_map.get(ms["current_expression"], QColor(220, 240, 255, alpha))

        # Text shadow yang lebih halus
        shadow_layers = [
            (QColor(0, 10, 30, int(alpha * 0.4)), 3),
            (QColor(0, 10, 30, int(alpha * 0.2)), 5),
        ]

        for shadow_color, offset in shadow_layers:
            painter.setPen(shadow_color)
            painter.drawText(
                int(box_x + emoji_width + 40 + offset),
                int(box_y + box_height // 2 + metrics.height() // 4 + offset),
                text
            )

        # Main text dengan glow effect
        text_glow_color = QColor(180, 220, 255, int(alpha * 0.4))
        painter.setPen(text_glow_color)
        painter.drawText(
            int(box_x + emoji_width + 40 + 1),
            int(box_y + box_height // 2 + metrics.height() // 4),
            text
        )

        painter.setPen(text_color)
        painter.drawText(
            int(box_x + emoji_width + 40),
            int(box_y + box_height // 2 + metrics.height() // 4),
            text
        )

        # Elegant indicator di atas box dengan pulse animation
        pulse_size = 1.0 + 0.2 * math.sin(t * 0.008)
        indicator_y = box_y - 10
        indicator_size = int(10 * pulse_size)

        # Glow untuk indicator
        indicator_glow = QRadialGradient(w // 2, indicator_y + indicator_size//2, indicator_size * 1.5)
        indicator_glow.setColorAt(0, QColor(120, 200, 255, int(alpha * 0.6)))
        indicator_glow.setColorAt(1, QColor(120, 200, 255, 0))
        painter.setBrush(QBrush(indicator_glow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            int(w // 2 - indicator_size * 1.5),
            int(indicator_y - indicator_size * 0.5),
            int(indicator_size * 3),
            int(indicator_size * 3)
        )

        # Main indicator
        painter.setBrush(QBrush(QColor(150, 220, 255, alpha)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            int(w // 2 - indicator_size // 2),
            int(indicator_y),
            indicator_size,
            indicator_size
        )

        # Highlight pada indicator
        painter.setBrush(QBrush(QColor(255, 255, 255, int(alpha * 0.8))))
        painter.drawEllipse(
            int(w // 2 - indicator_size // 4),
            int(indicator_y + indicator_size // 4),
            int(indicator_size // 2),
            int(indicator_size // 2)
        )

    # ─────────────────────────────────────────
    def _draw_particle(self, painter, x, y, ptype, size, rotation, alpha=255):
        painter.save()
        painter.translate(x, y)
        painter.rotate(rotation)
        s = size // 2

        if ptype == "heart":
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 80, 120, alpha)))
            painter.drawEllipse(-s, -s * 6 // 10, s, s)
            painter.drawEllipse(0,  -s * 6 // 10, s, s)
            pts = [QPointF(-s, -s // 6), QPointF(0, s * 8 // 10), QPointF(s, -s // 6)]
            painter.drawPolygon(QPolygonF(pts))

        elif ptype == "star":
            col = random.choice([QColor(255, 220, 80, alpha),
                                 QColor(255, 180, 100, alpha),
                                 QColor(200, 255, 150, alpha)])
            painter.setBrush(QBrush(col))
            painter.setPen(Qt.NoPen)
            self._draw_star_shape(painter, 0, 0, s, s // 2)

        elif ptype in ("question", "exclaim", "sleepy", "dizzy", "lol", "note"):
            chars = {"question": "?", "exclaim": "!", "sleepy": "Z",
                     "dizzy": "@", "lol": "lol", "note": "♪"}
            cols_map = {"question": QColor(200, 200, 255, alpha),
                        "exclaim":  QColor(255, 220, 80, alpha),
                        "sleepy":   QColor(180, 180, 220, alpha),
                        "dizzy":    QColor(200, 150, 255, alpha),
                        "lol":      QColor(255, 200, 80, alpha),
                        "note":     QColor(150, 220, 255, alpha)}
            font = QFont()
            font.setPointSize(size)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(cols_map.get(ptype, QColor(255, 255, 255, alpha)))
            painter.drawText(-size // 2, size // 2, chars.get(ptype, "?"))

        elif ptype == "sparkle":
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 180, alpha)))
            painter.drawRect(-s // 3, -s, s * 2 // 3, s * 2)
            painter.drawRect(-s, -s // 3, s * 2, s * 2 // 3)

        elif ptype == "heart":
            pass  # handled above

        elif ptype == "poop":
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(120, 80, 40, alpha)))
            painter.drawEllipse(-s, -s // 2, s * 2, s)
            painter.drawEllipse(-s * 2 // 3, -s, s * 4 // 3, s)
            painter.setBrush(QBrush(QColor(220, 220, 220, alpha)))
            painter.drawEllipse(-s // 4, -s * 3 // 4, s // 2, s // 2)

        elif ptype == "angry_vein":
            pen = QPen(QColor(255, 60, 60, alpha))
            pen.setWidth(3)
            painter.setPen(pen)
            painter.drawLine(-s, 0, 0, -s // 2)
            painter.drawLine(0, -s // 2, s, 0)

        elif ptype == "fire":
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 120, 20, alpha)))
            painter.drawEllipse(-s // 2, -s, s, s * 2)
            painter.setBrush(QBrush(QColor(255, 220, 60, alpha // 2)))
            painter.drawEllipse(-s // 3, -s // 2, s * 2 // 3, s)

        elif ptype in ("music", "speech", "cloud", "rain",
                       "rainbow_dot", "tear_drop", "moon", "zzz_p", "skull"):
            # simple symbol fallback
            font = QFont()
            font.setPointSize(max(8, size))
            painter.setFont(font)
            symbol_map = {
                "music":       ("♪", QColor(150, 200, 255, alpha)),
                "speech":      ("💬", QColor(200, 255, 200, alpha)),
                "cloud":       ("☁", QColor(150, 180, 220, alpha)),
                "rain":        ("💧", QColor(100, 160, 255, alpha)),
                "rainbow_dot": ("●", QColor.fromHsv(random.randint(0,359), 200, 255, alpha)),
                "tear_drop":   ("💧", QColor(120, 180, 255, alpha)),
                "moon":        ("☽", QColor(200, 180, 255, alpha)),
                "zzz_p":       ("Z", QColor(180, 150, 255, alpha)),
                "skull":       ("☠", QColor(255, 80, 80, alpha)),
            }
            ch, col = symbol_map.get(ptype, ("•", QColor(255, 255, 255, alpha)))
            painter.setPen(col)
            painter.drawText(-size // 2, size // 2, ch)

        elif ptype == "cat":
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 200, 150, alpha)))
            painter.drawEllipse(-s, -s // 2, s * 2, s)
            painter.drawEllipse(-s, -s, s, s)
            painter.drawEllipse(0, -s, s, s)
            painter.setBrush(QBrush(QColor(80, 60, 40, alpha)))
            painter.drawEllipse(-s // 2, -s // 2, s // 3, s // 3)
            painter.drawEllipse(s // 5, -s // 2, s // 3, s // 3)

        painter.restore()

    # ─────────────────────────────────────────
    def _cleanup(self):
        self.input_handler.running = False


# ═══════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication([])
    face = RobotFace()
    face.show()
    app.exec()

# END OF CODE --- AMBATUNATTTTTTTTTTTT