import multiprocessing
from Provider import Provider
from ProviderAgentException import ProviderException
from foundation.FoundationException import FoundationException
from foundation.AgentType import AgentType
import foundation.agent_properties
import MySQLdb
import logging
import datetime
import time
import os
import sys
import re
import inspect
from foundation.Bid import Bid
import uuid
from foundation.Agent import AgentServerHandler
from foundation.Agent import Agent
import random
from Consumer import Consumer
from costfunctions.CostFunctionFactory import CostFunctionFactory
from foundation.DecisionVariable import DecisionVariable


logger = logging.getLogger('provider_test')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('providers_test.log', mode='w')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

def isBlank (myString):
    if myString and myString.strip():
        #myString is not None AND myString is not empty or blank
        return False
    #myString is None OR myString is empty or blank
    return True

def getGeneralConfigurationParameters(cursor):
    sql = "SELECT bid_periods, initial_offer_number, \
            num_periods_market_share, execution_count \
            FROM simulation_generalparameters limit 1" 
    cursor.execute(sql)
    results = cursor.fetchall()
    for row in results:
        bidPeriods = row[0]
        numberOffers = row[1]
        numAccumPeriods = row[2]
        executionCount = row[3]
        break
    return bidPeriods, numberOffers, numAccumPeriods, executionCount

def getDecisionVariable(db, executionCount, bidId, decisionVariable):
    cursor = db.cursor() 
    value = 0
    sql =  'select distinct value \
              from simulation_bid_decision_variable a \
             where a.execution_count = %s\
               and a.parentId = %s \
               and a.decisionVariableName = %s'
    cursor.execute(sql, (executionCount, bidId, decisionVariable))
    results = cursor.fetchall()
    for row in results:
        value = float(row[0])
        break
    return value

def createBid(db, executionCount, bidId, strProv, service, period, unitary_cost, unitary_profit, capacity ):
    bid = Bid()
    bid.setValues(bidId, strProv, service.getId())
    bid.setStatus(Bid.ACTIVE)
    bid.setUnitaryProfit(unitary_profit)
    bid.setUnitaryCost(unitary_cost)
    bid.setCreationPeriod(period)
    bid.setCapacity(capacity)
    for decisionVariable in (service)._decision_variables:
        value = getDecisionVariable(db, executionCount, bidId, decisionVariable)
        bid.setDecisionVariable(decisionVariable, value)
    return bid

def bringParentBid(db, executionCount, strProv, service, bidId):
    logger.info('Starting bringParentBid + executionCount:' + str(executionCount) + 'provider:' + str(strProv) + 'BidId:' + bidId)
    cursor = db.cursor() 
    sql =  'select a.period, a.providerId, a.bidId, a.unitary_profit, \
                a.parentBidId, a.unitary_cost, a.init_capacity \
            from simulation_bid a \
            where a.execution_count = %s \
              and a.status = %s \
              and a.providerId  = %s \
              and a.bidId = %s'
    cursor.execute(sql, (executionCount, '1', strProv, bidId))
    results = cursor.fetchall()
    found = False
    for row in results:
        period = int(row[0]) 
        providerId = row[1]
        bidId = row[2]
        unitary_profit = float(row[3])
        parentBidId = row[4]
        unitary_cost = row[5]
        init_capacity = float(row[6])
        found = True
        break

    if found == True:
        bid = createBid(db, executionCount, bidId, providerId, service, period, unitary_cost, unitary_profit, init_capacity)
        return bid, parentBidId
    else:
        return None

