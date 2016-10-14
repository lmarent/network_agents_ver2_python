import multiprocessing
from Provider import Provider
from ProviderAgentException import ProviderException
from foundation.FoundationException import FoundationException
import foundation.agent_properties
import MySQLdb
import logging
import datetime
import os
import sys
import re
import inspect
from foundation.Bid import Bid
import uuid
from foundation.Agent import Agent
from foundation.AgentType import AgentType
from foundation.DecisionVariable import DecisionVariable




logger = logging.getLogger('provider_application')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('providers_test.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

def createBid(strProv, serviceId, delay, price):
    '''
    Create an edge provider bid
    '''
    bid = Bid()
    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
    idStr = str(uuidId)
    bid.setValues(idStr, strProv, serviceId)
    bid.setDecisionVariable("1", price)  #Price
    bid.setDecisionVariable("2", delay)     # Delay
    bid.setStatus(Bid.ACTIVE)
    return bid

def createBidService2(strProv, serviceId, quality, price):
    '''
    Create a transit provider bid
    '''
    bid = Bid()
    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
    idStr = str(uuidId)
    bid.setValues(idStr, strProv, serviceId)
    bid.setDecisionVariable("3", quality)  # quality
    bid.setDecisionVariable("4", price)     # Price
    bid.setStatus(Bid.ACTIVE)
    return bid


def load_classes(list_classes):
    currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    sys.path.append(currentdir)
    agents_directory = currentdir
    black_list = ['ProviderExecution', 'ProviderAgentException','ProviderExecutionTest', 'ProviderEdgeTest']
    for filename in os.listdir (agents_directory):
        	# Ignore subfolders
        	if os.path.isdir (os.path.join(agents_directory, filename)):
        	    continue
        	else:
        	    if re.match(r"Provider.*?\.py$", filename):
        		classname = re.sub(r".py", r"", filename)
        		if (classname not in black_list):
        		    module = __import__(classname)
        		    targetClass = getattr(module, classname)
        		    list_classes[classname] = targetClass   
    logging.debug('Load Providers Classes initialized')


def getGeneralConfigurationParameters(cursor):
    sql = "SELECT bid_periods, initial_offer_number, \
		  num_periods_market_share \
	     FROM simulation_generalparameters limit 1" 
    cursor.execute(sql)
    results = cursor.fetchall()
    for row in results:
        	bidPeriods = row[0]
        	numberOffers = row[1]
        	numAccumPeriods = row[2]
        	break
    return bidPeriods, numberOffers, numAccumPeriods

def getSeed(seed, year, month, day, hour, minute, second, microsecond):
    if (seed == 1):
        	# the seed for random numbers was defined, therefore we use it.
        	dtime = datetime.datetime(year,month,day,hour,minute,second,microsecond)
    else:
        dtime = datetime.datetime.now()		
    return dtime

def create(list_classes, typ, providerName, providerId, serviceId, providerSeed, marketPositon, 
	    adaptationFactor, monopolistPosition, debug, resources, numberOffers, 
        numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, 
        capacityControl, purchase_service):
    print 'In create provider - Class requested:' + str(typ)
    print list_classes
    if typ in list_classes:
        	targetClass = list_classes[typ]
        	return targetClass(providerName, providerId, serviceId, providerSeed, 
        			   marketPositon, adaptationFactor, monopolistPosition, 
        			   debug, resources, numberOffers, numAccumPeriods, 
        			   numAncestors, startFromPeriod, sellingAddress, buyingAddress, 
                    capacityControl, str(purchase_service))
    else:
        err = 'Class' + typ + 'not found to be loaded'
        raise ProviderException(err)

def deleteDBPreviousInformation(cursor):
    # Delete all the data for the current execution in the database.
    sql = "delete from Network_Simulation.simulation_bid \
            where execution_count in ( select b.execution_count  \
              from Network_Simulation.simulation_generalparameters b )"    
    cursor.execute(sql)
    
    sql = "delete from Network_Simulation.simulation_bid_purchases \
            where execution_count in ( select b.execution_count  \
              from Network_Simulation.simulation_generalparameters b )"
    cursor.execute(sql)

    sql = "delete from Network_Simulation.simulation_bid_decision_variable \
            where execution_count in ( select b.execution_count  \
              from Network_Simulation.simulation_generalparameters b )"
    cursor.execute(sql)

def getExecutionCount(cursor):
    executionCount = 0    
    sql = "select execution_count from Network_Simulation.simulation_generalparameters limit 1"
    cursor.execute(sql)
    results = cursor.fetchall()
    for row in results:
        executionCount = int(row[0])
        break
    if (executionCount == 0):
        raise FoundationException("execution count not defined")
    return executionCount


def insertDBBid(cursor, period, executionCount, bid):
    sql = "insert into Network_Simulation.simulation_bid (period, bidId, providerId, \
            status, paretoStatus,dominatedCount, execution_count) \
                values (%s, %s, %s, %s, %s, %s, %s)"    
    args = (period, bid.getId(), bid.getProvider(), 1, 0, 0, executionCount)
    cursor.execute(sql, args )

def insertDBBidPurchase(cursor, period, serviceId, executionCount, bid, quantity):
    sql = "insert into Network_Simulation.simulation_bid_purchases(period, \
            serviceId,bidId,quantity, execution_count) values (%s, %s, %s, %s, %s)"    
    args = (period, serviceId, bid.getId(), quantity, executionCount)
    cursor.execute(sql, args )

def sendBid(bid, action, provider):
    bid.setStatus(action)
    message = bid.to_message()
    messageResult = provider.sendMessageMarket(message)
    if messageResult.isMessageStatusOk():
        pass

def test_initialization(provider):
    provider.start_agent()
    provider.initialize()
    
    if ((provider._list_vars['Type']).getType() == AgentType.PROVIDER_ISP):
        resourceServices = provider._list_vars['Resource_Service']
        if (len (resourceServices) != 1):
            raise FoundationException("error in test_initialization")
        
        serviceRel = provider._servicesRelat
        if (len(serviceRel) <= 0):
            raise FoundationException("error in test_initialization")
        
def test_swap_purchased_bid(provider, currentPeriod, fileResult):
    # Happy path     
    # Create six bids for the provider and put it on staged
    staged_bids = {}
    bidsToVerify = []
    bid1 = createBid(provider.getProviderId(), serviceId, 0, 0)    
    staged_bids[bid1.getId()] = {'Object': bid1, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 0 }
    bidsToVerify.append(bid1)

    
    # Add the five bids to be purchased
    purchasedBids = []
    bid7 = createBid(provider.getProviderId(), serviceId, 0, 0)    
    bid7.setCapacity(10)
    bidsToVerify.append(bid7)
    
    bid8 = createBid(provider.getProviderId(), serviceId, 0, 0)    
    bid8.setCapacity(20)
    bidsToVerify.append(bid8)
    
    bid9 = createBid(provider.getProviderId(), serviceId, 0, 0)    
    bid9.setCapacity(30)
    bidsToVerify.append(bid9)
    
    bid10 = createBid(provider.getProviderId(), serviceId, 0, 0)    
    bid10.setCapacity(40)
    bidsToVerify.append(bid10)
    
    # This bid should not be included.    
    bid11 = createBid(provider.getProviderId(), serviceId, 0, 0)    
    bid11.setCapacity(0)
    
    purchasedBids.append(bid7)
    purchasedBids.append(bid8)
    purchasedBids.append(bid9)
    purchasedBids.append(bid10)
    purchasedBids.append(bid11)
        
    # Call the function 
    provider.swapPurchasedBids(currentPeriod, purchasedBids, staged_bids, fileResult)
    
    # Verifies the number of total bids.    
    if len(staged_bids) != len(bidsToVerify):
        raise FoundationException("error in test_swap_purchased_bid - Error:1")
    
    for bid in bidsToVerify:
        if bid.getId() not in staged_bids.keys():
            raise FoundationException("error in test_swap_purchased_bid - Error:2")
    
    # Verify that forecast was included
    if (staged_bids[bid7.getId()]['Forecast'] != bid7.getCapacity()):
        raise FoundationException("error in test_swap_purchased_bid - Error:3")

    if (staged_bids[bid8.getId()]['Forecast'] != bid8.getCapacity()):
        raise FoundationException("error in test_swap_purchased_bid - Error:4")

    if (staged_bids[bid9.getId()]['Forecast'] != bid9.getCapacity()):
        raise FoundationException("error in test_swap_purchased_bid - Error:5")

    if (staged_bids[bid10.getId()]['Forecast'] != bid10.getCapacity()):
        raise FoundationException("error in test_swap_purchased_bid - Error:6")
    
    # test errors: The bid given is not included
    
    purchasedBids2 = []
    bid12 = createBid(provider.getProviderId(), serviceId, 0, 0)    
    bid12.setCapacity(60)
    bidsToVerify.append(bid12)
    
    bid13 = createBid(provider.getProviderId(), serviceId, 0, 0)    
    bid13.setCapacity(60)
    bidsToVerify.append(bid13)
    
    purchasedBids2.append(bid12)
    purchasedBids2.append(bid13)
    
    provider.swapPurchasedBids(currentPeriod, purchasedBids2, staged_bids, fileResult)
    
    if len(staged_bids) != len(bidsToVerify):
        raise FoundationException("error in test_swap_purchased_bid - Error:8")

def test_calculate_bid_unitary_cost(ispProvider,transitProvider, fileResult):

    # a unit of resource has a cost of 10. 
    
    ownBid1a = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.194, 0)
    totUnitValue = ispProvider.calculateBidUnitaryCost(ownBid1a, fileResult)
    totUnitValue = round(totUnitValue,2)
    if (totUnitValue != 5.0):
        logger.error('totUnitValue:%s', str(totUnitValue))
        raise FoundationException("error in test_calculate_bid_unitary_cost - Error:1")

    ownBid1b = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.188, 0)
    totUnitValue = ispProvider.calculateBidUnitaryCost(ownBid1b, fileResult)
    totUnitValue = round(totUnitValue,2)
    if (totUnitValue != 6.0):
        logger.error('totUnitValue:%s', str(totUnitValue))
        raise FoundationException("error in test_calculate_bid_unitary_cost - Error:2")

    ownBid1c = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.182, 0)
    totUnitValue = ispProvider.calculateBidUnitaryCost(ownBid1c, fileResult)
    totUnitValue = round(totUnitValue,2)
    if (totUnitValue != 7.0):
        logger.error('totUnitValue:%s', str(totUnitValue))
        raise FoundationException("error in test_calculate_bid_unitary_cost - Error:3")

    ownBid1d = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.176, 0)
    totUnitValue = ispProvider.calculateBidUnitaryCost(ownBid1d, fileResult)
    totUnitValue = round(totUnitValue,2)
    if (totUnitValue != 8.0):
        logger.error('totUnitValue:%s', str(totUnitValue))
        raise FoundationException("error in test_calculate_bid_unitary_cost - Error:4")
    
    ownBid1 = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.2, 0)
    totUnitValue = ispProvider.calculateBidUnitaryCost(ownBid1, fileResult)
    totUnitValue = round(totUnitValue,0)
    if (totUnitValue != 4.0):
        logger.error('totUnitValue:%s', str(totUnitValue))
        raise FoundationException("error in test_calculate_bid_unitary_cost - Error:5")
    
    providerBid1 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.1, 10)
    
    ownBid2 = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.18, 0)
    ownBid2.setProviderBid(providerBid1)
    totUnitValue = ispProvider.calculateBidUnitaryCost(ownBid2, fileResult)
    totUnitValue = round(totUnitValue,2)
    if (totUnitValue != 17.33):
        logger.error('totUnitValue:%s', str(totUnitValue))
        raise FoundationException("error in test_calculate_bid_unitary_cost - Error:6")
        
    ownBid3 = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.16, 0)
    providerBid2 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.1, 6)
    ownBid3.setProviderBid(providerBid2)
    totUnitValue = ispProvider.calculateBidUnitaryCost(ownBid3, fileResult)
    totUnitValue = round(totUnitValue,2)
    if (totUnitValue != 16.67):
        logger.error('totUnitValue:%s', str(totUnitValue))
        raise FoundationException("error in test_calculate_bid_unitary_cost - Error:7")
    
    # test the resources assignment by quality requirement
    ownBid4 = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.16, 0)
    providerBid3 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.1, 6)
    ownBid4.setProviderBid(providerBid3)
    ownBid4.setQualityRequirement('2',0.18)
    totUnitValue = ispProvider.calculateBidUnitaryCost(ownBid4, fileResult)
    totUnitValue = round(totUnitValue,2)
    if (totUnitValue != 13.33):
        logger.error('totUnitValue:%s', str(totUnitValue))
        raise FoundationException("error in test_calculate_bid_unitary_cost - Error:8")
       
