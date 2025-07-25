import subprocess
import time
import logging
import os
import re
import glob

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DESCRIPTION = "MCU Test"

CO_MCU_SERIAL = "/dev/ttyS1"  # Replace with actual port if needed

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

def get_fw_version(bin_file):
    # Extract version string from filename: mcu_firmware.[version_string].bin
    match = re.search(r"mcu_firmware\.([^.]+)\.bin", os.path.basename(bin_file))
    if match:
        return match.group(1)
    return "unknown"

def flash_comcu_firmware(bin_file, serial_port="/dev/ttyS3"):
    PWM_CHIP = "/sys/class/pwm/pwmchip1"
    PWM = f"{PWM_CHIP}/pwm0"

    # Check firmware file
    if not bin_file or not os.path.isfile(bin_file):
        logger.error(f"Error: FW file not found: {bin_file}")
        return False, "File not found"

    try:
        # Export PWM if not exists
        if not os.path.isdir(PWM):
            subprocess.run(["/usr/bin/bash", "-c", f"echo 0 > {PWM_CHIP}/export"], check=True)
        # Set period and duty cycle
        subprocess.run(["/usr/bin/bash", "-c", f"echo 10000 > {PWM}/period"], check=True)
        subprocess.run(["/usr/bin/bash", "-c", f"echo 5000 > {PWM}/duty_cycle"], check=True)
        # Enable PWM
        subprocess.run(["/usr/bin/bash", "-c", f"echo 1 > {PWM}/enable"], check=True)
        time.sleep(1)
        # Disable PWM
        subprocess.run(["/usr/bin/bash", "-c", f"echo 0 > {PWM}/enable"], check=True)
        # Unexport PWM
        subprocess.run(["/usr/bin/bash", "-c", f"echo 0 > {PWM_CHIP}/unexport"], check=True)
        time.sleep(3)
        # Flash firmware via UART
        cmd = ["/usr/bin/stm32flash", "-w", bin_file, "-v", "-g", "0x0", serial_port]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Firmware flashing failed: {result.stderr}")
            return False, result.stderr
        logger.info("Firmware flashing successful")
        return True, "Firmware flashing successful"
    except Exception as e:
        logger.error(f"Error while flashing firmware: {e}")
        return False, str(e)

def test_task():
    logger.info("=== Starting MCU Test ===")
    detail_results = []

    # 1. Find firmware file
    fw_files = glob.glob("tasks/mcu_fw/mcu_firmware*.bin")
    if len(fw_files) == 0:
        detail_results.append({
            "item": "Find MCU firmware",
            "result": "FAIL",
            "detail": "No firmware file found in tasks/mcu_fw/",
            "passed": False
        })
        return "Failed", "No firmware file found", detail_results
    if len(fw_files) > 1:
        detail_results.append({
            "item": "Find MCU firmware",
            "result": "FAIL",
            "detail": f"Multiple firmware files found: {fw_files}",
            "passed": False
        })
        return "Failed", "Multiple firmware files found", detail_results

    fw_path = fw_files[0]
    fw_version = get_fw_version(fw_path)
    fw_ok, fw_msg = flash_comcu_firmware(fw_path)
    detail_results.append({
        "item": "Flash MCU FW",
        "result": "PASS" if fw_ok else "FAIL",
        "detail": f"{fw_msg} | Version: {fw_version}",
        "passed": fw_ok
    })
    if not fw_ok:
        return "Failed", f"MCU firmware burn error | Version: {fw_version}", detail_results

if __name__ == "__main__":
    status, detail, results = test_task()
    print(status, detail)
    for r in results:
        print(r)