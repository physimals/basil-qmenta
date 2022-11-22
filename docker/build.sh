#!/bin/bash

tag=`cat version.txt`
docker build -t martincraig/basil-qmenta .
docker tag martincraig/basil-qmenta martincraig/basil-qmenta:$tag 
#docker push martincraig/basil-qmenta:$tag
