#!/bin/bash
while [ ! -f my_result.txt ]
do
  echo "Wait.."
  sleep 2 # or less like 0.2
  adb exec-out run-as dev.navids.latte cat files/test_result.txt > my_result.txt
 cat my_result.txt | grep -q "No such file or directory" && rm my_result.txt
done
cat my_result.txt
rm my_result.txt
