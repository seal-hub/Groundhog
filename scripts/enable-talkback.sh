#!/bin/bash
device_name=${1:-"emulator-5554"}
adb -s $device_name shell settings put secure enabled_accessibility_services com.google.android.marvin.talkback/com.google.android.marvin.talkback.TalkBackService:dev.navids.latte/dev.navids.latte.app.MyLatteService
