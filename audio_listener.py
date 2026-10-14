"""WASAPI loopback helpers + optional COM serial stream."""

from __future__ import annotations

import argparse
import sys
import time
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

from angle_map import rms_to_angle, should_send
from config import (
    ANGLE_DEADBAND,
    BAUD_RATE,
    BLOCK_SIZE,
    MAX_ANGLE,
    MIN_RMS,
    PEAK_RMS,
    SAMPLE_RATE,
    SERIAL_PORT,
)


def get_wasapi_loopback_device() -> int:
    hostapis = sd.query_hostapis()
    wasapi_index = None
    for idx, api in enumerate(hostapis):
        if "WASAPI" in api["name"]:
            wasapi_index = idx
            break

    if wasapi_index is None:
        raise RuntimeError("Windows WASAPI host API not detected.")

    devices = list(sd.query_devices())

    for idx, dev in enumerate(devices):
        name = dev["name"]
        if (
            dev["hostapi"] == wasapi_index
            and "[Loopback]" in name
            and dev["max_input_channels"] > 0
        ):
            return idx

    default_speakers = sd.default.device[1]
    if default_speakers is None or default_speakers < 0:
        raise RuntimeError("No default WASAPI output device configured.")

    speaker_info = sd.query_devices(default_speakers)
    speaker_name = speaker_info["name"]

    for idx, dev in enumerate(devices):
        if (
            dev["hostapi"] == wasapi_index
            and dev["name"] == speaker_name
            and dev["max_input_channels"] > 0
        ):
            return idx

    for idx, dev in enumerate(devices):
        if (
            dev["hostapi"] == wasapi_index
            and speaker_name in dev["name"]
            and dev["max_input_channels"] > 0
        ):
            return idx

    for idx, dev in enumerate(devices):
        if dev["hostapi"] == wasapi_index and dev["max_output_channels"] > 0:
            return idx

    raise RuntimeError("No WASAPI loopback device found.")


def list_audio_devices() -> None:
    print(sd.query_devices())
    print()
    try:
        print("Default devices:", sd.default.device)
    except Exception as exc:
        print(f"Default devices unavailable: {exc}")


def list_serial_ports() -> None:
    try:
        from serial.tools import list_ports
    except ImportError:
        print("pyserial is required: pip install pyserial")
        return

    ports = list(list_ports.comports())
    if not ports:
        print("No serial ports found.")
        return

    for port in ports:
        print(f"{port.device:8}  {port.description}  [{port.hwid}]")


class SerialByteSink:
    def __init__(self, port: str, baud: int) -> None:
        import serial

        self._serial = serial.Serial(port, baud, timeout=0.05, write_timeout=0.05)
        time.sleep(1.5)

    def write(self, angle: int) -> None:
        import serial

        try:
            self._serial.write(bytes([angle]))
        except serial.SerialTimeoutException:
            pass

    def close(self) -> None:
        try:
            self._serial.write(bytes([0]))
            self._serial.close()
        except Exception:
            pass


class DryRunSink:
    def write(self, angle: int) -> None:
        print(f"angle={angle:02d}", flush=True)

    def close(self) -> None:
        print("Mouth parked at 0 degrees (dry-run).")


def build_callback(
    sink: object,
    min_rms: float,
    peak_rms: float,
    max_angle: int,
    deadband: int,
    verbose: bool,
) -> Callable:
    last_sent_angle = -1

    def callback(indata, frames, time_info, status):
        nonlocal last_sent_angle
        if status and verbose:
            print(status, file=sys.stderr)

        rms = float(np.sqrt(np.mean(indata**2)))
        target_angle = rms_to_angle(rms, min_rms, peak_rms, max_angle)

        if should_send(target_angle, last_sent_angle, deadband):
            sink.write(target_angle)
            last_sent_angle = target_angle
            if verbose:
                print(f"rms={rms:.4f} → {target_angle}°", flush=True)

    return callback


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stream WASAPI loopback RMS as single-byte jaw angles."
    )
    parser.add_argument("--port", default=SERIAL_PORT)
    parser.add_argument("--baud", type=int, default=BAUD_RATE)
    parser.add_argument("--min-rms", type=float, default=MIN_RMS)
    parser.add_argument("--peak-rms", type=float, default=PEAK_RMS)
    parser.add_argument("--deadband", type=int, default=ANGLE_DEADBAND)
    parser.add_argument("--device", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list-ports", action="store_true")
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    if args.list_ports:
        list_serial_ports()
        return 0

    if args.list_devices:
        list_audio_devices()
        return 0

    if args.dry_run:
        sink: object = DryRunSink()
        print("Dry-run mode: angles print to stdout (no serial).")
    else:
        try:
            sink = SerialByteSink(args.port, args.baud)
        except Exception as exc:
            print(f"Error opening serial port {args.port}: {exc}")
            return 1

    try:
        if args.device is not None:
            device_idx = args.device
        else:
            device_idx = get_wasapi_loopback_device()
        print(f"Bound to audio device [{device_idx}]: {sd.query_devices(device_idx)['name']}")

        callback = build_callback(
            sink, args.min_rms, args.peak_rms, MAX_ANGLE, args.deadband, args.verbose
        )

        stream_kwargs = dict(
            device=device_idx,
            channels=1,
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            callback=callback,
        )
        if hasattr(sd, "WasapiSettings"):
            stream_kwargs["extra_settings"] = sd.WasapiSettings(exclusive=False)

        with sd.InputStream(**stream_kwargs):
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping audio stream...")
    except Exception as exc:
        print(f"Audio stream error: {exc}")
        return 1
    finally:
        sink.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
