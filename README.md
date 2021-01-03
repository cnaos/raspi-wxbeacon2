# はじめに

## このプログラムについて

OmronのBluetooth環境センサー 2JCIE-BL01(WxBeacon2)から観測データを読み出すためのRaspberry pi用Pythonプログラムです。

環境センサーのデータ保存有りモードでの運用を前提としているため、
読み出し側のRaspberry piがある程度停止していても、データの欠測が起こりにくいのが特徴です。


## 動作環境

* Raspberry Pi 4
* Omron環境センサー 2JCIE-BL01

## OS

```
Distributor ID:	Raspbian
Description:	Raspbian GNU/Linux 10 (buster)
Release:	10
Codename:	buster
```

## BLE関係のOS用パッケージ

* libbluetooth3-dev 
* libglib2.0 
* libboost-python-dev
* libboost-thread-dev

インストールコマンド
```bash
sudo apt install libbluetooth3-dev libglib2.0 libboost-python-dev libboost-thread-dev
```

## python3の依存ライブラリ

* bluepy
    * BLE環境センサーとの通信用
    * version 1.3.0
* peewee
    * 環境センサーから読みだしたデータをsqliteに保存する
    * version 3.14.0
* PyYAML
    * 設定ファイル(config.yaml)の読み込み
    * version 5.3.1
* influxdb
    * influxdbへ環境センサーから採取したデータを投げる
    * version 5.3.1
* tqdm
    * プログレスバー用
    * version 4.55.0
* related
    * 設定ファイルの読み込みと構造化用
    * version 0.7.2

# プログラムの説明

## main.py

Omronの環境センサー 2JCIE-BL01 からデータを読み出してSQLite DBに保存するプログラムです。 読み取り対象の環境センサーは config.yamlで BLEデバイスのMACアドレスで指定します。

前回のコマンド起動時の取り込みの最終位置からの差分取り込みを行います。

### コマンドラインオプション

指定したデバイスだけ処理したい場合や、観測データの差分読み出しではなく、 指定した範囲のページを読み出したい場合はコマンドライン引数で指定します。

```
usage: main.py [-h] [--addr XX:XX:XX:XX:XX] [--pagerange [0-2047] [0-2047]]
               [--setinterval [1-3600]] [--dryrun] [--noscan]

OMRONの環境センサーから観測データを取得します

optional arguments:
  -h, --help            show this help message and exit
  --addr XX:XX:XX:XX:XX
                        環境センサーのMACアドレスを指定する
  --pagerange [0-2047] [0-2047]
                        データの読み出し範囲の開始ページと終了ページを指定する
  --setinterval [1-3600]
                        測定間隔を変更する **注意** データの記録位置が0ページにリセットされ、既存データが上書きされる。
  --dryrun              DBに書き込まない、測定間隔を変更しない
  --noscan              観測データのページ読み込みを行わない。
```

#### 例1:測定間隔を変更する

この例では300秒=5分間隔での測定を指定しています。
環境センサー側の最新の観測データの書き込み位置が0ページにリセットされるので注意してください。
```
main.py --addr XX:XX:XX:XX:XX:XX --setinterval 300
```

#### 例2:指定したページのデータを読み込む

データ取り込みの開始位置=ページ2045と終了位置=ページ3を指定しています。
この場合は「2045, 2046, 2047, 0, 1, 2, 3」という順序でデータを読み出します。

```
main.py --addr XX:XX:XX:XX:XX:XX --scanrange 2045 3
```

## post_influxdb.py

SQLite DBに保存されている環境センサーデータを読み出して、 influxdbにPOSTするプログラムです。 こちらも前回のコマンド起動時にSQLite DBからinfluxdbへ送信が完了したところからの差分送信になっています。

こちらにはコマンドラインオプションはありません。

## 設定ファイル

### config.yaml

```
target_device_list:
  - addr: xx:xx:xx:xx:xx:xx
  - addr: xx:xx:xx:xx:xx:xx

database:
  filename: "env_sensor.sqlite"

influxdb:
  host: 'localhost'
  port: 8086
  username: 'root'
  password: 'root'
  database: "env_sensor"
```

#### target_device_list

スキャン対象の環境センサーのリストを渡します。 BLE MACアドレスをaddrとして指定します。 

BLE MACアドレスタイプはaddr_typeとして指定できますが、省略時はデフォルト値の"random"が使われます。

#### database

環境センサーから読みだした測定データを一時的に保存するSQLiteDBのファイル名を指定します

#### influxdb

SQLiteDBから取り出したデータをPOSTするinfluxdbを指定します。

### logging_conf.yaml

pythonのlogging.config用のファイルです。


# その他

## ソースコードの構成

* main.py
  * 環境センサーから観測データを読み出してDBに保存する
* post_influxdb.py
  * DBに保存してある観測データをinfluxdbへPOSTする
* command_config.py
  * 設定ファイルの構造化用クラス群
* db_model.py
  * DBのモデル
* omron_env_sensor.py
  * Omron環境センサーのBLE Characteristicsと読み書きするデータを扱うためのクラス
* util.py
  * その他のクラス 

# 参考にさせていただいた資料

* https://ambidata.io/samples/temphumid/ble-gw-omron/
    * ここのpythonスクリプトをベースにしました。
    * https://github.com/AmbientDataInc/EnvSensorBleGw/blob/master/src/gw_RPi/env2ambientCS.py
* https://iot-plus.net/make/raspi/visualizing-watt-environment-using-influxdb-grafana/
    * influxdbとgrafanaをraspberry pi上にインストールする際の参考にしました。
* 2JCIE-BL01のユーザーズマニュアル
    * https://www.omron.co.jp/ecb/product-detail?partNumber=2JCIE-BL

