# main.py

import eventlet
eventlet.monkey_patch()
# Import ứng dụng 'app' và 'socketio' từ file app.py
from app import app, socketio

from flask import Flask

# Đoạn mã này chỉ chạy khi bạn thực thi file main.py trực tiếp
if __name__ == '__main__':
    print("Starting Flask-SocketIO server...")
    # Chạy ứng dụng web server sử dụng SocketIO
    # - debug=True: Chế độ debug, tự động reload khi code thay đổi (chỉ dùng khi phát triển)
    # - host='0.0.0.0': Cho phép truy cập từ mọi địa chỉ IP (cần thiết khi chạy trên Orange Pi và truy cập từ máy khác)
    # - port=5000: Cổng mặc định cho ứng dụng web
    # - allow_unsafe_werkzeug=True: Cần thiết khi dùng debug=True với Flask-SocketIO (cho môi trường dev)
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)