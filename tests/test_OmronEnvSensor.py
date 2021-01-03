import datetime
import unittest

from omron_env_sensor import OmronLatestData, OmronLatestPage, OmronTimeInformation, \
    OmronErrorStatus


class OmronEnvSensorTestCase(unittest.TestCase):
    def test_LatestData_uuid(self):
        latest_data = OmronLatestData()
        self.assertEqual("0c4c3001-7700-46f4-aa96-d5e974e32a54", str(latest_data.uuid))

    def test_LatestData_short_uuid(self):
        latest_data = OmronLatestData()
        self.assertEqual("0x3001", F'{latest_data.shortUuid:#0x}')

    def test_LatestData_parse(self):
        latest_data = OmronLatestData()
        data = b"\x06\x1d\n\x8a\x19\n\x00\x02\x00%'\x05\x0e+\x1db\ts\n"
        latest_data.parse(data)
        # latestData = {'row': 6, 'temp': 25.89, 'humid': 65.38, 'light': 10, 'uv': 0.02, 'press': 1002.1, 'noise': 35.89, 'discom': 74.67, 'heat': 24.02, 'batt': 2.675}
        self.assertEqual(6, latest_data.row)
        self.assertEqual(25.89, latest_data.temperature)
        self.assertEqual(65.38, latest_data.humidity)
        self.assertEqual(10, latest_data.light)
        self.assertEqual(0.02, latest_data.uv)
        self.assertEqual(1002.1, latest_data.barometric_pressure)
        self.assertEqual(35.89, latest_data.noise)
        self.assertEqual(74.67, latest_data.discomfort_index)
        self.assertEqual(24.02, latest_data.heat_stroke)
        self.assertEqual(2.675, latest_data.battery_level)

    def test_LatestData_str(self):
        latest_data = OmronLatestData()
        data = b"\x06\x1d\n\x8a\x19\n\x00\x02\x00%'\x05\x0e+\x1db\ts\n"
        latest_data.parse(data)
        # latestData = {'row': 6, 'temp': 25.89, 'humid': 65.38, 'light': 10, 'uv': 0.02, 'press': 1002.1, 'noise': 35.89, 'discom': 74.67, 'heat': 24.02, 'batt': 2.675}
        self.assertEqual(
            "{'row': 6, 'temperature': 25.89, 'humidity': 65.38, 'light': 10, 'uv': 0.02, 'barometric_pressure': 1002.1, 'noise': 35.89, 'discomfort_index': 74.67, 'heat_stroke': 24.02, 'battery_level': 2.675}",
            str(latest_data))

    def test_LatestData_to_dict(self):
        latest_data = OmronLatestData()
        data = b"\x06\x1d\n\x8a\x19\n\x00\x02\x00%'\x05\x0e+\x1db\ts\n"
        latest_data.parse(data)
        dict_data = latest_data.to_dict()
        # latestData = {'row': 6, 'temp': 25.89, 'humid': 65.38, 'light': 10, 'uv': 0.02, 'press': 1002.1, 'noise': 35.89, 'discom': 74.67, 'heat': 24.02, 'batt': 2.675}
        self.assertEqual(True, type(dict_data) is dict)
        self.assertEqual(6, dict_data["row"])
        self.assertEqual(25.89, dict_data["temperature"])
        self.assertEqual(65.38, dict_data["humidity"])
        self.assertEqual(10, dict_data["light"])
        self.assertEqual(0.02, dict_data["uv"])
        self.assertEqual(1002.1, dict_data["barometric_pressure"])
        self.assertEqual(35.89, dict_data["noise"])
        self.assertEqual(74.67, dict_data["discomfort_index"])
        self.assertEqual(24.02, dict_data["heat_stroke"])
        self.assertEqual(2.675, dict_data["battery_level"])

    def test_LatestPage_uuid(self):
        latest_page = OmronLatestPage()
        self.assertEqual("0c4c3002-7700-46f4-aa96-d5e974e32a54", str(latest_page.uuid))

    def test_LatestPage_service_uuid(self):
        latest_page = OmronLatestPage()
        self.assertEqual("0c4c3000-7700-46f4-aa96-d5e974e32a54", str(latest_page.serviceUuid))

    def test_LatestPage_short_uuid(self):
        latest_page = OmronLatestPage()
        self.assertEqual("0x3002", F'{latest_page.shortUuid:#0x}')

    def test_LatestData_parse(self):
        latest_page = OmronLatestPage()
        data = b'C\x91\xe5^,\x01\t\x02\x0b'
        latest_page.parse(data)
        # latestPage = {'unix_time': 1592103235, 'interval': 300, 'latest_page': 521, 'latest_row': 11}
        self.assertEqual(1592103235, latest_page.unix_time)
        self.assertEqual("2020-06-14T11:53:55+09:00", latest_page.datetime.isoformat())
        self.assertEqual(300, latest_page.measurement_interval)
        self.assertEqual(521, latest_page.page)
        self.assertEqual(11, latest_page.row)

    def test_LatestData_str(self):
        latest_page = OmronLatestPage()
        data = b'C\x91\xe5^,\x01\t\x02\x0b'
        latest_page.parse(data)

        self.assertEqual("JST", datetime.datetime.now().astimezone().tzname())
        self.assertEqual(
            "{'unix_time': 1592103235, 'datetime': '2020-06-14T11:53:55+09:00', 'measurement_interval': 300, 'page': 521, 'row': 11}",
            str(latest_page))

    def test_TimeInformation_service_uuid(self):
        time_info = OmronTimeInformation()
        self.assertEqual("0c4c3030-7700-46f4-aa96-d5e974e32a54", str(time_info.serviceUuid))

    def test_TimeInformation_parse(self):
        time_info = OmronTimeInformation()
        data = b'\xE3\x68\x3E\x5F'
        # data = {'unix_time': 1597925603, 'datetime': '2020-08-20T21:13:23+09:00'}
        time_info.parse(data)
        self.assertEqual(1597925603, time_info.unix_time)
        self.assertEqual("2020-08-20T21:13:23+09:00", str(time_info.datetime.isoformat()))

    def test_ErrorStatus_service_uuid(self):
        error_status = OmronErrorStatus()
        data = b'\x00\x01\x01\x00'
        error_status.parse(data)
        dict_data = error_status.to_dict()

        # error_status = {'sensor_status': 0, 'cpu_status': 1, 'battery_status': 1, 'rfu': 0}
        self.assertEqual(True, type(dict_data) is dict)
        self.assertEqual(0, dict_data["sensor_status"])
        self.assertEqual(1, dict_data["cpu_status"])
        self.assertEqual(1, dict_data["battery_status"])
        self.assertEqual(0, dict_data["rfu"])

        self.assertEquals(True, error_status.existsError())

    def test_ErrorStatus_existsError_noError(self):
        error_status = OmronErrorStatus()
        data = b'\x00\x00\x00\x00'
        error_status.parse(data)

        self.assertEqual(False, error_status.existsError())

    def test_ErrorStatus_existsError_error1(self):
        error_status = OmronErrorStatus()
        data = b'\x01\x00\x00\x00'
        error_status.parse(data)

        self.assertEqual(True, error_status.existsError())

    def test_ErrorStatus_existsError_error2(self):
        error_status = OmronErrorStatus()
        data = b'\x00\x01\x00\x00'
        error_status.parse(data)

        self.assertEqual(True, error_status.existsError())

    def test_ErrorStatus_existsError_error3(self):
        error_status = OmronErrorStatus()
        data = b'\x00\x00\x01\x00'
        error_status.parse(data)

        self.assertEqual(True, error_status.existsError())

    def test_ErrorStatus_existsError_error4(self):
        error_status = OmronErrorStatus()
        data = b'\x00\x00\x00\x01'
        error_status.parse(data)

        self.assertEqual(True, error_status.existsError())


if __name__ == '__main__':
    unittest.main()
