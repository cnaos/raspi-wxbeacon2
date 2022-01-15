import json
import logging
import time
from logging import DEBUG, INFO, ERROR, WARN
from typing import List

import bluepy
from bluepy import btle
from bluepy.btle import Peripheral
from retry import retry

from omron.env_sensor_data import OmronLatestData, OmronLatestPage, OmronRequestPage, OmronResponseFlag, \
    OmronResponseData, OmronTimeInformation, OmronMeasurementInterval, OmronErrorStatus, LogData
from util import DateTimeSupportJSONEncoder

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.propagate = True

BLE_READ_CHARA_WAIT_SEC = 100 / 1000  # 50 msec
BLE_READ_WAIT_SEC = 50 / 1000  # 50 msec
BLE_WRITE_WAIT_SEC = 50 / 1000  # 50 msec


class OmronEnvSensor:

    @retry(tries=3, delay=1, logger=logger)
    def __init__(self, address: str):
        super().__init__()
        self.address = address
        self.ble_peripheral = Peripheral(address, addrType=bluepy.btle.ADDR_TYPE_RANDOM)
        self.ble_peripheral.discoverServices()

    @property
    def peripheral(self):
        return self.ble_peripheral

    # @retry(tries=5, delay=1, logger=logger)
    def read_char_base(self, service_uuid, char_uuid) -> (btle.Characteristic, bytes):
        """
        BLEのCharacteristicsを読む

        Args:
            service_uuid: Omron環境センサBLEサービスのshort UUID
            char_uuid: Omron環境センサBLE Characteristicsのshort UUID

        Returns:
            (btle.Characteristic, bytes):
        """
        time.sleep(BLE_READ_CHARA_WAIT_SEC)
        service = self.ble_peripheral.getServiceByUUID(uuidVal=service_uuid)
        ble_char = service.getCharacteristics(forUUID=char_uuid)[0]

        time.sleep(BLE_READ_WAIT_SEC)
        raw_data = ble_char.read()
        return ble_char, raw_data

    # @retry(tries=5, delay=1, logger=logger)
    def write_char_base(self, service_uuid, char_uuid, write_value: bytes) -> None:
        """
        BLEのCharacteristicsに値を書く

        Args:
            service_uuid: Omron環境センサBLEサービスのshort UUID
            char_uuid: Omron環境センサBLE Characteristicsのshort UUID
            write_value: 書き込む値

        Returns:
            None
        """

        time.sleep(BLE_READ_CHARA_WAIT_SEC)
        service = self.ble_peripheral.getServiceByUUID(uuidVal=service_uuid)
        ble_char = service.getCharacteristics(forUUID=char_uuid)[0]

        time.sleep(BLE_WRITE_WAIT_SEC)
        ble_char.write(write_value)

    def __MSG(self, level: int, *args) -> None:
        """
        Bluetoothデバイスのアドレスをつけてログ出力する

        Args:
            level: ログ出力レベル
            *args: ログ出力内容

        Returns:
            None
        """

        msg = " ".join([str(a) for a in args])
        logger.log(level, F'{self.address}: {msg}')

    def read_device_name(self) -> str:
        """
        BLEデバイスの名前を読む(Generic Access:0x1800, Device Name:0x2a00)

        Returns:
            str: BLEデバイスの名前
        """
        (ble_chara, raw_data) = self.read_char_base(0x1800, 0x2a00)
        str_device_name = raw_data.decode('utf-8')
        self.__MSG(DEBUG, f'char={ble_chara}, raw_data={raw_data}, str={str_device_name}')
        return str_device_name

    def check_omron_env_sensor(self) -> bool:
        """
        デバイスがOmronの環境センサーかどうかを判定する

        Returns:
            bool: TrueならOmronの環境センサー

        """
        str_device_name = self.read_device_name()
        if str_device_name == "EnvSensor-BL01":
            return True
        else:
            self.__MSG(WARN, f'this device is not OMRON ')
            return False

    def read_latest_data(self) -> OmronLatestData:
        """
        環境センサーのLatest Dataを読み出す

        Returns:
            LatestData
        """

        latest_data = OmronLatestData()

        self.__MSG(DEBUG, F'reading LatestData(uuid={latest_data.shortUuid:#04x})')
        (ble_chara, raw_data) = self.read_char_base(latest_data.serviceUuid, latest_data.uuid)
        return latest_data.parse(raw_data)

    def read_latest_page(self) -> OmronLatestPage:
        """
        環境センサーのLatest Pageを読み出す

        Returns:
            LatestPage
        """

        latest_page = OmronLatestPage()

        self.__MSG(DEBUG, F'reading LatestPage(uuid={latest_page.shortUuid:#04x})')
        (ble_chara, raw_data) = self.read_char_base(latest_page.serviceUuid, latest_page.uuid)
        return latest_page.parse(raw_data)

    def write_request_page(self, page: int, row: int) -> None:
        """
        環境センサーへ読み出したいページのRequest Page要求を出す

        Args:
            page: 読み出したいページ番号 0から2047
            row: 読み出したい行数の指定 0で1行、 12で13行読み出されるっぽい

        Returns:
            None
        """
        assert 0 <= page <= 2047
        assert 0 <= row <= 12
        request_page = OmronRequestPage()
        data = request_page.encode_data(page, row)

        self.__MSG(DEBUG, F'writing RequestPage(uuid={request_page.shortUuid:#04x}): data={data}')
        self.write_char_base(request_page.serviceUuid, request_page.uuid, data)

    def read_response_flag(self) -> OmronResponseFlag:
        """
        環境センサーのResponse Flagを読み出す。

        Returns:
            ResponseFlag
        """
        response_flag = OmronResponseFlag()

        self.__MSG(DEBUG, F'reading ResponseFlag(uuid={response_flag.shortUuid:#04x})')
        (ble_chara, raw_data) = self.read_char_base(response_flag.serviceUuid, response_flag.uuid)
        return response_flag.parse(raw_data)

    def read_response_data(self) -> OmronResponseData:
        """
        環境センサーのResponse Dataを読み出す

        Returns:
            ResponseData
        """
        response_data = OmronResponseData()

        self.__MSG(DEBUG, F'reading ResponseData(uuid={response_data.shortUuid:#04x})')
        (ble_chara, raw_data) = self.read_char_base(response_data.serviceUuid, response_data.uuid)
        return response_data.parse(raw_data)

    def read_time_information(self) -> OmronTimeInformation:
        """
        環境センサーのTime Informationを読み出す
        Returns:
            TimeInformation
        """

        time_information = OmronTimeInformation()

        self.__MSG(DEBUG, F'reading TimeInformation(uuid={time_information.shortUuid:#04x})')
        (ble_chara, raw_data) = self.read_char_base(time_information.serviceUuid, time_information.uuid)
        return time_information.parse(raw_data)

    def read_measurement_interval(self) -> OmronMeasurementInterval:
        """
        環境センサーのMeasurement Intervalを読み出す

        Returns:
            MeasurementInterval
        """
        measurement_interval = OmronMeasurementInterval()

        self.__MSG(DEBUG, F'reading MeasurementInterval(uuid={measurement_interval.shortUuid:#04x})')
        (ble_chara, raw_data) = self.read_char_base(measurement_interval.serviceUuid, measurement_interval.uuid)
        return measurement_interval.parse(raw_data)

    def read_error_status(self) -> OmronErrorStatus:
        """
        環境センサーのError Statusを読み出す

        Returns:
            ErrorStatus
        """
        error_status = OmronErrorStatus()

        self.__MSG(DEBUG, F'reading ErrorStatus(uuid={error_status.shortUuid:#04x})')
        (ble_chara, raw_data) = self.read_char_base(error_status.serviceUuid, error_status.uuid)
        return error_status.parse(raw_data)

    # @retry(tries=3, delay=1, logger=logger)
    def write_read_page_and_wait_ready(self, page: int, row: int) -> OmronResponseFlag:
        """
        環境センサーに読み出したいページを指定して、準備が完了するまで待つ

        Args:
            page: 読み出したいページ番号 0から2047
            row: 読み出したい行数の指定 0で1行、 12で13行読み出されるっぽい

        Returns:
            ResponseFlag

        """
        assert 0 <= page <= 2047
        assert 0 <= row <= 12
        self.write_request_page(page, row)
        for i in range(3):
            response_flag = self.read_response_flag()
            self.__MSG(DEBUG, F'response_flag={response_flag}')
            if response_flag.update_flag == 0x01:  # 更新完了
                return response_flag
            elif response_flag.update_flag == 0x00:  # 更新中
                continue
            else:  # 更新失敗
                self.__MSG(ERROR, F'response flag failed.')
                raise IOError
        self.__MSG(ERROR, F'read response flag failed after retry.')
        raise IOError

    # @retry(tries=3, delay=1, logger=logger)
    def read_env_sensor_data(self, page: int, latest_page: OmronLatestPage) -> List[LogData]:
        """
        環境センサーの指定ページを読み出す

        Args:
            page: 読み出し対象ページ
            latest_page: 環境センサーのLatestPage、最新ページの読み出し行数の指定と観測データの時刻計算にmeasurement_intervalを使う

        Returns:
            List[LogData]: 読みだした観測データのリスト
        """
        try:
            target_row = 12 if page != latest_page.page else latest_page.row  # 最新ページ以外は13行の読み出し

            response_flag = self.write_read_page_and_wait_ready(page, target_row)
            self.__MSG(INFO, f'page = {page}, start_time={response_flag.datetime} ({response_flag.unix_time})')

            page_data = []
            for i in range(13 + 3):  # 1ページ分のデータは最大13件だけど、予備で3回追加しておく
                response_data = self.read_response_data()
                self.__MSG(DEBUG, F'response_data = {response_data}')
                page_data.append(response_data)
                if response_data is None or response_data.row == 0:
                    break

            list_log_data = list(
                map(lambda it: LogData(self.address,
                                       page,
                                       response_flag.unix_time,
                                       latest_page.measurement_interval,
                                       it),
                    page_data))

            self.__MSG(DEBUG, F'list_log_data={json.dumps(list_log_data, cls=DateTimeSupportJSONEncoder)}')
            return list_log_data
        except Exception as e:
            logger.exception(f"read_env_sensor_data failed: {e}")
            raise e

    def write_measurement_interval(self, new_measurement_interval: int) -> None:
        """
        測定間隔を変更する

        Args:
            new_measurement_interval: 測定間隔(秒) 1から3600

        Returns:
            None
        """
        assert 1 <= new_measurement_interval <= 3600
        measurement_interval = OmronMeasurementInterval()
        data = measurement_interval.encode_data(new_measurement_interval)

        self.__MSG(DEBUG, F'writing MeasurementInterval(uuid={measurement_interval.shortUuid:#04x}): data={data}')
        self.write_char_base(measurement_interval.serviceUuid, measurement_interval.uuid, data)

    def write_time_information(self, unix_time) -> None:
        """
        環境センサーへ現在時刻を設定する

        Args:
            unix_time: 現在時刻のunixタイムスタンプ

        Returns:
            None
        """
        time_information = OmronTimeInformation()
        data = time_information.encode_data(unix_time)

        self.__MSG(DEBUG, F'writing TimeInformation(uuid={time_information.shortUuid:#04x}): data={data}')
        self.write_char_base(time_information.serviceUuid, time_information.uuid, data)
