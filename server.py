import socket
import select
import logging
from typing import Optional, List, Tuple, Dict
from datetime import datetime

SERVER_PORT = 5555
SERVER_IP = '0.0.0.0'

# Protocol constants
NAME_LENGTH_BYTES = 2
COMMAND_NUM_BYTES = 1
ARGS_COUNT_BYTES = 1
ARG_LENGTH_BYTES = 4


def get_current_time():
	return datetime.now().strftime("%H:%M ")


def print_client_sockets(client_sockets):
	for c in client_sockets:
		print("\t", c.getpeername())


def format_message(data: bytes) -> bytes:
	"""Helper to prepend time and length to messages"""
	timed_data = get_current_time().encode() + data
	length = str(len(timed_data)).encode()
	return length + timed_data


def unicast(sock, data):
	sock.send(format_message(data))


def multicast(sockets, data):
	formatted = format_message(data)
	for sock in sockets:
		sock.send(formatted)


def broadcast(wlist, data, sender=None):
	formatted = format_message(data)
	for sock in wlist:
		if sock != sender:
			sock.send(formatted)


class MessageParseError(Exception):
	pass


def recv_exact(sock, n: int) -> Optional[bytes]:
	"""Receive exactly n bytes from the socket or return None if connection is closed."""
	data = bytearray()
	while len(data) < n:
		remaining = n - len(data)
		try:
			packet = sock.recv(remaining)
			if not packet:  # Connection closed
				return None
			data.extend(packet)
		except ConnectionError:
			return None
	return bytes(data)


def _read_name(sock) -> str:
	"""Read and validate the name field from the socket."""
	name_length_bytes = recv_exact(sock, NAME_LENGTH_BYTES)
	if not name_length_bytes:
		raise MessageParseError("Connection closed while reading name length")

	try:
		name_length = int(name_length_bytes.decode())
	except ValueError:
		raise MessageParseError(f"Invalid name length format: {name_length_bytes}")

	name_bytes = recv_exact(sock, name_length)
	if not name_bytes:
		raise MessageParseError("Connection closed while reading name")

	name = name_bytes.decode()
	if any(c in name for c in ('@', ' ')):
		raise MessageParseError(f"Invalid characters in name: {name}")

	return name


def _read_command_num(sock) -> str:
	"""Read and validate the command number from the socket."""
	command_num_bytes = recv_exact(sock, COMMAND_NUM_BYTES)
	if not command_num_bytes:
		raise MessageParseError("Connection closed while reading command number")

	try:
		return command_num_bytes.decode()
	except ValueError:
		raise MessageParseError(f"Invalid command number format: {command_num_bytes}")


def _read_args(sock) -> List[str]:
	"""Read and validate the arguments from the socket."""
	args_count_bytes = recv_exact(sock, ARGS_COUNT_BYTES)
	if not args_count_bytes:
		raise MessageParseError("Connection closed while reading args count")

	try:
		args_count = int(args_count_bytes.decode())
	except ValueError:
		raise MessageParseError(f"Invalid args count format: {args_count_bytes}")

	args = []
	for _ in range(args_count):
		arg_length_bytes = recv_exact(sock, ARG_LENGTH_BYTES)
		if not arg_length_bytes:
			raise MessageParseError("Connection closed while reading arg length")

		try:
			arg_length = int(arg_length_bytes.decode())
		except ValueError:
			raise MessageParseError(f"Invalid arg length format: {arg_length_bytes}")

		arg_bytes = recv_exact(sock, arg_length)
		if not arg_bytes:
			raise MessageParseError("Connection closed while reading argument")

		args.append(arg_bytes.decode())

	return args


def parse_message(receiving_socket) -> Tuple[str, str, List[str]]:
	"""
	Parse a complete message from the socket with format:
	[2-byte name len][name][1-byte cmd][1-byte args count][4-byte arg len][arg]...
	"""
	try:
		name = _read_name(receiving_socket)
		command_num = _read_command_num(receiving_socket)
		args = _read_args(receiving_socket)
		return name, command_num, args
	except UnicodeDecodeError as e:
		raise MessageParseError(f"Invalid encoding in message: {str(e)}")


