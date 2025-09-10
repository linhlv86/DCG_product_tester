# tasks/task_example_gpio.py
import time
import subprocess
import json
import re
import logging
import traceback

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import serial.tools.list_ports
    logger.info("Successfully imported serial.tools.list_ports")
except ImportError as e:
    logger.error(f"Failed to import serial.tools.list_ports: {e}")
    serial = None

# Mô tả của task này, sẽ hiển thị trên giao diện người dùng
TASK_NAME = "System Information Test"
DESCRIPTION = "System information and hardware checks"

# Biến global để lưu thông điệp chi tiết
global_message = []

def check_lsusb():
    logger.info("Starting check_lsusb()")
    try:
        output = subprocess.check_output(['/usr/bin/lsusb'], text=True)
        devices = [
            line for line in output.strip().split('\n')
            if line.strip() and "Linux Foundation" not in line
        ]
        found_terminus = any("Terminus Technology Inc. Hub" in line for line in devices)
        found_ethernet = any("Ethernet 10/100/1000 Adapter" in line for line in devices)
        ok = found_terminus and found_ethernet
        devices.sort()
        if devices:
            detail = "USB devices found:\n" + "\n".join(f"+ {d}" for d in devices)
        else:
            detail = "No USB devices found."

        if not found_terminus:
            detail += "\nNot found Terminus Technology Inc. Hub"
        if not found_ethernet:
            detail += "\nNot found Ethernet 10/100/1000 Adapter"
        
        global global_message
        global_message.append(detail)
        logger.info(f"check_lsusb completed: {'PASS' if ok else 'FAIL'}")
        return {
            "item": "USB devices",
            "result": "PASS" if ok else "FAIL",
            "detail": detail,
            "passed": ok
        }
    except Exception as e:
        logger.error(f"check_lsusb failed: {e}")
        return {
            "item": "USB devices",
            "result": "FAIL",
            "detail": str(e),
            "passed": False
        }

def list_network_interfaces():
    logger.info("Starting list_network_interfaces()")
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
                ip = parts[3]
                if name in interfaces:
                    interfaces[name]["ip"].append(ip)

        result = []
        for name, info in interfaces.items():
            if not name.startswith(('lo', 'docker', 'veth')):
                ip_str = info["ip"][0] if info["ip"] else "N/A"
                result.append(f"{name}: {ip_str} ({info['mac']})")

        result.sort()
        if result:
            detail = "Interfaces found:\n" + "\n".join(f"+ {d}" for d in result)
        else:
            detail = "No interfaces found."

        global global_message
        global_message.append(detail)
        logger.info(f"list_network_interfaces completed: {'PASS' if result else 'FAIL'}")
        return {
            "item": "Network interfaces",
            "result": "PASS" if result else "FAIL",
            "detail": detail,
            "passed": bool(result)
        }
    except Exception as e:
        logger.error(f"list_network_interfaces failed: {e}")
        return {
            "item": "Network interfaces",
            "result": "FAIL",
            "detail": str(e),
            "passed": False
        }

def check_serial_ports():
    """Check for ttyACM0-3 serial ports using pyserial"""
    logger.info("Starting check_serial_ports()")
    
    if serial is None:
        error_msg = "pyserial library not available"
        logger.error(error_msg)
        return {
            "item": "Serial ports",
            "result": "FAIL",
            "detail": error_msg,
            "passed": False
        }
    
    try:
        logger.info("Attempting to list all COM ports...")
        all_ports = list(serial.tools.list_ports.comports())
        logger.info(f"Found {len(all_ports)} total ports")
        
        for i, port in enumerate(all_ports):
            logger.info(f"Port {i}: {port.device} - {port.description}")
        
        ttyacm_ports = [port for port in all_ports if 'ttyACM' in port.device]
        logger.info(f"Found {len(ttyacm_ports)} ttyACM ports")
        
        required_ports = [f"/dev/ttyACM{i}" for i in range(4)]
        found_ports = []
        missing_ports = []
        
        for required_port in required_ports:
            found = any(port.device == required_port for port in ttyacm_ports)
            if found:
                found_ports.append(required_port)
                logger.info(f"Found required port: {required_port}")
            else:
                missing_ports.append(required_port)
                logger.warning(f"Missing required port: {required_port}")
        
        detail_parts = []
        
        if found_ports:
            detail_parts.append("Found required serial ports:")
            for port in found_ports:
                port_info = next((p for p in ttyacm_ports if p.device == port), None)
                if port_info:
                    detail_parts.append(f"+ {port} ({port_info.description})")
                    if port_info.vid and port_info.pid:
                        detail_parts.append(f"    VID:PID = {port_info.vid:04X}:{port_info.pid:04X}")
                else:
                    detail_parts.append(f"+ {port}")
        
        if missing_ports:
            detail_parts.append("Missing required serial ports:")
            for port in missing_ports:
                detail_parts.append(f"- {port}")
        
        detail_parts.append(f"Total ttyACM ports detected: {len(ttyacm_ports)}/4 required")
        
        if len(ttyacm_ports) > 4:
            detail_parts.append("Additional ttyACM ports found:")
            extra_ports = [p for p in ttyacm_ports if p.device not in required_ports]
            for port in extra_ports:
                detail_parts.append(f"  {port.device} - {port.description}")
        
        detail = "\n".join(detail_parts)
        all_found = len(found_ports) == 4
        
        global global_message
        global_message.append(detail)
        
        logger.info(f"check_serial_ports completed: {'PASS' if all_found else 'FAIL'}")
        logger.info(f"Found {len(found_ports)}/4 required ports")
        
        return {
            "item": "Serial ports (ttyACM0-3)",
            "result": "PASS" if all_found else "FAIL",
            "detail": detail,
            "passed": all_found
        }
        
    except Exception as e:
        logger.error(f"check_serial_ports failed with exception: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "item": "Serial ports",
            "result": "FAIL",
            "detail": f"Error checking serial ports: {str(e)}",
            "passed": False
        }

