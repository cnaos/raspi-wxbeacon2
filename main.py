#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# BLEセンサーを10秒間スキャンし、情報を表示します。
import argparse
import json
import logging
import logging.config
import math
import re
import time
from datetime import datetime
from logging import DEBUG, INFO, ERROR, WARN
from threading import Timer
from typing import List

import related
import yaml
from bluepy import btle
from bluepy.btle import Peripheral, BTLEException
from peewee import *
from playhouse.shortcuts import model_to_dict
from playhouse.sqlite_ext import SqliteExtDatabase
from retry import retry
from tqdm import tqdm

import db_model
from command_config import CommandConfig, TargetDevice
from omron_env_sensor import OmronLatestData, OmronLatestPage, OmronRequestPage, OmronResponseFlag, OmronResponseData, \
    OmronTimeInformation, \
    OmronErrorStatus, OmronMeasurementInterval
from util import DateTimeSupportJSONEncoder, LogData

logger = logging.getLogger("wxbeacon2_scan")

BLE_READ_CHARA_WAIT_SEC = 100 / 1000  # 50 msec
BLE_READ_WAIT_SEC = 50 / 1000  # 50 msec
BLE_WRITE_WAIT_SEC = 50 / 1000  # 50 msec


class EnvSensor:
    """
    環境センサーからのデータ読み出しとSQLiteへのデータ保存を行うクラス
    """

    def __init__(self, addr: str, addr_type: str = "random"):
        """

        Args:
            addr: 環境センサーのMACアドレス
            addr_type: 環境センサーのアドレスタイプ
        """
        self.ble_peripheral = Peripheral()
        self.isConnected = False
        self.addr = addr.lower()
        self.addr_type = addr_type.lower()
        self.connect_timer = None
        self.ble_services = None

    def __enter__(self):
        self.connect_with_timeout()
        self.ble_services = self.ble_peripheral.getServices()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cancel_timer_and_disconnect()

    def MSG(self, level: int, *args) -> None:
        """
        Bluetoothデバイスのアドレスをつけてログ出力する

        Args:
            level: ログ出力レベル
            *args: ログ出力内容

        Returns:
            None
        """

        msg = " ".join([str(a) for a in args])
        logger.log(level, F'{self.addr}: {msg}')

    def timeout_disconnect(self) -> None:
        """
        接続でタイムアウトしたときに呼ばれるdisconnect

        Returns:
            None
        """
        self.MSG(ERROR, f'connect timer expired')
        self.disconnect()

    def disconnect(self) -> None:
        """
        デバイスとの接続を切断する

        Returns:
            None
        """
        if self.isConnected:
            self.ble_peripheral.disconnect()
        self.isConnected = False
        self.MSG(INFO, f'device disconnected')

    def force_disconnect(self) -> None:
        """
        デバイスとの接続を強制切断する

        Returns:
            None
        """
        if self.isConnected:
            try:
                self.ble_peripheral.disconnect()
            except Exception as e:
                self.MSG(WARN, f'device disconnect error: {e}')
                pass

        self.isConnected = False
        self.MSG(INFO, f'device force disconnected')

    def connect_with_timeout(self, timeout_sec=45, max_retry=5, retry_interval_sec=5) -> None:
        """
        デバイスに接続する。タイムアウトあり

        Args:
            timeout_sec: タイムアウト秒数
            max_retry: 最大リトライ回数
            retry_interval_sec: リトライする前のインターバル秒数

        Returns:
            None:

        """
        for i in range(max_retry):
            try:
                self.MSG(INFO, f'connecting {i + 1}/{max_retry}')
                self.connect_timer = Timer(timeout_sec, self.timeout_disconnect)
                self.connect_timer.start()
                self.ble_peripheral.connect(addr=self.addr, addrType=self.addr_type)
            except BTLEException as e:
                self.MSG(ERROR, F'try {i + 1}: BTLE Exception while connecting ')
                self.MSG(ERROR, '  type:' + str(type(e)))
                self.MSG(ERROR, '  args:' + str(e.args))
                time.sleep(retry_interval_sec)
            else:
                self.isConnected = True
                self.MSG(INFO, 'connected')
                break
                # TODO cancelタイマーの待ち合わせしてから状態変更したほうがいいかも
            finally:
                self.connect_timer.cancel()
                self.connect_timer.join()  # 完全にキャンセルするまで待つ

        if not self.isConnected:
            self.MSG(ERROR, "connect failed.")
            raise Exception(F"BTLE connect to {self.addr} failed.")

    def cancel_timer_and_disconnect(self) -> None:
        """
        接続待ちのタイマーをキャンセルしてからデバイスとの接続を切断する

        Returns:
            None
        """
        self.MSG(DEBUG, 'cancel_timer_and_disconnect')
        self.connect_timer.cancel()
        self.connect_timer.join()
        self.disconnect()

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

    def read_device_name(self) -> str:
        """
        BLEデバイスの名前を読む(Generic Access:0x1800, Device Name:0x2a00)

        Returns:
            str: BLEデバイスの名前
        """
        (ble_chara, raw_data) = self.read_char_base(0x1800, 0x2a00)
        str_device_name = raw_data.decode('utf-8')
        self.MSG(DEBUG, f'char={ble_chara}, raw_data={raw_data}, str={str_device_name}')
        return str_device_name

    @retry(tries=3, delay=1, logger=logger)
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
            if not self.isConnected:
                self.MSG(INFO, f"reconnect.")
                self.connect_with_timeout()

            target_row = 12 if page != latest_page.page else latest_page.row  # 最新ページ以外は13行の読み出し

            response_flag = self.write_read_page_and_wait_ready(page, target_row)
            self.MSG(INFO, f'page = {page}, start_time={response_flag.datetime} ({response_flag.unix_time})')

            page_data = []
            for i in range(13 + 3):  # 1ページ分のデータは最大13件だけど、予備で3回追加しておく
                response_data = self.read_response_data()
                self.MSG(DEBUG, F'response_data = {response_data}')
                page_data.append(response_data)
                if response_data is None or response_data.row == 0:
                    break

            list_log_data = list(
                map(lambda it: LogData(self.addr,
                                       page,
                                       response_flag.unix_time,
                                       latest_page.measurement_interval,
                                       it),
                    page_data))

            self.MSG(DEBUG, F'list_log_data={json.dumps(list_log_data, cls=DateTimeSupportJSONEncoder)}')
            return list_log_data
        except Exception as e:
            logger.exception(f"read_env_sensor_data failed: {e}")
            self.force_disconnect()
            raise e

    def read_latest_data(self) -> OmronLatestData:
        """
        環境センサーのLatest Dataを読み出す

        Returns:
            LatestData
        """

        latest_data = OmronLatestData()

        self.MSG(DEBUG, F'reading LatestData(uuid={latest_data.shortUuid:#04x})')
        (ble_chara, raw_data) = self.read_char_base(latest_data.serviceUuid, latest_data.uuid)
        return latest_data.parse(raw_data)

    def read_latest_page(self) -> OmronLatestPage:
        """
        環境センサーのLatest Pageを読み出す

        Returns:
            LatestPage
        """

        latest_page = OmronLatestPage()

        self.MSG(DEBUG, F'reading LatestPage(uuid={latest_page.shortUuid:#04x})')
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

        self.MSG(DEBUG, F'writing RequestPage(uuid={request_page.shortUuid:#04x}): data={data}')
        self.write_char_base(request_page.serviceUuid, request_page.uuid, data)

    def read_response_flag(self) -> OmronResponseFlag:
        """
        環境センサーのResponse Flagを読み出す。

        Returns:
            ResponseFlag
        """
        response_flag = OmronResponseFlag()

        self.MSG(DEBUG, F'reading ResponseFlag(uuid={response_flag.shortUuid:#04x})')
        (ble_chara, raw_data) = self.read_char_base(response_flag.serviceUuid, response_flag.uuid)
        return response_flag.parse(raw_data)

    def read_response_data(self) -> OmronResponseData:
        """
        環境センサーのResponse Dataを読み出す

        Returns:
            ResponseData
        """
        response_data = OmronResponseData()

        self.MSG(DEBUG, F'reading ResponseData(uuid={response_data.shortUuid:#04x})')
        (ble_chara, raw_data) = self.read_char_base(response_data.serviceUuid, response_data.uuid)
        return response_data.parse(raw_data)

    def read_time_information(self) -> OmronTimeInformation:
        """
        環境センサーのTime Informationを読み出す
        Returns:
            TimeInformation
        """

        time_information = OmronTimeInformation()

        self.MSG(DEBUG, F'reading TimeInformation(uuid={time_information.shortUuid:#04x})')
        (ble_chara, raw_data) = self.read_char_base(time_information.serviceUuid, time_information.uuid)
        return time_information.parse(raw_data)

    def read_measurement_interval(self) -> OmronMeasurementInterval:
        """
        環境センサーのMeasurement Intervalを読み出す

        Returns:
            MeasurementInterval
        """
        measurement_interval = OmronMeasurementInterval()

        self.MSG(DEBUG, F'reading MeasurementInterval(uuid={measurement_interval.shortUuid:#04x})')
        (ble_chara, raw_data) = self.read_char_base(measurement_interval.serviceUuid, measurement_interval.uuid)
        return measurement_interval.parse(raw_data)

    def read_error_status(self) -> OmronErrorStatus:
        """
        環境センサーのError Statusを読み出す

        Returns:
            ErrorStatus
        """
        error_status = OmronErrorStatus()

        self.MSG(DEBUG, F'reading ErrorStatus(uuid={error_status.shortUuid:#04x})')
        (ble_chara, raw_data) = self.read_char_base(error_status.serviceUuid, error_status.uuid)
        return error_status.parse(raw_data)

    @retry(tries=3, delay=1)
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
            self.MSG(DEBUG, F'response_flag={response_flag}')
            if response_flag.update_flag == 0x01:  # 更新完了
                return response_flag
            elif response_flag.update_flag == 0x00:  # 更新中
                continue
            else:  # 更新失敗
                self.MSG(ERROR, F'response flag failed.')
                raise IOError
        self.MSG(ERROR, F'read response flag failed after retry.')
        raise IOError

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

        self.MSG(DEBUG, F'writing MeasurementInterval(uuid={measurement_interval.shortUuid:#04x}): data={data}')
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

        self.MSG(DEBUG, F'writing TimeInformation(uuid={time_information.shortUuid:#04x}): data={data}')
        self.write_char_base(time_information.serviceUuid, time_information.uuid, data)

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
            self.MSG(WARN, f'this device is not OMRON ')
            return False


