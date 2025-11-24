#!/usr/bin/env python3
"""
Universal Photo EXIF Reader + Z6 Detector + Sony Serial Extractor
---------------------------------------------------------------

✔ Reads all photos in current folder
✔ Extracts shutter count for all brands
✔ Extracts serial number for SONY, NIKON, CANON, FUJI, PANASONIC
✔ Scans Sony MakerNotes to find hidden serial values
✔ Detects if image is Z6 or not
"""

import subprocess
import json
from pathlib import Path


def run_exiftool(path):
    """Run ExifTool and return JSON data."""
    result = subprocess.run(
        ["exiftool", "-json", str(path)], capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)[0]
    except:
        return None


def extract_sony_serial(data):
    """Try multiple MakerNote tags where Sony hides serial."""
    sony_keys = [
        "SerialNumber",
        "InternalSerialNumber",
        "CameraSerialNumber",
        "BodySerialNumber",
        "SerialNumber2",
        # Sony MakerNote fields commonly containing serial-like data:
        "Sony_0x0018",
        "Sony_0xB000",
        "Sony_0xB001",
        "SonyModelID",
        "FirmwareVersion2",
    ]

    for key in sony_keys:
        if key in data:
            val = str(data[key]).strip()
            # Sony often encodes serial with prefix like "0x123456"
            if val and val != "None" and len(val) >= 5:
                # Remove hex prefix
                if val.startswith("0x"):
                    try:
                        return str(int(val, 16))
                    except:
                        return val
                return val

    # Fallback: scan all Keys for "serial"
    for key, val in data.items():
        if "serial" in key.lower():
            return str(val)

    return None


def get_serial_number(data):
    """Extract serial number for any brand."""
    make = str(data.get("Make", "")).upper()

    # Sony special handling
    if "SONY" in make:
        s = extract_sony_serial(data)
        return s or "N/A"

    # Standard fields for Nikon/Canon/Fuji/Panasonic
    for key in [
        "SerialNumber",
        "CameraSerialNumber",
        "InternalSerialNumber",
        "BodySerialNumber",
    ]:
        if key in data:
            return str(data[key])

    # Fallback generic search
    for key, val in data.items():
        if "serial" in key.lower():
            return str(val)

    return "N/A"


def get_shutter_count(data):
    """Extract shutter count for any brand."""
    keys = [
        "ShutterCount",
        "ImageCount",
        "ImageNumber",
        "TotalShot",
        "ActuationCount",
        "ShutterActuations",
        "TotalPhotos",
    ]

    for k in keys:
        if k in data:
            try:
                return int(data[k])
            except:
                pass
    return None


def print_info(data, filename):
    print("----------------------------------------------------")
    print(f"FILE: {filename}")

    make = data.get("Make", "Unknown")
    model = data.get("Model", "Unknown")
    serial = get_serial_number(data)
    shutter = get_shutter_count(data)

    dt = data.get("DateTimeOriginal", data.get("CreateDate", "Unknown"))
    lens = data.get("LensModel", data.get("Lens", "Unknown"))
    iso = data.get("ISO", "Unknown")
    aperture = data.get("Aperture", data.get("FNumber", "Unknown"))
    speed = data.get("ShutterSpeed", data.get("ExposureTime", "Unknown"))
    width = data.get("ImageWidth", "?")
    height = data.get("ImageHeight", "?")

    # Print
    print(f"- Camera      : {make} {model}")
    print(f"- Serial      : {serial}")
    print(f"- Date        : {dt}")
    print(f"- Lens        : {lens}")
    print(f"- ISO         : {iso}")
    print(f"- Aperture    : {aperture}")
    print(f"- Shutter     : {speed}")
    print(f"- Resolution  : {width} x {height}")
    print(f"- ShutterCount: {shutter}")

    # Z6 detection
    if "NIKON Z 6" in str(model).upper():
        print(">>> This photo IS from a Nikon Z6 ✓")
    else:
        print(">>> This photo is NOT from a Nikon Z6 ✗")


def main():
    print("=== UNIVERSAL PHOTO EXIF ANALYZER + SONY SERIAL SUPPORT ===")

    exts = ["*.jpg", "*.jpeg", "*.JPG", "*.JPEG", "*.nef", "*.NEF", "*.ARW", "*.arw"]
    files = []
    for ext in exts:
        files.extend(Path(".").glob(ext))

    if not files:
        print("No image files found in folder.")
        return

    print(f"Found {len(files)} image files.\n")

    for f in sorted(files):
        data = run_exiftool(f)
        if data:
            print_info(data, f.name)


if __name__ == "__main__":
    main()
