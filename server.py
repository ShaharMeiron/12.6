import socket
from typing import Any
import select
import logging


def close_socket(client_sockets, current_socket):
    print("Connection closed", )
    client_sockets.remove(current_socket)
    current_socket.close()
    print_client_sockets(client_sockets)


def print_client_sockets(client_sockets):
    for c in client_sockets:
        print("\t", c.getpeername())


def recv_exact(sock, n):
    """Receive exactly n bytes or return None if connection is closed."""
    data = b""
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None  # Connection closed
        data += packet
    return data


def parse_message(current_socket):
    name = None
    command_num = None
    args = []

    name_length_bytes = recv_exact(current_socket, 2)
    if not name_length_bytes:
        return False, name, command_num, args
    name_length_str = name_length_bytes.decode()
    if not name_length_str.isdigit():
        return False, name, command_num, args
    name_length = int(name_length_str)

    name_bytes = recv_exact(current_socket, name_length)
    if not name_bytes:
        return False, name, command_num, args
    name = name_bytes.decode()
    logging.debug(F"received name: {name}")

    command_num_bytes = current_socket.recv(1)
    if not command_num_bytes:
        return False, name, command_num, args
    command_num_str = command_num_bytes.decode()
    if not command_num_str.isdigit():
        return False, name, command_num, args
    command_num = int(command_num_str)
    logging.debug(F"command num: {command_num}")

    # Read number of arguments (1 byte)
    args_num_bytes = current_socket.recv(1)
    if not args_num_bytes:
        return False, name, command_num, args
    args_num_str = args_num_bytes.decode()
    if not args_num_str.isdigit():
        return False, name, command_num, args
    args_num = int(args_num_str)

    for _ in range(args_num):
        arg_length_bytes = recv_exact(current_socket, 4)
        if not arg_length_bytes:
            return False, name, command_num, args
        arg_length_str = arg_length_bytes.decode()
        if not arg_length_str.isdigit():
            return False, name, command_num, args
        arg_length = int(arg_length_str)

        # Read argument
        arg_bytes = recv_exact(current_socket, arg_length)
        if not arg_bytes:
            return False, name, command_num, args
        args.append(arg_bytes.decode())
    logging.debug(F"args: {args}")

    return True, name, command_num, args


def get_server_socket(addr):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(addr)
    server_socket.listen()
    logging.info("Listening for clients...")
    return server_socket


def main(addr=("0.0.0.0", 5555)):
    server_socket = get_server_socket(addr)
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
                status, name, command_num, args = parse_message(current_socket)
                # need to add function for each command num
                # messages_to_send.append((current_socket, data))

        for message in messages_to_send:
            current_socket, data = message
            if current_socket in wlist:
                current_socket.send(data.encode())
                messages_to_send.remove(message)


if __name__ == '__main__':
    logging.basicConfig(filemode='w', filename="server.log", level=logging.INFO)
    main()