def test_replicate_bids(ispProvider, transitProvider, fileResult):
    # create the own bid    
    ownBid = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0, 0)    
    
    # create four bids for the transitProvider
    providerBids = []
    providerBid1 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.1, 10)
    providerBids.append(providerBid1.getId())
    providerBid2 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.2, 11)
    providerBids.append(providerBid2.getId())
    providerBid3 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.3, 12)
    providerBids.append(providerBid3.getId())
    providerBid4 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.4, 13)
    providerBids.append(providerBid4.getId())
    
    # create the qualityRequirements for every bid of the transit provider
    qualityRequest1 = {}
    qualityRequest1['2'] = 0.194
    qualityRequest2 = {}
    qualityRequest2['2'] = 0.188
    qualityRequest3 = {}
    qualityRequest3['2'] = 0.182
    qualityRequest4 = {}
    qualityRequest4['2'] = 0.176
    
    # create the bidPurchasable dictionary
    bidPurchasable = {}
    bidPurchasable[providerBid1.getId()] = {'Object' : providerBid1, 'QualityRequirements' : qualityRequest1 }
    bidPurchasable[providerBid2.getId()] = {'Object' : providerBid2, 'QualityRequirements' : qualityRequest2 }
    bidPurchasable[providerBid3.getId()] = {'Object' : providerBid3, 'QualityRequirements' : qualityRequest3 }
    bidPurchasable[providerBid4.getId()] = {'Object' : providerBid4, 'QualityRequirements' : qualityRequest4 }
    
    # finally verified that four new bids are returned 
    bidPrice = 100 # This is a really big price in order to test that method is doing well.
    newOwnBids = ispProvider.replicateBids(ownBid, bidPrice , bidPurchasable, fileResult)
    if (len(newOwnBids) != 4):
        raise FoundationException("error in test_replicate_bids - Error:1")
    # This is the lowest price in order to test that method is doing well.
    bidPrice = 0 
    newOwnBids2 = ispProvider.replicateBids(ownBid, bidPrice , bidPurchasable, fileResult)
    if (len(newOwnBids2) != 0):
        raise FoundationException("error in test_replicate_bids - Error:2")
    # Verify costs of returned bids. - cost function is linear
        
    for bidTuple in newOwnBids:
        profit = bidTuple[0]
        bid = bidTuple[1]
        if (bid.getProviderBid() == None):
            raise FoundationException("error in test_replicate_bids - Error:3")
        
        if ((bid.getProviderBid()).getId() not in providerBids):
            raise FoundationException("error in test_replicate_bids - Error:4")
        else:
            providerBids.remove( (bid.getProviderBid().getId()) )
            
        if ((bid.getProviderBid()).getId() == providerBid1.getId()):
            if (round(profit,2) != 85.0):
                raise FoundationException("error in test_replicate_bids - Error:5")

        if ((bid.getProviderBid()).getId() == providerBid2.getId()):
            profit = round(profit,2)
            if (profit != 83.0):
                logger.error('profit:%s', str(profit))
                raise FoundationException("error in test_replicate_bids - Error:6")

        if ((bid.getProviderBid()).getId() == providerBid3.getId()):
            profit = round(profit,2)
            if (profit != 81.0):
                logger.error('profit:%s', str(profit))
                raise FoundationException("error in test_replicate_bids - Error:7")

        if ((bid.getProviderBid()).getId() == providerBid4.getId()):
            profit = round(profit,2)
            if (profit != 79.0):
                logger.error('profit:%s', str(profit))
                raise FoundationException("error in test_replicate_bids - Error:7")
    # Finally test that all bids from the provider were replicated.        
    if len(providerBids) > 0:
        raise FoundationException("error in test_replicate_bids - Error:5")

