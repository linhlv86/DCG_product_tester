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
import signal

# Bỏ hết tác vụ GPIO
# Xóa toàn bộ phần import, biến, hàm và thread liên quan đến GPIO

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

def start_gpio_blink_process():
    # Sử dụng đường dẫn tương đối từ thư mục hiện tại
    current_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(current_dir, "tasks", "bash", "gpio_test.py")
    
    # Kiểm tra xem file có tồn tại không trước khi chạy
    if not os.path.exists(script_path):
        print(f"GPIO script not found at: {script_path}")
        return
        
    try:
        proc = subprocess.Popen(["python3", script_path])
        print(f"Started blink process, pid={proc.pid}")
    except Exception as e:
        print(f"Blink process error: {e}")

# Chạy ở chế độ nền khi app khởi động
threading.Thread(target=send_udp_broadcast, daemon=True).start()
start_gpio_blink_process()

# Khởi động ứng dụng
if __name__ == "__main__":
    threading.Thread(target=send_udp_broadcast, daemon=True).start()
    subprocess.run(["/usr/bin/pkill", "-f", "gpio_test.py"])
    start_gpio_blink_process()
    print("Starting Flask-SocketIO server...")
    try:
        socketio.run(app, debug=True, host='0.0.0.0', port=80)
    finally:
        pass