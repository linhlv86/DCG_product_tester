# tasks/task_example_gpio.py
import time
import subprocess
import json
import re
import glob
import os

# Mô tả của task này, sẽ hiển thị trên giao diện người dùng
DESCRIPTION = "USB Serial Port Check"

global_message = []

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

def check_serial_ports():
    """Check for USB serial ports /dev/ttyACM0-3"""
    try:
        required_ports = [f"/dev/ttyACM{i}" for i in range(4)]
        existing_ports = []
        missing_ports = []
        
        # Check each required port
        for port in required_ports:
            if os.path.exists(port):
                existing_ports.append(port)
            else:
                missing_ports.append(port)
        
        # Get all ttyACM devices for additional info
        all_ttyacm = glob.glob('/dev/ttyACM*')
        all_ttyacm.sort()
        
        # Build detail message
        detail_parts = []
        if existing_ports:
            detail_parts.append("Required serial ports found:")
            for port in existing_ports:
                detail_parts.append(f"+ {port}")
        
        if missing_ports:
            detail_parts.append("Missing required serial ports:")
            for port in missing_ports:
                detail_parts.append(f"- {port}")
        
        if all_ttyacm:
            detail_parts.append("ttyACM* devices in system:")
            for port in all_ttyacm:
                detail_parts.append(f"  {port}")
        else:
            detail_parts.append("No ttyACM devices found in system")
        
        detail = "\n".join(detail_parts)
        
        # Check if all required ports exist
        all_found = len(existing_ports) == 4
        
        global global_message
        global_message.append(detail)
        
        return {
            "item": "USB Serial Ports (/dev/ttyACM0-3)",
            "result": "PASS" if all_found else "FAIL",
            "detail": detail,
            "passed": all_found
        }
        
    except Exception as e:
        return {
            "item": "USB Serial Ports",
            "result": "FAIL",
            "detail": f"Error checking serial ports: {str(e)}",
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

def test_task():
    detail_results = []
    global global_message
    global_message = []  # Reset global message
    
    # Run all checks
    detail_results.append(check_lsusb())
    detail_results.append(check_serial_ports())
    detail_results.append(list_network_interfaces())

    # Tổng kết
    num_pass = sum(1 for r in detail_results if r["passed"])
    num_fail = len(detail_results) - num_pass
    all_pass = all(r["passed"] for r in detail_results)
    status = "Passed" if all_pass else "Failed"
    message = "\n".join(global_message) + f"\nSummary: {num_pass} PASS, {num_fail} FAIL."

    return status, message, detail_results