def bringBidFromPeriod(db, executionCount, strProv, service, period):
    logger.info('Starting bringBidFromPeriod + executionCount:' + str(executionCount) + 'Period:' + str(period) + 'provider:' + str(strProv))
    listBids = {}
    cursor = db.cursor() 
    sql =  'select a.period, a.providerId, a.bidId, a.unitary_profit, \
                a.parentBidId, a.unitary_cost, a.init_capacity \
            from simulation_bid a \
            where a.execution_count = %s \
              and a.status = %s \
              and a.providerId  = %s \
              and a.period = %s\
            order by a.period'
    cursor.execute(sql, (executionCount, '1', strProv, period))
    results = cursor.fetchall()
    for row in results:
        period = int(row[0]) 
        providerId = row[1]
        bidId = row[2]
        unitary_profit = float(row[3])
        parentBidId = row[4]
        unitary_cost = row[5]
        init_capacity = float(row[6])
        bid = createBid(db, executionCount, bidId, providerId, service, period, unitary_cost, unitary_profit, init_capacity )
        print bid.__str__()
        if isBlank(parentBidId):
            pass
        else:
            count = 0
            if isBlank(parentBidId):
                pass
            else:
                #This function return the bid object as well as the id of the parent of that bid.
                listParents = []
                while (isBlank(parentBidId) == False):
                    bidParent, parentBidId = bringParentBid(db, executionCount, strProv, service, parentBidId)
                    listParents.append(bidParent)

            parent = None
            numPrecessesors = 1
            for bidTmp in reversed(listParents):
                bidTmp.insertParentBid(parent)
                bidTmp.setNumberPredecessor(numPrecessesors)
                parent = bidTmp
                numPrecessesors = numPrecessesors + 1

            if (parent != None):
                bid.insertParentBid(parent)
                bid.setNumberPredecessor(numPrecessesors)

            bidTmp = bid 
            while (bidTmp != None):
                if (bidTmp.getParentBid() != None):
                    logger.info('bibId:' + bidTmp.getId() + ':parentBidId:' + bidTmp.getParentBid().getId() + ':predecessors:' + str(bidTmp.getNumberPredecessor()) )
                else:
                    logger.info('bibId:' + bidTmp.getId() + ':parentBidId:' + 'None' + ':predecessors:' + str(bidTmp.getNumberPredecessor()) )
                bidTmp = bidTmp.getParentBid()

            listBids[bidId] = bid
    logger.info('Ending bringBidFromPeriod + numCreated' + str(len(listBids)))
    return listBids

def bringOtherProviderBids(db, executionCount, strProv, service, period):
    logger.info('Starting bringOtherProviderBids + executionCount:' + str(executionCount) + 'Period:' + str(period) + 'provider:' + str(strProv))
    listBids = {}
    cursor = db.cursor() 
    sql =  'select a.period, a.providerId, a.bidId, a.unitary_profit, \
                a.parentBidId, a.unitary_cost, a.init_capacity \
            from simulation_bid a \
            where a.execution_count = %s \
              and a.status = %s \
              and a.providerId in (select concat(name,id) from simulation_provider where service_id = %s ) \
              and a.providerId <> %s \
              and a.period = %s\
            order by a.period'
    cursor.execute(sql, (executionCount, '1', service.getId(), strProv, period))
    results = cursor.fetchall()
    for row in results:
        period = int(row[0]) 
        providerId = row[1]
        bidId = row[2]
        unitary_profit = float(row[3])
        parentBidId = row[4]
        unitary_cost = row[5]
        init_capacity = float(row[6])
        bid = createBid(db, executionCount, bidId, providerId, service, period, unitary_cost, unitary_profit, init_capacity )
        listBids[bidId] = bid
    logger.info('Ending bringOtherProviderBids + numCreated' + str(len(listBids)))
    return listBids

def getSeed(seed, year, month, day, hour, minute, second, microsecond):
    if (seed == 1):
            # the seed for random numbers was defined, therefore we use it.
            dtime = datetime.datetime(year,month,day,hour,minute,second,microsecond)
    else:
        dtime = datetime.datetime.now()     
    return dtime

