import socket
import logging
from typing import Optional, Tuple, List

SERVER_IP = '127.0.0.1'  # Change to server IP
SERVER_PORT = 5555


def send_message(sock: socket.socket, name: str, command: str, args: List[str]) -> bool:
	"""Send a properly formatted message to the server"""
	try:
		# Encode name with length prefix
		name_encoded = name.encode()
		name_length = f"{len(name_encoded):02d}".encode()

		# Encode command
		command_encoded = command.encode()

		# Encode arguments
		args_count = f"{len(args)}".encode()
		args_encoded = []
		for arg in args:
			arg_encoded = arg.encode()
			args_encoded.append(f"{len(arg_encoded):04d}".encode() + arg_encoded)

		# Construct full message
		message = (
				name_length + name_encoded +
				command_encoded + args_count +
				b"".join(args_encoded)
		)

		sock.sendall(message)
		return True
	except Exception as e:
		logging.error(f"Failed to send message: {e}")
		return False


def receive_response(sock: socket.socket) -> Optional[Tuple[int, bytes]]:
	"""Receive server response with length prefix"""
	try:
		# Read length prefix (first 4 bytes)
		length_bytes = sock.recv(4)
		if not length_bytes:
			return None

		length = int(length_bytes.decode())

		# Read the rest of the message
		data = sock.recv(length)
		while len(data) < length:
			data += sock.recv(length - len(data))

		# Split time and actual message
		time = data[:6].decode()
		message = data[6:]

		return (length, message)
	except Exception as e:
		logging.error(f"Failed to receive response: {e}")
		return None


def handle_user_commands(sock: socket.socket, username: str):
	"""Interactive command handler"""
	print("\nAvailable commands:")
	print("1. Send message to all")
	print("2. Moderate user (add @)")
	print("3. Unmoderate user (remove @)")
	print("4. Kick user")
	print("5. Mute user")
	print("6. Unmute user")
	print("7. Send private message")
	print("8. Quit")

	while True:
		try:
			cmd = input("\nEnter command number (1-8): ")

			if cmd == "1":  # Public message
				message = input("Enter your message: ")
				if send_message(sock, username, "1", [message]):
					print("Message sent!")

			elif cmd == "2" and username.startswith("@"):  # Moderate
				target = input("Enter username to moderate: ")
				if send_message(sock, username, "2", [target]):
					print(f"Moderation request for {target} sent")

			elif cmd == "3" and username.startswith("@"):  # Unmoderate
				target = input("Enter username to unmoderate: ")
				if send_message(sock, username, "3", [target]):
					print(f"Unmoderation request for {target} sent")

			elif cmd == "4" and username.startswith("@"):  # Kick
				target = input("Enter username to kick: ")
				if send_message(sock, username, "4", [target]):
					print(f"Kick request for {target} sent")

			elif cmd == "5" and username.startswith("@"):  # Mute
				target = input("Enter username to mute: ")
				if send_message(sock, username, "5", [target]):
					print(f"Mute request for {target} sent")

			elif cmd == "6" and username.startswith("@"):  # Unmute
				target = input("Enter username to unmute: ")
				if send_message(sock, username, "6", [target]):
					print(f"Unmute request for {target} sent")

			elif cmd == "7":  # Private DM
				target = input("Enter recipient username: ")
				message = input("Enter private message: ")
				if send_message(sock, username, "7", [target, message]):
					print(f"Private message to {target} sent")

			elif cmd == "8":  # Quit
				if send_message(sock, username, "8", []):
					print("Quit request sent")
					return

			else:
				print("Invalid command or insufficient permissions")

			# Check for incoming messages
			response = receive_response(sock)
			if response:
				_, message = response
				print(f"\n[Server] {message.decode()}")

		except KeyboardInterrupt:
			print("\nDisconnecting...")
			if send_message(sock, username, "8", []):  # Graceful quit
				return
			break


def main():
	logging.basicConfig(level=logging.INFO)

	# Connect to server
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try:
		sock.connect((SERVER_IP, SERVER_PORT))
		print(f"Connected to server at {SERVER_IP}:{SERVER_PORT}")
	except Exception as e:
		logging.error(f"Connection failed: {e}")
		return

	# Login
	username = input("Enter your username: ")
	if not send_message(sock, username, "0", []):
		print("Login failed")
		sock.close()
		return

	# Get login response
	response = receive_response(sock)
	if not response or b"successful" not in response[1]:
		print("Login rejected:", response[1].decode() if response else "No response")
		sock.close()
		return

	print("Login successful!")

	# Start command loop
	try:
		handle_user_commands(sock, username)
	finally:
		sock.close()
		print("Disconnected from server")


if __name__ == '__main__':
	main()