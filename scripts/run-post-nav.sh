#!/bin/bash
out_file=finish_nav_reult.txt
while [ ! -f $out_file ]
do
  echo "Wait.."
  sleep 2 # or less like 0.2
  adb exec-out run-as dev.navids.latte cat files/$out_file > $out_file
 cat $out_file | grep -q "No such file or directory" && rm $out_file
done
cat $out_file
rm $out_file
