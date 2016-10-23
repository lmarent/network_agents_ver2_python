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

def createBidService4(strProv, serviceId, delay, price):
    bid = Bid()
    uuidId = uuid.uuid1()   # make a UUID based on the host ID and current time
    idStr = str(uuidId)
    bid.setValues(idStr, strProv, serviceId)
    bid.setDecisionVariable("8", price)     # Price
    bid.setDecisionVariable("7", delay)  # Delay
    bid.setStatus(Bid.ACTIVE)
    message = bid.to_message()
    return message, idStr

def createCapacitatedBid(strProv, serviceId, delay, price, capacity):
    bid = Bid()
    uuidId = uuid.uuid1()   # make a UUID based on the host ID and current time
    idStr = str(uuidId)
    bid.setValues(idStr, strProv, serviceId)
    bid.setDecisionVariable("1", price)     # Price
    bid.setDecisionVariable("2", delay)  # Delay
    bid.setCapacity(capacity)
    bid.setStatus(Bid.ACTIVE)
    message = bid.to_message()
    return message, idStr

def inactiveBid(bidId, strProv, serviceId, delay, price):
    bid = Bid()
    bid.setValues(bidId, strProv, serviceId)
    bid.setDecisionVariable("1", price)     # Price
    bid.setDecisionVariable("2", delay)  # Delay
    bid.setStatus(Bid.INACTIVE)
    message = bid.to_message()
    return message, bidId

def verifyBid(sock2):
    received = sock2.recv(16800)
    messageBid= Message(received)
    if (not messageBid.isMessageStatusOk()):
        raise FoundationException("error in creating bid")

def getAvailability(strProvider, serviceStr, bidId):
    messageGetAvailability = Message('')
    messageGetAvailability.setMethod(Message.GET_AVAILABILITY)
    messageGetAvailability.setParameter('Provider', strProvider)       
    messageGetAvailability.setParameter('Service', serviceStr)
    messageGetAvailability.setParameter('Bid', bidId)
    return messageGetAvailability

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


def purchaseService4(serviceId, bidId, quantity, delay, price):
    messagePurchase = Message('')
    messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
    uuidId = uuid.uuid1()   # make a UUID based on the host ID and current time
    idStr = str(uuidId)
    messagePurchase.setParameter('Id', idStr)       
    messagePurchase.setParameter('Service', serviceId)
    messagePurchase.setParameter('Bid', bidId)
    messagePurchase.setParameter('Quantity', quantity)
    messagePurchase.setParameter('8', price) # Price decision variable
    messagePurchase.setParameter('7', delay) # Delay decision variable
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
            raise FoundationException("error in creating purchase - Qty purchased" + str(qtyPurchased)+ " not equal to " + str(qty))

def verifyAvailability(sock2, qty):
    received = sock2.recv(16800)
    messageAvail= Message(received)
    print messageAvail.__str__()
    if (not messageAvail.isMessageStatusOk()):
        raise FoundationException("error in the availability message")
    else:
        # verify that the quantity purchased.
        qtyStr = messageAvail.getParameter('Quantity')
        qtyAvail = float(qtyStr)
        qtyAvail = round(qtyAvail,2)
        if (qtyAvail <> qty):
            raise FoundationException("error in the quantity available" + str(qtyAvail)+ "- Qty not equal to " + str(qty))


# Sends the availability for the provider
def send_availability(strProv,strResource, quantity):
    messageAvail = Message('')
    messageAvail.setMethod(Message.SEND_AVAILABILITY)
    messageAvail.setParameter('Provider', strProv)
    messageAvail.setParameter('Resource', strResource)
    messageAvail.setParameter('Quantity', quantity)
    return messageAvail


