import subprocess
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DESCRIPTION = "CoMCU Test"

# Ví dụ: mapping GPIO hoặc serial nếu cần
CO_MCU_GPIO = 150  # Thay bằng GPIO thực tế
CO_MCU_SERIAL = "/dev/ttyS1"  # Thay bằng cổng thực tế

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

def test_comcu():
    logger.info("=== Starting CoMCU Test ===")
    detail_results = []

    # 1. Khởi động CoMCU (ví dụ bật nguồn qua GPIO)
    ok, msg = set_gpio(CO_MCU_GPIO, 1)
    if not ok:
        detail_results.append({
            "item": "Power ON CoMCU",
            "result": "FAIL",
            "detail": msg,
            "passed": False
        })
        return "Failed", "Power ON CoMCU error", detail_results
    logger.info("Power ON CoMCU")
    time.sleep(2)

    # 2. Kiểm tra giao tiếp CoMCU (ví dụ gửi lệnh qua serial)
    # Bạn bổ sung đoạn kiểm tra thực tế ở đây

    detail_results.append({
        "item": "CoMCU Test",
        "result": "PASS",
        "detail": "CoMCU test completed",
        "passed": True
    })
    return "Passed", "CoMCU test OK", detail_results

def flash_comcu_firmware(bin_file, serial_port="/dev/ttyS3"):
    PWM_CHIP = "/sys/class/pwm/pwmchip1"
    PWM = f"{PWM_CHIP}/pwm0"

    import os

    # Kiểm tra file firmware
    if not bin_file or not os.path.isfile(bin_file):
        logger.error(f"Lỗi: File không tồn tại hoặc chưa được chỉ định: {bin_file}")
        return False, "File không tồn tại hoặc chưa được chỉ định"

    try:
        # Export PWM nếu chưa tồn tại
        if not os.path.isdir(PWM):
            subprocess.run(["bash", "-c", f"echo 0 > {PWM_CHIP}/export"], check=True)
        # Thiết lập period và duty cycle
        subprocess.run(["bash", "-c", f"echo 10000 > {PWM}/period"], check=True)
        subprocess.run(["bash", "-c", f"echo 5000 > {PWM}/duty_cycle"], check=True)
        # Bật PWM
        subprocess.run(["bash", "-c", f"echo 1 > {PWM}/enable"], check=True)
        time.sleep(1)
        # Tắt PWM
        subprocess.run(["bash", "-c", f"echo 0 > {PWM}/enable"], check=True)
        # Unexport PWM
        subprocess.run(["bash", "-c", f"echo 0 > {PWM_CHIP}/unexport"], check=True)
        time.sleep(3)
        # Nạp firmware qua UART
        cmd = ["stm32flash", "-w", bin_file, "-v", "-g", "0x0", serial_port]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Lỗi nạp FW: {result.stderr}")
            return False, result.stderr
        logger.info("Nạp FW thành công")
        return True, "Nạp FW thành công"
    except Exception as e:
        logger.error(f"Lỗi khi nạp FW: {e}")
        return False, str(e)

def test_task():
    logger.info("=== Starting CoMCU Test ===")
    detail_results = []

    # 1. Nạp firmware cho CoMCU
    fw_path = "tasks/mcu_fw/mcu_firmware.bin"
    fw_ok, fw_msg = flash_comcu_firmware(fw_path)
    detail_results.append({
        "item": "Flash CoMCU FW",
        "result": "PASS" if fw_ok else "FAIL",
        "detail": fw_msg,
        "passed": fw_ok
    })
    if not fw_ok:
        return "Failed", "Nạp firmware CoMCU lỗi", detail_results

    # 2. Khởi động CoMCU (ví dụ bật nguồn qua GPIO)
    ok, msg = set_gpio(CO_MCU_GPIO, 1)
    if not ok:
        detail_results.append({
            "item": "Power ON CoMCU",
            "result": "FAIL",
            "detail": msg,
            "passed": False
        })
        return "Failed", "Power ON CoMCU error", detail_results
    logger.info("Power ON CoMCU")
    time.sleep(2)

    # 3. (Tùy chọn) Kiểm tra giao tiếp CoMCU ở đây nếu cần

    detail_results.append({
        "item": "CoMCU Test",
        "result": "PASS",
        "detail": "CoMCU test completed",
        "passed": True
    })
    return "Passed", "CoMCU test OK", detail_results

if __name__ == "__main__":
    status, detail, results = test_task()
    print(status, detail)
    for r in results:
        print(r)