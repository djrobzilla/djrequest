#!/bin/bash

docker-compose up -d djrequestdb
sleep 10
docker-compose up -d djrequest
docker-compose up -d ingress