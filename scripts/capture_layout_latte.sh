device_name=${1:-"emulator-5554"}
output_path=${2:-"-"}
SCRIPT_PATH=$(dirname "$0")
source $SCRIPT_PATH/../.env/bin/activate
python $SCRIPT_PATH/../py_src/demo.py --device $device_name --command capture_layout --extra $output_path