def test_calculate_own_quality_for_purchasable_bid( ispProvider, transitProvider, fileResult ):

    # create the own bid    
    ownBid = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.17, 14)
    
    # create a bid for the provider
    providerBid1 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.03, 10)

    qualityRequirements, nonPurchasable = ispProvider.calculateOwnQualityForPurchasableBid(ownBid, providerBid1, fileResult)
    if '2' in qualityRequirements.keys():
        val = round(qualityRequirements['2'],2)
        if  ( val != 0.14):
            raise FoundationException("error in test_calculate_own_quality_for_purchasable_bid - Error:1")
        if nonPurchasable != False:
            raise FoundationException("error in test_calculate_own_quality_for_purchasable_bid - Error:2")
    else:
        raise FoundationException("error in test_calculate_own_quality_for_purchasable_bid - Error:3")
    
    # create the own bid
    ownBid2 = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.2, 14)
    qualityRequirements, nonPurchasable = ispProvider.calculateOwnQualityForPurchasableBid(ownBid2, providerBid1, fileResult)
    if '2' in qualityRequirements.keys():
        val = round(qualityRequirements['2'],2)
        if  ( val != 0.17):
            raise FoundationException("error in test_calculate_own_quality_for_purchasable_bid - Error:4")

        if nonPurchasable != False:
            raise FoundationException("error in test_calculate_own_quality_for_purchasable_bid - Error:5")
    else:
        raise FoundationException("error in test_calculate_own_quality_for_purchasable_bid - Error:6")

    # create the own bid
    ownBid2 = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.14, 14)
    qualityRequirements, nonPurchasable = ispProvider.calculateOwnQualityForPurchasableBid(ownBid2, providerBid1, fileResult)
    if '2' in qualityRequirements.keys():
        val = round(qualityRequirements['2'],2)
        if  ( val != -1):
            raise FoundationException("error in test_calculate_own_quality_for_purchasable_bid - Error:7")

        if nonPurchasable != True:
            raise FoundationException("error in test_calculate_own_quality_for_purchasable_bid - Error:8")
    else:
        raise FoundationException("error in test_calculate_own_quality_for_purchasable_bid - Error:9")


    # create the own bid    
    ownBid2 = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.10, 14)
    qualityRequirements, nonPurchasable = ispProvider.calculateOwnQualityForPurchasableBid(ownBid2, providerBid1, fileResult)
    if '2' in qualityRequirements.keys():
        val = round(qualityRequirements['2'],2)
        if  ( val != -1 ):
            raise FoundationException("error in test_calculate_own_quality_for_purchasable_bid - Error:10")

        if nonPurchasable != True:
            raise FoundationException("error in test_calculate_own_quality_for_purchasable_bid - Error:11")
    else:
        raise FoundationException("error in test_calculate_own_quality_for_purchasable_bid - Error:12")
    
                   
