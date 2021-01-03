#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import functools
import json

from peewee import *
from playhouse.sqlite_ext import JSONField

from util import DateTimeSupportJSONEncoder

database_proxy = DatabaseProxy()

# datetimeをjsonにダンプするための関数設定
my_json_dumps = functools.partial(json.dumps, cls=DateTimeSupportJSONEncoder)


class EnvSensorDevice(Model):
    """環境センサーのDBエントリ

    Attributes:
        self.address (CharField): 環境センサーのMACアドレス
        self.label (CharField): 環境センサーにつける識別用のラベル
        self.time_information (IntegerField): デバイスの観測開始日時
    """
    address = CharField(unique=True)
    label = CharField(null=True)
    time_information = BigIntegerField(null=False)

    class Meta:
        database = database_proxy

    def latest_log(self):
        """DBの観測ログ(EnvSensorLog)から最新のlog_dateを持つレコードを返す

        Returns
        -------

        """
        query = (EnvSensorLog.select()
                 .join(EnvSensorDevice)
                 .where(EnvSensorLog.device == self)
                 .order_by(EnvSensorLog.log_date.desc())
                 .limit(1))
        for env_sensor_log in query:
            return env_sensor_log

        return None


class EnvSensorLog(Model):
    """環境センサーから読みだした定期観測ログデータのDBエントリ

    Attributes:
        self.device (ForeignKeyField): 環境センサーへの参照
        self.log_date (DateTimeField): 観測日時
        self.page (IntegerField): 観測データのページ番号
        self.data (JSONField): 観測データ
    """
    device = ForeignKeyField(EnvSensorDevice, backref='logs')
    log_date = DateTimeField(index=True)
    page = IntegerField()
    data = JSONField(json_dumps=my_json_dumps)

    class Meta:
        database = database_proxy
        indexes = (
            # create a unique on from/to/date
            (('device', 'log_date'), True),
        )


class EnvSensorCurrentDataLog(Model):
    """環境センサーから読みだした時点での観測ログデータ

    Attributes:
        self.device (EnvSensorDevice): 環境センサーへの参照
        self.log_date (DateTimeField): 観測日時
        self.data (JSONField): 観測データ
    """
    device = ForeignKeyField(EnvSensorDevice, backref='current_logs')
    log_date = DateTimeField(index=True)
    data = JSONField()

    class Meta:
        database = database_proxy
        indexes = (
            # create a unique on from/to/date
            (('device', 'log_date'), True),
        )


class InfluxdbPostPosition(Model):
    """
    SqliteからInfluxdbにどこまでPOSTしたかを記録する

    Attributes:
        self.post_log_position (IntegerField): InfluxdbへPostしたid
        self.timestamp (DateTimeField): InfluxdbへのPost時刻
    """
    post_log_position = IntegerField()
    timestamp = DateTimeField()

    class Meta:
        database = database_proxy
