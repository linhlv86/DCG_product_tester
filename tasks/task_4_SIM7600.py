import time
import subprocess
import os
import serial
import logging
import glob
import serial.tools.list_ports

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DESCRIPTION = "SIM7602 Module Test"

# GPIO mapping
GPIO_POWER = 123
GPIO_SIMSEL = 144

# Serial ports expected for SIM7602
SIM_SERIAL_PORTS = [f"/dev/ttyUSB{i}" for i in range(4)]
SIM_AT_PORT = "/dev/ttyUSB1"

def set_gpio(gpio_pin, value):
    GP_IOSET = "/usr/bin/gpioset"
    chip_idx = gpio_pin // 32
    line_idx = gpio_pin % 32
    chip = f"gpiochip{chip_idx}"
    line = str(line_idx)
    try:
        result = subprocess.run([GP_IOSET, chip, f"{line}={value}"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"gpioset error: {result.stderr}")
            return False, result.stderr
        logger.info(f"GPIO {gpio_pin} ({chip} line {line}) set to {value}")
        return True, ""
    except Exception as e:
        logger.error(f"GPIO setting failed: {e}")
        return False, str(e)

def check_sim_ports_exist():
    logger.info("Checking SIM7602 serial ports with glob...")
    found_ports = glob.glob("/dev/ttyUSB*")
    logger.info(f"Found ports: {found_ports}")
    missing_ports = []
    for port in SIM_SERIAL_PORTS:
        if port not in found_ports:
            missing_ports.append(port)
            logger.warning(f"Missing port: {port}")
        else:
            logger.info(f"Found port: {port}")
    if missing_ports:
        detail = f"Missing SIM7602 serial ports: {', '.join(missing_ports)}"
        logger.error(detail)
        return {
            "item": "Check SIM7602 serial ports",
            "result": "FAIL",
            "detail": detail,
            "passed": False
        }
    else:
        detail = f"All SIM7602 serial ports found: {', '.join(SIM_SERIAL_PORTS)}"
        logger.info(detail)
        return {
            "item": "Check SIM7602 serial ports",
            "result": "PASS",
            "detail": detail,
            "passed": True
        }

def sim7602_chat(port, chat_script, timeout=2):
    results = []
    try:
        ser = serial.Serial(port, 115200, timeout=timeout)
        time.sleep(0.5)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        for expect, cmd in chat_script:
            logger.info(f"Send: {cmd}")
            ser.write((cmd + "\r").encode())
            ser.flush()
            time.sleep(0.5)
            response = ser.read_all().decode(errors="ignore")
            logger.info(f"Response: {response.strip()}")
            if expect and expect not in response:
                results.append({
                    "item": f"SIM7602 chat: {cmd}",
                    "result": "FAIL",
                    "detail": f"Expect '{expect}' not found in response: {response.strip()}",
                    "passed": False
                })
            else:
                results.append({
                    "item": f"SIM7602 chat: {cmd}",
                    "result": "PASS",
                    "detail": f"Response: {response.strip()}",
                    "passed": True
                })
        ser.close()
    except Exception as e:
        logger.error(f"SIM7602 chat error: {e}")
        results.append({
            "item": "SIM7602 chat",
            "result": "FAIL",
            "detail": f"Serial error: {str(e)}",
            "passed": False
        })
    return results

def test_task():
    logger.info("=== Starting SIM7602 Module Test ===")
    detail_results = []

    # Power off module trước khi bắt đầu
    set_gpio(GPIO_POWER, 0)
    time.sleep(1)

    # Chọn SIM1
    sim1_ok, msgSIM1 = set_gpio(GPIO_SIMSEL, 0)
    # Power ON module
    power_ok, msgPower = set_gpio(GPIO_POWER, 1)
    time.sleep(10)  # Đợi module khởi động xong

    detail_results.append({
        "item": "Start SIM7602 with SIM card 1",
        "result": "PASS" if (power_ok and sim1_ok) else "FAIL",
        "detail": f"Power: {msgPower}, SIM1: {msgSIM1}" if not (power_ok and sim1_ok) else "Power ON & SIM1 OK",
        "passed": power_ok and sim1_ok
    })

    # Kiểm tra serial ports
    port_check = check_sim_ports_exist()
    detail_results.append(port_check)
    if not port_check["passed"]:
        logger.error("SIM7602 serial ports check failed, aborting test")
        status = "Failed"
        message = port_check["detail"] + f"\nSummary: 0 PASS, 1 FAIL."
        return status, message, detail_results

    # Đọc ICCID SIM1
    iccid1 = ""
    iccid_result1 = []
    try:
        ser = serial.Serial(SIM_AT_PORT, 115200, timeout=2)
        time.sleep(0.5)
        ser.write(b"AT+CICCID\r")
        ser.flush()
        time.sleep(0.5)
        response = ser.read_all().decode(errors="ignore")
        logger.info(f"SIM1 ICCID Response: {response.strip()}")
        for line in response.splitlines():
            if "+ICCID:" in line or "ICCID:" in line:
                iccid1 = line.strip().split(":")[-1].strip()
        if iccid1:
            iccid_result1.append({
                "item": "SIM1 CICCID",
                "result": "PASS",
                "detail": f"AT+CICCID\n{line.strip()}",
                "passed": True
            })
        else:
            iccid_result1.append({
                "item": " SIM1 CICCID",
                "result": "FAIL",
                "detail": f"No ICCID info: {response.strip()}",
                "passed": False
            })
        ser.close()
    except Exception as e:
        logger.error(f"ICCID SIM1 error: {e}")
        iccid_result1.append({
            "item": "SIM1 CICCID",
            "result": "FAIL",
            "detail": f"Serial error: {str(e)}",
            "passed": False
        })
    detail_results.extend(iccid_result1)

    # Power off module
    set_gpio(GPIO_POWER, 0)
    time.sleep(1)

    # Đổi sang SIM2
    sim2_ok, msgSIM2 = set_gpio(GPIO_SIMSEL, 1)
    # Power ON module lại
    power_ok2, msgPower2 = set_gpio(GPIO_POWER, 1)
    time.sleep(3)

    detail_results.append({
        "item": "Switch to SIM card 2 and power ON",
        "result": "PASS" if (power_ok2 and sim2_ok) else "FAIL",
        "detail": f"Power: {msgPower2}, SIM2: {msgSIM2}" if not (power_ok2 and sim2_ok) else "Power ON & SIM2 OK",
        "passed": power_ok2 and sim2_ok
    })

    # Đọc ICCID SIM2
    iccid2 = ""
    iccid_result2 = []
    try:
        ser = serial.Serial(SIM_AT_PORT, 115200, timeout=2)
        time.sleep(0.5)
        ser.write(b"AT+CICCID\r")
        ser.flush()
        time.sleep(0.5)
        response = ser.read_all().decode(errors="ignore")
        logger.info(f"SIM2 ICCID Response: {response.strip()}")
        for line in response.splitlines():
            if "+ICCID:" in line or "ICCID:" in line:
                iccid2 = line.strip().split(":")[-1].strip()
        if iccid2:
            iccid_result2.append({
                "item": "SIM2 CICCID",
                "result": "PASS",
                "detail": f"AT+CICCID\n{line.strip()}",
                "passed": True
            })
        else:
            iccid_result2.append({
                "item": "SIM2 CICCID",
                "result": "FAIL",
                "detail": f"No ICCID info: {response.strip()}",
                "passed": False
            })
        ser.close()
    except Exception as e:
        logger.error(f"SIM7602 ICCID SIM2 error: {e}")
        iccid_result2.append({
            "item": "SIM2 CICCID ",
            "result": "FAIL",
            "detail": f"Error: {str(e)}",
            "passed": False
        })
    detail_results.extend(iccid_result2)

    # So sánh ICCID SIM1 và SIM2
    compare_result = []
    if iccid1 and iccid2 and iccid1 != iccid2:
        compare_result.append({
            "item": "Switch SIM1 to SIM2",
            "result": "PASS",
            "detail": f"SIM1 ICCID: {iccid1}\nSIM2 ICCID: {iccid2}",
            "passed": True
        })
    else:
        compare_result.append({
            "item": "Compare ICCID SIM1 vs SIM2",
            "result": "FAIL",
            "detail": f"SIM1 ICCID: {iccid1}\nSIM2 ICCID: {iccid2}\nICCID can not switch SIM card normaly  .",
            "passed": False
        })
        
    detail_results.extend(compare_result)

    # Power off module cuối cùng
    set_gpio(GPIO_POWER, 0)

    # Tổng kết
    num_pass = sum(1 for r in detail_results if r["passed"])
    num_fail = len(detail_results) - num_pass
    status = "Passed" if num_fail == 0 else "Failed"
    message = f"SIM7602 Test: {num_pass} PASS, {num_fail} FAIL."
    logger.info(f"=== SIM7602 Test Completed: {status} ===")
    logger.info(f"Summary: {num_pass} PASS, {num_fail} FAIL")
    return status, message, detail_results