#!/bin/bash
is_all=${1:-NO}
snapshots=`adb emu avd snapshot list | awk '{ print $2 }' | sed 1,2d | grep -v "BASE" | grep -v "default_boot" | ( [[ $is_all == "YES" ]] && cat - || grep -e "_TMP")`
for snapshot in $snapshots; do
  echo "Removing $snapshot"
  adb emu avd snapshot delete $snapshot;
  rm -rf ~/.android/avd/Pixel_Stoat.avd/snapshots/$snapshot
done
