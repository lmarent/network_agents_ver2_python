import socket
import sys
sys.path.append("/home/network_agents_ver2_python/agents/foundation")
sys.path.append("/home/network_agents_ver2_python/agents/probabilities")
sys.path.append("/home/network_agents_ver2_python/agents/costfunctions")
sys.path.append("/home/network_agents_ver2_python/agents")

import time
import re
import uuid
import xml.dom.minidom
import logging

sys.path.insert(1,'/home/network_agents_ver2_python/agents/foundation')

from Message import Message
from Service import Service
from FoundationException import FoundationException
from Bid import Bid
import agent_properties

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
		 


sys.path.insert(1,'/home/network_agents_ver2_python/agents/foundation')

HOST, PORT = agent_properties.addr_clock_server, agent_properties.clock_listening_port # clock server port
HOST2, PORT2 = agent_properties.addr_mktplace_isp , agent_properties.mkt_place_listening_port # market server port

message1= Message('')
message1.setMethod(Message.CONNECT)
strProv = "Provider3"
serviceId = "1" # Movie Streaming
message1.setParameter("Agent", strProv)

# Create a socket (SOCK_STREAM means a TCP socket)
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def createBid(strProv, serviceId, delay, price):
    bid = Bid()
    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
    idStr = str(uuidId)
    bid.setValues(idStr, strProv, serviceId)
    bid.setDecisionVariable("1", price)     # Price
    bid.setDecisionVariable("2", delay)  # Delay
    bid.setStatus(Bid.ACTIVE)
    message = bid.to_message()
    return message, idStr

def verifyBid(sock2):
    received = sock2.recv(16800)
    messageBid= Message(received)
    if (not messageBid.isMessageStatusOk()):
        raise FoundationException("error in creating bid")


def purchase(serviceId, bidId, quantity, delay, price):
    messagePurchase = Message('')
    messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
    idStr = str(uuidId)
    messagePurchase.setParameter('Id', idStr)		
    messagePurchase.setParameter('Service', serviceId)
    messagePurchase.setParameter('Bid', bidId)
    messagePurchase.setParameter('Quantity', quantity)
    messagePurchase.setParameter('1', price) # Price decision variable
    messagePurchase.setParameter('2', delay) # Delay decision variable
    return messagePurchase

def verifyPurchase(sock2, qty):
    received = sock2.recv(16800)
    messagePurchase= Message(received)
    print messagePurchase.__str__()
    if (not messagePurchase.isMessageStatusOk()):
        raise FoundationException("error in creating purchase")
    else:
        # verify that the quantity purchased.
        qtyPurchasedStr = messagePurchase.getParameter('Quantity_Purchased')
        qtyPurchased = float(qtyPurchasedStr)
        if (qtyPurchased <> qty):
            raise FoundationException("error in creating purchase - Qty purchased not equal to " + str(qty))


# Sends the availability for the provider
def send_availability(strProv,strResource, quantity):
    messageAvail = Message('')
    messageAvail.setMethod(Message.SEND_AVAILABILITY)
    messageAvail.setParameter('Provider', strProv)
    messageAvail.setParameter('Resource', strResource)
    messageAvail.setParameter('Quantity', quantity)
    return messageAvail


