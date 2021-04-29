#!/bin/sh
# by Dann Mensah dann.mensah@aalto.fi

# how to use:
# 1. put this file in your Aalto home folder (e.g. using SMB)
# 2. log in to kosh: ssh usernamekosh.aalto.fi
# 3. run the script: bash paniikki-get-load.sh

parallel -i -j100 ssh -oBatchMode=yes -oConnectTimeout=2 {} 'l="$(cut -d" " -f1-3 /proc/loadavg)"; g="$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader)"; u="$(users | tr " " "\n" | sort -u | tr "\n" " " | sed "s, *$,," | sed "s,\(..*\),(\1),")"; t="$(who | egrep -c "\<tty[0-9]\>" | tr "01" " *")"; printf "%-17s [GPU:%6s]  %1s  %-15s %1s\n" "$l" "$g" "$t" "{}" "$u"' -- \
  deadfish entropy false fugue piet rename numberwang smith unlambda whitespace zombie \
| sort -n