def test_bulk_capacity():
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
                    port_message = Message("")
                    port_message.setMethod(Message.SEND_PORT)
                    port_message.setParameter("Port", agent_properties.l_port_provider)
                    port_message.setParameter("Type", "provider")
                    port_message.setParameter("CapacityType","bulk")


                    print 'recMsg', port_message.__str__()

                    sock2.sendall(port_message.__str__())
                    received = sock2.recv(4096)
                    recMsg = Message(received)

                    print 'recMsg', recMsg.__str__()

                    if (recMsg.isMessageStatusOk()):
                        pass
                    time.sleep(1)    

                    print 'Successful Market Place Server Connection'
                    resource = "1"
                    # send the provider availability
                    message = send_availability(strProv,resource, str(100))
                    print 'message to send:' + message.__str__()

                    sock2.sendall(message.__str__())                
                    received = sock2.recv(4096)
                    print received
                    recMsg= Message(received)
                    if (not recMsg.isMessageStatusOk()):
                        raise FoundationException("error in sending availability")

                    print "It is connected to the agent server"		
                    # creates bids for the service 01
                    message, bidId1 = createBid(strProv, serviceId, str(0.145), str(20))
                    sock2.sendall(message.__str__())
                    verifyBid(sock2)

                    # Number of resource used: 10*(0.4 + 1*(0.916666667)= 13.66
                    message = purchase(serviceId, bidId1, str(10), str(0.145), str(20))
                    sock2.sendall(message.__str__())
                    received = sock2.recv(16800)
                    messagePur1 = Message(received)
                    if (not messagePur1.isMessageStatusOk()):
                        raise FoundationException("error in creating purchase")

                    message = getAvailability(strProv,serviceId,'')                
                    sock2.sendall(message.__str__())
                    qtyAvail = round(100 - 13.166,2)
                    verifyAvailability(sock2, qtyAvail)

                    message, bidId2 = createBid(strProv, serviceId, str(0.16), str(18))
                    sock2.sendall(message.__str__())
                    verifyBid(sock2)

                    # Number of resource used: 5*(0.4 + 1*(0.6667))=5.333
                    message = purchase(serviceId, bidId2, str(5), str(0.16), str(18))
                    sock2.sendall(message.__str__())
                    verifyPurchase(sock2,5)

                    message = getAvailability(strProv,serviceId,'')                
                    sock2.sendall(message.__str__())
                    qtyAvail = round(qtyAvail - 5.333,2)
                    verifyAvailability(sock2, qtyAvail)

                    message, bidId3 = createBid(strProv, serviceId, str(0.15), str(21))
                    sock2.sendall(message.__str__())
                    verifyBid(sock2)

                    # Number of resource used: 4*(0.4 + 1*(0.83333))=4.9333
                    message = purchase(serviceId, bidId3, str(4), str(0.15), str(21))
                    sock2.sendall(message.__str__())
                    verifyPurchase(sock2,4)

                    message = getAvailability(strProv,serviceId,'')                
                    sock2.sendall(message.__str__())
                    qtyAvail = round(qtyAvail - 4.9333,2)
                    verifyAvailability(sock2, qtyAvail)

                    message, bidId4 = createBid(strProv, serviceId, str(0.15), str(19.5))
                    sock2.sendall(message.__str__())
                    verifyBid(sock2)

                    # Number of resource used: 3*(0.4 + 1*(0.83333))=3.7
                    message = purchase(serviceId, bidId4, str(3), str(0.15), str(19.5))
                    sock2.sendall(message.__str__())
                    verifyPurchase(sock2,3)

                    message = getAvailability(strProv,serviceId,'')                
                    sock2.sendall(message.__str__())
                    qtyAvail = round(qtyAvail - 3.7, 2)
                    verifyAvailability(sock2, qtyAvail)

                    message, bidId5 = createBid(strProv, serviceId, str(0.15), str(18))
                    sock2.sendall(message.__str__())
                    verifyBid(sock2)

                    # Number of resource used: 2*(0.4 + 1*(0.83333))=2.46
                    message = purchase(serviceId, bidId5, str(2), str(0.15), str(18))
                    sock2.sendall(message.__str__())
                    verifyPurchase(sock2,2)

                    message = getAvailability(strProv,serviceId,'')                
                    sock2.sendall(message.__str__())
                    qtyAvail = round(qtyAvail - 2.466, 2)
                    verifyAvailability(sock2, qtyAvail)

                    message, bidId6 = createBid(strProv, serviceId, str(0.155), str(17.5))
                    sock2.sendall(message.__str__())
                    verifyBid(sock2)

                    # Number of resource used: 1*(0.4 + 1*(0.75))=1.15
                    message = purchase(serviceId, bidId6, str(1), str(0.155), str(17.5))
                    sock2.sendall(message.__str__())
                    verifyPurchase(sock2,1)

                    message = getAvailability(strProv,serviceId,'')                
                    sock2.sendall(message.__str__())
                    qtyAvail = round(qtyAvail - 1.15, 2)
                    verifyAvailability(sock2, qtyAvail)
    #
                    # Number of resource used: 10*(0.4 + 1*(1.066))=11.5
                    message = purchase(serviceId, bidId6, str(10), str(0.16), str(17.5))
                    sock2.sendall(message.__str__())
                    verifyPurchase(sock2,10)

                    message = getAvailability(strProv,serviceId,'')                
                    sock2.sendall(message.__str__())
                    qtyAvail = round(qtyAvail - 11.5, 2)
                    verifyAvailability(sock2, qtyAvail)
    #                    
                    # Number of resource used: 10*(0.4 + 1*(0.833))=24.66
                    message = purchase(serviceId, bidId4, str(20), str(0.125), str(20))
                    sock2.sendall(message.__str__())
                    verifyPurchase(sock2,20)

                    message = getAvailability(strProv,serviceId,'')                
                    sock2.sendall(message.__str__())
                    qtyAvail = 33.08
                    verifyAvailability(sock2, qtyAvail)

                    # Number of resource used: 10*(0.4 + 1*(0.833))=12.333
                    message = purchase(serviceId, bidId5, str(10), str(0.16), str(17))
                    sock2.sendall(message.__str__())
                    verifyPurchase(sock2,10)

                    message = getAvailability(strProv,serviceId,'')                
                    sock2.sendall(message.__str__())
                    qtyAvail = round(qtyAvail - 12.33, 2)
                    verifyAvailability(sock2, qtyAvail)

                    # The quantity is not enough, so it could not purchase.
                    message = purchase(serviceId, bidId4, str(30), str(0.16), str(17))
                    sock2.sendall(message.__str__())
                    verifyPurchase(sock2,0)


                    #try to buy an inactive bid
                    message, bidId6 = inactiveBid(bidId6, strProv, serviceId, str(0.155), str(17.5))
                    sock2.sendall(message.__str__())
                    received = sock2.recv(4096)
                    messageBid6 = Message(received)
                    if (messageBid6.isMessageStatusOk()):
                        pass

                    message = purchase(serviceId, bidId6, str(1), str(0.16), str(17))
                    sock2.sendall(message.__str__())
                    verifyPurchase(sock2,0)

                    #message = getAvailability(strProv,serviceId,'')                
                    #sock2.sendall(message.__str__())
                    #qtyAvail = round(qtyAvail - 1.15, 2)
                    #verifyAvailability(sock2, qtyAvail)

                    
                    # this part test the restart of the capacity in the provider.
                    time.sleep(10)
                    message = getAvailability(strProv,serviceId,'')                
                    sock2.sendall(message.__str__())
                    qtyAvail = round(100, 2)
                    verifyAvailability(sock2, qtyAvail)
                    

    finally:
        sock.shutdown(socket.SHUT_WR)
        sock.close()
        sock2.shutdown(socket.SHUT_WR)
        sock2.close()

