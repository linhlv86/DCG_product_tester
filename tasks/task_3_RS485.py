# tasks/task_example_gpio.py
import time
import subprocess
import json
import re
import glob
import os
import serial
import threading

# Mô tả của task này, sẽ hiển thị trên giao diện người dùng
DESCRIPTION = "RS485 Communication Test"

# Configuration constants
GPIO_MODE = [129, 135, 122, 127]
SERIAL_PORTS = [f"/dev/ttyACM{i}" for i in range(4)]
BAUD_RATES = [1200, 9600, 38400, 115200]

global_message = []

def set_gpio_mode(gpio_pin, mode):
    """Set GPIO mode: 1 for RS422, 0 for RS485"""
    try:
        # Implement GPIO mode setting logic here
        # Example using sysfs GPIO interface:
        # echo {gpio_pin} > /sys/class/gpio/export
        # echo out > /sys/class/gpio/gpio{gpio_pin}/direction
        # echo {mode} > /sys/class/gpio/gpio{gpio_pin}/value
        
        # For now, simulate the GPIO setting
        print(f"Setting GPIO {gpio_pin} to mode {mode} (0=RS485, 1=RS422)")
        time.sleep(0.1)  # Small delay for GPIO setting
        return True, ""
    except Exception as e:
        return False, str(e)

def check_serial_ports_exist():
    """Check if all required serial ports exist"""
    missing_ports = []
    for port in SERIAL_PORTS:
        if not os.path.exists(port):
            missing_ports.append(port)
    
    if missing_ports:
        detail = f"Missing serial ports: {', '.join(missing_ports)}"
        return {
            "item": "Check required serial ports",
            "result": "FAIL",
            "detail": detail,
            "passed": False
        }
    else:
        detail = f"All required serial ports found: {', '.join(SERIAL_PORTS)}"
        return {
            "item": "Check required serial ports", 
            "result": "PASS",
            "detail": detail,
            "passed": True
        }

def test_rs485_at_baud(baud_rate):
    """Test RS485 communication at specific baud rate"""
    results = []
    
    # Open all serial ports
    serial_connections = {}
    try:
        for port in SERIAL_PORTS:
            ser = serial.Serial(port, baud_rate, timeout=1)
            serial_connections[port] = ser
            time.sleep(0.1)
    except Exception as e:
        return [{
            "item": f"Open serial ports at {baud_rate} baud",
            "result": "FAIL",
            "detail": f"Failed to open serial ports: {str(e)}",
            "passed": False
        }]
    
    try:
        # Set all GPIO modes to 0 (RS485 mode)
        for i, gpio_pin in enumerate(GPIO_MODE):
            success, error = set_gpio_mode(gpio_pin, 0)
            if not success:
                results.append({
                    "item": f"Set GPIO {gpio_pin} to RS485 mode",
                    "result": "FAIL",
                    "detail": f"Failed to set GPIO mode: {error}",
                    "passed": False
                })
        
        # Clear all serial buffers
        for ser in serial_connections.values():
            ser.reset_input_buffer()
            ser.reset_output_buffer()
        
        time.sleep(0.2)  # Wait for buffers to clear
        
        # Test each port as transmitter
        for tx_index, tx_port in enumerate(SERIAL_PORTS):
            test_data = f"TEST_RS485_{tx_index}_{baud_rate}".encode('utf-8')
            
            try:
                # Send test data from transmitter
                serial_connections[tx_port].write(test_data)
                serial_connections[tx_port].flush()
                time.sleep(0.3)  # Wait for transmission
                
                # Check if other ports received the data
                received_count = 0
                failed_ports = []
                
                for rx_index, rx_port in enumerate(SERIAL_PORTS):
                    if rx_index != tx_index:  # Skip transmitter port
                        try:
                            # Read available data
                            data = serial_connections[rx_port].read_all()
                            
                            if data == test_data:
                                received_count += 1
                            else:
                                failed_ports.append(f"{rx_port}(got:{data.decode() if data else 'nothing'})")
                        except Exception as e:
                            failed_ports.append(f"{rx_port}(error:{str(e)})")
                
                # Check if all other ports received data correctly
                expected_receivers = len(SERIAL_PORTS) - 1  # All ports except transmitter
                
                if received_count == expected_receivers:
                    results.append({
                        "item": f"RS485 TX from {tx_port} at {baud_rate} baud",
                        "result": "PASS",
                        "detail": f"Data '{test_data.decode()}' successfully received by all {expected_receivers} ports",
                        "passed": True
                    })
                    global_message.append(f"✓ {tx_port} -> all ports at {baud_rate} baud: PASS")
                else:
                    results.append({
                        "item": f"RS485 TX from {tx_port} at {baud_rate} baud",
                        "result": "FAIL",
                        "detail": f"Only {received_count}/{expected_receivers} ports received data. Failed: {', '.join(failed_ports)}",
                        "passed": False
                    })
                
                # Clear buffers after each test
                for ser in serial_connections.values():
                    ser.reset_input_buffer()
                    ser.reset_output_buffer()
                
                time.sleep(0.1)
                
            except Exception as e:
                results.append({
                    "item": f"RS485 TX from {tx_port} at {baud_rate} baud",
                    "result": "FAIL",
                    "detail": f"Transmission error: {str(e)}",
                    "passed": False
                })
    
    finally:
        # Close all serial connections
        for ser in serial_connections.values():
            try:
                ser.close()
            except:
                pass
    
    return results

def test_task():
    detail_results = []
    global global_message
    global_message = []  # Reset global message
    
    # First check if all serial ports exist
    port_check = check_serial_ports_exist()
    detail_results.append(port_check)
    
    if not port_check["passed"]:
        # If ports don't exist, return early
        status = "Failed"
        message = port_check["detail"]
        return status, message, detail_results
    
    # Test RS485 communication for each baud rate
    for baud_rate in BAUD_RATES:
        global_message.append(f"\n--- Testing at {baud_rate} baud ---")
        
        baud_results = test_rs485_at_baud(baud_rate)
        detail_results.extend(baud_results)
        
        # Count pass/fail for this baud rate
        baud_pass = sum(1 for r in baud_results if r["passed"])
        baud_total = len(baud_results)
        global_message.append(f"Baud {baud_rate}: {baud_pass}/{baud_total} tests passed")
    
    # Summary
    num_pass = sum(1 for r in detail_results if r["passed"])
    num_fail = len(detail_results) - num_pass
    all_pass = all(r["passed"] for r in detail_results)
    status = "Passed" if all_pass else "Failed"
    
    summary = f"\nRS485 Test Summary: {num_pass} PASS, {num_fail} FAIL"
    message = "\n".join(global_message) + summary

    return status, message, detail_results



