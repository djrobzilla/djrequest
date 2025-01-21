#!/bin/bash

docker-compose up -d recipedbserver 
sleep 2
docker-compose build discordbot
docker-compose run discordbot
