#!/bin/bash

DEVICE=emulator-5554
SNAPSHOT=$1
STEP=$2
EXECUTOR=${3:REG}
echo "Running on $EXECUTOR"
./load_snapshot.sh $SNAPSHOT  || exit 1
echo "wait for adb"
sleep 3
adb wait-for-device
if [[ $EXECUTOR == REG ]]; 
then
 ./enable-service.sh;
 ./send-command.sh set_step_executor regular;
elif [[ $EXECUTOR == TB ]]; 
then
 ./enable-talkback.sh;
 ./send-command.sh set_step_executor talkback;
else
 echo "UNKNOWN Executor $EXECUTOR";
 exit 1;
fi
./send-command.sh set_delay 2000
./send-command.sh enable
echo "Sleeping for 3 seconds"
sleep 3
echo Send step "$STEP"
./send-command.sh do_step "$STEP"
./run-post-custom.sh
adb exec-out uiautomator dump /dev/tty > $EXECUTOR.txt
