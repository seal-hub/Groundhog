#!/bin/bash
INITIAL_SNAPSHOT=$1
LAST_SNAPSHOT=BM_SNAPSHOT
FINAL_NAV_FILE="finish_nav_result.txt"
FINAL_ACITON_FILE="finish_nav_action.txt"
OUTPUT_PATH=result/$1
REG_OUTPUT_PATH=$OUTPUT_PATH/REG
TB_OUTPUT_PATH=$OUTPUT_PATH/TB
mkdir -p $OUTPUT_PATH
rm -rf $OUTPUT_PATH/*
mkdir -p $REG_OUTPUT_PATH
mkdir -p $TB_OUTPUT_PATH
RESULT_FILE=$OUTPUT_PATH/summary.txt
./load_snapshot.sh $1 || exit 1
sleep 3
./enable-talkback.sh;
sleep 2
./save_snapshot.sh $LAST_SNAPSHOT
echo "Result of Snapshot $1" > $RESULT_FILE
COUNT=0
while ! ./android_file_exists.sh $FINAL_NAV_FILE;
do
  COUNT=$((COUNT+1))
  ./load_snapshot.sh $LAST_SNAPSHOT || exit 1
  echo "wait for adb"
  sleep 3
  adb wait-for-device
  echo "Perform Next!"
  ./send-command.sh nav_next
  NEXT_COMMAND=$(./wait_for_file.sh $FINAL_ACITON_FILE)
  if ./android_file_exists.sh $FINAL_NAV_FILE; then
    break
  fi
  echo "$COUNT: [$NEXT_COMMAND]" >> $RESULT_FILE
  echo "Get another snapshot"
  ./save_snapshot.sh $LAST_SNAPSHOT
  sleep 2
  echo "Perform Select!"
  ./send-command.sh nav_select
  ./wait_for_file.sh $FINAL_ACITON_FILE
  ./capture_layout.sh > $TB_OUTPUT_PATH/${COUNT}.xml
  #----------------
  echo "Now with regular executor"
  ./load_snapshot.sh $LAST_SNAPSHOT || exit 1
  echo "wait for adb"
  sleep 3
  adb wait-for-device
  ./disable-talkback.sh
  ./send-command.sh enable
  ./send-command.sh set_step_executor regular
  ./send-command.sh set_physical_touch true
  ./send-command.sh do_step "$NEXT_COMMAND"
  sleep 3
  ./capture_layout.sh > $REG_OUTPUT_PATH/${COUNT}.xml
  #---------

  echo "Groundhug Day!"
  echo "-------"
done
./wait_for_file.sh $FINAL_NAV_FILE
