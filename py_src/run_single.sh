#!/bin/bash
APK_PATH=$1
APK_PATH=$(realpath "$APK_PATH")
RESULT_PATH=${2:-$(realpath ../dev_results)}
RESULT_PATH=$(realpath "$RESULT_PATH")
MAX_SNAPSHOT=5
MAX_EVENT=300
STOAT_PATH=$(realpath ~/Workspaces/python/Stoat/)
APK_NAME=$(basename "$APK_PATH")
APK_NAME="${APK_NAME%.*}"
deactivate
echo "Running APK $APK_NAME, the result will be written in $RESULT_PATH"
../scripts/load_snapshot.sh BASE
echo "Sleep 5 seconds"
sleep 5
$STOAT_PATH/explore.sh "$APK_PATH" "$MAX_SNAPSHOT" "$MAX_EVENT"
./run_my_snapshots.sh $APK_NAME $RESULT_PATH
