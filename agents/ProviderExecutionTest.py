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
fh = logging.FileHandler('providers_test.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

def createBid(strProv, serviceId, delay, price):
    bid = Bid()
    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
    idStr = str(uuidId)
    bid.setValues(idStr, strProv, serviceId)
    bid.setDecisionVariable("1", price)  #Price
    bid.setDecisionVariable("2", delay)     # Delay
    bid.setStatus(Bid.ACTIVE)
    return bid

def createBidBackhaul(strProv, serviceId, delay, price):
    bid = Bid()
    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
    idStr = str(uuidId)
    bid.setValues(idStr, strProv, serviceId)
    bid.setDecisionVariable("4", price)  #Price
    bid.setDecisionVariable("3", delay)     # Delay
    bid.setStatus(Bid.ACTIVE)
    return bid


def createBidWithCapacity(strProv, serviceId, delay, price, capacity):
    bid = Bid()
    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
    idStr = str(uuidId)
    bid.setValues(idStr, strProv, serviceId)
    bid.setDecisionVariable("4", price)  #Price
    bid.setDecisionVariable("3", delay)     # Delay
    bid.setStatus(Bid.ACTIVE)
    bid.setCapacity(capacity)
    return bid
    
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
            status, paretoStatus,dominatedCount, execution_count, unitary_profit, unitary_cost, capacity) \
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"    
    args = (period, bid.getId(), bid.getProvider(), 1, 0, 0, executionCount, bid.getUnitaryProfit(), bid.getUnitaryCost(), bid.getCapacity())
    cursor.execute(sql, args )

def insertDBBidPurchase(cursor, period, serviceId, executionCount, bid, quantity):
    sql = "insert into Network_Simulation.simulation_bid_purchases(period, \
            serviceId,bidId,quantity, execution_count) values (%s, %s, %s, %s, %s )"    
    args = (period, serviceId, bid.getId(), quantity, executionCount )
    cursor.execute(sql, args )

def insertDBDemandInformation(cursor, provider):
    '''
    This function insert bid history demand and include it in variables of the provider
    '''
    # variable initialization
    serviceIdISP = '1'    
    executionCount = getExecutionCount(cursor)
    
    delay = 0.19	
    price = 14.5	
    demand = 12
    bid4_5 = createBid(provider.getProviderId(), serviceIdISP, delay, price)
    bid4_5.setUnitaryProfit(0.2)
    bid4_5.setCreationPeriod(10)
    insertDBBid(cursor, 10, executionCount, bid4_5)
    insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_5, demand+4)        
    insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_5, demand+2)        
    insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_5, demand)        
    (provider._list_vars['Bids'])[bid4_5.getId()] = bid4_5
        
    delay = 0.19	
    price = 15
    demand = 11
    bid4_6 = createBid(provider.getProviderId(), serviceIdISP, delay, price)
    bid4_6.setUnitaryProfit(0.2)
    bid4_6.setCreationPeriod(10)
    insertDBBid(cursor, 10, executionCount, bid4_6)
    insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_6, demand+4)        
    insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_6, demand+2)        
    insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_6, demand)        
    (provider._list_vars['Bids'])[bid4_6.getId()] = bid4_6
        
        
    delay = 0.19	
    price = 15.5	
    demand = 10
    bid4_7 = createBid(provider.getProviderId(), serviceIdISP, delay, price)
    bid4_7.setUnitaryProfit(0.2)
    bid4_7.setCreationPeriod(10)
    insertDBBid(cursor, 10, executionCount, bid4_7)
    insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_7, demand+4)        
    insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_7, demand+2)        
    insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_7, demand+0)        
    (provider._list_vars['Bids'])[bid4_7.getId()] = bid4_7
    
        
    delay = 0.18	
    price = 13.5	
    demand = 15
    bid4_8 = createBid(provider.getProviderId(), serviceIdISP, delay, price)
    bid4_8.setUnitaryProfit(0.2)
    bid4_8.setCreationPeriod(10)
    insertDBBid(cursor, 10, executionCount, bid4_8)
    insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_8, demand+4)        
    insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_8, demand+2)        
    insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_8, demand+0)        
    (provider._list_vars['Bids'])[bid4_8.getId()] = bid4_8
    

    delay = 0.18	
    price = 14	
    demand = 14
    bid4_9 = createBid(provider.getProviderId(), serviceIdISP, delay, price)
    bid4_9.setUnitaryProfit(0.2)
    bid4_9.setCreationPeriod(10)
    insertDBBid(cursor, 10, executionCount, bid4_9)
    insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_9, demand+4)        
    insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_9, demand+2)        
    insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_9, demand+0)        
    (provider._list_vars['Bids'])[bid4_9.getId()] = bid4_9
        
    delay = 0.18	
    price = 14.5	
    demand = 13
    bid4_10 = createBid(provider.getProviderId(), serviceIdISP, delay, price)
    bid4_10.setUnitaryProfit(0.2)
    bid4_10.setCreationPeriod(10)
    insertDBBid(cursor, 10, executionCount, bid4_10)
    insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_10, demand+4)        
    insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_10, demand+2)        
    insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_10, demand+0)        
    (provider._list_vars['Bids'])[bid4_10.getId()] = bid4_10
    
    delay = 0.18	
    price = 15	
    demand = 12
    bid4_11 = createBid(provider.getProviderId(), serviceIdISP, delay, price)
    bid4_11.setUnitaryProfit(0.2)
    bid4_11.setCreationPeriod(10)
    insertDBBid(cursor, 10, executionCount, bid4_11)
    insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_11, demand+4)        
    insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_11, demand+2)        
    insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_11, demand+0)        
    (provider._list_vars['Bids'])[bid4_11.getId()] = bid4_11
        
    delay = 0.18	
    price = 15.5	
    demand = 11
    bid4_12 = createBid(provider.getProviderId(), serviceIdISP, delay, price)
    bid4_12.setUnitaryProfit(0.2)
    bid4_12.setCreationPeriod(10)
    insertDBBid(cursor, 10, executionCount, bid4_12)
    insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_12, demand+4)        
    insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_12, demand+2)        
    insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_12, demand+0)        
    (provider._list_vars['Bids'])[bid4_12.getId()] = bid4_12
    
    delay = 0.18	
    price = 16	
    demand = 10
    bid4_13 = createBid(provider.getProviderId(), serviceIdISP, delay, price)
    bid4_13.setUnitaryProfit(0.2)
    bid4_13.setCreationPeriod(10)
    insertDBBid(cursor, 10, executionCount, bid4_13)
    insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_13, demand+4)        
    insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_13, demand+2)        
    insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_13, demand+0)        
    (provider._list_vars['Bids'])[bid4_13.getId()] = bid4_13
        
    delay = 0.18	
    price = 16.5	
    demand = 9
    bid4_14 = createBid(provider.getProviderId(), serviceIdISP, delay, price)
    bid4_14.setUnitaryProfit(0.2)
    bid4_14.setCreationPeriod(10)
    insertDBBid(cursor, 10, executionCount, bid4_14)
    insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_14, demand+4)        
    insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_14, demand+2)        
    insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_14, demand+0)        
    (provider._list_vars['Bids'])[bid4_14.getId()] = bid4_14
    
    delay = 0.17	
    price = 14.5	
    demand = 14
    bid4_15 = createBid(provider.getProviderId(), serviceIdISP, delay, price)
    bid4_15.setUnitaryProfit(0.2)
    bid4_15.setCreationPeriod(10)
    insertDBBid(cursor, 10, executionCount, bid4_15)
    insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_15, demand+4)        
    insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_15, demand+2)        
    insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_15, demand+0)        
    (provider._list_vars['Bids'])[bid4_15.getId()] = bid4_15
    
    delay = 0.17	
    price = 15	
    demand = 13
    bid4_16 = createBid(provider.getProviderId(), serviceIdISP, delay, price)
    bid4_16.setUnitaryProfit(0.2)
    bid4_16.setCreationPeriod(10)
    insertDBBid(cursor, 10, executionCount, bid4_16)
    insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_16, demand+4)        
    insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_16, demand+2)
    insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_16, demand+0)        
    (provider._list_vars['Bids'])[bid4_16.getId()] = bid4_16
        
    delay = 0.17	
    price = 15.5	
    demand = 12
    bid4_17 = createBid(provider.getProviderId(), serviceIdISP, delay, price)
    bid4_17.setUnitaryProfit(0.2)
    bid4_17.setCreationPeriod(10)
    insertDBBid(cursor, 10, executionCount, bid4_17)
    insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_17, demand+4)
    insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_17, demand+2)
    insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_17, demand+0)
    (provider._list_vars['Bids'])[bid4_17.getId()] = bid4_17
    

def activateCustomer():

    # this method only activates a consumer.
    logger.info('Starting activateCustomer')

    # Open database connection
    db = MySQLdb.connect(foundation.agent_properties.addr_database,foundation.agent_properties.user_database, \
        foundation.agent_properties.user_password,foundation.agent_properties.database_name)

    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    # Brings the general parameters from the database
    bidPeriods, numberOffers, numAccumPeriods = getGeneralConfigurationParameters(cursor)

    # Prepare SQL query to SELECT customers from the database.
    sql = "select a.number_execute, b.service_id, a.seed, a.year, a.month, a.day, \
		  a.hour, a.minute, a.second, a.microsecond \
	   from simulation_consumer a, simulation_consumerservice b \
	  where a.id = b.consumer_id \
	    and b.execute = 1 \
	    LIMIT 1"
     
    try:
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()
        num_consumers = 0
        i = 20 # the first customer start with id 20, so we left 19 numbers for providers.
        for row in results:
            serviceId = str(row[1])
            seed = row[2]
            year = row[3]
            month = row[4]
            day = row[5]
            hour = row[6]
            minute = row[7]
            second = row[8]
            microsecond = row[9]
            seed = getSeed(seed, year, month, day, hour, minute, second, microsecond)
            # Start consumers
            logger.info('Creating %d consumers' % num_consumers)
            logger.info('seed:' + str(seed))
            # Creating aleatory numbers for the customers.
            consumers = []
            customer_seed = random.randint(0, 1000 * num_consumers)
            logger.info('customer seed:'+ str(customer_seed))
            consumer = Consumer("agent" + str(i), i, serviceId, customer_seed)
            consumer.start_agent()
            consumers.append(consumer)
            num_consumers = num_consumers + 1
            break

        logger.info('After activateCustomer')

        if num_consumers > 0:
            return consumers[0]
        else:
            return None

    except ProviderException as e:
        print e.__str__()
    except Exception as e:
        print e.__str__()

    finally:
        # disconnect from server
        db.close()


def test_cost_functions():

    logger.info('Starting test_cost_functions')

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
	    WHERE id = 1"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()

        serviceIdBackhaul = '2'
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
            
            capacityControl = 'G' # Bulk Capacity.
            class_name = 'Provider'
            sellingAddress = foundation.agent_properties.addr_mktplace_backhaul
            buyingAddress = ' '
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceIdBackhaul, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, 
                       capacityControl, purchase_service)
            providers.append(provider)
            break
        
        # The following code test the cost functions execution.
        factory = CostFunctionFactory.Instance()
        linealCost = factory.create('LinealCost')
        NaturalLogarithmCost = factory.create('NaturalLogarithmCost')
        QuadraticCost = factory.create('QuadraticCost')
        
        linealCost.setParameter('intercept', 2)
        linealCost.setParameter('slope', 3)
        value = linealCost.getEvaluation(3)
        if (value != 11.0):
            raise FoundationException("error in the evaluation of lineal cost object")

        NaturalLogarithmCost.setParameter('a', 2)
        NaturalLogarithmCost.setParameter('b', 3)
        value = NaturalLogarithmCost.getEvaluation(3)
        value = round(value,4)
        if (value != 5.7726):
            raise FoundationException("error in the evaluation of NaturalLogarithmCost object")

        QuadraticCost.setParameter('a', 2)
        QuadraticCost.setParameter('b', 3)
        QuadraticCost.setParameter('c', 4)
        value = QuadraticCost.getEvaluation(3)
        if (value != 31.0):
            raise FoundationException("error in the evaluation of QuadraticCost object")
        
        
        # start the providers
        provider1 = providers[0]  # backhaul provider - Bulk capacity.
        provider1.start_agent()
        
        # This code test that test the integration functions between clock server and agent.
        # The code assume that service serviceIdBackhaul has as quality variable bandwidth quality
        # as that variable has as cost function a lineal cost function.
        provider1.getServiceFromServer(serviceIdBackhaul)
        
        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                decisionVar = (provider1._service)._decision_variables[decisionVariable]
                if (decisionVar.getCostFunction() != None):
                    costFun = decisionVar.getCostFunction()
                    costFun2  = factory.create(costFun.getName())
                    if (costFun.getParameters() != costFun2.getParameters()):
                        raise FoundationException("error in the the cost function integration")
                    
        provider1.stop_agent()
        logger.info('ending test_cost_functions')
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
            

    
def test_marketplace_capacity_management():

    logger.info('Starting test_marketplace_capacity_management')

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
	    WHERE id = 1"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()

        serviceIdISP = '1'            
        serviceIdBackhaul = '2'
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
            
            capacityControl = 'G' # Bulk Capacity.
            class_name = 'Provider'
            providerId = i
            providerName = 'Provider' + str(providerId)
            sellingAddress = foundation.agent_properties.addr_mktplace_backhaul
            buyingAddress = ' '
            provider = create( list_classes, class_name, providerName + str(providerId), providerId, serviceIdBackhaul, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, 
                      buyingAddress, capacityControl, purchase_service )
            providers.append(provider)

            logger.info('first provider created')
            
            i = i + 1

            capacityControl = 'B' # Capacity by Bid.
            class_name = 'ProviderEdge'
            providerId = i
            providerName = 'Provider' + str(providerId)
            sellingAddress = foundation.agent_properties.addr_mktplace_isp
            buyingAddress = foundation.agent_properties.addr_mktplace_backhaul
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceIdISP, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
                          numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl, purchase_service)
            providers.append(provider)
            i = i + 1
            
            logger.info('second provider created')

            capacityControl = 'B' # Capacity by Bid.
            class_name = 'Provider'
            providerId = i
            providerName = 'Provider' + str(providerId)
            sellingAddress = foundation.agent_properties.addr_mktplace_backhaul
            buyingAddress = ' '
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceIdBackhaul, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
                          numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl, purchase_service)
            providers.append(provider)
            i = i + 1

            logger.info('third provider created')

            break

        # start the providers
        provider1 = providers[0]  # backhaul provider - Bulk capacity.
        provider2 = providers[1]  # isp provider
        provider3 = providers[2]  # backhaul provider - Bid capacity.

        provider1.start_agent()
        provider1.initialize()
        provider2.start_agent()
        provider2.initialize()
        provider3.start_agent()
        provider3.initialize()

        
        # This code verifies the Market Place Server with BulkCapacity
        # send capacity 10 units
        provider1.send_capacity()
        
        # Variable Initialization        
        serviceId = '2'
        fileResult1 = open(provider1.getProviderId() + '.log',"a")
        currentPeriod = provider2.getCurrentPeriod()
        
        # creates the bid with the minimal quality.                
        quality = 0
        price = 10
        bid = createBidBackhaul(provider1.getProviderId(), serviceId, quality, price)
        bid.setCreationPeriod(1)
        provider1.sendBid(bid, fileResult1)
        
        # Buy with minimum quality 3 units - Response 3 units purchased, provider2 acts as the customer.
        fileResult2 = open(provider2.getProviderId() + '.log',"a")        
        messagePurchase1 = provider2.createPurchaseMessage(serviceId)
        quantity = provider2.purchase(messagePurchase1, serviceId, bid, 3, fileResult2)
                             
        if (quantity != 3):
            raise FoundationException("error in the purchase function")
            
        # Buy with minimum quality 4 units - Response 4 units purchased
        messagePurchase2 = provider2.createPurchaseMessage(serviceId)
        quantity = provider2.purchase(messagePurchase2, serviceId, bid, 4, fileResult2)
        if (quantity != 4):
            raise FoundationException("error in the purchase function")

        # Buy with minimum quality 2 units - Response 2 units purchased
        messagePurchase3 = provider2.createPurchaseMessage(serviceId)
        quantity = provider2.purchase(messagePurchase3, serviceId, bid, 2, fileResult2)
        if (quantity != 2):
            raise FoundationException("error in the purchase function")

        # Buy with minimum quality 2 units - Response 0 units purchased
        messagePurchase4 = provider2.createPurchaseMessage(serviceId)
        quantity = provider2.purchase(messagePurchase4, serviceId, bid, 2, fileResult2)
        if (quantity != 0):
            raise FoundationException("error in the purchase function")

        # ------------
        # This code verifies the Market Place Server with BidCapacity, provider2 acts as the customer.
        # ------------

        # Variable Initialization        
        serviceId = '2'
        fileResult3 = open(provider3.getProviderId() + '.log',"a")
        currentPeriod = provider3.getCurrentPeriod()
        
        # Creates bids with the minimal quality.                
        quality = 0
        price = 10
        bid2 = createBidWithCapacity(provider3.getProviderId(), serviceId, quality, price, 10)
        bid2.setCreationPeriod(1)
        bid3 = createBidWithCapacity(provider3.getProviderId(), serviceId, quality, price, 5)
        bid3.setCreationPeriod(1)
        provider3.sendBid(bid2, fileResult3)
        provider3.sendBid(bid3, fileResult3)
        
        # Buy with minimum quality 5 units - Response 5 units purchased
        messagePurchase5 = provider2.createPurchaseMessage(serviceId)
        quantity = provider2.purchase(messagePurchase5, serviceId, bid2, 5, fileResult2)
        if (quantity != 5):
            raise FoundationException("error in the purchase function")
            
        # Buy with minimum quality 4 units - Response 5 units purchased
        messagePurchase6 = provider2.createPurchaseMessage(serviceId)
        quantity = provider2.purchase(messagePurchase6, serviceId, bid2, 6, fileResult2)
        if (quantity != 5):
            raise FoundationException("error in the purchase function")

        # Buy with minimum quality 2 units - Response 2 units purchased
        messagePurchase7 = provider2.createPurchaseMessage(serviceId)
        quantity = provider2.purchase(messagePurchase7, serviceId, bid3, 2, fileResult2)
        if (quantity != 2):
            raise FoundationException("error in the purchase function")

        # Buy with minimum quality 2 units - Response 2 units purchased
        messagePurchase8 = provider2.createPurchaseMessage(serviceId)
        quantity = provider2.purchase(messagePurchase8, serviceId, bid3, 2, fileResult2)
        if (quantity != 2):
            raise FoundationException("error in the purchase function")

        # Buy with minimum quality 2 units - Response 1 units purchased
        messagePurchase9 = provider2.createPurchaseMessage(serviceId)
        quantity = provider2.purchase(messagePurchase9, serviceId, bid3, 5, fileResult2)
        if (quantity != 1):
            raise FoundationException("error in the purchase function")
        
        # -----------------------------------        
        # This code test the backlog update for bids in the market place for 
        # bulk capacity control providers.
        # -----------------------------------
        
        # create four bids for provider 1 - bulk capacity test.
        quality = 1
        price = 11
        bid_2 = createBidBackhaul(provider1.getProviderId(), serviceId, quality, price)
        bid_2.setCreationPeriod(1)
        provider1.sendBid(bid_2, fileResult1)

        quality = 2
        price = 13
        bid_3 = createBidBackhaul(provider1.getProviderId(), serviceId, quality, price)
        bid_3.setCreationPeriod(1)
        provider1.sendBid(bid_3, fileResult1)

        quality = 2
        price = 13
        bid_4 = createBidBackhaul(provider1.getProviderId(), serviceId, quality, price)
        bid_4.setCreationPeriod(1)
        provider1.sendBid(bid_4, fileResult1)

        quality = 2
        price = 13
        bid_5 = createBidBackhaul(provider1.getProviderId(), serviceId, quality, price)
        bid_5.setCreationPeriod(1)
        provider1.sendBid(bid_5, fileResult1)

        #--------------------------------------------
        # create a purchase for bid2, backlog should go to this bid. 
        #--------------------------------------------
        messagePurchase10 = provider2.createPurchaseMessage(serviceId)
        quantity = provider2.purchase(messagePurchase10, serviceId, bid_2, 150, fileResult2)
                             
        if (quantity != 0):
            raise FoundationException("error in the purchase function")
        
        quantity = provider2.purchase(messagePurchase10, serviceId, bid_2, 3, fileResult2)
        
        # -----------------------------------        
        # This code test the backlog update for bids in the market place for 
        # bid capacity control providers.
        # -----------------------------------
        
        customer = activateCustomer()
        if customer != None:
            customer.initialize()
            delay = 0.14 
            price = 20
            bidIsp_1 = createBid(provider2.getProviderId(), serviceIdISP, delay, price)
            bidIsp_1.setCapacity(5)
            provider2.sendBid(bidIsp_1, fileResult2)
            
            delay = 0.15
            price = 19
            bidIsp_2 = createBid(provider2.getProviderId(), serviceIdISP, delay, price)
            bidIsp_2.setCapacity(5)
            provider2.sendBid(bidIsp_2, fileResult2)
            
            delay =  0.16
            price = 18
            bidIsp_3 = createBid(provider2.getProviderId(), serviceIdISP, delay, price)
            bidIsp_3.setCapacity(5)
            provider2.sendBid(bidIsp_3, fileResult2)
            
            delay = 0.17
            price = 17
            bidIsp_4 = createBid(provider2.getProviderId(), serviceIdISP, delay, price)
            bidIsp_4.setCapacity(5)
            provider2.sendBid(bidIsp_4, fileResult2)
            
            messagePurchase11 = customer.createPurchaseMessage()
            quantity = 8
            quantityPur = customer.purchase( messagePurchase11, bidIsp_1, quantity)
            quantityPur = quantityPur + customer.purchase( messagePurchase11, bidIsp_2, quantity - quantityPur)
            quantityPur = quantityPur + customer.purchase( messagePurchase11, bidIsp_3, quantity - quantityPur)
            quantityPur = quantityPur + customer.purchase( messagePurchase11, bidIsp_4, quantity - quantityPur)
           
        
        logger.info('ending test_marketplace_capacity_management')
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
        fileResult1.close()
        fileResult2.close()
        provider1.stop_agent()
        provider2.stop_agent()
        provider3.stop_agent()
        customer.stop_agent()

