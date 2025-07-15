# main.py

import eventlet
eventlet.monkey_patch()
# Import ứng dụng 'app' và 'socketio' từ file app.py
from app import app, socketio

from flask import Flask
import socket
import threading
import time
import subprocess
import os
import sys

# Thêm import để điều khiển GPIO
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

def gpio_control_task():
    """Task điều khiển GPIO lần lượt: chỉ 1 GPIO ON tại một thời điểm"""
    gpio_pins = [133, 132, 134, 125]
    
    if not GPIO_AVAILABLE:
        return
    
    try:
        # Thiết lập mode BCM
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Khởi tạo các GPIO pin như output
        for pin in gpio_pins:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        
        while True:
            for pin in gpio_pins:
                # Tắt tất cả GPIO trước
                GPIO.output(gpio_pins, GPIO.LOW)
                
                # Bật chỉ GPIO hiện tại
                GPIO.output(pin, GPIO.HIGH)
                time.sleep(0.3)  # 300ms ON
                
                # Tắt GPIO hiện tại
                GPIO.output(pin, GPIO.LOW)
                time.sleep(1.0)  # 1000ms OFF
                
    except Exception as e:
        print(f"GPIO error: {e}")
    finally:
        if GPIO_AVAILABLE:
            GPIO.cleanup()

def send_udp_broadcast(port=5005, interval=1):
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_socket.settimeout(0.2)

    # Lấy IP của máy
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    message = f"IP:{local_ip}".encode()

    while True:
        udp_socket.sendto(message, ('<broadcast>', port))
        time.sleep(interval)

def auto_git_pull(interval=10):
    project_dir = os.path.dirname(os.path.abspath(__file__))
    while True:
        try:
            GIT = '/usr/bin/git'
            
            # Fetch remote changes
            fetch_result = subprocess.run([GIT, 'fetch', 'origin'], 
                                        cwd=project_dir, capture_output=True, text=True)
            
            if fetch_result.returncode == 0:
                # Reset về remote version (luôn luôn, không kiểm tra diff)
                reset_result = subprocess.run([GIT, 'reset', '--hard', 'origin/main'], 
                                            cwd=project_dir, capture_output=True, text=True)
                
                if reset_result.returncode == 0:
                    print("Git auto-sync: OK")
                else:
                    print(f"Reset thất bại: {reset_result.stderr}")
            else:
                print(f"Fetch thất bại: {fetch_result.stderr}")
                
        except Exception as e:
            print(f"Git error: {e}")
        time.sleep(interval)

# Chạy ở chế độ nền khi app khởi động
threading.Thread(target=send_udp_broadcast, daemon=True).start()

# Khởi động GPIO control thread
threading.Thread(target=gpio_control_task, daemon=True).start()

# Khởi động thread auto pull khi chạy main.py
if __name__ == "__main__":
    threading.Thread(target=auto_git_pull, daemon=True).start()
    print("Starting Flask-SocketIO server...")
    try:
        socketio.run(app, debug=True, host='0.0.0.0', port=80)
    finally:
        # Cleanup GPIO khi thoát
        if GPIO_AVAILABLE:
            GPIO.cleanup()