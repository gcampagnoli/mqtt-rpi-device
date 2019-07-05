#!/usr/bin/python3
import json
import socket
import sys
import pickle



address = 'localhost'
port = 10000

def func_get_stato():
   return 1

def func_open():
   return 0

def func_close():
   return 1



data_client_info = {"name_int":"interruttore_serranda","name_ext":"interruttore della serranda","offered_function": {"stato":"func_get_stato","apri":"func_open","close":"func_close"}}

func_client_map = {}

func_client_map[data_client_info["offered_function"]["stato"]] = func_get_stato
func_client_map[data_client_info["offered_function"]["apri"]] = func_open
func_client_map[data_client_info["offered_function"]["close"]] = func_close


#inizializzazione

sock = socket.socket()
sock.connect((address, port))
msg = pickle.dumps(data_client_info)
sock.send(msg)
sock.close()
#registrazione dei servizi



