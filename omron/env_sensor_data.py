#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Omron 環境センサーから生データを読み出して、加工するためのクラス
import struct
from abc import ABCMeta, abstractmethod
from datetime import datetime
from typing import List

from bluepy.btle import UUID


class OmronEnvSensorBLEChara(metaclass=ABCMeta):
    """
    Omron環境センサーのBLE Characteristicsを扱うための基礎クラス

    """

    def __init__(self, short_uuid: int):
        self._shortUUID = short_uuid
        self._char_uuid = UUID('%08X-7700-46F4-AA96-D5E974E32A54' % (0x0C4C0000 + short_uuid))
        self._service_uuid = UUID('%08X-7700-46F4-AA96-D5E974E32A54' % (0x0C4C0000 + (0xFFF0 & short_uuid)))

    @property
    def shortUuid(self) -> int:
        """
        環境センサーのBLE Characteristicsの短いuuidを返す
        Returns
        -------
        uuid:int
            BLE Characteristicsの短いuuid
        """
        return self._shortUUID

    @property
    def uuid(self) -> UUID:
        """
        環境センサーのBLE Characteristicsのフルuuidを返す
        Returns
        -------
        uuid: UUID
            BLE Characteristicsのフルuuid
        """
        return self._char_uuid

    @property
    def serviceUuid(self) -> UUID:
        """
        環境センサーのBLE Characteristicsの親になっているBLE Serviceのフルuuidを返す
        Returns
        -------
        uuid: UUID
            BLE Characteristicsの親になっているBLE Serviceのフルuuidを返す
        """

        return self._service_uuid

    @abstractmethod
    def parse(self, raw_data: bytes):
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        pass


# noinspection SpellCheckingInspection
class OmronLatestData(OmronEnvSensorBLEChara):
    """
        Omron環境センサーのLatest Dataを扱うクラス
    """

    def __init__(self):
        OmronEnvSensorBLEChara.__init__(self, 0x3001)
        self.row = None
        self.temperature = None
        self.humidity = None
        self.light = None
        self.uv = None
        self.barometric_pressure = None
        self.noise = None
        self.discomfort_index = None
        self.heat_stroke = None
        self.battery_level = None

    def parse(self, raw_data: bytes):
        (row, temp, humid, light, uv, press, noise, discom,
         heat, batt) = struct.unpack('<BhhhhhhhhH', raw_data)

        self.row = row
        self.temperature = temp / 100
        self.humidity = humid / 100
        self.light = light
        self.uv = uv / 100
        self.barometric_pressure = press / 10
        self.noise = noise / 100
        self.discomfort_index = discom / 100
        self.heat_stroke = heat / 100
        self.battery_level = batt / 1000

        return self

    def __str__(self):
        tmp = self.to_dict()
        return f'{tmp}'

    def to_dict(self) -> dict:
        return dict(row=self.row,
                    temperature=self.temperature,
                    humidity=self.humidity,
                    light=self.light,
                    uv=self.uv,
                    barometric_pressure=self.barometric_pressure,
                    noise=self.noise,
                    discomfort_index=self.discomfort_index,
                    heat_stroke=self.heat_stroke,
                    battery_level=self.battery_level)


