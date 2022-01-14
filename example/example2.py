#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import struct
import time

from bluepy.btle import Peripheral, UUID, BTLEException

OMRON_LATEST_DATA_UUID = UUID('%08X-7700-46F4-AA96-D5E974E32A54' % (0x0C4C0000 + 0x3001))
OMRON_SENSOR_SERVICE_UUID = UUID('%08X-7700-46F4-AA96-D5E974E32A54' % (0x0C4C0000 + (0xFFF0 & 0x3000)))


def connect(addr: str, max_retry=5, retry_interval_sec=1) -> Peripheral:
    ble_peripheral = None
    is_connected = False
    for i in range(max_retry):
        try:
            print(f'connecting to {addr} {i + 1}/{max_retry}')
            ble_peripheral = Peripheral(deviceAddr=addr, addrType="random")
        except BTLEException as e:
            print(f'ERROR: try {i + 1}: BTLE Exception while connecting ')
            print(f'ERROR:   type:' + str(type(e)))
            print(f'ERROR:   args:' + str(e.args))
            time.sleep(retry_interval_sec)
        else:
            is_connected = True
            print(f'connected.')
            return ble_peripheral

    if not is_connected:
        print(f"ERROR: connect failed.")
        raise Exception(F"BTLE connect to {addr} failed.")


def main():
    parser = argparse.ArgumentParser(description='OMRONの環境センサーからLatestDataを取得します')
    parser.add_argument("--addr", required=True, type=str, help='環境センサーのMACアドレスを指定する')

    args = parser.parse_args()

    # 環境センサーに接続する
    ble_peripheral = connect(addr=args.addr)

    # BLE サービスを取得
    service = ble_peripheral.getServiceByUUID(uuidVal=OMRON_SENSOR_SERVICE_UUID)

    # BLE Characteristicsを取得
    ble_char = service.getCharacteristics(forUUID=OMRON_LATEST_DATA_UUID)[0]

    # LatestDataから測定データの読み出し
    raw_data = ble_char.read()

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


if __name__ == "__main__":
    main()