def test_provider_general_methods():

    logger.info('Starting test_provider_general_methods')

    list_classes = {}
    # Load Provider classes
    load_classes(list_classes)
    
    # Open database connection
    db = MySQLdb.connect(foundation.agent_properties.addr_database,foundation.agent_properties.user_database, \
        foundation.agent_properties.user_password,foundation.agent_properties.database_name )
    
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
	    WHERE id = 1"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()

        serviceId = '1'            
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
            
            capacityControl = 'G' # Bulk Capacity.
            class_name = 'Provider'
            sellingAddress = foundation.agent_properties.addr_mktplace_backhaul
            buyingAddress = ' '
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceId, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, 
                        buyingAddress, capacityControl, purchase_service)
            providers.append(provider)

            i = i + 1

        # start the providers
        provider1 = providers[0]  # backhaul provider - Bulk capacity.
        provider1.start_agent()
        fileResult1 = open(provider1.getProviderId() + '.log',"a")
    
        # This code test the method calculateDeltaProfitProgression
        progression = []
        progression.append({'bid' :None, 'profit' : 10, 'delta_profit' : 0 })
        progression.append({'bid' :None, 'profit' : 9, 'delta_profit' : 0 })
        progression.append({'bid' :None, 'profit' : 8, 'delta_profit' : 0 })
        progression.append({'bid' :None, 'profit' : 7, 'delta_profit' : 0 })
        progression.append({'bid' :None, 'profit' : 6, 'delta_profit' : 0 })
        progression.append({'bid' :None, 'profit' : 5, 'delta_profit' : 0 })
        provider1.calculateDeltaProfitProgression(progression)
        i = 0
        while (i < (len(progression) - 1)):
            if (progression[i])['delta_profit'] != 1:
                raise FoundationException("error in method calculateDeltaProfitProgression")
            i = i + 1

        # This code test the method moving average
        progression2 = []
        progression2.append({'bid' :None, 'profit' : 17, 'delta_profit' : 0 })
        progression2.append({'bid' :None, 'profit' : 12, 'delta_profit' : 0 })
        progression2.append({'bid' :None, 'profit' : 8, 'delta_profit' : 0 })
        progression2.append({'bid' :None, 'profit' : 4, 'delta_profit' : 0 })
        progression2.append({'bid' :None, 'profit' : 2, 'delta_profit' : 0 })
        progression2.append({'bid' :None, 'profit' : -1, 'delta_profit' : 0 })
        provider1.calculateDeltaProfitProgression(progression2)
        estimate = provider1.movingAverage(progression2)
        if round(estimate,2) != 4.47:
            raise FoundationException("error in method movingAverage")

        progression3 = []
        progression3.append({'bid' :None, 'profit' : 17, 'delta_profit' : 0 })
        provider1.calculateDeltaProfitProgression(progression3)
        if (progression3[0])['delta_profit'] != 17:
            raise FoundationException("error in method calculateDeltaProfitProgression")
        
        estimate = provider1.movingAverage(progression3)
        if estimate != 17:
            raise FoundationException("error in method movingAverage")
        
        progression4 = []
        provider1.calculateDeltaProfitProgression(progression4)
        estimate = provider1.movingAverage(progression4)
        if estimate != 0:
            raise FoundationException("error in method movingAverage")
        

        radius = 0.1        
        delay = 0.18
        price = 15
        bid = createBid( provider1.getProviderId(), serviceId, delay, price)

        # Verifies method bids are Neighborhood Bids
        delay = 0.17
        price = 14.5
        bid6 = createBid( provider1.getProviderId(), serviceId, delay, price)
        valReturn = provider1.areNeighborhoodBids(radius, bid, bid6, fileResult1)
        if (valReturn != True):
            raise FoundationException("Bids are not close")
        
        delay = 0.18
        price = 18
        bid7 = createBid( provider1.getProviderId(), serviceId, delay, price)
        valReturn = provider1.areNeighborhoodBids(radius, bid, bid7, fileResult1)
        if (valReturn != False):
            raise FoundationException("Bids are not close")
        
        deleteDBPreviousInformation(cursor)
        
        provider1.stop_agent()
        logger.info('Ending test_provider_general_methods')

    
    except FoundationException as e:
        print e.__str__()
    except ProviderException as e:
        print e.__str__()
    except Exception as e:
        print e.__str__()
    finally:
        	# disconnect from server
            fileResult1.close()
            db.close()

def test_replace_dominated_bids(cursor, executionCount, provider2, fileResult2):

    serviceId = '1'
    delay = 0.16
    price = 16

    # bid to compare 1
    bid_1_0 = createBid( provider2.getProviderId(), serviceId, delay, price)
    bid_1_0.setCreationPeriod(8)
    bid_1_0.setId('bid_replace_1_0')
    insertDBBid(cursor, 8, executionCount, bid_1_0)
    insertDBBidPurchase(cursor, 8, serviceId, executionCount, bid_1_0, 4)

    bid_1_1 = createBid( provider2.getProviderId(), serviceId, delay, price)
    bid_1_1.setCreationPeriod(9)
    bid_1_1.insertParentBid(bid_1_0)
    bid_1_1.setId('bid_replace_1_1')
    insertDBBid(cursor, 9, executionCount, bid_1_1)
    insertDBBidPurchase(cursor, 9, serviceId, executionCount, bid_1_1, 5)

    bid_1_2 = createBid( provider2.getProviderId(), serviceId, delay, price)
    bid_1_2.setCreationPeriod(10)
    bid_1_2.insertParentBid(bid_1_1)
    bid_1_2.setId('bid_replace_1_2')
    insertDBBid(cursor, 10, executionCount, bid_1_2)
    insertDBBidPurchase(cursor, 10, serviceId, executionCount, bid_1_2, 7)

    # bid to compare 2. 
    delay = 0.15
    price = 16.5
    bid_2_0 = createBid( provider2.getProviderId(), serviceId, delay, price)
    bid_2_0.setCreationPeriod(8)
    bid_2_0.setId('bid_replace_2_0')
    insertDBBid(cursor, 8, executionCount, bid_2_0)
    insertDBBidPurchase(cursor, 8, serviceId, executionCount, bid_2_0, 6)

    bid_2_1 = createBid( provider2.getProviderId(), serviceId, delay, price)
    bid_2_1.setCreationPeriod(9)
    bid_2_1.insertParentBid(bid_2_0)
    bid_2_1.setId('bid_replace_2_1')
    insertDBBid(cursor, 9, executionCount, bid_2_1)
    insertDBBidPurchase(cursor, 9, serviceId, executionCount, bid_2_1, 6)

    bid_2_2 = createBid( provider2.getProviderId(), serviceId, delay, price)
    bid_2_2.setCreationPeriod(10)
    bid_2_2.insertParentBid(bid_2_1)
    bid_2_2.setId('bid_replace_2_2')
    insertDBBid(cursor, 10, executionCount, bid_2_2)
    insertDBBidPurchase(cursor, 10, serviceId, executionCount, bid_2_2, 6)
    
    # Bid to tests.
    delay = 0.19
    price = 17.5
    bid_3_0 = createBid( provider2.getProviderId(), serviceId, delay, price)
    bid_3_0.setCreationPeriod(8)
    bid_3_0.setId('bid_replace_3_0')
    insertDBBid(cursor, 8, executionCount, bid_3_0)
    insertDBBidPurchase(cursor, 8, serviceId, executionCount, bid_3_0, 3)

    bid_3_1 = createBid( provider2.getProviderId(), serviceId, delay, price)
    bid_3_1.setCreationPeriod(9)
    bid_3_1.insertParentBid(bid_3_0)
    bid_3_1.setId('bid_replace_3_1')
    insertDBBid(cursor, 9, executionCount, bid_3_1)
    insertDBBidPurchase(cursor, 9, serviceId, executionCount, bid_3_1, 2)

    bid_3_2 = createBid( provider2.getProviderId(), serviceId, delay, price)
    bid_3_2.setCreationPeriod(10)
    bid_3_2.insertParentBid(bid_3_1)
    bid_3_2.setId('bid_replace_3_2')
    
    currentPeriod = 11    
    (provider2._list_vars['Bids'])= {}
    (provider2._list_vars['Bids'])[bid_3_2.getId()] = bid_3_2
    
    (provider2._list_vars['Related_Bids'])= {}    
    (provider2._list_vars['Related_Bids'])[bid_2_2.getId()] = bid_2_2
    (provider2._list_vars['Related_Bids'])[bid_1_2.getId()] = bid_1_2
    radius = 0.7
    staged_bids = {}
    provider2.replaceDominatedBids(currentPeriod, radius, staged_bids, fileResult2)
        
    if len(staged_bids) != 2: # one is the the current bid inactivated and the new one.|
        raise FoundationException("Error in method test_replace_dominated_bids")
    

def test_eliminateNeighborhoodBid():

    '''
    The ProviderExecution starts the threads for the service provider agents.
    '''    

    logger.info('Starting test_eliminateNeighborhoodBid')

    list_classes = {}
    # Load Provider classes
    load_classes(list_classes)
    
    # Open database connection
    db = MySQLdb.connect(foundation.agent_properties.addr_database,foundation.agent_properties.user_database, \
        foundation.agent_properties.user_password,foundation.agent_properties.database_name )
    
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
        WHERE id = 1"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()

        serviceIdISP = '1'            
        serviceIdBackhaul = '2'
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
            numAncestors = 4 # For testing we left four.
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
            capacityControl = 'B' # Bid Capacity.
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
                        
            capacityControl = 'B' # Bid Capacity.
            class_name = 'Provider'
            sellingAddress = foundation.agent_properties.addr_mktplace_backhaul
            buyingAddress = ' '
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceIdISP, 
                          providerSeed, marketPosition, adaptationFactor, 
                          monopolistPosition, debug, resources, numberOffers, 
                          numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, 
                       buyingAddress, capacityControl, purchase_service)
            providers.append(provider)

            i = i + 1

            break

        # start the providers
        provider1 = providers[0]  # provider - Bid capacity.
        
        provider1.start_agent()
        provider1.initialize()
        
        fileResult1 = open(provider1.getProviderId() + '.log',"a")     
        
        staged_bids = {}
        delay = 0.15
        price = 17
        bid1 = createBid(provider1.getProviderId(), provider1.getServiceId(),  delay, price)
        bid1.setCapacity(10)
        bid2 = createBid(provider1.getProviderId(), provider1.getServiceId(),  delay, price)
        bid2.setCapacity(8)
        bid3 = createBid(provider1.getProviderId(), provider1.getServiceId(),  delay, price)
        bid3.setCapacity(8.3)
        bid4 = createBid(provider1.getProviderId(), provider1.getServiceId(),  delay, price)
        bid4.setCapacity(4.5)
        bid5 = createBid(provider1.getProviderId(), provider1.getServiceId(),  delay, price)
        bid5.setCapacity(6.0)
        bid5.setStatus(Bid.INACTIVE)
        
        bid6 = createBid(provider1.getProviderId(), provider1.getServiceId(),  0.2, 12)
        bid6.setCapacity(7.0)
        
        staged_bids[bid1.getId()] = {'Object': bid1, 'Action': Bid.ACTIVE, 'MarketShare' : {}, 'Forecast' : 10 }
        staged_bids[bid2.getId()] = {'Object': bid2, 'Action': Bid.ACTIVE, 'MarketShare' : {}, 'Forecast' : 8 }
        staged_bids[bid3.getId()] = {'Object': bid3, 'Action': Bid.ACTIVE, 'MarketShare' : {}, 'Forecast' : 8.3 }
        staged_bids[bid4.getId()] = {'Object': bid4, 'Action': Bid.ACTIVE, 'MarketShare' : {}, 'Forecast' : 4.5 }
        staged_bids[bid5.getId()] = {'Object': bid5, 'Action': Bid.INACTIVE, 'MarketShare' : {}, 'Forecast' : 6 }
        staged_bids[bid6.getId()] = {'Object': bid6, 'Action': Bid.ACTIVE, 'MarketShare' : {}, 'Forecast' : 7 }
        
        provider1.eliminateNeighborhoodBid(staged_bids, fileResult1)
        
        # verifies that neigboorhood bids has been eliminated
        if len(staged_bids) != 3:
            raise FoundationException("Error in eliminate neighborhood bids Nbr Expected:3 found:" + str(len(staged_bids)))
        
        # Verifies the capacity
        for  bidId in staged_bids:
            if bidId == bid1.getId():
                bidTmp = ((staged_bids[bidId])['Object'])
                if bidTmp.getCapacity() != 30.8:
                    raise FoundationException("Error in eliminate neighborhood bids CapacityExpected:30.8" + "value:" + str(bidTmp.getCapacity()))

            if bidId == bid6.getId():
                bidTmp = ((staged_bids[bidId])['Object'])
                if bidTmp.getCapacity() != 7:
                    raise FoundationException("Error in eliminate neighborhood bids CapacityExpected:7" + "value:" + str(bidTmp.getCapacity()))

        # Verifies the forecast
        for  bidId in staged_bids:
            if bidId == bid1.getId():
                forecast = ((staged_bids[bidId])['Forecast'])
                if forecast != 30.8:
                    raise FoundationException("Error in eliminate neighborhood bids CapacityExpected:30.8" + "value:" + str(forecast))

            if bidId == bid6.getId():
                forecast = ((staged_bids[bidId])['Forecast'])
                if forecast != 7:
                    raise FoundationException("Error in eliminate neighborhood bids CapacityExpected:7" + "value:" + str(forecast))

        logger.info('Ending test_eliminateNeighborhoodBid')

    except FoundationException as e:
        print e.__str__()
    except ProviderException as e:
        print e.__str__()
    except Exception as e:
        print e.__str__()
    finally:
        # disconnect from server
        db.close()
        fileResult1.close()
        provider1.stop_agent()


