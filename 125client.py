import socket
from msvcrt import getch, kbhit
import select

# Server details
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5555
MAX_MSG_LENGTH = 1024

# Create client socket
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SERVER_IP, SERVER_PORT))

print("Connected to the chat server. Type and press Enter to send messages.")

buffer = ""  # Stores user input before sending

while True:
    # Use select to check if there's incoming data from the server
    rlist, _, _ = select.select([client], [], [], 0)  # Non-blocking check

    if client in rlist:
        try:
            data = client.recv(MAX_MSG_LENGTH).decode()
            if data:
                print(f"server: {data}", end="\n")  # Print message from the server
        except ConnectionError:
            print("Disconnected from the server.")
            break

    # Check if the user pressed a key (non-blocking)
    if kbhit():
        ch = getch()

        if ch == b'\r':  # Enter key: Send message
            if buffer:
                client.send(buffer.encode())
                buffer = ""  # Clear input buffer
            print("\n> ", end="", flush=True)  # Move to new input line

        elif ch == b'\x08':  # Backspace key
            buffer = buffer[:-1]  # Remove last character
            print("\b \b", end="", flush=True)  # Remove from screen

        elif ch == b'\x00':  # Special function key (e.g., F2)
            print("\nExiting chat.")
            break

        else:  # Regular character input
            buffer += ch.decode('utf-8')
            print(ch.decode('utf-8'), end="", flush=True)

client.close()
