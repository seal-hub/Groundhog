#!/bin/bash
APK_NAME=$1
RESULT_PATH=${2:-$(realpath ../dev_results)}
RESULT_PATH=$(realpath "$RESULT_PATH")
source ../.env/bin/activate
for SNAPSHOT in $(../scripts/list_snapshots.sh); do
  APP_NAME=${SNAPSHOT%%.S_*}
  if [[ "$APP_NAME" != *"$APK_NAME"* ]]; then
    continue
  fi
  ./run_snapshot.sh $SNAPSHOT $RESULT_PATH
done

