#!/bin/bash
is_all=${1:-NO}
snapshots=`adb emu avd snapshot list | awk '{ print $2 }' | sed 1,2d | grep -v "BASE" | grep -v "default_boot" | ( [[ $is_all == "YES" ]] && cat - || grep -v "_TMP")`
for snapshot in $snapshots; do
  echo "$snapshot"
done
