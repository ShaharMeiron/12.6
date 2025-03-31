import socket
import msvcrt

SERVER_IP = '127.0.0.1'
SERVER_PORT = 5555


def format_message(username: str, command: str, args: list[str]) -> bytes:
	"""Formats message EXACTLY to server protocol"""
	# Encode username with 2-byte length prefix
	username_encoded = username.encode()
	username_part = f"{len(username_encoded):02}{username_encoded.decode()}"

	# Encode command (1 byte)
	command_part = command

	# Encode arguments
	args_count = f"{len(args)}"
	args_part = ""
	for arg in args:
		arg_encoded = arg.encode()
		args_part += f"{len(arg_encoded):04}{arg_encoded.decode()}"

	# Combine all parts
	return f"{username_part}{command_part}{args_count}{args_part}".encode()


def send_login(sock: socket.socket, username: str) -> bool:
	"""Command 0: Login with no arguments"""
	try:
		sock.send(format_message(username, "0", []))
		return True
	except:
		return False


def send_public_message(sock: socket.socket, username: str, message: str) -> bool:
	"""Command 1: Public message (1 argument)"""
	try:
		sock.send(format_message(username, "1", [message]))
		return True
	except:
		return False


def send_private_message(sock: socket.socket, username: str, target: str, message: str) -> bool:
	"""Command 7: Private DM (2 arguments)"""
	try:
		sock.send(format_message(username, "7", [target, message]))
		return True
	except:
		return False


def send_quit(sock: socket.socket, username: str) -> bool:
	"""Command 8: Quit with no arguments"""
	try:
		sock.send(format_message(username, "8", []))
		return True
	except:
		return False


def main():
	sock = socket.socket()
	try:
		sock.connect((SERVER_IP, SERVER_PORT))
	except Exception as e:
		print(f"Connection failed: {e}")
		return

	# Get username (blocking input is fine here)
	username = input("Enter username: ")
	if not username or any(c in username for c in ('@', ' ')):
		print("Invalid username (no @ or spaces)")
		sock.close()
		return

	if not send_login(sock, username):
		print("Login failed")
		sock.close()
		return

	print("\nConnected! Commands:")
	print("/msg [text] - Public message")
	print("/dm [user] [text] - Private message")
	print("/quit - Exit")
	print("> ", end='', flush=True)

	input_buffer = ""
	while True:
		# Handle incoming messages (simplified)
		try:
			data = sock.recv(1024)
			if data:
				print(f"\n{data.decode()}\n> ", end='', flush=True)
		except BlockingIOError:
			pass

		# Non-blocking input handling
		if msvcrt.kbhit():
			char = msvcrt.getch().decode(errors='ignore')

			if char == '\r':  # Enter
				if input_buffer.startswith('/'):
					parts = input_buffer[1:].split(maxsplit=2)
					if parts and parts[0] == "quit":
						send_quit(sock, username)
						break
					elif len(parts) >= 2 and parts[0] == "dm":
						send_private_message(sock, username, parts[1], parts[2] if len(parts) > 2 else "")
					elif parts and parts[0] == "msg":
						send_public_message(sock, username, parts[1] if len(parts) > 1 else "")
				elif input_buffer:
					send_public_message(sock, username, input_buffer)
				input_buffer = ""
				print("\n> ", end='', flush=True)
			elif char == '\x1b':  # ESC
				send_quit(sock, username)
				break
			elif char == '\x08':  # Backspace
				input_buffer = input_buffer[:-1]
				print("\b \b", end='', flush=True)
			else:
				input_buffer += char
				print(char, end='', flush=True)

	sock.close()
	print("\nDisconnected")


if __name__ == '__main__':
	main()