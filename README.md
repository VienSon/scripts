Camera EXIF Utilities
=====================

Small helper scripts for sanity-checking used-camera photos before buying gear.  
Both tools expect to be dropped into a folder that contains example images (JPG/NEF/ARW, etc.) and will print human-readable diagnostics to stdout.

Requirements
------------

| Script           | Dependency                               | Install hint                                   |
|------------------|-------------------------------------------|-----------------------------------------------|
| `nikoncheck.py`  | [`exifread`](https://pypi.org/project/exifread/) | `python3 -m pip install --user exifread`       |
| `shotcheck.py`   | [`exiftool`](https://exiftool.org/) CLI   | macOS: `brew install exiftool` · Linux: package manager |

Scripts
-------

### `nikoncheck.py` — Nikon Z6 shutter history validator

Purpose:
  * Walks the current (or given) folder for JPG/JPEG/NEF files.
  * Extracts minimal EXIF metadata via `exifread`.
  * Produces a chronological table of photos alongside their shutter counts.
  * Flags suspicious patterns where shutter counts decrease as time moves forward (common sign of counter resets or mainboard swaps).

Usage:

```bash
# analyze photos in the current directory
python3 nikoncheck.py

# specify a folder and an expected camera body string (case-insensitive)
python3 nikoncheck.py /path/to/photos --expected-model "NIKON Z 6II"

# keep all photos regardless of EXIF model
python3 nikoncheck.py --no-model-filter
```

Output highlights:
  * Shows how many files were found and how many passed the model filter.
  * Prints a timeline table: index, EXIF DateTime, parsed shutter count, filename.
  * Emits `[WARN]` blocks whenever the shutter count drops between two adjacent photos so you can double-check seller claims.

### `shotcheck.py` — Universal EXIF + serial inspector

Purpose:
  * Uses `exiftool` to read every common photo format in the folder.
  * Prints camera make/model, hidden serial numbers (special Sony handling), and a best-effort shutter count for any brand.
  * Identifies whether a frame was taken with a Nikon Z6 to help mix-and-match bodies when reviewing seller samples.

Usage:

```bash
python3 shotcheck.py
```

What you get per file:

```
----------------------------------------------------
FILE: DSC01234.JPG
- Camera      : SONY ILCE-7C
- Serial      : 1234567
- Date        : 2024:05:01 21:14:25
- Lens        : FE 35mm F1.8
- ISO         : 400
- Aperture    : 1.8
- Shutter     : 1/125
- Resolution  : 6000 x 4000
- ShutterCount: 18234
>>> This photo is NOT from a Nikon Z6 ✗
```

Tips
----

* For both scripts, drop a handful of untouched sample photos straight from the card; exporting through Lightroom or Photos may strip data.
* If `shotcheck.py` prints nothing, ensure `exiftool` is on your `PATH` (`exiftool -ver` should work from the terminal).
* When `nikoncheck.py` says “No JPG/JPEG/NEF files found”, verify you are running it inside the folder that actually holds raw files, not inside a subfolder such as `RAW/`.

License
-------
These scripts are personal utilities; use them at your own risk.