def test_provider_database_classes():
    '''
    The ProviderExecution starts the threads for the service provider agents.
    '''    

    logger.info('Starting test_provider_database_classes')

    list_classes = {}
    # Load Provider classes
    load_classes(list_classes)
    
    # Open database connection
    db = MySQLdb.connect(foundation.agent_properties.addr_database,foundation.agent_properties.user_database, \
        foundation.agent_properties.user_password,foundation.agent_properties.database_name )
    
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
	    WHERE id = 1"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()

        serviceIdISP = '1'            
        serviceIdBackhaul = '2'
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
            numAncestors = 4 # For testing we left four.
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
                        
            capacityControl = 'G' # Bulk Capacity.
            class_name = 'Provider'
            sellingAddress = foundation.agent_properties.addr_mktplace_backhaul
            buyingAddress = ' '
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceIdBackhaul, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, 
                       buyingAddress, capacityControl, purchase_service)
            providers.append(provider)

            logger.info('test_provider_database_classes step:After creating provider 1')
            i = i + 1

            capacityControl = 'G' # Bulk Capacity.
            class_name = 'ProviderEdge'
            providerId = i
            providerName = 'Provider' + str(providerId)
            sellingAddress = foundation.agent_properties.addr_mktplace_isp
            buyingAddress = foundation.agent_properties.addr_mktplace_backhaul
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceIdISP, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, 
                      buyingAddress, capacityControl, ' ')
            providers.append(provider)
            i = i + 1

            logger.info('test_provider_database_classes setp:After creating provider 2')
            break

        # start the providers
        provider1 = providers[0]  # backhaul provider - Bulk capacity.
        provider2 = providers[1]  # isp provider
        
        logger.info('test_provider_database_classes step:before initiating provider 1')

        provider1.start_agent()
        provider1.initialize()
        
        logger.info('test_provider_database_classes step:after initiating provider 1')
        
        provider2.start_agent()
        provider2.initialize()

        logger.info('test_provider_database_classes step:1')

        fileResult2 = open(provider2.getProviderId() + '.log',"a")        

        deleteDBPreviousInformation(cursor)
        executionCount = getExecutionCount(cursor)         

        serviceId = '1'
        delay = 0.14
        price = 20
                
        bid = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid.setId('bf6632ce-1c7a-11e6-acae-080027fc03c6')
        bid.setCreationPeriod(3)
        insertDBBid(cursor, 3, executionCount, bid)
        insertDBBidPurchase(cursor, 3, serviceId, executionCount, bid, 10)
        insertDBBidPurchase(cursor, 4, serviceId, executionCount, bid, 7)
        
        bid2 = provider2.copyBid(bid)
        if (bid2.isEqual(bid) == False):
            raise FoundationException("copyBid Function Error")
                            
        competitor_bids = {}
        bid2 = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid2.setId('bf679646-1c7a-11e6-acae-080027fc03c6')
        bid2.setCreationPeriod(5)
        insertDBBid(cursor, 5, executionCount, bid2)
        insertDBBidPurchase(cursor, 5, serviceId, executionCount, bid2, 6)
        insertDBBidPurchase(cursor, 6, serviceId, executionCount, bid2, 5)
        
        competitor_bids[bid2.getId()] = bid2
        bid3 = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid3.setId('bf692efc-1c7a-11e6-acae-080027fc03c6')
        bid3.setCreationPeriod(7)
        insertDBBid(cursor, 7, executionCount, bid3)
        insertDBBidPurchase(cursor, 7, serviceId, executionCount, bid3, 7)
        insertDBBidPurchase(cursor, 8, serviceId, executionCount, bid3, 3)
        
        competitor_bids[bid3.getId()] = bid3
        bid4 = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid4.setId('bf695e04-1c7a-11e6-acae-080027fc03c6')
        bid4.setCreationPeriod(9)
        insertDBBid(cursor, 9, executionCount, bid4)
        insertDBBidPurchase(cursor, 9, serviceId, executionCount, bid4, 7)
        
        competitor_bids[bid4.getId()] = bid4
        bid5 = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid5.setId('bf697f4c-1c7a-11e6-acae-080027fc03c6')
        bid5.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid5)
        insertDBBidPurchase(cursor, 10, serviceId, executionCount, bid5, 5)
        
        competitor_bids[bid5.getId()] = bid5
        marketZoneDemand, totQuantity, numRelated = provider2.getDBMarketShareZone(bid,competitor_bids,3,1, fileResult2)
        if (totQuantity != 10):
            raise FoundationException("error in getDBMarketShareZone")

        marketZoneDemand, totQuantity, numRelated = provider2.getDBMarketShareZone(bid,competitor_bids,5,3, fileResult2)

        if (totQuantity != 23):
            raise FoundationException("error in getDBMarketShareZone")

        marketZoneDemand, totQuantity, numRelated = provider2.getDBMarketShareZone(bid,competitor_bids,7,2, fileResult2)
        if (totQuantity != 12):
            raise FoundationException("error in getDBMarketShareZone")

        # Verifies the number of ancestors.
        numAncestors = provider2.getNumAncestors()
        if (numAncestors != 4):
            raise FoundationException("error in getNumAncestors")

        
        bid6 = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid6.setId('e86298e6-9562-11e6-843d-02b51fdd81c5')
                        
        # verifies getDBBidMarketShare
        bidDemand, totQuantity = provider2.getDBBidMarketShare(bid5.getId(),  10, 1, fileResult2)
        if (totQuantity != 5):
            raise FoundationException("error in getDBBidMarketShare")
                
        # verifies getDBBidAncestorsMarketShare
        bid5.insertParentBid(bid4)
        bid4.insertParentBid(bid3)
        bid3.insertParentBid(bid2)
        bid2.insertParentBid(bid)
        
        bidDemand2, totQuantity2 = provider2.getDBBidAncestorsMarketShare(bid5, 10, 4, fileResult2)
        if (totQuantity2 != 22):
            raise FoundationException("error in getDBBidAncestorsMarketShare")
        
        
        logger.info('test_provider_database_classes step:2')
        
        provider2._list_vars['Current_Period'] = 11        
        
        bid6.insertParentBid(bid5)

        delay = 0.14
        price = 20 
                
        logger.info('test_provider_database_classes step: after acquire lock')
        
        # include in related bids in order to test the function getRelatedBids ( bid7 - bid 14)
        bid7 = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid7.setCreationPeriod(7)
        bid7.setId('e86a99d8-9562-11e6-843d-02b51fdd81c5')
        
        (provider2._list_vars['Related_Bids'])[bid7.getId()] = bid7
        bid8 = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid8.setCreationPeriod(7)
        bid8.setId('e87239f4-9562-11e6-843d-02b51fdd81c5')
        
        (provider2._list_vars['Related_Bids'])[bid8.getId()] = bid8
        bid9 = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid9.setCreationPeriod(8)
        bid9.setId('e879e910-9562-11e6-843d-02b51fdd81c5')
        
        (provider2._list_vars['Related_Bids'])[bid9.getId()] = bid9
        bid10 = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid10.setCreationPeriod(8)
        bid10.setId('Bid10')
        (provider2._list_vars['Related_Bids'])[bid10.getId()] = bid10
        bid11 = createBid(provider2.getProviderId(), serviceId, delay, price)
        bid11.setCreationPeriod(9)
        bid10.setId('Bid11')
        (provider2._list_vars['Related_Bids'])[bid11.getId()] = bid11

        insertDBBid(cursor, 9, executionCount, bid11)
        insertDBBidPurchase(cursor, 9, serviceId, executionCount, bid11, 9)

        bid12 = createBid(provider2.getProviderId(), serviceId, delay, price)
        bid12.setCreationPeriod(9)
        bid12.setId('Bid12')
        (provider2._list_vars['Related_Bids'])[bid12.getId()] = bid12

        insertDBBid(cursor, 9, executionCount, bid12)
        insertDBBidPurchase(cursor, 9, serviceId, executionCount, bid12, 8)

        bid13 = createBid(provider2.getProviderId(), serviceId, delay, price)
        bid13.setCreationPeriod(10)
        bid13.setId('Bid13')
        (provider2._list_vars['Related_Bids'])[bid13.getId()] = bid13

        insertDBBid(cursor, 10, executionCount, bid13)
        insertDBBidPurchase(cursor, 10, serviceId, executionCount, bid13, 7)

        bid14 = createBid(provider2.getProviderId(), serviceId, delay, price)
        bid14.setCreationPeriod(10)
        bid14.setId('Bid14')
        (provider2._list_vars['Related_Bids'])[bid14.getId()] = bid14

        insertDBBid(cursor, 10, executionCount, bid14)
        insertDBBidPurchase(cursor, 10, serviceId, executionCount, bid14, 7)
                        
        currentPeriod = 11
        radius = 0.1
        related_bids ={}
        related_bids = provider2.getRelatedBids(bid, currentPeriod, 0, radius, fileResult2)          
        if len(related_bids) != 0:
            raise FoundationException("error in getRelatedBids")
        
        
        related_bids ={}
        related_bids = provider2.getRelatedBids(bid, currentPeriod, 1, radius, fileResult2)          
        if len(related_bids) != 2:
            raise FoundationException("error in getRelatedBids")

        related_bids ={}
        related_bids = provider2.getRelatedBids(bid, currentPeriod, 2, radius, fileResult2)          
        if len(related_bids) != 4:
            raise FoundationException("error in getRelatedBids")

        related_bids ={}
        related_bids = provider2.getRelatedBids(bid, currentPeriod, 3, radius, fileResult2)          
        if len(related_bids) != 6:
            raise FoundationException("error in getRelatedBids")

        related_bids ={}
        related_bids = provider2.getRelatedBids(bid, currentPeriod, 4, radius, fileResult2)          
        if len(related_bids) != 8:
            raise FoundationException("error in getRelatedBids")

        # verifies the method calculateBidForecast
        bidDemand, forecast = provider2.calculateBidForecast(currentPeriod, bid5, fileResult2)

        if len(bidDemand) != 5:
            raise FoundationException("error in calculateBidForecast - Error:1")
        
        forecast = round(forecast, 4)
        if (forecast != 5.3648):
            raise FoundationException("error in calculateBidForecast - Error:2")
        
        # verifies calculateMovedBidForecast
        marketZoneDemand1, forecast1 = provider2.calculateMovedBidForecast(currentPeriod, radius, bid5, bid6, Provider.MARKET_SHARE_ORIENTED, fileResult2)
        # The forecast is 6.4549. which is ( the forecast for bid5:5.3648 plus forecast of competitorBid:13 + fforecast of competitorBid:14) / 3
        # that comes from demand competitor bids:bid13,bid14 and bid5 
        marketZoneDemand2, forecast2 = provider2.calculateMovedBidForecast(currentPeriod, radius, bid5, bid6, Provider.PROFIT_ORIENTED, fileResult2)

        if (forecast1 < 6) or (forecast1 > 7):
            raise FoundationException("error in calculateMovedBidForecast MARKET_SHARE - value" + str(forecast1) )

        if (forecast2 < 5) or (forecast2 > 6):
            raise FoundationException("error in calculateMovedBidForecast PROFIT_ORIENTED" + str(forecast2))


        logger.info('test_provider_database_classes step:3')
                        
        # ---------------------------------------------
        # verifies the method evaluateDirectionalDerivate
        # ---------------------------------------------
        
        # Test the case when the bid is not a current bids
        directions = provider2.evaluateDirectionalDerivate(currentPeriod, radius, bid, fileResult2)
        if len(directions) != 0:
            raise FoundationException("error in evaluateDirectionalDerivate")

        # In this case bid has zero purchases for the period and it is in the current bids.
        (provider2._list_vars['Bids'])[bid.getId()] = bid
        directions = provider2.evaluateDirectionalDerivate(currentPeriod, radius, bid, fileResult2)
        
        if len(directions) != 2:
            raise FoundationException("error in evaluateDirectionalDerivate")

        # In this case bid has 10  units of purchases for the period and it is in the current bids.        
        insertDBBidPurchase(cursor, 10, serviceId, executionCount, bid, 10)
        directions = provider2.evaluateDirectionalDerivate(currentPeriod, radius, bid, fileResult2)
        if len(directions) != 2:
            raise FoundationException("error in evaluateDirectionalDerivate")

        # ---------------------------------------------
        # verifies the method replacedominatedBids 
        # --------------------------------------------
        test_replace_dominated_bids(cursor, executionCount, provider2, fileResult2)
        
        logger.info('Ending test_provider_database_classes')

    except FoundationException as e:
        print e.__str__()
    except ProviderException as e:
        print e.__str__()
    except Exception as e:
        print e.__str__()
    finally:
        # disconnect from server
        db.close()
        fileResult2.close()
        provider1.stop_agent()
        provider2.stop_agent()

def test_provider_edge_move_quality(provider, fileResult):
    # variable initialization
    serviceIdBackhaul = '2'    
    direction = 1 
    adaptationFactor = 0.01
    marketPosition = 0.4
    
    serviceBackhaul = provider.getService(serviceIdBackhaul)
    if (serviceBackhaul == None):
        raise FoundationException("getService method is not working in class ProviderEdgeMonopoly")
            
    qualityVariableBack = serviceBackhaul.getDecisionVariable('3')
    minValueBack = qualityVariableBack.getMinValue()        
    maxValueBack = qualityVariableBack.getMaxValue()
    maxValueRange = (maxValueBack - minValueBack)*adaptationFactor
        
    output1 = provider.moveQuality(serviceBackhaul, adaptationFactor, marketPosition, direction, fileResult)

    if ((output1['3'])['Direction'] != 1):
        raise FoundationException("error in the purchase method of moveQuality Error:1")

    if (((output1['3'])['Step'] <= 0) or ((output1['3'])['Step'] >= maxValueRange) ):
        raise FoundationException("error in the purchase method of moveQuality Error:2")
    
    if ((output1['4'])['Direction'] != 1):
        raise FoundationException("error in the purchase method of moveQuality Error:3")

    if ((output1['4'])['Step'] != 0) :
        raise FoundationException("error in the purchase method of moveQuality Error:4")
    
                        
    adaptationFactor = 0.05
    marketPosition = 0.7
    maxValueRange = (maxValueBack - minValueBack)*adaptationFactor
    output1 = provider.moveQuality(serviceBackhaul, adaptationFactor, marketPosition, direction, fileResult)
    if (((output1['3'])['Step'] <= 0) or ((output1['3'])['Step'] >= maxValueRange) ):
        raise FoundationException("error in the purchase method of moveQuality Error:5")

    if ((output1['4'])['Step'] != 0) :
        raise FoundationException("error in the purchase method of moveQuality Error:6")

    direction = -1 
    maxValueRange = maxValueRange *-1
    output2 = provider.moveQuality(serviceBackhaul, adaptationFactor, marketPosition, direction, fileResult)
    if ((output2['3'])['Direction'] != -1):
        raise FoundationException("error in the purchase method of moveQuality Error:7")

    if (((output2['3'])['Step'] >= 0) or ((output2['3'])['Step'] <= maxValueRange) ):
        raise FoundationException("error in the purchase method of moveQuality Error:8")

    if ((output2['4'])['Direction'] != -1):
        raise FoundationException("error in the purchase method of moveQuality Error:9")

    if ((output2['4'])['Step'] != 0) :
        raise FoundationException("error in the purchase method of moveQuality Error:10")


