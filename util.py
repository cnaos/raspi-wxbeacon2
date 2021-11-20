#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from datetime import datetime

# from main import LogData
from omron.env_sensor_data import OmronEnvSensorBLEChara, OmronResponseData


class DateTimeSupportJSONEncoder(json.JSONEncoder):
    """
    datetimeをjsonでiso8601形式の日付文字列としてエンコードするためのコンバータ
    """

    def default(self, o):
        if isinstance(o, LogData):
            return o.to_dict()

        if isinstance(o, OmronEnvSensorBLEChara):
            return o.to_dict()

        if isinstance(o, datetime):
            return o.isoformat()

        return super(DateTimeSupportJSONEncoder, self).default(o)


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
