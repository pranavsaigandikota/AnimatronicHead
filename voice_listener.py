"""Speaker audio to Port F. Escape stops; no microphone is recorded."""
import argparse
import asyncio
import ctypes
from pathlib import Path
ctypes.windll.ole32.CoInitializeEx(None, 0)
import numpy as np
import pyaudiowpatch as pa
from angle_map import rms_to_angle, should_send
from hub_connect import connect_hub

async def run(args):
    audio = pa.PyAudio()
    stream = hub = None
    latest = peak = 0.0
    commands = 0
    loop = asyncio.get_running_loop()
    def update(rms):
        nonlocal latest, peak
        latest = rms
        peak = max(peak, rms)
    def capture(data, frames, time_info, status):
        samples = np.frombuffer(data, dtype=np.float32)
        loop.call_soon_threadsafe(update, float(np.sqrt(np.mean(samples * samples))))
        return None, pa.paContinue
    try:
        if args.speaker:
            device = next((d for d in audio.get_loopback_device_info_generator()
                           if args.speaker.lower() in d['name'].lower()), None)
            if device is None:
                raise RuntimeError(f'Speaker {args.speaker!r} is unavailable. Connect it or choose --speaker.')
        else:
            device = audio.get_default_wasapi_loopback()
        rate = int(device['defaultSampleRate'])
        print(f"Capturing: {device['name']}", flush=True)
        hub = await connect_hub('ble', args.name)
        await hub.run(str(Path(__file__).with_name('hub_firmware.py')), wait=False)
        await asyncio.sleep(0.8)
        stream = audio.open(format=pa.paFloat32, channels=int(device['maxInputChannels']), rate=rate,
                            input=True, input_device_index=int(device['index']),
                            frames_per_buffer=int(rate * 0.02), stream_callback=capture)
        key = ctypes.windll.user32.GetAsyncKeyState
        key.argtypes = [ctypes.c_int]
        key.restype = ctypes.c_short
        print('READY: Speech drives mouth F and left/right motion E. ESC stops and centers both.', flush=True)
        started = loop.time()
        last_target = -1
        last_send = envelope = 0.0
        while not key(0x1B) & 0x8000:
            if args.duration and loop.time() - started >= args.duration:
                break
            if not stream.is_active():
                raise RuntimeError('Audio capture stopped; restart after changing speakers.')
            envelope = latest if latest > envelope else latest * 0.8 + envelope * 0.2
            if latest < args.min_rms:
                envelope = 0.0
            target = rms_to_angle(envelope, args.min_rms, args.peak_rms, 45, args.response_curve)
            if last_target < 0 or (last_target == 0 and target > 0) or should_send(target, last_target, 2) or loop.time() - last_send >= 0.4:
                await asyncio.wait_for(hub.write(bytes([target])), timeout=3)
                commands += int(target > 0)
                if args.verbose and target != last_target:
                    print(f'rms={envelope:.4f} angle={target}', flush=True)
                last_target, last_send = target, loop.time()
            await asyncio.sleep(0.02)
        print(f'Peak RMS={peak:.4f}; open-mouth commands={commands}', flush=True)
        if args.require_audio and not commands:
            raise RuntimeError('No speech-level audio captured.')
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        audio.terminate()
        if hub:
            try:
                await asyncio.wait_for(hub.write(bytes([0])), 2)
                await asyncio.sleep(2.4)
                await asyncio.wait_for(hub.stop_user_program(), 2)
            finally:
                await asyncio.wait_for(hub.disconnect(), 3)
            print('Mouth closed; Port E centered. Disconnected.', flush=True)

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--name', default='Panther')
    p.add_argument('--speaker', default='HK Onyx Studio 8')
    p.add_argument('--min-rms', type=float, default=0.014)
    p.add_argument('--peak-rms', type=float, default=0.30)
    p.add_argument('--response-curve', type=float, default=1.2)
    p.add_argument('--duration', type=float, default=0)
    p.add_argument('--require-audio', action='store_true')
    p.add_argument('-v', '--verbose', action='store_true')
    args = p.parse_args()
    if not 0 <= args.min_rms < args.peak_rms:
        p.error('Require 0 <= min-rms < peak-rms')
    if args.response_curve <= 0:
        p.error('Require response-curve > 0')
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        pass
