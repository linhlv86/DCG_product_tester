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
            old_commit = subprocess.check_output([GIT, 'rev-parse', 'HEAD'], cwd=project_dir, text=True).strip()
            subprocess.run([GIT, 'fetch', 'origin'], cwd=project_dir)
            new_commit = subprocess.check_output([GIT, 'rev-parse', 'origin/main'], cwd=project_dir, text=True).strip()
            if old_commit != new_commit:
                print("New version detect,automatic pull và restart...")
                subprocess.run([GIT, 'stash'], cwd=project_dir)
                subprocess.run([GIT, 'pull', 'origin', 'main'], cwd=project_dir)
                # subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], cwd=project_dir)
                subprocess.run([GIT, 'stash', 'pop'], cwd=project_dir)
                # Restart lại process
                # os.execv(sys.executable, [sys.executable] + sys.argv)
            # else:
            #     print("Không có thay đổi mới.")
        except Exception as e:
            print("Git error:", e)
        time.sleep(interval)

# Chạy ở chế độ nền khi app khởi động
threading.Thread(target=send_udp_broadcast, daemon=True).start()

# Khởi động thread auto pull khi chạy main.py
if __name__ == "__main__":
    threading.Thread(target=auto_git_pull, daemon=True).start()
    print("Starting Flask-SocketIO server...")
    # Chạy ứng dụng web server sử dụng SocketIO
    # - debug=True: Chế độ debug, tự động reload khi code thay đổi (chỉ dùng khi phát triển)
    # - host='0.0.0.0': Cho phép truy cập từ mọi địa chỉ IP (cần thiết khi chạy trên Orange Pi và truy cập từ máy khác)
    # - port=5000: Cổng mặc định cho ứng dụng web
    # - allow_unsafe_werkzeug=True: Cần thiết khi dùng debug=True với Flask-SocketIO (cho môi trường dev)
    socketio.run(app, debug=True, host='0.0.0.0', port=80)