# tasks/task_example_gpio.py
import time
import subprocess
import json
import re
import glob
import serial
import threading

# Mô tả của task này, sẽ hiển thị trên giao diện người dùng
DESCRIPTION = "RS485 Serial Communication Test"

global_message = []

# Configuration constants
GPIO_MODE = [129, 135, 122, 127]
SERIAL_PORTS = [f"/dev/ttyACM{i}" for i in range(4)]
BAUD_RATES = [1200, 9600, 38400, 115200]

def set_gpio_mode(port, mode):
    """Set GPIO mode: 1 for RS422, 0 for RS485"""
    try:
        # Implement GPIO mode setting logic here
        # This depends on your hardware interface
        pass
    except Exception as e:
        return False, str(e)
    return True, ""

def clear_serial_buffer(ser):
    """Clear serial receive buffer"""
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.1)
    except Exception as e:
        return False

def test_rs485_communication(baud_rate):
    """Test RS485 communication at specified baud rate"""
    detail_results = []
    
    # Open all serial ports
    serial_connections = {}
    try:
        for port in SERIAL_PORTS:
            ser = serial.Serial(port, baud_rate, timeout=1)
            serial_connections[port] = ser
    except Exception as e:
        return [{
            "item": f"Open serial ports at {baud_rate} baud",
            "result": "FAIL",
            "detail": f"Failed to open serial ports: {str(e)}",
            "passed": False
        }]
    
    try:
        # Set all GPIO modes to 0 (RS485)
        for i, port in enumerate(SERIAL_PORTS):
            success, error = set_gpio_mode(GPIO_MODE[i], 0)
            if not success:
                detail_results.append({
                    "item": f"Set GPIO mode for {port}",
                    "result": "FAIL", 
                    "detail": f"Failed to set GPIO mode: {error}",
                    "passed": False
                })
                continue
        
        # Clear all buffers
        for ser in serial_connections.values():
            clear_serial_buffer(ser)
        
        # Test each port as transmitter
        for tx_index, tx_port in enumerate(SERIAL_PORTS):
            test_data = f"TEST_DATA_{tx_index}_{baud_rate}".encode('utf-8')
            
            # Send test data
            try:
                serial_connections[tx_port].write(test_data)
                time.sleep(0.2)  # Wait for transmission
                
                # Check if other ports received the data
                received_data = {}
                all_received = True
                
                for rx_index, rx_port in enumerate(SERIAL_PORTS):
                    if rx_index != tx_index:  # Skip transmitter port
                        try:
                            data = serial_connections[rx_port].read_all()
                            received_data[rx_port] = data
                            
                            if data != test_data:
                                all_received = False
                        except Exception as e:
                            received_data[rx_port] = f"Error: {str(e)}"
                            all_received = False
                
                # Record result
                if all_received:
                    detail_results.append({
                        "item": f"RS485 transmission from {tx_port} at {baud_rate} baud",
                        "result": "PASS",
                        "detail": f"Data '{test_data.decode()}' successfully received by all other ports",
                        "passed": True
                    })
                else:
                    failed_ports = [port for port, data in received_data.items() if data != test_data]
                    detail_results.append({
                        "item": f"RS485 transmission from {tx_port} at {baud_rate} baud", 
                        "result": "FAIL",
                        "detail": f"Data not received correctly by ports: {failed_ports}. Received: {received_data}",
                        "passed": False
                    })
                    
            except Exception as e:
                detail_results.append({
                    "item": f"RS485 transmission from {tx_port} at {baud_rate} baud",
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
    
    return detail_results

def test_task():
    detail_results = []
    global_message = []

    # First check if devices exist
    required_devices = [f"/dev/ttyACM{i}" for i in range(4)]
    devices = glob.glob('/dev/ttyACM*')
    
    found_all = all(dev in devices for dev in required_devices)
    if not found_all:
        missing = [dev for dev in required_devices if dev not in devices]
        detail = f"Missing devices: {', '.join(missing)}\nUSB serial devices found:\n" + "\n".join(devices)
        detail_results.append({
            "item": "Check USB serial devices",
            "result": "FAIL",
            "detail": detail,
            "passed": False
        })
        
        # Return early if devices not found
        status = "Failed"
        message = detail
        return status, message, detail_results
    
    # Test RS485 communication for each baud rate
    for baud_rate in BAUD_RATES:
        rs485_results = test_rs485_communication(baud_rate)
        detail_results.extend(rs485_results)
        
        # Log successful baud rate tests
        passed_tests = [r for r in rs485_results if r["passed"]]
        if passed_tests:
            global_message.append(f"RS485 tests at {baud_rate} baud: {len(passed_tests)} passed")
    
    # Summary
    num_pass = sum(1 for r in detail_results if r["passed"])
    num_fail = len(detail_results) - num_pass
    all_pass = all(r["passed"] for r in detail_results)
    status = "Passed" if all_pass else "Failed"
    
    summary_msg = f"RS485 Communication Test Summary: {num_pass} PASS, {num_fail} FAIL"
    if global_message:
        message = "\n".join(global_message) + "\n" + summary_msg
    else:
        message = summary_msg

    return status, message, detail_results




