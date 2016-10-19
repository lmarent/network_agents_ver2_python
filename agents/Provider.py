from __future__ import division
from foundation.Message import Message
from foundation.Bid import Bid
from foundation.Agent import Agent
from foundation.FoundationException import FoundationException
from foundation.Agent import AgentServerHandler
from foundation.AgentType import AgentType
from foundation.DecisionVariable import DecisionVariable
from ProviderAgentException import ProviderException

from collections import OrderedDict
import foundation.agent_properties
import copy
import logging
import math
import time
import uuid
import MySQLdb
from datetime import datetime
from time import gmtime, strftime
from operator import itemgetter
import threading



logger = logging.getLogger('Provider')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('provider_logs.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


'''
The Provider class defines methods to be used by the service
provider agent. It includes methods for pricing and quality
strategies, place offerings into the marketplace, get other 
providers offerings and determine the best strategy to capture 
more market share.    
'''
class Provider(Agent):

    PROFIT_ORIENTED = 0
    MARKET_SHARE_ORIENTED = 1
    PURCHASE = 3
    BACKLOG = 4

    

    def __init__(self, strID, Id, serviceId, providerSeed, marketPosition, 
        adaptationFactor, monopolistPosition, debug, resources, 
        numberOffers, numAccumPeriods, numAncestors, startFromPeriod, 
        sellingAddress, buyingAddress, capacityControl, purchase_service,
        providerType=None):
        try:
            logger.info('Initializing the provider:' + strID + 'Id:' + str(Id) 
                  + 'Service Id:' + serviceId
                  + 'seed:' + str(providerSeed)
                  + ' market position:' + str(marketPosition)
                  + ' monopolist position:' + str(monopolistPosition)
                  + 'debug:' + str(debug)
                  + 'numOffers:' + str(numberOffers))
                  
            self.lock = threading.RLock()
            if (providerType == None):
                logger.info('Type of provider not specified -using by default backhaul')
                providerType = AgentType(AgentType.PROVIDER_BACKHAUL)
            
            super(Provider, self).__init__(strID, Id, providerType, serviceId, providerSeed, sellingAddress, buyingAddress, capacityControl, purchase_service, self.lock) 
            
            self._used_variables['marketPosition'] = marketPosition
            # Is a value between 0 and 1, 1 means that the provider can complete follow another provider, 0
            # the provider fails to adapt others' strategies. 
            self._used_variables['adaptationFactor'] = adaptationFactor
            # resource is a dictionary of dictionaries ( key = resourceId, value {'Capacity': val_Capacity, 'Cost' : cost} )
            self._used_variables['resources'] = resources 
            self._used_variables['monopolistPosition'] = monopolistPosition
            self._used_variables['debug'] = debug
            self._used_variables['initialNumberBids'] = numberOffers
            self._used_variables['numPeriodsMarketShare'] = numAccumPeriods
            self._used_variables['numAncestors'] =numAncestors
            self._used_variables['startPeriod'] = startFromPeriod
            logger.info('Ending Initialization provider:' + strID)
            self._db = MySQLdb.connect(foundation.agent_properties.addr_database,foundation.agent_properties.user_database, \
                                foundation.agent_properties.user_password,foundation.agent_properties.database_name )
            self._db.autocommit(1)    
        except FoundationException as e:
            raise ProviderException(e.__str__())
    
    '''
    Get the Id - tested:OK    
    '''
    def getProviderId(self):
        strId = ''
        self.lock.acquire()
        try:
            strId = self._list_vars['strId']
        finally:
            self.lock.release()
        
        return strId
    
    '''
    Get the Service Id offering the provider - tested:OK
    '''
    def getServiceId(self):
        serviceId = ''
        self.lock.acquire()
        try:
            serviceId = (self._service).getId()
        finally:
            self.lock.release()
        return serviceId
            
    '''
    Get the Current Period - tested:OK
    '''
    def getCurrentPeriod(self):
        currentPeriod = 0
        self.lock.acquire()
        try:
            currentPeriod =  self._list_vars['Current_Period']
        finally:
            self.lock.release()
        return currentPeriod
    
    '''
    Get the Number of Ancestor to have into account. - tested:OK
    '''
    def getNumAncestors(self):
        numAncestors = 0
        self.lock.acquire()
        try:
            numAncestors = self._used_variables['numAncestors']
        finally:
            self.lock.release()
        return numAncestors
    
    '''
    Register a log in the file for the provider - tested:OK
    '''
    def registerLog(self, fileResult, message):
        self.lock.acquire()
        try:
            now = datetime.now()
            timeNow = now.strftime("%H:%M:%S.%f")
            if (self._used_variables['debug'] == True):
                fileResult.write(timeNow + ':' + message + '\n')
        finally:
            self.lock.release()

    '''
    Get the maxium period register for a purchase - Not Tested
    '''    
    def getDBMaxPeriod(self):
        cursor = self._db.cursor() 
        sql = 'select max(a.period) from Network_Simulation.simulation_bid_purchases a, \
                Network_Simulation.simulation_generalparameters b \
                where a.execution_count = b.execution_count'

        cursor.execute(sql)
        results = cursor.fetchall()
        period = 0
        for row in results:
            period = row[0]
        return period

    
    ''' 
    Get the bids related to a bid. ( those that are in the neigborhood)
    Only get those bids with creation period within the range [currentPeriod - numPeriods, currentPeriod]
    Tested: Ok
    '''    
    def getRelatedBids(self, bid, currentPeriod, numPeriods, radius, fileResult):
        ret_relatedBids = {}
        self.lock.acquire()
        logger.debug('After acquiring lock')
        try:
            self.registerLog(fileResult,'start getRelatedBids')
            for bidId in self._list_vars['Related_Bids']:
                bidCompetitor = (self._list_vars['Related_Bids'])[bidId]
                if (bidCompetitor.getCreationPeriod()>= (currentPeriod - numPeriods)) and (bidCompetitor.getCreationPeriod() <= (currentPeriod)):
                    if (self.areNeighborhoodBids(radius, bid, bidCompetitor, fileResult)):
                        ret_relatedBids[bidId] = bidCompetitor
            self.registerLog(fileResult, 'Ending getRelatedBids - Numrelated:' + str(len(ret_relatedBids)))
        finally:
            self.lock.release()
        logger.debug('end getRelatedBids')
        return ret_relatedBids
    
    '''
    Get the adaptation factor of this provider - tested:OK
    '''
    def getAdaptationFactor(self):
        adapt_factor = 0
        self.lock.acquire()
        try:
            adapt_factor = self._used_variables['adaptationFactor']
        finally:
            self.lock.release()
         
        return adapt_factor
        

    '''
    Get the market position of this provider - tested:OK
    '''
    def getMarketPosition(self):
        market_pos = 0
        self.lock.acquire()
        try:
            market_pos = self._used_variables['marketPosition']
        finally:
            self.lock.release()
        
        return market_pos
    '''
    Get the monopoly position of this provider - tested:OK
    '''
    def getMonopolistPosition(self):
        monop_pos = 0
        self.lock.acquire()
        try:
            monop_pos =  self._used_variables['monopolistPosition']
        finally:
            self.lock.release()
        return monop_pos

    '''
    Get price of a particular bid.
    '''
    def getBidPrice(self, bid):
        bidPrice = 0
        service = self._services[bid.getService()]
        for decisionVariable in service._decision_variables:
            if (service._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                bidPrice =  bid.getDecisionVariable(decisionVariable)
        return bidPrice

    def calculateBidMinimumQuality(self):  # TESTED: OK
        '''
        Get the bid with the minimal quality and minimum price
        '''
        logger.debug('Starting calculateBidMinimumQuality')
        bid = Bid()
        uuidId = uuid.uuid1()    # make a UUID based on the host ID and current time
        idStr = str(uuidId)
        bid.setValues(idStr,self._list_vars['strId'], (self._service).getId())

        # Establish the bid price.
        for decisionVariable in (self._service)._decision_variables:
            if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                min_val = (self._service)._decision_variables[decisionVariable].getMinValue()
                bid.setDecisionVariable(decisionVariable, min_val)
        
        # Establish the bid quality.
        for decisionVariable in (self._service)._decision_variables:
            if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                if ((self._service)._decision_variables[decisionVariable].getOptimizationObjective() == DecisionVariable.OPT_MAXIMIZE):
                    optimum = 1 # Maximize
                    val = (self._service)._decision_variables[decisionVariable].getMinValue()
                else:
                    optimum = 2 # Minimize
                    val = (self._service)._decision_variables[decisionVariable].getMaxValue()
                bid.setDecisionVariable(decisionVariable, val)
        logger.debug('Ending calculateBidMinimumQuality')
        return bid

    def getQualityMetric(self, bid):  # TESTED: OK
        ''' 
        get the distance to the origin in terms of quality for the bid
        '''
        dist = 0
        for decisionVariable in (self._service)._decision_variables:
            if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                max_value = (self._service)._decision_variables[decisionVariable].getMaxValue()
                min_value = (self._service)._decision_variables[decisionVariable].getMinValue()
                val_bid = bid.getDecisionVariable(decisionVariable)
                if ((self._service)._decision_variables[decisionVariable].getOptimizationObjective() == DecisionVariable.OPT_MAXIMIZE):
                    if (max_value - min_value != 0):
                        perc = (val_bid - min_value) / (max_value - min_value)
                    else:
                        perc =  1
                else:
                    if (max_value - min_value != 0):
                        perc = (max_value - val_bid) / (max_value - min_value)
                    else:
                        perc =  1
                dist = dist + math.pow(perc,2)
        return math.sqrt(dist)

    def getBidMinimumQuality(self): # TESTED: OK
        '''
        Get the bid with the minimum quality among the actual bids.given in dict_bids
        '''
        minBid = None
        self.lock.acquire()
        try:
            dist = 1 # distance is bounded between 0 and 1.
            for bidId in self._list_vars['Bids']:
                bid = (self._list_vars['Bids'])[bidId]
                dist_tmp = self.getQualityMetric(bid)
                if (dist_tmp <= dist):
                    dist = dist_tmp
                    minBid = bid
        finally:
            self.lock.release()
        return minBid

    def getBidMaximumQuality(self):  # TESTED: OK
        '''
        Get the bid with the maximum quality among the actual bids.given in dict_bids
        '''
        maxBid = None
        self.lock.acquire()
        try:
            dist = 0 # distance is bounded between 0 and 1.
            for bidId in self._list_vars['Bids']:
                bid = (self._list_vars['Bids'])[bidId]
                dist_tmp = self.getQualityMetric(bid)
                if (dist_tmp >= dist):
                    dist = dist_tmp
                    maxBid = bid
        finally:
            self.lock.release()
        return maxBid

    def calculateBidMaximumQuality(self):  # TESTED: OK
        ''' 
        Get the bid with the maximum quality and maximum price
        '''
        logger.debug('Starting CalculateBidMaximumQuality')
        bid = Bid()
        uuidId = uuid.uuid1()    # make a UUID based on the host ID and current time
        idStr = str(uuidId)
        bid.setValues(idStr,self._list_vars['strId'], (self._service).getId())

        # Establish the bid price.
        for decisionVariable in (self._service)._decision_variables:
            if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                max_val = (self._service)._decision_variables[decisionVariable].getMaxValue()
                bid.setDecisionVariable(decisionVariable, max_val)
        
        # Establish the bid quality.
        for decisionVariable in (self._service)._decision_variables:
            if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                if ((self._service)._decision_variables[decisionVariable].getOptimizationObjective() == DecisionVariable.OPT_MAXIMIZE):
                    optimum = 1 # Maximize
                    val = (self._service)._decision_variables[decisionVariable].getMaxValue()
                else:
                    optimum = 2 # Minimize
                    val = (self._service)._decision_variables[decisionVariable].getMinValue()
            
                bid.setDecisionVariable(decisionVariable, val)
        logger.debug('Ending CalculateBidMaximumQuality')
        return bid

    def calculateNewBidMaximumQuality(self, currentPeriod, radius, currBid, PotentialMaxBid, staged_bids, fileResult):
        '''
        This procedure creates a new exploratory bid towards the maximum quality
        '''
        self.registerLog(fileResult, 'Starting calculateNewBidMaximumQuality')
        orientation = Provider.MARKET_SHARE_ORIENTED
        newBid = None
        if currBid.isEqual(PotentialMaxBid):
            newBid = None
        else:
            output = self.generateDirectionMiddleMaximum( currBid, PotentialMaxBid, fileResult)
            newBid, bidPrice, send = self.moveBidOnDirectionUnconstrained(currBid, output)
            if (send == True):
                self.registerLog(fileResult,'Period:' + str(currentPeriod) + ' Bid moved:' + currBid.getId() + ' Bid created:' + newBid.getId() + ' Bid Price:' + str(bidPrice))
                unitaryBidCost = self.completeNewBidInformation(newBid, bidPrice, fileResult)
                if bidPrice >= unitaryBidCost:
                    marketZoneDemand, forecast = self.calculateMovedBidForecast(currentPeriod, radius, currBid, newBid, orientation, fileResult)
                    staged_bids[newBid.getId()] = {'Object': newBid, 'Action': Bid.ACTIVE, 'MarketShare': marketZoneDemand, 'Forecast': forecast }
                    self.registerLog(fileResult, 'New bid created - ready to be send:' +  newBid.getId() + 'Forecast:' + str(forecast))
                else:
                    newBid = None
            else:
                newBid = None
        self.registerLog(fileResult, 'Ending calculateNewBidMaximumQuality')
        return newBid

    def calculateNewBidMinimumQuality(self, currentPeriod, radius, currBid, PotentialMinBid, staged_bids, fileResult):
        '''
        This procedure creates a new exploratory bid towards the minimum quality
        '''
        self.registerLog(fileResult, 'Starting calculateNewBidMinimumQuality')
        orientation = Provider.MARKET_SHARE_ORIENTED
        newBid = None
        if currBid.isEqual(PotentialMinBid):
            newBid = None
        else:
            output = self.generateDirectionMiddleMinimum( currBid, PotentialMinBid, fileResult)
            print output
            newBid, bidPrice, send = self.moveBidOnDirectionUnconstrained(currBid, output)
            self.registerLog(fileResult, 'Ending calculateNewBidMinimumQuality')
            if (send == True):
                self.registerLog(fileResult,'Period:' + str(currentPeriod) + ' Bid moved:' + currBid.getId() + ' Bid created:' + newBid.getId() + ' Bid Price:' + str(bidPrice))
                unitaryBidCost = self.completeNewBidInformation(newBid, bidPrice, fileResult)
                if bidPrice >= unitaryBidCost:
                    marketZoneDemand, forecast = self.calculateMovedBidForecast(currentPeriod, radius, currBid, newBid, orientation, fileResult)
                    staged_bids[newBid.getId()] = {'Object': newBid, 'Action': Bid.ACTIVE, 'MarketShare': marketZoneDemand, 'Forecast': forecast }
                    self.registerLog(fileResult, 'New bid created - ready to be send:' +  newBid.getId() + 'Forecast:' + str(forecast))
                else:
                    newBid = None
            else:
                newBid = None
        self.registerLog(fileResult, 'Ending calculateNewBidMinimumQuality')
        return newBid

    def calculateIntervalsPrice(self, market_position, min_value, max_value):
        '''
        Compute the price interval where the offering will be placed.
        According to the market_position signal received by the simulation
        environment (demand server), the provider's offering will compete
        in quality (higher price expected) or price (lower quality expected).
        '''
        logger.debug('Starting calculateIntervals Price - parameters' + str(market_position) \
                 + ':' + str(min_value) + ':' + str(max_value))
        # if market prosition greater than 0.65
        # the provider's offer is going to compete on quality 
        if (market_position > 0.65): 
            min_val_adj = min_value + (( max_value - min_value ) * 0.65)
            max_val_adj = max_value
            
        # if market prosition greater than 0.35 and less than 0.65
        # the provider's offer is going to compete on price AND quality
        elif ((market_position >= 0.35) and (market_position <= 0.65)): 
            min_val_adj = min_value + (( max_value - min_value ) * 0.35)
            max_val_adj = min_value + (( max_value - min_value ) * 0.65)
            
        # if market prosition less than 0.35
        # the provider's offer is going to compete on price 
        else:
            min_val_adj = min_value 
            max_val_adj = min_value + (( max_value - min_value ) * 0.35)
        logger.debug('Ending calculateIntervals price - outputs' + str(min_val_adj) + ':' + str(max_val_adj))
        return min_val_adj, max_val_adj

    def calculateIntervalsQuality(self, market_position, min_value, max_value, optimum):
        '''
        Compute the quality interval. The market_position signal varies 
        from zero to one uniformally distributed. Signals closer to one
        offer higher quality levels, while signals closer to zero offer
        lower prices.
        '''
        logger.debug('Starting calculateIntervals Quality- parameters' + str(market_position) + ':' + str(min_value) + ':' + str(max_value) + ':' + str(optimum))
        # if optimum equals one, maximize decision variable
        if (optimum == 1):
            # if market prosition greater than 0.65
            # the provider's offer is going to compete on quality
            if (market_position > 0.65): 
                min_val_adj = min_value + (( max_value - min_value ) * 0.65)
                max_val_adj = max_value
            
            # if market prosition greater than 0.35 and less than 0.65
            # the provider's offer is going to compete on price AND quality
            elif ((market_position >= 0.35) and (market_position <= 0.65)): 
                min_val_adj = min_value + (( max_value - min_value ) * 0.35)
                max_val_adj = min_value + (( max_value - min_value ) * 0.65)
            
            # if market prosition less than 0.35
            # the provider's offer is going to compete on price
            else:
                min_val_adj = min_value 
                max_val_adj = min_value + (( max_value - min_value ) * 0.35)
        
        # if optimum does not equals one, minimize decision variable
        else:
            # if market prosition greater than 0.65
            # the provider's offer is going to compete on quality
            if (market_position > 0.65): 
                min_val_adj = min_value 
                max_val_adj = min_value + (( max_value - min_value ) * 0.35)
            
            # if market prosition greater than 0.35 and less than 0.65
            # the provider's offer is going to compete on price AND quality
            elif ((market_position >= 0.35) and (market_position <= 0.65)): 
                min_val_adj = min_value + (( max_value - min_value ) * 0.35)
                max_val_adj = min_value + (( max_value - min_value ) * 0.65)
            
            # if market prosition less than 0.35
            # the provider's offer is going to compete on price
            else:
                min_val_adj = min_value + (( max_value - min_value ) * 0.65)
                max_val_adj = max_value
            
        logger.debug('Ending calculateIntervals Quality- outputs' + str(min_val_adj) + ':' + str(max_val_adj))
        return min_val_adj, max_val_adj

    def calculateBidUnitaryResourceRequirements(self, bid, fileResult):
        '''
        Calculates the resource requirement in order to execute the 
        service provided by the bid.
        '''    
        self.registerLog(fileResult, 'Starting calculateBidUnitaryResourceRequirements')
        resourceConsumption = {}
        resources = self._used_variables['resources']
        for decisionVariable in (self._service)._decision_variables:
            minValue = ((self._service)._decision_variables[decisionVariable]).getMinValue()
            maxValue = ((self._service)._decision_variables[decisionVariable]).getMaxValue()
            resourceId = ((self._service)._decision_variables[decisionVariable]).getResource() 
            if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                # Bring the cost function associated to the decision variable.
                decisionVar = (self._service)._decision_variables[decisionVariable]
                costFun = decisionVar.getCostFunction() # None if not defined.

                value = float(bid.getQualityRequirement(decisionVariable))
                if ((self._service)._decision_variables[decisionVariable].getOptimizationObjective() == DecisionVariable.OPT_MAXIMIZE):
                    if ((maxValue - minValue) != 0): 
                        percentage = ((value - minValue) / ( maxValue - minValue ))
                    else:
                        percentage = ((value - minValue) / minValue)
                else:
                    if ((maxValue - minValue) != 0):
                        percentage = ((maxValue - value) / ( maxValue - minValue ))
                    else:
                        percentage = ((maxValue - value) / maxValue)
            
                self.registerLog(fileResult, 'value:' + str(value) + 'Percentage:'+ str(percentage))                
                if resourceId in resources:
                    costValue = 0
                    if (costFun != None):
                        costValue = costValue + costFun.getEvaluation(percentage)
                    else:
                        # linear relationship with 1 to 1 relationship.                        
                        costValue = 1 + percentage
                    
                    resourceConsumption.setdefault(resourceId, 0) 
                    resourceConsumption[resourceId] += costValue
        self.registerLog(fileResult, 'Ending calculateBidUnitaryResourceRequirements'+ str(resourceConsumption))
        return resourceConsumption  

    def calculateBidUnitaryCost(self, bid, fileResult):
        '''
        Calculates the bid unitary cost as a function of their decision variables
        '''    
        self.registerLog(fileResult, 'Starting calculateBidUnitaryCost')
        totalUnitaryCost = 0
        
        # If the bid is purchased, then it start by bringing the cost of the bid.
        providerBid = bid.getProviderBid()
        if (providerBid != None):
            totalUnitaryCost = self.getBidPrice(providerBid)
            self.registerLog(fileResult, 'transit bid:' + providerBid.getId() + ' cost:' + str(totalUnitaryCost))
        
        
        resources = self._used_variables['resources']
        resourceConsumption = self.calculateBidUnitaryResourceRequirements(bid, fileResult)
        for resource in resourceConsumption:
            if resource in resources:
                unitaryCost = float((resources[resource])['Cost'])
                totalUnitaryCost = totalUnitaryCost + (unitaryCost * resourceConsumption[resource] )
        self.registerLog(fileResult, 'Ending calculateBidUnitaryCost' + str(totalUnitaryCost))
        return totalUnitaryCost

    def initializeBids(self, market_position, k, fileResult):
        '''
        Method to initialize offers. It receives a signal from the 
        simulation environment (demand server) with its position 
        in the market. The argument position serves to understand 
        if the provider at the beginning is oriented towards low 
        price (0) or high quality (1).  - tested:OK
        '''
        output = {}
        #initialize the k points
        for i in range(0,k):
            output[i] = {}
        for decisionVariable in (self._service)._decision_variables:
            if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                min_val = (self._service)._decision_variables[decisionVariable].getMinValue()
                max_val = (self._service)._decision_variables[decisionVariable].getMaxValue()
                min_val_adj, max_val_adj = self.calculateIntervalsPrice(market_position, min_val, max_val)
                if (k == 1):
                    (output[0])[decisionVariable] = min_val_adj
                elif (k == 2):
                    (output[0])[decisionVariable] = min_val_adj
                    (output[1])[decisionVariable] = max_val_adj
                if (k >= 3):
                    step_size = (max_val_adj - min_val_adj) / (k - 1)
                    for i in range(0,k):
                        (output[i])[decisionVariable] = min_val_adj + step_size * i
        
        for decisionVariable in (self._service)._decision_variables:
            if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                if ((self._service)._decision_variables[decisionVariable].getOptimizationObjective() == DecisionVariable.OPT_MAXIMIZE):
                    optimum = 1 # Maximize
                else:
                    optimum = 2 # Minimize
            
                min_val = (self._service)._decision_variables[decisionVariable].getMinValue()
                max_val = (self._service)._decision_variables[decisionVariable].getMaxValue()
                min_val_adj, max_val_adj = self.calculateIntervalsQuality(market_position, min_val, max_val, optimum)
                if (optimum == 1):
                    if (k == 1):
                        (output[0])[decisionVariable] = min_val_adj
                    elif (k == 2):
                        (output[0])[decisionVariable] = min_val_adj
                        (output[1])[decisionVariable] = max_val_adj
                    if (k >= 3):
                        step_size = (max_val_adj - min_val_adj) / (k - 1)
                        for i in range(0,k):
                            (output[i])[decisionVariable] = min_val_adj + (step_size * i)
                else:
                    if (k == 1):
                        (output[0])[decisionVariable] = max_val_adj
                    elif (k == 2):
                        (output[0])[decisionVariable] = max_val_adj
                        (output[1])[decisionVariable] = min_val_adj
                    if (k >= 3):
                        step_size = (max_val_adj - min_val_adj) / (k - 1)
                        for i in range(0,k):
                            (output[i])[decisionVariable] = max_val_adj - (step_size * i)
        logger.debug('Ranges created in bid initialization')
        return self.createInitialBids(k, output, fileResult)
    

    def createInitialBids(self,k, output, fileResult):
        '''
        Create the inital bids in the market for this provider. - tested:OK
        '''    
        #Creates the offerings with the information in the dictionary
        staged_bids = {}
        for i in range(0,k):
            bid = Bid()
            uuidId = uuid.uuid1()    # make a UUID based on the host ID and current time
            idStr = str(uuidId)
            bid.setValues(idStr,self._list_vars['strId'], (self._service).getId())
            for decisionVariable in (self._service)._decision_variables:
                bid.setDecisionVariable(decisionVariable, (output[i])[decisionVariable])
                if (((self._service)._decision_variables[decisionVariable]).getModeling() == DecisionVariable.MODEL_PRICE):
                    priceBid = (output[i])[decisionVariable]
            
            # Only creates bids that can produce profits
            unitaryBidCost= self.completeNewBidInformation(bid, priceBid, fileResult)
            logger.debug('The cost of bid is: ' + str(bid.getUnitaryCost()))
            if priceBid >= unitaryBidCost:
                staged_bids[bid.getId()] = {'Object': bid, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 0}
        return staged_bids

    def sendBid(self, bid, fileResult):
        '''
        Send a specific bid to the server - tested:OK
        '''
        self.registerLog(fileResult, "sending bid:" + bid.getId() + 'Status:' + bid.getStatusStr() + 'Capacity:' + str(bid.getCapacity()) )
        message = bid.to_message()
        messageResult = self.sendMessageMarket(message)
        if messageResult.isMessageStatusOk():
            pass
        else:
            self.registerLog(fileResult, 'Bid not received! Communication failed Bid:' + bid.getId())
            raise ProviderException('Bid not received! Communication failed')
        self.registerLog(fileResult, "ending sending bid:" + bid.getId())        
                
                
    def sendBids(self, staged_bids, fileResult):
        '''
        With sendBids method, provider sends offers to the Marketplace - tested:OK
        '''
        self.registerLog(fileResult, 'Starting sendBids - number to send:' + str(len(staged_bids)) + ' currentPeriod:' + str(self._list_vars['Current_Period']))
        for bidId in staged_bids:
            bid = (staged_bids[bidId])['Object']
            action = (staged_bids[bidId])['Action']
            bid.setStatus(action)
            self.sendBid(bid, fileResult)
        
        self.registerLog(fileResult, 'Ending sendBids')
        
    
    def purgeBids(self, staged_bids, fileResult):
        '''
        If there is any bid that has not been read by the marketplace, 
        this method will remove it from the buffer. Therefore, in the next
        round, only new bids will be on the buffer.
        
        Precondition: Only bids with changes go in the staged_bids dictionary
        '''
        self.registerLog(fileResult, 'Starting purgeBids')
        self.lock.acquire()
        try:
            # counter initialization
            activeBids = 0
            inactiveBids = 0
            for bidId in staged_bids:
                bid = (staged_bids[bidId])['Object']
                action = (staged_bids[bidId])['Action']
                if (action == Bid.INACTIVE):
                    inactiveBids = inactiveBids + 1
                    bid = (self._list_vars['Bids']).pop(bidId, None)
                    if (bid != None):
                        (self._list_vars['Inactive_Bids'])[bidId] = bid
                if (action == Bid.ACTIVE):
                    (self._list_vars['Bids'])[bidId] = bid
                    activeBids = activeBids + 1

            # Register in the log active bids.
            for bidId in self._list_vars['Bids']:
                self.registerLog(fileResult, 'bid:' + bidId)
            self.registerLog(fileResult, 'Ending purgeBids numActive:' + str(activeBids) + ':nbrInactive:' + str(inactiveBids))
        finally:
            self.lock.release()
        logger.debug('Ending - purge Bids - Number of bids:' + str(len(self._list_vars['Bids'])))

    '''
    Return True if the distance between both bids is less tha radius - tested:OK
    '''
    def areNeighborhoodBids(self, radius, bid1, bid2, fileResult):
        val_return = False        
        distance = self.distance(bid1,bid2, fileResult)
        radiusTmp = radius * len(bid1._decision_variables)
        if distance <= radiusTmp:
            val_return = True            
        #self.registerLog(fileResult, 'Ending - areNeighborhoodBids - Radius' + str(radius) + ' distance:' + str(distance))
        return val_return
        

    def isANonValueAddedBid(self, radius, newBid, staged_bids, fileResult):
        '''
        Determine whether the newbid is a non value added with respecto to
        bids in the staged_bids dictionary. - tested:OK
        '''
        val_return = False
        for bidId in staged_bids:
            bid = (staged_bids[bidId])['Object']
            action = (staged_bids[bidId])['Action']
            if (action == Bid.ACTIVE):
                neighbor = self.areNeighborhoodBids(radius, newBid, bid, fileResult) 
                dominated = self.isDominated(newBid, bid)
                if (dominated == True) or (neighbor == True):
                    val_return = True
                    break
        self.registerLog(fileResult, 'Ending - isANonValueAddedBid - Period:' + str(self.getCurrentPeriod()) + ' output:' + str(val_return))
        return val_return
    
    def eliminateNeighborhoodBid(self, staged_bids, fileResult):
        '''
        Eliminates those bids that are close of each other.
        '''
        # Compare the distance againts bids that will not be changed
        to_delete = {}
        self.registerLog(fileResult, 'Starting - eliminateNeighborhoodBid - output:' + str(len(staged_bids)))
        self.lock.acquire()
        try:
            # Copy the active bids

            compared = {}
            # lopp throuhg bids and compare with those in to_compare dictionary
            for bidId in staged_bids:
                bid = (staged_bids[bidId])['Object']
                action = (staged_bids[bidId])['Action']
                if (action == Bid.ACTIVE):
                    to_compare = []
                    for bidId2 in staged_bids:
                        action2 = (staged_bids[bidId2])['Action']
                        if (action2 == Bid.ACTIVE) and (bidId2 != bidId):
                            if (bidId2 not in compared) and (bidId2 not in to_delete):
                                to_compare.append(bidId2)
                        
                    for bidIdComp in to_compare:
                        bidComp = (staged_bids[bidIdComp])['Object']
                        self.registerLog(fileResult, 'We are going fine :')
                        radius = foundation.agent_properties.own_neighbor_radius
                        if (self.areNeighborhoodBids( radius, bid,bidComp, fileResult) == True):
                            to_delete[bidIdComp] = bidIdComp
                            # transfer capacity
                            newCapacity =  ((staged_bids[bidId])['Object']).getCapacity()
                            newCapacity += bidComp.getCapacity()
                            ((staged_bids[bidId])['Object']).setCapacity(newCapacity)
                            # transfer Forecast
                            newForecast = (staged_bids[bidId])['Forecast']
                            newForecast += (staged_bids[bidIdComp])['Forecast']
                            ((staged_bids[bidId])['Forecast']) = newForecast
                    compared[bidId] = bid
            for bidId in to_delete:
                del staged_bids[bidId]
        finally:
            self.lock.release()
        self.registerLog(fileResult, 'Ending - eliminateNeighborhoodBid  - output:' + str(len(staged_bids)))
            
    def isDominated(self, bid, competitorBid):    
        '''
        This method establishes if a bid is dominated by a competitor bid or not. 
        '''
        logger.debug('Starting isDominated Id:' + self.getProviderId() + '\n' + competitorBid.__str__())
        strict_dom_dimensions = 0
        non_strict_dom_dimensions = 0
        for decisionVariable in bid._decision_variables:
            ownValue = bid.getDecisionVariable(decisionVariable)
            compValue = competitorBid.getDecisionVariable(decisionVariable)
            if (((self._service)._decision_variables[decisionVariable]).getOptimizationObjective() == DecisionVariable.OPT_MINIMIZE):
                ownValue = ownValue * -1
                compValue = compValue * -1
            
            if (ownValue <= compValue):
                non_strict_dom_dimensions += 1
                if (ownValue < compValue):
                    strict_dom_dimensions += 1
        logger.debug('calculate the competitorBid:' + self.getProviderId())
        # We said that the provider bid is dominated if forall decision variables
        # the value is less of equal to the corresponding value, and at least in 
        # one decision variable is strictly less.
        if ((non_strict_dom_dimensions == len(bid._decision_variables)) and ( strict_dom_dimensions > 0)):
            return True
        else:
            return False
        

    '''
    Copy the bid and returns a new bid with the same decision variables. - tested:OK
    '''    
    def copyBid(self, providerBid):
        newBid = Bid()
        uuidId = uuid.uuid1()    # make a UUID based on the host ID and current time
        idStr = str(uuidId)
        newBid.setValues(idStr, self.getProviderId() , self.getServiceId())
        for decisionVariable in (self._service)._decision_variables:
            value = providerBid.getDecisionVariable(decisionVariable)            
            newBid.setDecisionVariable(decisionVariable, value)
        
        return newBid    

    '''
    - tested:OK    
    '''
    def getDBBidMarketShare(self, bidId,  current_period, num_periods, fileResult ):
        self.registerLog(fileResult, 'Starting getDBBidMarketShare' + 'bidId:' + bidId + 'CurrentPeriod:' + str(current_period) + 'num_periods:' + str(num_periods))
        cursor = self._db.cursor() 
        sql = 'select a.period, a.quantity, a.qty_backlog from \
                     Network_Simulation.simulation_bid_purchases a, \
                     Network_Simulation.simulation_generalparameters b \
               where a.execution_count = b.execution_count \
                 and a.bidId = %s and a.period between %s and %s'
        # num periods start in 0, which is the current period
        num_periods = num_periods - 1
        cursor.execute(sql, (bidId, current_period - num_periods, current_period ))
        results = cursor.fetchall()
        bidDemand = {}
        totQuantity = 0
        for row in results:
            self.registerLog(fileResult, 'Entre:' + bidId + 'CurrentPeriod:' + str(current_period) + 'num_periods:' + str(num_periods))
            if int(row[0]) in bidDemand:
                bidDemand[int(row[0])] = bidDemand[int(row[0])] + float(row[1]) + (float(row[2]) * 0.1)
            else:
                bidDemand[int(row[0])] = float(row[1]) + (float(row[2]) * 0.1)
            totQuantity = totQuantity + float(row[1]) + (float(row[2]) * 0.1)
        self.registerLog(fileResult, 'Ending getDBBidMarketShare' + 'bidId:' + bidId + 'totQuantity:' + str(totQuantity))
        return bidDemand, totQuantity
    
    ''' 
    Get the Ancestor Market Share from a parent Bid, results are put in bidDemand and totQuantity - tested Ok
    '''    
    def getDBBidAncestorsMarketShare(self, bid, currentPeriod, numPeriods, fileResult):
        self.registerLog(fileResult, 'Start getDBBidAncestorsMarketShare:' + bid.getId())
        bidDemand = {}
        totQuantity = 0
        nbrAncestors = 0
        if (bid._parent != None):
            bidParent = bid._parent
            while ((bidParent != None) and (nbrAncestors <= numPeriods )):
                if bidParent != None:
                    period = currentPeriod - nbrAncestors
                    bidDemandTmp, totQuantityTmp = self.getDBBidMarketShare(bidParent.getId(), period, 1, fileResult )
                    bidDemand[period] = totQuantityTmp
                    totQuantity = totQuantity + totQuantityTmp

                # Verifies whether the bid has been active for more than one period.
                if (bidParent.getCreationPeriod() >= period):
                    bidParent = bidParent._parent
                nbrAncestors = nbrAncestors + 1
        self.registerLog(fileResult, 'Ending getDBBidAncestorsMarketShare:' + str(totQuantity) )
        return bidDemand, totQuantity
    
    '''
    Brings purchases of other providers' bids around the bid given as parameter. It includes the bid requested. 
    Periods included are [current_period - (num_period-1), current_period]
    Tested Ok
    '''    
    def getDBMarketShareZone(self, bid, related_bids, current_period, num_periods, fileResult, infoType=PURCHASE):
        self.registerLog(fileResult, 'Initializating getDBMarketShareZone - Id:' + bid.getId() + 'Period:' + str(current_period) + 'Num_periods:' + str(num_periods))
        
        cursor = self._db.cursor() 
        if infoType == Provider.PURCHASE: 
            sql = 'select a.period, a.quantity from \
                         Network_Simulation.simulation_bid_purchases a, \
                         Network_Simulation.simulation_generalparameters b \
                   where a.execution_count = b.execution_count \
                     and a.bidId = %s and a.period between %s and %s'
        else:
            sql = 'select a.period, a.qty_backlog from \
                         Network_Simulation.simulation_bid_purchases a, \
                         Network_Simulation.simulation_generalparameters b \
                   where a.execution_count = b.execution_count \
                     and a.bidId = %s and a.period between %s and %s'                     
        # num periods start in 0, which is the current period
        num_periods = num_periods - 1
        cursor.execute(sql, (bid.getId(), current_period - num_periods, current_period ))
        results = cursor.fetchall()
        marketZoneDemand = {}
        bidDemand = {}
        totQuantity = 0
        for row in results:
            bidDemand[int(row[0])] = float(row[1])
            totQuantity = totQuantity + float(row[1])
        # Insert the demand for the bid only when the sql found data.
        if (len(bidDemand) > 0):
                marketZoneDemand[bid.getId()] = bidDemand

        numRelated = 0
        for providerBidId in related_bids:
            cursor.execute(sql, (providerBidId, current_period - num_periods, current_period))
            bidQty = 0
            results2 = cursor.fetchall()
            bidDemand2 = {}
            found = False
            for row in results2:
                bidDemand2[int(row[0])] = float(row[1])
                totQuantity = totQuantity + float(row[1])
                bidQty = bidQty + float(row[1])
                found = True            
            
            if (found == True):
                # the bid was not purchased, then count as a related bid:
                numRelated = numRelated + 1
                self.registerLog(fileResult, 'relatedBid getDBMarketShareZone - Id:' + providerBidId + 'qty:' + str(bidQty))

            # Insert the demand for the bid only when the sql found data.
            if (len(bidDemand2) > 0):
                marketZoneDemand[providerBidId] = bidDemand2
        self.registerLog(fileResult, 'Ending getDBMarketShareZone - Id:' + bid.getId() +  ' totQuantity:' + str(totQuantity) + 'numRelated:' + str(numRelated) )
        return marketZoneDemand, totQuantity, numRelated



    '''
    Brings the profits associated with the bids for the specified period including the bid requested. Tested Ok
    '''    
    def getDBProfitZone(self, bid, related_bids, current_period, fileResult):
        self.registerLog(fileResult, 'Initializating getDBProfitZone - Id:' + bid.getId())
        status = '1'
        cursor = self._db.cursor() 
        sql = 'select a.period, a.quantity, c.unitary_profit \
                from Network_Simulation.simulation_bid_purchases a, \
                     Network_Simulation.simulation_generalparameters b, \
                     Network_Simulation.simulation_bid c \
                where a.execution_count = b.execution_count  \
                  and a.bidId = %s and a.period = %s and a.execution_count = c.execution_count \
                  and a.bidId = c.bidId and c.status = %s'
        
        # variables initialization
        profitZone = {}
        totProfit = 0
        numRelated = 0
                  
        # read the profit for bid.
        bidProfit = {}
        cursor.execute(sql, (bid.getId(), current_period, status ))
        results = cursor.fetchall()
        for row in results:
            if int(row[0]) in bidProfit:
                bidProfit[int(row[0])] = bidProfit[int(row[0])] + float(row[1]) * float(row[2])
            else:
                bidProfit[int(row[0])] = float(row[1]) * float(row[2])
            totProfit = totProfit + ( float(row[1]) * float(row[2]))
        # Insert the demand for the bid only when the sql found data.
        if (len(bidProfit) > 0):
                profitZone[bid.getId()] = bidProfit
        
        self.registerLog(fileResult, 'getDBProfitZone 2- Id:' + bid.getId())
        # read the profit for related_bids.        
        for providerBidId in related_bids:
            cursor.execute(sql, (providerBidId, current_period, status ))
            bidProf = 0
            results2 = cursor.fetchall()
            bidProfit2 = {}
            found = False
            for row in results2:
                if int(row[0]) in bidProfit2:
                    bidProfit2[int(row[0])] = bidProfit2[int(row[0])] + float(row[1]) * float(row[2])
                else:
                    bidProfit2[int(row[0])] = float(row[1]) * float(row[2])
                totProfit = totProfit + ( float(row[1]) * float(row[2]))
                bidProf = bidProf + ( float(row[1]) * float(row[2]))
                found = True            
            
            if (found == True):
                # the bid was not purchased, then count as a related bid:
                numRelated = numRelated + 1
                self.registerLog(fileResult, 'relatedBid getDBProfitZone - Id:' + providerBidId + 'profit:' + str(bidProf))
                profitZone[providerBidId] = bidProfit2
                        
        self.registerLog(fileResult, 'getDBProfitZone 3- Id:' + bid.getId())
        return profitZone, totProfit, numRelated


    
    def replaceDominatedBids(self, currentPeriod, radius, staged_bids, fileResult):
        '''
        In case a offer hasn't been sucessful in the market, i.e. has low
        market share, the method replaceDominateBids updates the offering
        information to mimic the offer with higher market share.
        '''
        self.registerLog(fileResult,'Initializating replace dominance bids')
        self.lock.acquire()
        try:
            for bidId in self._list_vars['Bids']:
                bid = (self._list_vars['Bids'])[bidId]
                for providerBidId in self._list_vars['Related_Bids']:
                    providerBid = (self._list_vars['Related_Bids'])[providerBidId]
                    if (self.isDominated(bid, providerBid)):
                        # Puts inactive the bid and copy the information for the competitor's bid 
                        staged_bids[bid.getId()] = {'Object': bid, 'Action': Bid.INACTIVE, 'MarketShare' : {}, 'Forecast' : 0 }
                        newBid = self.copyBid(providerBid)
                        newBid.setNumberPredecessor(bid.getNumberPredecessor())
                        priceBid = newBid.getDecisionVariable((self._service).getPriceDecisionVariable())
                        unitaryBidCost = self.completeNewBidInformation(newBid,priceBid, fileResult) 
                        if priceBid >= unitaryBidCost:
                            marketZoneDemand, forecast = self.calculateMovedBidForecast(currentPeriod, radius, bid, newBid, Provider.MARKET_SHARE_ORIENTED, fileResult)
                            staged_bids[newBid.getId()] = {'Object': newBid, 'Action': Bid.ACTIVE, 'MarketShare' : marketZoneDemand, 'Forecast' : forecast } 
                        break
        except Exception as e:
            raise FoundationException(str(e))
        finally:
            self.lock.release()
        self.registerLog(fileResult, 'Ending replace dominance bids stagedBids:' + str(len(staged_bids)))
    
    def getBidById(self, bidId):
        '''
        The method getBidId gets the offering by identification number. - Tested Ok.
        '''
        logger.debug('Getting own bid:' + bidId)
        bid = None
        self.lock.acquire()
        try:
            bid =  (self._list_vars['Bids'])[bidId]
        finally:
            self.lock.release()
        return bid
    
    def getCompetitorBid(self, competitorBidId):
        '''
        This method gets the competitors (other service providers) offers
        in the marketplace.
        '''
        competitorBid = None
        self.lock.acquire()
        try:
            if competitorBidId in self._list_vars['Related_Bids']:
                competitorBid = (self._list_vars['Related_Bids'])[competitorBidId]
            else:
                message = Message('')
                message.setMethod(Message.GET_BID)
                message.setParameter("Bid", competitorBidId)
                messageResult = self.sendMessageMarket(message)
                if messageResult.isMessageStatusOk():
                    bid = Bid()
                    bid.setFromMessage(self._service, messageResult)
                    # We put the bid as a related bid.
                    (self._list_vars['Related_Bids'])[bid.getId()] = bid
                    competitorBid = bid
                else:
                    logger.error('Bid not received! Communication failed')
                    raise ProviderException('Bid not received! Communication failed')
                logger.debug('Getting competitors bid:' + competitorBidId)
            competitorBid =  (self._list_vars['Related_Bids'])[competitorBidId]
        finally:
            self.lock.release()
        
        return competitorBid

    def generateDirectionBetweenTwoBids(self, bid1, bid2, fileResult): #Tested Ok
        '''
        This method establishes the direction (the positive or negative) 
        value in the decision variable cartesian space to goes from bid 1 to bid 2. 
        In this procedure the sign is only used when the system have to use another step not
        defined by this function. When the system uses this step, the sign is given in the step.
        '''
        output = {}
        self.lock.acquire()
        try:
            self.registerLog(fileResult, 'generateDirectionBetweenTwoBids:' + bid1.__str__())
            #self.registerLog(fileResult, 'generateDirectionBetweenTwoBids:' + bid2.__str__())    
            for decisionVariable in (self._service)._decision_variables:
                min_value = 1.0
                max_value = 1.0 + (self._used_variables['marketPosition'] / 3)
                step = ( bid2.getDecisionVariable(decisionVariable) - bid1.getDecisionVariable(decisionVariable) ) 
                step = step * self._list_vars['Random'].uniform(min_value, max_value)

                if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                    if (bid2.getDecisionVariable(decisionVariable) > bid1.getDecisionVariable(decisionVariable)):
                        direction = 1
                    else:
                        direction = -1
                else:
                    if (((self._service)._decision_variables[decisionVariable]).getOptimizationObjective() == DecisionVariable.OPT_MAXIMIZE):
                        if (bid2.getDecisionVariable(decisionVariable) > bid1.getDecisionVariable(decisionVariable)):
                            direction = 1
                        else:
                            direction = -1
                    else:
                        if (bid2.getDecisionVariable(decisionVariable) < bid1.getDecisionVariable(decisionVariable)):
                            direction = -1
                        else:
                            direction = 1
                output[decisionVariable] = {'Direction' : direction, 'Step' : step }
            self.registerLog(fileResult, 'generateDirectionBetweenTwoBids output :' + str(output))

        finally:
            self.lock.release()
        
        return output

    def generateDirectionMiddleMinimum(self, bid1, bid2, fileResult):
        '''
        This method establishes the direction (the positive or negative) 
        value in the decision variable cartesian space to goes from bid 1 to the middle of bid 1 and bid 2
        represents the bid with the minimum quality
        '''
        output = {}
        self.lock.acquire()
        try:
            self.registerLog(fileResult, 'generateDirectionMiddleMinimum:' + bid1.__str__() + 'MinBid:' + bid2.__str__())
            for decisionVariable in (self._service)._decision_variables:
                if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                    val = (bid2.getDecisionVariable(decisionVariable) + bid1.getDecisionVariable(decisionVariable)) / 2
                    step = val - bid1.getDecisionVariable(decisionVariable)
                    if (step > 0):
                        direction = 1
                    else:
                        direction = -1
                else:
                    step = bid2.getDecisionVariable(decisionVariable) - bid1.getDecisionVariable(decisionVariable)
                    if (((self._service)._decision_variables[decisionVariable]).getOptimizationObjective() == DecisionVariable.OPT_MAXIMIZE):
                        if (step > 0):
                            direction = 1
                        else:
                            direction = -1
                    else:
                        if (step < 0):
                            direction = -1
                        else:
                            direction = 1
                output[decisionVariable] = {'Direction' : direction, 'Step' : step }
            self.registerLog(fileResult, 'generateDirectionMiddleMinimum output :' + str(output))

        finally:
            self.lock.release()
        
        return output

    def generateDirectionMiddleMaximum(self, bid1, bid2, fileResult):
        '''
        This method establishes the direction (the positive or negative) 
        value in the decision variable cartesian space to goes from bid 1 to the middle of bid 1 and bid 2, bid2 
        represents the bid with the maxium quality
        '''
        output = {}
        self.lock.acquire()
        try:
            self.registerLog(fileResult, 'generateDirectionMiddleMaximum:' + bid1.__str__())
            for decisionVariable in (self._service)._decision_variables:
                if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                    step = bid2.getDecisionVariable(decisionVariable) - bid1.getDecisionVariable(decisionVariable)
                    if (bid2.getDecisionVariable(decisionVariable) > bid1.getDecisionVariable(decisionVariable)):
                        direction = 1
                    else:
                        direction = -1
                else:
                    val = (bid2.getDecisionVariable(decisionVariable) + bid1.getDecisionVariable(decisionVariable)) / 2
                    step = val - bid1.getDecisionVariable(decisionVariable)
                    if (((self._service)._decision_variables[decisionVariable]).getOptimizationObjective() == DecisionVariable.OPT_MAXIMIZE):
                        if (step > 0):
                            direction = 1
                        else:
                            direction = -1
                    else:
                        if (step < 0):
                            direction = -1
                        else:
                            direction = 1
                output[decisionVariable] = {'Direction' : direction, 'Step' : step }
            self.registerLog(fileResult, 'generateDirectionMiddleMaximum output :' + str(output))

        finally:
            self.lock.release()
        
        return output

        
    def followCompetitorsBid(self, mybidId, otherBidId, fileResult):
        '''
        This method is called in two situations:
        1. When a offer is in a region where has low, or no market share
        2. When the competitor's offer has a better market share than own
        offer.
        This method determines the direction to chase a better offer in 
        both cases.
        '''
        logger.debug("Initializing followCompetitorsBid")
        output = {}
        try:
            myBid = self.getBidById(mybidId)
            otherBid = self.getCompetitorBid(otherBidId)
            output = self.generateDirectionBetweenTwoBids(myBid, otherBid, fileResult)
        except ProviderException as e:
            # The market place could not send the bid, so the best action 
            # is to maintain current position.
            direction = 0
            step = 0
            for decisionVariable in (self._service)._decision_variables:
                output[decisionVariable] = {'Direction' : direction, 'Step' : step }
        self.registerLog(fileResult, 'followCompetitorsBid:' + str(output)) 
        logger.debug("Ending followCompetitorsBid")
        return output
    
    def improveBidForProfits(self, service, fileResult, reverse):
        ''' 
        The bid does not have any competitor registered, so in case that has zero users
        we take a direction of increasing decision variable objectives for profits. - Tested Ok
        '''
        self.registerLog(fileResult, 'improveBidForProfits - Reverse:' + str(reverse)) 
        output = {}
        self.lock.acquire()
        try:
            
            for decisionVariable in service._decision_variables:
                min_value = (service.getDecisionVariable(decisionVariable)).getMinValue()
                max_value = (service.getDecisionVariable(decisionVariable)).getMaxValue()
                maximum_step = (max_value - min_value) * self._used_variables['adaptationFactor']
                # Since we want to determine the step size, we have to do invert the
                # meaning of market position. 
                market_position = 1 - self._used_variables['marketPosition']
                # Gets the objetive to persuit.
                if (service._decision_variables[decisionVariable].getOptimizationObjective() == DecisionVariable.OPT_MAXIMIZE):
                    optimum = 1 # Maximize
                else:
                    optimum = 2 # Minimize

                # Gets the modeling objetive of the decision variable
                if (service._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                    min_val_adj, max_val_adj = self.calculateIntervalsPrice(market_position, 0, maximum_step)
                    direction = 1 * reverse
                    step = self._list_vars['Random'].uniform(min_val_adj, max_val_adj) * reverse
                else:
                    min_val_adj, max_val_adj = self.calculateIntervalsQuality(market_position, 0, maximum_step, optimum)
                    if (optimum == 1): # Maximize
                        direction = -1 * reverse
                        step = self._list_vars['Random'].uniform(min_val_adj, max_val_adj) * -1 * reverse
                    else: # Minimize
                        step = ( self._list_vars['Random'].uniform(min_val_adj, max_val_adj) ) * reverse
                        direction = 1 * reverse         
                output[decisionVariable] = {'Direction' : direction, 'Step': step}
            self.registerLog(fileResult, 'improveBidForProfits:' + str(output)) 
            
        finally:
            self.lock.release()
        return output
   
    def maintainBidForCompetence(self, fileResult):
        ''' 
        Return the direction for improvement quality of service 
        '''
        output = {}
        direction = 0 
        step = 0
        for decisionVariable in (self._service)._decision_variables:
            output[decisionVariable] = {'Direction' : direction, 'Step': step}
        return output

    def improveBidForCompetence(self, fileResult):
        '''
        The bid does not have any competitor registered, so in case that has zero users
        we take a direction of increasing decision variable objectives for user.
        '''
        output = {}
        self.lock.acquire()
        try:
            for decisionVariable in (self._service)._decision_variables:
                min_value = (self._service.getDecisionVariable(decisionVariable)).getMinValue()
                max_value = (self._service.getDecisionVariable(decisionVariable)).getMaxValue()
                maximum_step = (max_value - min_value) * self._used_variables['adaptationFactor']
                # Since we want to determine the step size, we have to do invert the
                # meaning of market position. 
                market_position = 1 - self._used_variables['marketPosition']
                # Gets the objetive to persuit.
                if ((self._service)._decision_variables[decisionVariable].getOptimizationObjective() \
                    == DecisionVariable.OPT_MAXIMIZE):
                    optimum = 1 # Maximize
                else:
                    optimum = 2 # Minimize

                # Gets the modeling objetive of the decision variable
                if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                    min_val_adj, max_val_adj = self.calculateIntervalsPrice(market_position, 0, maximum_step)
                    direction = -1
                    step = self._list_vars['Random'].uniform(min_val_adj, max_val_adj) * -1
                    if (self._used_variables['debug'] == True):
                        fileResult.write('Price variable:' + str(min_val_adj) + str(max_val_adj) + '\n') 
                        fileResult.write('Step variable:' + str(step)  + '\n') 
                else:
                    min_val_adj, max_val_adj = self.calculateIntervalsQuality(market_position, 0, maximum_step, optimum)
                    if (optimum == 1):
                        direction = 1
                        step = self._list_vars['Random'].uniform(min_val_adj, max_val_adj)
                    else:
                        step = self._list_vars['Random'].uniform(min_val_adj, max_val_adj) * -1
                        direction = -1         

                    if (self._used_variables['debug'] == True):
                        fileResult.write('Quality variable:' + str(min_val_adj) + str(max_val_adj) + '\n') 
                        fileResult.write('Step variable:' + str(step)  + '\n') 
                output[decisionVariable] = {'Direction' : direction, 'Step': step}
            self.registerLog(fileResult, 'improveBidForCompetence:' + str(output)) 
            
        finally:
            self.lock.release()
        
        return output

    def avoidCompetitorBid(self, mybidId, otherBidId, fileResult):
        '''
        Generate direction to go into the opposite direction of a 
        worse offer than the current one.
        '''
        self.registerLog(fileResult, 'starting avoidCompetitorBid') 
        output = {}
        try:
            myBid = self.getBidById(mybidId)
            otherBid = self.getCompetitorBid(otherBidId)
            if (myBid.isEqual(otherBid)):
                output = self.improveBidForCompetence(fileResult)
            else:
                output = self.generateDirectionBetweenTwoBids(otherBid, myBid, fileResult)
        except ProviderException as e:
            # The market place could not send the bid, so the best action 
            # is to maintain current position.
            direction = 0
            step = 0
            for decisionVariable in (self._service)._decision_variables:
                output[decisionVariable] = {'Direction' : direction, 'Step' : step } 
        self.registerLog(fileResult, 'avoidCompetitorBid:' + str(output)) 
        return output

    def calculateProgressionDirection(self, progression, towards, fileResult):
        '''
        Generates the direction of between a list of bids as the proggresion
        from the initial bid to the end bid.
        '''
        self.registerLog(fileResult, 'calculateProgressionDirection:' + str(towards)) 
        bidInitial = (progression[len(progression) - 1])['bid']
        bidFinal = (progression[0])['bid']
        if (towards == 1):
            output = self.generateDirectionBetweenTwoBids(bidInitial, bidFinal, fileResult)
        else:
            output = self.generateDirectionBetweenTwoBids(bidFinal, bidInitial, fileResult)
        self.registerLog(fileResult, 'calculateProgressionDirection:' + str(output)) 
        return output

    def generateOwnDirection(self, currentPeriod, mybidId, ownMarketShare, fileResult):
        '''
        Generates the direction to follow for a bid given if it has market share or not.
        '''
        self.registerLog(fileResult, 'generateOwnDirection:' + str(ownMarketShare)) 
        output = {}
        myBid = self.getBidById(mybidId)
        if (ownMarketShare == 0):
            # The bid does not have any competitor registered, so in case that has zero users
            # we take a direction of increasing decision variable objectives for user.
            output = self.improveBidForCompetence(fileResult)
        else:        
            can_continue, progression = self.continueDirectionImprovingProfits(currentPeriod, myBid, fileResult)
            if (can_continue == True):
            # If it does not have competitors and it has users, we just continue in the same point
            # We understand this situtaion as a niche provider.
                output = self.maintainBidForCompetence(fileResult)
            else:
                output = self.improveBidForProfits(self._service, fileResult, -1)
    
        self.registerLog(fileResult, 'Ending generateOwnDirection:' + str(output)) 
        return output

    def evaluateDirectionalDerivate(self, currentPeriod, radius, bid, fileResult):
        '''
        This method evaluates if there is a direction to replace the 
        offer in order to improve the number of customers.
        If the current offer has no competitors, the method looks to 
        improve its market share by increasing its decision variables.
        '''
        self.registerLog(fileResult,"Initializing evaluateDirectionalDerivate")
        
        # Variable initialization
        direction = []
        ownMarketShare = 0
        if bid.getId() in (self._list_vars['Bids']).keys():
            relatedBids = self.getRelatedBids( bid, currentPeriod -1, 0, radius, fileResult)
            bidDemandOwn, ownMarketShare = self.getDBBidMarketShare(bid.getId(),currentPeriod -1, 1, fileResult)
            # bring the market share of every related bid.
            competitiveBids = []
            for competitorBidId in relatedBids:
                bidDemandTmp, marketShare = self.getDBBidMarketShare(competitorBidId,currentPeriod -1, 1, fileResult)
                competitiveBids.append((competitorBidId,marketShare))
            # The tuple that corresponds to the offer must be eliminated. 
            competitiveBids.sort( key=lambda tup:tup[1], reverse=True)
            hasCompetitorBids = False
            numSplits = 0
            self.registerLog(fileResult, 'evaluateDirectionalDerivate - Period:' + str(currentPeriod) + 'BidId:' + bid.getId()) 
            for competitiveBid in competitiveBids:
                # competitiveBid has a tuple, the first element is the id of the bid, 
                # the second element is the market share.
                marketShare = competitiveBid[1]
                if (marketShare > 0): # Only tries to compare agains bids that have market
                    hasCompetitorBids = True
                    if (marketShare >= ownMarketShare):
                        # Exists a direction that can increase the number of customers.
                        direction.append(self.followCompetitorsBid(bid.getId(), competitiveBid[0], fileResult))
                        numSplits = numSplits + 1
                    else:
                        # There are no offerings better than current offer
                        direction.append(self.avoidCompetitorBid(bid.getId(), competitiveBid[0], fileResult))
                        numSplits = numSplits + 1
                    if (numSplits == 5 ):
                        break    
            
            if (hasCompetitorBids == False): 
                direction.append(self.generateOwnDirection(currentPeriod, bid.getId(), ownMarketShare, fileResult))

        else:
            # This does not create a new direction.             
            self.registerLog(fileResult, 'Bid has not register in the current bids:' + bid.getId())
                        
        self.registerLog(fileResult, 'Ending evaluateDirectionalDerivate - Nbr directions:' + str(len(direction)))
        return direction

    def distance(self, bid1, bid2, fileResult):
        '''
        Method to calculate the distance from a bid to another. Tested Ok.
        '''
        self.registerLog(fileResult, 'Starting Distance')
        distance = 0
        for decisionVariable in (self._service)._decision_variables:
            min_value = (((self._service)._decision_variables)[decisionVariable]).getMinValue()
            max_value = (((self._service)._decision_variables)[decisionVariable]).getMaxValue()
            bid1_value = bid1.getDecisionVariable(decisionVariable)
            bid2_value = bid2.getDecisionVariable(decisionVariable)
            var_range = max_value - min_value
            if (var_range > 0):
                distance_value = math.fabs(bid1_value - bid2_value) / var_range
            else:
                distance_value = 0
            distance = distance + ((distance_value)** 2)
        distance = math.sqrt(distance)
        self.registerLog(fileResult, 'Ending Distance ' + str(distance))
        return distance

    def MinimizingDelta(self, step, numPredecessors):
        assert(numPredecessors >= 1), "The number of precessors is less than 1"
        step = step / numPredecessors
        return step

    def moveBidOnDirection(self, bid, directionMove, fileResult):
        # Create a new bid
        self.registerLog(fileResult, 'Starting moveBidOnDirection')
        newBid = Bid()
        uuidId = uuid.uuid1()    # make a UUID based on the host ID and current time
        idStr = str(uuidId)
        newBid.setValues(idStr, bid.getProvider(), bid.getService())
        send = False
        newBid.setNumberPredecessor(bid.getNumberPredecessor())
        for decisionVariable in directionMove:
            direction = (directionMove[decisionVariable])['Direction']
            step = (directionMove[decisionVariable])['Step']
            step = self.MinimizingDelta(step, bid.getNumberPredecessor())
            min_value = (self._service.getDecisionVariable(decisionVariable)).getMinValue()
            max_value = (self._service.getDecisionVariable(decisionVariable)).getMaxValue()
            maximum_step = (max_value - min_value) * self._used_variables['adaptationFactor']
            if ((direction == 1) or (direction == -1)):
                if (abs(step) <= maximum_step):
                    new_value = bid.getDecisionVariable(decisionVariable) + step
                else:
                    if (direction == 1):
                        new_value = bid.getDecisionVariable(decisionVariable) + maximum_step
                    else:
                        new_value = bid.getDecisionVariable(decisionVariable) - maximum_step
                send = True
            else:
                new_value = bid.getDecisionVariable(decisionVariable)
            # Makes sure that the value is within the boundary.
            new_value = max(min_value, new_value)
            new_value = min(max_value, new_value)
            if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                bidPrice = new_value
            newBid.setDecisionVariable(decisionVariable, new_value)
            assert newBid.getNumberPredecessor() == bid.getNumberPredecessor(), "Incorrect number of predecessors in child"
        self.registerLog(fileResult, 'Ending moveBidOnDirection')
        return newBid, bidPrice, send
    

    def moveBidOnDirectionUnconstrained(self, bid, directionMove ):
        # Create a new bid
        newBid = Bid()
        uuidId = uuid.uuid1()    # make a UUID based on the host ID and current time
        idStr = str(uuidId)
        newBid.setValues(idStr, bid.getProvider(), bid.getService())
        send = False
        newBid.setNumberPredecessor(0) # New bids can freely move.
        for decisionVariable in directionMove:
            direction = (directionMove[decisionVariable])['Direction']
            step = (directionMove[decisionVariable])['Step']
            min_value = (self._service.getDecisionVariable(decisionVariable)).getMinValue()
            max_value = (self._service.getDecisionVariable(decisionVariable)).getMaxValue()
            maximum_step = (max_value - min_value)
            if ((direction == 1) or (direction == -1)):
                if (abs(step) <= maximum_step):
                    new_value = bid.getDecisionVariable(decisionVariable) + step
                else:
                    if (direction == 1):
                        new_value = bid.getDecisionVariable(decisionVariable) + maximum_step
                    else:
                        step = self.MinimizingDelta(maximum_step, bid.getNumberPredecessor())
                        new_value = bid.getDecisionVariable(decisionVariable) - maximum_step
                send = True
            else:
                new_value = bid.getDecisionVariable(decisionVariable)
            # Makes sure that the value is within the boundary.
            new_value = max(min_value, new_value)
            new_value = min(max_value, new_value)
            if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                bidPrice = new_value
            newBid.setDecisionVariable(decisionVariable, new_value)
        return newBid, bidPrice, send

    '''
    Completes the costs of the bid, profit and period - Tested Ok
    '''    
    def completeNewBidInformation(self, bid, bidPrice, fileResult ):
        unitaryBidCost = self.calculateBidUnitaryCost(bid, fileResult)
        bid.setUnitaryCost(unitaryBidCost)
        bid.setUnitaryProfit(bidPrice - unitaryBidCost)
        bid.setCreationPeriod(self._list_vars['Current_Period'])
        bid.incrementPredecessor()
        self.registerLog(fileResult, 'completeNewBidInformation' + 'Period:' + str(self._list_vars['Current_Period']) + ':Id:' + bid.getId() + ':Price:' + str(bidPrice) + ':cost:' + str(unitaryBidCost) + ':profit:' + str(bid.getUnitaryProfit()) + 'Predecessors:' + str(bid.getNumberPredecessor()) )
        return unitaryBidCost
    
    '''
    gets the consolidated demand from the dictionaries: demand and demand2. 
    '''
    def consolidateDemand(self, demand, totQuantity, demand2, totQuantity2):
        demand3 = {}
        totQuantity = 0
        
        for period in demand:
            demand3[period] = demand[period]
        
        for period in demand2:
            if (period in demand3.keys()):
                demand3[period] = demand3[period] + demand2[period]
            else:
                demand3[period] = demand2[period]
        
        totQuantity = totQuantity + totQuantity2
        return demand3, totQuantity
    
    '''
    Create progression for call the moving average algorithm. 
    Bid demand is in the form: period1 - value1, period2, value2, etc...
    '''
    def calculateForecastProgression(self, bidDemand):
        keys = bidDemand.keys()
        keys.sort(reverse=True)
        progression = []
        for period in keys:
            progression.append({'bid': ' ', 'profit': 0, 'delta_profit': bidDemand[period]})
        return progression

    '''
    Calculate the any bid forecast, the bid plus ancestors
    '''
    def calculateBidForecast(self, currentPeriod, bid, fileResult):
        self.registerLog(fileResult, 'starting calculateBidForecast')
        bidDemand, bidQuantity = self.getDBBidMarketShare(bid.getId(), currentPeriod - 1 , 1, fileResult)        
        bidDemand2, bidQuantity2 = self.getDBBidAncestorsMarketShare( bid, currentPeriod - 1, self.getNumAncestors(), fileResult )
        bidDemand3, bidQuantity3 = self.consolidateDemand(bidDemand, bidQuantity, bidDemand2, bidQuantity2)
        self.registerLog(fileResult, 'calculateBidForecast included numPeriods:' + str(len(bidDemand3)))
        for period in bidDemand3:
            self.registerLog(fileResult, 'calculateBidForecast - period'+ str(period)+ 'Qty:' + str(bidDemand3[period]))
        progression =self.calculateForecastProgression(bidDemand3)
        forecast = self.movingAverage(progression)
        self.registerLog(fileResult, 'Ending calculateBidForecast:' + str(forecast))
        return bidDemand3, forecast
        
    '''
    Calculates the forecast for a bid according with the orientation for the bid.
    Tested: Ok
    '''    
    def calculateMovedBidForecast(self, currentPeriod, radius, bid, newBid, orientation, fileResult):
        self.registerLog(fileResult, 'starting calculateMovedBidForecast ' + str(orientation))
        marketZoneDemand = {}        
        forecast = 0
        totForecast = 0
        numRelated = 0

        # First it brings the demand for the own demand.        
        bidDemand, forecast = self.calculateBidForecast(currentPeriod, bid, fileResult)
        marketZoneDemand[bid.getId()] = bidDemand
        totForecast = forecast
                
        # Then if it is market share, it brings the demand for all related bids.
        if (orientation == Provider.MARKET_SHARE_ORIENTED):
            self.registerLog(fileResult, 'Provider Market Share Oriented')
            competitorBids = self.getRelatedBids(bid, currentPeriod - 1 , 0, radius, fileResult)
            for compBidId in competitorBids:
                competitorBid = competitorBids[compBidId]
                bidDemand, forecast = self.calculateBidForecast(currentPeriod, competitorBid, fileResult)
                if forecast > 0:
                    numRelated = numRelated + 1
                    marketZoneDemand[compBidId] = bidDemand
                totForecast = totForecast + forecast
                
            self.registerLog(fileResult, 'End numRelated'+  str(numRelated))
            totForecast = totForecast / ( numRelated + 1 )
                
        self.registerLog(fileResult, 'Ending calculateMovedBidForecast - Period: ' + str(currentPeriod) + ' Forecast:' + str(totForecast))
        return marketZoneDemand, totForecast

    def moveBid(self, currentPeriod, radius, bid, moveDirections, marketShare, staged_bids, orientation, fileResult):
        '''
        If there is a better position to improve the current offer,
        this method will move the offer to the better position in unit
        steps.
        '''
        logger.debug("Initiating moveBid")
        send = False
        forecast = 0
        staged_bids_tmp = []
        self.registerLog(fileResult, 'moveBid:' + bid.getId() + 'NumBids:' + str(len(staged_bids))) 
        for directionMove in moveDirections:
            newBid, bidPrice, send = self.moveBidOnDirection( bid, directionMove, fileResult)
            if (send == True):
                self.registerLog(fileResult,'Period:' + str(currentPeriod) + ' Bid moved:' + bid.getId() + ' Bid created:' + newBid.getId() + ' Bid Price:' + str(bidPrice))
                unitaryBidCost = self.completeNewBidInformation(newBid, bidPrice, fileResult)
                if bidPrice >= unitaryBidCost:
                    if (self.isANonValueAddedBid( radius, newBid, staged_bids, fileResult) == False):
                        newBid.insertParentBid(bid)
                        marketZoneDemand, forecast = self.calculateMovedBidForecast(currentPeriod, radius, bid, newBid, orientation, fileResult)
                        self.registerLog(fileResult, 'New bid created - ready to be send:' +  newBid.getId() + 'Forecast:' + str(forecast))
                        staged_bids[newBid.getId()] = {'Object': newBid, 'Action': Bid.ACTIVE, 'MarketShare': marketZoneDemand, 'Forecast': forecast }
                        staged_bids_tmp.append(newBid.getId())
            else:
                self.registerLog(fileResult, 'Bid not moved:' + bid.getId())

        # In any case inactive the current bid, if it has purchases copy it.
        if (marketShare > 0): 
            copyB = self.copyBid(bid)
            copyB.insertParentBid(bid)
            copyB.setNumberPredecessor(bid.getNumberPredecessor())
            bidPrice = self.getBidPrice(copyB)
            self.completeNewBidInformation(copyB, bidPrice, fileResult)
            marketZoneDemand, forecast = self.calculateMovedBidForecast(currentPeriod, radius, bid, copyB, orientation, fileResult)
            self.registerLog(fileResult, 'newBids:' + ', '.join(staged_bids_tmp))
            # If the bid that is being moved is close to any new bid, then we share their forecast.
            for newBidId in staged_bids_tmp:
                newBid = (staged_bids[newBidId])['Object']
                if (self.areNeighborhoodBids(radius, copyB, newBid, fileResult)):
                    forecast = (staged_bids[newBidId])['Forecast']
                    (staged_bids[newBidId])['Forecast'] = forecast * 0.3
                    if copyB.getId() in staged_bids:
                        (staged_bids[copyB.getId()])['Forecast'] = (staged_bids[copyB.getId()])['Forecast'] + (forecast * 0.7)
                    else:
                        staged_bids[copyB.getId()] = {'Object': copyB, 'Action': Bid.ACTIVE, 'MarketShare': marketZoneDemand, 'Forecast': forecast *0.7 }

            # None of the new bid is a neighborhood bids
            if copyB.getId() not in staged_bids:
                staged_bids[copyB.getId()] = {'Object': copyB, 'Action': Bid.ACTIVE, 'MarketShare': marketZoneDemand, 'Forecast': forecast }
        
        # Inactive the bid being moved.
        staged_bids[bid.getId()] = {'Object': bid, 'Action': Bid.INACTIVE, 'MarketShare' : {}, 'Forecast': 0 }
        # print the results
        for bidId in staged_bids:
            forecast = (staged_bids[bidId])['Forecast']
            action = (staged_bids[bidId])['Action']
            self.registerLog(fileResult,"BidId:" + bidId + "Forecast:" + str(forecast) + "Action:" + str(action) )
        self.registerLog(fileResult, 'Ending moveBid:' + str(len(staged_bids))) 
    
    ''' 
    returns the available capacity for a specic resource.
    '''
    def getAvailableCapacity(self, resourceId):
        if (resourceId in self._used_variables['resources']):
            return ((self._used_variables['resources']).get(resourceId)).get('Capacity')
        return 0
        
    def summariesUsedCapacity(self, currentPeriod, fileResult):
        '''
        returns how much capacity is used.
        '''
        total_quantity = 0
        usedCapacity = {}
        for bidId in self._list_vars['Bids']:
            # Verifies if the bid has usage or not
            if bidId in self._list_vars['Bids_Usage'].keys():
                bidData = (self._list_vars['Bids_Usage'])[bidId]
                if currentPeriod in bidData:
                    periodData = bidData[currentPeriod]
                    if bidId in periodData:
                        bid = (self._list_vars['Bids']).get(bidId)
                        total_quantity = periodData[bidId]
                        if (total_quantity > 0):
                            resourceConsumption = self.calculateBidUnitaryResourceRequirements(bid, fileResult)
                            for resource in resourceConsumption:
                                usedCapacity.setdefault(resource, 0)
                                usedCapacity[resource] += ( resourceConsumption[resource] * total_quantity ) 
                                #self.registerLog(fileResult, 'Bid resource capacity:' + bid.__str__() + 'Total Quantity:' + str(total_quantity) )

        # For logging purpose.        
        for resource in usedCapacity:
            self.registerLog(fileResult, 'Resource: ' + str(resource) + ' UsedCapacity:' + str(usedCapacity[resource]) ) 
                    
        return usedCapacity
    
    def canAdoptStrongPosition(self, currentPeriod, fileResult):
        '''
        If the capacity used is low because their is not other competitors 
        then use a string position ( as a monopoly)
        '''
        
        self.registerLog(fileResult, 'Starting canAdoptStrongPosition - Id:' + self.getProviderId())
        adopt = False
        resourceUsedCapacity = self.summariesUsedCapacity(currentPeriod, fileResult)
        for resource in resourceUsedCapacity:
            if resource in self._used_variables['resources']:
                availableCapacity = ((self._used_variables['resources']).get(resource)).get('Capacity')
                self.registerLog(fileResult, 'canAdoptStrongPosition' + str(adopt) + ' Available capacity:' + str(availableCapacity) + ' resourceUsedCapacity[resource]' + str(resourceUsedCapacity[resource]) )
                if (resourceUsedCapacity[resource] >= availableCapacity * self._used_variables['monopolistPosition'] ): 
                    adopt = True
                    break
        self.registerLog(fileResult, 'Ending canAdoptStrongPosition' + str(adopt) )
        return adopt

    def movingAverage(self, progression):
        '''
        Calculates the moving average from a progression of bids. Tested: Ok
        '''
        alpha = 0.6
        if (len(progression) > 1):
            dictio = progression.pop()
            St = dictio.get('delta_profit')
            while (len(progression) > 0):
                dictio = progression.pop()
                St = (dictio.get('delta_profit') * (alpha)) + (( 1 - alpha)* St)
            return St
        else:
            if len(progression) == 1:
                dictio = progression.pop()
                St = dictio.get('delta_profit')
                return St
            return 0

    '''
    Calculate deltas for every offer. For the last element delta profit is 0 - Tested Ok.
    '''
    def calculateDeltaProfitProgression(self, progression):
        if len(progression) > 1:        
            i = 0
            while (i < (len(progression) - 1)):
                (progression[i])['delta_profit'] = ( (progression[i]).get('profit') - (progression[i + 1]).get('profit'))
                i = i + 1
        else:
            if len (progression) == 1:
                (progression[0])['delta_profit'] = (progression[0]).get('profit') 
        

    def continueDirectionImprovingProfits(self, currentPeriod, bid, fileResult):
        ''' 
        This function determine if the bid is following a path of increasing profits
        The way that it does is comparing the profits with their parents. Tested Ok.
        '''
        val_return = False
        progression = []
        nbr_ancestors = 0
        self.registerLog(fileResult, 'continueDirectionImprovingProfits' + bid.getId()) 
        if (bid._parent == None):
            result_progression = copy.copy(progression)
            val_return =  True
        else:
            bidParent = bid
            while ((bidParent != None) and (nbr_ancestors <= self._used_variables['numAncestors'])):
                # Verifies whether the bid has been active for more than one period.
                self.registerLog(fileResult, 'Parent BidId:' + bidParent.getId() + 'Creation Period:' + str(bidParent.getCreationPeriod()) + 'market share period:'+ str(currentPeriod - nbr_ancestors)) 
                # The equal is when the bid should have quanitities.
                if (bidParent.getCreationPeriod() > currentPeriod - (nbr_ancestors + 1)):
                    bidParent = bidParent._parent
                if bidParent != None:
                    bidDemandTmp, marketShare = self.getDBBidMarketShare(bidParent.getId(), currentPeriod - (nbr_ancestors + 1) , 1, fileResult )
                    profits = marketShare * bidParent.getUnitaryProfit()
                    progression.append({'bid' :bidParent, 'profit' : profits, 'delta_profit' : 0 })
                    nbr_ancestors = nbr_ancestors + 1
                
            # Calculate deltas for every offer.
            # For the last element delta profit is 0
            self.calculateDeltaProfitProgression(progression)
            
            result_progression = copy.copy(progression)
            estimated_profit = self.movingAverage(progression)
            self.registerLog(fileResult,  'bidId:' + bid.getId() + 'Data:' + str(progression) + ' estimated profits:' +  str(estimated_profit))
            if ( estimated_profit >= 0 ):
                val_return = True
            else:
                val_return = False
        self.registerLog(fileResult, 'Ending continueDirectionImprovingProfits' + str(val_return)) 
        return val_return, result_progression    
        
    def sortByLastMarketShare(self, currentPeriod, fileResult):
        '''
        Sort bids by market share. Tested Ok.
        '''
        self.registerLog(fileResult, 'Starting sortByLastMarketShare' + str(currentPeriod))
        dict_result = {}
        for bidId in self._list_vars['Bids']:
            bidDemandTmp, marketShare = self.getDBBidMarketShare(bidId,  currentPeriod - 1, 1, fileResult)
            dict_result[bidId] = marketShare
            
        dict_result_sorted_by_value = OrderedDict(sorted(dict_result.items(), 
                              key=lambda x: x[1], 
                              reverse=True))        
        self.registerLog(fileResult, 'Ending sortByLastMarketShare' + str(len(dict_result_sorted_by_value))) 
        return dict_result_sorted_by_value

    def countByStatus(self, staged_bids):
        count = {}
        count[Bid.ACTIVE] = 0
        count[Bid.INACTIVE] = 0
        for bidId in staged_bids:
            action = (staged_bids[bidId])['Action']
            if (action == Bid.ACTIVE):
                count[Bid.ACTIVE] = count[Bid.ACTIVE] + 1
            if (action == Bid.INACTIVE):
                count[Bid.INACTIVE] = count[Bid.INACTIVE] + 1
        
        return count

    def moveBetterProfits(self, currentPeriod, radius, staged_bids, fileResult):
        '''
        Determine the new offer based on current position, in this case
        these bids have no competitors.
        '''
        self.registerLog(fileResult, 'Starting obtainBetterProfits Nbr staged_bids:' + str(self.countByStatus(staged_bids)) )
        sortedActiveBids = self.sortByLastMarketShare(currentPeriod, fileResult)
            
        for bidId in sortedActiveBids:
            if bidId not in staged_bids:
                bid = (self._list_vars['Bids'])[bidId]
                moveDirections= []
                can_continue, progression = self.continueDirectionImprovingProfits(currentPeriod, bid, fileResult)
                if can_continue == True:
                    moveDirections.append(self.improveBidForProfits(self._service, fileResult, 1))
                else:
                    self.registerLog(fileResult, 'it cannot continue direction of improvement:' + str(len(progression)))
                    towards = -1
                    if (len(progression) >= 2):
                        direction = self.calculateProgressionDirection(progression, towards, fileResult)
                        moveDirections.append(direction)
                    else:
                        moveDirections.append(self.improveBidForProfits(self._service, fileResult, -1))
                marketShare = 0 # With this value we inactivate the current bid.
                self.moveBid(currentPeriod, radius, bid, moveDirections, marketShare, staged_bids, Provider.PROFIT_ORIENTED, fileResult)
        self.registerLog(fileResult, 'Finish obtainBetterProfits Nbr staged_bids:' + str(self.countByStatus(staged_bids)) )
    
    def moveForMarketShare(self, currentPeriod, radius, staged_bids, fileResult):
        '''
        Determine the new offer based on current position, in this case
        these bids have competitors and we want to improve the market share.
        '''
        self.registerLog(fileResult, 'Starting moveForMarketShare: ' + str(self._list_vars['strId']))
        sortedActiveBids = self.sortByLastMarketShare(currentPeriod, fileResult)
        for bidId in sortedActiveBids:
            if bidId not in staged_bids:
                bid = (self._list_vars['Bids'])[bidId]
                moveDirections = self.evaluateDirectionalDerivate(currentPeriod, radius, bid, fileResult)
                bidDemand, marketShare = self.getDBBidMarketShare( bid.getId(), currentPeriod-1, self._used_variables['numPeriodsMarketShare'], fileResult) 
                self.moveBid(currentPeriod, radius, bid, moveDirections, marketShare, staged_bids, Provider.MARKET_SHARE_ORIENTED, fileResult)
        self.registerLog(fileResult, 'Finish moveForMarketShare Nbr staged_bids:' + str(len(staged_bids)))

    def exploreMarket(self, currentPeriod, radius, staged_bids, fileResult):
        '''
        This method creates bids to explore the quality-price space that has been not studied yet.
            The procedure followed is to put bids with greater quality than the greatest quality actually offered 
            and to maintain the lowest quality and decrease prices. 
        This procedure is perfomed every time that the probability is found to be within the adaptation factor. 
        '''
        self.registerLog(fileResult, 'Starting exploreMarket Nbr staged_bids:' + str(self.countByStatus(staged_bids)) )
        self.lock.acquire()
        try:        
            adapt_factor = self._used_variables['adaptationFactor']
            value = self._list_vars['Random'].uniform(0,1)
            self.registerLog(fileResult, 'exploreMarket adapt_factor:' + str(adapt_factor)+ ' prob value:' + str(value) )
            if (value <= adapt_factor):        
                minBid = self.calculateBidMinimumQuality()
                minCurBid = self.getBidMinimumQuality()        
                self.calculateNewBidMinimumQuality(currentPeriod, radius, minCurBid, minBid, staged_bids, fileResult)

                maxBid = self.calculateBidMaximumQuality()
                maxCurBid = self.getBidMaximumQuality()
                self.calculateNewBidMaximumQuality(currentPeriod, radius, maxCurBid, maxBid, staged_bids, fileResult)
        finally:
            self.lock.release()
        self.registerLog(fileResult, 'Finish exploreMarket Nbr staged_bids:' + str(self.countByStatus(staged_bids)) )

                 
    def exec_algorithm(self):
        '''
        This method checks if the service provider is able to place an 
        offer in the marketplace, i.e. if the offering period is open.
        If this is the case, it will place the offer at the best position
        possible.
        '''
        if (self._list_vars['State'] == AgentServerHandler.BID_PERMITED):
            fileResult = open(self._list_vars['strId'] + '.log',"a")
            self.registerLog(fileResult, 'executing algorithm ####### ProviderId:' + str(self.getProviderId()) + ' - Period: ' +  str(self.getCurrentPeriod()) )            
            currentPeriod = self.getCurrentPeriod()
            period = self.getDBMaxPeriod()            
            self.registerLog(fileResult, 'Period in the Agent:' + str(currentPeriod) + ' - Period in the database: ' + str(period))
            
            radius = foundation.agent_properties.own_neighbor_radius
            logger.info('Bidding for agent %s in the period %s', self.getProviderId(), str(currentPeriod))
            logger.debug('Number of bids: %s for provider: %s', len(self._list_vars['Bids']), self.getProviderId())
            
            staged_bids = {}
            if (len(self._list_vars['Bids']) == 0):
                marketPosition = self._used_variables['marketPosition']
                initialNumberBids = self._used_variables['initialNumberBids']
                staged_bids = self.initializeBids(marketPosition, initialNumberBids, fileResult) 
            else:
                # By assumption providers at this point have the bid usage updated.
                self.replaceDominatedBids(currentPeriod, radius, staged_bids, fileResult) 
                if (self.canAdoptStrongPosition(currentPeriod, fileResult)):
                    self.moveBetterProfits(currentPeriod, radius, staged_bids, fileResult)
                else:
                    self.moveForMarketShare(currentPeriod, radius, staged_bids, fileResult)
                # Creates other bids in sectors not explored
                self.exploreMarket(currentPeriod, radius, staged_bids, fileResult)
            
            self.eliminateNeighborhoodBid(staged_bids, fileResult)
            self.registerLog(fileResult, 'The Final Number of Staged offers is:' + str(len(staged_bids)) ) 
            self.sendBids(staged_bids, fileResult) #Pending the status of the bid.
            self.purgeBids(staged_bids, fileResult)
            self.registerLog(fileResult, 'Ending executing algorithm ####### ProviderId:' + str(self.getProviderId()) + ' - Period: ' +  str(self.getCurrentPeriod()) )
            fileResult.close()
        self._list_vars['State'] = AgentServerHandler.IDLE
            
            
    def send_capacity(self):
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
            message.setParameter("Quantity",str(resourceNode['Capacity']))
            messageResult = self.sendMessageMarket(message)
            if messageResult.isMessageStatusOk():
                logger.info("Capacity tranmitted sucessfully")
            else:
                raise ProviderException('Capacity not received')
        logger.debug("Ends send capacity")
    
    def initialize(self):
        ''' 
        This method is run for Edge providers
        '''
        pass
    
    '''
    The run method is responsible for activate the socket to send 
    the offer to the marketplace. Then, close down the sockets
    to the marketplace and the simulation environment (demand server).
    '''
    def run(self):
        period = self.start_agent()
        self._list_vars['Current_Period'] = period
        logger.debug('Current period for agent %s is :%s', self._list_vars['strId'], str(self._list_vars['Current_Period']))
        self.initialize()
        try:
            if (self._used_variables['debug'] == True):
                fileResult = open(str(self._list_vars['strId']) + '.log',"w")
                fileResult.write("Starting provider\n") 
                fileResult.close()
    
            # Send the capacity
            self.send_capacity()
            while (self._list_vars['State'] != AgentServerHandler.TERMINATE):
                if self._list_vars['State'] == AgentServerHandler.BID_PERMITED:
                    self.exec_algorithm()
                time.sleep(1)
                logger.debug('Awake')
                #time.sleep(0.1)
            logger.debug('Shuting down the agent %s', self._list_vars['strId'])
        except ProviderException as e:
            logger.error(e.message)
        except Exception as e:
            logger.error(e.message)
        finally:
            # Close the sockets
            fileResult.close()
            self.stop_agent()
            self._db.close()
            return        
        
        
# End of Provider class
