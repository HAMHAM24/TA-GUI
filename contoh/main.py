import sys,random,os
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import (
    QCoreApplication, QPropertyAnimation, QDate, QDateTime, QMetaObject,
    QObject, QPoint, QRect, QSize, QTime, QTimer, QUrl, Qt, QEvent, QStandardPaths
)

from PySide6.QtGui import (
    QBrush, QColor, QConicalGradient, QCursor, QFont, QFontDatabase,
    QIcon, QKeySequence, QLinearGradient, QPalette, QPainter,
    QPixmap, QRadialGradient
)

from PySide6.QtWidgets import *
from PySide6.QtGui import QIntValidator, QDoubleValidator

# Import UI hasil Qt Designer
from ui_mainwindow import Ui_MainWindow
from ui_functions import UIFunctions

from lamp_setup import LampSetup
from ac_setup import ACSetup
from arrow_setup import ArrowSetup

from widgets.lamp_button import LampButton
from backend.growatt_backend import GrowattBackend
from backend.weathercloud_backend import WeatherCloudBackend
from backend.mqtt_client import MqttClient
from backend.mqtt_dht22_backend import DHT22MQTTBackend
from backend.lampbutton_backend import LampButtonBackend
from backend.acbutton_backend import ACButtonBackend
from backend.growatt_worker import GrowattWorker
from backend.mcu_status_backend import MCUStatusBackend

# Class untuk mengatur Hari dan Waktu
class Date:
    def update_time(self, label: QLabel):
        current_time = QDateTime.currentDateTime()

        time_text = current_time.toString("HH:mm")
        date_text = current_time.toString("dddd, dd MMMM yyyy")

        label.setText(QCoreApplication.translate("MainWindow", f"{time_text} - {date_text}", None))
        
