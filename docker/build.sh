#!/bin/bash

#cp Dockerfile.in Dockerfile
#python scripts/cmd2label.py cmore_t2star_cmd.json cmore_b0_cmd.json cmore_preproc_cmd.json >> Dockerfile

tag=0.0.1
docker build -t martincraig/basil-qmenta .
docker tag martincraig/basil-qmenta martincraig/basil-qmenta:$tag 
#docker push martincraig/xnat-cmore:$tag