# noinspection SpellCheckingInspection
class OmronLatestPage(OmronEnvSensorBLEChara):
    """
        Omron環境センサーのLatest Pageを扱うクラス
    """

    # ページとして指定できる範囲
    DEVICE_PAGE_RANGE = range(0, 2048)

    def __init__(self, arg_page=None):
        OmronEnvSensorBLEChara.__init__(self, 0x3002)
        self.unix_time = None
        self.measurement_interval = None
        self.page = arg_page
        self.row = None

    def parse(self, raw_data: bytes):
        (self.unix_time, self.measurement_interval, self.page, self.row) = struct.unpack('<LHHB', raw_data)
        return self

    @property
    def datetime(self):
        return datetime.fromtimestamp(self.unix_time).astimezone()

    def __str__(self):
        tmp = self.to_dict()
        return f'{tmp}'

    def to_dict(self) -> dict:
        return dict(unix_time=self.unix_time,
                    datetime=self.datetime.isoformat(),
                    measurement_interval=self.measurement_interval,
                    page=self.page,
                    row=self.row
                    )

    def calcPage(self, last_read_page=0) -> List[int]:
        """
        読み出し範囲のページを計算してリストを返す
        Parameters
        ----------
        last_read_page: int
            最後に読み込んで保存しているページ

        Returns
        -------

        """
        if not self.page in self.DEVICE_PAGE_RANGE:
            raise IndexError(F"page={self.page} is out of bound of page range {self.DEVICE_PAGE_RANGE:}")

        if not last_read_page in self.DEVICE_PAGE_RANGE:
            raise IndexError(
                F"local_newest_page={last_read_page} is out of bound of page range {self.DEVICE_PAGE_RANGE:}")

        if last_read_page <= self.page:
            return [*range(last_read_page, self.page + 1)]
        else:
            return [*range(last_read_page, max(self.DEVICE_PAGE_RANGE) + 1),
                    *range(min(self.DEVICE_PAGE_RANGE), self.page + 1)]


class OmronRequestPage(OmronEnvSensorBLEChara):
    """
        Omron環境センサーのRequest Pageを扱うクラス
    """

    def __init__(self):
        OmronEnvSensorBLEChara.__init__(self, 0x3003)

    def parse(self, raw_data: bytes) -> dict:
        pass

    @staticmethod
    def encode_data(page: int, row: int) -> bytes:
        return struct.pack("<HB", page, row)

    def to_dict(self) -> dict:
        return dict()


class OmronResponseFlag(OmronEnvSensorBLEChara):
    """
        Omron環境センサーのResponse Flagを扱うクラス
    """

    def __init__(self):
        OmronEnvSensorBLEChara.__init__(self, 0x3004)
        self.update_flag = None
        self.unix_time = None

    def parse(self, raw_data: bytes):
        (self.update_flag, self.unix_time) = struct.unpack('<BL', raw_data)
        return self

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.unix_time).astimezone()

    def __str__(self):
        tmp = self.to_dict()
        return f'{tmp}'

    def to_dict(self) -> dict:
        return dict(update_flag=self.update_flag,
                    unix_time=self.unix_time,
                    datetime=self.datetime.isoformat()
                    )


# noinspection SpellCheckingInspection
class OmronResponseData(OmronEnvSensorBLEChara):
    """
        Omron環境センサーのResponse Dataを扱うクラス
    """

    def __init__(self):
        OmronEnvSensorBLEChara.__init__(self, 0x3005)
        self.row = None
        self.temperature = None
        self.humidity = None
        self.light = None
        self.uv = None
        self.barometric_pressure = None
        self.noise = None
        self.discomfort_index = None
        self.heat_stroke = None
        self.battery_level = None

    def parse(self, raw_data: bytes):
        (row, temp, humid, light, uv, press, noise, discom,
         heat, batt) = struct.unpack('<BhhhhhhhhH', raw_data)

        self.row = row
        self.temperature = temp / 100
        self.humidity = humid / 100
        self.light = light
        self.uv = uv / 100
        self.barometric_pressure = press / 10
        self.noise = noise / 100
        self.discomfort_index = discom / 100
        self.heat_stroke = heat / 100
        self.battery_level = batt / 1000

        return self

    def __str__(self):
        tmp = self.to_dict()
        return f'{tmp}'

    def to_dict(self) -> dict:
        return dict(row=self.row,
                    temperature=self.temperature,
                    humidity=self.humidity,
                    light=self.light,
                    uv=self.uv,
                    barometric_pressure=self.barometric_pressure,
                    noise=self.noise,
                    discomfort_index=self.discomfort_index,
                    heat_stroke=self.heat_stroke,
                    battery_level=self.battery_level)


