#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import related


@related.immutable
class TargetDevice(object):
    addr = related.RegexField(r"([0-9A-Fa-f]{2}[:\-]?){6}")
    addr_type = related.StringField(required=False)
    scan_range = related.SequenceField(int, required=False)


@related.immutable
class Database(object):
    filename = related.StringField()


@related.immutable
class Influxdb(object):
    host = related.StringField()
    port = related.IntegerField()
    username = related.StringField()
    password = related.StringField()
    database = related.StringField()


@related.mutable
class CommandConfig(object):
    target_device_list = related.SequenceField(TargetDevice)
    database = related.ChildField(Database, required=False)
    influxdb = related.ChildField(Influxdb, required=False)
    set_measurement_interval = related.IntegerField(required=False)
    dry_run = related.BooleanField(default=False, required=False)
    no_scan = related.BooleanField(default=False, required=False)
