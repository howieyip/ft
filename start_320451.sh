#!/bin/bash

cd /data/release/ft
date > logs/start.log
if [ -f supervisord.pid ]; then
  cat supervisord.pid >> logs/start.log
  kill $(cat supervisord.pid)
fi
sleep 3
supervisord -c supervisord_320451.conf
supervisorctl start all >> logs/start.log
