import threading
import time
import socket
import sys
sys.path.append("/home/network_agents_ver2_python/agents/foundation")
from Message import Message
import agent_properties

sys.path.insert(1,'/home/network_agents_ver2_python/agents/foundation')

class socket_test:
    '''demonstration class only
      - coded for clarity, not efficiency
    '''
    streamStaged = ''

    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock

    def connect(self, host, port):
        self.sock.connect((host, port))

    def close(self):
        self.sock.close()
       

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

                
    '''
    This method is responsible for sending messages through the 
    socket.
    '''
    def sendMessage(self, message):
        print 'start sending message' 
        msgstr = message.__str__()
        self.sock.sendall(msgstr)
        messageResults = None
        return messageResults


class socket_clockserver_test(socket_test):
    
    def __init__(self):
        socket_test.__init__(self)
        
    def messagePeriod(self,period):
    	periodEnd = Message("")
    	periodEnd.setMethod(Message.END_PERIOD)
        periodEnd.setParameter("Period", period)
        return periodEnd

    def messageBids(self, period, body):
        bidsMes = Message("")
        bidsMes.setMethod(Message.RECEIVE_BID_INFORMATION)
        bidsMes.setParameter("Period", period)
        bidsMes.setBody(body)
        return bidsMes


class socket_mrk_place_test(socket_test):

    def __init__(self):
        socket_test.__init__(self)

    def messagePeriod(self,period):
        periodEnd = Message("")
        periodEnd.setMethod(Message.END_PERIOD)
        periodEnd.setParameter("Period", period)
        return periodEnd

    def messageBids(self, period, body):
        bidsMes = Message("")
        bidsMes.setMethod(Message.RECEIVE_BID_INFORMATION)
        bidsMes.setParameter("Period", period)
        bidsMes.setBody(body)
        return bidsMes


def clock_server(Id):
    period = 4
    body = open('MessageMarketPlace.txt', 'r').read()
    sck_clock_server = socket_clockserver_test() 
    host = agent_properties.addr_agent_clock_server
    port = agent_properties.l_port_provider + ( Id * 3 )
    print threading.currentThread().getName(), 'Starting', ' host:', host, ' port:', port
    sck_clock_server.connect(host,port)
    time.sleep(1)
    clockMessage = sck_clock_server.messagePeriod(period)
    sck_clock_server.sendMessage(clockMessage)
    print threading.currentThread().getName(), 'After sending end period message'
    bidMessage = sck_clock_server.messageBids(period, body)
    sck_clock_server.sendMessage(bidMessage)
    print threading.currentThread().getName(), 'After sending bid message'
    print threading.currentThread().getName(), 'Exiting', 
    sck_clock_server.close()

def market_place(Id):
    period = 3
    body = open('MessageMarketPlace.txt', 'r').read()
    sck_mkt_place_server = socket_mrk_place_test() 
    host = agent_properties.addr_agent_mktplace_isp
    port = agent_properties.l_port_provider + ( (Id * 3) + 1)
    print threading.currentThread().getName(), 'Starting', ' host:', host, ' port:', port
    sck_mkt_place_server.connect(host, port)
    bidMessage = sck_mkt_place_server.messageBids(period, body)
    sck_mkt_place_server.sendMessage(bidMessage)
    time.sleep(5)
    print threading.currentThread().getName(), 'Exiting'
    sck_mkt_place_server.close()



Id = 5
t = threading.Thread(name='clock_server', target=clock_server, args=(Id,))
w = threading.Thread(name='market_place', target=market_place, args=(Id,))

t.start()
w.start()

