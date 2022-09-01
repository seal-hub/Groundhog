#!/bin/bash
SNAPSHOT_NAME=$1
$LATTE_PATH/scripts/load_snapshot.sh $SNAPSHOT_NAME
sleep 4
adb install -r -g $LATTE_PATH/Setup/Latte.apk
sleep 2
$LATTE_PATH/scripts/enable-service.sh
sleep 3
$LATTE_PATH/scripts/disable-service.sh
sleep 2
$LATTE_PATH/scripts/save_snapshot.sh $SNAPSHOT_NAME