def test_bulk_capacity_service4():

    message1= Message('')
    message1.setMethod(Message.CONNECT)
    strProv = "Provider8"
    serviceId = "4" # Priority_Class_Streaming
    message1.setParameter("Agent", strProv)

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
                    port_message = Message("")
                    port_message.setMethod(Message.SEND_PORT)
                    port_message.setParameter("Port", agent_properties.l_port_provider)
                    port_message.setParameter("Type", "provider")
                    port_message.setParameter("CapacityType","bulk")


                    print 'recMsg', port_message.__str__()

                    sock2.sendall(port_message.__str__())
                    received = sock2.recv(4096)
                    recMsg = Message(received)

                    print 'recMsg', recMsg.__str__()

                    if (recMsg.isMessageStatusOk()):
                        pass
                    time.sleep(1)    

                    print 'Successful Market Place Server Connection'

                    # send the provider availability
                    resource = "2"
                    message = send_availability(strProv,resource, str(120))
                    print 'message to send:' + message.__str__()

                    sock2.sendall(message.__str__())                
                    received = sock2.recv(4096)
                    print received
                    recMsg= Message(received)
                    if (not recMsg.isMessageStatusOk()):
                        raise FoundationException("error in sending availability")

                    print "It is connected to the agent server"     
                    # creates bids for the service 01
                    message, bidId1 = createBidService4(strProv, serviceId, str(0), str(0.324563087213))
                    sock2.sendall(message.__str__())
                    verifyBid(sock2)

                    # Number of resource used: 28.386816*(1 + 1)= 13.66
                    message = purchaseService4(serviceId, bidId1, str(28.386816), str(0), str(0.324563087213))
                    sock2.sendall(message.__str__())
                    received = sock2.recv(16800)
                    messagePur1 = Message(received)
                    if (not messagePur1.isMessageStatusOk()):
                        raise FoundationException("error in creating purchase" + messagePur1.__str__())
                    else:
                        print 'Message arrived \n' + messagePur1.__str__() 

                    message = getAvailability(strProv,serviceId,'')                
                    sock2.sendall(message.__str__())
                    qtyAvail = 120 - (28.386816*2)
                    qtyAvail = round(qtyAvail,2)
                    verifyAvailability(sock2, qtyAvail)

                    # Number of resource used: 66.749068 *(1 + 1)= 133.498136, as there are not enough quantities, the the server only purchase 31
                    message = purchaseService4(serviceId, bidId1, str(66.749068), str(0), str(0.324563087213))
                    sock2.sendall(message.__str__())
                    verifyPurchase(sock2,31.613184)
                    
                    message = getAvailability(strProv,serviceId,'')                
                    sock2.sendall(message.__str__())
                    qtyAvail = 0
                    verifyAvailability(sock2, qtyAvail)

                    print 'It is going to sleep 10 seconds to see whether or not the server restart the availability' 
                    # this part test the restart of the capacity in the provider.
                    time.sleep(10)
                    message = getAvailability(strProv,serviceId,'')                
                    sock2.sendall(message.__str__())
                    qtyAvail = round(120, 2)
                    verifyAvailability(sock2, qtyAvail)
                    

    finally:
        sock.shutdown(socket.SHUT_WR)
        sock.close()
        sock2.shutdown(socket.SHUT_WR)
        sock2.close()


