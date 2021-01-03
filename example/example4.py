#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.path.append('../')
import argparse
import time
from threading import Timer

from bluepy.btle import Peripheral, BTLEException

from omron_env_sensor import OmronRequestPage, OmronResponseFlag, OmronResponseData


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


def write_request_page(ble_peripheral: Peripheral, page: int, row: int):
    assert 0 <= page <= 2047
    assert 0 <= row <= 12

    request_page = OmronRequestPage()
    ble_service = ble_peripheral.getServiceByUUID(uuidVal=request_page.serviceUuid)
    ble_char = ble_service.getCharacteristics(forUUID=request_page.uuid)[0]

    write_value = request_page.encode_data(page, row)
    print(f'write_request_page(page={page}, row={row}) write_value={write_value}')
    ble_char.write(write_value)


def read_response_flag(ble_peripheral: Peripheral) -> OmronResponseFlag:
    response_flag = OmronResponseFlag()

    ble_service = ble_peripheral.getServiceByUUID(uuidVal=response_flag.serviceUuid)
    ble_char = ble_service.getCharacteristics(forUUID=response_flag.uuid)[0]

    print(f'read_response_flag')
    raw_data = ble_char.read()
    return response_flag.parse(raw_data)


def read_response_data(ble_peripheral: Peripheral):
    response_data = OmronResponseData()
    ble_service = ble_peripheral.getServiceByUUID(uuidVal=response_data.serviceUuid)
    ble_char = ble_service.getCharacteristics(forUUID=response_data.uuid)[0]

    print(f'read_response_data')
    raw_data = ble_char.read()
    return response_data.parse(raw_data)


def main():
    parser = argparse.ArgumentParser(description='OMRONの環境センサーから指定したページの観測データを読み出します。')
    parser.add_argument("--addr", required=True, type=str, help='環境センサーのMACアドレスを指定する')
    parser.add_argument("--page", type=int, default=0, help='読み出したいページ番号')
    parser.add_argument("--row", type=int, default=12, help='読み出したいページ行数')

    args = parser.parse_args()

    assert 0 <= args.page <= 2047
    assert 0 <= args.row <= 12

    # 環境センサーに接続する
    ble_peripheral = Peripheral()

    connect_with_timeout(ble_peripheral, addr=args.addr)

    # RequestPageを書き込む
    write_request_page(ble_peripheral, args.page, args.row)

    # ResponseFlgの読み出し
    is_ready_response_data = False
    for i in range(3):
        response_flag = read_response_flag(ble_peripheral)
        print(f'response_flag({i})={response_flag}')
        if response_flag.update_flag == 0x01:  # 更新完了
            is_ready_response_data = True
            break
        elif response_flag.update_flag == 0x00:  # 更新中
            continue
        else:  # 更新失敗
            print(f'ERROR: response flag failed.')
            raise IOError

    if not is_ready_response_data:
        print(f'ERROR: response flag failed.')
        raise IOError

    # 指定したページのデータの読み出し
    for i in range(args.row + 1):
        response_data = read_response_data(ble_peripheral)
        print(F'response_data[{i}] = {response_data}')

    ble_peripheral.disconnect()


if __name__ == "__main__":
    main()