def test_capacity_update(provider1):
    
    # Assigns locally the capacity to 100 for all of the resources.
    provider1.restartAvailableCapacity()
    resources = provider1._used_variables['resources']
    for resourceId in resources:
        print (resources[resourceId])['Capacity']
        print (resources[resourceId])['Cost']
        provider1.updateAvailability(resourceId, 100)
        
    availability = {}
    for resourceId in resources:
        availability[resourceId] = provider1.getAvailableCapacity(resourceId)
        if (availability[resourceId] != 100):
            raise FoundationException("error in test_capacity_update")
        
    provider1.sendCapacityEdgeProvider(availability)
        
    # Assigns locally the capacity to 200 for all of the resources.
    provider1.restartAvailableCapacity()
    resources = provider1._used_variables['resources']
    for resourceId in resources:
        print (resources[resourceId])['Capacity']
        print (resources[resourceId])['Cost']
        provider1.updateAvailability(resourceId, 200)
        
    availability = {}
    for resourceId in resources:
        availability[resourceId] = provider1.getAvailableCapacity(resourceId)
        if (availability[resourceId] != 200):
            raise FoundationException("error in test_capacity_update")
                
    provider1.sendCapacityEdgeProvider(availability)
    provider1.restartAvailableCapacity()
    availability = {}
    for resourceId in resources:
        availability[resourceId] = provider1.getAvailableCapacity(resourceId)
    provider1.sendCapacityEdgeProvider(availability)


