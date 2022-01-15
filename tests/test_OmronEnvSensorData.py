import datetime

import pytest

from omron.env_sensor_data import OmronLatestData, OmronLatestPage, OmronTimeInformation, \
    OmronErrorStatus, OmronMeasurementInterval


class TestOmronLatestData:
    def test_serviceUuid(self):
        latest_data = OmronLatestData()
        assert str(latest_data.serviceUuid) == "0c4c3000-7700-46f4-aa96-d5e974e32a54"

    def test_uuid(self):
        latest_data = OmronLatestData()
        assert str(latest_data.uuid) == "0c4c3001-7700-46f4-aa96-d5e974e32a54"

    def test_shortUuid(self):
        latest_data = OmronLatestData()
        assert F'{latest_data.shortUuid:#0x}' == "0x3001"

    def test_parse(self):
        latest_data = OmronLatestData()
        data = b"\x06\x1d\n\x8a\x19\n\x00\x02\x00%'\x05\x0e+\x1db\ts\n"
        latest_data.parse(data)
        # latestData = {'row': 6, 'temp': 25.89, 'humid': 65.38, 'light': 10, 'uv': 0.02, 'press': 1002.1, 'noise': 35.89, 'discom': 74.67, 'heat': 24.02, 'batt': 2.675}
        assert latest_data.row == 6
        assert latest_data.temperature == 25.89
        assert latest_data.humidity == 65.38
        assert latest_data.light == 10
        assert latest_data.uv == 0.02
        assert latest_data.barometric_pressure == 1002.1
        assert latest_data.noise == 35.89
        assert latest_data.discomfort_index == 74.67
        assert latest_data.heat_stroke == 24.02
        assert latest_data.battery_level == 2.675

    def test_str(self):
        latest_data = OmronLatestData()
        data = b"\x06\x1d\n\x8a\x19\n\x00\x02\x00%'\x05\x0e+\x1db\ts\n"
        latest_data.parse(data)
        # latestData = {'row': 6, 'temp': 25.89, 'humid': 65.38, 'light': 10, 'uv': 0.02, 'press': 1002.1, 'noise': 35.89, 'discom': 74.67, 'heat': 24.02, 'batt': 2.675}
        assert str(latest_data) == "{'row': 6, 'temperature': 25.89, 'humidity': 65.38, 'light': 10, 'uv': 0.02, 'barometric_pressure': 1002.1, 'noise': 35.89, 'discomfort_index': 74.67, 'heat_stroke': 24.02, 'battery_level': 2.675}"

    def test_to_dict(self):
        latest_data = OmronLatestData()
        data = b"\x06\x1d\n\x8a\x19\n\x00\x02\x00%'\x05\x0e+\x1db\ts\n"
        latest_data.parse(data)
        dict_data = latest_data.to_dict()
        # latestData = {'row': 6, 'temp': 25.89, 'humid': 65.38, 'light': 10, 'uv': 0.02, 'press': 1002.1, 'noise': 35.89, 'discom': 74.67, 'heat': 24.02, 'batt': 2.675}
        assert type(dict_data) is dict
        assert dict_data["row"] == 6
        assert dict_data["temperature"] == 25.89
        assert dict_data["humidity"] == 65.38
        assert dict_data["light"] == 10
        assert dict_data["uv"] == 0.02
        assert dict_data["barometric_pressure"] == 1002.1
        assert dict_data["noise"] == 35.89
        assert dict_data["discomfort_index"] == 74.67
        assert dict_data["heat_stroke"] == 24.02
        assert dict_data["battery_level"] == 2.675


