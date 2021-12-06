#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# BLEセンサーを10秒間スキャンし、情報を表示します。
import argparse
import logging
import logging.config
import math
import re
from datetime import datetime
from logging import INFO, ERROR

import related
import yaml
from peewee import *
from playhouse.shortcuts import model_to_dict
from playhouse.sqlite_ext import SqliteExtDatabase
from retry import retry
from tqdm import tqdm

import db_model
from command_config import CommandConfig, TargetDevice
from omron.env_sensor import OmronEnvSensor

logger = logging.getLogger("wxbeacon2_scan")


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
    target_device: TargetDevice
    for target_device in config.target_device_list:
        try:
            process_target_device(db, target_device)
        except Exception as e:
            logger.exception(f"process_target_device: address={target_device.addr}, exception={e}")
            # pass


def log_device(level: int, address: str, *log_args):
    msg = " ".join([str(a) for a in log_args])
    logger.log(level, F'{address}: {msg}')


@retry(tries=3, delay=1, logger=logger)
def process_target_device(db: SqliteDatabase, target_device: TargetDevice):
    device = OmronEnvSensor(target_device.addr)
    if not device.check_omron_env_sensor():
        logger.error(f"{target_device.addr} is NOT Omron Env Sensor")
        return

    # 最新の観測データの表示
    latest_data = device.read_latest_data()
    log_device(INFO, device.address, F'latestData = {latest_data}')

    # 最新ページの表示
    latest_page = device.read_latest_page()
    log_device(INFO, device.address, F'latestPage = {latest_page}')

    # TimeInformationの表示
    time_information = device.read_time_information()
    log_device(INFO, device.address, F'time_information = {time_information}')

    # ErrorStatusの表示
    error_status = device.read_error_status()
    if error_status.existsError():
        log_device(ERROR, device.address, F'device has error. error_status = {error_status}')
    else:
        log_device(INFO, device.address, F'error_status = {error_status}')

    # デバイスの管理用レコードを作る
    with db.transaction() as tran:
        db_device, db_device_created = db_model.EnvSensorDevice.get_or_create(
            address=device.address,
            defaults={'time_information': time_information.unix_time}
        )

    # DBに取り込み済みの最後のレコードから、環境センサーの取り込み開始ページを求める
    scan_start_page = calc_scan_start_page(db_device, latest_page, time_information)

    # 環境センサーの最新ページと、DBから求めた取り込み開始位置から、取り込み範囲のページを計算してリストにする
    scan_range = latest_page.calcPage(scan_start_page)

    # 取り込み範囲の上書き設定があったらそっちを優先する
    if target_device.scan_range:
        scan_range = range(target_device.scan_range[0], target_device.scan_range[1])
        log_device(INFO, device.address, F"scan page range(OVERRIDE)={scan_range}")
    else:
        log_device(INFO, device.address, F'scan page range={scan_range[0], scan_range[-1]}')

    if config.no_scan:
        measurement_interval = device.read_measurement_interval()
        log_device(INFO, device.address, f"measurement interval = {measurement_interval}")
        log_device(INFO, device.address, "Test OK.")
        return

    # 観測データをページ単位で読み出し
    progress_bar = tqdm(scan_range)
    progress_bar.set_description_str(F"{device.address} reading page")
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
                    log_device(INFO, device.address,
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
            f"calc_scan_start_page: incremental scan, latest_log_row(id={latest_log_row.id}, device_address={latest_log_row.device.address}, log_date={latest_log_row.log_date}, page={latest_log_row.page} row={latest_log_row.data['row']})")
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


def set_measurement_interval(address: str, new_measurement_interval: int, dry_run: bool = True) -> None:
    """
    環境センサーの測定間隔を変更する
    Args:
        address (str): 対象デバイスのMACアドレス
        new_measurement_interval (int): 設定する測定間隔(秒) 1から3600
        dry_run (bool): 設定を実行しないテストモード

    Returns:
        None
    """
    logger.info(
        f"Set measurement interval{'(DRY RUN MODE)' if dry_run else ''}: address={address}, measurement_interval={new_measurement_interval}")
    assert 1 <= new_measurement_interval <= 3600

    device = OmronEnvSensor(address)
    if not device.check_omron_env_sensor():
        logger.error(f"{address} is NOT Omron Env Sensor")

    # 最新ページの表示
    latest_page = device.read_latest_page()
    log_device(INFO, device.address, F'latestPage = {latest_page}')

    # TimeInformationの表示
    time_information = device.read_time_information()
    log_device(INFO, device.address, F'time_information = {time_information}')

    if not dry_run:
        # Measurement Intervalの更新
        log_device(INFO, device.address, F'write measurement interval = {new_measurement_interval}')
        device.write_measurement_interval(new_measurement_interval)

        # TimeInformationの設定
        unix_time = math.floor(datetime.now().timestamp())
        log_device(INFO, device.address, F'write unix_time = {unix_time}')
        device.write_time_information(unix_time)

    # 測定間隔の変更結果確認用
    # 最新ページの表示
    after_latest_page = device.read_latest_page()
    log_device(INFO, device.address, F'after latestPage = {after_latest_page}')

    # TimeInformationの表示
    after_time_information = device.read_time_information()
    log_device(INFO, device.address, F'after time_information = {after_time_information}')


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

    target_device_address = args.addr.lower()

    # コマンドライン引数にデバイスのMACアドレスのみで、スキャンするページ範囲の指定が無い場合
    if args.pagerange is None:
        config.target_device_list = [TargetDevice(addr=target_device_address)]
        return

    # コマンドライン引数にデバイスのMACアドレスとスキャンするページ範囲の指定の両方がある場合
    config.target_device_list = [
        TargetDevice(addr=target_device_address, scan_range=[args.pagerange[0], args.pagerange[1]])]


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
