#!/bin/bash
cd /home/narbon/Aplikácie/dennik
PORT="${DENNIK_PORT:-5005}"
export DENNIK_PORT="$PORT"
nohup python3 run.py > /tmp/dennik.log 2>&1 &
sleep 2
echo "Denník spustený na porte $PORT"
echo "Otvára sa v Midori..."
/snap/bin/midori "http://localhost:${PORT}" &