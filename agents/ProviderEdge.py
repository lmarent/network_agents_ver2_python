from foundation.FoundationException import FoundationException
import foundation.agent_properties
import uuid
import logging
import time
from foundation.Agent import AgentServerHandler
from foundation.Agent import Agent
from foundation.Message import Message
from foundation.DecisionVariable import DecisionVariable
from ProviderAgentException import ProviderException
from Provider import Provider
from foundation.Bid import Bid


logger = logging.getLogger('Edge_provider_application')

''' 
The Edge Provider class defines methods to be used by the access provider
agent to purchase offers that are channels on the marketplace. 
    
Initizalize the agent, get the disutility function, and execute the buying
algorithm. 
'''
class ProviderEdge(Provider):
    
    def __init__(self,  strID, Id, serviceId, accessProviderSeed, marketPosition, 
				 adaptationFactor, monopolistPosition, debug, resources, 
				 numberOffers, numAccumPeriods, numAncestors, startFromPeriod):
        try:
            super(ProviderEdge, self).__init__(strID, Id, Agent.PROVIDER_ISP, serviceId, accessProviderSeed, marketPosition, adaptationFactor, monopolistPosition, debug, resources, numberOffers, numAccumPeriods, numAncestors, startFromPeriod)
            logger.debug('Agent: %s - Edge Provider Created', self._list_vars['Id'])
        except FoundationException as e:
            raise ProviderException(e.__str__())
	        	
    ''' 
    The Purchase method assigns all the parameters and access provider ID
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
                logger.debug( 'Agent: %s - Period: %s - Purchase: %s Vendor: %s', 
            				self._list_vars['Id'], str(self._list_vars['Current_Period']), 
            			        idStr, bid.getProvider())
                return True
            else:
                 logger.debug( 'Agent: %s - Period: %s - Not purchase - Vendor: %s Message: %s', 
        				self._list_vars['Id'], str(self._list_vars['Current_Period']), 
        				bid.getProvider(), messageResult.__str__())
                 return False
        else:
            logger.error('Agent: %s - Period: %s - Purchase not received! Communication failed - Message: %s', 
                             self._list_vars['Id'], str(self._list_vars['Current_Period']), messageResult.__str__())
            logger.error('Agent: %s - Period: %s - Purchase not received! Communication failed', 
                         self._list_vars['Id'], str(self._list_vars['Current_Period']))
            raise ProviderException('Purchase not received! Communication failed')
	    
	''' 
	The initialize function is responsible for initializing the 
	access provider agent and get the decision variables from the simulation
	environment (demand server). 
	'''
    def initialize(self):
        logger.debug('Agent: %s - Initilizing consumer', self._list_vars['Id'])
        for decisionVariable in (self._service)._decision_variables:
            ((self._service)._decision_variables[decisionVariable]).executeSample(self._list_vars['Random'])

	'''
	The getDisutility function is responsible for assigning the access provider
	agent a disutility function from the simulation environment (
	demand server)
	'''
    def getDisutility(self, bid):
	logger.debug('Agent: %s - Period: %s - Initiating getDisutility - Bid: %s', 
		    self._list_vars['Id'], str(self._list_vars['Current_Period']), bid.getId())
	disutility_quality = 0 # can be only non negative
	disutility_price = 0 # can be positive or negative
	for decisionVariable in (self._service)._decision_variables:
	    # Obtains the sampled value
	    valueSample = ((self._service)._decision_variables[decisionVariable]).getSample(DecisionVariable.PDST_VALUE)
	    logger.debug('Agent: %s - Decision Variable: %s - Value %s', 
			 self._list_vars['Id'], 
			 decisionVariable, str(valueSample))
	    # Obtains the sampled sensitivity
	    sensitivitySample = ((self._service)._decision_variables[decisionVariable]).getSample(DecisionVariable.PDST_SENSITIVITY)
	    offered = bid.getDecisionVariable(decisionVariable)
	    logger.debug('Agent: %s - Decision Variable %s  Sensitivity: %s - Offered %s', 
			self._list_vars['Id'],  decisionVariable, str(sensitivitySample), str(offered))
	    if (((self._service)._decision_variables[decisionVariable]).getModeling() 
			== DecisionVariable.MODEL_QUALITY):
		
		if (((self._service)._decision_variables[decisionVariable]).getOptimizationObjective() 
			== DecisionVariable.OPT_MAXIMIZE):
		    if offered < valueSample:
			disutility_quality = disutility_quality + (max(0, ((valueSample - offered)/ valueSample))  * sensitivitySample)
		elif (((self._service)._decision_variables[decisionVariable]).getOptimizationObjective() 
			== DecisionVariable.OPT_MINIMIZE):
		    if offered > valueSample:
			disutility_quality = disutility_quality + (max(0, ((offered - valueSample)/ valueSample))  * sensitivitySample)
	    else:
		disutility_price = disutility_price + (((offered - valueSample) / valueSample)  * sensitivitySample)
	logger.debug('Agent: %s - Period: %s - Finishing getDisutility - Disutility price: %s - Disutility Quality', 
		      self._list_vars['Id'], str(self._list_vars['Current_Period']), 
		      str(disutility_price), str(disutility_quality))
	disutility = disutility_price + disutility_quality
	logger.debug('Agent: %s - Period: %s - Finishing getDisutility - Disutility: %s', 
		      self._list_vars['Id'], str(self._list_vars['Current_Period']), str(disutility))
	return disutility
    
    
    def purchase(self, disutilities_sorted):
        for disutility in disutilities_sorted:
            logger.debug('Agent: %s - Period: %s - Front: %s  disutility: %s Nbr Bids: %s Threshold %s', self._list_vars['Id'], str(self._list_vars['Current_Period']), str(front), str(disutility), str(len(evaluatedBids[disutility]) ), str(Threshold) )
            if (disutility < Threshold):
                lenght = len(evaluatedBids[disutility])
                while (lenght > 0):
                    index_rand = (self._list_vars['Random']).randrange(0, lenght)
                    logger.debug('Agent: %s - Period: %s - Index: %d \n', self._list_vars['Id'], str(self._list_vars['Current_Period']), index_rand)
                    bid = evaluatedBids[disutility].pop(index_rand)
                    if (self.purchase(bid, quantity)):
                        purchased = True
                        break
                    else:
                        logger.debug('Agent: %s - Period: %s - Could not purchase: %s', self._list_vars['Id'],  str(self._list_vars['Current_Period']),bid.getId())                            
                        pass
                    lenght = len(evaluatedBids[disutility])
                    if (purchased == True):
                        break
            else:
                logger.debug('Agent: %s - Period: %s - It is not going to buy', self._list_vars['Id'], str(self._list_vars['Current_Period']) ) 
                break
        
    def evaluate_front_bids(self, bidList):
        # Sorts the offerings  based on the customer's needs 
        logger.debug('Agent: %s - Period: %s - Front: %s - Nbr Bids: %s', 
                      self._list_vars['Id'], str(self._list_vars['Current_Period']), 
        			     str(front), str(len(bidList)))
        
        evaluatedBids = {}
        for bid in bidList:
            disutility = self.getDisutility(bid)
            if disutility in evaluatedBids:
                evaluatedBids[disutility].append(bid)
            else:
                evaluatedBids[disutility] = [bid]
            # Purchase based on the disutility order.
            disutilities_sorted = sorted(evaluatedBids)
            purchased = self.purchase(disutilities_sorted)
            if (purchased == True):
                break
            
        
    def exec_resource_purchase():
        dic_return = self.createAskBids(serviceId)
        logger.debug('Agent: %s - Period: %s - Number of fronts: %s', 
		          self._list_vars['Id'], str(self._list_vars['Current_Period']), 
			  str(len(dic_return)))
        purchased = False
	    # Sorts the offerings  based on the customer's needs 
        keys_sorted = sorted(dic_return,reverse=True)
        for front in keys_sorted:
            bidList = dic_return[front]
            purchased = self.evaluate_front_bids(self, bidList):
            if (purchased == True):
                break
        if (purchased == True):
            logger.debug('Agent: %s - Period: %s - Puchase the bid: %s with quantity: \
			       %s in period: %d', self._list_vars['Id'], str(self._list_vars['Current_Period']),
			       bid.getId(), str(quantity), self._list_vars['Current_Period'])            
        else:
            logger.debug(' Agent: %s - Period: %s - could not puchase', 
		   self._list_vars['Id'], str(self._list_vars['Current_Period']))
        
        logger.debug('Agent: %s - Period: %s - Ending exec_algorithm',
		     self._list_vars['Id'], str(self._list_vars['Current_Period']))
        

    '''
    Execute the purchase process for the access network agent
    '''
    def exec_purchases(self, resources):
        Threshold = foundation.agent_properties.threshold
        serviceId = (self._service).getId()
        for resourceId in resources:        
        dic_return = self.createAskBids(serviceId)
        logger.debug('Agent: %s - Period: %s - Number of fronts: %s', 
		          self._list_vars['Id'], str(self._list_vars['Current_Period']), 
			  str(len(dic_return)))
        purchased = False
	    # Sorts the offerings  based on the customer's needs 
        keys_sorted = sorted(dic_return,reverse=True)
        for front in keys_sorted:
            bidList = dic_return[front]
            logger.debug('Agent: %s - Period: %s - Front: %s - Nbr Bids: %s', 
        			     self._list_vars['Id'], str(self._list_vars['Current_Period']), 
        			     str(front), str(len(bidList)))
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
                logger.debug('Agent: %s - Period: %s - Front: %s  disutility: %s Nbr Bids: %s Threshold %s', 
        			         self._list_vars['Id'], str(self._list_vars['Current_Period']), 
                          str(front), str(disutility), str(len(evaluatedBids[disutility]) ), 
            				 str(Threshold) )

                if (disutility < Threshold): 
                    lenght = len(evaluatedBids[disutility])
                    while (lenght > 0):
                        index_rand = (self._list_vars['Random']).randrange(0, lenght)
                        logger.debug('Agent: %s - Period: %s - Index: %d \n', 
            					  self._list_vars['Id'], str(self._list_vars['Current_Period']),
            					  index_rand)
                        bid = evaluatedBids[disutility].pop(index_rand)
                        if (self.purchase(bid, quantity)):
                            purchased = True
                            break
                        else:
                            logger.debug('Agent: %s - Period: %s - Could not purchase: %s', 
                					      self._list_vars['Id'],  str(self._list_vars['Current_Period']),
                					      bid.getId())                            
                            pass
                        lenght = len(evaluatedBids[disutility])
                    if (purchased == True):
                        break
                else:
                    logger.debug('Agent: %s - Period: %s - It is not going to buy', 
        				      self._list_vars['Id'], str(self._list_vars['Current_Period']) ) 
                    break
            if (purchased == True):
                break
        if (purchased == True):
            logger.debug('Agent: %s - Period: %s - Puchase the bid: %s with quantity: \
			       %s in period: %d', self._list_vars['Id'], str(self._list_vars['Current_Period']),
			       bid.getId(), str(quantity), self._list_vars['Current_Period'])            
        else:
            logger.debug(' Agent: %s - Period: %s - could not puchase', 
		   self._list_vars['Id'], str(self._list_vars['Current_Period']))
        
        logger.debug('Agent: %s - Period: %s - Ending exec_algorithm',
		     self._list_vars['Id'], str(self._list_vars['Current_Period']))
        
    
    def create_forecast(self, staged_bids):
        logger.debug('Start - create forecast')
        res_resources = {}
        for bidId in staged_bids:            
            action = (staged_bids[bidId])['Action']
            if (action == Bid.ACTIVE):
                bid = (staged_bids[bidId])['Object']
                resources = self.calculateBidResources(bid)
                for resourceId in resources:
                    res_resources[resourceId].setdefault(0)
                    res_resources[resourceId] += (1 + resources[resourceId] )
        return res_resources
        logger.debug('Ending - create forecast')
    
    def set_initial_bids(self):
        '''
        Initialize bids for customers
        '''
        marketPosition = self._used_variables['marketPosition']
        initialNumberBids = self._used_variables['initialNumberBids']
        return self.initializeBids(marketPosition, initialNumberBids) 
    
    def update_bids(self, staged_bids, fileResult):
        '''
        Update bids for customers given te previous history.
        '''
        
        # By assumption providers at this point have the bid usage updated.
        summarizedUsage = self.sumarizeBidUsage() 
        self.replaceDominatedBids(staged_bids) 
        if (self.canAdoptStrongPosition(fileResult)):
            self.moveBetterProfits(summarizedUsage, staged_bids, fileResult)
        else:
            self.moveForMarketShare(summarizedUsage, staged_bids, fileResult)        
                

	'''
	The exec_algorithm function finds available offerings and chooses
	the one that fits the access provider needs the best, based on the prior 
	signals received by the simulation environment (demand server).
	'''
    def exec_algorithm(self):
        logger.info('Agent: %s - Period %s - Initiating exec_algorithm ', 
		    self._list_vars['Id'], str(self._list_vars['Current_Period'])  )          
        staged_bids = {}
        if (self._list_vars['State'] == AgentServerHandler.BID_PERMITED):
            fileResult = open(self._list_vars['Id'] + '.log',"a")
             # Sends the request to the market place to find the best offerings             
             # This executes offers for the provider
            if (len(self._list_vars['Bids']) == 0):
                 staged_bids = self.set_initial_bids()
            else:
                 self.update_bids(staged_bids, fileResult)
            self.eliminateNeighborhoodBid(staged_bids, fileResult)
            self.registerLog(fileResult, 'The Final Number of Staged offers is:' + str(len(staged_bids)) ) 
            self.sendBids(staged_bids, fileResult) #Pending the status of the bid.
            self.purgeBids(staged_bids, fileResult)
            resources = self.create_forecast(staged_bids)
            fileResult.close()
                 
            # This executes the purchase part for this provider
            self.exec_purchases(resources) 
        self._list_vars['State'] = AgentServerHandler.IDLE
		
		
	
	
# End of Access provider class
