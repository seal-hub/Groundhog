#!/bin/bash
out_file=my_result_custom.txt
while [ ! -f $out_file ]
do
  echo "Wait.."
  sleep 2 # or less like 0.2
  adb exec-out run-as dev.navids.latte cat files/custom_step_result.txt > $out_file
 cat $out_file | grep -q "No such file or directory" && rm $out_file
done
cat $out_file
rm $out_file
