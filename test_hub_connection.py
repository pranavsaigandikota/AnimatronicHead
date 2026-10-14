"""USB connection test — Port F mouth wiggle."""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

from config import HUB_NAME, MOUTH_PORT

WIGGLE_SCRIPT = f"""\
from pybricks.hubs import InventorHub
from pybricks.pupdevices import Motor
from pybricks.parameters import Port, Stop
from pybricks.tools import wait

hub = InventorHub()
mouth = Motor(Port.{MOUTH_PORT})
mouth.reset_angle(0)
print("connected: mouth on Port {MOUTH_PORT}")

mouth.run_target(1000, 35, then=Stop.NONE, wait=True)
wait(250)
mouth.run_target(1000, 0, then=Stop.COAST, wait=True)
wait(150)
mouth.run_target(1000, 25, then=Stop.NONE, wait=True)
wait(200)
mouth.run_target(1000, 0, then=Stop.COAST, wait=True)
print("wiggle done — Port {MOUTH_PORT} OK")
"""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Port F jaw USB connection test")
    p.add_argument("--transport", choices=("usb", "ble"), default="usb")
    p.add_argument("--name", default=HUB_NAME)
    return p.parse_args(argv)


def run_via_cli(args: argparse.Namespace, script_path: Path) -> int:
    cmd = [sys.executable, "-m", "pybricksdev", "run", args.transport]
    if args.transport == "ble":
        cmd.extend(["-n", args.name])
    cmd.append(str(script_path))
    print("Running:", " ".join(cmd))
    rc = subprocess.run(cmd).returncode
    if rc == 0:
        print("OK — USB/hub link works. Mouth is on Port F.")
    else:
        print(f"FAILED (exit {rc}). Close Pybricks Code, re-plug USB, hub ON?")
    return rc


async def run_via_api(args: argparse.Namespace, script_path: Path) -> int:
    from hub_connect import connect_hub

    hub = await connect_hub(args.transport, args.name)
    try:
        await hub.run(str(script_path), wait=True, print_output=True)
        print("OK — hub link works. Mouth is on Port F.")
        return 0
    finally:
        try:
            await hub.disconnect()
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    script_path = Path(__file__).resolve().parent / "_mouth_wiggle_temp.py"
    script_path.write_text(WIGGLE_SCRIPT, encoding="utf-8")
    try:
        return asyncio.run(run_via_api(args, script_path))
    except ImportError as exc:
        print(f"Missing package ({exc}); trying CLI...")
        return run_via_cli(args, script_path)
    except Exception as exc:
        print(f"Connection test failed: {exc}")
        return 1
    finally:
        script_path.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
