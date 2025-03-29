import socket
from msvcrt import getch, kbhit
import threading

server_port = 5555
server_ip = "10.0.0.14"
MAX_MSG_LENGTH = 1024
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((server_ip, server_port))


def read_data():
	data = ""
	while True:
		data = client.recv(MAX_MSG_LENGTH).decode()
		if data:
			print(f"server: {data}")
			data = ""


def write_data():
	enter = b'\r'
	f_ = b'\x00'
	data = b""
	while True:
		if kbhit():
			key_pressed = getch()
			if 


def main():
	threading.Thread(target=read_data(), daemon=True).start()
# while True:
# 	name = b""
# 	if kbhit():
# 		name += getch()
# 	client.send(name.encode())
# 	respond = client.recv(len(name))
# 	print(f"bom bom: {respond}")
# client.close()