def test_get_related_decision_variable(ispProvider, transitProvider):

    # DELAY    
    delayVariable = '2'
    decisionVariableTo, aggregation = ispProvider.getRelatedDecisionVariable( ispProvider.getServiceId(), transitProvider.getServiceId(), delayVariable )
    if decisionVariableTo != '3':
        raise FoundationException("error in test_get_related_decision_variable - Error:1")

    if aggregation != 'S':
        raise FoundationException("error in test_get_related_decision_variable - Error:2")

    # PRICE    
    delayVariable = '1'
    decisionVariableTo, aggregation = ispProvider.getRelatedDecisionVariable( ispProvider.getServiceId(), transitProvider.getServiceId(), delayVariable )
    if decisionVariableTo != '4':
        raise FoundationException("error in test_get_related_decision_variable - Error:3")

    if aggregation != 'S':
        raise FoundationException("error in test_get_related_decision_variable - Error:4")

    # TRANSIT DELAY
    delayVariable = '3'    
    decisionVariableTo, aggregation = ispProvider.getRelatedDecisionVariable( transitProvider.getServiceId(), ispProvider.getServiceId(), delayVariable )
    if decisionVariableTo != '2':
        raise FoundationException("error in test_get_related_decision_variable - Error:5")

    if aggregation != 'S':
        raise FoundationException("error in test_get_related_decision_variable - Error:6")

    # TRANSIT PRICE
    delayVariable = '4'    
    decisionVariableTo, aggregation = ispProvider.getRelatedDecisionVariable( transitProvider.getServiceId(), ispProvider.getServiceId(), delayVariable )
    if decisionVariableTo != '1':
        raise FoundationException("error in test_get_related_decision_variable - Error:7")

    if aggregation != 'S':
        raise FoundationException("error in test_get_related_decision_variable - Error:8")

def test_calculate_required_quality(provider):
    bidQuality = 0.17
    aggregationMode = 'S'
    minValue = 0.0
    maxValue = 1.0
    providerQuality = 0.3
    optObjetive = DecisionVariable.OPT_MINIMIZE
    value = provider.calculateRequiredQuality( bidQuality, minValue, maxValue, providerQuality, optObjetive, aggregationMode)
    if (round(value,0) != -1.0):
        raise FoundationException("error in test_calculate_required_quality - Error 1")

    bidQuality = 0.5
    aggregationMode = 'S'
    minValue = 0.0
    maxValue = 1.0
    providerQuality = 0.3
    optObjetive = DecisionVariable.OPT_MINIMIZE
    value = provider.calculateRequiredQuality( bidQuality, minValue, maxValue, providerQuality, optObjetive, aggregationMode)
    if (round(value,1) != 0.2):
        raise FoundationException("error in test_calculate_required_quality - Error 2")
    
    
    bidQuality = 0.17
    aggregationMode = 'S'
    minValue = 0.0
    maxValue = 1.0
    providerQuality = 0.2
    optObjetive = DecisionVariable.OPT_MAXIMIZE
    value = provider.calculateRequiredQuality( bidQuality, minValue, maxValue, providerQuality, optObjetive, aggregationMode)
    if (round(value,0) != -1.0):
        raise FoundationException("error in test_calculate_required_quality - Error 3")

    bidQuality = 0.3
    aggregationMode = 'S'
    minValue = 0.0
    maxValue = 1.0
    providerQuality = 0.2
    optObjetive = DecisionVariable.OPT_MAXIMIZE
    value = provider.calculateRequiredQuality( bidQuality, minValue, maxValue, providerQuality, optObjetive, aggregationMode)
    if (round(value,1) != 0.1):
        raise FoundationException("error in test_calculate_required_quality - Error 4")


    bidQuality = 0.6
    aggregationMode = 'S'
    minValue = 0.0
    maxValue = 1.0
    providerQuality = 0.2
    optObjetive = DecisionVariable.OPT_MAXIMIZE
    value = provider.calculateRequiredQuality( bidQuality, minValue, maxValue, providerQuality, optObjetive, aggregationMode)
    if (round(value,1) != 0.4):
        raise FoundationException("error in test_calculate_required_quality - Error 5")

    bidQuality = 0.6
    aggregationMode = 'M'
    minValue = 0.0
    maxValue = 1.0
    providerQuality = 0.2
    optObjetive = DecisionVariable.OPT_MAXIMIZE
    value = provider.calculateRequiredQuality( bidQuality, minValue, maxValue, providerQuality, optObjetive, aggregationMode)
    if (round(value,1) != 0.6):
        raise FoundationException("error in test_calculate_required_quality - Error 6")

    bidQuality = 0.1
    aggregationMode = 'M'
    minValue = 0.0
    maxValue = 1.0
    providerQuality = 0.2
    optObjetive = DecisionVariable.OPT_MAXIMIZE
    value = provider.calculateRequiredQuality( bidQuality, minValue, maxValue, providerQuality, optObjetive, aggregationMode)
    if (round(value,0) != -1):
        raise FoundationException("error in test_calculate_required_quality - Error 7")


    bidQuality = 0.1
    aggregationMode = 'N'
    minValue = 0.0
    maxValue = 1.0
    providerQuality = 0.2
    optObjetive = DecisionVariable.OPT_MAXIMIZE
    value = provider.calculateRequiredQuality( bidQuality, minValue, maxValue, providerQuality, optObjetive, aggregationMode)
    if (round(value,1) != 0.1):
        raise FoundationException("error in test_calculate_required_quality - Error 6")

    bidQuality = 0.3
    aggregationMode = 'N'
    minValue = 0.0
    maxValue = 1.0
    providerQuality = 0.2
    optObjetive = DecisionVariable.OPT_MAXIMIZE
    value = provider.calculateRequiredQuality( bidQuality, minValue, maxValue, providerQuality, optObjetive, aggregationMode)
    if (round(value,0) != -1.0):
        raise FoundationException("error in test_calculate_required_quality - Error 7")