def main(config: CommandConfig) -> None:
    """
    環境センサーから測定データを読み出してDBに保存するメインロジック

    Args:
        config: コンフィグオブジェクト

    Returns:
        None:
    """

    # コマンドライン引数のオプションでconfigを上書きする処理
    logger.debug(f"scan config={config}")

    # DBへの接続作成
    if config.dry_run:
        logger.info("---DRY RUN MODE---")
        db = SqliteDatabase(':memory:')
    else:
        db = SqliteExtDatabase(config.database.filename)

    if config.no_scan:
        logger.info("---NO SCAN MODE---")

    try:
        db_model.database_proxy.initialize(db)
        db.create_tables([db_model.EnvSensorDevice, db_model.EnvSensorLog, db_model.EnvSensorCurrentDataLog])
    except IntegrityError as ex:
        logger.error("database open error.", ex)
        db.rollback()
        exit(1)

    logger.debug("----process Devices----")
    for target_device in config.target_device_list:
        with EnvSensor(target_device.addr) as device:
            if not device.check_omron_env_sensor():
                logger.error(f"{target_device.addr} is NOT Omron Env Sensor")
                break

            # 最新の観測データの表示
            latest_data = device.read_latest_data()
            device.MSG(INFO, F'latestData = {latest_data}')

            # 最新ページの表示
            latest_page = device.read_latest_page()
            device.MSG(INFO, F'latestPage = {latest_page}')

            # TimeInformationの表示
            time_information = device.read_time_information()
            device.MSG(INFO, F'time_information = {time_information}')

            # ErrorStatusの表示
            error_status = device.read_error_status()
            if error_status.existsError():
                device.MSG(ERROR, F'device has error. error_status = {error_status}')
            else:
                device.MSG(INFO, F'error_status = {error_status}')

            # デバイスの管理用レコードを作る
            with db.transaction() as tran:
                db_device, db_device_created = db_model.EnvSensorDevice.get_or_create(
                    address=target_device.addr,
                    defaults={'time_information': time_information.unix_time}
                )

            # DBに取り込み済みの最後のレコードから、環境センサーの取り込み開始ページを求める
            scan_start_page = calc_scan_start_page(db_device, latest_page, time_information)

            # 環境センサーの最新ページと、DBから求めた取り込み開始位置から、取り込み範囲のページを計算してリストにする
            scan_range = latest_page.calcPage(scan_start_page)

            # 取り込み範囲の上書き設定があったらそっちを優先する
            if target_device.scan_range:
                scan_range = range(target_device.scan_range[0], target_device.scan_range[1])
                device.MSG(INFO, F"scan page range(OVERRIDE)={scan_range}")
            else:
                device.MSG(INFO, F'scan page range={scan_range[0], scan_range[-1]}')

            if config.no_scan:
                measurement_interval = device.read_measurement_interval()
                device.MSG(INFO, f"measurement interval = {measurement_interval}")
                device.MSG(INFO, "Test OK.")
                continue

            # 観測データをページ単位で読み出し
            progress_bar = tqdm(scan_range)
            progress_bar.set_description_str(F"{device.addr} reading page")
            for page in progress_bar:
                with db.transaction() as tran:
                    # 観測データを読み出し
                    list_log_data = device.read_env_sensor_data(page, latest_page)

                    for log_line in list_log_data:
                        db_model.EnvSensorLog.get_or_create(device=db_device, log_date=log_line.timestamp,
                                                            defaults={'page': log_line.page,
                                                                      'data': log_line.to_flat_dict()})

                        # 差分取り込みのためにデバイスごとの管理レコードのTimeInformationを保存
                        db_device_for_update = db_model.EnvSensorDevice.get(address=db_device.address)
                        if db_device_for_update.time_information != time_information.unix_time:
                            device.MSG(INFO,
                                       f"Update time_information = {db_device_for_update.time_information} -> {time_information.unix_time}")
                        db_device_for_update.time_information = time_information.unix_time
                        db_device_for_update.save()