class OmronMeasurementInterval(OmronEnvSensorBLEChara):
    """
        Omron環境センサーのMeasurement Intervalを扱うクラス
    """

    def __init__(self):
        OmronEnvSensorBLEChara.__init__(self, 0x3011)
        self.measurement_interval = None

    def parse(self, raw_data: bytes):
        self.measurement_interval = struct.unpack('<H', raw_data)[0]
        return self

    def __str__(self):
        tmp = self.to_dict()
        return f'{tmp}'

    def to_dict(self):
        return dict(measurement_interval=self.measurement_interval)

    @staticmethod
    def encode_data(interval_sec: int) -> bytes:
        # TODO テスト
        assert 1 <= interval_sec <= 3600
        return struct.pack("<H", interval_sec)


class OmronTimeInformation(OmronEnvSensorBLEChara):
    """
        Omron環境センサーのTime Informationを扱うクラス
    """

    def __init__(self):
        OmronEnvSensorBLEChara.__init__(self, 0x3031)
        self.unix_time = None

    def parse(self, raw_data: bytes):
        self.unix_time = struct.unpack('<L', raw_data)[0]
        return self

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.unix_time).astimezone()

    def __str__(self):
        tmp = self.to_dict()
        return f'{tmp}'

    def to_dict(self):
        return dict(unix_time=self.unix_time,
                    datetime=self.datetime.isoformat()
                    )

    @staticmethod
    def encode_data(unix_time: int) -> bytes:
        # TODO テスト
        return struct.pack("<L", unix_time)


# noinspection SpellCheckingInspection
class OmronErrorStatus(OmronEnvSensorBLEChara):
    """
        Omron環境センサーのError Statusを扱うクラス
    """

    def __init__(self):
        OmronEnvSensorBLEChara.__init__(self, 0x3033)
        self.sensor_status = None
        self.cpu_status = None
        self.battery_status = None
        self.rfu = None

    def parse(self, raw_data: bytes):
        (self.sensor_status, self.cpu_status, self.battery_status, self.rfu) = struct.unpack('<BBBB', raw_data)
        return self

    def __str__(self):
        tmp = self.to_dict()
        return f'{tmp}'

    def existsError(self) -> bool:
        return any([self.sensor_status, self.cpu_status, self.battery_status, self.rfu])

    def to_dict(self) -> dict:
        return dict(sensor_status=self.sensor_status,
                    cpu_status=self.cpu_status,
                    battery_status=self.battery_status,
                    rfu=self.rfu
                    )


class LogData:
    """
    環境センサーから読みだしたデータ(ResponseData)をDBに保存するための中間データ
    ResponseDataの開始時刻(page_start_unixtime)と、
    計測間隔(measurement_interval)、
    ResponseDataのrowからデータの測定時刻を算出し、datetime形式にして保存します。
    """

    def __init__(self, ble_address: str,
                 page: int,
                 page_start_unixtime: int,
                 measurement_interval: int,
                 response_data: OmronResponseData):
        """

        Parameters
        ----------
        ble_address: 環境センサーのBLE MACアドレス
        page: 測定データのページ
        page_start_unixtime: 測定データの観測開始時刻
        measurement_interval: 環境センサーの測定間隔
        response_data: 観測データ
        """
        self.ble_address = ble_address
        self.page = page
        self.response_data = response_data

        log_unix_time = page_start_unixtime + measurement_interval * response_data.row
        log_timestamp = datetime.fromtimestamp(log_unix_time).astimezone()
        self.timestamp = log_timestamp

    def __str__(self):
        tmp = self.to_dict()
        return f'{tmp}'

    def to_dict(self) -> dict:
        """
        データをdictにして返す
        Returns
        -------
        dict
        """
        return dict(timestamp=self.timestamp,
                    ble_address=self.ble_address,
                    page=self.page,
                    response_data=self.response_data
                    )

    def to_flat_dict(self) -> dict:
        """
        データをflatなdictにして返す
        Returns
        -------
        dict
        """
        data = dict(timestamp=self.timestamp,
                    ble_address=self.ble_address,
                    page=self.page)
        data.update(self.response_data.to_dict())
        return data
