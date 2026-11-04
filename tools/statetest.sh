#!/bin/bash
# boot iso, load title savestate (slot 1), press START, screenshot to $2, print TLB miss count
tools/run.sh "$1"
PY=${PY:-python3}
timeout 200 $PY -I - "$2" "${WAIT:-35}" <<'PY'
import sys,time; sys.path.insert(0,'tools'); import pine,xinput
p=pine.wait(60); time.sleep(6)
p.load_state(1); time.sleep(5)
xinput.press(['Return'], hold=0.3); time.sleep(1.5); xinput.press(['Return'], hold=0.3); time.sleep(int(sys.argv[2]))
xinput.shot(sys.argv[1])
PY
grep -c "TLB Miss" ~/.var/app/net.pcsx2.PCSX2/config/PCSX2/logs/emulog.txt
