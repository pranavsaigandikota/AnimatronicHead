"""Port F keyboard test: raw target bytes from the computer."""
from pybricks.hubs import InventorHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port, Stop
from pybricks.tools import wait, StopWatch
from usys import stdin
import uselect

hub = InventorHub()
motor = Motor(Port.F)
motor.reset_angle(0)
poll = uselect.poll()
poll.register(stdin, uselect.POLLIN)
timer = StopWatch()
last_target = 0
print("KEYBOARD READY: Port F")
while True:
    target = None
    while poll.poll(0):
        data = stdin.buffer.read(1)
        if not data:
            break
        target = min(data[0], 45)
        timer.reset()
    if timer.time() > 1500 and last_target != 0:
        target = 0
    if target is not None and target != last_target:
        motor.run_target(500, target, then=Stop.HOLD, wait=True)
        last_target = target
        print("ANGLE", motor.angle())
    wait(5)
