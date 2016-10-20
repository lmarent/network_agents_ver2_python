from foundation.FoundationException import FoundationException
import uuid
import logging
from foundation.AgentServer import AgentServerHandler
from foundation.AgentType import AgentType
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
import numpy as np



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
                 sellingAddress, buyingAddress, capacityControl, purchase_service):
        try:
            
            agent_type = AgentType(AgentType.PROVIDER_ISP)
            super(ProviderEdge, self).__init__(strID, Id, serviceId, accessProviderSeed, marketPosition, adaptationFactor, monopolistPosition, debug, resources, numberOffers, numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl, purchase_service, agent_type)
            logger.debug('Agent: %s - Edge Provider Created', self._list_vars['strId'])
        except FoundationException as e:
            raise ProviderException(e.__str__())


	''' 
	The initialize function is responsible for initializing the 
	edge provider agent and get the decision variables from the simulation
	environment (demand server). 
    Test: Implemented.
	'''
    def initialize(self):
        logger.debug('Agent: %s - Initilizing provider', self._list_vars['strId'])
        self.lock.acquire()
        try:
            for decisionVariable in (self._service)._decision_variables:
                ((self._service)._decision_variables[decisionVariable]).executeSample(self._list_vars['Random'])
            #Bring services required to fulfill resources.
            # Open database connection
            db1 = MySQLdb.connect(foundation.agent_properties.addr_database,foundation.agent_properties.user_database, \
                                    foundation.agent_properties.user_password,foundation.agent_properties.database_name )

            purchaseServiceId = self._list_vars['PurchaseServiceId']
            self.getServiceFromServer(purchaseServiceId)

            # prepare a cursor object using cursor() method 
            # This is to be able to purchase raw resources from other providers.
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
                    self.getServiceFromServer(serviceId)

                resource_services[resourceId] = res_services
            self._list_vars['Resource_Service'] = resource_services

            self._servicesRelat = {}
            # Bring the service's decision variables relationships
            sql2 = "select a.service_to_id, a.decision_variable_to_id, a.aggregation \
                      from simulation_provider b, simulation_service_relationship a \
                        where b.id = %s and b.service_id = %s \
                        and b.service_id = a.service_from_id \
                        and b.purchase_service_id = a.service_to_id \
                        and a.decision_variable_from_id = %s"

            serviceIdOwn = (self._service).getId()        
            for decisionVariable in (self._service)._decision_variables:
                cursor.execute(sql2, (prov_id, serviceIdOwn, decisionVariable))
                results2 = cursor.fetchall()
                ret_tuple = None
                for row in results2:
                    serviceTo = str(row[0])
                    variableTo = str(row[1])
                    aggregation = str(row[2])
                    ret_tuple = (serviceTo, decisionVariable, variableTo, aggregation)
                    break
                if (ret_tuple != None):
                    # Insert direct relation from -> to                    
                    if serviceIdOwn in self._servicesRelat.keys():
                        (self._servicesRelat[serviceIdOwn]).append(ret_tuple)
                    else:
                        self._servicesRelat[serviceIdOwn] = []
                        (self._servicesRelat[serviceIdOwn]).append(ret_tuple)
                    # Insert direct relation from -> to
                    if ret_tuple[0] in self._servicesRelat.keys():
                        ret_tuple2 = (serviceIdOwn, ret_tuple[2], ret_tuple[1], ret_tuple[3])
                        (self._servicesRelat[ret_tuple[0]]).append(ret_tuple2)
                    else:
                        self._servicesRelat[ret_tuple[0]] = []
                        ret_tuple2 = (serviceIdOwn, ret_tuple[2], ret_tuple[1], ret_tuple[3])
                        (self._servicesRelat[ret_tuple[0]]).append(ret_tuple2)
            db1.close()
        finally:
            self.lock.release()
            logger.debug('Ending Initilizing provider')

    def getPurchaseService(self):
        purchaseServiceId = ''
        self.lock.acquire()
        try:
            purchaseServiceId = self._list_vars['PurchaseServiceId']
        finally:
            self.lock.release()
        return purchaseServiceId

    ''' 
    Create the purchase message without indicating bid and quantity.
    '''
    def createPurchaseMessage(self, serviceId):
        messagePurchase = Message('')
        messagePurchase.setMethod(Message.RECEIVE_PURCHASE)
        uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
        idStr = str(uuidId)
        messagePurchase.setParameter('Id', idStr)
        messagePurchase.setParameter('Service', serviceId)
        return messagePurchase

	        	
    ''' 
    The Purchase method assigns all the parameters and access provider ID
    to the message to be send to the Marketplace.
	
    In the end, the function sends the message to the marketplace
    and checks if it was succesfully received. 
    
    Test: Implemented.
    '''
    def purchase(self, messagePurchase, serviceId, bid, quantity, fileResult):
        self.registerLog(fileResult, 'Starting Purchase - Period:' + str(self.getCurrentPeriod()) + ' - bidId:' + bid.getId() + ' -qty to purchase:' + str(quantity))

        # Copy basic data from the purchase message given as parameter.
        message = Message('')
        message.setMethod(Message.RECEIVE_PURCHASE)
        message.setParameter('Id', messagePurchase.getParameter('Id'))
        message.setParameter('Service', messagePurchase.getParameter('Service'))
        
        # set the rest of the data from the bid and quantity given as parameters.
        message.setParameter('Bid', bid.getId())        
        message.setParameter('Quantity', str(quantity))
        service = self._services[serviceId]
        for decisionVariable in service._decision_variables:
            value = float(bid.getDecisionVariable(decisionVariable))
            message.setParameter(decisionVariable, str(value))
        messageResult = self.sendMessageMarketBuy(message)
        
        # Check if message was succesfully received by the marketplace
        if messageResult.isMessageStatusOk():
            quantity = float(messageResult.getParameter("Quantity_Purchased"))
            self.registerLog(fileResult,'Ending Purchase - Period:' + str(self.getCurrentPeriod()) + '- bidId:' + bid.getId() + 'qty_purchased:' + str(quantity))
            return quantity
        else:
            self.registerLog(fileResult, 'Period: ' + str(self.getCurrentPeriod()) + '- Purchase not received! Communication failed - Message:' + messageResult.__str__())
            raise ProviderException('Purchase not received! Communication failed')
	
    def replicateBids(self, ownBid, bidPrice, bidPurchasable, fileResult):
        '''
        Duplicates bids as many bids from the provider are in the list, because 
        costs depend on the quality of the provider bid.
        Test: implemented.
        '''
        newOwnBids = []    
        # creates a bid per provider bid.        
        for bidId in bidPurchasable:
            newOwnBid = self.copyBid(ownBid)
            providerBid = (bidPurchasable[bidId])['Object']
            # Assign the quality request given the providerBid
            qualityRequest = (bidPurchasable[bidId])['QualityRequirements']
            for decisionVariableId in qualityRequest:
                newOwnBid.setQualityRequirement(decisionVariableId, qualityRequest[decisionVariableId])
            # Assign the provider Bid.
            newOwnBid.setProviderBid(providerBid) 
            totUnitaryCost = self.calculateBidUnitaryCost(newOwnBid, fileResult)
            newOwnBid.insertParentBid(ownBid.getParentBid())
            self.completeNewBidInformation(newOwnBid, bidPrice, fileResult )
            if (bidPrice >= totUnitaryCost):
                newOwnBids.append( (bidPrice - totUnitaryCost, newOwnBid))
        return newOwnBids
        
    def purchaseBid(self, ownBid, providerServiceId, quantityReq, bidPrice, bidPurchasable, fileResult):
        '''
        Evaluate the bids than comes from the server.
        Test: Implemented.
        '''
        self.registerLog(fileResult, 'purchaseBid - Period: ' + str(self.getCurrentPeriod()) + '- Nbr provider Bids:'+ str(len(bidPurchasable)) )
        messagePurchase = self.createPurchaseMessage(providerServiceId)
        newOwnBids = self.replicateBids(ownBid, bidPrice, bidPurchasable, fileResult)
        utilities_sorted = sorted(newOwnBids, key=lambda tup: tup[0], reverse=True )
        
        qtyToPurchase = quantityReq
        totPurchased = 0
        purchasedBids = []
        for bidTuple in utilities_sorted:    
            # verifies that it is enoght capacity for this bid
            bid = bidTuple[1] 
            qtyBidToPurchase = qtyToPurchase
            
            resourceConsumption = self.calculateBidUnitaryResourceRequirements(bid, fileResult)
            for resourceId in resourceConsumption:
                resourceAvail = self.getAvailableCapacity(resourceId) / resourceConsumption[resourceId]
                qtyBidToPurchase = min (qtyBidToPurchase, resourceAvail)
            
            self.registerLog(fileResult, 'Bid: ' + bid.getId() + '- Qty to purchase:'+ str(qtyBidToPurchase) )
            # purchase the quantity
            if (qtyBidToPurchase > 0):
                qtyPurchased = self.purchase(messagePurchase, providerServiceId, bid.getProviderBid(), qtyBidToPurchase, fileResult)
                if (qtyPurchased > 0):
                    # decrease own resources based on values purchased.
                    for resourceId in resourceConsumption:
                        qtyToDecrease = qtyPurchased * resourceConsumption[resourceId]
                        resourceAvail = self.getAvailableCapacity(resourceId)
                        newAvail = resourceAvail - qtyToDecrease
                        self.updateAvailability(resourceId, newAvail)
                    #Totalize purchase quantities and stage the bid.
                    qtyToPurchase = qtyToPurchase - qtyPurchased
                    bid.setCapacity(qtyPurchased)
                    totPurchased = totPurchased + qtyPurchased
                    purchasedBids.append(bid)     
        self.registerLog(fileResult, 'Ending purchaseBid - Period: ' + str(self.getCurrentPeriod()) + ' qtyPurchased:' + str(totPurchased)) 
        return totPurchased, purchasedBids
           
    def getRelatedDecisionVariable(self, serviceFromId, serviceToId, decisionVariableIdFrom):
        '''
        Get the relationships between decision variables for services.
        Test: Implemented.
        '''
        if serviceFromId in self._servicesRelat.keys():
            for tmp_tuple in self._servicesRelat[serviceFromId]:
                if ((tmp_tuple[0] == serviceToId) and (tmp_tuple[1] == decisionVariableIdFrom)):
                    return tmp_tuple[2], tmp_tuple[3]
            raise FoundationException("service to" + serviceToId + " or decision variable from not found in relationships")
        else:
            raise FoundationException("Service from:" + serviceFromId + " not found in service relationships")

    def calculateRequiredQuality(self, bidQuality, minValue, maxValue, providerQuality, optObjetive, aggregationMode):
        ''' 
        Calculate the specific quality value given the provider quality, aggregationmode, and optimal objective
        Test: Implemented.
        '''
        qualityReq = 0        
        if (aggregationMode == 'M'): # MAX aggregation
            if (providerQuality < bidQuality):
                qualityReq = bidQuality
            else:
                qualityReq = -1
            
        if (aggregationMode == 'N'): # MIN aggregation
            if (providerQuality < bidQuality):
                qualityReq = -1
            else:
                qualityReq = bidQuality

        if (aggregationMode == 'S'): # SUM aggregation
            if (optObjetive == DecisionVariable.OPT_MAXIMIZE):
                qualityReq = bidQuality - providerQuality
            else:
                qualityReq = bidQuality - providerQuality

        if (aggregationMode == 'X'): # NON aggregation
            qualityReq = bidQuality
        
        if (qualityReq > maxValue) or (qualityReq < minValue):
            qualityReq = -1
            
        return qualityReq
            
    def calculateOwnQualityForPurchasableBid(self, ownBid, providerBid, fileResult):
        '''
        Verifies if a bid is or not purchasable given the quality requirements
        Test: implemented.
        '''
        nonPurchasable = False
        qualityRequirements = {}
        for decisionVariable in (self._service)._decision_variables:
            minValue = ((self._service)._decision_variables[decisionVariable]).getMinValue()
            maxValue = ((self._service)._decision_variables[decisionVariable]).getMaxValue()
            optObjetive = (self._service)._decision_variables[decisionVariable].getOptimizationObjective()
            if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                decisionVariableTo, aggregationMode = self.getRelatedDecisionVariable(ownBid.getService(), providerBid.getService(), decisionVariable)
                bidQuality = ownBid.getDecisionVariable(decisionVariable)
                if (bidQuality >= minValue) and (bidQuality <= maxValue):
                    providerQuality = providerBid.getDecisionVariable(decisionVariableTo)
                    qualityRequired = self.calculateRequiredQuality(bidQuality, minValue, maxValue, providerQuality, optObjetive, aggregationMode)
                    qualityRequirements[decisionVariable] = qualityRequired
                    if (qualityRequired < 0):
                        nonPurchasable = True
                else:
                    qualityRequirements[decisionVariable] = -1
                    nonPurchasable = True
        return qualityRequirements, nonPurchasable
                
    def getPurchasedFront(self, ownBid, bidList, fileResult):
        '''
        Get bid purchasable for a bid from a list of bids.
        Test: implemented.
        '''
        self.registerLog(fileResult, 'getPurchasedFront - Period:' + str(self._list_vars['Current_Period']) + '- Number of bids:' + str(len(bidList)) )
        dict_return = {}
        for bid in bidList:
            qualityRequirements, nonPurchasable = self.calculateOwnQualityForPurchasableBid(ownBid, bid, fileResult)
            if nonPurchasable == False:
                dict_return[bid.getId()] = {'Object' : bid, 'QualityRequirements' : qualityRequirements }
        return dict_return
    
    def getPurchasableBid(self, ownBid, dic_bids, fileResult):        
        ''' 
        Get those bids from providers that can be purchased based on the requirements of my own bid.
        The return is a dictionary based based on fronts.
        Test: implemented.
        '''
        self.registerLog(fileResult, 'getPurchasableBid - Period:' + str(self._list_vars['Current_Period']) + '- Number of fronts:' + str(len(dic_bids)) )
        totPurchasableBids = {}
        # Sorts the offerings  based on the customer's needs 
        if (len(dic_bids) > 0):
            keys_sorted = sorted(dic_bids,reverse=True)
            for front in keys_sorted:
                bidList = dic_bids[front]
                purchasableBids = self.getPurchasedFront(ownBid, bidList, fileResult)
                for bidId in purchasableBids:
                    totPurchasableBids[bidId] = purchasableBids[bidId]
        return totPurchasableBids


    def swapPurchasedBids(self, currentPeriod, purchasedBids, staged_bids, fileResult):
        '''
        swap the bid actually purchased
        Test: implemented.
        '''
        self.registerLog(fileResult, 'Starting swapPurchasedBids' + 'bid to include:' + str(len(purchasedBids)) + 'bids_staged:' + str(len(staged_bids)) )
            
        for bid in purchasedBids:
            if bid.getCapacity() > 0:
                staged_bids[bid.getId()] = {'Object': bid, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': bid.getCapacity() }
        self.registerLog(fileResult, 'Ending - swapPurchasedBids - Period:' + str(currentPeriod) + 'Bids_staged:' + str(len(staged_bids)))
          
    def purchaseBids(self, currentPeriod, staged_bids, fileResult):
        '''
        Create the forecast for the staged bids.
        Test: 
        '''        
        self.registerLog(fileResult, 'Starting purchaseBids - Period:' + str(currentPeriod) + 'Nbr Staged_bids:' + str(self.countByStatus(staged_bids)) )
        for bidId in staged_bids:
            forecast = (staged_bids[bidId])['Forecast']
            self.registerLog(fileResult, 'Period:' + str(currentPeriod) + 'BidId:' + bidId + 'Forecast:' + str(forecast) )
            
            
        staged_bids_result = {}
        purchaseServiceId = self.getPurchaseService()
        dic_return = self.AskBackhaulBids(purchaseServiceId)
        for bidId in staged_bids:
            action = (staged_bids[bidId])['Action']
            if (action == Bid.ACTIVE):
                bid = (staged_bids[bidId])['Object']
                forecast = (staged_bids[bidId])['Forecast']
                bidPrice = self.getBidPrice(bid)
                bidPurchasable = self.getPurchasableBid(bid, dic_return, fileResult)
                self.registerLog(fileResult, 'bidId' + bid.getId() + ' forecast:' + str(forecast) + 'price:' + str(bidPrice))
                if (forecast > 0) and (len(bidPurchasable) > 0):
                    totPurchased, purchasedBids = self.purchaseBid(bid, purchaseServiceId, forecast, bidPrice, bidPurchasable, fileResult)
                    # if could not purchase anything, then it removes the bid from the staged bids.
                    self.swapPurchasedBids(currentPeriod, purchasedBids, staged_bids_result, fileResult)
            else:
                staged_bids_result[bidId] = staged_bids[bidId]
        self.registerLog(fileResult, 'Ending purchaseBids - Period:' + str(currentPeriod) + 'bids included:' + str(self.countByStatus(staged_bids_result)) )
        return staged_bids_result

    def set_price_markup(self, marketPosition, bidList):
        # found the average price of the provider, which is the value used to update the bids.
        prices = []
        for bid in bidList
            prices.append(self.getBidPrice(bid))
            
        nprices = np.array(prices)
        sprices = np.sort(nprices)
        l,m,u = np.array_split(sprices, 3)

        shape = np.shape(l)
        if shape[0] > 0:
            la = np.average(l)

        shape = np.shape(m)
        if shape[0] > 0:
            ma = np.average(m)
        else:
            ma = la
                
        shape = np.shape(u)
        if shape[0] > 0:
            ua = np.average(u)
        else:
            ua = ma
        
        if (marketPosition > 0.65):
            priceUp = ua
        elif ((market_position >= 0.35) and (market_position <= 0.65)):
            priceUp = ma
        else:
            priceUp = la
        
        return priceUp
    
    def setInitialBids(self, fileResult):
        '''
        Initialize bids for customers
        '''
        marketPosition = self._used_variables['marketPosition']
        initialNumberBids = self._used_variables['initialNumberBids']
        self.registerLog(fileResult, 'The initial number of bids is:' + str(initialNumberBids) + 'market pos:' + str(marketPosition)) 
        staged_bids = self.initializeBids(marketPosition, initialNumberBids, fileResult) 
        
        # Ask the bids of the provider in order to update bid's price, so that we include the provider cost.
        purchaseServiceId = self.getPurchaseService()
        dic_return = self.AskBackhaulBids(purchaseServiceId)
        bidsFound = False
        if (len(dic_bids) > 0):
            keys_sorted = sorted(dic_bids,reverse=True)
            for front in keys_sorted:
                bidList = dic_bids[front]
                bidFound = True
            
            if bidFound == True:
                if len(bidList) > 0:
                    priceUp = self.set_price_markup(marketPosition, bidList)

                    # The following establishes the price for each of the initial bids.
                    for decisionVariable in (self._service)._decision_variables:
                        if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                            for bidId in staged_bids:
                                action = (staged_bids[bidId])['Action']
                                if (action == Bid.ACTIVE):
                                    currentPrice = ((staged_bids[bidId])['Object']).getDecisionVariable(decisionVariable) 
                                    newPrice = currentPrice + priceUp
                                    ((staged_bids[bidId])['Object']).setDecisionVariable(decisionVariable, newPrice) 
                                    (staged_bids[bidId])['Forecast'] = 10
                else:
                    # No bid can be bought.
                    staged_bids = {}                
            else:
                # No bid can be bought.
                staged_bids = {}

        else:
            # No bid can be bought.
            staged_bids = {}
        self.registerLog(fileResult, 'Ending setInitialBids - Period:' + str(self._list_vars['Current_Period']) + 'bids included:' + str(self.countByStatus(staged_bids)) )
        return staged_bids
    
    def updateAvailability(self, resourceId, newAvailability):
        self.lock.acquire()
        try:
            if (resourceId in self._used_variables['resources']):
                ((self._used_variables['resources'])[resourceId])['Capacity'] = newAvailability
        finally:
            self.lock.release()
        
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

    def sendCapacityEdgeProvider(self):
        '''
        Sends the capacity to the market server.
        '''
        logger.info("Initializing send capacity")    
        for resourceId in self._used_variables['resources']:
            resourceNode = (self._used_variables['resources'])[resourceId]
            message = Message('')
            message.setMethod(Message.SEND_AVAILABILITY)
            message.setParameter("Provider", self._list_vars['strId'])
            message.setParameter("Resource", resourceId)
            availableQty = resourceNode['InitCapacity'] - resourceNode['Capacity']
            message.setParameter("Quantity",str(availableQty))
            messageResult = self.sendMessageMarket(message)
            if messageResult.isMessageStatusOk():
                logger.info("Capacity tranmitted sucessfully")
            else:
                raise ProviderException('Capacity not received')
        logger.debug("Ends send capacity")
    
    def includeActiveBidsNotStaged(self,currentPeriod, radius,  staged_bids, fileResult):
        self.lock.acquire()
        try:
            for bidId in self._list_vars['Bids']:
                if bidId not in staged_bids.keys():
                    bid = (self._list_vars['Bids'])[bidId]
                    marketZoneDemand, forecast = self.calculateMovedBidForecast(currentPeriod, radius, bid, bid, Provider.MARKET_SHARE_ORIENTED, fileResult)
                    staged_bids[bid.getId()] = {'Object': bid, 'Action': Bid.ACTIVE, 'MarketShare': marketZoneDemand, 'Forecast': forecast }
            self.registerLog(fileResult, 'include active bids not stated end number of bids:' + str(len(staged_bids)) )
        finally:
            self.lock.release()

    def restartAvailableCapacity(self):
        self.lock.acquire()
        try:
            cursor2 = self._db.cursor()
            sql_resources = "SELECT resource_id, capacity, cost \
                               FROM simulation_provider_resource \
                              WHERE provider_id = '%s'" % (self._list_vars['Id'])
            cursor2.execute(sql_resources)
            resourceRows = cursor2.fetchall()
            resources = {}
            for resourceRow in resourceRows:
                resources[str(resourceRow[0])] = {'Capacity': resourceRow[1], 'Cost' : resourceRow[2], 'InitCapacity' : resourceRow[1]}
            # Replace the current cost
            for resourceId in self._used_variables['resources']:
                if resourceId in resources.keys():
                    (resources[resourceId])['Cost'] = ((self._used_variables['resources'])[resourceId])['Cost']

            # replace resource variables
            self._used_variables['resources'] = resources
        finally:
            self.lock.release()
    
    '''
    This method calculates the total capacity able to sell by the provider given purchases
    '''
    def calculate_capacity(self, staged_bids, fileResult):
        self.registerLog(fileResult, 'starting calculate_capacity' )
        resources = self._used_variables['resources']
        totResourceConsumption = {}
        for bidId in staged_bids:
            action = (staged_bids[bidId])['Action']
            if (action == Bid.ACTIVE):
                bid = (staged_bids[bidId])['Object']
                resourceConsumption = self.calculateBidUnitaryResourceRequirements(bid, fileResult)
                units = bid.getCapacity()
                for resource in resources:
                    totResourceConsumption[resource] = units*resourceConsumption[resource]

        for resource in totResourceConsumption:
            self.registerLog(fileResult, 'calculate_capacity - Resource:' + str(resource) + 'Consuption:' + str(totResourceConsumption[resource]) )
        self.registerLog(fileResult, 'Ending calculate_capacity ')
        return totResourceConsumption            
    
	'''
	The exec_algorithm function finds available offerings and chooses
	the one that fits the access provider needs the best, based on the prior 
	signals received by the simulation environment (demand server).
	'''
    def exec_algorithm(self):
        logger.debug('Starting exec_algorithm Agent: %s - Period %s', 
		    self._list_vars['strId'], str(self._list_vars['Current_Period'])  )
        staged_bids = {}
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
                    self.updateCurrentBids(currentPeriod, radius, staged_bids, fileResult)
                    self.registerLog(fileResult, 'The Number of updated Staged offers is:' + str(len(staged_bids)) ) 
                self.eliminateNeighborhoodBid(staged_bids, fileResult)
                self.registerLog(fileResult, 'The Final Number of Staged offers is:' + str(len(staged_bids)) ) 
                self.sendBids(staged_bids, fileResult) #Pending the status of the bid.
                
                # include active bids not staged. 
                initial_staged_bids = staged_bids
                self.includeActiveBidsNotStaged(currentPeriod, radius, staged_bids, fileResult)
                staged_bids = self.purchaseBids(currentPeriod, staged_bids, fileResult)
                
                totResourceConsumption = self.calculate_capacity(staged_bids, fileResult)
                for resource in totResourceConsumption:
                    self.registerLog(fileResult, 'calculate_capacity - Resource:' + str(resource) + 'Consuption:' + str(totResourceConsumption[resource]) )
                
                self.purgeBids(initial_staged_bids, fileResult)
                self.sendCapacityEdgeProvider()

        except ProviderException as e:
            self.registerLog(fileResult, e.message)
        except Exception as e:
            self.registerLog(fileResult, e.message)    
        fileResult.close()
        self._list_vars['State'] = AgentServerHandler.IDLE
        logger.debug('Ending exec_algorithm Agent: %s - Period %s', 
            self._list_vars['strId'], str(self._list_vars['Current_Period'])  )
# End of Access provider class
