"""Verify the actual speech firmware holds 45 degrees and returns to zero."""
import asyncio
import tempfile
from pathlib import Path
from hub_connect import connect_hub

async def main():
    source = Path(__file__).with_name('hub_firmware.py').read_text(encoding='utf-8')
    source = source.replace('current_target = -1', 'current_target = -1\ntelemetry = StopWatch()')
    source = source.replace('    wait(1)', '    if telemetry.time() >= 50:\n        print("POSITION", mouth.angle(), head.angle())\n        telemetry.reset()\n    wait(1)')
    with tempfile.TemporaryDirectory() as folder:
        script = Path(folder) / 'verify_hub.py'
        script.write_text(source, encoding='utf-8')
        hub = await connect_hub('ble', 'Panther')
        try:
            await hub.run(str(script), wait=False, print_output=False)
            await asyncio.sleep(0.5)
            for _ in range(36):
                await hub.write(bytes([45]))
                await asyncio.sleep(0.2)
            await hub.write(bytes([0]))
            await asyncio.sleep(2.4)
            positions = [int(line.split()[1]) for line in hub.output if line.startswith(b'POSITION ')]
            head_positions = [int(line.split()[2]) for line in hub.output if line.startswith(b'POSITION ')]
            if not positions or min(positions) < -10 or max(positions) > 55 or max(positions) < 10 or abs(positions[-1]) > 10:
                raise RuntimeError(f'Unexpected motor positions: {positions}')
            if min(head_positions) < -50 or max(head_positions) > 50 or min(head_positions) > -25 or max(head_positions) < 25 or abs(head_positions[-1]) > 8:
                raise RuntimeError(f'Unexpected Port E positions: {head_positions}')
            print(f'PASS: measured range {min(positions)} to {max(positions)} degrees; final position {positions[-1]}.')
            print(f'PASS: Port E range {min(head_positions)} to {max(head_positions)}; final position {head_positions[-1]}.')
        finally:
            await asyncio.wait_for(hub.write(bytes([0])), 2)
            await asyncio.sleep(2.4)
            await asyncio.wait_for(hub.stop_user_program(), 2)
            await asyncio.wait_for(hub.disconnect(), 3)

if __name__ == '__main__':
    asyncio.run(main())
