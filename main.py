# main.py

import eventlet
eventlet.monkey_patch()
# Import ứng dụng 'app' và 'socketio' từ file app.py
from app import app, socketio

from flask import Flask
import socket
import threading
import time

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

# Chạy ở chế độ nền khi app khởi động
threading.Thread(target=send_udp_broadcast, daemon=True).start()

# Đoạn mã này chỉ chạy khi bạn thực thi file main.py trực tiếp
if __name__ == '__main__':
    print("Starting Flask-SocketIO server...")
    # Chạy ứng dụng web server sử dụng SocketIO
    # - debug=True: Chế độ debug, tự động reload khi code thay đổi (chỉ dùng khi phát triển)
    # - host='0.0.0.0': Cho phép truy cập từ mọi địa chỉ IP (cần thiết khi chạy trên Orange Pi và truy cập từ máy khác)
    # - port=5000: Cổng mặc định cho ứng dụng web
    # - allow_unsafe_werkzeug=True: Cần thiết khi dùng debug=True với Flask-SocketIO (cho môi trường dev)
    socketio.run(app, debug=True, host='0.0.0.0', port=80)