def test_bid_capacity():
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
                    port_message = Message("")
                    port_message.setMethod(Message.SEND_PORT)
                    port_message.setParameter("Port", agent_properties.l_port_provider)
                    port_message.setParameter("Type", "provider")
                    port_message.setParameter("CapacityType","bid")

                    sock2.sendall(port_message.__str__())
                    received = sock2.recv(4096)
                    recMsg = Message(received)
                    if (recMsg.isMessageStatusOk()):
                        pass

                    message, bidId1 = createCapacitatedBid(strProv, serviceId, str(0.155), str(17.5),str(10))
                    sock2.sendall(message.__str__())
                    verifyBid(sock2)

                    message, bidId2 = createCapacitatedBid(strProv, serviceId, str(0.15), str(18),str(15))
                    sock2.sendall(message.__str__())
                    verifyBid(sock2)

                    message, bidId3 = createCapacitatedBid(strProv, serviceId, str(0.145), str(19),str(20))
                    sock2.sendall(message.__str__())
                    verifyBid(sock2)

                    # Number of units consumed: 5
                    message = purchase(serviceId, bidId1, str(5), str(0.155), str(17.5))
                    sock2.sendall(message.__str__())
                    verifyPurchase(sock2,5)
                    
                    qtyAvail = 10
                    message = getAvailability(strProv,serviceId, bidId1)
                    sock2.sendall(message.__str__())
                    qtyAvail = round(qtyAvail - 5, 2)
                    verifyAvailability(sock2, qtyAvail)

                    # Number of units consumed: 5
                    message = purchase(serviceId, bidId1, str(7), str(0.155), str(17.5))
                    sock2.sendall(message.__str__())
                    verifyPurchase(sock2,5)

                    message = getAvailability(strProv,serviceId, bidId1)
                    sock2.sendall(message.__str__())
                    qtyAvail = 0
                    verifyAvailability(sock2, qtyAvail)

    finally:
        sock.shutdown(socket.SHUT_WR)
        sock.close()
        sock2.shutdown(socket.SHUT_WR)
        sock2.close()
    
    
#test_bulk_capacity()
test_bulk_capacity_service4()

#test_bid_capacity()