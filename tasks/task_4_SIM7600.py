import time
import subprocess
import os
import serial
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DESCRIPTION = "SIM7600 Module Test"

# GPIO mapping
GPIO_POWER = 123
GPIO_SIMSEL = 144

# Serial ports expected for SIM7600
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
    logger.info("Checking SIM7600 serial ports...")
    missing_ports = []
    for port in SIM_SERIAL_PORTS:
        if not os.path.exists(port):
            missing_ports.append(port)
            logger.warning(f"Missing port: {port}")
        else:
            logger.info(f"Found port: {port}")
    if missing_ports:
        detail = f"Missing SIM7600 serial ports: {', '.join(missing_ports)}"
        logger.error(detail)
        return {
            "item": "Check SIM7600 serial ports",
            "result": "FAIL",
            "detail": detail,
            "passed": False
        }
    else:
        detail = f"All SIM7600 serial ports found: {', '.join(SIM_SERIAL_PORTS)}"
        logger.info(detail)
        return {
            "item": "Check SIM7600 serial ports",
            "result": "PASS",
            "detail": detail,
            "passed": True
        }

def sim7600_chat(port, chat_script, timeout=2):
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
                    "item": f"SIM7600 chat: {cmd}",
                    "result": "FAIL",
                    "detail": f"Expect '{expect}' not found in response: {response.strip()}",
                    "passed": False
                })
            else:
                results.append({
                    "item": f"SIM7600 chat: {cmd}",
                    "result": "PASS",
                    "detail": f"Response: {response.strip()}",
                    "passed": True
                })
        ser.close()
    except Exception as e:
        logger.error(f"SIM7600 chat error: {e}")
        results.append({
            "item": "SIM7600 chat",
            "result": "FAIL",
            "detail": f"Serial error: {str(e)}",
            "passed": False
        })
    return results

def test_task():
    logger.info("=== Starting SIM7600 Module Test ===")
    detail_results = []

    # 1. Power ON module
    ok, msg = set_gpio(GPIO_POWER, 1)
    detail_results.append({
        "item": "Power ON SIM7600 (GPIO123=1)",
        "result": "PASS" if ok else "FAIL",
        "detail": msg if not ok else "Power ON OK",
        "passed": ok
    })
    time.sleep(1)

    # 2. SIM select
    ok, msg = set_gpio(GPIO_SIMSEL, 0)
    detail_results.append({
        "item": "SIM Select (GPIO144=0)",
        "result": "PASS" if ok else "FAIL",
        "detail": msg if not ok else "SIM Select OK",
        "passed": ok
    })
    time.sleep(1)

    # 3. Check serial ports
    port_check = check_sim_ports_exist()
    detail_results.append(port_check)
    if not port_check["passed"]:
        logger.error("SIM7600 serial ports check failed, aborting test")
        status = "Failed"
        message = port_check["detail"] + f"\nSummary: 0 PASS, 1 FAIL."
        return status, message, detail_results

    # 4. Open ttyUSB2 and send ATI
    chat_script = [
        ("OK", "AT"),
        ("OK", "ATI"),
        ("OK", "AT+CPIN?"),
    ]
    chat_results = sim7600_chat(SIM_AT_PORT, chat_script)
    detail_results.extend(chat_results)

    # 5. Get ICCID (IMEI SIM)
    iccid_result = []
    try:
        ser = serial.Serial(SIM_AT_PORT, 115200, timeout=2)
        time.sleep(0.5)
        ser.write(b"AT+CICCID\r")
        ser.flush()
        time.sleep(0.5)
        response = ser.read_all().decode(errors="ignore")
        logger.info(f"ICCID Response: {response.strip()}")
        if "ICCID" in response or "+CICCID:" in response:
            iccid_result.append({
                "item": "SIM7600 AT+CICCID",
                "result": "PASS",
                "detail": response.strip(),
                "passed": True
            })
        else:
            iccid_result.append({
                "item": "SIM7600 AT+CICCID",
                "result": "FAIL",
                "detail": f"No ICCID info: {response.strip()}",
                "passed": False
            })
        ser.close()
    except Exception as e:
        logger.error(f"SIM7600 ICCID error: {e}")
        iccid_result.append({
            "item": "SIM7600 AT+CICCID",
            "result": "FAIL",
            "detail": f"Serial error: {str(e)}",
            "passed": False
        })
    detail_results.extend(iccid_result)

    # Tổng kết
    num_pass = sum(1 for r in detail_results if r["passed"])
    num_fail = len(detail_results) - num_pass
    status = "Passed" if num_fail == 0 else "Failed"
    message = f"SIM7600 Test: {num_pass} PASS, {num_fail} FAIL."
    logger.info(f"=== SIM7600 Test Completed: {status} ===")
    logger.info(f"Summary: {num_pass} PASS, {num_fail} FAIL")
    return status, message, detail_results