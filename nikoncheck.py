#!/usr/bin/env python3
"""
Analyze a batch of Nikon Z6 photos to look for suspicious shutter count patterns.

Usage (most real-life case):
    # Put some Z6 photos in the current folder, then:
    python analyze_z6_shutter_history.py

Optional:
    python analyze_z6_shutter_history.py /path/to/folder
    python analyze_z6_shutter_history.py --expected-model "NIKON Z 6"
"""

import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any

import exifread


def find_first_numeric(value_str) -> Optional[int]:
    """Try to extract an integer shutter value from something like '12345' or '12345/1'."""
    if value_str is None:
        return None

    s = str(value_str).strip()

    # Handle "12345/1"
    if "/" in s:
        num, _, den = s.partition("/")
        try:
            num = float(num)
            den = float(den) if den else 1.0
            return int(num / den)
        except ValueError:
            pass

    # Plain integer/float
    try:
        return int(float(s))
    except ValueError:
        return None


def get_exif_info(path: Path) -> Dict[str, Any]:
    """Extract minimal EXIF info we care about."""
    info = {
        "file": str(path),
        "datetime": None,
        "model": None,
        "shutter_raw": {},
        "shutter_value": None,
    }

    try:
        with path.open("rb") as f:
            tags = exifread.process_file(f, details=False)
    except Exception as e:
        info["error"] = str(e)
        return info

    model = tags.get("Image Model")
    dt = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")

    info["model"] = str(model).strip() if model else None
    info["datetime"] = str(dt).strip() if dt else None

    # Collect all shutter-related tags
    shutter_candidates = {
        k: v
        for k, v in tags.items()
        if "shutter" in k.lower() or "image number" in k.lower()
    }
    info["shutter_raw"] = {k: str(v) for k, v in shutter_candidates.items()}

    # Try to parse first numeric shutter candidate
    shutter_value = None
    for _, v in shutter_candidates.items():
        num = find_first_numeric(v)
        if num is not None:
            shutter_value = num
            break

    info["shutter_value"] = shutter_value
    return info


def analyze_folder(
    folder: Path,
    expected_model: str = "NIKON Z 6",
    require_model_match: bool = True,
):
    files: List[Path] = []

    # Collect typical image files (non-recursive, current folder only)
    for ext in ("*.JPG", "*.JPEG", "*.jpg", "*.jpeg", "*.NEF", "*.nef"):
        files.extend(folder.glob(ext))

    if not files:
        print(f"[ERROR] No JPG/JPEG/NEF files found in {folder}")
        return

    print(f"Scanning folder: {folder.resolve()}")
    print(f"Found {len(files)} image files")

    records: List[Dict[str, Any]] = []
    for p in sorted(files):
        info = get_exif_info(p)
        records.append(info)

    # Filter by model if requested
    if require_model_match:
        before = len(records)
        records = [
            r
            for r in records
            if r.get("model") and r["model"].upper() == expected_model.upper()
        ]
        print(
            f"After filtering by model '{expected_model}': "
            f"{len(records)}/{before} files remain."
        )

    # Filter by datetime
    usable = [r for r in records if r.get("datetime")]

    if not usable:
        print("[ERROR] No files with valid DateTimeOriginal found.")
        return

    # Sort by datetime string (good enough for EXIF)
    usable.sort(key=lambda x: x["datetime"])

    print("\n=== Photo timeline (simplified) ===")
    print("index | datetime            | shutter_value | file")
    print("------|----------------------|---------------|-------------------------")

    for i, r in enumerate(usable):
        print(
            f"{i:5d} | {r['datetime'] or 'N/A':20} | "
            f"{str(r['shutter_value']) if r['shutter_value'] is not None else 'N/A':13} | "
            f"{Path(r['file']).name}"
        )

    # Detect suspicious patterns: shutter decreasing with later datetime
    print("\n=== Suspicious pattern detection ===")
    prev_val = None
    prev_dt = None
    suspicious = []

    for i, r in enumerate(usable):
        val = r["shutter_value"]
        dt = r["datetime"]
        if prev_val is not None and val is not None:
            if val < prev_val:
                suspicious.append((i - 1, i, prev_val, val, prev_dt, dt))
        if val is not None:
            prev_val = val
            prev_dt = dt

    if not suspicious:
        print("[OK] No obvious shutter-count decreases detected over time.")
        print("     (This does NOT guarantee no reset, but nothing looks crazy.)")
    else:
        print("[WARN] Detected possible shutter-count resets or anomalies:")
        for i1, i2, v1, v2, d1, d2 in suspicious:
            print(
                f"  - Between index {i1} ({d1}, ~{v1}) and index {i2} "
                f"({d2}, ~{v2}): shutter value decreased."
            )
        print(
            "\n[NOTE] A decrease may mean:\n"
            "  • Mainboard/shutter replacement at service center (legit), or\n"
            "  • Tampering / counter reset.\n"
            "  Cross-check with seller’s story and any service paperwork."
        )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Analyze Nikon Z6 photos in a folder for suspicious shutter-count patterns.\n"
            "Default: use current folder."
        )
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default=".",
        help="Folder containing JPEG/NEF files (default: current folder).",
    )
    parser.add_argument(
        "--expected-model",
        default="NIKON Z 6",
        help="Expected EXIF camera model (default: 'NIKON Z 6').",
    )
    parser.add_argument(
        "--no-model-filter",
        action="store_true",
        help="Do NOT filter images by model.",
    )

    args = parser.parse_args()
    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"[ERROR] Not a folder: {folder}")
        return

    analyze_folder(
        folder,
        expected_model=args.expected_model,
        require_model_match=not args.no_model_filter,
    )


if __name__ == "__main__":
    main()
