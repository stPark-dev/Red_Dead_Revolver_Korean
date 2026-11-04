"""Fresh boot -> main menu, detecting the title screen by image similarity (headless :99)."""
import sys, time
sys.path.insert(0, 'tools')
import pine, xinput
from PIL import Image, ImageChops, ImageStat
SCR = sys.argv[1]
ref = Image.open('work/ref_title.png').convert('L').crop((250, 380, 800, 450))
def diff(path):
    im = Image.open(path).convert('L').crop((250, 380, 800, 450))
    return ImageStat.Stat(ImageChops.difference(im, ref)).mean[0]
p = pine.wait(60); time.sleep(10)
tmp = SCR + '.tmp.png'
for i in range(40):
    xinput.shot(tmp); dv = diff(tmp)
    if dv < 6:
        print('title detected after', i, 'polls'); break
    xinput.press(['k'], hold=0.25); time.sleep(3)
else:
    print('title NOT detected'); sys.exit(1)
time.sleep(1); xinput.press(['Return'], hold=0.3); time.sleep(40)
xinput.shot(SCR)
