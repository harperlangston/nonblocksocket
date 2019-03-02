import socket
import struct
import json
import sys

kill_signal = 'end_connection'

def recv_header_size(sock):
        """Get incoming message size
        
        Get a 4-byte buffer to indicate incoming messages

        Args:
            sock: socket

        Returns:
            remain_open:  whether there was an error indicating the socket should be closed
            bytesSize:        number of bytes in output after unpacking
        
        Exceptions:
             - struct.unpack failure
        """
        remain_open = True
        byte_size = 0

        try:
                message_size = sock.recv(4)
        except:
                remain_open = False

        if remain_open:
                try:
                        byte_size = int(struct.unpack("I", message_size)[0])
                except:
                        print("Unpack failure : " + str(sys.exc_info()))
                        # likely dead, so close it
                        byte_size = 0
                        remain_open = False

        return remain_open, byte_size

def recv_message(sock, msg_size):
        """Get incoming message chunk
        
        From a msg_size (from previous call to recv_header_size), get a message chunk

        Args:
            sock:   socket
            msg_size: expected message size

        Returns:
            remain_open:  whether there was an error indicating the socket should be closed
            msg:          message read (of size buf_len)
            buflen:       number of bytes read (less than or equal to msg_size)
        
        Exceptions:
            - socket recv failure

        """
        msg = ''
        buf_len = 0
        remain_open = True

        try:
                msg = sock.recv(msg_size)       
                buf_len = sys.getsizeof(msg)
        except:
                print("Recv error : " + str(sys.exc_info()))
                #likely dead, so close it
                remain_open = False

        return remain_open, msg, buf_len


def send_message(sock, message, prefix = ''):
  """Send message to a socket.  Optional prefix
  
    
  Args: 
     sock:     socket / connection
     message:  message to send
     prefix:   optional prefix

  Returns: None
    
  Raises: Exception on sendall 

  """
  try:
          print >>sys.stderr, 'sending "%s"' % message
          send_message = json.dumps(message)
          sock.sendall(struct.pack('I', sys.getsizeof(send_message)))
          sock.sendall(send_message)
  except:
          print("Cannot send message : " + str(sys.exc_info()))



def handle_response(sock):
        """Function / response during polling

        For each connection, this function listens
        for new messages (including the end of a connection) and processes them.

        Args:
            sock:    socket / connection

        Returns:
            remain_open: True / False flag whether to keep connection open (if EOF received)

        Raises: multiple exceptions:
            - socket receive fail
            - socket close fail (if EOF received)
            - socket send fail

        """
        remain_open = True
        message = ''
        remain_open, bytes_left = recv_header_size(sock)
                
        if remain_open:
                while True:
                        remain_open, bytes_left, message = process_message(sock, bytes_left, message)
                        if bytes_left == 0 or remain_open == False:
                                break

                # print out the final message if we've received all of it
                if remain_open == True and bytes_left == 0 and message != '':
                        remain_open, bytes_left, message = process_message(sock, bytes_left, message)
                        if (not(bytes_left == 0 and message == '')):
                            print("Error printing entire message.  Verify correctness")
                        
        return remain_open

def process_message(sock, msg_size, msg):
        """Function / response during polling

        For socket connection, this function listens
        for new messages (including the end of a connection) and processes them.

        Args:
            sock:      socket / connection
            msg_size:  size of the message to try to read.  If this is 0, it means
                       that either it is time to read a new 4-byte header or
                       time to print out the message.  If it is nonzero, we try to read
                       that amount and decrement how much is actually read.
            message:   message string that has been read thus far.  If this is empty, it 
                       means there is nothing that has been read so far.  If the msg_size
                       is nonzero, attempt to read msg_size (or less) and add it on to 
                       the message string

        Returns:
            remain_open: True / False flag whether to keep connection open (if EOF received)
            bytes_left:   How many bytes are left to read into message.  This value will be
                         less than or equal to the msg_size input.  If remain_open is False,
                         bytes_left is set to zero.
            message:     This is the update message.  If anything is read/ recv'ed after the 
                         4-byte read, it is tacked on to the message string and sent back.
                         If remain_open is False, message is set to a blank string.

        Raises: multiple exceptions:
            - socket receive fail
            - socket close fail (if EOF received)
            - socket send fail

        """
        remain_open = True
        message = msg
        bytes_left = msg_size

        # if the remaining message size is zero, it may be time to print
        # or it may be time to get a new message length

        if msg_size == 0:
                if message != '':
                        stripped_msg = json.dumps(message.decode("utf8").rstrip())
                        if stripped_msg:
                                if kill_signal in stripped_msg:
                                        print sock.getsockname(), ": " + json.loads(stripped_msg)
                                        remain_open = False
                                
                                else :
                                        try:
                                                print  sock.getsockname(), ": " + str(json.loads(stripped_msg))
                                        except:
                                                print("failure processing requests : " + str(sys.exc_info()))
                                        remain_open = True
                                        
                        #clear the message and bytesleft size if we printed or closed
                        message = ''
                        bytes_left = 0
                        
        else:
                remain_open, msg, buf_len = recv_message(sock, bytes_left)
                if remain_open == False:
                        bytes_left = 0
                        message = ''
                else:
                        message += msg
                        bytes_left -= buf_len
                
	return remain_open, bytes_left, message