def calc_scan_start_page(db_device, latest_page, time_information) -> int:
    latest_log_row = db_device.latest_log()

    if latest_log_row is None:
        # 初回取り込み
        # TODO 0ページから取り込むか、最新ページのみ取り込むか設定できると良いかも
        logger.info("calc_scan_start_page: initial scan")
        return latest_page.page

    logger.debug(f"latest_log_row dict={model_to_dict(latest_log_row)}")

    if db_device.time_information == time_information.unix_time:
        # 前回取り込み時からデバイス側のタイマーが変わってない
        # つまり、測定間隔の変更が行われていないので、差分取り込みができる
        logger.info(
            f"calc_scan_start_page: incremental scan, latest_log_row(id={latest_log_row.id}, device_addr={latest_log_row.device.address}, log_date={latest_log_row.log_date}, page={latest_log_row.page} row={latest_log_row.data['row']})")
        return latest_log_row.page
    else:
        # 前回取り込み時からデバイス側のタイマーが変更された
        # 差分取り込みはできない、初回取り込みでもないので、0ページから取り込む
        logger.info("calc_scan_start_page: after timer reset scan, start page = 0")
        return 0


def argparse_num_range(min_val: int, max_val: int):
    def inner(arg_str: str):
        value = int(arg_str)
        if min_val <= value <= max_val:
            return value
        else:
            raise argparse.ArgumentTypeError(f'value({arg_str}) not in range {min_val}-{max_val}')

    return inner


