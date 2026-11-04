"""Boot-to-title helper: waits for PINE, presses Cross through notices, screenshots."""
import sys, time
sys.path.insert(0, 'tools')
import pine, xinput
out = sys.argv[1]
p = pine.wait(60); time.sleep(14)
for i in range(2):
    xinput.press(['k']); time.sleep(3)
xinput.shot(out)
