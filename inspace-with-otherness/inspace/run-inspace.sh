#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
SCLANG='/Applications/SuperCollider/SuperCollider.app/Contents/MacOS/sclang'
PD='/Applications/Pd-0.50-0.app/Contents/Resources/bin/pd'

log_echo () {
    id=$1
    line=$2
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$id] $line"
}

run_sclang () {
    while true; do
        "$SCLANG" "$SCRIPT_DIR/inspace.scd" 2>&1 | while read line; do
            log_echo sclang "$line"
        done
        log_echo inspace 'sclang died! restarting...'
        sleep 2    
    done
}

run_pd () {
    while true; do
        "$PD" -nogui "$SCRIPT_DIR/nsynth.pd" 2>&1 | while read line; do
            log_echo pd "$line"
        done
        log_echo inspace 'pd died! restarting...'
        sleep 2
    done
}

run_pd &
RUN_PD_PID=$!

sleep 5

run_sclang &
RUN_SCLANG_PID=$!

cleanup () {
    log_echo inspace "killing run_sclang ($RUN_SCLANG_PID)"
    kill "$RUN_SCLANG_PID"
    log_echo inspace "killing run_pd ($RUN_PD_PID)"
    kill "$RUN_PD_PID"
    log_echo inspace "killing all scsynth processes"
    killall scsynth
    log_echo inspace "killing all sclang processes"
    killall sclang
    log_echo inspace "killing all pd processes"
    killall pd
}

trap cleanup SIGHUP SIGINT SIGTERM

wait "$RUN_SCLANG_PID"
wait "$RUN_PD_PID"

