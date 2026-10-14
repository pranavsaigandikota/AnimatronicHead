"""Realtime lip-sync over USB pybricksdev (Port F)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd

from angle_map import rms_to_angle, should_send
from audio_listener import get_wasapi_loopback_device
from config import (
    ANGLE_DEADBAND,
    BLOCK_SIZE,
    HUB_NAME,
    MAX_ANGLE,
    MIN_RMS,
    PEAK_RMS,
    SAMPLE_RATE,
)
from hub_connect import connect_hub

HUB_FIRMWARE = Path(__file__).resolve().parent / "hub_firmware.py"


class LatestWinsSink:
    def __init__(self, hub, loop: asyncio.AbstractEventLoop) -> None:
        self._hub = hub
        self._loop = loop
        self._pending: Optional[int] = None
        self._busy = False

    def write(self, angle: int) -> None:
        self._pending = angle
        if not self._busy:
            asyncio.run_coroutine_threadsafe(self._kick(), self._loop)

    async def _kick(self) -> None:
        if self._busy:
            return
        self._busy = True
        try:
            while True:
                angle = self._pending
                if angle is None:
                    break
                self._pending = None
                try:
                    await self._hub.write(bytes([angle]))
                except Exception:
                    break
        finally:
            self._busy = False
            if self._pending is not None:
                asyncio.run_coroutine_threadsafe(self._kick(), self._loop)

    async def park(self) -> None:
        self._pending = 0
        await self._kick()


async def run_stream(args: argparse.Namespace) -> int:
    if not HUB_FIRMWARE.exists():
        print(f"Missing {HUB_FIRMWARE}")
        return 1

    hub = await connect_hub(args.transport, args.name)
    loop = asyncio.get_running_loop()
    sink = LatestWinsSink(hub, loop)

    try:
        print(f"Starting {HUB_FIRMWARE.name} (mouth = Port F)...")
        await hub.run(str(HUB_FIRMWARE), wait=False, print_output=True)
        await asyncio.sleep(0.8)

        device_idx = (
            args.device if args.device is not None else get_wasapi_loopback_device()
        )
        print(f"Audio device [{device_idx}]: {sd.query_devices(device_idx)['name']}")
        print("Play speech on speakers. Ctrl+C to stop.")

        last_sent = -1

        def callback(indata, frames, time_info, status):
            nonlocal last_sent
            rms = float(np.sqrt(np.mean(indata**2)))
            target = rms_to_angle(rms, args.min_rms, args.peak_rms, MAX_ANGLE)
            if should_send(target, last_sent, args.deadband):
                sink.write(target)
                last_sent = target
                if args.verbose:
                    print(f"rms={rms:.4f} → {target}°", flush=True)

        kwargs = dict(
            device=device_idx,
            channels=1,
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            callback=callback,
        )
        if hasattr(sd, "WasapiSettings"):
            kwargs["extra_settings"] = sd.WasapiSettings(exclusive=False)

        with sd.InputStream(**kwargs):
            while True:
                await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass
    finally:
        await sink.park()
        try:
            await hub.stop_user_program()
        except Exception:
            pass
        try:
            await hub.disconnect()
        except Exception:
            pass
        print("Mouth parked. Disconnected.")

    return 0


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Realtime audio → Port F jaw over USB")
    p.add_argument("--transport", choices=("usb", "ble"), default="usb")
    p.add_argument("--name", default=HUB_NAME)
    p.add_argument("--min-rms", type=float, default=MIN_RMS)
    p.add_argument("--peak-rms", type=float, default=PEAK_RMS)
    p.add_argument("--deadband", type=int, default=ANGLE_DEADBAND)
    p.add_argument("--device", type=int, default=None)
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    try:
        return asyncio.run(run_stream(args))
    except KeyboardInterrupt:
        print("\nStopping...")
        return 0
    except Exception as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
