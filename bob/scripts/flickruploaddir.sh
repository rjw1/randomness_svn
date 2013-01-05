#!/bin/bash
#script to upload all files in the current dir
count=0
total=`ls |wc -l`
mkdir -p uploaded
for file in * 
do
(( count=count+1 ))
echo "uploading $count of $total"
flickrupload.sh $file
mv $file uploaded/$file
done
