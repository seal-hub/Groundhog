#!/bin/bash
device_name=${1:-"emulator-5554"}
adb -s $device_name shell settings delete secure enabled_accessibility_services
