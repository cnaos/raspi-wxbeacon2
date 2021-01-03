#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.path.append('../')
import argparse
import time
from threading import Timer

from bluepy.btle import Peripheral, BTLEException

from omron_env_sensor import OmronLatestData


def connect_with_timeout(ble_peripheral: Peripheral, addr: str, timeout_sec=30, max_retry=5,
                         retry_interval_sec=5) -> None:
    is_connected = False
    for i in range(max_retry):
        try:
            print(f'connecting to {addr} {i + 1}/{max_retry}')
            connect_timer = Timer(timeout_sec, timeout_disconnect, args=[ble_peripheral])
            connect_timer.start()
            ble_peripheral.connect(addr=addr, addrType="random")
        except BTLEException as e:
            print(f'ERROR: try {i + 1}: BTLE Exception while connecting ')
            print(f'ERROR:   type:' + str(type(e)))
            print(f'ERROR:   args:' + str(e.args))
            time.sleep(retry_interval_sec)
        else:
            is_connected = True
            print(f'connected.')
            break
        finally:
            connect_timer.cancel()
            connect_timer.join()  # 完全にキャンセルするまで待つ

    if not is_connected:
        print(f"ERROR: connect failed.")
        raise Exception(F"BTLE connect to {addr} failed.")


def timeout_disconnect(ble_peripheral: Peripheral) -> None:
    print(f'ERROR connect timer expired')
    ble_peripheral.disconnect()


def main():
    parser = argparse.ArgumentParser(description='OMRONの環境センサーからLatestDataを取得します')
    parser.add_argument("--addr", required=True, type=str, help='環境センサーのMACアドレスを指定する')

    args = parser.parse_args()

    # 環境センサーに接続する
    ble_peripheral = Peripheral()

    connect_with_timeout(ble_peripheral, addr=args.addr)

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
