"""
Mouth motor: Port F
Host streams raw angle bytes (0–45) to stdin.
"""

from pybricks.hubs import InventorHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port, Stop
from pybricks.tools import wait, StopWatch
from usys import stdin
import uselect
from micropython import kbd_intr

# Angle 3 is a raw data byte, not a keyboard interrupt.
kbd_intr(-1)

hub = InventorHub()
mouth = Motor(Port.F)
head = Motor(Port.E)
head.reset_angle(0)
head.control.limits(speed=60, acceleration=120)

mouth.reset_angle(0)
mouth.control.limits(speed=400, acceleration=1600)

poll = uselect.poll()
poll.register(stdin, uselect.POLLIN)

SPEED = 400
MAX_ANGLE = 45
current_target = -1
timer = StopWatch()
speech_timer = StopWatch()
speech_timer.reset()
has_spoken = False
head_timer = StopWatch()
head_target = 0
head_direction = 1

while True:
    if poll.poll(0):
        target = None
        while poll.poll(0):
            byte_data = stdin.buffer.read(1)
            if not byte_data:
                break
            target = byte_data[0]
            timer.reset()
            if target > 0:
                speech_timer.reset()
                has_spoken = True

        if target is None:
            continue

        if target > MAX_ANGLE:
            target = MAX_ANGLE

        if target != current_target:
            current_target = target
            if current_target == 0:
                mouth.run_target(SPEED, 0, then=Stop.COAST, wait=False)
            else:
                mouth.run_target(
                    SPEED, current_target, then=Stop.COAST, wait=False
                )
    if timer.time() > 1500 and current_target != 0:
        mouth.run_target(SPEED, 0, then=Stop.COAST, wait=False)
        current_target = 0
    talking = has_spoken and speech_timer.time() < 350 and timer.time() < 1500
    if talking:
        if head_target == 0 or head_timer.time() >= 2200:
            # Alternate left and right while speech remains active.
            head_target = head_direction * 45
            head_direction = -head_direction
            head.run_target(60, head_target, then=Stop.COAST, wait=False)
            head_timer.reset()
    elif head_target != 0:
        head_target = 0
        head.run_target(60, 0, then=Stop.COAST, wait=False)
    wait(1)