def test_get_purchased_front(ispProvider, transitProvider, fileResult):
    # create the own bid    
    ownBid = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.17, 14)
    
    # create a bid for the provider
    providerBid1 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.03, 10)
    providerBid2 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.06, 10)
    providerBid3 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.04, 10)
    providerBid4 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.02, 10)
    bidList = []
    bidList.append(providerBid1)
    bidList.append(providerBid2)
    bidList.append(providerBid3)
    bidList.append(providerBid4)
    
    bid_result = ispProvider.getPurchasedFront(ownBid, bidList, fileResult)
    if len(bid_result) != 2:
        raise FoundationException("error in test_get_purchased_front - Error 1")
    
    for bidId in bid_result:
        if (bidId == providerBid1.getId()):
            if ((bid_result[bidId])['Object']).getId() != bidId:
                raise FoundationException("error in test_get_purchased_front - Error 2")
            qualityValue = round(((bid_result[bidId])['QualityRequirements'])['2'],2)
            if (qualityValue != 0.14):
                raise FoundationException("error in test_get_purchased_front - Error 3")

        if (bidId == providerBid4.getId()):
            if ((bid_result[bidId])['Object']).getId() != bidId:
                raise FoundationException("error in test_get_purchased_front - Error 2")
            qualityValue = round(((bid_result[bidId])['QualityRequirements'])['2'],2)
            if (qualityValue != 0.15):
                raise FoundationException("error in test_get_purchased_front - Error 3")

def test_get_purchasable_bid( ispProvider, transitProvider, fileResult ):
    # create the own bid    
    ownBid = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.17, 14)
    dic_bids = {}    
    dic_return = ispProvider.getPurchasableBid(ownBid, dic_bids, fileResult)
    if len(dic_return) != 0:
        raise FoundationException("error in test_get_purchased_front - Error 1")
    
    dic_bids = {}    

    # create a bid for the provider
    providerBid1 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.03, 10)
    providerBid2 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.025, 10)
    providerBid3 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.028, 10)
    providerBid4 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.02, 10)
    providerBids = {}
    providerBids[providerBid1.getId()] = providerBid1
    providerBids[providerBid2.getId()] = providerBid2
    providerBids[providerBid3.getId()] = providerBid3
    providerBids[providerBid4.getId()] = providerBid4
    
    dic_bids[2] = [providerBid1, providerBid2]
    dic_bids[3] = [providerBid3, providerBid4]
    
    dic_return = ispProvider.getPurchasableBid(ownBid, dic_bids, fileResult)
    if len(dic_return) != 4:
        raise FoundationException("error in test_get_purchased_front - Error 2")
    
    for bidId in providerBids:
        if bidId not in dic_return:
            raise FoundationException("error in test_get_purchased_front - Error 3")
    
    # check the quality requirements.
    for bidId in dic_return:
        if bidId == providerBid1.getId():
            if ((dic_return[bidId])['Object']).getId() != bidId:
                raise FoundationException("error in test_get_purchased_front - Error 2")
            qualityValue = round(((dic_return[bidId])['QualityRequirements'])['2'],2)
            if (qualityValue != 0.14):
                raise FoundationException("error in test_get_purchased_front - Error 3")

        if bidId == providerBid2.getId():
            if ((dic_return[bidId])['Object']).getId() != bidId:
                raise FoundationException("error in test_get_purchased_front - Error 2")
            qualityValue = round(((dic_return[bidId])['QualityRequirements'])['2'],3)
            if (qualityValue != 0.145):
                raise FoundationException("error in test_get_purchased_front - Error 3")

        if bidId == providerBid3.getId():
            if ((dic_return[bidId])['Object']).getId() != bidId:
                raise FoundationException("error in test_get_purchased_front - Error 2")
            qualityValue = round(((dic_return[bidId])['QualityRequirements'])['2'],3)
            if (qualityValue != 0.142):
                raise FoundationException("error in test_get_purchased_front - Error 3")

        if bidId == providerBid4.getId():
            if ((dic_return[bidId])['Object']).getId() != bidId:
                raise FoundationException("error in test_get_purchased_front - Error 2")
            qualityValue = round(((dic_return[bidId])['QualityRequirements'])['2'],2)
            if (qualityValue != 0.15):
                raise FoundationException("error in test_get_purchased_front - Error 3")

