#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import logging.config
from datetime import datetime
from logging import getLogger

import related
import yaml
from influxdb import InfluxDBClient
from peewee import *
from playhouse.sqlite_ext import SqliteExtDatabase

import db_model
from command_config import CommandConfig

logger = getLogger("post_influxdb")


def prepare_logging():
    with open('logging_conf.yaml', 'r', encoding='utf-8') as f:
        logconfig_dict = yaml.safe_load(f)
    logging.config.dictConfig(logconfig_dict)


def convert(log_data_dict: dict) -> dict:
    """
    EnvSensorLogのdictをinfluxdbにPostする形に変形する
    Args:
        log_data_dict: 環境センサーのログデータ

    Returns:
        dict: influxdbに格納するデータ
    """
    ble_address = log_data_dict.pop("ble_address")

    influx_data = {
        "measurement": "env_sensor",
        "tags": {
            "ble_address": ble_address
        },
        "time": log_data_dict["timestamp"],
        "fields": log_data_dict
    }
    return influx_data


def read_influx_post_position(db) -> db_model.InfluxdbPostPosition:
    """
    SqliteからinfluxdbへPOST処理済みの位置を読み出す
    Args:
        db: SqliteDatabase

    Returns:
        db_model.InfluxdbPostPosition: 前回の処理時に最後にPOSTしたEnvSensorLogのID
    """

    with db.transaction() as tran:
        db_influx_last_position = db_model.InfluxdbPostPosition.get_or_none(id=0)

        if db_influx_last_position is None:
            logger.debug(f'initialize InfluxdbPostPosition.')
            result = db_model.InfluxdbPostPosition.create(id=0, post_log_position=0, timestamp=datetime.now())
            logger.debug(f"insert result={result}")

        db_influx_last_position = db_model.InfluxdbPostPosition.get_by_id(0)

    return db_influx_last_position


def main(config: CommandConfig):
    influxdb_config = config.influxdb

    client = InfluxDBClient(influxdb_config.host,
                            influxdb_config.port,
                            influxdb_config.username,
                            influxdb_config.password,
                            influxdb_config.database)
    client.create_database(influxdb_config.database)

    db = SqliteExtDatabase(config.database.filename)
    try:
        db_model.database_proxy.initialize(db)
        db.create_tables([db_model.InfluxdbPostPosition])
    except IntegrityError as ex:
        logger.error("database open error.", ex)
        db.rollback()
        exit(1)

    while True:
        db_influx_last_position = read_influx_post_position(db)
        last_post_position = db_influx_last_position.post_log_position

        logger.info(f'db_influx_last_position={last_post_position}')
        with db.transaction() as tran:
            db_result = db_model.EnvSensorLog.select() \
                .where(db_model.EnvSensorLog.id > last_post_position) \
                .order_by(db_model.EnvSensorLog.id) \
                .limit(1000)

            logger.info(F"db select count={db_result.count()}")
            if db_result.count() == 0:
                break

            influx_data = []
            for env_sensor_log in db_result:
                logger.debug(f"log_id={env_sensor_log.id}, data={env_sensor_log.data}")
                db_influx_last_position.post_log_position = env_sensor_log.id
                db_influx_last_position.timestamp = datetime.now()

                influx_data.append(convert(env_sensor_log.data))

            logger.debug(f"write_data={influx_data}")
            logger.info(f"processed position={db_influx_last_position.post_log_position}")
            client.write_points(influx_data)
            db_influx_last_position.save()

    logger.info(F"process complete.")


if __name__ == "__main__":
    prepare_logging()

    config_yaml = open('config.yaml').read().strip()
    config = related.from_yaml(config_yaml, CommandConfig)
    main(config)

    logging.shutdown()