class TestOmronLatestPage:
    def test_service_uuid(self):
        latest_page = OmronLatestPage()
        assert str(latest_page.serviceUuid) == "0c4c3000-7700-46f4-aa96-d5e974e32a54"

    def test_uuid(self):
        latest_page = OmronLatestPage()
        assert str(latest_page.uuid) == "0c4c3002-7700-46f4-aa96-d5e974e32a54"

    def test_short_uuid(self):
        latest_page = OmronLatestPage()
        assert F'{latest_page.shortUuid:#0x}' == "0x3002"

    def test_parse(self):
        latest_page = OmronLatestPage()
        data = b'C\x91\xe5^,\x01\t\x02\x0b'
        latest_page.parse(data)
        # latestPage = {'unix_time': 1592103235, 'interval': 300, 'latest_page': 521, 'latest_row': 11}
        assert latest_page.unix_time == 1592103235
        assert latest_page.datetime.isoformat() == "2020-06-14T11:53:55+09:00"
        assert latest_page.measurement_interval == 300
        assert latest_page.page == 521
        assert latest_page.row == 11

    def test_str(self):
        latest_page = OmronLatestPage()
        data = b'C\x91\xe5^,\x01\t\x02\x0b'
        latest_page.parse(data)

        assert datetime.datetime.now().astimezone().tzname() == "JST"
        assert str(latest_page) == "{'unix_time': 1592103235, 'datetime': '2020-06-14T11:53:55+09:00', 'measurement_interval': 300, 'page': 521, 'row': 11}"

    def test_calcPage(self):
        latest_page = OmronLatestPage()
        data = b'C\x91\xe5^,\x01\t\x02\x0b'
        latest_page.parse(data)
        # latestPage = {'unix_time': 1592103235, 'interval': 300, 'latest_page': 521, 'latest_row': 11}
        assert latest_page.unix_time == 1592103235
        assert latest_page.datetime.isoformat() == "2020-06-14T11:53:55+09:00"
        assert latest_page.measurement_interval == 300
        assert latest_page.page == 521
        assert latest_page.row == 11


class TestOmronLatestPageExportPagePosition:
    def test_calcpage_latest_page_0_to_0(self):
        target = OmronLatestPage(0)
        result = target.calcPage(0)
        assert len(result) == 1
        assert str(result) == "[0]"
        assert result[0] == 0

    def test_calcpage_latest_page_0_to_1(self):
        target = OmronLatestPage(1)
        result = target.calcPage(0)
        assert len(result) == 2
        assert str(result) == "[0, 1]"
        assert result[0] == 0
        assert result[1] == 1

    def test_calcpage_latest_page_0_to_2047(self):
        target = OmronLatestPage(2047)
        result = target.calcPage(0)
        assert len(result) == 2048
        assert result[0] == 0
        assert result[2047] == 2047

    def test_calcpage_latest_page_0_to_2048_invalid(self):
        target = OmronLatestPage(0)
        with pytest.raises(IndexError):
            target.calcPage(2048)

    def test_calcpage_latest_page_0_to_minus1_invalid(self):
        target = OmronLatestPage(0)
        with pytest.raises(IndexError):
            target.calcPage(-1)

    def test_calcpage_latest_page_1_to_1(self):
        target = OmronLatestPage(1)
        result = target.calcPage(1)
        assert len(result) == 1
        assert str(result) == "[1]"
        assert result[0] == 1

    def test_calcpage_latest_page_1_to_2(self):
        target = OmronLatestPage(2)
        result = target.calcPage(1)
        assert len(result) == 2
        assert str(result) == "[1, 2]"
        assert result[0] == 1
        assert result[1] == 2

    def test_calcpage_latest_page_2046_to_2047(self):
        target = OmronLatestPage(2047)
        result = target.calcPage(2046)
        assert len(result) == 2
        assert str(result) == "[2046, 2047]"
        assert result[0] == 2046
        assert result[1] == 2047

    def test_calcpage_latest_page_2046_to_0(self):
        target = OmronLatestPage(0)
        result = target.calcPage(2046)
        assert len(result) == 3
        assert str(result) == "[2046, 2047, 0]"
        assert result[0] == 2046
        assert result[1] == 2047
        assert result[2] == 0

    def test_calcpage_latest_page_2046_to_1(self):
        target = OmronLatestPage(1)
        result = target.calcPage(2046)
        assert len(result) == 4
        assert str(result) == "[2046, 2047, 0, 1]"
        assert result[0] == 2046
        assert result[1] == 2047
        assert result[2] == 0
        assert result[3] == 1


