import socket

UDP_PORT = 5005  # Phải giống với port bên gửi

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.bind(('', UDP_PORT))  # Lắng nghe trên mọi IP

print(f"Listening for UDP broadcast on port {UDP_PORT}...")

while True:
    data, addr = sock.recvfrom(1024)
    print(f"Received from {addr}: {data.decode()}")