try:
    # Connect to Clock server and send data
    print 'Connecting Host:', HOST, ' Port:', PORT
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
            print 'Successful Clock Server Connection'
            #print "Sent:     {}".format(message1.__str__())
            #print "Received: {}".format(received)
            
            # Connect to market Place server and send data
            print 'Connecting Host:', HOST2, ' Port:', PORT2
            sock2.connect((HOST2, PORT2))
            sock2.sendall(message1.__str__())
            received = sock2.recv(4096)
            recMsg = Message(received)
            if (recMsg.isMessageStatusOk()):            		
                # sends the message with the port connect. This assumes that
                # the program socket_server.py was previously executed.
                print 'Successful Market Place Server Connection'
                port_message = Message("")
                port_message.setMethod(Message.SEND_PORT)
                port_message.setParameter("Port", agent_properties.l_port_provider)
                port_message.setParameter("Type", "provider")
                port_message.setParameter("CapacityType","bulk")
                sock2.sendall(port_message.__str__())
                received = sock2.recv(4096)
                recMsg = Message(received)
                if (recMsg.isMessageStatusOk()):
                    pass
                time.sleep(1)    

                # send the provider availability
                message = send_availability(strProv,"1", str(100))
                sock2.sendall(message.__str__())                
                received = sock2.recv(16800)
                messageAvail= Message(received)
                if (not messageAvail.isMessageStatusOk()):
                    raise FoundationException("error in sending availability")
                
                print "It is connected to the agent server"		
                # creates bids for the service 01
                message, bidId1 = createBid(strProv, serviceId, str(0.145), str(20))
                sock2.sendall(message.__str__())
                verifyBid(sock2)
                
                message = purchase(serviceId, bidId1, str(10), str(0.145), str(20))
                sock2.sendall(message.__str__())
                received = sock2.recv(16800)
                messagePur1 = Message(received)
                if (not messagePur1.isMessageStatusOk()):
                    raise FoundationException("error in creating purchase")
                    
                message, bidId2 = createBid(strProv, serviceId, str(0.16), str(18))
                sock2.sendall(message.__str__())
                verifyBid(sock2)
                
                message = purchase(serviceId, bidId2, str(5), str(0.16), str(18))
                sock2.sendall(message.__str__())
                verifyPurchase(sock2,5)
                
                message, bidId3 = createBid(strProv, serviceId, str(0.13), str(21))
                sock2.sendall(message.__str__())
                verifyBid(sock2)

                message = purchase(serviceId, bidId3, str(4), str(0.13), str(21))
                sock2.sendall(message.__str__())
                verifyPurchase(sock2,4)
                
                message, bidId4 = createBid(strProv, serviceId, str(0.15), str(19.5))
                sock2.sendall(message.__str__())
                verifyBid(sock2)
                
                message = purchase(serviceId, bidId4, str(3), str(0.15), str(19.5))
                sock2.sendall(message.__str__())
                verifyPurchase(sock2,3)
                
                message, bidId5 = createBid(strProv, serviceId, str(0.155), str(18))
                sock2.sendall(message.__str__())
                verifyBid(sock2)
                
                message = purchase(serviceId, bidId5, str(2), str(0.155), str(18))
                sock2.sendall(message.__str__())
                verifyPurchase(sock2,2)
                
                message, bidId6 = createBid(strProv, serviceId, str(0.155), str(17.5))
                sock2.sendall(message.__str__())
                verifyBid(sock2)
                                
                message = purchase(serviceId, bidId6, str(1), str(0.155), str(17.5))
                sock2.sendall(message.__str__())
                verifyPurchase(sock2,1)

#
                # Try to purchase without availability
                message = purchase(serviceId, bidId6, str(10), str(0.16), str(17.5))
                sock2.sendall(message.__str__())
                verifyPurchase(sock2,10)
#                    
                message = purchase(serviceId, bidId4, str(20), str(0.125), str(20))
                sock2.sendall(message.__str__())
                verifyPurchase(sock2,20)

#                    
                message = purchase(serviceId, bidId5, str(10), str(0.16), str(17))
                sock2.sendall(message.__str__())
                verifyPurchase(sock2,10)
#                    

                message = purchase(serviceId, bidId4, str(30), str(0.16), str(17))
                sock2.sendall(message.__str__())
                verifyPurchase(sock2,30)

                time.sleep(30)

                #try to buy an inactive bid
#                bid6.setStatus(Bid.INACTIVE)
#                message = bid6.to_message()
#                sock2.sendall(message.__str__())
#                received = sock2.recv(4096)
#                messageBid6 = Message(received)
#                if (messageBid6.isMessageStatusOk()):
#                    print "Bid 6 Inactivated"
#                    
#                messagePurchase = Message('')
#                messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
#                uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
#                idStr = str(uuidId)
#                messagePurchase.setParameter('Id', idStr)		
#                messagePurchase.setParameter('Service', "Service_01")
#                messagePurchase.setParameter('Bid', bid6.getId())
#                messagePurchase.setParameter('Quantity', "30")
#                messagePurchase.setParameter('Delay', '0.16')
#                messagePurchase.setParameter('Price', '17')
#                sock2.sendall(messagePurchase.__str__())
#                received = sock2.recv(16800)
#                messagePur1 = Message(received)
#                if (messagePur1.isMessageStatusOk()):
#                    print bid6.getId() + 'Qua:' + messagePur1.getParameter("Quantity_Purchased")

	    
    # Receive data from the server and shut down
    
    
finally:
    sock.shutdown(socket.SHUT_WR)
    sock.close()
    sock2.shutdown(socket.SHUT_WR)
    sock2.close()
