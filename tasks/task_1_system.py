# tasks/task_example_gpio.py
import time
import subprocess
import json

# Mô tả của task này, sẽ hiển thị trên giao diện người dùng
DESCRIPTION = "System information"

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
        partitions = []
        for line in lines[1:]:  # Bỏ dòng tiêu đề
            parts = line.split()
            if len(parts) >= 2:
                partition_name = parts[0]
                size = parts[1]
                partitions.append(f"{partition_name}: {size}")
        ok = len(partitions) >= 2
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

    # Tổng kết
    num_pass = sum(1 for r in detail_results if r["passed"])
    num_fail = len(detail_results) - num_pass
    all_pass = all(r["passed"] for r in detail_results)
    status = "Passed" if all_pass else "Failed"
    message = f"Tổng kết: {num_pass} PASS, {num_fail} FAIL."

    return status, message, detail_results