def test_purchase_bid(currentPeriod, ispProvider, transitProvider, fileResult):
    # create the own bid    
    ownBid = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.17, 14)
    dic_bids = {}    

    transitProvider.send_capacity()
        
    # create a bid for the provider
    providerBid1 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.03, 11)
    sendBid(providerBid1, Bid.ACTIVE, transitProvider)

    providerBid2 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.025, 10.3)
    sendBid(providerBid2, Bid.ACTIVE, transitProvider)

    providerBid3 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.028, 10.5)
    sendBid(providerBid3, Bid.ACTIVE, transitProvider)
    
    providerBid4 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.02, 10)
    sendBid(providerBid4, Bid.ACTIVE, transitProvider)
        
    dic_bids[2] = [providerBid1, providerBid2]
    dic_bids[3] = [providerBid3, providerBid4]

    dic_return = ispProvider.getPurchasableBid(ownBid, dic_bids, fileResult)
    
    #
    # The quantity to purchase is 10 (the availability of the ISP provider) / resource requirement (1.23)   
    # This value is because to buy the most profitable bid that results from the provider's bid 
    # we need to put a bid requiring 1.23 unit of resource by every unit being sell. 
    
    # The following lines test purchasing for what we don't have enough capacity.
    totPurchased, purchasedBids = ispProvider.purchaseBid(ownBid, transitProvider.getServiceId(), 10, 30, dic_return, fileResult)

    if len(purchasedBids) != 1:
        raise FoundationException("error in test_purchase_bid - Error 1")

    val = round(totPurchased,1)
    if val != 8.1:
        logger.error('Val %s', str(val))
        raise FoundationException("error in test_purchase_bid - Error 2")

    # The following lines test purchasing for what we have enough capacity.
    resources = provider1._used_variables['resources']
    for resourceId in resources:
        provider1.updateAvailability(resourceId, 50)
        
    transitProvider.send_capacity()

    ownBid2 = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.17, 14)
    dic_return = ispProvider.getPurchasableBid(ownBid2, dic_bids, fileResult)
    totPurchased, purchasedBids = ispProvider.purchaseBid(ownBid2, transitProvider.getServiceId(), 10, 30, dic_return, fileResult)

    if len(purchasedBids) != 1:
        raise FoundationException("error in test_purchase_bid - Error 3")

    val = round(totPurchased,1)    
    if val != 10.0:
        raise FoundationException("error in test_purchase_bid - Error 4")

    # The following lines test purchasing for what we have enough capacity and provider does not have enough capacity.
    resources = provider1._used_variables['resources']
    for resourceId in resources:
        provider1.updateAvailability(resourceId, 300)

    transitProvider.send_capacity()

    ownBid3 = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.17, 14)
    dic_return = ispProvider.getPurchasableBid(ownBid3, dic_bids, fileResult)
    totPurchased, purchasedBids = ispProvider.purchaseBid(ownBid3, transitProvider.getServiceId(), 120, 30, dic_return, fileResult)

    if len(purchasedBids) != 0:
        raise FoundationException("error in test_purchase_bid - Error 5")

    val = round(totPurchased,1)    
    if val != 0:
        raise FoundationException("error in test_purchase_bid - Error 6")
        
    pass
    

def test_purchase_bids(currentPeriod, ispProvider, transitProvider, fileResult):
    # create the own bid    
    ownBid1 = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.17, 30)
    ownBid2 = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.175, 30.5)
    ownBid3 = createBid(ispProvider.getProviderId(), ispProvider.getServiceId(), 0.18, 31.0)

    transitProvider.send_capacity()

    # create a bid for the provider
    providerBid1 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.03, 11)
    sendBid(providerBid1, Bid.ACTIVE, transitProvider)

    providerBid2 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.025, 10.3)
    sendBid(providerBid2, Bid.ACTIVE, transitProvider)
    
    providerBid3 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.028, 10.5)
    sendBid(providerBid3, Bid.ACTIVE, transitProvider)
    
    providerBid4 = createBidService2(transitProvider.getProviderId(), transitProvider.getServiceId(), 0.02, 10)
    sendBid(providerBid4, Bid.ACTIVE, transitProvider)

    # set the ISP capacity enough for the first two bids.
    resources = provider1._used_variables['resources']
    for resourceId in resources:
        provider1.updateAvailability(resourceId, 40)
        
    staged_bids = {}
    staged_bids[ownBid1.getId()] = {'Object': ownBid1, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 10 }
    staged_bids[ownBid2.getId()] = {'Object': ownBid1, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 20 }
    staged_bids[ownBid3.getId()] = {'Object': ownBid1, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 15 }
    
    staged_bids = ispProvider.purchaseBids(currentPeriod, staged_bids, fileResult)
    
    if len(staged_bids) != 3:
        raise FoundationException("error in test_purchase_bids - Number staged:" + len(staged_bids) +  " - Error 1")
        
    pass

            
def test_purchase_from_previous_bids(provider1, provider2, fileResult):
    provider2.send_capacity()

    # These following lines create bids for the transit provider, so the edge provider 
    # can buy some of them.
    serviceId = provider2.getServiceId()
    quality = 0.5
    price = 14        
    BidService2_1 = createBidService2(provider2.getProviderId(), serviceId, quality, price)
    sendBid(BidService2_1, Bid.ACTIVE, provider2)

    serviceId = provider2.getServiceId()
    quality = 0.7
    price = 15        
    BidService2_2 = createBidService2(provider2.getProviderId(), serviceId, quality, price)
    sendBid(BidService2_2, Bid.ACTIVE, provider2)

    serviceId = provider2.getServiceId()
    quality = 0.8
    price = 16        
    BidService2_3 = createBidService2(provider2.getProviderId(), serviceId, quality, price)
    sendBid(BidService2_3, Bid.ACTIVE, provider2)

    serviceId = provider2.getServiceId()
    quality = 0.9
    price = 17        
    BidService2_4 = createBidService2(provider2.getProviderId(), serviceId, quality, price)
    sendBid(BidService2_4, Bid.ACTIVE, provider2)

    # test purchase function.    
    messagePurchase = provider1.createPurchaseMessage(serviceId)
    quantity = provider1.purchase( messagePurchase, serviceId, BidService2_1, 20, fileResult)
    if (quantity != 20):
        raise FoundationException("error in  test_purchase_from_previous_bids - Error:1")            
    
            

