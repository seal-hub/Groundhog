pkg_name=$1
output_dir=${2:-"$LATTE_PATH/OS_APKs/dev_apks/"}
device_name=${3:-"emulator-5554"}
apk_dir=$output_dir/$pkg_name
mkdir -p $apk_dir
paths=$(adb -s $device_name shell pm path $pkg_name | awk '{print substr($1, index($1, ":")+1, index($1, ".apk")-1);}')
for path in $paths; do
	adb -s $device_name pull "$path" "$apk_dir"
done
