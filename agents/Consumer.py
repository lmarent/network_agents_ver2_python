from __future__ import division
from foundation.Message import Message
from foundation.Bid import Bid
from foundation.Agent import Agent
from foundation.Agent import AgentServerHandler
from foundation.Service import Service
from foundation.DecisionVariable import DecisionVariable
from ProviderAgentException import ProviderException
from foundation.FoundationException import FoundationException
import foundation.agent_properties
import uuid
import logging
import time
import xml.dom.minidom
from math import fabs

logger = logging.getLogger('consumer_application')


class Consumer(Agent):
    ''' 
    The Consumer class defines methods to be used by the consumer
    agent to purchase offers on the marketplace, initizalize the
    agent, get the disutility function, and execute the buying
    algorithm. 
    '''
    
    def __init__(self, strID, Id, serviceId, customer_seed):
        try:
        	    super(Consumer, self).__init__(strID, Id, 'consumer', serviceId, customer_seed,' ',' ', ' ')
        	    logger.debug('Agent: %s - Consumer Created', self._list_vars['strId'])
        except FoundationException as e:
            raise ProviderException(e.__str__())
	        	
    ''' 
    The Purchase method assigns all the parameters and consumer ID
	to the message to be send to the Marketplace.
	In the end, the function sends the message to the marketplace
	and checks if it was succesfully received. 
    '''
    def purchase(self, bid, quantity):
        messagePurchase = Message('')
        messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
        uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
        idStr = str(uuidId)
        messagePurchase.setParameter('Id', idStr)
        messagePurchase.setParameter('Service', self._service.getId())        
        messagePurchase.setParameter('Bid', bid.getId())        
        messagePurchase.setParameter('Quantity', str(quantity))
        for decisionVariable in (self._service)._decision_variables:
        	    value = ((self._service)._decision_variables[decisionVariable]).getSample(DecisionVariable.PDST_VALUE)
        	    messagePurchase.setParameter(decisionVariable, str(value))
        messageResult = self._channelMarketPlace.sendMessage(messagePurchase)
        # Check if message was succesfully received by the marketplace
        if messageResult.isMessageStatusOk():
            quantity = float(messageResult.getParameter("Quantity_Purchased"))
            if quantity > 0:
                logger.debug( 'Agent: %s - Period: %s - Purchase: %s Vendor: %s', self._list_vars['strId'], str(self._list_vars['Current_Period']), idStr, bid.getProvider())
                return True
            else: 
            		logger.debug( 'Agent: %s - Period: %s - Not purchase - Vendor: %s Message: %s', 
            				self._list_vars['strId'], str(self._list_vars['Current_Period']), 
            				bid.getProvider(), messageResult.__str__())
            		return False
        else:
        	    logger.error('Agent: %s - Period: %s - Purchase not received! Communication failed - Message: %s', 
        			  self._list_vars['strId'], str(self._list_vars['Current_Period']), messageResult.__str__())
        			  
        	    logger.error('Agent: %s - Period: %s - Purchase not received! Communication failed', 
        			  self._list_vars['strId'], str(self._list_vars['Current_Period']))
                    raise ProviderException('Purchase not received! Communication failed')
	    
    def initialize(self):
	''' 
	The initialize function is responsible for initializing the 
	consumer agent and get the decision variables from the simulation
	environment (demand server). 
	'''
        logger.debug('Agent: %s - Initilizing consumer', self._list_vars['strId'])
        for decisionVariable in (self._service)._decision_variables:
            ((self._service)._decision_variables[decisionVariable]).executeSample(self._list_vars['Random'])

    '''
    The getDisutility function is responsible for assigning the consumer
    agent a disutility function from the simulation environment (
    demand server)
    '''
    def getDisutility(self, bid):
        logger.debug('Agent: %s - Period: %s - Initiating getDisutility - Bid: %s', self._list_vars['strId'], str(self._list_vars['Current_Period']), bid.getId())
        disutility_quality = 0 # can be only non negative
        disutility_price = 0 # can be positive or negative
        for decisionVariable in (self._service)._decision_variables:
            # Obtains the sampled value
            valueSample = ((self._service)._decision_variables[decisionVariable]).getSample(DecisionVariable.PDST_VALUE)
            logger.debug('Agent: %s - Decision Variable: %s - Value %s', self._list_vars['strId'], decisionVariable, str(valueSample))
            # Obtains the sampled sensitivity
            sensitivitySample = ((self._service)._decision_variables[decisionVariable]).getSample(DecisionVariable.PDST_SENSITIVITY)
            offered = bid.getDecisionVariable(decisionVariable)
            logger.debug('Agent: %s - Decision Variable %s  Sensitivity: %s - Offered %s', self._list_vars['strId'],  decisionVariable, str(sensitivitySample), str(offered))
            if (((self._service)._decision_variables[decisionVariable]).getModeling() == DecisionVariable.MODEL_QUALITY):        		
                if (((self._service)._decision_variables[decisionVariable]).getOptimizationObjective() == DecisionVariable.OPT_MAXIMIZE):
                    if offered < valueSample:
                        disutility_quality = disutility_quality + (max(0, ((valueSample - offered)/ valueSample))  * sensitivitySample)
                elif (((self._service)._decision_variables[decisionVariable]).getOptimizationObjective() == DecisionVariable.OPT_MINIMIZE):
                    if offered > valueSample:
                        disutility_quality = disutility_quality + (max(0, ((offered - valueSample)/ valueSample))  * sensitivitySample)
            else:
                disutility_price = disutility_price + (((offered - valueSample) / valueSample)  * sensitivitySample)
        logger.debug('Agent: %s - Period: %s - Finishing getDisutility - Disutility price: %s - Disutility Quality %s', str(self._list_vars['strId']), str(self._list_vars['Current_Period']), str(disutility_price), str(disutility_quality))       
        disutility = disutility_price + disutility_quality
        logger.debug('Agent: %s - Period: %s - Finishing getDisutility - Disutility: %s', str(self._list_vars['strId']), str(self._list_vars['Current_Period']), str(disutility)) 
        return disutility

	'''
	The exec_algorithm function finds available offerings and chooses
	the one that fits the consumer needs the best, based on the prior 
	signals received by the simulation environment (demand server).
	'''
    def exec_algorithm(self):
        Threshold = foundation.agent_properties.threshold
        logger.debug('Agent: %s - Period %s - Initiating exec_algorithm ', self._list_vars['strId'], str(self._list_vars['Current_Period'])  )
        if (self._list_vars['State'] == AgentServerHandler.ACTIVATE):
            # Sends the request to the market place to find the best offerings
            serviceId = (self._service).getId()
            dic_return = self.createAskBids(serviceId)
            parameters = self._list_vars['Parameters']
            quantity = parameters['quantity']        	    
            logger.debug('Agent: %s - Period: %s - Number of fronts: %s', self._list_vars['strId'], str(self._list_vars['Current_Period']), str(len(dic_return)))
            purchased = False
            # Sorts the offerings  based on the customer's needs 
            keys_sorted = sorted(dic_return,reverse=True)
            for front in keys_sorted:
                bidList = dic_return[front]
                logger.debug('Agent: %s - Period: %s - Front: %s - Nbr Bids: %s', self._list_vars['strId'], str(self._list_vars['Current_Period']), str(front), str(len(bidList)))
                bestUtility = -1
                altervative_found = False
                evaluatedBids = {}
                for bid in bidList:
                    disutility = self.getDisutility(bid)
                    if disutility in evaluatedBids:
                        evaluatedBids[disutility].append(bid)
                    else:
                        evaluatedBids[disutility] = [bid]
                # Purchase based on the disutility order.
                disutilities_sorted = sorted(evaluatedBids)
                for disutility in disutilities_sorted:
                    logger.debug('Agent: %s - Period: %s - Front: %s  disutility: %s Nbr Bids: %s Threshold %s', self._list_vars['strId'], str(self._list_vars['Current_Period']), str(front), str(disutility), str(len(evaluatedBids[disutility]) ), str(Threshold) )
                    if (disutility < Threshold): 
                        lenght = len(evaluatedBids[disutility])
                        while (lenght > 0):
                            index_rand = (self._list_vars['Random']).randrange(0, lenght)
                            logger.debug('Agent: %s - Period: %s - Index: %d \n', self._list_vars['strId'], str(self._list_vars['Current_Period']),index_rand)
                            bid = evaluatedBids[disutility].pop(index_rand)
                            if (self.purchase(bid, quantity)):
                                purchased = True
                                break
                            else:
                                logger.debug('Agent: %s - Period: %s - Could not purchase: %s', self._list_vars['strId'],  str(self._list_vars['Current_Period']),bid.getId())
                                pass
                            lenght = len(evaluatedBids[disutility])
                        if (purchased == True):
                            break
                    else:
                        logger.debug('Agent: %s - Period: %s - It is not going to buy', self._list_vars['strId'], str(self._list_vars['Current_Period']) ) 
                        break
                if (purchased == True):
                    break
            if (purchased == True):
                logger.debug('Agent: %s - Period: %s - Puchase the bid: %s with quantity: %s in period: %d', self._list_vars['strId'], str(self._list_vars['Current_Period']),bid.getId(), str(quantity), self._list_vars['Current_Period'])
        else:
            logger.debug(' Agent: %s - Period: %s - could not puchase', self._list_vars['strId'], str(self._list_vars['Current_Period']))
        
        logger.debug('Agent: %s - Period: %s - Ending exec_algorithm',self._list_vars['strId'], str(self._list_vars['Current_Period']))
		
	'''
	The run method activates the avaiable consumer agents.
	'''
    def run(self):
        proc_name = self.name
        self.start_listening()
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
        logger.debug('Agent: %s - Shuting down', self._list_vars['strId'])
        # Close the sockets
        self._server.stop()
        self._channelMarketPlace.close()
        self._channelClockServer.close()
        return		
		
	
	
# End of Provider class
