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



logger = logging.getLogger('provider_public')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('provider_public.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

class ProviderPublic(Provider):

    def __init__(self, strID, Id, serviceId, accessProviderSeed, marketPosition, 
                 adaptationFactor, monopolistPosition, debug, resources, 
                 numberOffers, numAccumPeriods, numAncestors, startFromPeriod, 
                 sellingAddress, buyingAddress, capacityControl, purchase_service):
        try:
            
            logger.debug('Starting Init Agent:%s - Public Provider', strID)
            agent_type = AgentType(AgentType.PROVIDER_BACKHAUL)
            super(ProviderPublic, self).__init__(strID, Id, serviceId, accessProviderSeed, marketPosition, adaptationFactor, monopolistPosition, debug, resources, numberOffers, numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl, purchase_service, agent_type)
            logger.debug('Ending Init Agent: %s - Type:%s Public Provider Created', self._list_vars['strId'], str((self._list_vars['Type']).getType()))
        except FoundationException as e:
            raise ProviderException(e.__str__())

    def calculateUnitaryResourceRequirements(self, bidQuality, fileResult):
        '''
        Calculates the resource requirement in order to execute the 
        service provided by a bid. with quality attributes speified in bidQuality
        The parameter bidQuality has the requirements in quality for a bid that will be created
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

                value = float(bidQuality[decisionVariable])
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
        self.registerLog(fileResult, 'Ending calculateUnitaryResourceRequirements'+ str(resourceConsumption))
        return resourceConsumption

    def calculateUnitaryCost(self, resourceConsumption, fileResult):
        '''
        Calculates the bid unitary cost as a function of their decision variables
        '''
        self.registerLog(fileResult, 'Starting calculateUnitaryCost')
        totalUnitaryCost = 0

        resources = self._used_variables['resources']
        for resource in resourceConsumption:
            if resource in resources:
                unitaryCost = float((resources[resource])['Cost'])
                totalUnitaryCost = totalUnitaryCost + (unitaryCost * resourceConsumption[resource] )
        self.registerLog(fileResult, 'Ending calculateUnitaryCost' + str(totalUnitaryCost))
        return totalUnitaryCost

    def initializeBidParameters(self, radius, fileResult):
        logger.debug('Starting - initializeBidParameters')
        output = {}
        #initialize the bids separeated every radious distance
        for decisionVariable in (self._service)._decision_variables:
            logger.debug('initializeBidParameters - decision Variable %s', str(decisionVariable))
            if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                if ((self._service)._decision_variables[decisionVariable].getOptimizationObjective() == DecisionVariable.OPT_MAXIMIZE):
                    optimum = 1 # Maximize
                else:
                    optimum = 2 # Minimize

                min_val = (self._service)._decision_variables[decisionVariable].getMinValue()
                max_val = (self._service)._decision_variables[decisionVariable].getMaxValue()
                logger.debug('miValue %s - maxValue%s', str(min_val), str(max_val))
                if (optimum == 1):
                    k = 0
                    val = min_val
                    output[k] = {}
                    while val < max_val:
                        (output[k])[decisionVariable] = val
                        k = k+1 
                        val = min_val + (k*radius*(max_val-min_val))
                        if val < max_val:
                            output[k] = {}
                        logger.debug('Value %s ', str(val))
                else:
                    k = 0
                    output[k] = {}
                    val = max_val
                    while val > min_val:
                        (output[k])[decisionVariable] = val
                        k = k + 1
                        val = max_val - (k*radius*(max_val-min_val))
                        if val > min_val:
                            output[k] = {}
                        logger.debug('Value %s ', str(val))
        logger.debug('initializeBidParameters - Quality parameters have been specified')
        # The following establishes the price for each bid.
        for decisionVariable in (self._service)._decision_variables:
            if ((self._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                for k in output:
                    resourceConsumption = self.calculateUnitaryResourceRequirements(output[k], fileResult)
                    totalCost = self.calculateUnitaryCost(resourceConsumption, fileResult)
                    (output[k])[decisionVariable] = totalCost
        logger.debug('Ending - initializeBidParameters NumOutput:' + str(len(output)) )
        return output

    def initializeBids(self, radius, fileResult):
        '''
        Method to initialize offers. It receives a signal from the 
        simulation environment (demand server) with its position 
        in the market. The argument position serves to understand 
        if the provider at the beginning is oriented towards low 
        price (0) or high quality (1). Providers innovators 
        can compite with offers with high quality and low price. 
        '''
        logger.debug('Starting - initializeBids')
        output = self.initializeBidParameters(radius, fileResult)
        k = len(output)
        staged_bids = self.createInitialBids(k, output, fileResult)
        logger.debug('Ending initializeBids - NumStaged' + str(len(staged_bids)))
        return staged_bids

    def updateClosestBidForecast(self, currentPeriod, bid, staged_bids, forecast, fileResult):
        ''' 
        This method updates the forecast of the bid closest to the given bid.
        '''
        finalDistance = -1 # infinity
        bidIdToIncrease = ''
        for bidId in staged_bids:
            if (staged_bids[bidId])['Action'] == Bid.ACTIVE:
                bidToCompare = (staged_bids[bidId])['Object']
                distance = self.distance(bid,bidToCompare, fileResult)
                if finalDistance == -1:
                    finalDistance = distance
                    bidIdToIncrease = bidId        
                if (finalDistance >= 0) and (finalDistance > distance):
                    finalDistance = distance
                    bidIdToIncrease = bidId
        if (finalDistance >= 0):
            (staged_bids[bidIdToIncrease])['Forecast'] = (staged_bids[bidIdToIncrease])['Forecast'] + forecast
            self.registerLog(fileResult, 'Ending updateClosestBidForecast - Period:' + str(currentPeriod) + ' The closest Bid is:' + bidIdToIncrease + 'Forecast:' + str(forecast) )


    '''
    Return True if the distance between both bids is less tha radius - tested:OK
    '''
    def areNeighborhoodBids(self, radius, bid1, bid2, fileResult):
        val_return = False        
        distance = self.distance(bid1,bid2, fileResult)
        if distance <= radius:
            val_return = True            
        #self.registerLog(fileResult, 'Ending - areNeighborhoodBids - Radius' + str(radius) + ' distance:' + str(distance))
        return val_return

    def maintainBids(self, currentPeriod, radius, serviceOwn, staged_bids, fileResult):
        self.registerLog(fileResult, 'Starting maintainBids:' + str(len(staged_bids)) )
        sortedActiveBids = self.sortByLastMarketShare(currentPeriod, fileResult)
        for bidId in sortedActiveBids:
            if bidId not in staged_bids:                
                bid = (self._list_vars['Bids'])[bidId]
                newBid = self.copyBid(bid)
                bidPrice = self.getBidPrice(newBid)
                unitaryBidCost = self.completeNewBidInformation(newBid, bidPrice, fileResult)
                if bidPrice >= unitaryBidCost:
                    if (self.isANonValueAddedBid( radius, newBid, staged_bids, fileResult) == False):
                        newBid.insertParentBid(bid)
                        marketZoneDemand, forecast = self.calculateMovedBidForecast(currentPeriod, radius, bid, newBid, Provider.MARKET_SHARE_ORIENTED, fileResult)
                        staged_bids[newBid.getId()] = {'Object': newBid, 'Action': Bid.ACTIVE, 'MarketShare': marketZoneDemand, 'Forecast': forecast }
                    else:
                        # increase the forecast of the closest bid. 
                        self.updateClosestBidForecast(currentPeriod, newBid, staged_bids, forecast, fileResult) 
                
                # inactive current bid.
                staged_bids[bid.getId()] = {'Object': bid, 'Action': Bid.INACTIVE, 'MarketShare': {}, 'Forecast': 0 }
        self.registerLog(fileResult, 'Ending maintainBids:' + str(len(staged_bids)) )

    def exec_algorithm(self):
        '''
        This method checks if the service provider is able to place an 
        offer in the marketplace, i.e. if the offering period is open.
        If this is the case, it will place the offer at the best position
        possible.
        '''
        try:
            logger.debug('The state for agent %s is %s', 
                            self._list_vars['strId'], str(self._list_vars['State']))
            fileResult = open(self._list_vars['strId'] + '.log',"a")
            self.registerLog(fileResult, 'executing algorithm - Period: ' + str(self._list_vars['Current_Period']) )
            if (self._list_vars['State'] == AgentServerHandler.BID_PERMITED):
                logger.debug('Number of bids: %s for provider: %s', len(self._list_vars['Bids']), self._list_vars['strId'])
                currentPeriod = self.getCurrentPeriod()
                adaptationFactor = self.getAdaptationFactor()
                marketPosition = self.getMarketPosition()
                serviceOwn = self._service
                radius = foundation.agent_properties.own_neighbor_radius

                staged_bids = {}
                if (len(self._list_vars['Bids']) == 0):
                    staged_bids = self.initializeBids(radius, fileResult)
                else:
                    # By assumption providers at this point have the bid usage updated.
                    self.maintainBids(self, currentPeriod, radius, serviceOwn, staged_bids, fileResult)
                    self.eliminateNeighborhoodBid(staged_bids, fileResult)
                    self.registerLog(fileResult, 'The Final Number of Staged offers is:' + str(len(staged_bids)) ) 
                self.sendBids(staged_bids, fileResult) #Pending the status of the bid.
                self.purgeBids(staged_bids, fileResult)
        except ProviderException as e:
            self.registerLog(fileResult, e.message)
        except Exception as e:
            self.registerLog(fileResult, e.message)    
        fileResult.close()
        self._list_vars['State'] = AgentServerHandler.IDLE
        logger.info('Ending exec_algorithm %s - CurrentPeriod: %s', self._list_vars['strId'], str(self._list_vars['Current_Period']) )