#!/usr/bin/python3
import socket
import sys
import pickle
import threading


def client_thread(conn):

    data = conn.recv(4096)
    data_variable = pickle.loads(data)
    conn.close()
    print(data_variable)


# Create a TCP/IP socket
threads = []
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Bind the socket to the port
server_address = ('', 10000)
print( 'starting up on %s port %s' % server_address)
sock.bind(server_address)
# Listen for incoming connections
sock.listen(255)
print("Listening...")

while True:
    # Wait for a connection
    print('waiting for a connection')
    connection, client_address = sock.accept()
    print("[-] Connected to " + client_address[0] + ":" + str(client_address[1]))
    thr = threading.Thread(target=client_thread, args=(connection,))
    threads.append(thr)
    thr.start()


s.close()


