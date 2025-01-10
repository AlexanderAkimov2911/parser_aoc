#!/bin/bash


for ((;;)) 
do
time=$(date +%H:%M:%S)
damage=$RANDOM
line1="[$time] You crush Avatar of Yig for $damage."
line2="[$time] You critically crush Zealot of Yig for $damage."

echo $line1 >> CombatLog-2024-09-05_2331.txt
echo $line2 >> CombatLog-2024-09-05_2331.txt

sleep 1
done



#[00:14:00] You crush Avatar of Yig for 1125.
#date +%H:%M:%S