def test_provider_edge_move_price(provider, fileResult):
    # variable initialization
    serviceIdBackhaul = '2'
    direction = 1 
    adaptationFactor = 0.01
    marketPosition = 0.4
    
    serviceBackhaul = provider.getService(serviceIdBackhaul)    
    priceVariableBack = serviceBackhaul.getDecisionVariable('4')
    minValueBack = priceVariableBack.getMinValue()        
    maxValueBack = priceVariableBack.getMaxValue()
    maxValueRange = (maxValueBack - minValueBack)*adaptationFactor

    direction = 1
    output2 = provider.movePrice(serviceBackhaul, adaptationFactor, marketPosition, direction, fileResult)
    if ((output2['4'])['Direction'] != 1):
        raise FoundationException("error in the purchase method of movePrice")

    if (((output2['4'])['Step'] <= 0) or ((output2['4'])['Step'] >= maxValueRange) ):
        raise FoundationException("error in the purchase method of moveQuality")

    direction = -1
    maxValueRange = maxValueRange *-1
    output2 = provider.movePrice(serviceBackhaul, adaptationFactor, marketPosition, direction, fileResult)
    if ((output2['4'])['Direction'] != -1):
        raise FoundationException("error in the purchase method of movePrice")

    if (((output2['4'])['Step'] >= 0) or ((output2['4'])['Step'] <= maxValueRange) ):
        raise FoundationException("error in the purchase method of moveQuality")

def test_provider_edge_convert_to_own_bid(ispProvider, transitProvider,  bid4, bid5, fileResult):
    # Variable initialization
    serviceIdISP = '1'     
    serviceIdBackhaul = '2'
    serviceBackhaul = ispProvider.getService(serviceIdBackhaul)
    serviceIsp = ispProvider.getService(serviceIdISP)
    adaptationFactor = 0.1
    
    # Test the function convert to own bid Backhaul --> ISP
    bid4_1 = ispProvider.convertToOwnBid(serviceIsp, serviceBackhaul, bid4, adaptationFactor, fileResult)
    bid4_2 = ispProvider.convertToOwnBid(serviceIsp, serviceBackhaul, bid5, adaptationFactor, fileResult)
                
    qualityValue = round(bid4_1.getDecisionVariable('2'),3)
    if ( qualityValue != 0.154):
        logger.error('qualityValue: %s', str(qualityValue))
        raise FoundationException("Error in method convertToOwnBid of ProviderEdgeMonopoly 1")

    qualityValue = round(bid4_2.getDecisionVariable('2'),3)    
    if ( qualityValue != 0.156):
        logger.error('qualityValue: %s', str(qualityValue))
        raise FoundationException("Error in method convertToOwnBid of ProviderEdgeMonopoly 2")

    
def test_isNeighborhood_bid_to_staged(provider, fileResult):
    # Variable initialization
    serviceIdISP = '1'     
    serviceIsp = provider.getService(serviceIdISP)

    staged_bids_test = {}
    radius = 0.1        
    delay = 0.18
    price = 15
    bidTest4_01 = createBid( provider.getProviderId(), serviceIsp.getId(), delay, price)

    # Verifies method bids are Neighborhood Bids
    delay = 0.17
    price = 14.5
    bidTest4_02 = createBid( provider.getProviderId(), serviceIsp.getId(), delay, price)

    delay = 0.18
    price = 18
    bidTest4_03 = createBid( provider.getProviderId(), serviceIsp.getId(), delay, price)

    staged_bids_test[bidTest4_03.getId()] = {'Object': bidTest4_03, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 0 }
    ret = provider.isNeighborhoodBidToStaged( bidTest4_01,  staged_bids_test, radius, fileResult)
    if ret != False:
        raise FoundationException("Error in method isNeighborhoodBidToStaged of ProviderEdgeMonopoly - Error:1")

    staged_bids_test[bidTest4_02.getId()] = {'Object': bidTest4_02, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 0 }
    ret = provider.isNeighborhoodBidToStaged( bidTest4_01,  staged_bids_test, radius, fileResult)
    if ret != True:
        raise FoundationException("Error in method isNeighborhoodBidToStaged of ProviderEdgeMonopoly - Error:2")


def test_include_exploring_bid(currentPeriod, provider, bid4, fileResult):
    # Variable initialization
    serviceIdISP = '1'     
    serviceIsp = provider.getService(serviceIdISP)
    serviceIdBackhaul = '2'        
    serviceProvider = provider.getService(serviceIdBackhaul)
    
    adaptationFactor = 0.01
    marketPosition = 0.4
    numAncestors = 4

    # Test is neighborhoodBidToStaged
    staged_bids_test = {}
    radius = 0.1        
    delay = 0.18
    price = 15
    bidTest4_01 = createBid( provider.getProviderId(), serviceIsp.getId(), delay, price)

    # Verifies method bids are Neighborhood Bids
    delay = 0.17
    price = 14.5
    bidTest4_02 = createBid( provider.getProviderId(), serviceIsp.getId(), delay, price)

    delay = 0.18
    price = 18
    bidTest4_03 = createBid( provider.getProviderId(), serviceIsp.getId(), delay, price)

    staged_bids_test[bidTest4_03.getId()] = {'Object': bidTest4_03, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 0 }

    staged_bids_resp = {}         
    provider.includeExploringBid( currentPeriod, numAncestors, serviceProvider, adaptationFactor, marketPosition, bidTest4_01, bid4, serviceIsp, radius, staged_bids_resp, staged_bids_test, fileResult)
    if len(staged_bids_resp) != 1:
        raise FoundationException("Error in method includeExploringBid of ProviderEdgeMonopoly - Error:1 expecting:1 len:" + str(len(staged_bids_resp)) )

    staged_bids_test[bidTest4_02.getId()] = {'Object': bidTest4_02, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 0 }
    
    staged_bids_resp = {}
    provider.includeExploringBid( currentPeriod, numAncestors, serviceProvider, adaptationFactor, marketPosition, bidTest4_01, bid4, serviceIsp, radius, staged_bids_resp, staged_bids_test, fileResult)
    if len(staged_bids_resp) != 0:
        raise FoundationException("Error in method includeExploringBid of ProviderEdgeMonopoly - Error 2")

def test_exec_front_bids(ispProvider, transitProvider, currentPeriod, bid, fileResult):
    '''
     We test the function Exec Front Bids by calling all of their functions
    '''
    # Variable initialization
    serviceIdISP = '1'     
    serviceIdBackhaul = '2'
    serviceBackhaul = ispProvider.getService(serviceIdBackhaul)
    serviceIsp = ispProvider.getService(serviceIdISP)
    staged_bids = {}
    adaptationFactor = 0.1
    marketPosition = 0.4
    radius = 0.1
    numAncestors = 4

    quality = 0.03 # the total delay will be when converted equal to the value (0.14 * random (minvalue, maxvalue)) + 0.03
    price = 15.5
    provBid4Test = createBidBackhaul(transitProvider.getProviderId(), serviceIdBackhaul, quality, price)
    newBid = ispProvider.convertToOwnBid( serviceIsp, serviceBackhaul,  provBid4Test, adaptationFactor, fileResult)
    
    # Verifies the own bid is within the correct quality and price.
    qualityValue = round(newBid.getDecisionVariable('2'),3)
    if ( qualityValue != 0.156):
        logger.error('qualityValue: %s', str(qualityValue))
        raise FoundationException("Error in method test_exec_front_bids of ProviderEdgeMonopoly - Error 1")

    priceValue = round(newBid.getDecisionVariable('1'),2)    
    if ( priceValue != 17.71):
        logger.error('priceValue: %s', str(priceValue))
        raise FoundationException("Error in method test_exec_front_bids of ProviderEdgeMonopoly - Error 2")

    staged_bids_resp = {}
    
    # decrease quality - To decrease quality means to increase the value of the quality.
    direction = -1
    directionQuality = ispProvider.moveQuality(serviceIsp, adaptationFactor, marketPosition, direction, fileResult)
    newBidOwn1 = ispProvider.moveBidOnDirectionEdge(newBid, serviceIsp, directionQuality)
    
    qualityValueTmp = round(newBidOwn1.getDecisionVariable('2'),4)
    if ( qualityValue > qualityValueTmp ): # 
        raise FoundationException("Error in method test_exec_front_bids of ProviderEdgeMonopoly - Error 3")
                
    direction = 1            
    directionPrice = ispProvider.movePrice(serviceIsp, adaptationFactor, marketPosition, direction, fileResult)
    newBidOwn1 = ispProvider.moveBidOnDirectionEdge(newBidOwn1, serviceIsp, directionPrice)

    priceValueTmp = round(newBidOwn1.getDecisionVariable('1'),4)
    if ( priceValueTmp < priceValue ):
        raise FoundationException("Error in method test_exec_front_bids of ProviderEdgeMonopoly - Error 4")
        
    if (newBidOwn1 != None):
        ispProvider.includeExploringBid(currentPeriod, numAncestors, serviceBackhaul, adaptationFactor, marketPosition, newBidOwn1, provBid4Test, serviceIsp, radius, staged_bids_resp, staged_bids, fileResult)

    # Increase quality and then calculate a profit.
    direction = 1
    directionQuality = ispProvider.moveQuality(serviceIsp, adaptationFactor, marketPosition, direction, fileResult)
    newBidOwn2 = ispProvider.moveBidOnDirectionEdge(newBid, serviceIsp, directionQuality)

    qualityValueTmp = round(newBidOwn2.getDecisionVariable('2'),4)
    if ( qualityValue < qualityValueTmp ):
        raise FoundationException("Error in method test_exec_front_bids of ProviderEdgeMonopoly - Error 5")

    direction = 1
    directionPrice = ispProvider.movePrice(serviceIsp, adaptationFactor, marketPosition, direction, fileResult)
    newBidOwn2 = ispProvider.moveBidOnDirectionEdge(newBidOwn2, serviceIsp, directionPrice)

    priceValueTmp = round(newBidOwn2.getDecisionVariable('1'),4)
    if ( priceValueTmp < priceValue ):
        raise FoundationException("Error in method test_exec_front_bids of ProviderEdgeMonopoly - Error 6")

    if (newBidOwn2 != None):
        ispProvider.includeExploringBid(currentPeriod, numAncestors, serviceBackhaul, adaptationFactor, marketPosition, newBidOwn2, provBid4Test, serviceIsp, radius, staged_bids_resp, staged_bids, fileResult)

    # Just increase for profit.
    direction = 1
    directionPrice = ispProvider.movePrice(serviceIsp, adaptationFactor, marketPosition, direction, fileResult)
    newBidOwn3 = ispProvider.moveBidOnDirectionEdge(newBid, serviceIsp, directionPrice)

    qualityValueTmp = round(newBidOwn3.getDecisionVariable('2'),3)
    if ( qualityValue != qualityValueTmp ):
        logger.error('qualityValueTmp: %s qualityValue:%s', str(qualityValueTmp), str(qualityValue) )
        raise FoundationException("Error in method test_exec_front_bids of ProviderEdgeMonopoly - Error 7")

    priceValueTmp = round(newBidOwn3.getDecisionVariable('1'),3)
    if ( priceValueTmp < priceValue ):
        logger.error('priceValueTmp: %s priceValue:%s', str(priceValueTmp), str(priceValue) )
        raise FoundationException("Error in method test_exec_front_bids of ProviderEdgeMonopoly - Error 8")

    if (newBidOwn3 != None):
        ispProvider.includeExploringBid(currentPeriod, numAncestors, serviceBackhaul, adaptationFactor, marketPosition, newBidOwn3, provBid4Test, serviceIsp, radius, staged_bids_resp, staged_bids, fileResult)
            
    staged_bids_resp.clear()
        
    bidList = []
    bidList.append(provBid4Test)
    ispProvider.execFrontBids(currentPeriod, numAncestors, radius, serviceIsp, serviceBackhaul, adaptationFactor, marketPosition, bidList, staged_bids, staged_bids_resp, fileResult)

    if (len(staged_bids_resp) != 1):
        raise FoundationException("Error in test_exec_front_bids - Error:9")
                
    staged_bids_resp.clear()

def test_ask_backhaul_bids(provider):
    serviceBackhaulId = '2'
    # Test the method AskBackhaulBids.
    dic_return = provider.AskBackhaulBids(serviceBackhaulId)
    if (len(dic_return) != 1):
        raise FoundationException("Error in method AskBackhaulBids of ProviderEdgeMonopoly")
        
    bidList = []
    keys_sorted = sorted(dic_return,reverse=True)
    for front in keys_sorted:
        bidList = dic_return[front]
        break        
        
    if (len(bidList) != 5):
        raise FoundationException("Error in method AskBackhaulBids of ProviderEdgeMonopoly")

def test_exec_bid_update(provider, currentPeriod, fileResult):
    # Variable initialization
    serviceIdISP = '1'     
    serviceIdBackhaul = '2'
    serviceBackhaul = provider.getService(serviceIdBackhaul)
    serviceIsp = provider.getService(serviceIdISP)
    staged_bids = {}
    adaptationFactor = 0.1
    marketPosition = 0.4
    radius = 0.1
    numAncestors = 4
    staged_bids_temp = {}
    staged_bids_temp2 = {}
    
    provider.execBidUpdate(currentPeriod, numAncestors, radius, serviceIsp, serviceBackhaul, adaptationFactor, marketPosition, staged_bids, staged_bids_temp2, fileResult)
    if (len(staged_bids_temp2) != 2):
        raise FoundationException("Error in method execBidUpdate of ProviderEdgeMonopoly")
        
    for bidId in staged_bids_temp:
        staged_bids_temp2[bidId] = staged_bids_temp[bidId]

def test_get_related_own_bids(cursor, provider, fileResult):
    # Variable initialization
    serviceIdISP = '1'     
    serviceIsp = provider.getService(serviceIdISP)
    executionCount = getExecutionCount(cursor)

    incrPrice = 0.5
    priceVariable = serviceIsp.getDecisionVariable('1')
    minPrice = priceVariable.getMinValue()
    maxPrice = priceVariable.getMaxValue()
        
    numBefore = len(provider._list_vars['Bids'])
        
    incrQuality = 0.01
    qualityVariable = serviceIsp.getDecisionVariable('2')
    minQuality = qualityVariable.getMinValue()
    maxQuality = qualityVariable.getMaxValue()
    price = minPrice
    quality = minQuality
    while (price <= maxPrice):
        quality = minQuality
        while (quality <= maxQuality):
            BidTmp = createBid(provider.getProviderId(), serviceIsp.getId(), quality, price)
            (provider._list_vars['Bids'])[BidTmp.getId()] = BidTmp
            quality = quality + incrQuality
        price = price + incrPrice
        
    numAfter = len(provider._list_vars['Bids'])

    if (numAfter - numBefore) != 102:
        raise FoundationException("Error in assigning bids to provider4")
    
    staged_bids_resp = {}
    
    radius = 0.05
    for bidId in staged_bids_resp:
        bid = (staged_bids_resp[bidId])['Object']
        relatedBids = provider.getOwnRelatedBids(bid, radius, 10, 2, fileResult)
        if len(relatedBids) != 0:
            raise FoundationException("Error in getOwnRelatedBids")
        
    for bidId in provider._list_vars['Bids']:
        ((provider._list_vars['Bids'])[bidId]).setCreationPeriod(10)

    radius = 0.2        
    for bidId in staged_bids_resp:
        bid = (staged_bids_resp[bidId])['Object']
        relatedBids = provider.getOwnRelatedBids(bid, radius, 10, 2, fileResult)
        if len(relatedBids) == 0:
            raise FoundationException("Error in getOwnRelatedBids")

    for bidId in provider._list_vars['Bids']:
        ((provider._list_vars['Bids'])[bidId]).setCreationPeriod(9)

    for bidId in staged_bids_resp:
        bid = (staged_bids_resp[bidId])['Object']
        relatedBids = provider.getOwnRelatedBids(bid, radius, 10, 2, fileResult)
        if len(relatedBids) == 0:
            raise FoundationException("Error in getOwnRelatedBids")

    for bidId in provider._list_vars['Bids']:
        ((provider._list_vars['Bids'])[bidId]).setCreationPeriod(8)

    for bidId in staged_bids_resp:
        bid = (staged_bids_resp[bidId])['Object']
        relatedBids = provider.getOwnRelatedBids(bid, radius, 10, 2, fileResult)
        if len(relatedBids) == 0:
            raise FoundationException("Error in getOwnRelatedBids")

    for bidId in provider._list_vars['Bids']:
        ((provider._list_vars['Bids'])[bidId]).setCreationPeriod(7)

    for bidId in staged_bids_resp:
        bid = (staged_bids_resp[bidId])['Object']
        relatedBids = provider.getOwnRelatedBids(bid, radius, 10, 2, fileResult)
        if len(relatedBids) != 0:
            raise FoundationException("Error in getOwnRelatedBids")

    # This code creates the bids in the database
    for bidId in provider._list_vars['Bids']:
        ((provider._list_vars['Bids'])[bidId]).setCreationPeriod(7)
        ((provider._list_vars['Bids'])[bidId]).setUnitaryProfit(0.6)
        bid = ((provider._list_vars['Bids'])[bidId])            
        insertDBBid(cursor, 7, executionCount, bid)
        insertDBBidPurchase(cursor, 7, serviceIdISP, executionCount, bid, 3)

    # This code creates purchases in the database for another period.
    for bidId in provider._list_vars['Bids']:
        bid = ((provider._list_vars['Bids'])[bidId])            
        insertDBBidPurchase(cursor, 8, serviceIdISP, executionCount, bid, 2)
        
    # This code creates purchases in the database for another period.
    for bidId in provider._list_vars['Bids']:
        bid = ((provider._list_vars['Bids'])[bidId])            
        insertDBBidPurchase(cursor, 9, serviceIdISP, executionCount, bid, 1)

    bid4_3 = createBid(provider.getProviderId(), serviceIdISP, 0.15, 17) 
    # This bring all bids that were created in the last three periods
    radius = 0.1
    currentPeriod = 10
    bids_related1 = provider.getOwnRelatedBids(bid4_3, radius, currentPeriod, 3, fileResult)
    num_bids_related = len(bids_related1)
    if num_bids_related != 13:
        raise FoundationException("Error in test_get_related_own_bids - Error:1")

    bid4_4 = createBid(provider.getProviderId(), serviceIdISP, 0.14, 15)
    bids_related2 = provider.getOwnRelatedBids(bid4_4, radius, currentPeriod, 3, fileResult)
        
    if len(bids_related2) != 10:
        raise FoundationException("Error in test_get_related_own_bids - Error:2")
    
    return bids_related1, bids_related2


