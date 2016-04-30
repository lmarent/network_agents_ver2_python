from FoundationException import FoundationException
from Message import Message
import socket

class ChannelProvider(object):
    '''
    The Channel_Provider class defines the methods for creating 
    the socket communication between the presenter and providers. 
    It includes the methods get and send message, as well as closing the socket.
    '''
    
    def __init__(self, address, port):	
        # Creates the socket
        self._streamStaged = ''
        HOST = address
        PORT = port
        self._s_provider = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        err = self._s_provider.connect_ex((HOST, PORT))
        if (err > 0):
	    raise FoundationException("Error: the provider is not running")
    
    def getMessage(self):
	'''
	This method is responsible for getting messages from 
	the socket.
	'''
	foundIdx = self._streamStaged.find("Method")
	if (foundIdx == 0):
	    foundIdx2 = self._streamStaged.find("Method", foundIdx + 1)
	    if (foundIdx2 != -1):
		message = Message(self._streamStaged[foundIdx : foundIdx2 - 1])
		# Even that the message could have errors is complete
		self._streamStaged = self._streamStaged[foundIdx2 : ]
	    else:
		message = Message(self._streamStaged)
		if (message.isComplete( len(self._streamStaged) )):
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
		    	
    def sendMessage(self, message):
	'''
	This method is responsible for sending messages through the 
	socket.
	'''
        msgstr = message.__str__()
        self._s_provider.sendall(msgstr)
        messageResults = None
        while (messageResults == None):
	    self._streamStaged = self._streamStaged + self._s_provider.recv(1024)
	    messageResults = self.getMessage()
        return messageResults
	
    def close(self):
	'''
	This method closes the socket.
	'''
        self._s_provider.shutdown(socket.SHUT_RDWR)
        self._s_provider.close()
# End of Channel Marketplace class