def set_measurement_interval(addr: str, new_measurement_interval: int, dry_run: bool = True) -> None:
    """
    環境センサーの測定間隔を変更する
    Args:
        addr (str): 対象デバイスのMACアドレス
        new_measurement_interval (int): 設定する測定間隔(秒) 1から3600
        dry_run (bool): 設定を実行しないテストモード

    Returns:
        None
    """
    logger.info(
        f"Set measurement interval{'(DRY RUN MODE)' if dry_run else ''}: addr={addr}, measurement_interval={new_measurement_interval}")
    assert 1 <= new_measurement_interval <= 3600

    with EnvSensor(addr) as device:
        if not device.check_omron_env_sensor():
            logger.error(f"{addr} is NOT Omron Env Sensor")

        # 最新ページの表示
        latest_page = device.read_latest_page()
        device.MSG(INFO, F'latestPage = {latest_page}')

        # TimeInformationの表示
        time_information = device.read_time_information()
        device.MSG(INFO, F'time_information = {time_information}')

        if not dry_run:
            # Measurement Intervalの更新
            device.MSG(INFO, F'write measurement interval = {new_measurement_interval}')
            device.write_measurement_interval(new_measurement_interval)

            # TimeInformationの設定
            unix_time = math.floor(datetime.now().timestamp())
            device.MSG(INFO, F'write unixtime = {unix_time}')
            device.write_time_information(unix_time)

        # 測定間隔の変更結果確認用
        # 最新ページの表示
        after_latest_page = device.read_latest_page()
        device.MSG(INFO, F'after latestPage = {after_latest_page}')

        # TimeInformationの表示
        after_time_information = device.read_time_information()
        device.MSG(INFO, F'after time_information = {after_time_information}')


