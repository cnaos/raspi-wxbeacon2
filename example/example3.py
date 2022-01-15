#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.path.append('../')
import argparse
import time

from bluepy.btle import Peripheral, BTLEException

from omron.env_sensor_data import OmronLatestData


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
    latest_data = OmronLatestData()
    service = ble_peripheral.getServiceByUUID(uuidVal=latest_data.serviceUuid)

    # BLE Characteristicsを取得
    ble_char = service.getCharacteristics(forUUID=latest_data.uuid)[0]

    # LatestDataから測定データの読み出し
    raw_data = ble_char.read()

    # 生の測定データを変換
    latest_data.parse(raw_data)

    # 変換結果を表示
    print(f"latest_data={latest_data.to_dict()}")


if __name__ == "__main__":
    main()
