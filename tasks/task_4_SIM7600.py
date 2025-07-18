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

def wait_for_ports(ports, timeout=20, interval=0.2):
    logger.info(f"Waiting for ports: {ports}")
    start = time.time()
    while time.time() - start < timeout:
        found = [port for port in ports if os.path.exists(port)]
        if len(found) == len(ports):
            logger.info(f"All ports found: {found}")
            return True
        time.sleep(interval)
    logger.warning(f"Timeout waiting for ports: {ports}. Found: {found}")
    return False

def test_task():
    logger.info("=== Starting SIM7602 Module Test ===")
    detail_results = []

    # 1. Khởi động module
    set_gpio(GPIO_POWER, 1)
    logger.info("Power ON SIM7602 module")
    time.sleep(2)  # Đợi module khởi động   
    try:
        subprocess.run(["modprobe", "option"], check=True)
        with open("/sys/bus/usb-serial/drivers/option1/new_id", "w") as f:
            f.write("1286 4e3c\n")
        logger.info("modprobe option & new_id OK")
    except Exception as e:
        logger.error(f"modprobe/echo new_id error: {e}")

    if not wait_for_ports(SIM_SERIAL_PORTS, timeout=20, interval=0.2):
        detail = "Timeout waiting for SIM7602 ports"
        logger.error(detail)
        detail_results.append({
            "item": "Module startup",
            "result": "FAIL",
            "detail": detail,
            "passed": False
        })
        set_gpio(GPIO_POWER, 0)
        return "Failed", detail, detail_results
    detail_results.append({
        "item": "Module startup",
        "result": "PASS",
        "detail": "SIM7602 ports detected",
        "passed": True
    })

    # 2. Kiểm tra SIM1
    sim1_ok, msgSIM1 = set_gpio(GPIO_SIMSEL, 0)
    logger.info("Select SIM1")
    time.sleep(0.5)
    ccid1 = ""
    try:
        ser = serial.Serial(SIM_AT_PORT, 115200, timeout=2)
        time.sleep(0.5)
        # Gửi at+cfun=0
        ser.write(b"AT+CFUN=0\r")
        ser.flush()
        time.sleep(1)
        ser.read_all()
        # Gửi AT+CGEREP=0,0
        ser.write(b"AT+CGEREP=0,0\r")
        ser.flush()
        time.sleep(1)
        ser.read_all()
        # Chuyển sang SIM1 (đã set GPIO ở trên)
        # Gửi at+cfun=1
        ser.write(b"AT+CFUN=1\r")
        ser.flush()
        time.sleep(5)
        ser.read_all()
        # Kiểm tra AT+CPIN?
        ser.write(b"AT+CPIN?\r")
        ser.flush()
        time.sleep(1)
        response = ser.read_all().decode(errors="ignore")
        logger.info(f"SIM1 AT+CPIN? Response: {response.strip()}")
        if "READY" in response or "CPIN: READY" in response:
            detail_results.append({
                "item": "SIM1 AT+CPIN?",
                "result": "PASS",
                "detail": response.strip(),
                "passed": True
            })
        else:
            detail_results.append({
                "item": "SIM1 AT+CPIN?",
                "result": "FAIL",
                "detail": response.strip(),
                "passed": False
            })
        # Đọc CCID SIM1
        ser.write(b"AT+CICCID\r")
        ser.flush()
        time.sleep(1)
        response = ser.read_all().decode(errors="ignore")
        logger.info(f"SIM1 AT+CICCID Response: {response.strip()}")
        for line in response.splitlines():
            if "+ICCID:" in line or "ICCID:" in line:
                ccid1 = line.strip().split(":")[-1].strip()
        if ccid1:
            detail_results.append({
                "item": "SIM1 CCID",
                "result": "PASS",
                "detail": ccid1,
                "passed": True
            })
        else:
            detail_results.append({
                "item": "SIM1 CCID",
                "result": "FAIL",
                "detail": response.strip(),
                "passed": False
            })
        ser.close()
    except Exception as e:
        logger.error(f"SIM1 test error: {e}")
        detail_results.append({
            "item": "SIM1 test",
            "result": "FAIL",
            "detail": str(e),
            "passed": False
        })

    # 3. Kiểm tra SIM2
    sim2_ok, msgSIM2 = set_gpio(GPIO_SIMSEL, 1)
    logger.info("Select SIM2")
    time.sleep(0.5)
    ccid2 = ""
    try:
        ser = serial.Serial(SIM_AT_PORT, 115200, timeout=2)
        time.sleep(0.5)
        # Gửi at+cfun=0
        ser.write(b"AT+CFUN=0\r")
        ser.flush()
        time.sleep(1)
        ser.read_all()
        # Gửi AT+CGEREP=0,0
        ser.write(b"AT+CGEREP=0,0\r")
        ser.flush()
        time.sleep(1)
        ser.read_all()
        # Chuyển sang SIM2 (đã set GPIO ở trên)
        time.sleep(0.5)
        # Gửi at+cfun=1
        ser.write(b"AT+CFUN=1\r")
        ser.flush()
        time.sleep(5)
        ser.read_all()
        # Kiểm tra AT+CPIN?
        ser.write(b"AT+CPIN?\r")
        ser.flush()
        time.sleep(1)
        response = ser.read_all().decode(errors="ignore")
        logger.info(f"SIM2 AT+CPIN? Response: {response.strip()}")
        if "READY" in response or "CPIN: READY" in response:
            detail_results.append({
                "item": "SIM2 AT+CPIN?",
                "result": "PASS",
                "detail": response.strip(),
                "passed": True
            })
        else:
            detail_results.append({
                "item": "SIM2 AT+CPIN?",
                "result": "FAIL",
                "detail": response.strip(),
                "passed": False
            })
        # Đọc CCID SIM2
        ser.write(b"AT+CICCID\r")
        ser.flush()
        time.sleep(1)
        response = ser.read_all().decode(errors="ignore")
        logger.info(f"SIM2 AT+CICCID Response: {response.strip()}")
        for line in response.splitlines():
            if "+ICCID:" in line or "ICCID:" in line:
                ccid2 = line.strip().split(":")[-1].strip()
        if ccid2:
            detail_results.append({
                "item": "SIM2 CCID",
                "result": "PASS",
                "detail": ccid2,
                "passed": True
            })
        else:
            detail_results.append({
                "item": "SIM2 CCID",
                "result": "FAIL",
                "detail": response.strip(),
                "passed": False
            })
        ser.close()
    except Exception as e:
        logger.error(f"SIM2 test error: {e}")
        detail_results.append({
            "item": "SIM2 test",
            "result": "FAIL",
            "detail": str(e),
            "passed": False
        })

    # 4. So sánh CCID
    if ccid1 and ccid2 and ccid1 != ccid2:
        detail_results.append({
            "item": "Switch SIM1 to SIM2",
            "result": "PASS",
            "detail": f"SIM1 CCID: {ccid1}\nSIM2 CCID: {ccid2}",
            "passed": True
        })
    else:
        detail_results.append({
            "item": "Compare CCID SIM1 vs SIM2",
            "result": "FAIL",
            "detail": f"SIM1 CCID: {ccid1}\nSIM2 CCID: {ccid2}\nCCID not switched or missing.",
            "passed": False
        })

    # 5. Trả các GPIO về giá trị ban đầu
    set_gpio(GPIO_POWER, 0)
    set_gpio(GPIO_SIMSEL, 0)

    # Tổng kết
    num_pass = sum(1 for r in detail_results if r["passed"])
    num_fail = len(detail_results) - num_pass
    status = "Passed" if num_fail == 0 else "Failed"
    message = f"SIM7602 Test: {num_pass} PASS, {num_fail} FAIL."
    logger.info(f"=== SIM7602 Test Completed: {status} ===")
    logger.info(f"Summary: {num_pass} PASS, {num_fail} FAIL")
    return status, message, detail_results