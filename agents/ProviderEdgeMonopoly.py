# -*- coding: utf-8 -*-
"""
Created on Wed May 25 13:16:15 2016

@author: luis
"""

from foundation.FoundationException import FoundationException
import uuid
import logging
from foundation.AgentServer import AgentServerHandler
from foundation.AgentType import AgentType
from foundation.Agent import Agent
from foundation.Message import Message
from foundation.DecisionVariable import DecisionVariable
import foundation.agent_properties 
from ProviderAgentException import ProviderException
from Provider import Provider
from ProviderEdge import ProviderEdge
from foundation.Bid import Bid
import MySQLdb
import xml.dom.minidom
import math
import threading


logger = logging.getLogger('provider_edge')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('provider_edge.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


''' 
The Edge Monopoly Provider class defines methods to be used by the access provider
agent to purchase offers that correspond to channels on the marketplace. 
    
Initizalize the agent, get the disutility function, and execute the buying
algorithm. 
'''
class ProviderEdgeMonopoly(ProviderEdge):
    
    def __init__(self,  strID, Id, serviceId, accessProviderSeed, marketPosition, 
				 adaptationFactor, monopolistPosition, debug, resources, 
				 numberOffers, numAccumPeriods, numAncestors, startFromPeriod, 
                 sellingAddress, buyingAddress, capacityControl, purchase_service):
        try:
            super(ProviderEdgeMonopoly, self).__init__(strID, Id, serviceId, accessProviderSeed, marketPosition, adaptationFactor, monopolistPosition, debug, resources, numberOffers, numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl, purchase_service)
            logger.debug('Agent: %s - Edge Provider Monopoly Created', self._list_vars['strId'])
        except FoundationException as e:
            raise ProviderException(e.__str__())

    def getNumberServices(self):
        numServices = 0
        self.lock.acquire()
        try:
            numServices = len(self._services)
        finally:
            self.lock.release()
        return numServices
            
    
    def getService(self, serviceId):
        service = None
        self.lock.acquire()
        try:
            if serviceId in self._services.keys():
                service = self._services[serviceId]
            else:
                service = None
        finally:
           self.lock.release()
        return service
    
    def purchaseBasedOnProvidersBids(self, currentPeriod, serviceId, bid, quantity, fileResult):        
        ''' 
        The Purchase method assigns all the parameters and access provider ID
        to the message to be send to the Marketplace.
    	
        In the end, the function sends the message to the marketplace
        and checks if it was succesfully received. 
        
        Test: implemented.
        '''
        self.registerLog(fileResult, 'PurchaseBasedOnProvidersBids - Period:' + str(self.getCurrentPeriod()) + ':bidId:' + bid.getId() + ':qty_to_purchase:' + str(quantity))
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
        messageResult = self.sendMessageMarketBuy(messagePurchase)
        # Check if message was succesfully received by the marketplace
        if messageResult.isMessageStatusOk():
            quantity = float(messageResult.getParameter("Quantity_Purchased"))
            self.registerLog(fileResult,'PurchaseBasedOnProvidersBids - Period: %s ' + str(currentPeriod) + ' - Purchase BidId:' + bid.getId() + ' purchase qty:' + str(quantity) )
            return quantity
        else:
            self.registerLog(fileResult,' Period: %s ' + str(currentPeriod) + ' - Purchase not received! Communication failed' )
            raise ProviderException('Purchase not received! Communication failed')

    def purchaseBidsBasedOnProvidersBids(self, currentPeriod, staged_bids, fileResult):
        '''
        Purchase the bids in the staged_bids dictionary.
        Test: implemented.
        '''
        self.registerLog(fileResult, 'purchaseBidsBasedOnProvidersBids - Period:' + str(self.getCurrentPeriod()) + ' NbrBids:' + str(len(staged_bids)))
        for bidId in staged_bids:
            if (staged_bids[bidId])['Action'] == Bid.ACTIVE:
                bid = (staged_bids[bidId])['Object']
                bidProv = bid.getProviderBid()
                forecast = (staged_bids[bidId])['Forecast']
                quantity = self.purchaseBasedOnProvidersBids(currentPeriod, bidProv.getService(), bidProv, forecast, fileResult)
                ((staged_bids[bidId])['Object']).setCapacity(quantity)


    def moveQuality(self, service, adaptationFactor, marketPosition, direction,  fileResult):
        ''' 
        This creates the direction of the move to quality.
        direction should be 1 or -1, when 1 improve, -1 lower
        Test: implemented.
        '''
        self.registerLog(fileResult, 'moveQuality')
        output = {}
        self.lock.acquire()
        try:
            minStep = 0.0
            for decisionVariable in service._decision_variables:
                min_value = (service.getDecisionVariable(decisionVariable)).getMinValue()
                max_value = (service.getDecisionVariable(decisionVariable)).getMaxValue()
                maximum_step = (max_value - min_value) * adaptationFactor
                # Since we want to determine the step size, we have to do invert the
                # meaning of market position. 
                market_position = 1 - marketPosition
                # Gets the objetive to persuit.
                optimum = service.getDecisionVariableObjetive(decisionVariable)

                # Gets the modeling objetive of the decision variable
                if (service._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                    min_val_adj, max_val_adj = self.calculateIntervalsQuality(market_position, 0, maximum_step, optimum)
                    if (optimum == 1): #Maximize
                        step = self._list_vars['Random'].uniform(min_val_adj, max_val_adj) * direction
                    else:
                        step = ( self._list_vars['Random'].uniform(min_val_adj, max_val_adj) ) * -1 * direction
                    output[decisionVariable] = {'Direction' : direction, 'Step': step}

                    if (minStep == 0.0):
                        minStep = step

                    if minStep > abs(step):
                        minStep = step
                else:
                    output[decisionVariable] = {'Direction' : direction, 'Step': 0}

            self.registerLog(fileResult, 'moveQuality:' + str(output)) 

        finally:
           self.lock.release()
        
        return output
            
    def movePrice(self, service, adaptationFactor, marketPosition, direction, fileResult):
        ''' 
        This creates the direction of the move the price.
        direction should be 1 or -1, when 1 improves, 0 decrease
        Test: implemented.
        '''
        self.registerLog(fileResult, 'movePrice') 
        output = {}
        self.lock.acquire()
        try:
            step = 0
            for decisionVariable in service._decision_variables:
                min_value = (service.getDecisionVariable(decisionVariable)).getMinValue()
                max_value = (service.getDecisionVariable(decisionVariable)).getMaxValue()
                maximum_step = (max_value - min_value) * adaptationFactor
                # Since we want to determine the step size, we have to do invert the
                # meaning of market position. 
                market_position = 1 - marketPosition

                # Gets the modeling objetive of the decision variable
                if (service._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                    min_val_adj, max_val_adj = self.calculateIntervalsPrice(market_position, 0, maximum_step)
                    step = self._list_vars['Random'].uniform(min_val_adj, max_val_adj) * direction
                    output[decisionVariable] = {'Direction' : direction, 'Step': step}
                else:
                    output[decisionVariable] = {'Direction' : direction, 'Step': 0}


            self.registerLog(fileResult, 'movePrice:' + str(output)) 
            
        finally:
           self.lock.release()
        
        return output
         

    def calculateQualityRelativeObjective(self, value, minValue, maxValue, aggregationMode, adaptationFactor):
        ''' 
        This method establishes the target position for quality for a bid based on the 
        quality percentage previously establised by the operator.
        '''
        qualityReq = 0
        self.lock.acquire()
        try:
            if ((aggregationMode == 'M') or (aggregationMode == 'N')): # MAX aggregation
                qualityReq = value 
                if ((maxValue - minValue) == 0 ):
                    qualityReq = maxValue
                else:
                    qualityReq = (qualityReq -minValue) / (maxValue - minValue)

            if ((aggregationMode == 'S') or (aggregationMode == 'X')) : # SUM aggregation or NON aggregation
                # this provider can decide              
                qualityReq = minValue + ( self._list_vars['Random'].uniform(minValue, maxValue) * adaptationFactor) + value 

        finally:
           self.lock.release()

        return qualityReq

    def convertToOwnBid(self, serviceOwn, serviceProvider,  bid, adaptationFactor, fileResult):
        '''
        This function assumes that:
            1. If the aggregation function is maximize or minimize we convservate the same quality in percentage
            2. If the aggregation function is sum, then we assume the minimal quality is added.
        Test: implemented.
        '''
        newBid = Bid()
        uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
        idStr = str(uuidId)
        newBid.setValues(idStr, self.getProviderId(), serviceOwn.getId())
        effectiveMove = True
        for decisionVariable in serviceProvider._decision_variables:
            min_value = (serviceProvider.getDecisionVariable(decisionVariable)).getMinValue()
            max_value = (serviceProvider.getDecisionVariable(decisionVariable)).getMaxValue()
            provOptimum = serviceProvider.getDecisionVariableObjetive(decisionVariable)            

            value = bid.getDecisionVariable(decisionVariable)
            
            if ((max_value - min_value) == 0 ):
                percentage = 1
            else:
                percentage = (value -min_value) / (max_value - min_value)
            
            ownDecisionVariable, aggregationMode = self.getRelatedDecisionVariable(serviceProvider.getId(), serviceOwn.getId(), decisionVariable)
            min_value = (serviceOwn.getDecisionVariable(ownDecisionVariable)).getMinValue()
            max_value = (serviceOwn.getDecisionVariable(ownDecisionVariable)).getMaxValue()            
            ownOptimum = serviceOwn.getDecisionVariableObjetive(ownDecisionVariable)
            
            if (decisionVariable != serviceProvider.getPriceDecisionVariable()):
                newValue = self.calculateQualityRelativeObjective(percentage, min_value, max_value, aggregationMode, adaptationFactor)
                newValueAdj = self.calculateRequiredQuality(newValue, min_value, max_value, value, ownOptimum, aggregationMode)
                newBid.setDecisionVariable(ownDecisionVariable, newValueAdj)
                if (newValueAdj < 0):
                    effectiveMove = False            
        
        # Set the original bid as the provider Bid parent.        
        newBid.setProviderBid(bid)
        if (effectiveMove == True):
            # calculate the cost
            unitaryCost = self.calculateBidUnitaryCost(newBid, fileResult)
            for decisionVariable in serviceOwn._decision_variables:            
                # If the variable is price, it maintains the current level of the decision variable
                if (serviceOwn._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                    newBid.setDecisionVariable(decisionVariable, unitaryCost)        
            return newBid 
        else: 
            return None

    def moveBidOnDirectionEdge(self, bid, service, directionMove ):
        '''
        Create a new bid from bid based on the direction given bu directionMove
        Test: implemented.
        '''
        newBid = Bid()
        uuidId = uuid.uuid1()    # make a UUID based on the host ID and current time
        idStr = str(uuidId)
        newBid.setValues(idStr, bid.getProvider(), bid.getService())
        for decisionVariable in directionMove:
            direction = (directionMove[decisionVariable])['Direction']
            step = (directionMove[decisionVariable])['Step']
            new_value = bid.getDecisionVariable(decisionVariable) + step

            # Make sure that the value is within the variable limits            
            min_value = (service.getDecisionVariable(decisionVariable)).getMinValue()
            max_value = (service.getDecisionVariable(decisionVariable)).getMaxValue()
            new_value = max(min_value, new_value)
            new_value = min(max_value, new_value)
                        
            newBid.setDecisionVariable(decisionVariable, new_value)
        return newBid
    
    def determineProfitForecast(self, currentPeriod, numAncestors, radius, serviceOwn, serviceProvider, adaptationFactor, marketPosition, bid, fileResult):
        '''
        Identifies the direction of the move depending on the profit forecast. 
        The Bid given must be an own bid.
        Test: implemented.
        '''
        bids_related = self.getOwnRelatedBids(bid, radius, currentPeriod - 1 , numAncestors, fileResult)
        i = 0
        progression = []
        while (i < numAncestors):
            profitZone, totProfit, numRelated = self.getDBProfitZone(bid, bids_related, currentPeriod - (i+1), fileResult)
            progression.append({'bid' : None, 'profit' : totProfit, 'delta_profit' : 0 })
            i = i + 1
        self.calculateDeltaProfitProgression(progression)
        profitEstimate = self.movingAverage(progression)
        self.registerLog(fileResult, 'Ending determineProfitForecast estimate:' + str(profitEstimate))
        return profitEstimate

    def isNeighborhoodBidToStaged(self, newBid,  staged_bids, radius, fileResult):
        '''
        Establish whether or not a bid is neigboor of other bid already staged.
        Test: implemented.
        '''    
        # Compare the distance againts bids that will not be changed
        for bidIdComp in staged_bids:
            bidComp = (staged_bids[bidIdComp])['Object']
            if (self.areNeighborhoodBids(radius, newBid, bidComp, fileResult) == True):
                return True
            
        return False


    def includeExploringBid(self, currentPeriod, numAncestors, serviceProvider, adaptationFactor, marketPosition, newBid, oldBid, serviceOwn, radius, staged_bids_resp, staged_bids, fileResult):
        '''
        Include the bid in the bid to be staged whenever there is a positive forecast
        Test: implemented.
        '''
        self.registerLog(fileResult, 'Starting includeExploringBid')
        profForecast = self.determineProfitForecast(currentPeriod, numAncestors, radius, serviceOwn, serviceProvider, adaptationFactor, marketPosition, newBid, fileResult) 
        if (profForecast >= 0):
            if ( (self.isANonValueAddedBid(radius, newBid, staged_bids, fileResult) == False ) and 
                 (self.isANonValueAddedBid(radius, newBid, staged_bids_resp, fileResult) == False ) ):
                self.registerLog(fileResult, 'includeExploringBid method is incluing another bid.')
                decVarPrice = serviceOwn.getPriceDecisionVariable()
                newBid.setProviderBid(oldBid)
                bidPrice = newBid.getDecisionVariable(decVarPrice)
                self.completeNewBidInformation(newBid, bidPrice, fileResult )
                if bidPrice >= newBid.getUnitaryCost():
                    staged_bids_resp[newBid.getId()] = {'Object': newBid, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 0 }
                else:
                    self.registerLog(fileResult, 'bid:' + newBid.getId() + ' not included - negative profit:' + str(bidPrice - newBid.getUnitaryCost()))
        
        
    def execFrontBids(self, currentPeriod, numAncestors, radius, serviceOwn, serviceProvider, adaptationFactor, marketPosition, bidList, staged_bids, explore_staged_bids, fileResult):
        '''
        This type of providers has three options, 
             1. Decrease quality - the aggregated quality is lower than the provider offers.
             2. Increase quality - The aggregated quality is better than the provider offers.
             3. Increase prices and maintain the same quality
        decrease the quality

        Test: implemented.
        ''' 
        self.registerLog(fileResult, 'Starting execFrontBids')
        for bid in bidList:
            # Decrease quality and then calculate a profit.
            self.registerLog(fileResult, 'execFrontBids - decrease quality - Bid' + bid.__str__())
            newBid = self.convertToOwnBid( serviceOwn, serviceProvider,  bid, adaptationFactor, fileResult)
            
            direction = -1
            directionQuality = self.moveQuality(serviceOwn, adaptationFactor, marketPosition, direction, fileResult)
            newBidOwn1 = self.moveBidOnDirectionEdge(newBid, serviceOwn, directionQuality)
            
            direction = 1            
            directionPrice = self.movePrice(serviceOwn, adaptationFactor, marketPosition, direction, fileResult)
            newBidOwn1 = self.moveBidOnDirectionEdge(newBidOwn1, serviceOwn, directionPrice)
            self.registerLog(fileResult, 'newBid:' + newBidOwn1.__str__() )
            if (newBidOwn1 != None):
                self.includeExploringBid(currentPeriod, numAncestors, serviceProvider, adaptationFactor, marketPosition, newBidOwn1, bid, serviceOwn, radius, explore_staged_bids, staged_bids, fileResult)

            # Increase quality and then calculate a profit.
            direction = 1
            self.registerLog(fileResult, 'execFrontBids - increase quality')
            directionQuality = self.moveQuality(serviceOwn, adaptationFactor, marketPosition, direction, fileResult)
            newBidOwn2 = self.moveBidOnDirectionEdge(newBid, serviceOwn, directionQuality)

            direction = 1
            directionPrice = self.movePrice(serviceOwn, adaptationFactor, marketPosition, direction, fileResult)
            newBidOwn2 = self.moveBidOnDirectionEdge(newBidOwn2, serviceOwn, directionPrice)
            self.registerLog(fileResult, 'newBid:' + newBidOwn2.__str__() )
            if (newBidOwn2 != None):
                self.includeExploringBid(currentPeriod, numAncestors, serviceProvider, adaptationFactor, marketPosition, newBidOwn2, bid, serviceOwn, radius, explore_staged_bids, staged_bids, fileResult)

            # Just increase for profit.
            direction = 1
            self.registerLog(fileResult, 'execFrontBids - increase price')
            directionPrice = self.movePrice(serviceOwn, adaptationFactor, marketPosition, direction, fileResult)
            newBidOwn3 = self.moveBidOnDirectionEdge(newBid, serviceOwn, directionPrice)
            self.registerLog(fileResult, 'newBid:' + newBidOwn3.__str__() )
            if (newBidOwn3 != None):
                self.includeExploringBid(currentPeriod, numAncestors, serviceProvider, adaptationFactor, marketPosition, newBidOwn3, bid, serviceOwn, radius, explore_staged_bids, staged_bids, fileResult)
            
                
    def execBidUpdate(self, currentPeriod, numAncestors, radius, serviceOwn, serviceProvider, adaptationFactor, marketPosition, staged_bids, explore_staged_bids, fileResult):
        '''
        Execute the bid update for an specific service that is required for a resource.
        return quantities purchased.
        Test: implemented.
        '''                             
        dic_return = self.AskBackhaulBids(serviceProvider.getId())
        self.registerLog(fileResult, 'Starting execBidUpdate - Period: ' + str(currentPeriod) + 'Number of fronts:' + str(len(dic_return)))
        if (len(dic_return) > 0):
            keys_sorted = sorted(dic_return,reverse=True)
            for front in keys_sorted:
                bidList = dic_return[front]                                                                        
                # Just explore those bids in the first pareto front.                
                self.execFrontBids(currentPeriod, numAncestors, radius, serviceOwn, serviceProvider, adaptationFactor, marketPosition, bidList, staged_bids, explore_staged_bids, fileResult)
                break
        self.registerLog(fileResult, 'Ending execBidUpdate - Nbr staged bids:' + str(len(explore_staged_bids)) )


    def getOwnRelatedBids(self, bid, radius, currentPeriod, numPeriods, fileResult):
        ''' 
        Get those own bids that are in my neighborhood
        Test: implemented.
        '''    
        self.registerLog(fileResult, 'getOwnRelatedBids:' + bid.getId() )
        ret_relatedBids = {}
        self.lock.acquire()
        try:    
            for bidId in self._list_vars['Bids']:
                otherBid = (self._list_vars['Bids'])[bidId]
                # bids recent enough to be taken into account.
                if (otherBid.getCreationPeriod() >= (currentPeriod - numPeriods)):
                    if (self.areNeighborhoodBids(radius, bid, otherBid, fileResult)):
                        ret_relatedBids[bidId] = otherBid        
            self.registerLog(fileResult, 'getOwnRelatedBids:' + str(len(ret_relatedBids)) )
            
        finally:
            self.lock.release()
        
        return ret_relatedBids


    def calculateForecast(self, radius, currentPeriod, numPeriods, initialQtyByBid, staged_bids, fileResult):
        '''
        Calculate the forecast for bids given as paramters in the dictionary staged_bids
        Test: implemented.
        '''
        totForecast = 0        
        for bidId in staged_bids:
            bid = (staged_bids[bidId])['Object']
            related_bids = self.getOwnRelatedBids( bid, radius, currentPeriod - 1, numPeriods, fileResult)
            marketZoneDemand, totQuantity, numRelated = self.getDBMarketShareZone(bid, related_bids, currentPeriod -1, numPeriods, fileResult)
            marketZoneBacklog, totQtyBacklog, numRelatedBacklog = self.getDBMarketShareZone(bid, related_bids, currentPeriod -1, numPeriods, fileResult, Provider.BACKLOG)
            (staged_bids[bidId])['MarketShare'] = marketZoneDemand
            totQtyBacklog = totQtyBacklog * 0.1
            totForecast = totForecast + (totQuantity + totQtyBacklog) / (numRelated + 1)
            (staged_bids[bidId])['Forecast'] = (totQuantity + totQtyBacklog) / (numRelated + 1)
        
        # Apply for cases where the forecast is zero as when the process starts
        if (totForecast == 0): 
            for bidId in staged_bids:
                (staged_bids[bidId])['Forecast'] = initialQtyByBid

    def canAdoptStrongPosition(self, currentPeriod, fileResult):
        val_return = True
        self.lock.acquire()
        try:
            self.registerLog(fileResult, 'Starting canAdoptStrongPosition')
            value = self._list_vars['Random'].uniform(0, 1)
            val_return = True
            if value <= self.getMonopolistPosition():
                val_return = False
            self.registerLog(fileResult, 'Ending canAdoptStrongPosition' + str(val_return))            
            
        finally:
            self.lock.release()
        return val_return

    def updateClosestBidForecast(self, currentPeriod, bid, staged_bids, forecast, fileResult):
        ''' 
        This method updates the forecast of the bid closest to the given bid.
        '''
        finalDistance = -1 # infinity
        bidIdToIncrease = ''
        for bidId in staged_bids:
            if (staged_bids[bidId])['Action'] == Bid.ACTIVE:
                bidToCompare = (staged_bids[bidId])['Object']
                distance = self.distance(bid,bidToCompare)
                if finalDistance == -1:
                    finalDistance = distance
                    bidIdToIncrease = bidId        
                if (finalDistance >= 0) and (finalDistance > distance):
                    finalDistance = distance
                    bidIdToIncrease = bidId
        if (finalDistance >= 0):
            (staged_bids[bidIdToIncrease])['Forecast'] = (staged_bids[bidIdToIncrease])['Forecast'] + forecast
            self.registerLog(fileResult, 'Ending updateClosestBidForecast - Period:' + str(currentPeriod) + ' The closest Bid is:' + bidIdToIncrease + 'Forecast:' + str(forecast) )
        

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

    def updateCurrentBids(self, currentPeriod, radius, serviceOwn, staged_bids, availability, fileResult):
        '''
        Update bids for customers given te previous history.
        '''
        # By assumption providers at this point have the bid usage updated.
        self.registerLog(fileResult, 'Starting updateCurrentBids - Nbr staged Bids:' + str(len(staged_bids)) )        
        self.replaceDominatedBids(currentPeriod, radius, staged_bids, fileResult)
        staged_bids_result = {}
        value = self._list_vars['Random'].uniform(0, 1)
        if (value <= 0.5):
            adoptStrong = self.canAdoptStrongPosition(currentPeriod, fileResult) 
            if (adoptStrong == True):
                self.moveBetterProfits(currentPeriod, radius, staged_bids, fileResult)
            else:
                self.moveForMarketShare(currentPeriod, radius, staged_bids, fileResult)
        else:
            # maintain bids.
            self.maintainBids(currentPeriod, radius, serviceOwn, staged_bids, fileResult)
        
        self.eliminateNeighborhoodBid(staged_bids, fileResult)
        staged_bids_result = self.purchaseBids(currentPeriod, staged_bids, fileResult)
        self.registerLog(fileResult, 'Ending updateCurrentBids -Period:' + str(currentPeriod) + 'bids_staged:' + str(len(staged_bids_result)) )
        return staged_bids_result
    
    def exploreOtherSegments(self, currentPeriod, numAncestors, radius, initialQtyByBid,  serviceOwn, serviceProvider, adaptationFactor, marketPosition, staged_bids, explore_staged_bids, fileResult):    
        self.registerLog(fileResult, 'Starting exploreOtherSegments - bids staged:' + str(len(staged_bids)) )
        self.execBidUpdate(currentPeriod, numAncestors, radius, serviceOwn, serviceProvider, adaptationFactor, marketPosition, staged_bids, explore_staged_bids, fileResult)
        self.calculateForecast(radius, currentPeriod, numAncestors, initialQtyByBid, explore_staged_bids, fileResult)
        self.purchaseBidsBasedOnProvidersBids(currentPeriod, explore_staged_bids, fileResult )
        self.registerLog(fileResult, 'The Final Number of Staged offers is:' + str(len(explore_staged_bids)) )
                
	'''
	The exec_algorithm function finds available offerings and chooses
	the one that fits the access provider needs the best, based on the prior 
	signals received by the simulation environment (demand server).
	'''
    def exec_algorithm(self):
        logger.debug('Starting exec_algorithm Agent: %s - Period %s', 
                    self._list_vars['strId'], str(self._list_vars['Current_Period'])  )
        if (self._list_vars['State'] == AgentServerHandler.BID_PERMITED):
            fileResult = open(self._list_vars['strId'] + '.log',"a")
            self.registerLog(fileResult, 'executing algorithm ####### ProviderId:' + str(self.getProviderId()) + ' - Period: ' +  str(self.getCurrentPeriod()) )
            
             # Sends the request to the market place to find the best offerings             
             # This executes offers for the provider
            
            # we assume here that the server already send the next period and all demand information
            # is registered with the previous period. 
            try:
                currentPeriod = self.getCurrentPeriod()
                adaptationFactor = self.getAdaptationFactor()
                marketPosition = self.getMarketPosition()
                serviceOwn = self._service
                radius = foundation.agent_properties.own_neighbor_radius
                numAncestors = self.getNumAncestors()
                initialQtyByBid = 5.0
                availability = {}            
                staged_bids = {}
                self.restartAvailableCapacity()
                
                # Purchase the bids that are already in place with the forecast given by historical demand
                staged_bids_result = self.updateCurrentBids(currentPeriod, radius, serviceOwn, staged_bids, availability, fileResult)
                self.sendBids(staged_bids_result, fileResult)
                staged_bids = staged_bids_result
    
                # Try to search for other parts of the quality-price spectrum given by the providers' bids.
                for resourceId in self._list_vars['Resource_Service']:
                    services = (self._list_vars['Resource_Service'])[resourceId]
                    for serviceId in services:      
                        serviceProvider = self._services[serviceId]
                        explore_staged_bids = {}
                        self.exploreOtherSegments(currentPeriod, numAncestors, radius, initialQtyByBid,  serviceOwn, serviceProvider, adaptationFactor, marketPosition, staged_bids, explore_staged_bids, fileResult)
                        self.sendBids(explore_staged_bids, fileResult) 
                        # purge the bids.                        
                        self.purgeBids(staged_bids, fileResult)
                        self.purgeBids(explore_staged_bids, fileResult)
                        self.registerLog(fileResult, 'Nbr bids after method purgeBids:' + str(len(self._list_vars['Bids'])) )
            except ProviderException as e:
                self.registerLog(fileResult, e.message)
            except Exception as e:
                self.registerLog(fileResult, e.message)
            
            self.registerLog(fileResult, 'Ending executing algorithm ####### ProviderId:' + str(self.getProviderId()) + ' - Period: ' +  str(self.getCurrentPeriod()) )            
            fileResult.close()
            
        self._list_vars['State'] = AgentServerHandler.IDLE
        logger.debug('Ending exec_algorithm Agent: %s - Period %s', 
                    self._list_vars['strId'], str(self._list_vars['Current_Period'])  )
