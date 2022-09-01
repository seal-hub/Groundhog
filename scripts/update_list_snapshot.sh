#!/bin/bash
for snapshot in $($LATTE_PATH/scripts/list_snapshots.sh); do
  echo "Updating $snapshot"
  $LATTE_PATH/scripts/update_snapshot.sh $snapshot
done
