# tasks/task_example_gpio.py
import time
import subprocess
import json
import re
import glob
import serial

# Mô tả của task này, sẽ hiển thị trên giao diện người dùng
DESCRIPTION = "System information"

global_message =[]


# GPIO mapping cho từng port
GPIO_PORTS = [129, 135, 122, 127]
SERIAL_PORTS = [f"/dev/ttyACM{i}" for i in range(4)]
BAUD_RATES = [1200, 9600, 38400, 115200]
TEST_STRING = "RS485_TEST"

def set_gpio_mode(gpio_num, value):
    # Đặt mức GPIO (giả sử đã export và có quyền ghi)
    try:
        with open(f"/sys/class/gpio/gpio{gpio_num}/value", "w") as f:
            f.write(str(value))
        return True
    except Exception as e:
        return False

def test_rs485(detail_results):
    # Đặt tất cả port về mode RS485 (mức 0)
    for gpio in GPIO_PORTS:
        set_gpio_mode(gpio, 0)

    for baud in BAUD_RATES:
        # Đặt lại mode RS485 cho mỗi tốc độ
        for gpio in GPIO_PORTS:
            set_gpio_mode(gpio, 0)
        time.sleep(0.1)

        for tx_idx, tx_port in enumerate(SERIAL_PORTS):
            # Mở tất cả port
            serial_ports = []
            for port in SERIAL_PORTS:
                try:
                    ser = serial.Serial(port, baudrate=baud, timeout=1)
                    serial_ports.append(ser)
                except Exception as e:
                    detail_results.append({
                        "item": f"Open {port} at {baud}",
                        "result": "FAIL",
                        "detail": str(e),
                        "passed": False
                    })
                    return

            # Gửi chuỗi mẫu từ port tx_idx
            serial_ports[tx_idx].write(TEST_STRING.encode())
            time.sleep(0.2)

            # Kiểm tra nhận ở các port còn lại
            for rx_idx, ser in enumerate(serial_ports):
                if rx_idx == tx_idx:
                    continue
                try:
                    received = ser.read(len(TEST_STRING)).decode(errors="ignore")
                    if received == TEST_STRING:
                        detail_results.append({
                            "item": f"RS485 {SERIAL_PORTS[tx_idx]}->{SERIAL_PORTS[rx_idx]} @ {baud}",
                            "result": "PASS",
                            "detail": f"Received: {received}",
                            "passed": True
                        })
                    else:
                        detail_results.append({
                            "item": f"RS485 {SERIAL_PORTS[tx_idx]}->{SERIAL_PORTS[rx_idx]} @ {baud}",
                            "result": "FAIL",
                            "detail": f"Received: {received}",
                            "passed": False
                        })
                except Exception as e:
                    detail_results.append({
                        "item": f"RS485 {SERIAL_PORTS[tx_idx]}->{SERIAL_PORTS[rx_idx]} @ {baud}",
                        "result": "FAIL",
                        "detail": str(e),
                        "passed": False
                    })
            # Đóng tất cả port
            for ser in serial_ports:
                ser.close()

    # Tổng kết sẽ nằm trong detail_results

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
        detail = f"Missing devices: {', '.join(missing)}\nUSB serial devices found:\n" + "\n".join(devices)
        detail_results.append({
            "item": "Search USB serial devices",
            "result": "FAIL",
            "detail": detail,
            "passed": False
        })
    else:
        detail = "USB serial devices found:\n" + "\n".join(devices)
        global_message.append(detail)
        detail_results.append({
            "item": "Search USB serial devices",
            "result": "PASS",
            "detail": detail,
            "passed": True
        })

    # Nếu bước 1 pass:
    test_rs485(detail_results)

    # Tổng kết
    num_pass = sum(1 for r in detail_results if r["passed"])
    num_fail = len(detail_results) - num_pass
    all_pass = all(r["passed"] for r in detail_results)
    status = "Passed" if all_pass else "Failed"
    message = "\n".join(global_message) + f"Summary: {num_pass} PASS, {num_fail} FAIL. " + "\n\n"

    return status, message, detail_results




