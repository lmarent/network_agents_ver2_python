import socket
import sys
from foundation.Message import Message
import time
from foundation.Service import Service
from foundation.FoundationException import FoundationException
from foundation.Bid import Bid
import re
import uuid
import xml.dom.minidom
import logging

def removeIlegalCharacters(xml):
    RE_XML_ILLEGAL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
		    u'|' + \
                 u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
                  (unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
                   unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
                   unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff))
    xml = re.sub(RE_XML_ILLEGAL, " ", xml)
    return xml

def handleGetServices(document):
    print 'starting get service handler'
    document = removeIlegalCharacters(document)
    try:
        	dom = xml.dom.minidom.parseString(document)
        	servicesXml = dom.getElementsByTagName("Service")
        	services = {}
        	print 'starting get service handler'
        	for servicexml in servicesXml:
        	    service = Service()
        	    print 'starting get service handler'
        	    service.setFromXmlNode(servicexml)
        	    print 'starting get service handler'
        	    services[service.getId()] = service
        	return services
    except Exception as e: 
        raise FoundationException(str(e))

def handleBestBids(docum):
    logging.info('Starting handleBestBids')
    fronts = docum.getElementsByTagName("Front")
    val_return = handleFronts(fronts)
    logging.info('Ending handleBestBids')
    return val_return

def handleFronts(fronts):
    logging.info('Starting handleFronts')
    dic_return = {}
    for front in fronts:
        	parNbrElement = front.getElementsByTagName("Pareto_Number")[0]
        	parNbr = int((parNbrElement.childNodes[0]).data)
        	dic_return[parNbr] = handleFront(front)
    logging.info('Ending handleFronts')
    return dic_return

def handleFront(front):
    logging.info('Starting handleFront')
    val_return =[]
    bidXmLNodes = front.getElementsByTagName("Bid")
    for bidXmlNode in bidXmLNodes:
        	bid = Bid()
        	bid.setFromXmlNode(bidXmlNode)
        	val_return.append(bid)
    logging.info('Ending handleFront')
    return val_return
		 


sys.path.insert(1,'/home/luis/network_agents_ver2_python/agents/foundation')

HOST, PORT = "192.168.2.12", 3333 # clock server port
HOST2, PORT2 = "192.168.2.13", 5555 # market server port
message1= Message('')
message1.setMethod(Message.CONNECT)
strProv = "Provider3"
serviceId = "2"
message1.setParameter("Agent", strProv)

# Create a socket (SOCK_STREAM means a TCP socket)
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def createBid(strProv, serviceId, delay, price):
    bid = Bid()
    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
    idStr = str(uuidId)
    bid.setValues(idStr, strProv, serviceId)
    bid.setDecisionVariable("1", delay)  # Delay
    bid.setDecisionVariable("2", price)     # Price
    bid.setStatus(Bid.ACTIVE)
    message = bid.to_message()
    return message, idStr

def purchase(serviceId, bidId, quantity, delay, price):
    messagePurchase = Message('')
    messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
    idStr = str(uuidId)
    messagePurchase.setParameter('Id', idStr)		
    messagePurchase.setParameter('Service', serviceId)
    messagePurchase.setParameter('Bid', bidId)
    messagePurchase.setParameter('Quantity', quantity)
    messagePurchase.setParameter('1', delay) # Delay decision variable
    messagePurchase.setParameter('2', price) # Price decision variable
    return messagePurchase

# Sends the availability for the provider
def send_availability(strProv,strResource, quantity):
    messageAvail = Message('')
    messageAvail.setMethod(Message.SEND_AVAILABILITY)
    messageAvail.setParameter('Provider', strProv)
    messageAvail.setParameter('Resource', strResource)
    messageAvail.setParameter('Quantity', quantity)
    return messageAvail


try:
    # Connect to server and send data
    sock.connect((HOST, PORT))
    sock.sendall(message1.__str__())

    received = ""
    received = sock.recv(4096)
    recMsg = Message(received)
    if (recMsg.isMessageStatusOk()):
        connect = Message("")
        connect.setMethod(Message.GET_SERVICES)
        connect.setParameter("Service",serviceId)
        sock.sendall(connect.__str__())
        received = sock.recv(4096)
        serviceResponse = Message(received)
        if (serviceResponse.isMessageStatusOk() == False):
            print 'Service not received'
        else:
            print received
            print "Sent:     {}".format(message1.__str__())
            print "Received: {}".format(received)
            
            sock2.connect((HOST2, PORT2))
            sock2.sendall(message1.__str__())
            received = sock2.recv(4096)
            recMsg = Message(received)
            if (recMsg.isMessageStatusOk()):            		
                	# sends the message with the port connect. This assumes that
                	# the program socket_server.py was previously executed.
                port_message = Message("")
                port_message.setMethod(Message.SEND_PORT)
                port_message.setParameter("Port", "4401")
                port_message.setParameter("Type", 'provider')
                sock2.sendall(port_message.__str__())
                #received = sock2.recv(4096)
                #recMsg = Message(received)
                #if (recMsg.isMessageStatusOk()):
                time.sleep(1)    

                # send the provider availability
                message = send_availability(strProv,"1", str(100))
                sock2.sendall(message.__str__())                
                
                print "It is connected to the agent server"		
                # creates bids for the service 01
                message, bidId = createBid(strProv, serviceId, str(0.145), str(20))
                sock2.sendall(message.__str__())
                message = purchase(serviceId, bidId, str(10), str(0.145), str(20))
                sock2.sendall(message.__str__())
                    
                message, bidId = createBid(strProv, serviceId, str(0.16), str(18))
                sock2.sendall(message.__str__())
                message = purchase(serviceId, bidId, str(5), str(0.16), str(18))
                sock2.sendall(message.__str__())
                
                message, bidId = createBid(strProv, serviceId, str(0.13), str(21))
                sock2.sendall(message.__str__())
                message = purchase(serviceId, bidId, str(4), str(0.13), str(21))
                sock2.sendall(message.__str__())
                
                message, bidId = createBid(strProv, serviceId, str(0.15), str(19.5))
                sock2.sendall(message.__str__())
                message = purchase(serviceId, bidId, str(3), str(0.15), str(19.5))
                sock2.sendall(message.__str__())
                
                message, bidId = createBid(strProv, serviceId, str(0.155), str(18))
                sock2.sendall(message.__str__())
                message = purchase(serviceId, bidId, str(2), str(0.155), str(18))
                sock2.sendall(message.__str__())
                
                message, bidId = createBid(strProv, serviceId, str(0.155), str(17.5))
                sock2.sendall(message.__str__())
                message = purchase(serviceId, bidId, str(1), str(0.155), str(17.5))
                sock2.sendall(message.__str__())
                

