# AnimatronicHead

Local Windows audio-driven animatronic using a LEGO hub with Pybricks firmware.
The tested connection is Bluetooth to the hub named `Panther`; USB can remain
connected for power. No Pybricks website is needed during operation.

## Setup

Install Python 3.10 or newer. Put the mouth motor on Port F and the left/right
motor on Port E. Place both mechanisms at their center/closed positions before
starting: the firmware treats those starting positions as zero.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe voice_listener.py -v
```

Enable Bluetooth on the hub and disconnect other apps from it first. Connect
the HK Onyx Studio 8 speaker and play speech through it. The listener captures
speaker output, including browser voice models; it does not record the microphone.
All sounds on that speaker can trigger movement.

## Movement and controls

- Port F follows audio volume with targets from 0 to 45 degrees. Normal speech
  uses smaller openings; full opening requires louder audio. Quiet pauses close
  the mouth quickly. Speed is 400 degrees/second.
- Port E alternates between -45 and +45 degrees while talking and returns to
  center during silence. Speed is 60 degrees/second.
- Motors coast after reaching each target rather than holding rigidly. Actual
  angles can differ slightly from the targets.
- Press Esc to stop, close the mouth, center Port E, and disconnect. The key
  works across applications. The hub center button also stops its program.
- The hub returns both motors toward zero if commands stop arriving.

Choose a different speaker or tune sensitivity:

```powershell
.\.venv\Scripts\python.exe voice_listener.py --speaker "speaker name" --name Panther --min-rms 0.014 --peak-rms 0.30 --response-curve 1.2 -v
```

Increase `--peak-rms` for smaller openings at the same audio volume. Increase
`--min-rms` to ignore quieter sounds. Use `--speaker ""` for the default Windows
output device. Stop and restart the listener after changing output devices.

## Hardware checks

These commands physically move the motors. Stop the listener before running them.

```powershell
# Mouth motor only
.\.venv\Scripts\python.exe test_hub_connection.py --transport ble --name Panther
# Both motors, with encoder measurements
.\.venv\Scripts\python.exe verify_mouth_range.py
# Hold Space to open the mouth; release to close; Esc to stop
.\.venv\Scripts\python.exe keyboard_controller.py
```

`run.ps1` installs dependencies, tests Port F, and starts speech animation.
`voice_listener.py` is the active speaker-audio implementation. The original
`audio_listener.py` and `pybricksdev_audio_listener.py` are retained as earlier
serial/USB experiments; they are not the tested launch path.
