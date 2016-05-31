from foundation.FoundationException import FoundationException
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
import xml.dom.minidom
import foundation.agent_properties
import math



logger = logging.getLogger('provider_edge')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('provider_edge.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


''' 
The Edge Provider class defines methods to be used by the access provider
agent to purchase offers that are channels on the marketplace. 
    
Initizalize the agent, get the disutility function, and execute the buying
algorithm. 
'''
class ProviderEdge(Provider):
    
    def __init__(self,  strID, Id, serviceId, accessProviderSeed, marketPosition, 
				 adaptationFactor, monopolistPosition, debug, resources, 
				 numberOffers, numAccumPeriods, numAncestors, startFromPeriod, 
                 sellingAddress, buyingAddress, capacityControl):
        try:
            super(ProviderEdge, self).__init__(strID, Id, serviceId, accessProviderSeed, marketPosition, adaptationFactor, monopolistPosition, debug, resources, numberOffers, numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl, Agent.PROVIDER_ISP)
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
        db1 = MySQLdb.connect("localhost","root","password","Network_Simulation" )

        # prepare a cursor object using cursor() method
        cursor = db1.cursor()
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
                serviceId = str(row[1])
                res_services.append(str(serviceId))
                if (str(serviceId) not in (self._services).keys()):
                    connect = Message("")
                    connect.setMethod(Message.GET_SERVICES)
                    connect.setParameter("Service", serviceId)
                    response = (self._channelClockServer).sendMessage(connect)
                    if (response.isMessageStatusOk() ):
                        self._services[serviceId] = self.handleGetService(response.getBody())
                    
            resource_services[resourceId] = res_services
        self._list_vars['Resource_Service'] = resource_services
        db1.close()
	        	
    ''' 
    The Purchase method assigns all the parameters and access provider ID
    to the message to be send to the Marketplace.
	
    In the end, the function sends the message to the marketplace
    and checks if it was succesfully received. 
    '''
    def purchase(self, serviceId, bid, quantity, fileResult):
        self.registerLog(fileResult, 'Period:' + str(self.getCurrentPeriod()) + ' - bidId:' + bid.getId() + ' -qty to purchase:' + str(quantity))
        messagePurchase = Message('')
        messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
        uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
        idStr = str(uuidId)
        messagePurchase.setParameter('Id', idStr)
        messagePurchase.setParameter('Service', serviceId)
        messagePurchase.setParameter('Bid', bid.getId())        
        messagePurchase.setParameter('Quantity', str(quantity))
        service = self._services[serviceId]
        for decisionVariable in service._decision_variables:
            value = float(bid.getDecisionVariable(decisionVariable))
            messagePurchase.setParameter(decisionVariable, str(value))
        messageResult = self._channelMarketPlaceBuy.sendMessage(messagePurchase)
        # Check if message was succesfully received by the marketplace
        if messageResult.isMessageStatusOk():
            quantity = float(messageResult.getParameter("Quantity_Purchased"))
            self.registerLog(fileResult,'Period:' + str(self.getCurrentPeriod()) + '- bidId:' + bid.getId() + 'qty_purchased:' + str(quantity))
            return quantity
        else:
            logger.error('Agent: %s - Period: %s - Purchase not received! Communication failed - Message: %s', 
                             self._list_vars['strId'], str(self._list_vars['Current_Period']), messageResult.__str__())
            logger.error('Agent: %s - Period: %s - Purchase not received! Communication failed', 
                         self._list_vars['strId'], str(self._list_vars['Current_Period']))
            raise ProviderException('Purchase not received! Communication failed')
	        
    
    '''
    Purchase an specific quantity, return the total quantity purchased
    '''
    def purchaseResource(self, front, serviceId, bidPrice, quantityReq, quality, evaluatedBids, disutilities_sorted, fileResult):
        self.registerLog(fileResult, 'starting purchaseResource - bidPrice:' + str(bidPrice) )
        remainingPurchasedQuantity = quantityReq * quality
        qtyTotPurchase = 0
        for disutility in disutilities_sorted:
            if (disutility < bidPrice): 
                lenght = len(evaluatedBids[disutility])
                while ((lenght > 0) and (remainingPurchasedQuantity > 0)):
                    index_rand = (self._list_vars['Random']).randrange(0, lenght)
                    self.registerLog(fileResult, ' disutility: ' + str(disutility) +' Index:' + str(index_rand))
                    dictUtil = evaluatedBids[disutility].pop(index_rand)
                    bid = dictUtil['Object']
                    overPercentage = dictUtil['OverPercentage']
                    qtyToPurchase = math.ceil(remainingPurchasedQuantity / overPercentage)
                    qtyPurchased = self.purchase(serviceId, bid, qtyToPurchase, fileResult)
                    qtyTotPurchase = qtyTotPurchase + qtyPurchased  * overPercentage
                    remainingPurchasedQuantity = remainingPurchasedQuantity - ( qtyPurchased  * overPercentage )
                    lenght = len(evaluatedBids[disutility])
                if (remainingPurchasedQuantity <= 0 ):
                    logger.debug('purchaseResource provId:%s qtyPurchased:%s remaining:%s', self._list_vars['strId'], str(quantityReq), str(remainingPurchasedQuantity))
                    return (qtyTotPurchase / quality )
        
        self.registerLog(fileResult, 'purchaseResource qtyPurchased:' + str(quantityReq)  + 'remaining:' + str(remainingPurchasedQuantity) )
        return quantityReq - ( remainingPurchasedQuantity / quality )
        
	'''
	The getDisutility function is responsible for assigning the access provider
	agent a disutility function from the simulation environment (
	demand server)
	'''
    def getDisutility(self, resourceId, serviceId, bid, fileResult):
        service = self._services[serviceId]
        disutil = 0
        cost = 0
        totPercentage = 0
        for decisionVariable in (service)._decision_variables:        
            offered = bid.getDecisionVariable(decisionVariable) 
            if ((service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                cost = offered

            if ((service._decision_variables[decisionVariable]).getModeling() == DecisionVariable.MODEL_QUALITY):        		
                percentage = self.calculatePercentageOverResources(service, decisionVariable, offered)
                totPercentage = totPercentage + percentage
                
        disutil = cost / totPercentage
        self.registerLog(fileResult, 'Disutulity -bidId: ' + bid.getId() + 'cost:' + str(cost) + 'percentage:' + str(totPercentage) + 'disutil:' + str(disutil))
        return disutil, totPercentage

       
    '''
    Evaluate the bids than comes from the server.
    '''
    def evaluateFrontBids(self, resourceId, serviceId, quantityReq, bidPrice, quality, front, bidList, fileResult):
        self.registerLog(fileResult, 'Period: ' + str(self.getCurrentPeriod()) + '- Front:' + str(front) + '- Nbr Bids:'+ str(len(bidList)) )
        # Sorts the offerings  based on the customer's needs 
        evaluatedBids = {}
        for bid in bidList:
            disutility, totPercentage = self.getDisutility(resourceId, serviceId, bid, fileResult)
            if disutility in evaluatedBids:
                evaluatedBids[disutility].append({'Object' : bid, 'OverPercentage' : totPercentage })
            else:
                evaluatedBids[disutility] = [{'Object' : bid, 'OverPercentage' : totPercentage }]
        # Purchase based on the disutility order.
        disutilities_sorted = sorted(evaluatedBids)
        self.registerLog(fileResult, 'disutilities:' + str(len(disutilities_sorted)) )
        purchased = self.purchaseResource(front, serviceId, bidPrice, quantityReq, quality, evaluatedBids, disutilities_sorted, fileResult)
        self.registerLog(fileResult, 'Ending evaluateFrontBids qtyPurchased:' + str(purchased)) 
        return purchased

    '''
    This method creates the query for the Marketplace asking 
    other providers' offers.
    '''
    def AskBackhaulBids(self, serviceId):
        messageAsk = Message('')
        messageAsk.setMethod(Message.GET_BEST_BIDS)
        messageAsk.setParameter('Provider', self._list_vars['strId'])
        messageAsk.setParameter('Service', serviceId)
        messageResult = self._channelMarketPlaceBuy.sendMessage(messageAsk)
        if messageResult.isMessageStatusOk():
            #print 'Best bids' + messageResult.__str__()
            document = self.removeIlegalCharacters(messageResult.getBody())
            try:
                dom = xml.dom.minidom.parseString(document)
                return self.handleBestBids(dom)
            except Exception as e: 
                raise FoundationException(str(e))
        else:
            raise FoundationException("Best bids not received")

   
    '''
    Execute purchases for an specific services that is required for a resource.
    return quantities purchased.
    '''
    def execServicePurchase(self, resourceId, serviceId, quantityReq, bidPrice, quality, fileResult):
        dic_return = self.AskBackhaulBids(serviceId)
        self.registerLog(fileResult, '- Period:' + str(self._list_vars['Current_Period']) + '- Number of fronts:' + str(len(dic_return))  )
        # Sorts the offerings  based on the customer's needs 
        qtyToPurchase = quantityReq
        if (len(dic_return) > 0):
            keys_sorted = sorted(dic_return,reverse=True)
            for front in keys_sorted:
                bidList = dic_return[front]
                purchased = self.evaluateFrontBids(resourceId, serviceId, qtyToPurchase, bidPrice, quality, front, bidList, fileResult)
                qtyToPurchase = qtyToPurchase - purchased
                if (qtyToPurchase == 0 ):
                    return quantityReq
            return quantityReq - qtyToPurchase
        else:
            return 0
        
                    
    '''
    Execute resource purchases for an specific resource.
    '''
    def execResourcePurchase(self, resourceId, quantity, bidPrice, quality, availQuantity, fileResult):
        self.registerLog(fileResult, 'Start - exec execResourcePurchase resource:' + str(resourceId) + '- quantity:' + str(quantity) + 'bidPrice:' + str(bidPrice) + 'quality:' + str(quality) + '- availQty:'+  str(availQuantity))
        # The provider has part of the quantities by himself.        
        # The rest of the quantities should be bought.
        quantityReq = quantity - (availQuantity / quality)

        # We assume here a service by every resource.
        services = (self._list_vars['Resource_Service'])[resourceId]
        for serviceId in services:
            qtyPurchased = self.execServicePurchase(resourceId, serviceId, quantityReq, bidPrice, quality, fileResult)
            self.registerLog(fileResult, 'Ending execResourcePurchase resourceId:' + resourceId  + 'qtyPurchased:' + str(qtyPurchased) )
            return qtyPurchased
        # If it arrives here, it means that nothing could be bought.
        return 0

    def purchaseResourceForBid(self, bid, forecast, bidPrice, resources, availability, fileResult):
        self.registerLog(fileResult, 'starting purchaseResourceForBid - Bid:' + bid.getId() + 'bidPrice:' + str(bidPrice) )
        bidCapacity = forecast
        for resourceId in resources:
            qtyTotal = 0
            availQty = self.getAvailableCapacity(resourceId)
            quality = resources[resourceId]
            if ((forecast * quality ) > availQty):
                qtyPurchased = self.execResourcePurchase(resourceId, forecast, bidPrice, quality, availQty, fileResult)
                qtyTotal = qtyTotal + (qtyPurchased * quality ) + availQty
                # The capacity of the bid is given by the resource with the minimal capacity
                bidCapacity = min( bidCapacity, qtyPurchased + (availQty / quality) )
                self.registerLog(fileResult, 'bidId' + bid.getId() + 'qtyPurchased:' + str(qtyPurchased) )
                self.updateAvailability(resourceId, 0)
            else:
                qtyTotal = qtyTotal + (forecast * quality) 
                # The capacity of the bid is given by the resource with the minimal capacity
                bidCapacity = min( bidCapacity, forecast )
                self.updateAvailability(resourceId, availQty - (forecast * quality))
                self.registerLog(fileResult, 'bidId' + bid.getId() + 'qtyDiscAvail:' + str(forecast * quality) )
            
            if resourceId in availability.keys():
                availability[resourceId] = availability[resourceId] + qtyTotal
            else:
                availability[resourceId] = qtyTotal
        self.registerLog(fileResult, 'ending purchaseResourceForBid -qtyForBid:' + str(qtyTotal) + 'bidCapacity:' + str(bidCapacity))
        return bidCapacity
                
    '''
    Create the forecast for the staged bids.
    '''
    def purchaseBids(self, staged_bids, availability, fileResult):
        self.registerLog(fileResult, 'Starting purchaseBids' )
        for bidId in staged_bids:            
            action = (staged_bids[bidId])['Action']
            if (action == Bid.ACTIVE):
                bid = (staged_bids[bidId])['Object']
                forecast = (staged_bids[bidId])['Forecast']
                bidPrice = self.getBidPrice(bid)
                self.registerLog(fileResult, 'bidId' + bid.getId() + ' forecast:' + str(forecast) + 'profit:' + str(bid.getUnitaryProfit()) + 'cost:' + str(bid.getUnitaryCost()) + 'price:' + str(bidPrice))
                resources = self.calculateBidResources(bid)
                if (forecast > 0):
                    bidCapacity = self.purchaseResourceForBid(bid, forecast, bidPrice, resources, availability, fileResult)
                    bid.setCapacity(bidCapacity)
                    (staged_bids[bidId])['Object'] = bid
        self.registerLog(fileResult, 'Ending purchaseBids' )
    
    def setInitialBids(self, fileResult):
        '''
        Initialize bids for customers
        '''
        marketPosition = self._used_variables['marketPosition']
        initialNumberBids = self._used_variables['initialNumberBids']
        self.registerLog(fileResult, 'The initial number of bids is:' + str(initialNumberBids) + 'market pos:' + str(marketPosition)) 
        return self.initializeBids(marketPosition, initialNumberBids, fileResult) 
    
    def updateAvailability(self, resourceId, newAvailability):
        if (resourceId in self._used_variables['resources']):
            ((self._used_variables['resources'])[resourceId])['Capacity'] = newAvailability
        
    def updateCurrentBids(self, currentPeriod, radius, staged_bids, fileResult):
        '''
        Update bids for customers given te previous history.
        '''
        # By assumption providers at this point have the bid usage updated.
        self.replaceDominatedBids(currentPeriod, radius, staged_bids, fileResult)
        adoptStrong = self.canAdoptStrongPosition(currentPeriod, fileResult) 
        # This type of provider does not adopt this strategy as their capacity is variable.        
        adoptStrong = False 
        if (adoptStrong == True):
            self.moveBetterProfits(currentPeriod, radius,  staged_bids, fileResult)
        else:
            self.moveForMarketShare(currentPeriod, radius, staged_bids, fileResult)        

    def sendCapacityEdgeProvider(self, availability):
        '''
        Sends the provider edge availability capacity to the market server.
        '''
        logger.info("Initializing send provider edge capacity")    
        for resourceId in availability:
            qtyAvailable = availability[resourceId]
            message = Message('')
            message.setMethod(Message.SEND_AVAILABILITY)
            message.setParameter("Provider", self._list_vars['strId'])
            message.setParameter("Resource", resourceId)
            message.setParameter("Quantity",str(qtyAvailable))
            messageResult = self._channelMarketPlace.sendMessage(message)
            if messageResult.isMessageStatusOk():
                logger.info("Capacity tranmitted sucessfully")
            else:
                raise ProviderException('Capacity not received')
        logger.debug("Ends send capacity")
    
    def includeActiveBidsNotStaged(self,currentPeriod, radius,  staged_bids, fileResult):
        for bidId in self._list_vars['Bids']:
            if bidId not in staged_bids.keys():
                bid = (self._list_vars['Bids'])[bidId]
                marketZoneDemand, forecast = self.calculateMovedBidForecast(currentPeriod, radius, bid, bid, Provider.MARKET_SHARE_ORIENTED, fileResult)
                staged_bids[bid.getId()] = {'Object': bid, 'Action': Bid.ACTIVE, 'MarketShare': marketZoneDemand, 'Forecast': forecast }
        self.registerLog(fileResult, 'include active bids not stated end number of bids:' + str(len(staged_bids)) )


    def restartAvailableCapacity(self):
        db1 = MySQLdb.connect("localhost","root","password","Network_Simulation" )
        cursor2 = db1.cursor()
        sql_resources = "SELECT resource_id, capacity, cost \
        			       FROM simulation_provider_resource \
        			      WHERE provider_id = '%s'" % (self._list_vars['Id'])
        cursor2.execute(sql_resources)
        resourceRows = cursor2.fetchall()
        resources = {}
        for resourceRow in resourceRows:
            resources[str(resourceRow[0])] = {'Capacity': resourceRow[1], 'Cost' : resourceRow[2]}
        # Replace the current cost
        for resourceId in self._used_variables['resources']:
            if resourceId in resources.keys():
                (resources[resourceId])['Cost'] = ((self._used_variables['resources'])[resourceId])['Cost']
        
        db1.close()
        # replace resource variables
        self._used_variables['resources'] = resources
        
	'''
	The exec_algorithm function finds available offerings and chooses
	the one that fits the access provider needs the best, based on the prior 
	signals received by the simulation environment (demand server).
	'''
    def exec_algorithm(self):
        logger.info('Agent: %s - Period %s - Initiating exec_algorithm ', 
		    self._list_vars['strId'], str(self._list_vars['Current_Period'])  )          
        staged_bids = {}
        availability = {}
        try:
            if (self._list_vars['State'] == AgentServerHandler.BID_PERMITED):
                fileResult = open(self._list_vars['strId'] + '.log',"a")
                self.registerLog(fileResult, 'executing algorithm ####### ProviderId:' + str(self.getProviderId()) + ' - Period: ' +  str(self.getCurrentPeriod()) )
                self.restartAvailableCapacity()
                 # Sends the request to the market place to find the best offerings             
                 # This executes offers for the provider
                currentPeriod = self.getCurrentPeriod()
                radius = foundation.agent_properties.own_neighbor_radius
                if (len(self._list_vars['Bids']) == 0):
                     staged_bids = self.setInitialBids(fileResult)
                     self.registerLog(fileResult, 'The Number of initial Staged offers is:' + str(len(staged_bids)) ) 
                else:
                    self.updateCurrentBids(currentPeriod, staged_bids, fileResult)
                    self.registerLog(fileResult, 'The Number of updated Staged offers is:' + str(len(staged_bids)) ) 
                self.eliminateNeighborhoodBid(staged_bids, fileResult)
                self.registerLog(fileResult, 'The Final Number of Staged offers is:' + str(len(staged_bids)) ) 
                self.sendBids(staged_bids, fileResult) #Pending the status of the bid.
                # include active bids not staged. 
                initial_staged_bids = staged_bids
                self.includeActiveBidsNotStaged(currentPeriod, radius, staged_bids, fileResult)
                self.purchaseBids(staged_bids, availability, fileResult)
                self.purgeBids(initial_staged_bids, fileResult)
                self.sendCapacityEdgeProvider(availability)

        except ProviderException as e:
            self.registerLog(fileResult, e.message)
        except Exception as e:
            self.registerLog(fileResult, e.message)
            
        fileResult.close()
        self._list_vars['State'] = AgentServerHandler.IDLE
		
		
	
	
# End of Access provider class
