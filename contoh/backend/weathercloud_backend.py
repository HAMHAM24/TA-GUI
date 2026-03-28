import requests


class WeatherCloudBackend:
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.url = f"https://app.weathercloud.net/device/values/{device_id}"

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://app.weathercloud.net/device/{device_id}",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }

    # ==========================================
    def fetch(self) -> dict:
        r = requests.get(self.url, headers=self.headers, timeout=10)
        r.raise_for_status()

        data = r.json()   # <-- PERSIS seperti script kamu

        # === MAPPING LANGSUNG DARI DATA NYATA ===
        return {
            "temperature": data.get("temp"),
            "humidity": data.get("hum"),
            "pressure": data.get("bar"),

            "wind_speed": data.get("wspd"),
            "wind_speed_avg": data.get("wspdavg"),
            "wind_direction": data.get("wdir"),

            "rain_total": data.get("rain"),
            "rain_rate": data.get("rainrate"),

            "heat_index": data.get("heat"),
        }
