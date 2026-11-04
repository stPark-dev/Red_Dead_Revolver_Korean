#!/bin/bash
# boot iso, go to main menu, screenshot to $2, print TLB miss count
tools/run.sh "$1"
PY=${PY:-python3}
timeout 300 $PY -I - "$2" <<'PY'
import sys,time; sys.path.insert(0,'tools'); import pine,xinput
p=pine.wait(60); time.sleep(12)
for i in range(10):
    xinput.press(['k']); time.sleep(3)
xinput.press(['Return']); time.sleep(40)
xinput.shot(sys.argv[1])
PY
grep -c "TLB Miss" ~/.var/app/net.pcsx2.PCSX2/config/PCSX2/logs/emulog.txt