class TestOmronTimeInformation:
    def test_serviceUuid(self):
        time_info = OmronTimeInformation()
        assert str(time_info.serviceUuid) == "0c4c3030-7700-46f4-aa96-d5e974e32a54"

    def test_uuid(self):
        time_info = OmronTimeInformation()
        assert str(time_info.uuid) == "0c4c3031-7700-46f4-aa96-d5e974e32a54"

    def test_short_uuid(self):
        time_info = OmronTimeInformation()
        assert F'{time_info.shortUuid:#0x}' == "0x3031"

    def test_parse(self):
        time_info = OmronTimeInformation()
        data = b'\xE3\x68\x3E\x5F'
        # data = {'unix_time': 1597925603, 'datetime': '2020-08-20T21:13:23+09:00'}
        time_info.parse(data)
        assert time_info.unix_time == 1597925603
        assert str(time_info.datetime.isoformat()) == "2020-08-20T21:13:23+09:00"

class TestOmronMeasurementInterval:
    def test_serviceUuid(self):
        measurementInterval = OmronMeasurementInterval()
        assert str(measurementInterval.serviceUuid) == "0c4c3010-7700-46f4-aa96-d5e974e32a54"

    def test_uuid(self):
        measurement_interval = OmronMeasurementInterval()
        assert str(measurement_interval.uuid) == "0c4c3011-7700-46f4-aa96-d5e974e32a54"

    def test_short_uuid(self):
        measurement_interval = OmronMeasurementInterval()
        assert F'{measurement_interval.shortUuid:#0x}' == "0x3011"


class TestErrorStatus:
    def test_serviceUuid(self):
        error_status = OmronErrorStatus()
        assert str(error_status.serviceUuid) == "0c4c3030-7700-46f4-aa96-d5e974e32a54"

    def test_uuid(self):
        error_status = OmronErrorStatus()
        assert str(error_status.uuid) == "0c4c3033-7700-46f4-aa96-d5e974e32a54"

    def test_short_uuid(self):
        error_status = OmronErrorStatus()
        assert F'{error_status.shortUuid:#0x}' == "0x3033"

    def test_parse(self):
        error_status = OmronErrorStatus()
        data = b'\x00\x01\x01\x00'
        error_status.parse(data)
        dict_data = error_status.to_dict()

        # error_status = {'sensor_status': 0, 'cpu_status': 1, 'battery_status': 1, 'rfu': 0}
        assert type(dict_data) is dict
        assert dict_data["sensor_status"] == 0
        assert dict_data["cpu_status"] == 1
        assert dict_data["battery_status"] == 1
        assert dict_data["rfu"] == 0

        assert error_status.existsError()

    def test_existsError_noError(self):
        error_status = OmronErrorStatus()
        data = b'\x00\x00\x00\x00'
        error_status.parse(data)

        assert error_status.existsError() == False

    def test_existsError_error1(self):
        error_status = OmronErrorStatus()
        data = b'\x01\x00\x00\x00'
        error_status.parse(data)

        assert error_status.existsError()

    def test_existsError_error2(self):
        error_status = OmronErrorStatus()
        data = b'\x00\x01\x00\x00'
        error_status.parse(data)

        assert error_status.existsError()

    def test_existsError_error3(self):
        error_status = OmronErrorStatus()
        data = b'\x00\x00\x01\x00'
        error_status.parse(data)

        assert error_status.existsError()

    def test_existsError_error4(self):
        error_status = OmronErrorStatus()
        data = b'\x00\x00\x00\x01'
        error_status.parse(data)

        assert error_status.existsError()