def prepare_logging() -> None:
    """
    ログ用の設定ファイルを読み込む
    Returns:
        None
    """
    logging_conf_yaml = open('logging_conf.yaml', 'r', encoding='utf-8').read()
    logging.config.dictConfig(yaml.safe_load(logging_conf_yaml))


class ArgParseChoiceRegex(object):
    """
    引数の正規表現バリデーション
    """

    def __init__(self, pattern):
        # 初期化
        self.pattern = pattern

    def __contains__(self, val):
        # マッチ処理を行う
        return re.match(self.pattern, val)

    def __iter__(self):
        # エラー時にコンソールに表示される(invalid choice: 値 (choose from なんとか)
        # print_help()のmetavarでも表示されるので、metaverオプションを使って隠す
        return iter(("str", self.pattern))


def override_device_config(config: CommandConfig, args: argparse.Namespace) -> None:
    """
    コマンドライン引数で設定ファイルの設定を上書きする

    Args:
        config: コンフィグオブジェクト
        args: コマンドライン引数の解析結果

    Returns:
        None
    """
    config.dry_run = args.dryrun
    config.no_scan = args.noscan

    if args.addr is None:
        return

    target_device_addr = args.addr.lower()

    # コマンドライン引数にデバイスのMACアドレスのみで、スキャンするページ範囲の指定が無い場合
    if args.pagerange is None:
        config.target_device_list = [TargetDevice(addr=target_device_addr)]
        return

    # コマンドライン引数にデバイスのMACアドレスとスキャンするページ範囲の指定の両方がある場合
    config.target_device_list = [
        TargetDevice(addr=target_device_addr, scan_range=[args.pagerange[0], args.pagerange[1]])]


def parse_command_argument() -> argparse.Namespace:
    """
    コマンドライン引数の解析
    Returns:
        argparse.Namespace コマンドライン引数の解析結果
    """
    parser = argparse.ArgumentParser(description='OMRONの環境センサーから観測データを取得します')
    parser.add_argument('--addr', type=str, metavar="XX:XX:XX:XX:XX",
                        choices=ArgParseChoiceRegex(r"([0-9A-Fa-f]{2}[:\-]?){6}"),
                        help='環境センサーのMACアドレスを指定する')
    parser.add_argument('--pagerange', type=argparse_num_range(0, 2047), nargs=2, metavar="[0-2047]",
                        help='データの読み出し範囲の開始ページと終了ページを指定する')
    parser.add_argument('--setinterval', type=argparse_num_range(1, 3600), nargs=1, metavar="[1-3600]",
                        help='測定間隔を変更する **注意** データの記録位置が0ページにリセットされ、既存データが上書きされる。')
    parser.add_argument('--dryrun', action='store_true',
                        help='DBに書き込まない、測定間隔を変更しない')
    parser.add_argument('--noscan', action='store_true',
                        help='観測データのページ読み込みを行わない。')
    return parser.parse_args()


if __name__ == "__main__":
    prepare_logging()

    args = parse_command_argument()
    logger.debug(f"cli option={args}")

    if args.addr is None and args.pagerange is not None:
        logger.error(f"pagerangeオプションを使うにはaddrオプションを指定してください。")
        exit(1)

    if args.addr is None and args.setinterval is not None:
        logger.error(f"setintervalオプションを使うにはaddrオプションを指定してください。")
        exit(1)

    if args.setinterval:
        # デバイス側の測定間隔の変更
        set_measurement_interval(args.addr, args.setinterval[0], args.dryrun)
        exit(0)

    config_yaml = open('config.yaml').read().strip()
    config = related.from_yaml(config_yaml, CommandConfig)
    override_device_config(config, args)

    main(config)
