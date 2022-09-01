#!/bin/bash
FLAG=0
RESULT_PATH=$(realpath ../dev_results)
LAST_APK_FILE="com.freemanhealth.EmployeePortal"
for APK_FILE in  ../BM_APKs/extra_az_apks/*.apk; do
	if [ "$(basename "$APK_FILE")" = "$LAST_APK_FILE.apk" ]; then
		FLAG=1
	fi
	if [ $FLAG -eq 0 ]; then
		continue
	fi
	adb kill-server
	adb start-server
	../scripts/remove_snapshots.sh YES
	./run_single.sh "$APK_FILE" "$RESULT_PATH"
done

