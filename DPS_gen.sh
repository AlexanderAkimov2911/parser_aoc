#!/bin/bash


for ((;;)) 
do
time=$(date +%H:%M:%S)
line1="[$time] You crush Avatar of Yig for 1125."
line2="[$time] You critically crush Zealot of Yig for 2010."

echo $line1 >> CombatLog-2024-09-05_2331.txt
echo $line2 >> CombatLog-2024-09-05_2331.txt

sleep 0.5
done



#[00:14:00] You crush Avatar of Yig for 1125.
#date +%H:%M:%S
