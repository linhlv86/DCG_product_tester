# tasks/task_example_gpio.py
import time
import subprocess
import json

# Mô tả của task này, sẽ hiển thị trên giao diện người dùng
DESCRIPTION = "System information"

def check_lsusb():
    try:
        output = subprocess.check_output(['/usr/bin/lsusb'], text=True)
        devices = [line for line in output.strip().split('\n') if line.strip()]
        found_terminus = any("Terminus Technology Inc. Hub" in line for line in devices)
        found_ethernet = any("Ethernet 10/100/1000 Adapter" in line for line in devices)
        ok = found_terminus and found_ethernet
        detail = "USB devices found:\n" + "\n".join(devices) if devices else "No USB devices found."
        if not found_terminus:
            detail += "\nKhông tìm thấy Terminus Technology Inc. Hub"
        if not found_ethernet:
            detail += "\nKhông tìm thấy Ethernet 10/100/1000 Adapter"
        return {
            "item": "lsusb",
            "result": "PASS" if ok else "FAIL",
            "detail": detail,
            "passed": ok
        }
    except Exception as e:
        return {
            "item": "lsusb",
            "result": "FAIL",
            "detail": str(e),
            "passed": False
        }

def test_task():
    detail_results = []

    # 1. Kiểm tra uname -a
    try:
        output = subprocess.check_output(['/usr/bin/uname', '-a'], text=True).strip()
        detail_results.append({
            "item": "System information",
            "result": "PASS",
            "detail": output,
            "passed": True
        })
    except Exception as e:
        detail_results.append({
            "item": "System information",
            "result": "FAIL",
            "detail": str(e),
            "passed": False
        })

    # 2. Kiểm tra số lượng phân vùng ổ đĩa
    try:
        output = subprocess.check_output(['/bin/df', '-h'], text=True)
        lines = output.strip().split('\n')
        found_p1 = False
        found_p2 = False
        partitions = []
        for line in lines[1:]:  # Bỏ dòng tiêu đề
            parts = line.split()
            if len(parts) >= 2 and parts[0].startswith('/dev/'):
                partition_name = parts[0]
                size = parts[1]
                partitions.append(f"{partition_name}: {size}")
                if partition_name == '/dev/mmcblk1p1':
                    found_p1 = True
                if partition_name == '/dev/mmcblk1p2':
                    found_p2 = True
        ok = found_p1 and found_p2
        detail = "Partitions and sizes:\n" + "\n".join(partitions) if partitions else "No partitions found."
        detail_results.append({
            "item": "Disk partitions",
            "result": "PASS" if ok else "FAIL",
            "detail": detail,
            "passed": ok
        })
    except Exception as e:
        detail_results.append({
            "item": "Disk partitions",
            "result": "FAIL",
            "detail": str(e),
            "passed": False
        })

    # 3. Kiểm tra lsusb
    detail_results.append(check_lsusb())

    # Tổng kết
    num_pass = sum(1 for r in detail_results if r["passed"])
    num_fail = len(detail_results) - num_pass
    all_pass = all(r["passed"] for r in detail_results)
    status = "Passed" if all_pass else "Failed"
    message = f"Sumary: {num_pass} PASS, {num_fail} FAIL."

    return status, message, detail_results



