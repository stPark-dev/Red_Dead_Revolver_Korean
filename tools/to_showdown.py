"""From the main menu (after boot_to_menu.py): Showdown poster -> 1P + one CPU -> first level -> match.
Captures DIR/mp_*.png along the way, then pauses the match (START) and captures DIR/mp_pause.png.
Menu inputs need ~3 s between presses or the poster drops them.

usage: to_showdown.py DIR
"""
import sys, time, os
sys.path.insert(0, 'tools')
import xinput
out = sys.argv[1]
os.makedirs(out, exist_ok=True)


def st(key, wait, shot=None):
    xinput.press([key], hold=0.3); time.sleep(wait)
    if shot: xinput.shot(os.path.join(out, shot))


st('Left', 4)
st('k', 5, 'mp_join.png')       # open the Showdown poster
st('k', 3)                       # 1P joins, picks a character in the lineup
st('k', 3, 'mp_p1.png')          # confirm 1P character -> pointer on slot 1
st('Right', 3)
st('k', 3)                       # CPU joins slot 2
st('k', 3)                       # CPU character in the lineup
st('k', 3, 'mp_cpu.png')         # confirm -> START prompt
st('Return', 7, 'mp_level.png')  # level poster
st('k', 95, 'mp_loading.png')    # start; loading screen with START prompt
st('Return', 4, 'mp_intro.png')  # into the match: win-condition banner
st('Return', 3, 'mp_pause.png')  # pause