def create(list_classes, typ, providerName, providerId, serviceId, providerSeed, marketPositon, 
        adaptationFactor, monopolistPosition, debug, 
        resources, numberOffers, numAccumPeriods, numAncestors, startFromPeriod,
        sellingAddress, buyingAddress, capacityControl, purchase_service ):

    if typ in list_classes:
            targetClass = list_classes[typ]
            return targetClass(providerName, providerId, serviceId, providerSeed, 
                       marketPositon, adaptationFactor, monopolistPosition, 
                       debug, resources, numberOffers, numAccumPeriods, 
                       numAncestors, startFromPeriod, sellingAddress, 
                    buyingAddress, capacityControl, str(purchase_service))
    else:
        err = 'Class' + typ + 'not found to be loaded'
        raise ProviderException(err)

def updateExecutionCount(cursor, executionCount):
    sql = 'update simulation_generalparameters \
              set execution_count = %s \
            where id = %s'
    cursor.execute(sql, (executionCount, '1'))


def load_classes(list_classes):
    currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    sys.path.append(currentdir)
    agents_directory = currentdir
    black_list = ['ProviderExecution', 'ProviderAgentException', 'ProviderExecutionTest', 'ProviderEdgeTest', 'ProviderPublicTest']
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

def test_moveForMarketShare_on_previous_execution(executionCount, providerId, replayPeriod):
    list_classes = {}
    # Load Provider classes
    load_classes(list_classes)
    
    logger.info('Starting test_integrated_classes')
    
    # Open database connection
    db = MySQLdb.connect(foundation.agent_properties.addr_database,foundation.agent_properties.user_database, \
        foundation.agent_properties.user_password,foundation.agent_properties.database_name )
    
    db.autocommit(1)    
    
    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    # Brings the general parameters from the database
    bidPeriods, numberOffers, numAccumPeriods, newExecutionCount = getGeneralConfigurationParameters(cursor)
    
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
	    WHERE status = 'A' \
	      and id = %s"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql, (providerId))
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()

        adaptationFactor = 0
        monopolistPosition = 0
        marketPosition = 0

        i = 1
        for row in results:
            providerId = row[0]
            providerName = row[1]
            marketPosition = row[2] 
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
            capacityControl = row[20]
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
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, 
                       buyingAddress, capacityControl, purchase_service)
            providers.append(provider)
            i = i + 1
            break 

        logger.info('Number of providers open: %d', len(providers) )
        
        # set the execution count equals to that one of being reinitiated.
        updateExecutionCount(cursor, executionCount)
        
        w = providers[0]
        w.start_agent()
        w.initialize()
        fileResult = open(w.getProviderId() + '_replay.log',"w")
        w._list_vars['State'] == AgentServerHandler.BID_PERMITED
        radius = foundation.agent_properties.own_neighbor_radius
        staged_bids = {}
        listBids = bringBidFromPeriod(db, executionCount, w.getProviderId(), w._service,replayPeriod - 1)
        listBidProviders = bringOtherProviderBids(db, executionCount, w.getProviderId(), w._service,replayPeriod - 1)
        w._list_vars['Bids'] = listBids
        w._list_vars['Related_Bids'] = listBidProviders
        w.moveForMarketShare(replayPeriod, radius, staged_bids, fileResult)
        for bidId in staged_bids:
            forecast = (staged_bids[bidId])['Forecast']
            action = (staged_bids[bidId])['Action']
            w.registerLog(fileResult,"BidId:" + bidId + "Forecast:" + str(forecast) + "Action:" + str(action) )
        
        # Go back to the current execution count.
        updateExecutionCount(cursor, newExecutionCount)
         
        logger.info('Ending Provider Reexecution Test')
        
    except FoundationException as e:
        print e.__str__()
    except ProviderException as e:
        print e.__str__()
    except Exception as e:
        print e.__str__()
    finally:
        # disconnect from server
        db.close()
        w.stop_agent()


test_moveForMarketShare_on_previous_execution(1987, 5, 28)