# tasks/task_example_gpio.py
import time
import subprocess
import json
import re
import glob
import os
import serial
import threading
import logging

# Cấu hình logging để xuất ra journalctl
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mô tả của task này, sẽ hiển thị trên giao diện người dùng
DESCRIPTION = "RS485 Communication Test"

# Configuration constants
GPIO_MODE = [129, 135, 122, 127]
SERIAL_PORTS = [f"/dev/ttyACM{i}" for i in range(4)]
BAUD_RATES = [1200, 9600, 38400, 115200]
global_message = []

TEST_DATA_LEN = 2000  # Số byte test, dễ dàng thay đổi

def set_gpio_mode(gpio_pin, mode):
    """
    Ghi giá trị mode vào GPIO thực tế bằng gpioset.
    mode: 0 (RS485), 1 (RS422)
    """
    GP_IOSET = "/usr/bin/gpioset"  # Đường dẫn tuyệt đối tới gpioset
    chip_idx = gpio_pin // 32
    line_idx = gpio_pin % 32
    chip = f"gpiochip{chip_idx}"
    line = str(line_idx)
    try:
        result = subprocess.run([GP_IOSET, chip, f"{line}={mode}"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"gpioset error: {result.stderr}")
            return False, result.stderr
        logger.info(f"GPIO {gpio_pin} ({chip} line {line}) set to {mode} (0=RS485, 1=RS422)")
        return True, ""
    except Exception as e:
        logger.error(f"GPIO setting failed: {e}")
        return False, str(e)

def check_serial_ports_exist():
    """Check if all required serial ports exist"""
    logger.info("Checking if serial ports exist...")
    missing_ports = []
    for port in SERIAL_PORTS:
        if not os.path.exists(port):
            missing_ports.append(port)
            logger.warning(f"Missing port: {port}")
        else:
            logger.info(f"Found port: {port}")
    
    if missing_ports:
        detail = f"Missing serial ports: {', '.join(missing_ports)}"
        logger.error(detail)
        return {
            "item": "Check required serial ports",
            "result": "FAIL",
            "detail": detail,
            "passed": False
        }
    else:
        detail = f"All required serial ports found: {', '.join(SERIAL_PORTS)}"
        logger.info(detail)
        return {
            "item": "Check required serial ports", 
            "result": "PASS",
            "detail": detail,
            "passed": True
        }

def calc_baud_delay(byte_count, baudrate):
    return byte_count * 10 / baudrate + 0.1

def test_rs485_at_baud(baud_rate):
    """Test RS485 communication at specific baud rate"""
    logger.info(f"Starting RS485 test at {baud_rate} baud")
    results = []
    serial_connections = {}
    try:
        logger.info("Opening serial ports...")
        for port in SERIAL_PORTS:
            logger.info(f"Opening {port} at {baud_rate} baud")
            ser = serial.Serial(port, baud_rate, timeout=1)
            serial_connections[port] = ser
            time.sleep(0.1)
        logger.info("All serial ports opened successfully")
    except Exception as e:
        logger.error(f"Failed to open serial ports: {e}")
        return [{
            "item": f"Open serial ports at {baud_rate} baud",
            "result": "FAIL",
            "detail": f"Failed to open serial ports: {str(e)}",
            "passed": False
        }]
    
    try:
        baud_delay = calc_baud_delay(TEST_DATA_LEN, baud_rate)

        # Set all GPIO modes to 0 (RS485 mode)
        logger.info("Setting GPIO modes to RS485...")
        for i, gpio_pin in enumerate(GPIO_MODE):
            set_gpio_mode(gpio_pin, 0)

        # Clear all serial buffers
        for ser in serial_connections.values():
            ser.reset_input_buffer()
            ser.reset_output_buffer()
        time.sleep(0.2)

        # Định nghĩa các cặp kiểm tra chéo
        port_pairs = [
            (SERIAL_PORTS[0], SERIAL_PORTS[1]),
            (SERIAL_PORTS[1], SERIAL_PORTS[0]),
            (SERIAL_PORTS[2], SERIAL_PORTS[3]),
            (SERIAL_PORTS[3], SERIAL_PORTS[2]),
        ]

        for tx_port, rx_port in port_pairs:
            logger.info(f"Testing TX {tx_port} -> RX {rx_port}")

            # Tạo test data dài TEST_DATA_LEN bytes
            base_msg = f"TEST_RS485_{tx_port}_to_{rx_port}_{baud_rate}_"
            remaining_bytes = TEST_DATA_LEN - len(base_msg.encode('utf-8'))
            if remaining_bytes > 0:
                filler = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" * (remaining_bytes // 36 + 1)
                test_data = (base_msg + filler[:remaining_bytes]).encode('utf-8')
            else:
                test_data = base_msg.encode('utf-8')
            if len(test_data) > TEST_DATA_LEN:
                test_data = test_data[:TEST_DATA_LEN]
            elif len(test_data) < TEST_DATA_LEN:
                test_data = test_data + b'X' * (TEST_DATA_LEN - len(test_data))

            # Clear buffers trước khi test
            for ser in serial_connections.values():
                ser.reset_input_buffer()
                ser.reset_output_buffer()
            time.sleep(0.2)

            # Gửi dữ liệu từ TX
            serial_connections[tx_port].write(test_data)
            serial_connections[tx_port].flush()
            time.sleep(baud_delay)

            # Chỉ kiểm tra data ở RX tương ứng
            try:
                data = serial_connections[rx_port].read_all()
                logger.info(f"Port {rx_port} received: {len(data)} bytes")
                if data == test_data:
                    results.append({
                        "item": f"@{baud_rate}:{tx_port}->{rx_port})",
                        "result": "PASS",
                        "detail": f"✓{TEST_DATA_LEN}-byte data successfully received",
                        "passed": True
                    })
                    logger.info(f"✓ {tx_port} -> {rx_port} at {baud_rate} baud: PASS")
                else:
                    # Tìm vị trí đầu tiên bị sai
                    diff_index = next((i for i in range(min(len(data), len(test_data))) if data[i] != test_data[i]), None)
                    diff_count = sum(1 for i in range(min(len(data), len(test_data))) if data[i] != test_data[i])
                    diff_percent = round(100 * diff_count / len(test_data), 2) if len(test_data) > 0 else 0
                    if diff_index is not None:
                        start = max(0, diff_index - 10)
                        end = min(len(test_data), diff_index + 10)
                        expected_snippet = test_data[start:end]
                        received_snippet = data[start:end]
                        detail_msg = (
                            f"[RS485 RX ERROR] Diff at byte {diff_index} (TX:{tx_port}, RX:{rx_port}, baud:{baud_rate}):\n"
                            f"Expected: {expected_snippet}\n"
                            f"Received: {received_snippet}\n"
                            f"Diff bytes: {diff_count}/{len(test_data)} ({diff_percent}%)"
                        )
                    else:
                        detail_msg = (
                            f"Data length mismatch or error. Expected: {len(test_data)}, Received: {len(data)}\n"
                            f"Diff bytes: {diff_count}/{len(test_data)} ({diff_percent}%)"
                        )
                    results.append({
                        "item": f"RS485 {tx_port} -> {rx_port} at {baud_rate} baud ({TEST_DATA_LEN} bytes)",
                        "result": "FAIL",
                        "detail": detail_msg,
                        "passed": False
                    })
                    logger.warning(f"✗ {tx_port} -> {rx_port} received wrong data at byte {diff_index}, diff {diff_percent}%")
            except Exception as e:
                results.append({
                    "item": f"RS485 {tx_port} -> {rx_port} at {baud_rate} baud ({TEST_DATA_LEN} bytes)",
                    "result": "FAIL",
                    "detail": detail_msg,
                    "passed": False
                })
                logger.error(detail_msg)

            # Clear buffers sau mỗi test
            for ser in serial_connections.values():
                ser.reset_input_buffer()
                ser.reset_output_buffer()
            time.sleep(0.2)

    finally:
        logger.info("Closing serial connections...")
        for port, ser in serial_connections.items():
            try:
                ser.close()
                logger.info(f"Closed {port}")
            except Exception as e:
                logger.error(f"Error closing {port}: {e}")

    logger.info(f"Completed RS485 test at {baud_rate} baud")
    return results

def test_task():
    logger.info("=== Starting RS485 Communication Test ===")
    detail_results = []
    global global_message
    global_message = []  # Reset global message
    
    try:
        # First check if all serial ports exist
        logger.info("Step 1: Checking serial ports existence")
        port_check = check_serial_ports_exist()
        detail_results.append(port_check)
        
        if not port_check["passed"]:
            # If ports don't exist, return early
            logger.error("Serial ports check failed, aborting test")
            status = "Failed"
            message = port_check["detail"] + f"\nSummary: 0 PASS, 1 FAIL."
            return status, message, detail_results
        
        # Test RS485 communication for each baud rate
        logger.info("Step 2: Testing RS485 communication at different baud rates")
        for baud_index, baud_rate in enumerate(BAUD_RATES):
            # Delay giữa các baud rate tests
            if baud_index > 0:
                logger.info(f"Waiting before testing baud rate {baud_rate}...")
                time.sleep(0.2)  # Delay .2 giây giữa các baud rate
            
            logger.info(f"Testing at {baud_rate} baud...")
            global_message.append(f"--- Testing at {baud_rate} baud ---")
            
            baud_results = test_rs485_at_baud(baud_rate)
            detail_results.extend(baud_results)
            
            # Count pass/fail for this baud rate
            baud_pass = sum(1 for r in baud_results if r["passed"])
            baud_total = len(baud_results)
            logger.info(f"Baud {baud_rate}: {baud_pass}/{baud_total} tests passed")
            global_message.append(f"Baud {baud_rate}: {baud_pass}/{baud_total} tests passed")
        
        # Tổng kết
        num_pass = sum(1 for r in detail_results if r["passed"])
        num_fail = len(detail_results) - num_pass
        all_pass = all(r["passed"] for r in detail_results)
        status = "Passed" if all_pass else "Failed"
        message = "\n".join(global_message) + f"\nSummary: {num_pass} PASS, {num_fail} FAIL."

        logger.info(f"=== RS485 Test Completed: {status} ===")
        logger.info(f"Summary: {num_pass} PASS, {num_fail} FAIL")

        return status, message, detail_results
        
    except Exception as e:
        logger.error(f"Unexpected error in test_task: {e}")
        # Tổng kết khi có lỗi
        num_pass = sum(1 for r in detail_results if r["passed"])
        num_fail = len(detail_results) - num_pass + 1  # +1 cho lỗi exception
        status = "Failed"
        message = "\n".join(global_message) + f"\nTest error: {str(e)}\nSummary: {num_pass} PASS, {num_fail} FAIL."
        return status, message, detail_results