def test_determine_profit_forecast(cursor, ispProvider, transitProvider, currentPeriod, fileResult):
    ''' 
    This code assumes that the database has been updated with demand
    '''
     
    #Variable initialization
    serviceIdISP = '1'     
    serviceIdBackhaul = '2'
    serviceBackhaul = ispProvider.getService(serviceIdBackhaul)
    serviceIsp = ispProvider.getService(serviceIdISP)
    adaptationFactor = 0.1
    marketPosition = 0.4
    radius = 0.1
    numAncestors = 4

    delay = 0.18	
    price = 15	
    bid4_test = createBid(ispProvider.getProviderId(), serviceBackhaul, delay, price)
            
    value = ispProvider.determineProfitForecast(currentPeriod, numAncestors, radius, serviceIsp, serviceBackhaul, adaptationFactor, marketPosition, bid4_test, fileResult)
    value = round(value,4)    
    if (value != -0.3744):
        raise FoundationException("Error in test_determine_profit_forecast - Error:1")
    

def test_get_db_market_share_zone1(provider, bids_related, fileResult):
    # Variable initialization
    serviceIdISP = '1'     

    bid4_3 = createBid(provider.getProviderId(), serviceIdISP, 0.15, 17) 
    # This bring all bids that were created in the last three periods
    currentPeriod = 10
    marketZoneDemand, totQuantity, numRelated = provider.getDBMarketShareZone(bid4_3, bids_related, currentPeriod -1 , 1, fileResult)
    if totQuantity != 13:
        raise FoundationException("Error in test_get_db_market_share_zone - Error:1")
        
    marketZoneDemand, totQuantity, numRelated = provider.getDBMarketShareZone(bid4_3, bids_related, currentPeriod -1 , 2, fileResult)
    if totQuantity != 39:
        raise FoundationException("Error in test_get_db_market_share_zone - Error:2")

    marketZoneDemand, totQuantity, numRelated = provider.getDBMarketShareZone(bid4_3, bids_related, currentPeriod -1 , 3, fileResult)
    if totQuantity != 78:
        raise FoundationException("Error in test_get_db_market_share_zone - Error:3")

def test_get_db_profit_zone1(provider, bids_related, fileResult):
    # Variable initialization
    serviceIdISP = '1'     

    bid4_3 = createBid(provider.getProviderId(), serviceIdISP, 0.15, 17) 
    # This bring all bids that were created in the last three periods

    profitZone, totProfit, numRelated = provider.getDBProfitZone(bid4_3, bids_related, 9, fileResult)
    if round(totProfit,1) != 7.8:
        raise FoundationException("Error (1) in calculating method getDBProfitZone of ProviderEdgeMonopoly")
        
    profitZone, totProfit, numRelated = provider.getDBProfitZone(bid4_3, bids_related, 8, fileResult)
    if round(totProfit,1) != 15.6:
        raise FoundationException("Error (2) in calculating method getDBProfitZone of ProviderEdgeMonopoly")

    profitZone, totProfit, numRelated = provider.getDBProfitZone(bid4_3, bids_related, 7, fileResult)
    if round(totProfit,1) != 23.4:
        raise FoundationException("Error (3) in calculating method getDBProfitZone of ProviderEdgeMonopoly")


def test_get_db_market_share_zone2(provider, bids_related, fileResult ):
    # Variable initialization
    serviceIdISP = '1'     
    bid4_4 = createBid(provider.getProviderId(), serviceIdISP, 0.14, 15)
    currentPeriod = 10
            
    marketZoneDemand, totQuantity, numRelated = provider.getDBMarketShareZone(bid4_4, bids_related, currentPeriod -1, 1, fileResult)
    if totQuantity != 10:
        raise FoundationException("Error (1) in calculating method getDBMarketShareZone of ProviderEdgeMonopoly")
        
    marketZoneDemand, totQuantity, numRelated = provider.getDBMarketShareZone(bid4_4, bids_related, currentPeriod -1, 2, fileResult)
    if totQuantity != 30:
        raise FoundationException("Error (2) in calculating method getDBMarketShareZone of ProviderEdgeMonopoly")

    marketZoneDemand, totQuantity, numRelated = provider.getDBMarketShareZone(bid4_4, bids_related, currentPeriod -1, 3, fileResult)
    if totQuantity != 60:
        raise FoundationException("Error (3) in calculating method getDBMarketShareZone of ProviderEdgeMonopoly")

def test_get_db_profit_zone2(provider, bids_related, fileResult):
    # Variable initialization
    serviceIdISP = '1'     
    bid4_4 = createBid(provider.getProviderId(), serviceIdISP, 0.14, 15)

    profitZone, totProfit, numRelated = provider.getDBProfitZone(bid4_4, bids_related, 9, fileResult)
    if round(totProfit,0) != 6:
        raise FoundationException("Error (1) in calculating method getDBProfitZone of ProviderEdgeMonopoly")
        
    profitZone, totProfit, numRelated = provider.getDBProfitZone(bid4_4, bids_related, 8, fileResult)
    if round(totProfit,0) != 12:
        raise FoundationException("Error (2) in calculating method getDBProfitZone of ProviderEdgeMonopoly")

    profitZone, totProfit, numRelated = provider.getDBProfitZone(bid4_4, bids_related, 7, fileResult)
    if round(totProfit,0) != 18:
        raise FoundationException("Error (3) in calculating method getDBProfitZone of ProviderEdgeMonopoly")

def test_calculate_forecast(provider, fileResult):
    # Variable initialization
    serviceIdISP = '1'     
    radius = 0.1
    bid4_3 = createBid(provider.getProviderId(), serviceIdISP, 0.15, 17) 
    bid4_4 = createBid(provider.getProviderId(), serviceIdISP, 0.14, 15)
    currentPeriod = 10
    #-------------------------------------------------------
    # Test Calculate Forecast
    #-------------------------------------------------------        
    staged_bids = {}
    staged_bids[bid4_3.getId()] = {'Object': bid4_3, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 0 }
    staged_bids[bid4_4.getId()] = {'Object': bid4_4, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 0 }
                                    
    provider.calculateForecast(radius, currentPeriod, 3, 5, staged_bids, fileResult)
        
    if ((staged_bids[bid4_3.getId()])['Forecast'] <= 5.571) or ((staged_bids[bid4_3.getId()])['Forecast'] >= 5.572):
        raise FoundationException("Error (1) in calculating method calculateForecast of ProviderEdgeMonopoly")
        
    if ((staged_bids[bid4_4.getId()])['Forecast'] <= 5.454) or ((staged_bids[bid4_4.getId()])['Forecast'] >= 5.455):
        raise FoundationException("Error (2) in calculating method calculateForecast of ProviderEdgeMonopoly")

def test_purchase_bids_based_on_providers_bids(provider, bid4, bid5, fileResult):
    # Variable initialization
    serviceIdISP = '1'     
    serviceIdBackhaul = '2'
    serviceBackhaul = provider.getService(serviceIdBackhaul)
    serviceIsp = provider.getService(serviceIdISP)
    adaptationFactor = 0.1

    # Test the function convert to own bid.        
    bid4_1 = provider.convertToOwnBid(serviceIsp, serviceBackhaul, bid4, adaptationFactor, fileResult)
    bid4_2 = provider.convertToOwnBid(serviceIsp, serviceBackhaul, bid5, adaptationFactor, fileResult)

    currentPeriod = provider.getCurrentPeriod()
    quantity = provider.purchaseBasedOnProvidersBids(currentPeriod, serviceIdBackhaul, bid4, 3, fileResult)
    if (quantity != 3):
        raise FoundationException("error in test_purchase_bids_based_on_providers_bids - Error:1")
    

    staged_bids = {}
    staged_bids[bid4_1.getId()] = {'Object': bid4_1, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 3 }
    staged_bids[bid4_2.getId()] = {'Object': bid4_2, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 3 }
    provider.purchaseBidsBasedOnProvidersBids( currentPeriod, staged_bids, fileResult)
    for bidId in staged_bids:
        if (staged_bids[bidId]['Object']).getCapacity() != staged_bids[bidId]['Forecast']:
            raise FoundationException("error in test_purchase_bids_based_on_providers_bids - Error:2")
    

def test_update_closest_bid_forecast(provider1, fileResult):
    # Create four bids: three active, one inactive, and put them into staged_bids. 
    # Then create another bid close to two bids registered in staged_bids.
    # Verify the forecast of the closest active bid.
    # Variable initialization
    serviceIdISP = '1'     
    currentPeriod = 1
    forecast = 50

    bid0_0 = createBid(provider1.getProviderId(), serviceIdISP, 0.2, 17.5)
    bid0_0.setStatus(Bid.ACTIVE)
    
    bid0_2 = createBid(provider1.getProviderId(), serviceIdISP, 0.18, 16)
    bid0_2.setStatus(Bid.ACTIVE)
    bid0_1 = createBid(provider1.getProviderId(), serviceIdISP, 0.2, 16.5)
    bid0_1.setStatus(Bid.ACTIVE)
    bid0_3 = createBid(provider1.getProviderId(), serviceIdISP, 0.15, 17.5)
    bid0_3.setStatus(Bid.ACTIVE)
    bid0_4 = createBid(provider1.getProviderId(), serviceIdISP, 0.2, 17.5)
    bid0_4.setStatus(Bid.INACTIVE)
    
    staged_bids = {}
    staged_bids[bid0_2.getId()] = {'Object': bid0_2, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 4 }
    staged_bids[bid0_1.getId()] = {'Object': bid0_1, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 3 }
    staged_bids[bid0_3.getId()] = {'Object': bid0_3, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 5 }
    staged_bids[bid0_4.getId()] = {'Object': bid0_4, 'Action': Bid.INACTIVE, 'MarketShare': {}, 'Forecast': 6 }
    
    provider1.updateClosestBidForecast( currentPeriod, bid0_0, staged_bids, forecast, fileResult)
    if (staged_bids[bid0_1.getId()])['Forecast'] != 53:
        raise FoundationException("error in test_update_closest_bid_forecast - Error:1")

def test_provider_edge_monopoly_classes():
    '''
    The ProviderExecution starts the threads for the service provider agents.
    '''    
    
    logger.info('Starting test_provider_edge_monopoly_classes')
    
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
	    WHERE id in (1,2,3,4)"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()

        serviceIdISP = '1'            
        serviceIdBackhaul = '2'
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

        # start the providers
        provider1 = providers[0]  # isp Edgeprovider 
        provider2 = providers[1]  # backhaul provider - Bulk capacity.
        provider3 = providers[2]  # isp Edge Monopoly provider 
        provider4 = providers[3]  # backhaul provider - Bid capacity. 

        # Verifies provider 1.
        if ((provider1._list_vars['Type']).getType() != AgentType.PROVIDER_ISP):
            raise FoundationException("error in configure provider 1 - Error 1 ")
            
        if (provider1._list_vars['SellingAddres'] != foundation.agent_properties.addr_mktplace_isp):
            raise FoundationException("error in configure provider 1 - Error 2 ")
        
        if (provider1._list_vars['BuyingAddres'] != foundation.agent_properties.addr_mktplace_backhaul):
            raise FoundationException("error in configure provider 1 - Error 3 ")
        
        if (provider1._list_vars['serviceId'] != serviceIdISP):
            raise FoundationException("error in configure provider 1 - Error 4 ")
            
        if (provider1._list_vars['capacityControl'] != 'B'):
            raise FoundationException("error in configure provider 1 - Error 5 ")
            
        if (provider1._list_vars['PurchaseServiceId'] != serviceIdBackhaul):
            raise FoundationException("error in configure provider 1 - Error 6 ")

        # Verifies provider 2.
        if ((provider2._list_vars['Type']).getType() != AgentType.PROVIDER_BACKHAUL):
            raise FoundationException("error in configure provider 2 - Error 1 ")
            
        if (provider2._list_vars['SellingAddres'] != foundation.agent_properties.addr_mktplace_backhaul):
            raise FoundationException("error in configure provider 2 - Error 2 ")
                
        if (provider2._list_vars['serviceId'] != serviceIdBackhaul):
            raise FoundationException("error in configure provider 2 - Error 3 ")
            
        if (provider2._list_vars['capacityControl'] != 'G'):
            raise FoundationException("error in configure provider 2 - Error 4 ")

        if (provider2._list_vars['PurchaseServiceId'] != 'None'):
            raise FoundationException("error in configure provider 2 - Error 5 ")
                    
        # Verifies provider 3.
        if ((provider3._list_vars['Type']).getType() != AgentType.PROVIDER_ISP):
            raise FoundationException("error in configure provider 3 - Error 1 ")
            
        if (provider3._list_vars['SellingAddres'] != foundation.agent_properties.addr_mktplace_isp):
            raise FoundationException("error in configure provider 3 - Error 2 ")
        
        if (provider3._list_vars['BuyingAddres'] != foundation.agent_properties.addr_mktplace_backhaul):
            raise FoundationException("error in configure provider 3 - Error 3 ")
        
        if (provider3._list_vars['serviceId'] != serviceIdISP):
            raise FoundationException("error in configure provider 3 - Error 4 ")
            
        if (provider3._list_vars['capacityControl'] != 'B'):
            raise FoundationException("error in configure provider 3 - Error 5 ")
            
        if (provider3._list_vars['PurchaseServiceId'] != serviceIdBackhaul):
            raise FoundationException("error in configure provider 3 - Error 6 ")

        # Verifies provider 4.
        if ((provider4._list_vars['Type']).getType() != AgentType.PROVIDER_BACKHAUL):
            raise FoundationException("error in configure provider 4 - Error 1 ")
            
        if (provider4._list_vars['SellingAddres'] != foundation.agent_properties.addr_mktplace_backhaul):
            raise FoundationException("error in configure provider 4 - Error 2 ")
                
        if (provider4._list_vars['serviceId'] != serviceIdBackhaul):
            raise FoundationException("error in configure provider 4 - Error 3 ")
            
        if (provider4._list_vars['capacityControl'] != 'B'):
            raise FoundationException("error in configure provider 4 - Error 4 ")
            
        if (provider4._list_vars['PurchaseServiceId'] != 'None'):
            raise FoundationException("error in configure provider 4 - Error 5 ")
        
        # Verifies parameters for providers, so we can start from a established point.
        

        provider1.start_agent()
        provider1.initialize()
        provider2.start_agent()
        provider2.initialize()
        provider3.start_agent()
        provider3.initialize()
        provider4.start_agent()
        provider4.initialize()
        if (provider3.getNumberServices() != 2):
            raise FoundationException("error in the initialize method of class ProviderEdgeMonopoly")
        
        # Variable Initialization        
        serviceId = '2'
        fileResult1 = open(provider1.getProviderId() + '.log',"a")
        fileResult2 = open(provider2.getProviderId() + '.log',"a")        
        fileResult3 = open(provider3.getProviderId() + '.log',"a")
        fileResult4 = open(provider4.getProviderId() + '.log',"a")

        # This code verifies the Market Place Server with BulkCapacity
        # send capacity 100 units
        provider2.send_capacity()
        currentPeriod = provider2.getCurrentPeriod()
        
        # creates the bid with the minimal quality.                
        quality = 0
        price = 10
        bid = createBidBackhaul(provider2.getProviderId(), serviceId, quality, price)
        provider2.sendBid(bid, fileResult1)
        
        logger.info('test_provider_edge_monopoly_classes Step:1')
                
        # creates bids for tranit provider with bulk capacity.
        quality = 0
        price = 10
        bid2 = createBidWithCapacity(provider4.getProviderId(), serviceId, quality, price, 10)
        bid3 = createBidWithCapacity(provider4.getProviderId(), serviceId, quality, price, 5)
        provider4.sendBid(bid2, fileResult3)
        provider4.sendBid(bid3, fileResult3)
        
        
        quality = 0.01
        price = 11
        bid4 = createBidWithCapacity(provider4.getProviderId(), serviceId, quality, price, 10)        
        provider4.sendBid(bid4, fileResult3)

        quality = 0.03
        price = 13
        bid5 = createBidWithCapacity(provider4.getProviderId(), serviceId, quality, price, 10)
        provider4.sendBid(bid5, fileResult3)

        logger.info('test_provider_edge_monopoly_classes Step:2')

        # test auxiliary functions for moving bids.        
        test_provider_edge_move_quality(provider3, fileResult3)
        test_provider_edge_move_price(provider3, fileResult3)
        test_provider_edge_convert_to_own_bid(provider3, provider4, bid4, bid5, fileResult3)   
        test_purchase_bids_based_on_providers_bids(provider3, bid4, bid5, fileResult3)
        test_isNeighborhood_bid_to_staged(provider3, fileResult3)
        test_include_exploring_bid(currentPeriod, provider3, bid4, fileResult3)
        
        logger.info('test_provider_edge_monopoly_classes Step:3')
        
        deleteDBPreviousInformation(cursor)
        insertDBDemandInformation(cursor, provider3)
        currentPeriod = 13
                                       
        test_determine_profit_forecast(cursor, provider3, provider4, currentPeriod, fileResult3 )
        test_exec_front_bids(provider3, provider2, currentPeriod, bid, fileResult3)        
        test_ask_backhaul_bids(provider3)
        test_exec_bid_update(provider3, currentPeriod, fileResult3)
        
        logger.info('test_provider_edge_monopoly_classes Step:4')
        
        # Delete all previous bids.
        provider3._list_vars['Bids'].clear()
        
        bids_related1, bids_related2 = test_get_related_own_bids(cursor, provider3, fileResult3)
        test_get_db_market_share_zone1(provider3, bids_related1, fileResult3)
        test_get_db_profit_zone1(provider3, bids_related1, fileResult3)        
        test_get_db_market_share_zone2(provider3, bids_related2, fileResult3 )
        test_get_db_profit_zone2( provider3, bids_related2, fileResult3 )
        test_calculate_forecast( provider3, fileResult3 )
        test_update_closest_bid_forecast( provider3, fileResult3 )
        
        logger.info('Ending test_provider_edge_monopoly_classes')
        
        pass

    except FoundationException as e:
        logger.error( e.__str__())
    except ProviderException as e:
        logger.error( e.__str__())
    except Exception as e:
        logger.error( e.__str__())
    finally:
        	# disconnect from server

        provider1.stop_agent()
        provider2.stop_agent()
        provider3.stop_agent()
        provider4.stop_agent()

        fileResult1.close()
        fileResult2.close()
        fileResult3.close()
        fileResult4.close()
        db.close()
    

