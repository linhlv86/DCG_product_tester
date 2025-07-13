# tasks/task_example_gpio.py
import time
import subprocess
import json
import re
import serial

# Mô tả của task này, sẽ hiển thị trên giao diện người dùng
DESCRIPTION = "System information"

global_message =[]

def check_lsusb():
    try:
        output = subprocess.check_output(['/usr/bin/lsusb'], text=True)
        # Lọc các dòng thực sự là thiết bị và không chứa "Linux Foundation"
        devices = [
            line for line in output.strip().split('\n')
            if line.strip() and "Linux Foundation" not in line
        ]
        found_terminus = any("Terminus Technology Inc. Hub" in line for line in devices)
        found_ethernet = any("Ethernet 10/100/1000 Adapter" in line for line in devices)
        ok = found_terminus and found_ethernet
        devices.sort()  # Sắp xếp danh sách thiết bị
        if devices:
            detail = "USB devices found:\n" + "\n".join(f"+ {d}" for d in devices)
        else:
            detail = "No USB devices found."

        if not found_terminus:
            detail += "\nNotfound Terminus Technology Inc. Hub"
        if not found_ethernet:
            detail += "\nNot found Ethernet 10/100/1000 Adapter"
        global global_message
        global_message.append(detail)
        return {
            "item": "USB devices",
            "result": "PASS" if ok else "FAIL",
            "detail": detail,
            "passed": ok
        }
    except Exception as e:
        return {
            "item": "USB devices",
            "result": "FAIL",
            "detail": str(e),
            "passed": False
        }

def list_network_interfaces():
    try:
        link_output = subprocess.check_output(['/sbin/ip', '-o', 'link'], text=True)
        addr_output = subprocess.check_output(['/sbin/ip', '-o', '-4', 'addr'], text=True)

        interfaces = {}
        for line in link_output.strip().split('\n'):
            match = re.match(r'\d+: (\S+):.*link/\w+ ([\da-f:]{17})', line)
            if match:
                name, mac = match.groups()
                interfaces[name] = {"mac": mac, "ip": []}

        for line in addr_output.strip().split('\n'):
            parts = line.split()
            if len(parts) >= 4:
                name = parts[1]
                ip = parts[3]  # giữ nguyên cả subnet mask
                if name in interfaces:
                    interfaces[name]["ip"].append(ip)

        # Hiển thị tất cả interface, kể cả không có IP
        result = []
        for name, info in interfaces.items():
            if not name.startswith(('lo', 'docker', 'veth')):
                ip_str = info["ip"][0] if info["ip"] else "N/A"
                result.append(f"{name}: {ip_str} ({info['mac']})")

        # detail = "Interfaces:\n" + "\n-".join(result) if result else "No network interfaces found."
        result.sort()  # Sắp xếp kết quả theo tên interface
        if result:
            detail = "Interfaces found:\n" + "\n".join(f"+ {d}" for d in result)
        else:
            detail = "No interfaces found."

        global global_message
        global_message.append(detail)
        return {
            "item": "Network interfaces",
            "result": "PASS" if result else "FAIL",
            "detail": detail,
            "passed": bool(result)
        }
    except Exception as e:
        return {
            "item": "Network interfaces",
            "result": "FAIL",
            "detail": str(e),
            "passed": False
        }

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
        partitions.sort()  # Sắp xếp danh sách phân vùng
        if partitions:
            detail = "Partitions and sizes:\n" + "\n".join(f"+ {p}" for p in partitions)
        else:
            detail = "No partitions found."

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
    # 4. Kiểm tra network interfaces
    detail_results.append(list_network_interfaces())

    # Nếu các bước trên đều PASS, tiến hành kiểm tra RS485
    if all(r["passed"] for r in detail_results):
        test_rs485(detail_results)

    # Tổng kết
    num_pass = sum(1 for r in detail_results if r["passed"])
    num_fail = len(detail_results) - num_pass
    all_pass = all(r["passed"] for r in detail_results)
    status = "Passed" if all_pass else "Failed"
    message = "\n".join(global_message) + f"Summary: {num_pass} PASS, {num_fail} FAIL. " + "\n\n"

    return status, message, detail_results



