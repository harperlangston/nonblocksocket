# nonblocksocket
Non-blocking multi-connection client-server socket in Python.  Uses selects and msg buffer queues for client &lt;-> server communication and connections.

Usage:
1. Start the server:
   server.py [host] [port]
2. Start a client (in another window or another host if desired):
   client.py [host] [port]
3.  Add more clients if desired.
4.  Type in client window and watch it go to server, using non-blocking round robin selects
5.  Have fun