def test_sort_by_last_market_share(cursor, ispProvider, executionCount, fileResult):
    # Variable initialization.
    serviceIdISP = '1'
    currentPeriod = 12

    delay = 0.2
    price = 13	
    demand = 11
    bid4_12 = createBid(ispProvider.getProviderId(), serviceIdISP, delay, price)
    bid4_12.setUnitaryProfit(0.2)
    bid4_12.setCreationPeriod(10)
    bid4_12.setNumberPredecessor(1)
    insertDBBid(cursor, 10, executionCount, bid4_12)
    insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_12, demand+4)        
    insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_12, demand+2)        
    insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_12, demand+0)        
    (ispProvider._list_vars['Bids'])[bid4_12.getId()] = bid4_12
             
    delay = 0.18
    price = 14.0	
    demand = 10
    bid4_13 = createBid(ispProvider.getProviderId(), serviceIdISP, delay, price)
    bid4_13.setUnitaryProfit(0.2)
    bid4_13.setCreationPeriod(10)
    bid4_13.setNumberPredecessor(1)
    insertDBBid(cursor, 10, executionCount, bid4_13)
    insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_13, demand+4)        
    insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_13, demand+2)        
    insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_13, demand+0)        
    (ispProvider._list_vars['Bids'])[bid4_13.getId()] = bid4_13
             
    delay = 0.15
    price = 15.5	
    demand = 9
    bid4_14 = createBid(ispProvider.getProviderId(), serviceIdISP, delay, price)
    bid4_14.setUnitaryProfit(0.2)
    bid4_14.setCreationPeriod(10)
    bid4_14.setNumberPredecessor(1)
    insertDBBid(cursor, 10, executionCount, bid4_14)
    insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_14, demand+4)        
    insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_14, demand+2)        
    insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_14, demand+0)        
    (ispProvider._list_vars['Bids'])[bid4_14.getId()] = bid4_14
        
    delay = 0.14
    price = 17	
    demand = 14
    bid4_15 = createBid(ispProvider.getProviderId(), serviceIdISP, delay, price)
    bid4_15.setUnitaryProfit(0.2)
    bid4_15.setCreationPeriod(10)
    bid4_15.setNumberPredecessor(1)
    insertDBBid(cursor, 10, executionCount, bid4_15)
    insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_15, demand+4)        
    insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_15, demand+2)        
    insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_15, demand+0)        
    (ispProvider._list_vars['Bids'])[bid4_15.getId()] = bid4_15
        
    dict_result = ispProvider.sortByLastMarketShare(currentPeriod, fileResult)
    list_keys = dict_result.keys()
    if (list_keys[0] != bid4_15.getId()):
        raise FoundationException("Error in test_sort_by_last_market_share - Error: 1")

    if (list_keys[1] != bid4_12.getId()):
        raise FoundationException("Error in test_sort_by_last_market_share - Error: 2")

    if (list_keys[2] != bid4_13.getId()):
        raise FoundationException("Error in test_sort_by_last_market_share - Error: 3")

    if (list_keys[3] != bid4_14.getId()):
        raise FoundationException("Error in test_sort_by_last_market_share - Error: 4")
    

def test_provider_edge_monopoly_current_bids():
    '''
    The ProviderExecution starts the threads for the service provider agents.
    '''    
    
    logger.info('Starting test_provider_edge_monopoly_current_bids')
    
    list_classes = {}
    # Load Provider classes
    load_classes(list_classes)
    
    # Open database connection
    db = MySQLdb.connect(foundation.agent_properties.addr_database,foundation.agent_properties.user_database, \
        foundation.agent_properties.user_password,foundation.agent_properties.database_name )
    
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
	    WHERE id in (2,3) order by id"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()

        serviceIdISP = '1'
        serviceIdBackhaul = '2'
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
            
            adaptationFactor = 0.99 # Large values for testing.            
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceId, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, 
                       buyingAddress, capacityControl, purchase_service)

            providers.append(provider)
            i = i + 1


        # start the providers
        provider1 = providers[0]  # backhaul provider - Bulk capacity.
        provider2 = providers[1]  # isp monopoly provider 

        provider1.start_agent()
        provider1.initialize()
        provider2.start_agent()
        provider2.initialize()

        fileResult1 = open(provider1.getProviderId() + '.log',"a")
        fileResult2 = open(provider2.getProviderId() + '.log',"a")        
        
        # test the function sortByLastMarketShare
        deleteDBPreviousInformation(cursor)
        executionCount = getExecutionCount(cursor)         
        currentPeriod = 12
        
        test_sort_by_last_market_share(cursor, provider2, executionCount, fileResult2)
        
        radius = 0.1
        staged_bids = {}    
        serviceIsp = provider2.getService(serviceIdISP)        
        provider2.maintainBids(currentPeriod, radius, serviceIsp, staged_bids, fileResult2)
                
        if len(staged_bids) != 8:
            raise FoundationException("Error in calculating method maintainBids of Provider")
        
        staged_bids.clear()
        provider2.moveBetterProfits(currentPeriod, radius, staged_bids, fileResult2)

        delay = 0.14
        price = 17	
        demand = 14
        bid4_16 = createBid(provider2.getProviderId(), serviceIdISP, delay, price)
        bid4_16.setUnitaryProfit(0.2)
        bid4_16.setCreationPeriod(10)
        bid4_16.setNumberPredecessor(1)
        insertDBBid(cursor, 10, executionCount, bid4_16)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_16, 0)        

        bid4_17 = createBid(provider2.getProviderId(), serviceIdISP, delay, price)
        bid4_17.setUnitaryProfit(0.2)
        bid4_17.setCreationPeriod(11)
        bid4_17.insertParentBid(bid4_16)
        bid4_17.setNumberPredecessor(2)
        insertDBBid(cursor, 11, executionCount, bid4_17)
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_17, 30)        

        bid4_18 = createBid(provider2.getProviderId(), serviceIdISP, delay, price)
        bid4_18.setUnitaryProfit(0.2)
        bid4_18.setCreationPeriod(12)
        bid4_18.insertParentBid(bid4_17)
        bid4_18.setNumberPredecessor(3)
        insertDBBid(cursor, 12, executionCount, bid4_18)
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_18, 20)        
        
        bid4_19 = createBid(provider2.getProviderId(), serviceIdISP, delay, price)
        bid4_19.setUnitaryProfit(0.2)
        bid4_19.setCreationPeriod(13)
        bid4_19.insertParentBid(bid4_18)
        bid4_19.setNumberPredecessor(4)
        insertDBBid(cursor, 13, executionCount, bid4_19)
        insertDBBidPurchase(cursor, 13, serviceIdISP, executionCount, bid4_19, 10)        
        

        currentPeriod = 14
        val_return, result_progression = provider2.continueDirectionImprovingProfits( currentPeriod, bid4_19, fileResult2)
        if val_return != False:
            raise FoundationException("Error in calculating method continueDirectionImprovingProfits of Provider")
            
        if len(result_progression) != 4:
            raise FoundationException("Error in calculating method continueDirectionImprovingProfits of Provider")

        logger.info('End test sortByLastMarketShare')


        #----------------------------------------        
        # test the method improveBidForProfits 
        #----------------------------------------

        serviceBackHaul = provider2.getService(serviceIdBackhaul)        
        variablePrice = serviceBackHaul.getDecisionVariable('4') #Price
        minValuePrice = variablePrice.getMinValue()        
        maxValuePrice = variablePrice.getMaxValue()
        maxValuePriceRange = (maxValuePrice - minValuePrice) * provider2.getAdaptationFactor()

        variableQual = serviceBackHaul.getDecisionVariable('3')
        minValueQual = variableQual.getMinValue()        
        maxValueQual = variableQual.getMaxValue()
        maxValueQualRange = (maxValueQual - minValueQual) * provider2.getAdaptationFactor()
                
        reverse = 1
        output2 = provider2.improveBidForProfits(serviceBackHaul, fileResult2, reverse)
        if ((output2['4'])['Direction'] != 1):
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['4'])['Step'] <= 0) or ((output2['4'])['Step'] >= maxValuePriceRange) ):
            raise FoundationException("error in the method of improveBidForProfits")

        if ((output2['3'])['Direction'] != -1):  # Quality
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['3'])['Step'] >= 0) or ((output2['3'])['Step'] <= maxValueQualRange *-1) ):
            raise FoundationException("error in the method of improveBidForProfits")

        reverse = -1
        output2 = provider2.improveBidForProfits(serviceBackHaul, fileResult2, reverse)
        if ((output2['4'])['Direction'] != -1):
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['4'])['Step'] >= 0) or ((output2['4'])['Step'] <= maxValuePriceRange*-1) ):
            raise FoundationException("error in the method of improveBidForProfits")

        if ((output2['3'])['Direction'] != 1):  # Quality
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['3'])['Step'] <= 0) or ((output2['3'])['Step'] >= maxValueQualRange) ):
            raise FoundationException("error in the method of improveBidForProfits")


        serviceIsp = provider2.getService(serviceIdISP)        
        variablePrice = serviceIsp.getDecisionVariable('1') #Price
        minValuePrice = variablePrice.getMinValue()        
        maxValuePrice = variablePrice.getMaxValue()
        maxValuePriceRange = (maxValuePrice - minValuePrice) * provider2.getAdaptationFactor()

        variableQual = serviceIsp.getDecisionVariable('2') # Quality
        minValueQual = variableQual.getMinValue()        
        maxValueQual = variableQual.getMaxValue()
        maxValueQualRange = (maxValueQual - minValueQual) * provider2.getAdaptationFactor()

        reverse = 1
        output2 = provider2.improveBidForProfits(serviceIsp, fileResult2, reverse)
        if ((output2['1'])['Direction'] != 1):  # Price
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['1'])['Step'] <= 0) or ((output2['1'])['Step'] >= maxValuePriceRange) ):
            raise FoundationException("error in the method of improveBidForProfits")

        if ((output2['2'])['Direction'] != 1):
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['2'])['Step'] <= 0) or ((output2['2'])['Step'] >= maxValueQualRange) ):
            raise FoundationException("error in the method of improveBidForProfits")
            
        reverse = -1
        output2 = provider2.improveBidForProfits(serviceIsp, fileResult2, reverse)
        if ((output2['1'])['Direction'] != -1):  # Price
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['1'])['Step'] >= 0) or ((output2['1'])['Step'] <= maxValuePriceRange*-1) ):
            raise FoundationException("error in the method of improveBidForProfits")

        if ((output2['2'])['Direction'] != -1):
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['2'])['Step'] >= 0) or ((output2['2'])['Step'] <= maxValueQualRange*-1) ):
            raise FoundationException("error in the method of improveBidForProfits")

        logger.info('End test improveBidForProfits')

        # -----------------------------
        # Test the function generate direction between two bids.
        # -----------------------------
        price1 = 17.5
        delay1 = 0.2
        
        price2 = 15
        delay2 = 0.16
        bid4_20 = createBid(provider2.getProviderId(), serviceIdISP, delay1, price1)
        bid4_21 = createBid(provider2.getProviderId(), serviceIdISP, delay2, price2)
        
        output1 = provider2.generateDirectionBetweenTwoBids( bid4_20, bid4_21, fileResult2)
        output2 = provider2.generateDirectionBetweenTwoBids( bid4_21, bid4_20, fileResult2)

        if ((output1['1'])['Direction'] != -1):  # Price
            raise FoundationException("error in the method of generateDirectionBetweenTwoBids")

        if (((output1['1'])['Step'] >= 0)  ): # it is expected a negative step
            raise FoundationException("error in the method of improveBidForProfits")

        if ((output1['2'])['Direction'] != -1): # quality - improve
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output1['2'])['Step'] >= 0)  ): # it is expected a negative step
            raise FoundationException("error in the method of improveBidForProfits")
        

        if ((output2['1'])['Direction'] != 1):  # Price - greater price
            raise FoundationException("error in the method of generateDirectionBetweenTwoBids")

        if (((output2['1'])['Step'] <= 0)  ): # it is expected a positive step
            raise FoundationException("error in the method of improveBidForProfits")

        if ((output2['2'])['Direction'] != 1): # quality - decrease quality
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['2'])['Step'] <= 0)  ): # it is expected a positive step
            raise FoundationException("error in the method of improveBidForProfits")
        
        
        price3 = 15 
        quality3 = 0.4
        
        price4 = 11
        quality4 = 0.8
        bid1_20 = createBidBackhaul(provider1.getProviderId(), serviceIdBackhaul, quality3, price3)
        bid1_21 = createBidBackhaul(provider1.getProviderId(), serviceIdBackhaul, quality4, price4)
        
        output1 = provider1.generateDirectionBetweenTwoBids(bid1_20, bid1_21, fileResult1)
        output2 = provider1.generateDirectionBetweenTwoBids(bid1_21, bid1_20, fileResult1)
        

        if ((output1['4'])['Direction'] != -1):  # Price
            raise FoundationException("error in the method of generateDirectionBetweenTwoBids")

        if (((output1['4'])['Step'] >= 0)  ): # it is expected a negative step
            raise FoundationException("error in the method of improveBidForProfits")

        if ((output1['3'])['Direction'] != 1): # quality - improve
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output1['3'])['Step'] <= 0)  ): # it is expected a positive step
            raise FoundationException("error in the method of improveBidForProfits")
        

        if ((output2['4'])['Direction'] != 1):  # Price - greater price
            raise FoundationException("error in the method of generateDirectionBetweenTwoBids")

        if (((output2['4'])['Step'] <= 0)  ): # it is expected a postive step
            raise FoundationException("error in the method of improveBidForProfits")

        if ((output2['3'])['Direction'] != -1): # quality - decrease quality
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['3'])['Step'] >= 0)  ): # it is expected a negative step
            raise FoundationException("error in the method of improveBidForProfits")        

        logger.info('End test generateDirectionBetweenTwoBids')
        
        #---------------------------------------
        # Test Move Bid method
        #---------------------------------------
        price1 = 17.5
        delay1 = 0.2
        
        price2 = 15
        delay2 = 0.16
        
        price3 = 17
        delay3 = 0.15       
        bid4_20 = createBid(provider2.getProviderId(), serviceIdISP, delay1, price1)
        bid4_20.setNumberPredecessor(1)
        bid4_21 = createBid(provider2.getProviderId(), serviceIdISP, delay2, price2)
        bid4_21.setNumberPredecessor(1)
        bid4_22 = createBid(provider2.getProviderId(), serviceIdISP, delay3, price3)
        bid4_22.setNumberPredecessor(1)

        output1 = provider2.generateDirectionBetweenTwoBids( bid4_20, bid4_21, fileResult2)
        output2 = provider2.generateDirectionBetweenTwoBids( bid4_20, bid4_22, fileResult2)
        output3 = { }
        output3['1'] = {'Direction': 0, 'Step': 0 } 
        output3['2'] = {'Direction': 0, 'Step': 0 } 
        
        
        moveDirections= []
        moveDirections.append(output1)
        moveDirections.append(output2)
        moveDirections.append(output3)
        
        staged_bids = {}        
        marketShare = 0        
        provider2.moveBid(currentPeriod, radius, bid4_20, moveDirections, marketShare, staged_bids, Provider.PROFIT_ORIENTED, fileResult2)
        
        # It should inactivivate the bid for and move it for the two first cases.
        if len(staged_bids) != 3:
            raise FoundationException("error in the method moveBid - 1 ") 
                
        staged_bids = {}        
        marketShare = 0        
        provider2.moveBid(currentPeriod, radius, bid4_20, moveDirections, marketShare, staged_bids, Provider.MARKET_SHARE_ORIENTED, fileResult2)

        if len(staged_bids) != 3:
            raise FoundationException("error in the method moveBid - 2") 

        staged_bids = {}        
        marketShare = 3  
        provider2.moveBid(currentPeriod, radius, bid4_20, moveDirections, marketShare, staged_bids, Provider.PROFIT_ORIENTED, fileResult2)

        if len(staged_bids) != 4:
            raise FoundationException("error in the method moveBid - 3") 

        staged_bids = {}        
        marketShare = 3  
        provider2.moveBid(currentPeriod, radius, bid4_20, moveDirections, marketShare, staged_bids, Provider.MARKET_SHARE_ORIENTED, fileResult2)

        if len(staged_bids) != 4:
            raise FoundationException("error in the method moveBid - 4") 
        
        prev_type = provider2._list_vars['Type']
        provider2._list_vars['Type'] = AgentType(AgentType.PROVIDER_BACKHAUL)
        
        staged_bids = {}        
        marketShare = 3  
        provider2.moveBid(currentPeriod, radius, bid4_20, moveDirections, marketShare, staged_bids, Provider.PROFIT_ORIENTED, fileResult2)

        if len(staged_bids) != 4:
            raise FoundationException("error in the method moveBid - 5") 

        staged_bids = {}        
        marketShare = 3  
        provider2.moveBid(currentPeriod, radius, bid4_20, moveDirections, marketShare, staged_bids, Provider.MARKET_SHARE_ORIENTED, fileResult2)

        if len(staged_bids) != 4:
            raise FoundationException("error in the method moveBid - 6") 
        
        logger.info('End test MoveBid')
        
        provider2._list_vars['Type'] = prev_type
        logger.info('Ending test_provider_edge_monopoly_current_bids')
        
    except FoundationException as e:
        print e.__str__()
        fileResult1.close()
        fileResult2.close()
    except ProviderException as e:
        print e.__str__()
    except Exception as e:
        print e.__str__()
    finally:
        # disconnect from server
        db.close()
        provider1.stop_agent()
        provider2.stop_agent()



