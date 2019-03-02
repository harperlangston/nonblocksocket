import socket
import sys
import json
import collections
import struct
import argparse
import select
import Queue
import random
import send_receive as sr

buf_lim = 4096

def main():
        """Main driver for server code

        Calls start_server(host, port), which opens a socket to
        start receiving streaming traffic.

        Args: None
        Returns: None

        Usage: server.py [host] [port]

        Raises: Exception if server cannot be started

        """

        parser = argparse.ArgumentParser(description="Start server")
        parser.add_argument('host', nargs='?', help='host name or IP for server (default=localhost)', default='localhost')
        parser.add_argument('port', nargs='?', help='host port number server will open at host name (default=10001)', default=10001)
        args = parser.parse_args()

        host = args.host
        port = int(args.port)

        try:
                start_server(host,port)
        except:
                print("Cannot start server : " + str(sys.exc_info()))
                sys.exit(-1)

def start_server(host, port):
        """Starts server on a given host-port combination

        Start a server and open a socket on a given host and port

        Args:
            host: name of host to start server on
            port: port number to use.  If the port is already in use, 
                  (e.g., a server recently started there), start_server
                  attempts to reuse it.

        Returns: None
        
        Raises:
                Exceptions:
                    - setting up socket (including on potential in-use port)
                    - socket bind
                    - socket listen
                    - deque initialization for holding sockets
                    - processing requests
                    - socket close
        """

        # set up an empty list and create the socket
        socket_list = []
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except:
                print("Set Socket Options failed : " + str(sys.exc_info()))
                sys.exit(-1)
        #sock.setblocking(False)
                
        server_address = (host, port)
        print >> sys.stderr, 'starting up on %s port %s' % server_address
        try:
                sock.bind(server_address)
        except:
                print("Socket Bind failure : " + str(sys.exc_info()))
                sys.exit(-1)
        print >> sys.stderr, 'waiting for a connection'

        try:
                sock.listen(10)
        except:
                print("Socket Listen failure : " + str(sys.exc_info()))
                sys.exit(-1)

        # add the server socket and address to the deque
        try:
                socket_list.append(sock)
        except:
                print("queue init failure : " + str(sys.exc_info()))
                sys.exit(-1)

        try:
                process_requests_and_clients(socket_list, (sock, server_address))
        except (KeyboardInterrupt, SystemExit):
                sock.close()
                print("Received Keyboard Interrupt or Premature Exit : " + str(sys.exc_info()))
        except:
                print("failure processing requests : " + str(sys.exc_info()))
                sys.exit(-1)
        
        try:
                sock.close()
        except:
                print("Socket Close failure : " + str(sys.exc_info()))
                sys.exit(-1)

                
def process_requests_and_clients(socket_list, (server_sock, server_addr)):
        """Non-blocking polling of a queue of connections

        Take a deque and loop through it, adding connections as requested
        and processing requests / messages from clients.  We pop from the given deque (de)
        If the top is the server (the first one put in), we check for a new client request,
        push that new connection to the deque and then push the server back in as well

        Args:
            de: A deque where entries are of the form (socket, addr, msg_size)
            (server_sock, server_addr): Tuple containing the server's information

        Returns: None
        
        Raises:
                Exceptions:
                    TODO
        """

        # As long as the deque is non-empty, keep going.  Currently we have no way of stopping the 
        # server with a command, so this should loop forever even if there are
        # no clients since the server is one of them
        server_open = True
        remain_open = True
        msg_queue = {}
        writable_list = []
        
        while socket_list and server_open == True:
                client_open = True
                bytes_left = 0
                message=''

                read_sockets, write_sockets, exceptional_sockets = select.select(socket_list, writable_list, socket_list)
                # pop off the end
                for sock in read_sockets:
                        #if the last socket is the server, check for a new client-connection request
                        if (sock == server_sock):
                                # get the client and push it to list
                                try:
                                        client_connection, client_address = sock.accept()
                                        #client_connection.setblocking(False)
                                        socket_list.append(client_connection)
                                        msg_queue[client_connection] = Queue.Queue()
                                except:
                                        server_open = True
                                        # put the server back in - it does not process messages, so last two fields blank
                        else:
                                # If this is a valid client connection, process any incoming message
                                # Check if it has been sent an EOF or closed.  If not, push it back after
                                # finished.  If it is closed, leave it out.
                                # Need to also check for lost connections
                                # Also working on receiving next message size
                                try:
                                        remain_open = sr.handle_response(sock)
                                except:
                                        print("Error receiving response "+ str(sock.getsockname()))
                                        remain_open = False
                                        server_open = True
                                        
                                #remain_open = True
                                # clean up if needed
                                if remain_open == True:
                                        if sock not in writable_list:
                                                writable_list.append(sock)
                                        try:
                                                remain_open, update_message = calc_upd_msg(socket_list, sock)
                                                msg_queue[sock].put(update_message)
                                        except:
                                                print("Error calculating update: " + str(sys.exc_info()))
                                                traceback.print_exc()
                                                
                                else:
                                        socket_list.remove(sock)
                                        del msg_queue[sock]
                                        if sock in writable_list:
                                                writable_list.remove(sock)
                                        print("Closing connection to "+ str(sock.getsockname()))
                                        try:
                                                sock.close()
                                        except:
                                                print("Socket close failure : " + str(sys.exc_info()))
                                                traceback.print_exc()

                                        
                                                
                for sock in write_sockets:
                        try:
                                next_msg = msg_queue[sock].get_nowait()
                        except Queue.Empty:
                                writable_list.remove(sock)
                        else:
                                sr.send_message(sock, next_msg)

                for sock in exceptional_sockets:
                        socket_list.remove(sock)
                        del msg_queue[sock]
                        if sock in writable_list:
                                writable_list.remove(sock)
                        print("Closing connection to "+ str(sock.getsockname()))
                        try:
                                sock.close()
                        except:
                                print("Socket close failure : " + str(sys.exc_info()))
                                traceback.print_exc()
                                            

        #need to handle a way of closing the server

                
def calc_upd_msg(socket_list, c_sock):
        """Get update message
        
        For a socket, calculate some sort of update.  
        ** This is a generic placeholder for now  **
        ** Use this function to create whatever update message you want **

        Args:
            c_sock: client socket size
            socket_list: list of open sockets (possibly for calculating some global knowledge - placeholder for now)
        
        Returns:
            remain_open:  whether there was an error indicating the socket should be closed
            update_msg:   message to send
        
        Exceptions:
            - socket recv failure

        """
        remain_open = True
        
        # for now this really doesn't do anything - just a placeholder
        # Calculations may go here

        val = random.randint(1,101)
        update_message = str({"event_type": "update_msg", "random_number": val})

        return remain_open, update_message

if __name__ == "__main__":
        main()
