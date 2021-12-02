import struct

import bluepy
import pytest
from bluepy import btle
from bluepy.btle import Peripheral, BTLEException

from omron.env_sensor import OmronEnvSensor

TEST_MAC_ADDRESS = "00:00:5e:00:53:00"


class TestBlePeripheral:

    def test_constructor(self, mocker):
        mock_peripheral = mocker.patch("omron.env_sensor.Peripheral", autospec=True)
        env_sensor = OmronEnvSensor(TEST_MAC_ADDRESS)

        peripheral = env_sensor.peripheral

        mock_peripheral.assert_called_once_with(TEST_MAC_ADDRESS, bluepy.btle.ADDR_TYPE_RANDOM)
        assert peripheral is not None

    def test_constructor_discoverServices(self, mocker):
        peripheral_mock = mocker.Mock(spec=Peripheral)
        constructor_mock = mocker.patch("omron.env_sensor.Peripheral", autospec=True, return_value=peripheral_mock)

        env_sensor = OmronEnvSensor(TEST_MAC_ADDRESS)

        peripheral = env_sensor.peripheral

        constructor_mock.assert_called_once_with(TEST_MAC_ADDRESS, bluepy.btle.ADDR_TYPE_RANDOM)
        peripheral_mock.discoverServices.assert_called_once()
        assert peripheral is not None
        assert peripheral is peripheral_mock

    def test_read_base(self, mocker):
        raw_data_mock = mocker.Mock()

        ble_char_mock = mocker.Mock(spec=btle.Characteristic)
        ble_char_mock.read.return_value = raw_data_mock

        ble_service_mock = mocker.Mock(spec=btle.Service)
        ble_service_mock.getCharacteristics.return_value = [ble_char_mock]

        peripheral_mock = mocker.Mock(spec=Peripheral)
        peripheral_mock.getServiceByUUID.return_value = ble_service_mock

        mocker.patch("omron.env_sensor.Peripheral", autospec=True, return_value=peripheral_mock)

        env_sensor = OmronEnvSensor(TEST_MAC_ADDRESS)
        (ble_chara, raw_data) = env_sensor.read_char_base(0x1800, 0x2a00)

        peripheral_mock.getServiceByUUID.assert_called_once_with(uuidVal=0x1800)
        ble_service_mock.getCharacteristics.assert_called_once_with(forUUID=0x2a00)
        ble_char_mock.read.assert_called_once()

        assert ble_chara is ble_char_mock
        assert raw_data is raw_data_mock

    def test_read_base_throw_exception(self, mocker):
        ble_char_mock = mocker.Mock(spec=btle.Characteristic)
        ble_char_mock.read.side_effect = BTLEException("Test IO Exception")

        ble_service_mock = mocker.Mock(spec=btle.Service)
        ble_service_mock.getCharacteristics.return_value = [ble_char_mock]

        peripheral_mock = mocker.Mock(spec=Peripheral)
        peripheral_mock.getServiceByUUID.return_value = ble_service_mock

        mocker.patch("omron.env_sensor.Peripheral", autospec=True, return_value=peripheral_mock)

        with pytest.raises(BTLEException) as e:
            env_sensor = OmronEnvSensor(TEST_MAC_ADDRESS)
            (ble_chara, raw_data) = env_sensor.read_char_base(0x1800, 0x2a00)

        assert str(e.value) == "Test IO Exception"

        peripheral_mock.getServiceByUUID.assert_called_with(uuidVal=0x1800)
        assert peripheral_mock.getServiceByUUID.call_count == 5

        ble_service_mock.getCharacteristics.assert_called_with(forUUID=0x2a00)
        assert ble_service_mock.getCharacteristics.call_count == 5

        ble_char_mock.read.assert_called_with()
        assert ble_char_mock.read.call_count == 5

    def test_write_base(self, mocker):
        ble_char_mock = mocker.Mock(spec=btle.Characteristic)

        ble_service_mock = mocker.Mock(spec=btle.Service)
        ble_service_mock.getCharacteristics.return_value = [ble_char_mock]

        peripheral_mock = mocker.Mock(spec=Peripheral)
        peripheral_mock.getServiceByUUID.return_value = ble_service_mock

        mocker.patch("omron.env_sensor.Peripheral", autospec=True, return_value=peripheral_mock)

        env_sensor = OmronEnvSensor(TEST_MAC_ADDRESS)

        write_data = struct.pack("<HB", 21, 10)
        env_sensor.write_char_base(0x3000, 0x3003, write_data)

        peripheral_mock.getServiceByUUID.assert_called_once_with(uuidVal=0x3000)
        ble_service_mock.getCharacteristics.assert_called_once_with(forUUID=0x3003)
        ble_char_mock.write.assert_called_once_with(write_data)

    def test_write_base_throw_exception(self, mocker):
        ble_char_mock = mocker.Mock(spec=btle.Characteristic)
        ble_char_mock.write.side_effect = BTLEException("Test IO Exception")

        ble_service_mock = mocker.Mock(spec=btle.Service)
        ble_service_mock.getCharacteristics.return_value = [ble_char_mock]

        peripheral_mock = mocker.Mock(spec=Peripheral)
        peripheral_mock.getServiceByUUID.return_value = ble_service_mock

        mocker.patch("omron.env_sensor.Peripheral", autospec=True, return_value=peripheral_mock)

        with pytest.raises(BTLEException) as e:
            env_sensor = OmronEnvSensor(TEST_MAC_ADDRESS)
            write_data = struct.pack("<HB", 21, 10)
            env_sensor.write_char_base(0x3000, 0x3003, write_data)

        assert str(e.value) == "Test IO Exception"

        peripheral_mock.getServiceByUUID.assert_called_with(uuidVal=0x3000)
        assert peripheral_mock.getServiceByUUID.call_count == 5

        ble_service_mock.getCharacteristics.assert_called_with(forUUID=0x3003)
        assert ble_service_mock.getCharacteristics.call_count == 5

        ble_char_mock.write.assert_called_with(write_data)
        assert ble_char_mock.write.call_count == 5
