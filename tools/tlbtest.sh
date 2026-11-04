#!/bin/bash
# boot iso, wait, report TLB miss count
tools/run.sh "$1"
PY=${PY:-python3}
timeout 100 $PY -I -c "
import sys,time; sys.path.insert(0,'tools'); import pine; p=pine.wait(60); time.sleep(${2:-30})"
grep -c "TLB Miss" ~/.var/app/net.pcsx2.PCSX2/config/PCSX2/logs/emulog.txt
