"""Hold Space to turn Port F; release to return. Esc exits."""
import argparse
import asyncio
import ctypes
from pathlib import Path

from hub_connect import connect_hub


async def run(args):
    hub = await connect_hub('ble', args.name)
    try:
        await hub.run(str(Path(__file__).with_name('keyboard_hub.py')), wait=False)
        await asyncio.sleep(0.8)
        if args.self_test:
            await hub.write(bytes([45]))
            await asyncio.sleep(0.6)
            await hub.write(bytes([0]))
            await asyncio.sleep(0.6)
            lines = b'\n'.join(hub.output).decode()
            if 'ANGLE' not in lines or 'KEYBOARD READY' not in lines:
                raise RuntimeError('Hub did not acknowledge the movement test')
            print('Realtime command test passed.', flush=True)
            return
        key_state = ctypes.windll.user32.GetAsyncKeyState
        key_state.argtypes = [ctypes.c_int]
        key_state.restype = ctypes.c_short
        print('READY: Hold SPACE = 45 degrees; release = 0. ESC stops. Keys work across apps.', flush=True)
        last_target = None
        last_send = 0
        loop = asyncio.get_running_loop()
        while not key_state(0x1B) & 0x8000:
            target = 45 if key_state(0x20) & 0x8000 else 0
            now = loop.time()
            if target != last_target or now - last_send >= 0.4:
                await asyncio.wait_for(hub.write(bytes([target])), timeout=3)
                if target != last_target:
                    print(f'Space {"held" if target else "released"}: {target} degrees', flush=True)
                last_target, last_send = target, now
            await asyncio.sleep(0.01)
    finally:
        try:
            await asyncio.wait_for(hub.write(bytes([0])), timeout=2)
            await asyncio.sleep(0.2)
            await asyncio.wait_for(hub.stop_user_program(), timeout=2)
        finally:
            await asyncio.wait_for(hub.disconnect(), timeout=3)
        print('Stopped and disconnected.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='Panther')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        pass
