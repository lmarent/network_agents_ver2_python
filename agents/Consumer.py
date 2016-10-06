from __future__ import division
from foundation.Message import Message
from foundation.Bid import Bid
from foundation.Agent import Agent
from foundation.Service import Service
from foundation.DecisionVariable import DecisionVariable
from ProviderAgentException import ProviderException
from foundation.FoundationException import FoundationException
from foundation.AgentServer import AgentServerHandler
from foundation.AgentType import AgentType

import foundation.agent_properties
import uuid
import logging
import logging.handlers
import time
import xml.dom.minidom
from math import fabs
import os
import threading


LOG_FILENAME = 'customer.log'
# Check if log exists and should therefore be rolled
needRoll = os.path.isfile(LOG_FILENAME)

logger = logging.getLogger('consumer_application')

logger.setLevel(logging.DEBUG)
fh = logging.handlers.RotatingFileHandler(LOG_FILENAME, backupCount=5)
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(threadName)-10s) - (asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

# This is a stale log, so roll it
if needRoll:
	# Roll over on application start
    logger.handlers[0].doRollover()



class Consumer(Agent):
    ''' 
    The Consumer class defines methods to be used by the consumer
    agent to purchase offers on the marketplace, initizalize the
    agent, get the disutility function, and execute the buying
    algorithm. 
    '''

    
    def __init__(self, strID, Id, serviceId, customer_seed):
        try:
            
            self.lock = threading.RLock()
            agent_type = AgentType(AgentType.CONSUMER_TYPE)                                           
            super(Consumer, self).__init__(strID, Id, agent_type, serviceId, customer_seed,' ',' ', ' ', ' ', self.lock)
            
            logger.debug('Agent: %s - Consumer Created', self._list_vars['strId'])
        except FoundationException as e:
            raise ProviderException(e.__str__())

    ''' 
    Create the purchase message without indicating bid and quantity.
    '''
    def createPurchaseMessage(self):
        messagePurchase = Message('')
        messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
        uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
        idStr = str(uuidId)
        messagePurchase.setParameter('Id', idStr)
        messagePurchase.setParameter('Service', self._service.getId())
        return messagePurchase
     	
    ''' 
    The Purchase method assigns all the parameters and consumer ID
	to the message to be send to the Marketplace.
	In the end, the function sends the message to the marketplace
	and checks if it was succesfully received. 
    '''
    def purchase(self, messagePurchase, bid, quantity):
        
        # Copy basic data from the purchase message given as parameter.        
        message = Message('')
        message.setMethod(Message.RECEIVE_PURCHASE)
        message.setParameter('Id', messagePurchase.getParameter('Id'))
        message.setParameter('Service', messagePurchase.getParameter('Service'))
        
        # Set the rest of the data from the bid and quantity given as parameters.        
        message.setParameter('Bid', bid.getId())        
        message.setParameter('Quantity', str(quantity))
        for decisionVariable in (self._service)._decision_variables:
            value = ((self._service)._decision_variables[decisionVariable]).getSample(DecisionVariable.PDST_VALUE)
            message.setParameter(decisionVariable, str(value))
        messageResult = self.sendMessageMarket(message)

        # Check if message was succesfully received by the marketplace
        if messageResult.isMessageStatusOk():
            quantity = float(messageResult.getParameter("Quantity_Purchased"))
            return quantity
        else:
            # logger.error('Agent: %s - Period: %s - Purchase not received! Communication failed - Message: %s', self._list_vars['strId'], str(self._list_vars['Current_Period']), messageResult.__str__())
            raise ProviderException('Purchase not received! Communication failed')
	    
    def initialize(self):
	''' 
	The initialize function is responsible for initializing the 
	consumer agent and get the decision variables from the simulation
	environment (demand server). 
	'''
        logger.debug('Period: %s Agent: %s - Initilizing consumer', str(self._list_vars['Current_Period']), self._list_vars['strId'])
        for decisionVariable in (self._service)._decision_variables:
            ((self._service)._decision_variables[decisionVariable]).executeSample(self._list_vars['Random'])

    '''
    The getDisutility function is responsible for assigning the consumer
    agent a disutility function from the simulation environment (
    demand server)
    '''
    def getDisutility(self, bid):
        # logger.debug('Agent: %s - Period: %s - Initiating getDisutility - Bid: %s', self._list_vars['strId'], str(self._list_vars['Current_Period']), bid.getId())
        disutility_quality = 0 # can be only non negative
        disutility_price = 0 # can be positive or negative
        for decisionVariable in (self._service)._decision_variables:
            # Obtains the sampled value
            valueSample = ((self._service)._decision_variables[decisionVariable]).getSample(DecisionVariable.PDST_VALUE)
            # logger.debug('Agent: %s - Decision Variable: %s - Value %s', self._list_vars['strId'], decisionVariable, str(valueSample))
            # Obtains the sampled sensitivity
            sensitivitySample = ((self._service)._decision_variables[decisionVariable]).getSample(DecisionVariable.PDST_SENSITIVITY)
            offered = bid.getDecisionVariable(decisionVariable)
            # logger.debug('Agent: %s - Decision Variable %s  Sensitivity: %s - Offered %s', self._list_vars['strId'],  decisionVariable, str(sensitivitySample), str(offered))
            if (((self._service)._decision_variables[decisionVariable]).getModeling() == DecisionVariable.MODEL_QUALITY):        		
                if (((self._service)._decision_variables[decisionVariable]).getOptimizationObjective() == DecisionVariable.OPT_MAXIMIZE):
                    if offered < valueSample:
                        disutility_quality = disutility_quality + (max(0, ((valueSample - offered)/ valueSample))  * sensitivitySample)
                elif (((self._service)._decision_variables[decisionVariable]).getOptimizationObjective() == DecisionVariable.OPT_MINIMIZE):
                    if offered > valueSample:
                        disutility_quality = disutility_quality + (max(0, ((offered - valueSample)/ valueSample))  * sensitivitySample)
            else:
                disutility_price = disutility_price + (((offered - valueSample) / valueSample)  * sensitivitySample)
        # logger.debug('Agent: %s - Period: %s - Finishing getDisutility - Disutility price: %s - Disutility Quality %s', str(self._list_vars['strId']), str(self._list_vars['Current_Period']), str(disutility_price), str(disutility_quality))       
        disutility = disutility_price + disutility_quality
        # logger.debug('Agent: %s - Period: %s - Finishing getDisutility - Disutility: %s', str(self._list_vars['strId']), str(self._list_vars['Current_Period']), str(disutility)) 
        return disutility
    

	'''
	The exec_algorithm function finds available offerings and chooses
	the one that fits the consumer needs the best, based on the prior 
	signals received by the simulation environment (demand server).
	'''
    def exec_algorithm(self):
        Threshold = foundation.agent_properties.threshold
        # logger.debug('Agent: %s - Period %s - Initiating exec_algorithm ', self._list_vars['strId'], str(self._list_vars['Current_Period'])  )
        if (self._list_vars['State'] == AgentServerHandler.ACTIVATE):
            # Sends the request to the market place to find the best offerings
            serviceId = (self._service).getId()
            dic_return = self.createAskBids(serviceId)
            parameters = self._list_vars['Parameters']
            quantity = parameters['quantity']
            # logger.debug('Agent: %s - Period: %s - Number of fronts: %s', self._list_vars['strId'], str(self._list_vars['Current_Period']), str(len(dic_return)))
            purchased = False
            # Sorts the offerings  based on the customer's needs 
            keys_sorted = sorted(dic_return,reverse=True)
            purchaseMessage = self.createPurchaseMessage()
            bidId = ' '
            evaluatedBids = {}
            numBids = 0 

            # Get bids available for purchasing.
            for front in keys_sorted:
                bidList = dic_return[front]
                # logger.debug('Agent: %s - Period: %s - Front: %s - Nbr Bids: %s', self._list_vars['strId'], str(self._list_vars['Current_Period']), str(front), str(len(bidList)))

                for bid in bidList:
                    disutility = self.getDisutility(bid)
                    if disutility < Threshold:
                         numBids  = numBids + 1
                         if disutility in evaluatedBids:
                             evaluatedBids[disutility].append(bid)
                         else:
                             evaluatedBids[disutility] = [bid]
            disutilities_sorted = sorted(evaluatedBids)

            # Purchase quantities requested.
            for disutility in disutilities_sorted:
                # logger.debug('Agent: %s - Period: %s - Front: %s  disutility: %s Nbr Bids: %s Threshold %s', self._list_vars['strId'], str(self._list_vars['Current_Period']), str(front), str(disutility), str(len(evaluatedBids[disutility]) ), str(Threshold) )
                lenght = len(evaluatedBids[disutility])
                while (lenght > 0) and (quantity > 0) :
                    index_rand = (self._list_vars['Random']).randrange(0, lenght)
                    # logger.debug('Agent: %s - Period: %s - Index: %d \n', self._list_vars['strId'], str(self._list_vars['Current_Period']),index_rand)
                    bid = evaluatedBids[disutility].pop(index_rand)
                    qtyPurchased = self.purchase(purchaseMessage, bid, quantity)
                    # Register the bid as purchased.                    
                    if qtyPurchased > 0:
                        bidId = bidId + ',' + bid.getId()

                    # update quantities.
                    if (qtyPurchased >= quantity):
                        quantity = 0
                        break
                    else:
                        quantity = quantity - qtyPurchased


                    lenght = len(evaluatedBids[disutility])
                if (quantity == 0):
                    break

            qtyPurchased = parameters['quantity'] - quantity
            logger.debug('Agent: %s - :Period: %s - :AvailBids: %s :initial qty:%s :qty_purchased:%s :Purchase the bid: %s', self._list_vars['strId'], str(self._list_vars['Current_Period']), str(numBids), str(parameters['quantity']), str(qtyPurchased), bidId )
        else:
            logger.debug(' Agent: %s - Period: %s - could not puchase', self._list_vars['strId'], str(self._list_vars['Current_Period']))

            # logger.debug('Agent: %s - Period: %s - Ending exec_algorithm',self._list_vars['strId'], str(self._list_vars['Current_Period']))
	'''
	The run method activates the avaiable consumer agents.
	'''
    def run(self):
        proc_name = self.name
        self.start_agent()
        while (True):
            if (self._list_vars['State'] == AgentServerHandler.TERMINATE):
                break
            else:
                if (self._list_vars['State'] == AgentServerHandler.TO_BE_ACTIVED):
                    self.initialize()
                    logger.debug('Agent: %s - Initialized' , self._list_vars['strId'])
                    self._list_vars['State'] = AgentServerHandler.ACTIVATE
                    logger.debug('Agent: %s - Now in state %s' , self._list_vars['strId'], self._list_vars['State'])
                    self.exec_algorithm()
                    self._list_vars['State'] = AgentServerHandler.IDLE
                elif (self._list_vars['State'] == AgentServerHandler.IDLE):
                    time.sleep(0.1)
        # logger.debug('Agent: %s - Shuting down', self._list_vars['strId'])
        # Close the sockets
        self.stop_agent()
        return
		

# End of Provider class
