device_name=${2:-"emulator-5554"}
echo "Load snapshot: $1 in device $device_name"
adb -s $device_name emu avd snapshot load $1 | grep "OK" && exit 0 || echo "Error!" && exit 1