def main():
	logging.info("Starting server...")
	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_socket.bind((SERVER_IP, SERVER_PORT))
	server_socket.listen()

	client_sockets = []
	users: Dict[str, socket.socket] = {}
	first_login = True

	while True:
		rlist, wlist, _ = select.select([server_socket] + client_sockets, client_sockets, [])

		# PHASE 1: Read all messages
		commands_to_process = []
		for sock in rlist:
			if sock is server_socket:
				connection, client_address = sock.accept()
				client_sockets.append(connection)
				logging.info(f"New connection from {client_address}")
				continue

			try:
				name, command, args = parse_message(sock)
				if name and command:
					commands_to_process.append((sock, name, command, args))
			except (MessageParseError, ConnectionError) as e:
				logging.error(f"Connection error: {e}")
				if sock in client_sockets:
					client_sockets.remove(sock)
				sock.close()
				# Remove from users if they were logged in
				for username, user_sock in list(users.items()):
					if user_sock == sock:
						users.pop(username)
						broadcast(wlist, f"{username} has disconnected".encode())

		# PHASE 2: Process and respond
		for sock, name, command, args in commands_to_process:
			try:
				# 0 - Login
				if command == "0":
					if any(variant in users for variant in {name, f"@{name}", f"{name} ", f"@{name} "}):
						unicast(sock, b"username is taken")
					else:
						if first_login:
							name = "@" + name
							first_login = False
							logging.info(f"First user {name} became moderator")
						users[name] = sock
						unicast(sock, b"login successful")
						broadcast(wlist, f"{name} has joined".encode(), sender=sock)

				# 1 - Public message
				elif command == "1":
					if f"{name} " in users:  # Check if muted
						unicast(sock, b"you are currently muted")
					elif name.startswith("@"):  # Moderator message
						broadcast(wlist, f"[MOD] {name}: {args[0]}".encode(), sender=sock)
					else:
						broadcast(wlist, f"{name}: {args[0]}".encode(), sender=sock)

				# 2 - Moderate (add @ prefix)
				elif command == "2" and name.startswith("@"):
					target = args[0]
					if target in users and not target.startswith("@"):
						users[f"@{target}"] = users.pop(target)
						broadcast(wlist, f"{target} is now a moderator".encode())
					else:
						unicast(sock, b"invalid target for moderation")

				# 3 - Unmoderate (remove @ prefix)
				elif command == "3" and name.startswith("@"):
					target = args[0]
					if f"@{target}" in users:
						users[target] = users.pop(f"@{target}")
						broadcast(wlist, f"{target} is no longer a moderator".encode())
					else:
						unicast(sock, b"target is not a moderator")

				# 4 - Kick
				elif command == "4" and name.startswith("@"):
					target = args[0]
					if target in users and not target.startswith("@"):  # Can't kick other mods
						users[target].close()
						client_sockets.remove(users[target])
						users.pop(target)
						broadcast(wlist, f"{target} has been kicked".encode())
					else:
						unicast(sock, b"invalid kick target")

				# 5 - Mute (add space suffix)
				elif command == "5" and name.startswith("@"):
					target = args[0]
					if target in users and not target.endswith(" ") and not target.startswith("@"):
						users[f"{target} "] = users.pop(target)
						broadcast(wlist, f"{target} has been muted".encode())
					else:
						unicast(sock, b"invalid mute target")

				# 6 - Unmute (remove space suffix)
				elif command == "6" and name.startswith("@"):
					target = args[0]
					if f"{target} " in users:
						users[target] = users.pop(f"{target} ")
						broadcast(wlist, f"{target} has been unmuted".encode())
					else:
						unicast(sock, b"target is not muted")

				# 7 - Private DM
				elif command == "7":
					target = args[0]
					message = args[1]
					if target in users:
						unicast(users[target], f"[DM from {name}] {message}".encode())
						unicast(sock, f"[DM to {target}] {message}".encode())
					else:
						unicast(sock, b"user not found")

				# 8 - Quit
				elif command == "8":
					if name in users:
						users.pop(name)
					sock.close()
					client_sockets.remove(sock)
					broadcast(wlist, f"{name} has left".encode())

			except (ConnectionError, OSError) as e:
				logging.error(f"Error processing command: {e}")
				if sock in client_sockets:
					client_sockets.remove(sock)
				sock.close()
				if name in users:
					users.pop(name)
					broadcast(wlist, f"{name} has disconnected".encode())


if __name__ == '__main__':
	logging.basicConfig(
		filename="server.log",
		filemode='w',
		level=logging.INFO,
		format='%(asctime)s - %(levelname)s - %(message)s'
	)
	main()