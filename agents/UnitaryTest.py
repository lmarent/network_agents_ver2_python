from __future__ import division
from foundation.Message import Message
from foundation.Bid import Bid
from foundation.Agent import Agent
from foundation.FoundationException import FoundationException
from foundation.Agent import AgentServerHandler
from foundation.DecisionVariable import DecisionVariable
from ProviderAgentException import ProviderException
import logging
import math
import operator
import random
import time
import uuid
import xml.dom.minidom
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO,
                    format='(%(threadName)-10s) %(message)s',
                    )


class Presenter_Test(Agent):
    '''
    The Provider class defines methods to be used by the service
    provider agent. It includes methods for pricing and quality
    strategies, place offerings into the marketplace, get other 
    providers offerings and determine the best strategy to capture 
    more market share.    
    '''

    def __init__(self, strID, Id, serviceId):
	try:
	    super(Presenter_Test, self).__init__(strID, Id, 'provider', serviceId) 
	    self._provider_colors = {}   # maintains the colors used for providers.

	    logging.info('Initializing the agent:' + strID )

	except FoundationException as e:
	    raise ProviderException(e.__str__())
    

    def isDominated(self, bid, competitorBid):	
	strict_dom_dimensions = 0
	non_strict_dom_dimensions = 0
	for decisionVariable in bid._decision_variables:
	    ownValue = bid.getDecisionVariable(decisionVariable)
	    compValue = competitorBid.getDecisionVariable(decisionVariable)
	    if (((self._service)._decision_variables[decisionVariable]).getOptimizationObjective() 
		    == DecisionVariable.OPT_MINIMIZE):
		print decisionVariable + 'In minimize'
		ownValue = ownValue * -1
		compValue = compValue * -1
	    
	    if (ownValue <= compValue):
		non_strict_dom_dimensions +=1
		if (ownValue < compValue):
		    strict_dom_dimensions +=1
	# We said that the provider bid is dominated if forall decision variables
	# the value is less of equal to the corresponding value, and at least in 
	# one decision variable is strictly less.
	print 'non_strict_dom_dimensions' + str(non_strict_dom_dimensions)
	print 'strict_dom_dimensions' + str(strict_dom_dimensions)
	if ((non_strict_dom_dimensions == len(bid._decision_variables)) and
	    ( strict_dom_dimensions > 0)):
	    return True
	else:
	    return False

							    	 
    def run(self):
	'''
	The run method is responsible for activate the socket to send 
	the offer to the marketplace. Then, close down the sockets
	to the marketplace and the simulation environment (demand server).
	'''
        proc_name = self.name
        self.start_listening()
	print 'Go to exec_algorithm, state:' + str(self._list_vars['State'])
	try:

		# creates bids for the service 01
		bid = Bid()
		idStr = 'Bid1'
		bid.setValues(idStr, self._list_vars['strId'], "Service_01")
		bid.setDecisionVariable("Delay", 0.145)
		bid.setDecisionVariable("Price", 20)
		bid.setStatus(Bid.ACTIVE)
		message = bid.to_message()
		messageBid = self._channelMarketPlace.sendMessage(message)
		if (messageBid.isMessageStatusOk()):
		    print "Ok - It is registering bids fine"
		
		messageBid2 = self._channelMarketPlace.sendMessage(message)
		if (messageBid2.isMessageStatusOk() == False):
		    if (int(messageBid2.getParameter("Status_Code"))==310):
			print "Ok - it is identifying duplicate bids"
		
		# Now we try to create many bid so we can verify the pareto front.
		bid3 = Bid()
		idStr = 'Bid3'
		bid3.setValues(idStr, self._list_vars['strId'], "Service_01")
		bid3.setDecisionVariable("Delay", 0.16)
		bid3.setDecisionVariable("Price", 18)
		bid3.setStatus(Bid.ACTIVE)
		message = bid3.to_message()
		messageBid3 = self._channelMarketPlace.sendMessage(message)
		if (messageBid3.isMessageStatusOk()):
		    print "Bid 3 Created"

		bid4 = Bid()
		idStr = 'Bid4'
		bid4.setValues(idStr, self._list_vars['strId'], "Service_01")
		bid4.setDecisionVariable("Delay", 0.167)
		bid4.setDecisionVariable("Price", 16.6)
		bid4.setStatus(Bid.ACTIVE)
		message = bid4.to_message()
		messageBid4 = self._channelMarketPlace.sendMessage(message)
		if (messageBid4.isMessageStatusOk()):
		    print "Bid 4 Created"
		
		bid5 = Bid()
		idStr = 'Bid5'
		bid5.setValues(idStr, self._list_vars['strId'], "Service_01")
		bid5.setDecisionVariable("Delay", 0.15)
		bid5.setDecisionVariable("Price", 19.5)
		bid5.setStatus(Bid.ACTIVE)
		message = bid5.to_message()
		messageBid5 = self._channelMarketPlace.sendMessage(message)
		if (messageBid5.isMessageStatusOk()):
		    print "Bid 5 Created"
		
		bid6 = Bid()
		idStr = 'Bid6'
		bid6.setValues(idStr, self._list_vars['strId'], "Service_01")
		bid6.setDecisionVariable("Delay", 0.18)
		bid6.setDecisionVariable("Price", 15.5)
		bid6.setStatus(Bid.ACTIVE)
		message = bid6.to_message()
		messageBid6 = self._channelMarketPlace.sendMessage(message)
		if (messageBid6.isMessageStatusOk()):
		    print "Bid 6 Created"

		'''
		# Brings the best Bids message and show them according
		messageAsk = Message('')
		messageAsk.setMethod(Message.GET_BEST_BIDS)
		messageAsk.setParameter('Provider', "Provider1")
		messageAsk.setParameter('Service', "Service_01")
		messageBestBids = self._channelMarketPlace.sendMessage(messageAsk)
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
		'''
		
		# Sends the availability for the provider
		messageAvail = Message('')
		messageAvail.setMethod(Message.SEND_AVAILABILITY)
		messageAvail.setParameter("Provider", self._list_vars['strId'])
		messageAvail.setParameter("Resource", "Bandwidth")
		messageAvail.setParameter("Quantity", "100")
		messageAvailRes = self._channelMarketPlace.sendMessage(messageAvail)
		print "Here we are" + messageAvailRes.__str__()
		if (messageAvailRes.isMessageStatusOk()):
		    print "Availability Received"
		
		
		bid7 = Bid()
		idStr = 'Bid7'
		bid7.setValues(idStr, self._list_vars['strId'], "Service_01")
		bid7.setDecisionVariable("Delay", 0.17)
		bid7.setDecisionVariable("Price", 15.5)
		bid7.setStatus(Bid.ACTIVE)

		bid8 = Bid()
		idStr = 'Bid8'
		bid8.setValues(idStr, self._list_vars['strId'], "Service_01")
		bid8.setDecisionVariable("Delay", 0.18)
		bid8.setDecisionVariable("Price", 15.5)
		bid8.setStatus(Bid.ACTIVE)

		dominated = self.isDominated(bid7, bid8)
		if (dominated == True):
		    print 'Error in domination function'
		else:
		    print 'Ok domination function' 

		bid7 = Bid()
		idStr = 'Bid7'
		bid7.setValues(idStr, self._list_vars['strId'], "Service_01")
		bid7.setDecisionVariable("Delay", 0.17)
		bid7.setDecisionVariable("Price", 15.5)
		bid7.setStatus(Bid.ACTIVE)

		bid8 = Bid()
		idStr = 'Bid8'
		bid8.setValues(idStr, self._list_vars['strId'], "Service_01")
		bid8.setDecisionVariable("Delay", 0.18)
		bid8.setDecisionVariable("Price", 15.5)
		bid8.setStatus(Bid.ACTIVE)

		dominated = self.isDominated(bid8, bid7)
		if (dominated == True):
		    print 'Ok domination function' 
		else:
		    print 'Error in domination function'

		bid7 = Bid()
		idStr = 'Bid7'
		bid7.setValues(idStr, self._list_vars['strId'], "Service_01")
		bid7.setDecisionVariable("Delay", 0.17)
		bid7.setDecisionVariable("Price", 16.5)
		bid7.setStatus(Bid.ACTIVE)

		bid8 = Bid()
		idStr = 'Bid8'
		bid8.setValues(idStr, self._list_vars['strId'], "Service_01")
		bid8.setDecisionVariable("Delay", 0.18)
		bid8.setDecisionVariable("Price", 15.5)
		bid8.setStatus(Bid.ACTIVE)

		dominated = self.isDominated(bid8, bid7)
		if (dominated == True):
		    print 'Error in domination function'
		else:
		    print 'Ok domination function'  

		bid7 = Bid()
		idStr = 'Bid7'
		bid7.setValues(idStr, self._list_vars['strId'], "Service_01")
		bid7.setDecisionVariable("Delay", 0.17)
		bid7.setDecisionVariable("Price", 16.5)
		bid7.setStatus(Bid.ACTIVE)

		bid8 = Bid()
		idStr = 'Bid8'
		bid8.setValues(idStr, self._list_vars['strId'], "Service_01")
		bid8.setDecisionVariable("Delay", 0.18)
		bid8.setDecisionVariable("Price", 15.5)
		bid8.setStatus(Bid.ACTIVE)

		dominated = self.isDominated(bid7, bid8)
		if (dominated == True):
		    print 'Error in domination function'
		else:
		    print 'Ok domination function'  
		    


		'''
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
		messagePur1 = self._channelMarketPlace.sendMessage(messagePurchase)
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
		messagePur1 = self._channelMarketPlace.sendMessage(messagePurchase)
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
		messagePur1 = self._channelMarketPlace.sendMessage(messagePurchase)
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
		messagePur1 = self._channelMarketPlace.sendMessage(messagePurchase)
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
		messagePur1 = self._channelMarketPlace.sendMessage(messagePurchase)
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
		'''
	except Exception as e:
	    print e.message

	finally:
	    # Close the sockets
	    self._server.stop()
	    self._channelMarketPlace.close()
	    self._channelClockServer.close()
	    return		
		
	
	
# End of Provider class
