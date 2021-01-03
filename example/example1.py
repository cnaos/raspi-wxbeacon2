#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import struct

from bluepy.btle import Peripheral, UUID

OMRON_LATEST_DATA_UUID = UUID('%08X-7700-46F4-AA96-D5E974E32A54' % (0x0C4C0000 + 0x3001))
OMRON_SENSOR_SERVICE_UUID = UUID('%08X-7700-46F4-AA96-D5E974E32A54' % (0x0C4C0000 + (0xFFF0 & 0x3000)))

parser = argparse.ArgumentParser(description='OMRONの環境センサーからLatestDataを取得します')
parser.add_argument("--addr", required=True, type=str, help='環境センサーのMACアドレスを指定する')

args = parser.parse_args()

# 環境センサーに接続する
ble_peripheral = Peripheral()
print(f"connecting... {args.addr}")
ble_peripheral.connect(addr=args.addr, addrType="random")
print(f"ble_peripheral={ble_peripheral}")

# BLE サービスを取得
service = ble_peripheral.getServiceByUUID(uuidVal=OMRON_SENSOR_SERVICE_UUID)
print(f"service = {service}")

# BLE Characteristicsを取得
ble_char = service.getCharacteristics(forUUID=OMRON_LATEST_DATA_UUID)[0]
print(f"ble_char = {ble_char}")

# LatestDataから測定データの読み出し
raw_data = ble_char.read()
print(f"raw_data = {raw_data}")

# 生の測定データを変換
(row_number, temperature, humidity, light, uv_index, pressure, noise, discomfort_index, heat_stroke,
 battery_level) = struct.unpack('<BhhhhhhhhH', raw_data)
temperature /= 100
humidity /= 100
uv_index /= 100
pressure /= 10
noise /= 100
discomfort_index /= 100
heat_stroke /= 100
battery_level /= 1000

# 変換結果を表示
print(
    f"temperature = {temperature}, humidity = {humidity}, uv_index={uv_index}, pressure={pressure}, noise={noise}"
    f", discomfort_index={discomfort_index}, heat_stroke={heat_stroke}, battery_level={battery_level}")
