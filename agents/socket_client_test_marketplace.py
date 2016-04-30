
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
		 


sys.path.insert(1,'/home/luis/network_agents/agents/foundation')

HOST, PORT = "localhost", 3333 # clock server port
HOST2, PORT2 = "localhost", 5555 # market server port
message1= Message('')
message1.setMethod(Message.CONNECT)
message1.setParameter("Provider", "Provider1")

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
	connect = Message("")
        connect.setMethod(Message.GET_SERVICES)
        connect.setParameter("Service","Service_01")
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
		port_message.setParameter("Port", "4400")
		port_message.setParameter("Type", 'provider')
		sock2.sendall(port_message.__str__())
		received = sock2.recv(4096)
		recMsg = Message(received)
		if (recMsg.isMessageStatusOk()):
		    print "It is connected to the agent server"
		
		# creates bids for the service 01
		bid = Bid()
		uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
		idStr = str(uuidId)
		bid.setValues(idStr, "Provider1", "Service_01")
		bid.setDecisionVariable("Delay", 0.145)
		bid.setDecisionVariable("Price", 20)
		bid.setStatus(Bid.ACTIVE)
		message = bid.to_message()
		sock2.sendall(message.__str__())
		received = sock2.recv(4096)
		messageBid = Message(received)
		if (messageBid.isMessageStatusOk()):
		    print "Ok - It is registering bids fine"
		
		sock2.sendall(message.__str__())
		received = sock2.recv(4096)
		messageBid2 = Message(received)
		if (messageBid2.isMessageStatusOk() == False):
		    if (int(messageBid2.getParameter("Status_Code"))==310):
			print "Ok - it is identifying duplicate bids"
		
		# Now we try to create many bid so we can verify the pareto front.
		bid3 = Bid()
		uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
		idStr = str(uuidId)
		bid3.setValues(idStr, "Provider1", "Service_01")
		bid3.setDecisionVariable("Delay", 0.16)
		bid3.setDecisionVariable("Price", 18)
		bid3.setStatus(Bid.ACTIVE)
		message = bid3.to_message()
		sock2.sendall(message.__str__())
		received = sock2.recv(4096)
		messageBid3 = Message(received)
		if (messageBid3.isMessageStatusOk()):
		    print "Bid 3 Created"

		bid4 = Bid()
		uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
		idStr = str(uuidId)
		bid4.setValues(idStr, "Provider1", "Service_01")
		bid4.setDecisionVariable("Delay", 0.13)
		bid4.setDecisionVariable("Price", 21)
		bid4.setStatus(Bid.ACTIVE)
		message = bid4.to_message()
		sock2.sendall(message.__str__())
		received = sock2.recv(4096)
		messageBid4 = Message(received)
		if (messageBid4.isMessageStatusOk()):
		    print "Bid 4 Created"
		
		bid5 = Bid()
		uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
		idStr = str(uuidId)
		bid5.setValues(idStr, "Provider1", "Service_01")
		bid5.setDecisionVariable("Delay", 0.15)
		bid5.setDecisionVariable("Price", 19.5)
		bid5.setStatus(Bid.ACTIVE)
		message = bid5.to_message()
		sock2.sendall(message.__str__())
		received = sock2.recv(4096)
		messageBid5 = Message(received)
		if (messageBid5.isMessageStatusOk()):
		    print "Bid 5 Created"
		
		bid6 = Bid()
		uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
		idStr = str(uuidId)
		bid6.setValues(idStr, "Provider1", "Service_01")
		bid6.setDecisionVariable("Delay", 0.155)
		bid6.setDecisionVariable("Price", 18)
		bid6.setStatus(Bid.ACTIVE)
		message = bid6.to_message()
		sock2.sendall(message.__str__())
		received = sock2.recv(4096)
		messageBid6 = Message(received)
		if (messageBid6.isMessageStatusOk()):
		    print "Bid 6 Created"

		# Brings the best Bids message and show them according
		messageAsk = Message('')
		messageAsk.setMethod(Message.GET_BEST_BIDS)
		messageAsk.setParameter('Provider', "Provider1")
		messageAsk.setParameter('Service', "Service_01")
		sock2.sendall(messageAsk.__str__())
		received = sock2.recv(16800)
		messageBestBids = Message(received)
		print messageBestBids
		if (messageBestBids.isMessageStatusOk()):
		    document = removeIlegalCharacters(messageBestBids.getBody())
		    try:
			dom = xml.dom.minidom.parseString(document)
			bids = handleBestBids(dom)
			for front in bids:
			    for bid in bids[front]:
				print bid
		    except Exception as e: 
			raise FoundationException(str(e))
		else:
		    raise FoundationException("Best bids not received")

		# Sends the availability for the provider
		messageAvail = Message('')
		messageAvail.setMethod(Message.SEND_AVAILABILITY)
		messageAvail.setParameter("Provider", "Provider1")
		messageAvail.setParameter("Resource", "Bandwidth")
		messageAvail.setParameter("Quantity", "100")
		sock2.sendall(messageAvail.__str__())
		received = sock2.recv(16800)
		messageAvailRes = Message(received)
		if (messageAvailRes.isMessageStatusOk()):
		    print "Availability Received"
		

		# Try to purchase without availability
		messagePurchase = Message('')
		messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
		uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
		idStr = str(uuidId)
		messagePurchase.setParameter('Id', idStr)		
		messagePurchase.setParameter('Service', "Service_01")
		messagePurchase.setParameter('Bid', bid6.getId())
		messagePurchase.setParameter('Quantity', "10")
		messagePurchase.setParameter('Delay', '0.16')
		messagePurchase.setParameter('Price', '17.5')
		sock2.sendall(messagePurchase.__str__())
		received = sock2.recv(16800)
		messagePur1 = Message(received)
		if (messagePur1.isMessageStatusOk()):
		    print bid6.getId() + 'Qua:' + messagePur1.getParameter("Quantity_Purchased")
		

		messagePurchase = Message('')
		messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
		uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
		idStr = str(uuidId)
		messagePurchase.setParameter('Id', idStr)		
		messagePurchase.setParameter('Service', "Service_01")
		messagePurchase.setParameter('Bid', bid4.getId())
		messagePurchase.setParameter('Quantity', "20")
		messagePurchase.setParameter('Delay', '0.125')
		messagePurchase.setParameter('Price', '20.5')
		sock2.sendall(messagePurchase.__str__())
		received = sock2.recv(16800)
		messagePur1 = Message(received)
		if (messagePur1.isMessageStatusOk()):
		    print bid4.getId() + 'Qua:' + messagePur1.getParameter("Quantity_Purchased")

		messagePurchase = Message('')
		messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
		uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
		idStr = str(uuidId)
		messagePurchase.setParameter('Id', idStr)		
		messagePurchase.setParameter('Service', "Service_01")
		messagePurchase.setParameter('Bid', bid4.getId())
		messagePurchase.setParameter('Quantity', "15")
		messagePurchase.setParameter('Delay', '0.125')
		messagePurchase.setParameter('Price', '20.5')
		sock2.sendall(messagePurchase.__str__())
		received = sock2.recv(16800)
		messagePur1 = Message(received)
		if (messagePur1.isMessageStatusOk()):
		    print bid4.getId() + 'Qua:' + messagePur1.getParameter("Quantity_Purchased")

		messagePurchase = Message('')
		messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
		uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
		idStr = str(uuidId)
		messagePurchase.setParameter('Id', idStr)		
		messagePurchase.setParameter('Service', "Service_01")
		messagePurchase.setParameter('Bid', bid6.getId())
		messagePurchase.setParameter('Quantity', "10")
		messagePurchase.setParameter('Delay', '0.16')
		messagePurchase.setParameter('Price', '17')
		sock2.sendall(messagePurchase.__str__())
		received = sock2.recv(16800)
		messagePur1 = Message(received)
		if (messagePur1.isMessageStatusOk()):
		    print bid6.getId() + 'Qua:' + messagePur1.getParameter("Quantity_Purchased")

		messagePurchase = Message('')
		messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
		uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
		idStr = str(uuidId)
		messagePurchase.setParameter('Id', idStr)		
		messagePurchase.setParameter('Service', "Service_01")
		messagePurchase.setParameter('Bid', bid6.getId())
		messagePurchase.setParameter('Quantity', "30")
		messagePurchase.setParameter('Delay', '0.16')
		messagePurchase.setParameter('Price', '17')
		sock2.sendall(messagePurchase.__str__())
		received = sock2.recv(16800)
		messagePur1 = Message(received)
		if (messagePur1.isMessageStatusOk()):
		    print bid6.getId() + 'Qua:' + messagePur1.getParameter("Quantity_Purchased")

		#messagePurchase.setParameter('Id', idStr)
		#messagePurchase.setParameter('Bid', bid.getId())        
		#messagePurchase.setParameter('Quantity', str(quantity))

		bid6.setStatus(Bid.INACTIVE)
		message = bid6.to_message()
		sock2.sendall(message.__str__())
		received = sock2.recv(4096)
		messageBid6 = Message(received)
		if (messageBid6.isMessageStatusOk()):
		    print "Bid 6 Inactivated"

		messagePurchase = Message('')
		messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
		uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
		idStr = str(uuidId)
		messagePurchase.setParameter('Id', idStr)		
		messagePurchase.setParameter('Service', "Service_01")
		messagePurchase.setParameter('Bid', bid6.getId())
		messagePurchase.setParameter('Quantity', "30")
		messagePurchase.setParameter('Delay', '0.16')
		messagePurchase.setParameter('Price', '17')
		sock2.sendall(messagePurchase.__str__())
		received = sock2.recv(16800)
		messagePur1 = Message(received)
		if (messagePur1.isMessageStatusOk()):
		    print bid6.getId() + 'Qua:' + messagePur1.getParameter("Quantity_Purchased")

	    
    # Receive data from the server and shut down
    
    
finally:
	sock.shutdown(socket.SHUT_RDWR)
	sock.close()