#
#                    # Try to purchase without availability
#                    messagePurchase = Message('')
#                    messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
#                    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
#                    idStr = str(uuidId)
#                    messagePurchase.setParameter('Id', idStr)		
#                    messagePurchase.setParameter('Service', "Service_01")
#                    messagePurchase.setParameter('Bid', bid6.getId())
#                    messagePurchase.setParameter('Quantity', "10")
#                    messagePurchase.setParameter('Delay', '0.16')
#                    messagePurchase.setParameter('Price', '17.5')
#                    sock2.sendall(messagePurchase.__str__())
#                    received = sock2.recv(16800)
#                    messagePur1 = Message(received)
#                    if (messagePur1.isMessageStatusOk()):
#                        print bid6.getId() + 'Qua:' + messagePur1.getParameter("Quantity_Purchased")
#                    
#                    messagePurchase = Message('')
#                    messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
#                    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
#                    idStr = str(uuidId)
#                    messagePurchase.setParameter('Id', idStr)		
#                    messagePurchase.setParameter('Service', "Service_01")
#                    messagePurchase.setParameter('Bid', bid4.getId())
#                    messagePurchase.setParameter('Quantity', "20")
#                    messagePurchase.setParameter('Delay', '0.125')
#                    messagePurchase.setParameter('Price', '20.5')
#                    sock2.sendall(messagePurchase.__str__())
#                    received = sock2.recv(16800)
#                    messagePur1 = Message(received)
#                    if (messagePur1.isMessageStatusOk()):
#                        print bid4.getId() + 'Qua:' + messagePur1.getParameter("Quantity_Purchased")
#                    
#                    
#                    messagePurchase = Message('')
#                    messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
#                    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
#                    idStr = str(uuidId)
#                    messagePurchase.setParameter('Id', idStr)		
#                    messagePurchase.setParameter('Service', "Service_01")
#                    messagePurchase.setParameter('Bid', bid6.getId())
#                    messagePurchase.setParameter('Quantity', "10")
#                    messagePurchase.setParameter('Delay', '0.16')
#                    messagePurchase.setParameter('Price', '17')
#                    sock2.sendall(messagePurchase.__str__())
#                    received = sock2.recv(16800)
#                    messagePur1 = Message(received)
#                    if (messagePur1.isMessageStatusOk()):
#                        print bid6.getId() + 'Qua:' + messagePur1.getParameter("Quantity_Purchased")
#                    messagePurchase = Message('')
#                    messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
#                    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
#                    idStr = str(uuidId)
#                    messagePurchase.setParameter('Id', idStr)		
#                    messagePurchase.setParameter('Service', "Service_01")
#                    messagePurchase.setParameter('Bid', bid6.getId())
#                    messagePurchase.setParameter('Quantity', "30")
#                    messagePurchase.setParameter('Delay', '0.16')
#                    messagePurchase.setParameter('Price', '17')
#                    sock2.sendall(messagePurchase.__str__())
#                    received = sock2.recv(16800)
#                    messagePur1 = Message(received)
#                    if (messagePur1.isMessageStatusOk()):
#                        print bid6.getId() + 'Qua:' + messagePur1.getParameter("Quantity_Purchased")
#                    #messagePurchase.setParameter('Id', idStr)
#                    #messagePurchase.setParameter('Bid', bid.getId())        
#                    #messagePurchase.setParameter('Quantity', str(quantity))
#                    
#                    bid6.setStatus(Bid.INACTIVE)
#                    message = bid6.to_message()
#                    sock2.sendall(message.__str__())
#                    received = sock2.recv(4096)
#                    messageBid6 = Message(received)
#                    if (messageBid6.isMessageStatusOk()):
#                        print "Bid 6 Inactivated"
#                    
#                    messagePurchase = Message('')
#                    messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
#                    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
#                    idStr = str(uuidId)
#                    messagePurchase.setParameter('Id', idStr)		
#                    messagePurchase.setParameter('Service', "Service_01")
#                    messagePurchase.setParameter('Bid', bid6.getId())
#                    messagePurchase.setParameter('Quantity', "30")
#                    messagePurchase.setParameter('Delay', '0.16')
#                    messagePurchase.setParameter('Price', '17')
#                    sock2.sendall(messagePurchase.__str__())
#                    received = sock2.recv(16800)
#                    messagePur1 = Message(received)
#                    if (messagePur1.isMessageStatusOk()):
#                        print bid6.getId() + 'Qua:' + messagePur1.getParameter("Quantity_Purchased")

	    
    # Receive data from the server and shut down
    
    
finally:
    sock.shutdown(socket.SHUT_WR)
    sock.close()
    sock2.shutdown(socket.SHUT_WR)
    sock2.close()
