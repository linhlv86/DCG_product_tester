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
        output = subprocess.check_output(['uname', '-a'], text=True).strip()
        detail_results.append({
            "item": "uname -a",
            "result": "PASS",
            "detail": output,
            "passed": True
        })
    except Exception as e:
        detail_results.append({
            "item": "uname -a",
            "result": "FAIL",
            "detail": str(e),
            "passed": False
        })

    # 2. Kiểm tra số lượng phân vùng ổ đĩa
    try:
        output = subprocess.check_output(['lsblk', '-n', '-o', 'TYPE'], text=True)
        partitions = [line for line in output.splitlines() if line.strip() == 'part']
        ok = len(partitions) >= 2
        detail_results.append({
            "item": "Disk partitions",
            "result": "PASS" if ok else "FAIL",
            "detail": f"Partitions found: {len(partitions)}",
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

# Ví dụ sử dụng:
if __name__ == "__main__":
    status, message, detail_results = test_task()
    print("Status:", status)
    print("Message:", message)
    print("Detail results:", detail_results)

