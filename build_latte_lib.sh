#!/bin/bash
APK_PATH=app/build/outputs/apk/debug/app-debug.apk
TARGET_PATH=Setup/Latte.apk
rm $APK_PATH 2> /dev/null
if ! ./gradlew build; then
	echo "FAILED!"
	exit 1
fi
if ! [[ -f "$APK_PATH" ]]; then
	echo "APK File is not created!"
	exit 1
fi
cp $APK_PATH $TARGET_PATH
echo "The Latte APK is located at $TARGET_PATH"

