from __future__ import division
from foundation.Message import Message
from foundation.Bid import Bid
from foundation.Agent import Agent
from foundation.FoundationException import FoundationException
from foundation.Agent import AgentServerHandler
from foundation.DecisionVariable import DecisionVariable
from ProviderAgentException import ProviderException
from collections import OrderedDict
import foundation.agent_properties
import copy
import logging
import math
import operator
import time
import uuid
import MySQLdb


logger = logging.getLogger('provider_application')


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


    def __init__(self, strID, Id, providerType, serviceId, providerSeed, marketPosition, 
                 adaptationFactor, monopolistPosition, debug, resources, 
                 numberOffers, numAccumPeriods, numAncestors, startFromPeriod):
        try:
            logger.info('Initializing the provider:' + strID + 'Id:' + str(Id) 
                  + 'Service Id:' + serviceId
                  + 'seed:' + str(providerSeed)
                      + ' market position:' + str(marketPosition)
                  + ' monopolist position:' + str(monopolistPosition)
                  + 'debug:' + str(debug) )
            super(Provider, self).__init__(strID, Id, providerType, serviceId, providerSeed) 
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
        except FoundationException as e:
            raise ProviderException(e.__str__())
    
    '''
    Get the Id     
    '''
    def getProviderId(self):
        return self._list_vars['strId']
    
    '''
    Get the Service Id offering the provider
    '''
    def getServiceId(self):
        return (self._service).getId()
    
    '''
    Get the Current Period
    '''
    def getCurrentPeriod(self):
        return self._list_vars['Current_Period']
    
    '''
    Get the Number of Ancestor to have into account.
    '''
    def getNumAncestors(self):
        return self._used_variables['numAncestors']
    
    def registerLog(self, fileResult, message):
        print 'Debug:' + str(self._used_variables['debug'] )
        if (self._used_variables['debug'] == True):
            fileResult.write(message + '\n')
    
    ''' 
    Get the bids related to a bid. ( those that are in the neigborhood)
    '''    
    def getRelatedBids(self, bid, currentPeriod, numPeriods):
        ret_relatedBids = {}
        for bidId in self._list_vars['Related_Bids']:
            bidCompetitor = (self._list_vars['Related_Bids'])[bidId]
            if (bidCompetitor.getCreationPeriod() >= (currentPeriod - numPeriods)):
                if (self.areNeighborhoodBids(bid, bidCompetitor)):
                    ret_relatedBids[bidId] = bidCompetitor
        return ret_relatedBids
    

    def calculateIntervalsPrice(self, market_position, min_value, max_value):
        '''
        Compute the price interval where the offering will be placed.
        According to the market_position signal received by the simulation
        environment (demand server), the provider's offering will compete
        in quality (higher price expected) or price (lower quality expected).
        '''
        logger.debug('Ending calculateIntervals - parameters' + str(market_position) \
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
        logger.debug('Ending calculateIntervals - outputs' + \
                str(min_val_adj) + ':' + str(max_val_adj))
        return min_val_adj, max_val_adj

    def calculateIntervalsQuality(self, market_position, min_value, max_value, optimum):
        '''
        Compute the quality interval. The market_position signal varies 
        from zero to one uniformally distributed. Signals closer to one
        offer higher quality levels, while signals closer to zero offer
        lower prices.
        '''
        logger.debug('Ending calculateIntervals - parameters' + str(market_position) \
                 + ':' + str(min_value) + ':' + str(max_value))
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
            
        logger.debug('Ending calculateIntervals - outputs' + \
                str(min_val_adj) + ':' + str(max_val_adj))
        return min_val_adj, max_val_adj

    def calculateBidUnitaryCost(self, bid):
        '''
        Calculates the bid unitary cost as a function of their decision variables
        '''    
        logger.debug('Starting - calculateBidUnitaryCost')
        totalUnitaryCost = 0
        totalPercentage = 0
        resources = self._used_variables['resources']
        for decisionVariable in (self._service)._decision_variables:
            minValue = ((self._service)._decision_variables[decisionVariable]).getMinValue()
            maxValue = ((self._service)._decision_variables[decisionVariable]).getMaxValue()
            resourceId = ((self._service)._decision_variables[decisionVariable]).getResource() 
            if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                    value = float(bid.getDecisionVariable(decisionVariable))
                    if ((self._service)._decision_variables[decisionVariable].getOptimizationObjective() == DecisionVariable.OPT_MAXIMIZE):
                            percentage = (value - minValue) / minValue
                    else:
                        percentage = (maxValue - value) / maxValue
                    totalPercentage = totalPercentage + percentage
                    if resourceId in resources:
                        unitaryCost = float((resources[resourceId])['Cost'])
                        totalUnitaryCost = totalUnitaryCost + (unitaryCost * (1+totalPercentage) )
        logger.debug('End - calculateBidUnitaryCost:' + str(totalUnitaryCost))
        return totalUnitaryCost
    
    def calculateBidResources(self, bid):
        '''
        Calculates the bid resource consumption as a function of their decision variables
        '''    
        logger.debug('Starting - calculateBidResources')
        totalPercentage = 0
        resources = self._used_variables['resources']
        res_resources = {}
        for decisionVariable in (self._service)._decision_variables:
            minValue = ((self._service)._decision_variables[decisionVariable]).getMinValue()
            maxValue = ((self._service)._decision_variables[decisionVariable]).getMaxValue()
            resourceId = ((self._service)._decision_variables[decisionVariable]).getResource() 
            if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                    value = float(bid.getDecisionVariable(decisionVariable))
                    if ((self._service)._decision_variables[decisionVariable].getOptimizationObjective() == DecisionVariable.OPT_MAXIMIZE):
                        percentage = (value - minValue) / minValue
                    else:
                        percentage = (maxValue - value) / maxValue
                    totalPercentage = totalPercentage + percentage
                    if resourceId in resources:
                        if (resourceId in res_resources.keys()):
                            res_resources[resourceId] = res_resources[resourceId] + ( 1 + totalPercentage ) 
                        else: 
                            res_resources[resourceId] = (1 + totalPercentage ) 
        logger.debug('End - calculateBidResources:')
        return res_resources
        

    def calculateBidUnitaryResourceRequirements(self, bid):
        '''
        Calculates the resource requirement in order to execute the 
        service provided by the bid.
        '''    
        logger.debug('Starting - calculateBidUnitaryResourceRequirements')
        resourceConsumption = {}
        resources = self._used_variables['resources']
        for decisionVariable in (self._service)._decision_variables:
            minValue = ((self._service)._decision_variables[decisionVariable]).getMinValue()
            maxValue = ((self._service)._decision_variables[decisionVariable]).getMaxValue()
            resourceId = ((self._service)._decision_variables[decisionVariable]).getResource() 
            if ((self._service)._decision_variables[decisionVariable].getModeling() 
                == DecisionVariable.MODEL_QUALITY):
                value = float(bid.getDecisionVariable(decisionVariable))
            if ((self._service)._decision_variables[decisionVariable].getOptimizationObjective() \
                == DecisionVariable.OPT_MAXIMIZE):
                percentage = (value - minValue) / minValue
            else:
                percentage = (maxValue - value) / maxValue
            
            if resourceId in resources:
                resourceConsumption.setdefault(resourceId, 1) 
                resourceConsumption[resourceId] += percentage
        logger.debug('End - calculateBidUnitaryResourceRequirements:' 
                    + str(resourceConsumption) + '\n')
        return resourceConsumption  


    def initializeBids(self, market_position, k):
        '''
        Method to initialize offers. It receives a signal from the 
        simulation environment (demand server) with its position 
        in the market. The argument position serve to understand 
        if the provider at the beginning is oriented towards low 
        price (0) or high quality (1). 
        '''
        logger.debug('Starting - initial bid generation')
        output = {}
        #initialize the k points
        for i in range(0,k):
            output[i] = {}
        for decisionVariable in (self._service)._decision_variables:
            if ((self._service)._decision_variables[decisionVariable].getModeling() 
                == DecisionVariable.MODEL_PRICE):
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
            if ((self._service)._decision_variables[decisionVariable].getModeling() 
                == DecisionVariable.MODEL_QUALITY):
                if ((self._service)._decision_variables[decisionVariable].getOptimizationObjective() \
                    == DecisionVariable.OPT_MAXIMIZE):
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
        return self.createInitialBids(k, output)
    

    def createInitialBids(self,k, output):
        '''
        Create the inital bids in the market for this provider.
        '''    
        logger.debug('Starting - Create Initial Bids')
        #Creates the offerings with the information in the dictionary
        staged_bids = {}
        for i in range(0,k):
            bid = Bid()
            uuidId = uuid.uuid1()    # make a UUID based on the host ID and current time
            idStr = str(uuidId)
            bid.setValues(idStr,self._list_vars['strId'], (self._service).getId())
            for decisionVariable in (self._service)._decision_variables:
                bid.setDecisionVariable(decisionVariable, (output[i])[decisionVariable])
                if (((self._service)._decision_variables[decisionVariable]).getModeling() 
                    == DecisionVariable.MODEL_PRICE):
                    priceBid = (output[i])[decisionVariable]
            
            # Only creates bids that can produce profits
            unitaryBidCost = self.calculateBidUnitaryCost(bid)
            bid.setUnitaryCost(unitaryBidCost)
            if priceBid >= unitaryBidCost:
                staged_bids[bid.getId()] = {'Object': bid, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 0}
        logger.debug('Ending - createInitialBids')
        return staged_bids
    
                
    def sendBids(self, staged_bids, fileResult):
        '''
        With sendBids method, provider sends offers to the Marketplace
        '''
        logger.debug('Starting - send bids - number to send:' + str(len(staged_bids)))
        
        self.registerLog(fileResult, 'Initializing sendBids')
        for bidId in staged_bids:
            bid = (staged_bids[bidId])['Object']
            action = (staged_bids[bidId])['Action']
            bid.setStatus(action)
            self.registerLog(fileResult, 'bid:' + bid.__str__())
            message = bid.to_message()
            messageResult = self._channelMarketPlace.sendMessage(message)
            if messageResult.isMessageStatusOk():
                pass
            else:
                logger.error('Bid not received! Communication failed')
                raise ProviderException('Bid not received! Communication failed')
        self.registerLog(fileResult, 'Ending sendBids')
        logger.debug('Ending - send bids')
    
    def purgeBids(self, staged_bids, fileResult):
        '''
        If there is any bid that has not been read by the marketplace, 
        this method will remove it from the buffer. Therefore, in the next
        round, only new bids will be on the buffer.
        
        Precondition: Only bids with changes go in the staged_bids dictionary
        '''
        self.registerLog(fileResult, 'Starting purgeBids')
    
        for bidId in staged_bids:
            bid = (staged_bids[bidId])['Object']
            action = (staged_bids[bidId])['Action']
            if (action == Bid.INACTIVE):
                bid = (self._list_vars['Bids']).pop(bidId, None)
                if (bid != None):
                    (self._list_vars['Inactive_Bids'])[bidId] = bid
            if (action == Bid.ACTIVE):
                (self._list_vars['Bids'])[bidId] = bid
        
        # Register in the log active bids.
        for bidId in self._list_vars['Bids']:
            self.registerLog(fileResult, 'bid:' + bidId)
        self.registerLog(fileResult, 'Ending purgeBids')
    
        logger.debug('Ending - purge Bids - Number of bids:' + str(len(self._list_vars['Bids'])))

    def areNeighborhoodBids(self, bid1, bid2):
        val_return = False        
        distance = self.distance(bid1,bid2)
        radius = foundation.agent_properties.neighbor_radius * len(bid1._decision_variables)
        if distance <= radius:
            val_return = True            
        return val_return
        

    def isANonValueAddedBid(self, newBid, staged_bids):
        '''
        Determine whether the newbid is a non value added with respecto to
        bids in the staged_bids dictionary.
        '''    
        val_return = False
        for bidId in staged_bids:
            bid = (staged_bids[bidId])['Object']
            action = (staged_bids[bidId])['Action']
            if (action == Bid.ACTIVE):
                distance = self.distance(newBid,bid)
                radius = foundation.agent_properties.neighbor_radius \
                        * len(newBid._decision_variables)
                if distance <= radius:
                    val_return = True
                    break            
                dominated = self.isDominated(newBid, bid)
                if (dominated == True):
                    val_return = True
                    break
        logger.debug('Ending - isANeighborBid - output:' + str(val_return))
        return val_return
    
    def eliminateNeighborhoodBid(self, staged_bids, fileResult):
        '''
        Eliminates those bids that are close of each other.
        '''    
        # Compare the distance againts bids that will not be changed
        to_delete = {}
        logger.debug('Starting - killNeighborhoodBid - output:' + str(len(staged_bids)))
        for bidId in staged_bids:
            bid = (staged_bids[bidId])['Object']
            action = (staged_bids[bidId])['Action']
            if (action == Bid.ACTIVE):
                for bidIdComp in self._list_vars['Bids']:
                    if bidIdComp not in staged_bids:
                        bidComp = (self._list_vars['Bids'])[bidIdComp]
                        distance = self.distance(bid,bidComp)
                        fileResult.write('New Bid:' + bidId + 'Actual Bid:' + bidIdComp + 'Distance:' + str(distance))
                        radius = foundation.agent_properties.neighbor_radius \
                                * len(bid._decision_variables)
                        if distance <= radius:
                            to_delete[bidId] = bid
                            break
        for bidId in to_delete:
            del staged_bids[bidId]
        logger.debug('Ending - killNeighborhoodBid - output:' + str(len(staged_bids)))
        
    def sumarizeBidUsage(self):
        '''
        This method gets a list of usage of offers. It returns the offers
        that has been bought by the consumers at certain period, and 
        the offers that hasn't been bought.
        '''
        output = {}
        for bidId in self._list_vars['Bids']:
            output[bidId] = {}
            # Verifies if the bid has usage or not
            if bidId in self._list_vars['Bids_Usage'].keys():
                bidData = (self._list_vars['Bids_Usage'])[bidId]
                for period in bidData:
                    periodData = bidData[period]
                    for bidIdUsage in periodData:
                        output[bidId].setdefault(bidIdUsage, 0)
                        (output[bidId])[bidIdUsage] += periodData[bidIdUsage]
            else:
                # This bid was never used.
                output[bidId] = {bidId : 0}
        logger.debug('Ending Summarize Bid Usage agent' + self._list_vars['strId'] + '\n' )
        return output
    
    def isDominated(self, bid, competitorBid):    
        '''
        This method establishes if a bid is dominated by a competitor bid or not. 
        '''
        strict_dom_dimensions = 0
        non_strict_dom_dimensions = 0
        for decisionVariable in bid._decision_variables:
            ownValue = bid.getDecisionVariable(decisionVariable)
            compValue = competitorBid.getDecisionVariable(decisionVariable)
            if (((self._service)._decision_variables[decisionVariable]).getOptimizationObjective() 
                == DecisionVariable.OPT_MINIMIZE):
                ownValue = ownValue * -1
                compValue = compValue * -1
            
            if (ownValue <= compValue):
                non_strict_dom_dimensions += 1
                if (ownValue < compValue):
                    strict_dom_dimensions += 1
        # We said that the provider bid is dominated if forall decision variables
        # the value is less of equal to the corresponding value, and at least in 
        # one decision variable is strictly less.
        if ((non_strict_dom_dimensions == len(bid._decision_variables)) and
            ( strict_dom_dimensions > 0)):
            return True
        else:
            return False

    '''
    Copy the bid and returns a new bid with the same decision variables.
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

    def getDBBidMarketShare(self, bidId,  current_period, num_periods):
        db1 = MySQLdb.connect("localhost","root","password","Network_Simulation" )
        cursor = db1.cursor() 
        sql = 'select a.period, a.quantity from \
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
            bidDemand[int(row[0])] = float(row[1])
            totQuantity = totQuantity + float(row[1])
        db1.close()
        return bidDemand, totQuantity
    
    ''' 
    Get the Ancestor Market Share from a parent Bid, results are put in bidDemand and totQuantity
    '''    
    def getDBBidAncestorsMarketShare(self, bid, currentPeriod, numPeriods):
        bidDemand = {}
        totQuantity = 0
        nbrAncestors = 0
        if (bid._parent != None):
            bidParent = bid._parent
            while ((bidParent != None) and (nbrAncestors <= numPeriods )):
                if bidParent != None:
                    period = currentPeriod - nbrAncestors
                    bidDemandTmp, totQuantityTmp = self.getDBBidMarketShare(bidParent.getId(), period, 1 )
                    bidDemand[period] = totQuantityTmp
                    totQuantity = totQuantity + totQuantityTmp

                # Verifies whether the bid has been active for more than one period.
                if (bidParent.getCreationPeriod() >= period):
                    bidParent = bidParent._parent
                nbrAncestors = nbrAncestors + 1
        return bidDemand, totQuantity
    
    def getDBMarketShareZone(self, bid, related_bids, current_period, num_periods):
        db1 = MySQLdb.connect("localhost","root","password","Network_Simulation" )
        cursor = db1.cursor() 
        sql = 'select a.period, a.quantity from \
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

        for providerBidId in related_bids:
            cursor.execute(sql, (providerBidId, current_period - num_periods, current_period))
            results2 = cursor.fetchall()
            bidDemand2 = {}
            for row in results2:
                bidDemand2[int(row[0])] = float(row[1])
                totQuantity = totQuantity + float(row[1])
            # Insert the demand for the bid only when the sql found data.
            if (len(bidDemand2) > 0):
                marketZoneDemand[providerBidId] = bidDemand2
        db1.close()
        return marketZoneDemand, totQuantity
    
    def replaceDominatedBids(self, staged_bids):
        '''
        In case a offer hasn't been sucessful in the market, i.e. has low
        market share, the method replaceDominateBids updates the offering
        information to mimic the offer with higher market share.
        '''
        logger.debug('Initializating replace dominance bids ')
        for bid in self._list_vars['Bids']:
            if bid in self._list_vars['Related_Bids']:
                related_bids = (self._list_vars['Related_Bids'])[bid]
                numRelatedBids = len(related_bids)
                for providerBid in related_bids:
                    if (self.isDominated(bid, providerBid)):
                        # Puts inactive the bid and copy the information for the competitor's bid 
                        staged_bids[bid.BidId()] = {'Object': bid, 'Action': Bid.INACTIVE, 'MarketShare' : {}, 'Forecast' : 0 }
                        newBid = self.copyBid(providerBid)
                        unitaryBidCost = self.calculateBidUnitaryCost(newBid)
                        newBid.setUnitaryCost(unitaryBidCost)
                        priceBid = newBid.getDecisionVariable((self._service).getPriceDecisionVariable())                        
                        if priceBid >= unitaryBidCost:
                            marketZoneDemand, totQuantity = self.getDBMarketShareZone(bid, related_bids, self.getCurrentPeriod() -1 , 1)
                            staged_bids[newBid.getId()] = {'Object': newBid, 'Action': Bid.ACTIVE, 'MarketShare' : marketZoneDemand, 'Forecast' : totQuantity / numRelatedBids}
                        break
        logger.debug('Ending replace dominance bids ')
    
    def getBidById(self, bidId):
        '''
        The method getBidId gets the offering by identification number.
        '''
        logger.debug('Getting own bid:' + bidId)
        return (self._list_vars['Bids'])[bidId]
    
    def getCompetitorBid(self, competitorBidId):
        '''
        This method gets the competitors (other service providers) offers
        in the marketplace.
        '''
        if competitorBidId in self._list_vars['Related_Bids']:
            return (self._list_vars['Related_Bids'])[competitorBidId]
        else:
            message = Message('')
            message.setMethod(Message.GET_BID)
            message.setParameter("Bid", competitorBidId)
            messageResult = self._channelMarketPlace.sendMessage(message)
            if messageResult.isMessageStatusOk():
                bid = Bid()
                bid.setFromMessage(self._service, messageResult)
                # We put the bid as a related bid.
                (self._list_vars['Related_Bids'])[bid.getId()] = bid
                return bid
            else:
                logger.error('Bid not received! Communication failed')
                raise ProviderException('Bid not received! Communication failed')
            logger.debug('Getting competitors bid:' + competitorBidId)
        return (self._list_vars['Related_Bids'])[competitorBidId]

    def generateDirectionBetweenTwoBids(self, bid1, bid2, fileResult):
        '''
        This method establishes the direction (the positive or negative) 
        value in the decision variable cartesian space to goes from bid 1 to bid 2.
        '''
        self.registerLog(fileResult, 'generateDirectionBetweenTwoBids:' + bid1.__str__())
        self.registerLog(fileResult, 'generateDirectionBetweenTwoBids:' + bid2.__str__())
        output = {}
        for decisionVariable in (self._service)._decision_variables:
            min_value = 1.0
            max_value = 1.0 + (self._used_variables['marketPosition'] / 3)
            step = ( bid2.getDecisionVariable(decisionVariable) - bid1.getDecisionVariable(decisionVariable) ) 
            step = step * self._list_vars['Random'].uniform(min_value, max_value)
            
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
    
    def improveBidForProfits(self, fileResult, reverse):
        ''' 
        The bid does not have any competitor registered, so in case that has zero users
        we take a direction of increasing decision variable objectives for profits.
        '''
        self.registerLog(fileResult, 'improveBidForProfits - Reverse:' + str(reverse)) 
        output = {}
        for decisionVariable in (self._service)._decision_variables:
            min_value = (self._service.getDecisionVariable(decisionVariable)).getMinValue()
            max_value = (self._service.getDecisionVariable(decisionVariable)).getMaxValue()
            maximum_step = (max_value - min_value) * self._used_variables['adaptationFactor']
            # Since we want to determine the step size, we have to do invert the
            # meaning of market position. 
            market_position = 1 - self._used_variables['marketPosition']
            # Gets the objetive to persuit.
            if ((self._service)._decision_variables[decisionVariable].getOptimizationObjective() == DecisionVariable.OPT_MAXIMIZE):
                optimum = 1 # Maximize
            else:
                optimum = 2 # Minimize
            
            # Gets the modeling objetive of the decision variable
            if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                min_val_adj, max_val_adj = self.calculateIntervalsPrice(market_position, 0, maximum_step)
                direction = 1 * reverse
                step = self._list_vars['Random'].uniform(min_val_adj, max_val_adj) * reverse
            else:
                min_val_adj, max_val_adj = self.calculateIntervalsQuality(market_position, 0, maximum_step, optimum)
                if (optimum == 1):
                    direction = -1 * reverse
                    step = self._list_vars['Random'].uniform(min_val_adj, max_val_adj) * -1 * reverse
                else:
                    step = ( self._list_vars['Random'].uniform(min_val_adj, max_val_adj) ) * reverse
                    direction = 1 * reverse         
            output[decisionVariable] = {'Direction' : direction, 'Step': step}
        self.registerLog(fileResult, 'improveBidForProfits:' + str(output)) 
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
        return output

    def avoidCompetitorBid(self, mybidId, otherBidId, fileResult):
        '''
        Generate direction to go into the opposite direction of a 
        worse offer than the current one.
        '''
        logger.debug("Initializing avoidCompetitorBid")
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
        logger.debug("Ending avoidCompetitorBid")
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

    def generateOwnDirection(self, mybidId, ownMarketShare, fileResult):
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
            can_continue, progression = self.continueDirectionImprovingProfits(myBid, fileResult)
            if (can_continue == True):
            # If it does not have competitors and it has users, we just continue in the same point
            # We understand this situtaion as a niche provider.
                output = self.maintainBidForCompetence(fileResult)
            else:
                output = self.improveBidForProfits(fileResult, -1)
    
        self.registerLog(fileResult, 'generateOwnDirection:' + str(output)) 
        return output

    def evaluateDirectionalDerivate(self, bid, summarizedUsage, fileResult):
        '''
        This method evaluates if there is a direction to replace the 
        offer in order to improve the number of customers.
        If the current offer has no competitors, the method looks to 
        improve its market share by increasing its decision variables.
        '''
        logger.debug("Initializing evaluateDirectionalDerivate")
        competitiveBids = summarizedUsage[bid.getId()]
        ownMarketShare = competitiveBids[bid.getId()]
        
        # The tuple that corresponds to the offer must be eliminated. 
        competitiveBids.pop(bid.getId(), None)
        competitiveBidsSorted = sorted(competitiveBids.iteritems(), key=operator.itemgetter(1), reverse=True)
        hasCompetitorBids = False
        numSplits = 0
        direction = []
        self.registerLog(fileResult, 'evaluateDirectionalDerivate:' + bid.getId()) 
        for competitiveBid in competitiveBidsSorted:
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
            direction.append(self.generateOwnDirection(bid.getId(), ownMarketShare, fileResult))
            
        logger.debug("Ending evaluateDirectionalDerivate")
        return direction

    def distance(self, bid1, bid2):
        '''
        Method to calculate the distance from a bid to another.
        '''
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
        return math.sqrt(distance)

    def getPeriodMarketShare(self, bid, fileResult, requested_period):
        '''
        This Method calculates the market share for an offerin the requested period.
        '''
        marketShare = 0
        bidId = bid.getId()
        if bidId in self._list_vars['Bids_Usage'].keys():
            bidData = (self._list_vars['Bids_Usage'])[bidId]
            for period in bidData:
                if (period == requested_period):
                    periodData = bidData[period]
                    if bidId in periodData:
                        marketShare += periodData[bidId]
        
        self.registerLog(fileResult, 'getPeriodMarketShare:' + bid.getId() +  'Period: ' + str(requested_period) + ' Value:' + str(marketShare)) 
        return marketShare


    def getMarketShare(self, bid, fileResult, last_period):
        '''
        This Method calculates the market share for an offer, the market share
        is defined as the quantity of the bid in the last periods defined by 
        numPeriodsMarketShare
        '''
        marketShare = 0
        period_init = ( last_period - 
                self._used_variables['numPeriodsMarketShare'] )
        bidId = bid.getId()
        if bidId in self._list_vars['Bids_Usage'].keys():
            bidData = (self._list_vars['Bids_Usage'])[bidId]
            for period in bidData:
                if (( period >= period_init) 
                  and ( period <= last_period) ):
                    periodData = bidData[period]
                    if bidId in periodData:
                        marketShare += periodData[bidId]
        
        self.registerLog(fileResult, 'getMarketShare:' + bid.getId() + ' Value:' + str(marketShare)) 
        return marketShare

    def moveBidOnDirection(self, bid, directionMove ):
        # Create a new bid
        newBid = Bid()
        uuidId = uuid.uuid1()    # make a UUID based on the host ID and current time
        idStr = str(uuidId)
        newBid.setValues(idStr, bid.getProvider(), bid.getService())
        send = False
        for decisionVariable in directionMove:
            direction = (directionMove[decisionVariable])['Direction']
            step = (directionMove[decisionVariable])['Step']
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
            if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                bidPrice = new_value
            else:
                new_value = max(min_value, new_value)
                new_value = min(max_value, new_value)
            newBid.setDecisionVariable(decisionVariable, new_value)
        return newBid, bidPrice, send
    
    '''
    Completes the costs of the bid, profit and period
    '''    
    def completeNewBidInformation(self, bid, bidPrice ):
        unitaryBidCost = self.calculateBidUnitaryCost(bid)
        bid.setUnitaryCost(unitaryBidCost)
        bid.setUnitaryProfit(bidPrice - unitaryBidCost)
        bid.setCreationPeriod(self._list_vars['Current_Period'])
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
    Calculates the forecast for a bid according with the orientation for the bid.
    '''    
    def calculateMovedBidForecast(self, bid, newBid, orientation):
        marketZoneDemand = {}        
        forecast = 0
        alpha = 0.6
        if (orientation == Provider.PROFIT_ORIENTED):
            bidDemand, bidQuantity = self.getDBBidMarketShare(bid.getId(), self.getCurrentPeriod() -1, 1)        
            bidDemand2, bidQuantity2 = self.getDBBidAncestorsMarketShare( bid, self.getCurrentPeriod() -1, self.getNumAncestors() )
            bidDemand3, bidQuantity3 = self.consolidateDemand(bidDemand, bidQuantity, bidDemand2, bidQuantity2)
            keys = bidDemand3.keys()
            keys.sort()
            for period in keys:
                forecast = (bidDemand3[period] * (alpha)) + (( 1 - alpha)* forecast)
            marketZoneDemand[bid.getId()] = bidDemand3
                
        if (orientation == Provider.MARKET_SHARE_ORIENTED):
            competitorBids = self.getRelatedBids(bid, self.getCurrentPeriod()-1, 0)
            marketZoneDemand, totQuantity = self.getDBMarketShareZone(bid, competitorBids , self.getCurrentPeriod() -1 , 1)
            forecast = totQuantity / (len(competitorBids) + 1)
        return marketZoneDemand, forecast

    def moveBid(self, bid, moveDirections, marketShare, staged_bids, orientation, fileResult):
        '''
        If there is a better position to improve the current offer,
        this method will move the offer to the better position in unit
        steps.
        '''
        logger.debug("Initiating moveBid")
        send = False
        newBidStage = False
        forecast = 0
        self.registerLog(fileResult, 'moveBid:' + bid.getId()) 
        for directionMove in moveDirections:
            newBid, bidPrice, send = self.moveBidOnDirection( bid, directionMove )            
            if (send == True):
                self.registerLog(fileResult, 'Bid moved:' + bid.getId() + 'Bid created:' + newBid.getId())
                unitaryBidCost = self.completeNewBidInformation(newBid, bidPrice)
                if bidPrice >= unitaryBidCost:
                    if (self.isANonValueAddedBid( newBid, staged_bids) == False):
                        newBid.insertParentBid(bid)
                        self.registerLog(fileResult, 'New bid created - ready to be send' +  newBid.__str__())
                        marketZoneDemand, forecast = self.calculateMovedBidForecast(bid, newBid, orientation)
                        staged_bids[newBid.getId()] = {'Object': newBid, 'Action': Bid.ACTIVE, 'MarketShare': marketZoneDemand, 'Forecast': marketShare }
                        newBidStage = True
            else:
                self.registerLog(fileResult, 'Bid not moved:' + bid.getId()) 
            
        if (newBidStage == True):            
            # As we move the bid, the originator bid must be inactive
            if (marketShare == 0):
                staged_bids[bid.getId()] = {'Object': bid, 'Action': Bid.INACTIVE, 'MarketShare' : {}, 'Forecast': 0 }
        logger.debug("Ending moveBid")
    
    ''' 
    returns the available capacity for a specic resource.
    '''
    def getAvailableCapacity(self, resourceId):
        if (resourceId in self._used_variables['resources']):
            return ((self._used_variables['resources']).get(resourceId)).get('Capacity')
        return 0
        
    
    def summariesUsedCapacity(self, fileResult):
        '''
        returns how much capacity is used.
        '''
        current_period = self._list_vars['Current_Period']
        total_quantity = 0
        usedCapacity = {}
        for bidId in self._list_vars['Bids']:
            # Verifies if the bid has usage or not
            if bidId in self._list_vars['Bids_Usage'].keys():
                bidData = (self._list_vars['Bids_Usage'])[bidId]
                if current_period in bidData:
                    periodData = bidData[current_period]
                    if bidId in periodData:
                        bid = (self._list_vars['Bids']).get(bidId)
                        total_quantity = periodData[bidId]
                        if (total_quantity > 0):
                            resourceConsumption = self.calculateBidUnitaryResourceRequirements(bid)
                            for resource in resourceConsumption:
                                usedCapacity.setdefault(resource, 0)
                                usedCapacity[resource] += ( resourceConsumption[resource] * total_quantity ) 
                                self.registerLog(fileResult, 'Bid resource capacity:' + bid.__str__() 
                                         + 'Total Quantity:' + str(total_quantity) )
                                self.registerLog(fileResult, ' UsedCapacity:' + str(usedCapacity[resource]) ) 
                    
        logger.debug('Ending Summarize Bid Usage agent' + self._list_vars['strId'] )
        return usedCapacity
    
    def canAdoptStrongPosition(self, fileResult):
        '''
        If the capacity used is low because their is not other competitors 
        then use a string position ( as a monopoly)
        '''
        adopt = False
        resourceUsedCapacity = self.summariesUsedCapacity(fileResult)
        for resource in resourceUsedCapacity:
            if resource in self._used_variables['resources']:
                availableCapacity = ((self._used_variables['resources']).get(resource)).get('Capacity')
                self.registerLog(fileResult, 'canAdoptStrongPosition' + str(adopt) + 'Available capacity:' + str(availableCapacity) + 'resourceUsedCapacity[resource]' + str(resourceUsedCapacity[resource]) )
                if (resourceUsedCapacity[resource] >= availableCapacity * self._used_variables['monopolistPosition'] ): 
                    adopt = True
                    break
        self.registerLog(fileResult, 'canAdoptStrongPosition' + str(adopt) )
        return adopt

    def movingAverage(self, progression):
        '''
        Calculates the moving average from a progression of bids.
        '''
        alpha = 0.6
        if (len(progression) > 0):
            dictio = progression.pop()
            St = dictio.get('delta_profit')
            while (len(progression) > 0):
                dictio = progression.pop()
                St = (dictio.get('delta_profit') * (alpha)) + (( 1 - alpha)* St)
            return St
        else:
            return 0

    def continueDirectionImprovingProfits(self, bid, fileResult):
        ''' 
        This function determine if the bid is following a path of increasing profits
        The way that it does is comparing the profits with their parents.
        '''
        val_return = False
        progression = []
        last_period = self._list_vars['Current_Period']
        nbr_ancestors = 0
        self.registerLog(fileResult, 'continueDirectionImprovingProfits' + bid.__str__()) 
        if (bid._parent == None):
            self.registerLog(fileResult, 'continueDirectionImprovingProfits' + 'No parent')
            result_progression = copy.copy(progression)
            val_return =  True
        else:
            bidParent = bid
            while ((bidParent != None) and (nbr_ancestors <= self._used_variables['numAncestors'])):
                # Verifies whether the bid has been active for more than one period.
                self.registerLog(fileResult, 'Parent BidId:' + bidParent.getId() + 'Creation Period:' + str(bidParent.getCreationPeriod()) + 'market share period:'+ str(last_period - nbr_ancestors)) 
                if (bidParent.getCreationPeriod() >= last_period - nbr_ancestors):
                    bidParent = bidParent._parent
                if bidParent != None:
                    marketShare = self.getPeriodMarketShare(bidParent, fileResult, last_period - nbr_ancestors )
                    profits = marketShare * bidParent.getUnitaryProfit()
                    progression.append({'bid' :bidParent, 'profit' : profits, 'delta_profit' : 0 })
                    nbr_ancestors = nbr_ancestors + 1
                
            # Calculate deltas for every offer.
            # For the last element delta profit is 0
            i = 0
            while (i < (len(progression) - 1)):
                (progression[i])['delta_profit'] = ( (progression[i]).get('profit') - 
                                     (progression[i + 1]).get('profit') 
                                    )
                i = i + 1
            
            self.registerLog(fileResult, 'bidId:' + bid.getId() + 'Data:' + str(progression))
            result_progression = copy.copy(progression)
            estimated_profit = self.movingAverage(progression)
            self.registerLog(fileResult, 'estimated profits:' + str(estimated_profit))
            if ( estimated_profit >= 0 ):
                val_return = True
            else:
                val_return = False
        return val_return, result_progression    
    
    def sortByLastMarketShare(self, fileResult):
        '''
        Sort bids by market share.
        '''
        dict_result = {}
        last_period = self._list_vars['Current_Period']
        for bidId in self._list_vars['Bids']:
            bid = (self._list_vars['Bids'])[bidId]
            marketShare = self.getPeriodMarketShare(bid, fileResult, last_period)
            dict_result[bidId] = marketShare
        dict_result_sorted_by_value = OrderedDict(sorted(dict_result.items(), 
                              key=lambda x: x[1], 
                              reverse=True))
        return dict_result_sorted_by_value

    def moveBetterProfits(self, summarizedUsage, staged_bids, fileResult):
        '''
        Determine the new offer based on current position, in this case
        these bids have no competitors.
        '''
        logger.debug('Starting moveBetterProfits')
        sortedActiveBids = self.sortByLastMarketShare(fileResult)
        for bidId in sortedActiveBids:
            if bidId not in staged_bids:
                bid = (self._list_vars['Bids'])[bidId]
                moveDirections= []
                can_continue, progression = self.continueDirectionImprovingProfits(bid, fileResult)
                if can_continue == True:
                    moveDirections.append(self.improveBidForProfits(fileResult, 1))
                else:
                    self.registerLog(fileResult, 'it cannot continue direction of improvement:' + str(len(progression)))
                    towards = -1
                    if (len(progression) >= 2):
                        direction = self.calculateProgressionDirection(progression, towards, fileResult)
                        moveDirections.append(direction)
                    else:
                        moveDirections.append(self.improveBidForProfits(fileResult, -1))
                marketShare = 0 # With this value we inactivate the current bid.
                self.moveBid(bid, moveDirections, marketShare, staged_bids, Provider.PROFIT_ORIENTED, fileResult)
        logger.debug('Finish obtainBetterProfits')
    
    def moveForMarketShare(self, summarizedUsage, staged_bids, fileResult):
        '''
        Determine the new offer based on current position, in this case
        these bids have competitors and we want to improve the market share.
        '''
        logger.debug('Starting moveForMarketShare: %s', self._list_vars['strId'])
        sortedActiveBids = self.sortByLastMarketShare(fileResult)
        for bidId in sortedActiveBids:
            if bidId not in staged_bids:
                bid = (self._list_vars['Bids'])[bidId]
                moveDirections = self.evaluateDirectionalDerivate(bid, summarizedUsage, fileResult) 
                marketShare = self.getMarketShare(bid, fileResult, self._list_vars['Current_Period']) 
                self.moveBid(bid, moveDirections, marketShare, staged_bids, Provider.MARKET_SHARE_ORIENTED, fileResult)
        logger.debug('Finish of moving bids for provider: %s', self._list_vars['strId'])
                 
    def exec_algorithm(self):
        '''
        This method checks if the service provider is able to place an 
        offer in the marketplace, i.e. if the offering period is open.
        If this is the case, it will place the offer at the best position
        possible.
        '''
        logger.debug('The state for agent %s is %s', 
                self._list_vars['strId'], str(self._list_vars['State']))
        fileResult = open(self._list_vars['strId'] + '.log',"a")
        self.registerLog(fileResult, 'executing algorithm - Period: '+ str(self._list_vars['Current_Period']) )
        if (self._list_vars['State'] == AgentServerHandler.BID_PERMITED):
            logger.info('Biding for agent %s in the period %s', 
                   str(self._list_vars['strId']), 
                   str(self._list_vars['Current_Period']))
    
            logger.debug('Number of bids: %s for provider: %s', \
                len(self._list_vars['Bids']), self._list_vars['strId'])
            staged_bids = {}
            if (len(self._list_vars['Bids']) == 0):
                marketPosition = self._used_variables['marketPosition']
                initialNumberBids = self._used_variables['initialNumberBids']
                staged_bids = self.initializeBids(marketPosition, 
                                  initialNumberBids) 
            else:
                # By assumption providers at this point have the bid usage updated.
                summarizedUsage = self.sumarizeBidUsage() 
                self.replaceDominatedBids(staged_bids) 
                if (self.canAdoptStrongPosition(fileResult)):
                    self.moveBetterProfits(summarizedUsage, staged_bids, fileResult)
                else:
                    self.moveForMarketShare(summarizedUsage, staged_bids, fileResult)
            
            self.eliminateNeighborhoodBid(staged_bids, fileResult)
            self.registerLog(fileResult, 'The Final Number of Staged offers is:' + str(len(staged_bids)) ) 
            self.sendBids(staged_bids, fileResult) #Pending the status of the bid.
            self.purgeBids(staged_bids, fileResult)
            fileResult.close()
        self._list_vars['State'] = AgentServerHandler.IDLE
            
        logger.info('Ending exec_algorithm %s is %s', 
                self._list_vars['strId'], str(self._list_vars['State']))

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
            messageResult = self._channelMarketPlace.sendMessage(message)
            if messageResult.isMessageStatusOk():
                logger.info("Capacity tranmitted sucessfully")
            else:
                print 'Here I am'
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
        print 'start agent' + str(self._list_vars['State'])
        self.start_listening()
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
                    print 'Go out from exec_algorithm, state:' + str(self._list_vars['State'])
                time.sleep(0.1)
            logger.debug('Shuting down the agent %s', self._list_vars['strId'])
        except ProviderException as e:
            logger.error(e.message)
        except Exception as e:
            logger.error(e.message)
        finally:
            # Close the sockets
            self._server.stop()
            if (self._list_vars['Type'] == Agent.PROVIDER_ISP):
                self._channelMarketPlaceBuy.close()
                self._channelMarketPlace.close()
            else:
                self._channelMarketPlace.close()
            self._channelClockServer.close()
            return        
        
        
# End of Provider class
