from foundation.FoundationException import FoundationException
import foundation.agent_properties
import uuid
import logging
from foundation.Agent import AgentServerHandler
from foundation.Agent import Agent
from foundation.Message import Message
from foundation.DecisionVariable import DecisionVariable
from ProviderAgentException import ProviderException
from Provider import Provider
from foundation.Bid import Bid
import MySQLdb



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
            logger.debug('Agent: %s - Edge Provider Created', self._list_vars['strId'])
        except FoundationException as e:
            raise ProviderException(e.__str__())


	''' 
	The initialize function is responsible for initializing the 
	edge provider agent and get the decision variables from the simulation
	environment (demand server). 
	'''
    def initialize(self):
        logger.debug('Agent: %s - Initilizing provider', self._list_vars['strId'])
        for decisionVariable in (self._service)._decision_variables:
            ((self._service)._decision_variables[decisionVariable]).executeSample(self._list_vars['Random'])
        #Bring services required to fulfill resources.
        # Open database connection
        db = MySQLdb.connect("localhost","root","password","Network_Simulation" )

        # prepare a cursor object using cursor() method
        cursor = db.cursor()
        resource_services = {}
        resources = self._used_variables['resources']
        prov_id = int(self._list_vars['Id'])
        for resourceId in resources:
            # Prepare SQL query to SELECT providers from the database.
            sql = "select b.resource_id, c.id, c.name  \
                    from simulation_provider a, simulation_provider_resource b, simulation_service c \
                    where a.id = %s and a.id = b.id and b.resource_id = %s and c.id = b.service_id"
                                
            iResourceId = int(resourceId)
            cursor.execute(sql, (prov_id, iResourceId))
            results = cursor.fetchall()
            res_services = []
            for row in results:
                serviceId = row[0]
                res_services.append(str(serviceId))
                if (str(serviceId) not in (self._services).keys()):
                    connect = Message("")
                    connect.setMethod(Message.GET_SERVICES)
                    connect.setParameter("Service",str(serviceId))
                    response = (self._channelClockServer).sendMessage(connect)
                    if (response.isMessageStatusOk() ):
                        self._services[serviceId] = self.handleGetService(response.getBody())
                    
            resource_services[resourceId] = res_services
        self._list_vars['Resource_Service'] = resource_services       
	        	
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
            return quantity
        else:
            logger.error('Agent: %s - Period: %s - Purchase not received! Communication failed - Message: %s', 
                             self._list_vars['strId'], str(self._list_vars['Current_Period']), messageResult.__str__())
            logger.error('Agent: %s - Period: %s - Purchase not received! Communication failed', 
                         self._list_vars['strId'], str(self._list_vars['Current_Period']))
            raise ProviderException('Purchase not received! Communication failed')
	        
    
    '''
    Purchase an specific quantity, return the total purchased quantity 
    '''
    def purchase_resource(self, front, quantity, evaluatedBids, disutilities_sorted):
        remainingPurchasedQuantity = quantity
        for disutility in disutilities_sorted:
            logger.debug('Agent: %s - Period: %s - Front: %s  disutility: %s', self._list_vars['strId'], str(self._list_vars['Current_Period']), str(front), str(disutility) )
            lenght = len(evaluatedBids[disutility])
            while ((lenght > 0) and (remainingPurchasedQuantity > 0)):
                index_rand = (self._list_vars['Random']).randrange(0, lenght)
                logger.debug('Agent: %s - Period: %s - Index: %d \n', self._list_vars['strId'], str(self._list_vars['Current_Period']), index_rand)
                bid = evaluatedBids[disutility].pop(index_rand)
                qtyPurchased = self.purchase(bid, remainingPurchasedQuantity)
                remainingPurchasedQuantity = remainingPurchasedQuantity - qtyPurchased  
                lenght = len(evaluatedBids[disutility])
            if (remainingPurchasedQuantity == 0 ):
                return quantity - remainingPurchasedQuantity
                
        return quantity - remainingPurchasedQuantity
        
	'''
	The getDisutility function is responsible for assigning the access provider
	agent a disutility function from the simulation environment (
	demand server)
	'''
    def getDisutility(self, resourceId, serviceId, bid):
        resources = self._used_variables['resources']
        service = self._services[serviceId]
        disutil = 0
        offered = 0
        unitaryCost = float((resources[resourceId])['Cost'])
        for decisionVariable in (service)._decision_variables:        
            if ((service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                offered = offered + bid.getDecisionVariable(decisionVariable)
        disutil = unitaryCost - offered
        return disutil

       
    '''
    Evaluate the bids than comes from the server.
    '''
    def evaluate_front_bids(self, resourceId, serviceId, quantity, front, bidList):
        # Sorts the offerings  based on the customer's needs 
        logger.debug('Agent: %s - Period: %s - Front: %s - Nbr Bids: %s', self._list_vars['strId'], str(self._list_vars['Current_Period']), str(front), str(len(bidList)))
        evaluatedBids = {}
        for bid in bidList:
            disutility = self.getDisutility(resourceId, bid)
            if disutility in evaluatedBids:
                evaluatedBids[disutility].append(bid)
            else:
                evaluatedBids[disutility] = [bid]
        # Purchase based on the disutility order.
        disutilities_sorted = sorted(evaluatedBids)
        purchased = self.purchase_resource(front, resourceId, quantity, evaluatedBids, disutilities_sorted)
        return purchased
   
    '''
    Execute purchases for an specific services that is required for a resource.
    '''
    def exec_service_purchase(self, resourceId, serviceId, quantity):
        dic_return = self.createAskBids(serviceId)
        logger.debug('Agent: %s - Period: %s - Number of fronts: %s', self._list_vars['strId'], str(self._list_vars['Current_Period']), str(len(dic_return)))
        # Sorts the offerings  based on the customer's needs 
        remainingPurchasedQuantity = quantity
        keys_sorted = sorted(dic_return,reverse=True)
        for front in keys_sorted:
            bidList = dic_return[front]
            purchased = self.evaluate_front_bids(self, resourceId, serviceId, remainingPurchasedQuantity, front, bidList)
            remainingPurchasedQuantity = remainingPurchasedQuantity - purchased
            if (remainingPurchasedQuantity == 0 ):
                return True
        return False
        
                    
    '''
    Execute resource purchases for an specific resource.
    '''
    def exec_resource_purchase(self, resourceId, quantity):
        res_purchased = True        
        services = (self._list_vars['Resource_Service'])[resourceId]
        for serviceId in services:
            purchased = self.exec_service_purchase(self, resourceId, serviceId, quantity)
            if (purchased == False):
                res_purchased = purchased
            
        logger.debug('Agent: %s - Period: %s - Ending exec_algorithm',self._list_vars['strId'], str(self._list_vars['Current_Period']))
        return res_purchased

    '''
    Execute the purchase process for the network provider
    '''
    def exec_purchases(self, resources):
        res_purchased = True
        for resourceId in resources:
            purchased = self.exec_resource_purchase(resourceId, resources[resourceId])
            if (purchased == False):
                res_purchased = purchased
        return res_purchased
                
    '''
    Create the forecast for the staged bids.
    '''
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
		    self._list_vars['strId'], str(self._list_vars['Current_Period'])  )          
        staged_bids = {}
        if (self._list_vars['State'] == AgentServerHandler.BID_PERMITED):
            fileResult = open(self._list_vars['strId'] + '.log',"a")
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
