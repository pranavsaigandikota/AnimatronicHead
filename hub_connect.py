"""Connect to a Pybricks hub over USB (wired) or BLE."""

from __future__ import annotations

import asyncio
from typing import Any


def _is_pybricks_usb(dev: Any) -> bool:
    from pybricksdev.usb import (
        EV3_USB_PID,
        LEGO_USB_VID,
        MINDSTORMS_INVENTOR_USB_PID,
        NXT_USB_PID,
        SPIKE_ESSENTIAL_USB_PID,
        SPIKE_PRIME_USB_PID,
    )

    return (dev.idVendor == LEGO_USB_VID) and (
        dev.idProduct
        in (
            NXT_USB_PID,
            EV3_USB_PID,
            SPIKE_PRIME_USB_PID,
            SPIKE_ESSENTIAL_USB_PID,
            MINDSTORMS_INVENTOR_USB_PID,
        )
    )


async def connect_hub(transport: str = "usb", name: str = "test"):
    if transport == "usb":
        from libusb_package import find as find_usb
        from usb.core import USBError
        from serial.tools import list_ports
        from pybricksdev.connections.pybricks import PybricksHubUSB

        print("Looking for Pybricks hub on USB...")
        lego_serial_ports = [p.device for p in list_ports.comports() if p.vid == 0x0694]
        if lego_serial_ports:
            raise RuntimeError(
                "Hub exposes a serial connection on " + ", ".join(lego_serial_ports)
                + "; this script needs Pybricks firmware with the native USB protocol. "
                "Check the installed hub firmware before changing drivers."
            )
        device = find_usb(custom_match=_is_pybricks_usb)
        if device is None:
            raise RuntimeError(
                "No Pybricks hub on USB.\n"
                "- Hub powered ON\n"
                "- USB cable data-capable (not charge-only)\n"
                "- Close Pybricks Code (it holds the USB device)\n"
                "- Re-plug the cable after closing the IDE"
            )
        hub = PybricksHubUSB(device)
        try:
            await asyncio.wait_for(hub.connect(), timeout=15)
        except USBError as exc:
            raise RuntimeError(
                "Cannot open the hub's Pybricks USB interface. "
                "Disconnect Pybricks Code and verify USB-capable Pybricks firmware is installed."
            ) from exc
        print("USB connected.")
        return hub

    from pybricksdev.ble import find_device
    from pybricksdev.connections.pybricks import PybricksHubBLE

    print(f"Scanning BLE for hub '{name}'...")
    device = await find_device(name)
    if device is None:
        raise RuntimeError(
            f"Hub '{name}' not found over BLE. "
            "Power ON, close Pybricks Code, check the hub name."
        )
    hub = PybricksHubBLE(device)
    await asyncio.wait_for(hub.connect(), timeout=30)
    print("BLE connected.")
    return hub
