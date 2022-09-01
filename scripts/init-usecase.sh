#!/bin/bash
TEST_GUIDELINE=$1
#./send-command.sh NONE
adb push  $TEST_GUIDELINE /data/local/tmp/test_guideline.json
PKG=`python3 get_data.py pkg $TEST_GUIDELINE`
APK_PATH=`python3 get_data.py apk $TEST_GUIDELINE`
if [ "$PKG" = "com.soundcloud.android" ]; then
    adb uninstall $PKG
fi
echo "The app with pkg $PKG is in $APK_PATH"
adb shell pm clear $PKG || adb install -r -t "$APK_PATH"
sleep 1
adb shell monkey -p $PKG 1
sleep 2
if [ "$PKG" = "com.vimeo.android.videoapp" ]; then
	adb shell am force-stop $PKG
	adb shell monkey -p $PKG 1
fi
./send-command.sh set_delay 2000
./send-command.sh init /data/local/tmp/test_guideline.json
./send-command.sh enable
