# tasks/task_example_gpio.py
import time
import subprocess
import json
import re
import glob

# Mô tả của task này, sẽ hiển thị trên giao diện người dùng
DESCRIPTION = "System information"

global_message =[]


def test_task():
    detail_results = []
    global_message = []

    # Danh sách thiết bị cần tìm
    required_devices = [f"/dev/ttyACM{i}" for i in range(4)]
    # Lấy danh sách thiết bị thực tế
    devices = glob.glob('/dev/ttyACM*')
    try:
        ls_output = subprocess.check_output(['/bin/ls', '/dev/ttyACM*'], text=True)
    except Exception as e:
        ls_output = str(e)

    # Kiểm tra đủ 4 thiết bị
    found_all = all(dev in devices for dev in required_devices)
    if not found_all:
        missing = [dev for dev in required_devices if dev not in devices]
        detail = f"Missing devices: {', '.join(missing)}\nls /dev/ttyACM* output:\n{ls_output}"
        detail_results.append({
            "item": "Search USB serial devices",
            "result": "FAIL",
            "detail": detail,
            "passed": False
        })
    else:
        detail = "USB serial devices found: " + ", ".join(devices)
        detail += f"\nls /dev/ttyACM* output:\n{ls_output}"
        global_message.append(detail)
        detail_results.append({
            "item": "Search USB serial devices",
            "result": "PASS",
            "detail": detail,
            "passed": True
        })

    # Tổng kết
    num_pass = sum(1 for r in detail_results if r["passed"])
    num_fail = len(detail_results) - num_pass
    all_pass = all(r["passed"] for r in detail_results)
    status = "Passed" if all_pass else "Failed"
    message = "\n".join(global_message) + f"Summary: {num_pass} PASS, {num_fail} FAIL. " + "\n\n"

    return status, message, detail_results




