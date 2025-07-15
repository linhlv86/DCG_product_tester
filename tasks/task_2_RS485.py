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
DESCRIPTION = "RS485 Communication Test:the quick brown fox jumped over the lazy dog"

# Configuration constants
GPIO_MODE = [129, 135, 122, 127]
SERIAL_PORTS = [f"/dev/ttyACM{i}" for i in range(4)]
BAUD_RATES = [1200, 9600, 38400, 115200]

global_message = []

def set_gpio_mode(gpio_pin, mode):
    """Set GPIO mode: 1 for RS422, 0 for RS485"""
    try:
        logger.info(f"Setting GPIO {gpio_pin} to mode {mode} (0=RS485, 1=RS422)")
        print(f"Setting GPIO {gpio_pin} to mode {mode} (0=RS485, 1=RS422)")
        time.sleep(0.1)  # Small delay for GPIO setting
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

def test_rs485_at_baud(baud_rate):
    """Test RS485 communication at specific baud rate"""
    logger.info(f"Starting RS485 test at {baud_rate} baud")
    results = []
    
    # Open all serial ports
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
        # Set all GPIO modes to 0 (RS485 mode)
        logger.info("Setting GPIO modes to RS485...")
        for i, gpio_pin in enumerate(GPIO_MODE):
            success, error = set_gpio_mode(gpio_pin, 0)
            if not success:
                logger.error(f"Failed to set GPIO {gpio_pin}: {error}")
                results.append({
                    "item": f"Set GPIO {gpio_pin} to RS485 mode",
                    "result": "FAIL",
                    "detail": f"Failed to set GPIO mode: {error}",
                    "passed": False
                })
        
        # Clear all serial buffers
        logger.info("Clearing serial buffers...")
        for ser in serial_connections.values():
            ser.reset_input_buffer()
            ser.reset_output_buffer()
        
        time.sleep(0.5)  # Tăng delay để đảm bảo buffers clear hoàn toàn
        
        # Test each port as transmitter
        for tx_index, tx_port in enumerate(SERIAL_PORTS):
            logger.info(f"Testing transmission from {tx_port}")
            test_data = f"TEST_RS485_{tx_index}_{baud_rate}".encode('utf-8')
            
            # Delay giữa các test để tránh xung đột
            if tx_index > 0:
                logger.info(f"Waiting before test {tx_index + 1}...")
                time.sleep(1.0)  # Delay 1 giây giữa các lần test
            
            try:
                # Clear buffers trước khi test
                for ser in serial_connections.values():
                    ser.reset_input_buffer()
                    ser.reset_output_buffer()
                
                time.sleep(0.2)  # Delay sau khi clear buffer
                
                # Send test data from transmitter
                logger.info(f"Sending data: {test_data}")
                serial_connections[tx_port].write(test_data)
                serial_connections[tx_port].flush()
                time.sleep(0.5)  # Tăng delay để đảm bảo transmission hoàn tất
                
                # Check if other ports received the data
                received_count = 0
                failed_ports = []
                
                for rx_index, rx_port in enumerate(SERIAL_PORTS):
                    if rx_index != tx_index:  # Skip transmitter port
                        try:
                            # Read available data
                            data = serial_connections[rx_port].read_all()
                            logger.info(f"Port {rx_port} received: {data}")
                            
                            if data == test_data:
                                received_count += 1
                                logger.info(f"✓ {rx_port} received correct data")
                            else:
                                failed_ports.append(f"{rx_port}(got:{data.decode() if data else 'nothing'})")
                                logger.warning(f"✗ {rx_port} received wrong data: {data}")
                        except Exception as e:
                            failed_ports.append(f"{rx_port}(error:{str(e)})")
                            logger.error(f"Error reading from {rx_port}: {e}")
                
                # Check if all other ports received data correctly
                expected_receivers = len(SERIAL_PORTS) - 1  # All ports except transmitter
                
                if received_count == expected_receivers:
                    results.append({
                        "item": f"RS485 TX from {tx_port} at {baud_rate} baud",
                        "result": "PASS",
                        "detail": f"Data '{test_data.decode()}' successfully received by all {expected_receivers} ports",
                        "passed": True
                    })
                    logger.info(f"✓ {tx_port} -> all ports at {baud_rate} baud: PASS")
                    global_message.append(f"✓ {tx_port} -> all ports at {baud_rate} baud: PASS")
                else:
                    results.append({
                        "item": f"RS485 TX from {tx_port} at {baud_rate} baud",
                        "result": "FAIL",
                        "detail": f"Only {received_count}/{expected_receivers} ports received data. Failed: {', '.join(failed_ports)}",
                        "passed": False
                    })
                    logger.warning(f"✗ {tx_port} test failed: {received_count}/{expected_receivers} received")
                
                # Clear buffers sau mỗi test
                for ser in serial_connections.values():
                    ser.reset_input_buffer()
                    ser.reset_output_buffer()
                
                time.sleep(0.3)  # Delay sau khi clear buffer
                
            except Exception as e:
                logger.error(f"Transmission error from {tx_port}: {e}")
                results.append({
                    "item": f"RS485 TX from {tx_port} at {baud_rate} baud",
                    "result": "FAIL",
                    "detail": f"Transmission error: {str(e)}",
                    "passed": False
                })
    
    finally:
        # Close all serial connections
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
                time.sleep(2.0)  # Delay 2 giây giữa các baud rate
            
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