def test_integrated_classes():
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
	    WHERE status = 'A'"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql)
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

        logger.info('Number of providers open: %d', len(providers) )
        
        k = 0
        while (k < i - 1):
            logger.info('Starting provider %d', k)
            w = providers[k]
            w.start_agent()
            logger.info('After starting provider %d', k)
            w.initialize()
            w._list_vars['State'] == AgentServerHandler.BID_PERMITED
            w.exec_algorithm()
            w.stop_agent()
            logger.info('Stopped provider %d', k)
            k = k + 1
                        
        logger.info('Ending test_integrated_classes')
        
    except FoundationException as e:
        print e.__str__()
    except ProviderException as e:
        print e.__str__()
    except Exception as e:
        print e.__str__()
    finally:
        	# disconnect from server
        	db.close()

def test_provider_exploration_functions():
    logger.info('Starting test_provider_exploration_functions')

    list_classes = {}
    # Load Provider classes
    load_classes(list_classes)
    
    # Open database connection
    db = MySQLdb.connect(foundation.agent_properties.addr_database,foundation.agent_properties.user_database, \
        foundation.agent_properties.user_password,foundation.agent_properties.database_name )
    
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
        WHERE id = 1"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()

        serviceId = '1'            
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
            
            capacityControl = 'G' # Bulk Capacity.
            class_name = 'Provider'
            sellingAddress = foundation.agent_properties.addr_mktplace_backhaul
            buyingAddress = ' '
            providerId = 1
            providerName = 'Provider' + str(providerId)
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceId, 
                          providerSeed, marketPosition, adaptationFactor, 
                          monopolistPosition, debug, resources, numberOffers, 
                          numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, 
                        buyingAddress, capacityControl, purchase_service)
            providers.append(provider)
            
            i = i + 1
            
            class_name = 'Provider'
            providerId = 2
            providerName = 'Provider' + str(providerId)
            serviceId = '2'
            sellingAddress = foundation.agent_properties.addr_mktplace_backhaul
            buyingAddress = ' '
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceId, 
                          providerSeed, marketPosition, adaptationFactor, 
                          monopolistPosition, debug, resources, numberOffers, 
                          numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, 
                        buyingAddress, capacityControl, purchase_service)
            providers.append(provider)

            class_name = 'Provider'
            serviceId = '3'
            providerId = 3
            providerName = 'Provider' + str(providerId)
            
            sellingAddress = foundation.agent_properties.addr_mktplace_backhaul
            buyingAddress = ' '
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceId, 
                          providerSeed, marketPosition, adaptationFactor, 
                          monopolistPosition, debug, resources, numberOffers, 
                          numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, 
                        buyingAddress, capacityControl, purchase_service)
            providers.append(provider)

            i = i + 1

        # start the providers
        provider1 = providers[0]  # backhaul provider - Bulk capacity.
        provider2 = providers[1]
        provider3 = providers[2]
        
        provider1.start_agent()
        fileResult1 = open(provider1.getProviderId() + '.log',"a")

        provider2.start_agent()
        fileResult2 = open(provider2.getProviderId() + '.log',"a")

        provider3.start_agent()
        fileResult3 = open(provider3.getProviderId() + '.log',"a")

        minBid = provider1.calculateBidMinimumQuality()
        maxBid = provider1.calculateBidMaximumQuality()
        
        # Verifies the bid price of the lower bid.
        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = minBid.getDecisionVariable(decisionVariable)
                if price != 12:
                    raise FoundationException("error in the method calculateBidMinimumQuality()")
                
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = minBid.getDecisionVariable(decisionVariable)
                if quality != 0.2:
                    raise FoundationException("error in the method calculateBidMinimumQuality()")
        
        # Verifies the bid price of the upper bid.
        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = maxBid.getDecisionVariable(decisionVariable)
                if price != 20:
                    raise FoundationException("error in the method calculateBidMaximumQuality() price != 20: - " + str(price))
                
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = maxBid.getDecisionVariable(decisionVariable)
                if quality != 0.14:
                    raise FoundationException("error in the method calculateBidMaximumQuality() quality!=0.14 - " + str(quality))

        minBid = provider2.calculateBidMinimumQuality()
        maxBid = provider2.calculateBidMaximumQuality()
        
        # Verifies the bid price of the lower bid.
        for decisionVariable in (provider2._service)._decision_variables:
            if ((provider2._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = minBid.getDecisionVariable(decisionVariable)
                if price != 10:
                    raise FoundationException("error in the method calculateBidMinimumQuality() price != 10 - " + str(price))
                
            if ((provider2._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = minBid.getDecisionVariable(decisionVariable)
                if quality != 0:
                    raise FoundationException("error in the method calculateBidMinimumQuality() quality != 0 - " + str(quality))

        # Verifies the bid price of the upper bid.
        for decisionVariable in (provider2._service)._decision_variables:
            print 'here we are 10a'
            if ((provider2._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = maxBid.getDecisionVariable(decisionVariable)
                if price != 18:
                    raise FoundationException("error in the method calculateBidMaximumQuality() price != 18 - " + str(price))
                
            if ((provider2._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = maxBid.getDecisionVariable(decisionVariable)
                if quality != 1:
                    raise FoundationException("error in the method calculateBidMaximumQuality() quality != 1 - " + str(quality))

        minBid = provider3.calculateBidMinimumQuality()
        maxBid = provider3.calculateBidMaximumQuality()

        # Verifies the bid price of the lower bid.
        for decisionVariable in (provider3._service)._decision_variables:
            if ((provider3._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = minBid.getDecisionVariable(decisionVariable)
                if price != 0:
                    raise FoundationException("error in the method calculateBidMinimumQuality() price != 0 - " + str(price))
                
            if ((provider3._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = minBid.getDecisionVariable(decisionVariable)
                if quality != 1:
                    raise FoundationException("error in the method calculateBidMinimumQuality() quality != 1 - " + str(quality))
        
        # Verifies the bid price of the upper bid.
        for decisionVariable in (provider3._service)._decision_variables:
            if ((provider3._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = maxBid.getDecisionVariable(decisionVariable)
                if price != 1:
                    raise FoundationException("error in the method calculateBidMaximumQuality() price != 1 - " + str(price))
                
            if ((provider3._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = maxBid.getDecisionVariable(decisionVariable)
                if quality != 0:
                    raise FoundationException("error in the method calculateBidMaximumQuality() quality != 0 - " + str(quality))
        

        # test the creation of the lower actual quality bid given a set of bids.

        # we create 5 bid, bid 3 is the lowest bid and bid 4 is the greatest bid.
        # this bids are from service 1. 

        bid1 = createBid(provider1.getProviderId(), provider1.getServiceId(), 0.147, 19.3)
        bid2 = createBid(provider1.getProviderId(), provider1.getServiceId(), 0.15, 19)
        bid3 = createBid(provider1.getProviderId(), provider1.getServiceId(), 0.18, 17)
        bid4 = createBid(provider1.getProviderId(), provider1.getServiceId(), 0.145, 19.5)
        bid5 = createBid(provider1.getProviderId(), provider1.getServiceId(), 0.16, 18)

        provider1.lock.acquire()
        (provider1._list_vars['Bids'])[bid1.getId()] = bid1
        (provider1._list_vars['Bids'])[bid2.getId()] = bid2
        (provider1._list_vars['Bids'])[bid3.getId()] = bid3
        (provider1._list_vars['Bids'])[bid4.getId()] = bid4
        (provider1._list_vars['Bids'])[bid5.getId()] = bid5
        provider1.lock.release()

        minBid = provider1.getBidMinimumQuality()
        maxBid = provider1.getBidMaximumQuality()
    
        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = minBid.getDecisionVariable(decisionVariable)
                if price != 17:
                    raise FoundationException("error in the method calculateBidMinimumQuality() price != 17 - " + str(price))
                
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = minBid.getDecisionVariable(decisionVariable)
                if quality != 0.18:
                    raise FoundationException("error in the method calculateBidMinimumQuality() price != 0.18 - " + str(quality))
    
        # test the creation of the greatest actual quality bid given a set of bids.
        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = maxBid.getDecisionVariable(decisionVariable)
                if price != 19.5:
                    raise FoundationException("error in the method calculateBidMaximumQuality() price!=19.5 - " + str(price))
                
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = maxBid.getDecisionVariable(decisionVariable)
                if quality != 0.145:
                    raise FoundationException("error in the method calculateBidMaximumQuality() quality!= 0.145 - " + str(quality))

        minBid = provider1.calculateBidMinimumQuality()
        maxBid = provider1.calculateBidMaximumQuality()
        minCurBid = provider1.getBidMinimumQuality()
        maxCurBid = provider1.getBidMaximumQuality()

        minCurBid.incrementPredecessor()
        maxCurBid.incrementPredecessor()

        output = provider1.generateDirectionMiddleMinimum( minCurBid, minBid, fileResult1)
        for decisionVariable in output:
            direction = (output[decisionVariable])['Direction']
            step = (output[decisionVariable])['Step']
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                stepTmp = (minBid.getDecisionVariable(decisionVariable) + minCurBid.getDecisionVariable(decisionVariable))/2
                stepTmp = stepTmp - minCurBid.getDecisionVariable(decisionVariable)
                if (step != stepTmp):
                    raise FoundationException("error in the method generateDirectionMiddleMinimum()- price step:" + str(stepTmp) + "val_step:" + str(step))
            else:
                stepTmp = minBid.getDecisionVariable(decisionVariable) - minCurBid.getDecisionVariable(decisionVariable)
                if (step != stepTmp):
                    raise FoundationException("error in the method generateDirectionMiddleMinimum() - quality step:" + str(stepTmp) + "val_step:" + str(step))

        output = provider1.generateDirectionMiddleMaximum( maxCurBid, maxBid, fileResult1)
        for decisionVariable in output:
            direction = (output[decisionVariable])['Direction']
            step = (output[decisionVariable])['Step']
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                stepTmp = maxBid.getDecisionVariable(decisionVariable) -maxCurBid.getDecisionVariable(decisionVariable)
                if (step != stepTmp):
                    raise FoundationException("error in the method generateDirectionMiddleMaximum()- price step:" + str(stepTmp) + "val_step:" + str(step))
            else:
                stepTmp = (maxBid.getDecisionVariable(decisionVariable) + maxCurBid.getDecisionVariable(decisionVariable))/2
                stepTmp = stepTmp - maxCurBid.getDecisionVariable(decisionVariable)
                if (step != stepTmp):
                    raise FoundationException("error in the method generateDirectionMiddleMaximum() - quality step:" + str(stepTmp) + "val_step:" + str(step))

        minBid = provider2.calculateBidMinimumQuality()
        maxBid = provider2.calculateBidMaximumQuality()
        bid2_1 = createBidBackhaul(provider2.getProviderId(), provider2.getServiceId(), 0.5, 14)
        output = provider2.generateDirectionMiddleMinimum( bid2_1, minBid, fileResult2)
        for decisionVariable in output:
            direction = (output[decisionVariable])['Direction']
            step = (output[decisionVariable])['Step']
            if ((provider2._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                stepTmp = (minBid.getDecisionVariable(decisionVariable) + bid2_1.getDecisionVariable(decisionVariable))/2
                stepTmp = stepTmp - bid2_1.getDecisionVariable(decisionVariable)
                if (step != stepTmp):
                    raise FoundationException("error in the method generateDirectionMiddleMinimum()- price step:" + str(stepTmp) + "val_step:" + str(step))
            else:
                stepTmp = minBid.getDecisionVariable(decisionVariable) - bid2_1.getDecisionVariable(decisionVariable)
                if (step != stepTmp):
                    raise FoundationException("error in the method generateDirectionMiddleMinimum() - quality step:" + str(stepTmp) + "val_step:" + str(step))

        output = provider2.generateDirectionMiddleMaximum( bid2_1, maxBid, fileResult2)
        for decisionVariable in output:
            direction = (output[decisionVariable])['Direction']
            step = (output[decisionVariable])['Step']
            if ((provider2._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                stepTmp = maxBid.getDecisionVariable(decisionVariable) -bid2_1.getDecisionVariable(decisionVariable)
                if (step != stepTmp):
                    raise FoundationException("error in the method generateDirectionMiddleMaximum()- price step:" + str(stepTmp) + "val_step:" + str(step))
            else:
                stepTmp = (maxBid.getDecisionVariable(decisionVariable) + bid2_1.getDecisionVariable(decisionVariable))/2
                stepTmp = stepTmp - bid2_1.getDecisionVariable(decisionVariable)
                if (step != stepTmp):
                    raise FoundationException("error in the method generateDirectionMiddleMaximum() - quality step:" + str(stepTmp) + "val_step:" + str(step))

        currentPeriod = 2
        radius = 0.1
        staged_bids = {}
        minBid = provider1.calculateBidMinimumQuality()
        maxBid = provider1.calculateBidMaximumQuality()

        # test the creation of the new exploratory lowest quality with the alreay lowest quality bid.
        newMinBid = provider1.calculateNewBidMinimumQuality(currentPeriod, radius, minBid, minBid, staged_bids, fileResult1)
        if (newMinBid != None):
            # No new bid should be generated as the current bid and the destin bid are equal
            raise FoundationException("error in the method calculateNewBidMinimumQuality() - No new bid is possible" )
        
        if len(staged_bids) != 0:
            raise FoundationException("error in the method calculateNewBidMinimumQuality() - No new bid is possible" )
        
        print 'MinCurBid:', minCurBid.__str__(), 'minBid:', minBid.__str__()
        
        # test the creation of the new exploratory lowest quality bid based on two bids.
        newMinBid = provider1.calculateNewBidMinimumQuality(currentPeriod, radius, minCurBid, minBid, staged_bids, fileResult1)

        if (newMinBid.getNumberPredecessor() != 1):
            raise FoundationException("error in the method calculateNewBidMinimumQuality() - Wrong ancestor number !=1 -" + str(newMinBid.getNumberPredecessor()) )

        # test the creation of the greatest actual quality bid given a set of bids.
        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = newMinBid.getDecisionVariable(decisionVariable)
                if price != 14.5:
                    raise FoundationException("error in the method calculateBidMaximumQuality() price!=14.5 - " + str(price))
                
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = newMinBid.getDecisionVariable(decisionVariable)
                if quality != 0.2:
                    raise FoundationException("error in the method calculateBidMaximumQuality() quality!= 0.2 - " + str(quality))


        # test the creation of the new exploratory high quality with the alreay highest quality bid.
        newMaxBid = provider1.calculateNewBidMaximumQuality(currentPeriod, radius, maxBid, maxBid, staged_bids, fileResult1)
        if (newMaxBid != None):
            # No new bid should be generated as the current bid and the destin bid are equal
            raise FoundationException("error in the method calculateNewBidMaximumQuality() - No new bid is possible" )

        if len(staged_bids) != 1:
            raise FoundationException("error in the method calculateNewBidMaximumQuality() - No new bid is possible" )
    
        # test the creation of the new exploratory highest quality bid based on two bids.
        newMaxBid = provider1.calculateNewBidMaximumQuality(currentPeriod, radius, maxCurBid, maxBid, staged_bids, fileResult1)
        if (newMaxBid.getNumberPredecessor() != 1):
            raise FoundationException("error in the method calculateNewBidMaximumQuality() - Wrong ancestor number !=1 -" + newMaxBid.getNumberPredecessor())

        # test the creation of the greatest actual quality bid given a set of bids.
        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = newMaxBid.getDecisionVariable(decisionVariable)
                if price != 20:
                    raise FoundationException("error in the method calculateBidMaximumQuality() price!=20 - " + str(price))
                
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = newMaxBid.getDecisionVariable(decisionVariable)
                if round(quality,4) != 0.1425:
                    raise FoundationException("error in the method calculateBidMaximumQuality() quality!= 0.1425 - " + str(quality))

        if len(staged_bids) != 2:
            raise FoundationException("error in the method calculateNewBidMaximumQuality() - bid not included in staged_bids" )

        # Test the method with the delta update.
        marketPosition = 0.5
        initialNumberBids = 10
        staged_bids = provider1.initializeBids(marketPosition, initialNumberBids, fileResult1)
        for bidId in staged_bids:
            bid = (staged_bids[bidId])['Object']
            if bid.getNumberPredecessor() != 1:
                raise FoundationException("error in the method initializeBids() - Incorrect num of predecessors" )

        # Perfom the move of the bid towards the higest quality bid.
        for bidId in staged_bids:
            staged_bids2 = {}
            bid = (staged_bids[bidId])['Object']
            directions = []
            output = provider1.generateDirectionBetweenTwoBids(bid, maxBid, fileResult1)
            directions.append(output)
            provider1.moveBid(currentPeriod, radius, bid, directions, 1, staged_bids2, Provider.MARKET_SHARE_ORIENTED, fileResult1)
            assert len(staged_bids2) == 3, "Error in the number of bids created"
            for bidId2 in staged_bids2:
                bid2 = (staged_bids2[bidId2])['Object']
                action = (staged_bids2[bidId2])['Action']
                if (action != Bid.INACTIVE):
                    if bid2.getNumberPredecessor() != (bid.getNumberPredecessor() + 1):
                        raise FoundationException("error in the method moveBid() - Incorrect num of predecessors"  
                                                + "NumResult:" + str(bid2.getNumberPredecessor()) 
                                                    + "Numexpected:" + str(bid.getNumberPredecessor() + 1) )

        
        #-------------------------------------
        # test the method exploreMarket
        #-------------------------------------
        staged_bids3 = {}
        provider1.exploreMarket(currentPeriod, radius, staged_bids3, fileResult1)
        if len(staged_bids3) != 0: # In this case the calculated probability is: 0.763531544593
            raise FoundationException("error in the method exploreMarket()" )

        provider1.lock.acquire()
        provider1._used_variables['adaptationFactor'] = 0.6
        provider1.lock.release()
        
        provider1.exploreMarket(currentPeriod, radius, staged_bids3, fileResult1)
        if len(staged_bids3) != 2: # In this case the calculated probability is: 0.403569183284
            raise FoundationException("error in the method exploreMarket()" )

        
        
        
        #-------------------------------------
        # test the method moveBidOnDirection
        #-------------------------------------

        bid6 = createBid(provider1.getProviderId(), provider1.getServiceId(), 0.18, 17)
        # As the number of predecessors is 2 all steps are divided by 2.
        bid6.setNumberPredecessor(2) 

        # Test when the step is less than the maximum step.
        output1 = {}
        output1['1'] = {'Direction' : 1, 'Step': 0.5}
        output1['2'] = {'Direction' : 1, 'Step': 0.02}
        newBid1, bidPrice1, send1 = provider1.moveBidOnDirection(bid6, output1, fileResult1)

        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = newBid1.getDecisionVariable(decisionVariable)
                if round(price,2) != 17.25:
                    raise FoundationException("error in the method moveBidOnDirection() -1- price!=17.25 - " + str(price))
                
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = newBid1.getDecisionVariable(decisionVariable)
                if round(quality,2) != 0.19:
                    raise FoundationException("error in the method moveBidOnDirection() -1- quality!= 0.19 - " + str(quality))

        output2 = {}
        output2['1'] = {'Direction' : -1, 'Step': -0.5}
        output2['2'] = {'Direction' : 1, 'Step': 0.02}
        newBid2, bidPrice2, send2 = provider1.moveBidOnDirection(bid6, output2, fileResult1)

        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = newBid2.getDecisionVariable(decisionVariable)
                if round(price,2) != 16.75:
                    raise FoundationException("error in the method moveBidOnDirection() -2- price!=16.75 - " + str(price))
                
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = newBid2.getDecisionVariable(decisionVariable)
                if round(quality,2) != 0.19:
                    raise FoundationException("error in the method moveBidOnDirection() -2- quality!= 0.19 - " + str(quality))

        output3 = {}
        output3['1'] = {'Direction' : 1, 'Step': 0.5}
        output3['2'] = {'Direction' : -1, 'Step': -0.02}
        newBid3, bidPrice3, send3 = provider1.moveBidOnDirection(bid6, output3, fileResult1)

        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = newBid3.getDecisionVariable(decisionVariable)
                if round(price,2) != 17.25:
                    raise FoundationException("error in the method moveBidOnDirection() -3- price!=17.25 - " + str(price))
                
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = newBid3.getDecisionVariable(decisionVariable)
                if round(quality,2) != 0.17:
                    raise FoundationException("error in the method moveBidOnDirection() -3- quality!= 0.17 - " + str(quality))

        output4 = {}
        output4['1'] = {'Direction' : -1, 'Step': -0.5}
        output4['2'] = {'Direction' : -1, 'Step': -0.02}
        newBid4, bidPrice4, send4 = provider1.moveBidOnDirection(bid6, output4, fileResult1)

        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = newBid4.getDecisionVariable(decisionVariable)
                if round(price,2) != 16.75:
                    raise FoundationException("error in the method moveBidOnDirection() -4- price!=16.75 - " + str(price))
                
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = newBid4.getDecisionVariable(decisionVariable)
                if round(quality,2) != 0.17:
                    raise FoundationException("error in the method moveBidOnDirection() -4- quality!= 0.17 - " + str(quality))

        output5 = {}
        output5['1'] = {'Direction' : 1, 'Step': 0.5}
        output5['2'] = {'Direction' : 0, 'Step': 0}
        newBid5, bidPrice5, send5 = provider1.moveBidOnDirection(bid6, output5, fileResult1)

        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = newBid5.getDecisionVariable(decisionVariable)
                if round(price,2) != 17.25:
                    raise FoundationException("error in the method moveBidOnDirection() -5- price!=17.25 - " + str(price))
                
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = newBid5.getDecisionVariable(decisionVariable)
                if round(quality,2) != 0.18:
                    raise FoundationException("error in the method moveBidOnDirection() -5- quality!= 0.18 - " + str(quality))

        output6 = {}
        output6['1'] = {'Direction' : 0, 'Step': 0}
        output6['2'] = {'Direction' : 1, 'Step': 0.02}
        newBid6, bidPrice6, send6 = provider1.moveBidOnDirection(bid6, output6, fileResult1)

        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = newBid6.getDecisionVariable(decisionVariable)
                if round(price,2) != 17:
                    raise FoundationException("error in the method moveBidOnDirection() -6- price!=17 - " + str(price))
                
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = newBid6.getDecisionVariable(decisionVariable)
                if round(quality,2) != 0.19:
                    raise FoundationException("error in the method moveBidOnDirection() -6- quality!= 0.18 - " + str(quality))


        # Test when the step is greater than the maximum step.
        adapt_factor = 0.0001
        provider1.lock.acquire()
        provider1._used_variables['adaptationFactor'] = adapt_factor
        provider1.lock.release()
        max_step_price = 0
        max_step_quality = 0
        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                min_value = (provider1._service.getDecisionVariable(decisionVariable)).getMinValue()
                max_value = (provider1._service.getDecisionVariable(decisionVariable)).getMaxValue()
                max_step_price = (max_value - min_value)* adapt_factor
                
            else:
                min_value = (provider1._service.getDecisionVariable(decisionVariable)).getMinValue()
                max_value = (provider1._service.getDecisionVariable(decisionVariable)).getMaxValue()
                max_step_quality = (max_value - min_value)* adapt_factor


        output1 = {}
        output1['1'] = {'Direction' : 1, 'Step': 0.5}
        output1['2'] = {'Direction' : 1, 'Step': 0.02}
        newBid1, bidPrice1, send1 = provider1.moveBidOnDirection(bid6, output1, fileResult1)

        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = newBid1.getDecisionVariable(decisionVariable)
                price_tmp = round((bid6.getDecisionVariable(decisionVariable) + max_step_price),4)
                if round(price,4) != price_tmp:
                    raise FoundationException("error in the method moveBidOnDirection() -1- price!=" + str(price_tmp) + "-" + str(price))
                
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = newBid1.getDecisionVariable(decisionVariable)
                quality_tmp = round((bid6.getDecisionVariable(decisionVariable) + max_step_quality),4)
                if round(quality,4) != quality_tmp:
                    raise FoundationException("error in the method moveBidOnDirection() -1- quality!=" + str(quality_tmp) + "-" + str(quality))

        output2 = {}
        output2['1'] = {'Direction' : -1, 'Step': -0.5}
        output2['2'] = {'Direction' : 1, 'Step': 0.02}
        newBid2, bidPrice2, send2 = provider1.moveBidOnDirection(bid6, output2, fileResult1)

        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = newBid2.getDecisionVariable(decisionVariable)
                price_tmp = round((bid6.getDecisionVariable(decisionVariable) - max_step_price),4)
                if round(price,4) != price_tmp:
                    raise FoundationException("error in the method moveBidOnDirection() -2- price!=" + str(price_tmp) + "-" + str(price))
                
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = newBid2.getDecisionVariable(decisionVariable)
                quality_tmp = round((bid6.getDecisionVariable(decisionVariable) + max_step_quality),4)
                if round(quality,4) != quality_tmp:
                    raise FoundationException("error in the method moveBidOnDirection() -2- quality!= " + str(quality_tmp) + "-" + str(quality))

        output3 = {}
        output3['1'] = {'Direction' : 1, 'Step': 0.5}
        output3['2'] = {'Direction' : -1, 'Step': -0.02}
        newBid3, bidPrice3, send3 = provider1.moveBidOnDirection(bid6, output3, fileResult1)

        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = newBid3.getDecisionVariable(decisionVariable)
                price_tmp = round((bid6.getDecisionVariable(decisionVariable) + max_step_price),4)
                if round(price,4) != price_tmp:
                    raise FoundationException("error in the method moveBidOnDirection() -3- price!= " + str(price_tmp) + "-" + str(price))
                
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = newBid3.getDecisionVariable(decisionVariable)
                quality_tmp = round((bid6.getDecisionVariable(decisionVariable) - max_step_quality),4)
                if round(quality,4) != quality_tmp:
                    raise FoundationException("error in the method moveBidOnDirection() -3- quality!=" + str(quality_tmp) + "-" + str(quality))

        output4 = {}
        output4['1'] = {'Direction' : -1, 'Step': -0.5}
        output4['2'] = {'Direction' : -1, 'Step': -0.02}
        newBid4, bidPrice4, send4 = provider1.moveBidOnDirection(bid6, output4, fileResult1)

        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = newBid4.getDecisionVariable(decisionVariable)
                price_tmp = round((bid6.getDecisionVariable(decisionVariable) - max_step_price),4)
                if round(price,4) != price_tmp:
                    raise FoundationException("error in the method moveBidOnDirection() -4- price!=" + str(price_tmp) + "-" + str(price))
                
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = newBid4.getDecisionVariable(decisionVariable)
                quality_tmp = round((bid6.getDecisionVariable(decisionVariable) - max_step_quality),4)
                if round(quality,4) != quality_tmp:
                    raise FoundationException("error in the method moveBidOnDirection() -4- quality!= 0.17" + str(quality_tmp) + "-" + str(quality))

        output5 = {}
        output5['1'] = {'Direction' : 1, 'Step': 0.5}
        output5['2'] = {'Direction' : 0, 'Step': 0}
        newBid5, bidPrice5, send5 = provider1.moveBidOnDirection(bid6, output5, fileResult1)

        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = newBid5.getDecisionVariable(decisionVariable)
                price_tmp = round((bid6.getDecisionVariable(decisionVariable) + max_step_price),4)
                if round(price,4) != price_tmp:
                    raise FoundationException("error in the method moveBidOnDirection() -5- price!=" + str(price_tmp)+ "-" + str(price))
                
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = newBid5.getDecisionVariable(decisionVariable)
                quality_tmp = bid6.getDecisionVariable(decisionVariable)
                if round(quality,2) != quality_tmp:
                    raise FoundationException("error in the method moveBidOnDirection() -5- quality!= " + str(quality_tmp) + "-" + str(quality))

        output6 = {}
        output6['1'] = {'Direction' : 0, 'Step': 0}
        output6['2'] = {'Direction' : 1, 'Step': 0.02}
        newBid6, bidPrice6, send6 = provider1.moveBidOnDirection(bid6, output6, fileResult1)

        for decisionVariable in (provider1._service)._decision_variables:
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_PRICE):
                price = newBid6.getDecisionVariable(decisionVariable)
                price_tmp = bid6.getDecisionVariable(decisionVariable)
                if round(price,2) != price_tmp:
                    raise FoundationException("error in the method moveBidOnDirection() -6- price!=" + str(price_tmp) + "-" + str(price))
                
            if ((provider1._service)._decision_variables[decisionVariable].getModeling() == DecisionVariable.MODEL_QUALITY):
                quality = newBid6.getDecisionVariable(decisionVariable)
                quality_tmp = round((bid6.getDecisionVariable(decisionVariable) + max_step_quality),4)
                if round(quality,4) != quality_tmp:
                    raise FoundationException("error in the method moveBidOnDirection() -6- quality!=" + str(quality_tmp) + "-" + str(quality))

        logger.info('Ending test_provider_exploration_functions')
    
    except FoundationException as e:
        print e.__str__()
    except ProviderException as e:
        print e.__str__()
    except Exception as e:
        print e.__str__()
    finally:
        # disconnect from server
        fileResult1.close()
        fileResult2.close()
        fileResult3.close()
        provider1.stop_agent()
        provider2.stop_agent()
        provider3.stop_agent()
        db.close()
    


if __name__ == '__main__':
    #test_integrated_classes()
    #test_provider_exploration_functions()
    #test_cost_functions()
    #test_marketplace_capacity_management()
    #test_provider_general_methods()
    test_eliminateNeighborhoodBid()
    #test_provider_database_classes()
    #test_provider_edge_monopoly_classes()
    #test_provider_edge_monopoly_current_bids()
    
