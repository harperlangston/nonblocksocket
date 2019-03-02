import socket
import sys
import json
import argparse
import struct
import send_receive as sr

buf_lim = 4096 
kill_signal = 'EOF'

def main():
  """Main driver for client code
  
  Calls start_server(host, port), which opens a socket to
  start receiving streaming traffic.
  
  Args: None
  Returns: None
  
  Usage: client.py [host] [port]
       : Type 'EOF' in client window to kill connection
  
  Raises: Exception if client cannot cannot or cannot be started

  """

  parser = argparse.ArgumentParser(description="Start client")
  parser.add_argument('host', nargs='?', help='host name or IP for client to connect to (default=localhost)', default='localhost')
  parser.add_argument('port', nargs='?', help='host port number client will connect to at host name (default=10001)', default=10001)
  args = parser.parse_args()

  dest_host = args.host
  port = int(args.port)

  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s_addr = (dest_host, port) 
  print >>sys.stderr, 'connecting to %s port %s' % s_addr
  
  local_hostname = socket.gethostname()

  begin_connection_message = {'event_type': 'new_connection', 'source_IP': local_hostname, 'destination_IP': dest_host}
  end_connection_message = {'event_type': 'end_connection', 'source_IP': local_hostname, 'destination_IP': dest_host}

  try:
    sock.connect(s_addr)
  except:
    print("Client connection error to : (" + dest_host + ","  + str(port) + ")" + str(sys.exc_info()))
    sys.exit(-1)

  print("T7ls 
ype 'EOF' to stop")
  sr.send_message(sock, begin_connection_message)
  remain_open = sr.handle_response(sock)

  #if remain_open == True
  client_in = ""
  
  while True:
    client_in = raw_input("CLIENT >> ")
    client_msg = {'event_type': 'message', 'source_IP': local_hostname, 'destination_IP': dest_host, 'message': client_in}
    if (client_in == kill_signal):
      print("Closing connection to "+ dest_host)
      sr.send_message(sock, end_connection_message)
      break
    else: 
      sr.send_message(sock, client_msg)
      remain_open = sr.handle_response(sock)
   
if __name__ == "__main__":
        main()

