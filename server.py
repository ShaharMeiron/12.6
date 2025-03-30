import socket
import select


class Client:
	def __init__(self, client_socket, username):
		self.client_socket = client_socket
		self.username = username
		self.is_owner = False
		self.is_muted = False


MAX_MSG_LENGTH = 1024
SERVER_PORT = 5555
SERVER_IP = '0.0.0.0'

def print_client_sockets(client_sockets):
	for c in client_sockets:
		print("\t", c.getpeername())


def broadcast(sender, wlist, data):
	for sock in wlist:
		if sock != sender:
			sock.send(data)


def main():
	print("Setting up server...")
	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_socket.bind((SERVER_IP, SERVER_PORT))
	server_socket.listen()
	print("Listening for clients...")
	client_sockets = []
	messages_to_send = []

	while True:
		rlist, wlist, xlist = select.select([server_socket] + client_sockets, client_sockets, [])
		for current_socket in rlist:
			if current_socket is server_socket:
				connection, client_address = current_socket.accept()
				print("New client joined!", client_address)
				client_sockets.append(connection)
				print_client_sockets(client_sockets)
			else:
				data = current_socket.recv(MAX_MSG_LENGTH).decode()
				if data == "":
					print("Connection closed", )
					client_sockets.remove(current_socket)
					current_socket.close()
					print_client_sockets(client_sockets)
				else:
					messages_to_send.append((current_socket, data))

		for message in messages_to_send:
			current_socket, data = message
			broadcast(sender=current_socket, data=data.encode(), wlist=wlist)
			messages_to_send.remove(message)


if __name__ == '__main__':
	main()