'''
The ProviderExecution starts the threads for the service provider agents.
'''    
if __name__ == '__main__':

    list_classes = {}
    # Load Provider classes
    load_classes(list_classes)
    
    # Open database connection
    db = MySQLdb.connect(foundation.agent_properties.addr_database,foundation.agent_properties.user_database, \
        foundation.agent_properties.user_password,foundation.agent_properties.database_name)
        
    db.autocommit(1)    
    
    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    # Brings the general parameters from the database
    bidPeriods, numberOffers, numAccumPeriods = getGeneralConfigurationParameters(cursor)
    
    # Verifies if they were configured, otherwise brings them from the agent properties.
    if (numberOffers == 0):
        numberOffers = foundation.agent_properties.initial_number_bids
    
    if (numAccumPeriods == 0):
        numAccumPeriods = foundation.agent_properties.num_periods_market_share

    # Prepare SQL query to SELECT providers from the database.
    sql = "SELECT id, name, market_position, adaptation_factor \
                  , monopolist_position, service_id, num_ancestors, debug \
		  , seed, year, month, day, hour, minute, second \
		  , microsecond, class_name, start_from_period, buying_marketplace_address \
          , selling_marketplace_address, capacity_controlled_at, purchase_service_id \
	     FROM simulation_provider \
	     WHERE id in (1,2)"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()
        i = 1
        for row in results:
            providerId = row[0]
            providerName = row[1]
            marketPositon = row[2] 
            adaptationFactor = row[3] 
            monopolistPosition = row[4] 
            serviceId = str(row[5])
            numAncestors = row[6]
            if (row[7] == 1):
                debug = True
            else:
                debug = False
            seed = row[8]
            year = row[9]
            month = row[10]
            day = row[11]
            hour = row[12]
            minute = row[13]
            second = row[14]
            microsecond = row[15]
            class_name = row[16]
            startFromPeriod = row[17]
            buyingAddress = row[18]
            sellingAddress = row[19]
            capacityControl = 'G' # Bulk Capacity.
            providerSeed = getSeed(seed, year, month, day, hour, minute, second, microsecond)
            purchase_service = row[21]
            # Brings resources definition
            cursor2 = db.cursor()
            sql_resources = "SELECT resource_id, capacity, cost \
        			       FROM simulation_provider_resource \
        			      WHERE provider_id = '%d'" % (providerId)
            cursor2.execute(sql_resources)
            resourceRows = cursor2.fetchall()
            resources = {}
            for resourceRow in resourceRows:
                resources[str(resourceRow[0])] = {'Capacity': resourceRow[1], 'Cost' : resourceRow[2]}
        	    
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceId, 
        			      providerSeed, marketPositon, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, 
                       buyingAddress, capacityControl, purchase_service)
            providers.append(provider)
            i = i + 1

        logger.info('Starting test providers created')
            
        # Test providers' initialization.
        provider1 = providers[0] # Edge provider
        provider2 =providers[1]  # Transit Provider
        
        fileResult1 = open(provider1.getProviderId() + '.log',"a")
        fileResult2 = open(provider1.getProviderId() + '.log',"a")
        
        test_initialization(provider1)
        test_initialization(provider2)
        test_calculate_required_quality(provider1)        
        
        logger.info('Starting test providers created - Step:1')
        
        currentPeriod = 1
        test_swap_purchased_bid(provider1, currentPeriod, fileResult1)
        test_get_related_decision_variable(provider1, provider2)        
        test_calculate_bid_unitary_cost(provider1, provider2, fileResult1)
        test_replicate_bids(provider1, provider2, fileResult1)
        test_calculate_own_quality_for_purchasable_bid( provider1, provider2, fileResult1 )
        test_get_purchased_front(provider1, provider2, fileResult1)

        logger.info('Starting test providers created - Step:1a')

        test_get_purchasable_bid(provider1, provider2, fileResult1)

        logger.info('Starting test providers created - Step:1b')

        test_purchase_bid(currentPeriod, provider1, provider2, fileResult1)

        logger.info('Starting test providers created - Step:1c')

        test_purchase_bids(currentPeriod, provider1, provider2, fileResult1)
        
        logger.info('Starting test providers created - Step:2')
        
        test_capacity_update(provider1)
        test_purchase_from_previous_bids(provider1, provider2, fileResult1)
                                     
        pass        
	
    except FoundationException as e:
        print e.__str__()
    except ProviderException as e:
        print e.__str__()
    except Exception as e:
        print e.__str__()
    finally:
        # disconnect from server
        db.close()
        provider1.stop_agent() # Edge provider
        provider2.stop_agent() # Transit Provider
        fileResult1.close()
        fileResult2.close()
