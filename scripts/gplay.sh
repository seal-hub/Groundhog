pkg_name=$1
device_name=${2:-"emulator-5554"}
adb -s $device_name shell am start -a android.intent.action.VIEW -d "market://details?id=$pkg_name"
