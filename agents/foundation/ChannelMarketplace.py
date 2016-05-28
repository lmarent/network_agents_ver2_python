import agent_properties
import socket
from FoundationException import FoundationException
from Message import Message

class Channel_Marketplace(object):
    '''
    The Channel_Marketplace class defines the methods for creating 
    the socket communication between the marketplace and the simulation
    environment (demand server). It includes the methods get and 
    send message, as well as closing the socket.
    '''
    def __init__(self, address, port):    
        # Creates the socket for marketplace
        self._streamStaged = ''
        #HOST = '192.168.1.129'    # The remote host
        HOST = address
        #PORT = 5555           # The same port as used by the server
        PORT = port
        try:
            self._s_mkt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            err = self._s_mkt.connect_ex((HOST, PORT))
            if (err > 0):
                raise FoundationException("Error: the Market Place Server is not running")
        except socket.error, msg:
            raise FoundationException('Failed to create socket. Error code: ' \
                                           + str(msg[0]) + ' , Error message : ' + msg[1])
    
    '''
    This method is responsible for getting messages from 
    the socket.
    '''
    def getMessage(self):
        foundIdx = self._streamStaged.find("Method")
        if (foundIdx == 0):
            foundIdx2 = self._streamStaged.find("Method", foundIdx + 1)
            if (foundIdx2 != -1):
                message = Message(self._streamStaged[foundIdx : foundIdx2 - 1])
                # Even that the message could have errors is complete
                self._streamStaged = self._streamStaged[foundIdx2 : ]
            else:
                message = Message(self._streamStaged)
                if (message.isComplete(len(self._streamStaged) )):
                    self._streamStaged = ''
                else:
                    message = None
        else:
            if (len(self._streamStaged) == 0):
                message = None
            else:
                # The message is not well formed, so we create a message with method not specified
                message = Message('')
                message.setMethod(Message.UNDEFINED)
                self._streamStaged = self._streamStaged[foundIdx :]
        return message
    
    '''
    This method is responsible for sending messages through the 
    socket.
    '''
    def sendMessage(self, message):
        msgstr = message.__str__()
        self._s_mkt.sendall(msgstr)
        messageResults = None
        while (messageResults == None):
            self._streamStaged = self._streamStaged + self._s_mkt.recv(1024)
            messageResults = self.getMessage()
        print messageResults.__str__()
        return messageResults

    '''
    This method closes the socket.
    '''
    def close(self):
        self._s_mkt.shutdown(socket.SHUT_RDWR)
        self._s_mkt.close()
        
# End of Channel Marketplace class
