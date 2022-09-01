device_name=${1:-"emulator-5554"}
LAYOUT=$(adb -s $device_name exec-out uiautomator dump /dev/tty)
FOO="UI hierchary dumped to: /dev/tty"
LAYOUT=${LAYOUT//"$FOO"/""}
echo "$LAYOUT"