# Main Window
class MainWindow(QMainWindow): 
    def __init__(self):
        super().__init__()

        # SETUP UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Method untuk inisialisasi GUI yang saat aplikasi berjalan.
        self.initUI()

        self.ui.logPlainEdit.setReadOnly(True)
        self._weather_initial_fetched = False

        # SETUP UI COMPONENTS (Lamp, AC, Arrow)
        LampSetup.setup(self.ui, self)
        ACSetup.setup(self.ui, self)
        ArrowSetup.setup(self.ui, self)

        # BACKEND: GROWATT
        self.growatt = GrowattBackend()
        self.growatt_worker = None
        self._last_growatt_data = None
        self.start_growatt_worker()

        # BACKEND: WEATHER CLOUD
        self.weather = WeatherCloudBackend("5476957392")

        # MQTT CORE & BACKENDS
        self.mqtt = MqttClient()
        self.mqtt.start()

        self.dht = DHT22MQTTBackend(self.mqtt)
        self.dht.start()

        self.lampbutton_backend = LampButtonBackend(self.mqtt, logger=self.log)
        self.acbutton_backend = ACButtonBackend(self.mqtt, logger=self.log)
        QTimer.singleShot(500, self.sync_ui_from_mqtt)


        # ROOT & BODY LAYOUT
        for w in [self.ui.styleSheet, self.ui.bgApp]:
            w.setContentsMargins(0, 0, 0, 0)
            if w.layout():
                w.layout().setContentsMargins(0, 0, 0, 0)
                w.layout().setSpacing(0)

        self.ui.contentTopBg.setContentsMargins(0, 0, 0, 0)

        # WINDOW SETTINGS (FRAMELESS)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # DATE & CLOCK TIMER
        self.date_helper = Date()
        self.timer = QTimer(self)
        self.timer.timeout.connect(
            lambda: self.date_helper.update_time(self.ui.clockInfo)
        )
        self.timer.start(1000)

        # UI FUNCTIONS & WINDOW BUTTONS
        self.ui_functions = UIFunctions(self)

        self.ui.minimizeAppBtn.clicked.connect(self.showMinimized)
        self.ui.maximizeRestoreAppBtn.clicked.connect(
            self.ui_functions.toggle_max_restore
        )
        self.ui.closeAppBtn.clicked.connect(self.close)
        self.ui.btn_exit.clicked.connect(self.close)

        # DRAG TITLE BAR
        self.ui.contentTopBg.mousePressEvent = self.ui_functions.mouse_press
        self.ui.contentTopBg.mouseMoveEvent = self.ui_functions.mouse_move
        self.ui.contentTopBg.mouseDoubleClickEvent = (
            self.ui_functions.mouse_double_click
        )

        # TOGGLE LEFT MENU
        self.ui.toggleButton.clicked.connect(
            lambda: self.ui_functions.toggle_left_menu(self.ui.leftMenuBg)
        )

        # STACKED WIDGET NAVIGATION
        self.ui.btn_growatt.clicked.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(
                self.ui.page1_growattMonitoring
            )
        )

        self.ui.btn_controlroom.clicked.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(
                self.ui.page2_controlRoom
            )
        )

        self.ui.btn_monitoringsensor.clicked.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(
                self.ui.page3_monitoringSensor
            )
        )

        self.ui.btn_growattgraph.clicked.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(
                self.ui.page4_growattGraph
            )
        )
        
        self.ui.btn_growattgraph.setEnabled(False)
        self.ui.btn_growattgraph.setToolTip("  Fitur belum tersedia")


        self.ui.btn_setting.clicked.connect(
            lambda: self.ui.stackedWidget.setCurrentWidget(
                self.ui.page5_settings
            )
        )

        self.ui.stackedWidget.setCurrentWidget(
            self.ui.page1_growattMonitoring
        )
        
        self.ac_buttons = [
            self.ac_button,
            self.ui.btn_temp_up,
            self.ui.btn_temp_down,
            self.ui.btn_cool_ac,
            self.ui.btn_fan_ac,
        ]
        
        # ===============================
        # FLOW INFO POPUP (Growatt)
        # ===============================
        self.flowInfoPopup = QFrame(self, Qt.Popup)
        self.flowInfoPopup.setObjectName("flowInfoPopup")
        self.flowInfoPopup.setStyleSheet("""
        QFrame#flowInfoPopup {
            background: white;
            border-radius: 8px;
            padding: 10px;
        }
        """)

        layoutPopup = QVBoxLayout(self.flowInfoPopup)
        layoutPopup.setContentsMargins(10, 10, 10, 10)
        layoutPopup.setSpacing(6)
        
        self.lblFlowTitle = QLabel(
            "PV Off-grid Inverter：PV Charging+Loads Supporting"
        )
        self.lblFlowTitle.setStyleSheet(
            "font-weight: bold; font-size: 13px;"
        )
        self.lblFlowTitle.setAlignment(Qt.AlignLeft)
        self.lblFlowTitle.setContentsMargins(0, 0, 0, 6)
        self.lblFlowTitle.setStyleSheet(
            "font-weight: bold; font-size: 13px; color: #2c2c2c;"
        )
        layoutPopup.addWidget(self.lblFlowTitle)

        self.lblBattery = QLabel("Battery Voltage: -- V")
        self.lblPVVolt = QLabel("PV1/PV2 Voltage: -- / -- V")
        self.lblPVCurrent = QLabel("PV1/PV2 Recharging Current: -- / -- A")
        self.lblTotalCharge = QLabel("Total Charge Current: -- A")
        self.lblACIn = QLabel("AC Input Voltage/Frequency: -- V / -- Hz")
        self.lblACOut = QLabel("AC Output Voltage/Frequency: -- V / -- Hz")
        self.lblConsumption = QLabel("Consumption Power: -- W")
        self.lblLoad = QLabel("Load Percentage: -- %")

        for lbl in (
            self.lblBattery,
            self.lblPVVolt,
            self.lblPVCurrent,
            self.lblTotalCharge,
            self.lblACIn,
            self.lblACOut,
            self.lblConsumption,
            self.lblLoad,
        ):
            layoutPopup.addWidget(lbl)
            
        self.ui.titleFlow.mousePressEvent = self.show_flow_popup


        # Disable input IP & add button (belum digunakan)
        self.ui.inputIP.setEnabled(False)
        self.ui.btn_add.setEnabled(False)
        
        self.lampbutton_backend = LampButtonBackend(self.mqtt, logger=self.log)
        self.lampbutton_backend.start()
        
        self.acbutton_backend = ACButtonBackend(self.mqtt, logger=self.log)
        self.acbutton_backend.start()

        # AC CONTROL BUTTONS
        self.ui.btn_temp_up.clicked.connect(self.ac_temp_up)
        self.ui.btn_temp_down.clicked.connect(self.ac_temp_down)
        self.ui.btn_cool_ac.clicked.connect(self.ac_mode_cool)
        self.ui.btn_fan_ac.clicked.connect(self.ac_mode_fan)

        # TIMERS: GROWATT
        self.timerGrowatt = QTimer(self)
        self.timerGrowatt.timeout.connect(self.start_growatt_worker)
        self.timerGrowatt.start(15000)  # 15 detik

        # TIMERS: WEATHER CLOUD
        self.timerWeathercloud = QTimer(self)
        self.timerWeathercloud.timeout.connect(self.update_dataWeathercloud)
        self.timerWeathercloud.start(5000)  # 5 detik

        # TIMERS: DHT MQTT
        self.timerDhtmqtt = QTimer(self)
        self.timerDhtmqtt.timeout.connect(self.update_dht_ui)
        self.timerDhtmqtt.start(1000)  # 1 detik

        # MCU STATUS BACKEND & TIMER
        self.mcu_status = MCUStatusBackend(self.mqtt)
        self.mcu_status.start()

        self.timerMCUStatus = QTimer(self)
        self.timerMCUStatus.timeout.connect(self.update_mcu_status_ui)
        self.timerMCUStatus.start(1000)  # 1 detik
        
        self.timerLampState = QTimer(self)
        self.timerLampState.timeout.connect(self.update_lamp_ui_from_state)
        self.timerLampState.start(300)
        
        self.timerACState = QTimer(self)
        self.timerACState.timeout.connect(self.update_ac_ui_from_state)
        self.timerACState.start(300)

        # SHOW WINDOW
        self.show()
        
    def show_flow_popup(self, event):
        # posisikan popup di bawah titleFlow
        pos = self.ui.titleFlow.mapToGlobal(
            self.ui.titleFlow.rect().bottomLeft()
        )
        self.flowInfoPopup.move(pos)
        self.flowInfoPopup.show()

    def update_flow_popup(self, flow):
        if not flow:
            return

        def fmt(val, unit="", dec=1):
            if val is None:
                return "--"
            return f"{val:.{dec}f}{unit}"

        def fmt_int(val, unit=""):
            if val is None:
                return "--"
            return f"{int(val)}{unit}"

        # 🔋 Battery
        self.lblBattery.setText(
            f"Battery Voltage: {fmt(flow.get('battery_voltage'), ' V')}"
        )

        # ☀️ PV Voltage
        self.lblPVVolt.setText(
            f"PV1/PV2 Voltage: "
            f"{fmt(flow.get('pv1_voltage'))} / {fmt(flow.get('pv2_voltage'), ' V')}"
        )

        # ☀️ PV Charging Current
        self.lblPVCurrent.setText(
            f"PV1/PV2 Recharging Current: "
            f"{fmt(flow.get('pv1_charge_current'))} / {fmt(flow.get('pv2_charge_current'), ' A')}"
        )

        # 🔌 Total Charge
        self.lblTotalCharge.setText(
            f"Total Charge Current: {fmt(flow.get('total_charge_current'), 'A')}"
        )

        # ⚡ AC Input
        self.lblACIn.setText(
            f"AC Input Voltage/Frequency: "
            f"{fmt(flow.get('ac_input_voltage'))} / {fmt(flow.get('ac_input_frequency'), ' Hz')}"
        )

        # ⚡ AC Output
        self.lblACOut.setText(
            f"AC Output Voltage/Frequency: "
            f"{fmt(flow.get('ac_output_voltage'))} / {fmt(flow.get('ac_output_frequency'), ' Hz')}"
        )

        # 🏠 Consumption
        self.lblConsumption.setText(
            f"Consumption Power: {fmt_int(flow.get('consumption_power'), 'W')}/ {fmt_int(flow.get('rateVA'), 'VA')}"
        )

        # 📊 Load
        self.lblLoad.setText(
            f"Load Percentage: {fmt(flow.get('load_percentage'), '%')}"
        )

        
    def update_growatt_ui(self, data: dict):
        if not data:
            return

        # skip kalau data sama
        if data == self._last_growatt_data:
            return
        
        self.ui.currentpvpower_value.setText(f"PV Power: {data['pv_power']}W")
        self.ui.currentimportgrid_value.setText(f"{data['grid_import_power']}W")
        self.ui.currentconsumppower_value.setText(f"{data['load_power']}W//{data['rateVA_power']}VA")
        self.ui.currentsocbat_value.setText(f"SoC Battery：{data['soc']}%")
        self.ui.pvtoday_value.setText(f"{data['pv_today']}")
        self.ui.pvtotal_value.setText(f"{data['pv_total']}")
        self.ui.loadtoday_value.setText(f"{data['load_today']}")
        self.ui.loadtotal_value.setText(f"{data['load_total']}")
        self.ui.chargingtotal_value.setText(f"{data['battery_charge_total']}")
        self.ui.dischargingtoday_value.setText(f"{data['battery_discharge_today']}")
        self.ui.dischargingtotal_value.setText(f"{data['battery_discharge_total']}")
        self.ui.imporgridttotal_value.setText(f"{data['grid_total']}")
        
        # self.ui.chargingtoday_value.setText(f"{data['battery_charge_today']}")
        # self.ui.imporgridttoday_value.setText(f"{data['grid_today']}")
        
        charge_today = self._safe_energy_value(data.get("battery_charge_today"))
        grid_today = self._safe_energy_value(data.get("grid_today"))
        
        self.ui.chargingtoday_value.setText(f"{charge_today}")
        self.ui.imporgridttoday_value.setText(f"{grid_today}")

        pbat = data["battery_power"]

        if pbat < 0:
            self.ui.currentdischpower_value.setText(f"Charging Power : {abs(pbat)} W")
            self.arrows["soc_dynamic"].set_direction("down")
            self.arrows["soc_dynamic"].set_active(True)
        else:
            self.ui.currentdischpower_value.setText(f"Discharging Power : {pbat} W")
            self.arrows["soc_dynamic"].set_direction("up")
            self.arrows["soc_dynamic"].set_active(True)

                        
        # ARROW
        self.arrows["pv"].set_active(data["pv_power"] > 0)
        self.arrows["grid"].set_active(data["grid_import_power"] > 0)
        self.arrows["load"].set_active(data["load_power"] > 0)
        
        self.log("[Growatt] Data updated")
        
        self.update_flow_popup(data.get("flow_info"))


    @staticmethod
    def deg_to_compass(deg: float) -> str:
        directions = [
            "North",
            "North East",
            "East",
            "South East",
            "South",
            "South West",
            "West",
            "North West",
        ]
        return directions[round(deg / 45) % 8]

    def update_dataWeathercloud(self):
        
        if not self._weather_initial_fetched:
            pass
        else:
            # Skip kalau halaman WeatherCloud tidak aktif
            if self.ui.stackedWidget.currentWidget() != self.ui.page3_monitoringSensor:
                return
    
        try:
            data = self.weather.fetch()
            
            
            # tandai initial fetch sudah dilakukan
            self._weather_initial_fetched = True
        
            self.ui.tempW_value.setText(f"{data['temperature']} °C")
            self.ui.humidW_value.setText(f"{data['humidity']} %")
            self.ui.pressureW_value.setText(f"{data['pressure']} hPa")
            self.ui.windspdW_value.setText(f"{data['wind_speed']} m/s")
            self.ui.windspdavgW_value.setText(f"{data['wind_speed_avg']} m/s")
            self.ui.windspddirW_value.setText(
                f"{data['wind_direction']}° / {MainWindow.deg_to_compass(data['wind_direction'])}"
            )
            self.ui.totalrainW_value.setText(f"{data['rain_total']} mm")
            self.ui.rainrateW_value.setText(f"{data['rain_rate']} mm/h")
            self.ui.heatindexW_value.setText(f"{data['heat_index']} °C")
            
            temp_outdoor = data.get("temperature")
            
            self.update_temp_style(
                temp_outdoor,
                self.ui.frameTempWeather,
                self.ui.titletempW
            )
            
            heat_index = data.get("heat_index")

            self.update_heatindex_style(
                heat_index,
                self.ui.frameHeatindexWeather,
                self.ui.titleheatindexW
            )
            
            humid_outdoor = data.get("humidity")

            self.update_humidity_style(
                humid_outdoor,
                self.ui.frameHumidWeather,
                self.ui.titlehumidw
            )


        except Exception as e:
            print("dataWeather Cloud:", e)
            self.log("dataWeather Cloud:", e)
            
    def update_dht_ui(self):
        data = self.dht.fetch()

        avg_temp = data.get("avg_temperature")
        avg_hum = data.get("avg_humidity")

        # ===== DETEKSI DATA PERTAMA =====
        if not hasattr(self, "_dht_initialized"):
            if avg_temp is not None or avg_hum is not None:
                self._dht_initialized = True
                self.log("[DHT] Data pertama diterima dari MQTT")
            else:
                return
        # ===============================

        # Update suhu
        if avg_temp is not None:
            if avg_temp != getattr(self, "_last_dht_temp", None):
                self.ui.tempIndoor_value.setText(f"{avg_temp:.1f} °C")
                self._last_dht_temp = avg_temp

        # Update kelembaban
        if avg_hum is not None:
            if avg_hum != getattr(self, "_last_dht_hum", None):
                self.ui.humidIndoor_value.setText(f"{avg_hum:.1f} %")
                self._last_dht_hum = avg_hum
                   
        if avg_temp is not None:
            if not hasattr(self, "_last_dht_log"):
                self._last_dht_log = 0

            now = QDateTime.currentSecsSinceEpoch()
            if now - self._last_dht_log >= 30:  # log tiap 30 detik
                self.log(f"[DHT] Avg Temp: {avg_temp:.1f} °C")
                self._last_dht_log = now
                
        self.update_temp_style(
            avg_temp,
            self.ui.frameTempIndoor,
            self.ui.titleSuhuIndoor
        )   
        
        self.update_humidity_style(
            avg_hum,
            self.ui.frameHumidIndoor,
            self.ui.titleHumidIndoor
        )


    def publish_lamp(self, lamp_index: int, state: bool):
        # self.lampbutton_backend.set_lamp(lamp_index, state)
        self.lampbutton_backend.publish(lamp_index, state)
        self.log(f"Lamp {lamp_index}: {state}")

    def publish_ac_power(self, state: bool):
        self.acbutton_backend.power(state)
        print(f"AC Power: {state}")
        self.log(f"AC Power: {state}")
        
    def ac_temp_up(self):
        self.acbutton_backend.temp_up()

    def ac_temp_down(self):
        self.acbutton_backend.temp_down()

    def ac_mode_cool(self):
        self.acbutton_backend.mode_cool()

    def ac_mode_fan(self):
        self.acbutton_backend.mode_fan()
        
    def log(self, message: str):
        QTimer.singleShot(0, lambda: self._append_log(message))

    def _append_log(self, message: str):
        time = QDateTime.currentDateTime().toString("HH:mm:ss")
        self.ui.logPlainEdit.appendPlainText(f"[{time}] {message}")
        self.ui.logPlainEdit.verticalScrollBar().setValue(
            self.ui.logPlainEdit.verticalScrollBar().maximum()
        )

    def start_growatt_worker(self):
        if self.growatt_worker and self.growatt_worker.isRunning():
            return

        self.growatt_worker = GrowattWorker(self.growatt)
        self.growatt_worker.data_ready.connect(self.update_growatt_ui)
        self.growatt_worker.error.connect(
            lambda err: self.log(f"[Growatt ERROR] {err}")
        )
        self.growatt_worker.start()
        
    def update_mcu_status_ui(self):
        status = self.mcu_status.fetch()

        # ===== MCU A =====
        if status["mcuA"] is not None:
            statemcuA = status["mcuA"]

            self.ui.statusmcuA.setText(
                "MCU A: ONLINE" if statemcuA else "MCU A: OFFLINE"
            )
            self.ui.statusmcuA.setProperty(
                "state", "on" if statemcuA else "off"
            )
            self.ui.statusmcuA.style().polish(self.ui.statusmcuA)
            
            disabled_lamps = {4}

            for idx, lamp in enumerate(self.lamps, start=1):
                if idx in disabled_lamps:
                    lamp.setEnabled(False)
                else:
                    lamp.setEnabled(statemcuA)

        # ===== MCU B =====
        if status["mcuB"] is not None:
            statemcuB = status["mcuB"]

            self.ui.statusmcuB.setText(
                "MCU B: ONLINE" if statemcuB else "MCU B: OFFLINE"
            )
            self.ui.statusmcuB.setProperty(
                "state", "on" if statemcuB else "off"
            )
            self.ui.statusmcuB.style().polish(self.ui.statusmcuB)
            
            for btn in self.ac_buttons:
                btn.setEnabled(statemcuB)
    
    def update_temp_style(self, temperature, frame, title):
        if temperature is None:
            return

        try:
            temp = float(temperature)
        except (ValueError, TypeError):
            return

        if temp < 20:
            frame_color = "#E3F2FD"
            border_color = "#90CAF9"
            title_bg = "#42A5F5"
        elif temp < 26:
            frame_color = "#FFF3E6"
            border_color = "#FFD6B0"
            title_bg = "#F4A261"
        elif temp < 32:
            frame_color = "#FFF8E1"
            border_color = "#FFE082"
            title_bg = "#F9A825"
        else:
            frame_color = "#FDECEA"
            border_color = "#F5C6CB"
            title_bg = "#E53935"

        frame.setStyleSheet(f"""
        QFrame#{frame.objectName()} {{
            background-color: {frame_color};
            border: 2px solid {border_color};
            border-radius: 10px;
        }}
        """)

        title.setStyleSheet(f"""
        QLabel#{title.objectName()} {{
            font: bold 14pt "Segoe UI";
            color: white;
            background-color: {title_bg};
            border-radius: 8px;
            padding: 6px 10px;
            border: 1px solid {title_bg};
        }}
        """)
        
    def update_heatindex_style(self, heat_index, frame, title):
        if heat_index is None:
            return

        try:
            hi = float(heat_index)
        except (ValueError, TypeError):
            return

        if hi < 27:
            frame_color = "#E8F5E9"   # hijau muda
            border_color = "#A5D6A7"
            title_bg = "#43A047"
        elif hi < 32:
            frame_color = "#FFFDE7"   # kuning muda
            border_color = "#FFF59D"
            title_bg = "#FBC02D"
        elif hi < 41:
            frame_color = "#FFF3E0"   # oranye muda
            border_color = "#FFCC80"
            title_bg = "#FB8C00"
        elif hi < 54:
            frame_color = "#FDECEA"   # merah muda
            border_color = "#EF9A9A"
            title_bg = "#E53935"
        else:
            frame_color = "#4E342E"   # maroon gelap
            border_color = "#3E2723"
            title_bg = "#212121"

        frame.setStyleSheet(f"""
        QFrame#{frame.objectName()} {{
            background-color: {frame_color};
            border: 2px solid {border_color};
            border-radius: 10px;
        }}
        """)

        title.setStyleSheet(f"""
        QLabel#{title.objectName()} {{
            font: bold 14pt "Segoe UI";
            color: white;
            background-color: {title_bg};
            border-radius: 8px;
            padding: 6px 10px;
            border: 1px solid {title_bg};
        }}
        """)
        
    def update_humidity_style(self, humidity, frame, title):
        if humidity is None:
            return

        try:
            h = float(humidity)
        except (ValueError, TypeError):
            return

        if h < 30:
            frame_color = "#E3F2FD"   # kering (biru)
            border_color = "#90CAF9"
            title_bg = "#42A5F5"
        elif h < 60:
            frame_color = "#E8F5E9"   # ideal (hijau)
            border_color = "#A5D6A7"
            title_bg = "#43A047"
        elif h < 70:
            frame_color = "#E0F2F1"   # lembap (toska)
            border_color = "#80CBC4"
            title_bg = "#26A69A"
        else:
            frame_color = "#F3E5F5"   # sangat lembap (ungu)
            border_color = "#CE93D8"
            title_bg = "#8E24AA"

        frame.setStyleSheet(f"""
        QFrame#{frame.objectName()} {{
            background-color: {frame_color};
            border: 2px solid {border_color};
            border-radius: 10px;
        }}
        """)

        title.setStyleSheet(f"""
        QLabel#{title.objectName()} {{
            font: bold 14pt "Segoe UI";
            color: white;
            background-color: {title_bg};
            border-radius: 8px;
            padding: 6px 10px;
            border: 1px solid {title_bg};
        }}
        """)

    def initUI(self):
        """Pengaturan Awal GUI"""
        # Mengatur Judul Aplikasi
        self.setWindowTitle("EcoLab Dashboard")
    
        # Mengatur Icon Aplikasi
        pixmap = QPixmap(self.resource_path("icon\\logoecolab.ico"))
        icon = QIcon(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.setWindowIcon(icon)
        
    def resource_path(self, relative_path):
        """ Mengonversi path relatif menjadi path absolut. 
        Berguna untuk memastikan file dapat ditemukan dari 
        direktori aplikasi saat ini.
        """
        base_path = os.path.abspath(".")  # Mengatur ke directory saat ini. 
        return os.path.join(base_path, relative_path)
    
    
    def update_lamp_ui_from_state(self):
        for idx, lamp in enumerate(self.lamps, start=1):
            state = self.lampbutton_backend.states.get(idx)
            if state is not None:
                lamp.blockSignals(True)
                lamp.setChecked(state)   # ✅ BENAR
                lamp.blockSignals(False)

    def update_ac_ui_from_state(self):
        state = self.acbutton_backend.state
        if state is not None:
            self.ac_button.blockSignals(True)
            self.ac_button.setChecked(state)
            self.ac_button.blockSignals(False)

            # 🔥 TAMBAHAN WAJIB
            if hasattr(self, "update_ac_status"):
                self.update_ac_status(state)

    def sync_ui_from_mqtt(self):
        # sinkron lampu
        self.update_lamp_ui_from_state()

        # sinkron AC
        self.update_ac_ui_from_state()

    def _safe_energy_value(self, value, max_limit=100000):
        """
        Convert value to float safely.
        Jika invalid / terlalu besar -> return 0
        """
        try:
            val = float(value)

            # jika nilai terlalu besar (bug device)
            if abs(val) > max_limit:
                return 0

            return round(val, 2)

        except (ValueError, TypeError):
            return 0
                    
# Run Application Mantap Sekali 
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())
