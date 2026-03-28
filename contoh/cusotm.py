import asyncio
from bleak import BleakClient, BleakScanner

SERVICE_UUID = "12345678-1234-1234-1234-1234567890ab"
CHAR_UUID    = "abcd1234-5678-1234-5678-abcdef123456"

async def main():
    devices = await BleakScanner.discover()
    esp = None

    for d in devices:
        if d.name == "ESP32-C3-Macropad":
            esp = d

    if not esp:
        print("ESP32 not found")
        return

    async with BleakClient(esp.address) as client:
        print("Connected to ESP32")

        # 🔑 READ DULU (INI KUNCI)
        value = await client.read_gatt_char(CHAR_UUID)
        print("Initial read:", value.decode())

        def callback(sender, data):
            print("Received:", data.decode())

        # 🔑 BARU notify
        await client.start_notify(CHAR_UUID, callback)

        print("Listening...")
        while True:
            await asyncio.sleep(1)

asyncio.run(main())
