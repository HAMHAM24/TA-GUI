import growattServer


class GrowattBackend:
    def __init__(self):
        # ================= CREDENTIAL =================
        self.username = "EcoLab"
        self.password = "ecolab321"

        self.api = growattServer.GrowattApi(
            agent_identifier="ShinePhone/8.1.17 (Android)"
        )

        # ================= LOGIN =================
        self.api.login(self.username, self.password)

        self.plant_id = self.api.plant_list_two()[0]["id"]

    # =================================================
    def fetch(self) -> dict:
        devices = self.api.device_list(self.plant_id)

        storage_sn = None
        for d in devices:
            if d.get("deviceType") == "storage":
                storage_sn = d.get("deviceSn")
                break

        if not storage_sn:
            raise RuntimeError("Storage device tidak ditemukan")

        storage = self.api.storage_params(storage_sn)["storageDetailBean"]

        # ================= POWER =================
        pv_power = int(storage.get("ppv2", 0))
        grid_import = int(storage.get("pAcInPut", 0))
        battery_power = float(storage.get("pBat", 0))
        soc = int(storage.get("capacity", 0))
        load_power = int(storage.get("outPutPower", 0))
        rateVA = int(storage.get("rateVA", 0))

        # ================= ENERGY =================
        pv_today = float(storage.get("epvToday", 0))
        pv_total = float(storage.get("epvTotal", 0))

        charge_today = float(storage.get("eChargeToday", 0))
        charge_total = round(float(storage.get("eChargeTotal", 0)), 1)


        discharge_today = float(storage.get("eDischargeToday", 0))
        discharge_total = float(storage.get("eDischargeTotal", 0))

        load_today = float(storage.get("eopDischrToday", 0))
        load_total = float(storage.get("eopDischrTotal", 0))

        grid_today = (
            float(storage.get("eacChargeToday", 0)) +
            float(storage.get("eacDisChargeToday", 0))
        )

        grid_total = (
            float(storage.get("eacChargeTotal", 0)) +
            float(storage.get("eacDisChargeTotal", 0))
        )
        
        
        storagepopup = self.api.storage_params(storage_sn)["storageDetailBean"]
        
        flow_info = {
            # 🔋 Battery
            "battery_voltage": storagepopup.get("vBat"),

            # ☀️ PV
            "pv1_voltage": storagepopup.get("vpv"),
            "pv2_voltage": storagepopup.get("vpv2"),
            "pv1_charge_current": storagepopup.get("iChargePV1"),
            "pv2_charge_current": storagepopup.get("iChargePV2"),
            "rateVA":storagepopup.get("rateVA"),

            # 🔌 Charging
            "total_charge_current": storagepopup.get("chgCurr"),

            # ⚡ AC Input
            "ac_input_voltage": storagepopup.get("vGrid"),
            "ac_input_frequency": storagepopup.get("freqGrid"),

            # ⚡ AC Output
            "ac_output_voltage": storagepopup.get("outPutVolt"),
            "ac_output_frequency": storagepopup.get("freqOutPut"),

            # 🏠 Load
            "consumption_power": storagepopup.get("outPutPower"),
            "load_percentage": storagepopup.get("loadPercent"),
        }

        # ================= RETURN =================
        return {
            # POWER (W)
            "pv_power": pv_power,
            "grid_import_power": grid_import,
            "battery_power": battery_power,
            "load_power": load_power,
            "rateVA_power":rateVA,

            # BATTERY
            "soc": soc,

            # ENERGY
            "pv_today": pv_today,
            "pv_total": pv_total,
            
            
            "battery_charge_today": charge_today,
            "battery_charge_total": charge_total,
            "battery_discharge_today": discharge_today,
            "battery_discharge_total": discharge_total,

            "load_today": load_today,
            "load_total": load_total,

            "grid_today": grid_today,
            "grid_total": grid_total,
            
            # 🔥 DATA BARU UNTUK POPUP
            "flow_info": flow_info,
        }
        
        
