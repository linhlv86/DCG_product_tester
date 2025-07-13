# tasks/task_example_gpio.py
import time
import subprocess
import json
import re

# Mô tả của task này, sẽ hiển thị trên giao diện người dùng
DESCRIPTION = "System information"

global_message =[]


def test_task():
    detail_results = []

   #1 Check for ls /dev/ttyUSB*
   # it must be exist ttyUSB0..3
    try:
        output = subprocess.check_output(['ls', '/dev/ttyUSB*'], text=True)
        devices = output.strip().split('\n')
        if not devices or len(devices) < 4:
            raise FileNotFoundError("Not enough USB serial devices found.")
        detail = "USB serial devices found: " + ", ".join(devices)
        global_message.append(detail)
        detail_results.append({
            "item": "USB serial devices",
            "result": "PASS",
            "detail": detail,
            "passed": True
        })
    except Exception as e:
        detail_results.append({
            "item": "USB serial devices",
            "result": "FAIL",
            "detail": str(e),
            "passed": False
        })
    # Tổng kết
    num_pass = sum(1 for r in detail_results if r["passed"])
    num_fail = len(detail_results) - num_pass
    all_pass = all(r["passed"] for r in detail_results)
    status = "Passed" if all_pass else "Failed"
    message = "\n".join(global_message) + f"Summary: {num_pass} PASS, {num_fail} FAIL. " + "\n\n"

    return status, message, detail_results




