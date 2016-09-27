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

    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock

    def connect(self, host, port):
        self.sock.connect((host, port))

    def mysend(self, msg):
        totalsent = 0
        while totalsent < MSGLEN:
            sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent

    def myreceive(self):
        chunks = []
        bytes_recd = 0
        while bytes_recd < MSGLEN:
            chunk = self.sock.recv(min(MSGLEN - bytes_recd, 2048))
            if chunk == '':
                raise RuntimeError("socket connection broken")
            chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
        return ''.join(chunks)

class socket_clockserver_test(socket_test):
    
    def __init__(self):
        socket_test.__init__(self)
        
    def messagePeriod(self,period):
    	periodEnd = Message("")
    	periodEnd.setMethod(Message.END_PERIOD)
	endPeriod.setParameter("Period", period);


class socket_mrk_place_test(socket_test):

    def __init__(self):
        socket_test.__init__(self)

    def messageBids(self,period):
    	periodEnd = Message("")
    	periodEnd.setMethod(Message.END_PERIOD)
	endPeriod.setParameter("Period", period);


def clock_server(Id):
    sck_clock_server = socket_clockserver_test() 
    host = agent_properties.addr_agent_clock_server
    port = agent_properties.l_port_provider + ( Id * 3 )
    sck_clock_server.connect(host,port)
    print threading.currentThread().getName(), 'Starting', ' host:', host, ' port:', port
    time.sleep(2)
    print threading.currentThread().getName(), 'Exiting', 

def market_place(Id):
    sck_mkt_place_server = socket_mrk_place_test() 
    host = agent_properties.addr_agent_mktplace_isp
    port = agent_properties.l_port_provider + ( (Id * 3) + 1)
    sck_mkt_place_server.connect(host, port)
    print threading.currentThread().getName(), 'Starting', ' host:', host, ' port:', port
    time.sleep(3)
    print threading.currentThread().getName(), 'Exiting'

Id = 5
t = threading.Thread(name='clock_server', target=clock_server, args=(Id,))
w = threading.Thread(name='market_place', target=market_place, args=(Id,))

w.start()
t.start()

