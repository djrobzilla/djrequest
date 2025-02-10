#!/bin/bash

docker-compose up -d djrequestdb
sleep 10
docker-compose up -d ingress
docker-compose build djrequest
docker-compose run djrequest