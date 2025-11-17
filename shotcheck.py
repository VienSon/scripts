import subprocess
import os
import json
from datetime import datetime

OUTPUT_FILE = "shutter_analysis.txt"

def parse_int(value):
    """Convert các giá trị string như '12,345' -> 12345, nếu fail thì trả None."""
    if value is None:
        return None
    try:
        s = str(value).split()[0].replace(",", "")
        return int(s)
    except Exception:
        return None

def parse_datetime(item):
    """Ưu tiên DateTimeOriginal, sau đó CreateDate, ModifyDate."""
    for key in ("DateTimeOriginal", "CreateDate", "ModifyDate"):
        dt_str = item.get(key)
        if not dt_str:
            continue
        # ExifTool format thường là '2024:10:15 12:34:56'
        for fmt in ("%Y:%m:%d %H:%M:%S", "%Y:%m:%d %H:%M:%S%z"):
            try:
                return datetime.strptime(dt_str, fmt)
            except Exception:
                continue
    return None

def find_first_key_contains(item, keywords):
    """
    Tìm key đầu tiên trong item có chứa 1 trong các keyword (không phân biệt hoa thường).
    Trả về (key, value) hoặc (None, None).
    """
    lower_map = {k.lower(): k for k in item.keys()}
    for lk, orig_k in lower_map.items():
        for kw in keywords:
            if kw in lk:
                return orig_k, item[orig_k]
    return None, None

def main():
    # Lấy list file JPEG
    jpeg_files = [f for f in os.listdir(".") if f.lower().endswith((".jpg", ".jpeg"))]
    if not jpeg_files:
        print("Không tìm thấy file JPEG nào trong folder hiện tại.")
        return

    # Gọi exiftool với output JSON
    cmd = [
        "exiftool",
        "-json",
        "-a",     # show all
        "-G1",    # show group (MakerNotes, EXIF...)
        "-s",     # short tag names
        "-FileName",
        "-DateTimeOriginal",
        "-CreateDate",
        "-ModifyDate",
        "-Make",
        "-Model",
        "-FirmwareVersion",
        "-*ShutterCount*",
        "-*ExposureCount*",
        "-*ReleaseCount*",
        "-*ImageNumber*",
        "-*ImageCount*",
        "-*ImageCounter*",
        "-*FileNumber*",
        "-*Serial*",
    ] + jpeg_files

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.stderr.strip():
        print("ExifTool stderr:\n", result.stderr)

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print("Lỗi đọc JSON từ exiftool:", e)
        return

    records = []

    for item in data:
        filename = item.get("FileName")
        dt = parse_datetime(item)

        # Tìm các field liên quan
        # shutter-like: ShutterCount / ExposureCount / ReleaseCount / Sony_ExposureCount...
        shutter_key, shutter_val_raw = find_first_key_contains(
            item,
            ["shuttercount", "exposurecount", "releasecount"]
        )
        image_key, image_val_raw = find_first_key_contains(
            item,
            ["imagenumber", "imagecount", "imagecounter", "filenumber"]
        )

        shutter_val = parse_int(shutter_val_raw)
        image_val = parse_int(image_val_raw)

        records.append({
            "filename": filename,
            "datetime": dt,
            "datetime_str": dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "N/A",
            "shutter_key": shutter_key,
            "shutter_val": shutter_val,
            "image_key": image_key,
            "image_val": image_val,
            "make": item.get("Make"),
            "model": item.get("Model"),
            "serial": item.get("SerialNumber") or item.get("InternalSerialNumber") or item.get("BodySerialNumber"),
        })

    # Sort theo thời gian chụp (ảnh không có thời gian đưa cuối danh sách)
    records.sort(key=lambda r: (r["datetime"] is None, r["datetime"] or datetime.max))

    # Phân tích nghi ngờ
    suspicious = []
    previous = None

    for rec in records:
        notes = []

        # 1. Quan hệ image_val vs shutter_val
        sv = rec["shutter_val"]
        iv = rec["image_val"]
        if sv is not None and iv is not None:
            if iv > sv * 1.5 + 1000:
                notes.append("ImageNumber lớn bất thường so với ShutterCount")

        # 2. Nhảy lùi theo thời gian
        if previous:
            # shutter count không nên giảm theo thời gian
            if previous["shutter_val"] is not None and rec["shutter_val"] is not None:
                if rec["shutter_val"] + 1000 < previous["shutter_val"]:
                    notes.append("ShutterCount bị giảm mạnh theo thời gian (reset/thay shutter?)")

            # image counter cũng không nên giảm nhiều
            if previous["image_val"] is not None and rec["image_val"] is not None:
                if rec["image_val"] + 1000 < previous["image_val"]:
                    notes.append("ImageNumber bị giảm mạnh theo thời gian (reset counter?)")

        if notes:
            suspicious.append((rec, notes))

        previous = rec

    # Ghi file report
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("PHÂN TÍCH SHUTTER / IMAGE COUNTER (tự động)\n")
        f.write("============================================================\n\n")
        if records:
            cam = records[0]
            f.write(f"Camera (dựa trên file đầu tiên): {cam['make']} {cam['model']}\n")
            f.write(f"Serial (nếu có): {cam['serial']}\n\n")

        f.write("TÓM TẮT TỪNG FILE:\n")
        f.write("------------------------------------------------------------\n")
        f.write("idx | datetime            | shutter       | image          | file\n")
        f.write("------------------------------------------------------------\n")

        for idx, rec in enumerate(records, start=1):
            f.write(
                f"{idx:3d} | {rec['datetime_str']:19} | "
                f"{(str(rec['shutter_val']) if rec['shutter_val'] is not None else '-'):13} | "
                f"{(str(rec['image_val']) if rec['image_val'] is not None else '-'):13} | "
                f"{rec['filename']}\n"
            )

        f.write("\n\nNGHI NGỜ BẤT THƯỜNG:\n")
        f.write("------------------------------------------------------------\n")
        if not suspicious:
            f.write("Không phát hiện bất thường rõ ràng theo các rule đơn giản.\n")
        else:
            for rec, notes in suspicious:
                f.write(f"FILE: {rec['filename']}\n")
                f.write(f"  Thời gian   : {rec['datetime_str']}\n")
                f.write(f"  Shutter     : {rec['shutter_val']} (key: {rec['shutter_key']})\n")
                f.write(f"  Image count : {rec['image_val']} (key: {rec['image_key']})\n")
                for n in notes:
                    f.write(f"  -> {n}\n")
                f.write("\n")

    print(f"Đã phân tích xong. Kết quả lưu tại: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
