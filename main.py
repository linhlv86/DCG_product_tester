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

def kill_old_gpio_blink():
    try:
        result = subprocess.run(
            ["pgrep", "-f", "gpio_test.py"],
            capture_output=True, text=True
        )
        pids = result.stdout.strip().split('\n')
        for pid in pids:
            if pid and pid.isdigit():
                os.kill(int(pid), signal.SIGKILL)
    except Exception as e:
        print(f"Error killing old gpio_test.py: {e}")

def start_gpio_blink_process():
    kill_old_gpio_blink()
    script_path = "/home/orangepi/product_tester/DCG_product_tester/tasks/bash/gpio_test.py"
    try:
        proc = subprocess.Popen(["python3", script_path])
        print(f"Started blink process, pid={proc.pid}")
    except Exception as e:
        print(f"Blink process error: {e}")

# Chạy ở chế độ nền khi app khởi động
threading.Thread(target=send_udp_broadcast, daemon=True).start()
start_gpio_blink_process()

# Khởi động thread auto pull khi chạy main.py
if __name__ == "__main__":
    threading.Thread(target=send_udp_broadcast, daemon=True).start()
    subprocess.run(["pkill", "-f", "gpio_test.py"])
    start_gpio_blink_process()
    threading.Thread(target=auto_git_pull, daemon=True).start()
    print("Starting Flask-SocketIO server...")
    try:
        socketio.run(app, debug=True, host='0.0.0.0', port=80)
    finally:
        pass  # Không cần cleanup GPIO