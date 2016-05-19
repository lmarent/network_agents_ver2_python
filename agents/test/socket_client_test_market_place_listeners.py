import socket
import sys
sys.path.append("/home/luis/network_agents_ver2_python/agents/foundation")
from Message import Message


sys.path.insert(1,'/home/luis/network_agents_ver2_python/agents/foundation')

HOST, PORT = "192.168.2.12", 5555 # market server port
HOST2, PORT2 = "192.168.2.12", 5555 # market server port

message1= Message('')
message1.setMethod(Message.CONNECT)
strProv = "Provider3"
serviceId = "1"
message1.setParameter("Agent", strProv)

# Create a socket (SOCK_STREAM means a TCP socket)
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    # Connect to server and send data
    sock.connect((HOST, PORT))
    sock.sendall(message1.__str__())

    received = ""
    received = sock.recv(4096)
    recMsg = Message(received)
    if (recMsg.isMessageStatusOk()):
        strProv = "Provider4"
        message1= Message('')
        message1.setMethod(Message.CONNECT)
        message1.setParameter("Agent", strProv)
        sock2.connect((HOST, PORT))
        sock2.sendall(message1.__str__())
            
finally:
    sock.shutdown(socket.SHUT_WR)
    sock.close()
    sock2.shutdown(socket.SHUT_WR)
    sock2.close()
