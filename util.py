#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from datetime import datetime

# from main import LogData
from omron.env_sensor_data import OmronEnvSensorBLEChara, LogData


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


