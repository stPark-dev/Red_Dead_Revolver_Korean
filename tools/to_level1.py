"""From the main menu (after boot_to_menu.py, fresh memory card): New profile -> New -> Begin chapter 1,
then capture screenshots into DIR every STEP seconds from T0 to T1 seconds after Begin.

usage: to_level1.py DIR T0 T1 STEP
"""
import sys, time, os
sys.path.insert(0, 'tools')
import xinput
out, t0, t1, step = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
os.makedirs(out, exist_ok=True)
for k in ['k', 'k', 'k']:  # profile screen, confirm name, New
    xinput.press([k], hold=0.25); time.sleep(5)
xinput.press(['k'], hold=0.25)  # Begin
start = time.time(); i = 0
while True:
    t = t0 + i * step
    if t > t1: break
    time.sleep(max(0, start + t - time.time()))
    xinput.shot(os.path.join(out, '%03d.png' % i)); i += 1