def run_task():
    """Main task function - đây là hàm mà main.py sẽ gọi"""
    logger.info("=== Starting System Information Test ===")
    detail_results = []
    global global_message
    global_message = []  # Reset global message

    # 1. Kiểm tra uname -a
    logger.info("Step 1: Checking system information")
    try:
        output = subprocess.check_output(['/usr/bin/uname', '-a'], text=True).strip()
        detail_results.append({
            "item": "System information",
            "result": "PASS",
            "detail": output,
            "passed": True
        })
        logger.info("System information check: PASS")
    except Exception as e:
        logger.error(f"System information check failed: {e}")
        detail_results.append({
            "item": "System information",
            "result": "FAIL",
            "detail": str(e),
            "passed": False
        })

    # 2. Kiểm tra số lượng phân vùng ổ đĩa
    logger.info("Step 2: Checking disk partitions")
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
        partitions.sort()
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
        logger.info(f"Disk partitions check: {'PASS' if ok else 'FAIL'}")
    except Exception as e:
        logger.error(f"Disk partitions check failed: {e}")
        detail_results.append({
            "item": "Disk partitions",
            "result": "FAIL",
            "detail": str(e),
            "passed": False
        })

    # 3. Kiểm tra lsusb
    logger.info("Step 3: Checking USB devices")
    detail_results.append(check_lsusb())
    
    # 4. Kiểm tra network interfaces
    logger.info("Step 4: Checking network interfaces")
    detail_results.append(list_network_interfaces())
    
    # 5. Kiểm tra serial ports bằng pyserial
    logger.info("Step 5: Checking serial ports")
    try:
        serial_result = check_serial_ports()
        detail_results.append(serial_result)
        logger.info("Serial ports check completed")
    except Exception as e:
        logger.error(f"Serial ports check crashed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        detail_results.append({
            "item": "Serial ports",
            "result": "FAIL", 
            "detail": f"Function crashed: {str(e)}",
            "passed": False
        })

    # 6. Kiểm tra I2C bus 2
    logger.info("Step 6: Checking I2C bus 2")
    try:
        output = subprocess.check_output(['/usr/sbin/i2cdetect', '-y', '2'], text=True)
        
        found_0x68 = False
        device_status = ""
        
        lines = output.strip().split('\n')
        for line in lines:
            # Tìm dòng chứa địa chỉ 60-6f (0x68 nằm trong dải này)
            if line.strip().startswith('60:'):
                parts = line.split()
                # parts[0] = "60:", parts[1] = "60", parts[2] = "61", ..., parts[9] = "68"
                # Vậy 0x68 ở vị trí parts[9] (index 9)
                if len(parts) >= 10:  # Đảm bảo có đủ phần tử
                    device_at_68 = parts[9]  # Vị trí 0x68
                    if device_at_68 in ['68', 'UU']:
                        found_0x68 = True
                        if device_at_68 == 'UU':
                            device_status = "Device at 0x68: UU (in use by driver)"
                        else:
                            device_status = "Device at 0x68: 68 (detected)"
                        break
        
        if not found_0x68:
            device_status = "No device found at 0x68"
        
        detail = f"I2C bus 2 scan result:\n{output.strip()}\n{device_status}"
        
        detail_results.append({
            "item": "I2C bus 2 (device 0x68)",
            "result": "PASS" if found_0x68 else "FAIL",
            "detail": detail,
            "passed": found_0x68
        })
        
        global_message.append(detail)
        logger.info(f"I2C bus 2 check: {'PASS' if found_0x68 else 'FAIL'}")
        
    except Exception as e:
        logger.error(f"I2C bus 2 check failed: {e}")
        detail_results.append({
            "item": "I2C bus 2",
            "result": "FAIL",
            "detail": f"Error checking I2C bus 2: {str(e)}",
            "passed": False
        })

    # Tổng kết
    num_pass = sum(1 for r in detail_results if r["passed"])
    num_fail = len(detail_results) - num_pass
    all_pass = all(r["passed"] for r in detail_results)
    status = "Passed" if all_pass else "Failed"
    message = "\n".join(global_message) + f"\nSummary: {num_pass} PASS, {num_fail} FAIL."

    logger.info(f"=== System Test Completed: {status} ===")
    logger.info(f"Summary: {num_pass} PASS, {num_fail} FAIL")

    return status, message, detail_results

# Alias cho compatibility (nếu có code khác gọi test_task)
test_task = run_task



