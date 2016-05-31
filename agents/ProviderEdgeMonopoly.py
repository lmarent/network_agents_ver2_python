# -*- coding: utf-8 -*-
"""
Created on Wed May 25 13:16:15 2016

@author: luis
"""

from foundation.FoundationException import FoundationException
import uuid
import logging
from foundation.Agent import AgentServerHandler
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
                 sellingAddress, buyingAddress, capacityControl):
        try:
            super(ProviderEdgeMonopoly, self).__init__(strID, Id, serviceId, accessProviderSeed, marketPosition, adaptationFactor, monopolistPosition, debug, resources, numberOffers, numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl)
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
        self._servicesRelat = {}
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

            # Bring the service's decision variables relationships
            sql2 = "select a.id_service_to, a.id_decision_variable_to from simulation_provider b, \
                     simulation_provider_resource c,  simulation_service_relationship a \
                      where b.id = %s and b.service_id = %s and b.id = c.id and b.service_id = a.id_service_from \
                        and c.service_id = a.id_service_to and c.resource_id = %s and a.id_decision_variable_from = %s"
            
            serviceIdOwn = (self._service).getId()        
            for decisionVariable in (self._service)._decision_variables:
                cursor.execute(sql2, (prov_id, serviceIdOwn, iResourceId,decisionVariable))
                results2 = cursor.fetchall()
                ret_tuple = None
                for row in results2:
                    serviceTo = str(row[0])
                    variableTo = str(row[1])
                    ret_tuple = (serviceTo, decisionVariable, variableTo)
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
                        ret_tuple2 = (serviceIdOwn, ret_tuple[2], ret_tuple[1])
                        (self._servicesRelat[ret_tuple[0]]).append(ret_tuple2)
                    else:
                        self._servicesRelat[ret_tuple[0]] = []
                        ret_tuple2 = (serviceIdOwn, ret_tuple[2], ret_tuple[1])
                        (self._servicesRelat[ret_tuple[0]]).append(ret_tuple2)
                    

        self._list_vars['Resource_Service'] = resource_services

                    
        db1.close()


    def getNumberServices(self):
        return len(self._services)
    
    def getService(self, serviceId):
        if serviceId in self._services.keys():
            return self._services[serviceId]
        else:
            return None
    
    ''' 
    The Purchase method assigns all the parameters and access provider ID
    to the message to be send to the Marketplace.
	
    In the end, the function sends the message to the marketplace
    and checks if it was succesfully received. 
    '''
    def purchaseBasedOnProvidersBids(self, currentPeriod, serviceId, bid, quantity, fileResult):        
        self.registerLog(fileResult, 'Period:' + str(self.getCurrentPeriod()) + ':bidId:' + bid.getId() + ':qty_to_purchase:' + str(quantity))
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
            self.registerLog(fileResult,' Period: %s ' + str(currentPeriod) + ' - Purchase BidId:' + bid.getId() + ' purchase qty:' + str(quantity) )
            return quantity
        else:
            self.registerLog(fileResult,' Period: %s ' + str(currentPeriod) + ' - Purchase not received! Communication failed' )
            raise ProviderException('Purchase not received! Communication failed')

    def purchaseBidsBasedOnProvidersBids(self, currentPeriod, staged_bids, fileResult):
        for bidId in staged_bids:
            bid = (staged_bids[bidId])['Object']
            bidProv = bid.getProviderBid()
            forecast = (staged_bids[bidId])['Forecast']
            quantity = self.purchaseBasedOnProvidersBids(currentPeriod, bidProv.getService(), bidProv, forecast, fileResult)
            ((staged_bids[bidId])['Object']).setCapacity(quantity)

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
            document = self.removeIlegalCharacters(messageResult.getBody())
            try:
                dom = xml.dom.minidom.parseString(document)
                return self.handleBestBids(dom)
            except Exception as e: 
                raise FoundationException(str(e))
        else:
            raise FoundationException("Best bids not received")

    def moveQuality(self, service, adaptationFactor, marketPosition, direction,  fileResult):
        ''' 
        This creates the direction of the move to quality.
        direction should be 1 or -1, when 1 improves, -1 decrease
        '''
        self.registerLog(fileResult, 'decreaseQuality') 
        output = {}
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

            # If the variable is price, it maintains the current level of the decision variable
            if (service._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                output[decisionVariable] = {'Direction' : direction, 'Step': 0}
        
        
        self.registerLog(fileResult, 'decreaseQuality:' + str(output)) 
        return output
        
            
    def movePrice(self, service, adaptationFactor, marketPosition, direction, fileResult):
        ''' 
        This creates the direction of the move to decrease quality.
        direction should be 1 or -1, when 1 improves, 0 decrease
        '''
        self.registerLog(fileResult, 'movePrice') 
        output = {}
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

            # Gets the modeling objetive of the decision variable
            if (service._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                output[decisionVariable] = {'Direction' : direction, 'Step': 0}
                
        self.registerLog(fileResult, 'movePrice:' + str(output)) 
        return output

    def getRelatedDecisionVariable(self, serviceFrom, serviceTo, decisionVariableIdFrom):
        if serviceFrom.getId() in self._servicesRelat.keys():
            for tmp_tuple in self._servicesRelat[serviceFrom.getId()]:
                if ((tmp_tuple[0] == serviceTo.getId()) and (tmp_tuple[1] == decisionVariableIdFrom)):
                    return tmp_tuple[2]
            raise FoundationException("service to or decision variable from not found in relationships")
        else:
            raise FoundationException("Own Service not found in service relationships")

    def convertToOwnBid(self, serviceOwn, serviceProvider,  bid):
        '''
        This function assumes that we keep the same distance in percentage with the optimal 
        value
        '''
        newBid = Bid()
        uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
        idStr = str(uuidId)
        newBid.setValues(idStr, self.getProviderId(), serviceOwn.getId())

        for decisionVariable in serviceProvider._decision_variables:
            min_value = (serviceProvider.getDecisionVariable(decisionVariable)).getMinValue()
            max_value = (serviceProvider.getDecisionVariable(decisionVariable)).getMaxValue()
            provOptimum = serviceProvider.getDecisionVariableObjetive(decisionVariable)            

            value = bid.getDecisionVariable(decisionVariable)
            
            if ((max_value - min_value) == 0 ):
                percentage = 1
            else:
                percentage = (value -min_value) / (max_value - min_value)
            
            ownDecisionVariable = self.getRelatedDecisionVariable(serviceProvider, serviceOwn, decisionVariable)
            min_value = (serviceOwn.getDecisionVariable(ownDecisionVariable)).getMinValue()
            max_value = (serviceOwn.getDecisionVariable(ownDecisionVariable)).getMaxValue()            
            ownOptimum = serviceOwn.getDecisionVariableObjetive(ownDecisionVariable)
            
            if (decisionVariable != serviceProvider.getPriceDecisionVariable()):
                if (ownOptimum == 1) and (provOptimum == 1) : # both maximize
                    newValue = min_value + (percentage*(max_value-min_value))
                
                if (ownOptimum == 1) and (provOptimum == 2) : # own maximize provider:minimize
                    newValue = min_value + ((1-percentage)*(max_value-min_value))
                
                if (ownOptimum == 2) and (provOptimum == 1) : # own minimize provider:maximize
                    newValue = min_value + ((1-percentage)*(max_value-min_value))
                
                if (ownOptimum == 2) and (provOptimum == 2) : # own minimize provider:minimize
                    newValue = min_value + (percentage*(max_value-min_value))
            else:
                newValue = min_value + (percentage*(max_value-min_value))
                
            newBid.setDecisionVariable(ownDecisionVariable, newValue)
        
        return newBid

    def moveBidOnDirectionEdge(self, bid, service, directionMove ):
        # Create a new bid
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
    
    '''
    Identifies the direction of the move depending on the profit forecast. Bid must be an own bid.
    '''
    def determineProfitForecast(self, currentPeriod, numAncestors, radius, serviceOwn, serviceProvider, adaptationFactor, marketPosition, bid, fileResult):
        bids_related = self.getOwnRelatedBids(bid, radius, currentPeriod - 1 , numAncestors, fileResult)
        i = 0
        progression = []
        while (i < numAncestors):
            profitZone, totProfit, numRelated = self.getDBProfitZone(bid, bids_related, currentPeriod - (i+1), fileResult)
            progression.append({'bid' : None, 'profit' : totProfit, 'delta_profit' : 0 })
            i = i + 1
        self.calculateDeltaProfitProgression(progression)
        profitEstimate = self.movingAverage(progression)
        return profitEstimate

    def isNeighborhoodBidToStaged(self, newBid,  staged_bids, radius, fileResult):
        '''
        Establish whether or not a bid is neigboor of other bid already staged.
        '''    
        # Compare the distance againts bids that will not be changed
        for bidIdComp in staged_bids:
            bidComp = (staged_bids[bidIdComp])['Object']
            if (self.areNeighborhoodBids(radius, newBid, bidComp) == True):
                return True
            
        return False


    def includeExploringBid(self, newBid, oldBid, serviceOwn, radius, staged_bids_resp, staged_bids, fileResult):
        self.registerLog(fileResult, 'Starting includeExploringBid')
        if ( self.isNeighborhoodBidToStaged(newBid,staged_bids,radius, fileResult) == False ):
            self.registerLog(fileResult, 'includeExploringBid method is incluing another bid.')
            decVarPrice = serviceOwn.getPriceDecisionVariable()
            newBid.setProviderBid(oldBid)
            bidPrice = newBid.getDecisionVariable(decVarPrice)
            self.completeNewBidInformation(newBid, bidPrice, fileResult )
            staged_bids_resp[newBid.getId()] = {'Object': newBid, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 0 }
        
        
    def execFrontBids(self, currentPeriod, numAncestors, radius, serviceOwn, serviceProvider, adaptationFactor, marketPosition, bidList, staged_bids, explore_staged_bids, fileResult):
        for bid in bidList:
            # This type of providers have three options, decrease quality, decrease price, or increase prices
            # decrease the quality
            direction = -1
            directionQuality = self.moveQuality(serviceProvider, adaptationFactor, marketPosition, direction, fileResult)
            newBidProv = self.moveBidOnDirectionEdge(bid, serviceProvider, directionQuality)
            newBidOwn1 = self.convertToOwnBid( serviceOwn, serviceProvider,  newBidProv)
            profForecast = self.determineProfitForecast(currentPeriod, numAncestors, radius, serviceOwn, serviceProvider, adaptationFactor, marketPosition, newBidOwn1, fileResult) 
            if (profForecast >= 0):
                self.includeExploringBid(newBidOwn1, bid, serviceOwn, radius, explore_staged_bids, staged_bids, fileResult)
                
            
            # increase prices
            direction = 1
            directionPrice = self.movePrice(serviceProvider, adaptationFactor, marketPosition, direction, fileResult)
            newBidProv = self.moveBidOnDirectionEdge(bid, serviceProvider, directionPrice)
            newBidOwn2 = self.convertToOwnBid( serviceOwn, serviceProvider,  newBidProv)
            profForecast = self.determineProfitForecast(currentPeriod, numAncestors, radius, serviceOwn, serviceProvider, adaptationFactor, marketPosition, newBidOwn2, fileResult)
            if (profForecast >= 0):
                self.includeExploringBid(newBidOwn2, bid, serviceOwn, radius, explore_staged_bids, staged_bids, fileResult)
            
            # decrease prices
            direction = -1
            directionPrice = self.movePrice(serviceProvider, adaptationFactor, marketPosition, direction, fileResult)
            newBidProv = self.moveBidOnDirectionEdge(bid, serviceProvider, directionPrice)
            newBidOwn3 = self.convertToOwnBid( serviceOwn, serviceProvider,  newBidProv)
            profForecast = self.determineProfitForecast(currentPeriod, numAncestors, radius, serviceOwn, serviceProvider, adaptationFactor, marketPosition, newBidOwn3, fileResult)
            if (profForecast >= 0):
                self.includeExploringBid(newBidOwn3, bid, serviceOwn, radius, explore_staged_bids, staged_bids, fileResult)
                

    '''
    Execute the bid update for an specific service that is required for a resource.
    return quantities purchased.
    '''                     
    def execBidUpdate(self, currentPeriod, numAncestors, radius, serviceOwn, serviceProvider, adaptationFactor, marketPosition, staged_bids, explore_staged_bids, fileResult):
        dic_return = self.AskBackhaulBids(serviceProvider.getId())
        self.registerLog(fileResult, 'Period: ' + str(currentPeriod) + 'Number of fronts:' + str(len(dic_return)))
        # Sorts the offerings  based on the customer's needs 
        if (len(dic_return) > 0):
            keys_sorted = sorted(dic_return,reverse=True)
            for front in keys_sorted:
                bidList = dic_return[front]                                                                        
                self.execFrontBids(currentPeriod, numAncestors, radius, serviceOwn, serviceProvider, adaptationFactor, marketPosition, bidList, staged_bids, explore_staged_bids, fileResult)
                break
        self.registerLog(fileResult, 'Nbr staged bids by method execBidUpdate:' + str(len(explore_staged_bids)) )


    ''' 
    get those own bids that are in my neighborhood
    '''    
    def getOwnRelatedBids(self, bid, radius, currentPeriod, numPeriods, fileResult):
        self.registerLog(fileResult, 'getOwnRelatedBids:' + bid.getId() )
        ret_relatedBids = {}
        for bidId in self._list_vars['Bids']:
            otherBid = (self._list_vars['Bids'])[bidId]
            # bids recent enough to be taken into account.
            if (otherBid.getCreationPeriod() >= (currentPeriod - numPeriods)):
                if (self.areNeighborhoodBids(radius, bid, otherBid)):
                    ret_relatedBids[bidId] = otherBid
        
        self.registerLog(fileResult, 'getOwnRelatedBids:' + str(len(ret_relatedBids)) )
        return ret_relatedBids


    def calculateForecast(self, radius, currentPeriod, numPeriods, initialQtyByBid, staged_bids, fileResult):
        totForecast = 0        
        for bidId in staged_bids:
            bid = (staged_bids[bidId])['Object']
            related_bids = self.getOwnRelatedBids( bid, radius, currentPeriod - 1, numPeriods, fileResult)
            marketZoneDemand, totQuantity, numRelated = self.getDBMarketShareZone(bid, related_bids, currentPeriod -1, numPeriods, fileResult)
            marketZoneBacklog, totQtyBacklog, numRelatedBacklog = self.getDBMarketShareZone(bid, related_bids, currentPeriod -1, numPeriods, fileResult, Provider.BACKLOG)
            (staged_bids[bidId])['MarketShare'] = marketZoneDemand
            totQtyBacklog = totQtyBacklog *0.1
            totForecast = totForecast + (totQuantity + totQtyBacklog) / (numRelated + 1)
            (staged_bids[bidId])['Forecast'] = (totQuantity + totQtyBacklog) / (numRelated + 1)
        
        # Apply for cases where the forecast is zero as when the process starts
        if (totForecast == 0): 
            for bidId in staged_bids:
                (staged_bids[bidId])['Forecast'] = initialQtyByBid

    def canAdoptStrongPosition(self, currentPeriod, fileResult):
        self.registerLog(fileResult, 'Starting canAdoptStrongPosition')
        value = self._list_vars['Random'].uniform(0, 1)
        val_return = True
        if value <= self.getMonopolistPosition():
            val_return = False
        self.registerLog(fileResult, 'Ending canAdoptStrongPosition' + str(val_return))            
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
        self.purchaseBids(staged_bids, availability, fileResult)
        self.registerLog(fileResult, 'Nbr staged bids by method updateCurrentBids:' + str(len(staged_bids)) )
    
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
        if (self._list_vars['State'] == AgentServerHandler.BID_PERMITED):
            fileResult = open(self._list_vars['strId'] + '.log',"a")
            self.registerLog(fileResult, 'executing algorithm ####### ProviderId:' + str(self.getProviderId()) + ' - Period: ' +  str(self.getCurrentPeriod()) )

            # This code can be used to test connection with servers.  
#            price = 16
#            quality = 0.4
#            newBid = Bid()
#            uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
#            idStr = str(uuidId)
#            newBid.setValues(idStr, 'Provider22', '2')
#            newBid.setDecisionVariable("4", price)  #Price
#            newBid.setDecisionVariable("3", quality)     # Delay
#            newBid.setId('Bid' + str(self.getCurrentPeriod()))
#            newBid.setStatus(Bid.ACTIVE)
#            newBid.setCreationPeriod(self.getCurrentPeriod())
#            try:
#                self.purchaseBasedOnProvidersBids( self.getCurrentPeriod(), '2', newBid, 5, fileResult)
#            except:
#                pass
            # End code inital test.
            
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
                
                # Purchase the bids that are already in place with the forecast given by historical demand
                self.updateCurrentBids(currentPeriod, radius, serviceOwn, staged_bids, availability, fileResult)
                self.sendBids(staged_bids, fileResult)
    
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
            
            fileResult.close()
            
        self._list_vars['State'] = AgentServerHandler.IDLE
